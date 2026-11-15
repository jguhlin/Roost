#!/usr/bin/env python3
"""Publish rendered figures (and videos) to the web app + registry.

  pixi run python scripts/figures/publish_figure.py \
      --figure fig-qinghai-mortality \
      --page Qinghai-Lake-mortality-discrep-contradiction-investigati

Copies from figures/preview + figures/export into web/public/figures/,
pulls caption/attribution from figures/manifests/<fig>.json, and rewrites
web/public/figures/index.json — the registry the research pages read:

  { "figures": [{"page": "<slug>", "file": "NAME", "kind": "figure",
                  "caption": "...", "attribution": "...",
                  "url": "figures/NAME.png", "svg": "figures/NAME.svg"}],
    "videos":  [{"page": "<slug>", "file": "NAME.mp4", ...}] }

Videos: --video PATH --page SLUG [--caption ...] copies any mp4/webm into
web/public/videos/ and registers it.

Re-running with the same --figure updates its entry in place.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "figures" / "preview"
EXPORT = ROOT / "figures" / "export"
MANIFESTS = ROOT / "figures" / "manifests"
WEB_FIGS = ROOT / "web" / "public" / "figures"
WEB_VIDS = ROOT / "web" / "public" / "videos"
INDEX = WEB_FIGS / "index.json"


def load_index() -> dict:
    if INDEX.exists():
        try:
            return json.loads(INDEX.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"figures": [], "videos": []}


def save_index(idx: dict) -> None:
    WEB_FIGS.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(f"registry → {INDEX.relative_to(ROOT)} "
          f"({len(idx['figures'])} figures, {len(idx['videos'])} videos)")


def upsert(items: list, key: dict, entry: dict) -> list:
    """Replace the entry matching key (dict equality on key fields) else append."""
    out = [e for e in items if not all(e.get(k) == v for k, v in key.items())]
    out.append(entry)
    return out


def publish_figure(fig: str, page: str, caption: str | None) -> int:
    png = PREVIEW / f"{fig}.png"
    svg = EXPORT / f"{fig}.svg"
    if not png.exists():
        print(f"error: {png.relative_to(ROOT)} missing — run render_figure.py first",
              file=sys.stderr)
        return 1
    if not svg.exists():
        print(f"warning: {svg.relative_to(ROOT)} missing — publishing PNG only",
              file=sys.stderr)

    WEB_FIGS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(png, WEB_FIGS / f"{fig}.png")
    entry: dict = {"page": page, "file": fig, "kind": "figure",
                   "url": f"figures/{fig}.png"}
    if svg.exists():
        shutil.copy2(svg, WEB_FIGS / f"{fig}.svg")
        entry["svg"] = f"figures/{fig}.svg"

    # caption: CLI > manifest caption > manifest title
    man = MANIFESTS / f"{fig}.json"
    attribution = ""
    if man.exists():
        try:
            m = json.loads(man.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            m = {}
        caption = caption or m.get("caption") or m.get("title") or fig
        # structured credits — deterministic from the manifest; the page renders
        # these as clickable author + license links (MEDIA_PLAN credits policy)
        LICENSE_LINKS = {
            "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
            "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
            "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
            "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
            "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
            "Public Domain": "https://creativecommons.org/publicdomain/mark/1.0/",
        }
        credits = []
        for a in m.get("assets", []):
            lic = a.get("license", "")
            credits.append({
                "title": a.get("title", "asset"),
                "author": a.get("author") or a.get("source") or "unknown",
                "license": lic,
                "license_url": a.get("license_url") or LICENSE_LINKS.get(lic, ""),
                "source_url": a.get("source_url", ""),
                "required": bool(a.get("requires_attribution")),
                "modified": bool(a.get("modified")),
            })
        # plain-text form kept for simple consumers
        attribution = "; ".join(
            f"{c['title']} by {c['author']}, {c['license']}"
            + ("" if c["required"] else " (no attribution required — credited anyway)")
            for c in credits)
    else:
        caption = caption or fig

    entry["caption"] = caption
    if attribution:
        entry["attribution"] = attribution
    if credits:
        entry["credits"] = credits
    from datetime import datetime, timezone
    entry["published"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    idx = load_index()
    idx["figures"] = upsert(idx["figures"], {"page": page, "file": fig}, entry)
    save_index(idx)
    print(f"published figure '{fig}' → page '{page}'")
    return 0


def publish_video(path: str, page: str, caption: str | None) -> int:
    src = Path(path)
    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 1
    if src.suffix.lower() not in (".mp4", ".webm"):
        print(f"error: unsupported video type {src.suffix}", file=sys.stderr)
        return 1
    WEB_VIDS.mkdir(parents=True, exist_ok=True)
    name = src.name
    dst = WEB_VIDS / name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    entry = {"page": page, "file": name, "kind": "video",
             "url": f"videos/{name}",
             "caption": caption or name}
    from datetime import datetime, timezone
    entry["published"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    idx = load_index()
    idx["videos"] = upsert(idx["videos"], {"page": page, "file": name}, entry)
    save_index(idx)
    print(f"published video '{name}' → page '{page}'")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--figure", help="figure name (figures/src/<name>.* family)")
    g.add_argument("--video", help="path to an .mp4/.webm to publish")
    ap.add_argument("--page", required=True,
                    help="page slug the media belongs to (e.g. briefing slug)")
    ap.add_argument("--caption", help="override caption")
    args = ap.parse_args()
    if args.figure:
        return publish_figure(args.figure, args.page, args.caption)
    return publish_video(args.video, args.page, args.caption)


if __name__ == "__main__":
    sys.exit(main())
