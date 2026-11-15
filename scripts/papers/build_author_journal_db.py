#!/usr/bin/env python3
"""Build author and journal databases with reliability tracking."""

import json
import re
from collections import defaultdict
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "papers"

# Journal reliability ratings
# Values: "reliable", "half_iffy", "iffy", "unknown"
JOURNAL_RELIABILITY = {
    # MDPI journals - known for questionable peer review
    "MDPI": "iffy",
    "Biology": "iffy",
    "Viruses": "iffy",
    "Pathogens": "iffy",
    "Animals": "iffy",
    "Veterinary Sciences": "iffy",
    "International Journal of Molecular Sciences": "iffy",

    # Frontiers - mixed reputation
    "Frontiers in Immunology": "half_iffy",
    "Frontiers in Microbiology": "half_iffy",
    "Frontiers in Veterinary Science": "half_iffy",
    "Frontiers in Cellular and Infection Microbiology": "half_iffy",

    # High-quality journals
    "Nature": "reliable",
    "Science": "reliable",
    "Cell": "reliable",
    "Nature Medicine": "reliable",
    "Nature Microbiology": "reliable",
    "Nature Reviews Microbiology": "reliable",
    "Nature Communications": "reliable",
    "Scientific Reports": "reliable",  # Nature family but less rigorous
    "Proceedings of the National Academy of Sciences": "reliable",
    "eLife": "reliable",
    "PLoS Pathogens": "reliable",
    "PLoS Biology": "reliable",

    # Good virology/infectious disease journals
    "Journal of Virology": "reliable",
    "mBio": "reliable",
    "Microbiology Spectrum": "reliable",  # ASM journal
    "Journal of Clinical Microbiology": "reliable",  # ASM journal
    "Emerging Infectious Diseases": "reliable",
    "Emerging Microbes & Infections": "reliable",
    "Virus Evolution": "reliable",
    "Virology": "reliable",
    "Journal of General Virology": "reliable",
    "Influenza and Other Respiratory Viruses": "reliable",  # Wiley/ISIRV

    # Veterinary/wildlife journals
    "Veterinary Research": "reliable",
    "Veterinary Record": "reliable",
    "Avian Pathology": "reliable",
    "Avian Diseases": "reliable",
    "Poultry Science": "reliable",
    "Transboundary and Emerging Diseases": "reliable",
    "Animal Frontiers": "reliable",

    # Ecology/wildlife
    "Ecology and Evolution": "reliable",  # Wiley
    "FACETS": "reliable",  # Canadian Science Publishing
    "GeoHealth": "reliable",  # AGU

    # Surveillance journals
    "Eurosurveillance": "reliable",

    # General science
    "Vaccine": "reliable",
    "Proceedings B Royal Society": "reliable",
    "Advanced Genetics (Wiley)": "reliable",
    "Journal of Biomolecular Structure and Dynamics": "reliable",

    # Institutional reports
    "EFSA Journal": "reliable",
    "Weekly Epidemiological Record": "reliable",
    "WOAH Scientific and Technical Review": "reliable",
    "USGS Report": "reliable",
    "CDFW Report": "reliable",

    # Preprints - not peer reviewed
    "bioRxiv (preprint)": "preprint",
    "bioRxiv": "preprint",
    "medRxiv": "preprint",
    "arXiv": "preprint",
}


def detect_mdpi(journal: str) -> bool:
    """Detect if a journal is from MDPI."""
    mdpi_journals = {
        "biology", "viruses", "pathogens", "animals", "cells",
        "microorganisms", "vaccines", "antibiotics", "ijms",
        "international journal of molecular sciences", "veterinary sciences"
    }
    return journal.lower() in mdpi_journals


def detect_frontiers(journal: str) -> bool:
    """Detect if a journal is from Frontiers."""
    return journal.lower().startswith("frontiers")


def get_reliability(journal: str) -> str:
    """Get reliability rating for a journal."""
    if not journal:
        return "unknown"

    # Check exact match first
    if journal in JOURNAL_RELIABILITY:
        return JOURNAL_RELIABILITY[journal]

    # Check publisher patterns
    if detect_mdpi(journal):
        return "iffy"
    if detect_frontiers(journal):
        return "half_iffy"

    # Check partial matches
    journal_lower = journal.lower()
    for known_journal, rating in JOURNAL_RELIABILITY.items():
        if known_journal.lower() in journal_lower:
            return rating

    return "unknown"


def parse_authors(author_string: str) -> list[dict]:
    """Parse author string into structured data."""
    if not author_string:
        return []

    authors = []

    # Handle "et al." and variations
    author_string = re.sub(r'\s*et\s*al\.?\s*', '', author_string, flags=re.IGNORECASE)

    # Split by common delimiters
    parts = re.split(r'[;,]|\s+and\s+', author_string)

    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue

        # Parse name (Last First or First Last)
        name_parts = part.split()
        if len(name_parts) >= 2:
            # Assume Last FirstInitial format (e.g., "Smith J" or "Smith JK")
            surname = name_parts[0].rstrip(',')
            initials = ' '.join(name_parts[1:])
            authors.append({
                "full_name": part,
                "surname": surname,
                "initials": initials,
            })
        elif len(name_parts) == 1:
            authors.append({
                "full_name": part,
                "surname": part,
                "initials": "",
            })

    return authors


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load papers
    with open(PAPERS_JSON) as f:
        data = json.load(f)

    papers = data.get("papers", [])
    print(f"Processing {len(papers)} papers\n")

    # Build journal database
    journal_stats = defaultdict(lambda: {
        "paper_count": 0,
        "paper_ids": [],
        "years": [],
    })

    # Build author database
    author_stats = defaultdict(lambda: {
        "paper_count": 0,
        "paper_ids": [],
        "journals": set(),
        "years": [],
        "full_names": set(),
    })

    for p in papers:
        pid = p.get("id", "")
        journal = p.get("journal", "") or ""
        authors_str = p.get("authors", "") or ""
        year = p.get("year")

        # Track journal
        if journal:
            journal_stats[journal]["paper_count"] += 1
            journal_stats[journal]["paper_ids"].append(pid)
            if year:
                journal_stats[journal]["years"].append(year)

        # Track authors — prefer the structured full roster (D72 / 2026-10-05
        # backfill) over the "et al."-truncated string
        structured = p.get("authors_list") or p.get("authors_full")
        if structured:
            authors = []
            for a in structured:
                fam = (a.get("family") or "").strip()
                giv = (a.get("given") or "").strip()
                if not fam:
                    continue
                initials = "".join(f"{w[0].upper()}." for w in giv.replace("-", " ").split() if w)
                authors.append({"surname": fam,
                                "full_name": f"{fam} {initials}".strip()})
        else:
            authors = parse_authors(authors_str)
        for author in authors:
            key = author["surname"].lower()
            author_stats[key]["paper_count"] += 1
            author_stats[key]["paper_ids"].append(pid)
            author_stats[key]["full_names"].add(author["full_name"])
            if journal:
                author_stats[key]["journals"].add(journal)
            if year:
                author_stats[key]["years"].append(year)

    # Create journal DataFrame
    journal_records = []
    for journal, stats in journal_stats.items():
        reliability = get_reliability(journal)
        journal_records.append({
            "journal": journal,
            "paper_count": stats["paper_count"],
            "paper_ids": ",".join(stats["paper_ids"]),
            "year_range": (lambda ys: f"{min(ys)}-{max(ys)}" if ys else "")([int(y) for y in stats["years"] if str(y).strip()[:4].isdigit()]),
            "reliability": reliability,
            "is_mdpi": detect_mdpi(journal),
            "is_frontiers": detect_frontiers(journal),
        })

    journal_df = pl.DataFrame(journal_records).sort("paper_count", descending=True)

    # Create author DataFrame
    author_records = []
    for surname, stats in author_stats.items():
        author_records.append({
            "surname": surname,
            "full_names": "|".join(sorted(stats["full_names"])),
            "paper_count": stats["paper_count"],
            "paper_ids": ",".join(stats["paper_ids"]),
            "journals": ",".join(sorted(stats["journals"])),
            "year_range": (lambda ys: f"{min(ys)}-{max(ys)}" if ys else "")([int(y) for y in stats["years"] if str(y).strip()[:4].isdigit()]),
        })

    author_df = pl.DataFrame(author_records).sort("paper_count", descending=True)

    # Save to parquet
    journal_path = OUTPUT_DIR / "journals.parquet"
    author_path = OUTPUT_DIR / "authors.parquet"

    journal_df.write_parquet(journal_path)
    author_df.write_parquet(author_path)

    print(f"Saved {len(journal_df)} journals to {journal_path}")
    print(f"Saved {len(author_df)} authors to {author_path}")

    # Print summaries
    print("\n=== Journal Reliability Summary ===")
    reliability_counts = journal_df.group_by("reliability").agg(
        pl.col("paper_count").sum().alias("papers"),
        pl.len().alias("journals")
    ).sort("papers", descending=True)
    print(reliability_counts)

    print("\n=== Iffy Journals ===")
    iffy = journal_df.filter(pl.col("reliability") == "iffy").select(["journal", "paper_count"])
    print(iffy)

    print("\n=== Half-Iffy Journals ===")
    half_iffy = journal_df.filter(pl.col("reliability") == "half_iffy").select(["journal", "paper_count"])
    print(half_iffy)

    print("\n=== Top Authors (5+ papers) ===")
    top_authors = author_df.filter(pl.col("paper_count") >= 5).select(["surname", "full_names", "paper_count"])
    print(top_authors)

    # Also save as JSON for web consumption (excluding internal reliability flags)
    journal_json = journal_df.select(["journal", "paper_count", "paper_ids", "year_range"]).to_dicts()
    author_json = author_df.select(["surname", "full_names", "paper_count", "paper_ids"]).to_dicts()

    with open(OUTPUT_DIR / "journals.json", "w") as f:
        json.dump({"journals": journal_json}, f, indent=2)

    with open(OUTPUT_DIR / "authors.json", "w") as f:
        json.dump({"authors": author_json}, f, indent=2)

    print(f"\nJSON files saved for web use (without reliability flags)")


if __name__ == "__main__":
    main()
