#!/usr/bin/env python3
"""Data ↔ literature bridges (landscape Stage 6d, deterministic).

Two joins between the project's surveillance/genomics data and the paper
corpus, surfacing checkable gaps instead of only synthesized ones:

  1. SPECIES: species.parquet + susceptibility.parquet (data side) vs
     paper_species_traits.parquet (literature side)
       - lit_no_surveillance: literature reports a species, zero field detections
       - data_no_literature: detections + high susceptibility, no literature traits
       - outcome_mismatches: literature mortality vs low modeled susceptibility
  2. GENES: gene_catalogue key genes (panel) vs gene_evidence/*.json (lit)
       - key_gene_thin_evidence: panel key genes with <2 papers
       - lit_rich_not_key: well-studied genes absent from the key panel

Output: web/public/data/data_lit_bridges.json
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "data" / "data_lit_bridges.json"

MORTALITY = re.compile(r"dead|mortal|death|euthan|lethal", re.I)


def norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def bridge_species() -> dict:
    sp = pd.read_parquet(ROOT / "web/public/data/species.parquet")
    sus = pd.read_parquet(ROOT / "web/public/data/susceptibility.parquet")
    traits = pd.read_parquet(ROOT / "data/papers/paper_species_traits.parquet")

    sp = sp.merge(sus, on="scientific_name", how="left")
    sp["n"] = sp["scientific_name"].map(norm)
    surv = sp.set_index("n")

    traits["n"] = traits["species_norm"].map(norm) if "species_norm" in traits \
        else traits["name"].map(norm)
    traits = traits[~traits["n"].isin({"nan", "none", "", "unknown"})]
    lit_species = traits.dropna(subset=["n"]).groupby("n").agg(
        n_papers=("paper_id", "nunique"),
        mortality_reports=("outcome", lambda s: int(sum(bool(MORTALITY.search(str(x))) for x in s))),
    )

    joined = surv.join(lit_species, how="outer")
    # detection_records = surveillance record count (the honest "detections"
    # metric); raw detection_count sums animals affected (flock sizes) and
    # would distort the ≥5-detections threshold and the display ranking.
    det_col = "detection_records" if "detection_records" in joined.columns else "detection_count"
    joined = joined.rename(columns={det_col: "det_records"})
    has_surv = joined["det_records"].notna()
    has_lit = joined["n_papers"].notna()

    lit_only = joined[has_lit & ~has_surv].sort_values("n_papers", ascending=False)
    data_only = joined[has_surv & ~has_lit & (joined["det_records"] >= 5) &
                       (joined["susceptibility_score"] >= 3)].sort_values(
        ["det_records", "susceptibility_score"], ascending=False)
    mism = joined[has_surv & has_lit & (joined["mortality_reports"] > 0) &
                  (joined["susceptibility_score"] <= 2)]

    def rows(df, cols):
        return df.head(25).reset_index()[cols].to_dict("records")

    return {
        "n_surveillance_species": int(has_surv.sum()),
        "n_literature_species": int(has_lit.sum()),
        "n_overlap": int((has_surv & has_lit).sum()),
        "lit_no_surveillance": rows(lit_only, ["n", "n_papers", "mortality_reports"]),
        "data_no_literature": rows(
            data_only, ["scientific_name", "common_name", "det_records",
                        "susceptibility_score", "susceptibility_class"]),
        "outcome_mismatches": rows(
            mism, ["scientific_name", "det_records", "susceptibility_score",
                   "mortality_reports", "n_papers"]),
        "note": "lit_no_surveillance names are normalized scientific names "
                "(species_norm); data_no_literature requires ≥5 detections and "
                "susceptibility_score ≥3",
    }


def bridge_genes() -> dict:
    gc = json.loads((ROOT / "web/public/data/gene_catalogue.json").read_text())
    key_genes = gc.get("key_genes", {})

    lit_counts: dict[str, int] = {}
    for f in (ROOT / "web/public/data/gene_evidence").glob("*.json"):
        try:
            g = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        gene = f.stem
        n = g.get("n_papers", 0) or len(g.get("papers", []))
        lit_counts[gene.upper()] = max(lit_counts.get(gene.upper(), 0), int(n or 0))

    thin = []
    for gene, meta in key_genes.items():
        n = lit_counts.get(gene.upper(), 0)
        if n < 2:
            thin.append({"gene": gene, "importance": meta.get("importance", ""),
                         "n_papers": n,
                         "function": (meta.get("function") or "")[:120]})
    thin.sort(key=lambda x: x["n_papers"])

    rich_not_key = sorted(
        ({"gene": g, "n_papers": n} for g, n in lit_counts.items()
         if g not in key_genes and n >= 5),
        key=lambda x: -x["n_papers"])

    return {
        "n_key_genes": len(key_genes),
        "n_genes_with_evidence": len(lit_counts),
        "key_gene_thin_evidence": thin[:20],
        "lit_rich_not_key": rich_not_key[:20],
        "note": "thin = key panel genes with <2 evidence papers; rich-not-key "
                "= genes with ≥5 papers absent from the key HOST panel "
                "(viral segments like HA/PB2 dominate this list — host-panel "
                "expansion candidates are the remainder)",
    }


def main() -> int:
    payload = {
        "meta": {"generated": datetime.now(timezone.utc).isoformat(),
                 "method": "deterministic joins — see script docstring"},
        "species": bridge_species(),
        "genes": bridge_genes(),
    }
    # pandas emits NaN/Infinity literals which are INVALID JSON for browsers —
    # scrub to null before writing
    def scrub(o):
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items()}
        if isinstance(o, list):
            return [scrub(v) for v in o]
        if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
            return None
        return o
    payload = scrub(payload)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False, allow_nan=False) + "\n",
                   encoding="utf-8")
    s, g = payload["species"], payload["genes"]
    print(f"bridges → {OUT.relative_to(ROOT)}")
    print(f"  species: {s['n_overlap']} overlapped | "
          f"{len(s['lit_no_surveillance'])} lit-only (top-listed) | "
          f"{len(s['data_no_literature'])} data-only | "
          f"{len(s['outcome_mismatches'])} outcome mismatches")
    print(f"  genes: {g['n_key_genes']} key | {len(g['key_gene_thin_evidence'])} "
          f"thin-evidence | {len(g['lit_rich_not_key'])} rich-not-key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
