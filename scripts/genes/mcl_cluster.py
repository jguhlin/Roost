#!/usr/bin/env python3
"""
MCL ortholog clustering across the full immunome.

1. Concatenate all protein sequences from sequences_v2/
2. All-vs-all DIAMOND blastp (similarity network)
3. Convert to MCL input format (ABC: node1 node2 weight)
4. Run MCL at multiple inflation values
5. Parse clusters; output ortholog groups + paralogs + singletons

Usage: pixi run python scripts/genes/mcl_cluster.py
"""

import json
import os
import re
import subprocess
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SEQ_DIR = ROOT / "data" / "genes" / "sequences_v2"
OUT_DIR = ROOT / "data" / "genes" / "clusters"
BIN = ROOT / ".pixi/envs/default/bin"


def build_combined_fasta() -> tuple[Path, dict[str, str]]:
    """Concatenate all sequences with gene|species headers."""
    combined = OUT_DIR / "_all_proteins.faa"
    combined.parent.mkdir(parents=True, exist_ok=True)
    id_map = {}  # header_id → gene|species
    with open(combined, "w") as out:
        idx = 0
        for faa in sorted(SEQ_DIR.glob("*.faa")):
            gene = faa.stem
            header, seq = None, []
            for line in faa.read_text().splitlines() + [">"]:
                if line.startswith(">"):
                    if header and seq:
                        idx += 1
                        prot_id = f"P{idx:06d}"
                        id_map[prot_id] = f"{gene}|{header.split('|')[0]}"
                        out.write(f">{prot_id}\n{''.join(seq)}\n")
                    header = line[1:]
                    seq = []
                else:
                    seq.append(line.strip())
    return combined, id_map


def run_all_vs_all(fasta: Path) -> Path:
    """DIAMOND all-vs-all, return ABC file (node1 node2 weight)."""
    db = OUT_DIR / "_all_vs_all.dmnd"
    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}

    # make db
    subprocess.run(
        [str(BIN / "diamond"), "makedb", "--in", str(fasta), "-d", str(db)],
        capture_output=True, timeout=600, env=env)

    # all-vs-all
    abc = OUT_DIR / "_similarity.abc"
    subprocess.run(
        [str(BIN / "diamond"), "blastp",
         "-q", str(fasta), "-d", str(db),
         "-o", str(abc),
         "--outfmt", "6", "qseqid", "sseqid", "bitscore",
         "--very-sensitive", "--threads", "8",
         "-e", "1e-10"],
        capture_output=True, timeout=3600, env=env)
    return abc


def run_mcl(abc: Path, inflation: float) -> Path:
    out = OUT_DIR / f"_mcl_i{inflation}.tsv"
    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}
    subprocess.run(
        [str(BIN / "mcl"), str(abc), "--abc", "-I", str(inflation),
         "-o", str(out), "-te", "4"],
        capture_output=True, timeout=600, env=env)
    return out


def parse_clusters(mcl_out: Path, id_map: dict) -> list[dict]:
    clusters = []
    for line in open(mcl_out):
        members = line.strip().split("\t")
        if not members:
            continue
        annotated = [id_map.get(m, m) for m in members]
        genes = {a.split("|")[0] for a in annotated}
        species = {a.split("|")[1] if "|" in a else "?" for a in annotated}
        clusters.append({
            "size": len(members),
            "genes": sorted(genes),
            "species": sorted(species),
            "members": annotated,
            "type": "ortholog" if len(genes) == 1 else "mixed" if len(genes) <= 3 else "supercluster",
        })
    clusters.sort(key=lambda c: -c["size"])
    return clusters


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Building combined FASTA…")
    combined, id_map = build_combined_fasta()
    n_seqs = len(id_map)
    print(f"   {n_seqs} protein sequences")

    print("2. All-vs-all DIAMOND…")
    abc = run_all_vs_all(combined)
    n_edges = sum(1 for _ in open(abc))
    print(f"   {n_edges} similarity edges")

    results = {}
    for inflation in [1.4, 2.0]:
        print(f"3. MCL (inflation={inflation})…")
        mcl_out = run_mcl(abc, inflation)
        clusters = parse_clusters(mcl_out, id_map)
        n_orthologs = sum(1 for c in clusters if c["type"] == "ortholog")
        n_mixed = sum(1 for c in clusters if c["type"] == "mixed")
        n_super = sum(1 for c in clusters if c["type"] == "supercluster")
        print(f"   {len(clusters)} clusters: {n_orthologs} ortholog groups, "
              f"{n_mixed} mixed, {n_super} superclusters")
        results[f"inflation_{inflation}"] = clusters

    # save
    out_json = OUT_DIR / "mcl_clusters.json"
    out_json.write_text(json.dumps({
        "generated": date.today().isoformat(),
        "total_sequences": n_seqs,
        "total_edges": n_edges,
        "results": results,
    }, indent=1))
    print(f"\nSaved → {out_json}")

    # summary at inflation 1.4 (moderate)
    clusters = results["inflation_1.4"]
    print(f"\nTop 10 clusters (inflation 1.4):")
    for c in clusters[:10]:
        print(f"  {c['size']:4d} seqs | {len(c['genes']):3d} genes | "
              f"{len(c['species']):2d} species | {c['type']}")


if __name__ == "__main__":
    main()
