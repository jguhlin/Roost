#!/usr/bin/env python3
"""
Export HSP-level evidence for the web "judge it yourself" viewers (D33).

Re-runs the batch DIAMOND (same params as extract_batch: --very-sensitive,
-k 10, ORF db) for all panel genes × all genomes, and writes per-gene
evidence files:

  data/genes/evidence/{GENE}.json (and web/public/data/evidence/{GENE}.json)

Per gene → per species: query info, best-contig HSP cluster with coordinates
(qstart/qend/sstart/send, identity, e-value), summed coverage, multi-exon
flag, representative hit protein (truncated for web size). Species with no
passing hit get an explicit "searched, no HSP above threshold" record.

Usage: pixi run python scripts/genes/export_evidence.py [--genes DDX58,IFIH1]
"""

import argparse
import json
import os
import subprocess
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOMES_DIR = ROOT / "data" / "genomes"
REF_DIR = ROOT / "data" / "genes" / "references_v2"
CALLS = ROOT / "data" / "genes" / "gene_presence_v2.jsonl"
OUT_DIR = ROOT / "data" / "genes" / "evidence"
WEB_DIR = ROOT / "web" / "public" / "data" / "evidence"

BIN = ROOT / ".pixi" / "envs" / "default" / "bin"

MAX_PROT = 3000   # chars of hit protein kept in JSON


def build_rna_batch(wanted):
    """Concatenate reference mRNAs: >{sym}__rna — duck first, chicken fallback."""
    panel = json.loads((REF_DIR / "panel_references.json").read_text())
    tmp = Path(tempfile.mkstemp(suffix=".fna")[1])
    n = 0
    with open(tmp, "w") as f:
        for g in panel["genes"]:
            sym = g["symbol"]
            if wanted and sym not in wanted:
                continue
            for sp in ("duck", "chicken"):
                fa = REF_DIR / sym / f"{sp}_rna.fna"
                if fa.exists() and fa.stat().st_size > 0:
                    used = False
                    for line in fa.read_text().splitlines():
                        if line.startswith(">"):
                            if used:
                                continue  # single transcript per gene
                            f.write(f">{sym}__rna\n")
                            used = True
                            n += 1
                        elif used:
                            f.write(line + "\n")
                    if used:
                        break
    return tmp, n


def run_blastn_genome(query_fna, acc, panel_version="v3"):
    """One divergent-friendly blastn of all reference RNAs vs one genome.
    Results cached per genome (rna_hits.tsv) — delete to force re-run when
    references change. Returns {gene: {contig: [hsp,...]}}."""
    cache = GENOMES_DIR / acc / "rna_hits.tsv"
    if cache.exists():
        hits = {}
        with open(cache) as f:
            first = f.readline()
            if first.strip() != f"# panel {panel_version}":
                cache.unlink()  # stale — regenerate below
            else:
                for line in f:
                    p = line.rstrip("\n").split("\t")
                    if len(p) < 8:
                        continue
                    gene, contig = p[0], p[1]
                    hits.setdefault(gene, {}).setdefault(contig, []).append({
                        "qstart": int(p[2]), "qend": int(p[3]),
                        "gstart": int(p[4]), "gend": int(p[5]),
                        "strand": p[6], "pident": float(p[7]),
                        "evalue": float(p[8]) if len(p) > 8 else 0.0,
                    })
                return hits
    db = GENOMES_DIR / acc / "blastdb" / "genome"
    if not (GENOMES_DIR / acc / "blastdb" / "genome.nhr").exists():
        return {}
    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
        out = tf.name
    try:
        r = subprocess.run(
            [str(BIN / "blastn"), "-task", "blastn", "-dust", "no",
             "-query", str(query_fna), "-db", str(db), "-out", out,
             "-outfmt", "6 qseqid sseqid qstart qend sstart send pident evalue", "-evalue", "1e-10", "-max_target_seqs", "500",
             "-num_threads", "8"],
            capture_output=True, text=True, timeout=7200, env=env)
        if r.returncode != 0:
            return {}
        hits = {}
        for line in open(out):
            f = line.rstrip("\n").split("\t")
            if len(f) < 8:
                continue
            gene = f[0].rsplit("__", 1)[0]
            hits.setdefault(gene, {}).setdefault(f[1], []).append({
                "qstart": int(f[2]), "qend": int(f[3]),
                "gstart": min(int(f[4]), int(f[5])), "gend": max(int(f[4]), int(f[5])),
                "strand": "+" if int(f[4]) <= int(f[5]) else "-",
                "pident": float(f[6]), "evalue": float(f[7]),
            })
        # persist cache
        with open(cache, "w") as cf:
            cf.write(f"# panel {panel_version}\n")
            for gene, contigs in hits.items():
                for contig, hsp_list in contigs.items():
                    for h in hsp_list:
                        cf.write("\t".join(map(str, [gene, contig, h["qstart"],
                            h["qend"], h["gstart"], h["gend"], h["strand"],
                            h["pident"], h["evalue"]])) + "\n")
        return hits
    finally:
        os.unlink(out)


def load_calls():
    calls = {}
    for line in CALLS.read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            calls[(c["species"], c["gene_symbol"])] = c
    return calls


def build_batch(wanted):
    """Concatenate reference proteins: >{sym}__{sp}|{acc} — duck first
    (avians), chicken as fallback."""
    panel = json.loads((REF_DIR / "panel_references.json").read_text())
    genes = panel["genes"]
    tmp = Path(tempfile.mkstemp(suffix=".faa")[1])
    n = 0
    with open(tmp, "w") as f:
        for g in genes:
            sym = g["symbol"]
            if wanted and sym not in wanted:
                continue
            used = False
            for sp in ("duck", "chicken"):
                fa = REF_DIR / sym / f"{sp}_protein.faa"
                if not used and fa.exists() and fa.stat().st_size > 0:
                    for line in fa.read_text().splitlines():
                        if line.startswith(">"):
                            f.write(f">{sym}__{sp}\n")
                            n += 1
                            used = True
                        else:
                            f.write(line + "\n")
    return tmp, n


def run_diamond(query_faa, acc):
    dmnd = GENOMES_DIR / acc / "diamond_db" / "orfs"
    if not (dmnd.parent / "orfs.dmnd").exists():
        return {}
    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", "")}
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
        out = tf.name
    try:
        r = subprocess.run(
            [str(BIN / "diamond"), "blastp",
             "-q", str(query_faa), "-d", str(dmnd), "-o", out,
             "--outfmt", "6", "qseqid", "sseqid", "pident", "qcovhsp", "evalue",
             "bitscore", "qstart", "qend", "qlen", "sstart", "send", "slen", "full_sseq",
             "--very-sensitive", "--threads", "8", "-k", "10", "-e", "10"],
            capture_output=True, text=True, timeout=3600, env=env)
        if r.returncode != 0:
            return {}
        hsps = []
        for line in open(out):
            f = line.rstrip("\n").split("\t")
            if len(f) < 13:
                continue
            hsps.append({
                "q": f[0], "orf": f[1], "pident": float(f[2]), "qcov": float(f[3]),
                "evalue": float(f[4]), "bitscore": float(f[5]),
                "qstart": int(f[6]), "qend": int(f[7]), "qlen": int(f[8]),
                "sstart": int(f[9]), "send": int(f[10]), "slen": int(f[11]),
                "sseq": f[12] if len(f) > 12 else "",
            })
        return hsps
    finally:
        os.unlink(out)


def load_query_seqs(wanted):
    """symbol → (query_id, sequence) from duck-first references."""
    panel = json.loads((REF_DIR / "panel_references.json").read_text())
    out = {}
    for g in panel["genes"]:
        sym = g["symbol"]
        if wanted and sym not in wanted:
            continue
        for sp in ("duck", "chicken"):
            fa = REF_DIR / sym / f"{sp}_protein.faa"
            if fa.exists() and fa.stat().st_size > 0:
                lines = fa.read_text().splitlines()
                seq = "".join(l for l in lines[1:] if not l.startswith(">"))
                if seq:
                    out[sym] = (f"{sym}__{sp}", seq)
                    break
    return out


def load_orf_coords(acc):
    """orf_id → (contig, start, end, strand) from prepare_igv's table."""
    tsv = GENOMES_DIR / acc / "orf_coords.tsv"
    if not tsv.exists():
        return {}
    out = {}
    with open(tsv) as f:
        next(f)  # header
        for line in f:
            orf_id, contig, s, e, strand = line.rstrip("\n").split("\t")
            out[orf_id] = (contig, int(s), int(e), strand)
    return out


def genomic_span(h, oc):
    """Map HSP protein coords onto genomic coordinates via the ORF table."""
    info = oc.get(h["orf"])
    if not info:
        return None
    contig, ostart, oend, strand = info
    if strand == "+":
        gstart = ostart + (h["sstart"] - 1) * 3
        gend = ostart + (h["send"] - 1) * 3 + 2
    else:
        gstart = oend - (h["send"] - 1) * 3 - 2
        gend = oend - (h["sstart"] - 1) * 3
    return {"contig": contig, "gstart": gstart, "gend": gend, "strand": strand}


def exon_fields(rna_gene_hits, verdict_contig):
    """Attach nucleotide-level exon HSPs (blastn, genomic coords) for the
    verdict contig. Returns {} when no mRNA hit there."""
    if not rna_gene_hits or verdict_contig not in rna_gene_hits:
        return {}
    hsps = sorted(rna_gene_hits[verdict_contig], key=lambda h: h["qstart"])
    # mRNA coverage: union of query intervals
    covered = set()
    for h in hsps:
        covered.update(range(h["qstart"], h["qend"] + 1))
    cov_pct = None
    return {
        "exon_hsps": [{"contig": verdict_contig, **h} for h in hsps][:60],
        "exon_count": len(hsps),
        "exon_best_e": min(h["evalue"] for h in hsps),
        "exon_mrna_coverage": None,  # filled below with qlen
        "_exon_covered_bp": len(covered),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", default=None)
    args = ap.parse_args()
    wanted = set(args.genes.split(",")) if args.genes else None

    calls = load_calls()
    genomes = json.loads((GENOMES_DIR / "genomes.json").read_text())["genomes"]
    batch, n_q = build_batch(wanted)
    rna_batch, n_rna = build_rna_batch(wanted)
    query_seqs = load_query_seqs(wanted)
    print(f"{n_q} protein queries, {n_rna} mRNA queries, {len(genomes)} genomes")

    # gene → species → evidence
    ev = {}

    for gi, g in enumerate(genomes):
        if g["status"] not in ("ok", "cached"):
            continue
        acc, species = g["accession"], g["species"]
        print(f"  [{gi+1}/{len(genomes)}] {g.get('common', species)}…", flush=True)
        hsps = run_diamond(batch, acc)
        oc = load_orf_coords(acc)
        rna_hits = run_blastn_genome(rna_batch, acc)

        # group by query
        by_q = {}
        for h in hsps:
            by_q.setdefault(h["q"], []).append(h)

        for q, qhsps in by_q.items():
            sym = q.split("__")[0]
            if wanted and sym not in wanted:
                continue
            # best contig cluster by summed qcov (same logic as extract_batch)
            by_contig = {}
            for h in qhsps:
                contig = h["orf"].rsplit("_", 1)[0] if "_" in h["orf"] else h["orf"]
                by_contig.setdefault(contig, []).append(h)
            best_contig, best_cov, best = None, 0, None
            for contig, ch in by_contig.items():
                cov = min(100.0, sum(x["qcov"] for x in ch))
                if cov > best_cov:
                    best_contig, best_cov, best = contig, cov, ch
            if not best:
                continue

            call = calls.get((species, sym)) or {}
            rec = ev.setdefault(sym, {"gene": sym, "generated": date.today().isoformat(),
                                      "species": {}})
            qlen = best[0]["qlen"]
            single_best = max(x["qcov"] for x in best)
            multi_exon = len(best) > 1 and best_cov > single_best * 1.5
            # query sequence (first time we see this gene)
            if "query" not in rec:
                qid, qseq = query_seqs.get(sym, (q, ""))
                rec["query"] = {"id": qid, "length": qlen, "seq": qseq[:4000]}

            # ALL hits on non-verdict contigs — possible paralogs / cross-matches
            others = []
            for contig, ch in by_contig.items():
                if contig == best_contig:
                    continue
                for x in ch:
                    others.append({**{k: x[k] for k in ("orf", "qstart", "qend", "sstart",
                                                        "send", "slen", "pident", "evalue", "qcov")},
                                   **{"contig": contig}})

            rec["species"][species] = {
                "status": call.get("search_status", "HIT"),
                "level": call.get("status_level", ""),
                "method": call.get("method", "diamond"),
                "contig": best_contig,
                "qlen": qlen,
                "total_qcov": round(best_cov, 1),
                "multi_exon": multi_exon,
                "hsps": sorted(
                    [{**{k: h[k] for k in ("orf", "qstart", "qend", "sstart", "send",
                                           "slen", "pident", "evalue", "qcov", "bitscore", "sseq")},
                      **(genomic_span(h, oc) or {})}
                     for h in best], key=lambda x: x["qstart"]),
                "other_hits": sorted(others, key=lambda x: -x["bitscore"] if "bitscore" in x else -x["evalue"])[:50],
                "assembly": acc,
                **exon_fields(rna_hits.get(sym), best_contig),
                "verdict": {
                    "threshold": "e < 1e-50 AND coverage >= 80% -> FULL (D20)",
                    "evalue_best": min(x["evalue"] for x in best),
                    "passed": best_cov >= 80 and min(x["evalue"] for x in best) < 1e-50,
                },
            }

    # record species with no HSP for completeness (absence context)
    all_species = {g["species"] for g in genomes if g["status"] in ("ok", "cached")}
    for sym in ev:
        for sp in all_species - set(ev[sym]["species"]):
            call = calls.get((sp, sym)) or {}
            ev[sym]["species"][sp] = {
                "status": call.get("search_status", "NOT_FOUND"),
                "level": call.get("status_level", ""),
                "method": call.get("method", "diamond"),
                "no_hit": True,
                "note": "Searched (blastp --very-sensitive, e<=10): no HSP passed inclusion",
            }

    # write both copies
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    for sym, data in ev.items():
        safe = sym.replace("/", "_")
        text = json.dumps(data, separators=(",", ":"))
        (OUT_DIR / f"{safe}.json").write_text(json.dumps(data, indent=1))
        (WEB_DIR / f"{safe}.json").write_text(text)

    print(f"\n{len(ev)} evidence files → {OUT_DIR} + {WEB_DIR}")
    # size check
    total = sum(f.stat().st_size for f in WEB_DIR.glob('*.json'))
    print(f"web total: {total/1048576:.1f} MB")


if __name__ == "__main__":
    main()
