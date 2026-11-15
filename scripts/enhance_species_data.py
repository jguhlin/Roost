#!/usr/bin/env python3
"""
Enhance species data with IUCN conservation status and other metadata.

Adds to species_index.json:
- IUCN Red List status (CR, EN, VU, NT, LC)
- Population trend (increasing, decreasing, stable, unknown)
- Endemic status for key species
- Range/distribution notes

Usage:
    python scripts/enhance_species_data.py
"""

import json
from pathlib import Path

ROOST_DIR = Path(__file__).parent.parent
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"

# IUCN Red List Categories
IUCN_CATEGORIES = {
    "EX": {"code": "EX", "name": "Extinct", "color": "black"},
    "EW": {"code": "EW", "name": "Extinct in the Wild", "color": "black"},
    "CR": {"code": "CR", "name": "Critically Endangered", "color": "red"},
    "EN": {"code": "EN", "name": "Endangered", "color": "orange"},
    "VU": {"code": "VU", "name": "Vulnerable", "color": "yellow"},
    "NT": {"code": "NT", "name": "Near Threatened", "color": "lime"},
    "LC": {"code": "LC", "name": "Least Concern", "color": "green"},
    "DD": {"code": "DD", "name": "Data Deficient", "color": "gray"},
    "NE": {"code": "NE", "name": "Not Evaluated", "color": "gray"},
}

# Species data: scientific_name -> {iucn, trend, endemic, range, population}
# Sources: IUCN Red List, BirdLife International (as of Aug 2026)
SPECIES_DATA = {
    # ========== NEW ZEALAND SPECIES ==========
    # NZ confirmed cases
    "Stercorarius lonnbergi": {
        "iucn": "LC",
        "trend": "stable",
        "range": "Subantarctic islands, Southern Ocean",
        "notes": "First NZ H5 case (July 2026)"
    },
    "Circus approximans": {
        "iucn": "LC",
        "trend": "stable",
        "endemic": "Australasia",
        "range": "Australia, New Zealand, Pacific islands",
        "notes": "Second NZ H5 case (July 2026). Native to NZ."
    },
    "Macronectes halli": {
        "iucn": "LC",
        "trend": "stable",
        "range": "Southern Ocean, subantarctic",
        "notes": "Third NZ H5 case (August 2026)"
    },

    # NZ vaccination targets
    "Strigops habroptila": {
        "iucn": "CR",
        "trend": "increasing",
        "endemic": "New Zealand",
        "range": "Predator-free offshore islands, NZ",
        "population": "~250",
        "notes": "Kakapo. World's only flightless parrot. Under emergency vaccination."
    },
    "Porphyrio hochstetteri": {
        "iucn": "EN",
        "trend": "increasing",
        "endemic": "New Zealand",
        "range": "Fiordland, Murchison Mountains, sanctuary sites",
        "population": "~500",
        "notes": "Takahe. Thought extinct until 1948 rediscovery."
    },

    # ========== HIGH-DETECTION SPECIES ==========
    "Cygnus olor": {
        "iucn": "LC",
        "trend": "increasing",
        "range": "Europe, Central Asia; introduced worldwide",
    },
    "Branta canadensis": {
        "iucn": "LC",
        "trend": "increasing",
        "range": "North America; introduced Europe, NZ",
    },
    "Anas platyrhynchos": {
        "iucn": "LC",
        "trend": "decreasing",
        "range": "Holarctic; most widespread duck",
    },
    "Haliaeetus leucocephalus": {
        "iucn": "LC",
        "trend": "increasing",
        "range": "North America",
        "notes": "Population recovered from DDT era lows"
    },
    "Larus argentatus": {
        "iucn": "LC",
        "trend": "decreasing",
        "range": "Northern Hemisphere coasts",
    },
    "Buteo jamaicensis": {
        "iucn": "LC",
        "trend": "stable",
        "range": "North America to Panama",
    },
    "Morus bassanus": {
        "iucn": "LC",
        "trend": "increasing",
        "range": "North Atlantic coasts",
        "notes": "Major HPAI mortality 2022-2023"
    },

    # ========== CONSERVATION CONCERN SPECIES ==========
    "Gymnogyps californianus": {
        "iucn": "CR",
        "trend": "increasing",
        "endemic": "North America",
        "range": "California, Arizona, Baja California",
        "population": "~500",
        "notes": "California condor. Emergency vaccinated May 2023."
    },
    "Grus americana": {
        "iucn": "EN",
        "trend": "increasing",
        "endemic": "North America",
        "range": "Central flyway, Wood Buffalo NP to Aransas",
        "population": "~800",
        "notes": "Whooping crane. Intensive conservation."
    },
    "Spheniscus demersus": {
        "iucn": "EN",
        "trend": "decreasing",
        "endemic": "Southern Africa",
        "range": "Namibia, South Africa coasts",
        "notes": "African penguin. Major HPAI concern."
    },
    "Pelecanus crispus": {
        "iucn": "NT",
        "trend": "increasing",
        "range": "SE Europe to Central Asia",
    },
    "Geronticus eremita": {
        "iucn": "EN",
        "trend": "increasing",
        "range": "Morocco; reintroduced Spain, Austria",
        "population": "~700 wild",
        "notes": "Northern bald ibis. Reintroduction programs."
    },

    # ========== SEABIRDS OF CONCERN ==========
    "Stercorarius skua": {
        "iucn": "LC",
        "trend": "decreasing",
        "range": "North Atlantic, breeding Scotland/Iceland",
        "notes": "Great skua. Significant HPAI mortality 2022."
    },
    "Uria aalge": {
        "iucn": "LC",
        "trend": "decreasing",
        "range": "North Atlantic, North Pacific",
        "notes": "Common murre. Colony die-offs from HPAI."
    },
    "Fratercula arctica": {
        "iucn": "VU",
        "trend": "decreasing",
        "range": "North Atlantic breeding colonies",
        "notes": "Atlantic puffin."
    },
    "Rissa tridactyla": {
        "iucn": "VU",
        "trend": "decreasing",
        "range": "Arctic and North Atlantic coasts",
        "notes": "Black-legged kittiwake."
    },

    # ========== RAPTORS ==========
    "Aquila chrysaetos": {
        "iucn": "LC",
        "trend": "stable",
        "range": "Holarctic mountains and open country",
    },
    "Falco peregrinus": {
        "iucn": "LC",
        "trend": "increasing",
        "range": "Worldwide except Antarctica",
        "notes": "Recovered from pesticide era decline"
    },
    "Haliaeetus albicilla": {
        "iucn": "LC",
        "trend": "increasing",
        "range": "Eurasia; reintroduced UK, Ireland",
        "notes": "White-tailed eagle"
    },
    "Bubo scandiacus": {
        "iucn": "VU",
        "trend": "decreasing",
        "range": "Arctic tundra circumpolar",
        "notes": "Snowy owl"
    },

    # ========== CRANES ==========
    "Grus japonensis": {
        "iucn": "EN",
        "trend": "stable",
        "range": "Japan, Korea, NE China, Russia",
        "population": "~3,000",
        "notes": "Red-crowned crane"
    },
    "Grus monacha": {
        "iucn": "VU",
        "trend": "decreasing",
        "range": "E Russia breeding; Japan, Korea wintering",
        "notes": "Hooded crane"
    },
    "Balearica regulorum": {
        "iucn": "EN",
        "trend": "decreasing",
        "range": "East and Southern Africa",
        "notes": "Grey crowned-crane"
    },

    # ========== WATERFOWL ==========
    "Cygnus atratus": {
        "iucn": "LC",
        "trend": "stable",
        "endemic": "Australia",
        "range": "Australia, introduced NZ",
        "notes": "Black swan. Highly susceptible to HPAI."
    },
    "Anser indicus": {
        "iucn": "LC",
        "trend": "stable",
        "range": "Central Asia; world's highest-flying bird",
        "notes": "Bar-headed goose. Key HPAI vector species."
    },
    "Mergus squamatus": {
        "iucn": "EN",
        "trend": "decreasing",
        "range": "Russian Far East, NE China, Korea",
        "population": "~2,500",
        "notes": "Scaly-sided merganser"
    },
    "Aythya baeri": {
        "iucn": "CR",
        "trend": "decreasing",
        "range": "NE Asia breeding; SE Asia wintering",
        "population": "~500",
        "notes": "Baer's pochard"
    },

    # ========== MAMMALS (not in avian phylogeny) ==========
    "Arctocephalus forsteri": {
        "iucn": "LC",
        "trend": "increasing",
        "class": "Mammalia",
        "range": "New Zealand, southern Australia",
        "notes": "Long-nosed fur seal. First AU mainland mammal H5N1 case (Aug 2026)."
    },
    "Neophoca cinerea": {
        "iucn": "EN",
        "trend": "decreasing",
        "class": "Mammalia",
        "endemic": "Australia",
        "range": "South and Western Australia coasts",
        "population": "<12,000",
        "notes": "Australian sea lion. Endangered, at risk from HPAI."
    },
    "Mirounga leonina": {
        "iucn": "LC",
        "trend": "stable",
        "class": "Mammalia",
        "range": "Subantarctic islands, Southern Ocean",
        "notes": "Southern elephant seal. >17,000 pups died in Argentina 2023."
    },
    "Arctocephalus pusillus": {
        "iucn": "LC",
        "trend": "increasing",
        "class": "Mammalia",
        "range": "Southern Africa, Australia",
        "notes": "Cape/Australian fur seal."
    },
}


def load_species_index():
    """Load the current species index."""
    index_file = WEB_DATA_DIR / "species_index.json"
    with open(index_file) as f:
        return json.load(f)


def save_species_index(species_list):
    """Save the updated species index."""
    index_file = WEB_DATA_DIR / "species_index.json"
    with open(index_file, "w") as f:
        json.dump(species_list, f, separators=(",", ":"))
    print(f"Saved {len(species_list)} species to {index_file}")


def enhance_species(species_list):
    """Add conservation data to species records."""
    enhanced_count = 0

    for sp in species_list:
        sci_name = sp.get("sci", "")
        if sci_name in SPECIES_DATA:
            data = SPECIES_DATA[sci_name]

            # Add IUCN status
            if "iucn" in data:
                sp["iucn"] = data["iucn"]

            # Add population trend
            if "trend" in data:
                sp["trend"] = data["trend"]

            # Add endemic status
            if "endemic" in data:
                sp["endemic"] = data["endemic"]

            # Add range
            if "range" in data:
                sp["range"] = data["range"]

            # Add population estimate
            if "population" in data:
                sp["population"] = data["population"]

            # Add notes
            if "notes" in data:
                sp["notes"] = data["notes"]

            enhanced_count += 1

    return enhanced_count


def main():
    print("=" * 60)
    print("ENHANCE SPECIES DATA WITH IUCN STATUS")
    print("=" * 60)

    # Load current index
    species_list = load_species_index()
    print(f"\nLoaded {len(species_list)} species from index")

    # Enhance with conservation data
    print(f"\nAdding conservation data for {len(SPECIES_DATA)} species...")
    enhanced = enhance_species(species_list)
    print(f"Enhanced {enhanced} species records")

    # Save
    save_species_index(species_list)

    # Also update enhanced index
    enhanced_file = WEB_DATA_DIR / "species_index_enhanced.json"
    with open(enhanced_file, "w") as f:
        json.dump(species_list, f, separators=(",", ":"))
    print(f"Saved to {enhanced_file}")

    # Copy to dist if exists
    dist_file = WEB_DATA_DIR.parent.parent / "dist" / "data" / "species_index.json"
    if dist_file.parent.exists():
        with open(dist_file, "w") as f:
            json.dump(species_list, f, separators=(",", ":"))
        print(f"Saved to {dist_file}")

    # Summary by IUCN category
    print("\n" + "=" * 60)
    print("SPECIES BY IUCN CATEGORY")
    print("=" * 60)

    categories = {}
    for sp in species_list:
        iucn = sp.get("iucn", "NE")
        if iucn not in categories:
            categories[iucn] = []
        categories[iucn].append(sp.get("com") or sp.get("sci"))

    # Sort by severity
    order = ["CR", "EN", "VU", "NT", "LC", "DD", "NE"]
    for cat in order:
        if cat in categories:
            info = IUCN_CATEGORIES.get(cat, {"name": cat})
            print(f"\n{cat} - {info.get('name', cat)} ({len(categories[cat])} species):")
            for name in categories[cat][:5]:
                print(f"  - {name}")
            if len(categories[cat]) > 5:
                print(f"  ... and {len(categories[cat]) - 5} more")


if __name__ == "__main__":
    main()
