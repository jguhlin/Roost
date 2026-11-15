#!/usr/bin/env python3
"""URL backfill for DOI-less papers via the local searxng instance.

Papers with full text but no DOI and no URL are grey literature (WHO
updates, agency reports). Search each title on searxng
(http://localhost:8888/search?format=json), take the best-scoring
result whose title token-overlaps the paper title and whose domain is a
credible source (who.int, cdc.gov, pubmed, journals, agencies), and
store it as the paper URL with url_source provenance.

Run:  pixi run python scripts/papers/backfill_urls_searxng.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
SEARXNG = "http://localhost:8888/search"

GOOD_DOMAINS = ("who.int", "cdc.gov", "pubmed.ncbi", "ncbi.nlm", "doi.org",
                "who.int", "fao.org", "woah.org", "oie.int", "ecdc.europa",
                "gov.uk", "usda.gov", "aphis.usda", "eurasianet", "nature.com",
                "thelancet.com", "science.org", "cell.com", "pnas.org",
                "biorxiv.org", "medrxiv.org", "frontiersin.org", "plos.org",
                "wiley.com", "sciencedirect.com", "springer.com", "mdpi.com")


def search(q: str) -> tuple[list[dict], list]:
    """Returns (results, unresponsive_engines) — the caller backs off when
    the majors are suspended (junk from weak engines is worse than none)."""
    url = f"{SEARXNG}?{urllib.parse.urlencode({'q': q, 'format': 'json'})}"
    req = urllib.request.Request(url, headers={"User-Agent": "Roost-backfill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
        return d.get("results", []), d.get("unresponsive_engines", [])


def overlap(a: str, b: str) -> float:
    ta = {w for w in re.sub(r"[^a-z0-9 ]", " ", a.lower()).split() if len(w) > 3}
    tb = {w for w in re.sub(r"[^a-z0-9 ]", " ", b.lower()).split() if len(w) > 3}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(PAPERS_JSON.read_text())
    papers = doc["papers"]
    todo = [p for p in papers
            if not p.get("url") and not p.get("doi")
            and (ROOT / "docs" / "papers_md" / f"{p['id']}.md").exists()]
    print(f"{len(todo)} papers without URL/DOI", file=sys.stderr)

    fixed = 0
    for p in todo:
        title = p.get("title") or ""
        if len(title) < 15:
            continue
        try:
            results, dead = search(title[:100])
            majors = ("brave", "duckduckgo", "google cse", "bing")
            if sum(1 for e in dead if e and e[0] in majors) >= 2:
                print("  engines degraded — cooling down 90s", file=sys.stderr)
                time.sleep(90)
                results, dead = search(title[:100])
                if sum(1 for e in dead if e and e[0] in majors) >= 2:
                    continue   # skip this round; paper stays pending
        except Exception as e:
            print(f"  {p['id']}: search failed {str(e)[:60]}", file=sys.stderr)
            time.sleep(30)
            continue
        best = None
        for r in results[:8]:
            url = r.get("url", "")
            if not url or not any(d in url for d in GOOD_DOMAINS):
                continue
            ov = overlap(title, r.get("title", ""))
            if ov >= 0.5:
                best = (url, r.get("title", ""), ov)
                break
        if best:
            print(f"  {p['id']}: {best[0][:70]} (overlap {best[2]:.2f})",
                  file=sys.stderr)
            if not args.dry_run:
                p["url"] = best[0]
                p["url_source"] = "searxng-title-search"
            fixed += 1
        time.sleep(8)

    if not args.dry_run and fixed:
        PAPERS_JSON.write_text(json.dumps(doc, indent=1))
    print(f"URLs backfilled: {fixed}{' (dry run)' if args.dry_run else ''}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
