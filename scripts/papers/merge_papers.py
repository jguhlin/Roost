#!/usr/bin/env python3
"""
Merge new papers into the main papers.json database.
Reviews new_papers.json and adds approved papers.

Usage:
    python scripts/papers/merge_papers.py [--review] [--all] [--ids paper1,paper2]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Import species linking from add_species_links.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from add_species_links import extract_species_links

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
NEW_PAPERS_JSON = PROJECT_ROOT / "scripts" / "papers" / "new_papers.json"
ARCHIVE_DIR = PROJECT_ROOT / "scripts" / "papers" / "archive"


def generate_paper_id(paper: dict) -> str:
    """Generate a unique ID for a paper."""
    # Use first author's last name + year + topic
    authors = paper.get("authors", "unknown")
    first_author = authors.split(",")[0].split()[0].lower() if authors else "unknown"
    first_author = re.sub(r'[^a-z]', '', first_author)

    year = paper.get("year", 2024)

    # Add a topic hint
    title = paper.get("title", "").lower()
    topic_hint = ""
    if "cattle" in title or "dairy" in title:
        topic_hint = "_cattle"
    elif "seal" in title:
        topic_hint = "_seal"
    elif "gannet" in title:
        topic_hint = "_gannet"
    elif "duck" in title:
        topic_hint = "_duck"
    elif "anp32" in title:
        topic_hint = "_anp32"
    elif "wild bird" in title:
        topic_hint = "_wildbird"

    return f"{first_author}{year}{topic_hint}"


def load_papers_json() -> dict:
    """Load existing papers database."""
    if not PAPERS_JSON.exists():
        return {
            "papers": [],
            "categories": [],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "total_papers": 0
        }

    with open(PAPERS_JSON) as f:
        return json.load(f)


def load_new_papers() -> list:
    """Load new papers from search results."""
    if not NEW_PAPERS_JSON.exists():
        return []

    with open(NEW_PAPERS_JSON) as f:
        data = json.load(f)

    return data.get("new_papers", [])


def format_paper_for_db(paper: dict) -> dict:
    """Format a paper for insertion into papers.json."""
    # Generate ID if not present
    paper_id = paper.get("id") or generate_paper_id(paper)

    # Ensure unique ID
    base_id = paper_id
    counter = 1
    existing_ids = set()  # Will be populated by caller

    formatted = {
        "id": paper_id,
        "title": paper.get("title") or "",
        "authors": paper.get("authors") or "",
        "journal": paper.get("journal") or "",
        "year": paper.get("year") or 2024,
        "doi": paper.get("doi"),
        "url": paper.get("url") or "",
        # D109: fold LLM topic variants ('Cross-Species Transmission' -> 'Cross-Species')
        "topics": sorted({("Cross-Species" if t == "Cross-Species Transmission" else t)
                          for t in (paper.get("topics") or [])}),
        "category": paper.get("category") or "Wild Birds",
        "summary": paper.get("summary") or "",
        "cited_for": paper.get("cited_for") or "",
    }

    # Add PDF status if present
    if paper.get("pdf_status"):
        formatted["pdf_status"] = paper["pdf_status"]
    elif paper.get("source") == "pmc":
        formatted["pdf_status"] = "available_pmc"
    elif paper.get("source") == "biorxiv":
        formatted["pdf_status"] = "available_open"

    return formatted


def review_papers(papers: list) -> list:
    """Interactive review of papers for inclusion."""
    approved = []

    print(f"\n{'='*60}")
    print(f"Reviewing {len(papers)} new papers")
    print(f"{'='*60}\n")

    for i, paper in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] {paper.get('title', 'No title')[:70]}...")
        print(f"  Authors: {paper.get('authors', 'Unknown')}")
        print(f"  Journal: {paper.get('journal', 'Unknown')} ({paper.get('year', '?')})")
        print(f"  Category: {paper.get('category', 'Unknown')}")
        print(f"  Topics: {', '.join(paper.get('topics', []))}")
        if paper.get("doi"):
            print(f"  DOI: {paper.get('doi')}")
        if paper.get("url"):
            print(f"  URL: {paper.get('url')}")

        while True:
            response = input("\n  [a]pprove, [s]kip, [e]dit category, [q]uit? ").strip().lower()

            if response == 'a':
                # Prompt for summary if empty
                if not paper.get("summary"):
                    summary = input("  Summary (optional): ").strip()
                    if summary:
                        paper["summary"] = summary

                if not paper.get("cited_for"):
                    cited_for = input("  Cited for (optional): ").strip()
                    if cited_for:
                        paper["cited_for"] = cited_for

                approved.append(paper)
                print("  ✓ Approved")
                break

            elif response == 's':
                print("  ✗ Skipped")
                break

            elif response == 'e':
                categories = [
                    "Wild Birds", "Seabirds", "Host Genomics", "Evolution",
                    "Surveillance", "Cross-Species Transmission", "Control",
                    "Human Infections", "Pandemic Risk", "Host Adaptation", "Reviews"
                ]
                print("  Categories:")
                for j, cat in enumerate(categories, 1):
                    print(f"    {j}. {cat}")
                try:
                    cat_idx = int(input("  Select category number: ")) - 1
                    if 0 <= cat_idx < len(categories):
                        paper["category"] = categories[cat_idx]
                        print(f"  Category set to: {paper['category']}")
                except (ValueError, IndexError):
                    print("  Invalid selection")

            elif response == 'q':
                return approved

            else:
                print("  Invalid response. Use a/s/e/q")

    return approved


def merge_papers(new_papers: list, existing_data: dict) -> dict:
    """Merge new papers into existing database."""
    existing_papers = existing_data.get("papers", [])
    existing_ids = {p.get("id") for p in existing_papers}

    added = 0
    for paper in new_papers:
        formatted = format_paper_for_db(paper)

        # Ensure unique ID
        base_id = formatted["id"]
        counter = 1
        while formatted["id"] in existing_ids:
            formatted["id"] = f"{base_id}_{counter}"
            counter += 1

        # Add species links
        formatted["species_links"] = extract_species_links(formatted)

        existing_papers.append(formatted)
        existing_ids.add(formatted["id"])
        added += 1

    # Update categories list
    categories = set(existing_data.get("categories", []))
    for paper in existing_papers:
        if paper.get("category"):
            categories.add(paper["category"])

    existing_data["papers"] = existing_papers
    existing_data["categories"] = sorted(list(categories))
    existing_data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    existing_data["total_papers"] = len(existing_papers)

    return existing_data, added


def archive_new_papers():
    """Archive the new_papers.json file."""
    if not NEW_PAPERS_JSON.exists():
        return

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = ARCHIVE_DIR / f"new_papers_{timestamp}.json"

    NEW_PAPERS_JSON.rename(archive_path)
    print(f"Archived to: {archive_path}")


def main():
    parser = argparse.ArgumentParser(description="Merge new papers into database")
    parser.add_argument(
        "--review",
        action="store_true",
        help="Interactive review mode"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Add all new papers without review"
    )
    parser.add_argument(
        "--ids",
        type=str,
        help="Comma-separated list of paper indices to add (0-indexed)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without making changes"
    )
    args = parser.parse_args()

    # Load data
    new_papers = load_new_papers()
    if not new_papers:
        print("No new papers to merge. Run search_papers.py first.")
        return

    existing_data = load_papers_json()
    print(f"Existing papers: {len(existing_data.get('papers', []))}")
    print(f"New papers available: {len(new_papers)}")

    # Determine which papers to add
    papers_to_add = []

    if args.review:
        papers_to_add = review_papers(new_papers)
    elif args.all:
        papers_to_add = new_papers
    elif args.ids:
        indices = [int(i.strip()) for i in args.ids.split(",")]
        papers_to_add = [new_papers[i] for i in indices if 0 <= i < len(new_papers)]
    else:
        # Default: show list and ask for selection
        print("\nNew papers found:")
        for i, paper in enumerate(new_papers):
            print(f"  [{i}] {paper.get('title', 'No title')[:60]}...")
            print(f"      {paper.get('journal', '')} ({paper.get('year', '?')}) - {paper.get('category', 'Unknown')}")

        print("\nOptions:")
        print("  --review     Interactive review of each paper")
        print("  --all        Add all papers")
        print("  --ids 0,2,5  Add specific papers by index")
        return

    if not papers_to_add:
        print("No papers selected for merging.")
        return

    print(f"\nPapers to add: {len(papers_to_add)}")

    if args.dry_run:
        print("\n[DRY RUN] Would add these papers:")
        for paper in papers_to_add:
            print(f"  - {paper.get('title', 'No title')[:60]}...")
        return

    # Merge papers
    updated_data, added = merge_papers(papers_to_add, existing_data)

    # Save updated database
    with open(PAPERS_JSON, "w") as f:
        json.dump(updated_data, f, indent=2)

    print(f"\n✓ Added {added} papers to database")
    print(f"  Total papers now: {updated_data['total_papers']}")

    # Archive processed papers
    archive_new_papers()


if __name__ == "__main__":
    main()
