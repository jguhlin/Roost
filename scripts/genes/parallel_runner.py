#!/usr/bin/env python3
"""Parallel gene-presence expansion: many genomes at once on one box.

Replaces sequential chunk_runner.py for large batches. Per genome:
  fetch (disk-cached) -> blast_presence --batch --genomes ACC
  with PRESENCE_OUT=parts/<acc>.jsonl (per-worker output, no shared writes)
  -> verify calls -> delete genome dir -> progress += done (flock)

At the end a single coordinator merges every part into
data/genes/gene_presence_v2.jsonl ((gene, assembly)-scoped replace),
rewrites the parquet, and runs the validation gates over the merged set.

Workers are whole-subprocess isolated; manifest + progress updates are
serialized with flock so nothing clobbers. FASTAs deleted after success
keeps disk bounded at ~workers x 2.5 GB.

Usage:
  nice -n 19 ionice -c3 pixi run python scripts/genes/parallel_runner.py \
      [--workers 7] [--tier all|host_expansion|outgroup] [--limit N]
"""

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from multiprocessing import Process
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "genes"))
from fetch_genomes import fetch_genome  # noqa: E402

GENE_DIR = ROOT / "data" / "genes"
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
TODO = GENOME_DIR / "chrom_todo.json"
PROGRESS = GENOME_DIR / "chrom_progress.json"
CALLS = GENE_DIR / "gene_presence_v2.jsonl"
PARTS = GENE_DIR / "presence_parts"
LOCK = GENOME_DIR / "parallel.lock"
PY = sys.executable
BLAST_SCRIPT = ROOT / "scripts" / "genes" / "blast_presence.py"

MIN_FREE_GB = 150
KEEP_GENOMES = os.environ.get("KEEP_GENOMES", "1") == "1"  # DEFAULT: retain+zstd FASTAs (space available; opt out with 0)
GENES_FLAG = os.environ.get("PANEL_GENES", "")  # comma syms: gene-delta run

WEB_GENOMES = ROOT / "web" / "public" / "data" / "genomes"


def prune_public_links(acc: str) -> None:
    """Drop dangling staging links for acc in web/public/data/genomes.

    Called whenever this runner deletes or archives a genome's derived
    files (genome.2bit, annotation.gff.bgz…). Dangling symlinks crash
    `vite build`'s public-dir copy step with ENOENT, so the public side
    must be cleaned whenever the data side shrinks.
    """
    pdir = WEB_GENOMES / acc
    if not pdir.is_dir():
        return
    for link in pdir.iterdir():
        if link.is_symlink() and not link.exists():
            link.unlink()
    try:
        pdir.rmdir()  # remove the dir if nothing stageable remains
    except OSError:
        pass


def free_gb() -> float:
    return shutil.disk_usage(ROOT).free / 1e9


def locked(fn):
    """Run fn() while holding the coordinator flock (manifest/progress)."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            return fn()
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def update_manifest_entries(entries: dict) -> None:
    """entries: {accession: fields-to-set}. Merged under lock."""
    def _do():
        m = load_json(MANIFEST, {"genomes": []})
        by_acc = {g["accession"]: g for g in m["genomes"]}
        for acc, fields in entries.items():
            e = by_acc.get(acc) or {"accession": acc, "species": fields.get("species", "")}
            e.update(fields)
            by_acc[acc] = e
        m["genomes"] = list(by_acc.values())
        MANIFEST.write_text(json.dumps(m, indent=1))
    locked(_do)


def mark(acc: str, bucket: str, species: str = "") -> None:
    def _do():
        p = load_json(PROGRESS, {"done": [], "failed": [], "chunks_run": 0})
        if acc not in p[bucket]:
            p[bucket].append(acc)
        PROGRESS.write_text(json.dumps(p, indent=1))
    locked(_do)


def wlog(i: int, msg: str) -> None:
    """Worker-safe logger: append to shared log under flock."""
    line = f"{time.strftime('%H:%M:%S')} [w{i}] {msg}\n"
    print(line, end="", flush=True)
    with open(LOCK, "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            with open(GENOME_DIR / "parallel_runner.log", "a") as f:
                f.write(line)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def worker(i: int, my_jobs: list) -> None:
    env = os.environ.copy()
    log = lambda m: wlog(i, m)
    for job in my_jobs:
        acc, species = job["accession"], job["organism"]
        t0 = time.time()
        try:
            if free_gb() < MIN_FREE_GB:
                log(f"disk below {MIN_FREE_GB} GB — pausing {acc}")
                time.sleep(300)
                continue
            # register/refresh the manifest entry FIRST (species+common+
            # assembly level) so blast_presence --genomes always finds a
            # complete record regardless of redo vs new
            update_manifest_entries({acc: {
                "species": species,
                "common": job.get("common") or species,
                "assembly_level": job.get("assembly_level", ""),
                "status": "pending"}})
            rec = fetch_genome({"accession": acc, "species": species})
            if rec["status"] not in ("ok", "cached"):
                mark(acc, "failed")
                update_manifest_entries({acc: {"status": rec["status"]}})
                log(f"{acc} FETCH-FAIL {rec['status']}")
                continue
            # register in the manifest so blast_presence --genomes finds it
            # (mirrors chunk_runner's pending-entry step)
            update_manifest_entries({acc: {
                "species": species, "common": job.get("common", species),
                "status": rec["status"],
                "dir": str(GENOME_DIR / acc),
                "size_mb": rec.get("size_mb"),
                "assembly_level": job.get("assembly_level", "")}})
            part = PARTS / f"{acc}.jsonl"
            env["PRESENCE_OUT"] = str(part)
            env["PRESENCE_SKIP_GATES"] = "1"
            env["PRESENCE_SKIP_PARQUET"] = "1"  # coordinator owns the parquet
            r = subprocess.run(
                [PY, str(BLAST_SCRIPT), "--batch", "--genomes", acc]
                + (["--genes", GENES_FLAG] if GENES_FLAG else []),
                capture_output=True, text=True, timeout=4 * 3600, env=env)
            n_calls = sum(1 for _ in open(part)) if part.exists() else 0
            if r.returncode != 0 or n_calls == 0:
                mark(acc, "failed")
                update_manifest_entries({acc: {"species": species, "status": "search_failed"}})
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:][:110]
                log(f"{acc} SEARCH-FAIL rc={r.returncode} calls={n_calls} {tail}")
            else:
                mark(acc, "done")
                update_manifest_entries({acc: {
                    "species": species, "status": "archived",
                    "size_mb": rec.get("size_mb"), "dir": ""}})
                log(f"[w{i}] {acc} OK {n_calls} calls in {time.time()-t0:.0f}s "
                    f"({rec['status']})")
            if KEEP_GENOMES:
                # retain for future gene-panel deltas: zstd the raw FASTA FIRST,
                # then drop rebuildable blast/diamond DBs (never rmtree the
                # whole dir — that would delete the archive we just made)
                fna = GENOME_DIR / acc / "genome.fna"
                if fna.exists():
                    subprocess.run(["zstd", "-19", "-q", str(fna)], check=False)
                    fna.unlink(missing_ok=True)
                for sub in ("blastdb", "diamond_db"):
                    shutil.rmtree(GENOME_DIR / acc / sub, ignore_errors=True)
                (GENOME_DIR / acc / "genome.zip").unlink(missing_ok=True)
            else:
                shutil.rmtree(GENOME_DIR / acc, ignore_errors=True)
            # data side may have shrunk — drop any now-dangling public links
            prune_public_links(acc)
        except Exception as e:  # keep the worker alive
            mark(acc, "failed")
            log(f"[w{i}] {acc} EXC {str(e)[:120]}")
            shutil.rmtree(GENOME_DIR / acc, ignore_errors=True)
            prune_public_links(acc)


def merge_parts(log) -> None:
    """Single-writer merge of all part files into the shared jsonl."""
    parts = sorted(PARTS.glob("*.jsonl")) if PARTS.exists() else []
    if not parts:
        log("no parts to merge")
        return
    existing = [json.loads(l) for l in CALLS.read_text().splitlines() if l.strip()] \
        if CALLS.exists() else []
    new = []
    for p in parts:
        new += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    in_scope = {(c["gene_symbol"], c.get("assembly_accession")) for c in new}
    kept = [c for c in existing
            if (c["gene_symbol"], c.get("assembly_accession")) not in in_scope]
    merged = kept + new
    CALLS.write_text("".join(json.dumps(c) + "\n" for c in merged))
    log(f"merge: kept {len(kept)} + new {len(new)} = {len(merged)} calls")
    try:
        import polars as pl
        # infer over ALL rows: delta-run rows (appended last) may carry new
        # evidence fields a 100k-row window would miss → silent field loss
        pl.read_ndjson(CALLS, infer_schema_length=None).write_parquet(
            GENE_DIR / "gene_presence_v2.parquet")
    except Exception as e:
        log(f"(parquet rewrite skipped: {e})")
    # validation gates over the merged set (plan §5)
    def get(taxon, sym):
        return next((c for c in merged if c["taxon_id"] == taxon
                     and c["gene_symbol"] == sym), None)
    checks = []
    dc, dd, ac = get(9031, "DDX58"), get(8839, "DDX58"), get(9031, "ANP32A")
    if dc:
        checks.append(("DDX58 chicken NOT_FOUND/high", dc["search_status"] == "NOT_FOUND"
                       and dc.get("absence_confidence") == "high"))
    if dd:
        checks.append(("DDX58 duck FULL/FRAGMENT",
                       dd["search_status"] in ("FULL", "FRAGMENT")))
    if ac:
        checks.append(("ANP32A chicken FULL", ac["search_status"] == "FULL"))
    for name, ok in checks:
        log(f"  gate {'PASS' if ok else 'FAIL'}: {name}")
    for p in parts:
        p.unlink()
    log(f"parts merged & cleaned: {len(parts)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--tier", default="all",
                    choices=["all", "host_expansion", "outgroup"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--redo", action="store_true",
                    help="re-run genomes already done (gene-panel deltas: "
                         "the (gene,assembly)-scoped merge keeps old calls "
                         "and adds the new panel genes)")
    ap.add_argument("--genes", default=None,
                    help="comma-separated panel symbols (delta run; default "
                         "full panel). Equivalent env: PANEL_GENES")
    args = ap.parse_args()
    if args.genes:
        os.environ["PANEL_GENES"] = args.genes

    todo = load_json(TODO, {}).get("candidates", [])
    prog = load_json(PROGRESS, {"done": [], "failed": []})
    settled = set(prog["done"]) | set(prog["failed"])
    jobs = [t for t in todo if args.redo or t["accession"] not in settled]
    if args.redo:
        # resumable redo: a finished part file means the genome's calls are
        # complete (parts are written once, atomically, and deleted at
        # merge) — skip instead of re-searching on restarted delta runs
        before = len(jobs)
        jobs = [t for t in jobs
                if not (PARTS / f"{t['accession']}.jsonl").exists()]
        if before != len(jobs):
            print(f"redo resume: skipping {before - len(jobs)} genomes "
                  f"with finished parts", flush=True)
    # dedup by accession (chrom_candidates re-appends can duplicate) and
    # drop broken entries defensively
    seen_acc = set()
    jobs = [t for t in jobs
            if t.get("accession") and not (t["accession"] in seen_acc
                                            or seen_acc.add(t["accession"]))]
    if args.tier != "all":
        jobs = [t for t in jobs if t.get("tier") == args.tier]
    if args.limit:
        jobs = jobs[:args.limit]
    # keep chrom-first ordering, then round-robin shard across workers
    lvl = {"Complete Genome": 0, "Chromosome": 1, "Scaffold": 2, "Contig": 3}
    jobs.sort(key=lambda t: (lvl.get(t.get("assembly_level", "Scaffold"), 2)))
    shards = [[] for _ in range(args.workers)]
    for i, t in enumerate(jobs):
        shards[i % args.workers].append(t)

    logf = open(GENOME_DIR / "parallel_runner.log", "a")
    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    log(f"parallel_runner: {len(jobs)} genomes, {args.workers} workers, "
        f"free {free_gb():.0f} GB")
    PARTS.mkdir(parents=True, exist_ok=True)
    procs = [Process(target=worker, args=(i, shard)) for i, shard in enumerate(shards)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    merge_parts(log)
    prog = load_json(PROGRESS, {"done": [], "failed": []})
    log(f"FINISHED. done={len(prog['done'])} failed={len(prog.get('failed', []))}")


if __name__ == "__main__":
    main()
