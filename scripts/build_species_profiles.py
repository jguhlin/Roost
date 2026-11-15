#!/usr/bin/env python3
"""
Build unified species profiles for Roost.

Creates a single table with one row per species, joining:
- Taxonomy (order, family, genus, common names)
- Detection summary (count, countries, date range, strains)
- Genome info (best assembly, annotation status, quality metrics)
- Phenotype (mortality rate, susceptibility class, confidence)

This is the primary synthesis layer for querying species data.

Usage:
    python scripts/build_species_profiles.py
    python scripts/build_species_profiles.py --min-detections 5
"""

import argparse
import json
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")


def load_taxonomy() -> pl.DataFrame:
    """Load species taxonomy: Aves base + supplement (mammals, drifted
    synonyms) resolved against NCBI. Mammals are spillover hosts with
    real detections and gene-panel runs — they belong in the profiles."""
    species_table = DATA_DIR / "species_table.parquet"
    if species_table.exists():
        base = pl.read_parquet(species_table)
        base = base.with_columns(pl.lit("Aves").alias("class"))
    else:
        # Fallback to TSV
        base = pl.read_csv(
            DATA_DIR / "aves_taxonomy.tsv",
            separator="\t",
            schema_overrides={"taxon_id": pl.Int64}
        ).filter(pl.col("rank") == "species").with_columns(
            pl.lit("Aves").alias("class"))

    supp_file = DATA_DIR / "taxonomy_supplement.tsv"
    if supp_file.exists():
        supp = pl.read_csv(supp_file, separator="\t",
                           schema_overrides={"taxon_id": pl.Int64})
        supp = supp.select([
            "taxon_id", "scientific_name", "common_name",
            "genus", "family", "order", "class",
        ])
        # Mammal orders (Carnivora etc.) must not collide with avian
        # order filters — they are distinct strings, so a plain concat is safe
        base_cols = ["taxon_id", "scientific_name", "common_name",
                     "genus", "family", "order", "class"]
        base = base.select(base_cols)
        base = pl.concat([base, supp], how="diagonal")
        n_mam = supp.filter(pl.col("class") == "Mammalia").height
        print(f"  + {supp.height} supplemented species "
              f"({n_mam} mammals, {supp.height - n_mam} resolvable birds)")
    return base


def load_genomes() -> pl.DataFrame:
    """Load genome assembly info."""
    genomes_file = DATA_DIR / "genomes.parquet"
    if not genomes_file.exists():
        return pl.DataFrame()

    return pl.read_parquet(genomes_file)


def load_detections() -> pl.DataFrame:
    """Load merged detection data."""
    detections_file = DATA_DIR / "detections_merged.parquet"
    if not detections_file.exists():
        return pl.DataFrame()

    return pl.read_parquet(detections_file)


def load_phenotype() -> pl.DataFrame:
    """Load phenotype table."""
    phenotype_file = DATA_DIR / "phenotype_table.parquet"
    if not phenotype_file.exists():
        return pl.DataFrame()

    return pl.read_parquet(phenotype_file)


def summarize_detections(detections: pl.DataFrame, taxonomy: pl.DataFrame | None = None) -> pl.DataFrame:
    """
    Summarize detection data per species.

    Mammal and synonym-drifted rows carry no taxon_id in the merged
    detections (they were resolved against aves taxonomy only) — a
    name-based backfill from the taxonomy table fixes them before
    aggregation.
    """
    if len(detections) == 0:
        return pl.DataFrame()

    if taxonomy is not None:
        name_map = taxonomy.select(
            ["scientific_name", "taxon_id"]).unique(subset=["scientific_name"])
        resolved = detections.join(
            name_map.rename({"taxon_id": "taxon_id_from_name"}),
            on="scientific_name", how="left")
        detections = resolved.with_columns(
            pl.coalesce(["taxon_id", "taxon_id_from_name"]).alias("taxon_id"))

    # Filter to mapped species
    mapped = detections.filter(pl.col("taxon_id").is_not_null())

    if len(mapped) == 0:
        return pl.DataFrame()

    summary = (
        mapped
        .group_by("taxon_id")
        .agg([
            # detection_records = number of surveillance records (rows) —
            # THE count shown as "detections" in the UI and captions.
            # detection_count (below) = summed animals affected: 1 for wild-
            # bird events, animals affected for premises (APHIS flocks) and
            # case counts for WAHIS/WHISPers events — "numbers affected".
            # Keep both; NEVER display detection_count as a detection tally
            # (it reaches 182M for chicken because of flock sizes).
            pl.len().alias("detection_records"),
            pl.col("detection_count").cast(pl.Int64).fill_null(1).sum()
              .alias("detection_count"),
            pl.col("country").drop_nulls().unique().alias("countries_detected"),
            pl.col("country").n_unique().alias("country_count"),
            pl.col("source").drop_nulls().unique().alias("sources"),
            pl.col("source").n_unique().alias("source_count"),
            pl.col("strain").drop_nulls().unique().alias("strains"),
            pl.col("strain").drop_nulls().n_unique().alias("strain_count"),
            pl.col("date_detected").min().alias("first_detection"),
            pl.col("date_detected").max().alias("last_detection"),
            # Coordinate info
            (pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()).sum().alias("georef_count"),
        ])
        .with_columns([
            (pl.col("georef_count") > 0).alias("has_coordinates"),
            # Convert lists to strings for easier output
            pl.col("countries_detected").list.join(", ").alias("countries_str"),
            pl.col("sources").list.join(", ").alias("sources_str"),
            pl.col("strains").list.join(", ").alias("strains_str"),
        ])
    )

    return summary


def summarize_genomes(genomes: pl.DataFrame) -> pl.DataFrame:
    """
    Get best genome per species.

    Returns DataFrame with columns:
    - taxon_id
    - genome_accession
    - assembly_level
    - scaffold_n50
    - total_length
    - has_annotation
    - genome_count (total assemblies for this species)
    """
    if len(genomes) == 0:
        return pl.DataFrame()

    # Rank assemblies
    level_ranks = {
        "Complete Genome": 4,
        "Chromosome": 3,
        "Scaffold": 2,
        "Contig": 1,
    }

    ranked = genomes.with_columns([
        pl.col("assembly_level").replace(level_ranks, default=0).alias("level_rank"),
        pl.col("accession").str.starts_with("GCF").alias("is_refseq"),
        (pl.col("annotation_status").is_not_null() &
         (pl.col("annotation_status") != "")).alias("has_annotation"),
    ])

    # Count per species
    counts = ranked.group_by("taxon_id").agg(pl.len().alias("genome_count"))

    # Select best per species
    best = (
        ranked
        .sort([
            "taxon_id",
            "is_refseq",
            "has_annotation",
            "level_rank",
            "scaffold_n50",
        ], descending=[False, True, True, True, True])
        .group_by("taxon_id")
        .first()
        .select([
            "taxon_id",
            pl.col("accession").alias("genome_accession"),
            "assembly_level",
            "scaffold_n50",
            "total_length",
            "has_annotation",
        ])
    )

    return best.join(counts, on="taxon_id", how="left")


def build_profiles(min_detections: int = 0) -> pl.DataFrame:
    """
    Build unified species profiles.

    Args:
        min_detections: Minimum detections to include species (0 = include all)

    Returns:
        DataFrame with one row per species
    """
    print("Loading data sources...")

    # Load all data
    taxonomy = load_taxonomy()
    print(f"  Taxonomy: {len(taxonomy):,} species")

    genomes = load_genomes()
    print(f"  Genomes: {len(genomes):,} assemblies")

    detections = load_detections()
    print(f"  Detections: {len(detections):,} records")

    phenotype = load_phenotype()
    print(f"  Phenotype: {len(phenotype):,} species")

    # Summarize detections (with name-based taxon backfill for mammals)
    print("\nSummarizing detections...")
    detection_summary = summarize_detections(detections, taxonomy)
    print(f"  {len(detection_summary):,} species with detections")

    # Summarize genomes (mammal rows carry taxon_id NULL — backfill by name)
    print("Summarizing genomes...")
    if len(genomes) > 0:
        name_map = taxonomy.select(
            ["scientific_name", "taxon_id"]).unique(subset=["scientific_name"])
        genomes = genomes.join(
            name_map.rename({"taxon_id": "taxon_id_from_name",
                             "scientific_name": "organism_name"}),
            on="organism_name", how="left")
        genomes = genomes.with_columns(
            pl.coalesce(["taxon_id", "taxon_id_from_name"]).alias("taxon_id"))
    genome_summary = summarize_genomes(genomes)
    print(f"  {len(genome_summary):,} species with genomes")

    # Build profiles starting from taxonomy (Aves + supplement)
    print("\nBuilding species profiles...")

    profiles = taxonomy.select([
        "taxon_id",
        "scientific_name",
        "common_name",
        "genus",
        "family",
        "order",
        "class",
    ])

    # Join detection summary
    if len(detection_summary) > 0:
        profiles = profiles.join(
            detection_summary.select([
                "taxon_id",
                "detection_records",
                "detection_count",
                "country_count",
                "countries_str",
                "source_count",
                "sources_str",
                "strain_count",
                "strains_str",
                "first_detection",
                "last_detection",
                "has_coordinates",
                "georef_count",
            ]),
            on="taxon_id",
            how="left"
        )
    else:
        # Add empty detection columns
        profiles = profiles.with_columns([
            pl.lit(None).cast(pl.Int64).alias("detection_records"),
            pl.lit(None).cast(pl.Int64).alias("detection_count"),
            pl.lit(None).cast(pl.Int64).alias("country_count"),
            pl.lit(None).cast(pl.Utf8).alias("countries_str"),
            pl.lit(None).cast(pl.Int64).alias("source_count"),
            pl.lit(None).cast(pl.Utf8).alias("sources_str"),
            pl.lit(None).cast(pl.Int64).alias("strain_count"),
            pl.lit(None).cast(pl.Utf8).alias("strains_str"),
            pl.lit(None).cast(pl.Date).alias("first_detection"),
            pl.lit(None).cast(pl.Date).alias("last_detection"),
            pl.lit(False).alias("has_coordinates"),
            pl.lit(0).cast(pl.Int64).alias("georef_count"),
        ])

    # Join genome summary
    if len(genome_summary) > 0:
        profiles = profiles.join(
            genome_summary.select([
                "taxon_id",
                "genome_accession",
                "assembly_level",
                "scaffold_n50",
                "total_length",
                "has_annotation",
                "genome_count",
            ]),
            on="taxon_id",
            how="left"
        )
    else:
        profiles = profiles.with_columns([
            pl.lit(None).cast(pl.Utf8).alias("genome_accession"),
            pl.lit(None).cast(pl.Utf8).alias("assembly_level"),
            pl.lit(None).cast(pl.Int64).alias("scaffold_n50"),
            pl.lit(None).cast(pl.Int64).alias("total_length"),
            pl.lit(False).alias("has_annotation"),
            pl.lit(0).cast(pl.Int64).alias("genome_count"),
        ])

    # Join phenotype
    if len(phenotype) > 0:
        profiles = profiles.join(
            phenotype.select([
                "taxon_id",
                "mortality_rate",
                "mortality_count",
                "live_count",
                "harvest_count",
                "phenotype_class",
                "confidence",
            ]),
            on="taxon_id",
            how="left"
        )
    else:
        profiles = profiles.with_columns([
            pl.lit(None).cast(pl.Float64).alias("mortality_rate"),
            pl.lit(None).cast(pl.Int64).alias("mortality_count"),
            pl.lit(None).cast(pl.Int64).alias("live_count"),
            pl.lit(None).cast(pl.Int64).alias("harvest_count"),
            pl.lit(None).cast(pl.Utf8).alias("phenotype_class"),
            pl.lit(None).cast(pl.Utf8).alias("confidence"),
        ])

    # Add derived flags
    # The phenotype table can hold >1 row per taxon (multiple studies),
    # which fan-out duplicates profile rows — collapse back to one per species
    profiles = profiles.unique(subset=["taxon_id"], keep="first")
    profiles = profiles.with_columns([
        (pl.col("detection_count").is_not_null() & (pl.col("detection_count") > 0)).alias("has_detections"),
        (pl.col("genome_accession").is_not_null()).alias("has_genome"),
        (pl.col("phenotype_class").is_not_null()).alias("has_phenotype"),
    ])

    # Fill nulls for counts
    profiles = profiles.with_columns([
        pl.col("detection_count").fill_null(0),
        pl.col("detection_records").fill_null(0),
        pl.col("country_count").fill_null(0),
        pl.col("source_count").fill_null(0),
        pl.col("strain_count").fill_null(0),
        pl.col("georef_count").fill_null(0),
        pl.col("genome_count").fill_null(0),
    ])

    # Calculate data completeness score (0-100)
    profiles = profiles.with_columns([
        (
            (pl.col("has_detections").cast(pl.Int64) * 25) +
            (pl.col("has_genome").cast(pl.Int64) * 25) +
            (pl.col("has_annotation").fill_null(False).cast(pl.Int64) * 15) +
            (pl.col("has_phenotype").cast(pl.Int64) * 20) +
            (pl.col("has_coordinates").fill_null(False).cast(pl.Int64) * 15)
        ).alias("data_completeness")
    ])

    # Filter by minimum detections if specified (record count, not animals
    # affected)
    if min_detections > 0:
        profiles = profiles.filter(pl.col("detection_records") >= min_detections)

    # Sort by detection records (most detected first), then by completeness
    profiles = profiles.sort(
        ["detection_records", "data_completeness"],
        descending=[True, True]
    )

    return profiles


def main():
    parser = argparse.ArgumentParser(description="Build unified species profiles")
    parser.add_argument(
        "--min-detections", "-m", type=int, default=0,
        help="Minimum detections to include species (0 = all)"
    )
    parser.add_argument(
        "--detected-only", action="store_true",
        help="Only include species with HPAI detections"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("BUILDING SPECIES PROFILES")
    print("=" * 60)

    min_det = 1 if args.detected_only else args.min_detections
    profiles = build_profiles(min_detections=min_det)

    print(f"\nSpecies profiles built: {len(profiles):,}")

    # Summary statistics
    with_detections = profiles.filter(pl.col("has_detections")).height
    with_genome = profiles.filter(pl.col("has_genome")).height
    with_phenotype = profiles.filter(pl.col("has_phenotype")).height
    with_coords = profiles.filter(pl.col("has_coordinates")).height

    print(f"\nData coverage:")
    print(f"  With HPAI detections: {with_detections:,}")
    print(f"  With genome assembly: {with_genome:,}")
    print(f"  With phenotype data:  {with_phenotype:,}")
    print(f"  With coordinates:     {with_coords:,}")

    # Species with complete data
    complete = profiles.filter(
        pl.col("has_detections") &
        pl.col("has_genome") &
        pl.col("has_phenotype")
    )
    print(f"\nSpecies with detection + genome + phenotype: {len(complete):,}")

    # Top species by detection count
    print(f"\nTop 10 most detected species:")
    top10 = profiles.filter(pl.col("has_detections")).head(10)
    for row in top10.iter_rows(named=True):
        genome = "✓" if row["has_genome"] else "✗"
        pheno = row.get("phenotype_class", "")[:4] if row.get("phenotype_class") else "-"
        mort = f"{row['mortality_rate']*100:.0f}%" if row.get("mortality_rate") is not None else "-"
        print(f"  {row['scientific_name']:30s} {row['detection_count']:5,} det  {genome} genome  {pheno:5s} {mort:>4s} mort")

    # By order
    print(f"\nDetections by order (top 10):")
    order_stats = (
        profiles
        .filter(pl.col("has_detections"))
        .group_by("order")
        .agg([
            pl.col("detection_count").sum().alias("total_detections"),
            pl.len().alias("species_count"),
        ])
        .sort("total_detections", descending=True)
        .head(10)
    )
    for row in order_stats.iter_rows(named=True):
        order = row["order"] or "Unknown"
        print(f"  {order:25s} {row['total_detections']:6,} detections ({row['species_count']} species)")

    # Phenotype distribution
    if with_phenotype > 0:
        print(f"\nPhenotype distribution:")
        pheno_stats = (
            profiles
            .filter(pl.col("has_phenotype"))
            .group_by("phenotype_class")
            .agg([
                pl.len().alias("species_count"),
                pl.col("detection_count").sum().alias("total_detections"),
            ])
            .sort("total_detections", descending=True)
        )
        for row in pheno_stats.iter_rows(named=True):
            print(f"  {row['phenotype_class']:20s} {row['species_count']:3} species, {row['total_detections']:,} detections")

    # Save outputs
    print("\nSaving outputs...")

    # Full profiles
    profiles.write_parquet(DATA_DIR / "species_profiles.parquet")
    print(f"  species_profiles.parquet ({len(profiles):,} species)")

    # Detected species only (more useful for most queries)
    detected = profiles.filter(pl.col("has_detections"))
    detected.write_parquet(DATA_DIR / "species_profiles_detected.parquet")
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# detected.write_csv(DATA_DIR / "species_profiles_detected.tsv", separator="\t")
    print(f"  species_profiles_detected.parquet/tsv ({len(detected):,} species)")

    # High-value species (complete data)
    if len(complete) > 0:
        # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# complete.write_csv(DATA_DIR / "species_profiles_complete.tsv", separator="\t")
        print(f"  species_profiles_complete.tsv ({len(complete):,} species)")

    # JSON summary for programmatic access
    summary = {
        "generated": str(date.today()),
        "total_species": len(profiles),
        "with_detections": with_detections,
        "with_genome": with_genome,
        "with_phenotype": with_phenotype,
        "complete_data": len(complete),
        "top_detected": [
            {
                "taxon_id": int(row["taxon_id"]),
                "scientific_name": row["scientific_name"],
                "common_name": row["common_name"],
                "detection_count": int(row["detection_count"]),
                "detection_records": int(row.get("detection_records") or 0),
                "countries": row.get("countries_str", ""),
                "has_genome": row["has_genome"],
                "phenotype_class": row.get("phenotype_class"),
                "mortality_rate": row.get("mortality_rate"),
            }
            for row in top10.iter_rows(named=True)
        ],
    }
    with open(DATA_DIR / "species_profiles_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  species_profiles_summary.json")


if __name__ == "__main__":
    main()
