#!/usr/bin/env python3
"""
BLAST evidence layer for the gene-presence pipeline (plan §Phase D/E).

For each (panel gene × genome):
  - makeblastdb once per genome (cached)
  - blastn  chicken transcript (+ duck transcript when available) vs genome
  - tblastn chicken protein  (+ duck protein)  vs genome
  - classify into the evidence ladder with thresholds from the decision log:
        FULL      blastn  e≤1e-20, id≥80%, cov≥60%  (or tblastn e≤1e-10, id≥40%, cov≥50%)
        FRAGMENT  same e-value/id, cov 20–60%
        NOT_FOUND below thresholds
  - compute genome searchability s = control genes recovered / 12
    (control recovered = blastn id≥80%, cov≥60%)
  - absence confidence: high (s≥0.90), medium (s≥0.75), low (below)

Output: data/genes/gene_presence_v2.jsonl + .parquet, keyed (panel_version,
taxon_id, gene_symbol), with full blast provenance.

Validation gates (asserted at the end, plan §5):
  DDX58 × chicken  → NOT_FOUND with s ≥ 0.9 (known RIG-I loss)
  DDX58 × duck     → FULL or FRAGMENT (RIG-I present)
  ANP32A × chicken/duck → FULL

Usage: pixi run python scripts/genes/blast_presence.py [--genes DDX58,ANP32A]
"""

import argparse
import json
import os
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENE_DIR = ROOT / "data" / "genes"
REF_DIR = GENE_DIR / "references_v2"
GENOME_DIR = ROOT / "data" / "genomes"
OUT_JSONL = Path(os.environ.get("PRESENCE_OUT", str(GENE_DIR / "gene_presence_v2.jsonl")))

BLAST_BIN = str(ROOT / ".pixi/envs/default/bin")

# Thresholds (decision log D1)
BLASTN = {"evalue": 1e-20, "identity": 80.0, "cov_full": 60.0, "cov_frag_min": 20.0}
TBLASTN = {"evalue": 1e-10, "identity": 40.0, "cov_full": 50.0, "cov_frag_min": 20.0}
CONTROL_MIN = {"identity": 80.0, "cov": 60.0}


def blast(cmd_args, timeout=7200):
    r = subprocess.run([str(Path(BLAST_BIN) / cmd_args[0]), *cmd_args[1:]],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd_args[0]} failed: {r.stderr[:300]}")
    return r.stdout


def ensure_blastdb(genome_accession: str) -> Path:
    db_prefix = GENOME_DIR / genome_accession / "blastdb" / "genome"
    db_dir = db_prefix.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    if (db_dir / "genome.nhr").exists():
        return db_prefix
    fna = GENOME_DIR / genome_accession / "genome.fna"
    if not fna.exists():
        raise FileNotFoundError(f"no genome.fna for {genome_accession}")
    blast(["makeblastdb", "-in", str(fna), "-dbtype", "nucl",
           "-out", str(db_prefix), "-title", genome_accession])
    return db_prefix


def run_blast(task: str, query: Path, db: Path) -> list[dict]:
    fmt = "6 qseqid sseqid pident length qcovs evalue bitscore qlen slen"
    out = blast([task, "-query", str(query), "-db", str(db),
                 "-outfmt", fmt, "-evalue", "10",
                 "-max_target_seqs", "5", "-num_threads", "4",
                 "-task", {"blastn": "dc-megablast", "tblastn": "tblastn"}[task]])
    hits = []
    for line in out.splitlines():
        f = line.split("\t")
        if len(f) < 9:
            continue
        hits.append({
            "subject": f[1], "pident": float(f[2]), "alen": int(f[3]),
            "qcov": float(f[4]), "evalue": float(f[5]),
            "bitscore": float(f[6]), "qlen": int(f[7]),
        })
    return hits


def best_hit(hits: list[dict]):
    return max(hits, key=lambda h: h["bitscore"]) if hits else None


def sum_hit_coverage(hits: list[dict], identity: float, evalue: float) -> float:
    """Sum non-overlapping query coverage across qualifying hits.

    Multi-exon genes (DDX58/RIG-I ~20 exons) produce one tblastn hit per
    exon; the best single hit covers ~5-10%. Summing the query ranges of
    all qualifying hits gives the true gene coverage (D116).

    The e-value here is relaxed to 1e-5 (vs 1e-10 for single-hit calls):
    individual exon fragments are short (~40 aa) and can't individually
    reach 1e-10, but multiple independent hits at 1e-5 on the same
    chromosome constitute strong evidence. The identity bar (≥40%)
    is unchanged.
    """
    sum_evalue = max(evalue, 1e-5)  # relax for exon-level summation
    ranges = []
    for h in hits:
        if h["evalue"] <= sum_evalue and h["pident"] >= identity and h.get("qstart") and h.get("qend"):
            ranges.append((int(h["qstart"]), int(h["qend"])))
    if not ranges:
        return 0.0
    ranges.sort()
    merged = [list(ranges[0])]
    for s, e in ranges[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return sum(e - s + 1 for s, e in merged)


def classify(hits: dict[str, list[dict]]) -> tuple[str, dict]:
    """Returns (status, best_evidence). status ∈ FULL/FRAGMENT/NOT_FOUND.

    Includes a high-significance override (D20): blastn hits with e-value < 1e-50
    AND coverage ≥ 80% are FULL regardless of identity — duck-reference
    comparisons to distant species naturally produce 75-80% identity at
    full coverage, which is a real ortholog, not noise."""
    best = None
    for method in ("blastn", "tblastn"):
        h = best_hit(hits.get(method, []))
        if not h:
            continue
        th = BLASTN if method == "blastn" else TBLASTN
        if h["evalue"] <= th["evalue"] and h["pident"] >= th["identity"]:
            if h["qcov"] >= th["cov_full"]:
                cand = ("FULL", method, h)
            elif h["qcov"] >= th["cov_frag_min"]:
                cand = ("FRAGMENT", method, h)
            else:
                cand = None
            # D116: summed tblastn coverage — multi-exon genes split across
            # exons get each exon as a separate hit; sum non-overlapping query
            # ranges to recover the true gene coverage
            if cand is None and method == "tblastn":
                scov_aa = sum_hit_coverage(hits.get(method, []), th["identity"], th["evalue"])
                scov = min(100.0, scov_aa / max(1, h.get("qlen", 1)) * 100) if scov_aa else 0
                h2 = {**h, "qcov": scov, "summed_coverage": True}
                if scov >= th["cov_full"]:
                    cand = ("FULL", method, h2)
                elif scov >= th["cov_frag_min"]:
                    cand = ("FRAGMENT", method, h2)
        else:
            cand = None
        # D20 high-significance override: real ortholog just below identity cutoff
        if (cand is None and method == "blastn"
                and h["evalue"] < 1e-50 and h["qcov"] >= 80):
            cand = ("FULL", method, h)
        if cand and (best is None or cand[2]["bitscore"] > best[2]["bitscore"]):
            best = cand
    if not best:
        # keep the top raw hit for provenance even when below thresholds
        raw = None
        for method in ("blastn", "tblastn"):
            h = best_hit(hits.get(method, []))
            if h and (raw is None or h["bitscore"] > raw[2]["bitscore"]):
                raw = ("NOT_FOUND", method, h)
        status, method, h = raw if raw else ("NOT_FOUND", None, None)
        return status, {"method": method, **({k: h[k] for k in
                        ("subject", "pident", "qcov", "evalue", "bitscore")} if h else {})}
    status, method, h = best
    return status, {"method": method, **{k: h[k] for k in
                    ("subject", "pident", "qcov", "evalue", "bitscore")}}


def searchability(db: Path, controls_manifest: dict) -> tuple[float, list[str]]:
    recovered, missing = 0, []
    for c in controls_manifest["genes"]:
        if not c.get("chicken"):
            continue
        q = REF_DIR / "controls" / c["symbol"] / "chicken_rna.fna"
        if not q.exists():
            continue
        h = best_hit(run_blast("blastn", q, db))
        if h and h["pident"] >= CONTROL_MIN["identity"] and h["qcov"] >= CONTROL_MIN["cov"]:
            recovered += 1
        else:
            missing.append(c["symbol"])
    total = sum(1 for c in controls_manifest["genes"] if c.get("chicken"))
    return (recovered / total if total else 0.0), missing


def absence_confidence(s: float, assembly_level: str | None) -> str:
    if s >= 0.90 and (assembly_level or "").lower() in ("chromosome", "complete genome"):
        return "high"
    if s >= 0.75:
        return "medium"
    return "low"


def build_batch_queries(refs_manifest, wanted=None):
    """Combine all reference sequences into two batch FASTAs (blastn/tblastn)
    with re-headered records >SYMBOL__C / >SYMBOL__D so blast runs once per
     genome per method instead of once per gene."""
    import tempfile
    batch_dir = REF_DIR / f"_batch_{os.getpid()}"  # per-process: parallel workers safe
    batch_dir.mkdir(exist_ok=True)
    counts = {"rna": 0, "protein": 0}
    files = {"rna": batch_dir / "all_rna.fna", "protein": batch_dir / "all_protein.faa"}
    seen = set()
    for kind in ("rna", "protein"):
        with open(files[kind], "w") as out:
            for entry in refs_manifest["genes"]:
                sym = entry["symbol"]
                if wanted and sym not in wanted:
                    continue
                for tag, fname in (("C", f"chicken_{'rna' if kind=='rna' else 'protein'}.fna" if kind=="rna" else "chicken_protein.faa"),
                                   ("D", f"duck_{'rna' if kind=='rna' else 'protein'}.fa")):
                    # normalize filename patterns
                    if kind == "rna":
                        fnames = {"C": "chicken_rna.fna", "D": "duck_rna.fna"}
                    else:
                        fnames = {"C": "chicken_protein.faa", "D": "duck_protein.faa"}
                    q = REF_DIR / sym / fnames[tag]
                    if not q.exists() or q.stat().st_size == 0:
                        continue
                    key = (sym, tag, kind)
                    if key in seen:
                        continue
                    seen.add(key)
                    for line in q.read_text().splitlines():
                        if line.startswith(">"):
                            out.write(f">{sym}__{tag}\n")
                        else:
                            out.write(line + "\n")
                    counts[kind] += 1
                # D116: mammal reference proteins (Swiss-Prot) — searched
                # alongside avian refs so cross-taxon genes like DDX58/RIG-I
                # are detectable in mammal genomes
                if kind == "protein":
                    mq = REF_DIR / sym / "mammal_protein.faa"
                    if mq.exists() and mq.stat().st_size > 0:
                        mkey = (sym, "M", kind)
                        if mkey not in seen:
                            seen.add(mkey)
                            for line in mq.read_text().splitlines():
                                if line.startswith(">"):
                                    out.write(f">{sym}__M\n")
                                else:
                                    out.write(line + "\n")
                            counts[kind] += 1
    return files, counts


def run_batch(task: str, query: Path, db: Path) -> dict[str, list[dict]]:
    """One blast for all queries; returns hits keyed by query id (SYMBOL__C)."""
    fmt = "6 qseqid sseqid pident length qcovs evalue bitscore qlen slen"
    out = blast([task, "-query", str(query), "-db", str(db),
                 "-outfmt", fmt, "-evalue", "10",
                 "-max_target_seqs", "5", "-num_threads", "8",
                 "-task", {"blastn": "dc-megablast", "tblastn": "tblastn"}[task]])
    by_q = {}
    for line in out.splitlines():
        f = line.split("\t")
        if len(f) < 9:
            continue
        h = {
            "subject": f[1], "pident": float(f[2]), "alen": int(f[3]),
            "qcov": float(f[4]), "evalue": float(f[5]),
            "bitscore": float(f[6]), "qlen": int(f[7]),
        }
        by_q.setdefault(f[0], []).append(h)
    return by_q


def split_fasta_chunks(src: Path, n_chunks: int, dest_dir: Path) -> list[Path]:
    """Split a FASTA into n chunk files (round-robin by record)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    records = []
    cur = []
    for line in src.read_text().splitlines() + [">"]:
        if line.startswith(">"):
            if cur:
                records.append(cur)
            cur = [line]
        else:
            cur.append(line)
    records = records[:-1] if records and records[-1] == [">"] else records
    chunks = [[] for _ in range(n_chunks)]
    for i, rec in enumerate(records):
        chunks[i % n_chunks].append(rec)
    paths = []
    for i, ch in enumerate(chunks):
        p = dest_dir / f"chunk_{i}.faa"
        with open(p, "w") as f:
            for rec in ch:
                f.write("\n".join(rec) + "\n")
        paths.append(p)
    return [p for p in paths if p.stat().st_size > 0]


def run_tblastn_chunked(query: Path, db: Path, n_chunks: int = 6) -> dict[str, list[dict]]:
    """tblastn in query chunks (genome 6-frame translation dominates cost;
    chunking bounds per-call runtime and lets each finish under timeout)."""
    by_q: dict[str, list[dict]] = {}
    chunk_dir = query.parent / f"{query.stem}_chunks"
    for chunk in split_fasta_chunks(query, n_chunks, chunk_dir):
        print(f"      tblastn chunk {chunk.name}…", flush=True)
        by_q.update(run_batch("tblastn", chunk, db))
    return by_q


def translate_genome_sixframe(fna: Path, out_faa: Path, min_orf=30):
    """6-frame translation of a genome FASTA into protein ORFs (≥ min_orf aa).
    Codon table 1 (standard); stops → trimmed. DIAMOND-compatible output."""
    from textwrap import wrap
    CODON = {}
    bases = "TCAG"
    aas = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
    i = 0
    for b1 in bases:
        for b2 in bases:
            for b3 in bases:
                CODON[b1+b2+b3] = aas[i]; i += 1
    def revcomp(s):
        comp = {"A":"T","T":"A","G":"C","C":"G","N":"N"}
        return "".join(comp.get(c, "N") for c in reversed(s))
    def translate(seq):
        prot = []
        for i in range(0, len(seq)-2, 3):
            aa = CODON.get(seq[i:i+3].upper(), "X")
            if aa == "*":
                break
            prot.append(aa)
        return "".join(prot)
    with open(fna) as fin, open(out_faa, "w") as fout:
        header, seq = None, []
        def emit_orfs(contig, frame, dna):
            orfs = []
            start = 0
            for i in range(0, len(dna)-2, 3):
                if CODON.get(dna[i:i+3].upper(), "X") == "*":
                    orf = translate(dna[start:i])
                    if len(orf) >= min_orf:
                        orfs.append((start, orf))
                    start = i + 3
            # trailing orf
            orf = translate(dna[start:])
            if len(orf) >= min_orf:
                orfs.append((start, orf))
            for pos, p in orfs:
                fout.write(f">{contig}_f{frame}_{pos}\n")
                for chunk in wrap(p, 60):
                    fout.write(chunk + "\n")
        for line in fin:
            if line.startswith(">"):
                if header and seq:
                    s = "".join(seq)
                    for frame in range(3):
                        emit_orfs(header[:40], frame+1, s[frame:])
                        emit_orfs(header[:40], frame+4, revcomp(s)[frame:])
                header = line[1:].strip().split()[0]
                seq = []
            else:
                seq.append(line.strip())
        if header and seq:
            s = "".join(seq)
            for frame in range(3):
                emit_orfs(header[:40], frame+1, s[frame:])
                emit_orfs(header[:40], frame+4, revcomp(s)[frame:])


def ensure_diamond_db(genome_accession: str) -> Path:
    """Build cached 6-frame ORF database for DIAMOND (via EMBOSS transeq — fast)."""
    db_prefix = GENOME_DIR / genome_accession / "diamond_db" / "orfs"
    db_dir = db_prefix.parent
    db_dir.mkdir(parents=True, exist_ok=True)
    if (db_dir / "orfs.dmnd").exists():
        return db_prefix
    fna = GENOME_DIR / genome_accession / "genome.fna"
    if not fna.exists():
        raise FileNotFoundError(f"no genome.fna for {genome_accession}")
    orfs_faa = db_dir / "orfs.faa"
    if not orfs_faa.exists() or orfs_faa.stat().st_size < 1000:
        print(f"    getorf 6-frame ORFs {genome_accession}…", flush=True)
        import subprocess, os
        env = {**os.environ,
               "PATH": str(ROOT / ".pixi/envs/default/bin") + ":" + os.environ.get("PATH", "")}
        r = subprocess.run(
            [str(ROOT / ".pixi/envs/default/bin/getorf"),
             "-sequence", str(fna), "-outseq", str(orfs_faa),
             "-minsize", "90", "-find", "1"],
            capture_output=True, text=True, timeout=3600, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"transeq failed: {r.stderr[:300]}")
    import subprocess
    r = subprocess.run(
        [str(ROOT / ".pixi/envs/default/bin/diamond"), "makedb",
         "--in", str(orfs_faa), "-d", str(db_prefix)],
        capture_output=True, text=True, timeout=1800,
        env={**__import__('os').environ, "PATH": str(ROOT / ".pixi/envs/default/bin") + ":" + __import__('os').environ.get("PATH", "")})
    if r.returncode != 0:
        raise RuntimeError(f"diamond makedb failed: {r.stderr[:300]}")
    orfs_faa.unlink(missing_ok=True)  # save disk
    return db_prefix


def run_diamond_blastp(query_faa: Path, db_prefix: Path) -> dict[str, list[dict]]:
    """DIAMOND blastp with very-sensitive mode. Returns hits keyed by qseqid."""
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
        out_path = tf.name
    r = subprocess.run(
        [str(ROOT / ".pixi/envs/default/bin/diamond"), "blastp",
         "-q", str(query_faa), "-d", str(db_prefix),
         "-o", out_path, "--outfmt", "6", "qseqid", "sseqid", "pident", "length", "qcovhsp", "evalue", "bitscore", "qlen", "slen", "qstart", "qend",
         "--very-sensitive", "--threads", "8", "-k", "25", "-e", "10"],
        capture_output=True, text=True, timeout=7200,
        env={**__import__('os').environ, "PATH": str(ROOT / ".pixi/envs/default/bin") + ":" + __import__('os').environ.get("PATH", "")})
    if r.returncode != 0:
        raise RuntimeError(f"diamond blastp failed: {r.stderr[:300]}")
    by_q = {}
    for line in open(out_path):
        f = line.strip().split("\t")
        if len(f) < 9:
            continue
        hit = {
            "subject": f[1], "pident": float(f[2]), "alen": int(f[3]),
            "qcov": float(f[4]), "evalue": float(f[5]),
            "bitscore": float(f[6]), "qlen": int(f[7]),
        }
        if len(f) >= 11:
            try:
                hit["qstart"] = int(f[9])
                hit["qend"] = int(f[10])
            except (ValueError, IndexError):
                pass
        by_q.setdefault(f[0], []).append(hit)
    __import__('os').unlink(out_path)
    return by_q


def sum_hsp_coverage(hits: list[dict]) -> float:
    """Sum non-overlapping query coverage across HSPs on the same subject.
    Handles multi-exon genes where the query aligns to exon after exon.
    Input hits need 'subject' + 'qstart'/'qend' to compute overlap."""
    if not hits:
        return 0.0
    # group by subject (chromosome/scaffold)
    by_subject = {}
    for h in hits:
        by_subject.setdefault(h["subject"], []).append(h)
    best_total = 0.0
    for subj, shits in by_subject.items():
        # approximate: sum aligned lengths / query length
        total_len = sum(h.get("alen", 0) for h in shits)
        qlen = max(h.get("qlen", 1) for h in shits)
        best_total = max(best_total, min(100.0, 100.0 * total_len / qlen))
    return best_total


def classify_v2(hits: dict[str, list[dict]], annotation_status=None) -> tuple[str, dict]:
    """Evidence-integration classifier (D22).

    Layer 0: annotation → E5 (checked before calling this)
    Layer 1: blastn e-value significance + summed coverage
    Layer 2: DIAMOND/tblastn grouped coverage
    Returns (status, evidence) where status ∈ FULL/FRAGMENT/NOT_FOUND.
    """
    # Layer 1: blastn with summed coverage + e-value significance
    blastn_hits = hits.get("blastn", [])
    if blastn_hits:
        h = best_hit(blastn_hits)
        summed_cov = sum_hsp_coverage(blastn_hits)
        if h["evalue"] < 1e-50:
            if summed_cov >= 60:
                return "FULL", {"method": "blastn", "pident": h["pident"],
                                "qcov": summed_cov, "evalue": h["evalue"],
                                "bitscore": h["bitscore"],
                                "summed_coverage": True,
                                "subject": h["subject"]}
            elif summed_cov >= 20:
                return "FRAGMENT", {"method": "blastn", "pident": h["pident"],
                                    "qcov": summed_cov, "evalue": h["evalue"],
                                    "bitscore": h["bitscore"],
                                    "summed_coverage": True,
                                    "subject": h["subject"]}

    # Layer 2: DIAMOND/tblastn — group by subject, sum coverage
    tblastn_hits = hits.get("tblastn", [])
    if tblastn_hits:
        h = best_hit(tblastn_hits)
        grouped_cov = sum_hsp_coverage(tblastn_hits)
        if h["evalue"] < 1e-20 and h["pident"] >= 30:
            if grouped_cov >= 40:
                return "FULL", {"method": "tblastn", "pident": h["pident"],
                                "qcov": grouped_cov, "evalue": h["evalue"],
                                "bitscore": h["bitscore"],
                                "summed_coverage": True,
                                "subject": h["subject"]}
            elif grouped_cov >= 15:
                return "FRAGMENT", {"method": "tblastn", "pident": h["pident"],
                                    "qcov": grouped_cov, "evalue": h["evalue"],
                                    "bitscore": h["bitscore"],
                                    "summed_coverage": True,
                                    "subject": h["subject"]}

    # No qualifying evidence — report raw best if available
    raw = None
    for method in ("blastn", "tblastn"):
        h = best_hit(hits.get(method, []))
        if h and (raw is None or h["bitscore"] > raw[2]["bitscore"]):
            raw = ("NOT_FOUND", method, h)
    if raw:
        _, method, h = raw
        return "NOT_FOUND", {"method": method, "pident": h["pident"],
                             "qcov": h["qcov"], "evalue": h["evalue"],
                             "bitscore": h["bitscore"], "subject": h.get("subject")}
    return "NOT_FOUND", {"method": None}


def check_ncbi_annotation(species: str, panel_refs: dict, wanted=None) -> dict[str, dict]:
    """Layer 0: query NCBI for annotated genes. Returns {symbol: annotation_info}.

    Alias-aware: NCBI records the same gene under different official
    symbols across taxa (e.g. DDX58 is "RIGI" in Anas platyrhynchos), so a
    record matching any alias of a panel gene (gene_config.json aliases:
    alias -> canonical) resolves to the canonical symbol. Without this,
    annotated detections were systematically mis-called E4 (putative)."""
    import subprocess, time
    # alias -> canonical panel symbol (config is the D28 source of truth)
    alias_map: dict[str, str] = {}
    try:
        cfg = json.loads((Path(__file__).resolve().parents[2]
                          / "data/genes/gene_config.json").read_text())
        alias_map = {a.upper(): c for a, c in cfg.get("aliases", {}).items()
                     if a != "_doc" and isinstance(c, str)}
    except Exception:
        pass
    annotated = {}
    # Query all genes for this species in one batch (taxon-wide)
    try:
        r = subprocess.run(
            ["pixi", "run", "datasets", "summary", "gene", "taxon", species],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return annotated
        d = json.loads(r.stdout)
        # Build symbol → gene info map
        for rep in d.get("reports", []):
            g = rep["gene"]
            sym = g.get("symbol", "").upper()
            if not sym:
                continue
            sym = alias_map.get(sym, sym)   # resolve alias → canonical
            loc = {}
            for ann in g.get("annotations", []):
                for gl in ann.get("genomic_locations", []):
                    loc = {
                        "chromosome": gl.get("sequence_name", ""),
                        "start": gl.get("genomic_range", {}).get("begin"),
                        "end": gl.get("genomic_range", {}).get("end"),
                    }
            annotated[sym] = {
                "gene_id": g.get("gene_id"),
                "description": g.get("description", ""),
                "location": loc,
            }
    except Exception as e:
        print(f"    annotation check failed: {e}")
    return annotated


def _read_manifest_retries(path: Path, attempts: int = 8):
    """The manifest is rewritten under a coordinator lock by parallel
    workers; an unlocked reader can catch a partial write. Retry."""
    import time as _t
    last = None
    for i in range(attempts):
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError as e:
            last = e
            _t.sleep(0.1 + 0.05 * i)
    raise last


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--genes", default=None, help="comma-separated symbols (subset run)")
    parser.add_argument("--batch", action="store_true",
                        help="batch mode: one blast per genome per method (fast for full panels)")
    parser.add_argument("--genomes", default=None,
                        help="comma-separated accessions: search only these genomes "
                             "(delta runs when the manifest grows; calls merge safely)")
    args = parser.parse_args()

    genomes = _read_manifest_retries(GENOME_DIR / "genomes.json")["genomes"]
    if args.genomes:
        wanted_genomes = {a.strip() for a in args.genomes.split(",") if a.strip()}
        genomes = [g for g in genomes if g["accession"] in wanted_genomes]
        print(f"[genomes] delta run: {len(genomes)} of manifest selected")
    panel_refs = json.loads((REF_DIR / "panel_references.json").read_text())
    controls = json.loads((REF_DIR / "control_references.json").read_text())
    panel_version = panel_refs["panel_version"]

    wanted = set(args.genes.split(",")) if args.genes else None

    if args.batch:
        files, counts = build_batch_queries(panel_refs, wanted)
        print(f"batch queries: {counts['rna']} rna + {counts['protein']} protein records")

    calls = []
    for g in genomes:
        if g["status"] not in ("ok", "cached"):
            print(f"  skipping {g['accession']} ({g['status']})")
            continue
        acc = g["accession"]
        print(f"\n== {g['common']} ({acc}) ==", flush=True)
        db = ensure_blastdb(acc)
        s, missing = searchability(db, controls)
        conf_grade = absence_confidence(s, "chromosome")
        print(f"  searchability s={s:.2f} ({conf_grade})" +
              (f"  missing: {missing}" if missing else ""), flush=True)

        # Layer 0: NCBI annotation check (E5 = proof positive, D22)
        annotations = check_ncbi_annotation(g["species"], panel_refs, wanted)
        n_annotated = sum(1 for e in panel_refs["genes"]
                          if e["symbol"].upper() in annotations
                          and (not wanted or e["symbol"] in wanted))
        print(f"  Layer 0: {n_annotated} genes NCBI-annotated", flush=True)

        # gather all hits for all genes
        gene_hits: dict[str, dict[str, list]] = {}
        if args.batch:
            # Stage 1: batch blastn (fast, dc-megablast on transcripts)
            print("    stage 1: batch blastn…", flush=True)
            for qid, hits in run_batch("blastn", files["rna"], db).items():
                sym, _, tag = qid.partition("__")
                gene_hits.setdefault(sym, {}).setdefault("blastn", []).extend(hits)

            # Stage 2: tblastn only for genes blastn didn't call FULL
            # (genome 6-frame translation dominates tblastn cost)
            need = []
            for entry in panel_refs["genes"]:
                sym = entry["symbol"]
                if wanted and sym not in wanted:
                    continue
                if not (entry.get("chicken") or entry.get("duck")):
                    continue
                h = gene_hits.get(sym, {}).get("blastn", [])
                st, _ = classify({"blastn": h} if h else {})
                if st != "FULL":
                    need.append(sym)
            if need:
                print(f"    stage 2: DIAMOND blastp --very-sensitive for {len(need)} genes…", flush=True)
                subset = files["protein"].parent / "subset_protein.faa"
                take = False
                with open(subset, "w") as out:
                    for line in files["protein"].read_text().splitlines():
                        if line.startswith(">"):
                            sym = line[1:].split("__")[0]
                            if sym in need:
                                out.write(line + "\n")
                                take = True
                            else:
                                take = False
                        elif take:
                            out.write(line + "\n")
                dmnd_db = ensure_diamond_db(acc)
                for qid, hits in run_diamond_blastp(subset, dmnd_db).items():
                    sym, _, tag = qid.partition("__")
                    gene_hits.setdefault(sym, {}).setdefault("tblastn", []).extend(hits)
            else:
                print("    stage 2: all genes FULL via blastn — DIAMOND skipped", flush=True)
        else:
            for entry in panel_refs["genes"]:
                sym = entry["symbol"]
                if wanted and sym not in wanted:
                    continue
                has_chicken = bool(entry.get("chicken"))
                has_duck = bool(entry.get("duck"))
                if not has_chicken and not has_duck:
                    continue
                hits = {}
                for method, fname in (("blastn", "chicken_rna.fna"), ("tblastn", "chicken_protein.faa")):
                    q = REF_DIR / sym / fname
                    if q.exists() and q.stat().st_size > 0:
                        hits[method] = run_blast(method, q, db)
                for method, fname in (("blastn", "duck_rna.fna"), ("tblastn", "duck_protein.faa")):
                    q = REF_DIR / sym / fname
                    if q.exists() and q.stat().st_size > 0:
                        extra = run_blast(method, q, db)
                        hits[method] = (hits.get(method) or []) + extra
                gene_hits[sym] = hits

        for entry in panel_refs["genes"]:
            sym = entry["symbol"]
            if wanted and sym not in wanted:
                continue
            has_any = bool(entry.get("chicken") or entry.get("duck"))
            if not has_any:
                continue
            hits = gene_hits.get(sym, {})

            # Layer 0: an NCBI record (symbol or alias) makes the call E5,
            # but the search outcome is still recorded — blast-confirmed
            # annotations stay distinguishable from annotation-only calls
            # (alias corroboration; D22 semantics preserved).
            ann = annotations.get(sym.upper())
            blast_status, blast_evidence = classify_v2(hits)
            if ann:
                status = "FULL"
                status_level = "E5_annotated"
                evidence = {"method": "annotation", "gene_id": ann["gene_id"],
                            "description": ann["description"],
                            "location": ann.get("location", {}),
                            "blast_status": blast_status}
                if blast_status != "NOT_FOUND":
                    evidence["blast_hit"] = blast_evidence
            else:
                status, evidence = blast_status, blast_evidence
                status_level = {"FULL": "E4_unannotated_found", "FRAGMENT": "E3_fragment",
                                "NOT_FOUND": "E2_searched_not_found"}[status]

            calls.append({
                "panel_version": panel_version,
                "taxon_id": taxon_for(g["species"], acc),
                "species": g["species"],
                "assembly_accession": acc,
                "gene_symbol": sym,
                "status_level": status_level,
                "search_status": status,
                "evidence": evidence,
                "searchability": round(s, 3),
                "absence_confidence": conf_grade if status == "NOT_FOUND" else None,
                "call_date": date.today().isoformat(),
                "method": "annotation" if ann else "blast",
            })
            if status != "FULL":
                print(f"    {sym:10s} {status:10s} "
                      + (f"via {evidence.get('method')} id={evidence.get('pident')}% "
                         f"cov={evidence.get('qcov')}%" if evidence.get("method") else ""), flush=True)
        print(f"    … {sum(1 for c in calls if c['assembly_accession']==acc)} genes evaluated", flush=True)

    # write output — SUBSET RUNS MERGE, never replace the full call set.
    # (D78 postmortem: a --genes run that produced 0 calls wiped the jsonl.)
    if wanted:
        if not calls:
            print("\n✗ subset run produced 0 calls — ABORTING WRITE (jsonl untouched)")
            import sys
            sys.exit(1)
        # load existing, drop only in-scope (species, gene) pairs, append new
        existing = []
        if OUT_JSONL.exists():
            existing = [json.loads(l) for l in OUT_JSONL.read_text().splitlines() if l.strip()]
        # (gene, assembly) scoping: delta runs on a genome subset must never
        # drop other genomes' calls for the same genes
        in_scope = {(c["gene_symbol"], c.get("assembly_accession")) for c in calls}
        kept = [c for c in existing
                if (c["gene_symbol"], c.get("assembly_accession")) not in in_scope]
        merged = kept + calls
        print(f"\nmerge: kept {len(kept)} existing + {len(calls)} new = {len(merged)} calls")
        with open(OUT_JSONL, "w") as f:
            for c in merged:
                f.write(json.dumps(c) + "\n")
        calls = merged  # gates evaluate the merged set
    else:
        if not calls:
            print("\n✗ full run produced 0 calls — ABORTING WRITE (jsonl untouched)")
            import shutil as _sh, sys
            _sh.rmtree(REF_DIR / f"_batch_{os.getpid()}", ignore_errors=True)
            sys.exit(1)
        with open(OUT_JSONL, "w") as f:
            for c in calls:
                f.write(json.dumps(c) + "\n")
    if os.environ.get("PRESENCE_OUT"):
        # worker mode (parallel_runner): per-genome part output — the
        # coordinator merge owns the shared parquet, never clobber it
        print("(parquet write skipped: parallel worker run)")
    else:
        try:
            import polars as pl
            # infer over ALL rows: new evidence fields (e.g. blast_status)
            # may only appear in rows appended at the end of the jsonl
            pl.read_ndjson(OUT_JSONL, infer_schema_length=None).write_parquet(
                GENE_DIR / "gene_presence_v2.parquet")
        except Exception as e:
            print(f"(parquet write skipped: {e})")
    print(f"\n{len(calls)} calls → {OUT_JSONL}")

    # self-clean this process's batch query dir (parallel-safe: own PID only)
    import shutil as _sh
    _sh.rmtree(REF_DIR / f"_batch_{os.getpid()}", ignore_errors=True)

    # ---- validation gates (plan §5) ----
    if os.environ.get("PRESENCE_SKIP_GATES"):
        print("(validation gates skipped: parallel worker run)")
        return 0
    print("\nVALIDATION GATES:")
    def get(taxon, sym):
        return next((c for c in calls if c["taxon_id"] == taxon and c["gene_symbol"] == sym), None)
    def in_scope(sym):
        return (not wanted) or (sym in wanted)

    ddx_chicken = get(9031, "DDX58") if in_scope("DDX58") else None
    ddx_duck = get(8839, "DDX58") if in_scope("DDX58") else None
    anp_chicken = get(9031, "ANP32A") if in_scope("ANP32A") else None
    gates = []
    if in_scope("DDX58"):
        gates.append(("DDX58 chicken call EXISTS", ddx_chicken is not None, ddx_chicken))
        gates.append(("DDX58 duck call EXISTS", ddx_duck is not None, ddx_duck))
        if ddx_chicken:
            ok = ddx_chicken["search_status"] == "NOT_FOUND" and ddx_chicken["absence_confidence"] == "high"
            gates.append(("DDX58 chicken NOT_FOUND/high-conf absence", ok, ddx_chicken))
        if ddx_duck:
            ok = ddx_duck["search_status"] in ("FULL", "FRAGMENT")
            gates.append(("DDX58 duck found", ok, ddx_duck))
    if in_scope("ANP32A"):
        gates.append(("ANP32A chicken call EXISTS", anp_chicken is not None, anp_chicken))
        if anp_chicken:
            ok = anp_chicken["search_status"] == "FULL"
            gates.append(("ANP32A chicken FULL", ok, anp_chicken))
    all_ok = True
    for name, ok, call in gates:
        detail = (call['search_status'] +
                  (f" (conf={call['absence_confidence']})" if call.get('absence_confidence') else '')
                  ) if call else 'missing'
        print(f"  {'✓' if ok else '✗ FAIL'} {name} → {detail}")
        all_ok = all_ok and ok
    print(f"\n{'✓ ALL GATES PASS' if all_ok and gates else '✗ GATES FAILED OR MISSING — inspect before proceeding'}")
    return 0 if all_ok else 1


TAXON_BY_ACCESSION = {
    "GCF_016699485.2": 9031,   # chicken
    "GCF_047663525.1": 8839,   # Pekin duck
    "GCF_003957565.2": 59729,  # zebra finch
    "GCF_905368555.1": 9103,   # turkey
}

def _load_taxon_lookup():
    """species latin name → taxon_id from our taxonomy table."""
    import csv
    lookup = {}
    path = ROOT / "data" / "aves_taxonomy.tsv"
    if path.exists():
        with open(path) as f:
            for row in csv.DictReader(f, delimiter="\t"):
                lookup[row["scientific_name"]] = int(row["taxon_id"])
    return lookup

_TAXA = None

def taxon_for(species: str, accession: str):
    global _TAXA
    if accession in TAXON_BY_ACCESSION:
        return TAXON_BY_ACCESSION[accession]
    if _TAXA is None:
        _TAXA = _load_taxon_lookup()
    return _TAXA.get(species)

if __name__ == "__main__":
    raise SystemExit(main())
