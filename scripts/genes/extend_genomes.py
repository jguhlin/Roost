#!/usr/bin/env python3
"""Extend data/genomes/genomes.json from discovered candidate assemblies.

Usage:
  pixi run python scripts/genes/extend_genomes.py [--max N] [--min-papers N]
      [--level chromosome|any]

Merges candidate_species.json entries into the manifest (dedup by accession
and species; keeps existing entries untouched). Actual downloads happen via
fetch_genomes.py --set all.
"""

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
CANDIDATES = GENOME_DIR / "candidate_species.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=None, help="max entries to add")
    ap.add_argument("--min-papers", type=int, default=2,
                    help="min corpus papers (default 2)")
    ap.add_argument("--level", choices=["chromosome", "any"], default="any",
                    help="assembly level filter (default any)")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())["genomes"]
    cand = json.loads(CANDIDATES.read_text())["candidates"]
    have_acc = {g["accession"] for g in manifest}
    have_sci = {g["species"] for g in manifest}

    added = []
    for c in cand:
        if args.max and len(added) >= args.max:
            break
        if c["papers"] < args.min_papers:
            continue
        if args.level == "chromosome" and c["assembly_level"] != "Chromosome":
            continue
        if c["accession"] in have_acc or c["organism"] in have_sci:
            continue
        added.append({
            "accession": c["accession"],
            "species": c["organism"] or c.get("scientific_name", c["common"]),
            "common": c["common"],
            "role": f"corpus expansion ({c['papers']} papers, "
                    f"{c['assembly_level'].lower()} assembly)",
            "status": "pending",
        })
        have_acc.add(c["accession"])
        have_sci.add(c["organism"])

    if not added:
        print("nothing to add")
        return
    manifest.extend(added)
    MANIFEST.write_text(json.dumps({
        "set": "extended", "generated": date.today().isoformat(),
        "genomes": manifest,
    }, indent=1))
    print(f"added {len(added)} genomes → manifest now {len(manifest)} species")
    for a in added[:10]:
        print(f"  {a['accession']:16s} {a['species'][:34]:36s} {a['common'][:20]}")


if __name__ == "__main__":
    main()
