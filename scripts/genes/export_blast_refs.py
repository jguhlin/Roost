#!/usr/bin/env python3
"""Build the static BLAST reference database (protein sequences).

One entry per (panel gene, key species): the longest protein of that
species in the gene's OrthoFinder orthogroup FASTA. The web app's WASM
blastp kernel (web/wasm-blast) searches this database entirely
client-side — no server, no upload.

Output: web/public/data/blast/panel_refs.json
  [{ g: gene, s: species, n: description, q: sequence }]

Run:  pixi run python scripts/genes/export_blast_refs.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OG_DIR = ROOT / "web" / "public" / "data" / "orthogroups"
MAPPING = ROOT / "web" / "public" / "data" / "gene_orthogroups.json"
SPECIES_MAP = ROOT / "web" / "public" / "data" / "orthofinder" / "species_map.json"
OUT = ROOT / "web" / "public" / "data" / "blast" / "panel_refs.json"

# reference species tier: genomes of research interest, in priority order
PRIORITY = [
    "Gallus_gallus",        # chicken
    "Anas_platyrhynchos",   # mallard
    "Meleagris_gallopavo",  # turkey
    "Taeniopygia_guttata",  # zebra finch
    "Coturnix_japonica",    # Japanese quail
    "Anser_cygnoides",      # swan goose
    "Haliaeetus_albicilla", # white-tailed eagle (raptor)
    "Apteryx_owenii",       # kiwi (palaeognath outgroup)
]


def og_fasta(og: str) -> list[tuple[str, str]]:
    zst = OG_DIR / f"{og}.fa.zst"
    if not zst.exists():
        return []
    txt = subprocess.run(["zstd", "-dc", str(zst)],
                         capture_output=True, text=True, check=True).stdout
    recs, name, buf = [], None, []
    for line in txt.split("\n"):
        if line.startswith(">"):
            if name is not None:
                recs.append((name, "".join(buf)))
            name, buf = line[1:], []
        elif name is not None:
            buf.append(line.strip().upper())
    if name is not None:
        recs.append((name, "".join(buf)))
    return recs


def main() -> int:
    mapping = json.loads(MAPPING.read_text())["genes"]
    smap = {s["label"].split("__")[0]: s for s in json.loads(SPECIES_MAP.read_text())}

    out = []
    for gene, info in sorted(mapping.items()):
        og = info.get("og")
        if not og:
            continue
        recs = og_fasta(og)
        best: dict[str, tuple[str, int]] = {}   # binomial -> (seq, len)
        for head, seq in recs:
            ung = seq.replace("-", "")
            key = head.split("__")[0]
            if key not in best or len(ung) > best[key][1]:
                best[key] = (ung, len(ung))
        for key in PRIORITY:
            if key not in best:
                continue
            seq = best[key][0]
            meta = smap.get(key, {})
            out.append({
                "g": gene,
                "s": meta.get("sci", key.replace("_", " ")),
                "n": f"{meta.get('com', key.replace('_', ' '))} {gene}",
                "q": seq,
            })
        # fall back: if none of the priority species present, keep the longest
        if not any(e["g"] == gene for e in out) and best:
            key, (seq, ln) = max(best.items(), key=lambda kv: kv[1][1])
            meta = smap.get(key, {})
            out.append({
                "g": gene,
                "s": meta.get("sci", key.replace("_", " ")),
                "n": f"{meta.get('com', key.replace('_', ' '))} {gene}",
                "q": seq,
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "meta": {
            "generated": datetime.fromtimestamp(
                __import__("time").time(), tz=timezone.utc).isoformat(timespec="seconds"),
            "n_entries": len(out),
            "species": sorted({e["s"] for e in out}),
            "scoring": "BLOSUM62, affine gaps 11/1 (NCBI blastp defaults), "
                       "Karlin-Altschul E-values (lambda 0.267, K 0.041)",
        },
        "entries": out,
    }))
    genes = sorted({e["g"] for e in out})
    print(f"wrote {OUT.name}: {len(out)} sequences across {len(genes)} genes, "
          f"{len(set(e['s'] for e in out))} species", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
