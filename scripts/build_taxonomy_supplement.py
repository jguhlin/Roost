#!/usr/bin/env python3
"""Build a taxonomy supplement for non-aves-taxonomy species.

The aves_taxonomy.tsv (16,564 species) is the canonical base for profiles,
but two groups of detected species fall outside it:

1. MAMMALS — real spillover hosts (mink, foxes, cats, seals, …). They were
   invisible to species.parquet entirely, so the gene panel runs (mink:
   816 genes searched, 649 FULL) and their detections had no profile row.
2. TAXONOMY-DRIFTED BIRDS — source databases report old binomials
   (Anas penelope, Larus ridibundus, …) that current checklists moved
   (Mareca penelope, Chroicocephalus ridibundus), so the name join fails.

This script queries the NCBI datasets taxonomy API for every binomial
scientific name in our data that does not match aves_taxonomy.tsv,
keeps Mammalia and Aves results (with NCBI's current classification and
taxon_id), and writes data/taxonomy_supplement.tsv.

Rows whose taxon_id already exists in aves_taxonomy.tsv are dropped
(synonym-drifted birds resolve to the same tax_id — no duplicates).

Usage: pixi run python scripts/build_taxonomy_supplement.py
"""

import json
import subprocess
import time
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "taxonomy_supplement.tsv"
GENE_DIR = DATA_DIR / "genes"


def query_ncbi_taxonomy(name: str) -> dict | None:
    """Query NCBI datasets taxonomy API; return classification or None."""
    try:
        r = subprocess.run(
            ["pixi", "run", "datasets", "summary", "taxonomy", "taxon", name,
             "--as-json-lines"],
            capture_output=True, text=True, timeout=120)
        for line in r.stdout.splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            tax = d.get("taxonomy") or {}
            cls = tax.get("classification") or {}
            sp = cls.get("species") or {}
            if not sp.get("id"):
                continue
            return {
                "taxon_id": int(sp["id"]),
                "scientific_name": name,  # queried name (sources use it)
                "common_name": (tax.get("organism") or {}).get("common_name", "")
                               if isinstance(tax.get("organism"), dict) else "",
                "class": (cls.get("class") or {}).get("name", ""),
                "order": (cls.get("order") or {}).get("name", ""),
                "family": (cls.get("family") or {}).get("name", ""),
                "genus": (cls.get("genus") or {}).get("name", ""),
            }
    except Exception:
        return None
    return None


def main():
    import re

    aves = pl.read_csv(DATA_DIR / "aves_taxonomy.tsv", separator="\t")
    aves_names = set(aves["scientific_name"].to_list())
    aves_taxids = set(aves["taxon_id"].unique().to_list())

    # Collect candidate names from every species-bearing source
    names = set()
    det = pl.read_parquet(DATA_DIR / "detections_merged.parquet")
    names |= set(det["scientific_name"].drop_nulls().unique().to_list())
    genomes = pl.read_parquet(DATA_DIR / "genomes.parquet")
    names |= set(genomes["organism_name"].drop_nulls().unique().to_list())
    pq = pl.read_parquet(GENE_DIR / "gene_presence_v2.parquet")
    names |= set(pq["species"].drop_nulls().unique().to_list())

    # Unresolved, plausible binomials only (drops common-name garbage like
    # "Tufted duck" — a separate data-quality issue — and blanks)
    unresolved = sorted(
        n for n in names
        if n not in aves_names and re.match(r"^[A-Z][a-z]+ [a-z]+$", n)
    )
    print(f"{len(names)} total names, {len(unresolved)} unresolved binomials to query")

    # Reuse cached rows where available
    cached = {}
    if OUT.exists():
        for r in pl.read_csv(OUT, separator="\t").to_dicts():
            cached[r["scientific_name"]] = r

    rows = []
    for i, name in enumerate(unresolved):
        if name in cached:
            rows.append(cached[name])
            continue
        r = query_ncbi_taxonomy(name)
        if r:
            rows.append(r)
            print(f"  [{i+1}/{len(unresolved)}] {name:34s} {r['class']:10s} "
                  f"{r['order']}", flush=True)
        else:
            print(f"  [{i+1}/{len(unresolved)}] {name:34s} — no match", flush=True)
        time.sleep(0.4)

    if not rows:
        print("No rows resolved — nothing to write")
        return

    df = pl.DataFrame(rows)
    # Keep only vertebrate classes we profile (Mammalia + Aves)
    df = df.filter(pl.col("class").is_in(["Mammalia", "Aves"]))
    # Drop synonym-drifted birds that resolve to an existing aves tax_id
    before = df.height
    df = df.filter(~pl.col("taxon_id").is_in(list(aves_taxids)))
    dropped = before - df.height
    df = df.unique(subset=["taxon_id"], keep="first").sort("scientific_name")

    df.write_csv(OUT, separator="\t")
    n_mam = df.filter(pl.col("class") == "Mammalia").height
    n_aves = df.filter(pl.col("class") == "Aves").height
    print(f"\nWrote {OUT}: {df.height} species ({n_mam} mammals, {n_aves} birds)")
    if dropped:
        print(f"  ({dropped} synonym-drifted birds resolved to existing aves tax_ids — dropped)")


if __name__ == "__main__":
    main()
