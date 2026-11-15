#!/usr/bin/env python3
"""
Fetch and prepare phylogenetic tree data for the Roost web application.

Downloads the Ericson All Species tree from BirdTree.org (via VertLife) and merges
with species detection metadata from our database.

Output: web/public/data/phylogeny.json

Data source: https://birdtree.org/
Citation required: Jetz, W., G. H. Thomas, J. B. Joy, K. Hartmann, and A. O. Mooers. 2012.
                   The global diversity of birds in space and time. Nature 491:444-448

Usage:
    python scripts/fetch_phylogeny.py
    python scripts/fetch_phylogeny.py --download  # Re-download tree from BirdTree.org
"""

import argparse
import json
import re
import zipfile
import io
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

try:
    import httpx
except ImportError:
    httpx = None

# Paths
DATA_DIR = Path("data")
WEB_DATA_DIR = Path("web/public/data")
TREE_CACHE = DATA_DIR / "birdtree_ericson.tre"
TREE_ZIP_CACHE = DATA_DIR / "birdtree_ericson.zip"

# BirdTree.org / VertLife download URLs
BIRDTREE_URLS = [
    # Direct zip download
    "https://data.vertlife.org/birdtree/Stage2/EricsonStage2_0001_1000.zip",
    # Alternative: single tree file (may not exist)
    "https://data.vertlife.org/birdtree/Stage2/EricsonStage2_0001_1000/AllBirdsEricson1.tre",
]


def download_birdtree():
    """
    Download consensus tree from BirdTree.org via VertLife.

    BirdTree.org provides phylogenetic trees for ~10,000 bird species.
    We use the first tree from the Ericson backbone Stage 2 (full species) distribution.
    """
    if httpx is None:
        print("  Warning: httpx not available, cannot download")
        return None

    print("Downloading Ericson tree from BirdTree.org/VertLife...")

    # Try the zip file first
    zip_url = BIRDTREE_URLS[0]
    print(f"  Trying: {zip_url}")

    try:
        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            response = client.get(zip_url)
            response.raise_for_status()

            # Save the zip
            TREE_ZIP_CACHE.parent.mkdir(parents=True, exist_ok=True)
            TREE_ZIP_CACHE.write_bytes(response.content)
            print(f"  Downloaded zip ({len(response.content) / 1024 / 1024:.1f} MB)")

            # Extract the first tree file
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                # List files in zip
                tree_files = [n for n in zf.namelist() if n.endswith('.tre')]
                print(f"  Found {len(tree_files)} tree files in archive")

                if tree_files:
                    # Use the first tree (AllBirdsEricson1.tre typically)
                    tree_file = sorted(tree_files)[0]
                    print(f"  Extracting: {tree_file}")

                    tree_content = zf.read(tree_file).decode('utf-8')
                    TREE_CACHE.write_text(tree_content)
                    print(f"  Saved to {TREE_CACHE}")
                    return tree_content

    except Exception as e:
        print(f"  Failed to download zip: {e}")

    # Try direct tree file as fallback
    tree_url = BIRDTREE_URLS[1]
    print(f"  Trying direct: {tree_url}")

    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(tree_url)
            response.raise_for_status()

            TREE_CACHE.write_text(response.text)
            print(f"  Downloaded tree to {TREE_CACHE}")
            return response.text
    except Exception as e:
        print(f"  Failed: {e}")

    print("  Could not download tree, using sample tree")
    return None


def load_tree():
    """Load the Newick tree, downloading if necessary."""
    if TREE_CACHE.exists():
        print(f"Loading cached tree from {TREE_CACHE}")
        content = TREE_CACHE.read_text().strip()
        # Handle multiple trees in file (take first one)
        if '\n' in content:
            content = content.split('\n')[0].strip()
        return content

    # Try to download if httpx is available
    if httpx is not None:
        tree = download_birdtree()
        if tree:
            # Handle multiple trees
            if '\n' in tree:
                tree = tree.split('\n')[0].strip()
            return tree

    # If download fails or httpx not available, create a sample tree
    return create_sample_tree()


def create_sample_tree():
    """
    Create a sample phylogenetic tree for testing.

    This is a simplified tree showing major avian orders with representative
    species that have H5N1 detections in our database.
    """
    print("Creating sample phylogenetic tree...")

    # Simplified avian phylogeny focusing on orders with high detection counts
    sample_tree = """(
        (
            (
                (Cygnus_olor:0.05,Cygnus_cygnus:0.05,Cygnus_atratus:0.06):0.02,
                (Branta_canadensis:0.04,Branta_leucopsis:0.04,Branta_bernicla:0.04):0.02,
                (
                    Anser_anser:0.03,
                    Anser_caerulescens:0.03,
                    Anser_albifrons:0.03,
                    Anser_brachyrhynchus:0.03
                ):0.02,
                (
                    (Anas_platyrhynchos:0.02,Anas_crecca:0.02,Anas_acuta:0.02):0.01,
                    (Mareca_americana:0.02,Mareca_strepera:0.02,Mareca_penelope:0.02):0.01,
                    (Spatula_discors:0.02,Spatula_clypeata:0.02,Spatula_cyanoptera:0.02):0.01,
                    (Aythya_collaris:0.02,Aythya_fuligula:0.02,Aythya_affinis:0.02,Aythya_marila:0.02):0.01,
                    (Bucephala_albeola:0.02,Bucephala_clangula:0.02):0.01,
                    (Mergus_merganser:0.02,Mergus_serrator:0.02):0.01,
                    Aix_sponsa:0.03,
                    Oxyura_jamaicensis:0.03,
                    Somateria_mollissima:0.03
                ):0.02
            )Anseriformes:0.10,
            (
                (
                    Chroicocephalus_ridibundus:0.03,
                    (Larus_argentatus:0.02,Larus_marinus:0.02,Larus_fuscus:0.02,Larus_canus:0.02):0.01,
                    Rissa_tridactyla:0.03
                ):0.02,
                (Sterna_hirundo:0.03,Sterna_paradisaea:0.03):0.02,
                (Calidris_alpina:0.03,Calidris_alba:0.03,Calidris_mauri:0.03):0.02,
                Uria_aalge:0.04,
                Alca_torda:0.04,
                Fratercula_arctica:0.04
            )Charadriiformes:0.10
        ):0.05,
        (
            (
                (Haliaeetus_leucocephalus:0.03,Haliaeetus_albicilla:0.03):0.02,
                (Buteo_jamaicensis:0.03,Buteo_buteo:0.03,Buteo_lineatus:0.03,Buteo_lagopus:0.03):0.02,
                Aquila_chrysaetos:0.04,
                (Accipiter_cooperii:0.03,Accipiter_nisus:0.03,Accipiter_striatus:0.03):0.02,
                Circus_hudsonius:0.04,
                Pandion_haliaetus:0.04
            )Accipitriformes:0.08,
            (
                Coragyps_atratus:0.04,
                Cathartes_aura:0.04,
                Gymnogyps_californianus:0.05
            )Cathartiformes:0.08,
            (
                (Bubo_virginianus:0.03,Bubo_scandiacus:0.03,Bubo_bubo:0.03):0.02,
                (Strix_varia:0.03,Strix_aluco:0.03):0.02,
                Tyto_alba:0.04,
                Asio_otus:0.04
            )Strigiformes:0.08,
            (
                Falco_peregrinus:0.03,
                Falco_tinnunculus:0.03,
                Falco_sparverius:0.03
            )Falconiformes:0.08
        ):0.05,
        (
            (Morus_bassanus:0.04,Morus_capensis:0.04):0.02,
            (
                Pelecanus_erythrorhynchos:0.03,
                Pelecanus_crispus:0.03,
                Pelecanus_occidentalis:0.03
            ):0.02,
            (Phalacrocorax_carbo:0.03,Phalacrocorax_penicillatus:0.03):0.02,
            (
                Ardea_cinerea:0.03,
                Ardea_herodias:0.03,
                Ardea_alba:0.03,
                Nycticorax_nycticorax:0.03
            ):0.02
        )Pelecaniformes:0.10,
        (
            Columba_livia:0.04,
            Columba_palumbus:0.04,
            Streptopelia_decaocto:0.04,
            Zenaida_macroura:0.04
        )Columbiformes:0.10,
        (
            (Corvus_brachyrhynchos:0.03,Corvus_corax:0.03,Corvus_cornix:0.03,Corvus_corone:0.03):0.02,
            (Pica_pica:0.03,Pica_hudsonia:0.03):0.02,
            Cyanocitta_cristata:0.04
        )Passeriformes:0.10,
        (
            Phasianus_colchicus:0.04,
            Coturnix_coturnix:0.04,
            Meleagris_gallopavo:0.04,
            Pavo_cristatus:0.05
        )Galliformes:0.10,
        (
            (Grus_grus:0.03,Grus_americana:0.03,Grus_japonensis:0.03):0.02,
            Antigone_canadensis:0.04,
            Balearica_regulorum:0.04,
            (Fulica_atra:0.03,Fulica_americana:0.03):0.02
        )Gruiformes:0.10,
        (
            Phoenicopterus_roseus:0.04,
            Phoenicopterus_chilensis:0.04
        )Phoenicopteriformes:0.10,
        (
            Ciconia_ciconia:0.04,
            Mycteria_americana:0.04
        )Ciconiiformes:0.10,
        (
            (Podiceps_cristatus:0.03,Podiceps_nigricollis:0.03,Podiceps_auritus:0.03):0.02,
            Tachybaptus_ruficollis:0.04
        )Podicipediformes:0.10,
        (
            Gavia_immer:0.04,
            Gavia_stellata:0.04,
            Gavia_pacifica:0.04
        )Gaviiformes:0.10,
        (
            Fulmarus_glacialis:0.04,
            Puffinus_puffinus:0.04
        )Procellariiformes:0.10,
        (
            Spheniscus_demersus:0.05
        )Sphenisciformes:0.12,
        (
            Dromaius_novaehollandiae:0.06,
            Rhea_americana:0.06
        )Struthioniformes:0.12
    )Aves;"""

    # Clean up the tree (remove whitespace and newlines)
    sample_tree = re.sub(r'\s+', '', sample_tree)

    # Save the sample tree
    TREE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TREE_CACHE.write_text(sample_tree)

    print(f"  Created sample tree with major orders")
    return sample_tree


def extract_species_from_newick(newick):
    """Extract all species names from a Newick tree string."""
    # Match species names - handles various formats:
    # - Simple: Anas_platyrhynchos
    # - With underscores: Anas_platyrhynchos_platyrhynchos
    # - BirdTree format may have quotes or other characters

    # Remove any quoted strings first and extract their contents
    quoted_names = re.findall(r"'([^']+)'", newick)

    # Also match unquoted names (genus_species pattern)
    unquoted_names = re.findall(r'([A-Z][a-z]+_[a-z]+(?:_[a-z]+)?)', newick)

    # Combine and deduplicate
    all_names = set(quoted_names + unquoted_names)

    # Filter to likely species names (Genus_species format)
    species = []
    for name in all_names:
        # Clean the name
        clean_name = name.replace("'", "").strip()
        # Check if it looks like a species name
        if re.match(r'^[A-Z][a-z]+_[a-z]+', clean_name):
            species.append(clean_name)

    return list(set(species))


def load_species_metadata():
    """Load species metadata from our database."""
    if pl is None:
        print("  Warning: polars not available, using species_index.json")
        # Fall back to species_index.json
        index_file = WEB_DATA_DIR / "species_index.json"
        if index_file.exists():
            with open(index_file) as f:
                records = json.load(f)
            return {
                # Convert "Anas platyrhynchos" to "Anas_platyrhynchos"
                r["sci"].replace(" ", "_"): {
                    "taxon_id": r.get("id"),
                    "common_name": r.get("com"),
                    "order_name": r.get("ord") or None,
                    "family_name": r.get("fam") or None,
                    "detection_count": r.get("det", 0),
                }
                for r in records
            }
        return {}

    metadata = {}

    # Load species profiles (includes genome info directly)
    species_file = DATA_DIR / "species_profiles_detected.parquet"
    if species_file.exists():
        print(f"Loading species profiles from {species_file}")
        df = pl.read_parquet(species_file)

        for row in df.iter_rows(named=True):
            sci_name = row.get("scientific_name", "").replace(" ", "_")
            if sci_name:
                metadata[sci_name] = {
                    "taxon_id": row.get("taxon_id"),
                    "common_name": row.get("common_name"),
                    "order_name": row.get("order"),
                    "family_name": row.get("family"),
                    # surveillance RECORD count — raw detection_count sums
                    # animals affected (flock sizes) and would wreck the
                    # detections colour scale
                    "detection_count": row.get("detection_records",
                                                row.get("detection_count", 0)),
                    "has_genome": row.get("has_genome", False),
                    "assembly_level": row.get("assembly_level"),
                }

    # Also load ALL genomes (not just detected species) to enrich tree
    genome_file = DATA_DIR / "genomes.parquet"
    if genome_file.exists():
        print(f"Loading additional genome data from {genome_file}")
        df = pl.read_parquet(genome_file)
        genome_count = 0

        for row in df.iter_rows(named=True):
            # organism_name is the scientific name in genomes.parquet
            sci_name = row.get("organism_name", "").replace(" ", "_")
            if sci_name:
                if sci_name in metadata:
                    # Update existing entry
                    metadata[sci_name]["has_genome"] = True
                    if not metadata[sci_name].get("assembly_level"):
                        metadata[sci_name]["assembly_level"] = row.get("assembly_level")
                else:
                    # Add new entry for species with genome but no detections
                    metadata[sci_name] = {
                        "taxon_id": row.get("taxon_id"),
                        "common_name": row.get("organism_common_name"),
                        "detection_count": 0,
                        "has_genome": True,
                        "assembly_level": row.get("assembly_level"),
                    }
                genome_count += 1
        print(f"  Added/updated {genome_count} genome entries")

    # Load susceptibility scores
    susc_file = DATA_DIR / "susceptibility_scores.parquet"
    if susc_file.exists():
        print(f"Loading susceptibility data from {susc_file}")
        df = pl.read_parquet(susc_file)

        for row in df.iter_rows(named=True):
            sci_name = row.get("scientific_name", "").replace(" ", "_")
            if sci_name and sci_name in metadata:
                score = row.get("susceptibility_score", 0)
                # Classify into categories
                if score >= 0.7:
                    metadata[sci_name]["susceptibility"] = "High"
                elif score >= 0.4:
                    metadata[sci_name]["susceptibility"] = "Medium"
                else:
                    metadata[sci_name]["susceptibility"] = "Low"
                metadata[sci_name]["susceptibility_score"] = score

    return metadata


def build_phylogeny_json(newick, metadata):
    """Build the final phylogeny JSON structure."""
    # Extract species from tree
    tree_species = extract_species_from_newick(newick)
    print(f"  Found {len(tree_species)} species in tree")

    # Match with our metadata
    matched = 0
    with_detections = 0
    with_genomes = 0
    enriched_metadata = {}

    for species in tree_species:
        if species in metadata:
            enriched_metadata[species] = metadata[species]
            matched += 1
            if metadata[species].get("detection_count", 0) > 0:
                with_detections += 1
            if metadata[species].get("has_genome"):
                with_genomes += 1
        else:
            # Add placeholder entry for species in tree but not in our DB
            enriched_metadata[species] = {
                "taxon_id": None,
                "common_name": None,
                "detection_count": 0,
                "has_genome": False,
            }

    print(f"  Matched {matched}/{len(tree_species)} species with detection data")

    return {
        "newick": newick,
        "metadata": enriched_metadata,
        "stats": {
            "total_species": len(tree_species),
            "with_detections": with_detections,
            "with_genomes": with_genomes,
        },
        "citation": "Jetz, W., G. H. Thomas, J. B. Joy, K. Hartmann, and A. O. Mooers. 2012. The global diversity of birds in space and time. Nature 491:444-448",
        "source": "https://birdtree.org/",
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch and prepare phylogeny data")
    parser.add_argument("--download", action="store_true", help="Re-download tree from BirdTree.org")
    args = parser.parse_args()

    print("Roost Phylogeny Data Pipeline")
    print("=" * 40)

    # Ensure output directory exists
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Delete cache if re-downloading
    if args.download:
        if TREE_CACHE.exists():
            TREE_CACHE.unlink()
            print("Deleted cached tree, will re-download")
        if TREE_ZIP_CACHE.exists():
            TREE_ZIP_CACHE.unlink()
            print("Deleted cached zip")

    # Load or download tree
    print("\n=== Loading phylogenetic tree ===")
    newick = load_tree()
    print(f"  Tree length: {len(newick):,} characters")

    # Load metadata
    print("\n=== Loading species metadata ===")
    metadata = load_species_metadata()
    print(f"  Loaded {len(metadata)} species with metadata")

    # Build output
    print("\n=== Building phylogeny JSON ===")
    phylo_data = build_phylogeny_json(newick, metadata)

    # Write output
    output_file = WEB_DATA_DIR / "phylogeny.json"
    with open(output_file, "w") as f:
        json.dump(phylo_data, f, separators=(",", ":"))

    size_kb = output_file.stat().st_size / 1024
    print(f"\n  Wrote {output_file} ({size_kb:.1f} KB)")

    # Summary
    print("\n" + "=" * 40)
    print("Summary:")
    print(f"  Species in tree: {phylo_data['stats']['total_species']:,}")
    print(f"  With detections: {phylo_data['stats']['with_detections']}")
    print(f"  With genomes: {phylo_data['stats']['with_genomes']}")


if __name__ == "__main__":
    main()
