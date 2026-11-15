#!/usr/bin/env python3
"""Map panel genes (host_panel_v2.json) to OrthoFinder orthogroups.

Strategy
--------
1.  Build match patterns per gene:
      - CURATED patterns for all Tier-1 genes (family-discriminating phrases)
      - generic patterns for Tier-2/3: full gene name + symbol token
2.  One pass over Identifiers/SequenceIDs.txt (6.8M lines, 4-gram bucket
    prefilter + word-boundary regex confirmation) -> (species, accession) hits.
3.  One scan of Orthogroups.tsv maps hit accessions -> orthogroup; votes per gene.
4.  Confidence: high (top OG >= 75% of hits, >= 10 species) / medium (>= 50%,
    >= 3 species) / review (split families, weak or no matches).
5.  Chicken symbol cross-check via Identifiers/protein_to_gene/GCF_016699485.2.tsv.

Outputs
-------
  data/orthofinder/gene_to_og.tsv          full review artifact (every gene)
  web/public/data/gene_orthogroups.json    web payload (gene -> OG(s), OG -> genes)

Run:  pixi run python scripts/orthofinder/map_panel_to_og.py
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OF_RUN = ROOT / "orthofinder" / "orthofinder_aves463_root16_20260928"
PANEL = ROOT / "data" / "genes" / "host_panel_v2.json"
OUT_TSV = ROOT / "data" / "orthofinder" / "gene_to_og.tsv"
OUT_JSON = ROOT / "web" / "public" / "data" / "gene_orthogroups.json"

CHICKEN_LABEL = "Gallus_gallus__GCF_016699485.2"

# Hand-curated, family-discriminating patterns for Tier-1 genes.
# Phrases are lowercased; word boundaries are enforced at confirmation time.
CURATED: dict[str, list[str]] = {
    "ANP32A": ["nuclear phosphoprotein 32 family member a", "acidic leucine-rich nuclear phosphoprotein 32 family member a", "anp32a", "pp32", "phapi"],
    "ANP32B": ["nuclear phosphoprotein 32 family member b", "anp32b"],
    "ANP32E": ["nuclear phosphoprotein 32 family member e", "anp32e"],
    "DDX58": ["rig-i", "ddx58"],
    "DHX58": ["lgp2", "dhx58", "dexh-box helicase 58"],
    "IFIH1": ["mda5", "ifih1", "melanoma differentiation-associated protein 5", "interferon induced with helicase c domain 1"],
    "IFIT5": ["ifit5", "tetratricopeptide repeats 5", "interferon-induced protein 57"],
    "IFITM1": ["ifitm1", "interferon-induced transmembrane protein 1"],
    "IFITM3": ["ifitm3", "interferon-induced transmembrane protein 3"],
    "IFNAR1": ["ifnar1", "interferon alpha/beta receptor 1", "interferon-alpha/beta receptor 1"],
    "MAVS": ["mavs", "mitochondrial antiviral signaling", "ips-1", "cardif"],
    "MX1": ["mx1", "gtp-binding protein mx"],
    "OASL": ["oasl", "oligoadenylate synthase-like", "oligoadenylate synthetase-like", "oligoadenylate synthase like"],
    "PLAU": ["plau", "urokinase-type plasminogen activator", "u-plasminogen activator", "urokinase plasminogen activator"],
    "RNASEL": ["rnasel", "ribonuclease l", "rnase l"],
    "RNF135": ["rnf135", "ring finger protein 135", "riplet"],
    "STAT1": ["stat1", "activator of transcription 1", "transcription factor stat1"],
    "STAT2": ["stat2", "activator of transcription 2", "transcription factor stat2"],
}

# Manual overrides applied after automatic voting. Fill from the review list.
CURATED_OVERRIDES: dict[str, dict] = {
    # IFITM1/IFITM3: OrthoFinder does not separate the recently-duplicated IFITM
    # cluster; most species' IFITM1- and IFITM3-annotated proteins co-cluster in
    # OG0016003 (chicken IFITM1 NP_001336988 is there; chicken IFITM3
    # NP_001336990 falls in OG0015728). Both panel genes point at the union OG.
    "IFITM1": {"og": "OG0016003", "note": "IFITM1/IFITM3 cluster not fully separated; OG spans both annotations"},
    "IFITM3": {"og": "OG0016003", "note": "IFITM1/IFITM3 cluster not fully separated; OG spans both annotations"},
}


def build_patterns(panel_genes: list[dict]):
    """Return (patterns, short_symbols):
    patterns: list of (gene, phrase_lower) — matched with \\b...\\b confirmation
    short_symbols: dict token -> set(genes) for symbols <= 4 chars (exact token match)
    """
    patterns: list[tuple[str, str]] = []
    short_symbols: dict[str, set[str]] = collections.defaultdict(set)
    seen: set[tuple[str, str]] = set()

    def add(gene: str, phrase: str):
        phrase = phrase.strip().lower()
        if len(phrase) >= 4 and (gene, phrase) not in seen:
            seen.add((gene, phrase))
            patterns.append((gene, phrase))

    for g in panel_genes:
        sym = g["symbol"]
        tiers_patterns = CURATED.get(sym)
        if tiers_patterns:
            for p in tiers_patterns:
                add(sym, p)
            if sym.lower() in tiers_patterns or len(sym) > 4:
                pass
            if len(sym) <= 4 and sym.lower() not in tiers_patterns:
                short_symbols[sym.lower()].add(sym)
        else:
            # generic: symbol token + full name + aliases
            if len(sym) <= 4:
                short_symbols[sym.lower()].add(sym)
            else:
                add(sym, sym)
            name = (g.get("name") or "").strip()
            if name and name.lower() != sym.lower() and len(name) >= 4:
                add(sym, name)
            for al in g.get("aliases") or []:
                al = al.strip()
                if al:
                    if len(al) <= 4:
                        short_symbols[al.lower()].add(sym)
                    else:
                        add(sym, al)
    return patterns, dict(short_symbols)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--of-run", type=Path, default=OF_RUN)
    ap.add_argument("--panel", type=Path, default=PANEL)
    args = ap.parse_args()

    t0 = time.time()
    run = args.of_run

    # ---- species registry -------------------------------------------------
    species: dict[str, str] = {}  # of_id -> column label
    for line in (run / "Identifiers" / "SpeciesIDs.txt").read_text().splitlines():
        sid, rest = line.split(": ", 1)
        species[sid] = rest.replace(".faa", "").strip()

    # ---- panel ------------------------------------------------------------
    panel = json.loads(args.panel.read_text())
    genes = panel["genes"]
    gene_meta = {g["symbol"]: g for g in genes}
    patterns, short_symbols = build_patterns(genes)

    # phrase prefilter: first-4-chars bucket
    bucket: dict[str, list[int]] = collections.defaultdict(list)
    confirm_re: dict[int, re.Pattern] = {}
    for i, (gene, phrase) in enumerate(patterns):
        bucket[phrase[:4]].append(i)
        confirm_re[i] = re.compile(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])")

    # ---- pass 1: SequenceIDs -> hits --------------------------------------
    hits: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    tok_split = re.compile(r"[^a-z0-9]+")
    n_lines = 0
    with open(run / "Identifiers" / "SequenceIDs.txt") as f:
        for line in f:
            n_lines += 1
            iid, rest = line.split(": ", 1)
            low = rest.lower()
            # short-symbol tokens
            if short_symbols:
                for tok in tok_split.split(low):
                    gs = short_symbols.get(tok)
                    if gs:
                        acc = rest.split(" ")[0]
                        col = species[iid.split("_")[0]]
                        for g in gs:
                            hits[g].append((col, acc))
            # phrase bucket
            grams = set()
            for i in range(len(low) - 3):
                grams.add(low[i : i + 4])
            cands: set[int] = set()
            for gram in grams:
                lst = bucket.get(gram)
                if lst:
                    cands.update(lst)
            if cands:
                acc = rest.split(" ")[0]
                col = species[iid.split("_")[0]]
                for i in cands:
                    if confirm_re[i].search(low):
                        hits[patterns[i][0]].append((col, acc))
    print(f"[1] SequenceIDs: {n_lines} lines, {len(hits)} genes with hits "
          f"({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- pass 1b: symbol anchors from protein_to_gene maps --------------------
    # 462/463 assemblies carry gene-SYMBOL style ids (gene-RNASEL); LOC ids are
    # skipped. Anchors genes whose product text is missing/unhelpful (e.g. RNASEL).
    p2g_dir = run / "Identifiers" / "protein_to_gene"
    label_by_asm: dict[str, str] = {}
    for lab in species.values():
        label_by_asm[lab.split("__")[1]] = lab
    symset: dict[str, set[str]] = collections.defaultdict(set)  # UPPER sym -> genes
    for sym, g in gene_meta.items():
        symset[sym.upper()].add(sym)
        for al in g.get("aliases") or []:
            if al.strip():
                symset[al.strip().upper()].add(sym)
    loc_re = re.compile(r"^LOC\d+$", re.I)
    n_anchor = 0
    for path in sorted(p2g_dir.glob("*.tsv")):
        col = label_by_asm.get(path.stem)
        if not col:
            continue
        with open(path) as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                gid = parts[1].removeprefix("gene-")
                if not gid or loc_re.match(gid):
                    continue
                genes_hit = symset.get(gid.upper())
                if genes_hit:
                    n_anchor += 1
                    for g in genes_hit:
                        hits[g].append((col, parts[0]))
    print(f"[1b] symbol anchors: {n_anchor} protein hits "
          f"({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- pass 2: Orthogroups.tsv -> og_of ---------------------------------
    need: dict[str, set[str]] = collections.defaultdict(set)
    for lst in hits.values():
        for col, acc in lst:
            need[col].add(acc)

    og_of: dict[tuple[str, str], str] = {}
    with open(run / "Results_Aves463_Root16" / "Orthogroups" / "Orthogroups.tsv") as f:
        header = f.readline().rstrip("\n").split("\t")[1:]
        for row in f:
            parts = row.rstrip("\n").split("\t")
            og = parts[0]
            for i, cell in enumerate(parts[1:]):
                if cell:
                    col = header[i]
                    s = need.get(col)
                    if s:
                        for a in cell.split(","):
                            a = a.strip()
                            if a in s:
                                og_of[(col, a)] = og
    print(f"[2] Orthogroups: {len(og_of)} hit proteins mapped to OGs "
          f"({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- votes -------------------------------------------------------------
    chicken_acc_by_og: dict[str, set[str]] = collections.defaultdict(set)
    chi_idx = header.index(CHICKEN_LABEL)
    rows: dict[str, dict] = {}
    for g, lst in hits.items():
        votes: collections.Counter = collections.Counter()
        for col, acc in lst:
            og = og_of.get((col, acc))
            if og:
                votes[og] += 1
        n_hits = len(lst)
        n_species = len({c for c, _ in lst})
        mapped = sum(votes.values())
        top_og, top_n = (votes.most_common(1)[0] if votes else (None, 0))
        frac = (top_n / mapped) if mapped else 0.0
        if votes and frac >= 0.75 and n_species >= 10:
            conf = "high"
        elif votes and frac >= 0.50 and n_species >= 3:
            conf = "medium"
        else:
            conf = "review"
        if g in CURATED_OVERRIDES:
            o = CURATED_OVERRIDES[g]
            top_og, conf = o["og"], "curated"
        rows[g] = {
            "symbol": g, "tier": gene_meta[g].get("tier"),
            "category": gene_meta[g].get("category"),
            "n_hits": n_hits, "n_species_hit": n_species,
            "primary_og": top_og, "primary_frac": round(frac, 3),
            "top_ogs": votes.most_common(3), "confidence": conf,
        }
        if top_og:
            chicken_acc_by_og[top_og]  # ensure key

    # genes with zero hits at all -> review rows
    for g in gene_meta:
        if g not in rows:
            rows[g] = {
                "symbol": g, "tier": gene_meta[g].get("tier"),
                "category": gene_meta[g].get("category"),
                "n_hits": 0, "n_species_hit": 0, "primary_og": None,
                "primary_frac": 0.0, "top_ogs": [], "confidence": "review",
            }

    # ---- chicken symbol cross-check ---------------------------------------
    wanted_ogs = {r["primary_og"] for r in rows.values() if r["primary_og"]}
    chicken_col_accs: dict[str, set[str]] = collections.defaultdict(set)
    with open(run / "Results_Aves463_Root16" / "Orthogroups" / "Orthogroups.tsv") as f:
        f.readline()
        for row in f:
            parts = row.rstrip("\n").split("\t")
            og = parts[0]
            if og in wanted_ogs:
                cell = parts[1:][chi_idx] if len(parts) > chi_idx + 1 else ""
                if cell:
                    chicken_col_accs[og] = {a.strip() for a in cell.split(",")}

    p2g_path = run / "Identifiers" / "protein_to_gene" / "GCF_016699485.2.tsv"
    chicken_sym: dict[str, str] = {}
    if p2g_path.exists():
        for line in p2g_path.read_text().splitlines():
            acc, gene_id = line.split("\t")[:2]
            chicken_sym[acc] = gene_id.removeprefix("gene-").upper()

    sym_aliases: dict[str, set[str]] = collections.defaultdict(set)
    for sym, g in gene_meta.items():
        sym_aliases[sym.upper()].add(sym.upper())
        for al in g.get("aliases") or []:
            sym_aliases[sym.upper()].add(al.upper())

    for r in rows.values():
        og = r["primary_og"]
        if not og:
            r["chicken_check"] = "no-og"
            continue
        accs = chicken_col_accs.get(og, set())
        syms = {chicken_sym.get(a) for a in accs} - {None}
        want = sym_aliases[r["symbol"].upper()]
        if not syms:
            r["chicken_check"] = "no-chicken-data" if not accs else "no-symbol-map"
        elif syms & want:
            r["chicken_check"] = "agree"
        else:
            r["chicken_check"] = f"disagree:{','.join(sorted(syms))[:60]}"

    # ---- write outputs ------------------------------------------------------
    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_TSV, "w") as f:
        f.write("symbol\ttier\tcategory\tn_hits\tn_species_hit\tprimary_og\t"
                "primary_frac\ttop_ogs\tconfidence\tchicken_check\n")
        for r in sorted(rows.values(), key=lambda x: ({"high": 0, "curated": 0, "medium": 1, "review": 2}[x["confidence"]], x["symbol"])):
            tops = ";".join(f"{og}:{n}" for og, n in r["top_ogs"]) or "-"
            f.write(f"{r['symbol']}\t{r['tier']}\t{r['category'] or ''}\t{r['n_hits']}\t"
                    f"{r['n_species_hit']}\t{r['primary_og'] or '-'}\t{r['primary_frac']}\t"
                    f"{tops}\t{r['confidence']}\t{r['chicken_check']}\n")
    print(f"[3] wrote {OUT_TSV} ({time.time()-t0:.0f}s)", file=sys.stderr)

    conf_counts = collections.Counter(r["confidence"] for r in rows.values())
    print("confidence:", dict(conf_counts), file=sys.stderr)
    review = [r["symbol"] for r in rows.values() if r["confidence"] == "review"]
    print(f"review ({len(review)}):", ", ".join(sorted(review)[:60]), file=sys.stderr)

    # web payload
    og_to_genes: dict[str, list[str]] = collections.defaultdict(list)
    web_genes = {}
    for r in rows.values():
        if not r["primary_og"]:
            continue
        web_genes[r["symbol"]] = {
            "tier": r["tier"],
            "confidence": r["confidence"],
            "og": r["primary_og"],
            "og_frac": r["primary_frac"],
            "n_species_hit": r["n_species_hit"],
        }
        og_to_genes[r["primary_og"]].append(r["symbol"])
    payload = {
        "meta": {
            "panel_version": panel.get("panel_version"),
            "source": "orthofinder_aves463_root16_20260928",
            "generated": time.strftime("%Y-%m-%d"),
            "n_genes_mapped": len(web_genes),
            "n_ogs": len(og_to_genes),
        },
        "genes": web_genes,
        "og_to_genes": {og: sorted(syms) for og, syms in og_to_genes.items()},
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False))
    print(f"[4] wrote {OUT_JSON}: {len(web_genes)} genes -> {len(og_to_genes)} OGs "
          f"({time.time()-t0:.0f}s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
