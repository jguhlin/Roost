#!/usr/bin/env python3
"""Build manifests for the Togo Picture Gallery and Servier Medical Art mirrors.

Schema matches the other asset mirrors (build_asset_index.py consumes it):
  id, title, category, keywords, description, license, license_url,
  requires_attribution, share_alike, collection, creator, citation,
  source, source_page, local_files[{files{SVG: path}}]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, "assets")

CC_BY_4 = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/")


def title_from(fn: str) -> str:
    stem = os.path.splitext(fn)[0]
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:80] or stem


def togo_manifest() -> int:
    d = os.path.join(ASSETS, "togo")
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(".svg"):
            continue
        stem = os.path.splitext(fn)[0]
        out.append({
            "id": f"togo:{stem}",
            "title": title_from(fn),
            "category": "illustration",
            "keywords": [w.lower() for w in title_from(fn).split()],
            "description": "Togo Picture Gallery illustration by DBCLS TogoTV.",
            "license": CC_BY_4[0],
            "license_url": CC_BY_4[1],
            "requires_attribution": True,
            "share_alike": False,
            "collection": "Togo Picture Gallery",
            "creator": "DBCLS TogoTV",
            "citation": "© DBCLS TogoTV / CC-BY-4.0",
            "source": "togo",
            "source_page": f"https://dbarchive.biosciencedbc.jp/data/togo-pic/image/{fn}",
            "local_files": [{"files": {"SVG": f"assets/togo/{fn}"}}],
        })
    if out:
        with open(os.path.join(d, "manifest.json"), "w") as f:
            json.dump(out, f, ensure_ascii=False)
    return len(out)


def svg_title(path: str) -> str:
    """Best-effort title from the SVG's own <title>/dc:title, else ''."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
        m = re.search(r"<title[^>]*>([^<]{2,120})</title>", head)
        if m:
            t = m.group(1).strip()
            if t.lower() not in ("image", "svg", "layer 1") and not re.match(r"^image\d*$", t, re.I):
                return t
    except OSError:
        pass
    return ""


def servier_manifest() -> int:
    d = os.path.join(ASSETS, "servier")
    out = []
    for cat in sorted(os.listdir(d)):
        catd = os.path.join(d, cat)
        if not os.path.isdir(catd):
            continue
        for fn in sorted(os.listdir(catd)):
            if not fn.lower().endswith(".svg"):
                continue
            stem = os.path.splitext(fn)[0]
            title = svg_title(os.path.join(catd, fn)) or f"{cat} {stem}"
            out.append({
                "id": f"servier:{cat}/{stem}",
                "title": title,
                "category": cat,
                "keywords": [w.lower() for w in title.split()] + [cat],
                "description": f"Servier Medical Art ({cat}).",
                "license": CC_BY_4[0],
                "license_url": CC_BY_4[1],
                "requires_attribution": True,
                "share_alike": False,
                "collection": "Servier Medical Art",
                "creator": "Servier Medical Art",
                "citation": "Image(s) provided by Servier Medical Art (https://smart.servier.com), licensed under CC BY 4.0.",
                "source": "servier",
                "source_page": "https://smart.servier.com/",
                "local_files": [{"files": {"SVG": f"assets/servier/{cat}/{fn}"}}],
            })
    if out:
        with open(os.path.join(d, "manifest.json"), "w") as f:
            json.dump(out, f, ensure_ascii=False)
    return len(out)


if __name__ == "__main__":
    n_togo = togo_manifest()
    n_serv = servier_manifest()
    print(f"togo manifest: {n_togo} entries")
    print(f"servier manifest: {n_serv} entries")
    sys.exit(0 if (n_togo or n_serv) else 1)
