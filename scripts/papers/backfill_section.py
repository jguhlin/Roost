#!/usr/bin/env python3
"""Re-run ONE extraction section for already-done papers (targeted repass).

Used when a section's prompt was broken or weak (e.g. seasonality's
missing {"item":…} wrapper; introduction_events' missing direction field):
re-runs just that section for every done paper whose file has an empty
OR stale result, updating the per-paper JSON in place.

Usage:
  pixi run python scripts/papers/backfill_section.py --section introduction_events [--workers 32] [--force]
--force re-runs even when the section has items (prompt improved; existing
items are REPLACED, so only use when the new prompt strictly supersedes).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm_extract_spread as ex  # noqa: E402
import httpx  # noqa: E402


def load_papers() -> list[dict]:
    return json.loads(ex.PAPERS_JSON.read_text())["papers"]


def load_mds() -> dict:
    out = {}
    for f in Path(ex.MD_DIR).glob("*.md"):
        if f.stat().st_size >= 1000:
            out[f.stem] = f.read_text(errors="replace")
    return out


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", required=True)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--force", action="store_true",
                    help="re-run even when the section already has items")
    ap.add_argument("--backup", action="store_true",
                    help="with --force: copy affected per-paper JSONs to "
                         "data/papers/spread_v2_backup_<section>/ first "
                         "(force REPLACES items; keep an escape hatch)")
    args = ap.parse_args()
    section = args.section
    if section not in ex.SECTIONS:
        print(f"unknown section {section}; valid: {', '.join(ex.SECTIONS)}")
        return 2

    papers = {p["id"]: p for p in load_papers()}
    mds = load_mds()
    targets = []
    for f in sorted(ex.OUT_DIR.glob("*.json")):
        pid = f.stem
        if pid not in papers or pid not in mds:
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if args.force or not d.get("sections", {}).get(section):
            targets.append((pid, f, d))
    print(f"papers needing {section}: {len(targets)}{' (forced)' if args.force else ''}")
    if not targets:
        return 0

    if args.force and args.backup:
        bdir = ex.OUT_DIR.parent / f"spread_v2_backup_{section}"
        bdir.mkdir(exist_ok=True)
        import shutil
        for _, f, _ in targets:
            shutil.copy2(f, bdir / f.name)
        print(f"backed up {len(targets)} files → {bdir.name}")

    sem = asyncio.Semaphore(args.workers)
    done = 0
    nonempty = 0

    async with httpx.AsyncClient(timeout=600.0) as client:

        async def one(pid, f, d):
            nonlocal done, nonempty
            text = mds[pid][: ex.MAX_CHARS]
            header = ex.HEADER.format(
                title=(papers[pid].get("title") or "")[:200],
                scope=papers[pid].get("scope") or "?",
                year=papers[pid].get("year") or "?",
                text=text,
            )
            items = await ex.extract_section(client, sem, pid, text,
                                             header, section)
            d["sections"][section] = items
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1))
            done += 1
            if items:
                nonempty += 1
            if done % 50 == 0:
                print(f"  {done}/{len(targets)} re-run, {nonempty} with items")

        await asyncio.gather(*(one(pid, f, d) for pid, f, d in targets))

    print(f"done: {done} papers re-run, {nonempty} with {section} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
