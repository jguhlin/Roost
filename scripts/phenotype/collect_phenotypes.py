#!/usr/bin/env python3
"""D117: Host Response Phenotype Collection — ingestion and staging.

Phase 1 (collecting, no LLM): registers sources, extracts raw text from
fetched HTML, stores as structured staging records for later LLM
extraction. Also handles manual entry from PDFs and spreadsheets.

The three outcome categories are strictly separated:
  1. experimental_survival — survivors/total challenged (denominator explicit)
  2. field_survival — longitudinal estimates from marked/tracked birds
  3. evidence_of_recovery — seropositive survivors (NO survival percentage)

Each record is species × study × virus, retaining age, prior immunity,
follow-up duration, and euthanasia handling.

Usage: pixi run python scripts/phenotype/collect_phenotypes.py [--stage]
"""

import argparse
import json
import re
import html as htmlmod
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
RAW = ROOT / "data" / "raw" / "phenotype"
OUT = ROOT / "data" / "phenotype"
STAGING = OUT / "staging.jsonl"
SCHEMA = RAW / "schema.json"


def html_to_text(path: Path) -> str:
    """Crude but effective HTML → text for staging."""
    text = path.read_text(errors="ignore")
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    # preserve table structure for data tables
    text = re.sub(r"<t[dh][^>]*>", " | ", text)
    text = re.sub(r"<tr[^>]*>", "\n", text)
    text = re.sub(r"<br[^>]*>", "\n", text)
    text = re.sub(r"<p[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmlmod.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def stage_sources():
    """Extract raw text from fetched HTML and write staging records."""
    records = []

    sources = [
        {
            "source_id": "fws_condor_hpai",
            "path": RAW / "fws-condor" / "page.html",
            "url": "https://www.fws.gov/program/california-condor-recovery/southwest-california-condor-flock-hpai-information-updates-2023",
            "citation": "U.S. Fish and Wildlife Service. Southwest California Condor Flock HPAI Information Updates — 2023.",
            "source_type": "government_report",
            "reliability": "high",
            "expected_species": ["Gymnogyps californianus"],
            "expected_outcomes": ["field_survival", "evidence_of_recovery"],
        },
        {
            "source_id": "antarctica_heard_hpai",
            "path": RAW / "antarctica-heard" / "page.html",
            "url": "https://www.antarctica.gov.au/news/2026/scientists-determine-extent-of-h5-avian-influenza-bird-flu-outbreak-at-heard-island-and-mcdonald-islands/",
            "citation": "Australian Antarctic Program. Scientists determine extent of H5 bird flu outbreak at Heard Island and McDonald Islands. 2026.",
            "source_type": "government_report",
            "reliability": "high",
            "expected_species": [],
            "expected_outcomes": ["field_survival"],
        },
        {
            "source_id": "cdc_eid_07_0740",
            "path": RAW / "cdc-eid" / "table.html",
            "url": "https://wwwnc.cdc.gov/eid/article/14/1/07-0740-t1",
            "citation": "Kalthoff D, et al. Pathogenicity and transmissibility of highly pathogenic avian influenza virus A (H5N1) in swans and geese. Emerg Infect Dis. 2008;14(1):123-128.",
            "source_type": "peer_reviewed",
            "reliability": "high",
            "expected_species": ["Cygnus cygnus", "Cygnus olor", "Anser anser", "Branta canadensis", "Anas platyrhynchos"],
            "expected_outcomes": ["experimental_survival"],
        },
    ]

    for src in sources:
        if not src["path"].exists():
            print(f"  SKIP {src['source_id']}: file not found")
            continue
        text = html_to_text(src["path"])
        rec = {
            "staging_id": f"{src['source_id']}_{date.today().isoformat()}",
            "stage": "collected",
            "collected": date.today().isoformat(),
            "raw_text": text,
            "schema": json.loads(SCHEMA.read_text())["title"] if SCHEMA.exists() else "D117",
            **{k: v for k, v in src.items() if k != "path"},
        }
        records.append(rec)
        print(f"  staged {src['source_id']}: {len(text)} chars")

    if records:
        with open(STAGING, "a") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nstaged {len(records)} sources -> {STAGING}")
    else:
        print("nothing to stage")


def add_manual(study_id: str, species: str, outcome_type: str, **kwargs):
    """Add a manually-entered phenotype record (for spreadsheet/PDF data)."""
    rec = {
        "record_id": f"manual_{study_id}_{species}_{date.today().isoformat()}",
        "species": species,
        "study_id": study_id,
        "outcome_type": outcome_type,
        "source": {"source_type": "manual_entry", "reliability": "medium",
                   "accessed": date.today().isoformat()},
        **kwargs,
    }
    OUT.mkdir(exist_ok=True)
    with open(OUT / "manual_records.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"added manual record: {rec['record_id']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", action="store_true", help="stage fetched HTML sources")
    args = ap.parse_args()

    if args.stage:
        stage_sources()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
