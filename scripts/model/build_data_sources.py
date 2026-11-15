#!/usr/bin/env python3
"""Data sources registry — every dataset, study, and source we use, with
citations. Rendered on the Credits page.

Aggregates:
  Movebank studies     (cached CSV; studies matching our species)
  Corpus papers        (papers.json — full citation list)
  Genome sources       (genomes.json manifest)
  Detection feeds      (EMPRES-i, WAHIS, etc.)
  Susceptibility/traits (derived from corpus extraction)

The Movebank license terms require attribution of studies whose data
informs our model — this artifact makes that automatic and complete.

Output: data/model/data_sources.json + web twin (large — the credits page
paginates/lazy-loads).

Usage: pixi run python scripts/model/build_data_sources.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
MB_STUDIES = ROOT / "data" / "raw" / "movebank" / "studies.csv"
MOVEMENT = ROOT / "data" / "model" / "movement_coverage.json"
PAPERS = ROOT / "web" / "public" / "data" / "papers.json"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
OUT = ROOT / "data" / "model" / "data_sources.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "data_sources.json"


def movebank_sources() -> list[dict]:
    """All Movebank studies involving our species, with citation info."""
    studies = pl.read_csv(str(MB_STUDIES), infer_schema_length=0)
    mc = json.loads(MOVEMENT.read_text())
    tracked_spp = {c["species"] for c in mc["coverage"] if c["tracked"]}

    out = []
    for r in studies.filter(
        pl.col("taxon_ids").is_not_null() & (pl.col("taxon_ids") != "")
    ).iter_rows(named=True):
        names = [x.strip() for x in str(r["taxon_ids"]).replace(",", "|").split("|")
                 if x.strip() and len(x.strip().split()) == 2]
        our_spp = [n for n in names if n in tracked_spp]
        if not our_spp:
            continue

        citation = str(r.get("citation") or "").strip()
        if citation in ("null", ""):
            citation = ""

        out.append({
            "study_id": r.get("id"),
            "study_name": str(r.get("name") or "")[:200],
            "pi": str(r.get("principal_investigator_name") or "")[:120],
            "pi_email": str(r.get("principal_investigator_email") or "")[:120]
                        if r.get("principal_investigator_email") else "",
            "citation": citation[:500],
            "acknowledgements": str(r.get("acknowledgements") or "")[:300],
            "license_type": str(r.get("license_type") or ""),
            "n_individuals": int(float(r["number_of_individuals"]))
                             if r.get("number_of_individuals")
                             and str(r["number_of_individuals"]) not in ("null", "")
                             else 0,
            "n_locations": int(float(r["number_of_deployed_locations"]))
                           if r.get("number_of_deployed_locations")
                           and str(r["number_of_deployed_locations"]) not in ("null", "")
                           else 0,
            "years": [str(r.get("timestamp_first_deployed_location") or "")[:4],
                      str(r.get("timestamp_last_deployed_location") or "")[:4]],
            "our_species": our_spp[:8],
            "species_count": len(names),
        })

    out.sort(key=lambda s: -s["n_individuals"])
    return out


def corpus_papers() -> list[dict]:
    """Full citation list for every paper in our corpus."""
    papers = json.loads(PAPERS.read_text())["papers"]
    return [{
        "id": p["id"],
        "title": p.get("title", ""),
        "doi": p.get("doi", ""),
        "year": p.get("year"),
        "journal": p.get("journal", ""),
        "authors": p.get("authors", ""),
    } for p in sorted(papers, key=lambda p: p.get("year") or 0)]


def main() -> None:
    mb = movebank_sources()
    papers = corpus_papers()

    n_cited = sum(1 for s in mb if s["citation"])
    n_uncited = len(mb) - n_cited

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "movebank": {
            "total_studies_matching": len(mb),
            "with_formal_citations": n_cited,
            "without_citations": n_uncited,
            "studies": mb,
            "attribution_note": (
                "Study data were provided by Movebank (movebank.org) "
                "researchers. Each study's data remains the property of "
                "its contributors; we use study METADATA only (species, "
                "individual counts, timestamps) — no GPS track data "
                "was downloaded without explicit permission."),
        },
        "corpus_papers": {
            "total": len(papers),
            "papers": papers,
            "attribution_note": (
                "Full-text corpus used for literature extraction. "
                "See individual paper pages for abstracts and links."),
        },
        "detection_sources": [
            {"name": "EMPRES-i Global Animal Disease Intelligence",
             "url": "https://empres-i.fao.org/",
             "description": "FAO Global Animal Disease Intelligence System"},
            {"name": "WOAH WAHIS",
             "url": "https://wahis.woah.org/",
             "description": "World Organisation for Animal Health "
                            "World Animal Health Information System"},
            {"name": "USDA APHIS",
             "url": "https://www.aphis.usda.gov/",
             "description": "US commercial/backyard flock detections"},
        ],
        "genome_sources": [
            {"name": "NCBI RefSeq",
             "url": "https://www.ncbi.nlm.nih.gov/refseq/",
             "description": "Reference genome assemblies"},
            {"name": "Ensembl",
             "url": "https://ensembl.org/",
             "description": "Gene annotations and comparative genomics"},
            {"name": "B10K",
             "url": "https://b10k.genomics.cn/",
             "description": "Bird 10,000 Genomes Project"},
        ],
        "tools": [
            {"name": "Roost", "role": "analysis, extraction, modelling"},
            {"name": "Movebank", "role": "movement study metadata"},
            {"name": "BirdLife Seabird Tracking Database",
             "role": "seabird colony and tracking metadata"},
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"movebank studies (our species): {len(mb)} "
          f"({n_cited} with formal citations)")
    print(f"corpus papers: {len(papers)}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
