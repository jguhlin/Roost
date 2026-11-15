#!/usr/bin/env python3
"""SVG text-geometry lint for figure sources.

Parses an SVG, measures every <text> with real Lato advance metrics
(same engine as make_fig1.py), and reports:

  1. text ↔ text bbox overlaps          (label collisions)
  2. text ↔ <image> bbox overlaps       (labels over embedded screenshots —
                                         fine for halo'd callouts, flagged
                                         for everything else)
  3. text outside the canvas

Exit 0 = clean, 1 = findings. Tunable tolerance in px (default 1).

Usage: python3 scripts/figures/svg_text_lint.py figures/src/fig1_overview.svg
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath

TTP = TextToPath()
TOL = 1.0  # px — overlaps smaller than this are rounding noise


def measure(s: str, size: float, weight: float, spacing: float) -> float:
    fp = FontProperties(family="Lato", weight=weight, size=size)
    w, _h, _d = TTP.get_text_width_height_descent(s, fp, ismath=False)
    return w + max(len(s) - 1, 0) * spacing


def texts(root, ns):
    for el in root.iter(f"{ns}text"):
        content = "".join(el.itertext())
        if not content.strip():
            continue
        x = float(el.get("x", "0"))
        y = float(el.get("y", "0"))
        fs = float(re.sub(r"[^0-9.]", "", el.get("font-size", "14")) or 14)
        fw = float(el.get("font-weight", "400") or 400)
        sp = float(el.get("letter-spacing", "0") or 0)
        anchor = el.get("text-anchor", "start")
        w = measure(content, fs, fw, sp)
        left = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
        halo = float(el.get("stroke-width", "0") or 0)
        yield {"s": content, "left": left, "right": left + w,
               "top": y - fs * 0.78, "bottom": y + fs * 0.22, "halo": halo,
               "x": x, "y": y}


def images(root, ns):
    for el in root.iter(f"{ns}image"):
        yield {"left": float(el.get("x", "0")),
               "right": float(el.get("x", "0")) + float(el.get("width", "0")),
               "top": float(el.get("y", "0")),
               "bottom": float(el.get("y", "0")) + float(el.get("height", "0"))}


def overlaps(a, b, tol=TOL):
    return (a["left"] < b["right"] - tol and b["left"] < a["right"] - tol
            and a["top"] < b["bottom"] - tol and b["top"] < a["bottom"] - tol)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else
                "figures/src/fig1_overview.svg")
    root = ET.parse(path).getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
    W = float(root.get("width", "0"))
    H = float(root.get("height", "0"))

    ts = list(texts(root, ns))
    ims = list(images(root, ns))
    findings = []

    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            if overlaps(ts[i], ts[j]):
                findings.append(
                    f"TEXT×TEXT  {ts[i]['s'][:32]!r} @({ts[i]['x']:.0f},"
                    f"{ts[i]['y']:.0f})  ×  {ts[j]['s'][:32]!r} @"
                    f"({ts[j]['x']:.0f},{ts[j]['y']:.0f})")

    for t in ts:
        for im in ims:
            if overlaps(t, im):
                tag = "halo" if t["halo"] > 0 else "PLAIN"
                findings.append(
                    f"TEXT×IMG[{tag}]  {t['s'][:36]!r} @({t['x']:.0f},"
                    f"{t['y']:.0f}) over image "
                    f"[{im['left']:.0f},{im['top']:.0f}–{im['right']:.0f},"
                    f"{im['bottom']:.0f}]")
        if (t["left"] < 0 or t["right"] > W or t["top"] < 0
                or t["bottom"] > H):
            findings.append(f"OUTSIDE   {t['s'][:36]!r} @({t['x']:.0f},"
                            f"{t['y']:.0f})")

    print(f"{len(ts)} texts, {len(ims)} images, canvas {W:.0f}×{H:.0f}")
    for f in findings:
        print("  " + f)
    print("lint: " + ("CLEAN" if not findings else f"{len(findings)} findings"))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
