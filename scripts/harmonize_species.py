#!/usr/bin/env python3
"""
Species name harmonization for Roost.

Maps raw species names from detection data to NCBI taxonomy.
Handles:
- Case normalization
- Common name -> scientific name mapping
- Taxonomic synonyms (old names)
- Spelling variations

Usage:
    python scripts/harmonize_species.py
    python scripts/harmonize_species.py --show-unmapped
    python scripts/harmonize_species.py --rebuild-cache
"""

import argparse
import json
import re
from pathlib import Path
from typing import Optional

import polars as pl

DATA_DIR = Path("data")


# =============================================================================
# MANUAL MAPPINGS
# =============================================================================

# Common name -> Scientific name (NCBI canonical)
COMMON_NAME_MAP = {
    # Waterfowl
    "american widgeon": "Mareca americana",
    "american wigeon": "Mareca americana",
    "eurasian wigeon": "Mareca penelope",
    "american green-winged teal": "Anas crecca carolinensis",
    "green-winged teal": "Anas crecca",
    "blue-winged teal": "Spatula discors",
    "cinnamon teal": "Spatula cyanoptera",
    "northern shoveler": "Spatula clypeata",
    "gadwall": "Mareca strepera",
    "northern pintail": "Anas acuta",
    "mallard": "Anas platyrhynchos",
    "wood duck": "Aix sponsa",
    "muscovy duck": "Cairina moschata",
    "black-bellied whistling duck": "Dendrocygna autumnalis",
    "fulvous whistling duck": "Dendrocygna bicolor",
    "barrow's goldeneye": "Bucephala islandica",
    "common goldeneye": "Bucephala clangula",
    "bufflehead": "Bucephala albeola",
    "ruddy duck": "Oxyura jamaicensis",
    "redhead duck": "Aythya americana",
    "redhead": "Aythya americana",
    "canvasback": "Aythya valisineria",
    "lesser scaup": "Aythya affinis",
    "greater scaup": "Aythya marila",
    "ring-necked duck": "Aythya collaris",
    "harlequin duck": "Histrionicus histrionicus",
    "long-tailed duck": "Clangula hyemalis",
    "scoter": "Melanitta",
    "surf scoter": "Melanitta perspicillata",
    "white-winged scoter": "Melanitta deglandi",
    "black scoter": "Melanitta americana",
    "common eider": "Somateria mollissima",
    "king eider": "Somateria spectabilis",
    "steller's eider": "Polysticta stelleri",
    "spectacled eider": "Somateria fischeri",
    "hooded merganser": "Lophodytes cucullatus",
    "common merganser": "Mergus merganser",
    "red-breasted merganser": "Mergus serrator",

    # Geese
    "canada goose": "Branta canadensis",
    "cackling goose": "Branta hutchinsii",
    "snow goose": "Anser caerulescens",
    "ross's goose": "Anser rossii",
    "greater white-fronted goose": "Anser albifrons",
    "white-fronted goose": "Anser albifrons",
    "brant": "Branta bernicla",
    "brant goose": "Branta bernicla",
    "african goose": "Anser cygnoides",  # Domestic swan goose
    "greylag goose": "Anser anser",
    "graylag goose": "Anser anser",
    "barnacle goose": "Branta leucopsis",
    "bar-headed goose": "Anser indicus",

    # Swans
    "mute swan": "Cygnus olor",
    "trumpeter swan": "Cygnus buccinator",
    "tundra swan": "Cygnus columbianus",
    "whooper swan": "Cygnus cygnus",
    "black swan": "Cygnus atratus",

    # Shorebirds
    "black-bellied plover": "Pluvialis squatarola",
    "american golden-plover": "Pluvialis dominica",
    "semipalmated plover": "Charadrius semipalmatus",
    "killdeer": "Charadrius vociferus",
    "sanderling": "Calidris alba",
    "dunlin": "Calidris alpina",
    "red knot": "Calidris canutus",
    "western sandpiper": "Calidris mauri",
    "least sandpiper": "Calidris minutilla",
    "semipalmated sandpiper": "Calidris pusilla",
    "pectoral sandpiper": "Calidris melanotos",
    "american woodcock": "Scolopax minor",
    "wilson's snipe": "Gallinago delicata",
    "common snipe": "Gallinago gallinago",
    "willet": "Tringa semipalmata",
    "greater yellowlegs": "Tringa melanoleuca",
    "lesser yellowlegs": "Tringa flavipes",
    "spotted sandpiper": "Actitis macularius",
    "ruddy turnstone": "Arenaria interpres",
    "whimbrel": "Numenius phaeopus",
    "long-billed curlew": "Numenius americanus",
    "marbled godwit": "Limosa fedoa",
    "hudsonian godwit": "Limosa haemastica",
    "bar-tailed godwit": "Limosa lapponica",
    "avocet": "Recurvirostra americana",
    "american avocet": "Recurvirostra americana",
    "black-necked stilt": "Himantopus mexicanus",

    # Gulls
    "ring-billed gull": "Larus delawarensis",
    "herring gull": "Larus argentatus",
    "great black-backed gull": "Larus marinus",
    "glaucous gull": "Larus hyperboreus",
    "iceland gull": "Larus glaucoides",
    "lesser black-backed gull": "Larus fuscus",
    "california gull": "Larus californicus",
    "western gull": "Larus occidentalis",
    "laughing gull": "Leucophaeus atricilla",
    "franklin's gull": "Leucophaeus pipixcan",
    "bonaparte's gull": "Chroicocephalus philadelphia",
    "black-headed gull": "Chroicocephalus ridibundus",
    "mew gull": "Larus canus",
    "black-legged kittiwake": "Rissa tridactyla",

    # Terns
    "caspian tern": "Hydroprogne caspia",
    "royal tern": "Thalasseus maximus",
    "sandwich tern": "Thalasseus sandvicensis",
    "common tern": "Sterna hirundo",
    "arctic tern": "Sterna paradisaea",
    "forster's tern": "Sterna forsteri",
    "least tern": "Sternula antillarum",
    "black tern": "Chlidonias niger",

    # Pelicans
    "american white pelican": "Pelecanus erythrorhynchos",
    "brown pelican": "Pelecanus occidentalis",

    # Cormorants
    "double-crested cormorant": "Nannopterum auritum",
    "neotropic cormorant": "Nannopterum brasilianum",
    "pelagic cormorant": "Urile pelagicus",
    "great cormorant": "Phalacrocorax carbo",

    # Herons
    "great blue heron": "Ardea herodias",
    "great egret": "Ardea alba",
    "snowy egret": "Egretta thula",
    "little blue heron": "Egretta caerulea",
    "tricolored heron": "Egretta tricolor",
    "reddish egret": "Egretta rufescens",
    "cattle egret": "Bubulcus ibis",
    "green heron": "Butorides virescens",
    "black-crowned night-heron": "Nycticorax nycticorax",
    "yellow-crowned night-heron": "Nyctanassa violacea",
    "american bittern": "Botaurus lentiginosus",
    "least bittern": "Ixobrychus exilis",

    # Ibises and spoonbills
    "white ibis": "Eudocimus albus",
    "glossy ibis": "Plegadis falcinellus",
    "white-faced ibis": "Plegadis chihi",
    "roseate spoonbill": "Platalea ajaja",

    # Storks
    "wood stork": "Mycteria americana",
    "american wood stork": "Mycteria americana",

    # Cranes
    "sandhill crane": "Antigone canadensis",
    "whooping crane": "Grus americana",
    "african crowned crane": "Balearica regulorum",
    "grey crowned crane": "Balearica regulorum",
    "blue crane": "Grus paradisea",

    # Rails
    "american coot": "Fulica americana",
    "common moorhen": "Gallinula chloropus",
    "common gallinule": "Gallinula galeata",
    "purple gallinule": "Porphyrio martinica",
    "virginia rail": "Rallus limicola",
    "clapper rail": "Rallus crepitans",
    "king rail": "Rallus elegans",
    "sora": "Porzana carolina",

    # Raptors
    "bald eagle": "Haliaeetus leucocephalus",
    "golden eagle": "Aquila chrysaetos",
    "red-tailed hawk": "Buteo jamaicensis",
    "red-shouldered hawk": "Buteo lineatus",
    "cooper's hawk": "Accipiter cooperii",
    "sharp-shinned hawk": "Accipiter striatus",
    "northern goshawk": "Accipiter gentilis",
    "american goshawk": "Accipiter atricapillus",
    "northern harrier": "Circus hudsonius",
    "osprey": "Pandion haliaetus",
    "peregrine falcon": "Falco peregrinus",
    "american kestrel": "Falco sparverius",
    "merlin": "Falco columbarius",
    "rough-legged hawk": "Buteo lagopus",
    "turkey vulture": "Cathartes aura",
    "black vulture": "Coragyps atratus",
    "barn owl": "Tyto alba",
    "great horned owl": "Bubo virginianus",
    "snowy owl": "Bubo scandiacus",
    "barred owl": "Strix varia",
    "short-eared owl": "Asio flammeus",
    "long-eared owl": "Asio otus",
    "great gray owl": "Strix nebulosa",

    # Seabirds
    "black guillemot": "Cepphus grylle",
    "common murre": "Uria aalge",
    "thick-billed murre": "Uria lomvia",
    "razorbill": "Alca torda",
    "atlantic puffin": "Fratercula arctica",
    "horned puffin": "Fratercula corniculata",
    "tufted puffin": "Fratercula cirrhata",
    "pigeon guillemot": "Cepphus columba",
    "cassin's auklet": "Ptychoramphus aleuticus",
    "northern gannet": "Morus bassanus",
    "brown booby": "Sula leucogaster",
    "magnificent frigatebird": "Fregata magnificens",
    "arctic skua": "Stercorarius parasiticus",
    "parasitic jaeger": "Stercorarius parasiticus",
    "pomarine jaeger": "Stercorarius pomarinus",
    "long-tailed jaeger": "Stercorarius longicaudus",

    # Grebes
    "pied-billed grebe": "Podilymbus podiceps",
    "horned grebe": "Podiceps auritus",
    "eared grebe": "Podiceps nigricollis",
    "black-necked grebe": "Podiceps nigricollis",
    "western grebe": "Aechmophorus occidentalis",
    "clark's grebe": "Aechmophorus clarkii",
    "red-necked grebe": "Podiceps grisegena",

    # Loons
    "common loon": "Gavia immer",
    "red-throated loon": "Gavia stellata",
    "pacific loon": "Gavia pacifica",
    "yellow-billed loon": "Gavia adamsii",

    # Gamebirds
    "wild turkey": "Meleagris gallopavo",
    "ring-necked pheasant": "Phasianus colchicus",
    "greater prairie-chicken": "Tympanuchus cupido",
    "lesser prairie-chicken": "Tympanuchus pallidicinctus",
    "sharp-tailed grouse": "Tympanuchus phasianellus",
    "ruffed grouse": "Bonasa umbellus",
    "spruce grouse": "Canachites canadensis",
    "dusky grouse": "Dendragapus obscurus",
    "sooty grouse": "Dendragapus fuliginosus",
    "greater sage-grouse": "Centrocercus urophasianus",
    "northern bobwhite": "Colinus virginianus",
    "california quail": "Callipepla californica",
    "gambel's quail": "Callipepla gambelii",
    "scaled quail": "Callipepla squamata",
    "mountain quail": "Oreortyx pictus",
    "willow ptarmigan": "Lagopus lagopus",
    "rock ptarmigan": "Lagopus muta",
    "white-tailed ptarmigan": "Lagopus leucura",

    # Pigeons and doves
    "rock pigeon": "Columba livia",
    "rock dove": "Columba livia",
    "mourning dove": "Zenaida macroura",
    "white-winged dove": "Zenaida asiatica",
    "eurasian collared-dove": "Streptopelia decaocto",
    "common ground-dove": "Columbina passerina",

    # Crows and ravens
    "american crow": "Corvus brachyrhynchos",
    "fish crow": "Corvus ossifragus",
    "common raven": "Corvus corax",
    "american magpie": "Pica hudsonia",
    "black-billed magpie": "Pica hudsonia",
    "blue jay": "Cyanocitta cristata",
    "steller's jay": "Cyanocitta stelleri",

    # Parrots (captive/escaped)
    "african gray parrot": "Psittacus erithacus",
    "african grey parrot": "Psittacus erithacus",

    # Passerines
    "european starling": "Sturnus vulgaris",
    "common grackle": "Quiscalus quiscula",
    "boat-tailed grackle": "Quiscalus major",
    "great-tailed grackle": "Quiscalus mexicanus",
    "red-winged blackbird": "Agelaius phoeniceus",
    "yellow-headed blackbird": "Xanthocephalus xanthocephalus",
    "brown-headed cowbird": "Molothrus ater",
    "house sparrow": "Passer domesticus",
    "american robin": "Turdus migratorius",
    "house finch": "Haemorhous mexicanus",

    # European species
    "mute swan": "Cygnus olor",
    "greylag goose": "Anser anser",
    "canada goose": "Branta canadensis",
    "black-headed gull": "Chroicocephalus ridibundus",
    "common buzzard": "Buteo buteo",
    "buzzard": "Buteo buteo",
    "eurasian sparrowhawk": "Accipiter nisus",
    "sparrowhawk": "Accipiter nisus",
    "common kestrel": "Falco tinnunculus",
    "kestrel": "Falco tinnunculus",
    "common pheasant": "Phasianus colchicus",
    "pheasant": "Phasianus colchicus",
    "eurasian coot": "Fulica atra",
    "common coot": "Fulica atra",
    "coot": "Fulica atra",
    "common moorhen": "Gallinula chloropus",
    "moorhen": "Gallinula chloropus",
    "eurasian curlew": "Numenius arquata",
    "curlew": "Numenius arquata",
    "eurasian oystercatcher": "Haematopus ostralegus",
    "oystercatcher": "Haematopus ostralegus",
    "northern lapwing": "Vanellus vanellus",
    "lapwing": "Vanellus vanellus",

    # UK/European common names
    "goosander": "Mergus merganser",
    "smew": "Mergellus albellus",
    "goldeneye": "Bucephala clangula",
    "wigeon": "Mareca penelope",
    "teal": "Anas crecca",
    "pochard": "Aythya ferina",
    "tufted duck": "Aythya fuligula",
    "shelduck": "Tadorna tadorna",
    "common shelduck": "Tadorna tadorna",
    "shoveler": "Spatula clypeata",
    "pintail": "Anas acuta",
    "jackdaw": "Corvus monedula",
    "eurasian jackdaw": "Corvus monedula",
    "magpie": "Pica pica",
    "eurasian magpie": "Pica pica",
    "carrion crow": "Corvus corone",
    "hooded crow": "Corvus cornix",
    "rook": "Corvus frugilegus",
    "little egret": "Egretta garzetta",
    "grey heron": "Ardea cinerea",
    "gray heron": "Ardea cinerea",
    "white stork": "Ciconia ciconia",
    "black stork": "Ciconia nigra",
    "spoonbill": "Platalea leucorodia",
    "eurasian spoonbill": "Platalea leucorodia",
    "common scoter": "Melanitta nigra",
    "velvet scoter": "Melanitta fusca",
    "european turtle dove": "Streptopelia turtur",
    "turtle dove": "Streptopelia turtur",
    "eurasian collared dove": "Streptopelia decaocto",
    "collared dove": "Streptopelia decaocto",
    "stock dove": "Columba oenas",
    "woodpigeon": "Columba palumbus",
    "wood pigeon": "Columba palumbus",

    # More US species
    "eastern screech owl": "Megascops asio",
    "western screech owl": "Megascops kennicottii",
    "harris hawk": "Parabuteo unicinctus",
    "harris's hawk": "Parabuteo unicinctus",
    "greater sage grouse": "Centrocercus urophasianus",
    "green winged teal": "Anas crecca",
    "green-winged teal": "Anas crecca",
    "american green-winged teal": "Anas crecca",  # A. crecca carolinensis
    "bufflehead duck": "Bucephala albeola",
    "cackling geese": "Branta hutchinsii",
    "brazilian teal": "Amazonetta brasiliensis",

    # South American species
    "chimango caracara": "Phalcoboenus chimango",
    "guanay cormorant": "Leucocarbo bougainvillii",

    # African species
    "charadrius pallidus": "Anarhynchus pallidus",  # plover genus move
    "charadrius nivosus": "Anarhynchus nivosus",   # snowy plover genus move

    # Generic fallbacks: single generic words resolve to NO species.
    # Genus-level strings used to leak through and attach detections to an
    # arbitrary species of the genus ("Crane" -> Whooping crane,
    # "Duck" -> Northern pintail, "Owl" -> Tawny owl, "Gull" -> Herring
    # gull...). Keep only names that genuinely denote one species.
    "goshawk": "Accipiter gentilis",
}

# Taxonomic synonyms: old name -> current NCBI name
TAXONOMIC_SYNONYMS = {
    # Case fixes and common variations
    "accipiter gentilis": "Astur gentilis",  # goshawk genus move (was a no-op case fix)
    "corvus monedula": "Coloeus monedula",  # Jackdaw moved to Coloeus

    # Ducks - genus changes
    "anas clypeata": "Spatula clypeata",
    "anas discors": "Spatula discors",
    "anas cyanoptera": "Spatula cyanoptera",
    "anas strepera": "Mareca strepera",
    "anas americana": "Mareca americana",
    "anas penelope": "Mareca penelope",
    "anas rhynchotis": "Spatula rhynchotis",
    "anas versicolor": "Spatula versicolor",

    # Cormorants
    "phalacrocorax auritus": "Nannopterum auritum",
    "phalacrocorax brasilianus": "Nannopterum brasilianum",
    "phalacrocorax pelagicus": "Urile pelagicus",

    # Cranes
    "grus canadensis": "Antigone canadensis",

    # Hawks
    "accipiter cooperii": "Astur cooperii",

    # Egrets
    "casmerodius albus": "Ardea alba",

    # Geese
    "chen caerulescens": "Anser caerulescens",
    "chen rossii": "Anser rossii",

    # Gulls - recent genus splits
    "larus ridibundus": "Chroicocephalus ridibundus",
    "larus genei": "Chroicocephalus genei",
    "larus novaehollandiae": "Chroicocephalus novaehollandiae",
    "larus brunicephalus": "Chroicocephalus brunnicephalus",
    "larus ichthyaetus": "Ichthyaetus ichthyaetus",

    # Caracaras / falcons
    "caracara cheriway": "Caracara plancus",       # NCBI lumps crested caracara
    "daptrius chimango": "Milvago chimango",        # chimango caracara

    # Others
    "grus paradisea": "Anthropoides paradiseus",    # blue crane
    "gulosus aristotelis": "Phalacrocorax aristotelis",  # European shag
    "thalasseus acuflavidus": "Thalasseus sandvicensis",  # Cabot's tern lumped

    # Mammal synonyms / combinations (spillover hosts)
    "arctophoca australis": "Arctocephalus australis",   # junior synonym
    "otospermophilus tereticaudus": "Xerospermophilus tereticaudus",

    # Egyptian goose (important invasive in Europe)
    "alopochen aegyptiaca": "Alopochen aegyptiaca",
    "alopochen aegyptiacus": "Alopochen aegyptiaca",

    # Mammals (spillover hosts; common-name leaks in source data)
    "south america fur seal": "Arctocephalus australis",
    "south american fur seal": "Arctocephalus australis",
    "round-tailed ground squirrel": "Xerospermophilus tereticaudus",
    "western deer mouse": "Peromyscus sonoriensis",
    "japanese marten": "Martes melampus",
    "northern raccoon": "Procyon lotor",

    # Common names leaked into the scientific-name field
    "red junglefowl": "Gallus gallus",
    "water hen": "Gallinula chloropus",
    "wild duck": "Anas platyrhynchos",
}


# =============================================================================
# HARMONIZATION FUNCTIONS
# =============================================================================

def normalize_name(name: str) -> str:
    """Normalize a species name for matching."""
    if not name:
        return ""
    # Lowercase
    name = name.lower().strip()
    # Remove parenthetical taxonomic info like "(Cepphus Grylle)"
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def is_unidentified(name: str) -> bool:
    """Check if name indicates unidentified species."""
    if not name:
        return True
    normalized = normalize_name(name)
    unidentified_patterns = [
        "unidentified", "unknown", "unspecified", "undetermined",
        "not specified", "bird sp", "bird spp",
        "avian sp", "species", "(unidentified)", "sp.",
    ]
    return any(p in normalized for p in unidentified_patterns)


def looks_like_scientific_name(name: str) -> bool:
    """Check if name looks like a binomial scientific name."""
    if not name:
        return False
    parts = name.strip().split()
    if len(parts) < 2:
        return False
    # First word capitalized, second lowercase (typical binomial format)
    # But also handle all-caps or oddly cased entries
    return len(parts[0]) > 1 and len(parts[1]) > 1


def load_taxonomy() -> pl.DataFrame:
    """Load NCBI taxonomy: Aves base + mammal/other supplement."""
    tax_file = DATA_DIR / "aves_taxonomy.tsv"
    if not tax_file.exists():
        raise FileNotFoundError(f"Taxonomy not found: {tax_file}. Run: pixi run parse-taxonomy")
    tax = pl.read_csv(tax_file, separator="\t", schema_overrides={"taxon_id": pl.Int64})
    supp_file = DATA_DIR / "taxonomy_supplement.tsv"
    if supp_file.exists():
        supp = pl.read_csv(supp_file, separator="\t",
                           schema_overrides={"taxon_id": pl.Int64})
        common = [c for c in tax.columns if c in supp.columns]
        tax = pl.concat([tax.select(common), supp.select(common)], how="diagonal")
    return tax


def build_name_index(taxonomy: pl.DataFrame) -> dict[str, tuple[int, str]]:
    """
    Build a comprehensive name index from taxonomy.

    Returns dict mapping normalized name -> (taxon_id, canonical_name)
    """
    index = {}

    # Index scientific names
    for row in taxonomy.iter_rows(named=True):
        taxon_id = row["taxon_id"]
        sci_name = row.get("scientific_name", "") or row.get("name", "")
        common_name = row.get("common_name", "")

        if sci_name:
            # Scientific name (normalized)
            key = normalize_name(sci_name)
            if key and key not in index:
                index[key] = (taxon_id, sci_name)

            # NO genus-only indexing: a bare genus (DEFRA's "Numenius" for
            # 'Unspecified Curlew') used to resolve to the FIRST species in
            # the taxonomy table — arbitrary, false detections attached to
            # real species (2026-11-06: Numenius→americanus,
            # Buteo→albigula, Cygnus→atratus, 90 rows total). Genus-level
            # records must stay unresolved (null species, raw preserved).

        if common_name:
            key = normalize_name(common_name)
            if key and key not in index:
                index[key] = (taxon_id, sci_name)

    # Add manual common name mappings
    for common, scientific in COMMON_NAME_MAP.items():
        key = normalize_name(common)
        # Look up taxon_id for scientific name
        sci_key = normalize_name(scientific)
        if sci_key in index:
            index[key] = index[sci_key]
        else:
            # Scientific name not in taxonomy - skip but log
            pass

    # Add taxonomic synonyms
    for old_name, new_name in TAXONOMIC_SYNONYMS.items():
        old_key = normalize_name(old_name)
        new_key = normalize_name(new_name)
        if new_key in index:
            index[old_key] = index[new_key]

    return index


def harmonize_species_name(
    raw_name: str,
    name_index: dict[str, tuple[int, str]],
) -> Optional[tuple[int, str]]:
    """
    Harmonize a raw species name to NCBI taxonomy.

    Returns (taxon_id, scientific_name) or None if not found.
    """
    if not raw_name or is_unidentified(raw_name):
        return None

    normalized = normalize_name(raw_name)

    # Direct lookup
    if normalized in name_index:
        return name_index[normalized]

    # Try without hyphens
    no_hyphen = normalized.replace("-", " ")
    if no_hyphen in name_index:
        return name_index[no_hyphen]

    # Try with hyphens as single words
    with_hyphen = normalized.replace(" ", "-")
    if with_hyphen in name_index:
        return name_index[with_hyphen]

    # If looks like scientific name, try with swapped case
    if looks_like_scientific_name(raw_name):
        parts = raw_name.strip().split()
        # Proper case: Genus species
        proper = parts[0].capitalize() + " " + " ".join(p.lower() for p in parts[1:])
        proper_key = normalize_name(proper)
        if proper_key in name_index:
            return name_index[proper_key]

    # Try first two words only (in case of subspecies or extra info)
    words = normalized.split()
    if len(words) > 2:
        two_words = " ".join(words[:2])
        if two_words in name_index:
            return name_index[two_words]

    return None


def harmonize_dataframe(
    df: pl.DataFrame,
    name_index: dict[str, tuple[int, str]],
    species_col: str = "species_raw",
    taxon_col: str = "taxon_id",
    sci_name_col: str = "scientific_name",
) -> pl.DataFrame:
    """
    Add/update taxon_id and scientific_name columns based on harmonization.
    """
    # Build lookup results for all unique raw names
    unique_names = df[species_col].drop_nulls().unique().to_list()

    lookup_results = {}
    for name in unique_names:
        result = harmonize_species_name(name, name_index)
        if result:
            lookup_results[name] = result

    # Create mapping columns
    mapping_data = {
        species_col: list(lookup_results.keys()),
        f"{taxon_col}_new": [r[0] for r in lookup_results.values()],
        f"{sci_name_col}_new": [r[1] for r in lookup_results.values()],
    }
    mapping_df = pl.DataFrame(mapping_data)

    # Join with original dataframe
    result = df.join(mapping_df, on=species_col, how="left")

    # Update taxon_id where null
    if taxon_col in result.columns:
        result = result.with_columns(
            pl.when(pl.col(taxon_col).is_null())
              .then(pl.col(f"{taxon_col}_new"))
              .otherwise(pl.col(taxon_col))
              .alias(taxon_col)
        )
    else:
        result = result.rename({f"{taxon_col}_new": taxon_col})

    # Update scientific_name where null
    if sci_name_col in result.columns:
        result = result.with_columns(
            pl.when(pl.col(sci_name_col).is_null())
              .then(pl.col(f"{sci_name_col}_new"))
              .otherwise(pl.col(sci_name_col))
              .alias(sci_name_col)
        )
    else:
        result = result.rename({f"{sci_name_col}_new": sci_name_col})

    # Second pass: rows that still have no taxon_id — resolve via their
    # existing scientific_name (covers synonym combinations that arrived
    # from the source, e.g. Arctophoca australis, when species_raw was a
    # common name the lookup missed)
    if taxon_col in result.columns and sci_name_col in result.columns:
        sci_uniq = (result.filter(pl.col(taxon_col).is_null())
                          [sci_name_col].drop_nulls().unique().to_list())
        sci_lookup = {}
        for name in sci_uniq:
            hit = harmonize_species_name(name, name_index)
            if hit and hit[0] is not None:
                sci_lookup[name] = hit
        if sci_lookup:
            sci_map = pl.DataFrame({
                sci_name_col: list(sci_lookup.keys()),
                "_tid2": [r[0] for r in sci_lookup.values()],
            })
            result = (result.join(sci_map, on=sci_name_col, how="left")
                            .with_columns(
                                pl.when(pl.col(taxon_col).is_null() & pl.col("_tid2").is_not_null())
                                  .then(pl.col("_tid2"))
                                  .otherwise(pl.col(taxon_col))
                                  .alias(taxon_col))
                            .drop("_tid2"))
            # names get rewritten by the canonicalize pass via the new taxon_id

    # Clean up
    for col in [f"{taxon_col}_new", f"{sci_name_col}_new"]:
        if col in result.columns:
            result = result.drop(col)

    return result


# =============================================================================
# CANONICALIZATION (D112 audit guards)
# =============================================================================
# After alias/synonym mapping, scientific_name must be exactly what NCBI says
# for the assigned taxon_id — never a synonym, common-name leak, family
# placeholder, or trinomial. Generic single-word raw names ("Goose", "Gull")
# never resolve to a species.

STRICT_BINOMIAL = re.compile(r"^[A-Z][a-z]+ [a-z][a-z-]+$")
GENERIC_NAMES = {
    "crane", "duck", "hawk", "owl", "gull", "swan", "goose", "pigeon",
    "raptor", "shorebird", "waterfowl", "poultry", "bird",
}


def load_full_taxonomy_species() -> tuple[dict, dict]:
    """Parse the NCBI taxdump (all life, incl. mammals).

    Returns (canon_by_taxon, taxon_by_name):
      canon_by_taxon: taxon_id -> canonical name (None if not a strict binomial)
      taxon_by_name:  lowercase binomial -> taxon_id (strict binomials only)
    """
    tax_dir = DATA_DIR / "taxonomy"
    sci_names = {}  # taxon_id -> scientific name
    with open(tax_dir / "names.dmp") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t|\t")
            if len(parts) >= 4 and parts[3].startswith("scientific name"):
                sci_names[parts[0]] = parts[1]
    canon_by_taxon, taxon_by_name = {}, {}
    with open(tax_dir / "nodes.dmp") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t|\t")
            if len(parts) >= 3 and parts[2] == "species":
                tid_s, name = parts[0], sci_names.get(parts[0])
                if not name:
                    continue
                tid = int(tid_s)
                if STRICT_BINOMIAL.match(name):
                    canon_by_taxon[tid] = name
                    taxon_by_name[name.lower()] = tid
                else:
                    canon_by_taxon[tid] = None  # placeholder/hybrid "species"
    return canon_by_taxon, taxon_by_name


def canonicalize(df: pl.DataFrame, verbose: bool = True) -> pl.DataFrame:
    """Enforce species-level canonical names; report each fix class."""
    canon_by_taxon, taxon_by_name = load_full_taxonomy_species()
    if verbose:
        print(f"  Canonicalization: {len(canon_by_taxon):,} NCBI species loaded")

    n0_null = df.filter(pl.col("scientific_name").is_null()).height

    # 1) generic single-word raw names never resolve to a species
    raw_lc = pl.col("species_raw").str.strip_chars().str.to_lowercase()
    is_generic = raw_lc.is_in(sorted(GENERIC_NAMES)) & ~raw_lc.str.contains(" ")
    n_generic = df.filter(is_generic & pl.col("scientific_name").is_not_null()).height
    df = df.with_columns(
        pl.when(is_generic).then(None).otherwise(pl.col("taxon_id")).alias("taxon_id"),
        pl.when(is_generic).then(None).otherwise(pl.col("scientific_name")).alias("scientific_name"),
    )

    # 2) canonicalize by taxon_id (synonyms/common leaks → NCBI name;
    #    placeholder taxa like "Phasianidae sp." → dropped)
    uniq_tax = df["taxon_id"].drop_nulls().unique().to_list()
    canon_map = pl.DataFrame({
        "taxon_id": uniq_tax,
        "_canon": [canon_by_taxon.get(int(t)) for t in uniq_tax],
    })
    df = df.join(canon_map, on="taxon_id", how="left")
    n_placeholder = df.filter(pl.col("_canon").is_null() & pl.col("taxon_id").is_not_null()).height
    n_synonym = df.filter(
        pl.col("_canon").is_not_null()
        & pl.col("scientific_name").is_not_null()
        & (pl.col("scientific_name") != pl.col("_canon"))
    ).height
    df = df.with_columns(
        pl.when(pl.col("_canon").is_not_null())
          .then(pl.col("_canon"))
          .when(pl.col("taxon_id").is_not_null())
          .then(None)
          .otherwise(pl.col("scientific_name"))
          .alias("scientific_name"),
        pl.when(pl.col("_canon").is_null() & pl.col("taxon_id").is_not_null())
          .then(None)
          .otherwise(pl.col("taxon_id"))
          .alias("taxon_id"),
    ).drop("_canon")

    # 3) no taxon: trinomials → parent binomial (if known); other
    #    non-binomials ("Anser / Branta", common-name leaks) → null
    no_tax = df.filter(pl.col("taxon_id").is_null())
    uniq_sci = no_tax["scientific_name"].drop_nulls().unique().to_list()
    fixes = {}
    for s in uniq_sci:
        if STRICT_BINOMIAL.match(s):
            fixes[s] = (s, taxon_by_name.get(s.lower()))  # keep; link if known
            continue
        words = s.split()
        if len(words) >= 2:
            cand = f"{words[0]} {words[1]}"
            if STRICT_BINOMIAL.match(cand) and cand.lower() in taxon_by_name:
                fixes[s] = (cand, taxon_by_name[cand.lower()])  # trinomial → parent
                continue
        fixes[s] = (None, None)
    fix_df = pl.DataFrame({
        "scientific_name": pl.Series(list(fixes.keys()), dtype=pl.String),
        "_fix_name": pl.Series([v[0] for v in fixes.values()], dtype=pl.String),
        "_fix_taxon": pl.Series([v[1] for v in fixes.values()], dtype=pl.Int64),
        "_in_fixes": pl.Series([True] * len(fixes), dtype=pl.Boolean),
    }) if fixes else pl.DataFrame(
        schema={"scientific_name": pl.String, "_fix_name": pl.String,
                "_fix_taxon": pl.Int64, "_in_fixes": pl.Boolean}
    )
    before = df.height
    df = df.join(fix_df, on="scientific_name", how="left")
    n_trinomial = df.filter(pl.col("_in_fixes") & pl.col("_fix_name").is_not_null()
                            & (pl.col("_fix_name") != pl.col("scientific_name"))).height
    n_dropped = df.filter(pl.col("_in_fixes") & pl.col("_fix_name").is_null()).height
    in_fix = pl.col("_in_fixes").fill_null(False)
    df = df.with_columns(
        pl.when(in_fix)
          .then(pl.col("_fix_name"))          # may be null: the fix IS "drop"
          .otherwise(pl.col("scientific_name"))
          .alias("scientific_name"),
        pl.when(in_fix)
          .then(pl.coalesce([pl.col("_fix_taxon"), pl.col("taxon_id")]))
          .otherwise(pl.col("taxon_id"))
          .alias("taxon_id"),
    ).drop("_fix_name", "_fix_taxon", "_in_fixes")
    assert df.height == before, "canonicalize changed row count"

    n1_null = df.filter(pl.col("scientific_name").is_null()).height
    if verbose:
        print(f"    generic raws nulled:        {n_generic:,}")
        print(f"    placeholder taxa dropped:   {n_placeholder:,}")
        print(f"    synonyms canonicalized:     {n_synonym:,}")
        print(f"    trinomials → parent:        {n_trinomial:,}")
        print(f"    non-species names dropped:  {n_dropped:,}")
        print(f"    null-species: {n0_null:,} → {n1_null:,} ({100*n1_null/df.height:.1f}%)")

    # Final resolution sweep (2026-11-10): a genus-level tag must never
    # coexist with a resolved species — canonicalization may resolve a
    # species AFTER the ingest policy tagged the row's genus (e.g. canada
    # rows whose parsed column held a common name that looks like a genus:
    # 'Merlin'). Genus is only for the unresolved.
    if "genus" in df.columns and "scientific_name" in df.columns:
        n_both = df.filter(pl.col("genus").is_not_null()
                           & pl.col("scientific_name").is_not_null()).height
        if n_both:
            print(f"    genus cleared on resolved species: {n_both:,}")
            df = df.with_columns(
                pl.when(pl.col("scientific_name").is_not_null())
                  .then(None).otherwise(pl.col("genus")).alias("genus"))
    return df


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Species name harmonization")
    parser.add_argument("--show-unmapped", action="store_true", help="Show unmapped species")
    parser.add_argument("--rebuild-cache", action="store_true", help="Rebuild name index cache")
    parser.add_argument("--apply", action="store_true", help="Apply harmonization to detections")
    args = parser.parse_args()

    print("=" * 60)
    print("SPECIES NAME HARMONIZATION")
    print("=" * 60)

    # Load taxonomy
    print("\nLoading taxonomy...")
    taxonomy = load_taxonomy()
    print(f"  {len(taxonomy):,} taxa")

    # Build name index
    print("\nBuilding name index...")
    name_index = build_name_index(taxonomy)
    print(f"  {len(name_index):,} name variants indexed")
    print(f"  {len(COMMON_NAME_MAP)} manual common name mappings")
    print(f"  {len(TAXONOMIC_SYNONYMS)} taxonomic synonyms")

    # Load detections
    print("\nLoading detections...")
    detections_file = DATA_DIR / "detections_merged.parquet"
    if not detections_file.exists():
        print("  No detections file found. Run ingest-detections first.")
        return

    df = pl.read_parquet(detections_file)
    print(f"  {len(df):,} records")

    # Current mapping status
    if "taxon_id" in df.columns:
        currently_mapped = df.filter(pl.col("taxon_id").is_not_null()).height
        print(f"  Currently mapped: {currently_mapped:,} ({100*currently_mapped/len(df):.1f}%)")

    # Apply harmonization
    print("\nHarmonizing species names...")
    df_harmonized = harmonize_dataframe(df, name_index)

    # Canonicalization pass (audit guards: D112)
    print("\nCanonicalizing species names...")
    df_harmonized = canonicalize(df_harmonized)

    # New mapping status
    newly_mapped = df_harmonized.filter(pl.col("taxon_id").is_not_null()).height
    improvement = newly_mapped - currently_mapped if "taxon_id" in df.columns else newly_mapped
    print(f"  After harmonization: {newly_mapped:,} ({100*newly_mapped/len(df):.1f}%)")
    print(f"  Improvement: +{improvement:,} records")

    # Show unmapped if requested
    if args.show_unmapped:
        unmapped = df_harmonized.filter(pl.col("taxon_id").is_null())
        raw_names = unmapped["species_raw"].drop_nulls().unique().sort()
        print(f"\nUnmapped species ({len(raw_names)} unique names):")
        for name in raw_names.to_list()[:50]:
            count = unmapped.filter(pl.col("species_raw") == name).height
            print(f"  {name}: {count} records")
        if len(raw_names) > 50:
            print(f"  ... and {len(raw_names) - 50} more")

    # Apply if requested
    if args.apply:
        print("\nSaving harmonized data...")
        df_harmonized.write_parquet(DATA_DIR / "detections_merged.parquet")
        print(f"  Updated {detections_file}")

        # Rebuild phenotype table
        print("\nRebuilding phenotype table...")
        from build_phenotype_table import main as build_phenotype
        build_phenotype()
    else:
        print("\nRun with --apply to save changes")

    # Save mapping statistics
    stats = {
        "total_records": len(df),
        "mapped_before": currently_mapped if "taxon_id" in df.columns else 0,
        "mapped_after": newly_mapped,
        "improvement": improvement,
        "unmapped_count": len(df) - newly_mapped,
        "mapping_rate_before": currently_mapped / len(df) if "taxon_id" in df.columns else 0,
        "mapping_rate_after": newly_mapped / len(df),
        "common_name_mappings": len(COMMON_NAME_MAP),
        "synonym_mappings": len(TAXONOMIC_SYNONYMS),
        "total_index_entries": len(name_index),
    }

    print("\nMapping Statistics:")
    print(f"  Before: {stats['mapping_rate_before']*100:.1f}%")
    print(f"  After:  {stats['mapping_rate_after']*100:.1f}%")
    print(f"  Gap closed: {(stats['mapping_rate_after'] - stats['mapping_rate_before'])*100:.1f}%")


if __name__ == "__main__":
    main()
