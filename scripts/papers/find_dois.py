#!/usr/bin/env python3
"""
DOI discovery (D72): find DOIs for papers missing them.

Two paths, deterministic before fuzzy:
  1. PMID path — paper has a PubMed URL → extract PMID → NCBI esummary → DOI
  2. Crossref path — query.bibliographic=<title> + query.author=<first author>,
     verify with normalized-title similarity ≥ threshold + author family match

Usage:
  find_dois.py                     # dry-run: report proposed matches
  find_dois.py --apply             # write DOIs into papers.json (merge-write)
  find_dois.py --apply --min 0.97  # stricter threshold
"""
import argparse
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote_plus

import httpx

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
CACHE = ROOT / "data" / "papers" / "doi_cache.json"

HEADERS = {
    "User-Agent": "Roost/1.0 (avian-influenza resource; mailto:roost@example.org)",
}
# doc types that legitimately lack DOIs — news only; theses often have
# DataCite DOIs (ProQuest, university repositories)
NO_DOI_EXPECTED = {"news"}


def normalize_title(t):
    t = unicodedata.normalize("NFKD", t)
    t = t.encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def pmid_from_url(url):
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url or "")
    return m.group(1) if m else None


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))


def crossref_search(title, author, cache, key):
    """Search Crossref by bibliographic string. Returns list of candidates."""
    if key in cache:
        return cache[key]["results"]
    q = f"https://api.crossref.org/works?query.bibliographic={quote_plus(title)}&rows=5"
    if author:
        first_family = re.split(r"[,;]", author)[0].strip()
        q += f"&query.author={quote_plus(first_family)}"
    try:
        r = httpx.get(q, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            items = r.json().get("message", {}).get("items", [])
            results = [{
                "doi": it.get("DOI", ""),
                "title": (it.get("title") or [""])[0],
                "authors": [a.get("family", "") for a in it.get("author", []) if a.get("family")],
                "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
                "type": it.get("type", ""),
            } for it in items]
            cache[key] = {"results": results}
            return results
        cache[key] = {"results": [], "status": r.status_code}
    except Exception as e:
        cache[key] = {"results": [], "error": str(e)[:80]}
    return []


def pmid_lookup(pmid, cache):
    key = f"pmid:{pmid}"
    if key in cache:
        return cache[key]
    try:
        r = httpx.get(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            f"?db=pubmed&id={pmid}&retmode=json",
            headers=HEADERS, timeout=30)
        if r.status_code == 200:
            result = r.json().get("result", {}).get(str(pmid), {})
            doi = result.get("elocationid", "")
            m = re.search(r"doi:\s*(\S+)", doi or "")
            cache[key] = {"doi": m.group(1) if m else "",
                          "title": result.get("title", ""),
                          "source": result.get("source", "")}
        else:
            cache[key] = {"doi": ""}
    except Exception as e:
        cache[key] = {"doi": "", "error": str(e)[:80]}
    return cache[key]


def datacite_search(title, cache, key):
    """Search DataCite (theses, repos, datasets) — Crossref's blind spot."""
    if key in cache:
        return cache[key].get("results", [])
    try:
        r = httpx.get(
            f"https://api.datacite.org/dois?query={quote_plus(title)}&page[size]=5",
            headers=HEADERS, timeout=30)
        if r.status_code == 200:
            items = r.json().get("data", [])
            results = []
            for it in items:
                at = it.get("attributes", {})
                results.append({
                    "doi": at.get("doi", "").lower(),
                    "title": (at.get("titles") or [{}])[0].get("title", ""),
                    "authors": [c.get("name", "") for c in at.get("creators", []) if c.get("name")],
                    "year": at.get("publicationYear"),
                    "type": at.get("types", {}).get("resourceTypeGeneral", ""),
                })
            cache[key] = {"results": results}
            return results
        cache[key] = {"results": [], "status": r.status_code}
    except Exception as e:
        cache[key] = {"results": [], "error": str(e)[:80]}
    return []


def score_match(paper, cand):
    """Score a Crossref candidate against our paper record."""
    nt_paper = normalize_title(paper.get("title", ""))
    nt_cand = normalize_title(cand.get("title", ""))
    title_score = 1.0 if nt_paper == nt_cand else SequenceMatcher(
        None, nt_paper, nt_cand).ratio()

    # author check: our first author family in candidate authors
    author_ok = None  # None = can't check
    our_author = (paper.get("authors") or "").split(",")[0].strip().lower()
    our_family = re.split(r"\s+", our_author)[0]
    if our_family and cand["authors"]:
        author_ok = any(our_family in a.lower() for a in cand["authors"])

    # year check
    year_ok = None
    our_year = paper.get("year")
    if our_year and cand.get("year"):
        year_ok = abs(int(our_year) - int(cand["year"])) <= 1

    return title_score, author_ok, year_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min", type=float, default=0.90,
                    help="min normalized-title similarity to accept")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]
    no_doi = [p for p in papers if not p.get("doi")]
    print(f"{len(no_doi)} papers without DOI")

    cache = load_cache()

    # --- Pass 1: PMID path (exact) ---
    pmid_hits = {}
    for p in no_doi:
        pmid = pmid_from_url(p.get("url"))
        if pmid:
            res = pmid_lookup(pmid, cache)
            if res.get("doi"):
                pmid_hits[p["id"]] = res["doi"]
    print(f"PMID path: {len(pmid_hits)} resolved")
    for pid, doi in pmid_hits.items():
        print(f"  {pid}: {doi}")

    # --- Pass 2: Crossref fuzzy ---
    searchable = [p for p in no_doi
                  if p["id"] not in pmid_hits
                  and len(p.get("title", "")) > 15
                  and not p["title"].startswith("Untitled")
                  and p.get("doc_type") not in NO_DOI_EXPECTED]
    print(f"\nCrossref path: {len(searchable)} searchable "
          f"(skipping {len(no_doi) - len(pmid_hits) - len(searchable)} — "
          f"thesis/news/short-title)")

    proposals = {}

    def search_paper(p):
        key = f"cr:{p['id']}"
        results = crossref_search(p["title"], p.get("authors"), cache, key)
        time.sleep(0.35)  # polite pool
        return p, results

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for p, results in ex.map(search_paper, searchable):
            if not results:
                continue
            best, scores = None, None
            for cand in results:
                if not cand["doi"] or "jats" in cand["doi"]:
                    continue
                ts, a_ok, y_ok = score_match(p, cand)
                # accept: strong title, author corroboration if checkable
                if ts >= args.min and (a_ok is not False):
                    if best is None or ts > scores[0]:
                        best, scores = cand, (ts, a_ok, y_ok)
            if best:
                proposals[p["id"]] = {
                    "doi": best["doi"], "title": best["title"][:90],
                    "title_score": round(scores[0], 3),
                    "author_ok": scores[1], "year_ok": scores[2],
                }

    # --- Pass 3: DataCite (theses, repositories) for still-missing ---
    still_missing = [p for p in searchable
                     if p["id"] not in proposals and p["id"] not in pmid_hits]
    print(f"\nDataCite pass: {len(still_missing)} still without DOI")

    def dc_search_paper(p):
        key = f"dc:{p['id']}"
        results = datacite_search(p["title"], cache, key)
        time.sleep(0.3)
        return p, results

    dc_found = {}
    DC_GOOD_TYPES = {"Text", "Thesis", "Dissertation", "JournalArticle",
                     "Preprint", "Report", "Other"}
    DC_BAD_TITLE = re.compile(
        r"^(Additional file|Data from:|Data and code|Data complementing|"
        r"Supporting data|Supplementary)", re.I)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for p, results in ex.map(dc_search_paper, still_missing):
            if not results:
                continue
            for cand in results:
                if not cand["doi"] or cand["type"] not in DC_GOOD_TYPES:
                    continue
                if DC_BAD_TITLE.match(cand["title"]):
                    continue
                ts, a_ok, y_ok = score_match(p, cand)
                # DataCite is noisier: require ≥0.97 + author corroboration if checkable
                if ts >= 0.97 and (a_ok is not False):
                    dc_found[p["id"]] = {
                        "doi": cand["doi"], "title": cand["title"][:90],
                        "title_score": round(ts, 3),
                        "author_ok": a_ok, "year_ok": y_ok, "type": cand["type"],
                    }
                    break

    if dc_found:
        print(f"  DataCite resolved: {len(dc_found)}")
        for pid, v in list(dc_found.items())[:10]:
            print(f"    {pid}: {v['doi']}  score={v['title_score']}")
        if args.apply:
            for p in papers:
                pid = p["id"]
                if pid in dc_found and not p.get("doi"):
                    p["doi"] = dc_found[pid]["doi"]

    save_cache(cache)

    print(f"\nproposed: {len(proposals)} (threshold {args.min})")
    strong = {k: v for k, v in proposals.items() if v["title_score"] >= 0.97}
    medium = {k: v for k, v in proposals.items() if 0.90 <= v["title_score"] < 0.97}
    print(f"  strong (≥0.97): {len(strong)}")
    print(f"  medium (0.90–0.97): {len(medium)}")

    print("\n--- STRONG ---")
    for pid, v in list(strong.items())[:10]:
        print(f"  {pid}: {v['doi']}")
        print(f"    crossref: {v['title']}")
    if len(strong) > 10:
        print(f"  … +{len(strong)-10} more")
    print("\n--- MEDIUM (review) ---")
    for pid, v in list(medium.items())[:15]:
        print(f"  {pid}: {v['doi']}  score={v['title_score']} author={v['author_ok']} year={v['year_ok']}")
        print(f"    crossref: {v['title']}")
    if len(medium) > 15:
        print(f"  … +{len(medium)-15} more")

    if args.apply:
        # merge-write: preserve structure, only set doi fields
        changed = 0
        for p in papers:
            pid = p["id"]
            if pid in pmid_hits and not p.get("doi"):
                p["doi"] = pmid_hits[pid]
                changed += 1
            elif pid in strong and not p.get("doi"):
                p["doi"] = strong[pid]["doi"]
                changed += 1
        # medium only with author corroboration
        for p in papers:
            pid = p["id"]
            if pid in medium and not p.get("doi") and medium[pid]["author_ok"] is True:
                p["doi"] = medium[pid]["doi"]
                changed += 1
        PAPERS_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        print(f"\nAPPLIED: {changed} DOIs written (strong + PMID + author-corroborated medium)")
    else:
        print("\n(dry-run — no changes written; rerun with --apply)")


if __name__ == "__main__":
    main()
