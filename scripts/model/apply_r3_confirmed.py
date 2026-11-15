#!/usr/bin/env python3
"""
Apply double-confirmed R3 stage additions (D81).

Parses data/model/r3_proposals.md for gene additions marked ✅ (skeptic
confirmed) and writes them to data/papers/connections/gene_overrides.json —
the explicit-review path assign_stages.py honours. When a gene is confirmed
for several stages the FIRST proposal wins and the alternatives are recorded
in the note for the curator. Fully reversible: delete an entry to revert.

Usage:
  pixi run python scripts/model/apply_r3_confirmed.py          # show plan
  pixi run python scripts/model/apply_r3_confirmed.py --apply  # write overrides
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
REPORT = ROOT / "data" / "model" / "r3_proposals.md"
OVERRIDES = ROOT / "data" / "papers" / "connections" / "gene_overrides.json"


def parse_confirmed_adds():
    if not REPORT.exists():
        return []
    adds = []
    stage = None
    in_additions = False
    for line in REPORT.read_text().splitlines():
        m = re.match(r"^## (\w[\w-]*) — ", line)
        if m:
            stage = m.group(1)
            in_additions = False
            continue
        if line.startswith("### Proposed gene additions"):
            in_additions = True
            continue
        if line.startswith("###"):
            in_additions = False
            continue
        if in_additions and stage:
            m = re.match(r"^- ✅ \*\*([A-Za-z0-9][A-Za-z0-9._-]*)\*\* — (.+)$",
                         line.strip())
            if m and "--" not in m.group(1):   # gene adds, not edge notes
                adds.append({"stage": stage, "symbol": m.group(1),
                             "reason": m.group(2).strip()})
    return adds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    raw = parse_confirmed_adds()
    if not raw:
        print("no confirmed gene additions found in r3_proposals.md")
        return

    # one stage per gene: first confirmed proposal wins, alternatives noted
    deduped = {}
    order = []
    for a in raw:
        if a["symbol"] in deduped:
            deduped[a["symbol"]].setdefault("alt_stages", []).append(a["stage"])
        else:
            deduped[a["symbol"]] = a
            order.append(a["symbol"])

    existing = {}
    if OVERRIDES.exists():
        existing = json.loads(OVERRIDES.read_text())

    print(f"{len(raw)} confirmed addition(s) → {len(order)} genes:")
    for sym in order:
        a = deduped[sym]
        cur = existing.get(sym, {})
        alts = f" (also proposed: {', '.join(a['alt_stages'])})" \
            if a.get("alt_stages") else ""
        print(f"  {sym:10s} → {a['stage']:16s} "
              f"(current override: {cur.get('stage', '—')}){alts}")
        print(f"      {a['reason'][:110]}")

    if not args.apply:
        print("\n(dry run — pass --apply to write gene_overrides.json)")
        return

    for sym in order:
        a = deduped[sym]
        alts = f"; also proposed for {', '.join(a['alt_stages'])}" \
            if a.get("alt_stages") else ""
        existing[sym] = {
            "stage": a["stage"],
            "note": f"r3 confirmed addition (LLM double-confirmed{alts}): "
                    f"{a['reason'][:180]}",
        }
    OVERRIDES.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES.write_text(json.dumps(existing, indent=1, ensure_ascii=False))
    print(f"\nwrote {len(order)} override(s) → {OVERRIDES.relative_to(ROOT)}")
    print("next: pixi run python scripts/genes/assign_stages.py")


if __name__ == "__main__":
    main()
