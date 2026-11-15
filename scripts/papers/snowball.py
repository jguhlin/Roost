#!/usr/bin/env python3
"""
Citation snowball miner (D86): discover H5N1-relevant papers through the
citations of the papers we already hold.

For each seed paper with a PMCID (via EuropePMC CITES: search) or DOI
(via OpenAlex cites: filter), fetch works that CITE it, filter for avian-
influenza relevance, deduplicate against the database, and write
new_papers.json (same shape search_papers.py produces) so the standard
merge_papers.py review flow applies.

Resume-safe: processed seeds logged to scripts/papers/snowball_log.json.

Usage:
  pixi run python scripts/papers/snowball.py                # all seeds
  pixi run python scripts/papers/snowball.py --limit 30     # first N seeds
  pixi run python scripts/papers/snowball.py --seed ID      # single seed
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
NEW_PAPERS_JSON = PROJECT_ROOT / "scripts" / "papers" / "new_papers.json"
LOG = PROJECT_ROOT / "scripts" / "papers" / "snowball_log.json"

UA = "Roost/1.0 (citation snowball)"
# relevance filter: citing work must mention avian influenza specifically
RELEVANCE = re.compile(
    r"H5N1|HPAI|highly pathogenic avian|avian influenza|A\(H5N"
    r"|influenza A virus subtype H5", re.IGNORECASE)


def fetch_json(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def normalize_title(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def existing_keys():
    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    dois = {p["doi"].lower() for p in papers if p.get("doi")}
    titles = {normalize_title(p.get("title")) for p in papers}
    return dois, titles


def citing_via_europepmc(pmcid, cap=20):
    """Works citing a PMC article (EuropePMC CITES: query)."""
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
           f"?query={quote_plus(f'CITES:PMC{pmcid}')}"
           "&format=json&pageSize=25&resultType=core")
    try:
        data = fetch_json(url)
    except Exception:
        return []
    out = []
    for r in data.get("resultList", {}).get("result", [])[:cap]:
        out.append({
            "title": r.get("title") or "",
            "doi": r.get("doi"),
            "pmcid": (r.get("pmcid") or "").replace("PMC", "") or None,
            "authors": (r.get("authorString") or "").split(",")[0] + " et al.",
            "journal": r.get("journalTitle") or "Unknown",
            "year": int(r.get("pubYear") or 0) or None,
            "is_open_access": r.get("isOpenAccess") == "Y",
        })
    time.sleep(0.35)
    return out


def citing_via_openalex(doi, cap=20):
    """Works citing a DOI (OpenAlex cites: filter)."""
    try:
        # resolve the work id first
        work = fetch_json(f"https://api.openalex.org/works/doi:{doi}"
                          "?mailto=roost-project@example.org")
        wid = work.get("id")  # https://openalex.org/W123
    except Exception:
        return []
    try:
        data = fetch_json(
            "https://api.openalex.org/works"
            f"?filter=cites:{wid.rsplit('/', 1)[-1]}"
            f"&per-page={cap}&mailto=roost-project@example.org")
    except Exception:
        return []
    out = []
    for w in data.get("results", []):
        d = (w.get("doi") or "").replace("https://doi.org/", "")
        src = (((w.get("primary_location") or {}).get("source")) or {})
        out.append({
            "title": w.get("display_name") or "",
            "doi": d or None,
            "pmcid": None,
            "authors": ((w.get("authorships") or [{}])[0]
                        .get("author", {}).get("display_name", "Unknown")
                        + " et al."),
            "journal": src.get("display_name") or "Unknown",
            "year": w.get("publication_year"),
            "is_open_access": (w.get("open_access") or {}).get("is_oa", False),
        })
    time.sleep(0.35)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="process only the first N unprocessed seeds")
    ap.add_argument("--seed", help="single seed paper id")
    ap.add_argument("--cap", type=int, default=20,
                    help="max citing papers harvested per seed")
    args = ap.parse_args()

    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    dois, titles = existing_keys()

    # seeds: papers with a PMC URL/PMCID, else DOI (openalex route)
    seeds = []
    for p in papers:
        pmcid = None
        url = p.get("url") or ""
        m = re.search(r"PMC(\d+)", url)
        if m:
            pmcid = m.group(1)
        if args.seed and p["id"] != args.seed:
            continue
        if pmcid or p.get("doi"):
            seeds.append({"id": p["id"], "pmcid": pmcid, "doi": p.get("doi"),
                          "title": p.get("title")})

    done = set()
    if LOG.exists():
        try:
            done = set(json.loads(LOG.read_text()).get("processed", []))
        except Exception:
            pass
    todo = [s for s in seeds if s["id"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"snowball: {len(seeds)} seeds, {len(done)} processed, "
          f"{len(todo)} to process")

    harvested = {}
    processed = []
    for i, s in enumerate(todo, 1):
        works = []
        if s["pmcid"]:
            works = citing_via_europepmc(s["pmcid"], args.cap)
        if not works and s["doi"]:
            works = citing_via_openalex(s["doi"], args.cap)
        n_new = 0
        for w in works:
            title = w["title"]
            if not RELEVANCE.search(title):
                continue
            if w.get("doi") and w["doi"].lower() in dois:
                continue
            if normalize_title(title) in titles:
                continue
            key = w.get("doi") or normalize_title(title)
            if key in harvested:
                harvested[key]["via"].append(s["id"])
                continue
            rec = dict(w)
            rec["source"] = "snowball"
            rec["via"] = [s["id"]]
            rec["query"] = f"cites:{s['id']}"
            harvested[key] = rec
            n_new += 1
        processed.append(s["id"])
        if i % 10 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] harvested {len(harvested)} unique "
                  f"(+{n_new} from {s['id']})")
            # checkpoint
            done.update(processed)
            LOG.write_text(json.dumps(
                {"processed": sorted(done),
                 "updated": datetime.now().isoformat()}, indent=1))
            processed = []

    done.update(processed)
    LOG.write_text(json.dumps(
        {"processed": sorted(done),
         "updated": datetime.now().isoformat()}, indent=1))

    out = sorted(harvested.values(),
                 key=lambda r: -(r.get("year") or 0))
    NEW_PAPERS_JSON.write_text(json.dumps({
        "search_date": datetime.now().isoformat(),
        "days_searched": 0,
        "sources": ["snowball"],
        "total_found": len(out),
        "new_papers": out,
    }, indent=1, ensure_ascii=False))
    print(f"→ {NEW_PAPERS_JSON.name}: {len(out)} new candidate papers "
          f"(review with merge_papers.py)")


if __name__ == "__main__":
    main()
