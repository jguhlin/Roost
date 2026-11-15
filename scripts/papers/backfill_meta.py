#!/usr/bin/env python3
"""
Backfill metadata for auto-ID'd papers (input_*/task_*) from their
markdown + fast-pass internal analyses:
  - title: markdown H1 (already done in earlier pass — re-verified)
  - authors: lines after the H1, <sup>-stripped, name-shaped tokens
  - doi + url: DOI regex in the first 10k chars
  - summary: internal analysis results_summary (interim until the full
    digest's metadata step supersedes)

Usage: pixi run python scripts/papers/backfill_meta.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"
INTERNAL = ROOT / "data" / "papers" / "internal"

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>\]\),;]+)", re.I)
AFFIL_WORDS = re.compile(r"university|department|laboratory|institute|college|"
                         r"center|centre|hospital|school|faculty|ministry|"
                         r"agency|director|editor|reviewed", re.I)
NAME_RE = re.compile(r"^[A-Z][A-Za-zà-ÿ'\-]*(?:\s+[A-Z][A-Za-zà-ÿ'\-.]*){0,3}$")
BAD_TITLE_END = re.compile(r"\b(by|of|the|and|in|to|a|with|from)$", re.I)


def pick_title(head: str) -> str:
    """Longest sane # heading: ≥4 words, not ending mid-phrase."""
    best = ""
    for m in re.finditer(r"^#{1,2}\s+(.{15,200})$", head, re.M):
        t = re.sub(r"[*_#]", "", m.group(1)).strip()
        words = t.split()
        if len(words) >= 4 and not BAD_TITLE_END.search(t):
            if len(t) > len(best):
                best = t
    return best


def extract_authors(md_head: str) -> str:
    """Author block = lines between the H1 and the first blank-separated
    non-name content. Strip <sup> affixes, keep name-shaped tokens."""
    lines = md_head.splitlines()
    title_idx = None
    for i, l in enumerate(lines):
        if l.startswith("# ") and len(l) > 20:
            title_idx = i
            break
    if title_idx is None:
        return ""
    names = []
    for l in lines[title_idx + 1:title_idx + 8]:
        clean = re.sub(r"<sup>.*?</sup>", " ", l)
        clean = re.sub(r"[\d*✉†‡§¶]|#\d+", " ", clean)
        clean = clean.replace(" and ", ", ")
        for part in clean.split(","):
            part = re.sub(r"\s+", " ", part).strip(" .-–")
            if not part or AFFIL_WORDS.search(part):
                continue
            if NAME_RE.match(part) and any(c.isupper() for c in part[1:]):
                names.append(part)
        if names and (AFFIL_WORDS.search(l) or re.match(r"^\s*\d", l)):
            break
    names = list(dict.fromkeys(names))[:8]
    if len(names) > 6:
        return ", ".join(names[:5]) + ", et al"
    return ", ".join(names)


def main():
    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    n_title = n_auth = n_doi = n_sum = 0
    for x in papers:
        pid = x["id"]
        if not re.match(r"^(input|task)_", pid):
            continue
        md = MD_DIR / f"{pid}.md"
        if not md.exists():
            continue
        text = md.read_text(errors="ignore")
        head = text[:6000]

        if not x.get("title") or re.fullmatch(r"(Input|Task) \d+( \d+)?", x.get("title") or "", re.I) \
                or len((x.get("title") or "").split()) < 4 or BAD_TITLE_END.search(x.get("title") or ""):
            t = pick_title(head)
            if t:
                x["title"] = t[:180]
                n_title += 1

        if not x.get("authors"):
            authors = extract_authors(head)
            if authors:
                x["authors"] = authors
                n_auth += 1

        if not x.get("doi"):
            m = DOI_RE.search(text[:10000])
            if m:
                doi = m.group(1).rstrip(".")
                x["doi"] = doi
                x["url"] = f"https://doi.org/{doi}"
                n_doi += 1

        if not x.get("summary"):
            ip = INTERNAL / f"{pid}.json"
            if ip.exists():
                try:
                    d = json.loads(ip.read_text())
                    summ = ((d.get("knowledge_summary") or {}).get("one_liner")
                            or d.get("results_summary") or "")
                    summ = re.sub(r"\s+", " ", str(summ)).strip()
                    if len(summ) > 40:
                        x["summary"] = summ[:400]
                        n_sum += 1
                except Exception:
                    pass

    PAPERS_JSON.write_text(json.dumps(data, indent=1))
    print(f"backfilled: {n_title} titles, {n_auth} authors, {n_doi} DOIs, {n_sum} summaries")


if __name__ == "__main__":
    main()
