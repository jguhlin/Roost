#!/usr/bin/env python3
"""Convert all PDFs in docs/papers_pdfs to markdown."""

import pymupdf4llm
from pathlib import Path


def main():
    pdf_dir = Path("docs/papers_pdfs")
    output_dir = Path("docs/papers_md")
    output_dir.mkdir(exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs to convert\n")

    for pdf_path in pdfs:
        output_path = output_dir / f"{pdf_path.stem}.md"
        print(f"Converting: {pdf_path.name}")

        try:
            md_text = pymupdf4llm.to_markdown(str(pdf_path))
            output_path.write_text(md_text)
            print(f"  → {output_path} ({len(md_text):,} chars)")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\nDone! Markdown files saved to {output_dir}/")


if __name__ == "__main__":
    main()
