#!/usr/bin/env python3
"""Gap ledger — track research gaps opened/closed between runs.

Snapshots the synthesised gap list (data/papers/research_gaps.json → "gaps")
each run into a persistent ledger and diffs consecutive snapshots.

Output: web/public/data/gap_ledger.json
  {"meta": {...}, "current": {gap: {"status": "open"|"closed", "since": ts,
                                    "first_seen": ts}},
   "history": [{"ts": ..., "n_open": N, "opened": [...], "closed": [...]}]}
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAPS = ROOT / "data" / "papers" / "research_gaps.json"
LEDGER = ROOT / "data" / "papers" / "gap_ledger.json"
OUT = ROOT / "web" / "public" / "data" / "gap_ledger.json"


def norm_gap(g: str) -> str:
    return " ".join(g.split())


def main() -> int:
    if not GAPS.exists():
        print("research_gaps.json missing", file=sys.stderr)
        return 1
    gaps_raw = json.loads(GAPS.read_text(encoding="utf-8")).get("gaps", [])
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # gaps may be plain strings or {title, why, study_needed} dicts — key on title
    current_gaps: dict[str, str] = {}
    for g in gaps_raw:
        if isinstance(g, dict):
            t = norm_gap(str(g.get("title", "")))
            if t:
                current_gaps[t] = json.dumps(g, ensure_ascii=False)
        elif isinstance(g, str) and g.strip():
            current_gaps[norm_gap(g)] = g

    ledger = {"current": {}, "history": []}
    if LEDGER.exists():
        try:
            ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    prev: dict[str, dict] = ledger.get("current", {})
    prev_gaps = set(prev)

    opened = sorted(set(current_gaps) - prev_gaps)
    closed = sorted(prev_gaps - set(current_gaps))

    current: dict[str, dict] = {}
    for g, body in current_gaps.items():
        old = prev.get(g, {})
        current[g] = {"status": "open", "since": old.get("since", now),
                      "first_seen": old.get("first_seen", now), "body": body}
    for g in closed:
        old = prev.get(g, {})
        current[g] = {"status": "closed", "since": now,
                      "first_seen": old.get("first_seen", now)}

    entry = {"ts": now, "n_open": len(current_gaps),
             "n_new": len(opened), "n_closed": len(closed),
             "opened": opened, "closed": closed}
    if not ledger.get("history") or ledger["history"][-1]["n_open"] != entry["n_open"] \
            or opened or closed:
        ledger["history"].append(entry)

    ledger["current"] = current
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tag = "baseline established" if not prev else \
          f"{len(opened)} opened, {len(closed)} closed"
    print(f"gap ledger → {OUT.relative_to(ROOT)} ({len(current_gaps)} open; {tag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
