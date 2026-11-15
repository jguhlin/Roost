#!/usr/bin/env python3
"""Manual mapping of PDF filenames to paper IDs."""

import shutil
from pathlib import Path
import pymupdf4llm

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "pdfs_to_process"
OUTPUT_PDF_DIR = PROJECT_ROOT / "docs" / "papers_pdfs"
OUTPUT_MD_DIR = PROJECT_ROOT / "docs" / "papers_md"

# Manual mappings: filename (without .pdf) -> paper_id
MANUAL_MAPPINGS = {
    # ScienceDirect papers
    "1-s2.0-S1995820X25000021-main": "h5n6_china2025",
    "1-s2.0-S2352771424000405-main": "vaccine_efficacy_meta2024",

    # By DOI/journal patterns
    "biology-11-00219-v2": "duck_chicken_comparison2022",
    "jgv002109": "mammal_adaptations_review2025",
    "viruses-16-01898": "environment_water2024",
    "srep26787": "host_genetics_transmission2016",
    "cir1558": "usgs_strategy2025",

    # By title
    "Phylodynamics of high pathogenicity avian influenza virus in Bangladesh identifying domestic ducks as the amplifying host reservoir": "bangladesh_duck_reservoir2024",
    "Responding to high pathogenicity avian influenza HPAI and the conservation crisis in wild birds where next ": "conservation_response2025",
    "Increasing spillover of highly pathogenic avian influenza A (H5N1) virus to mammals": "mammal_spillover2024",

    # CDFW California report
    "CDFW WHL_AIV H5 surveillance 2024-25_final": "california_wildbird_2025",

    # CDC EID papers
    "24-0192": None,  # Need to identify
    "24-1456": None,  # Need to identify

    # EFSA
    "EFS2-23-e9834": None,  # Old EFSA report - skip if not in DB

    # Frontiers papers
    "fcimb-16-1755375": None,  # Need to identify
    "fimmu-11-00377": "innate_immune_review2019",  # Likely
    "fimmu-12-786205": None,  # Need to identify
    "fimmu-09-02025": None,  # Need to identify from earlier run

    # Journal of General Virology
    "jgv-105-02035": None,  # Need to identify
    "jgv001852": None,  # Need to identify

    # Journal of Virology
    "jvi.01857-23": None,  # Need to identify

    # MDPI papers (mark these as iffy source)
    "animals-14-03211": None,  # MDPI Animals
    "animals-15-02057": None,  # MDPI Animals
    "pathogens-13-00083": None,  # MDPI Pathogens
    "vetsci-06-00005": None,  # MDPI Vet Sci
    "viruses-15-01403": None,  # MDPI Viruses
    "viruses-16-00358": None,  # MDPI Viruses
    "viruses-16-00896": None,  # MDPI Viruses

    # Other
    "veae014": None,  # Virus Evolution
    "eurosurv-28-42-1": None,  # Eurosurveillance
    "main": None,  # Generic - skip
    "elife-45066-v1": None,  # Was long2019 - REMOVED as hallucination

    # TBED papers from earlier
    "TBED-2026-2963364": None,  # Need to identify
    "TBED-2026-8053623": None,  # Need to identify
    "TBED2024-4900097": None,  # Need to identify

    "41467_2024_Article_53766": None,  # Nature Communications
    "41467_2026_Article_76726": "sandwich_tern_age_mortality_2026",

    "1297-9716-45-66": None,  # Veterinary Research
    "1-s2.0-S0141813024100785-main": None,  # ScienceDirect
    "nihpp-2023.06.30.547205v1": "duck_chicken2023",  # bioRxiv preprint
}


def main():
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_DIR.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0

    for pdf_filename, paper_id in MANUAL_MAPPINGS.items():
        if paper_id is None:
            continue

        pdf_path = INPUT_DIR / f"{pdf_filename}.pdf"
        if not pdf_path.exists():
            continue

        dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
        dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"

        if dest_pdf.exists():
            print(f"SKIP (exists): {paper_id}")
            skipped += 1
            continue

        print(f"Processing: {pdf_filename}")
        print(f"  → {paper_id}")

        # Copy PDF
        shutil.copy2(pdf_path, dest_pdf)

        # Convert to markdown
        try:
            md_text = pymupdf4llm.to_markdown(str(dest_pdf))
            dest_md.write_text(md_text)
            print(f"  ✓ Done ({len(md_text):,} chars)")
            processed += 1
        except Exception as e:
            print(f"  ✗ MD conversion failed: {e}")

    print(f"\nProcessed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
