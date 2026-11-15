#!/usr/bin/env python3
"""Recurring LLM enrichment pipeline — run every pass on whatever is pending.

New papers land via process_new_papers.py (PDF intake). This orchestrator
then brings them up to the full extraction standard, pass by pass, each
resuming from its own done-file (papers already processed are skipped):

  1. key findings + keywords   (llm_key_findings.py)
  2. species phenotypes        (llm_extract_phenotypes.py)
  3. mechanisms                (llm_extract_mechanisms.py)
  4. 7-field enrichment        (llm_enrich_new_papers.py --pending)
  5. claim typing              (llm_type_claims.py)
  6. species-name normalization (normalize_species_names.py)

Periodic (not per-paper — rerun after big batches):
  7. contradiction adjudication --reset  (llm_claims_adjudicate.py)
  8. research gaps rebuild      (build_research_gaps.py)
  9. exports: contradictions.json, paper index refresh

Usage:
  pixi run python scripts/papers/enrich_pipeline.py            # pending only
  pixi run python scripts/papers/enrich_pipeline.py --with-adjudication
  pixi run python scripts/papers/enrich_pipeline.py --ids id1,id2
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "scripts" / "papers"
DATA = ROOT / "data" / "papers"

DONE_FILES = {
    "findings+keywords": DATA / "keyfindings_done.json",
    "phenotypes": DATA / "phenotypes_done.json",
    "mechanisms": DATA / "mechanisms_done.json",
    "enrichment": None,   # tracked via llm_enriched_at in paper_extras
    "typing": DATA / "claim_typing_done.json",
}

STEPS = [
    ("findings+keywords",
     ["llm_key_findings.py", "--concurrency", "32", "--chunk", "25"]),
    ("phenotypes",
     ["llm_extract_phenotypes.py", "--concurrency", "24", "--chunk", "50"]),
    ("mechanisms",
     ["llm_extract_mechanisms.py", "--concurrency", "32", "--chunk", "25"]),
    ("enrichment",
     ["llm_enrich_new_papers.py", "--pending", "--concurrency", "48",
      "--chunk", "50"]),
    ("typing",
     ["llm_type_claims.py", "--concurrency", "32", "--chunk", "25"]),
    # --- spread-model evidence (SPREAD_MODEL.md Phase 6): resume-safe, one
    #     JSON per paper in data/papers/spread_v2/, aggregate below ---
    ("spread-evidence",
     ["llm_extract_spread.py", "--workers", "24"]),
    ("normalize", ["normalize_species_names.py"]),
    # --- database-level constraint: no invalid paper refs leave the pipeline ---
    ("cleanup-paper-refs", ["clean_paper_refs.py"]),
]


def pending_papers() -> set:
    """Papers with markdown that are missing from ANY pass's done-set."""
    mds = {p.stem for p in (ROOT / "docs" / "papers_md").glob("*.md")}
    done_union = set()
    for f in DONE_FILES.values():
        if f and f.exists():
            done_union |= set(json.loads(f.read_text()))
    if (DATA / "paper_extras.parquet").exists():
        import polars as pl
        e = pl.read_parquet(DATA / "paper_extras.parquet")
        done_union |= set(e.filter(pl.col("llm_enriched_at").is_not_null())
                          ["id"].to_list())
    return mds - done_union


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="restrict to these paper ids")
    ap.add_argument("--with-adjudication", action="store_true",
                    help="also reset+rerun contradiction adjudication and "
                         "rebuild research gaps/exports (slow; after batches)")
    args = ap.parse_args()

    pend = pending_papers()
    print(f"papers pending at least one pass: {len(pend)}", file=sys.stderr)
    if not pend and not args.with_adjudication:
        print("nothing to do", file=sys.stderr)
        return 0

    import os
    env_extra = {**os.environ, "LLM_MAX_TOKENS": "8192"}
    for name, cmd in STEPS:
        argv = [sys.executable, str(P / cmd[0]), *cmd[1:]]
        if args.ids and "--ids" in (" ".join(cmd)):
            argv += ["--ids", args.ids]
        print(f"\n=== {name}: {' '.join(cmd)}", file=sys.stderr)
        r = subprocess.run(argv, env=env_extra)
        if r.returncode != 0:
            print(f"  WARN {name} exited {r.returncode} — continuing",
                  file=sys.stderr)

    if args.with_adjudication:
        (DATA / "adjudication_done.json").write_text("[]")
        subprocess.run([sys.executable, str(P / "llm_claims_adjudicate.py"),
                        "--concurrency", "32", "--chunk", "25",
                        "--min-papers", "3"], env=env_extra)
        subprocess.run([sys.executable, str(P / "build_research_gaps.py")])
        subprocess.run([sys.executable, str(P / "export_contradictions.py")])

    # --- database-level constraint: validation gate ---
    # the pipeline does not succeed if any paper reference is invalid
    print("\n=== VALIDATION GATE", file=sys.stderr)
    vr = subprocess.run([sys.executable,
                          str(P / "validate_paper_refs.py")],
                         env=env_extra)
    if vr.returncode != 0:
        print("PIPELINE FAILED: invalid paper references detected. "
              "Run clean_paper_refs.py and investigate.", file=sys.stderr)
        return 1
    print("validation: all paper references valid ✓", file=sys.stderr)

    print("\npipeline complete", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
