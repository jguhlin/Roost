#!/usr/bin/env python3
"""Alias-aware annotation re-check for DDX58 (RIG-I) across screened birds.

The presence pipeline's Layer 0 (blast_presence.py) matches NCBI gene
records by exact official symbol — but many taxa record RIG-I under the
symbol RIGI (e.g. Anas platyrhynchos), so DDX58 is systematically
under-called as E5 and over-called as E4 (putative).

This script re-queries NCBI datasets for every screened H5N1-host bird
species (the Figure 2 panel-D set), matches DDX58's synonym set
(DDX58 / RIGI / RIG-I / RIG-1), and writes a cache consumed by
make_fig2.py:

    data/genes/ddx58_alias_annotation.json
      {species: {"matched": "RIGI", "gene_id": ..., "description": ...,
                 "n_records": 26115} | {"matched": null, "n_records": N} | null}

n_records = number of NCBI gene records for the taxon (>0 means the
species is annotated; RIG-I missed by that annotation when matched=null
but n_records>0 — the "BLAST + annotation exists but misses it" class).

Idempotent + incremental: existing entries are kept unless they lack the
n_records field (added v2).

Usage: pixi run python scripts/figures/check_ddx58_annotations.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/genes/ddx58_alias_annotation.json"
SYNONYMS = {"DDX58", "RIGI", "RIG-I", "RIG-1"}   # NCBI symbol variants

import polars as pl  # noqa: E402

def species_to_check() -> list[str]:
    pq = pl.read_parquet(ROOT / "data/genes/gene_presence_v2.parquet")
    dd = pq.filter(pl.col("gene_symbol") == "DDX58")
    spq = pl.read_parquet(ROOT / "web/public/data/species.parquet")
    order_of = dict(zip(spq["scientific_name"].to_list(),
                        spq["order"].to_list()))
    mammals = set(spq.filter(pl.col("class") == "Mammalia")["order"]
                  .unique().to_list())
    # bird species with a known order that have any DDX58 call
    need = sorted({r["species"] for r in dd.iter_rows(named=True)
                   if order_of.get(r["species"])
                   and order_of[r["species"]] not in mammals})
    return need

def query(species: str) -> dict | None:
    """NCBI datasets query for this taxon; return alias match or None."""
    try:
        r = subprocess.run(
            ["pixi", "run", "datasets", "summary", "gene", "taxon", species],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return None
        d = json.loads(r.stdout)
    except Exception:
        return None
    n_records = len(d.get("reports", []))
    for rep in d.get("reports", []):
        g = rep["gene"]
        sym = (g.get("symbol") or "").upper()
        if sym in SYNONYMS:
            return {"matched": sym, "gene_id": g.get("gene_id"),
                    "description": g.get("description", ""),
                    "n_records": n_records}
    return {"matched": None, "n_records": n_records}

def main() -> int:
    cache = json.loads(OUT.read_text()) if OUT.exists() else {}
    # v2: refresh entries lacking n_records
    stale = [s for s, v in cache.items()
             if not isinstance(v, dict) or "n_records" not in v]
    for s in stale:
        del cache[s]
    need = [s for s in species_to_check() if s not in cache]
    print(f"species in scope: {len(species_to_check())}; "
          f"cached: {len(cache)}; to query: {len(need)}")
    if need:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for i, (sp, res) in enumerate(zip(need, ex.map(query, need)), 1):
                cache[sp] = res
                if i % 50 == 0:
                    OUT.write_text(json.dumps(cache))
                    print(f"  {i}/{len(need)} (checkpoint)", flush=True)
        OUT.write_text(json.dumps(cache))
    hits = {s: v for s, v in cache.items() if isinstance(v, dict) and v.get("matched")}
    print(f"alias-annotated species: {len(hits)} of {len(cache)}")
    for s, v in sorted(hits.items())[:15]:
        print(f"  {s}: {v['matched']} — {v['description'][:50]}")
    ann = sum(1 for v in cache.values()
              if isinstance(v, dict) and v.get("n_records", 0) > 0)
    print(f"species with NCBI gene records (annotated): {ann} of {len(cache)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
