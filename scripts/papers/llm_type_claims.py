#!/usr/bin/env python3
"""Claim typing — bind findings/effects to entities + stance (the clustering key).

One LLM call per paper takes its extracted findings (and effects) and types
every claim: which genes/species/clades/methods/places it concerns, its
stance (asserts|refutes|increases|decreases|no_effect|mixed|descriptive),
and scope notes (e.g. "chickens only"). Typed claims cluster by
(entity, outcome) key — the input for contradiction adjudication and
research-gap detection (see llm_claims_adjudicate.py, planned).

Output: data/papers/typed_claims.parquet
  (paper_id, idx, text, genes[], species[], clades[], methods[], places[],
   stance, scope, source)
Resume: --done file.
Run:  pixi run python scripts/papers/llm_type_claims.py [--concurrency 16]
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

FINDINGS = ROOT / "data" / "papers" / "paper_key_findings.parquet"
EXTRAS = ROOT / "data" / "papers" / "paper_extras.parquet"
OUT = ROOT / "data" / "papers" / "typed_claims.parquet"
DONE = ROOT / "data" / "papers" / "claim_typing_done.json"
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """You are typing research claims for contradiction/gap analysis of
the avian-influenza literature. For EACH claim below, from paper
"{title}" ({year}), extract:

- entities: gene symbols, host species (scientific names), virus subtypes/
  clades, methods, and geographic scopes the claim is ABOUT
- stance: asserts | refutes | increases | decreases | no_effect | mixed |
  descriptive (descriptive = measurement/observation without a directional
  relationship)
- scope: short note when the claim is bound to a specific context
  (e.g. "chickens only", "in vitro", "2.3.4.4b era"), else null

Return JSON: {{"claims": [
 {{"text": "<the claim, lightly compressed>",
  "genes": [], "species": [], "clades": [], "methods": [], "places": [],
  "stance": "...", "scope": null}}]}} — one output per input, same order.

CLAIMS:
{claims}"""


async def type_paper(client, sem, pid, title, year, claims):
    """Type claims in batches of ≤6 — one huge response overruns the token
    cap, truncates mid-JSON and fails parsing (the 70% failure mode)."""
    all_typed = []
    for b in range(0, len(claims), 6):
        batch = claims[b:b + 6]
        async with sem:
            payload = PROMPT.format(
                title=title, year=year,
                claims="\n".join(f"  {i+1}. {c}" for i, c in enumerate(batch)))
            ok = False
            for attempt in range(2):
                try:
                    out = await call_llm(client, payload, 0.2, BASE, MODEL)
                    parsed = parse_json_response(out)
                    if parsed and isinstance(parsed.get("claims"), list) \
                            and len(parsed["claims"]) >= max(1, len(batch) // 2):
                        all_typed.extend(parsed["claims"])
                        ok = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(2)
            if not ok:
                return pid, None     # a failed batch fails the paper (resume)
    return pid, all_typed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--chunk", type=int, default=25)
    args = ap.parse_args()

    fnd = pl.read_parquet(FINDINGS)
    extras = pl.read_parquet(EXTRAS).select(["id", "title", "year"])
    meta = {r["id"]: r for r in extras.iter_rows(named=True)}
    done = set(json.loads(DONE.read_text())) if DONE.exists() else set()

    by_paper: dict[str, list[str]] = {}
    for r in fnd.filter(~pl.col("paper_id").is_in(sorted(done))
                        if done else pl.lit(True)).iter_rows(named=True):
        by_paper.setdefault(r["paper_id"], []).append(r["finding"])
    # also type the effect-direction claims (exposure→outcome→direction)
    for r in pl.read_parquet(EXTRAS).iter_rows(named=True):
        effs = json.loads(r.get("effect_direction") or "[]")
        if r["id"] in by_paper:
            for e in effs[:6]:
                by_paper[r["id"]].append(
                    f"{e.get('exposure')} {e.get('direction')} "
                    f"{e.get('outcome')} — {e.get('evidence', '')[:100]}")

    todo = [(pid, meta.get(pid, {}).get("title", pid),
             meta.get(pid, {}).get("year", "")) for pid in sorted(by_paper)]
    print(f"{len(todo)} papers with claims to type (done: {len(done)})",
          file=sys.stderr)
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
                jobs = [type_paper(client, sem, pid, t, y, by_paper[pid])
                        for pid, t, y in chunk]
                results = await asyncio.gather(*jobs)
                rows, failed = [], 0
                for pid, typed in results:
                    if typed is None:
                        failed += 1
                        continue
                    for i, c in enumerate(typed):
                        if not isinstance(c, dict):
                            continue
                        rows.append({
                            "paper_id": pid, "idx": i,
                            "text": str(c.get("text", ""))[:1000],
                            "genes": json.dumps(c.get("genes") or []),
                            "species": json.dumps(c.get("species") or []),
                            "clades": json.dumps(c.get("clades") or []),
                            "methods": json.dumps(c.get("methods") or []),
                            "places": json.dumps(c.get("places") or []),
                            "stance": c.get("stance"),
                            "scope": c.get("scope"),
                            "typed_at": datetime.now(timezone.utc)
                                .isoformat(timespec="seconds"),
                        })
                    done.add(pid)
                if rows:
                    fresh = pl.DataFrame(rows, infer_schema_length=None)
                    fresh = fresh.with_columns(pl.col("idx").cast(pl.Int64))
                    if OUT.exists():
                        old = pl.read_parquet(OUT).filter(
                            ~pl.col("paper_id").is_in([p for p, _ in results]))
                        fresh = pl.concat([old, fresh], how="diagonal")
                    fresh.write_parquet(OUT)
                DONE.write_text(json.dumps(sorted(done)))
                print(f"  {min(start + args.chunk, len(todo))}/{len(todo)} "
                      f"papers · {failed} failed in chunk", file=sys.stderr)
    asyncio.run(run())
    print("claim typing done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
