#!/usr/bin/env python3
"""
Parse NCBI taxonomy dump and extract Aves taxonomy tree.
"""

import csv
from pathlib import Path
from collections import defaultdict

TAXONOMY_DIR = Path("data/taxonomy")
DATA_DIR = Path("data")

AVES_TAXID = 8782  # Class Aves


def parse_nodes(nodes_file: Path) -> dict:
    """Parse nodes.dmp to get parent-child relationships and ranks."""
    nodes = {}
    with open(nodes_file, "r") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            tax_id = int(parts[0])
            parent_id = int(parts[1])
            rank = parts[2]
            nodes[tax_id] = {"parent_id": parent_id, "rank": rank}
    return nodes


def parse_names(names_file: Path) -> dict:
    """Parse names.dmp to get scientific names and common names."""
    names = defaultdict(dict)
    with open(names_file, "r") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            tax_id = int(parts[0])
            name = parts[1]
            name_class = parts[3]

            if name_class == "scientific name":
                names[tax_id]["scientific_name"] = name
            elif name_class == "genbank common name":
                names[tax_id]["common_name"] = name
            elif name_class == "common name" and "common_name" not in names[tax_id]:
                names[tax_id]["common_name"] = name
    return dict(names)


def get_descendants(nodes: dict, root_taxid: int) -> set:
    """Get all descendant taxids of a given root."""
    descendants = set()
    to_process = [root_taxid]

    # Build children lookup for efficiency
    children = defaultdict(list)
    for tax_id, info in nodes.items():
        children[info["parent_id"]].append(tax_id)

    while to_process:
        current = to_process.pop()
        descendants.add(current)
        to_process.extend(children[current])

    return descendants


def get_lineage(nodes: dict, names: dict, tax_id: int) -> dict:
    """Get taxonomic lineage for a taxid."""
    lineage = {}
    current = tax_id
    while current != 1:  # 1 is root
        node = nodes.get(current)
        if not node:
            break
        rank = node["rank"]
        if rank in ["order", "family", "genus", "species", "subspecies"]:
            name_info = names.get(current, {})
            lineage[rank] = {
                "taxid": current,
                "name": name_info.get("scientific_name", ""),
            }
        current = node["parent_id"]
    return lineage


def main():
    print("Parsing nodes.dmp...")
    nodes = parse_nodes(TAXONOMY_DIR / "nodes.dmp")
    print(f"  Loaded {len(nodes):,} nodes")

    print("Parsing names.dmp...")
    names = parse_names(TAXONOMY_DIR / "names.dmp")
    print(f"  Loaded {len(names):,} named taxa")

    print(f"Finding Aves descendants (root: {AVES_TAXID})...")
    aves_taxids = get_descendants(nodes, AVES_TAXID)
    print(f"  Found {len(aves_taxids):,} Aves taxa")

    # Filter to species and subspecies ranks
    species_ranks = {"species", "subspecies"}
    aves_species = []

    for tax_id in aves_taxids:
        node = nodes.get(tax_id)
        if not node:
            continue
        if node["rank"] not in species_ranks:
            continue

        name_info = names.get(tax_id, {})
        lineage = get_lineage(nodes, names, tax_id)

        aves_species.append({
            "taxon_id": tax_id,
            "scientific_name": name_info.get("scientific_name", ""),
            "common_name": name_info.get("common_name", ""),
            "rank": node["rank"],
            "genus": lineage.get("genus", {}).get("name", ""),
            "family": lineage.get("family", {}).get("name", ""),
            "order": lineage.get("order", {}).get("name", ""),
        })

    print(f"  Filtered to {len(aves_species):,} species/subspecies")

    # Write output
    DATA_DIR.mkdir(exist_ok=True)
    output_file = DATA_DIR / "aves_taxonomy.tsv"

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f,
            fieldnames=["taxon_id", "scientific_name", "common_name", "rank", "genus", "family", "order"],
            delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(sorted(aves_species, key=lambda x: x["scientific_name"]))

    print(f"Wrote {output_file}")

    # Summary stats
    orders = set(s["order"] for s in aves_species if s["order"])
    families = set(s["family"] for s in aves_species if s["family"])
    species_only = [s for s in aves_species if s["rank"] == "species"]

    print(f"\nSummary:")
    print(f"  Orders: {len(orders)}")
    print(f"  Families: {len(families)}")
    print(f"  Species: {len(species_only)}")
    print(f"  Subspecies: {len(aves_species) - len(species_only)}")


if __name__ == "__main__":
    main()
