#!/usr/bin/env python3
"""
Build phenotype table from merged detection data.

Derives mortality rate from sampling method:
- Morbidity/Mortality = bird found sick or dead
- Hunter harvest / Live = bird was alive when sampled

Mortality rate = mortality_count / total_detections
- High mortality = susceptible (cannot tolerate virus)
- Low mortality = tolerant (reservoir species)

Sources:
- APHIS US wild birds (2023-2024)
- OAFD US wild birds (2022)
- Italy wild birds (2021-2023) - no mortality data, detection only
"""

import polars as pl
from pathlib import Path
import json

DATA_DIR = Path("data")


def load_merged_detections() -> pl.DataFrame:
    """Load merged detection data from all sources."""
    merged_file = DATA_DIR / "detections_merged.parquet"
    if merged_file.exists():
        return pl.read_parquet(merged_file)

    # Fallback to APHIS only if merged not available
    print("  Warning: Using APHIS only (run ingest-detections first for full data)")
    aphis = pl.read_csv(DATA_DIR / "raw" / "aphis_wild_birds.csv")
    return aphis.with_columns([
        pl.col("Bird Species").alias("species_raw"),
        pl.col("Sampling Method").str.to_lowercase().alias("sampling_method_raw"),
        pl.when(pl.col("Sampling Method").str.to_lowercase().str.contains("morbidity|mortality"))
          .then(pl.lit("mortality"))
          .when(pl.col("Sampling Method").str.to_lowercase().str.contains("live"))
          .then(pl.lit("live"))
          .otherwise(pl.lit("harvest"))
          .alias("sampling_type"),
        pl.lit("aphis_us").alias("source"),
        pl.lit("USA").alias("country"),
    ])


def build_phenotype_table(min_detections: int = 10) -> pl.DataFrame:
    """
    Build phenotype table with mortality rate per species.

    Args:
        min_detections: Minimum detections required for inclusion

    Note: Only includes species with sampling_type data (excludes Italy
    which only has detection counts without mortality information).
    """
    detections = load_merged_detections()

    # Filter to records with phenotype-relevant sampling data
    # (exclude 'unknown' sampling type from Italy, etc.)
    phenotype_data = detections.filter(
        pl.col("sampling_type").is_in(["mortality", "harvest", "live"])
    )

    print(f"  Records with phenotype data: {len(phenotype_data):,}")
    print(f"  Records excluded (no sampling info): {len(detections) - len(phenotype_data):,}")

    # Aggregate by taxon_id (preferred) or scientific_name
    # Group by taxon_id where available, otherwise by scientific_name
    species_stats = (
        phenotype_data
        .group_by(["taxon_id", "scientific_name"])
        .agg([
            pl.len().alias("total_detections"),
            (pl.col("sampling_type") == "mortality").sum().alias("mortality_count"),
            (pl.col("sampling_type") == "harvest").sum().alias("harvest_count"),
            (pl.col("sampling_type") == "live").sum().alias("live_count"),
            pl.col("strain").n_unique().alias("strain_count"),
            pl.col("country").n_unique().alias("country_count"),
            pl.col("source").n_unique().alias("source_count"),
            pl.col("source").unique().alias("sources"),
            pl.col("date_detected").min().alias("first_detection"),
            pl.col("date_detected").max().alias("last_detection"),
            # Keep raw species names for reference
            pl.col("species_raw").unique().alias("raw_names"),
        ])
    )

    # Calculate derived metrics
    species_stats = species_stats.with_columns([
        # Mortality rate (primary phenotype)
        (pl.col("mortality_count") / pl.col("total_detections")).alias("mortality_rate"),
        # Live detection rate (survival/tolerance indicator)
        ((pl.col("harvest_count") + pl.col("live_count")) / pl.col("total_detections")).alias("live_rate"),
        # Convert list columns to strings for output
        pl.col("sources").list.join(", ").alias("data_sources"),
        pl.col("raw_names").list.join("; ").alias("common_names"),
    ])

    # Classify phenotype
    species_stats = species_stats.with_columns([
        pl.when(pl.col("mortality_rate") >= 0.9)
          .then(pl.lit("highly_susceptible"))
          .when(pl.col("mortality_rate") >= 0.5)
          .then(pl.lit("susceptible"))
          .when(pl.col("mortality_rate") >= 0.2)
          .then(pl.lit("intermediate"))
          .when(pl.col("mortality_rate") >= 0.05)
          .then(pl.lit("tolerant"))
          .otherwise(pl.lit("highly_tolerant"))
          .alias("phenotype_class")
    ])

    # Filter to minimum detections
    phenotype = species_stats.filter(pl.col("total_detections") >= min_detections)

    # Filter to mapped species (have taxon_id)
    phenotype_mapped = phenotype.filter(pl.col("taxon_id").is_not_null())

    print(f"  Species with >= {min_detections} detections: {len(phenotype)}")
    print(f"  Species mapped to NCBI: {len(phenotype_mapped)}")

    # Confidence based on sample size and source count
    phenotype_mapped = phenotype_mapped.with_columns([
        pl.when((pl.col("total_detections") >= 100) & (pl.col("source_count") >= 2))
          .then(pl.lit("high"))
          .when(pl.col("total_detections") >= 100)
          .then(pl.lit("high"))
          .when(pl.col("total_detections") >= 30)
          .then(pl.lit("medium"))
          .otherwise(pl.lit("low"))
          .alias("confidence")
    ])

    # Select and order columns
    phenotype_final = phenotype_mapped.select([
        "taxon_id",
        "scientific_name",
        "common_names",
        "total_detections",
        "mortality_count",
        "live_count",
        "harvest_count",
        "mortality_rate",
        "live_rate",
        "phenotype_class",
        "confidence",
        "strain_count",
        "country_count",
        "source_count",
        "data_sources",
        "first_detection",
        "last_detection",
    ]).sort("total_detections", descending=True)

    return phenotype_final


def main():
    print("=" * 60)
    print("BUILDING PHENOTYPE TABLE FROM MERGED DETECTION DATA")
    print("=" * 60)

    phenotype = build_phenotype_table(min_detections=10)

    print(f"\nSpecies with phenotype data: {len(phenotype)}")

    # Summary by phenotype class
    print("\nBy phenotype class:")
    class_summary = phenotype.group_by("phenotype_class").agg([
        pl.len().alias("species"),
        pl.col("total_detections").sum().alias("total_detections"),
    ]).sort("total_detections", descending=True)

    for row in class_summary.iter_rows(named=True):
        print(f"  {row['phenotype_class']:20s} {row['species']:3d} species, {row['total_detections']:,d} detections")

    # Multi-source species
    multi_source = phenotype.filter(pl.col("source_count") > 1)
    print(f"\nSpecies with data from multiple sources: {len(multi_source)}")

    # Examples
    print("\nHighly tolerant species (mortality < 5%):")
    tolerant = phenotype.filter(pl.col("phenotype_class") == "highly_tolerant").head(10)
    for row in tolerant.iter_rows(named=True):
        sources = row.get("data_sources", "unknown")
        print(f"  {row['scientific_name']:30s} {row['mortality_rate']*100:5.1f}% (n={row['total_detections']}) [{sources}]")

    print("\nHighly susceptible species (mortality >= 90%):")
    susceptible = phenotype.filter(pl.col("phenotype_class") == "highly_susceptible").head(10)
    for row in susceptible.iter_rows(named=True):
        sources = row.get("data_sources", "unknown")
        print(f"  {row['scientific_name']:30s} {row['mortality_rate']*100:5.1f}% (n={row['total_detections']}) [{sources}]")

    # Save outputs
    print("\nSaving outputs...")
    phenotype.write_parquet(DATA_DIR / "phenotype_table.parquet")
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# phenotype.write_csv(DATA_DIR / "phenotype_table.tsv", separator="\t")

    # Also save as JSON for provenance
    records = phenotype.to_dicts()
    with open(DATA_DIR / "phenotype_table.json", "w") as f:
        json.dump({
            "description": "HPAI mortality phenotype derived from sampling method",
            "method": "mortality_rate = mortality_detections / total_detections",
            "sources": [
                "APHIS US Wild Bird HPAI Detections (2023-2024)",
                "Open Avian Flu Dataset US (2022)",
            ],
            "min_detections": 10,
            "phenotype_classes": {
                "highly_susceptible": "mortality >= 90%",
                "susceptible": "mortality 50-90%",
                "intermediate": "mortality 20-50%",
                "tolerant": "mortality 5-20%",
                "highly_tolerant": "mortality < 5%",
            },
            "species_count": len(records),
            "multi_source_species": len(multi_source),
            "data": records,
        }, f, indent=2, default=str)

    print(f"  phenotype_table.parquet ({len(phenotype)} species)")
    print(f"  phenotype_table.tsv")
    print(f"  phenotype_table.json")


if __name__ == "__main__":
    main()
