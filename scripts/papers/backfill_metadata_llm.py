#!/usr/bin/env python3
"""Backfill missing doc_type + thin summaries via one LLM call per paper.

Targets papers with doc_type unknown OR summary < 40 chars. Uses title,
journal, findings sample, and keywords as context (no fulltext needed).
Incremental saves; skips papers already complete on both fields.

Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python \
    scripts/papers/backfill_metadata_llm.py [--limit N]
"""
import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web/public/data/papers.json"
LEDGER = ROOT / "data/papers/steward_ledger.jsonl"
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """Fill the missing bibliographic fields for this paper. Return ONLY JSON:
 {"doc_type": "article|preprint|review|book-chapter|report|thesis|announcement|article_metadata",
  "summary": "1-3 factual sentences (<=400 chars) of what the paper did/found"}
Use ONLY the evidence given; for summary prefer concrete findings over vague description."""


def llm(prompt):
    body = json.dumps({"model": MODEL, "temperature": 0.1, "max_tokens": 3072,
                       "messages": [{"role": "system",
                                     "content": "Bibliographic metadata completion. Strict JSON. No reasoning, answer immediately."},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        out = json.loads(r.read())["choices"][0]["message"]
    # reasoning-mode servers: text may land in reasoning_content with empty
    # content — accept either (reasoning stripped of think tags below)
    text = (out.get("content") or "").strip()
    if not text:
        rc = (out.get("reasoning_content") or "").strip()
        m = re.search(r"\{.*\}", rc, re.S)
        text = m.group(0) if m else rc
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    pj = json.loads(PAPERS_JSON.read_text())
    papers = pj["papers"] if isinstance(pj, dict) else pj
    findings = pl.read_parquet(ROOT / "data/papers/paper_key_findings.parquet")
    keywords = pl.read_parquet(ROOT / "data/papers/paper_keywords.parquet")
    fnd_by = {}
    for pid, grp in findings.group_by("paper_id"):
        fnd_by[pid[0]] = grp["finding"].to_list()[:5]
    kw_by = {}
    for r in keywords.iter_rows(named=True):
        kw_by.setdefault(r["paper_id"], []).append(r["keyword"])

    targets = [p for p in papers
               if p.get("doc_type") in (None, "", "?")
               or len((p.get("summary") or "").strip()) < 40]
    if args.limit:
        targets = targets[:args.limit]
    print(f"backfill targets: {len(targets)}")

    n_doc = n_sum = failed = 0
    for p in targets:
        ctx = {"title": p.get("title"), "journal": p.get("journal"),
               "year": p.get("year"), "authors_n": len(p.get("authors_full") or []),
               "findings_sample": fnd_by.get(p["id"], [])[:5],
               "keywords": kw_by.get(p["id"], [])[:12]}
        try:
            raw = llm(PROMPT + "\n\n" + json.dumps(ctx, indent=1)[:2500])
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            fix = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception as e:
            failed += 1
            time.sleep(1)
            continue
        if p.get("doc_type") in (None, "", "?") and fix.get("doc_type"):
            p["doc_type"] = fix["doc_type"]; n_doc += 1
        if len((p.get("summary") or "").strip()) < 40 and fix.get("summary"):
            p["summary"] = str(fix["summary"])[:450]; n_sum += 1
        if (n_doc + n_sum) % 50 == 0:
            PAPERS_JSON.write_text(json.dumps(pj, indent=1))
            print(f"  ... {n_doc} doc_types, {n_sum} summaries", flush=True)
    PAPERS_JSON.write_text(json.dumps(pj, indent=1))
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M"),
                            "paper": "__backfill_metadata__",
                            "rounds": [{"doc_types": n_doc, "summaries": n_sum,
                                        "failed": failed}]}) + "\n")
    print(f"backfill: doc_type={n_doc} summaries={n_sum} failed={failed}")


if __name__ == "__main__":
    main()
