#!/usr/bin/env python3
"""
Metadata cleanup pass (D62): fix bad titles, add categories, clean summaries.
Targets papers with missing/placeholder titles, no category, or no authors.

Deterministic first (markdown title extraction, scope→category mapping),
LLM for stubborn cases (optional).

Usage: pixi run python scripts/papers/cleanup_meta.py [--llm]
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"

BAD_TITLE_END = re.compile(r"\b(by|of|the|and|in|to|a|with|from)$", re.I)


def extract_title_from_md(pid):
    """Best title from markdown: longest sane # heading."""
    md = MD_DIR / f"{pid}.md"
    if not md.exists():
        return None
    text = md.read_text(errors="ignore")[:8000]
    best = ""
    for m in re.finditer(r"^#{1,2}\s+(.{15,200})$", text, re.M):
        t = re.sub(r"[*_#]", "", m.group(1)).strip()
        words = t.split()
        if len(words) >= 4 and not BAD_TITLE_END.search(t):
            if len(t) > len(best):
                best = t
    return best or None


def infer_category(paper):
    """Deterministic category from scope + title keywords."""
    title = (paper.get("title") or "").lower()
    scope = paper.get("scope") or ""
    species = " ".join(paper.get("species_focus") or []).lower()

    if scope == "vaccination" or re.search(r"vaccin|immunization", title):
        return "Vaccines"
    if scope == "human":
        return "Human Infection"
    if scope == "mammalian" or re.search(r"cattle|bovine|dairy|cat|dog|fox|mink|marine mammal|sea lion", species):
        return "Mammalian Spillover"
    if re.search(r"outbreak|spread|transmission|surveillance|epidemiol|mortality event|migration", title):
        return "Epidemiology"
    if re.search(r"genome|genomic|sequence|phylogen|evolution|mutation", title):
        return "Viral Evolution"
    if re.search(r"immune|immunol|interferon|innate|cytokine|antiviral|restriction factor", title):
        return "Immunology"
    if re.search(r"pathogen|virulence|lesion|patholog|disease", title):
        return "Pathogenesis"
    if re.search(r"seabird|colony|wild bird|waterfowl|shorebird|migrat", title + " " + species):
        return "Wild Birds"
    if re.search(r"poultry|chicken|farm|domestic", title + " " + species):
        return "Poultry"
    if scope == "avian":
        return "Avian Influenza"
    return "Other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="also LLM-fix stubborn titles")
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    n_title = n_cat = n_auth = n_sum = 0

    for p in papers:
        pid = p["id"]
        t = p.get("title") or ""

        # ── Fix bad titles ──
        is_bad = (
            not t
            or t.lower() in ("sciencedirect", "input 2023", "input 2024", "task 2024")
            or (t.startswith(("Input ", "Task ")) and len(t.split()) <= 3)
            or (t == "ScienceDirect")
        )
        if is_bad:
            md_title = extract_title_from_md(pid)
            if md_title:
                p["title"] = md_title[:180]
                n_title += 1
            elif args.llm:
                # try summary first line
                s = p.get("summary") or ""
                if isinstance(s, str) and len(s) > 30:
                    first = s.split(".")[0]
                    if len(first.split()) >= 5:
                        p["title"] = first[:180]
                        n_title += 1

        # ── Fix array summaries ──
        s = p.get("summary")
        if isinstance(s, list):
            p["summary"] = " ".join(str(x) for x in s[:3])[:400]
            n_sum += 1

        # ── Add categories ──
        if not p.get("category"):
            cat = infer_category(p)
            if cat != "Other":
                p["category"] = cat
                n_cat += 1

        # ── Fix missing authors ──
        if not p.get("authors"):
            md = MD_DIR / f"{pid}.md"
            if md.exists():
                text = md.read_text(errors="ignore")[:4000]
                # look for author patterns after title
                title_m = re.search(r"^#\s+(.{15,200})$", text, re.M)
                if title_m:
                    after = text[title_m.end():title_m.end() + 1000]
                    # name-like: "Word Word" or "Word X." patterns, comma-separated
                    for line in after.split("\n")[:6]:
                        clean = re.sub(r"<sup>.*?</sup>", "", line).strip()
                        clean = re.sub(r"[\d*✉†‡§¶]", "", clean).strip(" .,-")
                        names = [n.strip() for n in clean.split(",") if n.strip()]
                        valid = [n for n in names if 3 < len(n) < 40 and
                                 re.match(r"^[A-Z]", n) and
                                 not re.search(r"university|department|laboratory|institute", n, re.I)]
                        if len(valid) >= 2:
                            p["authors"] = ", ".join(valid[:6]) + (", et al" if len(valid) > 6 else "")
                            n_auth += 1
                            break

    PAPERS_JSON.write_text(json.dumps(data, indent=1))

    # report
    still_bad = [p["id"] for p in papers if not p.get("title")
                 or p["title"].lower() in ("sciencedirect", "input 2023")
                 or (p["title"].startswith(("Input ", "Task ")) and len(p["title"].split()) <= 3)]
    still_nocat = [p["id"] for p in papers if not p.get("category")]

    print(f"fixed: {n_title} titles, {n_cat} categories, {n_auth} authors, {n_sum} summaries")
    print(f"remaining bad titles: {len(still_bad)}")
    print(f"remaining no-category: {len(still_nocat)}")

    from collections import Counter
    cats = Counter(p.get("category") for p in papers)
    print("categories:", dict(cats.most_common(12)))


if __name__ == "__main__":
    main()
