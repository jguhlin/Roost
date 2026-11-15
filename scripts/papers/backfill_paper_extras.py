#!/usr/bin/env python3
"""Backfill deterministic extras (stage 1) for the pre-existing corpus.

The 1,083 papers processed before D133 have paper_db gene/strain hits but
never went through process_new_papers — they lack the extras fields
(mutations, sample sizes, geography, social template, study heuristics).
This runs the same deterministic miners over their markdown and merges the
results into data/papers/paper_extras.parquet, ready for the LLM pass
(llm_enrich_new_papers.py --pending).

Run:  pixi run python scripts/papers/backfill_paper_extras.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from process_new_papers import (  # noqa: E402
    mine_mutations, mine_sample_sizes, mine_geography, social_snippet,
    study_types, TODAY_ISO,
)
from build_paper_db import paper_type, language_guess  # noqa: E402

MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
EXTRAS = ROOT / "data" / "papers" / "paper_extras.parquet"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    meta_by = {p["id"]: p for p in papers}
    extras = pl.read_parquet(EXTRAS) if EXTRAS.exists() else None
    done_ids = set(extras["id"].to_list()) if extras is not None else set()

    mds = sorted(MD_DIR.glob("*.md"))
    if args.limit:
        mds = mds[:args.limit]
    rows = []
    for md in mds:
        pid = md.stem
        if pid in done_ids:
            continue
        p = meta_by.get(pid)
        raw_topics = (p.get("topics", "") if p else "")
        if isinstance(raw_topics, list):
            raw_topics = ",".join(str(t) for t in raw_topics)
        raw_category = (p.get("category", "") if p else "")
        if not isinstance(raw_category, str):
            raw_category = str(raw_category or "")
        text = md.read_text(errors="replace")
        meta = {
            "authors": p.get("authors", "") if p else "",
            "year": p.get("year") if p else None,
            "title": p.get("title", "") if p else pid,
            "doi": p.get("doi") if p else None,
            "url": p.get("url", "") if p else "",
            "journal": p.get("journal", "") if p else "",
        }
        rows.append({
            "id": pid,
            "title": meta["title"],
            "authors": [a.strip() for a in re.split(r",|\band\b", meta["authors"])
                        if a.strip() and a.strip().lower() != "et al."],
            "journal": meta["journal"],
            "year": meta["year"],
            "doi": meta["doi"],
            "url": meta["url"],
            "paper_type": paper_type(meta),
            "category": raw_category,
            "topics": raw_topics,
            "summary": (p.get("summary", "") if p else ""),
            "language_guess": language_guess(text),
            "study_type": study_types(text),
            "mutations": json.dumps(mine_mutations(text)),
            "sample_sizes": json.dumps(mine_sample_sizes(text)),
            "geography": json.dumps(mine_geography(text)),
            "social_snippet": social_snippet(meta),
            "effect_direction": "[]",
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "backfill": True,
        })

    if not rows:
        print("nothing to backfill", file=sys.stderr)
        return 0
    fresh = pl.DataFrame(rows, infer_schema_length=None)
    # align dtypes with the existing extras table (year is String there)
    for col, dt in (("year", pl.Utf8),):
        if col in fresh.columns:
            fresh = fresh.with_columns(pl.col(col).cast(dt, strict=False))
    out = pl.concat([extras, fresh], how="diagonal") if extras is not None else fresh
    out.write_parquet(EXTRAS)
    print(f"backfilled {len(rows)} papers (extras now {out.height} rows)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
