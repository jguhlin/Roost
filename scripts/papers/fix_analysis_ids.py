#!/usr/bin/env python3
"""Fix paper-analysis identifiers and quarantine orphaned analyses.

Problem: rename_paper_ids.py renamed corpus papers (papers.json, markdown)
but the LLM analysis stores kept the OLD ids (input_*/paper_*/read_*).
Consequences:
  * wiki key findings cite dead paper ids (broken links)
  * metadata lookups fail (empty title/year/journal in wiki citations)
  * 47 analyses belong to papers no longer in the corpus (orphaned) and
    their findings pollute wiki pages.

This script:
  1. renames stale analysis files + their internal paper_id
     (llm_analyses/, analyses/, internal/)
  2. moves orphaned analyses to *_orphaned/ quarantine dirs

Run:  pixi run python scripts/papers/fix_analysis_ids.py [--dry-run]
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RENAME_MAP = json.loads(
    (PROJECT_ROOT / "data" / "papers" / "id_rename_map.json").read_text()
)
PAPERS_JSON = json.loads(
    (PROJECT_ROOT / "web" / "public" / "data" / "papers.json").read_text()
)
CORPUS_IDS = {p["id"] for p in PAPERS_JSON.get("papers", [])}

# analysis stores: (dir, internal-id-key)
STORES = [
    (PROJECT_ROOT / "data" / "papers" / "llm_analyses", "paper_id"),
    (PROJECT_ROOT / "data" / "papers" / "analyses", "paper_id"),
    (PROJECT_ROOT / "data" / "papers" / "internal", "paper_id"),
]


def resolve(pid: str) -> str:
    """Follow rename map (handles chained renames defensively)."""
    seen = set()
    while pid in RENAME_MAP and pid not in seen:
        seen.add(pid)
        pid = RENAME_MAP[pid]
    return pid


def main() -> None:
    dry = "--dry-run" in sys.argv
    renamed = quarantined = updated = 0

    for store, id_key in STORES:
        if not store.exists():
            continue
        orphan_dir = store.parent / (store.name + "_orphaned")
        for path in sorted(store.glob("*.json")):
            old_id = path.stem
            new_id = resolve(old_id)
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue

            in_corpus = new_id in CORPUS_IDS and not old_id.startswith("_")

            if not in_corpus:
                # Orphaned or duplicate: quarantine
                dest = orphan_dir / path.name
                if not dry:
                    orphan_dir.mkdir(exist_ok=True)
                    shutil.move(str(path), str(dest))
                quarantined += 1
                continue

            if new_id != old_id:
                # Rename file + internal id
                dest = store / f"{new_id}.json"
                if dest.exists():
                    # already renamed copy exists; drop the stale one
                    if not dry:
                        path.unlink()
                    continue
                data[id_key] = new_id
                if not dry:
                    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                    shutil.move(str(path), str(dest))
                renamed += 1
            elif data.get(id_key) != new_id:
                data[id_key] = new_id
                if not dry:
                    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                updated += 1

    action = "would rename" if dry else "renamed"
    print(f"{action}: {renamed} files (filename + internal id)")
    print(f"{'would quarantine' if dry else 'quarantined'}: {quarantined} orphaned analyses")
    print(f"internal-id-only updates: {updated}")


if __name__ == "__main__":
    main()
