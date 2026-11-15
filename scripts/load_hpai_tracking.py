#!/usr/bin/env python3
"""
Load HPAI-related tracking and occurrence data.

This script consolidates data specifically for infected or HPAI-associated birds:
1. ACAP HPAI Database - Confirmed HPAI in seabirds (albatrosses, petrels) with coordinates
2. GPS telemetry mortality data - Birds tracked until death
3. Detection data with coordinates - HPAI-positive wild birds with location info

Output:
- Parquet files for spatial analysis of HPAI occurrences
- Summary statistics by species and region
"""

import polars as pl
from pathlib import Path
import json
from datetime import datetime

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
EXTERNAL_DIR = DATA_DIR / "raw" / "external"
OUTPUT_DIR = DATA_DIR / "hpai_tracking"


def load_acap_hpai() -> pl.DataFrame:
    """
    Load ACAP HPAI database for seabirds (albatrosses and petrels).

    Contains confirmed and suspected HPAI H5N1 cases in Procellariiformes
    with coordinates, dates, and diagnostic details.
    """
    file_path = EXTERNAL_DIR / "zenodo-acap-hpai" / "events.tsv"
    if not file_path.exists():
        print(f"  ACAP HPAI data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path, separator="\t", encoding="utf8-lossy")

    # Standardize columns
    df = df.with_columns([
        pl.col("Latitude").cast(pl.Float64).alias("latitude"),
        pl.col("Longitude").cast(pl.Float64).alias("longitude"),
        pl.col("Date").str.to_date("%Y-%m-%d").alias("date"),
        pl.col("Species").alias("scientific_name"),
        pl.col("EnglishName").alias("common_name"),
        pl.col("Subtype").alias("subtype"),
        pl.col("Category").alias("confirmation_status"),
        pl.col("Individuals").str.replace_all(",", "").cast(pl.Int32).alias("n_individuals"),
        pl.lit("acap_hpai").alias("source"),
    ])

    # Filter to records with coordinates
    df = df.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )

    print(f"  Loaded {len(df)} ACAP HPAI records")
    print(f"  Species: {df['scientific_name'].n_unique()}")
    print(f"  Confirmed: {len(df.filter(pl.col('confirmation_status').str.starts_with('C')))}")
    print(f"  Suspected: {len(df.filter(pl.col('confirmation_status').str.starts_with('S')))}")

    return df


def load_gps_mortality() -> pl.DataFrame:
    """
    Extract mortality events from GPS telemetry data.

    These are birds that were tracked until death - useful for understanding
    mortality locations and timing relative to HPAI outbreaks.
    """
    file_path = DATA_DIR / "gps_telemetry" / "hourly_life_history_gps.parquet"
    if not file_path.exists():
        print(f"  GPS telemetry data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_parquet(file_path)

    # Filter to "Dead" state records
    dead = df.filter(pl.col("life_history_state") == "Dead")

    if len(dead) == 0:
        print("  No mortality records found in GPS data")
        return pl.DataFrame()

    # Get last known location for each individual (approximate death location)
    # and first "Dead" timestamp
    mortality_events = dead.group_by("individual_id").agg([
        pl.col("latitude").last().alias("latitude"),
        pl.col("longitude").last().alias("longitude"),
        pl.col("timestamp_str").first().alias("first_dead_timestamp"),
        pl.col("timestamp_str").last().alias("last_timestamp"),
        pl.len().alias("n_dead_locations"),
    ])

    mortality_events = mortality_events.with_columns([
        pl.lit("gps_mortality").alias("source"),
        pl.lit("waterfowl").alias("taxon_group"),
    ])

    print(f"  Found {len(mortality_events)} mortality events from GPS tracking")
    print(f"  Total dead-state locations: {dead['individual_id'].len()}")

    return mortality_events


def load_detection_coordinates() -> pl.DataFrame:
    """
    Load HPAI detection data that includes coordinates.

    Sources with coordinates:
    - Ireland DAFM: ~16K records with lat/long
    - Italy ISS: ~240 records with lat/long
    - SDM HPAI (Europe): ~11K records with converted WGS84 coords
    - Canada CWHC: ~750 records with lat/long
    """
    detections_path = DATA_DIR / "detections_merged.parquet"
    if not detections_path.exists():
        print(f"  Merged detections not found: {detections_path}")
        return pl.DataFrame()

    df = pl.read_parquet(detections_path)

    # Filter to records with coordinates
    with_coords = df.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null() &
        (pl.col("latitude") != 0) &
        (pl.col("longitude") != 0)
    )

    print(f"  Found {len(with_coords)} detection records with coordinates")
    print(f"  Species: {with_coords['scientific_name'].n_unique()}")
    print(f"  Sources: {with_coords['source'].unique().to_list()}")

    return with_coords


def summarize_hpai_by_species(df: pl.DataFrame) -> pl.DataFrame:
    """Create summary statistics by species."""
    if "scientific_name" not in df.columns:
        return pl.DataFrame()

    summary = df.group_by("scientific_name").agg([
        pl.len().alias("n_records"),
        pl.col("latitude").min().alias("lat_min"),
        pl.col("latitude").max().alias("lat_max"),
        pl.col("longitude").min().alias("lon_min"),
        pl.col("longitude").max().alias("lon_max"),
    ]).sort("n_records", descending=True)

    return summary


def main():
    print("=" * 60)
    print("LOADING HPAI TRACKING AND OCCURRENCE DATA")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {}

    # Load ACAP HPAI database
    print("\n1. Loading ACAP HPAI Database (Seabirds)...")
    acap = load_acap_hpai()
    if len(acap) > 0:
        datasets["acap_hpai"] = acap
        output_path = OUTPUT_DIR / "acap_hpai_events.parquet"
        acap.write_parquet(output_path)
        print(f"   Saved: {output_path}")

    # Load GPS mortality data
    print("\n2. Loading GPS Telemetry Mortality Events...")
    mortality = load_gps_mortality()
    if len(mortality) > 0:
        datasets["gps_mortality"] = mortality
        output_path = OUTPUT_DIR / "gps_mortality_events.parquet"
        mortality.write_parquet(output_path)
        print(f"   Saved: {output_path}")

    # Load detection data with coordinates
    print("\n3. Loading Detection Data with Coordinates...")
    detections = load_detection_coordinates()
    if len(detections) > 0:
        datasets["detections_with_coords"] = detections
        output_path = OUTPUT_DIR / "detections_with_coordinates.parquet"
        detections.write_parquet(output_path)
        print(f"   Saved: {output_path}")

    # Create metadata
    metadata = {
        "generated": datetime.now().isoformat(),
        "datasets": {}
    }

    for name, df in datasets.items():
        metadata["datasets"][name] = {
            "records": len(df),
            "species": df["scientific_name"].n_unique() if "scientific_name" in df.columns else 0,
        }

    # Calculate totals
    total_records = sum(len(df) for df in datasets.values())
    metadata["total_georeferenced_hpai_records"] = total_records

    metadata_path = OUTPUT_DIR / "hpai_tracking_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"\nSaved: {metadata_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("HPAI TRACKING DATA SUMMARY")
    print("=" * 60)
    print(f"\nTotal georeferenced HPAI records: {total_records:,}")

    for name, df in datasets.items():
        print(f"\n{name}:")
        print(f"  Records: {len(df):,}")
        if "scientific_name" in df.columns:
            print(f"  Species: {df['scientific_name'].n_unique()}")

    # Species summary for detections
    if "detections_with_coords" in datasets:
        print("\nTop species in georeferenced detections:")
        summary = summarize_hpai_by_species(datasets["detections_with_coords"])
        for row in summary.head(10).iter_rows(named=True):
            print(f"  {row['scientific_name']}: {row['n_records']:,} records")


if __name__ == "__main__":
    main()
