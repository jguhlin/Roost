#!/usr/bin/env python3
"""Triage the steward queue's keyword proposals into the keyword table.

Reads data/papers/steward_queue.jsonl add_keywords entries, normalises the
proposed keywords, drops noise (too short/long, existing, non-topical),
and merges accepted ones into data/papers/paper_keywords.parquet with
origin='steward'. Queue entries consumed by this pass are archived to
steward_queue_done.jsonl.

Usage: pixi run python scripts/papers/triage_keyword_queue.py [--dry-run]
"""
import argparse
import json
import re
import time
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / "data" / "papers"
QUEUE = PAPERS / "steward_queue.jsonl"
DONE = PAPERS / "steward_queue_done.jsonl"
KW = PAPERS / "paper_keywords.parquet"

JUNK = re.compile(r"^(et al|the|and|this|study|paper|result|results|conclusion|introduction|method|methods|unknown|none)$", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kw = pl.read_parquet(KW)
    existing = {(r["paper_id"], r["keyword"].lower()) for r in kw.iter_rows(named=True)}
    papers = {p["id"] for p in (lambda d: d.get("papers", d))(
        json.loads((ROOT / "web/public/data/papers.json").read_text()))}

    entries = [json.loads(l) for l in QUEUE.read_text().splitlines() if l.strip()]
    kw_entries = [e for e in entries if e.get("action") == "add_keywords"]
    accepted, kept = [], []
    for e in kw_entries:
        pid = e.get("paper")
        if pid not in papers:
            continue
        for k in (e.get("keywords") or []):
            k = re.sub(r"\s+", " ", str(k)).strip(" .,-")
            if not (3 <= len(k) <= 40) or JUNK.match(k):
                continue
            if (pid, k.lower()) in existing:
                continue
            existing.add((pid, k.lower()))
            accepted.append({"paper_id": pid, "keyword": k, "origin": "steward"})
        kept.append(e)

    print(f"queue entries: {len(entries)} | add_keywords: {len(kw_entries)} | "
          f"accepted keywords: {len(accepted)}")
    if args.dry_run or not accepted:
        return
    kw = pl.concat([kw, pl.DataFrame(accepted)], how="diagonal")
    kw.write_parquet(KW)
    with open(DONE, "a") as f:
        for e in kept:
            e["resolved"] = {"ts": time.strftime("%Y-%m-%d %H:%M"), "how": "keyword triage"}
            f.write(json.dumps(e) + "\n")
    remaining = [e for e in entries if e not in kept]
    QUEUE.write_text("".join(json.dumps(e) + "\n" for e in remaining))
    print(f"merged {len(accepted)} keywords; queue now {len(remaining)} entries")


if __name__ == "__main__":
    main()
