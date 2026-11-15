#!/usr/bin/env python3
"""
LLM provenance tracker (D90): centralized registry of every LLM-driven
extraction/decision pass, with model, prompt version, date, affected records,
and notes. Written to data/papers/llm_provenance.json.

Usage from other scripts:
    from llm_provenance import track
    track("summaries", "muse-glimmer-30b", "v2", 695,
          notes="rebuilt all paper summaries")

    # or with specific paper IDs:
    track("topic_extraction", "muse-glimmer-30b", "topics-v2",
          ["paper1", "paper2"], notes="assigned topics to 2 papers")

CLI:
    pixi run python scripts/papers/llm_provenance.py           # show log
    pixi run python scripts/papers/llm_provenance.py --summary # grouped stats
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"


def load():
    if PROVENANCE.exists():
        try:
            return json.loads(PROVENANCE.read_text())
        except Exception:
            pass
    return {"calls": []}


def track(task, model, prompt_version, affected, notes=""):
    """Record one LLM pass. `affected` is a count or list of IDs."""
    prov = load()
    entry = {
        "task": task,
        "model": model,
        "prompt_version": prompt_version,
        "total": len(affected) if isinstance(affected, (list, set)) else affected,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "notes": notes,
    }
    if isinstance(affected, (list, set)):
        entry["ids"] = sorted(affected)[:50]  # cap for file size
    prov["calls"].append(entry)
    PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    PROVENANCE.write_text(json.dumps(prov, indent=1, ensure_ascii=False))
    return entry


def summary():
    prov = load()
    calls = prov.get("calls", [])
    if not calls:
        print("no provenance entries yet")
        return
    by_task = defaultdict(list)
    for c in calls:
        by_task[c["task"]].append(c)
    print(f"total LLM passes recorded: {len(calls)}")
    print()
    for task in sorted(by_task):
        entries = by_task[task]
        total = sum(e.get("total", 0) for e in entries)
        latest = entries[-1]
        print(f"  {task:30s} {len(entries):>3} pass(es) | {total:>6} records | "
              f"latest: {latest['ts'][:10]} | model: {latest['model']} | "
              f"prompt: {latest.get('prompt_version', '?')}")
        if latest.get("notes"):
            print(f"    └─ {latest['notes'][:100]}")


def full_log():
    prov = load()
    for c in prov.get("calls", []):
        print(json.dumps(c, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    if args.summary:
        summary()
    elif args.full:
        full_log()
    else:
        summary()


if __name__ == "__main__":
    main()
