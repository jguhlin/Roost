#!/usr/bin/env python3
"""
Unified data fetcher for Roost.

Fetches data from registered sources using appropriate methods.
Tracks download state, handles errors, and logs results.

Usage:
    python scripts/fetch.py [source_id ...]
    python scripts/fetch.py --all
    python scripts/fetch.py --type detection
    python scripts/fetch.py --status

Examples:
    python scripts/fetch.py aphis ireland_dafm
    python scripts/fetch.py --all --skip-manual
    python scripts/fetch.py --type detection --dry-run
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess

import httpx

from sources import (
    SOURCES, get_source, list_sources, DataSource,
    SourceType, AccessMethod
)


# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = Path("data/raw/external")
STATE_FILE = Path("data/.fetch_state.json")
LOG_FILE = Path("data/.fetch_log.jsonl")


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

def load_state() -> dict:
    """Load fetch state from file."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    """Save fetch state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def log_fetch(source_id: str, success: bool, records: int = 0, error: str = ""):
    """Append to fetch log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source_id,
        "success": success,
        "records": records,
        "error": error,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def file_checksum(path: Path) -> str:
    """Calculate MD5 checksum of a file."""
    if not path.exists():
        return ""
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


# =============================================================================
# FETCHERS
# =============================================================================

def fetch_direct(source: DataSource, output_path: Path, prev: dict = None) -> tuple[bool, int, str, dict]:
    """
    Fetch via direct HTTP download, with incremental support:
    sends If-None-Match / If-Modified-Since validators from the previous
    fetch; a 304 response or an identical checksum skips re-processing.

    Returns: (success, record_count, error_message, state_meta)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prev = prev or {}
    headers = {}
    if prev.get("etag"):
        headers["If-None-Match"] = prev["etag"]
    if prev.get("last_modified"):
        headers["If-Modified-Since"] = prev["last_modified"]

    try:
        with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(source.url)

            if resp.status_code == 304:
                return True, 0, "Not modified (304)", {
                    "etag": prev.get("etag"),
                    "last_modified": prev.get("last_modified"),
                    "checksum": prev.get("checksum"),
                }

            resp.raise_for_status()

            content = resp.content
            checksum = hashlib.md5(content).hexdigest()

            if prev.get("checksum") and checksum == prev["checksum"]:
                # Server ignored our validators but content is unchanged
                return True, 0, "Not modified (checksum)", {
                    "etag": resp.headers.get("etag", prev.get("etag")),
                    "last_modified": resp.headers.get("last-modified", prev.get("last_modified")),
                    "checksum": checksum,
                }

            with open(output_path, "wb") as f:
                f.write(content)

            # Count records if CSV
            records = 0
            if output_path.suffix == ".csv":
                with open(output_path) as f:
                    records = sum(1 for _ in f) - 1  # Minus header

            return True, records, "", {
                "etag": resp.headers.get("etag", ""),
                "last_modified": resp.headers.get("last-modified", ""),
                "checksum": checksum,
            }

    except Exception as e:
        return False, 0, str(e), {}


def _feature_oid(feature: dict, oid_field: str) -> str:
    """Stable identity for a feature (OID, falling back to its content)."""
    attrs = feature.get("attributes", feature)
    if oid_field and attrs.get(oid_field) is not None:
        return f"oid:{attrs[oid_field]}"
    return "hash:" + hashlib.md5(json.dumps(attrs, sort_keys=True, default=str).encode()).hexdigest()


def _merge_features(existing: list, new: list, oid_field: str):
    """Merge new features into existing by OID (new wins)."""
    merged = {_feature_oid(f, oid_field): f for f in existing}
    added = 0
    for f in new:
        key = _feature_oid(f, oid_field)
        if key not in merged:
            added += 1
        merged[key] = f
    return list(merged.values()), added


def _max_date_ms(features: list, date_field: str):
    """Largest epoch-ms value of date_field across features (None if absent)."""
    best = None
    for f in features:
        v = (f.get("attributes", f)).get(date_field)
        if isinstance(v, (int, float)) and v and (best is None or v > best):
            best = int(v)
    return best


def _ms_to_date_literal(ms: int) -> str:
    """Epoch ms → SQL date literal for ArcGIS WHERE clauses."""
    from datetime import timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date().isoformat()


FULL_REFRESH_DAYS = 7  # periodic full snapshot to catch edits/withdrawals


def fetch_arcgis(source: DataSource, output_path: Path, prev: dict = None,
                 full: bool = False) -> tuple[bool, int, str, dict]:
    """
    Fetch from an ArcGIS Feature Service with pagination.

    Incremental: if source.date_field is set and the previous fetch stored
    max_date_ms, only features newer than that are fetched and merged into
    the existing snapshot by OID. A full snapshot is taken when full=True or
    the last full fetch is older than FULL_REFRESH_DAYS (drift safety).

    Returns: (success, record_count, error_message, state_meta)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prev = prev or {}
    oid_field = source.api_params.get("oid_field", "OBJECTID")
    # Service-side date field (may differ from the ingest schema's date_field)
    svc_date_field = source.api_params.get("date_field") or source.date_field

    can_incremental = (
        bool(svc_date_field)
        and not full
        and prev.get("max_date_ms")
        and output_path.with_suffix(".json").exists()
    )
    if can_incremental and prev.get("last_full"):
        try:
            last_full = datetime.fromisoformat(prev["last_full"])
            if (datetime.now() - last_full).days >= FULL_REFRESH_DAYS:
                can_incremental = False
        except ValueError:
            pass

    where = source.arcgis_filter
    existing = []
    if can_incremental:
        date_lit = _ms_to_date_literal(int(prev["max_date_ms"]))
        where = f"({source.arcgis_filter}) AND ({svc_date_field} > DATE '{date_lit}')"
        try:
            with open(output_path.with_suffix(".json")) as f:
                existing = json.load(f).get("features", [])
        except (OSError, json.JSONDecodeError):
            existing = []
            can_incremental = False
            where = source.arcgis_filter

    all_features = []
    offset = 0
    batch_size = 2000

    try:
        with httpx.Client(timeout=120.0) as client:
            while True:
                params = {
                    "where": where,
                    "outFields": "*",
                    "f": "json",
                    "resultOffset": offset,
                    "resultRecordCount": batch_size,
                }

                resp = client.get(f"{source.url}/query", params=params)
                resp.raise_for_status()

                data = resp.json()
                if "error" in data:
                    return False, 0, data["error"].get("message", str(data["error"])), {}

                features = data.get("features", [])
                if not features:
                    break

                all_features.extend(features)

                # exceededTransferLimit is authoritative: the service may cap
                # pages below our batch_size (e.g. maxRecordCount=1000)
                if not data.get("exceededTransferLimit"):
                    break
                offset += len(features)

        if can_incremental:
            merged, added = _merge_features(existing, all_features, oid_field)
            all_features = merged
            print(f"      incremental: +{added} new, {len(all_features)} total in snapshot")

        if not all_features:
            return False, 0, "No features returned", {}

        # Save as CSV
        attrs = [f.get("attributes", f) for f in all_features]
        fieldnames = list(attrs[0].keys())

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(attrs)

        # Also save JSON with metadata
        json_path = output_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "source": source.id,
                "record_count": len(all_features),
                "features": all_features,
            }, f)

        meta = {
            "max_date_ms": _max_date_ms(all_features, svc_date_field) if svc_date_field else None,
            "last_full": prev.get("last_full") if can_incremental else datetime.now().isoformat(),
        }
        return True, len(all_features), "", meta

    except Exception as e:
        return False, 0, str(e), {}


def fetch_ncbi(source: DataSource, output_path: Path, prev: dict = None,
               full: bool = False) -> tuple[bool, int, str, dict]:
    """
    Fetch from NCBI using datasets CLI.

    Returns: (success, record_count, error_message, state_meta)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if source.id == "ncbi_genomes":
        cmd = f'pixi run datasets download genome taxon "Aves" --dehydrated --filename {output_path}'
    elif source.id == "ncbi_taxonomy":
        cmd = f"curl -o {output_path} {source.url}"
    else:
        return False, 0, f"Unknown NCBI source: {source.id}", {}

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False, 0, result.stderr, {}
        return True, 0, "", {}  # Record count not easily available
    except Exception as e:
        return False, 0, str(e), {}


# Scrapers for sources that need browser automation (source id -> script path)
SCRAPE_SCRIPTS = {
    "aphis_flocks": Path("scripts/fetch_aphis_flocks.py"),
}


def fetch_scrape(source: DataSource, output_path: Path, prev: dict = None) -> tuple[bool, int, str, dict]:
    """
    Fetch via a dedicated Playwright scraper script.

    The script prints a final "FETCH_RESULT: {json}" line with the record
    count and checksum; state bookkeeping (checksums for change detection)
    is handled here so scrapers stay simple.

    Returns: (success, record_count, error_message, state_meta)
    """
    script = SCRAPE_SCRIPTS.get(source.id)
    if not script or not script.exists():
        return False, 0, f"No scrape script for {source.id} at {script}", {}

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--output", str(output_path)],
            capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, 0, "Scraper timed out after 600s", {}

    if result.stdout:
        for line in result.stdout.splitlines():
            if not line.startswith("FETCH_RESULT:"):
                print(f"      {line}")

    if result.returncode != 0:
        return False, 0, (result.stderr or result.stdout or "scraper failed")[-500:], {}

    meta = {}
    for line in result.stdout.splitlines():
        if line.startswith("FETCH_RESULT:"):
            try:
                meta = json.loads(line.split("FETCH_RESULT:", 1)[1].strip())
            except json.JSONDecodeError:
                meta = {}
            break

    records = int(meta.get("records", 0))
    checksum = meta.get("checksum") or (file_checksum(output_path) if output_path.exists() else "")
    # Detect no-change without burning an extra pass
    if prev and prev.get("checksum") and checksum == prev["checksum"]:
        return True, records, "Not modified (checksum)", {"checksum": checksum}
    return True, records, "", {"checksum": checksum}


def fetch_source(source: DataSource, dry_run: bool = False, prev: dict = None,
                 full: bool = False) -> tuple[bool, int, str, dict]:
    """
    Fetch a data source using the appropriate method.

    Returns: (success, record_count, error_message, state_meta)
    """
    # Determine output path
    if source.output_dir:
        output_path = DATA_DIR / source.output_dir / source.output_file
    else:
        output_path = DATA_DIR / source.output_file

    if dry_run:
        print(f"  [DRY RUN] Would fetch to: {output_path}")
        return True, 0, "", {}

    prev = prev or {}

    # Route to appropriate fetcher
    if source.access == AccessMethod.DIRECT_DOWNLOAD:
        return fetch_direct(source, output_path, prev)
    elif source.access == AccessMethod.ARCGIS:
        return fetch_arcgis(source, output_path, prev, full)
    elif source.access == AccessMethod.NCBI:
        return fetch_ncbi(source, output_path, prev, full)
    elif source.access == AccessMethod.SCRAPE:
        return fetch_scrape(source, output_path, prev)
    elif source.access == AccessMethod.MANUAL:
        return False, 0, "Manual download required", {}
    elif source.access == AccessMethod.API:
        return False, 0, "API access not implemented for this source", {}
    else:
        return False, 0, f"Unknown access method: {source.access}", {}


# =============================================================================
# MAIN
# =============================================================================

def fetch_sources(
    source_ids: list[str],
    dry_run: bool = False,
    skip_manual: bool = True,
    full: bool = False,
) -> dict[str, tuple[bool, int, str]]:
    """
    Fetch multiple sources.

    Returns: dict of source_id -> (success, records, error)
    """
    results = {}
    state = load_state()

    for source_id in source_ids:
        source = get_source(source_id)

        print(f"\n{'='*60}")
        print(f"Fetching: {source.name}")
        print(f"{'='*60}")
        print(f"  Type: {source.type.value}")
        print(f"  Method: {source.access.value}")
        print(f"  URL: {source.url[:70]}...")

        if source.access == AccessMethod.MANUAL and skip_manual:
            print(f"  SKIPPED: Manual download required")
            print(f"  Notes: {source.notes}")
            results[source_id] = (False, 0, "Skipped (manual)")
            continue

        if source.type == SourceType.REFERENCE:
            print(f"  SKIPPED: Reference source (external link only)")
            results[source_id] = (False, 0, "Skipped (reference)")
            continue

        success, records, error, meta = fetch_source(source, dry_run, prev=state.get(source_id, {}), full=full)

        if success:
            note = f" ({error})" if error else ""
            print(f"  SUCCESS: {records:,} records{note}")
            entry = {
                "last_fetch": datetime.now().isoformat(),
                "records": records,
                "success": True,
            }
            if error:
                entry["note"] = error  # e.g. "Not modified (304)"
            # Preserve/merge incremental state (etag, checksum, max_date_ms, last_full)
            for key in ("etag", "last_modified", "checksum", "max_date_ms", "last_full"):
                if meta.get(key) is not None:
                    entry[key] = meta[key]
                elif key in state.get(source_id, {}):
                    entry[key] = state[source_id][key]
            state[source_id] = entry
        else:
            print(f"  FAILED: {error}")
            state[source_id] = {
                **state.get(source_id, {}),
                "last_fetch": datetime.now().isoformat(),
                "success": False,
                "error": error,
            }

        log_fetch(source_id, success, records, error)
        results[source_id] = (success, records, error)

    if not dry_run:
        save_state(state)

    return results


def print_status():
    """Print status of all sources."""
    state = load_state()

    print(f"{'Source':<20} {'Type':<12} {'Last Fetch':<20} {'Records':<10} {'Status'}")
    print("-" * 80)

    for source_id, source in sorted(SOURCES.items()):
        s = state.get(source_id, {})

        last_fetch = s.get("last_fetch", "Never")[:19] if s else "Never"
        records = s.get("records", "-") if s else "-"
        status = "OK" if s.get("success") else ("FAILED" if s else "PENDING")

        if source.access == AccessMethod.MANUAL:
            status = "MANUAL"
        elif source.type == SourceType.REFERENCE:
            status = "LINKED"

        print(f"{source_id:<20} {source.type.value:<12} {last_fetch:<20} {str(records):<10} {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch data from registered sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "sources", nargs="*",
        help="Source IDs to fetch (default: none)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Fetch all downloadable sources"
    )
    parser.add_argument(
        "--type", "-t", choices=[t.value for t in SourceType],
        help="Fetch sources of this type"
    )
    parser.add_argument(
        "--status", "-s", action="store_true",
        help="Show status of all sources"
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true",
        help="Show what would be fetched without downloading"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Force full fetch (skip incremental 304/date-filter shortcuts)"
    )
    parser.add_argument(
        "--skip-manual", action="store_true", default=True,
        help="Skip sources requiring manual download (default: True)"
    )
    parser.add_argument(
        "--include-manual", action="store_true",
        help="Include sources requiring manual download"
    )

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    # Determine which sources to fetch
    source_ids = []

    if args.all:
        source_ids = [s.id for s in list_sources(downloadable_only=True)]
    elif args.type:
        stype = SourceType(args.type)
        source_ids = [s.id for s in list_sources(source_type=stype, downloadable_only=True)]
    elif args.sources:
        source_ids = args.sources
    else:
        parser.print_help()
        print("\nAvailable sources:")
        for s in SOURCES.values():
            auth = " [AUTH]" if s.requires_auth else ""
            print(f"  {s.id}: {s.name}{auth}")
        return

    # Validate source IDs
    for sid in source_ids:
        if sid not in SOURCES:
            print(f"Unknown source: {sid}")
            sys.exit(1)

    # Fetch
    skip_manual = not args.include_manual
    results = fetch_sources(source_ids, dry_run=args.dry_run, skip_manual=skip_manual,
                            full=args.full)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)

    success_count = sum(1 for s, r, e in results.values() if s)
    fail_count = sum(1 for s, r, e in results.values() if not s and "Skipped" not in e)
    skip_count = sum(1 for s, r, e in results.values() if "Skipped" in e)

    for source_id, (success, records, error) in results.items():
        status = "OK" if success else ("SKIP" if "Skipped" in error else "FAIL")
        rec_str = f"{records:,}" if records else "-"
        print(f"  {source_id}: {status} ({rec_str} records)")

    print(f"\nSuccess: {success_count}, Failed: {fail_count}, Skipped: {skip_count}")


if __name__ == "__main__":
    main()
