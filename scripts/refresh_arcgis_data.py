#!/usr/bin/env python3
"""
Refresh avian influenza data from ArcGIS feature services.

This script fetches the latest data from publicly accessible ArcGIS
dashboards and saves them for integration into the detection pipeline.

Usage:
    python scripts/refresh_arcgis_data.py [--source SOURCE]

Sources:
    canada     - Canada CWHC HPAI Wildlife Dashboard
    vs         - VS Wild Bird Surveillance (USDA)
    all        - All sources (default)

Run periodically (e.g., weekly) to keep data current.
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

DATA_DIR = Path("data/raw/external/arcgis-hpai")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Incremental-fetch state (per source: max date seen, last full snapshot)
STATE_FILE = DATA_DIR / "_state.json"
FULL_REFRESH_DAYS = 7  # periodic full snapshot to catch edits/withdrawals

# ArcGIS Feature Service endpoints
SOURCES = {
    "canada": {
        "name": "Canada CWHC HPAI Wildlife Dashboard",
        "url": "https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/hpai_dashboard/FeatureServer/0",
        "filter": "Species_Group='Bird' AND HPAI='High Path'",
        "output_prefix": "Canada_HPAI_HighPath_Birds",
        "date_field": "Date_Found",   # service-side epoch-ms field
        "oid_field": "ObjectId",
    },
    "vs": {
        "name": "VS Wild Bird Surveillance",
        "url": "https://services7.arcgis.com/2C1NQ7u6M6SXoa8p/arcgis/rest/services/VS_Avian_Influenza_Wild_Bird_Surveillance_Dashboard_data_view_feature_layer_/FeatureServer/0",
        "filter": "1=1",
        "output_prefix": "VS_Wild_Bird_Surveillance",
        "date_field": "Date_Collected",
        "oid_field": "OBJECTID",
    },
    "vs_h5": {
        "name": "VS Wild Bird Surveillance (H5 Positive)",
        "url": "https://services7.arcgis.com/2C1NQ7u6M6SXoa8p/arcgis/rest/services/VS_Avian_Influenza_Wild_Bird_Surveillance_Dashboard_data_view_feature_layer_/FeatureServer/0",
        "filter": "Final_H5='Detected'",
        "output_prefix": "VS_Wild_Bird_H5_Positive",
        "date_field": "Date_Collected",
        "oid_field": "OBJECTID",
    },
}


def load_incremental_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_incremental_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def feature_key(feature: dict, oid_field: str) -> str:
    attrs = feature.get("attributes", feature)
    if attrs.get(oid_field) is not None:
        return f"oid:{attrs[oid_field]}"
    return "hash:" + hashlib.md5(json.dumps(attrs, sort_keys=True, default=str).encode()).hexdigest()


def max_date_ms(features: list, date_field: str):
    best = None
    for f in features:
        v = (f.get("attributes", f)).get(date_field)
        if isinstance(v, (int, float)) and v and (best is None or v > best):
            best = int(v)
    return best


def ms_to_date_literal(ms: int) -> str:
    """Epoch ms → SQL date literal for ArcGIS WHERE clauses."""
    from datetime import timezone
    d = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
    return d.isoformat()


def fetch_all_features(client: httpx.Client, base_url: str, where_clause: str = "1=1") -> list[dict]:
    """
    Fetch all features from an ArcGIS Feature Service with pagination.

    Args:
        client: httpx Client instance
        base_url: Feature service layer URL
        where_clause: SQL WHERE clause for filtering

    Returns:
        List of feature dictionaries
    """
    all_features = []
    offset = 0
    batch_size = 2000

    while True:
        params = {
            "where": where_clause,
            "outFields": "*",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }

        try:
            resp = client.get(f"{base_url}/query", params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error during paged query: {e}") from e

        data = resp.json()
        if "error" in data:
            msg = data["error"].get("message", str(data["error"]))
            # Loud failure: a bad WHERE clause must not masquerade as "no new records"
            raise RuntimeError(f"ArcGIS API error: {msg} (where: {where_clause!r})")

        features = data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        print(f"    Fetched {len(all_features):,} records...", end="\r")

        # exceededTransferLimit is authoritative: the service may cap pages
        # below our batch_size (e.g. maxRecordCount=1000)
        if not data.get("exceededTransferLimit"):
            break
        offset += len(features)

    print(f"    Fetched {len(all_features):,} total records    ")
    return all_features


def save_features(features: list[dict], output_prefix: str) -> tuple[Path, Path]:
    """
    Save features to JSON and CSV files.

    Args:
        features: List of feature dictionaries
        output_prefix: Filename prefix for output files

    Returns:
        Tuple of (json_path, csv_path)
    """
    json_path = DATA_DIR / f"{output_prefix}.json"
    csv_path = DATA_DIR / f"{output_prefix}.csv"

    # Save JSON
    with open(json_path, "w") as f:
        json.dump({"features": features, "fetched_at": datetime.now().isoformat()}, f)

    # Save CSV
    if features:
        attrs = [f.get("attributes", f) for f in features]
        fieldnames = list(attrs[0].keys())

        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(attrs)

    return json_path, csv_path


def get_layer_info(client: httpx.Client, url: str) -> dict:
    """Get feature layer metadata."""
    try:
        resp = client.get(f"{url}?f=json")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    Could not get layer info: {e}")
        return {}


def refresh_source(client: httpx.Client, source_key: str, full: bool = False) -> bool:
    """
    Refresh data from a single source.

    Incremental: if the previous run stored a max date and a snapshot exists,
    only features newer than that are fetched and merged by OID. A full
    snapshot is taken when --full is passed or the last full fetch is older
    than FULL_REFRESH_DAYS.

    Args:
        client: httpx Client instance
        source_key: Key from SOURCES dict
        full: Force a full snapshot

    Returns:
        True if successful, False otherwise
    """
    if source_key not in SOURCES:
        print(f"Unknown source: {source_key}")
        return False

    source = SOURCES[source_key]
    state = load_incremental_state()
    src_state = state.get(source_key, {})
    json_path = DATA_DIR / f"{source['output_prefix']}.json"

    print(f"\n{'='*60}")
    print(f"Refreshing: {source['name']}")
    print(f"{'='*60}")

    # Get layer info
    info = get_layer_info(client, source["url"])
    if info:
        print(f"  Layer: {info.get('name', 'Unknown')}")
        fields = [f.get("name") for f in info.get("fields", [])]
        print(f"  Fields: {len(fields)}")

    # Decide incremental vs full
    can_incremental = (
        not full
        and src_state.get("max_date_ms")
        and json_path.exists()
        and source.get("date_field")
    )
    if can_incremental and src_state.get("last_full"):
        try:
            last_full = datetime.fromisoformat(src_state["last_full"])
            if (datetime.now() - last_full).days >= FULL_REFRESH_DAYS:
                print(f"  Last full snapshot > {FULL_REFRESH_DAYS}d ago — taking full refresh")
                can_incremental = False
        except ValueError:
            pass

    existing = []
    where = source["filter"]
    if can_incremental:
        date_lit = ms_to_date_literal(int(src_state["max_date_ms"]))
        where = f"({source['filter']}) AND ({source['date_field']} > DATE '{date_lit}')"
        try:
            existing = json.loads(json_path.read_text()).get("features", [])
        except (OSError, json.JSONDecodeError):
            existing = []
            can_incremental = False
            where = source["filter"]

    # Fetch features
    mode = "incremental" if can_incremental else "full"
    print(f"  Filter: {where}")
    print(f"  Mode: {mode}")
    features = fetch_all_features(client, source["url"], where)

    if can_incremental and not features:
        # No new records — snapshot is already current
        print("  No new records (snapshot current)")
        state[source_key] = {
            **src_state,
            "last_fetch": datetime.now().isoformat(),
            "count": len(existing),
        }
        save_incremental_state(state)
        return True

    if not features:
        print("  No features retrieved")
        return False

    if can_incremental:
        merged = {feature_key(f, source["oid_field"]): f for f in existing}
        added = 0
        for f in features:
            key = feature_key(f, source["oid_field"])
            if key not in merged:
                added += 1
            merged[key] = f
        features = list(merged.values())
        print(f"  Merged: +{added} new, {len(features)} total in snapshot")

    # Save
    json_path, csv_path = save_features(features, source["output_prefix"])
    print(f"  Saved: {json_path.name} ({json_path.stat().st_size / 1024:.1f} KB)")
    print(f"  Saved: {csv_path.name} ({csv_path.stat().st_size / 1024:.1f} KB)")

    # Update incremental state
    state[source_key] = {
        "last_fetch": datetime.now().isoformat(),
        "count": len(features),
        "max_date_ms": max_date_ms(features, source.get("date_field", "")),
        "last_full": src_state.get("last_full") if can_incremental else datetime.now().isoformat(),
    }
    save_incremental_state(state)

    # Summary stats
    attrs = [f.get("attributes", f) for f in features]

    # Try to count unique species
    species_fields = ["Species", "Bird_Species", "species"]
    for sf in species_fields:
        if sf in attrs[0]:
            unique_species = len(set(a.get(sf) for a in attrs if a.get(sf)))
            print(f"  Unique species: {unique_species}")
            break

    return True


def main():
    parser = argparse.ArgumentParser(description="Refresh ArcGIS avian influenza data")
    parser.add_argument(
        "--source", "-s",
        choices=list(SOURCES.keys()) + ["all"],
        default="all",
        help="Data source to refresh (default: all)"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Force full snapshot (skip incremental date filter)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ARCGIS DATA REFRESH")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Output: {DATA_DIR}")
    print("=" * 60)

    sources_to_refresh = list(SOURCES.keys()) if args.source == "all" else [args.source]

    results = {}
    with httpx.Client(timeout=120.0) as client:
        for source_key in sources_to_refresh:
            try:
                results[source_key] = refresh_source(client, source_key, full=args.full)
            except Exception as e:
                print(f"  Error: {e}")
                results[source_key] = False

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    for source, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {SOURCES[source]['name']}: {status}")

    print(f"\nCompleted: {datetime.now().isoformat()}")

    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
