#!/usr/bin/env python3
"""
Load and process GPS telemetry data for avian species.

This script consolidates GPS tracking data from multiple sources:
- USGS Waterfowl GPS (2019-2020): 2.8M locations, 9 species
- USGS Hourly GPS with Life History: 225K locations, 5 species

Output:
- GPS telemetry parquet files for spatial analysis
- Species occurrence summaries by location
"""

import polars as pl
from pathlib import Path
import json
from datetime import datetime

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
EXTERNAL_DIR = DATA_DIR / "raw" / "external"
GPS_DIR = EXTERNAL_DIR / "usgs-gps-tracking"
OUTPUT_DIR = DATA_DIR / "gps_telemetry"


def load_waterfowl_gps() -> pl.DataFrame:
    """
    Load USGS GPS-marked waterfowl locations (2019-2020).

    Contains hourly GPS fixes from 412 individuals across 9 species
    in Western North America.
    """
    file_path = GPS_DIR / "waterfowl_gps_covid_2019_2020.csv"
    if not file_path.exists():
        print(f"  Waterfowl GPS data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Standardize columns
    df = df.with_columns([
        pl.col("location_lat").alias("latitude"),
        pl.col("location_long").alias("longitude"),
        pl.col("timestamp").str.to_datetime(format="%Y-%m-%dT%H:%M:%SZ", time_zone="UTC").alias("timestamp_dt"),
        pl.col("individual_taxon_canonical_name").alias("scientific_name"),
        pl.col("individual_local_identifier").alias("individual_id"),
        pl.lit("usgs_waterfowl_gps").alias("source"),
    ])

    print(f"  Loaded {len(df):,} GPS locations")
    print(f"  Species: {df['scientific_name'].n_unique()}")
    print(f"  Individuals: {df['individual_id'].n_unique()}")

    return df


def load_hourly_gps_life_history() -> pl.DataFrame:
    """
    Load USGS hourly GPS with life history annotations (2015-2020).

    Contains hourly GPS fixes with behavioral state labels:
    Brooding, Dead, Local Movements, Migration, Molting,
    Molt-Like, Nesting, Regional Relocation
    """
    file_path = GPS_DIR / "waterfowl_hourly_gps_2015_2020.csv"
    if not file_path.exists():
        print(f"  Hourly GPS data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Standardize columns
    df = df.with_columns([
        pl.col("Location-Lat").alias("latitude"),
        pl.col("Location-Long").alias("longitude"),
        pl.col("Timestamp").alias("timestamp_str"),  # Keep as string for now
        pl.col("Status").alias("life_history_state"),
        pl.col("Xdeployment ID").alias("individual_id"),
        pl.lit("usgs_hourly_life_history").alias("source"),
    ])

    print(f"  Loaded {len(df):,} GPS locations")
    print(f"  Life history states: {df['life_history_state'].n_unique()}")

    return df


def summarize_by_species(df: pl.DataFrame) -> pl.DataFrame:
    """Create summary statistics by species."""
    aggs = [
        pl.len().alias("n_locations"),
        pl.col("individual_id").n_unique().alias("n_individuals"),
        pl.col("latitude").min().alias("lat_min"),
        pl.col("latitude").max().alias("lat_max"),
        pl.col("longitude").min().alias("lon_min"),
        pl.col("longitude").max().alias("lon_max"),
    ]

    # Add timestamp aggregation if column exists
    if "timestamp_dt" in df.columns:
        aggs.extend([
            pl.col("timestamp_dt").min().alias("date_min"),
            pl.col("timestamp_dt").max().alias("date_max"),
        ])

    summary = df.group_by("scientific_name").agg(aggs).sort("n_locations", descending=True)

    return summary


def main():
    print("=" * 60)
    print("LOADING GPS TELEMETRY DATA")
    print("=" * 60)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load waterfowl GPS
    print("\nLoading USGS Waterfowl GPS (2019-2020)...")
    waterfowl = load_waterfowl_gps()

    # Load hourly GPS with life history
    print("\nLoading USGS Hourly GPS with Life History...")
    hourly = load_hourly_gps_life_history()

    # Save individual datasets
    if len(waterfowl) > 0:
        output_path = OUTPUT_DIR / "waterfowl_gps_2019_2020.parquet"
        waterfowl.write_parquet(output_path)
        print(f"\nSaved: {output_path}")

        # Species summary
        species_summary = summarize_by_species(waterfowl)
        summary_path = OUTPUT_DIR / "waterfowl_species_summary.csv"
        species_summary.write_csv(summary_path)
        print(f"Saved: {summary_path}")

    if len(hourly) > 0:
        output_path = OUTPUT_DIR / "hourly_life_history_gps.parquet"
        hourly.write_parquet(output_path)
        print(f"Saved: {output_path}")

    # Create metadata
    metadata = {
        "generated": datetime.now().isoformat(),
        "datasets": {
            "waterfowl_gps_2019_2020": {
                "records": len(waterfowl) if len(waterfowl) > 0 else 0,
                "species": waterfowl["scientific_name"].n_unique() if len(waterfowl) > 0 else 0,
                "individuals": waterfowl["individual_id"].n_unique() if len(waterfowl) > 0 else 0,
                "source": "USGS ScienceBase doi:10.5066/P13E7PCP",
            },
            "hourly_life_history": {
                "records": len(hourly) if len(hourly) > 0 else 0,
                "life_history_states": hourly["life_history_state"].unique().to_list() if len(hourly) > 0 else [],
                "source": "USGS ScienceBase doi:10.5066/P9XBZKZ8",
            },
        },
        "total_gps_locations": (len(waterfowl) if len(waterfowl) > 0 else 0) +
                               (len(hourly) if len(hourly) > 0 else 0),
    }

    metadata_path = OUTPUT_DIR / "gps_telemetry_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"Saved: {metadata_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("GPS TELEMETRY SUMMARY")
    print("=" * 60)
    print(f"\nTotal GPS locations: {metadata['total_gps_locations']:,}")

    if len(waterfowl) > 0:
        print("\nWaterfowl GPS by species:")
        for row in species_summary.iter_rows(named=True):
            print(f"  {row['scientific_name']}: {row['n_locations']:,} locations, {row['n_individuals']} individuals")


if __name__ == "__main__":
    main()
