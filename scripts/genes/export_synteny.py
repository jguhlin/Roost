#!/usr/bin/env python3
"""Export conserved micro-synteny blocks among host-panel genes.

Source: data/genes/gene_presence_v2.parquet — annotation-method rows carry
evidence.location {chromosome, start, end} (no strand). We keep calls on
proper chromosomes only (drop unlocalized/unplaced scaffolds), link gene
pairs co-located within GAP_MB on the same chromosome, and union-find the
links into blocks. A block ships when its members are co-located (>=2 of
them within the gap) in >= MIN_SPECIES species.

Outputs (web/public/data/synteny/):
  blocks.json          conserved blocks + per-species tracks (for #/synteny)
  gene_context.json    per-gene neighbouring panel genes (GeneFullPage card)

Run:  pixi run python scripts/genes/export_synteny.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRESENCE = ROOT / "data" / "genes" / "gene_presence_v2.parquet"
OUT_DIR = ROOT / "web" / "public" / "data" / "synteny"

GAP_MB = 0.5          # max intergenic distance for "co-located"
MAX_SPAN_MB = 2.0      # cap on a segment's total span
MIN_SPECIES = 3       # recurring in >= this many species to ship a block
LINK_MIN_SPECIES = 3   # seed pairs must co-locate in >= this many species
CONTEXT_WINDOW_MB = 2.5
MAX_CONTEXT_SPECIES = 8

CHROM_RE = re.compile(r"^(\d{1,2}[AB]?|[A-Z]\d{1,2}|Z|W|X|Y)$")


def parse_evidence(e):
    if isinstance(e, dict):
        return e
    try:
        return json.loads(e)
    except (TypeError, ValueError):
        return {}


def load_located_rows() -> pd.DataFrame:
    df = pd.read_parquet(PRESENCE)
    df["ev"] = df["evidence"].map(parse_evidence)
    mask = df["ev"].map(
        lambda e: isinstance(e.get("location"), dict) and bool(e["location"].get("chromosome"))
    )
    d = df[mask].copy()
    d["chrom"] = d["ev"].map(lambda e: str(e["location"]["chromosome"]).strip())
    d["start"] = d["ev"].map(lambda e: int(e["location"]["start"]))
    d["end"] = d["ev"].map(lambda e: int(e["location"]["end"]))
    d = d[d["start"] > 0]
    d.loc[d["end"] < d["start"], ["start", "end"]] = d.loc[
        d["end"] < d["start"], ["end", "start"]
    ].values
    proper = d["chrom"].str.fullmatch(CHROM_RE.pattern)
    d = d[proper]
    return d[["species", "assembly_accession", "gene_symbol", "chrom", "start", "end"]]


class UnionFind:
    pass  # (unused — blocks come from recurring segment cores below)


def main() -> int:
    t0 = time.time()
    d = load_located_rows()
    print(f"located rows on proper chromosomes: {len(d):,} "
          f"({d.species.nunique()} species, {d.gene_symbol.nunique()} genes)",
          file=sys.stderr)

    gap = int(GAP_MB * 1e6)
    max_span = int(MAX_SPAN_MB * 1e6)

    # --- per-species segments: genes sorted per chrom, chained within gap
    segs_by_species: dict[str, list[dict]] = defaultdict(list)
    uf = UnionFind()
    links: dict[frozenset, int] = defaultdict(int)  # pair -> n species linked

    for (species, assembly, chrom), g in d.groupby(
        ["species", "assembly_accession", "chrom"], sort=False
    ):
        g = g.sort_values("start")
        genes = [
            {"sym": r.gene_symbol, "start": int(r.start), "end": int(r.end)}
            for r in g.itertuples()
        ]
        seg: list[dict] = []
        seg_hi = None
        seg_lo = None
        for gene in genes:
            if seg and (
                gene["start"] - seg_hi > gap
                or gene["end"] - seg_lo > max_span
            ):
                if len(seg) >= 2:
                    segs_by_species[species].append(
                        {"assembly": assembly, "chrom": chrom, "members": seg}
                    )
                seg, seg_hi, seg_lo = [], None, None
            seg.append(gene)
            seg_hi = max(seg_hi or gene["end"], gene["end"])
            seg_lo = min(seg_lo or gene["start"], gene["start"])
        if len(seg) >= 2:
            segs_by_species[species].append(
                {"assembly": assembly, "chrom": chrom, "members": seg}
            )

    # pair-link counts (species where BOTH co-located in one segment)
    for species, segs in segs_by_species.items():
        seen_pairs = set()
        for seg in segs:
            syms = [m["sym"] for m in seg["members"]]
            for i in range(len(syms)):
                for j in range(i + 1, len(syms)):
                    if syms[i] != syms[j]:
                        seen_pairs.add(frozenset((syms[i], syms[j])))
        for p in seen_pairs:
            links[p] += 1

    # --- blocks from RECURRING SEGMENT CORES:
    # a block is a gene-set that recurs as the co-located core of segments in
    # >= MIN_SPECIES species. Seeded by best-supported pairs, grown by
    # intersecting the gene-sets of the segments that contain the seed.
    # (Union-find is deliberately NOT used: bird chromosomes are broadly
    # syntenic, so transitive linkage chains the whole panel into one blob.)
    seg_list = []
    for species, segs in segs_by_species.items():
        for seg in segs:
            seg_list.append((species, seg))
    seg_syms = [(sp, seg, {m["sym"] for m in seg["members"]}) for sp, seg in seg_list]

    # literature-famous avian immune loci get seed priority over raw support —
    # the ranked pass below fills up with genome-wide high-support pairs first
    CURATED_SEEDS = [
        ("TAP1", "TAP2"), ("TAPBP", "BF2"), ("BF2", "BLB1"), ("BLB1", "BLB2"),
        ("DMA", "DMB1"), ("TLR2A", "TLR2B"), ("TLR1", "TLR2"),
        ("IFITM1", "IFITM3"), ("IFITM2", "IFITM3"), ("IFITM1", "IFITM2"),
        ("MX1", "MX2"), ("CCL4", "CCL5"), ("IL2", "IL21"), ("IFNG", "IL22"),
        ("STAT1", "STAT4"), ("CD28", "CTLA4"), ("CCR2", "CCR5"),
        ("RAG1", "RAG2"), ("IL28RA", "IL10RB"),
    ]
    seeds = [(-1, list(p)) for p in CURATED_SEEDS] + sorted(
        ((n, sorted(p)) for p, n in links.items() if n >= LINK_MIN_SPECIES),
        key=lambda t: (-t[0], t[1]),
    )

    emitted_cores: set[frozenset] = set()
    blocks = []
    for n_support, (ga, gb) in seeds:
        if any(frozenset((ga, gb)) <= core for core in emitted_cores):
            continue  # already covered by an emitted block
        group = [(sp, seg, syms) for sp, seg, syms in seg_syms if {ga, gb} <= syms]
        species_here = {sp for sp, _, _ in group}
        if len(species_here) < MIN_SPECIES:
            continue
        core = set.intersection(*[syms for _, _, syms in group])
        if len(core) < 2:
            core = {ga, gb}
        # re-collect on the tightened core
        group = [(sp, seg, syms) for sp, seg, syms in seg_syms if core <= syms]
        species_here = {sp for sp, _, _ in group}
        if len(species_here) < MIN_SPECIES:
            continue
        # one track per species (the segment with the most core members)
        tracks: dict[str, dict] = {}
        for sp, seg, syms in group:
            cur = tracks.get(sp)
            n_core = len(syms & core)
            if cur is None or n_core > cur["n_core"]:
                tracks[sp] = {
                    "n_core": n_core,
                    "assembly": seg["assembly"],
                    "chrom": seg["chrom"],
                    "members": seg["members"],
                }
        if len(tracks) < MIN_SPECIES:
            continue
        emitted_cores.add(frozenset(core))
        genes = sorted(core)
        lo = min(m["start"] for t in tracks.values() for m in t["members"])
        hi = max(m["end"] for t in tracks.values() for m in t["members"])
        label = "–".join(genes[:3]) + (f" +{len(genes) - 3}" if len(genes) > 3 else "")
        blocks.append(
            {
                "id": "b_" + "_".join(g.lower() for g in genes)[:40],
                "label": label,
                "genes": genes,
                "n_species": len(tracks),
                "span_hint_mb": round((hi - lo) / 1e6, 2),
                "tracks": {
                    sci: {
                        "assembly": t["assembly"],
                        "chrom": t["chrom"],
                        "members": t["members"],
                    }
                    for sci, t in sorted(tracks.items())
                },
            }
        )
        if len(blocks) >= 100:
            break  # keep the explorer focused on the strongest structure

    blocks.sort(key=lambda b: (-b["n_species"], -len(b["genes"]), b["label"]))
    for i, b in enumerate(blocks, 1):
        b["rank"] = i

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": time.strftime("%Y-%m-%d"),
        "source": "gene_presence_v2.parquet (annotation calls; coordinates from NCBI annotation)",
        "gap_mb": GAP_MB,
        "max_span_mb": MAX_SPAN_MB,
        "min_species": MIN_SPECIES,
        "n_species_total": d.species.nunique(),
        "caveat": "Coordinates only from annotated genomes (no strand). "
        "Blocks are recurring co-located core gene-sets across species. "
        "Tracks show host-panel genes only; intergenic regions and non-panel "
        "genes are not drawn to scale.",
        "blocks": blocks,
    }
    (OUT_DIR / "blocks.json").write_text(json.dumps(payload))
    print(f"wrote blocks.json: {len(blocks)} blocks "
          f"({time.time() - t0:.0f}s)", file=sys.stderr)
    for b in blocks[:12]:
        gs = b['genes']
        shown = ', '.join(gs[:6]) + (f' …+{len(gs)-6}' if len(gs) > 6 else '')
        print(f"  {b['label']:24s} [{shown}]  n={b['n_species']}", file=sys.stderr)

    # --- gene context (GeneFullPage): per gene, species where panel
    # neighbours sit within CONTEXT_WINDOW_MB (prefer well-connected rows)
    win = int(CONTEXT_WINDOW_MB * 1e6)
    context: dict[str, list[dict]] = defaultdict(list)
    for gene_sym, g in d.groupby("gene_symbol"):
        rows = []
        for (species, assembly), gg in g.groupby(["species", "assembly_accession"]):
            for r in gg.itertuples():
                nb = d[
                    (d.species == species)
                    & (d.assembly_accession == assembly)
                    & (d.chrom == r.chrom)
                    & (d.gene_symbol != gene_sym)
                    & (d.start < r.end + win)
                    & (d.end > r.start - win)
                ]
                if len(nb):
                    rows.append(
                        {
                            "sci": species,
                            "assembly": assembly,
                            "chrom": r.chrom,
                            "self": [r.start, r.end],
                            "nb": [
                                {"sym": n.gene_symbol, "start": int(n.start), "end": int(n.end)}
                                for n in nb.itertuples()
                            ],
                        }
                    )
        rows.sort(
            key=lambda r: (
                -len(r["nb"]),
                r["sci"] != "Gallus gallus",
                r["sci"] != "Anas platyrhynchos",
                r["sci"],
            )
        )
        if rows:
            context[gene_sym] = rows[:MAX_CONTEXT_SPECIES]
    (OUT_DIR / "gene_context.json").write_text(json.dumps(context))
    print(f"wrote gene_context.json: {len(context)} genes ({time.time() - t0:.0f}s)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
