#!/usr/bin/env python3
"""Build attribution files from figure manifests.

  --figure NAME  → figures/attribution/NAME.txt (per-figure credit lines)
  --rollup       → docs/ASSET_CREDITS.md (project-wide credits rollup)

Licensing is part of figure correctness: every figure that imports third-party
assets ships its credits next to the source.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "figures" / "manifests"
ATTR = ROOT / "figures" / "attribution"
CREDITS = ROOT / "docs" / "ASSET_CREDITS.md"

LIBRARY_CREDITS = {
    "bioicons": ("Bioicons", "https://bioicons.com",
                 "Site code MIT; each icon retains its own license "
                 "(recorded per asset below)."),
    "reactome": ("Reactome Icon Library", "https://reactome.org/icon-lib",
                 "CC BY 4.0. Attribution required."),
    "healthicons": ("Health Icons", "https://healthicons.org",
                    "Public domain / CC0. No attribution required."),
    "phylopic": ("PhyloPic", "https://www.phylopic.org",
                 "Per-image licenses; this mirror contains only "
                 "public-domain/CC0/CC BY images."),
    "nih-bioart": ("NIH/NIAID BioArt", "https://bioart.niaid.nih.gov",
                   "Free for educational, research, informational and commercial "
                   "purposes; see per-entry terms."),
    "scidraw": ("SciDraw", "https://scidraw.io", "CC BY 4.0. Attribution required."),
    "togo": ("Togo Picture Gallery / DBCLS", "https://togotv.dbcls.jp/ja/pics.html",
             "© 2016 DBCLS TogoTV / CC-BY-4.0."),
    "servier": ("Servier Medical Art", "https://smart.servier.com",
                "CC BY 4.0. Image(s) provided by Servier Medical Art "
                "(https://smart.servier.com), licensed under CC BY 4.0."),
}


def figure_attribution(figure: str) -> str | None:
    mpath = MANIFESTS / f"{figure}.json"
    if not mpath.exists():
        return None
    manifest = json.loads(mpath.read_text())
    lines = [f"Attribution — {manifest.get('figure', figure)}",
             "=" * (14 + len(manifest.get("figure", figure))), ""]
    assets = manifest.get("assets", [])
    if not assets:
        lines.append("No third-party assets imported.")
    for a in assets:
        lines.append(f"• {a.get('title', '?')} — by {a.get('author', 'unknown')}")
        lines.append(f"    Source: {a.get('source', '?')} <{a.get('source_url', '')}>")
        lines.append(f"    License: {a.get('license', '?')} "
                     f"<{a.get('license_url', '')}>")
        credit = a.get("attribution") or a.get("citation") or ""
        if credit:
            lines.append(f"    Credit: {credit}")
        if a.get("modified"):
            lines.append("    Modified from the original (within license terms).")
        lines.append("")
    if manifest.get("mock"):
        lines.append("NOTE: figure flagged as mock-up — not grounded in verified data.")
    return "\n".join(lines)


LICENSE_LINKS = {
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "Public Domain": "https://creativecommons.org/publicdomain/mark/1.0/",
    "MIT": "https://opensource.org/licenses/MIT",
    "BSD-3-Clause": "https://opensource.org/licenses/BSD-3-Clause",
}


def web_artifacts() -> None:
    """Emit web-serving credits: per-library JSON + markdown rollup copy.

    The site Credits page renders web/public/figures/libraries.json and links
    the full rollup at credits/asset-credits.md.
    """
    import shutil
    import sqlite3

    counts: dict[str, int] = {}
    try:
        con = sqlite3.connect(ROOT / "assets" / "manifest.sqlite")
        for src, n in con.execute(
                "select source, count(*) from assets group by source"):
            counts[src] = n
        con.close()
    except sqlite3.Error:
        pass

    libs = []
    for key, (name, url, note) in LIBRARY_CREDITS.items():
        lic = "CC BY 4.0" if key in ("reactome", "scidraw", "togo", "servier") \
            else "per-asset" if key in ("bioicons", "phylopic") \
            else "CC0 / Public Domain" if key == "healthicons" \
            else "free-use terms" if key == "nih-bioart" else "per-asset"
        libs.append({
            "key": key, "name": name, "url": url, "note": note,
            "license": lic,
            "license_url": LICENSE_LINKS.get(lic, ""),
            "assets_indexed": counts.get(key, 0),
        })
    out = ROOT / "web" / "public" / "figures" / "libraries.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"libraries": libs}, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    md_dir = ROOT / "web" / "public" / "credits"
    md_dir.mkdir(parents=True, exist_ok=True)
    if CREDITS.exists():
        shutil.copy2(CREDITS, md_dir / "asset-credits.md")
    print("web credits → web/public/figures/libraries.json + credits/asset-credits.md")


def rollup() -> str:
    per_source: dict[str, set[str]] = defaultdict(set)
    figures_by_source: dict[str, set[str]] = defaultdict(set)
    total = 0
    for mf in sorted(MANIFESTS.glob("*.json")) if MANIFESTS.exists() else []:
        try:
            manifest = json.loads(mf.read_text())
        except json.JSONDecodeError:
            continue
        for a in manifest.get("assets", []):
            total += 1
            key = a.get("source", "unknown")
            label = f"{a.get('title', '?')} ({a.get('license', '?')}) — {mf.stem}"
            per_source[key].add(label)
            figures_by_source[key].add(mf.stem)
    lines = [
        "# Asset Credits",
        "",
        "Rollup of third-party scientific assets used in project figures.",
        f"Auto-generated by `scripts/figures/build_attribution.py --rollup` — {date.today():%Y-%m-%d}.",
        "Per-figure credits: `figures/attribution/*.txt`; provenance:",
        "`figures/manifests/*.json`; index: `assets/manifest.sqlite`.",
        "",
        "Assets used so far: **%d** across **%d** figures." % (
            total, len({f for figs in figures_by_source.values() for f in figs})),
        "",
    ]
    if not per_source:
        lines += ["_(no figures have imported assets yet — see "
                  "`figures/src/` for current work)_", ""]
    for key in sorted(per_source):
        name, url, note = LIBRARY_CREDITS.get(key, (key, "", ""))
        lines += [f"## {name}", ""]
        if url:
            lines.append(f"<{url}>")
        lines += [note, "", f"Used by: {', '.join(sorted(figures_by_source[key]))}", ""]
        for label in sorted(per_source[key]):
            lines.append(f"- {label}")
        lines.append("")
    lines += ["## Mirrored libraries (available, not yet used in figures)", ""]
    used = set(per_source)
    for key, (name, url, note) in LIBRARY_CREDITS.items():
        if key not in used:
            lines += [f"- **{name}** <{url}> — {note}"]
    lines += ["", "All eight libraries mirrored under `assets/` (Togo + Servier via "
               "`mirror_togo_servier.sh`); rerun `build_asset_index.py` after "
               "any mirror refresh.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--figure", help="figure name (manifests/<name>.json)")
    g.add_argument("--rollup", action="store_true", help="regenerate docs/ASSET_CREDITS.md")
    args = ap.parse_args()

    if args.rollup:
        CREDITS.parent.mkdir(parents=True, exist_ok=True)
        CREDITS.write_text(rollup())
        web_artifacts()
        print(f"wrote {CREDITS.relative_to(ROOT)}")
        return 0

    text = figure_attribution(args.figure)
    if text is None:
        raise SystemExit(f"no manifest for figure '{args.figure}' "
                         f"(figures/manifests/{args.figure}.json)")
    ATTR.mkdir(parents=True, exist_ok=True)
    out = ATTR / f"{args.figure}.txt"
    out.write_text(text + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
