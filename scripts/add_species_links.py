#!/usr/bin/env python3
"""
Add species_links to papers.json to create a graph connecting papers to species.
Also creates a mammal_species.json for non-avian species mentioned in papers.
"""

import json
import re
from pathlib import Path

# Mapping of common names/keywords to scientific names
SPECIES_KEYWORDS = {
    # Waterfowl - Ducks
    "mallard": "Anas platyrhynchos",
    "duck": "Anas platyrhynchos",  # Generic duck -> mallard as representative
    "ducks": "Anas platyrhynchos",
    "domestic duck": "Anas platyrhynchos",
    "teal": "Anas crecca",
    "common teal": "Anas crecca",
    "wigeon": "Mareca americana",
    "pintail": "Anas acuta",
    "shoveler": "Spatula clypeata",
    "eider": "Somateria mollissima",
    "muscovy": "Cairina moschata",
    "anseriformes": "Anas platyrhynchos",  # Order -> representative

    # Waterfowl - Geese
    "goose": "Anser anser",
    "geese": "Anser anser",
    "barnacle goose": "Branta leucopsis",
    "barnacle geese": "Branta leucopsis",
    "canada goose": "Branta canadensis",
    "snow goose": "Anser caerulescens",
    "greylag": "Anser anser",
    "bean goose": "Anser fabalis",
    "pink-footed": "Anser brachyrhynchus",

    # Waterfowl - Swans
    "swan": "Cygnus olor",
    "swans": "Cygnus olor",
    "mute swan": "Cygnus olor",
    "whooper swan": "Cygnus cygnus",
    "whooper": "Cygnus cygnus",
    "trumpeter swan": "Cygnus buccinator",
    "tundra swan": "Cygnus columbianus",
    "black swan": "Cygnus atratus",

    # Poultry
    "chicken": "Gallus gallus",
    "chickens": "Gallus gallus",
    "poultry": "Gallus gallus",
    "domestic birds": "Gallus gallus",
    "turkey": "Meleagris gallopavo",
    "turkeys": "Meleagris gallopavo",
    "quail": "Coturnix coturnix",
    "pheasant": "Phasianus colchicus",
    "galliformes": "Gallus gallus",  # Order -> representative

    # Generic wild bird terms
    "wild bird": "WILD_BIRD",
    "wild birds": "WILD_BIRD",
    "waterfowl": "Anas platyrhynchos",
    "migratory bird": "WILD_BIRD",
    "migratory birds": "WILD_BIRD",
    "avian": "WILD_BIRD",

    # Seabirds
    "gannet": "Morus bassanus",
    "gannets": "Morus bassanus",
    "northern gannet": "Morus bassanus",
    "tern": "Sterna hirundo",
    "terns": "Sterna hirundo",
    "sandwich tern": "Thalasseus sandvicensis",
    "skua": "Stercorarius skua",
    "skuas": "Stercorarius skua",
    "great skua": "Stercorarius skua",
    "south polar skua": "Stercorarius skua",
    "kittiwake": "Rissa tridactyla",
    "kittiwakes": "Rissa tridactyla",
    "gull": "Larus argentatus",
    "gulls": "Larus argentatus",
    "herring gull": "Larus argentatus",
    "black-headed gull": "Chroicocephalus ridibundus",
    "pelican": "Pelecanus erythrorhynchos",
    "pelicans": "Pelecanus erythrorhynchos",
    "dalmatian pelican": "Pelecanus crispus",
    "cormorant": "Phalacrocorax carbo",
    "murre": "Uria aalge",
    "puffin": "Fratercula arctica",
    "fulmar": "Fulmarus glacialis",
    "shearwater": "Ardenna tenuirostris",
    "seabird": "Morus bassanus",
    "seabirds": "Morus bassanus",
    "sea duck": "Somateria mollissima",
    "sea ducks": "Somateria mollissima",

    # Raptors
    "eagle": "Haliaeetus leucocephalus",
    "eagles": "Haliaeetus leucocephalus",
    "bald eagle": "Haliaeetus leucocephalus",
    "white-tailed eagle": "Haliaeetus albicilla",
    "hawk": "Buteo jamaicensis",
    "hawks": "Buteo jamaicensis",
    "red-tailed hawk": "Buteo jamaicensis",
    "rough-legged hawk": "Buteo lagopus",
    "buzzard": "Buteo buteo",
    "falcon": "Falco peregrinus",
    "falcons": "Falco peregrinus",
    "peregrine": "Falco peregrinus",
    "owl": "Bubo virginianus",
    "owls": "Bubo virginianus",
    "great horned owl": "Bubo virginianus",
    "snowy owl": "Bubo scandiacus",
    "vulture": "Coragyps atratus",
    "vultures": "Coragyps atratus",
    "griffon vulture": "Gyps fulvus",
    "griffon": "Gyps fulvus",
    "condor": "Gymnogyps californianus",
    "california condor": "Gymnogyps californianus",
    "raptor": "Buteo jamaicensis",
    "raptors": "Buteo jamaicensis",
    "kite": "Milvus milvus",
    "scavenger": "Coragyps atratus",
    "scavengers": "Coragyps atratus",

    # Corvids
    "crow": "Corvus brachyrhynchos",
    "crows": "Corvus brachyrhynchos",
    "american crow": "Corvus brachyrhynchos",
    "raven": "Corvus corax",
    "corvid": "Corvus brachyrhynchos",
    "corvids": "Corvus brachyrhynchos",
    "magpie": "Pica pica",
    "jay": "Cyanocitta cristata",
    "synanthropic": "Corvus brachyrhynchos",

    # Shorebirds
    "sanderling": "Calidris alba",
    "sandpiper": "Calidris alpina",
    "dunlin": "Calidris alpina",
    "shorebird": "Calidris alba",
    "shorebirds": "Calidris alba",
    "plover": "Charadrius vociferus",
    "curlew": "Numenius arquata",

    # Other waterbirds
    "heron": "Ardea cinerea",
    "herons": "Ardea cinerea",
    "egret": "Ardea alba",
    "stork": "Ciconia ciconia",
    "crane": "Grus grus",
    "cranes": "Grus grus",
    "flamingo": "Phoenicopterus roseus",
    "ibis": "Threskiornis aethiopicus",
    "coot": "Fulica atra",
    "grebe": "Podiceps cristatus",

    # Penguins
    "penguin": "Spheniscus demersus",
    "penguins": "Spheniscus demersus",
    "adélie penguin": "Pygoscelis adeliae",
    "adélie": "Pygoscelis adeliae",
}

# Generic marker for papers about wild birds in general
WILD_BIRD_MARKER = "WILD_BIRD"

# Mammal species mapping (will be stored separately)
MAMMAL_KEYWORDS = {
    "cattle": {"sci": "Bos taurus", "common": "Domestic cattle"},
    "cow": {"sci": "Bos taurus", "common": "Domestic cattle"},
    "cows": {"sci": "Bos taurus", "common": "Domestic cattle"},
    "dairy": {"sci": "Bos taurus", "common": "Domestic cattle"},
    "bovine": {"sci": "Bos taurus", "common": "Domestic cattle"},

    "cat": {"sci": "Felis catus", "common": "Domestic cat"},
    "cats": {"sci": "Felis catus", "common": "Domestic cat"},
    "feline": {"sci": "Felis catus", "common": "Domestic cat"},

    "fox": {"sci": "Vulpes vulpes", "common": "Red fox"},
    "foxes": {"sci": "Vulpes vulpes", "common": "Red fox"},
    "red fox": {"sci": "Vulpes vulpes", "common": "Red fox"},

    "seal": {"sci": "Mirounga leonina", "common": "Southern elephant seal"},
    "seals": {"sci": "Mirounga leonina", "common": "Southern elephant seal"},
    "elephant seal": {"sci": "Mirounga leonina", "common": "Southern elephant seal"},
    "fur seal": {"sci": "Arctocephalus gazella", "common": "Antarctic fur seal"},

    "sea lion": {"sci": "Otaria flavescens", "common": "South American sea lion"},
    "sea lions": {"sci": "Otaria flavescens", "common": "South American sea lion"},
    "pinniped": {"sci": "Otaria flavescens", "common": "South American sea lion"},
    "pinnipeds": {"sci": "Otaria flavescens", "common": "South American sea lion"},

    "mink": {"sci": "Neogale vison", "common": "American mink"},

    "swine": {"sci": "Sus scrofa", "common": "Domestic pig"},
    "pig": {"sci": "Sus scrofa", "common": "Domestic pig"},
    "pigs": {"sci": "Sus scrofa", "common": "Domestic pig"},

    "ferret": {"sci": "Mustela furo", "common": "Domestic ferret"},
    "ferrets": {"sci": "Mustela furo", "common": "Domestic ferret"},

    "skunk": {"sci": "Mephitis mephitis", "common": "Striped skunk"},
    "raccoon": {"sci": "Procyon lotor", "common": "Raccoon"},
    "bobcat": {"sci": "Lynx rufus", "common": "Bobcat"},
    "coyote": {"sci": "Canis latrans", "common": "Coyote"},
    "opossum": {"sci": "Didelphis virginiana", "common": "Virginia opossum"},

    "human": {"sci": "Homo sapiens", "common": "Human"},
    "humans": {"sci": "Homo sapiens", "common": "Human"},

    "mammal": {"sci": "MAMMAL", "common": "Mammal (general)"},  # Generic marker
    "mammals": {"sci": "MAMMAL", "common": "Mammal (general)"},
    "marine mammal": {"sci": "MAMMAL", "common": "Mammal (general)"},
    "marine mammals": {"sci": "MAMMAL", "common": "Mammal (general)"},
}

# Generic marker for papers about mammals in general
MAMMAL_MARKER = "MAMMAL"


def extract_species_links(paper):
    """Extract species links from a paper based on title, summary, and topics."""
    text = " ".join([
        paper.get("title", ""),
        paper.get("summary", ""),
        " ".join(paper.get("topics", [])),
    ]).lower()

    avian_species = set()
    mammal_species = set()
    is_general_wild_bird = False
    is_general_mammal = False

    # Check for avian species
    for keyword, sci_name in SPECIES_KEYWORDS.items():
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text):
            if sci_name == WILD_BIRD_MARKER:
                is_general_wild_bird = True
            else:
                avian_species.add(sci_name)

    # Check for mammal species
    for keyword, mammal_info in MAMMAL_KEYWORDS.items():
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text):
            if mammal_info["sci"] == MAMMAL_MARKER:
                is_general_mammal = True
            else:
                mammal_species.add(mammal_info["sci"])

    return {
        "avian": sorted(list(avian_species)),
        "mammal": sorted(list(mammal_species)),
        "general_wild_bird": is_general_wild_bird,
        "general_mammal": is_general_mammal
    }


def main():
    # Paths
    papers_path = Path("/mnt/data/development/Roost/web/public/data/papers.json")
    mammals_path = Path("/mnt/data/development/Roost/web/public/data/mammals.json")

    # Load papers
    with open(papers_path) as f:
        data = json.load(f)

    papers = data.get("papers", [])

    # Track all mammals found
    all_mammals = {}

    # Add species_links to each paper
    for paper in papers:
        links = extract_species_links(paper)
        paper["species_links"] = links

        # Collect mammal species
        for sci in links["mammal"]:
            if sci not in all_mammals:
                # Find the common name
                for keyword, info in MAMMAL_KEYWORDS.items():
                    if info and info["sci"] == sci:
                        all_mammals[sci] = info["common"]
                        break

    # Update papers.json
    with open(papers_path, "w") as f:
        json.dump(data, f, indent=2)

    # Create mammals.json for non-avian species
    mammal_list = [
        {"sci": sci, "common": common, "type": "mammal"}
        for sci, common in sorted(all_mammals.items())
    ]

    mammals_data = {
        "species": mammal_list,
        "last_updated": "2026-08-26",
        "description": "Non-avian species mentioned in H5N1 research papers"
    }

    with open(mammals_path, "w") as f:
        json.dump(mammals_data, f, indent=2)

    # Print summary
    print(f"Updated {len(papers)} papers with species_links")
    print(f"Created mammals.json with {len(mammal_list)} mammal species")

    # Count papers by species type
    avian_count = sum(1 for p in papers if p["species_links"]["avian"])
    mammal_count = sum(1 for p in papers if p["species_links"]["mammal"])
    both_count = sum(1 for p in papers if p["species_links"]["avian"] and p["species_links"]["mammal"])
    general_wild_count = sum(1 for p in papers if p["species_links"].get("general_wild_bird", False))
    general_mammal_count = sum(1 for p in papers if p["species_links"].get("general_mammal", False))

    # Papers with no links at all
    no_links = sum(1 for p in papers if (
        not p["species_links"]["avian"] and
        not p["species_links"]["mammal"] and
        not p["species_links"].get("general_wild_bird", False) and
        not p["species_links"].get("general_mammal", False)
    ))

    print(f"\nPapers with specific avian species links: {avian_count}")
    print(f"Papers with specific mammal species links: {mammal_count}")
    print(f"Papers with both avian and mammal: {both_count}")
    print(f"Papers about wild birds in general: {general_wild_count}")
    print(f"Papers about mammals in general: {general_mammal_count}")
    print(f"Papers with no species links: {no_links}")

    # Show some examples
    print("\nSample species links:")
    for paper in papers[:5]:
        print(f"  {paper['id']}: {paper['species_links']}")


if __name__ == "__main__":
    main()
