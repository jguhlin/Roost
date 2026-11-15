#!/usr/bin/env python3
"""Consolidate every deterministic per-paper output into one record each.

Internal research database (NOT web-served): data/papers/records/{id}.json
One file per paper — the single record an agent (paper_steward.py) or human
reads to see everything we know deterministically:

  metadata      papers.json entry (title/doi/journal/year/category/summary)
  intake        ledger events for this paper (route, classifier, ts)
  authors       full roster + source (doi_cache/crossref/llm/corporate)
  analysis      step-by-step status from llm_analyses
  findings      key findings (iterative extraction)
  keywords      stated + generated
  claims        typed-claim count + stance distribution
  mechanisms    actor->target rows
  extras        study_type, mutations, sample_sizes, geography, social
  genes         distinct genes implicated (registry view)
  species       distinct host species named

Usage: pixi run python scripts/papers/build_paper_records.py [--paper ID]
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / "data" / "papers"
OUT = PAPERS / "records"

am = json.loads((PAPERS / "gene_alias_map.json").read_text())
AL, SYN = am.get("aliases", {}), am.get("synonyms", {})


def resolve(t):
    t = str(t).strip()
    if not (1 < len(t) < 40):
        return None
    for probe in (t, t.upper(), t.lower()):
        h = AL.get(probe)
        if h is not None:
            return None if h == "NOT_A_GENE" else SYN.get(h, h)
    return SYN.get(t.upper(), t.upper())


def J(x):
    try:
        return json.loads(x) if isinstance(x, str) else (x or [])
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default=None)
    args = ap.parse_args()

    pj = json.loads((ROOT / "web/public/data/papers.json").read_text())
    papers = pj["papers"] if isinstance(pj, dict) else pj
    if args.paper:
        papers = [p for p in papers if p["id"] == args.paper]
        assert papers, f"unknown paper {args.paper}"

    # load all sources once
    ledger = [json.loads(l) for l in (PAPERS / "intake_ledger.jsonl").read_text().splitlines()]
    findings = pl.read_parquet(PAPERS / "paper_key_findings.parquet")
    keywords = pl.read_parquet(PAPERS / "paper_keywords.parquet")
    claims = pl.read_parquet(PAPERS / "typed_claims.parquet")
    try:
        mech = pl.read_parquet(PAPERS / "paper_mechanisms.parquet")
    except Exception:
        mech = None
    try:
        extras = pl.read_parquet(PAPERS / "paper_extras.parquet")
    except Exception:
        extras = None

    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in papers:
        pid = p["id"]
        rec = {
            "id": pid,
            "metadata": {k: v for k, v in p.items() if k not in ("authors_full",)},
            "authors": {
                "roster": p.get("authors_full") or [],
                "source": p.get("authors_source"),
                "legacy_string": p.get("authors"),
            },
            "intake": [e for e in ledger if e.get("title") == p.get("title")][:6],
            "analysis": {},
            "findings": [],
            "keywords": [],
            "claims": {"n": 0, "stances": {}},
            "mechanisms": {"n": 0},
            "extras": {},
            "genes": [],
            "species": [],
        }
        an_path = PAPERS / "llm_analyses" / f"{pid}.json"
        if an_path.exists():
            an = json.loads(an_path.read_text())
            rec["analysis"] = {
                "verified": an.get("verified"),
                "steps": {k: ("ok" if ("extracted" in v or v.get("status") == "verified")
                              else v.get("status", "error"))
                          for k, v in (an.get("steps") or {}).items()
                          if isinstance(v, dict)},
            }
        rec["findings"] = findings.filter(pl.col("paper_id") == pid)["finding"].to_list()[:30]
        rec["keywords"] = keywords.filter(pl.col("paper_id") == pid).select(
            ["keyword", "origin"]).to_dicts()
        c = claims.filter(pl.col("paper_id") == pid)
        genes, species = set(), set()
        for r in c.iter_rows(named=True):
            genes |= {g for g in J(r["genes"]) if resolve(g)}
            species |= {s for s in J(r["species"]) if isinstance(s, str) and " " in s}
        rec["claims"] = {"n": c.height,
                         "stances": dict(Counter(s for s in c["stance"] if s))}
        if mech is not None:
            rec["mechanisms"] = {"n": mech.filter(pl.col("paper_id") == pid).height}
        if extras is not None:
            e = extras.filter(pl.col("id") == pid)
            if e.height:
                row = e.row(0, named=True)
                rec["extras"] = {k: row.get(k) for k in
                                 ("study_type", "mutations", "sample_sizes",
                                  "geography", "social_snippet") if row.get(k) is not None}
        rec["genes"] = sorted(genes)[:80]
        rec["species"] = sorted(species)[:40]
        (OUT / f"{pid}.json").write_text(json.dumps(rec, indent=1))
        n += 1
    print(f"paper records: {n} -> {OUT}")


if __name__ == "__main__":
    main()
