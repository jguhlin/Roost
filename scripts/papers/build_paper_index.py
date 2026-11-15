#!/usr/bin/env python3
"""Build paper tracking index with download status and metadata."""

import json
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
PDF_DIR = PROJECT_ROOT / "docs" / "papers_pdfs"
MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
OUTPUT_DIR = PROJECT_ROOT / "data" / "papers"


def _display_string(p, max_show=3):
    """Author display string from the full structured list when available
    (D72 + 2026-10-05 backfill), falling back to the legacy string."""
    structured = p.get("authors_list") or p.get("authors_full")
    if not structured:
        return p.get("authors", "")
    parts = []
    for a in structured[:max_show]:
        fam = (a.get("family") or "").strip()
        giv = (a.get("given") or "").strip()
        initials = "".join(f"{w[0].upper()}." for w in giv.replace("-", " ").split() if w)
        parts.append(f"{fam} {initials}".strip())
    if len(structured) > max_show:
        parts.append("et al.")
    return ", ".join(parts)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load papers database
    with open(PAPERS_JSON) as f:
        data = json.load(f)

    papers = data.get("papers", [])
    print(f"Total papers in database: {len(papers)}")

    # Get downloaded files
    pdf_files = {p.stem for p in PDF_DIR.glob("*.pdf")}
    md_files = {p.stem for p in MD_DIR.glob("*.md")}

    print(f"PDFs downloaded: {len(pdf_files)}")
    print(f"Markdown files: {len(md_files)}")

    # Build records
    records = []
    for p in papers:
        pid = p.get("id", "")

        # Check if PDF exists (handle naming variations)
        has_pdf = pid in pdf_files or pid.replace("_", "") in pdf_files
        has_md = pid in md_files or pid.replace("_", "") in md_files

        # Determine source type
        url = p.get("url") or ""
        if "biorxiv" in url:
            source_type = "biorxiv"
        elif "arxiv" in url:
            source_type = "arxiv"
        elif "pmc" in url.lower():
            source_type = "pmc"
        elif "cdc.gov/eid" in url:
            source_type = "cdc_eid"
        elif "frontiers" in url:
            source_type = "frontiers"
        elif "nature.com" in url:
            source_type = "nature"
        elif "mdpi" in url:
            source_type = "mdpi"
        elif "plos" in url:
            source_type = "plos"
        elif "wiley" in url:
            source_type = "wiley"
        else:
            source_type = "other"

        # Determine access status
        pdf_status = p.get("pdf_status") or ""
        if has_pdf:
            access_status = "downloaded"
        elif "open" in pdf_status or "pmc" in pdf_status:
            access_status = "open_access"
        elif "subscription" in pdf_status:
            access_status = "paywalled"
        else:
            access_status = "unknown"

        records.append({
            "id": pid,
            "title": p.get("title", ""),
            "authors": _display_string(p),
            "journal": p.get("journal", ""),
            "year": p.get("year"),
            "doi": p.get("doi"),
            "url": url,
            "category": p.get("category", ""),
            "topics": ",".join(p.get("topics", [])),
            "summary": p.get("summary", ""),
            "cited_for": p.get("cited_for", ""),
            "source_type": source_type,
            "has_pdf": has_pdf,
            "has_markdown": has_md,
            "access_status": access_status,
            "species_avian": ",".join(p.get("species_links", {}).get("avian", [])),
            "species_mammal": ",".join(p.get("species_links", {}).get("mammal", [])),
        })

    # Create DataFrame
    df = pl.DataFrame(records)

    # Save to parquet
    parquet_path = OUTPUT_DIR / "papers_index.parquet"
    df.write_parquet(parquet_path)
    print(f"\nSaved to: {parquet_path}")

    # Print summary stats
    print("\n=== Paper Index Summary ===")
    print(f"Total papers: {len(df)}")
    print(f"With PDF: {df['has_pdf'].sum()}")
    print(f"With Markdown: {df['has_markdown'].sum()}")

    print("\nBy category:")
    print(df.group_by("category").len().sort("len", descending=True))

    print("\nBy source type:")
    print(df.group_by("source_type").len().sort("len", descending=True))

    print("\nBy access status:")
    print(df.group_by("access_status").len().sort("len", descending=True))

    # Save papers needing download
    needs_download = df.filter(
        (pl.col("has_pdf") == False) &
        (pl.col("access_status").is_in(["open_access", "unknown"]))
    ).select(["id", "title", "source_type", "url"])

    needs_path = OUTPUT_DIR / "papers_need_download.parquet"
    needs_download.write_parquet(needs_path)
    print(f"\nPapers needing download: {len(needs_download)}")
    print(f"Saved to: {needs_path}")


if __name__ == "__main__":
    main()
