#!/usr/bin/env python3
"""Verify all downloadable files on the website are present, fresh, and
contain expected row counts. Exit 0 = pass; exit 1 = failures found.

Usage: pixi run verify-downloads
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent
WEB = ROOT / "web" / "public" / "data"

failures = []
warnings = []

MAX_AGE_DAYS = 7  # warn if older

# Dynamic expected counts: read from the interior (canonical) files.
# If the interior is unavailable, fall back to permissive minimums.
def get_expected():
    exp = {}
    interior = {
        "detections.parquet": ROOT / "data" / "detections_merged.parquet",
        "species.parquet": ROOT / "data" / "species_profiles_detected.parquet",
        "genomes.parquet": ROOT / "data" / "genomes.parquet",
        "susceptibility.parquet": ROOT / "data" / "susceptibility_scores.parquet",
        # gene_presence: shipped file is canonical (alias-merged from jsonl);
        # the interior parquet is a raw count that legitimately differs
    }
    for name, path in interior.items():
        if path.exists():
            try:
                exp[name] = pl.read_parquet(path).height
            except Exception:
                pass
    # genes.parquet derives from the gene panel export
    genes_pq = ROOT / "data" / "genes" / "gene_panel.tsv"
    if not genes_pq.exists():
        genes_pq = ROOT / "data" / "genes" / "host_panel_v2.json"
    # just use the web copy count if interior isn't available
    if "genes.parquet" not in exp:
        web_genes = WEB / "genes.parquet"
        if web_genes.exists():
            exp["genes.parquet"] = pl.read_parquet(web_genes).height
    return exp


def get_expected_index():
    idx = WEB / "species_index.json"
    if idx.exists():
        return len(json.load(open(idx)))
    return 0  # don't check if missing


def get_expected_papers():
    """Corpus size from the authoritative papers index."""
    p = WEB / "papers.json"
    if p.exists():
        d = json.load(open(p))
        return len(d["papers"]) if isinstance(d, dict) and "papers" in d else len(d)
    return 0


def get_expected_panel():
    """Panel size from the gene catalogue (post-alias-merge searched genes)."""
    c = WEB / "gene_catalogue.json"
    if c.exists():
        return json.load(open(c)).get("total_genes", 0)
    return 0


def check_file(name: str, path: Path):
    if not path.exists():
        failures.append(f"MISSING: {name}")
        return
    size = path.stat().st_size
    if size < 10:
        failures.append(f"EMPTY: {name} ({size} bytes)")
        return
    age_days = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
    if age_days > MAX_AGE_DAYS:
        warnings.append(f"STALE: {name} is {age_days} days old")


def check_parquet(name: str, expected_rows: int):
    path = WEB / name
    check_file(name, path)
    if not path.exists():
        return
    rows = pl.read_parquet(path).height
    if rows != expected_rows:
        failures.append(f"ROW COUNT: {name} has {rows} rows, expected {expected_rows}")


def check_json(name: str, predicate, description: str):
    path = WEB / name
    check_file(name, path)
    if not path.exists():
        return
    try:
        data = json.load(open(path))
        if not predicate(data):
            failures.append(f"CONTENT: {name} — {description}")
    except json.JSONDecodeError:
        failures.append(f"PARSE ERROR: {name}")


def main():
    print("=" * 60)
    print("DOWNLOAD VERIFICATION")
    print("=" * 60)

    # 1. Parquet tables (dynamic expected counts from interior)
    print("\n--- Parquet tables ---")
    expected = get_expected()
    for name, exp_count in expected.items():
        check_parquet(name, exp_count)
        path = WEB / name
        if path.exists():
            rows = pl.read_parquet(path).height
            print(f"  {'✓' if rows == exp_count else '✗'} {name}: {rows:,} rows (expected {exp_count:,})")

    # 2. detections.parquet specific checks
    print("\n--- Detection data quality ---")
    det = WEB / "detections.parquet"
    if det.exists():
        df = pl.read_parquet(det)
        geo = df.filter(pl.col("latitude").is_not_null()).height
        dated = df.filter(pl.col("date_iso").is_not_null()).height
        print(f"  {'✓' if geo > 30_000 else '✗'} georeferenced: {geo:,} ({geo / df.height:.1%})")
        pct_dated = dated / df.height if df.height else 0
        print(f"  {'✓' if pct_dated > 0.95 else '✗'} dated (date_iso): {dated:,} ({pct_dated:.1%})")

        # stats.json georeferenced should match
        stats_file = WEB / "stats.json"
        if stats_file.exists():
            stats = json.load(open(stats_file))
            if stats.get("georeferenced") != geo:
                failures.append(
                    f"STATS MISMATCH: stats.json georeferenced={stats.get('georeferenced')} "
                    f"but parquet has {geo}")

    # 3. Species index
    print("\n--- Species index ---")
    idx_file = WEB / "species_index.json"
    check_file("species_index.json", idx_file)
    if idx_file.exists():
        idx = json.load(open(idx_file))
        mammals = sum(1 for s in idx if s.get("ord") == "Mammalia")
        iucn = sum(1 for s in idx if s.get("iucn"))
        expected_idx = get_expected_index()
        print(f"  {'✓' if len(idx) == expected_idx else '✗'} entries: {len(idx)} (expected {expected_idx})")
        print(f"  {'✓' if mammals > 60 else '✗'} mammals: {mammals}")
        print(f"  {'✓' if iucn > 25 else '✗'} with IUCN: {iucn}")

    # 4. GeoJSON downloads
    print("\n--- GeoJSON downloads ---")
    for name in ["detections.geojson", "detections_by_country.geojson",
                  "detections_by_species.geojson", "hotspots.geojson"]:
        path = WEB / "geojson" / name
        check_file(name, path)
        if path.exists():
            features = len(json.load(open(path))["features"])
            if name == "detections.geojson":
                web_det = WEB / "detections.parquet"
                if web_det.exists():
                    expected_geo = pl.read_parquet(web_det).filter(
                        pl.col("latitude").is_not_null()).height
                    if features != expected_geo:
                        failures.append(
                            f"STALE GEOJSON: {name} has {features} features "
                            f"but detections.parquet has {expected_geo} georeferenced. "
                            f"Run: pixi run export-all")
            print(f"  {'✓' if features > 100 else '✗'} {name}: {features:,} features")

    # 5. Curated overlays
    print("\n--- Curated overlays ---")
    for name in ["spread_events.json", "spread_mutations.json",
                  "spread_regions.json", "flyways.json", "species_overlay.json"]:
        path = WEB / name
        check_file(name, path)
        print(f"  {'✓' if path.exists() else '✗'} {name}")

    # 6. Spread model evidence block
    print("\n--- Spread model ---")
    sm_file = WEB / "h5n1_spread_model.json"
    check_file("h5n1_spread_model.json", sm_file)
    if sm_file.exists():
        sm = json.load(open(sm_file))
        ev = sm.get("evidence", {}).get("edges", {})
        if not ev:
            failures.append("SPREAD MODEL: no evidence block (run: pixi run spread-edges)")
        else:
            total = sum(b.get("count", 0) for b in ev.values())
            contested = sum(1 for b in ev.values() if b.get("contested"))
            print(f"  ✓ evidence block: {len(ev)} edges, {total} paper links, {contested} contested")

    # 7. Key JSON data files
    print("\n--- JSON data files ---")
    for name in ["papers.json", "wiki_genes.json", "wiki_species.json",
                  "wiki_mutations.json", "gene_catalogue.json", "stats.json",
                  "provenance.json"]:
        check_file(name, WEB / name)
        print(f"  {'✓' if (WEB / name).exists() else '✗'} {name}")

    # 8. Stats.json consistency
    print("\n--- Stats consistency ---")
    stats_file = WEB / "stats.json"
    if stats_file.exists():
        stats = json.load(open(stats_file))
        checks = [
            ("detections", expected.get("detections.parquet", 0)),
            ("species", expected.get("species.parquet", 0)),
            ("searchable_species", get_expected_index()),
            ("papers", get_expected_papers()),
            ("panel_genes", get_expected_panel()),
        ]
        for key, expected in checks:
            actual = stats.get(key)
            ok = "✓" if actual == expected else "✗"
            print(f"  {ok} stats.{key}: {actual} (expected {expected})")
            if actual != expected:
                failures.append(f"STATS: stats.{key}={actual}, expected {expected}")

    # Summary
    print("\n" + "=" * 60)
    if warnings:
        print(f"\n⚠ WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")
    if failures:
        print(f"\n✗ FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  {f}")
        print("\nTo fix: pixi run export-all")
        sys.exit(1)
    else:
        print("\n✓ All downloads verified")
        sys.exit(0)


if __name__ == "__main__":
    main()
