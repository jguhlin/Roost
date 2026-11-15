#!/usr/bin/env python3
"""Iterative key-findings + keyword extraction from papers (muse-glimmer).

Keywords: ONE query per paper — capture the paper's own stated keywords
AND generate new descriptive keywords (both).

Key findings: an ITERATIVE protocol, unlimited until the model signals
exhaustion:
  call 1   "give the single strongest key finding… if none, FALSE"
  call n   "we know these findings: […]. give one additional distinct
            strong finding… if none strong remain, FALSE"
Each iteration returns exactly one finding or FALSE; the loop stops on
FALSE (safety cap 20). The full paper text is resent each iteration —
sglang's prefix cache makes the shared prefix cheap.

Outputs:
  data/papers/paper_key_findings.parquet   (paper_id, idx, finding, ts)
  data/papers/paper_keywords.parquet       (paper_id, keyword, origin: stated|generated)

Resume: --done files track finished papers; reruns skip them.
Run:  pixi run python scripts/papers/llm_key_findings.py [--concurrency 16]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
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
OUT_F = ROOT / "data" / "papers" / "paper_key_findings.parquet"
OUT_K = ROOT / "data" / "papers" / "paper_keywords.parquet"
DONE = ROOT / "data" / "papers" / "keyfindings_done.json"
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
MAX_ITER = 20

KW_PROMPT = """Keywords for a research database. From this paper:
1. CAPTURE the author-stated keywords if any appear in the text.
2. CREATE 4-8 new descriptive keywords (topic, host species, virus subtype/
clade, method, geography) that are NOT already in the stated list.
Return JSON: {{"stated": ["..."], "generated": ["..."]}} (empty arrays if none).

TITLE: {title}

=== FULL PAPER TEXT ===
{text}"""

FIND1_PROMPT = """Given the above paper, give me a singular key finding, the
strongest. It must be a distinct, specific, evidence-backed statement (with
numbers where the paper has them) — not a topic or a restatement of the title.
Return JSON: {"finding": "..."} — or exactly {"finding": false} if there
is none."""

FINDN_PROMPT = """Given the above paper, we already know these findings:
{known}
Give me an additional singular key finding not in that list — distinct,
specific, evidence-backed (numbers where the paper has them).
Return JSON: {"finding": "..."} — or exactly {"finding": false} if there
are none left that are strong."""


def head_block(title: str) -> str:
    return f"TITLE: {title}\n"


async def extract_keywords(client, sem, pid, title, text):
    async with sem:
        try:
            out = await call_llm(client, KW_PROMPT.format(title=title, text=text),
                                 0.2, BASE, MODEL)
            parsed = parse_json_response(out)
            if parsed:
                return pid, parsed
        except Exception as e:
            return pid, {"error": str(e)[:100]}
        return pid, {}


async def findings_loop(client, sem, pid, title, text):
    """Iterative strongest-finding extraction until FALSE or cap."""
    async with sem:
        findings = []
        base = head_block(title) + "\n=== FULL PAPER TEXT ===\n" + text + "\n\n"
        for i in range(MAX_ITER):
            if i == 0:
                prompt = base + FIND1_PROMPT
            else:
                known = "\n".join(f'  {j+1}. "{f}"' for j, f in enumerate(findings))
                prompt = base + FINDN_PROMPT.replace("{known}", known)
            try:
                out = await call_llm(client, prompt, 0.2, BASE, MODEL)
                parsed = parse_json_response(out)
                f = parsed.get("finding") if isinstance(parsed, dict) else None
                if f is False or f is None or f == "false":
                    break
                if isinstance(f, str) and len(f) > 8 and f not in findings:
                    findings.append(f.strip()[:1500])
                else:
                    break   # malformed → treat as exhaustion
            except Exception:
                break
        return pid, findings


async def process_chunk(client, sem, chunk):
    kw_jobs = [extract_keywords(client, sem, pid, t,
                                (MD_DIR / f"{pid}.md").read_text(errors="replace"))
               for pid, t in chunk]
    find_jobs = [findings_loop(client, sem, pid, t,
                               (MD_DIR / f"{pid}.md").read_text(errors="replace"))
                 for pid, t in chunk]
    return await asyncio.gather(*kw_jobs, *find_jobs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--chunk", type=int, default=25)
    ap.add_argument("--ids", help="comma-separated paper ids")
    args = ap.parse_args()

    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    done = set(json.loads(DONE.read_text())) if DONE.exists() else set()
    todo = [(p["id"], p.get("title", "")) for p in papers
            if p["id"] not in done
            and (not args.ids or p["id"] in args.ids.split(","))
            and (MD_DIR / f"{p['id']}.md").exists()]
    print(f"{len(todo)} papers (done: {len(done)})", file=sys.stderr)
    if not todo:
        return 0

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        limits = httpx.Limits(max_connections=args.concurrency * 2,
                              max_keepalive_connections=args.concurrency)
        n = len(todo)
        async with httpx.AsyncClient(timeout=httpx.Timeout(900.0),
                                     limits=limits) as client:
            for start in range(0, n, args.chunk):
                chunk = todo[start:start + args.chunk]
                results = await process_chunk(client, sem, chunk)
                kws = {pid: r for pid, r in results[:len(chunk)]}
                fnds = {pid: r for pid, r in results[len(chunk):]}
                kw_rows, find_rows = [], []
                for pid, _ in chunk:
                    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    k = kws.get(pid, {})
                    if not isinstance(k, dict):
                        k = {}
                    for origin, key in (("stated", k.get("stated") or []),
                                        ("generated", k.get("generated") or [])):
                        for w in (key if isinstance(key, list) else [])[:15]:
                            if isinstance(w, str) and w.strip():
                                kw_rows.append({"paper_id": pid, "keyword":
                                                w.strip()[:60], "origin": origin,
                                                "extracted_at": ts})
                    for i, f in enumerate(fnds.get(pid) or []):
                        find_rows.append({"paper_id": pid, "idx": i,
                                          "finding": f, "extracted_at": ts})
                    done.add(pid)
                for out, rows, dt_casts in (
                        (OUT_K, kw_rows, {}),
                        (OUT_F, find_rows, {"idx": pl.Int64})):
                    if rows:
                        fresh = pl.DataFrame(rows, infer_schema_length=None)
                        for col, dt in dt_casts.items():
                            fresh = fresh.with_columns(
                                pl.col(col).cast(dt, strict=False))
                        if out.exists():
                            old = pl.read_parquet(out).filter(
                                ~pl.col("paper_id").is_in(
                                    [r["paper_id"] for r in rows]))
                            fresh = pl.concat([old, fresh], how="diagonal")
                        fresh.write_parquet(out)
                DONE.write_text(json.dumps(sorted(done)))
                tot = sum(len(v) for v in fnds.values())
                print(f"  {min(start + args.chunk, n)}/{n} papers · "
                      f"{tot} findings this chunk", file=sys.stderr)
    asyncio.run(run())

    prov = json.loads(PROVENANCE.read_text()) if PROVENANCE.exists() \
        else {"calls": []}
    prov["calls"].append({
        "task": "keywords_and_key_findings", "model": MODEL,
        "prompt_version": "kw-v1/findings-iterative-v1",
        "papers": len(done), "max_iterations": MAX_ITER,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    PROVENANCE.write_text(json.dumps(prov, indent=1))
    print("done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
