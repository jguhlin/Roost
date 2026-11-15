#!/usr/bin/env python3
"""Build the OrthoFinder species map: 463 OF species labels <-> site taxonomy.

Joins each `SpeciesIDs.txt` label (Genus_species__ACCESSION) to
data/species_table.parquet by scientific name. Emits:
  - data/orthofinder/species_map.parquet   (build artifact)
  - web/public/data/orthofinder/species_map.json  (web payload)

Run:  pixi run python scripts/orthofinder/build_species_map.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OF_RUN = ROOT / "orthofinder" / "orthofinder_aves463_root16_20260928"
SPECIES_IDS = OF_RUN / "Identifiers" / "SpeciesIDs.txt"
SPECIES_TABLE = ROOT / "data" / "species_table.parquet"
OUT_PARQUET = ROOT / "data" / "orthofinder" / "species_map.parquet"
OUT_JSON = ROOT / "web" / "public" / "data" / "orthofinder" / "species_map.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--of-run", type=Path, default=OF_RUN, help="OrthoFinder run dir")
    args = ap.parse_args()

    import pandas as pd

    species_ids = args.of_run / "Identifiers" / "SpeciesIDs.txt"
    rows = []
    for line in species_ids.read_text().splitlines():
        sid, rest = line.split(": ", 1)
        label = rest.replace(".faa", "").strip()
        sci_underscore, asm = label.split("__")
        rows.append(
            {
                "of_id": int(sid),
                "label": label,
                "sci_name": sci_underscore.replace("_", " "),
                "assembly": asm,
            }
        )
    of = pd.DataFrame(rows)

    st = pd.read_parquet(SPECIES_TABLE)
    keep = [
        "taxon_id",
        "scientific_name",
        "common_name",
        "order",
        "family",
        "genus",
        "accession",
        "assembly_level",
    ]
    keep = [c for c in keep if c in st.columns]
    st = st[keep].rename(columns={"scientific_name": "sci_name", "accession": "assembly"})

    # primary join: scientific name; fall back to assembly accession for stragglers
    merged = of.merge(st, on="sci_name", how="left", suffixes=("", "_st"))
    unmatched = merged["taxon_id"].isna()
    if unmatched.any():
        by_asm = st.dropna(subset=["assembly"]).set_index("assembly")
        for idx in merged.index[unmatched]:
            asm = merged.at[idx, "assembly"]
            if asm in by_asm.index:
                rec = by_asm.loc[asm]
                if isinstance(rec, pd.DataFrame):
                    rec = rec.iloc[0]
                for col in keep:
                    tgt = col if col != "scientific_name" else "sci_name"
                    if col != "accession":
                        merged.at[idx, tgt] = rec[col]
        unmatched = merged["taxon_id"].isna()

    merged = merged.drop(columns=[c for c in merged.columns if c.endswith("_st")])
    merged["taxon_id"] = merged["taxon_id"].astype("Int64")

    n_bad = int(unmatched.sum())
    print(f"OF species: {len(merged)}  matched: {len(merged) - n_bad}  unmatched: {n_bad}")
    if n_bad:
        print("Unmatched:", merged.loc[unmatched, ["label", "sci_name", "assembly"]].to_string(index=False))

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {OUT_PARQUET}")

    web = [
        {
            "of_id": int(r.of_id),
            "label": r.label,
            "sci": r.sci_name,
            "com": None if pd.isna(r.common_name) else r.common_name,
            "order": None if pd.isna(r.order) else r.order,
            "family": None if pd.isna(r.family) else r.family,
            "taxon_id": None if pd.isna(r.taxon_id) else int(r.taxon_id),
            "assembly": r.assembly,
        }
        for r in merged.itertuples()
    ]
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(web, ensure_ascii=False))
    print(f"wrote {OUT_JSON} ({len(web)} entries)")

    # ship the rooted species tree for phylogenetic ordering in the UI
    src = args.of_run / "Results_Aves463_Root16" / "Species_Tree" / "SpeciesTree_rooted_node_labels.txt"
    if src.exists():
        dst = OUT_JSON.parent / "species_tree.txt"
        dst.write_text(src.read_text().strip())
        print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
