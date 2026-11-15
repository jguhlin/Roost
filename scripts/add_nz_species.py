#!/usr/bin/env python3
"""
Add curated HPAI detections and species of concern to the species index.

This script:
1. Adds manually-confirmed detection cases (any country; historically the
   NZ HPAI incursion — brown skua, swamp harrier, northern giant petrel)
2. Adds species of concern for conservation/vaccination programs
   (takahe, kakapo, etc.) — equal treatment, no region-specific schema
3. Upserts the curated overlay (data/manual/species_overlay.json); the index
   regenerates via scripts/export_web_data.py (its only writer)

Usage:
    python scripts/add_nz_species.py
"""

import json
from pathlib import Path
from datetime import datetime

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"

# Manually-confirmed HPAI cases (August 2026, NZ incursion — the case
# provenance is country-agnostic schema; these happen to be NZ DOC/MPI)
NZ_CONFIRMED_CASES = [
    {
        "taxon_id": 54054,
        "scientific_name": "Stercorarius lonnbergi",
        "common_name": "brown skua",
        "order": "Charadriiformes",
        "family": "Stercorariidae",
        "detections": 1,
        "countries": ["NZL"],
        "case": {
            "case_number": 1,
            "date": "2026-07-15",
            "source": "DOC"
        }
    },
    {
        "taxon_id": 387821,
        "scientific_name": "Circus approximans",
        "common_name": "swamp harrier",
        "maori_name": "kāhu",
        "order": "Accipitriformes",
        "family": "Accipitridae",
        "detections": 1,
        "countries": ["NZL"],
        "case": {
            "case_number": 2,
            "date": "2026-07-17",
            "location": "Wairarapa",
            "source": "DOC"
        }
    },
    {
        "taxon_id": 79630,
        "scientific_name": "Macronectes halli",
        "common_name": "northern giant petrel",
        "order": "Procellariiformes",
        "family": "Procellariidae",
        "detections": 1,
        "countries": ["NZL"],
        "case": {
            "case_number": 3,
            "date": "2026-08-21",
            "location": "Cape Palliser, Wairarapa",
            "source": "MPI"
        }
    },
]

# Species of concern (conservation / vaccination-program targets —
# historically the NZ endemic set; schema is country-agnostic)
NZ_SPECIES_OF_CONCERN = [
    {
        "taxon_id": 2489341,
        "scientific_name": "Strigops habroptila",
        "common_name": "kākāpō",
        "order": "Psittaciformes",
        "family": "Psittacidae",
        "detections": 0,
        "conservation_status": "critically_endangered",
        "vaccination_target": True,
        "population_estimate": "~250",
        "countries": ["NZL"]
    },
    {
        "taxon_id": 439704,
        "scientific_name": "Porphyrio hochstetteri",
        "common_name": "takahē",
        "order": "Gruiformes",
        "family": "Rallidae",
        "detections": 0,
        "conservation_status": "nationally_vulnerable",
        "vaccination_target": True,
        "population_estimate": "~500",
        "countries": ["NZL"]
    },
]


def load_overlay():
    path = ROOST_DIR / "data" / "manual" / "species_overlay.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"mammals": [], "manual_detections": [], "species_of_concern": []}


def save_overlay(overlay):
    path = ROOST_DIR / "data" / "manual" / "species_overlay.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    overlay.setdefault("_doc", (
        "Curated species overlay - the single home for hand-curated species "
        "metadata. Merged into species_index.json by "
        "scripts/export_web_data.py:generate_search_index (the index's only "
        "writer)."))
    with open(path, "w") as f:
        json.dump(overlay, f, indent=1, ensure_ascii=False)
    print(f"Saved overlay -> {path}")


def upsert(entries, new_entries, label):
    by_sci = {e.get("scientific_name"): i for i, e in enumerate(entries)}
    for sp in new_entries:
        sci = sp["scientific_name"]
        if sci in by_sci:
            entries[by_sci[sci]].update(sp)
            print(f"  UPDATED: {sp['common_name']}")
        else:
            entries.append(sp)
            by_sci[sci] = len(entries) - 1
            print(f"  ADDED: {sp['common_name']}")


def main():
    """Upsert NZ cases + species of concern into the curated overlay.

    Phase 3 (DATA_MATURATION): no longer edits species_index.json directly -
    export_web_data.py is its only writer. After updating the overlay,
    regenerate with: pixi run python scripts/export_web_data.py
    """
    print("=" * 60)
    print("UPDATE NZ SPECIES OVERLAY (data/manual/species_overlay.json)")
    print("=" * 60)

    overlay = load_overlay()
    print("\n--- NZ Confirmed Cases ---")
    upsert(overlay.setdefault("manual_detections", []), NZ_CONFIRMED_CASES, "case")
    print("\n--- NZ Species of Concern (Vaccination Program) ---")
    upsert(overlay.setdefault("species_of_concern", []), NZ_SPECIES_OF_CONCERN, "concern")

    save_overlay(overlay)
    print("\nRegenerate the index: pixi run python scripts/export_web_data.py")


if __name__ == "__main__":
    main()
