#!/usr/bin/env python3
"""Execute figure_proposals from research briefings → published figures.

Closes the loop: the research agent proposes figures (gap-map specs mostly)
during synthesis; this renders them via the spec-driven gap-map generator,
writes manifests, and publishes to the briefing's page. Deterministic —
no LLM here.

  pixi run python scripts/papers/execute_figure_proposals.py [--slug NAME]

Without --slug: scan ALL briefings for unexecuted proposals.
Execution marker: the figure's manifest records {"from_proposal": slug, ...};
a proposal whose generated figure name already exists is skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIEF = ROOT / "web" / "public" / "data" / "research_briefings"
SPECS = ROOT / "figures" / "specs"
MANIFESTS = ROOT / "figures" / "manifests"

sys.path.insert(0, str(ROOT / "scripts" / "figures"))
from make_gap_map import render as render_gap_map  # noqa: E402


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48].rstrip("-")


def cite_to_credits(b: dict) -> list[str]:
    """[paper_id] citations referenced in the proposal caption/sections —
    recorded as figure sources (deterministic provenance)."""
    ids = set()
    for sec in b.get("sections", []):
        ids.update(re.findall(r"\[([a-z0-9_\-\.]+)\]", sec.get("body", "")))
    return sorted(ids)[:8]


def execute(b: dict, i: int, prop: dict, done: list[str]) -> str | None:
    slug = b["slug"]
    kind = prop.get("kind", "gap-map")
    if kind != "gap-map":
        done.append(f"SKIP {slug} #{i}: kind={kind} (only gap-maps are "
                    f"auto-rendered; diagrams need the figure pipeline)")
        return None
    cols, rows, cells = prop.get("columns"), prop.get("rows"), prop.get("cells")
    if not (isinstance(cols, list) and isinstance(rows, list)
            and isinstance(cells, list) and len(cells) == len(rows)
            and all(isinstance(r, list) and len(r) == len(cols) for r in cells)):
        done.append(f"SKIP {slug} #{i}: malformed matrix")
        return None
    if not (1 <= len(cols) <= 5 and 1 <= len(rows) <= 6):
        done.append(f"SKIP {slug} #{i}: matrix {len(cols)}x{len(rows)} out of bounds")
        return None
    # sanitize: clamp levels, stringify labels
    cols = [str(c)[:60] for c in cols]
    rows = [str(r)[:60] for r in rows]
    def _lvl(c):
        if isinstance(c, dict):
            c = c.get("level", 0)
        try:
            return max(0, min(2, int(c)))
        except (TypeError, ValueError):
            return 0
    cells = [[_lvl(c) for c in row] for row in cells]

    name = f"fig-{slugify(slug)}-auto{i}" if len(
        json.dumps(prop)) else None
    name = f"fig-{slugify(slug)[:38]}-auto"
    # avoid clobbering a manual figure with the same name
    if (MANIFESTS / f"{name}.json").exists():
        m = json.loads((MANIFESTS / f"{name}.json").read_text())
        if m.get("from_proposal") == slug:
            done.append(f"SKIP {slug}: proposal already executed ({name})")
            return None
        name = f"{name}-{i}"

    columns = [{"label": c, "gap": j == len(cols) - 1}
               for j, c in enumerate(cols)]
    spec = {
        "figure": name, "page": slug,
        "title": prop.get("title") or b.get("title", slug)[:90],
        "columns": columns, "rows": rows,
        "cells": [[c if isinstance(c, (int,)) else (c.get("level", 0) if isinstance(c, dict) else 0)
                   for c in row] for row in cells],
        "note_box": prop.get("note_box", ""),
        "caption": prop.get("caption") or prop.get("title") or "",
        "footnote": f"Proposed by the research agent during briefing synthesis — "
                    f"figure: {name} (auto-rendered).",
        "sources": cite_to_credits(b),
        "generated": str(date.today()),
    }
    (SPECS / f"{name}.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render_gap_map(spec)
    m_path = MANIFESTS / f"{name}.json"
    m = json.loads(m_path.read_text())
    m["from_proposal"] = slug
    m["kind"] = "gap-map (agent-proposed)"
    m_path.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")

    r = subprocess.run([sys.executable, str(ROOT / "scripts/figures/publish_figure.py"),
                        "--figure", name, "--page", slug],
                       capture_output=True, text=True)
    if r.returncode != 0:
        done.append(f"FAIL {slug}: publish failed — {r.stderr.strip()[:120]}")
        return None
    done.append(f"OK   {slug} → {name} ({len(cols)}×{len(rows)} gap map)")
    return name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", help="only this briefing")
    args = ap.parse_args()

    done: list[str] = []
    files = sorted(BRIEF.glob("*.json"))
    for f in files:
        if f.name == "index.json":
            continue
        b = json.loads(f.read_text(encoding="utf-8"))
        if args.slug and b.get("slug") != args.slug:
            continue
        for i, prop in enumerate(b.get("figure_proposals") or []):
            try:
                execute(b, i, prop, done)
            except Exception as e:  # never let one bad proposal stop the run
                done.append(f"FAIL {b.get('slug', f.stem)} #{i}: {type(e).__name__}: {e}")

    for line in done:
        print(line)
    if not done:
        print("no figure_proposals found in briefings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
