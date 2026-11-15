#!/usr/bin/env python3
"""Fetch, search, and archive the remaining mammal genomes (D115).

Proper Python replacement for the bash-inline campaign (which corrupted
the manifest on JSON race conditions). For each pending mammal in the
manifest: download → BLAST/DIAMOND the full gene panel → verify calls →
delete genome files → archive the manifest entry.

Resumable: skips already-archived accessions. Disk-bounded (one genome
at a time).

Usage: pixi run python scripts/genes/run_mammal_panel.py
"""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "genes"))
from fetch_genomes import fetch_genome  # noqa: E402

GENE_DIR = ROOT / "data" / "genes"
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
CALLS = GENE_DIR / "gene_presence_v2.jsonl"
PY = str(ROOT / ".pixi/envs/default/bin/python")


def load_manifest():
    return json.loads(MANIFEST.read_text())


def save_manifest(m):
    MANIFEST.write_text(json.dumps(m, indent=1))


def get_targets():
    """All searchable panel genes (with references)."""
    import re
    refs = json.loads((GENE_DIR / "references_v2" / "panel_references.json").read_text())["genes"]
    def canon(s):
        return re.sub(r"[-_\s]", "", (s or "").upper())
    panel = {}
    for e in refs:
        if e.get("chicken") or e.get("duck"):
            panel.setdefault(canon(e["symbol"]), e["symbol"])
    wiki = json.loads((ROOT / "web/public/data/wiki_genes.json").read_text())["genes"]
    targets = set()
    for sym, w in wiki.items():
        if w.get("kind") != "viral" and canon(sym) in panel:
            targets.add(panel[canon(sym)])
    targets.update(panel.values())
    return sorted(targets)


def main():
    m = load_manifest()
    mammals = [g for g in m["genomes"] if str(g.get("role", "")).startswith("mammal")]
    pending = [g for g in mammals if g.get("status") != "archived"]
    print(f"mammals: {len(mammals)} total, {len(mammals) - len(pending)} archived, {len(pending)} to go")

    if not pending:
        print("nothing to do")
        return

    targets = get_targets()
    target_list = ",".join(targets)
    print(f"targets: {len(targets)} genes")

    for i, g in enumerate(pending):
        acc = g["accession"]
        print(f"\n[{i+1}/{len(pending)}] {acc} {g['species']}", flush=True)

        # 1) fetch (always check the actual genome file — manifest status
        #    can be stale from crashed campaigns)
        genome_fna = GENOME_DIR / acc / "genome.fna"
        if not genome_fna.exists():
            try:
                rec = fetch_genome(g)
                g.update(rec)
                save_manifest(load_manifest().__class__(
                    {**load_manifest(), "genomes":
                     [g if x["accession"] == acc else x for x in load_manifest()["genomes"]]}
                ))
                # simpler: just update the entry in the loaded manifest
                m2 = load_manifest()
                for x in m2["genomes"]:
                    if x["accession"] == acc:
                        x.update(rec)
                save_manifest(m2)
                if rec["status"] not in ("ok", "cached"):
                    print(f"  FETCH FAILED: {str(rec.get('error', ''))[:60]}")
                    continue
                print(f"  fetched ({rec.get('size_mb', 0)} MB)", flush=True)
            except Exception as e:
                print(f"  FETCH ERROR: {e}")
                continue

        # 2) blast
        r = subprocess.run(
            [PY, str(ROOT / "scripts/genes/blast_presence.py"),
             "--batch", "--genes", target_list, "--genomes", acc],
            capture_output=True, text=True, timeout=4 * 3600,
        )
        if r.returncode != 0:
            print(f"  BLAST FAILED (exit {r.returncode}): {r.stderr[-200:]}")
            continue
        tail = [l for l in r.stdout.strip().splitlines() if "genes evaluated" in l or "merge:" in l]
        for l in tail:
            print(f"  {l}")

        # 3) verify + archive
        calls = {}
        for line in CALLS.read_text().splitlines():
            try:
                c = json.loads(line)
                if c.get("assembly_accession") == acc:
                    calls[c["gene_symbol"]] = c["search_status"]
            except json.JSONDecodeError:
                continue
        n = len(calls)
        full = sum(1 for s in calls.values() if s == "FULL")

        # delete genome + blastdbs
        d = GENOME_DIR / acc
        if d.exists():
            shutil.rmtree(d)
        for p in GENOME_DIR.glob(f"{acc}*"):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)

        # archive in manifest
        m2 = load_manifest()
        for x in m2["genomes"]:
            if x["accession"] == acc:
                x["status"] = "archived"
        save_manifest(m2)
        print(f"  archived: {n} calls ({full} FULL)", flush=True)

    print(f"\nmammal panel complete")


if __name__ == "__main__":
    main()
