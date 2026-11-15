#!/usr/bin/env python3
"""Backfill full author lists from DOI metadata (Crossref), cache-first.

Sources, in priority order per paper:
  1. data/papers/doi_meta_cache.json (keys normalized: strip doi:/URL prefix,
     lowercase) — 561 papers already carry structured {family, given} lists
  2. Crossref API (polite pool, mailto) for papers with a DOI but no cache —
     fetched lists are added to the cache so reruns never refetch
  3. Left untouched: papers with no DOI — these need the LLM pass over the
     paper fulltext (llm server), tracked as `authors_source: "llm_pending"`

Writes back into web/public/data/papers.json:
  authors_full: [{family, given}, ...]   — complete list when known
  authors_source: "doi_cache" | "crossref" | "llm_pending" | "legacy_string"

Usage: pixi run python scripts/papers/backfill_authors.py [--crossref]
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
CACHE = ROOT / "data" / "papers" / "doi_meta_cache.json"
MAILTO = "roost-project@example.org"  # Crossref polite pool


def norm_doi(d):
    return (d or "").strip().lower().removeprefix("https://doi.org/") \
        .removeprefix("http://doi.org/").removeprefix("doi:")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crossref", action="store_true",
                    help="fetch missing DOIs from Crossref (network)")
    args = ap.parse_args()

    pj = json.loads(PAPERS_JSON.read_text())
    papers = pj["papers"] if isinstance(pj, dict) else pj
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    cache_norm = {norm_doi(k): v for k, v in cache.items()}

    from collections import Counter
    stats = Counter()
    fetch_plan = []

    for p in papers:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        d = norm_doi(p.get("doi"))
        entry = cache_norm.get(d)
        if entry and isinstance(entry.get("authors"), list) and entry["authors"]:
            p["authors_full"] = entry["authors"]
            p["authors_source"] = "doi_cache"
            stats["doi_cache"] += 1
        elif d and args.crossref:
            fetch_plan.append((p, d))
        elif d:
            p["authors_source"] = "crossref_pending"
            stats["crossref_pending"] += 1
        else:
            p["authors_source"] = "llm_pending"
            stats["llm_pending"] += 1

    fetched = 0
    for p, d in fetch_plan:
        try:
            url = f"https://api.crossref.org/works/{d}?mailto={MAILTO}"
            req = urllib.request.Request(url, headers={"User-Agent": f"Roost/1.0 ({MAILTO})"})
            with urllib.request.urlopen(req, timeout=30) as r:
                msg = json.loads(r.read())["message"]
            authors = [{"family": a.get("family", ""), "given": a.get("given", "")}
                       for a in msg.get("author", []) if a.get("family")]
            if authors:
                p["authors_full"] = authors
                p["authors_source"] = "crossref"
                cache[f"doi:{d}"] = {"authors": authors,
                                     "title": msg.get("title", [""])[0],
                                     "year": (msg.get("issued", {}).get("date-parts") or [[None]])[0][0],
                                     "journal": (msg.get("container-title") or [""])[0],
                                     "type": msg.get("type", "")}
                fetched += 1
                stats["crossref"] += 1
            else:
                p["authors_source"] = "llm_pending"
                stats["crossref_empty->llm"] += 1
        except Exception as e:
            p["authors_source"] = "crossref_failed"
            stats["crossref_failed"] += 1
            if fetched < 3:
                print(f"  crossref error {d}: {str(e)[:80]}")
        time.sleep(1.0)  # polite pool
        if fetched % 50 == 0 and fetched:
            print(f"  ... {fetched} fetched", flush=True)

    PAPERS_JSON.write_text(json.dumps(pj, indent=1))
    CACHE.write_text(json.dumps(cache, indent=1))
    print(f"authors backfill: {dict(stats)} | crossref fetched: {fetched}")
    print(f"full author lists now on: "
          f"{sum(1 for p in papers if isinstance(p, dict) and p.get('authors_full'))} papers")


if __name__ == "__main__":
    main()
