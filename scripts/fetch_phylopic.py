#!/usr/bin/env python3
"""
Fetch PhyloPic silhouettes for species in the Roost portal.

Downloads images locally (one PNG per species) so the site never hits
PhyloPic at runtime. Attribution metadata is saved alongside and shown
on the Credits page.

Sources of species names: detected species (species.parquet), the
gene-presence species, and wiki-supplement mammals.

Usage:
  pixi run python scripts/fetch_phylopic.py            # incremental fetch
  pixi run python scripts/fetch_phylopic.py --refresh  # re-download all
"""

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent
IMG_DIR = ROOT / "web" / "public" / "images" / "phylopic"
ATTR_FILE = ROOT / "web" / "public" / "data" / "phylopic.json"

API = "https://api.phylopic.org"
UA = "Roost/0.1 (avian influenza research portal; batch species silhouettes)"
SLEEP = 0.35          # be polite between requests
TARGET_RASTER = 512   # preferred raster width for header images


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def http_download(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())


def normalize_name(name: str) -> str:
    """PhyloPic wants lowercase, non-alphabetic chars removed, trimmed."""
    name = name.lower().strip()
    return re.sub(r"[^a-z\s]", "", name)


def get_build() -> str:
    d = http_json(API)
    return str(d.get("build"))


def search_node(name: str, build: str):
    """Return first node matching a taxon name, or None."""
    q = urllib.parse.quote(normalize_name(name))
    try:
        d = http_json(f"{API}/nodes?build={build}&filter_name={q}&page=0")
    except Exception:
        return None
    items = d.get("_links", {}).get("items", [])
    if not items:
        return None
    return items[0].get("href", "").split("/nodes/")[1].split("?")[0], items[0].get("title")


def node_with_image(uuid: str):
    """Fetch node + primary image metadata."""
    try:
        d = http_json(f"{API}/nodes/{uuid}?embed_primaryImage=true&embed_contributor=true")
    except Exception:
        return None
    img = d.get("_embedded", {}).get("primaryImage")
    if not img:
        return None
    links = img.get("_links", {})
    rasters = links.get("rasterFiles", [])
    thumbs = links.get("thumbnailFiles", [])
    contributor = img.get("_embedded", {}).get("contributor", {})
    return {
        "image_uuid": img.get("uuid"),
        "attribution": img.get("attribution"),
        "license": img.get("license"),
        "contributor": contributor.get("name"),
        "contributor_uuid": contributor.get("uuid"),
        "rasters": rasters,
        "thumbs": thumbs,
    }


def pick_raster(rasters, thumbs):
    """Choose an image URL: smallest raster >= TARGET, else 192 thumb, else any."""
    parsed = []
    for f in rasters:
        m = re.search(r"(\d+)x(\d+)", f.get("sizes", "") or f.get("href", ""))
        if m:
            parsed.append((int(m.group(1)), f["href"]))
    parsed.sort()
    for w, href in parsed:
        if w >= 256:
            return href
    if parsed:
        return parsed[-1][1]  # largest available
    for f in thumbs:
        if "192" in (f.get("sizes") or f.get("href", "")):
            return f["href"]
    return thumbs[0]["href"] if thumbs else None


def slug(sci: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", sci).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download existing images")
    args = ap.parse_args()

    # ---- collect species names ----
    names = {}

    sp = pl.read_parquet(ROOT / "web" / "public" / "data" / "species.parquet")
    for row in sp.select(["scientific_name"]).iter_rows():
        if row[0]:
            names[row[0]] = "detected"

    presence = ROOT / "data" / "genes" / "gene_presence_v2.jsonl"
    if presence.exists():
        for line in presence.read_text().splitlines():
            if line.strip():
                names.setdefault(json.loads(line)["species"], "presence")

    supp = ROOT / "web" / "public" / "data" / "species_wiki_supplement.json"
    if supp.exists():
        for s in json.loads(supp.read_text()):
            if s.get("sci"):
                names.setdefault(s["sci"], "supplement")

    print(f"Species to fetch: {len(names)}")

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    attr = json.loads(ATTR_FILE.read_text()) if ATTR_FILE.exists() else {}

    build = get_build()
    print(f"PhyloPic build: {build}")

    ok = miss = skip = 0
    for i, (sci, source) in enumerate(sorted(names.items()), 1):
        s = slug(sci)
        img_path = IMG_DIR / f"{s}.png"
        if img_path.exists() and not args.refresh and s in attr:
            skip += 1
            continue

        node = None
        # species → genus fallback
        for candidate in [sci, sci.split()[0] if " " in sci else None]:
            if not candidate:
                continue
            node = search_node(candidate, build)
            time.sleep(SLEEP)
            if node:
                break
        if not node:
            miss += 1
            attr[s] = {"sci": sci, "status": "not_in_phylopic"}
            ATTR_FILE.write_text(json.dumps(attr, indent=1))
            if i % 50 == 0:
                print(f"  [{i}/{len(names)}] {sci}: no silhouette")
            continue

        node_uuid, node_title = node
        meta = node_with_image(node_uuid)
        time.sleep(SLEEP)
        if not meta:
            miss += 1
            attr[s] = {"sci": sci, "status": "no_image", "node": node_title}
            continue

        href = pick_raster(meta["rasters"], meta["thumbs"])
        if not href:
            miss += 1
            continue
        try:
            http_download(href, img_path)
        except Exception as e:
            print(f"  {sci}: download failed: {e}")
            miss += 1
            continue

        attr[s] = {
            "sci": sci,
            "status": "ok",
            "matched_node": node_title,
            "exact": node_title.lower() == normalize_name(sci) if node_title else False,
            "image_uuid": meta["image_uuid"],
            "attribution": meta["attribution"],
            "license": meta["license"],
            "contributor": meta["contributor"],
            "url": f"https://www.phylopic.org/images/{meta['image_uuid']}/",
        }
        ok += 1
        # persist incrementally so partial runs stay usable and resume works
        ATTR_FILE.write_text(json.dumps(attr, indent=1))
        if i % 25 == 0:
            print(f"  [{i}/{len(names)}] {sci} → {node_title} ({meta['attribution']})")

    ATTR_FILE.write_text(json.dumps(attr, indent=1))
    print(f"\nDone: {ok} downloaded, {skip} skipped (cached), {miss} unavailable")
    print(f"Attribution → {ATTR_FILE}")


if __name__ == "__main__":
    main()
