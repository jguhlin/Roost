#!/usr/bin/env python3
"""Build per-paper differential-expression (DEG) summaries for the papers page.

DEG lists and counts are properties of a PAPER (an experiment), not of each
gene. Gene pages keep only quantified per-gene findings (fold changes, titres)
— the "this paper found N DEGs" story lives here instead.

Derived deterministically from data/papers/llm_analyses/*.json:
  * count findings — findings mentioning DEGs/differential expression with a
    number (infection-category only; methods criteria like FDR cut-offs are
    skipped)
  * top_genes — the paper's extracted genes whose role text reports an
    expression change (up/down-regulated, induced, elevated ...), with role
    and importance

Output: web/public/data/paper_deg_summaries.json
  { "papers": { "<paper_id>": {
      "count_findings": [{finding, value, context}],
      "top_genes": [{symbol, role, importance}] } } }

Run:  pixi run python scripts/papers/build_deg_summaries.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_DIR = PROJECT_ROOT / "data" / "papers" / "llm_analyses"
OUT = PROJECT_ROOT / "web" / "public" / "data" / "paper_deg_summaries.json"


def load_known_symbols() -> set[str]:
    """Symbols with a real gene page: wiki genes + presence panel catalogue."""
    known: set[str] = set()
    wiki = PROJECT_ROOT / "web" / "public" / "data" / "wiki_genes.json"
    panel = PROJECT_ROOT / "web" / "public" / "data" / "gene_catalogue.json"
    if wiki.exists():
        known |= set(json.loads(wiki.read_text()).get("genes", {}).keys())
    if panel.exists():
        known |= set(json.loads(panel.read_text()).get("gene_catalogue", {}).keys())
    return known

DEG_RE = re.compile(r"differentially expressed|\bDEGs?\b", re.I)
EXPR_ROLE_RE = re.compile(
    r"up-?regulat|down-?regulat|over-?express|under-?express|"
    r"\binduc(?:ed|es|ement)\b|elevated|suppress(?:ed|ion) of expression|"
    r"expression (?:was|is|increas|decreas|higher|lower)|"
    r"higher in resistant|lower in resistant|transcriptional",
    re.I,
)
# criteria-style findings belong to methods, not the infection story
CRITERIA_RE = re.compile(
    r"identification criteria|selection criteria|significance threshold|cut-?off|"
    r"\bFDR\b.*threshold|criteria (?:was|were|for)",
    re.I,
)


def main() -> None:
    papers: dict[str, dict] = {}
    known_symbols = load_known_symbols()

    for path in sorted(LLM_DIR.glob("*.json")):
        try:
            d = json.loads(path.read_text())
        except Exception:
            continue
        steps = d.get("steps", {})

        # --- count findings ------------------------------------------------
        findings = steps.get("findings", {}).get("extracted", {}).get("findings", [])
        count_findings = []
        for f in findings:
            if f.get("category", "infection") == "methods":
                continue
            text = f.get("finding", "")
            if not DEG_RE.search(text):
                continue
            if CRITERIA_RE.search(text) or CRITERIA_RE.search(f.get("context", "")):
                continue
            value = f.get("value", "")
            if not re.search(r"\d", value or ""):
                continue  # only quantified DEG statements
            count_findings.append({
                "finding": text[:300],
                "value": value[:80],
                "context": (f.get("context", "") or "")[:200],
            })

        # --- top expressed genes --------------------------------------------
        genes = steps.get("genes", {}).get("extracted", {}).get("genes", [])
        top_genes = []
        for g in genes:
            role = (g.get("role", "") or "").strip()
            if not role or not EXPR_ROLE_RE.search(role):
                continue
            raw = (g.get("name", "") or "").strip()
            raw = re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()  # strip "(long name)"
            # multi-gene entries ("IFNA, IFNE, IFNG") → one chip each
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            for symbol in parts:
                if not symbol or symbol.lower().startswith(("immunoglobulin", "igg", "igm", "iga")):
                    continue  # antibodies are not gene chips
                if known_symbols and symbol not in known_symbols:
                    continue  # only chip symbols with a real gene page
                top_genes.append({
                    "symbol": symbol,
                    "role": role[:300],
                    "importance": g.get("importance", "mentioned"),
                })
        # central genes first, cap for page readability
        top_genes.sort(key=lambda g: 0 if g.get("importance") == "central" else 1)
        top_genes = top_genes[:12]

        if count_findings or top_genes:
            papers[d.get("paper_id", path.stem)] = {
                "count_findings": count_findings[:4],
                "top_genes": top_genes,
            }

    OUT.write_text(json.dumps({"papers": papers}, ensure_ascii=False, indent=1))
    n_count = sum(1 for p in papers.values() if p["count_findings"])
    n_genes = sum(1 for p in papers.values() if p["top_genes"])
    print(f"DEG summaries: {len(papers)} papers "
          f"({n_count} with count findings, {n_genes} with top genes)")


if __name__ == "__main__":
    main()
