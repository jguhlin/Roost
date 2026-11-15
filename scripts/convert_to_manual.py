#!/usr/bin/env python3
"""
One-time converter: turn curated one-off additions (NZ, Australia) into
manual supplement JSONs under data/manual/.

Supplements in data/manual/*.json are loaded by ingest_detections.py as a
first-class source, so curated records survive pipeline rebuilds (the old
add_*_detections.py scripts wrote directly into detections_merged.parquet
and were silently wiped by the next ingest).

Each supplement file:
  {"source": "<tag>", "records": [{...canonical schema...}]}
Record fields: species_raw, scientific_name_parsed, date_detected, country,
state, county, strain, sampling_method_raw, sampling_type, source_file,
detection_count, latitude, longitude.  (taxon_id is looked up from the
taxonomy automatically during harmonization.)

Usage: pixi run python scripts/convert_to_manual.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
MANUAL_DIR = DATA_DIR / "manual"
sys.path.insert(0, str(ROOST_DIR / "scripts"))


def convert_nz():
    """Extract the 3 NZ records from add_nz_detections.py's hardcoded list."""
    from add_nz_detections import NZ_DETECTIONS
    records = []
    for r in NZ_DETECTIONS:
        records.append({
            "species_raw": r["species_raw"],
            "scientific_name_parsed": r["scientific_name"],
            "date_detected": r["date_detected"],
            "country": r["country"],
            "state": r.get("state"),
            "county": r.get("county"),
            "strain": r.get("strain", "H5"),
            "sampling_method_raw": r.get("sampling_method_raw", "dead bird"),
            "sampling_type": r.get("sampling_type", "mortality"),
            "source_file": "nz_hpai_cases.json",
            "detection_count": r.get("detection_count", 1),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
        })
    return records


def convert_aus():
    """Convert scraped Australian events using add_aus_detections.py logic."""
    from add_aus_detections import get_coordinates

    scraped = json.loads((DATA_DIR / "sources" / "aus_scraped_events.json").read_text())
    events = scraped.get("events_by_species", [])

    species_keywords = ["Tern", "Gull", "Penguin", "Petrel", "Seal", "Gannet",
                        "Booby", "Shearwater"]
    records = []
    for e in events:
        loc = e.get("locality", "")
        if any(kw in loc for kw in species_keywords):
            continue  # malformed scrape rows
        try:
            date_iso = datetime.strptime(e.get("date", ""), "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            date_iso = e.get("date", "")
        lat, lon = get_coordinates(loc, e.get("state", ""))
        records.append({
            "species_raw": e.get("common_name", ""),
            "scientific_name_parsed": e.get("scientific_name", ""),
            "date_detected": date_iso,
            "country": "AUS",
            "state": e.get("state", ""),
            "county": loc,
            "strain": "H5N1",
            "sampling_method_raw": "DAFF wildlife disease report",
            "sampling_type": "mortality",
            "source_file": "aus_scraped_events.json",
            "detection_count": 1,
            "latitude": lat,
            "longitude": lon,
        })
    return records


def main():
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)

    for name, records in [("nz_doc_detections.json", convert_nz()),
                          ("aus_daff_detections.json", convert_aus())]:
        source_tag = "NZ-DOC" if name.startswith("nz") else "DAFF"
        path = MANUAL_DIR / name
        path.write_text(json.dumps({
            "source": source_tag,
            "description": "Curated supplement (see scripts/convert_to_manual.py)",
            "records": records,
        }, indent=1))
        print(f"wrote {path} ({len(records)} records, source={source_tag})")


if __name__ == "__main__":
    main()
