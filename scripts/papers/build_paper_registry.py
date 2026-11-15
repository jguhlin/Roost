#!/usr/bin/env python3
"""
Paper asset registry (D50) — internal inventory of every paper's physical
locations: canonical PDF, markdown, corrections, and which drop-folder
filenames deduped into it. Written to data/papers/paper_registry.json —
INTERNAL ONLY, never exported to web/public (per user directive).

Usage: pixi run python scripts/papers/build_paper_registry.py
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PDF_DIR = ROOT / "docs" / "papers_pdfs"
MD_DIR = ROOT / "docs" / "papers_md"
CORR_DIR = ROOT / "data" / "papers" / "correction_pdfs"
CORR_JSON = ROOT / "data" / "papers" / "corrections.json"
DEDUP_LOG = ROOT / "data" / "papers" / "dedup_log.txt"
NEWS_DIR = ROOT / "docs" / "news_md"
OUT = ROOT / "data" / "papers" / "paper_registry.json"


def sha_short(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main():
    registry = {}

    def entry(pid):
        return registry.setdefault(pid, {"pdf": None, "md": None,
                                         "correction_pdf": None,
                                         "dedup_sources": []})

    # canonical PDFs
    for p in sorted(PDF_DIR.glob("*.pdf")):
        e = entry(p.stem)
        e["pdf"] = {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                    "md5_12": sha_short(p)}

    # markdowns (incl. _correction and _dup_ variants)
    for p in sorted(MD_DIR.glob("*.md")):
        stem = p.stem
        if stem.endswith("_correction"):
            e = entry(stem[:-len("_correction")])
            e["correction_md"] = str(p.relative_to(ROOT))
        elif stem.startswith("_dup_"):
            e = entry(stem)
            e["dup_md"] = str(p.relative_to(ROOT))
        else:
            e = entry(stem)
            e["md"] = str(p.relative_to(ROOT))

    # correction PDFs (archived)
    if CORR_DIR.exists():
        for p in CORR_DIR.glob("*.pdf"):
            # attach by filename hint from corrections.json if possible
            for pid, info in (json.loads(CORR_JSON.read_text())
                              if CORR_JSON.exists() else {}).items():
                if info.get("source_pdf") == p.name and not pid.startswith("_"):
                    entry(pid)["correction_pdf"] = str(p.relative_to(ROOT))
                    break
            else:
                entry(f"_orphan:{p.stem}")["correction_pdf"] = str(p.relative_to(ROOT))

    # dedup ledger: drop-filenames → target pid
    if DEDUP_LOG.exists():
        for line in DEDUP_LOG.read_text().splitlines():
            if "\t→" in line:
                src, _, tgt = line.partition("\t→ ")
                tgt = tgt.replace(" (filename)", "").strip()
                entry(tgt)["dedup_sources"].append(src.strip())

    # news clips (separate shelf)
    news = []
    if NEWS_DIR.exists():
        news = [str(p.relative_to(ROOT)) for p in sorted(NEWS_DIR.glob("*.md"))]

    # orphans / integrity flags
    orphan_mds, orphan_pdfs = [], []
    for pid, e in registry.items():
        if e.get("md") and not e.get("pdf") and not pid.startswith(("_")):
            orphan_mds.append(pid)
        if e.get("pdf") and not e.get("md"):
            orphan_pdfs.append(pid)

    out = {
        "generated": datetime.now().isoformat(timespec="minutes"),
        "counts": {
            "papers": sum(1 for e in registry.values() if e.get("pdf") or e.get("md")),
            "pdfs": sum(1 for e in registry.values() if e.get("pdf")),
            "markdowns": sum(1 for e in registry.values() if e.get("md")),
            "corrections": sum(1 for e in registry.values()
                               if e.get("correction_pdf") or e.get("correction_md")),
            "news_clips": len(news),
            "orphan_md_no_pdf": len(orphan_mds),
            "orphan_pdf_no_md": len(orphan_pdfs),
        },
        "orphan_md_no_pdf": orphan_mds[:50],
        "orphan_pdf_no_md": orphan_pdfs[:50],
        "news_clips": news,
        "papers": registry,
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(out["counts"], indent=1))
    print(f"→ {OUT} (internal only — not exported to web)")


if __name__ == "__main__":
    main()
