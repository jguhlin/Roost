#!/usr/bin/env python3
"""
Build enhanced species data by connecting paper analyses to species database.
Creates species profiles with:
- Paper citation counts
- Infection/study evidence
- Gene associations from papers
- Susceptibility data from papers vs. database
"""

import json
from pathlib import Path
from collections import defaultdict
import re

# Paths
ROOST_DIR = Path(__file__).parent.parent.parent
ANALYSES_DIR = ROOST_DIR / "data" / "papers" / "analyses"
SPECIES_INDEX = ROOST_DIR / "web" / "public" / "data" / "species_index.json"
SPECIES_PROFILES = ROOST_DIR / "data" / "species_profiles_summary.json"
OUTPUT_FILE = ROOST_DIR / "web" / "public" / "data" / "species_papers.json"
PAPERS_FILE = ROOST_DIR / "web" / "public" / "data" / "papers.json"

# Mapping from paper species names to database common names
SPECIES_NAME_MAP = {
    # Avian - Note: Chicken/Gallus gallus is domestic poultry, not in wild bird detection DB
    "Chicken": [],  # Gallus gallus - poultry, not tracked as wild bird
    "Duck": ["duck", "mallard", "teal"],
    "Mallard": ["mallard"],
    "Turkey": ["turkey"],  # Meleagris gallopavo
    "Goose": ["goose"],
    "Swan": ["swan", "mute swan", "trumperter swan", "common whooper", "black swan", "tundra swan", "black-necked swan", "Bewick's swan"],
    "Whooper Swan": ["common whooper"],  # Cygnus cygnus
    "Eagle": ["eagle", "bald eagle", "golden eagle", "white-tailed eagle"],
    "Northern Gannet": ["northern gannet"],
    "Great Skua": ["great skua"],
    "Gull": ["gull", "herring gull", "black-headed gull", "great black-backed gull", "lesser black-backed gull", "glaucous gull", "mew gull", "kittiwake"],
    "Crow": ["crow", "American crow", "hooded crow", "carrion crow", "House crow"],
    "Raven": ["raven", "Common raven"],
    "Vulture": ["vulture", "black vulture", "turkey vulture", "Eurasian griffon", "lammergeier"],
    "Hawk": ["hawk", "red-tailed hawk", "red-shouldered hawk", "Cooper's hawk", "Sharp-shinned hawk", "Swainson's hawk", "broad-winged hawk", "Harris's hawk", "ferruginous hawk", "jackal buzzard"],
    "Falcon": ["falcon", "peregrine falcon", "kestrel", "American kestrel", "gyrfalcon", "Saker falcon", "prairie falcon"],
    "Owl": ["owl", "great horned owl", "Snowy owl", "Northern barred owl", "Tawny owl", "barn owl", "American barn owl", "Eurasian eagle-owl", "long-eared owl", "little owl", "spotted eagle-owl", "burrowing owl", "Ural owl", "short-eared owl"],
    "Pelican": ["pelican", "American white pelican", "Dalmatian pelican"],
    "Cormorant": ["cormorant", "great cormorant", "Cape cormorant", "Brandt's cormorant", "Neotropic cormorant", "crowned cormorant"],
    "Heron": ["heron", "grey heron", "great blue heron", "great egret", "snowy egret", "little egret", "Little blue heron", "cattle egret", "green heron", "black-crowned night-heron"],
    "Crane": ["crane", "Sandhill crane", "hooded crane", "Eurasian crane", "Red-crowned crane", "Japanese crane", "Whooping crane", "grey crowned-crane", "blue crane", "black crowned-crane"],
    "Pheasant": ["pheasant", "ring-necked pheasant", "gray peacock-pheasant"],
    "Quail": ["quail", "Common quail", "California quail", "Gambel's quail"],
    "Pigeon": ["pigeon", "rock pigeon", "common wood pigeon", "dove", "mourning dove", "Eurasian collared-dove", "laughing dove", "white-winged dove"],
    "Sparrow": ["sparrow", "house sparrow", "Savannah sparrow", "song sparrow", "white-crowned sparrow"],
    "Penguin": ["penguin", "jackass penguin"],
    "African Penguin": ["jackass penguin"],  # Spheniscus demersus
    "Gentoo Penguin": [],  # Pygoscelis papua - not in detection DB
    "King Penguin": [],  # Aptenodytes patagonicus - not in detection DB
    "Emperor Penguin": [],  # Aptenodytes forsteri - not in detection DB
    "Adelie Penguin": [],  # Pygoscelis adeliae - not in detection DB
    "Chinstrap Penguin": [],  # Pygoscelis antarcticus - not in detection DB
    "Rockhopper Penguin": [],  # Eudyptes chrysocome - not in detection DB
    "Humboldt Penguin": [],  # Spheniscus humboldti - not in detection DB
    "Flamingo": ["flamingo", "Greater flamingo", "Chilean flamingo", "lesser flamingo"],
    "Condor": ["condor", "California condor"],
    "Buzzard": ["buzzard", "common buzzard", "rough-legged hawk"],
    "Grebe": ["grebe", "great crested grebe", "black-necked grebe", "little grebe", "horned grebe", "western grebe"],
    "Tern": ["tern", "Common tern", "Sandwich tern", "Caspian tern", "arctic tern", "royal tern", "Roseate tern", "Forster's tern", "gull-billed tern", "great crested-tern", "white-winged tern"],
    "Stork": ["stork", "White stork", "wood stork", "Asian openbill"],
    "Osprey": ["osprey"],
    "Harrier": ["harrier", "northern harrier", "hen harrier", "western marsh harrier"],
    "Murre": ["murre", "common murre"],
    "Puffin": ["puffin", "Atlantic puffin"],
    "Razorbill": ["razorbill"],
    "Magpie": ["magpie", "Eurasian magpie", "Black-billed magpie", "Oriental magpie-robin"],
    "Rock Pigeon": ["rock pigeon"],
    "Japanese Crane": ["Red-crowned crane", "Japanese crane"],
    "Hooded Crane": ["hooded crane"],
    "White-necked Crane": [],  # Not in database
    "Peregrine Falcon": ["peregrine falcon"],
    "Golden Eagle": ["golden eagle"],
    "Mountain Hawk-Eagle": [],  # Not in database
    "Northern Goshawk": ["Northern goshawk"],
    # Mammals (for reference)
    "Human": [],
    "Cattle": [],
    "Red Fox": [],
    "Domestic Cat": [],
    "Sea Lion": [],
    "Seal": [],
    "Bear": [],
    "Mink": [],
    "Ferret": [],
    "Mouse": [],
    "Pig": [],
    "Dog": [],
}

def load_species_index():
    """Load species index and create lookup by common name."""
    with open(SPECIES_INDEX) as f:
        species_list = json.load(f)

    # Create lookup by common name (lowercase)
    lookup = {}
    for sp in species_list:
        if sp.get("com"):
            lookup[sp["com"].lower()] = sp

    return species_list, lookup

def load_papers():
    """Load papers metadata."""
    with open(PAPERS_FILE) as f:
        data = json.load(f)
    papers = data.get("papers", data) if isinstance(data, dict) else data
    return {p["id"]: p for p in papers}

def load_all_analyses():
    """Load all paper analyses."""
    analyses = {}
    for f in ANALYSES_DIR.glob("*.json"):
        with open(f) as fp:
            analyses[f.stem] = json.load(fp)
    return analyses

def extract_species_data(analyses, papers_meta):
    """Extract species mentions and data from all papers."""
    species_data = defaultdict(lambda: {
        "paper_count": 0,
        "papers": [],
        "total_mentions": 0,
        "genes_mentioned": defaultdict(int),
        "mortality_events": [],
        "locations": set(),
        "effects": defaultdict(int),
    })

    for paper_id, analysis in analyses.items():
        paper_meta = papers_meta.get(paper_id, {})

        # Process avian species
        for sp_name, mentions in analysis.get("avian_species", {}).items():
            if mentions > 0:
                data = species_data[sp_name]
                data["paper_count"] += 1
                data["papers"].append({
                    "id": paper_id,
                    "title": paper_meta.get("title", analysis.get("metadata", {}).get("title", paper_id)),
                    "year": paper_meta.get("year", analysis.get("metadata", {}).get("year")),
                    "mentions": mentions,
                })
                data["total_mentions"] += mentions

                # Add genes from this paper
                for gene, gene_data in analysis.get("genes", {}).items():
                    if gene_data.get("mentions", 0) > 0:
                        data["genes_mentioned"][gene] += 1

                # Add effects
                for effect, count in analysis.get("effects", {}).items():
                    if count > 0:
                        data["effects"][effect] += count

    return species_data

def match_to_database(species_data, species_lookup):
    """Match paper species to database species."""
    matched = {}
    unmatched = []

    for sp_name, data in species_data.items():
        # Try direct match
        sp_lower = sp_name.lower()
        if sp_lower in species_lookup:
            db_sp = species_lookup[sp_lower]
            matched[sp_name] = {
                "db_id": db_sp["id"],
                "db_sci": db_sp["sci"],
                "db_com": db_sp["com"],
                "db_det": db_sp["det"],
                **data,
            }
            continue

        # Try map
        if sp_name in SPECIES_NAME_MAP:
            for possible_name in SPECIES_NAME_MAP[sp_name]:
                if possible_name.lower() in species_lookup:
                    db_sp = species_lookup[possible_name.lower()]
                    matched[sp_name] = {
                        "db_id": db_sp["id"],
                        "db_sci": db_sp["sci"],
                        "db_com": db_sp["com"],
                        "db_det": db_sp["det"],
                        **data,
                    }
                    break

        if sp_name not in matched:
            unmatched.append(sp_name)
            matched[sp_name] = {
                "db_id": None,
                "db_sci": None,
                "db_com": sp_name,
                "db_det": 0,
                **data,
            }

    return matched, unmatched

def build_species_gene_matrix(matched_species, analyses):
    """Build a matrix of species vs genes mentioned in papers."""
    # Get all genes
    all_genes = set()
    for sp_data in matched_species.values():
        all_genes.update(sp_data.get("genes_mentioned", {}).keys())

    # Build matrix
    matrix = {}
    for sp_name, sp_data in matched_species.items():
        matrix[sp_name] = {
            gene: sp_data.get("genes_mentioned", {}).get(gene, 0)
            for gene in sorted(all_genes)
        }

    return matrix, sorted(all_genes)

def main():
    print("Loading data...")
    species_list, species_lookup = load_species_index()
    papers_meta = load_papers()
    analyses = load_all_analyses()

    print(f"Loaded {len(analyses)} paper analyses")
    print(f"Loaded {len(species_list)} species from database")

    print("\nExtracting species data from papers...")
    species_data = extract_species_data(analyses, papers_meta)

    print(f"Found {len(species_data)} species mentioned in papers")

    print("\nMatching to database...")
    matched, unmatched = match_to_database(species_data, species_lookup)

    print(f"Matched: {len(matched) - len(unmatched)} species")
    if unmatched:
        print(f"Unmatched: {unmatched}")

    # Build gene matrix
    print("\nBuilding species-gene matrix...")
    gene_matrix, all_genes = build_species_gene_matrix(matched, analyses)

    # Convert sets to lists for JSON
    for sp_name, data in matched.items():
        data["locations"] = list(data.get("locations", set()))
        data["genes_mentioned"] = dict(data.get("genes_mentioned", {}))
        data["effects"] = dict(data.get("effects", {}))
        # Sort papers by year desc
        data["papers"] = sorted(data["papers"], key=lambda x: x.get("year") or 0, reverse=True)

    # Build output
    output = {
        "generated": "2026-08-26",
        "total_papers": len(analyses),
        "species_count": len(matched),
        "genes_tracked": all_genes,
        "species": dict(sorted(matched.items(), key=lambda x: x[1]["paper_count"], reverse=True)),
    }

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {OUTPUT_FILE}")

    # Print summary
    print("\n=== TOP SPECIES BY PAPER COUNT ===")
    for sp_name, data in sorted(matched.items(), key=lambda x: x[1]["paper_count"], reverse=True)[:20]:
        db_det = data.get("db_det", 0)
        db_status = f"(DB: {db_det} detections)" if db_det > 0 else "(not in DB)"
        print(f"  {sp_name}: {data['paper_count']} papers, {data['total_mentions']} mentions {db_status}")

    print("\n=== SPECIES-GENE ASSOCIATIONS ===")
    # Show species with most gene associations
    gene_rich = sorted(matched.items(), key=lambda x: len([g for g,c in x[1].get("genes_mentioned", {}).items() if c > 0]), reverse=True)[:10]
    for sp_name, data in gene_rich:
        genes = [g for g, c in data.get("genes_mentioned", {}).items() if c > 0]
        print(f"  {sp_name}: {len(genes)} genes - {', '.join(genes[:5])}...")

    # Also update species_index with paper counts
    print("\n=== UPDATING SPECIES INDEX ===")
    updated_count = 0
    for sp in species_list:
        com = sp.get("com", "").lower() if sp.get("com") else None
        if com:
            for paper_sp_name, data in matched.items():
                if data.get("db_com") and data["db_com"].lower() == com:
                    sp["paper_count"] = data["paper_count"]
                    sp["paper_ids"] = [p["id"] for p in data["papers"][:5]]  # Top 5
                    updated_count += 1
                    break

    # Write updated species index
    updated_index_path = ROOST_DIR / "web" / "public" / "data" / "species_index_enhanced.json"
    with open(updated_index_path, "w") as f:
        json.dump(species_list, f)

    print(f"Updated {updated_count} species with paper data")
    print(f"Wrote {updated_index_path}")

    return matched

if __name__ == "__main__":
    main()
