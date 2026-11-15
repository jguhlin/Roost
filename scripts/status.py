#!/usr/bin/env python3
"""
Show current data status and coverage statistics.
"""

import polars as pl
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")


def file_info(path: Path) -> str:
    """Get file size and modification time."""
    if not path.exists():
        return "MISSING"
    size = path.stat().st_size
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 * 1024:
        size_str = f"{size/1024:.1f} KB"
    else:
        size_str = f"{size/1024/1024:.1f} MB"
    return f"{size_str}, {mtime:%Y-%m-%d %H:%M}"


def main():
    print("=" * 60)
    print("ROOST DATA STATUS")
    print("=" * 60)

    # Check required files
    print("\n[Data Files]")
    files = [
        ("Taxonomy", DATA_DIR / "aves_taxonomy.tsv"),
        ("Genomes (core)", DATA_DIR / "avian_genome_core.tsv"),
        ("Species table", DATA_DIR / "species_table.parquet"),
        ("Genomes table", DATA_DIR / "genomes.parquet"),
        ("APHIS raw", DATA_DIR / "raw" / "aphis_wild_birds.csv"),
        ("APHIS detections", DATA_DIR / "aphis_detections.parquet"),
        ("Coverage matrix", DATA_DIR / "coverage_matrix.parquet"),
    ]

    for name, path in files:
        status = file_info(path)
        symbol = "✓" if path.exists() else "✗"
        print(f"  {symbol} {name:20s} {status}")

    # Load and summarize coverage matrix if available
    cm_path = DATA_DIR / "coverage_matrix.parquet"
    if cm_path.exists():
        print("\n[Coverage Matrix Summary]")
        cm = pl.read_parquet(cm_path)

        total = len(cm)
        with_genome = cm.filter(pl.col("has_genome")).height
        with_annotation = cm.filter(pl.col("has_annotation")).height
        with_detection = cm.filter(pl.col("has_detection")).height
        with_expression = cm.filter(pl.col("has_expression")).height
        both = cm.filter(pl.col("has_genome") & pl.col("has_detection")).height

        print(f"  Total species:     {total:,}")
        print(f"  With genome:       {with_genome:,} ({100*with_genome/total:.1f}%)")
        print(f"  With annotation:   {with_annotation:,}")
        print(f"  With detection:    {with_detection:,}")
        print(f"  With expression:   {with_expression:,}")
        print(f"  Genome+Detection:  {both:,}")

        # Top orders
        print("\n[Top Orders by Detection]")
        order_stats = (
            cm.filter(pl.col("has_detection"))
            .group_by("order")
            .agg([
                pl.col("detection_count").sum().alias("detections"),
                pl.len().alias("species"),
            ])
            .sort("detections", descending=True)
            .head(5)
        )
        for row in order_stats.iter_rows(named=True):
            print(f"  {row['order']:20s} {row['detections']:,} detections, {row['species']} species")

    # Check for missing data
    print("\n[Data Gaps]")
    if cm_path.exists():
        gaps = cm.filter(pl.col("has_detection") & ~pl.col("has_genome"))
        if len(gaps) > 0:
            print(f"  {len(gaps)} species with detection but NO genome")
            top_gaps = gaps.sort("detection_count", descending=True).head(3)
            for row in top_gaps.iter_rows(named=True):
                print(f"    - {row['scientific_name']} ({row['detection_count']} detections)")
    else:
        print("  Coverage matrix not built yet")

    print("\n[Commands]")
    print("  pixi run build-all          # Full rebuild")
    print("  pixi run build-coverage-matrix  # Just matrix")
    print()


if __name__ == "__main__":
    main()
