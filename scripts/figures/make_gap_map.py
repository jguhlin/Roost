#!/usr/bin/env python3
"""Render an evidence gap map from a JSON spec.

  pixi run python scripts/figures/make_gap_map.py --spec figures/specs/<name>.json

The spec IS the editable figure source (declarative); this renderer writes
figures/preview/<name>.png and figures/export/<name>.{png,svg,pdf} and the
figures/manifests/<name>.json entry. Cell levels: 2 = direct evidence,
1 = adjacent/partial, 0 = nothing found.

Spec schema:
{
  "figure": "fig-x-gap-map", "page": "<briefing-slug>",
  "title": "...", "columns": [{"label": "...", "gap": true}],
  "rows": ["..."], "cells": [[{"level": 2, "text": "..."} | 0 | 1 | 2]],
  "footnote": "...", "note_box": "optional italic box text", "sources": ["pid"]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "figures"))
from style import apply_style, C, source_line  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
apply_style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "figures" / "specs"
PREVIEW = ROOT / "figures" / "preview"
EXPORT = ROOT / "figures" / "export"
MANIFESTS = ROOT / "figures" / "manifests"

LEVEL_STYLE = {
    2: dict(fc=C["primary_soft"], ec=C["primary"], tc="#1e3a8a"),
    1: dict(fc="#f1f5f9", ec="#94a3b8", tc=C["muted"]),
    0: dict(fc=C["alert_soft"], ec="#fca5a5", tc="#b91c1c"),
}
INK, MUTED = C["ink"], C["muted"]


def render(spec: dict) -> None:
    name = spec["figure"]
    cols = spec["columns"]
    rows = spec["rows"]
    cells = spec["cells"]
    assert len(cells) == len(rows) and all(len(r) == len(cols) for r in cells), \
        "cells must be rows×columns"

    ncol, nrow = len(cols), len(rows)
    fig_w = max(9.5, 1.15 + 2.6 * ncol)
    fig_h = max(5.2, 1.5 + 1.55 * nrow)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=160)
    ax.set_xlim(0, ncol)
    ax.set_ylim(0, nrow)
    ax.invert_yaxis()
    ax.axis("off")
    ax.set_title(spec["title"], fontsize=13.5, fontweight="bold",
                 color=INK, loc="left", pad=14)

    for j, c in enumerate(cols):
        is_gap = isinstance(c, dict) and c.get("gap")
        label = c["label"] if isinstance(c, dict) else c
        ax.text(j + 0.5, -0.22, label, ha="center", va="bottom", fontsize=10,
                fontweight="bold" if is_gap else "normal",
                color="#b91c1c" if is_gap else INK)
    for i, r in enumerate(rows):
        ax.text(-0.08, i + 0.5, r, ha="right", va="center",
                fontsize=9.4, color=INK)

    for i in range(nrow):
        for j in range(ncol):
            cell = cells[i][j]
            if isinstance(cell, int):
                level, text = cell, ""
            else:
                level, text = cell.get("level", 0), cell.get("text", "")
            st = LEVEL_STYLE[level]
            ax.add_patch(Rectangle((j + 0.04, i + 0.08), 0.92, 0.84,
                                   fc=st["fc"], ec=st["ec"], lw=2.0, zorder=2))
            if text:
                fs = 8.2 if len(text) < 90 else 7.6
                ax.text(j + 0.5, i + 0.5, text, ha="center", va="center",
                        fontsize=fs, color=st["tc"], zorder=3)
            else:
                ax.text(j + 0.5, i + 0.5, "—", ha="center", va="center",
                        fontsize=13, color="#fca5a5", zorder=3)

    # dashed outline around declared gap columns
    gap_js = [j for j, c in enumerate(cols)
              if isinstance(c, dict) and c.get("gap")]
    for j in gap_js:
        ax.add_patch(Rectangle((j + 0.02, 0.06), 0.96, nrow - 0.1, fc="none",
                               ec="#dc2626", lw=3.2, ls=(0, (6, 4)), zorder=4))
        ax.text(j + 0.5, nrow - 0.02 + 0.08, "THE GAP", ha="center", va="top",
                fontsize=12 if len(gap_js) == 1 else 10.5,
                fontweight="bold", color="#dc2626")

    if spec.get("note_box"):
        ax.text(ncol / 2.0, nrow + 0.32, spec["note_box"], ha="center",
                va="center", fontsize=9.2, color=MUTED, style="italic",
                bbox=dict(boxstyle="round,pad=0.45", fc="#fffbeb",
                          ec="#ca8a04", lw=1.0))

    legend = [("#dbeafe", "#1d4ed8", "direct evidence in corpus"),
              ("#f1f5f9", "#94a3b8", "adjacent / partial"),
              ("#fef2f2", "#fca5a5", "nothing found")]
    for k, (fc, ec, lab) in enumerate(legend):
        x0 = 0.02 + k * 0.30
        ax.add_patch(Rectangle((x0, 3.22), 0.045, 0.16, fc=fc, ec=ec, lw=1.5,
                               transform=ax.transAxes, clip_on=False))
        ax.text(x0 + 0.06, 3.30, lab, fontsize=9, color=MUTED,
                transform=ax.transAxes, va="center")

    fig.text(0.008, 0.004, spec.get("footnote", f"Figure: {name}"),
             fontsize=10, color=C["faint"])

    EXPORT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    fig.savefig(PREVIEW / f"{name}.png", bbox_inches="tight", facecolor=C["surface"])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(EXPORT / f"{name}.{ext}", bbox_inches="tight",
                    facecolor=C["surface"])
    plt.close(fig)

    man = {
        "figure": name, "kind": "gap-map-spec",
        "title": spec["title"], "caption": spec.get("caption", spec["title"]),
        "page": spec["page"], "generated": spec.get("generated", ""),
        "assets": [], "attribution_summary": "",
        "sources": spec.get("sources", []),
        "spec": f"figures/specs/{name}.json",
    }
    (MANIFESTS / f"{name}.json").write_text(
        json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote preview+export for {name} ({ncol}×{nrow}) + manifest")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", required=True, help="path to spec JSON")
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    render(spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
