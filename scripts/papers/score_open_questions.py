#!/usr/bin/env python3
"""Score all open questions by importance/feasibility/data-availability.

~5,000 open questions from the adjudication, scored in batches of 50
(~100 LLM calls). Each question gets:
  importance (1-5): how much would answering this advance the field?
  feasibility (1-5): can this be answered with available methods?
  data_availability (1-5): does our corpus have relevant evidence?
  combined: weighted score

Output: data/papers/scored_questions.parquet (queryable, sorted)

Run:  pixi run python scripts/papers/score_open_questions.py [--batch 50]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

CONTRA = ROOT / "web" / "public" / "data" / "papers" / "contradictions.json"
OUT = ROOT / "data" / "papers" / "scored_questions.parquet"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """Rate each research question on three dimensions (1-5 each):

IMPORTANCE: How much would answering this advance understanding of
avian influenza host response, species barriers, or epidemiology?
5 = field-changing insight; 1 = incremental detail.

FEASIBILITY: Can this realistically be answered with available methods?
5 = routine experiment/analysis; 1 = requires breakthrough technology.

DATA_AVAILABILITY: Is there likely enough existing data (in our corpus
of ~1,100 avian influenza papers plus public databases) to make progress?
5 = abundant data; 1 = no relevant data exists.

Questions:
{questions}

Return JSON:
{{"scores": [{{"q": "first few words of question", "importance": N,
  "feasibility": N, "data_availability": N}}]}}
One entry per question, same order."""


async def score_batch(client, sem, questions):
    """Score a batch of questions."""
    async with sem:
        body = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(questions))
        prompt = PROMPT.format(questions=body)
        for attempt in range(2):
            try:
                out = await call_llm(client, prompt, 0.1, BASE, MODEL)
                parsed = parse_json_response(out)
                if parsed and isinstance(parsed.get("scores"), list):
                    return parsed["scores"]
            except Exception:
                pass
            await asyncio.sleep(3)
        return []


async def main_async(args):
    d = json.loads(CONTRA.read_text())
    questions = [(q["q"], q.get("cluster", "")) for q in d.get("open_questions", [])]
    print(f"{len(questions)} open questions to score", file=sys.stderr)

    # deduplicate
    seen = set()
    unique = []
    for q, c in questions:
        if q not in seen:
            seen.add(q)
            unique.append((q, c))
    print(f"  unique: {len(unique)}", file=sys.stderr)

    # batch
    batches = [unique[i:i + args.batch] for i in range(0, len(unique), args.batch)]
    print(f"  batches: {len(batches)} of {args.batch}", file=sys.stderr)

    sem = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency * 2,
                           max_keepalive_connections=args.concurrency)

    all_rows = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0), limits=limits) as client:
        for bi, batch in enumerate(batches):
            batch_questions = [q for q, _ in batch]
            results = await score_batch(client, sem, batch_questions)

            for (q, cluster), score in zip(batch, results):
                if isinstance(score, dict):
                    imp = int(score.get("importance", 3))
                    fea = int(score.get("feasibility", 3))
                    dat = int(score.get("data_availability", 3))
                    combined = round(imp * 0.4 + fea * 0.3 + dat * 0.3, 2)
                    all_rows.append({
                        "question": q, "cluster": cluster,
                        "importance": imp, "feasibility": fea,
                        "data_availability": dat, "combined": combined,
                        "scored_at": datetime.fromtimestamp(
                            __import__("time").time(), tz=timezone.utc
                        ).isoformat(timespec="seconds"),
                    })
                else:
                    all_rows.append({
                        "question": q, "cluster": cluster,
                        "importance": None, "feasibility": None,
                        "data_availability": None, "combined": None,
                        "scored_at": "unscored",
                    })

            done = min((bi + 1) * args.batch, len(unique))
            print(f"  {done}/{len(unique)} scored "
                  f"({sum(1 for r in all_rows if r['combined'])} with scores)",
                  file=sys.stderr)

    # write parquet
    df = pl.DataFrame(all_rows, infer_schema_length=None)
    for col in ("importance", "feasibility", "data_availability", "combined"):
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))
    df = df.sort("combined", descending=True, nulls_last=True)
    df.write_parquet(OUT)

    scored = df.filter(pl.col("combined").is_not_null())
    print(f"\nwrote {OUT.name}: {len(df)} questions, "
          f"{len(scored)} scored", file=sys.stderr)
    print(f"  top 5 by combined score:", file=sys.stderr)
    for r in scored.head(5).iter_rows(named=True):
        print(f"    [{r['combined']:.1f}] imp={r['importance']:.0f} "
              f"fea={r['feasibility']:.0f} dat={r['data_availability']:.0f}  "
              f"{r['question'][:60]}", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--concurrency", type=int, default=32)
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
