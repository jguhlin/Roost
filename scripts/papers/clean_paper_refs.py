#!/usr/bin/env python3
"""Site-wide deterministic paper-ID cleanup.

Cleans every data file that references paper IDs:
  1. contradictions.parquet — strip year/study_type suffixes, fuzzy-resolve
  2. paper_extras.parquet — remove _dup_* orphans, fix invalid IDs
  3. All extraction parquets — validate paper_id, report + fix
  4. Re-export contradictions.json, pathway_edges.json, gene evidence

After this runs, validate_paper_refs.py should exit 0.

Run:  pixi run python scripts/papers/clean_paper_refs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from resolve_paper_ids import resolve_id, build_index  # noqa: E402

DATA = ROOT / "data" / "papers"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
RENAME_MAP = ROOT / "data" / "papers" / "id_rename_map.json"


def clean_id(raw: str, valid: set, by_norm, by_prefix, by_title) -> str | None:
    """Strip suffix junk, then fuzzy-resolve."""
    if not raw or raw in ("id", "None", "null", ""):
        return None
    if raw in valid:
        return raw
    # strip trailing " YEAR study_type" (including None year)
    stripped = re.sub(r"\s+(?:\d{4}|None)\s+\S+.*$", "", raw).strip()
    if stripped in valid:
        return stripped
    # strip bracket-style suffix
    stripped2 = re.sub(r"\s*\[[^\]]+\]\s*$", "", raw).strip()
    if stripped2 in valid:
        return stripped2
    # fuzzy resolve
    r = resolve_id(stripped or raw, list(valid), {},
                   by_norm, by_prefix, by_title)
    return r


def main() -> int:
    papers_list = json.loads(PAPERS_JSON.read_text())["papers"]
    valid = {p["id"] for p in papers_list}
    titles = {p["id"]: p.get("title", "") for p in papers_list}
    by_norm, by_prefix, by_title = build_index(list(valid), titles)

    # --- 1. contradictions.parquet ---
    x_path = DATA / "contradictions.parquet"
    x = pl.read_parquet(x_path)
    fixed_a, fixed_b, dropped = [], [], 0
    rows = []
    for r in x.iter_rows(named=True):
        ra = clean_id(r.get("paper_a", ""), valid, by_norm, by_prefix, by_title)
        rb = clean_id(r.get("paper_b", ""), valid, by_norm, by_prefix, by_title)
        if ra and rb and ra != rb:
            r = {**r, "paper_a": ra, "paper_b": rb}
            rows.append(r)
        else:
            dropped += 1
    x = pl.DataFrame(rows, infer_schema_length=None,
                     schema=x.schema if rows else None)
    x.write_parquet(x_path)
    print(f"contradictions: {len(rows)} kept, {dropped} dropped "
          f"(self-pair/unresolvable)", file=sys.stderr)

    # --- 2. paper_extras.parquet — remove orphans ---
    e_path = DATA / "paper_extras.parquet"
    e = pl.read_parquet(e_path)
    n_before = e.height
    e = e.filter(pl.col("id").is_in(list(valid)))
    orphaned = n_before - e.height
    e.write_parquet(e_path)
    print(f"extras: {orphaned} orphaned entries removed "
          f"({e.height}/{n_before} kept)", file=sys.stderr)

    # --- 3. all extraction parquets with paper_id columns ---
    for fname in ["paper_key_findings.parquet", "paper_mechanisms.parquet",
                  "paper_quantitative.parquet", "paper_limitations.parquet",
                  "paper_disagreements.parquet", "paper_species_traits.parquet",
                  "typed_claims.parquet", "paper_keywords.parquet"]:
        fpath = DATA / fname
        if not fpath.exists():
            continue
        df = pl.read_parquet(fpath)
        n = df.height
        df = df.filter(pl.col("paper_id").is_in(list(valid)))
        removed = n - df.height
        if removed:
            df.write_parquet(fpath)
            print(f"  {fname}: {removed} orphaned rows removed", file=sys.stderr)

    # --- 4. re-export ---
    import subprocess
    for script in ["export_contradictions.py", "build_aggregation.py"]:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "papers" / script)],
            capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  {script}: ✓", file=sys.stderr)
        else:
            print(f"  {script}: FAILED — {r.stderr[-100:]}", file=sys.stderr)

    # --- 5. validate ---
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "papers" /
                             "validate_paper_refs.py")],
        capture_output=True, text=True)
    if r.returncode == 0:
        print(f"validation: ✓ all paper references valid", file=sys.stderr)
    else:
        print(f"validation: {r.stderr[-200:]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
