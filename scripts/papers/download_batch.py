#!/usr/bin/env python3
"""Download PDFs from various open access sources."""

import json
import re
import subprocess
import time
from pathlib import Path

OUTPUT_DIR = Path("docs/papers_pdfs")
PAPERS_JSON = Path("web/public/data/papers.json")


def curl_download(url: str, output_path: Path) -> bool:
    """Download using curl."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "-A", "Mozilla/5.0", "-o", str(output_path), url],
            timeout=60,
            capture_output=True,
        )
        if output_path.exists():
            content = output_path.read_bytes()[:10]
            if b"%PDF" in content:
                return True
            output_path.unlink()
    except Exception:
        pass
    return False


def get_pdf_urls(paper: dict) -> list[str]:
    """Get potential PDF URLs for a paper."""
    urls = []
    url = paper.get("url") or ""
    doi = paper.get("doi") or ""
    journal = (paper.get("journal") or "").lower()

    # Nature / Scientific Reports
    if "nature.com" in url:
        # https://www.nature.com/articles/s41598-026-55259-5
        # -> https://www.nature.com/articles/s41598-026-55259-5.pdf
        urls.append(url.rstrip("/") + ".pdf")

    # eLife
    if "elife" in url.lower() or "elife" in doi.lower():
        # https://doi.org/10.7554/eLife.45066
        # -> https://elifesciences.org/articles/45066/elife-45066-v2.pdf
        match = re.search(r"eLife\.(\d+)", doi, re.I)
        if match:
            art_id = match.group(1)
            urls.append(f"https://elifesciences.org/download/aHR0cHM6Ly9jZG4uZWxpZmVzY2llbmNlcy5vcmcvYXJ0aWNsZXMve2FydF9pZH0vZWxpZmUte2FydF9pZH0tdjIucGRm/elife-{art_id}-v2.pdf")
            urls.append(f"https://elifesciences.org/articles/{art_id}/elife-{art_id}-v2.pdf")

    # PLoS
    if "plos" in url.lower():
        # https://doi.org/10.1371/journal.ppat.1007426
        match = re.search(r"10\.1371/(journal\.[^/]+)", doi or url)
        if match:
            doi_path = match.group(1)
            urls.append(f"https://journals.plos.org/{doi_path.split('.')[1]}/article/file?id=10.1371/{doi_path}&type=printable")

    # EFSA Journal
    if "efsa" in journal:
        # PMC articles for EFSA
        match = re.search(r"PMC(\d+)", url)
        if match:
            pmc_id = match.group(1)
            urls.append(f"https://efsa.onlinelibrary.wiley.com/doi/pdfdirect/10.2903/j.efsa.2025.9254")

    # mBio / ASM journals
    if "mbio" in url.lower() or "asm.org" in url.lower():
        if doi:
            # https://doi.org/10.1128/mbio.02542-24
            urls.append(f"https://journals.asm.org/doi/pdf/{doi}")

    # CDC EID
    if "cdc.gov/eid" in url:
        match = re.search(r"/eid/article/(\d+)/(\d+)/(\d+-\d+)", url)
        if match:
            vol, num, art_id = match.groups()
            urls.append(f"https://wwwnc.cdc.gov/eid/article/{vol}/{num}/pdfs/{art_id}.pdf")

    # Frontiers
    if "frontiersin.org" in url:
        urls.append(url.replace("/full", "/pdf"))

    # MDPI (Viruses, etc.)
    if "mdpi.com" in url:
        urls.append(url.replace("/htm", "/pdf"))
        match = re.search(r"/(\d+)/(\d+)/(\d+)", url)
        if match:
            urls.append(f"https://www.mdpi.com/{match.group(1)}/{match.group(2)}/{match.group(3)}/pdf")

    # Wiley
    if "wiley.com" in url:
        if doi:
            urls.append(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi}")

    # Nature Communications / Springer
    if "s41467" in url or "nature.com/articles/s41467" in url:
        urls.append(url.rstrip("/") + ".pdf")

    # Immunology journals
    if "jimmunol" in url.lower() or "jimmunol" in (doi or "").lower():
        if doi:
            urls.append(f"https://journals.aai.org/jimmunol/article-pdf/doi/{doi}")

    return urls


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(PAPERS_JSON) as f:
        data = json.load(f)

    downloaded = {p.stem for p in OUTPUT_DIR.glob("*.pdf")}

    # Find papers without PDFs that have potential sources
    to_download = []
    for p in data.get("papers", []):
        pid = p.get("id", "")
        if pid in downloaded:
            continue

        urls = get_pdf_urls(p)
        if urls:
            to_download.append({
                "id": pid,
                "title": p.get("title", "")[:45],
                "urls": urls,
            })

    print(f"Attempting {len(to_download)} papers with known URL patterns\n")

    success = 0
    failed = []

    for i, paper in enumerate(to_download, 1):
        paper_id = paper["id"]
        output_path = OUTPUT_DIR / f"{paper_id}.pdf"

        print(f"[{i}/{len(to_download)}] {paper_id}")
        print(f"    {paper['title']}...")

        downloaded_ok = False
        for url in paper["urls"]:
            print(f"    Trying: {url[:55]}...")
            if curl_download(url, output_path):
                size_kb = output_path.stat().st_size / 1024
                print(f"    -> {size_kb:.0f} KB")
                success += 1
                downloaded_ok = True
                break

        if not downloaded_ok:
            print("    -> Failed")
            failed.append(paper_id)

        time.sleep(1)

    print(f"\nDone: {success}/{len(to_download)} downloaded")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed[:10])}...")


if __name__ == "__main__":
    main()
