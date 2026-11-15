#!/usr/bin/env python3
"""Structural + license audit for a figure source.

  python3 scripts/figures/audit_figure.py figures/src/fig.svg --figure figname

SVG checks: well-formed XML; no scripts/foreignObject; duplicate IDs; text
placed outside the viewBox; tiny text; external references; missing local
image refs; sane dimensions.
Python checks: unseeded randomness; savefig present.
License audit (with --figure): every imported asset still resolves in the
index; ShareAlike/NonCommercial flags surfaced for publication decisions.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "assets" / "manifest.sqlite"
MIN_FONT = 9.0
CHAR_W = 0.62  # rough sans-serif advance width as fraction of font size

DISALLOWED = ("{http://www.w3.org/2000/svg}script", "script",
              "{http://www.w3.org/2000/svg}foreignObject", "foreignObject")


def audit_svg(path: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return [f"XML parse error: {e}"], []
    root = tree.getroot()
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
    vb = (root.get("viewBox") or "").split()
    try:
        x0, y0, w, h = (float(v) for v in vb) if len(vb) == 4 else (0.0, 0.0, float(root.get("width", "0").replace("px", "") or 0), float(root.get("height", "0").replace("px", "") or 0))
    except ValueError:
        x0 = y0 = w = h = 0.0
    if w < 50 or h < 50:
        errors.append(f"canvas too small or unreadable: {w}x{h}")

    ids: dict[str, int] = {}
    texts = 0
    for el in root.iter():
        tag = el.tag.replace(ns, "")
        if tag in DISALLOWED:
            errors.append(f"disallowed element <{tag}> (GitHub-unsafe / non-editable)")
        eid = el.get("id")
        if eid:
            ids[eid] = ids.get(eid, 0) + 1
        href = el.get("href") or el.get(f"{ns}href") or el.get("xlink:href") or ""
        if tag == "image":
            if href.startswith(("http://", "https://")):
                errors.append(f"external image reference: {href[:80]}")
            elif href.startswith("data:"):
                pass  # embedded data URI — self-contained by construction
            elif href and not (path.parent / href).exists():
                errors.append(f"missing local image ref: {href}")
        if tag == "text":
            texts += 1
            x = float(el.get("x", "0") or 0)
            y = float(el.get("y", "0") or 0)
            fs = None
            for a in (el, *list(el)):
                if a is not None and a.get("font-size"):
                    try:
                        fs = float(re.sub(r"[^0-9.]", "", a.get("font-size")))
                    except ValueError:
                        pass
                    break
            fs = fs if fs else 14.0
            content = "".join(el.itertext())
            est_w = len(content) * fs * CHAR_W
            # text-anchor shifts the box: end → extends left, middle → centered
            anchor = el.get("text-anchor", "start")
            left = (x - est_w if anchor == "end"
                    else x - est_w / 2 if anchor == "middle" else x)
            right = left + est_w
            if left < x0 - 1 or y < y0 - 1 or right > x0 + w + 2 or y - fs > y0 + h + 2:
                warnings.append(f"text may fall outside canvas at ({x:.0f},{y:.0f}): "
                                f"{content[:40]!r}")
            if fs < MIN_FONT:
                warnings.append(f"font-size {fs:g} < {MIN_FONT:g}: {content[:40]!r}")
    for eid, n in ids.items():
        if n > 1:
            errors.append(f"duplicate id '{eid}' used {n}x")
    if texts == 0 and any(True for _ in root.iter(f"{ns}image")) is False:
        warnings.append("no text elements found (labels should stay live text)")
    return errors, warnings


def audit_py(path: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    src = path.read_text(encoding="utf-8", errors="replace")
    if "savefig" not in src and "save(fig" not in src:
        errors.append("no savefig call — script must write its outputs "
                      "(fig.savefig or style.save)")
    for m in re.finditer(r"(np\.random|random\.)[a-z_]+\(", src):
        if "seed" not in src:
            errors.append(f"unseeded randomness used ({m.group(0)}…) — figures must be reproducible")
            break
    for m in re.finditer(r"interpolate|rolling\(|smooth", src):
        warnings.append(f"possible smoothing/interpolation: '{m.group(0)}' — must be "
                        "explicit and documented if it alters plotted values")
        break
    return errors, warnings


def audit_licenses(figure: str, strict: bool) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    mpath = ROOT / "figures" / "manifests" / f"{figure}.json"
    if not mpath.exists():
        warnings.append(f"no manifest for figure '{figure}' (figures/manifests/{figure}.json)")
        return errors, warnings
    manifest = json.loads(mpath.read_text())
    if manifest.get("mock"):
        warnings.append("figure is flagged as a mock-up (not grounded in verified data)")
    con = sqlite3.connect(DB) if DB.exists() else None
    for a in manifest.get("assets", []):
        lic = a.get("license", "")
        if re.search(r"\b(nc|non[- ]?commercial)\b", lic, re.I):
            errors.append(f"NonCommercial asset in publication figure: {a['title']} ({lic})")
        if a.get("share_alike"):
            warnings.append(f"ShareAlike asset: {a['title']} ({lic}) — check downstream licensing")
        if a.get("requires_attribution") and not (a.get("attribution") or "").strip():
            errors.append(f"attribution required but missing for: {a['title']}")
        local = ROOT / a.get("imported_path", "")
        if not local.exists():
            errors.append(f"imported asset file missing: {a.get('imported_path')}")
        if con is not None and a.get("source_id"):
            row = con.execute("SELECT 1 FROM assets WHERE source_id = ?", (a["source_id"],)).fetchone()
            if row is None and a.get("original_path"):
                row = con.execute("SELECT 1 FROM assets WHERE file_path = ?",
                                  (a["original_path"],)).fetchone()
            if row is None:
                warnings.append(f"asset not found in current index: {a['title']}")
    if con is not None:
        con.close()
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="figures/src/<fig>.svg|.py")
    ap.add_argument("--figure", help="figure name for license/manifest audit")
    ap.add_argument("--strict", action="store_true", help="exit nonzero on warnings too")
    args = ap.parse_args()

    path = Path(args.source)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"no such source: {path}")
    figure = args.figure or path.stem

    if path.suffix == ".svg":
        errors, warnings = audit_svg(path)
    elif path.suffix == ".py":
        errors, warnings = audit_py(path)
    else:
        errors, warnings = [], [f"no structural audit for {path.suffix} files"]

    lerr, lwarn = audit_licenses(figure, args.strict)
    errors += lerr
    warnings += lwarn

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARN : {w}")
    if not errors and not warnings:
        print("audit clean")
    verdict = "FAIL" if errors else ("PASS (with warnings)" if warnings else "PASS")
    print(f"— {path.name}: {verdict}")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
