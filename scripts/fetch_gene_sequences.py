#!/usr/bin/env python3
"""
Fetch reference protein sequences for gene panel from NCBI.
"""

import json
import subprocess
from pathlib import Path
import time

DATA_DIR = Path("data")
GENE_DIR = DATA_DIR / "genes"
SEQ_DIR = GENE_DIR / "sequences"


def load_gene_panel() -> list[dict]:
    """Load gene panel from JSON."""
    with open(GENE_DIR / "gene_panel.json") as f:
        return json.load(f)


def fetch_protein_sequence(accession: str, output_file: Path) -> bool:
    """Fetch a protein sequence from NCBI using efetch."""
    if output_file.exists():
        print(f"  {accession}: already exists")
        return True

    cmd = [
        "curl", "-s",
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=protein&id={accession}&rettype=fasta&retmode=text"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.startswith(">"):
            output_file.write_text(result.stdout)
            print(f"  {accession}: downloaded")
            return True
        else:
            print(f"  {accession}: failed - {result.stderr or 'no data'}")
            return False
    except Exception as e:
        print(f"  {accession}: error - {e}")
        return False


def main():
    print("=" * 60)
    print("FETCHING GENE PANEL REFERENCE SEQUENCES")
    print("=" * 60)

    SEQ_DIR.mkdir(parents=True, exist_ok=True)

    panel = load_gene_panel()

    # Collect all accessions to fetch
    to_fetch = []
    for gene in panel:
        symbol = gene["symbol"]

        # Try chicken RefSeq first
        if gene.get("chicken_refseq"):
            to_fetch.append((symbol, gene["chicken_refseq"], "chicken"))

        # For RIG-I and RNF135, use duck sequences
        if gene.get("duck_refseq"):
            to_fetch.append((symbol, gene["duck_refseq"], "duck"))

    print(f"\nFetching {len(to_fetch)} sequences...")

    success = 0
    for symbol, accession, species in to_fetch:
        output_file = SEQ_DIR / f"{symbol}_{species}.fasta"
        if fetch_protein_sequence(accession, output_file):
            success += 1
        time.sleep(0.5)  # Be nice to NCBI

    print(f"\nDownloaded {success}/{len(to_fetch)} sequences to {SEQ_DIR}/")

    # Create combined FASTA for BLAST database
    print("\nCreating combined reference FASTA...")
    combined = SEQ_DIR / "gene_panel_references.fasta"
    with open(combined, "w") as out:
        for fasta_file in SEQ_DIR.glob("*.fasta"):
            if fasta_file.name == "gene_panel_references.fasta":
                continue
            content = fasta_file.read_text()
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")

    print(f"  Created {combined}")


if __name__ == "__main__":
    main()
