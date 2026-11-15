#!/usr/bin/env python3
"""Per-species phenotype extraction from papers — the trait-table feed.

One full-text query per paper asks: "for every species this paper reports
RESULTS for, extract structured trait evidence" — severity, counts,
clinical signs, viral load, shedding, replication, serology, comparator
role, clade. Results land in data/papers/paper_species_traits.parquet
(one row per paper × species), which aggregates into
data/species_traits.parquet (the 11 pending_papers traits) with full
paper provenance.

Resume: --done file tracks finished paper ids; reruns skip them.
Concurrency is deliberately configurable — piggyback at low --concurrency
while other LLM passes run, or go full width afterwards.

Run:  pixi run python scripts/papers/llm_extract_phenotypes.py \
          [--concurrency 24] [--chunk 100]
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
OUT = ROOT / "data" / "papers" / "paper_species_traits.parquet"
DONE = ROOT / "data" / "papers" / "phenotypes_done.json"
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
PROMPT_VERSION = "species-phenotypes-v1"

PROMPT = """You are extracting per-species trait evidence for an avian-influenza
host-factor database. TITLE: {title}

For EVERY avian or mammalian species this paper reports RESULTS for (challenge
outcomes, field outbreak mortality, or serology — not species merely mentioned
in background), extract structured evidence. Prefer scientific names; use the
common name if no Latin name appears.

Return JSON:
{{"species": [
 {{"name": "<scientific or common name>",
   "kind": "experimental_challenge | field_outbreak | serology | surveillance",
   "n_total": <int or null>, "n_dead": <int or null>,
   "outcome": "severe_mortality | moderate_mortality | subclinical | asymptomatic_seropositive | mixed | unknown",
   "clinical": "<notable clinical signs, short phrase, or null>",
   "viral_load": "<peak titre with units, or null>",
   "shedding_days": <number or null>,
   "replication": "low | normal | none | null",
   "comparator": <true if used as a low-susceptibility comparator>,
   "serology": "positive | negative | <titre> | null",
   "clade": "<e.g. 2.3.4.4b or null>",
   "evidence": "<short verbatim quote supporting the outcome>"}}]}}
Use REAL values from the paper; null what is not reported. Empty list if the
paper reports no per-species results.

=== FULL PAPER TEXT ===
{text}"""


async def one(client, sem, pid, title, text, retries=2):
    async with sem:
        prompt = PROMPT.format(title=title, text=text)
        for attempt in range(retries + 1):
            try:
                out = await call_llm(client, prompt, 0.2, BASE, MODEL)
                parsed = parse_json_response(out)
                if parsed and "species" in parsed:
                    return pid, parsed["species"]
                if parsed:
                    return pid, []
            except Exception as e:
                if attempt == retries:
                    return pid, {"error": str(e)[:120]}
                await asyncio.sleep(3 * (attempt + 1))
        return pid, {"error": "no valid JSON"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--chunk", type=int, default=100)
    ap.add_argument("--ids", help="comma-separated paper ids")
    args = ap.parse_args()

    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    done = set(json.loads(DONE.read_text())) if DONE.exists() else set()
    todo = [(p["id"], p.get("title", "")) for p in papers
            if p["id"] not in done
            and (not args.ids or p["id"] in args.ids.split(","))
            and (MD_DIR / f"{p['id']}.md").exists()]
    print(f"{len(todo)} papers to extract (done: {len(done)})", file=sys.stderr)
    if not todo:
        return 0

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        limits = httpx.Limits(max_connections=args.concurrency * 2,
                              max_keepalive_connections=args.concurrency)
        all_rows, errors = [], 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0),
                                     limits=limits) as client:
            for start in range(0, len(todo), args.chunk):
                chunk = todo[start:start + args.chunk]
                jobs = []
                for pid, title in chunk:
                    text = (MD_DIR / f"{pid}.md").read_text(errors="replace")
                    jobs.append(one(client, sem, pid, title, text))
                results = await asyncio.gather(*jobs)
                for pid, species in results:
                    if isinstance(species, dict):   # error marker
                        errors += 1
                        continue
                    for s in species if isinstance(species, list) else []:
                        if not isinstance(s, dict) or not s.get("name"):
                            continue
                        row = {"paper_id": pid,
                               "extracted_at": datetime.now(timezone.utc)
                                   .isoformat(timespec="seconds")}
                        for k in ("name", "kind", "n_total", "n_dead", "outcome",
                                  "clinical", "viral_load", "shedding_days",
                                  "replication", "comparator", "serology",
                                  "clade", "evidence"):
                            row[k] = s.get(k)
                        all_rows.append(row)
                    done.add(pid)
                fresh = pl.DataFrame(all_rows, infer_schema_length=None) \
                    if all_rows else None
                if fresh is not None:
                    for col, dt in (("n_total", pl.Int64), ("n_dead", pl.Int64),
                                    ("shedding_days", pl.Float64),
                                    ("comparator", pl.Boolean)):
                        if col in fresh.columns:
                            fresh = fresh.with_columns(
                                pl.col(col).cast(dt, strict=False))
                    for col in ("paper_id", "extracted_at", "name", "kind",
                                "outcome", "clinical", "viral_load",
                                "replication", "serology", "clade",
                                "evidence"):
                        if col in fresh.columns:
                            fresh = fresh.with_columns(
                                pl.col(col).cast(pl.Utf8, strict=False))
                    if OUT.exists():
                        old = pl.read_parquet(OUT).filter(
                            ~pl.col("paper_id").is_in(
                                fresh["paper_id"].unique().to_list()))
                        fresh = pl.concat([old, fresh], how="diagonal")
                    fresh.write_parquet(OUT)
                # mark done ONLY after rows are safely on disk (crash-safety:
                # a crash here re-extracts the chunk instead of losing it)
                DONE.write_text(json.dumps(sorted(done)))
                print(f"  {min(start + args.chunk, len(todo))}/{len(todo)} "
                      f"papers · {len(all_rows)} species rows · {errors} errors",
                      file=sys.stderr)

    asyncio.run(run())

    prov = json.loads(PROVENANCE.read_text()) if PROVENANCE.exists() \
        else {"calls": []}
    prov["calls"].append({
        "task": "species_phenotypes", "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "papers": len(done), "ts": datetime.now(timezone.utc)
                       .isoformat(timespec="seconds"),
    })
    PROVENANCE.write_text(json.dumps(prov, indent=1))
    print("phenotype extraction complete", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
