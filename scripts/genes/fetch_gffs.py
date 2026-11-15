#!/usr/bin/env python3
"""
Fetch NCBI GFF3 annotations for the panel genomes, bgzip + tabix them,
and stage for the igv.js annotation overlay track (D35).

Per genome:
  1. Resolve the FTP path via NCBI Datasets API (assembly name)
  2. Download {acc}_genomic.gff.gz
  3. bgzip -c (force BGZF) + tabix -p gff → queryable by igv range requests
  4. Symlink into web/public/data/genomes/{acc}/

Usage: pixi run python scripts/genes/fetch_gffs.py [--acc GCF_x]
"""

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOMES_DIR = ROOT / "data" / "genomes"
WEB_GENOMES = ROOT / "web" / "public" / "data" / "genomes"
BIN = ROOT / ".pixi" / "envs" / "default" / "bin"

DATASETS_API = "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/{acc}/dataset_report"
UA = "Roost/0.1 (research portal; genome annotations for igv overlay)"


def resolve_ftp(acc: str):
    """Assembly name via NCBI Datasets API → FTP path."""
    url = DATASETS_API.format(acc=acc)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except Exception as e:
        print(f"  API failed: {e}")
        return None
    try:
        rep = d["reports"][0]
        acc_node = rep["accession"]
        name = rep["assembly_info"]["assembly_name"]
    except (KeyError, IndexError):
        return None
    prefix = acc.split("_")[0]                     # GCF | GCA
    num = acc.split("_")[1].split(".")[0]          # 004027225
    num = num.zfill(9)
    a, b, c = num[:3], num[3:6], num[6:]
    safe = name.replace(" ", "_").replace(",", "").replace("#", "")
    return (f"https://ftp.ncbi.nlm.nih.gov/genomes/all/{prefix}/{a}/{b}/{c}/"
            f"{acc}_{safe}/{acc}_{safe}_genomic.gff.gz")


def fetch_gff(acc: str):
    gdir = GENOMES_DIR / acc
    final = gdir / "annotation.gff.bgz"
    tbi = gdir / "annotation.gff.bgz.tbi"
    if final.exists() and tbi.exists():
        return "cached"

    url = resolve_ftp(acc)
    if not url:
        return "no-ftp-path"
    raw = gdir / "_raw.gff.gz"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(raw, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        return f"download failed: {str(e)[:80]}"

    env = {**os.environ, "PATH": str(BIN) + ":" + os.environ.get("PATH", ""), "LC_ALL": "C"}
    with open(final, "wb") as out:
        p1 = subprocess.run(
            "{ gzip -dc %s | grep '^#'; gzip -dc %s | grep -v '^#' | sort -t \"$(printf '\\t')\" -k1,1 -k4,4n; } | %s -c"
            % (str(raw), str(raw), str(BIN / "bgzip")),
            shell=True, stdout=out, env=env)
    subprocess.run([str(BIN / "tabix"), "-f", "-p", "gff", str(final)],
                   capture_output=True, env=env)
    raw.unlink(missing_ok=True)
    if final.exists() and (gdir / "annotation.gff.bgz.tbi").exists():
        return "ok"
    return "bgzip/tabix failed"


def stage_web(acc: str):
    wdir = WEB_GENOMES / acc
    wdir.mkdir(parents=True, exist_ok=True)
    for fname in ("annotation.gff.bgz", "annotation.gff.bgz.tbi"):
        src = GENOMES_DIR / acc / fname
        dst = wdir / fname
        if not src.exists():
            # Data-side file was pruned (e.g. KEEP_GENOMES archiving) —
            # remove the now-dangling public link instead of leaving it.
            # Dangling symlinks crash `vite build`'s public-dir copy step.
            if dst.is_symlink() and not dst.exists():
                dst.unlink()
            continue
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        os.symlink(os.path.relpath(src, wdir), dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acc", default=None)
    args = ap.parse_args()

    genomes = json.loads((GENOMES_DIR / "genomes.json").read_text())["genomes"]
    ok = fail = 0
    for g in genomes:
        # "archived" included: KEEP_GENOMES zstd-archived genomes still have
        # fetchable annotations (2bit/gff staging is independent of FASTA state)
        if g["status"] not in ("ok", "cached", "archived"):
            continue
        if args.acc and g["accession"] != args.acc:
            continue
        acc = g["accession"]
        res = fetch_gff(acc)
        print(f"{acc} ({g.get('common', g['species'])[:20]:20s}): {res}", flush=True)
        if res in ("ok", "cached"):
            stage_web(acc)
            ok += 1
        else:
            fail += 1
    print(f"\n{ok} staged, {fail} failed")


if __name__ == "__main__":
    main()
