#!/usr/bin/env python3
"""Classify existing key findings and filter garbage extractions.

Two jobs (deterministic, no LLM):

1. CATEGORISE every finding in data/papers/llm_analyses/*.json as
   "infection" or "methods". Methods/QC metrics (alignment rate, reads
   per sample, QC thresholds...) describe HOW the study was done, not
   what it found about infection. They stay in the data (tagged) so
   people digging into papers can still see them, but the wiki builder
   and frontend can separate them.

2. FILTER garbage extractions: table dumps used as gene roles
   (markdown bold markers, gene-list + number-grid text) and truncated
   sentence fragments used as findings. Both are dropped in place.

Run:  pixi run python scripts/papers/classify_findings.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_DIR = PROJECT_ROOT / "data" / "papers" / "llm_analyses"

# --- methods/QC markers (regex, case-insensitive) -------------------------
METHODS_PATTERNS = [
    r"alignment rate",
    r"\baligned\b.*%",            # "aligned to the duck genome" + %
    r"mapping rate",
    r"mapped reads?",
    r"reads per sample",
    r"paired-end reads",
    r"raw sequencing reads",
    r"sequencing depth",
    r"\bQC\b",                     # "Cell-level QC n_genes..."
    r"quality control",
    r"quality-filtered",
    r"adapter trimm",
    r"\bFDR\b.*threshold",
    r"identification criteria",
    r"selection criteria",
    r"significance threshold",
    r"cut-?off",
    r"n_genes (lower|upper) bound",
    r"cells? (passing|retained|filtered)",
    r"genome build",
    r"\bBWA\b|\bbowtie\d?\b|\bSTAR\b",  # aligner tools
    r"library prep",
    r"\bfastq\b",
    r"base pairs?\b.*generated",
    r"on-target rate",
    r"deduplication rate",
]
METHODS_RE = re.compile("|".join(f"(?:{p})" for p in METHODS_PATTERNS), re.I)

# --- garbage detection -----------------------------------------------------
# Table-dump role: many markdown bold markers, or gene-symbol soup
BOLD_SOUP = re.compile(r"\*\*")             # counted
GENE_SOUP = re.compile(r"\b[A-Z][A-Za-z0-9]{1,7}\b(?:\s+[A-Z][A-Za-z0-9]{1,7}\b){6,}")
NUM_GRID = re.compile(r"\b\d+\s+[+-]?\d+\s+[+-]?\d+\s+[+-]?\d+\b")  # "8 6 4 2"


def is_garbage_role(role: str) -> bool:
    if not role:
        return False
    if role.count("**") >= 4:           # markdown table/figure dump
        return True
    if NUM_GRID.search(role):           # number grid from a heatmap legend
        return True
    if GENE_SOUP.search(role) and re.search(r"\d", role):
        # gene-symbol list interleaved with numbers = axis labels
        return True
    return False


def is_garbage_finding(text: str) -> bool:
    if not text:
        return False
    # truncated fragment starting mid-markdown ("s** Our study...")
    if text.lstrip().startswith(("s**", "e**", "y**", "**")) and "**" in text:
        return True
    if text.count("**") >= 4:
        return True
    if NUM_GRID.search(text):
        return True
    # gene-list dump with no verb (heuristic: >6 uppercase tokens, no lowercase sentence)
    words = text.split()
    if len(words) > 8:
        upper = sum(1 for w in words if re.fullmatch(r"[A-Z][A-Za-z0-9]*\d?", w))
        if upper / len(words) > 0.6:
            return True
    return False


def classify(finding_text: str, context: str = "") -> str:
    blob = f"{finding_text} {context}"
    return "methods" if METHODS_RE.search(blob) else "infection"


def main() -> None:
    dry = "--dry-run" in sys.argv
    cats = Counter()
    garbage_roles = garbage_findings = 0
    files_touched = 0

    for path in sorted(LLM_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        steps = data.get("steps", {})
        changed = False

        # --- findings: classify + garbage-filter --------------------------
        findings_step = steps.get("findings")
        if findings_step and isinstance(findings_step.get("extracted"), dict):
            items = findings_step["extracted"].get("findings", [])
            kept = []
            for f in items:
                text = f.get("finding", "")
                if is_garbage_finding(text):
                    garbage_findings += 1
                    changed = True
                    continue
                cat = classify(text, f.get("context", ""))
                if cat != f.get("category"):
                    f["category"] = cat
                    changed = True
                cats[cat] += 1
                kept.append(f)
            if len(kept) != len(items):
                findings_step["extracted"]["findings"] = kept
            # also handle the corrected copy if present
            corr = findings_step.get("corrected")
            if isinstance(corr, dict) and isinstance(corr.get("findings"), list):
                corr["findings"] = [
                    {**f, "category": f.get("category") or classify(f.get("finding", ""), f.get("context", ""))}
                    for f in corr["findings"] if not is_garbage_finding(f.get("finding", ""))
                ]

        # --- genes: drop table-dump roles ----------------------------------
        genes_step = steps.get("genes")
        if genes_step and isinstance(genes_step.get("extracted"), dict):
            items = genes_step["extracted"].get("genes", [])
            kept = []
            for g in items:
                if is_garbage_role(g.get("role", "")):
                    garbage_roles += 1
                    changed = True
                    # keep the gene but blank the garbage role
                    g["role"] = ""
                kept.append(g)
            genes_step["extracted"]["genes"] = kept

        if changed:
            files_touched += 1
            if not dry:
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    print(f"findings classified: {dict(cats)}")
    print(f"garbage findings dropped: {garbage_findings}")
    print(f"garbage roles blanked: {garbage_roles}")
    print(f"files touched: {files_touched}{' (dry-run)' if dry else ''}")


if __name__ == "__main__":
    main()
