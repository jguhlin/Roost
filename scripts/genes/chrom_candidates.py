#!/usr/bin/env python3
"""List chromosome-level avian assemblies NOT yet in the manifest.

Queries NCBI for all Aves assemblies, keeps the best chromosome-level
assembly per species, and excludes anything already covered by
data/genomes/genomes.json (by accession or species name).

Writes data/genomes/chrom_todo.json ordered by (corpus papers desc, RefSeq).

Usage: pixi run python scripts/genes/chrom_candidates.py
"""

import json
import subprocess
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
TODO = GENOME_DIR / "chrom_todo.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())["genomes"]
    have_acc = {g["accession"] for g in manifest}
    have_sci = {g["species"] for g in manifest}

    # corpus paper counts for prioritisation
    wiki = json.loads((ROOT / "web" / "public" / "data" / "wiki_species.json").read_text())["species"]
    papers = {}
    sci_by_common = {}
    for s, v in wiki.items():
        papers[s] = v.get("paper_count") or 0
        if v.get("scientific_name"):
            sci_by_common[s] = v["scientific_name"]

    r = subprocess.run(
        ["pixi", "run", "datasets", "summary", "genome", "taxon", "Aves",
         "--as-json-lines"],
        capture_output=True, text=True, timeout=1800,
    )
    if r.returncode != 0:
        raise SystemExit(f"datasets query failed: {r.stderr[:200]}")

    best = {}  # species -> record
    total = 0
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        ai = d.get("assembly_info", {})
        if ai.get("assembly_level") != "Chromosome":
            continue
        acc = d.get("accession", "")
        org = ((ai.get("biosample") or {}).get("organism") or {}).get("organism_name") \
            or d.get("organism", {}).get("organism_name", "")
        if not acc or not org or acc in have_acc or org in have_sci:
            continue
        rec = {
            "accession": acc,
            "organism": org,
            "refseq": acc.startswith("GCF"),
            "release_date": (ai.get("release_date") or "")[:10],
            "annotated": bool(d.get("annotation_info", {}).get("release_name")),
        }
        score = (rec["refseq"], rec["annotated"], rec["release_date"])
        if org not in best or score > best[org][0]:
            best[org] = (score, rec)
        total += 1

    # attach corpus paper counts (common-name match or scientific-name match)
    todo = []
    for org, (_s, rec) in best.items():
        p = papers.get(org, 0)
        if not p:
            p = max((papers[c] for c, sci in sci_by_common.items() if sci == org), default=0)
        rec["papers"] = p
        rec["common"] = next((c for c, sci in sci_by_common.items() if sci == org), org)
        todo.append(rec)

    todo.sort(key=lambda x: (-x["papers"], not x["refseq"]))
    TODO.write_text(json.dumps(
        {"generated": date.today().isoformat(),
         "chromosome_level_candidates": len(todo),
         "aves_chromosome_records_seen": total,
         "candidates": todo}, indent=1))
    print(f"{len(todo)} chromosome-level candidates not yet covered -> {TODO.name}")
    for t in todo[:12]:
        print(f"  {t['papers']:3d}p {t['accession']:16s} {t['organism'][:36]}")


if __name__ == "__main__":
    main()
