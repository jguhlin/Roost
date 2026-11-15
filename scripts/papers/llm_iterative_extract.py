#!/usr/bin/env python3
"""Generic iterative extractor — one engine, many claim kinds.

Same protocol as key findings: strongest item → "we know these: […]" →
next → FALSE. Kinds:

  quantitative   exact numeric results with units (titres, mortality %,
                 shedding days, HI titres, TCID50 …) — the numbers bank
  limitations    author-stated limitations / future-work gaps
  disagreements  explicit "contrary to X et al." conflicts

Output: data/papers/paper_{kind}.parquet (paper_id, idx, text,
detail JSON, extracted_at). Resume via done-file per kind.
Run:  pixi run python scripts/papers/llm_iterative_extract.py \
          --kind quantitative [--concurrency 32]
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

MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
OUT_DIR = ROOT / "data" / "papers"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
MAX_ITER = 12

KINDS = {
    "quantitative": {
        "first": """Given the above paper, state the single most important
QUANTITATIVE RESULT: an exact number with units, its measurement, the
group/species it belongs to. Return JSON:
{{"text": "...", "value": <number>, "unit": "...", "measure": "...",
"subject": "species or group"}} — or exactly {{"item": false}}.""",
        "next": """Given the above paper, we already have these results:
{known}
State ONE additional distinct quantitative result (same JSON shape).
Return {{"item": false}} if none important remain.""",
        "claim": "quantitative result",
    },
    "limitations": {
        "first": """Given the above paper, state the single most important
LIMITATION or future-work gap THE AUTHORS THEMSELVES state (from the
discussion/limitations section). Return JSON: {{"text": "..."}}
— or exactly {{"item": false}} if the paper states none.""",
        "next": """Given the above paper, we already have these stated
limitations: {known}
State ONE additional distinct author-stated limitation (same JSON shape).
Return {{"item": false}} if none remain.""",
        "claim": "author-stated limitation",
    },
    "disagreements": {
        "first": """Given the above paper, state the single strongest EXPLICIT
DISAGREEMENT the authors express with prior published work ("contrary to
X et al.", "in contrast to previous reports…"). Include who they disagree
with if named. Return JSON: {{"text": "...", "disagrees_with": "..."}}
— or exactly {{"item": false}} if none.""",
        "next": """Given the above paper, we already have these
disagreements: {known}
State ONE additional distinct explicit disagreement (same JSON shape).
Return {{"item": false}} if none remain.""",
        "claim": "explicit disagreement",
    },
}


async def loop_paper(client, sem, pid, title, text, kind):
    spec = KINDS[kind]
    async with sem:
        base = f"TITLE: {title}\n\n=== FULL PAPER TEXT ===\n{text}\n\n"
        items = []
        for i in range(MAX_ITER):
            if i == 0:
                prompt = base + spec["first"]
            else:
                known = "\n".join(f'  {j+1}. {it["text"]}' for j, it in enumerate(items))
                prompt = base + spec["next"].replace("{known}", known)
            try:
                out = await call_llm(client, prompt, 0.2, BASE, MODEL)
                parsed = parse_json_response(out)
                m = parsed.get("item", parsed) if isinstance(parsed, dict) else None
                if m is False or m is None or m == "false":
                    break
                # model sometimes returns the item as a plain string
                if isinstance(m, str) and len(m) > 10:
                    m = {"text": m}
                if isinstance(m, dict) and m.get("text") \
                        and str(m["text"]) not in [str(x["text"]) for x in items]:
                    items.append({k: (str(v)[:200] if v is not None else None)
                                  for k, v in m.items() if k != "item"})
                else:
                    break
            except Exception:
                break
        return pid, items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=list(KINDS), required=True)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--chunk", type=int, default=25)
    args = ap.parse_args()

    out_path = OUT_DIR / f"paper_{args.kind}.parquet"
    done_path = OUT_DIR / f"{args.kind}_done.json"
    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    done = set(json.loads(done_path.read_text())) if done_path.exists() else set()
    todo = [(p["id"], p.get("title", "")) for p in papers
            if p["id"] not in done
            and (MD_DIR / f"{p['id']}.md").exists()]
    print(f"{args.kind}: {len(todo)} papers (done: {len(done)})", file=sys.stderr)
    if not todo:
        return 0

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        limits = httpx.Limits(max_connections=args.concurrency * 2,
                              max_keepalive_connections=args.concurrency)
        async with httpx.AsyncClient(timeout=httpx.Timeout(900.0),
                                     limits=limits) as client:
            for s in range(0, len(todo), args.chunk):
                chunk = todo[s:s + args.chunk]
                jobs = [loop_paper(client, sem, pid, t,
                                   (MD_DIR / f"{pid}.md").read_text(errors="replace"),
                                   args.kind) for pid, t in chunk]
                results = await asyncio.gather(*jobs)
                rows = []
                for pid, items in results:
                    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    for i, it in enumerate(items):
                        rows.append({"paper_id": pid, "idx": i,
                                     "text": it.get("text"),
                                     "detail": json.dumps(
                                         {k: v for k, v in it.items()
                                          if k != "text"}),
                                     "extracted_at": ts})
                    done.add(pid)
                if rows:
                    fresh = pl.DataFrame(rows, infer_schema_length=None)
                    fresh = fresh.with_columns(pl.col("idx").cast(pl.Int64))
                    for col in fresh.columns:
                        if col != "idx":
                            fresh = fresh.with_columns(
                                pl.col(col).cast(pl.Utf8, strict=False))
                    if out_path.exists():
                        old = pl.read_parquet(out_path).filter(
                            ~pl.col("paper_id").is_in(
                                [r["paper_id"] for r in rows]))
                        fresh = pl.concat([old, fresh], how="diagonal")
                    fresh.write_parquet(out_path)
                done_path.write_text(json.dumps(sorted(done)))
                print(f"  {min(s + args.chunk, len(todo))}/{len(todo)} · "
                      f"{sum(len(x) for _, x in results)} items in chunk",
                      file=sys.stderr)
    asyncio.run(run())
    print(f"{args.kind} extraction done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
