#!/usr/bin/env python3
"""Download PDFs for papers that failed or need re-downloading."""

import httpx
import time
from pathlib import Path

OUTPUT_DIR = Path("docs/papers_pdfs")

# Papers to download with their PDF URLs
PAPERS = {
    "griffon_vulture_2025.pdf": {
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12309751/pdf/",
        "alt_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12309751/pdf/main.pdf",
    },
    "h5n6_korea_2024.pdf": {
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11139000/pdf/",
        "alt_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11139000/pdf/main.pdf",
    },
    "white_tailed_eagles_2024.pdf": {
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11529892/pdf/",
        "alt_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11529892/pdf/main.pdf",
    },
    "seabird_recovery_canada_2024.pdf": {
        "url": "https://www.biorxiv.org/content/10.1101/2024.05.03.591923v1.full.pdf",
        "alt_url": "https://www.biorxiv.org/content/10.1101/2024.05.03.591923.full.pdf",
    },
    "synanthropic_birds_2023.pdf": {
        "url": "https://www.biorxiv.org/content/10.1101/2023.11.08.565892v1.full.pdf",
        "alt_url": "https://www.biorxiv.org/content/10.1101/2023.11.08.565892.full.pdf",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
}


def download_pdf(filename: str, urls: dict) -> bool:
    """Try to download PDF from primary URL, fall back to alt."""
    output_path = OUTPUT_DIR / filename

    for url_key in ["url", "alt_url"]:
        url = urls.get(url_key)
        if not url:
            continue

        print(f"  Trying: {url[:60]}...")
        try:
            with httpx.Client(follow_redirects=True, timeout=60) as client:
                response = client.get(url, headers=HEADERS)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type or response.content[:4] == b"%PDF":
                        output_path.write_bytes(response.content)
                        size_kb = len(response.content) / 1024
                        print(f"  -> Downloaded {size_kb:.1f} KB")
                        return True
                    else:
                        print(f"  -> Not a PDF (got {content_type[:30]})")
                else:
                    print(f"  -> HTTP {response.status_code}")

        except Exception as e:
            print(f"  -> Error: {e}")

        time.sleep(1)

    return False


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Downloading {len(PAPERS)} PDFs to {OUTPUT_DIR}/\n")

    success = 0
    failed = []

    for filename, urls in PAPERS.items():
        print(f"[{filename}]")
        if download_pdf(filename, urls):
            success += 1
        else:
            failed.append(filename)
        time.sleep(2)  # Rate limiting

    print(f"\nDone: {success}/{len(PAPERS)} downloaded")
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
