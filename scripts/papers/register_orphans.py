#!/usr/bin/env python3
"""
Orphan markdown intake (D81): register papers whose markdown exists in
docs/papers_md but which never got a papers.json entry (fast-pass
registration gap — same failure mode as the read_* three).

Per orphan:
  - skip _dup_* (dedup archives) and *_correction (attached to parents)
  - extract title from first heading / header lines
  - extract DOI (doi.org link pattern), journal, year where present
  - create minimal entry (id = filename stem)
Then downstream: find_dois → backfill_doi_meta → tag_scope → campaign phases.

Usage: pixi run python scripts/papers/register_orphans.py [--apply]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"

DOI_RE = re.compile(r"(?:doi\.org/|doi:\s*|DOI:\s*)(10\.\d{4,5}/[^\s)\]\"<>]+)", re.I)
YEAR_RE = re.compile(r"\b(19[89]\d|20[0-2]\d)\b")


def extract_meta(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()][:30]
    title, doi, journal, year = None, None, None, None

    # DOI from the header zone
    for l in lines[:12]:
        m = DOI_RE.search(l)
        if m and not doi:
            doi = m.group(1).rstrip(".,")

    # title: first markdown heading, else first long line that isn't a doi/citation line
    for l in lines:
        if l.startswith("#"):
            cand = l.lstrip("# ").strip()
            if len(cand) > 12:
                title = cand
                break
    if not title:
        for l in lines:
            if (len(l) > 25 and not l.startswith(("http", "<!", "<sup"))
                    and "doi" not in l.lower() and not DOI_RE.search(l)
                    and not re.fullmatch(r"[\d\s\-–—|,*()]+", l)
                    and "_et al._" not in l and "et al." not in l[:40]
                    and not l.startswith(("RESEARCH", "Open Access", "Article"))):
                title = l.strip("*_")
                break

    # year from header zone
    for l in lines[:12]:
        m = YEAR_RE.search(l)
        if m:
            year = int(m.group(1))
            if 1990 <= year <= 2030:
                break
            year = None

    # journal guess: italic journal-citation line like "Chen _et al. Veterinary Research (2025) 56:104_"
    for l in lines[:6]:
        m = re.search(r"_et al\._?\s+([A-Z][A-Za-z&\-\s]{4,40}?)\s+\(\d{4}\)", l)
        if m:
            journal = m.group(1).strip()
            break
        m = re.match(r"([A-Z][A-Za-z&\-\s]{4,40})\s+\d{4};", l)
        if m:
            journal = m.group(1).strip()
            break

    return title, doi, journal, year


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]
    ids = {p["id"] for p in papers}

    orphans = []
    for f in sorted(MD_DIR.glob("*.md")):
        stem = f.stem
        if stem.startswith("_dup_"):
            continue
        if stem.endswith("_correction") and stem[: -len("_correction")] in ids:
            continue  # attached correction for an existing parent
        if stem in ids:
            continue
        orphans.append(f)

    print(f"orphan markdowns: {len(orphans)}")

    new_entries = []
    for f in orphans:
        text = f.read_text(errors="replace")[:4000]
        title, doi, journal, year = extract_meta(text)
        entry = {
            "id": f.stem,
            "title": (title or f.stem.replace("_", " "))[:250],
            "doi": doi,
            "authors": "",  # D124: always present — unguarded consumers crash on undefined
            "journal": journal or "",
            "year": year,
            "category": "General",
            "topics": [],
            "summary": "",
            "doc_type": "article",
            "language": "en",
            "scope": "avian",
            "source": "orphan_intake",
            "added": "2026-09-04",
        }
        new_entries.append(entry)
        flag = "✓" if title and len(title) > 20 else "?"
        print(f"  {flag} {f.stem}: {entry['title'][:60]} doi={doi or '—'}")

    if args.apply:
        papers.extend(new_entries)
        PAPERS_JSON.write_text(json.dumps({"papers": papers}, indent=1, ensure_ascii=False))
        d = json.loads(PAPERS_JSON.read_text())
        assert isinstance(d, dict) and "papers" in d
        print(f"\nAPPLIED: +{len(new_entries)} papers → {len(d['papers'])} total")
    else:
        print(f"\n(dry-run — {len(new_entries)} would be added; rerun with --apply)")


if __name__ == "__main__":
    main()
