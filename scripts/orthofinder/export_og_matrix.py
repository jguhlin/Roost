#!/usr/bin/env python3
"""Export the full orthogroup x species copy-count matrix as parquet.

GeneCount.tsv (40,494 OGs x 463 species) -> web/public/data/og_matrix.parquet
DENSE long format: one row per (og, of_id) for all 463 species including
copies=0 — DuckDB-WASM friendly (`WHERE og='OGxxx'` returns the full presence
vector with no missing-species handling). Species metadata joins client-side
via of_id against orthofinder/species_map.json.

Run:  pixi run python scripts/orthofinder/export_og_matrix.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OF_RUN = ROOT / "orthofinder" / "orthofinder_aves463_root16_20260928"
RESULTS = OF_RUN / "Results_Aves463_Root16"
SPECIES_JSON = ROOT / "web" / "public" / "data" / "orthofinder" / "species_map.json"
GENE_MAP = ROOT / "web" / "public" / "data" / "gene_orthogroups.json"
OUT = ROOT / "web" / "public" / "data" / "og_matrix.parquet"
SPECIES_STATS = ROOT / "web" / "public" / "data" / "orthofinder" / "species_og_stats.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--of-run", type=Path, default=OF_RUN)
    args = ap.parse_args()
    t0 = time.time()
    results = args.of_run / "Results_Aves463_Root16"

    smap = json.loads(SPECIES_JSON.read_text())
    smap.sort(key=lambda r: r["of_id"])

    import pandas as pd

    rows = []
    with open(results / "Orthogroups" / "Orthogroups.GeneCount.tsv") as f:
        header = f.readline().rstrip("\n").split("\t")[1:]
        labels = [h for h in header if h != "Total"]
        label_to_ofid = {lab: next(r["of_id"] for r in smap if r["label"] == lab)
                         for lab in set(labels)}
        for line in f:
            parts = line.rstrip("\n").split("\t")
            og = parts[0]
            for lab, v in zip(labels, parts[1:1 + len(labels)]):
                v = v.strip()
                if v:
                    rows.append((og, label_to_ofid[lab], int(v)))
    df = pd.DataFrame(rows, columns=["og", "of_id", "copies"])
    df["of_id"] = df["of_id"].astype("int16")
    df["copies"] = df["copies"].astype("int8")
    print(f"rows: {len(df):,} ({time.time()-t0:.0f}s)", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False, compression="zstd")
    size = OUT.stat().st_size / 1e6
    print(f"wrote {OUT} ({size:.1f} MB, {time.time()-t0:.0f}s)", file=sys.stderr)

    # Per-species orthogroup stats for species-page badges (keyed by sci name):
    # n_ogs = distinct OGs with >=1 protein, n_proteins = total proteins,
    # n_panel_ogs = how many of the 720 exported panel OGs the species appears in.
    pres = df[df["copies"] > 0]
    g = pres.groupby("of_id").agg(n_ogs=("og", "nunique"), n_proteins=("copies", "sum"))
    summary = OUT.parent / "orthogroups" / "og_summary.json"
    panel_ogs = set(json.loads(summary.read_text()).keys()) if summary.exists() else set()
    p = pres[pres["og"].isin(panel_ogs)].groupby("of_id").size()
    stats = {
        r["sci"]: {
            "of_id": r["of_id"],
            "n_ogs": int(g.loc[r["of_id"], "n_ogs"]),
            "n_proteins": int(g.loc[r["of_id"], "n_proteins"]),
            "n_panel_ogs": int(p.get(r["of_id"], 0)),
        }
        for r in smap if r["of_id"] in g.index
    }
    SPECIES_STATS.parent.mkdir(parents=True, exist_ok=True)
    SPECIES_STATS.write_text(json.dumps(stats))
    print(f"wrote {SPECIES_STATS.name} ({len(stats)} species, {time.time()-t0:.0f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
