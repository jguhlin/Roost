#!/usr/bin/env python3
"""
Generate publication-ready summary statistics for Roost.

Creates comprehensive tables and statistics suitable for:
- Publication supplementary materials
- Data quality reporting
- Dashboard displays

Output: data/summary/ (multiple TSV and JSON files)

Usage:
    python scripts/generate_summary_stats.py
"""

import json
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")
OUTPUT_DIR = DATA_DIR / "summary"


def load_data() -> dict:
    """Load all data sources."""
    data = {}

    # Detections
    det_file = DATA_DIR / "detections_merged.parquet"
    if det_file.exists():
        data["detections"] = pl.read_parquet(det_file)
    else:
        data["detections"] = pl.DataFrame()

    # Species profiles
    profiles_file = DATA_DIR / "species_profiles.parquet"
    if profiles_file.exists():
        data["profiles"] = pl.read_parquet(profiles_file)
    else:
        data["profiles"] = pl.DataFrame()

    # Susceptibility
    susc_file = DATA_DIR / "susceptibility_scores.parquet"
    if susc_file.exists():
        data["susceptibility"] = pl.read_parquet(susc_file)
    else:
        data["susceptibility"] = pl.DataFrame()

    return data


def generate_overview_stats(data: dict) -> dict:
    """Generate high-level overview statistics."""
    det = data["detections"]
    profiles = data["profiles"]
    susc = data["susceptibility"]

    # Detection stats
    total_detections = len(det)
    georef_detections = det.filter(
        pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()
    ).height if len(det) > 0 else 0

    # Species stats
    total_species = len(profiles)
    species_with_detections = profiles.filter(pl.col("has_detections")).height if len(profiles) > 0 else 0
    species_with_genome = profiles.filter(pl.col("has_genome")).height if len(profiles) > 0 else 0

    # Susceptibility stats
    species_scored = len(susc)
    high_conf = susc.filter(pl.col("confidence") >= 0.5).height if len(susc) > 0 else 0

    return {
        "generated": str(date.today()),
        "detection_records": {
            "total": total_detections,
            "georeferenced": georef_detections,
            "georeferenced_pct": round(100 * georef_detections / total_detections, 1) if total_detections > 0 else 0,
        },
        "species": {
            "total_in_taxonomy": total_species,
            "with_detections": species_with_detections,
            "with_genome": species_with_genome,
            "with_susceptibility_score": species_scored,
            "high_confidence_scores": high_conf,
        },
        "data_sources": {
            "count": det["source"].n_unique() if len(det) > 0 and "source" in det.columns else 0,
        },
    }


def generate_detection_by_source(data: dict) -> pl.DataFrame:
    """Generate detection counts by data source."""
    det = data["detections"]
    if len(det) == 0 or "source" not in det.columns:
        return pl.DataFrame()

    by_source = det.group_by("source").agg([
        pl.len().alias("detection_count"),
        pl.col("scientific_name").n_unique().alias("species_count"),
    ]).sort("detection_count", descending=True)

    # Add percentage
    total = by_source["detection_count"].sum()
    by_source = by_source.with_columns([
        (pl.col("detection_count") / total * 100).round(1).alias("pct_of_total")
    ])

    return by_source


def generate_detection_by_country(data: dict) -> pl.DataFrame:
    """Generate detection counts by country."""
    det = data["detections"]
    if len(det) == 0 or "country" not in det.columns:
        return pl.DataFrame()

    by_country = det.filter(pl.col("country").is_not_null()).group_by("country").agg([
        pl.len().alias("detection_count"),
        pl.col("scientific_name").n_unique().alias("species_count"),
    ]).sort("detection_count", descending=True)

    return by_country


def generate_detection_by_order(data: dict) -> pl.DataFrame:
    """Generate detection counts by taxonomic order."""
    susc = data["susceptibility"]
    if len(susc) == 0:
        return pl.DataFrame()

    by_order = susc.group_by("order").agg([
        pl.len().alias("species_count"),
        pl.col("detection_count").sum().alias("total_detections"),
        pl.col("susceptibility_score").mean().round(1).alias("avg_susceptibility"),
        pl.col("has_rigi").first().alias("has_rigi"),
    ]).sort("total_detections", descending=True)

    return by_order


def generate_susceptibility_distribution(data: dict) -> pl.DataFrame:
    """Generate susceptibility class distribution."""
    susc = data["susceptibility"]
    if len(susc) == 0:
        return pl.DataFrame()

    by_class = susc.group_by("susceptibility_class").agg([
        pl.len().alias("species_count"),
        pl.col("detection_count").sum().alias("total_detections"),
        pl.col("susceptibility_score").mean().round(1).alias("avg_score"),
        pl.col("confidence").mean().round(2).alias("avg_confidence"),
    ])

    # Order by severity
    class_order = ["highly_susceptible", "susceptible", "intermediate", "tolerant", "highly_tolerant"]
    by_class = by_class.with_columns([
        pl.col("susceptibility_class").map_elements(
            lambda x: class_order.index(x) if x in class_order else 99,
            return_dtype=pl.Int64
        ).alias("_order")
    ]).sort("_order").drop("_order")

    return by_class


def generate_genome_coverage(data: dict) -> pl.DataFrame:
    """Generate genome coverage statistics by order."""
    profiles = data["profiles"]
    if len(profiles) == 0:
        return pl.DataFrame()

    # Only include orders with detected species
    detected = profiles.filter(pl.col("has_detections"))

    by_order = detected.group_by("order").agg([
        pl.len().alias("species_with_detections"),
        pl.col("has_genome").sum().alias("with_genome"),
        pl.col("has_annotation").fill_null(False).sum().alias("with_annotation"),
    ]).filter(pl.col("order").is_not_null())

    by_order = by_order.with_columns([
        (pl.col("with_genome") / pl.col("species_with_detections") * 100).round(1).alias("genome_coverage_pct"),
        (pl.col("with_annotation") / pl.col("species_with_detections") * 100).round(1).alias("annotation_coverage_pct"),
    ]).sort("species_with_detections", descending=True)

    return by_order


def generate_top_species(data: dict, n: int = 50) -> pl.DataFrame:
    """Generate top N species by detection count."""
    susc = data["susceptibility"]
    if len(susc) == 0:
        return pl.DataFrame()

    top = susc.select([
        "scientific_name",
        "common_name",
        "order",
        "family",
        "detection_count",
        "susceptibility_score",
        "susceptibility_class",
        "confidence",
        "has_rigi",
        "has_genome",
    ]).sort("detection_count", descending=True).head(n)

    return top


def generate_data_quality_report(data: dict) -> dict:
    """Generate data quality metrics."""
    det = data["detections"]
    profiles = data["profiles"]

    quality = {
        "detections": {},
        "species": {},
    }

    if len(det) > 0:
        total = len(det)
        quality["detections"] = {
            "total_records": total,
            "with_coordinates": det.filter(
                pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()
            ).height,
            "with_date": det.filter(pl.col("date_detected").is_not_null()).height,
            "with_country": det.filter(pl.col("country").is_not_null()).height,
            "with_strain": det.filter(
                pl.col("strain").is_not_null() & (pl.col("strain") != "")
            ).height if "strain" in det.columns else 0,
        }

        # Calculate percentages
        for key in list(quality["detections"].keys()):
            if key != "total_records":
                pct_key = f"{key}_pct"
                quality["detections"][pct_key] = round(
                    100 * quality["detections"][key] / total, 1
                )

    if len(profiles) > 0:
        detected = profiles.filter(pl.col("has_detections"))
        quality["species"] = {
            "total_in_taxonomy": len(profiles),
            "with_detections": len(detected),
            "with_genome": detected.filter(pl.col("has_genome")).height,
            "with_annotation": detected.filter(
                pl.col("has_annotation").fill_null(False)
            ).height,
            "with_phenotype": detected.filter(
                pl.col("has_phenotype").fill_null(False)
            ).height,
            "complete_data": detected.filter(
                pl.col("data_completeness") == 100
            ).height if "data_completeness" in detected.columns else 0,
        }

    return quality


def main():
    print("=" * 60)
    print("GENERATING SUMMARY STATISTICS")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    data = load_data()
    print(f"  Detections: {len(data['detections']):,}")
    print(f"  Profiles: {len(data['profiles']):,}")
    print(f"  Susceptibility: {len(data['susceptibility']):,}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate all statistics
    print("\nGenerating statistics...")

    # 1. Overview stats (JSON)
    print("  Overview statistics...")
    overview = generate_overview_stats(data)
    with open(OUTPUT_DIR / "overview.json", "w") as f:
        json.dump(overview, f, indent=2)

    # 2. Detection by source
    print("  Detection by source...")
    by_source = generate_detection_by_source(data)
    if len(by_source) > 0:
        by_source.write_csv(OUTPUT_DIR / "detections_by_source.tsv", separator="\t")

    # 3. Detection by country
    print("  Detection by country...")
    by_country = generate_detection_by_country(data)
    if len(by_country) > 0:
        by_country.write_csv(OUTPUT_DIR / "detections_by_country.tsv", separator="\t")

    # 4. Detection by order
    print("  Detection by order...")
    by_order = generate_detection_by_order(data)
    if len(by_order) > 0:
        by_order.write_csv(OUTPUT_DIR / "detections_by_order.tsv", separator="\t")

    # 5. Susceptibility distribution
    print("  Susceptibility distribution...")
    susc_dist = generate_susceptibility_distribution(data)
    if len(susc_dist) > 0:
        susc_dist.write_csv(OUTPUT_DIR / "susceptibility_distribution.tsv", separator="\t")

    # 6. Genome coverage
    print("  Genome coverage...")
    genome_cov = generate_genome_coverage(data)
    if len(genome_cov) > 0:
        genome_cov.write_csv(OUTPUT_DIR / "genome_coverage_by_order.tsv", separator="\t")

    # 7. Top species
    print("  Top species...")
    top_species = generate_top_species(data)
    if len(top_species) > 0:
        top_species.write_csv(OUTPUT_DIR / "top_50_species.tsv", separator="\t")

    # 8. Data quality report
    print("  Data quality report...")
    quality = generate_data_quality_report(data)
    with open(OUTPUT_DIR / "data_quality.json", "w") as f:
        json.dump(quality, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nFiles generated:")
    for f in sorted(OUTPUT_DIR.glob("*")):
        print(f"  {f.name}")

    print("\n--- Overview ---")
    print(f"Detection records: {overview['detection_records']['total']:,}")
    print(f"  Georeferenced: {overview['detection_records']['georeferenced']:,} ({overview['detection_records']['georeferenced_pct']}%)")
    print(f"Species with detections: {overview['species']['with_detections']}")
    print(f"  With genome: {overview['species']['with_genome']}")
    print(f"  With susceptibility score: {overview['species']['with_susceptibility_score']}")
    print(f"    High-confidence: {overview['species']['high_confidence_scores']}")

    if len(by_country) > 0:
        print("\n--- Top Countries ---")
        for row in by_country.head(5).iter_rows(named=True):
            print(f"  {row['country']}: {row['detection_count']:,} detections, {row['species_count']} species")

    if len(susc_dist) > 0:
        print("\n--- Susceptibility Distribution ---")
        for row in susc_dist.iter_rows(named=True):
            print(f"  {row['susceptibility_class']}: {row['species_count']} species")


if __name__ == "__main__":
    main()
