#!/usr/bin/env python3
"""
Vaccine-page claims audit (D71) — the sourcing gate.

Goal: everything the vaccine page asserts is backed by a corpus paper,
a curated+flagged web source, or our own deterministic pipeline. This audit
makes that checkable instead of aspirational:

  1. CLAIMS — every load-bearing stage claim must resolve to ≥1 corpus
     paper via its rg probe (claims + probes curated in build_vaccine_model).
  2. TRACKER — every corpus paper-id cited by a tracker entry must exist
     as a markdown file; entries without corpus anchors must carry
     web_verified=false (so the page shows the ⚠ flag).
  3. GENE BRIDGE — every gene must exist in the shipped gene catalogue.
  4. READINESS — the shipped vaccine_readiness.json must exist and its
     anchor species (chicken, mallard, kākāpō) must be scored.

Exit 0 = all sourced. Exit 1 = anything unsourced (CI-able).
Writes data/model/vaccine_claims_audit.md as the human-readable report.

Usage: pixi run python scripts/model/audit_vaccine_claims.py
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "model"))

spec = importlib.util.spec_from_file_location(
    "bvm", ROOT / "scripts" / "model" / "build_vaccine_model.py")
bvm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bvm)

MD_DIR = ROOT / "docs" / "papers_md"
CATALOGUE = ROOT / "web" / "public" / "data" / "gene_catalogue.json"
READINESS = ROOT / "web" / "public" / "data" / "vaccine_readiness.json"
MODEL = ROOT / "web" / "public" / "data" / "h5n1_vaccine_model.json"
REPORT = ROOT / "data" / "model" / "vaccine_claims_audit.md"


def probe(pattern: str) -> list[str]:
    out = subprocess.run(
        ["rg", "-i", "-l", "-e", pattern, "--glob", "*.md", str(MD_DIR)],
        capture_output=True, text=True, timeout=120).stdout
    files = [Path(l).stem for l in out.splitlines()
             if not Path(l).stem.startswith("_")]
    return sorted(files)


def main() -> int:
    failures, lines = [], ["# Vaccine page — claims audit", ""]

    # --- 1. stage claims ---
    lines += ["## Stage claims", "",
              "| stage | claim | corpus papers | status |",
              "|---|---|---|---|"]
    n_claims = n_backed = 0
    for sid, claims in bvm.CLAIMS.items():
        for c in claims:
            papers = probe(c["probe"])
            n_claims += 1
            ok = bool(papers)
            n_backed += ok
            status = f"✅ {len(papers)}pp" if ok else "❌ UNSOURCED"
            if not ok:
                failures.append(f"claim unsourced [{sid}]: {c['claim'][:60]}")
            lines.append(f"| {sid} | {c['claim'][:80]} | "
                         f"{', '.join(papers[:3]) or '—'} | {status} |")
    lines.append(f"\n**Claims: {n_backed}/{n_claims} corpus-backed.**\n")

    # --- 2. tracker entries ---
    lines += ["## Tracker entries", "",
              "| entry | corpus ids valid | flagged for web-verify | status |",
              "|---|---|---|---|"]
    for t in bvm.TRACKER:
        bad = [p for p in t.get("corpus", [])
               if not (MD_DIR / f"{p}.md").exists()]
        needs_flag = not t.get("corpus") and t.get("web_verified") is not False
        ok = not bad and not needs_flag
        if bad:
            failures.append(f"tracker cites missing papers {bad}: {t['name']}")
        if needs_flag:
            failures.append(f"tracker entry has no source & no flag: {t['name']}")
        status = "✅" if ok else "❌"
        lines.append(f"| {t['name'][:40]} | "
                     f"{'all' if not bad else 'MISSING: ' + ','.join(bad)} | "
                     f"{'yes' if t.get('web_verified') is False else '—'} | {status} |")
    lines.append("")

    # --- 3. gene bridge ---
    cat = json.loads(CATALOGUE.read_text())["gene_catalogue"]
    missing = [g["gene"] for g in bvm.GENE_BRIDGE if g["gene"] not in cat]
    lines += ["## Gene bridge", "",
              f"- {len(bvm.GENE_BRIDGE)} genes, "
              f"{'all in catalogue ✅' if not missing else 'MISSING: ' + ', '.join(missing)}",
              ""]
    if missing:
        failures.append(f"gene-bridge genes not in catalogue: {missing}")

    # --- 4. readiness ---
    if READINESS.exists():
        r = json.loads(READINESS.read_text())["species"]
        anchors = [s for s in ("Gallus gallus", "Anas platyrhynchos",
                               "Strigops habroptila") if s in r]
        lines += ["## Readiness", "",
                  f"- {len(r)} species scored; anchors present: "
                  f"{', '.join(anchors)} {'✅' if len(anchors) == 3 else '❌'}", ""]
        if len(anchors) != 3:
            failures.append(f"readiness anchors missing: {len(anchors)}/3")
    else:
        failures.append("vaccine_readiness.json missing — run "
                        "scripts/genes/build_vaccine_readiness.py")

    # --- summary ---
    if failures:
        lines += ["## FAILURES", ""] + [f"- ❌ {f}" for f in failures] + [""
                 , "**AUDIT: FAIL**"]
    else:
        lines += ["**AUDIT: PASS — every vaccine-page claim traces to a source.**"]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines))
    print("\n".join(lines[-3:]))
    print(f"report → {REPORT}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
