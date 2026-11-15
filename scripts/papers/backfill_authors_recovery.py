#!/usr/bin/env python3
"""Recovery pass for papers where the author list is still missing.

Three strategies, in order:
  1. Crossref TITLE SEARCH (works without a DOI) for papers that look like
     real journal articles — authoritative full rosters
  2. Deeper LLM retry: 30k head chars (authors sometimes sit after the
     abstract or in a footnote block)
  3. Corporate author for agency reports (doc_type == report):
     {"family": <journal/org>, "given": ""}

Incremental saves; skips anything that already has authors_full.

Usage: LLM_BASE_URL=http://localhost:8005/v1 \
  pixi run python scripts/papers/backfill_authors_recovery.py
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"
CACHE = ROOT / "data" / "papers" / "doi_meta_cache.json"
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
MAILTO = "roost-project@example.org"

JUNK_RE = re.compile(r"list of issues|volume \d+, issue \d+", re.I)
PROMPT = """Find the author list of this paper. Authors may appear after the
abstract, in footnotes, or as superscript affiliations. Return ONLY a JSON
array: [{"family": "Surname", "given": "Initials or names"}] — every author,
in order, no "et al.". If truly absent, return []."""


def crossref_title_search(title: str):
    q = urllib.parse.quote(title[:200])
    url = (f"https://api.crossref.org/works?query.bibliographic={q}"
           f"&rows=3&mailto={MAILTO}")
    req = urllib.request.Request(url, headers={"User-Agent": f"Roost/1.0 ({MAILTO})"})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.loads(r.read())["message"]["items"]
    for it in items:
        t = (it.get("title") or [""])[0].lower()
        if t and (t[:60] == title.lower().strip()[:60]
                  or title.lower().strip()[:50] in t):
            authors = [{"family": a.get("family", ""), "given": a.get("given", "")}
                       for a in it.get("author", []) if a.get("family")]
            if authors:
                return it.get("DOI", ""), authors
    return None, None


def call_llm(text: str) -> str:
    body = json.dumps({"model": MODEL, "temperature": 0.0, "max_tokens": 2048,
                       "messages": [{"role": "system",
                                     "content": "You extract bibliographic metadata. Strict JSON only."},
                                    {"role": "user", "content": PROMPT + "\n\n---\n" + text}]}).encode()
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def parse_list(raw: str):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        arr = json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("["), raw.rfind("]")
        arr = json.loads(raw[s:e + 1]) if 0 <= s < e else []
    return [{"family": str(a["family"]).strip(), "given": str(a.get("given", "") or "").strip()}
            for a in arr if isinstance(a, dict) and a.get("family")]


def main():
    pj = json.loads(PAPERS_JSON.read_text())
    papers = pj["papers"] if isinstance(pj, dict) else pj
    targets = [p for p in papers
               if isinstance(p, dict) and not p.get("authors_full")
               and p.get("authors_source") in ("llm_not_found", "llm_no_fulltext",
                                               "crossref_failed", "crossref_pending")]
    print(f"recovery targets: {len(targets)}")
    stats = {"crossref_title": 0, "llm_deep": 0, "corporate": 0, "junk_flagged": 0, "still_missing": 0}
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    for p in targets:
        title = (p.get("title") or "").strip()
        # 0. flag scraping artifacts — not papers; authors N/A by nature
        if JUNK_RE.search(title):
            p["authors_source"] = "scraping_artifact"
            stats["junk_flagged"] += 1
            continue
        got = False
        # 1. Crossref by title (real articles)
        if title and len(title) > 15:
            try:
                doi, authors = crossref_title_search(title)
                if authors:
                    p["authors_full"] = authors
                    p["authors_source"] = "crossref_title"
                    if doi:
                        p.setdefault("doi", doi)
                        cache[f"doi:{doi.lower()}"] = {"authors": authors}
                    got = True
            except Exception:
                pass
            time.sleep(1.0)
        if got:
            stats["crossref_title"] += 1
            PAPERS_JSON.write_text(json.dumps(pj, indent=1))
            print(f"  crossref: {p['id']}: {len(p['authors_full'])} authors")
            continue
        # 2. corporate author for reports
        if p.get("doc_type") == "report" and p.get("journal"):
            p["authors_full"] = [{"family": p["journal"], "given": ""}]
            p["authors_source"] = "corporate"
            stats["corporate"] += 1
            PAPERS_JSON.write_text(json.dumps(pj, indent=1))
            continue
        # 3. deeper LLM retry (30k)
        md = MD_DIR / f"{p['id']}.md"
        if md.exists():
            try:
                authors = parse_list(call_llm(md.read_text(errors="ignore")[:30000]))
                if authors:
                    p["authors_full"] = authors
                    p["authors_source"] = "llm_deep"
                    stats["llm_deep"] += 1
                    print(f"  llm-deep: {p['id']}: {len(authors)} authors")
                else:
                    stats["still_missing"] += 1
            except Exception as e:
                print(f"  {p['id']}: llm error {str(e)[:80]}")
                stats["still_missing"] += 1
        else:
            stats["still_missing"] += 1
        PAPERS_JSON.write_text(json.dumps(pj, indent=1))

    CACHE.write_text(json.dumps(cache, indent=1))
    print(f"recovery: {stats}")
    have = sum(1 for p in papers if isinstance(p, dict) and p.get("authors_full"))
    print(f"full author lists now: {have} / {len(papers)}")


if __name__ == "__main__":
    main()
