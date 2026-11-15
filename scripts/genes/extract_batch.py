#!/usr/bin/env python3
"""
Batch extraction: one DIAMOND call per genome with ALL reference proteins,
then assign the subject sequences to genes by qseqid.

~15 DIAMOND calls instead of ~8,850 → minutes instead of hours.

Output per gene: data/genes/sequences_v2/{GENE}.faa

Usage: pixi run python scripts/genes/extract_batch.py [--genes DDX58,ANP32A]
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
GENOMES_DIR = ROOT / "data" / "genomes"


def load_calls():
    calls = [json.loads(l) for l in open(CALLS_FILE)]
    by_key = {}
    for c in calls:
        by_key[(c["species"], c["gene_symbol"])] = c
    return list(by_key.values())


def build_batch_protein_file(panel_refs, wanted=None):
    """Concatenate all reference proteins with SYMBOL__SPECIES headers."""
    batch = REF_DIR / "_batch" / "all_protein.faa"
    if batch.exists() and not wanted:
        return batch
    batch.parent.mkdir(exist_ok=True)
    with open(batch, "w") as out:
        for entry in panel_refs["genes"]:
            sym = entry["symbol"]
            if wanted and sym not in wanted:
                continue
            for tag in ("C", "D"):
                fname = f"{'chicken' if tag == 'C' else 'duck'}_protein.faa"
                q = REF_DIR / sym / fname
                if not q.exists() or q.stat().st_size == 0:
                    continue
                writing = False
                for line in q.read_text().splitlines():
                    if line.startswith(">"):
                        out.write(f">{sym}__{tag}\n")
                        writing = True
                    elif writing:
                        out.write(line + "\n")
    return batch


def run_diamond_batch(query_faa: Path, genome_acc: str) -> dict[str, dict]:
    """One DIAMOND call for all queries against one genome.
    Returns {qseqid: {"protein": str, "pident": float, "total_qcov": float,
                       "orfs": int, "multi_exon": bool}}
    """
    dmnd = GENOMES_DIR / genome_acc / "diamond_db" / "orfs"
    if not (dmnd.parent / "orfs.dmnd").exists():
        return {}

    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
        out = tf.name
    try:
        r = subprocess.run(
            [str(BIN / "diamond"), "blastp",
             "-q", str(query_faa), "-d", str(dmnd),
             "-o", out,
             "--outfmt", "6", "qseqid", "sseqid", "pident", "qcovhsp", "full_sseq", "bitscore",
             "--very-sensitive", "--threads", "8", "-k", "10"],  # 10 hits per query
            capture_output=True, text=True, timeout=1800, env=env)
        if r.returncode != 0:
            return {}

        # Collect all hits per qseqid, grouped by contig
        all_hits = {}  # qseqid → list of (sseqid, pident, qcov, protein, bitscore)
        for line in open(out):
            f = line.rstrip("\n").split("\t")
            if len(f) < 6:
                continue
            qseqid, sseqid, pident, qcov, protein, bitscore = (
                f[0], f[1], float(f[2]), float(f[3]), f[4], float(f[5]))
            if len(protein) >= 20:
                all_hits.setdefault(qseqid, []).append(
                    (sseqid, pident, qcov, protein, bitscore))

        # For each query: find best contig cluster, sum coverage
        results = {}
        for qseqid, hits in all_hits.items():
            # Group by contig (ORF IDs look like NC_044302.2_118841 → contig is NC_044302.2)
            by_contig = {}
            for sseqid, pident, qcov, protein, bitscore in hits:
                contig = sseqid.rsplit("_", 1)[0] if "_" in sseqid else sseqid
                by_contig.setdefault(contig, []).append((sseqid, pident, qcov, protein, bitscore))

            # Find the contig with highest summed coverage
            best_contig, best_total_cov, best_hits = None, 0, None
            for contig, chits in by_contig.items():
                total_cov = min(100.0, sum(h[2] for h in chits))  # cap at 100%
                if total_cov > best_total_cov:
                    best_total_cov = total_cov
                    best_contig = contig
                    best_hits = chits

            if best_hits:
                # Longest protein as representative
                best_hit = max(best_hits, key=lambda h: len(h[3]))
                multi_exon = len(best_hits) > 1 and best_total_cov > best_hit[2] * 1.5
                results[qseqid] = {
                    "protein": best_hit[3],
                    "pident": best_hit[1],
                    "total_qcov": best_total_cov,
                    "orfs_on_contig": len(best_hits),
                    "multi_exon": multi_exon,
                }
        return results
    finally:
        os.unlink(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--genes", default=None)
    args = parser.parse_args()
    wanted = set(args.genes.split(",")) if args.genes else None

    SEQ_DIR.mkdir(parents=True, exist_ok=True)

    calls = load_calls()
    genomes = json.loads((GENOMES_DIR / "genomes.json").read_text())["genomes"]
    panel_refs = json.loads((REF_DIR / "panel_references.json").read_text())

    # Build batch query
    batch = build_batch_protein_file(panel_refs, wanted)
    n_queries = sum(1 for l in batch.read_text().splitlines() if l.startswith(">"))
    print(f"Batch protein file: {n_queries} queries → {batch}")

    # Find genes that need sequences (skip already-extracted unless forced)
    genes_needing = set()
    for c in calls:
        if c["search_status"] in ("FULL", "FRAGMENT"):
            sym = c["gene_symbol"]
            if wanted and sym not in wanted:
                continue
            faa = SEQ_DIR / f"{sym}.faa"
            if not faa.exists() or faa.stat().st_size < 50:
                genes_needing.add(sym)
    print(f"Genes needing extraction: {len(genes_needing)}")

    if not genes_needing:
        print("All genes already extracted. Use --genes to force re-extraction.")
        return

    # Run DIAMOND per genome (batch)
    # gene_symbol → list of (species, protein, pident, source)
    gene_seqs = {g: [] for g in genes_needing}

    for gi, g in enumerate(genomes):
        if g["status"] not in ("ok", "cached"):
            continue
        acc = g["accession"]
        species = g["species"].replace(" ", "_")
        print(f"  [{gi+1}/{len(genomes)}] {g.get('common', species)} ({acc})…", flush=True)

        results = run_diamond_batch(batch, acc)
        print(f"    {len(results)} genes with hits", flush=True)

        for qseqid, info in results.items():
            sym = qseqid.split("__")[0]
            if sym in genes_needing:
                call = next((c for c in calls
                             if c["gene_symbol"] == sym
                             and c["species"] == g["species"]), None)
                if call and call["search_status"] in ("FULL", "FRAGMENT"):
                    source = "ncbi" if call.get("method") == "annotation" else "diamond"
                    gene_seqs[sym].append((
                        species, info["protein"], info["pident"], source,
                        info.get("total_qcov", 0), info.get("multi_exon", False)
                    ))

    # Write per-gene FASTAs
    written = 0
    multi_exon_count = 0
    for sym, seqs in sorted(gene_seqs.items()):
        if not seqs:
            continue
        safe_sym = sym.replace("/", "_")
        out = SEQ_DIR / f"{safe_sym}.faa"
        with open(out, "w") as f:
            for entry in seqs:
                if len(entry) == 6:
                    species, protein, pident, source, total_qcov, multi_exon = entry
                    tag = f"{source}|pid={pident:.0f}|cov={total_qcov:.0f}"
                    if multi_exon:
                        tag += "|multi_exon"
                        multi_exon_count += 1
                else:
                    species, protein, pident, source = entry[:4]
                    tag = f"{source}|pid={pident:.0f}"
                f.write(f">{species}|{tag}\n{protein}\n")
        written += 1

    print(f"\n{written} gene FASTAs written → {SEQ_DIR}")
    print(f"Total FASTAs: {len(list(SEQ_DIR.glob('*.faa')))}")


if __name__ == "__main__":
    main()
