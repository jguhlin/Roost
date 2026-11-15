#!/usr/bin/env python3
"""
Metadata backfill via DOI (D72): for every paper with a DOI, fetch structured
metadata from Crossref (works/{doi}) and PubMed (esummary) and merge:

  authors_list: [{family, given, ...}] — full list, network-ready
  year: publication year (int)
  journal: container title
  + fills missing url (DOI link)

papers.json display keeps 'authors' as a display string; the full list lives
in authors_list. Merge-write only — never drops existing fields.

Usage:
  backfill_doi_meta.py                # dry-run
  backfill_doi_meta.py --apply
"""
import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
CACHE = ROOT / "data" / "papers" / "doi_meta_cache.json"

HEADERS = {"User-Agent": "Roost/1.0 (mailto:roost@example.org)"}


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def crossref_work(doi, cache):
    key = f"doi:{doi}"
    if key in cache:
        return cache[key]
    try:
        r = httpx.get(f"https://api.crossref.org/works/{doi}",
                      headers=HEADERS, timeout=30)
        if r.status_code == 200:
            m = r.json().get("message", {})
            authors = [
                {"family": a.get("family", ""), "given": a.get("given", "")}
                for a in m.get("author", [])
            ]
            year = None
            for field in ("published-print", "published-online", "issued", "created"):
                dp = m.get(field, {}).get("date-parts", [[None]])
                if dp and dp[0] and dp[0][0]:
                    year = dp[0][0]
                    break
            cache[key] = {
                "authors": authors,
                "year": year,
                "journal": (m.get("container-title") or [""])[0],
                "type": m.get("type", ""),
                "title": (m.get("title") or [""])[0],
            }
        else:
            cache[key] = {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        cache[key] = {"error": str(e)[:80]}
    return cache[key]


def display_string(authors_list, max_show=3):
    """'Family I, Family I, Family I, et al.' — full list stays in data."""
    shown = []
    for a in authors_list[:max_show]:
        fam = a.get("family", "").strip()
        giv = a.get("given", "").strip()
        initials = " ".join(f"{p[0]}." for p in giv.replace("-", " ").split() if p)
        shown.append(f"{fam} {initials}".strip())
    if not shown:
        return ""
    if len(authors_list) > max_show:
        return ", ".join(shown) + ", et al."
    return ", ".join(shown)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]
    doi_papers = [p for p in papers if p.get("doi")]
    print(f"{len(doi_papers)} papers with DOI")

    cache = load_cache()

    def fetch(p):
        res = crossref_work(p["doi"], cache)
        time.sleep(0.3)
        return p, res

    updates = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (p, res) in enumerate(ex.map(fetch, doi_papers), 1):
            if i % 50 == 0:
                print(f"  fetched {i}/{len(doi_papers)}")
            if res.get("error") or not res.get("authors") and not res.get("year"):
                continue
            updates[p["id"]] = res

    # Save cache
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))

    # Report what would change
    n_authors = sum(1 for p in papers if p["id"] in updates
                    and updates[p["id"]].get("authors")
                    and not p.get("authors_list"))
    n_year = sum(1 for p in papers if p["id"] in updates
                 and updates[p["id"]].get("year") and not p.get("year"))
    n_journal = sum(1 for p in papers if p["id"] in updates
                    and updates[p["id"]].get("journal") and not p.get("journal"))
    print(f"\nwould add: authors_list {n_authors}, year {n_year}, journal {n_journal}")

    if args.apply:
        changed = 0
        for p in papers:
            u = updates.get(p["id"])
            if not u:
                continue
            touched = False
            if u.get("authors") and len(u["authors"]) > 0:
                p["authors_list"] = u["authors"]
                # upgrade display string only if current one is missing/thin
                if not p.get("authors") or len(p.get("authors", "")) < 8:
                    p["authors"] = display_string(u["authors"])
                touched = True
            if u.get("year") and not p.get("year"):
                p["year"] = int(u["year"])
                touched = True
            if u.get("journal") and not p.get("journal"):
                p["journal"] = u["journal"]
                touched = True
            if not p.get("url") and u.get("title"):
                p["url"] = f"https://doi.org/{p['doi']}"
                touched = True
            if touched:
                changed += 1
        PAPERS_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        print(f"APPLIED: {changed} papers updated")

        # verify structure
        d = json.loads(PAPERS_JSON.read_text())
        assert isinstance(d, dict) and "papers" in d
        n_al = sum(1 for p in d["papers"] if p.get("authors_list"))
        n_y = sum(1 for p in d["papers"] if p.get("year"))
        n_j = sum(1 for p in d["papers"] if p.get("journal"))
        print(f"now: authors_list {n_al}/{len(d['papers'])}, "
              f"year {n_y}, journal {n_j}")
    else:
        print("(dry-run — rerun with --apply)")


if __name__ == "__main__":
    main()
