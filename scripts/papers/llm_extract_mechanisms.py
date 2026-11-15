#!/usr/bin/env python3
"""Iterative mechanistic extraction — same protocol as key findings.

"Given the above paper, state the single strongest MECHANISTIC claim
(actor → interaction → target → effect); FALSE when none left." Each
mechanism is typed inline: actors (genes/proteins), interaction type,
targets, effect, context (in vitro / species), verbatim evidence.
Output feeds pathway annotation (nodes/edges with literature provenance).

Output: data/papers/paper_mechanisms.parquet
Resume: --done file.
Run:  pixi run python scripts/papers/llm_extract_mechanisms.py [--concurrency 32]
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
OUT = ROOT / "data" / "papers" / "paper_mechanisms.parquet"
DONE = ROOT / "data" / "papers" / "mechanisms_done.json"
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
MAX_ITER = 15

PROMPT_1 = """Given the above paper, state the single strongest MECHANISTIC
claim — a causal molecular/host-factor statement of the form
actor → interaction → target → effect (e.g. "PB2 627K enhances polymerase
activity in mammalian nuclei by binding host ANP32A"). Host factors, viral
proteins, immune pathways all count; species-level observations WITHOUT a
molecular/causal chain do NOT.
Return JSON: {{"actors": ["PB2 627K"], "interaction": "binds",
"targets": ["ANP32A"], "effect": "enhanced polymerase activity in mammalian
nuclei", "context": "in vitro | species/tissue", "evidence": "short verbatim
quote", "text": "one-sentence mechanism"}}
— or exactly {{"mechanism": false}} if the paper contains none."""

PROMPT_N = """Given the above paper, we already have these mechanisms:
{known}
State ONE additional distinct mechanistic claim (same actor→interaction→
target→effect form, same JSON shape). Return {{"mechanism": false}} if
none strong remain."""


async def loop_paper(client, sem, pid, title, text):
    async with sem:
        base = f"TITLE: {title}\n\n=== FULL PAPER TEXT ===\n{text}\n\n"
        mechs = []
        clean = False   # TRUE only when the model itself said FALSE —
        # an exception/timeout break leaves clean=False so the paper is
        # NOT marked done and re-extracts on a later run
        for i in range(MAX_ITER):
            if i == 0:
                prompt = base + PROMPT_1
            else:
                known = "\n".join(f'  {j+1}. {m["text"]}' for j, m in enumerate(mechs))
                prompt = base + PROMPT_N.replace("{known}", known)
            try:
                out = await call_llm(client, prompt, 0.2, BASE, MODEL)
                parsed = parse_json_response(out)
                m = parsed.get("mechanism", parsed) if isinstance(parsed, dict) else None
                if m is False or m is None or m == "false":
                    clean = True
                    break
                # model sometimes returns the mechanism as a plain string
                if isinstance(m, str) and len(m) > 20:
                    m = {"text": m, "actors": ["unknown"], "effect": m[:100]}
                if isinstance(m, dict):
                    # models mix singular/plural keys — normalize both
                    for plur, sing in (("actors", "actor"),
                                       ("targets", "target")):
                        if plur not in m or not m.get(plur):
                            v = m.get(sing)
                            m[plur] = [v] if isinstance(v, str) else (
                                v if isinstance(v, list) else [])
                        m.pop(sing, None)
                if isinstance(m, dict) and m.get("actors") and m.get("effect"):
                    m = {k: (v if not isinstance(v, list) else
                             [str(x)[:40] for x in v][:6])
                         for k, v in m.items() if k in
                         ("actors", "interaction", "targets", "effect",
                          "context", "evidence", "text")}
                    m.setdefault("text", f"{m.get('actors')} {m.get('interaction')} "
                                  f"{m.get('targets')} — {m.get('effect')}")
                    if str(m["text"]) not in [str(x["text"]) for x in mechs]:
                        mechs.append(m)
                    else:
                        clean = True
                        break
                else:
                    break
            except Exception:
                break
        return pid, mechs, clean


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=32)
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
        async with httpx.AsyncClient(timeout=httpx.Timeout(900.0),
                                     limits=limits) as client:
            for start in range(0, len(todo), args.chunk):
                chunk = todo[start:start + args.chunk]
                jobs = []
                for pid, t in chunk:
                    text = (MD_DIR / f"{pid}.md").read_text(errors="replace")
                    jobs.append(loop_paper(client, sem, pid, t, text))
                results = await asyncio.gather(*jobs)
                rows = []
                for pid, mechs, clean in results:
                    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    for i, m in enumerate(mechs):
                        rows.append({
                            "paper_id": pid, "idx": i,
                            "actors": json.dumps(m.get("actors") or []),
                            "interaction": str(m.get("interaction") or "")[:40],
                            "targets": json.dumps(m.get("targets") or []),
                            "effect": str(m.get("effect") or "")[:300],
                            "context": str(m.get("context") or "")[:120],
                            "evidence": str(m.get("evidence") or "")[:300],
                            "text": str(m.get("text") or "")[:500],
                            "extracted_at": ts,
                        })
                    if clean:
                        done.add(pid)
                if rows:
                    fresh = pl.DataFrame(rows, infer_schema_length=None)
                    fresh = fresh.with_columns(pl.col("idx").cast(pl.Int64))
                    for col in ("paper_id", "actors", "interaction", "targets",
                                "effect", "context", "evidence", "text",
                                "extracted_at"):
                        fresh = fresh.with_columns(
                            pl.col(col).cast(pl.Utf8, strict=False))
                    if OUT.exists():
                        old = pl.read_parquet(OUT).filter(
                            ~pl.col("paper_id").is_in(
                                fresh["paper_id"].unique().to_list()))
                        fresh = pl.concat([old, fresh], how="diagonal")
                    fresh.write_parquet(OUT)
                DONE.write_text(json.dumps(sorted(done)))
                print(f"  {min(start + args.chunk, len(todo))}/{len(todo)} "
                      f"papers · {sum(len(m) for _, m, _c in results)} mechanisms "
                      f"in chunk", file=sys.stderr)
    asyncio.run(run())
    prov = json.loads(PROVENANCE.read_text()) if PROVENANCE.exists() \
        else {"calls": []}
    prov["calls"].append({
        "task": "mechanisms", "model": MODEL,
        "prompt_version": "mechanisms-iterative-v1", "max_iterations": MAX_ITER,
        "papers": len(done),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    PROVENANCE.write_text(json.dumps(prov, indent=1))
    print("mechanism extraction done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
