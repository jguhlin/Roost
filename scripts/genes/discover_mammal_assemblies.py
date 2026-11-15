#!/usr/bin/env python3
"""Discover best NCBI assemblies for the infected mammal species.

For each species in /tmp/mammal_species.txt (species \t detections), query
NCBI datasets for its best assembly (RefSeq > chromosome > scaffold, newest).
Writes data/genomes/mammal_candidates.json.

Usage: pixi run python scripts/genes/discover_mammal_assemblies.py
"""

import json
import subprocess
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
LIST = Path("/tmp/mammal_species.txt")
OUT = GENOME_DIR / "mammal_candidates.json"


def best_assembly(records):
    best, best_score = None, None
    for d in records:
        ai = d.get("assembly_info", {})
        acc = d.get("accession", "")
        if not acc:
            continue
        level = ai.get("assembly_level", "")
        rec = {
            "accession": acc,
            "assembly_level": level,
            "refseq": acc.startswith("GCF"),
            "release_date": (ai.get("release_date") or "")[:10],
            "annotated": bool(d.get("annotation_info", {}).get("name")
                              or d.get("annotation_info", {}).get("release_name")),
        }
        score = (rec["refseq"], level == "Chromosome", rec["annotated"], rec["release_date"])
        if best_score is None or score > best_score:
            best, best_score = rec, score
    return best



def ena_has_assembly(sci: str) -> str | None:
    """Check ENA (EMBL-EBI) for assemblies NCBI may lack (DNA Zoo-era releases)."""
    import json as _json
    import urllib.parse as _up
    import urllib.request as _ur
    try:
        url = ("https://www.ebi.ac.uk/ena/portal/api/search?result=assembly"
               f"&query=scientific_name%3D%22{_up.quote(sci)}%22"
               "&format=json&fields=accession,assembly_level")
        with _ur.urlopen(url, timeout=20) as r:
            rows = _json.loads(r.read() or b"[]")
        return rows[0]["accession"] if rows else None
    except Exception:
        return None

def main():
    species = []
    for line in LIST.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            species.append((parts[0], int(parts[1])))
    print(f"{len(species)} mammal species to query")

    results = []
    for i, (sci, det) in enumerate(species):
        r = subprocess.run(
            ["pixi", "run", "datasets", "summary", "genome", "taxon", sci,
             "--as-json-lines"],
            capture_output=True, text=True, timeout=180)
        best = None
        if r.returncode == 0:
            recs = []
            for line in r.stdout.splitlines():
                try:
                    recs.append(json.loads(line))
                except Exception:
                    continue
            best = best_assembly(recs)
        if best:
            best.update({"species": sci, "detections": det})
            results.append(best)
            print(f"  [{i+1}/{len(species)}] {sci:34s} {best['accession']:16s} "
                  f"{best['assembly_level'][:4]:5s} ({det} det)", flush=True)
        else:
            print(f"  [{i+1}/{len(species)}] {sci:34s} — no assembly", flush=True)
        time.sleep(0.5)
        if (i + 1) % 10 == 0:
            OUT.write_text(json.dumps(
                {"generated": date.today().isoformat(), "partial": True,
                 "candidates": results}, indent=1))

    results.sort(key=lambda r: (-r["detections"], not r["refseq"]))
    OUT.write_text(json.dumps(
        {"generated": date.today().isoformat(), "candidates": results}, indent=1))
    chrom = sum(1 for r in results if r["assembly_level"] == "Chromosome")
    print(f"\n{len(results)}/{len(species)} have assemblies ({chrom} chromosome-level) -> {OUT.name}")


if __name__ == "__main__":
    main()
