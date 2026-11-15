#!/usr/bin/env python3
"""
Unified detection addition script.

This is the SINGLE entry point for adding new detection records.
It updates ALL data stores to keep them in sync:
- data/detections_merged.parquet (source of truth)
- web/public/data/detections.parquet
- data/manual/species_overlay.json (curated overlay; index regenerates via export_web_data.py)
- web/public/data/geojson/detections.geojson
- Copies to web/dist/data/ for production

Usage:
    # Add from JSON file
    python scripts/add_detections.py data/sources/nz_hpai_cases.json

    # Add with inline data
    python scripts/add_detections.py --inline '{"species": "Anas platyrhynchos", ...}'

    # Rebuild all derived data from parquet
    python scripts/add_detections.py --rebuild
"""

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
import polars as pl

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"
DIST_DIR = ROOST_DIR / "web" / "dist" / "data"


def load_detections() -> pl.DataFrame:
    """Load the master detections file."""
    return pl.read_parquet(DATA_DIR / "detections_merged.parquet")


def save_detections(df: pl.DataFrame):
    """Save to all detection parquet locations."""
    df.write_parquet(DATA_DIR / "detections_merged.parquet")
    df.write_parquet(WEB_DATA_DIR / "detections.parquet")
    if DIST_DIR.exists():
        df.write_parquet(DIST_DIR / "detections.parquet")
    print(f"  Saved {len(df):,} detections to parquet files")


# NOTE (DATA_MATURATION Phase 3): species_index.json writers were removed
# from this script. scripts/export_web_data.py:generate_search_index is
# the index's ONLY writer (profiles parquet + detected_mammals.json +
# data/manual/species_overlay.json). Run it after adding detections.


def rebuild_geojson(df: pl.DataFrame):
    """Rebuild detection GeoJSON from parquet."""
    # Filter to records with coordinates
    geo_df = df.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )

    features = []
    for row in geo_df.iter_rows(named=True):
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]]
            },
            "properties": {
                "species": row.get("scientific_name"),
                "common_name": row.get("species_raw"),
                "date": row.get("date_detected"),
                "country": row.get("country"),
                "state": row.get("state"),
                "strain": row.get("strain"),
                "source": row.get("source"),
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # Save
    gj_dir = WEB_DATA_DIR / "geojson"
    gj_dir.mkdir(exist_ok=True)
    with open(gj_dir / "detections.geojson", "w") as f:
        json.dump(geojson, f)

    if DIST_DIR.exists():
        dist_gj_dir = DIST_DIR / "geojson"
        dist_gj_dir.mkdir(exist_ok=True)
        with open(dist_gj_dir / "detections.geojson", "w") as f:
            json.dump(geojson, f)

    print(f"  Rebuilt detections.geojson ({len(features)} features)")


def add_records(df: pl.DataFrame, new_records: list[dict]) -> pl.DataFrame:
    """Add new records to the detections DataFrame."""
    if not new_records:
        return df

    # Assign record IDs
    max_id = df["record_id"].max()
    for i, record in enumerate(new_records):
        if record.get("record_id") is None:
            record["record_id"] = max_id + i + 1

    # Create new DataFrame and align schema
    new_df = pl.DataFrame(new_records)
    schema = df.schema

    for col, dtype in schema.items():
        if col not in new_df.columns:
            new_df = new_df.with_columns(pl.lit(None).cast(dtype).alias(col))
        else:
            new_df = new_df.with_columns(pl.col(col).cast(dtype))

    new_df = new_df.select(df.columns)

    return pl.concat([df, new_df])


def parse_source_file(source_file: Path) -> list[dict]:
    """Parse a source JSON file into detection records."""
    with open(source_file) as f:
        data = json.load(f)

    records = []

    # Handle NZ format (confirmed_cases list)
    if "confirmed_cases" in data:
        for case in data["confirmed_cases"]:
            record = {
                "record_id": None,
                "species_raw": case["species"]["common_name"],
                "scientific_name": case["species"]["scientific_name"],
                "taxon_id": case["species"].get("taxon_id"),
                "date_detected": case["date_detected"],
                "country": "NZL",
                "state": case.get("location", {}).get("region"),
                "county": case.get("location", {}).get("description"),
                "strain": "H5",
                "sampling_type": "mortality",
                "source": f"NZ-{case.get('source_id', 'DOC').split('_')[0].upper()}",
                "source_file": source_file.name,
                "detection_count": 1,
            }
            records.append(record)

    return records


def main():
    parser = argparse.ArgumentParser(description="Add detection records")
    parser.add_argument("source_file", nargs="?", help="JSON source file")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild all derived data")
    parser.add_argument("--inline", help="Inline JSON record(s)")
    args = parser.parse_args()

    print("=" * 60)
    print("UNIFIED DETECTION UPDATE")
    print("=" * 60)

    # Load current data
    df = load_detections()
    print(f"\nLoaded {len(df):,} existing detections")

    if args.rebuild:
        print("\n--- Rebuilding all derived data ---")
        save_detections(df)
        rebuild_geojson(df)
        print("\nDone! Regenerate the species index with:")
        print("  pixi run python scripts/export_web_data.py")
        return

    # Add new records
    new_records = []

    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.is_absolute():
            source_path = ROOST_DIR / source_path
        print(f"\nParsing {source_path.name}...")
        new_records = parse_source_file(source_path)

    if args.inline:
        inline_data = json.loads(args.inline)
        if isinstance(inline_data, dict):
            new_records.append(inline_data)
        else:
            new_records.extend(inline_data)

    if not new_records:
        print("No new records to add")
        return

    # Check for duplicates
    existing_combos = set()
    for row in df.iter_rows(named=True):
        combo = (row.get("scientific_name"), row.get("date_detected"), row.get("country"))
        existing_combos.add(combo)

    new_records = [
        r for r in new_records
        if (r.get("scientific_name"), r.get("date_detected"), r.get("country")) not in existing_combos
    ]

    if not new_records:
        print("All records already exist - nothing to add")
        return

    print(f"Adding {len(new_records)} new records...")

    # Add records
    df = add_records(df, new_records)

    # Save everything
    print("\n--- Updating all data stores ---")
    save_detections(df)
    rebuild_geojson(df)
    print("Regenerate the species index with: pixi run python scripts/export_web_data.py")

    print("\n" + "=" * 60)
    print("Done! All data stores updated.")


if __name__ == "__main__":
    main()
