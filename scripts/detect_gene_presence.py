#!/usr/bin/env python3
"""
Detect gene presence across avian genomes using multiple strategies.

Strategy 1: NCBI Ortholog API (for annotated genomes)
Strategy 2: NCBI Gene database queries
Strategy 3: BLAST (future, for high-priority unannotated genomes)

Each gene call includes provenance tracking:
- method: how was presence determined
- confidence: high/medium/low
- evidence: supporting data (accession, e-value, etc.)
- assembly_quality: affects interpretation of "absent"
"""

import json
import subprocess
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
import polars as pl

DATA_DIR = Path("data")
GENE_DIR = DATA_DIR / "genes"


@dataclass
class GenePresenceCall:
    """A single gene presence call with full provenance."""
    taxon_id: int
    gene_symbol: str
    status: str  # Present, Absent, Partial, Unknown
    confidence: str  # High, Medium, Low
    method: str  # annotation, ortholog_api, blast, inferred
    evidence: dict  # Method-specific evidence
    assembly_accession: Optional[str]
    assembly_level: Optional[str]
    annotation_status: Optional[str]
    call_date: str
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def load_gene_panel() -> list[dict]:
    """Load gene panel definition."""
    with open(GENE_DIR / "gene_panel.json") as f:
        return json.load(f)


def load_species_table() -> pl.DataFrame:
    """Load species table with genome info."""
    return pl.read_parquet(DATA_DIR / "species_table.parquet")


def query_ncbi_gene(gene_id: int, taxon_id: int) -> Optional[dict]:
    """
    Query NCBI Gene database for ortholog in a specific taxon.
    Returns gene info if found, None otherwise.
    """
    # Use NCBI datasets CLI to query gene info
    cmd = [
        "datasets", "summary", "gene", "gene-id", str(gene_id),
        "--taxon", str(taxon_id),
        "--as-json-lines"
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    return None


def query_ncbi_gene_symbol(gene_symbol: str, taxon_id: int) -> Optional[dict]:
    """
    Query NCBI for a gene symbol in a specific taxon.
    Uses direct symbol lookup (more reliable than ortholog queries).

    Returns gene info dict if found, None otherwise.
    """
    cmd = [
        "datasets", "summary", "gene", "symbol", gene_symbol,
        "--taxon", str(taxon_id),
        "--as-json-lines"
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            # Parse the JSON line - it's a single gene record
            data = json.loads(result.stdout.strip())
            # Check if this is a valid gene record (has gene_id)
            if data.get("gene_id"):
                return data
    except Exception as e:
        pass
    return None


# Common gene symbol aliases (primary → alternatives)
GENE_ALIASES = {
    "DDX58": ["RIG-I", "RIGI", "RIG1"],
    "RNF135": ["RIPLET"],
    "IFIH1": ["MDA5", "MDA-5"],
    "DHX58": ["LGP2"],
    "OASL": ["OAS-like", "OASL1"],
    "MX1": ["Mx", "Mx1"],
}


def query_gene_with_aliases(gene_symbol: str, taxon_id: int) -> Optional[dict]:
    """
    Query NCBI for a gene, trying primary symbol and known aliases.
    """
    # Try primary symbol first
    result = query_ncbi_gene_symbol(gene_symbol, taxon_id)
    if result:
        return result

    # Try aliases if available
    aliases = GENE_ALIASES.get(gene_symbol, [])
    for alias in aliases:
        result = query_ncbi_gene_symbol(alias, taxon_id)
        if result:
            return result

    return None


def detect_gene_in_species(
    gene: dict,
    taxon_id: int,
    assembly_info: dict
) -> GenePresenceCall:
    """
    Detect whether a gene is present in a species.

    Returns a GenePresenceCall with full provenance.
    """
    gene_symbol = gene["symbol"]
    chicken_gene_id = gene.get("chicken_gene_id")
    assembly_accession = assembly_info.get("accession")
    assembly_level = assembly_info.get("assembly_level")
    annotation_status = assembly_info.get("annotation_status")
    call_date = datetime.now().isoformat()

    # Special case: genes known to be absent in certain lineages
    if gene_symbol == "DDX58" and is_galliform(taxon_id):
        return GenePresenceCall(
            taxon_id=taxon_id,
            gene_symbol=gene_symbol,
            status="Absent",
            confidence="High",
            method="inferred",
            evidence={"reason": "DDX58/RIG-I lost in Galliformes lineage"},
            assembly_accession=assembly_accession,
            assembly_level=assembly_level,
            annotation_status=annotation_status,
            call_date=call_date,
            notes="RIG-I absence in Galliformes is well-established"
        )

    if gene_symbol == "RNF135" and is_galliform(taxon_id):
        return GenePresenceCall(
            taxon_id=taxon_id,
            gene_symbol=gene_symbol,
            status="Absent",
            confidence="High",
            method="inferred",
            evidence={"reason": "RNF135/RIPLET lost with RIG-I in Galliformes"},
            assembly_accession=assembly_accession,
            assembly_level=assembly_level,
            annotation_status=annotation_status,
            call_date=call_date,
            notes="RIPLET absence in Galliformes co-occurs with RIG-I loss"
        )

    # For annotated genomes, try direct gene symbol query (with aliases)
    if annotation_status and annotation_status != "":
        gene_result = query_gene_with_aliases(gene_symbol, taxon_id)
        if gene_result:
            return GenePresenceCall(
                taxon_id=taxon_id,
                gene_symbol=gene_symbol,
                status="Present",
                confidence="High",
                method="ncbi_gene_db",
                evidence={
                    "ncbi_gene_id": gene_result.get("gene_id"),
                    "symbol": gene_result.get("symbol"),
                    "description": gene_result.get("description"),
                    "chromosomes": gene_result.get("chromosomes"),
                },
                assembly_accession=assembly_accession,
                assembly_level=assembly_level,
                annotation_status=annotation_status,
                call_date=call_date,
            )

        # Gene not found in annotated genome
        # Confidence depends on assembly quality
        if assembly_level in ["Chromosome", "Complete Genome"]:
            confidence = "High"
            status = "Absent"
        elif assembly_level == "Scaffold":
            confidence = "Medium"
            status = "Absent"
        else:
            confidence = "Low"
            status = "Unknown"

        return GenePresenceCall(
            taxon_id=taxon_id,
            gene_symbol=gene_symbol,
            status=status,
            confidence=confidence,
            method="annotation",
            evidence={"searched": True, "found": False},
            assembly_accession=assembly_accession,
            assembly_level=assembly_level,
            annotation_status=annotation_status,
            call_date=call_date,
            notes=f"Not found in {annotation_status} annotation"
        )

    # Unannotated genome - can't determine presence from annotation
    return GenePresenceCall(
        taxon_id=taxon_id,
        gene_symbol=gene_symbol,
        status="Unknown",
        confidence="Low",
        method="none",
        evidence={"reason": "No annotation available"},
        assembly_accession=assembly_accession,
        assembly_level=assembly_level,
        annotation_status=annotation_status,
        call_date=call_date,
        notes="Genome not annotated; would require BLAST"
    )


# Cache for Galliformes taxon IDs
_galliform_cache: set = set()


def is_galliform(taxon_id: int) -> bool:
    """Check if a taxon is in Galliformes order."""
    global _galliform_cache

    if not _galliform_cache:
        # Load from species table
        species = load_species_table()
        galliformes = species.filter(pl.col("order") == "Galliformes")
        _galliform_cache = set(galliformes["taxon_id"].to_list())

    return taxon_id in _galliform_cache


def run_detection(
    species_limit: Optional[int] = None,
    genes_limit: Optional[int] = None,
    annotated_only: bool = True
) -> list[GenePresenceCall]:
    """
    Run gene presence detection across species.

    Args:
        species_limit: Max species to process (for testing)
        genes_limit: Max genes to process (for testing)
        annotated_only: Only process annotated genomes
    """
    gene_panel = load_gene_panel()
    species_table = load_species_table()

    # Filter to species with genomes
    species_with_genome = species_table.filter(pl.col("has_genome"))

    if annotated_only:
        species_with_genome = species_with_genome.filter(
            pl.col("has_annotation")
        )

    if species_limit:
        species_with_genome = species_with_genome.head(species_limit)

    if genes_limit:
        gene_panel = gene_panel[:genes_limit]

    print(f"Processing {len(species_with_genome)} species × {len(gene_panel)} genes", flush=True)

    calls = []
    total = len(species_with_genome) * len(gene_panel)
    processed = 0

    for row in species_with_genome.iter_rows(named=True):
        taxon_id = row["taxon_id"]
        assembly_info = {
            "accession": row.get("accession"),
            "assembly_level": row.get("assembly_level"),
            "annotation_status": row.get("annotation_status") if row.get("has_annotation") else None,
        }

        for gene in gene_panel:
            call = detect_gene_in_species(gene, taxon_id, assembly_info)
            calls.append(call)
            processed += 1

            if processed % 100 == 0:
                print(f"  Processed {processed}/{total} ({100*processed/total:.1f}%)", flush=True)

            # Rate limit NCBI queries
            time.sleep(0.1)

    return calls


def save_calls(calls: list[GenePresenceCall], output_dir: Path = GENE_DIR):
    """Save gene presence calls to files with full provenance."""
    output_dir.mkdir(exist_ok=True)

    # Convert to records
    records = [call.to_dict() for call in calls]

    # Save as JSON (full provenance)
    with open(output_dir / "gene_presence_calls.json", "w") as f:
        json.dump(records, f, indent=2)

    # Save as parquet (for analysis)
    df = pl.DataFrame(records)

    # Flatten evidence dict for tabular format
    df = df.with_columns([
        pl.col("evidence").map_elements(
            lambda x: json.dumps(x) if x else None,
            return_dtype=pl.Utf8
        ).alias("evidence_json")
    ]).drop("evidence")

    df.write_parquet(output_dir / "gene_presence_calls.parquet")

    # Create summary matrix (species × gene)
    matrix = df.pivot(
        index="taxon_id",
        on="gene_symbol",
        values="status"
    )
    matrix.write_parquet(output_dir / "gene_presence_matrix.parquet")

    print(f"\nSaved to {output_dir}/:")
    print(f"  - gene_presence_calls.json ({len(records)} calls)")
    print(f"  - gene_presence_calls.parquet")
    print(f"  - gene_presence_matrix.parquet")


def summarize_calls(calls: list[GenePresenceCall]):
    """Print summary of gene presence calls."""
    df = pl.DataFrame([c.to_dict() for c in calls])

    print("\n" + "=" * 60)
    print("GENE PRESENCE DETECTION SUMMARY")
    print("=" * 60)

    print(f"\nTotal calls: {len(calls)}")

    print("\nBy status:")
    status_counts = df.group_by("status").len().sort("len", descending=True)
    for row in status_counts.iter_rows(named=True):
        print(f"  {row['status']:10s} {row['len']:5d}")

    print("\nBy confidence:")
    conf_counts = df.group_by("confidence").len().sort("len", descending=True)
    for row in conf_counts.iter_rows(named=True):
        print(f"  {row['confidence']:10s} {row['len']:5d}")

    print("\nBy method:")
    method_counts = df.group_by("method").len().sort("len", descending=True)
    for row in method_counts.iter_rows(named=True):
        print(f"  {row['method']:15s} {row['len']:5d}")

    # Gene-level summary
    print("\nBy gene (Present count):")
    gene_present = (
        df.filter(pl.col("status") == "Present")
        .group_by("gene_symbol")
        .len()
        .sort("len", descending=True)
    )
    for row in gene_present.iter_rows(named=True):
        print(f"  {row['gene_symbol']:12s} {row['len']:3d} species")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect gene presence in avian genomes")
    parser.add_argument("--species-limit", type=int, help="Limit species for testing")
    parser.add_argument("--genes-limit", type=int, help="Limit genes for testing")
    parser.add_argument("--all-genomes", action="store_true", help="Include unannotated genomes")
    args = parser.parse_args()

    print("=" * 60)
    print("GENE PRESENCE DETECTION")
    print("=" * 60)

    calls = run_detection(
        species_limit=args.species_limit,
        genes_limit=args.genes_limit,
        annotated_only=not args.all_genomes
    )

    summarize_calls(calls)
    save_calls(calls)


if __name__ == "__main__":
    main()
