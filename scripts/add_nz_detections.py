#!/usr/bin/env python3
"""
Add New Zealand H5 HPAI detection records to the detections database.

Adds the 3 confirmed NZ cases to:
- data/detections_merged.parquet
- web/public/data/detections.parquet
- GeoJSON files for mapping

Usage:
    python scripts/add_nz_detections.py
"""

import json
from pathlib import Path
from datetime import datetime
import polars as pl

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"

# NZ H5 HPAI confirmed cases with coordinates
# Cape Palliser coordinates: -41.6167, 175.2833
# Wairarapa region center: -41.2, 175.5
# Note: record_id will be assigned dynamically based on max existing ID
NZ_DETECTIONS = [
    {
        "record_id": None,  # Will be assigned dynamically
        "species_raw": "Brown skua",
        "scientific_name": "Stercorarius lonnbergi",
        "taxon_id": 54054,
        "date_detected": "2026-07-15",
        "country": "NZL",
        "state": None,
        "county": None,
        "strain": "H5",
        "sampling_method_raw": "dead bird",
        "sampling_type": "mortality",
        "source": "NZ-DOC",
        "source_file": "nz_hpai_cases.json",
        "detection_count": 1,
        "latitude": -41.5,  # Approximate - location not disclosed
        "longitude": 174.5,
    },
    {
        "record_id": None,  # Will be assigned dynamically
        "species_raw": "Swamp harrier",
        "scientific_name": "Circus approximans",
        "taxon_id": 387821,
        "date_detected": "2026-07-17",
        "country": "NZL",
        "state": "Wairarapa",
        "county": None,
        "strain": "H5",
        "sampling_method_raw": "dead bird",
        "sampling_type": "mortality",
        "source": "NZ-DOC",
        "source_file": "nz_hpai_cases.json",
        "detection_count": 1,
        "latitude": -41.2,  # Wairarapa region
        "longitude": 175.5,
    },
    {
        "record_id": None,  # Will be assigned dynamically
        "species_raw": "Northern giant petrel",
        "scientific_name": "Macronectes halli",
        "taxon_id": 79630,
        "date_detected": "2026-08-21",
        "country": "NZL",
        "state": "Wairarapa",
        "county": "Cape Palliser",
        "strain": "H5",
        "sampling_method_raw": "dead bird found on beach",
        "sampling_type": "mortality",
        "source": "NZ-MPI",
        "source_file": "nz_hpai_cases.json",
        "detection_count": 1,
        "latitude": -41.6167,  # Cape Palliser
        "longitude": 175.2833,
    },
]


def add_to_parquet(parquet_path: Path, new_records: list[dict]) -> int:
    """Add new records to a parquet file."""
    if not parquet_path.exists():
        print(f"  WARNING: {parquet_path} not found")
        return 0

    # Load existing data
    df = pl.read_parquet(parquet_path)
    print(f"  Loaded {len(df):,} existing records from {parquet_path.name}")

    # Check for existing NZ records by matching on scientific_name + date
    existing_nz = df.filter(pl.col("country") == "NZL")
    if len(existing_nz) > 0:
        print(f"  Found {len(existing_nz)} existing NZ records")
        # Check by species + date combo
        existing_combos = set()
        for row in existing_nz.iter_rows(named=True):
            combo = (row.get("scientific_name"), row.get("date_detected"))
            existing_combos.add(combo)

        new_records = [
            r for r in new_records
            if (r.get("scientific_name"), r.get("date_detected")) not in existing_combos
        ]
        if not new_records:
            print("  All NZ records already exist - skipping")
            return 0

    # Get max record_id and assign new IDs
    max_id = df["record_id"].max()
    for i, record in enumerate(new_records):
        record["record_id"] = max_id + i + 1

    # Create DataFrame
    new_df = pl.DataFrame(new_records)

    # Ensure columns match schema
    schema = df.schema
    for col, dtype in schema.items():
        if col not in new_df.columns:
            new_df = new_df.with_columns(pl.lit(None).cast(dtype).alias(col))
        else:
            # Cast to match type
            new_df = new_df.with_columns(pl.col(col).cast(dtype))

    # Select only columns that exist in original, in order
    new_df = new_df.select(df.columns)

    # Concatenate
    combined = pl.concat([df, new_df])

    # Save
    combined.write_parquet(parquet_path)
    print(f"  Added {len(new_records)} NZ records -> {len(combined):,} total")

    return len(new_records)


def update_geojson(geojson_path: Path, new_records: list[dict]) -> int:
    """Add new records to a GeoJSON file."""
    if not geojson_path.exists():
        print(f"  WARNING: {geojson_path} not found")
        return 0

    with open(geojson_path) as f:
        geojson = json.load(f)

    features = geojson.get("features", [])
    print(f"  Loaded {len(features)} existing features from {geojson_path.name}")

    # Check for existing NZ features by species + date
    existing_combos = set()
    for feat in features:
        props = feat.get("properties", {})
        if props.get("country") == "NZL":
            combo = (props.get("species"), props.get("date"))
            existing_combos.add(combo)

    # Add new features
    added = 0
    for record in new_records:
        combo = (record.get("scientific_name"), record.get("date_detected"))
        if combo in existing_combos:
            continue

        if record.get("latitude") and record.get("longitude"):
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [record["longitude"], record["latitude"]]
                },
                "properties": {
                    "species": record["scientific_name"],
                    "common_name": record["species_raw"],
                    "date": record["date_detected"],
                    "country": record["country"],
                    "state": record.get("state"),
                    "strain": record["strain"],
                    "source": record["source"],
                }
            }
            features.append(feature)
            added += 1

    if added > 0:
        geojson["features"] = features
        with open(geojson_path, "w") as f:
            json.dump(geojson, f)
        print(f"  Added {added} NZ features -> {len(features)} total")

    return added


def main():
    print("=" * 60)
    print("ADD NZ DETECTIONS TO DATABASE")
    print("=" * 60)
    print(f"\nAdding {len(NZ_DETECTIONS)} NZ detection records...")

    # Update parquet files
    print("\n--- Parquet Files ---")
    parquet_files = [
        DATA_DIR / "detections_merged.parquet",
        WEB_DATA_DIR / "detections.parquet",
    ]

    for pq_file in parquet_files:
        add_to_parquet(pq_file, NZ_DETECTIONS)

    # Update GeoJSON files
    print("\n--- GeoJSON Files ---")
    geojson_files = [
        DATA_DIR / "geojson" / "detections.geojson",
        WEB_DATA_DIR / "geojson" / "detections.geojson",
    ]

    for gj_file in geojson_files:
        update_geojson(gj_file, NZ_DETECTIONS)

    # Copy to dist
    print("\n--- Copying to dist ---")
    dist_dir = ROOST_DIR / "web" / "dist" / "data"
    if dist_dir.exists():
        import shutil

        # Copy parquet
        src = WEB_DATA_DIR / "detections.parquet"
        dst = dist_dir / "detections.parquet"
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied {src.name} to dist")

        # Copy geojson
        src_gj = WEB_DATA_DIR / "geojson" / "detections.geojson"
        dst_gj = dist_dir / "geojson" / "detections.geojson"
        if src_gj.exists():
            shutil.copy2(src_gj, dst_gj)
            print(f"  Copied detections.geojson to dist")

    print("\n" + "=" * 60)
    print("Done! NZ detections added.")
    print("\nVerification:")
    df = pl.read_parquet(WEB_DATA_DIR / "detections.parquet")
    nz = df.filter(pl.col("country") == "NZL")
    print(f"  NZ records in web data: {len(nz)}")
    if len(nz) > 0:
        print(f"  Species: {nz['scientific_name'].unique().to_list()}")


if __name__ == "__main__":
    main()
