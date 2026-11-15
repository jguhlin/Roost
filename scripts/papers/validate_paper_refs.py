#!/usr/bin/env python3
"""Site-wide paper-ID validation — deterministic, no LLM.

Scans every data file that references paper_ids and reports any that don't
resolve to a registered paper in papers.json. This is the deterministic
catch for the entire corpus, not just contradictions.

Files checked:
  data/papers/paper_extras.parquet           (id column)
  data/papers/paper_key_findings.parquet     (paper_id)
  data/papers/paper_mechanisms.parquet       (paper_id)
  data/papers/paper_quantitative.parquet     (paper_id)
  data/papers/paper_limitations.parquet      (paper_id)
  data/papers/paper_disagreements.parquet    (paper_id)
  data/papers/paper_species_traits.parquet   (paper_id)
  data/papers/typed_claims.parquet           (paper_id)
  data/papers/paper_keywords.parquet         (paper_id)
  data/papers/contradictions.parquet         (paper_a, paper_b)
  data/papers/paper_species_traits.parquet   (paper_id)
  web/public/data/papers/contradictions.json (a.id, b.id)
  web/public/data/gene_evidence/*.json       (papers[].id, mechanisms[].paper_id)
  web/public/data/pathway_edges.json         (edges[].paper_id)
  web/public/data/research_landscape.json    (contradictions.top_real[].a.id etc.)

Run:  pixi run python scripts/papers/validate_paper_refs.py
Exit 0 = all clean; exit 1 = invalid references found (printed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
DATA = ROOT / "data" / "papers"
WEB = ROOT / "web" / "public" / "data"

PARQUET_COLS = [
    ("paper_extras.parquet", "id"),
    ("paper_key_findings.parquet", "paper_id"),
    ("paper_mechanisms.parquet", "paper_id"),
    ("paper_quantitative.parquet", "paper_id"),
    ("paper_limitations.parquet", "paper_id"),
    ("paper_disagreements.parquet", "paper_id"),
    ("paper_species_traits.parquet", "paper_id"),
    ("typed_claims.parquet", "paper_id"),
    ("paper_keywords.parquet", "paper_id"),
    ("contradictions.parquet", "paper_a"),
    ("contradictions.parquet", "paper_b"),
]


def check_parquet(valid: set, path: Path, col: str) -> list[str]:
    if not path.exists():
        return []
    df = pl.read_parquet(path, columns=[col])
    bad = df.filter(~pl.col(col).is_in(list(valid)) &
                    pl.col(col).is_not_null())[col].unique().to_list()
    return [f"  {path.name}[{col}]: {pid}" for pid in bad]


def check_json(valid: set, path: Path) -> list[str]:
    if not path.exists():
        return []
    d = json.loads(path.read_text())
    bad = []
    # contradictions.json format: list of contradiction dicts
    contras = d.get("contradictions", [])
    if isinstance(contras, list):
        for c in contras:
            if not isinstance(c, dict):
                continue
            for side in ("a", "b"):
                pid = c.get(side, {})
                if isinstance(pid, dict):
                    pid = pid.get("id")
                if pid and pid not in valid:
                    bad.append(f"  {path.name}[{side}.id]: {pid}")
    # landscape format: contradictions is a dict with top_real list
    elif isinstance(contras, dict):
        for c in contras.get("top_real", []):
            if not isinstance(c, dict):
                continue
            for side in ("a", "b"):
                pid = c.get(side)
                if isinstance(pid, dict):
                    pid = pid.get("id")
                if isinstance(pid, str) and pid not in valid:
                    bad.append(f"  {path.name}[top_real.{side}.id]: {pid}")
    return bad


def check_gene_evidence(valid: set, ev_dir: Path) -> list[str]:
    if not ev_dir.exists():
        return []
    bad = []
    for f in sorted(ev_dir.glob("*.json")):
        d = json.loads(f.read_text())
        for p in d.get("papers", []):
            if p.get("id") and p["id"] not in valid:
                bad.append(f"  gene_evidence/{f.name}[papers.id]: {p['id']}")
        for m in d.get("mechanisms", []):
            if m.get("paper_id") and m["paper_id"] not in valid:
                bad.append(f"  gene_evidence/{f.name}[mechanisms.paper_id]: "
                           f"{m['paper_id']}")
    return bad


def check_pathway_edges(valid: set, path: Path) -> list[str]:
    if not path.exists():
        return []
    d = json.loads(path.read_text())
    return [f"  {path.name}[edges.paper_id]: {e['paper_id']}"
            for e in d.get("edges", [])
            if e.get("paper_id") and e["paper_id"] not in valid]


def check_gene_profiles(valid: set, gp_dir: Path) -> list[str]:
    """Gene profiles reference paper IDs in evidence/claims."""
    if not gp_dir.exists():
        return []
    import re as _re
    bad = []
    for f in sorted(gp_dir.glob("*.json")):
        blob = f.read_text(errors="replace")
        # find any paper-ID-like strings that aren't valid
        for pid in _re.findall(r'"(?:paper_id|paper)":\s*"([^"]+)"', blob):
            if pid and pid not in valid and not pid.startswith("http"):
                bad.append(f"  gene_profiles/{f.name}[paper_id]: {pid}")
    return bad


def check_model_json(valid: set, model_path: Path) -> list[str]:
    """The model JSON and other top-level data files."""
    if not model_path.exists():
        return []
    import re as _re
    blob = model_path.read_text(errors="replace")
    bad = []
    for pid in _re.findall(r'"(?:paper_id|paper)":\s*"([^"]+)"', blob):
        if pid and pid not in valid and not pid.startswith("http"):
            bad.append(f"  {model_path.name}[paper_id]: {pid}")
    return bad


def check_text_files(valid: set, data_dir: Path) -> list[str]:
    """JSONL and misc JSON files with paper references."""
    import re as _re
    bad = []
    for f in sorted(data_dir.glob("*.jsonl")) + \
            sorted(data_dir.glob("social_queue.jsonl")):
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(errors="replace").splitlines()[:1000]):
            try:
                d = json.loads(line)
                pid = d.get("paper_id") or d.get("id")
                if pid and pid not in valid:
                    bad.append(f"  {f.name}[line {i+1}]: {pid}")
            except (ValueError, TypeError):
                continue
    return bad


def main() -> int:
    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    valid = {p["id"] for p in papers}
    print(f"valid paper IDs: {len(valid)}", file=sys.stderr)

    all_bad = []

    # parquet files
    for fname, col in PARQUET_COLS:
        all_bad.extend(check_parquet(valid, DATA / fname, col))

    # exported JSON
    all_bad.extend(check_json(valid, WEB / "papers" / "contradictions.json"))
    all_bad.extend(check_json(valid, WEB / "research_landscape.json"))
    all_bad.extend(check_pathway_edges(valid, WEB / "pathway_edges.json"))

    # per-gene evidence
    all_bad.extend(check_gene_evidence(valid, WEB / "gene_evidence"))

    # gene profiles (the old input_2024 source)
    all_bad.extend(check_gene_profiles(valid, WEB / "gene_profiles"))

    # model + spread model + synthesis
    for fname in ["avian_h5n1_model.json", "h5n1_spread_model.json",
                  "synthesis_insights.json", "gene_absence_summary.json",
                  "gene_citations.json"]:
        all_bad.extend(check_model_json(valid, WEB / fname))

    # JSONL files — data files fail, audit logs warn only
    # (intake_ledger is append-only history; model_verdicts is provenance)
    log_only = {"intake_ledger.jsonl", "model_verdicts.jsonl",
                "dedup_log.txt"}
    for f in sorted(DATA.glob("*.jsonl")):
        if f.name in log_only:
            # warn but don't fail
            for i, line in enumerate(f.read_text(errors="replace").splitlines()[:1000]):
                try:
                    d = json.loads(line)
                    pid = d.get("paper_id") or d.get("id")
                    if pid and pid not in valid:
                        print(f"  WARN (log) {f.name}[line {i+1}]: {pid}",
                              file=sys.stderr)
                except (ValueError, TypeError):
                    continue
        else:
            all_bad.extend(check_text_files(valid, DATA / f.name))

    # old-style ID check: any input_2024* reference is a bug
    import re as _re
    for f in sorted(WEB.rglob("*.json")):
        if "node_modules" in str(f):
            continue
        try:
            blob = f.read_text(errors="replace")
        except Exception:
            continue
        for m in _re.findall(r"input_2024\w*", blob):
            all_bad.append(f"  {f.relative_to(WEB)}: STALE ID {m}")

    if all_bad:
        print(f"INVALID PAPER REFERENCES: {len(all_bad)}", file=sys.stderr)
        for line in all_bad[:30]:
            print(line, file=sys.stderr)
        if len(all_bad) > 30:
            print(f"  ... and {len(all_bad) - 30} more", file=sys.stderr)
        return 1
    else:
        print("all paper references valid ✓", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
