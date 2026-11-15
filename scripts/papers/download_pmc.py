#!/usr/bin/env python3
"""Download PMC PDFs using httpx with browser-like headers."""

import json
import re
import time
from pathlib import Path

import httpx

OUTPUT_DIR = Path("docs/papers_pdfs")
PAPERS_JSON = Path("web/public/data/papers.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


def fetch_pmc_pdf(pmc_id: str, output_path: Path) -> bool:
    """Fetch PDF from PMC."""
    with httpx.Client(follow_redirects=True, timeout=60, headers=HEADERS) as client:
        # First, fetch the PMC page to find the PDF link
        page_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/"

        try:
            response = client.get(page_url)
            html = response.text

            # Look for PDF link patterns
            # Pattern 1: href="pdf/filename.pdf"
            match = re.search(r'href="(pdf/[^"]+\.pdf)"', html)
            if match:
                pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/{match.group(1)}"
            else:
                # Pattern 2: Look for CDC EID link
                match = re.search(r'href="(https://wwwnc\.cdc\.gov/eid/[^"]+)"', html)
                if match:
                    eid_url = match.group(1)
                    # Convert to PDF URL
                    match2 = re.search(r'/eid/article/(\d+)/(\d+)/(\d+-\d+)', eid_url)
                    if match2:
                        vol, num, art_id = match2.groups()
                        pdf_url = f"https://wwwnc.cdc.gov/eid/article/{vol}/{num}/pdfs/{art_id}.pdf"
                    else:
                        return False
                else:
                    # Pattern 3: direct PDF link in cdn
                    match = re.search(r'href="(https://cdn\.ncbi[^"]+\.pdf)"', html)
                    if match:
                        pdf_url = match.group(1)
                    else:
                        return False

            print(f"    Found: {pdf_url[:60]}...")

            # Download the PDF
            pdf_headers = HEADERS.copy()
            pdf_headers["Accept"] = "application/pdf,*/*"

            response = client.get(pdf_url, headers=pdf_headers)

            if response.status_code == 200 and response.content[:4] == b"%PDF":
                output_path.write_bytes(response.content)
                return True

        except Exception as e:
            print(f"    Error: {e}")

    return False


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(PAPERS_JSON) as f:
        data = json.load(f)

    # Find PMC papers without PDFs
    pmc_papers = []
    for p in data.get("papers", []):
        if p.get("pdf"):
            continue
        url = p.get("url") or ""
        if "pmc" in url.lower():
            match = re.search(r"PMC(\d+)", url)
            if match:
                pmc_papers.append({
                    "id": p["id"],
                    "pmc_id": match.group(1),
                    "title": p.get("title", "")[:45],
                })

    print(f"Found {len(pmc_papers)} PMC papers to download\n")

    success = 0
    failed = []

    for i, paper in enumerate(pmc_papers, 1):
        paper_id = paper["id"]
        pmc_id = paper["pmc_id"]
        output_path = OUTPUT_DIR / f"{paper_id}.pdf"

        print(f"[{i}/{len(pmc_papers)}] {paper_id} (PMC{pmc_id})")
        print(f"    {paper['title']}...")

        if fetch_pmc_pdf(pmc_id, output_path):
            size_kb = output_path.stat().st_size / 1024
            print(f"    -> {size_kb:.0f} KB")
            success += 1
        else:
            print("    -> Failed")
            failed.append(paper_id)
            if output_path.exists():
                output_path.unlink()

        time.sleep(2)  # Rate limiting

    print(f"\nDone: {success}/{len(pmc_papers)} downloaded")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed[:10])}...")


if __name__ == "__main__":
    main()
