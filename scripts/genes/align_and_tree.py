#!/usr/bin/env python3
"""
Align extracted protein sequences and build phylogenetic trees per gene.

Input:  data/genes/sequences_v2/{GENE}.faa (from extract_sequences.py)
Output: data/genes/alignments/{GENE}.aln.faa (MAFFT alignment)
        data/genes/trees/{GENE}.nwk (FastTree newick)
        data/genes/alignments/{GENE}_identity.tsv (pairwise identity matrix)

Usage: pixi run python scripts/genes/align_and_tree.py [--genes DDX58,ANP32A]
"""

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SEQ_DIR = ROOT / "data" / "genes" / "sequences_v2"
ALN_DIR = ROOT / "data" / "genes" / "alignments"
TREE_DIR = ROOT / "data" / "genes" / "trees"
BIN = ROOT / ".pixi/envs/default/bin"


def run_mafft(input_faa: Path, output_aln: Path) -> bool:
    r = subprocess.run(
        [str(BIN / "mafft"), "--auto", "--quiet", str(input_faa)],
        capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        return False
    output_aln.write_text(r.stdout)
    return True


def run_fasttree(aln_faa: Path, output_nwk: Path) -> bool:
    r = subprocess.run(
        [str(BIN / "FastTree"), "-quiet", "-wag", str(aln_faa)],
        capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        return False
    output_nwk.write_text(r.stdout)
    return True


def identity_matrix(aln_path: Path) -> str:
    """Compute pairwise identity from an aligned FASTA."""
    seqs = {}
    header, seq = None, []
    for line in aln_path.read_text().splitlines():
        if line.startswith(">"):
            if header and seq:
                seqs[header] = "".join(seq)
            header = line[1:].split("|")[0]  # species name only
            seq = []
        else:
            seq.append(line.strip())
    if header and seq:
        seqs[header] = "".join(seq)

    names = sorted(seqs.keys())
    lines = ["\t".join([""] + names)]
    for n1 in names:
        row = [n1]
        s1 = seqs[n1]
        for n2 in names:
            s2 = seqs[n2]
            matches = sum(1 for a, b in zip(s1, s2) if a == b and a != "-")
            aligned = sum(1 for a, b in zip(s1, s2) if a != "-" or b != "-")
            ident = 100 * matches / aligned if aligned else 0
            row.append(f"{ident:.1f}")
        lines.append("\t".join(row))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--genes", default=None)
    args = parser.parse_args()

    wanted = set(args.genes.split(",")) if args.genes else None
    ALN_DIR.mkdir(parents=True, exist_ok=True)
    TREE_DIR.mkdir(parents=True, exist_ok=True)

    faa_files = sorted(SEQ_DIR.glob("*.faa"))
    if wanted:
        faa_files = [f for f in faa_files if f.stem in wanted]

    print(f"Aligning {len(faa_files)} gene FASTAs…\n")
    aligned = treed = 0
    for faa in faa_files:
        symbol = faa.stem
        n_seqs = sum(1 for line in faa.read_text().splitlines() if line.startswith(">"))
        if n_seqs < 3:
            print(f"  {symbol:12s} — only {n_seqs} sequences, skipping")
            continue

        aln_path = ALN_DIR / f"{symbol}.aln.faa"
        tree_path = TREE_DIR / f"{symbol}.nwk"
        ident_path = ALN_DIR / f"{symbol}_identity.tsv"

        if run_mafft(faa, aln_path):
            aligned += 1
            ident_path.write_text(identity_matrix(aln_path))
            if run_fasttree(aln_path, tree_path):
                treed += 1
                print(f"  ✓ {symbol:12s} {n_seqs:3d} seqs → aligned + tree")
            else:
                print(f"  ✓ {symbol:12s} {n_seqs:3d} seqs → aligned (tree failed)")
        else:
            print(f"  ✗ {symbol:12s} alignment failed")

    print(f"\n{aligned} alignments, {treed} trees → {ALN_DIR}")


if __name__ == "__main__":
    main()
