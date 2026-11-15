#!/usr/bin/env python3
"""
Ingest APHIS wild bird HPAI detection data and map to NCBI taxonomy.
"""

import polars as pl
from pathlib import Path
from collections import defaultdict
import re

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"

# Manual mapping from APHIS common names to NCBI scientific names
# This covers the most common species in the dataset
APHIS_TO_SCIENTIFIC = {
    # Waterfowl (Anseriformes)
    "Mallard": "Anas platyrhynchos",
    "Canada goose": "Branta canadensis",
    "Green-winged teal": "Anas crecca",
    "Snow goose": "Anser caerulescens",
    "Blue-winged teal": "Spatula discors",
    "American wigeon": "Mareca americana",
    "Wood duck": "Aix sponsa",
    "Gadwall": "Mareca strepera",
    "Northern pintail": "Anas acuta",
    "Northern shoveler": "Spatula clypeata",
    "Ring-necked duck": "Aythya collaris",
    "Ross's goose": "Anser rossii",
    "Cackling goose": "Branta hutchinsii",
    "American black duck": "Anas rubripes",
    "Trumpeter swan": "Cygnus buccinator",
    "Common eider": "Somateria mollissima",
    "Lesser scaup": "Aythya affinis",
    "Greater scaup": "Aythya marila",
    "Bufflehead": "Bucephala albeola",
    "Hooded merganser": "Lophodytes cucullatus",
    "Common merganser": "Mergus merganser",
    "Red-breasted merganser": "Mergus serrator",
    "Redhead": "Aythya americana",
    "Canvasback": "Aythya valisineria",
    "Tundra swan": "Cygnus columbianus",
    "Mute swan": "Cygnus olor",
    "Ruddy duck": "Oxyura jamaicensis",
    "Long-tailed duck": "Clangula hyemalis",
    "Common goldeneye": "Bucephala clangula",
    "Surf scoter": "Melanitta perspicillata",
    "White-winged scoter": "Melanitta deglandi",
    "Black scoter": "Melanitta americana",
    "Greater white-fronted goose": "Anser albifrons",
    "Cinnamon teal": "Spatula cyanoptera",
    "Brant": "Branta bernicla",
    "Harlequin duck": "Histrionicus histrionicus",
    "King eider": "Somateria spectabilis",

    # Raptors (Accipitriformes, Falconiformes)
    "Bald eagle": "Haliaeetus leucocephalus",
    "Black vulture": "Coragyps atratus",
    "Red-tailed hawk": "Buteo jamaicensis",
    "Turkey vulture": "Cathartes aura",
    "Peregrine falcon": "Falco peregrinus",
    "Cooper's hawk": "Accipiter cooperii",
    "Red-shouldered hawk": "Buteo lineatus",
    "Great horned owl": "Bubo virginianus",
    "Barred owl": "Strix varia",
    "American kestrel": "Falco sparverius",
    "Sharp-shinned hawk": "Accipiter striatus",
    "Rough-legged hawk": "Buteo lagopus",
    "Northern harrier": "Circus hudsonius",
    "Broad-winged hawk": "Buteo platypterus",
    "Osprey": "Pandion haliaetus",
    "Golden eagle": "Aquila chrysaetos",
    "Swainson's hawk": "Buteo swainsoni",
    "Ferruginous hawk": "Buteo regalis",
    "Snowy owl": "Bubo scandiacus",
    "Eastern screech-owl": "Megascops asio",
    "Short-eared owl": "Asio flammeus",
    "Long-eared owl": "Asio otus",
    "Barn owl": "Tyto alba",
    "Northern saw-whet owl": "Aegolius acadicus",
    "Great gray owl": "Strix nebulosa",

    # Corvids (Passeriformes - Corvidae)
    "American crow": "Corvus brachyrhynchos",
    "Common raven": "Corvus corax",
    "Blue jay": "Cyanocitta cristata",
    "Fish crow": "Corvus ossifragus",
    "Black-billed magpie": "Pica hudsonia",

    # Gulls and terns (Charadriiformes - Laridae)
    "Herring gull": "Larus argentatus",
    "Great black-backed gull": "Larus marinus",
    "Western gull": "Larus occidentalis",
    "Ring-billed gull": "Larus delawarensis",
    "California gull": "Larus californicus",
    "Laughing gull": "Leucophaeus atricilla",
    "Glaucous-winged gull": "Larus glaucescens",
    "Lesser black-backed gull": "Larus fuscus",
    "Bonaparte's gull": "Chroicocephalus philadelphia",
    "Iceland gull": "Larus glaucoides",
    "Glaucous gull": "Larus hyperboreus",
    "Caspian tern": "Hydroprogne caspia",
    "Royal tern": "Thalasseus maximus",
    "Common tern": "Sterna hirundo",
    "Forster's tern": "Sterna forsteri",
    "Black skimmer": "Rynchops niger",

    # Other water birds
    "American white pelican": "Pelecanus erythrorhynchos",
    "Brown pelican": "Pelecanus occidentalis",
    "Double-crested cormorant": "Nannopterum auritum",
    "Great blue heron": "Ardea herodias",
    "Great egret": "Ardea alba",
    "Black-crowned night-heron": "Nycticorax nycticorax",
    "American coot": "Fulica americana",
    "Sandhill crane": "Antigone canadensis",
    "Common loon": "Gavia immer",
    "Red-throated loon": "Gavia stellata",
    "Pacific loon": "Gavia pacifica",
    "Horned grebe": "Podiceps auritus",
    "Western grebe": "Aechmophorus occidentalis",
    "Pied-billed grebe": "Podilymbus podiceps",
    "Eared grebe": "Podiceps nigricollis",

    # Shorebirds
    "Killdeer": "Charadrius vociferus",
    "American oystercatcher": "Haematopus palliatus",
    "Sanderling": "Calidris alba",
    "Ruddy turnstone": "Arenaria interpres",

    # Other common species
    "House sparrow": "Passer domesticus",
    "Rock pigeon": "Columba livia",
    "Mourning dove": "Zenaida macroura",
    "Wild turkey": "Meleagris gallopavo",
    "Ruffed grouse": "Bonasa umbellus",
    "American robin": "Turdus migratorius",
    "Red-winged blackbird": "Agelaius phoeniceus",
    "European starling": "Sturnus vulgaris",
    "House finch": "Haemorhous mexicanus",
    "Northern cardinal": "Cardinalis cardinalis",
    "Brown-headed cowbird": "Molothrus ater",
    "Common grackle": "Quiscalus quiscula",

    # Gamebirds
    "Ring-necked pheasant": "Phasianus colchicus",
    "Northern bobwhite": "Colinus virginianus",
    "Greater prairie-chicken": "Tympanuchus cupido",
    "Chukar": "Alectoris chukar",

    # Seabirds
    "Northern gannet": "Morus bassanus",
    "Brown booby": "Sula leucogaster",
    "Magnificent frigatebird": "Fregata magnificens",
}

# Common name variations/alternates
NAME_ALIASES = {
    "Green winged teal": "Green-winged teal",
    "Blue winged teal": "Blue-winged teal",
    "Red tailed hawk": "Red-tailed hawk",
    "Great horned Owl": "Great horned owl",
    "Black crowned night heron": "Black-crowned night-heron",
    "Black-crowned night heron": "Black-crowned night-heron",
    "Double crested cormorant": "Double-crested cormorant",
    "Red breasted merganser": "Red-breasted merganser",
    "Red shouldered hawk": "Red-shouldered hawk",
    "Sharp shinned hawk": "Sharp-shinned hawk",
    "Rough legged hawk": "Rough-legged hawk",
    "Ring billed gull": "Ring-billed gull",
    "Ring necked duck": "Ring-necked duck",
    "Ring necked pheasant": "Ring-necked pheasant",
    "Black billed magpie": "Black-billed magpie",
    "White winged scoter": "White-winged scoter",
    "Long tailed duck": "Long-tailed duck",
    "Short eared owl": "Short-eared owl",
    "Long eared owl": "Long-eared owl",
    "Saw whet owl": "Northern saw-whet owl",
    "Northern Saw-whet Owl": "Northern saw-whet owl",
}


def normalize_name(name: str) -> str:
    """Normalize a common name for matching."""
    name = name.strip()
    name = NAME_ALIASES.get(name, name)
    return name


def load_aphis_data() -> pl.DataFrame:
    """Load APHIS wild bird detection data."""
    return pl.read_csv(
        RAW_DIR / "aphis_wild_birds.csv",
        try_parse_dates=True,
    )


def load_taxonomy() -> pl.DataFrame:
    """Load our species table with common names."""
    return pl.read_parquet(DATA_DIR / "species_table.parquet")


def build_common_name_index(taxonomy: pl.DataFrame) -> dict:
    """Build index from common names to scientific names."""
    index = {}
    for row in taxonomy.iter_rows(named=True):
        if row["common_name"]:
            # Store lowercase for case-insensitive matching
            index[row["common_name"].lower()] = row["scientific_name"]
    return index


def map_species(aphis_df: pl.DataFrame, taxonomy: pl.DataFrame) -> pl.DataFrame:
    """Map APHIS bird species to NCBI taxonomy."""
    # Build common name index from taxonomy
    common_name_index = build_common_name_index(taxonomy)

    # Get unique species from APHIS
    unique_species = aphis_df["Bird Species"].unique().to_list()

    mappings = []
    unmapped = []

    for species in unique_species:
        if not species:
            continue

        normalized = normalize_name(species)
        scientific_name = None
        match_type = None

        # Try manual mapping first
        if normalized in APHIS_TO_SCIENTIFIC:
            scientific_name = APHIS_TO_SCIENTIFIC[normalized]
            match_type = "manual"
        # Try common name index (case-insensitive)
        elif normalized.lower() in common_name_index:
            scientific_name = common_name_index[normalized.lower()]
            match_type = "common_name"
        else:
            unmapped.append(species)

        if scientific_name:
            # Look up taxon_id
            match = taxonomy.filter(pl.col("scientific_name") == scientific_name)
            if len(match) > 0:
                taxon_id = match["taxon_id"][0]
                mappings.append({
                    "aphis_name": species,
                    "scientific_name": scientific_name,
                    "taxon_id": taxon_id,
                    "match_type": match_type,
                })
            else:
                unmapped.append(f"{species} -> {scientific_name} (not in taxonomy)")

    print(f"Mapped {len(mappings)} species")
    print(f"Unmapped: {len(unmapped)}")

    if unmapped:
        print("\nUnmapped species (top 20):")
        # Count occurrences
        unmapped_counts = aphis_df.filter(
            pl.col("Bird Species").is_in(unmapped)
        ).group_by("Bird Species").len().sort("len", descending=True)
        print(unmapped_counts.head(20))

    return pl.DataFrame(mappings)


def main():
    print("Loading APHIS data...")
    aphis = load_aphis_data()
    print(f"  {len(aphis):,} detection records")

    print("\nLoading taxonomy...")
    taxonomy = load_taxonomy()

    print("\nMapping species...")
    species_mapping = map_species(aphis, taxonomy)

    # Join mapping to APHIS data
    print("\nAggregating detections by species...")
    aphis_with_taxon = aphis.join(
        species_mapping.select(["aphis_name", "taxon_id", "scientific_name"]),
        left_on="Bird Species",
        right_on="aphis_name",
        how="left"
    )

    # Aggregate by species
    detection_counts = (
        aphis_with_taxon
        .filter(pl.col("taxon_id").is_not_null())
        .group_by(["taxon_id", "scientific_name"])
        .agg([
            pl.len().alias("detection_count"),
            pl.col("State").n_unique().alias("states_detected"),
            pl.col("Date Detected").min().alias("first_detection"),
            pl.col("Date Detected").max().alias("last_detection"),
        ])
        .sort("detection_count", descending=True)
    )

    print(f"\n{len(detection_counts)} species with mapped detections")
    print("\nTop 20 species by detection count:")
    print(detection_counts.head(20))

    # Write outputs
    print("\nWriting outputs...")

    # Species mapping
    species_mapping.write_csv(DATA_DIR / "aphis_species_mapping.tsv", separator="\t")
    print(f"  Wrote aphis_species_mapping.tsv")

    # Detection counts
    detection_counts.write_parquet(DATA_DIR / "aphis_detections.parquet")
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# detection_counts.write_csv(DATA_DIR / "aphis_detections.tsv", separator="\t")
    print(f"  Wrote aphis_detections.parquet")

    # Full APHIS data with taxon IDs
    aphis_with_taxon.write_parquet(DATA_DIR / "aphis_full.parquet")
    print(f"  Wrote aphis_full.parquet ({len(aphis_with_taxon):,} records)")

    # Summary stats
    mapped_records = aphis_with_taxon.filter(pl.col("taxon_id").is_not_null()).height
    print(f"\nSummary:")
    print(f"  Total APHIS records: {len(aphis):,}")
    print(f"  Mapped to taxonomy: {mapped_records:,} ({100*mapped_records/len(aphis):.1f}%)")
    print(f"  Unique species mapped: {len(detection_counts)}")


if __name__ == "__main__":
    main()
