#!/usr/bin/env python3
"""LLM enrichment for newly processed papers — muse-glimmer-30b, full text.

Several focused queries per paper, each fed the FULL paper text (131k
context): categorization, summary, effect directions, mutation attribution,
sample-size structure, and the social snippet. Free-text judgements come
from the LLM; deterministic regex candidates are provided as grounding and
kept as *_deterministic columns.

Server: http://127.0.0.1:8005/v1 (sglang, muse-glimmer-30b). Concurrency
48 by default — the box is meant to be hit hard.

Updates:
  data/papers/paper_extras.parquet  (study_type → LLM, summary, effect_
    direction, mutations gene-attributed, sample_sizes structured,
    social_snippet rewritten; originals kept as *_deterministic)
  web/public/data/papers.json       (summaries for the new papers)
  data/papers/llm_provenance.json   (task/model/prompt-version entry)

Run:  pixi run python scripts/papers/llm_enrich_new_papers.py \
          [--ids id1,id2 | --all-extras] [--concurrency 48] [--test-one]
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
EXTRAS = ROOT / "data" / "papers" / "paper_extras.parquet"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"
URL = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")   # base URL — call_llm appends /chat/completions
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
PROMPT_VERSION = "newpaper-enrich-v1"

STUDY_VOCAB = ("experimental_challenge, field_outbreak, serology, "
               "surveillance, review, genomics, vaccine, risk_model, "
               "pathology, diagnostics, other")

QUERIES = {
    "categorize": """You are classifying an avian-influenza research paper.
Return JSON: {{"study_type": [2-4 labels from: VOCAB, most-primary first],
"host_taxa": "domestic birds | wild birds | mammals | humans | mixed | other",
"setting": "one short phrase (country/region + context)",
"confidence": "high | medium | low"}}
VOCAB: {vocab}""",
    "summarize": """Summarize this avian-influenza paper for a research
database in 2-3 sentences (max 60 words total): what was done, in what
species/setting, and the key finding with numbers where available.
No hype, no "this study".
Return JSON: {{"summary": "..."}}""",
    "effects": """Extract every distinct effect studied in this paper.
Direction depends on the effect: for each, record exposure (gene/drug/
virus/intervention), outcome (what was measured), direction (increases |
decreases | no_effect | complex), and a short verbatim evidence quote.
Use REAL values from the paper — never dots or placeholders; if an entry
cannot be filled from the text, omit it. Return JSON:
{{"effects": [{{"exposure": "<real>", "outcome": "<real>",
"direction": "<real>", "evidence": "<real quote>"}}]}} (empty if none).""",
    "mutations": """This paper mentions these candidate mutations (from
automated scanning): {mutations}. Using the full text, attribute each real
viral/host mutation to its gene and significance, DROP spurious matches,
and ADD significant mutations the scanner missed. Return JSON:
{{"mutations": [{{"mutation": "E627K", "gene": "PB2",
"significance": "mammalian adaptation marker"}}]}}""",
    "samples": """Extract the study's sample structure as a clean hashmap.
Return JSON: {{"total_n": <int or null>, "groups": [{{"label": "e.g. wild
birds (mallard)", "n": <int>}}], "hosts": ["species names studied"],
"time_span": "e.g. 2021-2024 or null"}}""",
    "social": """Write a Bluesky post (max 270 chars, no hashtag spam, 1-2
hashtags max) summarizing this paper for bird-flu researchers. MUST start
with the first author surname + " et al." and year, MUST end with the DOI
link. Plain factual tone. Return JSON: {{"post": "..."}}""",
    "genes": """This paper mentions these host/viral genes (automated scan,
with mention counts): {gene_candidates}.
For each gene GENUINELY STUDIED in this paper (not merely name-dropped in
a method or intro), classify its role and capture the finding — this
feeds gene encyclopedia pages and pathway annotation. Return JSON:
{{"genes": [{{"gene": "MX1", "role": "studied | perturbed | measured |
context-only", "finding": "one sentence: what this paper shows about it",
"evidence": "short verbatim quote"}}]}} (empty list if none studied).""",
}


async def run_query(client, sem, paper_id, kind, prompt, retries=2):
    async with sem:
        for attempt in range(retries + 1):
            try:
                out = await call_llm(client, prompt, 0.2, URL, MODEL)
                parsed = parse_json_response(out)
                if parsed:
                    return paper_id, kind, parsed
            except Exception as e:
                if attempt == retries:
                    return paper_id, kind, {"error": str(e)[:120]}
                await asyncio.sleep(3 * (attempt + 1))
        return paper_id, kind, {"error": "no valid JSON"}


def build_prompts(paper: dict, text: str, gene_candidates: str) -> dict[str, str]:
    head = f"TITLE: {paper['title']}\nAUTHORS: {', '.join(paper['authors'][:6])}"
    if paper.get("doi"):
        head += f"\nDOI: https://doi.org/{paper['doi']}"
    muts = json.loads(paper["mutations"]) if paper.get("mutations") else []
    mut_list = ", ".join(m["mutation"] for m in muts[:40]) or "(none found)"
    out = {}
    for kind, tmpl in QUERIES.items():
        body = tmpl.format(vocab=STUDY_VOCAB, mutations=mut_list,
                           gene_candidates=gene_candidates)
        out[kind] = (f"{head}\n\n{body}\n\n=== FULL PAPER TEXT ===\n{text}")
    return out



def merge_paper(paper: dict, q: dict, papers_by_id: dict) -> dict:
    """Apply one paper's query results onto its extras row."""
    r = dict(paper)
    if "categorize" in q and "study_type" in q["categorize"]:
        r["study_type_deterministic"] = r["study_type"]
        r["study_type"] = q["categorize"]["study_type"]
        r["host_taxa"] = q["categorize"].get("host_taxa")
        r["setting"] = q["categorize"].get("setting")
        r["study_confidence"] = q["categorize"].get("confidence")
    if "summarize" in q and q["summarize"].get("summary"):
        r["summary"] = q["summarize"]["summary"]
        if paper["id"] in papers_by_id:
            papers_by_id[paper["id"]]["summary"] = r["summary"]
    if "effects" in q:
        effs = [e for e in q["effects"].get("effects", [])
                if not any(str(v).strip() in ("...", "<real>", "<real quote>")
                           for v in e.values())]
        r["effect_direction"] = json.dumps(effs)
    if "mutations" in q and q["mutations"].get("mutations") is not None:
        r["mutations_llm"] = json.dumps(q["mutations"]["mutations"])
    if "samples" in q:
        r["sample_sizes_structured"] = json.dumps(q["samples"])
    if "genes" in q and q["genes"].get("genes") is not None:
        r["gene_involvement"] = json.dumps(q["genes"]["genes"])
    if "social" in q and q["social"].get("post"):
        r["social_snippet_deterministic"] = r["social_snippet"]
        r["social_snippet"] = q["social"]["post"]
    r["llm_enriched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    r["llm_model"] = MODEL
    return r


async def checkpoint_save(chunk_rows: list[dict]) -> None:
    """Crash-safe incremental write of enriched rows to the extras table."""
    if not chunk_rows:
        return
    fresh = pl.DataFrame(chunk_rows, infer_schema_length=None)
    old = pl.read_parquet(EXTRAS)
    old = old.filter(~pl.col("id").is_in(fresh["id"].to_list()))
    pl.concat([old, fresh], how="diagonal").write_parquet(EXTRAS)


async def main_async(args) -> int:
    extras = pl.read_parquet(EXTRAS)
    if args.ids:
        want = [i.strip() for i in args.ids.split(",")]
        extras = extras.filter(pl.col("id").is_in(want))
    elif args.pending:
        # resumable corpus runs: only rows not yet LLM-enriched
        extras = extras.filter(pl.col("llm_enriched_at").is_null() |
                               ~pl.col("id").is_in(
                                   pl.read_parquet(EXTRAS)
                                     .filter(pl.col("llm_enriched_at").is_not_null())
                                     ["id"].to_list()))
    if args.test_one:
        extras = extras.head(1)

    # gene-hit candidates from the paper database (grounding for the genes
    # query; downstream: gene pages + pathway annotation)
    pdb = pl.read_parquet(ROOT / "data" / "papers" / "paper_db.parquet")
    gene_hits_by_id = {}
    for r in pdb.iter_rows(named=True):
        if r.get("gene_hits") and r["gene_hits"] != "{}":
            gh = json.loads(r["gene_hits"])
            gene_hits_by_id[r["id"]] = ", ".join(
                f"{g} (×{d['n']})" for g, d in
                sorted(gh.items(), key=lambda kv: -kv[1]["n"])[:25])

    sem = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency * 2,
                          max_keepalive_connections=args.concurrency)
    papers_doc = json.loads(PAPERS_JSON.read_text())
    papers_by_id = {p["id"]: p for p in papers_doc["papers"]}
    papers_list = list(extras.iter_rows(named=True))
    starts = list(range(0, len(papers_list), args.chunk))
    total_errors = 0
    print(f"{len(papers_list)} papers x {len(QUERIES)} queries in "
          f"{len(starts)} checkpoints of {args.chunk} "
          f"@ concurrency {args.concurrency}", file=sys.stderr)
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0),
                                 limits=limits) as client:
        for ci, start_i in enumerate(starts):
            chunk = papers_list[start_i:start_i + args.chunk]
            jobs = []
            for paper in chunk:
                md = MD_DIR / f"{paper['id']}.md"
                text = md.read_text(errors="replace") if md.exists() else ""
                if len(text) < 500:
                    print(f"  WARN {paper['id']}: no md text", file=sys.stderr)
                    continue
                prompts = build_prompts(
                    paper, text,
                    gene_hits_by_id.get(paper["id"], "(none found)"))
                for kind, prompt in prompts.items():
                    jobs.append(run_query(client, sem, paper["id"], kind,
                                          prompt))
            results = await asyncio.gather(*jobs)
            by_paper = {}
            for pid, kind, parsed in results:
                if "error" in parsed:
                    total_errors += 1
                by_paper.setdefault(pid, {})[kind] = parsed
            rows = [merge_paper(p, by_paper.get(p["id"], {}), papers_by_id)
                    for p in chunk]
            await checkpoint_save(rows)
            print(f"  checkpoint {ci + 1}/{len(starts)} done "
                  f"({min(start_i + args.chunk, len(papers_list))}/"
                  f"{len(papers_list)} papers, {total_errors} errors so far)",
                  file=sys.stderr)
    errors = total_errors
    print(f"done: {errors} total query errors", file=sys.stderr)
    # extras were checkpoint-saved per chunk; write papers.json summaries +
    # provenance (paper rows for provenance = every enriched id this run)
    PAPERS_JSON.write_text(json.dumps(papers_doc, indent=1))
    enriched_ids = [p["id"] for p in papers_list]

    # provenance
    prov = json.loads(PROVENANCE.read_text()) if PROVENANCE.exists() else {"calls": []}
    prov["calls"].append({
        "task": "new_paper_enrichment", "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "papers": enriched_ids,
        "queries_per_paper": len(QUERIES),
        "errors": errors,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    PROVENANCE.write_text(json.dumps(prov, indent=1))
    print(f"enriched {len(enriched_ids)} papers → extras (checkpointed) + "
          f"papers.json + provenance", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated paper ids (default: all extras)")
    ap.add_argument("--pending", action="store_true",
                    help="only papers not yet LLM-enriched (resumable)")
    ap.add_argument("--all-extras", action="store_true")
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--test-one", action="store_true")
    ap.add_argument("--chunk", type=int, default=50,
                    help="papers per checkpoint save (crash-safe on long runs)")
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
