#!/usr/bin/env python3
"""Gene alias resolution via LLM — canonical symbols for every extraction name.

The mechanism/gene_involvement extractions use whatever name the paper used
("AIV HEMAGGLUTININ (HA)", "MYXOVIRUS RESISTANCE PROTEIN A", "RIG-I").
This pass sends batches to the LLM and asks it to map each to a canonical
gene symbol (or NOT_A_GENE for processes/concepts). The result is a
persistent alias map (like species_alias_map.json) that future aggregation
runs use for normalization.

Output: data/papers/gene_alias_map.json
Run:  pixi run python scripts/papers/llm_gene_aliases.py
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

PATHWAY_EDGES = ROOT / "web" / "public" / "data" / "pathway_edges.json"
GENE_EV_DIR = ROOT / "web" / "public" / "data" / "gene_evidence"
OUT = ROOT / "data" / "papers" / "gene_alias_map.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """You are building a gene alias dictionary for an avian-influenza
host-factor database. Map each name below to its CANONICAL GENE SYMBOL
(HGNC/NCBI standard, e.g. DDX58 not "RIG-I", IFIH1 not "MDA5").
Rules:
- Viral proteins: use the standard influenza segment name (HA, NA, NP, NS1,
  PB1, PB2, PA, M1, M2, NEP)
- Host proteins: use the official gene symbol, not the protein name
- Mutation-specific names like "PB2 E627K" → just "PB2" (the mutation is
  context, not a different gene)
- If the name is a PROCESS, CONCEPT, or viral entity (not a specific gene
  product), map to "NOT_A_GENE"
- If the name contains a specific gene plus other words, extract just the gene

Return JSON: {{"mappings": [{{"input": "...", "canonical": "..."}}]}}

NAMES:
{names}"""


def collect_names() -> list[str]:
    """All unique gene names from pathway edges + gene evidence files."""
    names = set()
    if PATHWAY_EDGES.exists():
        pe = json.loads(PATHWAY_EDGES.read_text())
        for e in pe["edges"]:
            names.add(e["from"])
            names.add(e["to"])
    if GENE_EV_DIR.exists():
        for f in GENE_EV_DIR.glob("*.json"):
            names.add(f.stem.replace("_", " "))
    return sorted(n for n in names if n and len(n) > 1)


async def resolve_batch(client, sem, names):
    async with sem:
        body = "\n".join(f"  {i+1}. {n}" for i, n in enumerate(names))
        prompt = PROMPT.format(names=body)
        for attempt in range(2):
            try:
                out = await call_llm(client, prompt, 0.1, BASE, MODEL)
                parsed = parse_json_response(out)
                if parsed and isinstance(parsed.get("mappings"), list):
                    return {m["input"]: m["canonical"]
                            for m in parsed["mappings"]
                            if isinstance(m, dict) and m.get("input")}
            except Exception:
                pass
            await asyncio.sleep(3)
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=24)
    args = ap.parse_args()

    names = collect_names()
    print(f"{len(names)} unique gene names to resolve", file=sys.stderr)

    # skip already-clean symbols (regex for standard gene symbols)
    clean_pat = re.compile(r"^[A-Z][A-Z0-9-]{1,10}$")
    needs_llm = [n for n in names if not clean_pat.match(n)]
    already_clean = {n: n for n in names if clean_pat.match(n)}
    # skip already-resolved from a prior run
    existing = {}
    if OUT.exists():
        existing = json.loads(OUT.read_text()).get("aliases", {})
    needs_llm = [n for n in needs_llm if n not in existing]
    already_clean.update({k: v for k, v in existing.items() if k in already_clean})
    print(f"  resuming: {len(needs_llm)} still need LLM", file=sys.stderr)

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        limits = httpx.Limits(max_connections=args.concurrency * 2,
                              max_keepalive_connections=args.concurrency)
        alias = dict(already_clean)
        batches = [needs_llm[i:i+20] for i in range(0, len(needs_llm), 20)]
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0),
                                     limits=limits) as client:
            for bi, batch in enumerate(batches):
                results = await resolve_batch(client, sem, batch)
                alias.update(results)
                print(f"  batch {bi+1}/{len(batches)}: "
                      f"{len(results)}/{len(batch)} resolved "
                      f"(total {len(alias)})", file=sys.stderr)
        return alias

    alias = asyncio.run(run())

    # stats
    not_gene = sum(1 for v in alias.values() if v == "NOT_A_GENE")
    resolved = sum(1 for v in alias.values() if v and v != "NOT_A_GENE")
    OUT.write_text(json.dumps({
        "meta": {
            "generated": datetime.fromtimestamp(
                __import__("time").time(), tz=timezone.utc)
                    .isoformat(timespec="seconds"),
            "n_total": len(alias),
            "n_resolved": resolved,
            "n_not_gene": not_gene,
            "source": "LLM canonicalization (muse-glimmer-30b)",
        },
        "aliases": alias,
    }, indent=1))
    print(f"gene alias map: {len(alias)} entries "
          f"({resolved} genes, {not_gene} not-gene) → {OUT.name}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
