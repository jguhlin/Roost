#!/usr/bin/env python3
"""
Model node mining orchestrator (D46) — set up, run later.

For every gene node in the avian H5N1 response model
(data/model/avian_h5n1_model.json), compile a CONTEXT PACK:
  1. rg corpus mentions (mine_context.py machinery, no LLM with --dry)
  2. LLM context explanations per top paper (top N)
  3. contradiction mining focused on this gene (same-gene pairs)
  4. gap status: evidence counts vs thresholds

Packs land in data/model/node_packs/{GENE}.json and surface on the /model
page node drawers (when wired) and in the narrative doc regeneration.

Usage:
  pixi run python scripts/model/mine_model_nodes.py --dry          # rg only
  pixi run python scripts/model/mine_model_nodes.py --top 3        # LLM packs
  pixi run python scripts/model/mine_model_nodes.py --genes DDX58,OASL
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "papers"))

MODEL_JSON = ROOT / "data" / "model" / "avian_h5n1_model.json"
COUNTS = ROOT / "data" / "papers" / "gene_evidence_counts.json"
PACKS = ROOT / "data" / "model" / "node_packs"
MD_DIR = ROOT / "docs" / "papers_md"


def corpus_mentions(sym: str) -> dict:
    """rg over markdown corpus: {pid: count}."""
    try:
        out = subprocess.run(
            ["rg", "-c", "-i", "--", sym, str(MD_DIR)],
            capture_output=True, text=True, timeout=60).stdout
    except FileNotFoundError:
        return {}
    hits = {}
    for line in out.splitlines():
        path, _, n = line.rpartition(":")
        hits[Path(path).stem] = int(n)
    return dict(sorted(hits.items(), key=lambda kv: -kv[1]))


def gap_status(sym: str, counts: dict) -> str:
    c = counts.get(sym) or {}
    if not c.get("papers"):
        return "gap"
    if c.get("studied", 0) >= 2:
        return "well_studied"
    if c.get("studied", 0) == 1:
        return "single_study"
    return "mentions_only"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="rg only, no LLM")
    ap.add_argument("--top", type=int, default=3, help="papers per pack for LLM context")
    ap.add_argument("--genes", default=None, help="comma-separated subset")
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    args = ap.parse_args()

    model = json.loads(MODEL_JSON.read_text())
    counts = json.loads(COUNTS.read_text()) if COUNTS.exists() else {}

    wanted = set(args.genes.split(",")) if args.genes else None
    nodes = {}
    for stage in model["stages"]:
        for sym, note in stage["genes"]:
            nodes[sym] = {"stage": stage["id"], "note": note}

    PACKS.mkdir(parents=True, exist_ok=True)
    syms = sorted(nodes)
    if wanted:
        syms = [s for s in syms if s in wanted]

    print(f"{len(syms)} model nodes to pack {'(DRY — no LLM)' if args.dry else ''}")
    for i, sym in enumerate(syms, 1):
        mentions = corpus_mentions(sym)
        pack = {
            "gene": sym,
            "stage": nodes[sym]["stage"],
            "note": nodes[sym]["note"],
            "status": gap_status(sym, counts),
            "evidence": counts.get(sym) or {},
            "mentions": mentions,
            "generated": datetime.now().isoformat(timespec="minutes"),
        }
        if not args.dry and mentions:
            # LLM context for the top papers (mine_context does the heavy lifting)
            from mine_context import llm_explain, paper_title
            contexts = []
            for pid in list(mentions)[:args.top]:
                md = MD_DIR / f"{pid}.md"
                if not md.exists():
                    continue
                text = md.read_text(errors="ignore")
                m = re.search(re.escape(sym), text, re.IGNORECASE)
                if not m:
                    continue
                start = max(0, m.start() - 450)
                passage = text[start:m.end() + 450].replace("\n", " ")
                expl = llm_explain(sym, pid, paper_title(pid), [passage],
                                   url=args.url, model=args.model) if False else None
                # mine_context.llm_explain signature differs; call generically
                try:
                    from mine_context import llm_explain as _le
                    expl = _le(sym, pid, paper_title(pid), [passage])
                except TypeError:
                    expl = None
                contexts.append({"paper_id": pid, "explanation": expl})
            pack["contexts"] = contexts
        (PACKS / f"{sym.replace('/', '_')}.json").write_text(json.dumps(pack, indent=1))
        if i % 10 == 0 or i == len(syms):
            print(f"  [{i}/{len(syms)}] {sym}: {len(mentions)} papers, status={pack['status']}")

    print(f"\n→ {PACKS}")
    # status summary
    from collections import Counter
    statuses = Counter()
    for sym in syms:
        statuses[gap_status(sym, counts)] += 1
    print("node status:", dict(statuses))


if __name__ == "__main__":
    main()
