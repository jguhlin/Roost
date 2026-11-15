#!/usr/bin/env python3
"""
Detection record deduplication for Roost.

Identifies and removes duplicate records across sources:
- Exact duplicates (same data from multiple sources)
- Near-duplicates (same species + date + location within radius)

Keeps the highest-quality record based on:
1. Coordinate presence (prefer georeferenced)
2. Strain information
3. Sampling type information
4. Source reliability

Usage:
    python scripts/deduplicate.py
    python scripts/deduplicate.py --dry-run
    python scripts/deduplicate.py --show-duplicates
"""

import argparse
import json
from pathlib import Path
from datetime import date

import polars as pl

DATA_DIR = Path("data")

# Known exact duplicates (same data, different source names)
# Format: source_to_remove -> source_to_keep
KNOWN_DUPLICATES = {
    "github_usa": "oafd_us_2022",      # Same OAFD data from GitHub mirror
    "github_italy": "italy_wild",       # Same Italy data from GitHub mirror
}

# Source quality ranking (higher = better, prefer to keep)
SOURCE_QUALITY = {
    "aphis_us": 100,         # Official USDA source, high quality
    "aphis_mammals": 95,     # Official USDA mammals page export
    "aphis_flocks": 95,      # Official USDA flock dashboard export
    "canada_cwhc": 95,       # Official Canadian source
    "uk_defra": 95,          # Official UK APHA source (2024-2026)
    "vs_surveillance": 90,   # USDA VS surveillance
    "oafd_us_2022": 85,      # Curated Zenodo dataset
    "iceland_usgs": 80,      # USGS Iceland study
    "usgs_alaska": 80,       # USGS Alaska study
    "acap_hpai": 80,         # ACAP seabird HPAI database
    "italy_wild": 75,        # Official Italy data
    "ireland_occurrence": 70,
    "owid_h5n1_human": 70,   # WHO/CDC H5N1 human cases
    "sdm_hpai": 65,          # European SDM aggregation
    "empresi_linked": 60,    # FAO EMPRES-i linked
    "gisaid_avilist": 55,    # Derived from GISAID
    # GitHub mirrors (duplicates)
    "github_usa": 40,
    "github_italy": 40,
}


def get_source_quality(source: str) -> int:
    """Get quality score for a source."""
    return SOURCE_QUALITY.get(source, 50)


def remove_known_duplicates(df: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """
    Remove records from known duplicate sources.

    Returns (cleaned_df, stats_dict)
    """
    stats = {"removed_sources": {}, "records_removed": 0}

    for dup_source, keep_source in KNOWN_DUPLICATES.items():
        dup_count = df.filter(pl.col("source") == dup_source).height
        if dup_count > 0:
            df = df.filter(pl.col("source") != dup_source)
            stats["removed_sources"][dup_source] = {
                "records": dup_count,
                "kept_source": keep_source,
            }
            stats["records_removed"] += dup_count

    return df, stats


def find_near_duplicates(
    df: pl.DataFrame,
    date_tolerance_days: int = 1,
    coord_tolerance_degrees: float = 0.1,
) -> pl.DataFrame:
    """
    Find near-duplicate records.

    Records are considered duplicates if they have:
    - Same taxon_id (or scientific_name if taxon_id is null)
    - Date within tolerance
    - Coordinates within tolerance (if both have coords)
    - OR same state/county (if no coords)

    Returns DataFrame with duplicate groups marked.
    """
    # Add duplicate detection key
    # Handle multiple date formats
    # Handle multiple date formats:
    # - ISO: "2024-01-15"
    # - US: "1/15/2024"
    # - ISO Week: "2024-W01-1" (UK DEFRA)
    df = df.with_columns([
        pl.when(pl.col("date_detected").str.contains(r"^\d{4}-\d{2}-\d{2}"))
          .then(pl.col("date_detected").str.to_date("%Y-%m-%d", strict=False))
          .when(pl.col("date_detected").str.contains(r"^\d{1,2}/\d{1,2}/\d{4}"))
          .then(pl.col("date_detected").str.to_date("%m/%d/%Y", strict=False))
          .when(pl.col("date_detected").str.contains(r"^\d{4}-W\d{2}"))
          # ISO week format: parse year and week, convert to approximate date
          .then(
              pl.concat_str([
                  pl.col("date_detected").str.extract(r"(\d{4})-W", group_index=1),
                  pl.lit("-01-01")
              ]).str.to_date("%Y-%m-%d", strict=False)
              # Add week offset (approximate)
              + pl.duration(weeks=pl.col("date_detected")
                  .str.extract(r"-W(\d{2})", group_index=1)
                  .cast(pl.Int32).fill_null(1) - 1)
          )
          .otherwise(pl.lit(None).cast(pl.Date))
          .alias("date_key"),
    ])

    # For records with coordinates, round to tolerance
    if "latitude" in df.columns and "longitude" in df.columns:
        df = df.with_columns([
            (pl.col("latitude") / coord_tolerance_degrees).round().alias("lat_bucket"),
            (pl.col("longitude") / coord_tolerance_degrees).round().alias("lon_bucket"),
        ])
    else:
        df = df.with_columns([
            pl.lit(None).cast(pl.Float64).alias("lat_bucket"),
            pl.lit(None).cast(pl.Float64).alias("lon_bucket"),
        ])

    # Create dedup key
    # species_raw (lowercased) is part of the key so that distinct premises
    # detected the same day in the same county (APHIS flocks: multiple
    # production types / Special IDs) and cross-source records for different
    # species without taxon_id are not collapsed. Every component is
    # null-safe: pl.concat_str propagates nulls, and records with unmapped
    # species or unparseable dates previously all collapsed into a single
    # null-keyed group (silently dropped ~9k vs_surveillance records).
    df = df.with_columns([
        pl.concat_str([
            pl.col("taxon_id").cast(pl.Utf8).fill_null(pl.col("scientific_name"))
              .fill_null(""),
            pl.col("date_key").cast(pl.Utf8).fill_null(""),
            pl.col("country").fill_null(""),
            # Use coord buckets if available, otherwise state
            pl.when(pl.col("lat_bucket").is_not_null())
              .then(pl.col("lat_bucket").cast(pl.Utf8))
              .otherwise(pl.col("state").fill_null("")),
            pl.when(pl.col("lon_bucket").is_not_null())
              .then(pl.col("lon_bucket").cast(pl.Utf8))
              .otherwise(pl.col("county").fill_null("")),
            pl.col("species_raw").cast(pl.Utf8).fill_null("").str.to_lowercase(),
            # Stable per-record reference (APHIS flock "Special ID") — distinct
            # premises detected the same day in the same county must not collapse
            pl.col("record_ref").cast(pl.Utf8).fill_null("")
              if "record_ref" in df.columns else pl.lit(""),
        ], separator="|").alias("dedup_key")
    ])

    return df


def score_record(row: dict) -> int:
    """
    Score a record for quality (higher = better to keep).

    Factors:
    - Source quality
    - Has coordinates
    - Has strain info
    - Has sampling type
    """
    score = get_source_quality(row.get("source", ""))

    # Bonus for coordinates
    if row.get("latitude") is not None and row.get("longitude") is not None:
        score += 20

    # Bonus for strain info
    if row.get("strain") and str(row.get("strain")).strip():
        score += 10

    # Bonus for sampling type
    sampling = row.get("sampling_type", "")
    if sampling and sampling != "unknown":
        score += 10

    # Bonus for taxon_id (mapped to NCBI)
    if row.get("taxon_id") is not None:
        score += 5

    return score


def deduplicate_groups(df: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """
    Deduplicate records within each dedup_key group.

    Keeps the highest-scoring record from each group.
    """
    # Find groups with multiple records
    group_counts = df.group_by("dedup_key").agg(pl.len().alias("group_size"))
    dup_keys = group_counts.filter(pl.col("group_size") > 1)["dedup_key"].to_list()

    print(f"  Found {len(dup_keys):,} duplicate groups")

    if len(dup_keys) == 0:
        drop_cols = ["dedup_key", "date_key", "lat_bucket", "lon_bucket"]
        for col in drop_cols:
            if col in df.columns:
                df = df.drop(col)
        return df, {"duplicates_removed": 0}

    # Separate duplicates from unique records
    unique = df.filter(~pl.col("dedup_key").is_in(dup_keys))
    duplicates = df.filter(pl.col("dedup_key").is_in(dup_keys))

    # Calculate quality score using polars expressions
    # Build quality score column
    source_quality_map = {k: v for k, v in SOURCE_QUALITY.items()}

    duplicates = duplicates.with_columns([
        # Base source quality
        pl.col("source").replace(source_quality_map, default=50).alias("_base_quality"),
    ]).with_columns([
        # Add bonuses
        (
            pl.col("_base_quality") +
            # Coordinates bonus
            pl.when(pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null())
              .then(20)
              .otherwise(0) +
            # Strain bonus
            pl.when(pl.col("strain").is_not_null() & (pl.col("strain") != ""))
              .then(10)
              .otherwise(0) +
            # Sampling type bonus
            pl.when(pl.col("sampling_type").is_not_null() & (pl.col("sampling_type") != "unknown"))
              .then(10)
              .otherwise(0) +
            # Taxon ID bonus
            pl.when(pl.col("taxon_id").is_not_null())
              .then(5)
              .otherwise(0)
        ).alias("_quality_score")
    ]).drop("_base_quality")

    # Keep best record per group
    best_records = (
        duplicates
        .sort(["dedup_key", "_quality_score"], descending=[False, True])
        .group_by("dedup_key")
        .first()
        .drop("_quality_score")
    )

    # Ensure same column order
    all_cols = unique.columns
    best_records = best_records.select(all_cols)

    # Combine
    result = pl.concat([unique, best_records])

    # Clean up temporary columns
    drop_cols = ["dedup_key", "date_key", "lat_bucket", "lon_bucket"]
    for col in drop_cols:
        if col in result.columns:
            result = result.drop(col)

    duplicates_removed = len(df) - len(result)

    return result, {"duplicates_removed": duplicates_removed}


def deduplicate(df: pl.DataFrame, dry_run: bool = False) -> tuple[pl.DataFrame, dict]:
    """
    Full deduplication pipeline.

    Returns (cleaned_df, stats_dict)
    """
    original_count = len(df)
    stats = {
        "original_records": original_count,
        "steps": [],
    }

    print(f"Starting with {original_count:,} records")

    # Step 1: Remove known duplicate sources
    print("\nStep 1: Removing known duplicate sources...")
    df, step1_stats = remove_known_duplicates(df)
    stats["steps"].append({"name": "remove_known_duplicates", **step1_stats})
    print(f"  Removed {step1_stats['records_removed']:,} records from duplicate sources")

    # Step 2: Find and remove near-duplicates
    print("\nStep 2: Finding near-duplicates...")
    df = find_near_duplicates(df)

    print("Step 3: Deduplicating groups...")
    df, step3_stats = deduplicate_groups(df)
    stats["steps"].append({"name": "deduplicate_groups", **step3_stats})
    print(f"  Removed {step3_stats['duplicates_removed']:,} near-duplicate records")

    stats["final_records"] = len(df)
    stats["total_removed"] = original_count - len(df)
    stats["reduction_pct"] = (original_count - len(df)) / original_count * 100

    return df, stats


def main():
    parser = argparse.ArgumentParser(description="Deduplicate detection records")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be done")
    parser.add_argument("--show-duplicates", action="store_true", help="Show duplicate details")
    args = parser.parse_args()

    print("=" * 60)
    print("DETECTION RECORD DEDUPLICATION")
    print("=" * 60)

    # Load detections
    detections_file = DATA_DIR / "detections_merged.parquet"
    if not detections_file.exists():
        print("No detections file found. Run ingest-detections first.")
        return

    df = pl.read_parquet(detections_file)
    print(f"\nLoaded {len(df):,} detection records")

    # Show source distribution
    print("\nRecords by source (before):")
    source_counts = df.group_by("source").agg(pl.len().alias("count")).sort("count", descending=True)
    for row in source_counts.iter_rows(named=True):
        quality = get_source_quality(row["source"])
        dup_marker = " [DUP]" if row["source"] in KNOWN_DUPLICATES else ""
        print(f"  {row['source']:20s} {row['count']:6,} (quality: {quality}){dup_marker}")

    # Deduplicate
    df_clean, stats = deduplicate(df, dry_run=args.dry_run)

    # Results
    print(f"\n{'=' * 60}")
    print("DEDUPLICATION RESULTS")
    print("=" * 60)
    print(f"Original records:  {stats['original_records']:,}")
    print(f"Final records:     {stats['final_records']:,}")
    print(f"Records removed:   {stats['total_removed']:,} ({stats['reduction_pct']:.1f}%)")

    # Show source distribution after
    print("\nRecords by source (after):")
    source_counts_after = df_clean.group_by("source").agg(pl.len().alias("count")).sort("count", descending=True)
    for row in source_counts_after.iter_rows(named=True):
        print(f"  {row['source']:20s} {row['count']:6,}")

    if not args.dry_run:
        # Save cleaned data
        print("\nSaving deduplicated data...")

        # Backup original
        backup_file = DATA_DIR / "detections_merged_backup.parquet"
        if not backup_file.exists():
            df_orig = pl.read_parquet(detections_file)
            df_orig.write_parquet(backup_file)
            print(f"  Backed up original to {backup_file}")

        # Write cleaned
        df_clean.write_parquet(detections_file)
        print(f"  Updated {detections_file}")

        # Save dedup stats
        stats_file = DATA_DIR / "deduplication_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2, default=str)
        print(f"  Wrote {stats_file}")

        print("\nRun build-phenotype and build-profiles to update derived tables.")
    else:
        print("\n[DRY RUN] No changes made")


if __name__ == "__main__":
    main()
