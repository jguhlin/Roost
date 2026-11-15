#!/usr/bin/env python3
"""Download all available open access PDFs."""

import json
import re
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

OUTPUT_DIR = Path("docs/papers_pdfs")
PAPERS_JSON = Path("web/public/data/papers.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
}


def get_pdf_url(paper: dict) -> str | None:
    """Determine the PDF URL based on paper source."""
    url = paper.get("url") or ""
    paper_id = paper.get("id", "")

    # bioRxiv
    if "biorxiv.org" in url:
        # https://www.biorxiv.org/content/10.1101/2023.05.01.538918
        # -> https://www.biorxiv.org/content/10.1101/2023.05.01.538918.full.pdf
        return url.rstrip("/") + ".full.pdf"

    # arXiv
    if "arxiv.org" in url:
        # https://arxiv.org/pdf/2504.11910 or https://arxiv.org/abs/2504.11910
        if "/pdf/" in url:
            return url if url.endswith(".pdf") else url + ".pdf"
        match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)", url)
        if match:
            return f"https://arxiv.org/pdf/{match.group(1)}.pdf"

    # PMC - need to fetch page to get actual PDF link
    if "pmc.ncbi.nlm.nih.gov" in url or "ncbi.nlm.nih.gov/pmc" in url:
        match = re.search(r"PMC(\d+)", url)
        if match:
            return f"PMC:{match.group(1)}"  # Special marker for PMC

    # Frontiers
    if "frontiersin.org" in url:
        # Need to construct PDF URL from article URL
        if "/full" in url:
            return url.replace("/full", "/pdf")

    # PLOS
    if "plos" in url and "journal.pone" in url:
        # https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0299330
        match = re.search(r"id=(10\.\d+/journal\.pone\.\d+)", url)
        if match:
            doi = match.group(1)
            return f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable"

    # Virology Journal (BMC)
    if "biomedcentral.com" in url:
        # https://virologyj.biomedcentral.com/articles/10.1186/1743-422X-7-365
        # -> https://virologyj.biomedcentral.com/counter/pdf/10.1186/1743-422X-7-365.pdf
        match = re.search(r"articles/(10\.\d+/[^/]+)", url)
        if match:
            return f"https://link.springer.com/content/pdf/{match.group(1)}.pdf"

    return None


def fetch_pmc_pdf_url(pmc_id: str) -> str | None:
    """Fetch actual PDF URL from PMC page."""
    # Try CDC EID format first (most reliable)
    # Then try direct PMC PDF paths
    patterns = [
        f"https://wwwnc.cdc.gov/eid/article/{{vol}}/{{num}}/pdfs/{{id}}.pdf",  # CDC EID
        f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/main.pdf",
    ]

    # Fetch PMC page to find PDF link
    try:
        url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/"
        req = Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
        with urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Look for PDF link in HTML
        # Pattern: href="pdf/24-0192.pdf" or similar
        match = re.search(r'href="(pdf/[^"]+\.pdf)"', html)
        if match:
            pdf_path = match.group(1)
            return f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/{pdf_path}"

        # Try CDC EID pattern - look for article ID
        match = re.search(r"/eid/article/(\d+)/(\d+)/(\d+-\d+)", html)
        if match:
            vol, num, art_id = match.groups()
            return f"https://wwwnc.cdc.gov/eid/article/{vol}/{num}/pdfs/{art_id}.pdf"

    except Exception as e:
        print(f"    Error fetching PMC page: {e}")

    return None


def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=60) as response:
            content = response.read()

            # Verify it's a PDF
            if content[:4] != b"%PDF":
                return False

            output_path.write_bytes(content)
            return True

    except (URLError, HTTPError) as e:
        print(f"    Error: {e}")
        return False


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(PAPERS_JSON) as f:
        data = json.load(f)

    papers = data.get("papers", [])

    # Find open access papers without PDFs
    to_download = []
    for p in papers:
        if p.get("pdf"):
            continue  # Already has PDF

        url = p.get("url") or ""
        status = p.get("pdf_status") or ""

        # Check if likely open access
        if any(
            x in url.lower()
            for x in ["biorxiv", "arxiv", "pmc", "frontiers", "mdpi", "plos", "biomedcentral"]
        ) or any(x in status.lower() for x in ["pmc", "open"]):
            pdf_url = get_pdf_url(p)
            if pdf_url:
                to_download.append(
                    {
                        "id": p.get("id"),
                        "title": p.get("title", "")[:50],
                        "pdf_url": pdf_url,
                    }
                )

    print(f"Found {len(to_download)} papers to download\n")

    success = 0
    failed = []

    for i, paper in enumerate(to_download, 1):
        paper_id = paper["id"]
        pdf_url = paper["pdf_url"]
        output_path = OUTPUT_DIR / f"{paper_id}.pdf"

        print(f"[{i}/{len(to_download)}] {paper_id}")
        print(f"    {paper['title']}...")

        # Handle PMC specially
        if pdf_url.startswith("PMC:"):
            pmc_id = pdf_url[4:]
            print(f"    Fetching PMC{pmc_id} PDF link...")
            pdf_url = fetch_pmc_pdf_url(pmc_id)
            if not pdf_url:
                print("    Could not find PDF link")
                failed.append(paper_id)
                continue

        print(f"    {pdf_url[:60]}...")

        if download_pdf(pdf_url, output_path):
            size_kb = output_path.stat().st_size / 1024
            print(f"    -> {size_kb:.0f} KB")
            success += 1
        else:
            print("    -> Failed (not a PDF)")
            failed.append(paper_id)
            if output_path.exists():
                output_path.unlink()

        time.sleep(1.5)  # Rate limiting

    print(f"\nDone: {success}/{len(to_download)} downloaded")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed[:10])}...")


if __name__ == "__main__":
    main()
