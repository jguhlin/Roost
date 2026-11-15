#!/usr/bin/env python3
"""
Prepare per-genome assets for the igv.js genome browser (D34).

Per genome:
  1. Re-run getorf (identical params to the pipeline) — deterministic
     ordinals recover the ORF ID → genomic coordinate map from deflines
     like `>NC_044302.2_118841 [6985738 - 6985936] (reverse)`
  2. Write genome.fna.fai (pure-python faidx)
  3. Stage symlinks into web/public/data/genomes/{acc}/ for igv.js
     (genome.fna is served with HTTP range requests via the .fai index —
     browsers only fetch the viewed region, never the whole file)

Usage: pixi run python scripts/genes/prepare_igv.py [--acc GCF_x]
"""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOMES_DIR = ROOT / "data" / "genomes"
WEB_GENOMES = ROOT / "web" / "public" / "data" / "genomes"
BIN = ROOT / ".pixi" / "envs" / "default" / "bin"

COORDS_RE = re.compile(r"^(\S+) \[(\d+) - (\d+)\](.*)$")


def faidx(fna: Path):
    """Write a .fai index (name, length, offset, linebases, linewidth)."""
    out = []
    name = None
    length = offset = 0
    linebases = linewidth = None
    with open(fna, "rb") as f:
        pos = 0
        for line in f:
            if line.startswith(b">"):
                if name is not None:
                    out.append(f"{name}\t{length}\t{offset}\t{linebases}\t{linewidth}")
                name = line[1:].split()[0].decode()
                offset = pos + len(line)
                length = 0
            else:
                if linewidth is None or linebases is None:
                    linewidth = len(line)
                    linebases = len(line.rstrip(b"\r\n"))
                length += len(line.rstrip(b"\r\n"))
            pos += len(line)
    if name is not None:
        out.append(f"{name}\t{length}\t{offset}\t{linebases}\t{linewidth}")
    fna.with_suffix(".fna.fai").write_text("\n".join(out) + "\n")


def orf_coords(acc: str) -> int:
    """Re-run getorf, parse deflines → orf_coords.tsv (orf_id, contig, start, end, strand)."""
    gdir = GENOMES_DIR / acc
    fna = gdir / "genome.fna"
    tsv = gdir / "orf_coords.tsv"
    if tsv.exists() and tsv.stat().st_size > 100:
        return sum(1 for _ in open(tsv)) - 1

    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}
    with subprocess.Popen(
        [str(BIN / "getorf"), "-sequence", str(fna), "-outseq", "stdout",
         "-minsize", "90", "-find", "1"],
        stdout=subprocess.PIPE, text=True, env=env,
    ) as proc:
        n = 0
        with open(tsv, "w") as out:
            out.write("orf_id\tcontig\tstart\tend\tstrand\n")
            for line in proc.stdout:
                if not line.startswith(">"):
                    continue
                m = COORDS_RE.match(line[1:].rstrip())
                if not m:
                    continue
                orf_id, contig = m.group(1).split()[0], None
                # orf id = contig_ordinal (contig may contain underscores —
                # split on last _N)
                c, _, ordinal = orf_id.rpartition("_")
                strand = "-" if "reverse" in m.group(4) else "+"
                out.write(f"{orf_id}\t{c}\t{m.group(2)}\t{m.group(3)}\t{strand}\n")
                n += 1
        proc.wait()
    return n


def stage_web(acc: str):
    """Symlink genome.fna + .fai into web/public for igv.js range requests."""
    wdir = WEB_GENOMES / acc
    wdir.mkdir(parents=True, exist_ok=True)
    # Phase 5 (DATA_MATURATION): stage NOTHING here for the fasta path.
    # The browser serves reference sequence from genome.2bit (self-contained,
    # staged by genomes_to_2bit.sh); the plain-fasta fallback stays supported
    # in GenomeBrowser.svelte for custom deployments, but the default staging
    # ships 2bit + gff only — genome.fna (+.fai, +.gz) never leaves data/.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acc", default=None, help="single genome accession")
    args = ap.parse_args()

    genomes = json.loads((GENOMES_DIR / "genomes.json").read_text())["genomes"]
    for g in genomes:
        if g["status"] not in ("ok", "cached"):
            continue
        if args.acc and g["accession"] != args.acc:
            continue
        acc = g["accession"]
        print(f"{acc} ({g.get('common', g['species'])})…", flush=True)
        fna = GENOMES_DIR / acc / "genome.fna"
        if not fna.exists():
            print("  no genome.fna, skipping")
            continue
        if not fna.with_suffix(".fna.fai").exists():
            faidx(fna)
            print("  fai written")
        n = orf_coords(acc)
        print(f"  ORF coords: {n:,}")
        stage_web(acc)
        print("  staged for web")


if __name__ == "__main__":
    main()
