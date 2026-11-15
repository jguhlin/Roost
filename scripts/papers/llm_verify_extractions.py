#!/usr/bin/env python3
"""Verify extracted claims against their papers — two-layer anti-hallucination.

Layer 1 (deterministic): evidence-quote containment — does the quote appear
in the paper's markdown? Passes → verified_quote=True.
Layer 2 (LLM): for flagged rows only, re-read the paper and adjudicate:
   confirmed | paraphrased-supported | unsupported | contradicted
with the exact supporting passage. Rows that fail both layers are marked
unsupported and downstream consumers can filter on verify_verdict.

Tables: paper_species_traits (evidence), paper_mechanisms (evidence).
Usage: pixi run python scripts/papers/llm_verify_extractions.py \
           [--table traits|mechanisms] [--all] [--concurrency 24]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

MD_DIR = ROOT / "docs" / "papers_md"
TABLES = {
    "traits": (ROOT / "data" / "papers" / "paper_species_traits.parquet",
               "evidence", "paper_id"),
    "mechanisms": (ROOT / "data" / "papers" / "paper_mechanisms.parquet",
                   "evidence", "paper_id"),
}
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """You are verifying an extracted claim against its source paper.
CLAIM: {claim}
The extractor cited this evidence: "{quote}"

Read the paper below and adjudicate:
- "confirmed": the claim is directly supported; the quote appears verbatim.
- "paraphrased-supported": the claim is supported but the quote was
  paraphrased — give the EXACT supporting passage from the text.
- "unsupported": nothing in the paper supports this claim.
- "contradicted": the paper says the opposite.
Return JSON: {{"verdict": "...", "exact_quote": "..."}}

=== FULL PAPER TEXT ===
{text}"""


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    for a, b in (("‐", "-"), ("‑", "-"), ("“", '"'), ("”", '"'), ("’", "'")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).lower().strip()


def containment(text: str, quote: str) -> bool:
    q = _norm(quote)
    return len(q) >= 40 and _norm(q)[10:60] in _norm(text)


async def verify(client, sem, row_id, paper_id, claim, quote, text):
    async with sem:
        try:
            prompt = PROMPT.format(claim=claim[:400], quote=str(quote)[:300],
                                   text=text)
            out = await call_llm(client, prompt, 0.1, BASE, MODEL)
            parsed = parse_json_response(out)
            if parsed and parsed.get("verdict") in (
                    "confirmed", "paraphrased-supported", "unsupported",
                    "contradicted"):
                return row_id, parsed["verdict"], str(parsed.get(
                    "exact_quote", ""))[:400]
        except Exception:
            pass
        return row_id, "unverified", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=list(TABLES), required=True)
    ap.add_argument("--all", action="store_true",
                    help="verify every row, not just containment-flagged")
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--chunk", type=int, default=40)
    args = ap.parse_args()

    path, quote_col, pid_col = TABLES[args.table]
    df = pl.read_parquet(path)
    if "verify_verdict" in df.columns:      # resume-safe: drop old verdicts
        df = df.drop(["verify_verdict", "verify_quote", "quote_in_text"]
                     if "quote_in_text" in df.columns
                     else ["verify_verdict", "verify_quote"])

    text_cache: dict[str, str] = {}
    rows = []
    for i, r in enumerate(df.iter_rows(named=True)):
        q = r.get(quote_col)
        text = text_cache.get(r[pid_col])
        if text is None:
            try:
                text = (MD_DIR / f"{r[pid_col]}.md").read_text(errors="replace")
            except FileNotFoundError:
                text = ""
            text_cache[r[pid_col]] = text
        in_text = containment(text, q) if q else False
        rows.append({"i": i, "in_text": in_text,
                     "needs_llm": (not in_text) if args.all is False else True,
                     "paper": r[pid_col],
                     "claim": (str(r.get("outcome") or "") + " "
                               + str(r.get("text") or r.get("finding") or ""))[:400],
                     "quote": q or ""})
    n_ok = sum(1 for r in rows if r["in_text"])
    print(f"{args.table}: {len(rows)} rows · quote-in-text {n_ok} · "
          f"flagged for LLM verify {sum(1 for r in rows if r['needs_llm'])}",
          file=sys.stderr)

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        limits = httpx.Limits(max_connections=args.concurrency * 2,
                              max_keepalive_connections=args.concurrency)
        verdicts = {}
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0),
                                     limits=limits) as client:
            todo = [r for r in rows if r["needs_llm"]]
            for s in range(0, len(todo), args.chunk):
                chunk = todo[s:s + args.chunk]
                results = await asyncio.gather(*[
                    verify(client, sem, r["i"], r["paper"], r["claim"],
                           r["quote"], text_cache.get(r["paper"], ""))
                    for r in chunk])
                for rid, verdict, q in results:
                    verdicts[rid] = (verdict, q)
                print(f"  {min(s + args.chunk, len(todo))}/{len(todo)} verified",
                      file=sys.stderr)
        out_rows = []
        for i, r in enumerate(rows):
            v, q = verdicts.get(i, (None, None))
            if r["in_text"] and v is None:
                v, q = "confirmed", r["quote"]
            out_rows.append({"verify_verdict": v or "unverified",
                             "verify_quote": q or "",
                             "quote_in_text": r["in_text"]})
        verdict_df = pl.DataFrame(out_rows)
        for col in ("verify_verdict", "verify_quote"):
            verdict_df = verdict_df.with_columns(
                pl.col(col).cast(pl.Utf8, strict=False))
        verdict_df = verdict_df.with_columns(pl.col("quote_in_text")
                                             .cast(pl.Boolean, strict=False))
        df.with_row_index("i").drop("i").with_columns(
            verdict_df).write_parquet(path)
        vc = verdict_df["verify_verdict"].value_counts().to_dicts()
        print(f"final verdicts: {vc}", file=sys.stderr)
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
