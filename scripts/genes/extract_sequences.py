#!/usr/bin/env python3
"""
Extract protein sequences for each panel gene across all searched genomes.

Simple approach:
  E5 (NCBI annotated): fetch protein via datasets API
  E4 (blast/DIAMOND): run DIAMOND blastp with --outfmt including full_sseq
                       to get the actual subject ORF protein sequence

Output per gene: data/genes/sequences_v2/{GENE}.faa

Usage: pixi run python scripts/genes/extract_sequences.py [--genes DDX58]
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENE_DIR = ROOT / "data" / "genes"
REF_DIR = GENE_DIR / "references_v2"
CALLS_FILE = GENE_DIR / "gene_presence_v2.jsonl"
SEQ_DIR = GENE_DIR / "sequences_v2"
BIN = ROOT / ".pixi/envs/default/bin"


def load_calls():
    calls = [json.loads(l) for l in open(CALLS_FILE)]
    by_key = {}
    for c in calls:
        by_key[(c["species"], c["gene_symbol"])] = c
    return list(by_key.values())


def fetch_ncbi_protein(gene_id: str) -> str | None:
    """Fetch the longest protein product for an NCBI gene."""
    try:
        import zipfile
        r = subprocess.run(
            ["pixi", "run", "datasets", "download", "gene", "gene-id", gene_id,
             "--filename", "/tmp/_gene_prot.zip"],
            capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return None
        with zipfile.ZipFile("/tmp/_gene_prot.zip") as z:
            for name in z.namelist():
                if "protein.faa" in name:
                    content = z.read(name).decode()
                    best, cur = [], []
                    for line in content.splitlines() + [">"]:
                        if line.startswith(">"):
                            if cur and len(cur) > len(best):
                                best = cur
                            cur = []
                        else:
                            cur.append(line.strip())
                    if best:
                        return "\n".join(best)
    except Exception:
        pass
    return None


def diamond_extract(ref_faa: Path, genome_acc: str) -> tuple[str, float] | None:
    """Run DIAMOND blastp and return (protein_sequence, identity) of best hit."""
    dmnd = ROOT / "data" / "genomes" / genome_acc / "diamond_db" / "orfs"
    if not (dmnd.parent / "orfs.dmnd").exists():
        return None

    env = {**os.environ,
           "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}
    try:
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
            out = tf.name
        r = subprocess.run(
            [str(BIN / "diamond"), "blastp",
             "-q", str(ref_faa), "-d", str(dmnd),
             "-o", out,
             "--outfmt", "6", "sseqid", "pident", "full_sseq", "bitscore",
             "--very-sensitive", "--threads", "4", "-k", "1"],
            capture_output=True, text=True, timeout=300, env=env)
        if r.returncode != 0:
            os.unlink(out)
            return None
        for line in open(out):
            f = line.rstrip("\n").split("\t")
            if len(f) >= 4:
                sseqid, pident, sseq, bitscore = f[0], float(f[1]), f[2], f[3]
                # full_sseq can contain the whole protein
                if len(sseq) >= 30:
                    os.unlink(out)
                    return sseq, pident
        os.unlink(out)
    except Exception as e:
        print(f"    diamond extract error: {e}")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--genes", default=None)
    args = parser.parse_args()

    wanted = set(args.genes.split(",")) if args.genes else None
    SEQ_DIR.mkdir(parents=True, exist_ok=True)

    calls = load_calls()
    genes = sorted({c["gene_symbol"] for c in calls
                    if c["search_status"] in ("FULL", "FRAGMENT")
                    and (not wanted or c["gene_symbol"] in wanted)})

    print(f"Extracting sequences for {len(genes)} genes…\n")

    for symbol in genes:
        gene_calls = [c for c in calls if c["gene_symbol"] == symbol
                      and c["search_status"] in ("FULL", "FRAGMENT")]
        seqs = []
        for c in gene_calls:
            species = c["species"].replace(" ", "_")
            ev = c.get("evidence", {})
            prot = None
            pident = None
            source = "unknown"

            if c.get("method") == "annotation" and ev.get("gene_id"):
                prot = fetch_ncbi_protein(str(ev["gene_id"]))
                source = "ncbi"
                pident = 100.0
            else:
                # Use DIAMOND against the species' ORF database
                ref = REF_DIR / symbol / "duck_protein.faa"
                if not ref.exists():
                    ref = REF_DIR / symbol / "chicken_protein.faa"
                if ref.exists():
                    result = diamond_extract(ref, c["assembly_accession"])
                    if result:
                        prot, pident = result
                        source = "diamond"

            if prot and len(prot) >= 30:
                hdr = f">{species}|{source}|pid={pident:.0f}"
                seqs.append(f"{hdr}\n{prot}")

        if seqs:
            out = SEQ_DIR / f"{symbol}.faa"
            out.write_text("\n".join(seqs) + "\n")
            print(f"  {symbol:12s} {len(seqs):3d} seqs → {out.name}")
        else:
            print(f"  {symbol:12s} — 0 sequences")

    print(f"\n{len(list(SEQ_DIR.glob('*.faa')))} gene FASTAs")


if __name__ == "__main__":
    main()
