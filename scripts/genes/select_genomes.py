#!/usr/bin/env python3
"""
Select and register target genomes for the gene-presence pipeline.

Priority tiers (user-directed):
  P0  NZ conservation species (kākāpō, takahē, kiwi, kea, …)
  P1  detected-species ∩ ImmunomeDB species (reconfirmation value, D17)
  P2  remaining detected species with assemblies

For each species: query NCBI datasets for assemblies, pick the best
(chromosome > scaffold; RefSeq GCF > GenBank GCA; annotated > not; newest),
and append to data/genomes/genomes.json for fetch_genomes.py.

Usage:
    pixi run python scripts/genes/select_genomes.py --tier nz [--add]
    pixi run python scripts/genes/select_genomes.py --species "Strigops habroptilus,..."
"""

import argparse
import json
import subprocess
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
IMM_SAMPLE = ROOT / "data" / "genes" / "immunomedb" / "data" / "Sample_sheet_363genomes_short_name.txt"

# P0 — NZ conservation priority (user direction 2026-08-31)
NZ_SPECIES = [
    ("Strigops habroptilus", "kakapo", "conservation priority — critically endangered, T2T genome exists"),
    ("Porphyrio hochstetteri", "takahē", "conservation priority — icon species"),
    ("Nestor notabilis", "kea", "conservation priority + ImmunomeDB species"),
    ("Nestor meridionalis", "kākā", "conservation priority"),
    ("Apteryx mantelli", "North Island brown kiwi", "conservation priority + ImmunomeDB (rowi kin)"),
    ("Apteryx rowi", "rowi", "conservation priority + ImmunomeDB"),
    ("Apteryx haastii", "great spotted kiwi", "conservation priority + ImmunomeDB"),
    ("Apteryx owenii", "little spotted kiwi", "conservation priority + ImmunomeDB"),
    ("Apteryx australis", "southern brown kiwi", "conservation priority + ImmunomeDB"),
    ("Megadyptes antipodes", "yellow-eyed penguin/hoiho", "conservation priority — HPAI-vaccination target"),
    ("Cyanoramphus novaezelandiae", "red-crowned kākāriki", "conservation priority"),
    ("Cyanoramphus auriceps", "yellow-crowned kākāriki", "conservation priority"),
    ("Gallirallus australis", "weka", "conservation priority"),
    ("Hymenolaimus malacorhynchos", "whio/blue duck", "conservation priority"),
    ("Anarhynchus frontalis", "wrybill", "conservation priority"),
    ("Petroica australis", "toutouwai/SI robin", "conservation priority"),
    ("Notiomystis cincta", "hihi/stitchbird", "conservation priority"),
]

LEVEL_RANK = {"Complete Genome": 0, "Chromosome": 1, "Scaffold": 2, "Contig": 3}


def datasets_json(*args):
    # datasets prints JSON by default for summary; --as-json is not a flag
    r = subprocess.run(["pixi", "run", "datasets", *args],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def best_assembly(species: str) -> dict | None:
    d = datasets_json("summary", "genome", "taxon", species)
    if not d:
        return None
    best, best_key = None, (99, 1, 9, "")
    for r in d.get("reports", []):
        acc = r.get("accession", "")
        ai = r.get("assembly_info", {})
        level = ai.get("assembly_level", "Contig")
        annot = 1 if r.get("annotation_info") else 0
        is_gcf = 0 if acc.startswith("GCF_") else 1
        date_str = ai.get("biosample", "") or ""
        key = (LEVEL_RANK.get(level, 9), is_gcf, -annot, acc)
        if key < best_key:
            best_key = key
            best = {
                "accession": acc, "species": r.get("organism", {}).get("organism_name", species),
                "common": "", "assembly_level": level,
                "annotated": bool(annot), "assembly_name": ai.get("assembly_name", ""),
            }
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=["nz"], default=None)
    parser.add_argument("--species", default=None, help="comma-separated latin names")
    parser.add_argument("--add", action="store_true", help="append selections to genomes.json")
    args = parser.parse_args()

    targets = []
    if args.tier == "nz":
        targets = NZ_SPECIES
    if args.species:
        for s in args.species.split(","):
            targets.append((s.strip(), "", "manual"))

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"genomes": []}
    existing = {g["accession"] for g in manifest["genomes"]}

    selections = []
    for latin, common, role in targets:
        best = best_assembly(latin)
        time.sleep(0.4)
        if not best:
            print(f"  ✗ {latin} — no assembly found")
            continue
        if best["accession"] in existing:
            print(f"  = {latin} — {best['accession']} already in manifest")
            continue
        best["common"] = common or best["species"]
        best["role"] = role
        selections.append(best)
        print(f"  ✓ {latin:30s} → {best['accession']} {best['assembly_level']:11s} "
              f"{'annot' if best['annotated'] else 'no-annot':9s} {best['assembly_name'][:26]}")

    if args.add and selections:
        manifest["genomes"].extend(selections)
        manifest["generated"] = date.today().isoformat()
        MANIFEST.write_text(json.dumps(manifest, indent=1))
        print(f"\nadded {len(selections)} genomes → {MANIFEST}")
    else:
        print(f"\n{len(selections)} selected (dry run — use --add to append)")


if __name__ == "__main__":
    main()
