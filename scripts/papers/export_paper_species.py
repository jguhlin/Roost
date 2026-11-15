#!/usr/bin/env python3
"""Export paper -> mentioned-species index from typed claims.

Feeds the species-aware pass on the Papers page: q=kelp gull matches the
23 papers whose claims name Larus dominicanus, not just the 3 with it in
title/summary. Scientific names + common names (where known).

Output: web/public/data/paper_species_mentions.json
  {paper_id: [{"sci": ..., "com": ...}, ...]}
Usage: pixi run python scripts/papers/export_paper_species.py
"""
import json
from collections import defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web/public/data/paper_species_mentions.json"


def J(x):
    try:
        return json.loads(x) if isinstance(x, str) else (x or [])
    except Exception:
        return []


def main():
    com_of = {}
    try:
        for r in json.load(open(ROOT / "web/public/data/species_index.json")):
            if r.get("com"):
                com_of[r["sci"]] = r["com"]
    except Exception:
        pass
    by_paper = defaultdict(set)
    for r in pl.read_parquet(ROOT / "data/papers/typed_claims.parquet").iter_rows(named=True):
        for s in J(r["species"]):
            if isinstance(s, str) and " " in s:
                by_paper[r["paper_id"]].add(s)
    out = {pid: sorted(({"sci": s, "com": com_of.get(s, "")} for s in ss),
                       key=lambda d: d["sci"])
           for pid, ss in by_paper.items()}
    OUT.write_text(json.dumps(out))
    n = sum(len(v) for v in out.values())
    print(f"paper_species_mentions.json: {len(out)} papers, {n} species links")


if __name__ == "__main__":
    main()
