#!/usr/bin/env python3
"""Fetch real flanking genes for curated synteny blocks (NCBI datasets CLI).

For each interesting block (immune-loci filter) and a few key species per
block, download the GFF3 for that species' exact assembly via the official
`datasets` CLI (accession-pinned), stream-extract the protein-coding genes
around the block window, and emit a compact web payload:

  web/public/data/synteny/flanks.json
    { block_id: { sci: { chrom, seq, lo, hi,
                         genes: [{s, n, t, b, e, o}] } },
      gene_index: { SYMBOL: block_id } }

GFF seqids are NC_*/NZ_* accessions; the target seqid is resolved by finding
the anchor gene (a block member) by symbol, falling back to coordinate
overlap. Slim per-seqid gene lists are cached under
data/synteny/flanks/cache/{acc}.json.gz so reruns are offline.

The cached gene lists also carry strand, used to patch `o` into blocks.json
and gene_context.json (panel coordinates have no strand) — only cached
assemblies gain arrows; others stay strandless.

Run:  pixi run python scripts/genes/fetch_synteny_flanks.py [--dry-run]
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOCKS = ROOT / "web" / "public" / "data" / "synteny" / "blocks.json"
CACHE = ROOT / "data" / "synteny" / "flanks" / "cache"
OUT = ROOT / "web" / "public" / "data" / "synteny" / "flanks.json"

# blocks whose core contains any of these genes get flankers
FAMOUS = {
    "STAT1", "STAT4", "TAP1", "TAP2", "TAPBP", "BF2", "BLB1", "BLB2",
    "RAG1", "RAG2", "CD28", "CTLA4", "ICOS", "IFITM1", "IFITM2", "IFITM3",
    "CCR2", "CCR5", "CCR9", "CCL4", "CCL5", "IL2", "IL21", "IFNG", "IL22",
    "TLR2A", "TLR2B", "MX1", "MX2", "IFIH1", "DPP4", "OASL",
}
SPECIES_PRIORITY = [
    "Gallus gallus",          # chicken
    "Anas platyrhynchos",     # mallard
    "Meleagris gallopavo",    # turkey
    "Taeniopygia guttata",    # zebra finch
    "Coturnix japonica",      # quail
    "Anser cygnoides",        # swan goose
]
SPECIES_PER_BLOCK = 4
PAD_KB = 150

SKIP_BIOTYPE = re.compile(
    r"pseudogene|_rna\b|lnc_rna|linc_rna|misc_rna|antisense|ribozyme|"
    r"scaRNA|vault_rna|srp_rna|tmrna|unconfirmed_cds|transposable_element",
    re.I,
)
SKIP_SYMBOL = re.compile(r"^(LOC\d|MIR|SNOR|RNU|RNA\d|TR[AD]\d|AC\d{6})")
ATTR = re.compile(r"([^;=]+)=([^;]*)")


def gff_genes_for_seqids(gff_path: Path, anchors: dict[str, list[tuple[int, int]]],
                         coords: list[tuple[int, int, int, int]]) -> dict:
    """Two streaming passes over the GFF.

    Pass 1 resolves each anchor symbol (case-insensitive — mouse GFF uses
    'Ifitm1' where the panel says 'IFITM1') to a seqid by coordinate
    agreement. Pass 2 collects every kept gene on the resolved seqids that
    overlaps the wide window (genes earlier in the stream than the anchor
    are included this time).
    """
    anchors_upper = {sym.upper(): (sym, positions) for sym, positions in anchors.items()}
    wide_lo = min(w[2] for w in coords)
    wide_hi = max(w[3] for w in coords)

    seqid_of: dict[str, str] = {}   # panel symbol -> seqid
    target_seqids: set[str] = set()

    def try_anchor(sym: str, name: str, synonyms, start: int, end: int, seqid: str):
        upper = sym.upper()
        hit = anchors_upper.get(upper) or anchors_upper.get(name.upper())
        if hit is None:
            for syn in synonyms:
                hit = anchors_upper.get(syn.upper())
                if hit:
                    break
        if hit is None:
            return
        panel_sym, positions = hit
        if panel_sym in seqid_of:
            return
        for pos in positions:
            if abs(pos[0] - start) < 300_000 and abs(pos[1] - end) < 300_000:
                seqid_of[panel_sym] = seqid
                target_seqids.add(seqid)
                return

    syn_re = re.compile(r"(?:^|,)gene_synonym=([^;,]+)")
    with open(gff_path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9 or parts[2] not in ("gene", "pseudogene"):
                continue
            attrs = dict(ATTR.findall(parts[8]))
            sym = attrs.get("gene") or attrs.get("Name") or ""
            if not sym:
                continue
            synonyms = [s.strip() for s in syn_re.findall(parts[8])]
            try_anchor(sym, attrs.get("Name", ""), synonyms,
                       int(parts[3]), int(parts[4]), parts[0])
            if len(seqid_of) == len(anchors_upper):
                break  # all anchors resolved — skip the rest of the file

    # fallback for unresolved anchors: pick the seqid whose genes most overlap
    # the anchor interval (±300 kb) — handles renamed/shifted anchors
    unresolved = [s for s in anchors if s not in seqid_of]
    if unresolved:
        overlap_counts: dict[tuple[str, str], int] = {}
        for panel_sym in unresolved:
            for pos in anchors[panel_sym]:
                lo, hi = pos[0] - 300_000, pos[1] + 300_000
                with open(gff_path, "rt") as f:
                    for line in f:
                        if line.startswith("#"):
                            continue
                        p = line.rstrip("\n").split("\t")
                        if len(p) < 9 or p[2] not in ("gene", "pseudogene"):
                            continue
                        start, end = int(p[3]), int(p[4])
                        if end >= lo and start <= hi:
                            key = (panel_sym, p[0])
                            overlap_counts[key] = overlap_counts.get(key, 0) + 1
        for (panel_sym, seqid), _n in sorted(overlap_counts.items(),
                                             key=lambda kv: -kv[1]):
            if panel_sym not in seqid_of:
                seqid_of[panel_sym] = seqid
                target_seqids.add(seqid)

    if not target_seqids:
        return {"seqids": {}, "genes": {}}

    out: dict[str, list[dict]] = {}
    with open(gff_path, "rt") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9 or parts[2] not in ("gene", "pseudogene"):
                continue
            seqid = parts[0]
            if seqid not in target_seqids:
                continue
            start, end = int(parts[3]), int(parts[4])
            attrs = dict(ATTR.findall(parts[8]))
            if SKIP_BIOTYPE.search(attrs.get("gene_biotype", "")):
                continue
            sym = attrs.get("gene") or attrs.get("Name") or ""
            if not sym or SKIP_SYMBOL.match(sym):
                continue
            out.setdefault(seqid, []).append(
                {"s": sym, "n": attrs.get("description", sym),
                 "b": start, "e": end, "o": parts[6]}
            )
    return {"seqids": seqid_of,
            "genes": {sid: genes for sid, genes in out.items() if genes}}


def load_assembly(assembly: str, windows: list[dict]) -> dict[str, list[dict]]:
    """Return {seqid: [genes]} for the windows' seqids (cache-first)."""
    cache = CACHE / f"{assembly}.json.gz"
    anchors = {}
    coords = []
    for w in windows:
        anchors.setdefault(w["anchor_sym"], []).append((w["anchor_start"], w["anchor_end"]))
        coords.append((w["lo"], w["hi"], w["lo"] - PAD_KB * 1000, w["hi"] + PAD_KB * 1000))

    if cache.exists():
        with gzip.open(cache, "rt") as f:
            cached = json.load(f)
        # cache format v2 carries the seqid map; v1 (window-limited) is stale
        if isinstance(cached, dict) and "seqids" in cached:
            ok = True
            for w in windows:
                if w["anchor_sym"] not in cached["seqids"]:
                    ok = False
                    break
            if ok:
                return cached

    print(f"  downloading GFF3 for {assembly} (datasets CLI)…", file=sys.stderr)
    with tempfile.TemporaryDirectory(prefix="syntflank_") as tmp:
        tmp = Path(tmp)
        zip_path = tmp / f"{assembly}.zip"
        for attempt in range(3):
            r = subprocess.run(
                ["datasets", "download", "genome", "accession", assembly,
                 "--include", "gff3", "--filename", str(zip_path)],
                capture_output=True, text=True, timeout=1200,
            )
            if r.returncode == 0 and zip_path.exists():
                break
            print(f"    datasets rc={r.returncode}: {(r.stderr or '')[-200:]}",
                  file=sys.stderr)
            time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"datasets download failed for {assembly}")
        with zipfile.ZipFile(zip_path) as z:
            member = next(m for m in z.namelist() if m.endswith(".gff"))
            z.extract(member, tmp)
            gff = tmp / member
        genes = gff_genes_for_seqids(gff, anchors, coords)
        (tmp / member).unlink(missing_ok=True)

    CACHE.mkdir(parents=True, exist_ok=True)
    with gzip.open(cache, "wt") as f:
        json.dump(genes, f)
    print(f"    cached {sum(len(v) for v in genes['genes'].values())} genes "
          f"on {len(genes['genes'])} seqid(s)", file=sys.stderr)
    return genes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="plan only, no fetching")
    args = ap.parse_args()

    blocks = json.loads(BLOCKS.read_text())
    interesting = [b for b in blocks["blocks"] if set(b["genes"]) & FAMOUS]
    print(f"interesting blocks: {len(interesting)}", file=sys.stderr)

    # plan: block -> species -> window spec (anchor = first core member present)
    plan: dict[str, dict[str, dict]] = {}
    for b in interesting:
        picks = [s for s in SPECIES_PRIORITY if s in b["tracks"]]
        picks += [s for s in sorted(b["tracks"]) if s not in picks]
        picks = picks[:SPECIES_PER_BLOCK]
        for sci in picks:
            t = b["tracks"][sci]
            members = sorted(t["members"], key=lambda m: m["start"])
            anchor = members[0]
            core_syms = set(b["genes"])
            if anchor["sym"] not in core_syms:
                anchor = next((m for m in members if m["sym"] in core_syms), anchor)
            plan.setdefault(b["id"], {})[sci] = {
                "assembly": t["assembly"], "chrom": t["chrom"],
                "lo": min(m["start"] for m in members) - PAD_KB * 1000,
                "hi": max(m["end"] for m in members) + PAD_KB * 1000,
                "anchor_sym": anchor["sym"],
                "anchor_start": anchor["start"], "anchor_end": anchor["end"],
                "core": b["genes"],
                "members": t["members"],
            }

    n_asm = len({p["assembly"] for blk in plan.values() for p in blk.values()})
    print(f"windows: {sum(len(v) for v in plan.values())} across {n_asm} assemblies",
          file=sys.stderr)
    if args.dry_run:
        for bid, sps in plan.items():
            lbl = next((b["label"] for b in interesting if b["id"] == bid), bid)
            print(f"  {lbl}: {list(sps)}", file=sys.stderr)
        return 0

    # group windows by assembly for one download per assembly
    by_asm: dict[str, list[dict]] = {}
    for blk in plan.values():
        for sci, w in blk.items():
            by_asm.setdefault(w["assembly"], []).append(w)
    asm_genes: dict[str, dict] = {}
    for acc, ws in sorted(by_asm.items()):
        try:
            asm_genes[acc] = load_assembly(acc, ws)
        except Exception as e:
            print(f"  WARN {acc}: {e}", file=sys.stderr)

    out: dict[str, dict[str, dict]] = {}
    for bid, sps in plan.items():
        for sci, w in sps.items():
            pack = asm_genes.get(w["assembly"], {})
            genes_by_seq = pack.get("genes", {})
            seqid_map = pack.get("seqids", {})
            core_upper = {c.upper() for c in w["core"]}

            # seqid: prefer the symbol+coordinate anchor; fall back to the
            # resolver's seqid map (synonym / coordinate-overlap resolution)
            seq = seqid_map.get(w["anchor_sym"])
            anchor_gff = None
            for g in genes_by_seq.get(seq, []):
                if g["s"].upper() == w["anchor_sym"].upper() and abs(
                    g["b"] - w["anchor_start"]
                ) < 300_000:
                    anchor_gff = g
                    break
            if seq is None:
                print(f"  WARN {bid}/{sci}: anchor {w['anchor_sym']} not located",
                      file=sys.stderr)
                continue

            # drift between our panel coordinates and the current annotation
            # (same assembly, possibly newer annotation release); unknown for
            # overlap-resolved tracks → no translation, flagged unaligned
            aligned = anchor_gff is not None
            offset = (anchor_gff["b"] - w["anchor_start"]) if aligned else 0
            wlo, whi = w["lo"] - PAD_KB * 1000, w["hi"] + PAD_KB * 1000
            # shift the panel-frame window into the GFF (current-annotation) frame
            glo, ghi = wlo + offset, whi + offset
            window = [
                {"s": g["s"], "n": g["n"], "b": g["b"], "e": g["e"], "o": g["o"],
                 "core": g["s"].upper() in core_upper}
                for g in genes_by_seq.get(seq, [])
                if g["e"] >= glo and g["b"] <= ghi
            ]

            # safety net for unaligned windows: if no core symbol landed in the
            # window, the overlap fallback picked a wrong region. Re-resolve by
            # searching the whole assembly for a core symbol; drop if absent.
            if not any(g["core"] for g in window) and not aligned:
                rescue = None
                for sid, genes in genes_by_seq.items():
                    for g in genes:
                        if g["s"].upper() in core_upper:
                            rescue = (sid, g)
                            break
                    if rescue:
                        break
                if rescue:
                    seq, anchor_gff = rescue
                    aligned = True
                    offset = anchor_gff["b"] - w["anchor_start"]
                    mid = (anchor_gff["b"] + anchor_gff["e"]) // 2
                    span = max(w["hi"] - w["lo"], 200_000)
                    glo, ghi = mid - span // 2 - PAD_KB * 1000, mid + span // 2 + PAD_KB * 1000
                    window = [
                        {"s": g["s"], "n": g["n"], "b": g["b"], "e": g["e"], "o": g["o"],
                         "core": g["s"].upper() in core_upper}
                        for g in genes_by_seq.get(seq, [])
                        if g["e"] >= glo and g["b"] <= ghi
                    ]
                    print(f"  RESCUE {bid}/{sci}: re-resolved to {seq} via symbol",
                          file=sys.stderr)
                else:
                    print(f"  WARN {bid}/{sci}: no core symbol in current annotation "
                          f"— window dropped", file=sys.stderr)
                    continue
            # panel genes missing from the GFF (renamed/dropped in the current
            # annotation): translate by the anchor's observed drift so the
            # track stays internally consistent; flagged "tr"
            if aligned:
                present_upper = {g["s"].upper() for g in window}
                for m in w.get("members", []):
                    if m["sym"].upper() in present_upper:
                        continue
                    tb, te = m["start"] + offset, m["end"] + offset
                    if te >= glo and tb <= ghi:
                        window.append({"s": m["sym"], "n": m["sym"], "b": tb, "e": te,
                                       "o": None, "tr": True,
                                       "core": m["sym"].upper() in core_upper})
            if not window:
                continue
            out.setdefault(bid, {})[sci] = {
                "chrom": w["chrom"], "seq": seq, "offset": offset,
                "aligned": aligned,
                "lo": min(g["b"] for g in window), "hi": max(g["e"] for g in window),
                "genes": sorted(window, key=lambda x: x["b"]),
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    n_g = sum(len(s.get("genes", [])) for blk in out.values() for s in blk.values())
    gene_index = {}
    for b in interesting:
        if b["id"] in out:
            for g in b["genes"]:
                gene_index[g] = b["id"]
    out["gene_index"] = gene_index
    OUT.write_text(json.dumps(out))
    print(f"wrote {OUT.name}: {len(out) - 1} blocks, "
          f"{sum(len(v) for k, v in out.items() if k != 'gene_index')} species-windows, {n_g} genes",
          file=sys.stderr)

    patch_strand(asm_genes)
    return 0


def patch_strand(asm_genes: dict[str, dict]) -> None:
    """Copy strand (o) from the cached current-annotation gene lists into
    blocks.json track members and gene_context.json neighbour entries.
    Matches symbol case-insensitively, coordinates nearest (paralogs)."""
    # assembly -> SYMUPPER -> [(mid, strand)]
    lookup: dict[str, dict[str, list[tuple[int, str]]]] = {}
    for acc, pack in asm_genes.items():
        for genes in pack["genes"].values():
            for g in genes:
                lookup.setdefault(acc, {}).setdefault(
                    g["s"].upper(), []).append(
                    ((g["b"] + g["e"]) // 2, g["o"] or "+"))

    def strand_of(acc: str, sym: str, start: int, end: int):
        cands = lookup.get(acc, {}).get(sym.upper())
        if not cands:
            return None
        mid = (start + end) // 2
        best = min(cands, key=lambda c: abs(c[0] - mid))
        return best[1] if abs(best[0] - mid) < 5_000_000 else None

    n_b = n_bc = 0
    if BLOCKS.exists():
        blocks = json.loads(BLOCKS.read_text())
        for b in blocks.get("blocks", []):
            for t in b["tracks"].values():
                for m in t["members"]:
                    o = strand_of(t["assembly"], m["sym"], m["start"], m["end"])
                    if o:
                        m["o"] = o
                        n_b += 1
        BLOCKS.write_text(json.dumps(blocks))

    ctx_path = BLOCKS.parent / "gene_context.json"
    if ctx_path.exists():
        ctx = json.loads(ctx_path.read_text())
        for sym, rows in ctx.items():
            for c in rows:
                o = strand_of(c["assembly"], sym, c["self"][0], c["self"][1])
                if o:
                    c["o"] = o
                    n_bc += 1
                for nb in c["nb"]:
                    o = strand_of(c["assembly"], nb["sym"], nb["start"], nb["end"])
                    if o:
                        nb["o"] = o
                        n_bc += 1
        ctx_path.write_text(json.dumps(ctx))
    print(f"patched strand: {n_b} block members, {n_bc} context genes", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
