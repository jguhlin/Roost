#!/usr/bin/env python3
"""
Build a comprehensive species index covering ALL Aves (~11,284 species) plus
mammals and other taxa from detections/WAHIS. This replaces the
detection-only index — species are searchable whether or not they have
detection data. Data layers (detections, genomes, papers, gene presence)
are attributes, not gates.

Output: web/public/data/species_index.json (comprehensive)
        web/public/data/species_wiki_supplement.json (paper-referenced extras)

Usage: pixi run python scripts/genes/build_species_index.py
"""

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent.parent
DATA = ROOT / "data"
WEB_DATA = ROOT / "web" / "public" / "data"

def main():
    # 1. Load full Aves taxonomy
    tax = pl.read_csv(DATA / "aves_taxonomy.tsv", separator="\t")
    print(f"Aves taxonomy: {tax.height} species")

    # 2. Load detection counts — detection_records = surveillance record
    #    count (rows); detection_count sums animals affected (flock sizes)
    #    and must never back the searchable `det` badge.
    try:
        det = pl.read_parquet(DATA / "species_profiles_detected.parquet")
        _col = ("detection_records" if "detection_records" in det.columns
                else "detection_count")
        det_counts = dict(zip(
            det["scientific_name"].to_list(),
            det[_col].to_list()
        ))
        det_species = set(det["scientific_name"].to_list())
    except Exception:
        det_counts, det_species = {}, set()
    print(f"Detected species: {len(det_species)}")

    # 3. Load genome availability + metadata (accession, assembly level)
    genome_meta = {}
    try:
        genomes = pl.read_parquet(DATA / "species_table.parquet")
        for row in genomes.filter(pl.col("has_genome") == True).iter_rows(named=True):
            genome_meta[row["scientific_name"]] = {
                "acc": row.get("accession"),
                "level": row.get("assembly_level"),
                "n50": row.get("scaffold_n50"),
                "ctg_n50": row.get("contig_n50"),
                "length": row.get("total_length"),
                "annot": row.get("has_annotation"),
                "annot_status": row.get("annotation_status"),
                "rep": row.get("is_representative"),
            }
    except Exception:
        pass
    genome_species = set(genome_meta)
    print(f"Species with genomes: {len(genome_species)}")

    # 4. Gene presence species
    presence_species = set()
    presence_path = DATA / "genes" / "gene_presence_v2.jsonl"
    if presence_path.exists():
        for line in presence_path.read_text().splitlines():
            if line.strip():
                try:
                    presence_species.add(json.loads(line)["species"])
                except (json.JSONDecodeError, KeyError):
                    pass
    print(f"Gene presence species: {len(presence_species)}")

    # 5. Species from detection data that are NOT birds (mammals via WAHIS etc)
    try:
        merged = pl.read_parquet(DATA / "detections_merged.parquet")
        all_det_species = set(merged["scientific_name"].drop_nulls().unique().to_list())
    except Exception:
        all_det_species = set()

    # Mammals and others: species in detections but not in Aves taxonomy.
    # Many are taxonomic splits/synonyms (old Anas → Mareca/Spatula) or
    # common names in the sci field — resolve via common-name and
    # genus-swap matching before falling back to an unresolved entry.
    aves_names = set(tax["scientific_name"].to_list())
    aves_lower = {s.lower() for s in aves_names}

    def norm(s: str) -> str:
        return " ".join(s.lower().split())

    tax_by_common = {}
    tax_by_epithet = defaultdict(list)
    for row in tax.iter_rows(named=True):
        sci = row["scientific_name"]
        if row.get("common_name"):
            tax_by_common[norm(row["common_name"])] = sci
        parts = sci.split()
        if len(parts) == 2:
            tax_by_epithet[parts[1].lower()].append((parts[0].lower(), sci))

    def resolve(sci: str):
        """Resolve a detection species name to the taxonomy equivalent."""
        if sci in aves_names or sci.lower() in aves_lower:
            return sci
        # common name in the sci field
        hit = tax_by_common.get(norm(sci))
        if hit:
            return hit
        # same species epithet, different genus (split/synonym) — unique only
        parts = sci.split()
        if len(parts) == 2:
            cands = [c for g, c in tax_by_epithet.get(parts[1].lower(), [])
                     if g != parts[0].lower()]
            if len(cands) == 1:
                return cands[0]
        return None

    # wiki supplement mammal flags — trusted non-Aves classification
    supp_path = WEB_DATA / "species_wiki_supplement.json"
    old_supp = json.loads(supp_path.read_text()) if supp_path.exists() else []
    known_mammals = {s["sci"].lower() for s in old_supp if s.get("mammal")}

    # taxonomy supplement (class column) — stable, pipeline-generated mammal set
    supp_tsv = DATA / "taxonomy_supplement.tsv"
    supp_mammals = set()
    if supp_tsv.exists():
        supp = pl.read_csv(supp_tsv, separator="\t",
                           schema_overrides={"taxon_id": pl.Int64})
        supp_mammals = set(
            supp.filter(pl.col("class") == "Mammalia")["scientific_name"].to_list()
        )

    non_aves = []
    unresolved = []
    merge_counts = defaultdict(int)  # resolved sci → detection count to merge
    for sci in sorted(all_det_species):
        resolved = resolve(sci)
        if resolved:
            if resolved != sci:
                merge_counts[resolved] += det_counts.get(sci, 0)
            continue
        if sci.lower() in known_mammals or sci in supp_mammals:
            non_aves.append(sci)
        else:
            unresolved.append(sci)
    print(f"Non-Aves species in detections: {len(non_aves)} mammals, {len(unresolved)} unresolved")
    if merge_counts:
        print(f"  synonym-merged: {len(merge_counts)} species (e.g. "
              f"{list(merge_counts)[:3]})")

    # 6b. Common names from wiki supplement (for mammals etc.)
    # (old_supp loaded above for mammal flags)

    # 7. Build comprehensive index
    def genome_fields(sci):
        gm = genome_meta.get(sci)
        if not gm:
            return {"has_genome": sci in genome_species}
        out = {
            "has_genome": True,
            "genome_acc": gm["acc"],
            "genome_level": gm["level"],
            "genome_n50": gm["n50"],
        }
        if gm.get("ctg_n50") is not None:
            out["genome_ctg_n50"] = gm["ctg_n50"]
        if gm.get("length") is not None:
            out["genome_len"] = gm["length"]
        if gm.get("annot") is not None:
            out["genome_annot"] = bool(gm["annot"])
        if gm.get("annot_status"):
            out["genome_annot_status"] = gm["annot_status"]
        if gm.get("rep") is not None:
            out["genome_rep"] = bool(gm["rep"])
        return out

    entries = []
    for row in tax.iter_rows(named=True):
        sci = row["scientific_name"]
        com = row.get("common_name") or ""
        entries.append({
            "id": row.get("taxon_id"),
            "sci": sci,
            "com": com,
            "ord": row.get("order"),
            "fam": row.get("family"),
            "det": det_counts.get(sci, 0) + merge_counts.get(sci, 0),
            "iucn": None,
            **genome_fields(sci),
            "has_presence": sci in presence_species,
        })

    # Add non-Aves mammals from detections (wiki-confirmed only)
    for sci in sorted(non_aves):
        com = ""
        # Try to get common name from old supplement
        for s in old_supp:
            if s.get("sci", "").lower() == sci.lower():
                com = s.get("com", "")
                break
        entries.append({
            "id": None,
            "sci": sci,
            "com": com,
            "ord": "Mammalia" if sci not in aves_names else None,
            "fam": None,
            "det": det_counts.get(sci, 0),
            "iucn": None,
            **genome_fields(sci),
            "has_presence": sci in presence_species,
            "mammal": True,
        })

    # Unresolved detection species — keep searchable but unclassified
    for sci in sorted(unresolved):
        com = ""
        for s in old_supp:
            if s.get("sci", "").lower() == sci.lower():
                com = s.get("com", "")
                break
        entries.append({
            "id": None, "sci": sci, "com": com, "ord": None, "fam": None,
            "det": det_counts.get(sci, 0), "iucn": None,
            **genome_fields(sci),
            "has_presence": sci in presence_species,
            "unresolved": True,
        })

    # Also add mammals from WAHIS calls that have scientific names
    wahis_species = presence_species - aves_names - set(non_aves) - set(unresolved)
    for sci in sorted(wahis_species):
        entries.append({
            "id": None, "sci": sci, "com": "", "ord": None, "fam": None,
            "det": 0, "iucn": None,
            "has_genome": False, "has_presence": True,
        })

    # Write
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / "species_index.json").write_text(json.dumps(entries, indent=None, separators=(",", ":")))

    n_detected = sum(1 for e in entries if e["det"] > 0)
    n_genomes = sum(1 for e in entries if e.get("has_genome"))
    n_presence = sum(1 for e in entries if e.get("has_presence"))
    n_mammals = sum(1 for e in entries if e.get("mammal"))

    print(f"\nComprehensive species index: {len(entries)} entries")
    print(f"  Aves: {len(entries) - n_mammals}")
    print(f"  Mammals/others: {n_mammals}")
    print(f"  With detections: {n_detected}")
    print(f"  With genomes: {n_genomes}")
    print(f"  With gene presence: {n_presence}")
    # NOTE: species_breakdown.json is written by export_web_data.py (the
    # stats single-writer); this legacy builder no longer writes it.

    # Update the wiki supplement (only paper-referenced species NOT in the comprehensive index)
    all_sci_lower = {e["sci"].lower() for e in entries}
    new_supp = [s for s in old_supp if s.get("sci", "").lower() not in all_sci_lower]
    (WEB_DATA / "species_wiki_supplement.json").write_text(json.dumps(new_supp, indent=1))
    print(f"  Wiki supplement (non-taxonomy extras): {len(new_supp)}")


if __name__ == "__main__":
    main()
