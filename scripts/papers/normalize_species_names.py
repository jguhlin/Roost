#!/usr/bin/env python3
"""Species alias map + name normalization for LLM extractions.

LLM phenotype/gene extraction emits whatever name the paper used
("chicken", "Gallus gallus domesticus", "mallard duck"). This builds a
canonical alias map and normalizes extractions to scientific names.

Sources (merged in priority order):
  1. our species table (scientific + common names, NCBI-backed)
  2. NCBI taxdump names.dmp (synonyms, common, genbank-common, includes)
  3. trinomial→species rollup ("Gallus gallus domesticus" → "Gallus gallus")
  4. curated HPAI-context entries (data/papers/species_alias_curated.json)

Outputs:
  data/papers/species_alias_map.json   {alias_lower: {canonical, method}}
  normalization of data/papers/paper_species_traits.parquet
    (+ species_norm, norm_method columns) and an unresolved-names report
  data/papers/species_alias_unresolved.json  (for manual curation → feed
    back via species_alias_curated.json)

Run:  pixi run python scripts/papers/normalize_species_names.py [--rebuild-map]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
SPECIES_TABLE = ROOT / "data" / "species_table.parquet"
NAMES_DMP = ROOT / "data" / "taxonomy" / "names.dmp"
TRAITS = ROOT / "data" / "papers" / "paper_species_traits.parquet"
ALIAS_MAP = ROOT / "data" / "papers" / "species_alias_map.json"
CURATED = ROOT / "data" / "papers" / "species_alias_curated.json"
UNRESOLVED = ROOT / "data" / "papers" / "species_alias_unresolved.json"

AMBIGUOUS_COMMON = {
    # group-level common names — never silently mapped to one species
    "duck", "goose", "swan", "gull", "raptor", "hawk", "eagle", "owl",
    "sparrow", "finch", "warbler", "shorebird", "wader", "waterfowl",
    "seabird", "poultry", "turkey", "quail", "pigeon", "dove", "crane",
    "heron", "cormorant", "pelican", "tern", "penguin", "parrot",
    "wild bird", "bird", "mammal", "rodent",
}

CURATED_DEFAULTS = {
    "chicken": "Gallus gallus",
    "domestic chicken": "Gallus gallus",
    "gallus gallus domesticus": "Gallus gallus",
    "mallard": "Anas platyrhynchos",
    "mallard duck": "Anas platyrhynchos",
    "domestic duck": "Anas platyrhynchos",   # HPAI literature default
    "mute swan": "Cygnus olor",
    "whooper swan": "Cygnus cygnus",
    "greylag goose": "Anser anser",
    "greylag": "Anser anser",
    "brown rat": "Rattus norvegicus",
    "house mouse": "Mus musculus",
    "laboratory mouse": "Mus musculus",
    "lab mouse": "Mus musculus",
    "ferret": "Mustela putorius furo",
    "domestic ferret": "Mustela putorius furo",
    "american mink": "Neogale vison",
    "mink": "Neogale vison",
    "red fox": "Vulpes vulpes",
    "cattle": "Bos taurus",
    "cow": "Bos taurus",
    "domestic cat": "Felis catus",
    "cat": "Felis catus",
    "dog": "Canis lupus familiaris",
    "domestic dog": "Canis lupus familiaris",
    "human": "Homo sapiens",
    "human s": "Homo sapiens",
    "human patients": "Homo sapiens",
    "human case": "Homo sapiens",
    "humans": "Homo sapiens",
    "pig": "Sus scrofa domesticus",
    "domestic pig": "Sus scrofa domesticus",
    "swine": "Sus scrofa domesticus",
    "horse": "Equus caballus",
    "domestic turkey": "Meleagris gallopavo",
    "wild turkey": "Meleagris gallopavo",
    "japanese quail": "Coturnix japonica",
    "coturnix quail": "Coturnix japonica",
    "bobwhite quail": "Colinus virginianus",
    "zebra finch": "Taeniopygia guttata",
    "mouse": "Mus musculus",
    "rat": "Rattus norvegicus",
    "guinea pig": "Cavia porcellus",
    "hamster": "Mesocricetus auratus",
    "syrian hamster": "Mesocricetus auratus",
    "raccoon dog": "Nyctereutes procyonoides",
    "harbor seal": "Phoca vitulina",
    "south american sea lion": "Otaria flavescens",
    "southern elephant seal": "Mirounga leonina",
    # scientific-name self-maps for mammals absent from the avian table
    "homo sapiens": "Homo sapiens",
    "mus musculus": "Mus musculus",
    "bos taurus": "Bos taurus",
    "vulpes vulpes": "Vulpes vulpes",
    "felis catus": "Felis catus",
    "sus scrofa": "Sus scrofa domesticus",
    "sus scrofa domesticus": "Sus scrofa domesticus",
    "mustela putorius furo": "Mustela putorius furo",
    "otaria flavescens": "Otaria flavescens",
    "mirounga leonina": "Mirounga leonina",
    "phoca vitulina": "Phoca vitulina",
    "neogale vison": "Neogale vison",
    "rattus norvegicus": "Rattus norvegicus",
    "canis lupus familiaris": "Canis lupus familiaris",
    "equus caballus": "Equus caballus",
    "ovis aries": "Ovis aries",
    "capra hircus": "Capra hircus",
    "numida meleagris": "Numida meleagris",
    "coturnix japonica": "Coturnix japonica",
    "gallus gallus domesticus": "Gallus gallus",
    "white leghorn chicken": "Gallus gallus",
    "leghorn chicken": "Gallus gallus",
    "pekin duck": "Anas platyrhynchos domesticus",
    "sheep": "Ovis aries",
    "goat": "Capra hircus",
    "guinea fowl": "Numida meleagris",
    "mustela putorius fero": "Mustela putorius furo",
    "balb/c": "Mus musculus",
    "balb/c mouse": "Mus musculus",
    "balb/c mice": "Mus musculus",
    "c57bl/6": "Mus musculus",
    "c57bl/6 mouse": "Mus musculus",
    "c57bl/6 mice": "Mus musculus",
}



def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).lower().strip()
    return re.sub(r"\s+", " ", s)


def build_map() -> dict:
    alias: dict[str, dict] = {}

    def put(name: str, canonical: str, method: str):
        k = norm(name)
        if k and k not in alias:
            alias[k] = {"canonical": canonical, "method": method}

    # 1. our species table (scientific + common)
    st = pl.read_parquet(SPECIES_TABLE).filter(
        pl.col("rank") == "species")
    sci = st["scientific_name"].to_list()
    for s in sci:
        put(s, s, "scientific")
    com = st.filter(pl.col("common_name").is_not_null())
    for s, c in zip(com["scientific_name"], com["common_name"]):
        if norm(c) not in AMBIGUOUS_COMMON:
            put(c, s, "common_table")

    # 2. taxdump: map synonyms/common names → the taxon's SCIENTIFIC name
    #    (two passes: first scientific names per tax_id, then the aliases)
    sci_by_tax: dict[str, str] = {}
    with NAMES_DMP.open(errors="ignore") as f:
        for line in f:
            parts = [p.strip() for p in line.split("\t|\t")]
            if len(parts) >= 4 and parts[3] == "scientific name":
                sci_by_tax[parts[0]] = parts[1]
    with NAMES_DMP.open(errors="ignore") as f:
        for line in f:
            parts = [p.strip() for p in line.split("\t|\t")]
            if len(parts) < 4:
                continue
            _tax_id, name, _uniq, cls = parts[0], parts[1], parts[2], parts[3]
            canon = sci_by_tax.get(parts[0])
            if not canon:
                continue
            if cls == "synonym":
                put(name, canon, "taxdump_synonym")
            elif cls in ("common name", "genbank common name", "equivalent name"):
                n = norm(name)
                if n not in AMBIGUOUS_COMMON:
                    put(name, canon, "taxdump_common")

    # 3. trinomial → binomial rollup for known species
    sci_set = {norm(s): s for s in sci}
    for k, s in list(sci_set.items()):
        toks = k.split()
        if len(toks) >= 3:
            binom = f"{toks[0]} {toks[1]}"
            if norm(binom) in sci_set:
                put(k, sci_set[norm(binom)], "trinomial_rollup")

    # 4. curated HPAI-context layer (highest priority — overwrite)
    curated = {}
    if CURATED.exists():
        curated = json.loads(CURATED.read_text())
    for k, v in {**CURATED_DEFAULTS, **curated}.items():
        alias[norm(k)] = {"canonical": v, "method": "curated"}

    return alias


def resolve(name: str, alias: dict, sci_set: dict) -> tuple[str, str]:
    """→ (canonical, method). Cleans parentheticals/qualifiers first."""
    candidates = []
    raw = str(name or "").strip()
    # strip trailing parentheticals and bracketed qualifiers, keep both forms
    stripped = re.sub(r"[\(\[][^)\]]*[\)\]]", " ", raw)
    for cand in (raw, stripped,
                 re.sub(r"\b(dairy|domestic|wild|white|pekin|laboratory|lab)\b",
                        " ", stripped, flags=re.I)):
        c = norm(cand)
        if c and c not in candidates:
            candidates.append(c)
            # simple plural fallback
            if c.endswith("s") and not c.endswith("ss"):
                sg = c[:-1]
                if sg not in candidates:
                    candidates.append(sg)
    for k in candidates:
        if k in alias:
            return alias[k]["canonical"], alias[k]["method"]
    # trinomial → binomial rollup on the fly
    for k in candidates:
        toks = k.split()
        if len(toks) >= 3 and f"{toks[0]} {toks[1]}" in sci_set:
            return sci_set[f"{toks[0]} {toks[1]}"], "trinomial_rollup"
        if len(toks) >= 2:
            title = " ".join([toks[0].capitalize(), toks[1]])
            if norm(title) in sci_set:
                return sci_set[norm(title)], "case_fix"
    k0 = candidates[0] if candidates else ""
    toks0 = k0.split()
    if k0 in AMBIGUOUS_COMMON or (any(w in k0 for w in AMBIGUOUS_COMMON)
                                  and len(toks0) <= 2):
        return "", "ambiguous"
    # binomial passthrough: a well-formed Latin name the paper itself used
    # (e.g. mammals outside our avian table) is trusted as its own canon
    if len(toks0) == 2 and all(t.isalpha() for t in toks0) \
            and len(toks0[0]) > 2 and len(toks0[1]) > 3:
        return " ".join([toks0[0].capitalize(), toks0[1]]), "binomial_passthrough"
    return "", "unresolved"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-map", action="store_true")
    args = ap.parse_args()

    if args.rebuild_map or not ALIAS_MAP.exists():
        alias = build_map()
        ALIAS_MAP.parent.mkdir(parents=True, exist_ok=True)
        ALIAS_MAP.write_text(json.dumps(alias, indent=0))
        print(f"alias map: {len(alias)} aliases", file=sys.stderr)
    alias = json.loads(ALIAS_MAP.read_text())
    sci_set = {norm(v["canonical"]): v["canonical"]
               for v in alias.values() if v["method"] == "scientific"}
    st = pl.read_parquet(SPECIES_TABLE).filter(pl.col("rank") == "species")
    for s in st["scientific_name"].to_list():
        sci_set.setdefault(norm(s), s)

    # normalize the phenotype table (drop any stale norm columns first)
    t = pl.read_parquet(TRAITS)
    drop_cols = [c for c in ("species_norm", "norm_method",
                              "species_norm_right", "norm_method_right")
                 if c in t.columns]
    if drop_cols:
        t = t.drop(drop_cols)
    rows = []
    unresolved = Counter()
    for i, r in enumerate(t.iter_rows(named=True)):
        canon, method = resolve(r["name"], alias, sci_set)
        rows.append({"idx0": i,
                     "species_norm": canon or None, "norm_method": method})
        if method in ("unresolved", "ambiguous"):
            unresolved[(r["name"], method)] += 1
    t = t.with_row_index("idx0")
    n = pl.DataFrame(rows).with_columns(pl.col("idx0").cast(pl.Int64))
    t = t.join(n.select(["idx0", "species_norm", "norm_method"]), on="idx0") \
         .drop("idx0")
    t.write_parquet(TRAITS)

    rep = [{"name": k[0], "method": k[1], "count": v}
           for k, v in unresolved.most_common()]
    UNRESOLVED.write_text(json.dumps(rep, indent=1))
    print(f"normalized {t.height} rows: "
          f"{t.filter(pl.col('species_norm').is_not_null()).height} resolved, "
          f"{len(rep)} unresolved/ambiguous names "
          f"(→ species_alias_unresolved.json; add fixes to "
          f"species_alias_curated.json)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
