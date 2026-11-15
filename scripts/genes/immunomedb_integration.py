#!/usr/bin/env python3
"""
Map ImmunomeDB probe IDs (Ensembl chicken/finch proteins) to gene symbols via
UniProt ID mapping, then build the ImmunomeDB presence layer:
  - data/genes/immunomedb/probe_to_symbol.json
  - data/genes/immunomedb/immunomedb_presence.jsonl  (species × gene calls)

Usage: pixi run python scripts/genes/immunomedb_integration.py [--probes-only]
"""

import argparse
import gzip
import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
IMM = ROOT / "data" / "genes" / "immunomedb"
GFF_DIR = IMM / "b10k_annotation"
SAMPLE_SHEET = IMM / "data" / "Sample_sheet_363genomes_short_name.txt"
PROBE_MAP = IMM / "probe_to_symbol.json"
OUT_CALLS = IMM / "immunomedb_presence.jsonl"


def map_probes_via_uniprot(probes: list[str]) -> dict[str, str]:
    """Ensembl_Protein → UniProtKB → gene symbol, batches of 500."""
    mapped = {}
    with httpx.Client(timeout=180, headers={"User-Agent": "Roost/0.1"}) as c:
        for i in range(0, len(probes), 500):
            batch = probes[i:i + 500]
            r = c.post("https://rest.uniprot.org/idmapping/run",
                       data={"from": "Ensembl_Protein", "to": "UniProtKB",
                             "ids": ",".join(batch)})
            r.raise_for_status()
            job = r.json()["jobId"]
            for _ in range(60):
                time.sleep(3)
                s = c.get(f"https://rest.uniprot.org/idmapping/status/{job}")
                if s.json().get("jobStatus") == "FINISHED":
                    break
            else:
                print(f"  batch {i//500}: timeout")
                continue
            url = (f"https://rest.uniprot.org/idmapping/uniprotkb/results/stream/{job}"
                   "?format=tsv&fields=accession,gene_primary&size=500")
            r2 = c.get(url)
            for line in r2.text.strip().split("\n")[1:]:
                parts = line.split("\t")
                if len(parts) >= 3 and parts[2]:
                    mapped[parts[0]] = parts[2].split(";")[0].strip()
            print(f"  {len(mapped)}/{len(probes)} mapped", flush=True)
    return mapped


def parse_gff(path: Path):
    """Yield (probe_id, shift, midstop) per mRNA."""
    calls = []
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            f_ = line.rstrip("\n").split("\t")
            if len(f_) < 9 or f_[2] not in ("mRNA", "gene"):
                continue
            m = re.search(r"Source=([A-Z0-9]+)", f_[8])
            if not m:
                continue
            probe = m.group(1)
            shift = re.search(r"Shift=(\d+)", f_[8])
            midstop = re.search(r"MidStop=(\d+)", f_[8])
            calls.append({
                "probe": probe,
                "shift": int(shift.group(1)) if shift else 0,
                "midstop": int(midstop.group(1)) if midstop else 0,
            })
    return calls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probes-only", action="store_true")
    args = parser.parse_args()

    # 1. probe→symbol map (cached)
    if PROBE_MAP.exists():
        mapped = json.loads(PROBE_MAP.read_text())
        print(f"cached probe map: {len(mapped)}")
    else:
        probes = set()
        for gff in GFF_DIR.glob("*_immune.gff.gz"):
            with gzip.open(gff, "rt") as f:
                for line in f:
                    m = re.search(r"Source=([A-Z0-9]+)-D\d", line)
                    if m:
                        probes.add(m.group(1))
        probes = sorted(probes)
        print(f"{len(probes)} unique probes across {len(list(GFF_DIR.glob('*.gff.gz')))} species")
        mapped = map_probes_via_uniprot(probes)
        PROBE_MAP.write_text(json.dumps(mapped, indent=1))
        print(f"saved {len(mapped)} mappings → {PROBE_MAP}")

    if args.probes_only:
        return

    # 2. species metadata
    species_meta = {}
    lines = SAMPLE_SHEET.read_text().splitlines()
    header = lines[0].split("\t")
    for line in lines[1:]:
        f = line.split("\t")
        if len(f) >= 6:
            species_meta[f[0]] = {"latin": f[4], "common": f[5],
                                  "order": f[2], "family": f[3]}

    # 3. presence calls
    calls = []
    unmapped_probes = set()
    for gff in sorted(GFF_DIR.glob("*_immune.gff.gz")):
        code = gff.name.split("_")[0]
        meta = species_meta.get(code, {})
        for rec in parse_gff(gff):
            symbol = mapped.get(rec["probe"])
            if not symbol:
                unmapped_probes.add(rec["probe"])
                continue
            status = "ANNOTATED"
            if rec["midstop"] or rec["shift"]:
                status = "PSEUDOGENIZED"
            calls.append({
                "species_code": code,
                "latin_name": meta.get("latin", ""),
                "order": meta.get("order", ""),
                "gene_symbol": symbol,
                "status": status,
                "shift": rec["shift"],
                "midstop": rec["midstop"],
                "source": "immunomedb_b10k_2020",
                "source_vintage": "2020-B10K1",
                "method": "annotation",
            })

    with open(OUT_CALLS, "w") as f:
        for c in calls:
            f.write(json.dumps(c) + "\n")
    genes = {c["gene_symbol"] for c in calls}
    species = {c["species_code"] for c in calls}
    pseudos = sum(1 for c in calls if c["status"] == "PSEUDOGENIZED")
    print(f"\n{len(calls)} calls | {len(genes)} unique genes | "
          f"{len(species)} species | {pseudos} pseudogenized")
    if unmapped_probes:
        print(f"unmapped probes (no UniProt gene name): {len(unmapped_probes)}")


if __name__ == "__main__":
    main()
