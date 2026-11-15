#!/usr/bin/env python3
"""
Gene panel definition and presence detection.

This module defines the core immune gene panel and provides methods
to detect gene presence across avian genomes using multiple strategies:
1. Existing annotations (for annotated genomes)
2. NCBI orthology data
3. BLAST (for high-priority genes only)
"""

import polars as pl
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import json

DATA_DIR = Path("data")
GENE_DIR = DATA_DIR / "genes"

# Gene panel definition
# Each gene has: symbol, name, category, tier, chicken IDs
GENE_PANEL = [
    # Tier 1: Host dependency factors (strongest evidence)
    {
        "symbol": "ANP32A",
        "name": "Acidic nuclear phosphoprotein 32A",
        "category": "Dependency",
        "tier": 1,
        "chicken_gene_id": 395532,
        "chicken_ensembl": "ENSGALG00000014113",
        "chicken_refseq": "NP_001292185.1",
        "notes": "Influenza polymerase host factor. Gene editing shows causal resistance.",
    },
    {
        "symbol": "ANP32B",
        "name": "Acidic nuclear phosphoprotein 32B",
        "category": "Dependency",
        "tier": 1,
        "chicken_gene_id": 418215,
        "chicken_ensembl": "ENSGALG00000002633",
        "chicken_refseq": "NP_001305365.1",
        "notes": "Escape route when ANP32A blocked.",
    },
    {
        "symbol": "ANP32E",
        "name": "Acidic nuclear phosphoprotein 32E",
        "category": "Dependency",
        "tier": 1,
        "chicken_gene_id": 420590,
        "chicken_ensembl": "ENSGALG00000006947",
        "chicken_refseq": "NP_001006544.1",
        "notes": "Triple knockout blocks viral growth.",
    },

    # Tier 1: Direct H5N1 evidence
    {
        "symbol": "IFIT5",
        "name": "Interferon-induced protein with tetratricopeptide repeats 5",
        "category": "Effector",
        "tier": 1,
        "chicken_gene_id": 424212,
        "chicken_ensembl": "ENSGALG00000016142",
        "chicken_refseq": "NP_001012934.1",
        "notes": "Transgenic chicks: reduced H5N1 disease.",
    },
    {
        "symbol": "IFITM1",
        "name": "Interferon-induced transmembrane protein 1",
        "category": "Effector",
        "tier": 1,
        "chicken_gene_id": 768632,
        "chicken_ensembl": "ENSGALG00000043895",
        "chicken_refseq": None,
        "notes": "Blocks viral entry/fusion. Complete protection at low dose.",
    },
    {
        "symbol": "IFITM3",
        "name": "Interferon-induced transmembrane protein 3",
        "category": "Effector",
        "tier": 1,
        "chicken_gene_id": 426913,
        "chicken_ensembl": "ENSGALG00000046389",
        "chicken_refseq": "NP_001032412.1",
        "notes": "Transgenic chicks: reduced shedding and pathology.",
    },

    # Tier 2: Viral sensing (RIG-I pathway)
    {
        "symbol": "DDX58",
        "name": "DExD/H-box helicase 58 (RIG-I)",
        "category": "Sensor",
        "tier": 2,
        "chicken_gene_id": None,  # ABSENT in chickens!
        "chicken_ensembl": None,
        "chicken_refseq": None,
        "duck_gene_id": 101801498,
        "duck_refseq": "XP_005017577.2",
        "notes": "Present in ducks, ABSENT in chickens. Key species difference.",
    },
    {
        "symbol": "RNF135",
        "name": "Ring finger protein 135 (RIPLET)",
        "category": "Sensor",
        "tier": 2,
        "chicken_gene_id": None,  # ABSENT in chickens!
        "chicken_ensembl": None,
        "chicken_refseq": None,
        "duck_refseq": "XP_005020182.1",
        "notes": "RIG-I activator. Lost with RIG-I in Galliformes.",
    },
    {
        "symbol": "IFIH1",
        "name": "Interferon-induced helicase C domain 1 (MDA5)",
        "category": "Sensor",
        "tier": 2,
        "chicken_gene_id": 418721,
        "chicken_ensembl": "ENSGALG00000003831",
        "chicken_refseq": "NP_001180400.1",
        "notes": "Primary sensor in chickens (compensates for RIG-I loss).",
    },
    {
        "symbol": "DHX58",
        "name": "DExH-box helicase 58 (LGP2)",
        "category": "Sensor",
        "tier": 2,
        "chicken_gene_id": 418016,
        "chicken_ensembl": "ENSGALG00000013851",
        "chicken_refseq": "NP_001025928.1",
        "notes": "Modulates MDA5 signaling.",
    },
    {
        "symbol": "MAVS",
        "name": "Mitochondrial antiviral signaling protein",
        "category": "Sensor",
        "tier": 2,
        "chicken_gene_id": 420254,
        "chicken_ensembl": "ENSGALG00000007653",
        "chicken_refseq": "NP_001012893.1",
        "notes": "Signal adaptor for RIG-I/MDA5.",
    },

    # Tier 2: Interferon signaling
    {
        "symbol": "IFNAR1",
        "name": "Interferon alpha/beta receptor subunit 1",
        "category": "Signaling",
        "tier": 2,
        "chicken_gene_id": 395665,
        "chicken_ensembl": "ENSGALG00000012495",
        "chicken_refseq": "NP_989941.1",
        "notes": "Knockout chickens: severely compromised antiviral state.",
    },
    {
        "symbol": "STAT1",
        "name": "Signal transducer and activator of transcription 1",
        "category": "Signaling",
        "tier": 2,
        "chicken_gene_id": 424044,
        "chicken_ensembl": "ENSGALG00000004456",
        "chicken_refseq": "NP_001012915.1",
        "notes": "Key transcription factor for interferon response.",
    },
    {
        "symbol": "STAT2",
        "name": "Signal transducer and activator of transcription 2",
        "category": "Signaling",
        "tier": 2,
        "chicken_gene_id": 424043,
        "chicken_ensembl": "ENSGALG00000004455",
        "chicken_refseq": "NP_001012916.1",
        "notes": "Partners with STAT1.",
    },

    # Tier 2: OAS pathway
    {
        "symbol": "OASL",
        "name": "2'-5'-oligoadenylate synthetase-like",
        "category": "Effector",
        "tier": 2,
        "chicken_gene_id": 419587,
        "chicken_ensembl": "ENSGALG00000010270",
        "chicken_refseq": "NP_001025778.1",
        "notes": "Early induction correlates with resistance.",
    },
    {
        "symbol": "RNASEL",
        "name": "Ribonuclease L",
        "category": "Effector",
        "tier": 2,
        "chicken_gene_id": 374110,
        "chicken_ensembl": "ENSGALG00000000877",
        "chicken_refseq": "NP_001001764.1",
        "notes": "Downstream effector of OAS pathway.",
    },

    # Tier 2: Tolerance candidate
    {
        "symbol": "PLAU",
        "name": "Plasminogen activator, urokinase",
        "category": "Tolerance",
        "tier": 2,
        "chicken_gene_id": 396061,
        "chicken_ensembl": "ENSGALG00000008050",
        "chicken_refseq": "NP_990398.1",
        "notes": "Downregulated in resistant chickens. Best tolerance candidate.",
    },

    # Tier 3: MX1 (controversial)
    {
        "symbol": "MX1",
        "name": "MX dynamin-like GTPase 1",
        "category": "Effector",
        "tier": 3,
        "chicken_gene_id": 396434,
        "chicken_ensembl": "ENSGALG00000015385",
        "chicken_refseq": "NP_990770.1",
        "notes": "S631N allele inconsistent across studies. Do not treat as validated.",
    },
]


@dataclass
class GeneInfo:
    """Information about a gene in the panel."""
    symbol: str
    name: str
    category: str
    tier: int
    chicken_gene_id: Optional[int]
    chicken_ensembl: Optional[str]
    chicken_refseq: Optional[str]
    notes: str


def get_gene_panel() -> list[dict]:
    """Return the full gene panel as a list of dicts."""
    return GENE_PANEL


def get_gene_panel_df() -> pl.DataFrame:
    """Return the gene panel as a polars DataFrame."""
    return pl.DataFrame(GENE_PANEL)


def save_gene_panel():
    """Save the gene panel to files."""
    GENE_DIR.mkdir(exist_ok=True)

    # Save as JSON
    with open(GENE_DIR / "gene_panel.json", "w") as f:
        json.dump(GENE_PANEL, f, indent=2)

    # Save as TSV
    df = get_gene_panel_df()
    df.write_csv(GENE_DIR / "gene_panel.tsv", separator="\t")

    print(f"Saved {len(GENE_PANEL)} genes to {GENE_DIR}/")
    print(f"  - gene_panel.json")
    print(f"  - gene_panel.tsv")


def summarize_panel():
    """Print summary of the gene panel."""
    df = get_gene_panel_df()

    print("=" * 60)
    print("GENE PANEL SUMMARY")
    print("=" * 60)

    print(f"\nTotal genes: {len(df)}")

    print("\nBy tier:")
    for tier in sorted(df["tier"].unique().to_list()):
        count = df.filter(pl.col("tier") == tier).height
        print(f"  Tier {tier}: {count} genes")

    print("\nBy category:")
    for cat in df["category"].unique().sort().to_list():
        count = df.filter(pl.col("category") == cat).height
        print(f"  {cat}: {count}")

    print("\nKey genes absent in chicken (present in duck):")
    absent = df.filter(pl.col("chicken_gene_id").is_null())
    for row in absent.iter_rows(named=True):
        print(f"  {row['symbol']}: {row['notes']}")


def main():
    """Main entry point."""
    summarize_panel()
    save_gene_panel()


if __name__ == "__main__":
    main()
