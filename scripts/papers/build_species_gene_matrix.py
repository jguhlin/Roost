#!/usr/bin/env python3
"""
Build species-gene interaction matrix for web display.
Shows which genes have been studied in which species based on paper evidence.
"""

import json
from pathlib import Path
from collections import defaultdict

ROOST_DIR = Path(__file__).parent.parent.parent
SPECIES_PAPERS = ROOST_DIR / "web" / "public" / "data" / "species_papers.json"
GENES_JSON = ROOST_DIR / "web" / "public" / "data" / "genes.json"
OUTPUT_FILE = ROOST_DIR / "web" / "public" / "data" / "species_gene_matrix.json"

# Key genes for the matrix (Tier 1 and some Tier 2)
KEY_GENES = [
    "DDX58",   # RIG-I
    "IFIH1",   # MDA5
    "MAVS",    # MAVS
    "OAS",     # OAS
    "IFIT5",   # IFIT5
    "MX1",     # MX1
    "IRF3",    # IRF3
    "IRF7",    # IRF7
    "ANP32A",  # ANP32A
    "ANP32B",  # ANP32B
    "TRIM25",  # TRIM25
    "NS1",     # NS1 (viral)
    "PB2",     # PB2 (viral)
]

# Species susceptibility classifications from the literature
SPECIES_SUSCEPTIBILITY = {
    "Chicken": {"class": "highly_susceptible", "evidence": "RIG-I absent, high mortality"},
    "Turkey": {"class": "highly_susceptible", "evidence": "Similar to chicken"},
    "Duck": {"class": "tolerant", "evidence": "RIG-I present, reservoir species"},
    "Mallard": {"class": "tolerant", "evidence": "RIG-I present, reservoir species"},
    "Mute Swan": {"class": "highly_susceptible", "evidence": "98% mortality rate in outbreak data"},
    "Northern Gannet": {"class": "highly_susceptible", "evidence": "Major die-offs 2021-2024"},
    "Great Skua": {"class": "highly_susceptible", "evidence": "Severe declines, colonial breeder"},
    "Bald Eagle": {"class": "highly_susceptible", "evidence": ">99% mortality in outbreak data"},
    "Peregrine Falcon": {"class": "susceptible", "evidence": "Low OAS/IFIT5 upregulation"},
    "Golden Eagle": {"class": "susceptible", "evidence": "Low OAS/IFIT5 upregulation"},
    "Rock Pigeon": {"class": "resistant", "evidence": "HIGH OAS/IFIT5 upregulation"},
    "Hooded Crane": {"class": "resistant", "evidence": "HIGH OAS/IFIT5 upregulation"},
    "African Penguin": {"class": "susceptible", "evidence": "Documented mortality events"},
    "Gentoo Penguin": {"class": "susceptible", "evidence": "Antarctic die-offs 2023-2024"},
    "American Crow": {"class": "susceptible", "evidence": "Significant mortality in outbreaks"},
    "Sandwich Tern": {"class": "susceptible", "evidence": "Colony die-offs"},
    "Common Murre": {"class": "susceptible", "evidence": "Documented mass mortality"},
}

def main():
    # Load species papers data
    with open(SPECIES_PAPERS) as f:
        species_data = json.load(f)

    # Load genes data
    with open(GENES_JSON) as f:
        genes_data = json.load(f)

    # Build matrix
    matrix = {}

    for sp_name, sp_info in species_data["species"].items():
        genes_mentioned = sp_info.get("genes_mentioned", {})

        # Filter to key genes and build row
        gene_row = {}
        for gene in KEY_GENES:
            count = genes_mentioned.get(gene, 0)
            gene_row[gene] = {
                "papers": count,
                "status": "studied" if count > 0 else "unknown"
            }

        # Add susceptibility info
        susc = SPECIES_SUSCEPTIBILITY.get(sp_name, {"class": "unknown", "evidence": ""})

        matrix[sp_name] = {
            "db_id": sp_info.get("db_id"),
            "paper_count": sp_info.get("paper_count", 0),
            "total_mentions": sp_info.get("total_mentions", 0),
            "susceptibility_class": susc["class"],
            "susceptibility_evidence": susc["evidence"],
            "genes": gene_row,
        }

    # Sort by paper count
    matrix_sorted = dict(sorted(matrix.items(), key=lambda x: x[1]["paper_count"], reverse=True))

    # Build summary statistics
    gene_coverage = {}
    for gene in KEY_GENES:
        species_with_gene = sum(1 for sp in matrix.values() if sp["genes"][gene]["papers"] > 0)
        gene_coverage[gene] = species_with_gene

    # Build output
    output = {
        "generated": "2026-08-26",
        "total_species": len(matrix_sorted),
        "key_genes": KEY_GENES,
        "gene_coverage": gene_coverage,
        "susceptibility_classes": {
            "highly_susceptible": sum(1 for sp in matrix.values() if sp["susceptibility_class"] == "highly_susceptible"),
            "susceptible": sum(1 for sp in matrix.values() if sp["susceptibility_class"] == "susceptible"),
            "tolerant": sum(1 for sp in matrix.values() if sp["susceptibility_class"] == "tolerant"),
            "resistant": sum(1 for sp in matrix.values() if sp["susceptibility_class"] == "resistant"),
            "unknown": sum(1 for sp in matrix.values() if sp["susceptibility_class"] == "unknown"),
        },
        "species": matrix_sorted,
    }

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Created species-gene matrix with {len(matrix_sorted)} species")
    print(f"Gene coverage:")
    for gene, count in sorted(gene_coverage.items(), key=lambda x: x[1], reverse=True):
        print(f"  {gene}: {count} species")

    print(f"\nSusceptibility distribution:")
    for cls, count in output["susceptibility_classes"].items():
        print(f"  {cls}: {count} species")

    return output

if __name__ == "__main__":
    main()
