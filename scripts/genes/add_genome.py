#!/usr/bin/env python3
"""Add a local (non-NCBI) genome to the gene-presence pipeline.

For genomes that aren't publicly available (private assemblies, collaborators'
draft genomes, etc.). Sets up the directory structure, creates the BLAST
database, registers the genome in the manifest, and runs gene detection
against just this genome.

Usage:
    pixi run add-genome --species "Strigops habroptila" --common "kākāpō" \\
        --fasta /path/to/genome.fna [--taxon-id 2489341] \\
        [--gff /path/to/annotation.gff] [--accession LOCAL_kakapo_v1]

After this runs:
    pixi run export-all          # rebuild all web data including the new species
    pixi run verify-downloads    # confirm everything is consistent

The species will appear on the site with gene-presence calls, in the species
index, and (if the .2bit is built) in the genome browser.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
BLAST_BIN = ROOT / ".pixi" / "envs" / "default" / "bin"


def makeblastdb(fasta: Path, outdir: Path) -> bool:
    """Create a BLAST nucleotide database from a FASTA file."""
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(BLAST_BIN / "makeblastdb"),
        "-in", str(fasta),
        "-dbtype", "nucl",
        "-out", str(outdir / "genome"),
        "-title", "local genome",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        print(f"  ✗ makeblastdb failed: {r.stderr[:300]}")
        return False
    return True


def build_2bit(fasta: Path, out: Path) -> bool:
    """Convert FASTA to 2bit for the IGV genome browser."""
    script = ROOT / "scripts" / "genes" / "fa_to_2bit.py"
    if not script.exists():
        return False
    r = subprocess.run(
        [sys.executable, str(script), str(fasta), str(out)],
        capture_output=True, text=True, timeout=3600)
    return r.returncode == 0


def build_fai(fasta: Path) -> bool:
    """Write a .fai index (samtools-style) for the FASTA."""
    fai = fasta.with_suffix(".fna.fai")
    try:
        records = []
        name = None
        length = offset = 0
        linebases = linewidth = None
        with open(fasta, "rb") as f:
            pos = 0
            for line in f:
                if line.startswith(b">"):
                    if name is not None:
                        records.append(f"{name}\t{length}\t{offset}\t{linebases}\t{linewidth}")
                    name = line[1:].split()[0].decode()
                    offset = pos + len(line)
                    length = 0
                    linebases = linewidth = None
                else:
                    if linewidth is None or linebases is None:
                        linewidth = len(line)
                        linebases = len(line.rstrip(b"\r\n"))
                    length += len(line.rstrip(b"\r\n"))
                pos += len(line)
            if name is not None:
                records.append(f"{name}\t{length}\t{offset}\t{linebases}\t{linewidth}")
        fai.write_text("\n".join(records) + "\n")
        return True
    except Exception as e:
        print(f"  ~ fai creation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Add a local genome to the pipeline")
    parser.add_argument("--species", required=True, help="scientific name (e.g. 'Strigops habroptila')")
    parser.add_argument("--common", required=True, help="common name (e.g. 'kākāpō')")
    parser.add_argument("--fasta", required=True, help="path to the genome FASTA file")
    parser.add_argument("--taxon-id", type=int, default=None,
                        help="NCBI taxon ID if known (optional)")
    parser.add_argument("--gff", default=None,
                        help="path to a GFF3 annotation file (optional)")
    parser.add_argument("--accession", default=None,
                        help="custom accession (default: LOCAL_{genus}_{species}_v1)")
    parser.add_argument("--skip-detection", action="store_true",
                        help="set up the genome but don't run gene detection (useful for testing)")
    args = parser.parse_args()

    fasta_path = Path(args.fasta).resolve()
    if not fasta_path.exists():
        print(f"✗ FASTA not found: {fasta_path}")
        sys.exit(1)

    # Generate an accession if not provided
    if not args.accession:
        genus, _, epithet = args.species.partition(" ")
        acc = f"LOCAL_{genus[:3].upper()}{epithet[:3].upper()}_v1"
    else:
        acc = args.accession

    genome_dir = GENOME_DIR / acc
    if genome_dir.exists():
        print(f"⚠ {acc} already exists at {genome_dir}")
        response = input("Overwrite? [y/N] ").strip().lower()
        if response != "y":
            sys.exit(0)
        shutil.rmtree(genome_dir)

    print(f"\n{'=' * 60}")
    print(f"Adding genome: {args.species} ({args.common})")
    print(f"Accession: {acc}")
    print(f"FASTA: {fasta_path}")
    print(f"{'=' * 60}\n")

    # 1. Set up the directory
    genome_dir.mkdir(parents=True, exist_ok=True)
    dest_fasta = genome_dir / "genome.fna"
    shutil.copy2(fasta_path, dest_fasta)
    print(f"  ✓ FASTA copied → {dest_fasta}")

    # 2. Create .fai index
    if build_fai(dest_fasta):
        print(f"  ✓ fai index created")

    # 3. Create BLAST database
    blastdb_dir = genome_dir / "blastdb"
    if makeblastdb(dest_fasta, blastdb_dir):
        print(f"  ✓ BLAST database created → {blastdb_dir}")
    else:
        print(f"  ✗ BLAST database failed — gene detection will not work")
        sys.exit(1)

    # 4. Create 2bit for the genome browser
    twobit = genome_dir / "genome.2bit"
    if build_2bit(dest_fasta, twobit):
        print(f"  ✓ 2bit created → {twobit} (genome browser enabled)")
    else:
        print(f"  ~ 2bit not created (genome browser will show 'not staged')")

    # 5. Copy GFF if provided
    if args.gff:
        gff_path = Path(args.gff).resolve()
        if gff_path.exists():
            shutil.copy2(gff_path, genome_dir / "annotation.gff")
            print(f"  ✓ GFF annotation copied")
        else:
            print(f"  ⚠ GFF not found: {gff_path}")

    # 6. Add to the manifest
    manifest = json.loads(MANIFEST.read_text())
    entry = {
        "accession": acc,
        "species": args.species,
        "common": args.common,
        "status": "ok",
        "source": "local",
        "added": date.today().isoformat(),
        "assembly_level": "unknown",
        "annotation": bool(args.gff),
    }
    if args.taxon_id:
        entry["taxon_id"] = args.taxon_id

    # Replace if same accession exists, else append
    manifest["genomes"] = [g for g in manifest["genomes"] if g["accession"] != acc]
    manifest["genomes"].append(entry)
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(f"  ✓ manifest updated ({len(manifest['genomes'])} genomes)")

    # 7. Run gene detection against this genome
    if not args.skip_detection:
        print(f"\n--- Gene presence detection ---")
        detect = ROOT / "scripts" / "genes" / "blast_presence.py"
        r = subprocess.run(
            [sys.executable, str(detect), "--genomes", acc],
            capture_output=False, timeout=14_400)  # 4 hour timeout
        if r.returncode != 0:
            print(f"\n  ⚠ Gene detection exited with code {r.returncode}")
            print(f"  The genome is set up; you can re-run detection manually:")
            print(f"  pixi run detect --genomes {acc}")
        else:
            print(f"\n  ✓ Gene detection complete")

    # 8. Next steps
    print(f"\n{'=' * 60}")
    print(f"Genome {acc} added successfully.")
    print(f"\nTo publish to the website:")
    print(f"  pixi run export-all")
    print(f"  pixi run verify-downloads")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
