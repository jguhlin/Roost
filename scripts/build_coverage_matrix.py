#!/usr/bin/env python3
"""
Build the coverage matrix showing data availability per species.
"""

import polars as pl
from pathlib import Path

DATA_DIR = Path("data")


def load_species_table() -> pl.DataFrame:
    """Load the species table."""
    return pl.read_parquet(DATA_DIR / "species_table.parquet")


def load_detection_data() -> pl.DataFrame:
    """Load APHIS detection data if available."""
    detection_file = DATA_DIR / "aphis_detections.parquet"
    if detection_file.exists():
        return pl.read_parquet(detection_file)
    return pl.DataFrame({
        "taxon_id": [],
        "detection_count": [],
    })


def load_gene_presence() -> pl.DataFrame:
    """Load gene presence matrix if available."""
    gene_file = DATA_DIR / "genes" / "gene_presence_matrix.parquet"
    if gene_file.exists():
        return pl.read_parquet(gene_file)
    return None


def load_expression_datasets() -> pl.DataFrame:
    """
    Load curated list of species with expression data.
    For now, manually curated from DATA_CATALOG.md.
    """
    # Species with known RNA-seq challenge data
    expression_species = [
        # PRJEB41063 - multi-species
        {"scientific_name": "Gallus gallus", "datasets": "PRJEB41063,CRA006707,E-MTAB-2908,multiple"},
        {"scientific_name": "Meleagris gallopavo", "datasets": "PRJEB41063"},
        {"scientific_name": "Anas platyrhynchos", "datasets": "PRJEB41063,E-MTAB-2909,PRJNA767080"},
        {"scientific_name": "Corvus macrorhynchos", "datasets": "PRJEB41063"},  # Jungle crow
        {"scientific_name": "Anser anser", "datasets": "PRJEB41063"},  # Embden/greylag goose
        {"scientific_name": "Columba livia", "datasets": "PRJEB41063,OMIX017644"},
        # PRJNA664709 - chicken and tufted duck
        {"scientific_name": "Aythya fuligula", "datasets": "PRJNA664709"},  # Tufted duck
        # Black/mute swan comparison
        {"scientific_name": "Cygnus atratus", "datasets": "PRJNA640810,PRJEB44719"},
        {"scientific_name": "Cygnus olor", "datasets": "reference_comparison"},
        # PRJDB17017 - 11 species fibroblasts (need to verify all species)
        {"scientific_name": "Grus japonensis", "datasets": "PRJDB17017"},  # Japanese crane
    ]
    return pl.DataFrame(expression_species)


def main():
    print("Loading species table...")
    species = load_species_table()
    print(f"  {len(species):,} species")

    print("Loading detection data...")
    detections = load_detection_data()
    print(f"  {len(detections)} species with detection data")

    print("Loading expression dataset info...")
    expression = load_expression_datasets()
    print(f"  {len(expression)} species with expression data")

    print("Loading gene presence data...")
    gene_matrix = load_gene_presence()
    if gene_matrix is not None:
        print(f"  Gene presence matrix: {len(gene_matrix)} species × {len(gene_matrix.columns)-1} genes")
    else:
        print("  No gene presence data yet")

    # Build coverage matrix
    print("Building coverage matrix...")

    # Add detection data
    coverage = species.join(
        detections.select(["taxon_id", "detection_count", "states_detected"]),
        on="taxon_id",
        how="left"
    ).with_columns([
        pl.col("detection_count").is_not_null().alias("has_detection"),
    ])

    # Add expression data flag
    coverage = coverage.join(
        expression.select(["scientific_name", "datasets"]),
        on="scientific_name",
        how="left"
    ).with_columns([
        pl.col("datasets").is_not_null().alias("has_expression"),
    ])

    # Add gene presence data if available
    has_gene_data = False
    gene_cols = []
    if gene_matrix is not None:
        gene_cols = [c for c in gene_matrix.columns if c != "taxon_id"]
        coverage = coverage.join(
            gene_matrix,
            on="taxon_id",
            how="left"
        )
        has_gene_data = True

    # Select and reorder columns for coverage matrix
    base_cols = [
        "taxon_id",
        "scientific_name",
        "common_name",
        "order",
        "family",
        "has_genome",
        "assembly_level",
        "scaffold_n50",
        "has_annotation",
        "has_expression",
        "datasets",
        "has_detection",
        "detection_count",
        "states_detected",
        "accession",
    ]
    # Add gene columns if available
    all_cols = base_cols + gene_cols if has_gene_data else base_cols
    # Filter to only columns that exist in coverage
    all_cols = [c for c in all_cols if c in coverage.columns]
    coverage_matrix = coverage.select(all_cols)

    # Summary
    print(f"\nCoverage matrix summary:")
    print(f"  Total species: {len(coverage_matrix):,}")
    print(f"  With genome: {coverage_matrix.filter(pl.col('has_genome')).height:,}")
    print(f"  With annotation: {coverage_matrix.filter(pl.col('has_annotation')).height:,}")
    print(f"  With detection: {coverage_matrix.filter(pl.col('has_detection')).height:,}")
    print(f"  With expression: {coverage_matrix.filter(pl.col('has_expression')).height:,}")
    print(f"  Chromosome-level: {coverage_matrix.filter(pl.col('assembly_level') == 'Chromosome').height:,}")

    # Gene presence summary if available
    if has_gene_data and gene_cols:
        print(f"\n  Gene presence ({len(gene_cols)} genes):")
        for gene in gene_cols[:6]:  # Show first 6 genes
            present_count = coverage_matrix.filter(pl.col(gene) == "Present").height
            print(f"    {gene}: {present_count} species")

    # Species with genome AND detection
    with_genome_detection = coverage_matrix.filter(
        pl.col("has_genome") & pl.col("has_detection")
    )
    print(f"\nSpecies with BOTH genome AND detection data: {len(with_genome_detection)}")

    # Top species with both
    print("\nTop 15 species with genome + detections (by detection count):")
    top_both = (
        with_genome_detection
        .sort("detection_count", descending=True)
        .head(15)
        .select([
            "scientific_name", "common_name", "detection_count",
            "assembly_level", "has_annotation"
        ])
    )
    print(top_both)

    # Species with detection but NO genome
    detection_no_genome = coverage_matrix.filter(
        pl.col("has_detection") & ~pl.col("has_genome")
    ).sort("detection_count", descending=True)
    print(f"\nSpecies with detection but NO genome: {len(detection_no_genome)}")
    if len(detection_no_genome) > 0:
        print("Top 10:")
        print(detection_no_genome.head(10).select([
            "scientific_name", "common_name", "detection_count"
        ]))

    # Write outputs
    print("\nWriting outputs...")
    coverage_matrix.write_parquet(DATA_DIR / "coverage_matrix.parquet")
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# coverage_matrix.write_csv(DATA_DIR / "coverage_matrix.tsv", separator="\t")

    # Also write a filtered version with only species that have some data
    has_data = coverage_matrix.filter(
        pl.col("has_genome") | pl.col("has_expression") | pl.col("has_detection").fill_null(False)
    )
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# has_data.write_csv(DATA_DIR / "coverage_matrix_with_data.tsv", separator="\t")
    print(f"  Wrote coverage_matrix.parquet ({len(coverage_matrix)} species)")
    print(f"  Wrote coverage_matrix_with_data.tsv ({len(has_data)} species with any data)")

    # Write order-level summary
    order_summary = (
        coverage_matrix
        .group_by("order")
        .agg([
            pl.len().alias("total_species"),
            pl.col("has_genome").sum().alias("with_genome"),
            pl.col("has_annotation").sum().alias("with_annotation"),
            pl.col("has_detection").sum().alias("with_detection"),
            pl.col("detection_count").sum().alias("total_detections"),
            pl.col("has_expression").sum().alias("with_expression"),
            (pl.col("assembly_level") == "Chromosome").sum().alias("chromosome_level"),
        ])
        .with_columns([
            (100 * pl.col("with_genome") / pl.col("total_species")).round(1).alias("pct_genome"),
            (100 * pl.col("with_detection") / pl.col("total_species")).round(1).alias("pct_detection"),
        ])
        .sort("total_detections", descending=True, nulls_last=True)
    )
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# order_summary.write_csv(DATA_DIR / "coverage_by_order.tsv", separator="\t")
    print(f"  Wrote coverage_by_order.tsv")


if __name__ == "__main__":
    main()
