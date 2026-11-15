#!/usr/bin/env python3
"""
Fetch validation-set genomes for the gene-presence pipeline (plan §Phase C).

Downloads genome-only FASTA per accession via the NCBI datasets CLI, records
a manifest (accession, level, annotation status, checksum), and prepares
makeblastdb-ready directories under data/genomes/{accession}/.

The validation set (V0): the four control genomes with chromosome-level
annotated assemblies. T1 (detected-species best assemblies) is generated
separately once V0 passes.

Usage: pixi run python scripts/genes/fetch_genomes.py [--set validation]
"""

import argparse
import hashlib
import json
import subprocess
import time
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"

# V0 validation set — controls for the evidence ladder (see plan §5)
VALIDATION_SET = [
    {"accession": "GCF_016699485.2", "species": "Gallus gallus", "common": "chicken",
     "role": "control: RIG-I known-loss; gold-standard annotation"},
    {"accession": "GCF_047663525.1", "species": "Anas platyrhynchos", "common": "Pekin duck",
     "role": "control: RIG-I present; anseriform comparator"},
    {"accession": "GCF_003957565.2", "species": "Taeniopygia guttata", "common": "zebra finch",
     "role": "control: passerine outgroup"},
    {"accession": "GCF_905368555.1", "species": "Meleagris gallopavo", "common": "turkey",
     "role": "control: galliform comparator"},
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def fetch_genome(entry: dict) -> dict:
    acc = entry["accession"]
    dest = GENOME_DIR / acc
    dest.mkdir(parents=True, exist_ok=True)
    fna = dest / "genome.fna"

    record = {**entry, "dir": str(dest), "status": "ok"}

    if fna.exists() and fna.stat().st_size > 10_000_000:
        record["status"] = "cached"
        record["size_mb"] = fna.stat().st_size // (1024 * 1024)
        return record
    # KEEP_GENOMES mode: decompress the retained zstd archive on demand
    zst = dest / "genome.fna.zst"
    if zst.exists() and not fna.exists():
        subprocess.run(["zstd", "-d", "-q", str(zst), "-o", str(fna)], check=True)
        record["status"] = "cached"
        record["size_mb"] = fna.stat().st_size // (1024 * 1024)
        return record

    zip_path = dest / "genome.zip"
    r = subprocess.run(
        ["pixi", "run", "datasets", "download", "genome", "accession", acc,
         "--include", "genome", "--filename", str(zip_path)],
        capture_output=True, text=True, timeout=1200,
    )
    if r.returncode != 0 or not zip_path.exists():
        record["status"] = "download_failed"
        record["error"] = r.stderr[:200]
        return record

    with zipfile.ZipFile(zip_path) as z:
        # exact genome.fna preferred; fallback = largest *.fna in package
        candidates = [n for n in z.namelist() if n.rsplit("/", 1)[-1] == "genome.fna"]
        if not candidates:
            candidates = sorted((n for n in z.namelist() if n.endswith(".fna")),
                                key=lambda n: z.getinfo(n).file_size, reverse=True)[:1]
        if candidates:
            with open(fna, "wb") as out:
                out.write(z.read(candidates[0]))
    zip_path.unlink(missing_ok=True)

    if not fna.exists():
        record["status"] = "no_fna_in_package"
        return record

    record["size_mb"] = fna.stat().st_size // (1024 * 1024)
    record["sha256"] = sha256(fna)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="all",
                        choices=["validation", "concern", "all"],
                        help="which genomes to fetch (default: all in manifest)")
    args = parser.parse_args()

    GENOME_DIR.mkdir(parents=True, exist_ok=True)

    if args.set == "all" and MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        entries = manifest["genomes"]
    elif args.set == "concern":
        manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"genomes": []}
        entries = [g for g in manifest["genomes"]
                   if g.get("role", "").startswith("conservation priority")]
    else:
        entries = VALIDATION_SET

    results = []
    for i, entry in enumerate(entries):
        rec = fetch_genome(entry)
        results.append(rec)
        print(f"  [{i+1}/{len(entries)}] {entry['accession']} {entry['common']:12s} "
              f"{rec['status']:10s} {rec.get('size_mb', 0)} MB", flush=True)
        time.sleep(1)

    # merge results back into manifest without clobbering other entries
    existing = {g["accession"]: g for g in json.loads(MANIFEST.read_text())["genomes"]} \
        if MANIFEST.exists() else {}
    for r in results:
        existing[r["accession"]] = {**existing.get(r["accession"], {}), **r}
    MANIFEST.write_text(json.dumps({
        "set": args.set, "generated": date.today().isoformat(),
        "genomes": list(existing.values()),
    }, indent=1))
    ok = sum(1 for r in results if r["status"] in ("ok", "cached"))
    print(f"\n{ok}/{len(results)} genomes ready → {MANIFEST}")


if __name__ == "__main__":
    main()
