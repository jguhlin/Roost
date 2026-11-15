#!/usr/bin/env python3
"""Match PDFs in pdfs_to_process to paper IDs, rename, move, and convert to markdown."""

import json
import re
import shutil
from pathlib import Path

import pymupdf4llm

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "pdfs_to_process"
OUTPUT_PDF_DIR = PROJECT_ROOT / "docs" / "papers_pdfs"
OUTPUT_MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"


def normalize(s: str) -> str:
    """Normalize string for matching."""
    return re.sub(r'[^a-z0-9]', '', s.lower())


def build_paper_patterns():
    """Build matching patterns from papers database."""
    with open(PAPERS_JSON) as f:
        data = json.load(f)

    patterns = []
    for p in data.get("papers", []):
        pid = p.get("id", "")
        title = p.get("title", "")
        doi = p.get("doi", "") or ""
        authors = p.get("authors", "") or ""
        journal = p.get("journal", "") or ""
        year = str(p.get("year", ""))

        # Extract key terms for matching
        terms = [
            pid,
            normalize(title)[:50],  # First 50 chars of normalized title
            doi.split("/")[-1] if "/" in doi else doi,  # DOI suffix
            year,
        ]

        # Extract first author surname
        if authors:
            first_author = authors.split(",")[0].split(" ")[0].lower()
            terms.append(first_author)

        patterns.append({
            "id": pid,
            "title": title,
            "doi": doi,
            "terms": [t for t in terms if t],
            "year": year,
        })

    return patterns


def match_pdf_to_paper(pdf_path: Path, patterns: list) -> dict | None:
    """Try to match a PDF filename to a paper."""
    filename = pdf_path.stem.lower()
    filename_norm = normalize(filename)

    best_match = None
    best_score = 0

    for p in patterns:
        score = 0

        # Check for paper ID in filename
        if p["id"].lower() in filename:
            score += 100

        # Check for DOI suffix
        if p["doi"]:
            doi_suffix = p["doi"].split("/")[-1].lower()
            if doi_suffix in filename:
                score += 80

        # Check for year
        if p["year"] and p["year"] in filename:
            score += 10

        # Check for title keywords
        title_words = normalize(p["title"]).split()
        for word in title_words[:5]:  # First 5 significant words
            if len(word) > 4 and word in filename_norm:
                score += 5

        # Check for author name patterns
        for term in p["terms"]:
            if len(term) > 3 and term in filename_norm:
                score += 3

        if score > best_score:
            best_score = score
            best_match = p

    # Require minimum confidence
    if best_score >= 10:
        return best_match
    return None


def main():
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_DIR.exists():
        print(f"Input directory not found: {INPUT_DIR}")
        return

    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs to process\n")

    patterns = build_paper_patterns()
    print(f"Loaded {len(patterns)} papers from database\n")

    matched = []
    unmatched = []

    for pdf_path in pdfs:
        match = match_pdf_to_paper(pdf_path, patterns)
        if match:
            matched.append((pdf_path, match))
        else:
            unmatched.append(pdf_path)

    print(f"Matched: {len(matched)}")
    print(f"Unmatched: {len(unmatched)}\n")

    # Process matched PDFs
    print("=== Processing Matched PDFs ===\n")
    for pdf_path, paper in matched:
        paper_id = paper["id"]
        dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
        dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"

        # Check if already exists
        if dest_pdf.exists():
            print(f"SKIP (exists): {paper_id}")
            continue

        print(f"{pdf_path.name}")
        print(f"  → {paper_id}: {paper['title'][:60]}...")

        # Move PDF
        shutil.copy2(pdf_path, dest_pdf)

        # Convert to markdown
        try:
            md_text = pymupdf4llm.to_markdown(str(dest_pdf))
            dest_md.write_text(md_text)
            print(f"  ✓ PDF + MD saved ({len(md_text):,} chars)")
        except Exception as e:
            print(f"  ✗ MD conversion failed: {e}")

        print()

    # List unmatched for manual review
    if unmatched:
        print("\n=== Unmatched PDFs (need manual matching) ===\n")
        for pdf_path in unmatched:
            print(f"  {pdf_path.name}")

    print("\nDone!")


if __name__ == "__main__":
    main()
