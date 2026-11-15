#!/usr/bin/env python3
"""
Download all required data sources.
"""

import subprocess
import sys
from pathlib import Path

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"


def run(cmd: str, desc: str) -> bool:
    """Run a shell command with description."""
    print(f"\n[{desc}]")
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode})")
        return False
    return True


def download_taxonomy() -> bool:
    """Download NCBI taxonomy dump."""
    taxonomy_dir = DATA_DIR / "taxonomy"
    if taxonomy_dir.exists() and (taxonomy_dir / "nodes.dmp").exists():
        print("\n[NCBI Taxonomy] Already exists, skipping")
        return True

    DATA_DIR.mkdir(exist_ok=True)
    taxonomy_dir.mkdir(exist_ok=True)

    if not run(
        f"curl -o {DATA_DIR}/taxdump.tar.gz https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz",
        "Downloading NCBI taxonomy"
    ):
        return False

    return run(
        f"tar -xzf {DATA_DIR}/taxdump.tar.gz -C {taxonomy_dir}",
        "Extracting taxonomy"
    )


def download_genomes() -> bool:
    """Download NCBI Aves genome metadata."""
    genome_zip = DATA_DIR / "avian_genomes.zip"
    if genome_zip.exists():
        print("\n[NCBI Genomes] Already exists, skipping")
        return True

    DATA_DIR.mkdir(exist_ok=True)

    return run(
        f'pixi run datasets download genome taxon "Aves" --dehydrated --filename {genome_zip}',
        "Downloading Aves genome metadata"
    )


def download_aphis() -> bool:
    """Download APHIS wild bird detection data."""
    aphis_file = RAW_DIR / "aphis_wild_birds.csv"
    RAW_DIR.mkdir(exist_ok=True)

    # Always re-download APHIS (it updates frequently)
    return run(
        f"curl -o {aphis_file} https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv",
        "Downloading APHIS wild bird detections"
    )


def main():
    print("=" * 60)
    print("ROOST DATA DOWNLOAD")
    print("=" * 60)

    success = True

    if not download_taxonomy():
        success = False

    if not download_genomes():
        success = False

    if not download_aphis():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("All downloads complete!")
        print("\nNext: pixi run build-all")
    else:
        print("Some downloads failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
