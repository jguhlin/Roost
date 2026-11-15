#!/usr/bin/env python3
"""
Build the species table by joining taxonomy with genome inventory.
Select representative genome per species.
"""

import polars as pl
from pathlib import Path

DATA_DIR = Path("data")


def load_taxonomy() -> pl.DataFrame:
    """Load the Aves taxonomy."""
    return pl.read_csv(
        DATA_DIR / "aves_taxonomy.tsv",
        separator="\t",
        schema_overrides={"taxon_id": pl.Int64}
    )


def load_genomes() -> pl.DataFrame:
    """Load the genome inventory."""
    return pl.read_csv(
        DATA_DIR / "avian_genome_core.tsv",
        separator="\t",
        schema_overrides={"Organism Taxonomic ID": pl.Int64}
    ).rename({
        "Assembly Accession": "accession",
        "Organism Name": "organism_name",
        "Organism Common Name": "organism_common_name",
        "Organism Taxonomic ID": "taxon_id",
        "Assembly Level": "assembly_level",
        "Assembly Stats Contig N50": "contig_n50",
        "Assembly Stats Scaffold N50": "scaffold_n50",
        "Assembly Stats Total Sequence Length": "total_length",
        "Annotation Status": "annotation_status",
    })


def assembly_level_rank(level: str) -> int:
    """Rank assembly levels for sorting (higher is better)."""
    ranks = {
        "Complete Genome": 4,
        "Chromosome": 3,
        "Scaffold": 2,
        "Contig": 1,
    }
    return ranks.get(level, 0)


def select_representative(genomes: pl.DataFrame) -> pl.DataFrame:
    """
    Select representative genome per species.
    Priority:
    1. RefSeq (GCF) over GenBank (GCA)
    2. Annotated over unannotated
    3. Higher assembly level
    4. Higher scaffold N50
    """
    return (
        genomes
        .with_columns([
            # Is RefSeq?
            pl.col("accession").str.starts_with("GCF").alias("is_refseq"),
            # Is annotated?
            (pl.col("annotation_status").is_not_null() &
             (pl.col("annotation_status") != "")).alias("is_annotated"),
            # Assembly level rank
            pl.col("assembly_level").map_elements(
                assembly_level_rank, return_dtype=pl.Int64
            ).alias("level_rank"),
        ])
        .sort([
            "taxon_id",
            "is_refseq",
            "is_annotated",
            "level_rank",
            "scaffold_n50",
        ], descending=[False, True, True, True, True])
        .group_by("taxon_id")
        .first()
        .with_columns(pl.lit(True).alias("is_representative"))
    )


def main():
    print("Loading taxonomy...")
    taxonomy = load_taxonomy()
    print(f"  {len(taxonomy):,} taxa")

    # Filter to species only (not subspecies) for now
    species_taxonomy = taxonomy.filter(pl.col("rank") == "species")
    print(f"  {len(species_taxonomy):,} species")

    print("Loading genomes...")
    genomes = load_genomes()
    print(f"  {len(genomes):,} assemblies")

    print("Selecting representative genomes...")
    representatives = select_representative(genomes)
    print(f"  {len(representatives):,} species with genomes")

    # Join taxonomy with representative genomes
    print("Building species table...")
    species_table = (
        species_taxonomy
        .join(
            representatives.select([
                "taxon_id", "accession", "assembly_level",
                "contig_n50", "scaffold_n50", "total_length",
                "annotation_status", "is_representative"
            ]),
            on="taxon_id",
            how="left"
        )
        .with_columns([
            pl.col("accession").is_not_null().alias("has_genome"),
            (pl.col("annotation_status").is_not_null() &
             (pl.col("annotation_status") != "")).alias("has_annotation"),
        ])
    )

    # Summary stats
    with_genome = species_table.filter(pl.col("has_genome")).height
    with_annotation = species_table.filter(pl.col("has_annotation")).height
    chromosome_level = species_table.filter(
        pl.col("assembly_level") == "Chromosome"
    ).height

    print(f"\nSpecies table summary:")
    print(f"  Total species: {len(species_table):,}")
    print(f"  With genome: {with_genome:,} ({100*with_genome/len(species_table):.1f}%)")
    print(f"  With annotation: {with_annotation:,} ({100*with_annotation/len(species_table):.1f}%)")
    print(f"  Chromosome-level: {chromosome_level:,} ({100*chromosome_level/len(species_table):.1f}%)")

    # By order
    print(f"\nBy order (top 10):")
    order_stats = (
        species_table
        .group_by("order")
        .agg([
            pl.len().alias("total"),
            pl.col("has_genome").sum().alias("with_genome"),
            pl.col("has_annotation").sum().alias("with_annotation"),
        ])
        .with_columns(
            (100 * pl.col("with_genome") / pl.col("total")).round(1).alias("pct_genome")
        )
        .sort("total", descending=True)
        .head(10)
    )
    print(order_stats)

    # Write outputs
    print("\nWriting outputs...")

    # Full species table
    species_table.write_parquet(DATA_DIR / "species_table.parquet")
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# species_table.write_csv(DATA_DIR / "species_table.tsv", separator="\t")
    print(f"  Wrote species_table.parquet and species_table.tsv")

    # Genome list with representative flag
    genomes_with_rep = genomes.join(
        representatives.select(["accession", "is_representative"]),
        on="accession",
        how="left"
    ).with_columns(
        pl.col("is_representative").fill_null(False)
    )
    # D114: append mammal assemblies (infected-mammal panel) — the avian
    # TSV is birds-only; mammals come from mammal_candidates.json
    import json as _json
    _mc = DATA_DIR / "genomes" / "mammal_candidates.json"
    if _mc.exists():
        _cands = _json.loads(_mc.read_text())["candidates"]
        _have = set(genomes_with_rep["accession"].to_list())
        _mrows = []
        for c in _cands:
            if c["accession"] in _have:
                continue
            _mrows.append({
                "accession": c["accession"],
                "organism_name": c["species"],
                "organism_common_name": c["species"],
                "taxon_id": None,
                "assembly_level": c["assembly_level"],
                "contig_n50": c.get("contig_n50"), "scaffold_n50": c.get("scaffold_n50"),
                "total_length": c.get("total_length"),
                "annotation_status": "Annotated" if c.get("annotated") else None,
                "is_representative": False,
            })
        if _mrows:
            _schema = {c: genomes_with_rep.schema[c] for c in genomes_with_rep.columns}
            _fix = {k: _schema[k] for k in _mrows[0]}
            _mammals = pl.DataFrame(_mrows, schema_overrides=_fix, infer_schema_length=None)
            _mammals = _mammals.select(genomes_with_rep.columns).with_columns([
                pl.col("taxon_id").cast(pl.Int64),
                pl.col("total_length").cast(pl.Int64),
                pl.col("contig_n50").cast(pl.Int64),
                pl.col("scaffold_n50").cast(pl.Int64),
            ])
            genomes_with_rep = pl.concat([genomes_with_rep, _mammals], how="diagonal")
            print(f"  +{len(_mrows)} mammal assemblies")

    genomes_with_rep.write_parquet(DATA_DIR / "genomes.parquet")
    print(f"  Wrote genomes.parquet ({genomes_with_rep.height} total)")

    # Coverage summary
    coverage_summary = (
        species_table
        .group_by("order")
        .agg([
            pl.len().alias("total_species"),
            pl.col("has_genome").sum().alias("with_genome"),
            pl.col("has_annotation").sum().alias("with_annotation"),
            (pl.col("assembly_level") == "Chromosome").sum().alias("chromosome_level"),
        ])
        .sort("total_species", descending=True)
    )
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# coverage_summary.write_csv(DATA_DIR / "coverage_by_order.tsv", separator="\t")
    print(f"  Wrote coverage_by_order.tsv")


if __name__ == "__main__":
    main()
