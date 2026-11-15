#!/usr/bin/env python3
"""Verify the v2 spread extraction — quote-fidelity adjudication.

Layer 1 (already done at extraction): quote containment in the paper text
(quote_in_text, 90% corpus-wide). Layer 2 (this script): LLM adjudication
of EVERY item — does the quote actually support the extracted fields?

Per item the judge sees ONLY the section name, the extracted payload, and
the quote, and returns:
  faithful      — every field is supported by the quote
  partial       — core claim supported, some fields drift/hallucinate
  unsupported   — the quote does not support the item
  plus `fields` — which specific fields drift (for partial/unsupported)

Resume-safe: verdicts append to data/papers/spread_verify.jsonl keyed by
(paper_id, section, idx); re-runs verify only unadjudicated items.

Usage:
  pixi run python scripts/papers/llm_verify_spread.py [--workers 40]
  pixi run python scripts/papers/llm_verify_spread.py --report  # summary only
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"
LEDGER = ROOT / "data" / "papers" / "spread_verify.jsonl"
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

JUDGE_SYS = "You are a meticulous data-quality auditor. Reply ONLY with JSON."


def judge_prompt(section, payload, quote):
    return f"""You are auditing a literature-extraction pipeline. A model extracted
a structured item from a scientific paper, citing this quote as its evidence:

QUOTE: {json.dumps(quote, ensure_ascii=False)}

EXTRACTED ITEM (section: {section}):
{json.dumps(payload, ensure_ascii=False)}

Does the QUOTE support every field of the extracted item? Judge ONLY what the quote addresses; IGNORE fields the quote is silent on
(often established elsewhere in the paper — species names, dates, regions):
- "faithful": nothing the quote says contradicts the item
- "partial": the quote CONTRADICTS or disallows some field values
  (wrong number, wrong direction, invented detail the quote excludes)
- "unsupported": the quote contradicts the item's core claim
Example: item says mortality eliminated, quote says 84% died →
unsupported (core contradicted). Item says 84% seroconverted, quote says
84% seroconverted → faithful, even if species isn't in the quote.

Return JSON:
{{"verdict": "<faithful|partial|unsupported>",
 "fields": ["<field names that drift, empty if faithful>"]}}"""


async def verify(client, sem, paper_id, section, idx, payload, quote):
    async with sem:
        try:
            out = await call_llm(client, judge_prompt(section, payload, quote),
                                 0.0, BASE, MODEL)
        except Exception as e:
            return ("error", [str(e)[:80]])
    parsed = parse_json_response(out)
    if isinstance(parsed, dict) and parsed.get("verdict") in (
            "faithful", "partial", "unsupported"):
        return (parsed["verdict"], parsed.get("fields") or [])
    return ("error", ["unparseable"])


async def run(workers: int) -> int:
    df = pl.read_parquet(SPREAD)
    done = set()
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                d = json.loads(line)
                done.add((d["paper_id"], d["section"], d["idx"]))
            except Exception:
                pass

    todo = []
    for r in df.iter_rows(named=True):
        key = (r["paper_id"], r["section"], r["idx"])
        if key in done:
            continue
        try:
            payload = json.loads(r["payload"])
        except Exception:
            continue
        payload.pop("quote", None)
        todo.append((*key, payload, r["quote"]))
    print(f"items to verify: {len(todo)} ({len(done)} already adjudicated)",
          file=sys.stderr)
    if not todo:
        return 0

    sem = asyncio.Semaphore(workers)
    n = 0
    async with httpx.AsyncClient(timeout=600.0) as client:

        async def one(paper_id, section, idx, payload, quote):
            nonlocal n
            verdict, fields = await verify(client, sem, paper_id, section,
                                           idx, payload, quote)
            rec = {"paper_id": paper_id, "section": section, "idx": idx,
                   "verdict": verdict, "fields": fields,
                   "ts": __import__("datetime").datetime.now(
                       __import__("datetime").timezone.utc).isoformat()}
            with LEDGER.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            if n % 200 == 0:
                print(f"  {n}/{len(todo)} adjudicated", file=sys.stderr)

        await asyncio.gather(*(one(*t) for t in todo))
    print(f"done: {n} items verified", file=sys.stderr)
    return 0


def report() -> None:
    if not LEDGER.exists():
        print("no verdicts yet")
        return
    by_section = {}
    overall = Counter()
    drift = Counter()
    for line in LEDGER.read_text().splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        s = by_section.setdefault(d["section"], Counter())
        s[d["verdict"]] += 1
        overall[d["verdict"]] += 1
        for f in d.get("fields") or []:
            drift[f] += 1
    total = sum(overall.values())
    print(f"VERIFIED: {total} items — faithful {overall['faithful']} "
          f"({100*overall['faithful']/max(total,1):.0f}%), "
          f"partial {overall['partial']}, unsupported {overall['unsupported']}, "
          f"error {overall['error']}")
    print(f"\n{'section':<26} {'items':>5} {'faithful':>9} {'partial':>8} {'unsup':>6}")
    for sec in sorted(by_section, key=lambda s: -sum(by_section[s].values())):
        c = by_section[sec]
        n = sum(c.values())
        print(f"{sec:<26} {n:>5} {100*c['faithful']/n:>8.0f}% "
              f"{c['partial']:>8} {c['unsupported']:>6}")
    if drift:
        print("\ntop drifting fields:",
              drift.most_common(10))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=40)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        report()
        return 0
    return asyncio.run(run(args.workers))


if __name__ == "__main__":
    raise SystemExit(main())
