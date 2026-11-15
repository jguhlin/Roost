#!/usr/bin/env python3
"""
Add mammalian species affected by H5N1 to the species index.

Mammals are tracked separately from birds:
- They appear in species search and details
- They do NOT appear in the avian phylogeny
- They have a "class": "Mammalia" field to distinguish them

Usage:
    python scripts/add_mammal_species.py
"""

import json
from pathlib import Path

ROOST_DIR = Path(__file__).parent.parent
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"

# Mammalian species with H5N1 detections or at high risk
# Genome accessions from DNA Zoo and NCBI
MAMMAL_SPECIES = [
    {
        "taxon_id": None,  # Will look up or generate
        "scientific_name": "Arctocephalus forsteri",
        "common_name": "long-nosed fur seal",
        "class": "Mammalia",
        "order": "Carnivora",
        "family": "Otariidae",
        "iucn": "LC",
        "trend": "increasing",
        "range": "New Zealand, southern Australia",
        "detections": 1,
        "notes": "First AU mainland mammal H5N1 case (Aug 2026, Beachport SA)",
        "genome": "DNA Zoo assembly",
        "genome_accession": "GCA_028648375.1",
    },
    {
        "taxon_id": None,
        "scientific_name": "Neophoca cinerea",
        "common_name": "Australian sea lion",
        "class": "Mammalia",
        "order": "Carnivora",
        "family": "Otariidae",
        "iucn": "EN",
        "trend": "decreasing",
        "endemic": "Australia",
        "range": "South and Western Australia coasts",
        "population": "<12,000",
        "detections": 0,
        "notes": "Endangered, at high risk from HPAI"
    },
    {
        "taxon_id": None,
        "scientific_name": "Mirounga leonina",
        "common_name": "southern elephant seal",
        "class": "Mammalia",
        "order": "Carnivora",
        "family": "Phocidae",
        "iucn": "LC",
        "trend": "stable",
        "range": "Subantarctic islands, Southern Ocean",
        "detections": 0,  # Not in our AU data, but major outbreaks elsewhere
        "notes": ">17,000 pups died in Argentina 2023; 13,359 at Heard Island 2025",
        "genome": "NCBI reference genome",
        "genome_accession": "GCF_011800145.1",
    },
    {
        "taxon_id": None,
        "scientific_name": "Arctocephalus pusillus",
        "common_name": "Australian fur seal",
        "class": "Mammalia",
        "order": "Carnivora",
        "family": "Otariidae",
        "iucn": "LC",
        "trend": "increasing",
        "range": "Southern Africa, southeastern Australia",
        "detections": 0,
        "notes": "Cape/Australian fur seal. At risk from HPAI."
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


def main():
    """Upsert MAMMAL_SPECIES into the curated overlay.

    Phase 3 (DATA_MATURATION): this script no longer edits
    species_index.json directly - export_web_data.py is its only writer.
    After updating the overlay, regenerate with:
        pixi run python scripts/export_web_data.py   # or just generate_search_index()
    """
    print("=" * 60)
    print("UPDATE MAMMAL OVERLAY (data/manual/species_overlay.json)")
    print("=" * 60)

    overlay = load_overlay()
    mammals = overlay.setdefault("mammals", [])
    by_sci = {m.get("scientific_name"): i for i, m in enumerate(mammals)}

    for mammal in MAMMAL_SPECIES:
        sci = mammal["scientific_name"]
        if sci in by_sci:
            mammals[by_sci[sci]].update(mammal)
            print(f"  UPDATED: {mammal['common_name']}")
        else:
            mammals.append(mammal)
            by_sci[sci] = len(mammals) - 1
            print(f"  ADDED: {mammal['common_name']}")

    save_overlay(overlay)
    print(f"\n{len(mammals)} curated mammals in overlay.")
    print("Regenerate the index: pixi run python scripts/export_web_data.py")


if __name__ == "__main__":
    main()
