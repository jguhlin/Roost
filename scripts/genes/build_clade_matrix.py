#!/usr/bin/env python3
"""Build the precomputed clade matrix for the Clade view (#/clade).

Reads the gene presence calls + the FULL aves taxonomy (not just detected
species), computes per-order presence percentages, and writes a compact
JSON that the Clade page fetches directly — no DuckDB queries needed.

This solves two problems:
1. Taxonomy gap: 40 bird species with genomes searched but no HPAI
   detection are missing from species.parquet and thus invisible to the
   clade view. Using aves_taxonomy.tsv covers all of them.
2. Speed: precomputed JSON loads in <100ms vs 5-10s of DuckDB init + queries.

Usage: pixi run python scripts/genes/build_clade_matrix.py
       (also called by export-all)
"""

import json
from pathlib import Path
from collections import defaultdict

import polars as pl

ROOT = Path(__file__).parent.parent.parent
GENE_DIR = ROOT / "data" / "genes"
TAXONOMY = ROOT / "data" / "aves_taxonomy.tsv"
OUT = ROOT / "web" / "public" / "data" / "clade_matrix.json"


def main():
    # Load gene presence calls
    calls = pl.read_parquet(GENE_DIR / "gene_presence_v2.parquet")

    # Research counts (papers per gene) + curated importance — joined into
    # each gene row so the Clade view can sort by "most researched" and
    # filter to the core gene panel (2026-11 user request).
    # Family-level symbols fold into member genes for the papers sort:
    # members carry max(member, family) — family mentions ⊇ member
    # mentions, so max (never sum) is the honest merge — and the family row
    # is flagged so the sort hides it (members own the ranking).
    FAMILY_FOLD = {
        "POLYMERASE": ["PB2", "PB1", "PA"],
        "IFN": ["IFNA1", "IFNB1", "IFNG"],
    }
    papers = {}
    try:
        ev = json.loads((ROOT / "web" / "public" / "data" / "gene_evidence_counts.json").read_text())
        papers = {g: int(v.get("papers") or 0) for g, v in ev.items()}
    except (OSError, json.JSONDecodeError):
        pass
    importance = {}
    try:
        cat = json.loads((ROOT / "web" / "public" / "data" / "gene_catalogue.json").read_text())
        importance = {g: (v.get("importance") or "standard") for g, v in (cat.get("gene_catalogue") or {}).items()}
    except (OSError, json.JSONDecodeError):
        pass

    # Load FULL taxonomy (all Aves, not just detected species)
    tax = pl.read_csv(TAXONOMY, separator="\t").select([
        "scientific_name", "common_name", "order", "family"
    ])

    # Join: assign taxonomy to every searched species
    searched = calls.select("species").unique()
    with_tax = searched.join(tax.rename({"scientific_name": "species"}), on="species", how="left")

    # Species with valid orders (excludes mammals: they have no aves order)
    bird_species = with_tax.filter(
        pl.col("order").is_not_null() & (pl.col("order") != "")
    )
    n_birds = bird_species.height
    n_excluded = searched.height - n_birds
    print(f"Genome-searched species: {searched.height}")
    print(f"  with aves taxonomy: {n_birds}")
    print(f"  excluded (no order — mammals, unmatched): {n_excluded}")

    # Build species → order map
    sp_order = dict(zip(bird_species["species"], bird_species["order"]))
    sp_family = dict(zip(bird_species["species"], bird_species["family"]))

    # Count species per order (only genome-searched)
    order_n = defaultdict(int)
    for sp in sp_order:
        order_n[sp_order[sp]] += 1

    # Only include orders with ≥3 searched species
    good_orders = {o for o, n in order_n.items() if n >= 3}
    order_n = {o: n for o, n in order_n.items() if o in good_orders}

    # Aggregate: gene × order → n_full
    gene_order_full = defaultdict(lambda: defaultdict(int))
    gene_total_full = defaultdict(int)

    for row in calls.iter_rows(named=True):
        sp = row["species"]
        if row["search_status"] != "FULL":
            continue
        order = sp_order.get(sp)
        if order not in good_orders:
            continue
        gene = row["gene_symbol"]
        gene_order_full[gene][order] += 1
        gene_total_full[gene] += 1

    # Total searched species per order (for denominator)
    order_species = defaultdict(list)
    for sp, o in sp_order.items():
        if o in good_orders:
            order_species[o].append(sp)

    # Build matrix
    total_searched = sum(order_n.values())
    genes = []
    for gene in sorted(gene_order_full.keys()):
        n_full = gene_total_full.get(gene, 0)
        if n_full < 3:
            continue  # skip genes present in <3 species total

        orders_data = {}
        losses = []
        overall_pct = n_full / total_searched if total_searched else 0

        for order in sorted(good_orders, key=lambda o: -order_n[o]):
            full = gene_order_full[gene].get(order, 0)
            n_sp = order_n[order]
            pct = full / n_sp if n_sp else 0
            orders_data[order] = round(pct, 4)
            if pct <= 0.1 and overall_pct >= 0.3:
                losses.append({"order": order, "full": full, "nSpecies": n_sp})

        genes.append({
            "gene": gene,
            "orders": orders_data,
            "losses": losses,
            "nLosses": len(losses),
            "nFull": n_full,
            "nTotal": total_searched,
            "conservation": round(overall_pct, 4),
            "papers": papers.get(gene, 0),
            "importance": importance.get(gene, "standard"),
            **({"family": FAMILY_FOLD[gene]} if gene in FAMILY_FOLD else {}),
        })

    # Order metadata (sorted by species count descending)
    orders_meta = [
        {"name": o, "nSpecies": order_n[o]}
        for o in sorted(good_orders, key=lambda o: -order_n[o])
    ]

    # Fold family paper counts into member rows (max-merge: family mentions
    # ⊇ member mentions — max, never sum) and flag family rows so the
    # "most researched" sort hides them in favour of their members.
    gene_rows = {g["gene"]: g for g in genes}
    for fam, members in FAMILY_FOLD.items():
        frow = gene_rows.get(fam)
        if not frow:
            continue
        for m in members:
            mrow = gene_rows.get(m)
            if mrow:
                mrow["papers"] = max(mrow.get("papers", 0), frow.get("papers", 0))

    result = {
        "_doc": (
            "Precomputed clade matrix: gene × order presence percentages. "
            "Each cell = (# species with FULL match) / (# genome-searched "
            "species in that order). Only orders with ≥3 searched species "
            "included. Clade loss = ≤10% present in an order while ≥30% "
            "present overall. Built from the FULL aves taxonomy, not just "
            "detected species."
        ),
        "orders": orders_meta,
        "genes": genes,
        "totalSearched": total_searched,
        "totalExcluded": n_excluded,
    }

    OUT.write_text(json.dumps(result, separators=(",", ":")))
    n_loss_genes = sum(1 for g in genes if g["nLosses"] > 0)
    print(f"\nMatrix: {len(genes)} genes × {len(orders_meta)} orders")
    print(f"Genes with clade-specific losses: {n_loss_genes}")
    print(f"Orders: {', '.join(o['name'] for o in orders_meta)}")
    print(f"\nWrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
