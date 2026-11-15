#!/usr/bin/env python3
"""Chunked chromosome-level genome expansion: fetch -> search -> delete.

For each chunk of accessions from data/genomes/chrom_todo.json:
  1. add to the manifest as pending, download the genome
  2. blast_presence --batch --genes <searchable panel> --genomes <chunk>
     ((gene, assembly)-scoped merge keeps all existing calls)
  3. verify every chunk genome produced calls
  4. DELETE the genome fasta + blast db for the chunk, mark manifest
     entries archived (searched; local copy removed) so full-manifest
     runs never re-download them

Disk stays bounded at ~one chunk of genomes + dbs.

Usage:
  pixi run python scripts/genes/chunk_runner.py [--chunk-size 40] [--max-chunks N]
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
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
REFS = GENE_DIR / "references_v2" / "panel_references.json"
DB_DIR = GENOME_DIR / "blast_dbs"
PY = str(ROOT / ".pixi/envs/default/bin/python")

MIN_FREE_GB = 120  # abort if free disk drops below this


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def save_manifest(m: dict) -> None:
    MANIFEST.write_text(json.dumps(m, indent=1))


def free_gb() -> float:
    return shutil.disk_usage(ROOT).free / 1e9


def searchable_targets() -> list[str]:
    """Panel genes with reference sequences (wiki-backed panel, §12.6)."""
    import re
    refs = json.loads(REFS.read_text())["genes"]
    def canon(s): return re.sub(r"[-_\s]", "", (s or "").upper())
    panel = {}
    for e in refs:
        if e.get("chicken") or e.get("duck"):
            panel.setdefault(canon(e["symbol"]), e["symbol"])
    wiki = json.loads((ROOT / "web/public/data/wiki_genes.json").read_text())["genes"]
    out = []
    for sym, w in wiki.items():
        if w.get("kind") == "viral":
            continue
        c = canon(sym)
        if c in panel:
            out.append(panel[c])
            panel.pop(c)
    out.extend(panel.values())  # ref'd genes outside the wiki (legacy panel)
    return sorted(set(out))


def run(cmd: list[str], timeout: int = 14400) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd[:4])}…", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.stdout:
        tail = r.stdout.strip().splitlines()[-6:]
        for line in tail:
            print(f"    | {line[:110]}")
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-size", type=int, default=40)
    ap.add_argument("--max-chunks", type=int, default=None)
    args = ap.parse_args()

    todo = json.loads(TODO.read_text())["candidates"]
    progress = {"done": [], "failed": [], "chunks_run": 0}
    if PROGRESS.exists():
        progress = json.loads(PROGRESS.read_text())
    done_acc = set(progress["done"]) | set(progress["failed"])

    remaining = [t for t in todo if t["accession"] not in done_acc]
    chunks = [remaining[i:i + args.chunk_size]
              for i in range(0, len(remaining), args.chunk_size)]
    if args.max_chunks:
        chunks = chunks[:args.max_chunks]
    print(f"{len(remaining)} genomes remaining; running {len(chunks)} chunk(s) "
          f"of <= {args.chunk_size}")

    targets = searchable_targets()
    print(f"searchable targets: {len(targets)} genes")

    for ci, chunk in enumerate(chunks):
        accs = [t["accession"] for t in chunk]
        print(f"\n=== chunk {ci + 1}/{len(chunks)}: {len(accs)} genomes "
              f"(free {free_gb():.0f} GB) ===", flush=True)
        if free_gb() < MIN_FREE_GB:
            print("ABORT: free disk below guard threshold")
            break

        manifest = load_manifest()
        by_acc = {g["accession"]: g for g in manifest["genomes"]}
        # 1. fetch
        for t in chunk:
            acc = t["accession"]
            if acc not in by_acc:
                manifest["genomes"].append({
                    "accession": acc, "species": t["organism"],
                    "common": t.get("common", t["organism"]),
                    "role": f"chromosome-level expansion ({t.get('papers', 0)} papers)",
                    "status": "pending",
                })
                by_acc[acc] = manifest["genomes"][-1]
            save_manifest(manifest)
            manifest = load_manifest()
            by_acc = {g["accession"]: g for g in manifest["genomes"]}
            rec = fetch_genome(by_acc[acc])
            manifest = load_manifest()
            by_acc = {g["accession"]: g for g in manifest["genomes"]}
            by_acc[acc].update(rec)
            save_manifest(manifest)
            if rec["status"] not in ("ok", "cached"):
                print(f"  FETCH FAILED {acc} {t['organism']}: "
                      f"{str(rec.get('error',''))[:80]}")
                progress["failed"].append(acc)
            else:
                print(f"  fetched {acc} {t['organism'][:34]} "
                      f"({rec.get('size_mb', 0)} MB)", flush=True)
            PROGRESS.write_text(json.dumps(progress, indent=1))

        ok_accs = [a for a in accs
                   if {g["accession"]: g for g in load_manifest()["genomes"]}[a]["status"]
                   in ("ok", "cached")]
        if not ok_accs:
            print("  chunk produced no usable genomes; skipping search")
            continue

        # 2. blast the chunk
        r = run([PY, str(ROOT / "scripts/genes/blast_presence.py"),
                 "--batch", "--genes", ",".join(targets),
                 "--genomes", ",".join(ok_accs)], timeout=21600)
        if r.returncode != 0:
            print(f"  BLAST FAILED (exit {r.returncode}): {r.stderr[-300:]}")
            # do not delete genomes of a failed chunk — retryable
            continue

        # 3. verify calls per chunk genome
        have = {}
        for line in CALLS.read_text().splitlines():
            c = json.loads(line)
            have.setdefault(c.get("assembly_accession"), set()).add(c["gene_symbol"])
        missing = [a for a in ok_accs
                   if len(have.get(a, set()) & set(targets)) < len(targets) * 0.9]
        if missing:
            print(f"  WARNING: {len(missing)} genomes with <90% target coverage: "
                  f"{missing[:5]} — keeping their files for inspection")
            ok_accs = [a for a in ok_accs if a not in missing]

        # 4. delete genomes (fasta + blast/diamond dbs live under the
        # accession dir), archive manifest entries
        for acc in ok_accs:
            gdir = GENOME_DIR / acc
            if gdir.exists():
                shutil.rmtree(gdir)
            for p in list(GENOME_DIR.glob(f"{acc}*")):
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
            manifest = load_manifest()
            for g in manifest["genomes"]:
                if g["accession"] == acc:
                    g["status"] = "archived"
                    g["archived_at"] = date.today().isoformat()
            save_manifest(manifest)
            progress["done"].append(acc)
        PROGRESS.write_text(json.dumps(progress, indent=1))
        print(f"  chunk {ci + 1} complete: {len(ok_accs)} searched + archived; "
              f"free {free_gb():.0f} GB", flush=True)

    print(f"\nprogress: {len(progress['done'])} searched+archived, "
          f"{len(progress['failed'])} failed, corpus calls file now "
          f"{sum(1 for _ in open(CALLS))} rows")


if __name__ == "__main__":
    main()
