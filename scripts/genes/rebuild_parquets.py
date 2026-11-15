#!/usr/bin/env python3
"""Rebuild the gene-presence parquet family from the canonical jsonl.

gene_presence_v2.jsonl is the append-only source of truth (BLAST runs,
manual purges all write it). These parquets are derived views and go
stale whenever the jsonl is edited outside a blast run:

  gene_presence_v2.parquet       — row-per-call mirror of the jsonl
  gene_presence_calls.parquet    — same rows, v1-era name (coverage matrix)
  gene_presence_matrix.parquet   — species x gene status matrix

Usage: pixi run python scripts/genes/rebuild_parquets.py
"""

import json
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent.parent
GENE_DIR = ROOT / "data" / "genes"
CALLS = GENE_DIR / "gene_presence_v2.jsonl"


def main() -> None:
    rows = [json.loads(l) for l in CALLS.read_text().splitlines() if l.strip()]
    df = pl.DataFrame(rows, infer_schema_length=None)
    df.write_parquet(GENE_DIR / "gene_presence_v2.parquet")
    df.write_parquet(GENE_DIR / "gene_presence_calls.parquet")
    print(f"calls: {df.height} rows, {df['gene_symbol'].n_unique()} genes, "
          f"{df['species'].n_unique()} species")

    matrix = df.pivot(
        on="gene_symbol", index=["taxon_id", "species"], values="search_status",
        aggregate_function="first",
    ).sort("species")
    matrix.write_parquet(GENE_DIR / "gene_presence_matrix.parquet")
    print(f"matrix: {matrix.height} species x {matrix.width - 1} genes")


if __name__ == "__main__":
    main()
