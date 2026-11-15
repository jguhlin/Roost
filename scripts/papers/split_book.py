#!/usr/bin/env python3
"""split_book.py — split book-length PDFs into chapter PDFs (2026-11).

Not part of the intake pipeline: books would overwhelm the per-paper
pipeline (one 600-page "paper" pollutes corpus stats). This tool stages
splits for LATER manual intake — outputs land in
pdfs_to_process/_split/<stem>/NN - <chapter>.pdf and are NOT picked up
by process_new_papers.py (it globs *.pdf at the top level only).

Two detection paths:
  1. PDF bookmarks (get_toc): chapters = entries at the level that
     yields a sensible count (target 5–60 segments; prefer level 1).
  2. No bookmarks: parse the PRINTED table of contents — find pages
     whose text looks like a contents list ("Contents" heading), extract
     "<title> .... <pagenum>" lines, resolve against the page-offset.
     Falls back to "Chapter N" heading detection in body text.

Dry-run by default (lists detected chapters); --write produces the PDFs.

Usage:
  pixi run python scripts/papers/split_book.py <book.pdf>          # dry-run
  pixi run python scripts/papers/split_book.py <book.pdf> --write
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SPLIT_DIR = ROOT / "pdfs_to_process" / "_split"

CHAPTER_RE = re.compile(r"^\s*(chapter|chapitre|kapitel|section)\s+"
                        r"([\divxl]+|\d+)\b[:.\s—-]*(.*)$", re.I)
DOTLEADER_RE = re.compile(r"^(.*?)[\s.·⋯]{3,}(\d{1,4})\s*$")
# numbered-entry TOC line: "1. Inﬂ uenza A Virus" (page number may follow
# on the SAME line or the next — Swayne-style extraction has no leaders)
ENTRY_RE = re.compile(r"^(\d{1,2})\.\s+(.+?)\s*(\d{1,4})?$")
PURE_NUM_RE = re.compile(r"^(\d{1,4})$")
_LIGS = {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl",
         "\ufb03": "ffi", "\ufb04": "ffl"}


def _norm_title(s: str) -> str:
    """Fix extraction ligature artifacts: 'Inﬂ uenza' → 'Influenza'."""
    s = re.sub(r"([\ufb00-\ufb04])\s+", lambda m: _LIGS[m.group(1)], s)
    for k, v in _LIGS.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ bookmarks
def chapters_from_toc(doc: pymupdf.Document) -> list[tuple[str, int, int]] | None:
    """(title, start, end) from bookmarks — pick the level with a sane count."""
    toc = [t for t in doc.get_toc() if t[2] > 0]  # drop deleted/negative pages
    if not toc:
        return None
    by_level: dict[int, list[tuple[int, str]]] = {}
    for lvl, title, page in toc:
        by_level.setdefault(lvl, []).append((page, title.strip()))
    best = None
    for lvl in sorted(by_level):
        entries = by_level[lvl]
        if 5 <= len(entries) <= 60:
            best = (lvl, entries)
            break
    if not best:
        return None
    lvl, entries = best
    chapters = []
    for i, (page, title) in enumerate(entries):
        end = entries[i + 1][0] - 1 if i + 1 < len(entries) else doc.page_count
        chapters.append((title, page, max(page, end)))
    return chapters


# -------------------------------------------------------------- printed TOC
def find_printed_toc_pages(doc: pymupdf.Document, scan: int = 40) -> list[int]:
    """Pages that look like a contents listing: a 'contents' heading, or
    dot-leader lines, or several numbered-entry lines."""
    pages = []
    for pno in range(min(scan, doc.page_count)):
        text = doc[pno].get_text()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        leaders = sum(1 for l in lines if DOTLEADER_RE.match(l))
        entries = sum(1 for l in lines if ENTRY_RE.match(_norm_title(l)))
        if leaders >= 5 or entries >= 4 or (
                "contents" in text.lower()[:300] and (leaders >= 3 or entries >= 3)):
            pages.append(pno)
    return pages


def parse_printed_toc(doc: pymupdf.Document) -> list[tuple[str, int]] | None:
    """(title, printed-page) pairs — handles dot-leader style AND the
    title-line/page-number-on-next-line style (Swayne), including titles
    that WRAP across lines before their page number."""
    entries: list[tuple[str, int]] = []
    for pno in find_printed_toc_pages(doc):
        lines = [_norm_title(l) for l in doc[pno].get_text().splitlines()]
        lines = [l for l in lines if l and not re.match(r"^[ivxlcdm]+$", l, re.I)]
        i = 0
        while i < len(lines):
            m = DOTLEADER_RE.match(lines[i])
            if m and m.group(1).strip():
                entries.append((m.group(1).strip(), int(m.group(2))))
                i += 1
                continue
            m = ENTRY_RE.match(lines[i])
            if m and m.group(2) and len(m.group(2)) > 3:
                title_parts = [m.group(2)]
                page = m.group(3)
                j = i + 1
                # consume continuation lines until the page number
                while (not page and j < len(lines) and j - i <= 4
                       and not ENTRY_RE.match(lines[j])):
                    if PURE_NUM_RE.match(lines[j]):
                        page = PURE_NUM_RE.match(lines[j]).group(1)
                    else:
                        title_parts.append(lines[j])
                    j += 1
                if page:
                    entries.append((" ".join(title_parts).strip(), int(page)))
                    i = j
                    continue
            i += 1
    if len(entries) < 5:
        return None
    return entries


def display_type_pages(doc: pymupdf.Document,
                        lo: float = 20.0, hi: float = 45.0) -> list[tuple[int, str]]:
    """(1-based page, concatenated display-type text) — chapter openers
    carry display type in this corpus (Swayne: ~26pt)."""
    out = []
    for pno in range(doc.page_count):
        spans = [s["text"] for b in doc[pno].get_text("dict")["blocks"]
                 if b.get("type") == 0
                 for l in b["lines"] for s in l["spans"]
                 if lo <= s["size"] <= hi and s["text"].strip()]
        if spans:
            out.append((pno + 1, _norm_title(" ".join(spans))))
    return out


def chapters_from_display(doc: pymupdf.Document,
                          printed: list[tuple[str, int]] | None
                          ) -> list[tuple[str, int, int]] | None:
    """Pair display-type chapter openers (numbered 'N Title' big text)
    with printed-TOC titles by ORDER; page ranges from opener positions.
    Robust where body-text search false-positives (chapters cite each
    other constantly) and where a global printed→pdf offset can't exist
    (unnumbered color plates shift numbering mid-book)."""
    numbered = [(pg, text) for pg, text in display_type_pages(doc)
                if re.match(r"^\d{1,2}\s+.{4,}", text)]
    if len(numbered) < 3:
        return None
    titles = [t for t, _ in (printed or [])]
    if titles and len(titles) == len(numbered):
        names = titles  # TOC titles are single-line and complete
    else:
        names = [text[:80] for _, text in numbered]
    chapters = []
    for i, ((pg, _), name) in enumerate(zip(numbered, names)):
        end = numbered[i + 1][0] - 1 if i + 1 < len(numbered) else doc.page_count
        chapters.append((name, pg, end))
    # non-numbered display page right after the last opener (e.g. Index)
    # terminates the final chapter
    if numbered:
        last_pg = numbered[-1][0]
        later = [pg for pg, text in display_type_pages(doc) if pg > last_pg]
        if later:
            prev = chapters[-1]
            chapters[-1] = (prev[0], prev[1], min(prev[2], later[0] - 1))
    return chapters


def chapters_from_printed_toc(doc: pymupdf.Document) -> list[tuple[str, int, int]] | None:
    """Locate each printed-TOC chapter's START PAGE in the body by chained
    text search — robust to unnumbered inserts (color plates) that make a
    single printed→pdf offset impossible."""
    entries = parse_printed_toc(doc)
    if not entries:
        return None
    toc_end = max(find_printed_toc_pages(doc)) + 1
    chapters: list[tuple[str, int, int]] = []
    cursor = toc_end
    for title, _printed in entries:
        probe = _norm_title(title).lower()[:28]
        start = None
        for pno in range(cursor, min(cursor + 120, doc.page_count)):
            head = _norm_title(doc[pno].get_text()[:400]).lower()
            if probe in head:
                start = pno + 1  # 1-based
                break
        if start is None:
            continue  # unlocatable entry — skip rather than guess
        if chapters:
            prev = chapters[-1]
            chapters[-1] = (prev[0], prev[1], start - 1)
        chapters.append((title, start, doc.page_count))
        cursor = start + 1
    return chapters if len(chapters) >= 3 else None


def _resolve_offset(doc: pymupdf.Document, first_title: str,
                    first_printed: int, toc_end: int) -> int:
    """printed-to-pdf page offset: find the pdf page where chapter 1 actually
    starts (its title appears in the page's opening text) — front matter
    between TOC and chapter 1 breaks the naive heuristic."""
    probe = _norm_title(first_title).lower()[:30]
    for pno in range(toc_end, min(toc_end + 30, doc.page_count)):
        head = _norm_title(doc[pno].get_text()[:400]).lower()
        if probe and probe in head:
            return (pno + 1) - first_printed  # 1-based pdf page
    return (toc_end + 1) - first_printed  # fallback, warn via offset sanity


def chapters_from_headings(doc: pymupdf.Document) -> list[tuple[str, int, int]]:
    """Fallback: 'Chapter N' lines on body pages (text-position aware)."""
    starts: list[tuple[int, str]] = []
    for pno in range(3, doc.page_count):  # skip cover/title
        text = doc[pno].get_text()
        for line in text.splitlines()[:12]:
            m = CHAPTER_RE.match(line.strip())
            if m and m.group(3).strip():
                starts.append((pno, f"{line.strip()[:80]}"))
                break
    chapters = []
    for i, (pno, title) in enumerate(starts):
        end = starts[i + 1][0] - 1 if i + 1 < len(starts) else doc.page_count - 1
        if end - pno >= 1:
            chapters.append((title, pno + 1, end + 1))
    return chapters


# ------------------------------------------------------------------- output
def write_chapters(doc: pymupdf.Document, stem: str,
                   chapters: list[tuple[str, int, int]], out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for i, (title, start, end) in enumerate(chapters, 1):
        safe = re.sub(r"[^\w\s-]", "", _norm_title(title))[:60].strip() or f"part{i}"
        safe = re.sub(r"\s+", " ", safe)
        dest = out_dir / f"{i:02d} - {safe}.pdf"
        part = pymupdf.open()
        part.insert_pdf(doc, from_page=start - 1, to_page=min(end, doc.page_count) - 1)
        part.save(dest)
        part.close()
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Split a book PDF into chapter PDFs")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--write", action="store_true",
                    help="write the split PDFs (default: dry-run listing)")
    args = ap.parse_args()

    doc = pymupdf.open(args.pdf)
    stem = args.pdf.stem
    print(f"{stem}: {doc.page_count} pages")

    chapters = chapters_from_toc(doc)
    method = "bookmarks"
    if not chapters:
        printed = parse_printed_toc(doc)
        chapters = chapters_from_display(doc, printed)
        if chapters:
            method = ("display-type openers + printed TOC titles"
                      if printed and len(printed) == len(chapters)
                      else "display-type openers")
    if not chapters:
        printed = chapters_from_printed_toc(doc)
        if printed:
            chapters = printed
            method = "printed TOC (chained body search)"
    if not chapters or len(chapters) < 3:
        chapters = chapters_from_headings(doc)
        method = "chapter headings"

    if not chapters or len(chapters) < 3:
        print("  could not detect chapters (no bookmarks, no readable printed "
              "TOC, no 'Chapter N' headings) — needs manual split")
        return 1

    print(f"  method: {method} → {len(chapters)} chapters")
    for i, (title, start, end) in enumerate(chapters, 1):
        print(f"  {i:02d}. p{start:4d}-{end:<4d} {title[:70]}")

    if not args.write:
        print("\n(dry-run — pass --write to split into "
              f"{SPLIT_DIR.relative_to(ROOT) / stem}/)")
        return 0

    n = write_chapters(doc, stem, chapters, SPLIT_DIR / stem)
    print(f"\nwrote {n} chapter PDFs → {SPLIT_DIR / stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
