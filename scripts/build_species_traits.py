#!/usr/bin/env python3
"""Species trait capture for the internal workbench (pre-paper-phase).

Assembles a long-format trait table (one row per species × trait) from the
deterministic sources we already have — detections, the mortality phenotype
table, and the susceptibility model — and declares the paper-phase traits
(serology, experimental challenge, viral load, shedding…) in a registry so
the schema is fixed before LLM extraction begins.

Outputs (internal, not exported to the web):
  data/species_traits.parquet      long: scientific_name, taxon_id, trait,
                                   value, value_type, basis, confidence,
                                   evidence
  data/species_traits_wide.csv     convenience pivot
  data/species_trait_registry.json trait definitions + fill status

Run:  pixi run python scripts/build_species_traits.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
DETECTIONS = ROOT / "web" / "public" / "data" / "detections.parquet"
PHENOTYPE = ROOT / "data" / "phenotype_table.parquet"
SUSCEPT = ROOT / "data" / "susceptibility_scores.parquet"
IUCN = ROOT / "web" / "public" / "data" / "species" / "iucn_status.json"
OUT = ROOT / "data" / "species_traits.parquet"
OUT_WIDE = ROOT / "data" / "species_traits_wide.csv"
OUT_REG = ROOT / "data" / "species_trait_registry.json"

TRAIT_REGISTRY = [
    # --- filled deterministically today ---
    ("hpai_detected", "bool", "filled",
     "≥1 HPAI detection record (all sources, deduplicated)"),
    ("h5n1_subtype_detected", "string", "filled",
     "distinct H5/H7Nx subtype strings in the species' detection records "
     "(strain field); clade-level detail (2.3.4.4b) needs paper extraction"),
    ("detection_span_years", "int", "filled",
     "number of distinct calendar years with detections"),
    ("reservoir_status", "enum", "filled",
     "heuristic: suspected_reservoir (≥5 years, ≥100 detections, ≥10 "
     "countries) / detected_recurrent / detected_sporadic"),
    ("susceptibility_class", "enum", "filled",
     "joined from the susceptibility model (susceptibility_scores.parquet)"),
    ("predicted_susceptibility_score", "float", "filled",
     "joined from the susceptibility model"),
    ("tolerance_class", "enum", "filled",
     "phenotype_class from the mortality table: highly_tolerant … "
     "highly_susceptible (requires field mortality data)"),
    ("mortality_proportion", "float", "filled",
     "mortality_count / (mortality + live + harvest) from the phenotype table"),
    ("mortality_score", "int", "filled",
     "ordinal 1–5 of mortality_proportion (see basis in each row)"),
    ("field_mortality_evidence", "int", "filled",
     "mortality_count from field detection records"),
    ("hpai_severe_outcome", "enum", "filled",
     "derived: yes when phenotype_class ∈ {susceptible, highly_susceptible} "
     "and mortality_proportion ≥ 0.5; no when tolerant-class with low "
     "mortality; confidence carried from the phenotype table"),
    ("iucn_status", "enum", "filled",
     "IUCN Red List category (LC/NT/VU/EN/CR/EW/EX/DD) via Wikidata P141; "
     "joined from web/public/data/species/iucn_status.json "
     "(scripts/species/fetch_iucn_status.py)"),
    # --- paper phase (schema fixed, values pending LLM extraction) ---
    ("h5n1_clade_subtype", "string", "pending_papers",
     "clade detail (2.3.4.4b etc.) per species — from paper corpus "
     "(analyses.species_detections) + curated clade references"),
    ("experimental_challenge_available", "bool", "pending_papers",
     "species has an experimental challenge study in the corpus "
     "(inoculation dose, route, outcome)"),
    ("serology_evidence", "enum", "pending_papers",
     "antibody-positive field serology without mortality"),
    ("clinical_score", "int", "pending_papers",
     "ordinal clinical-sign severity from challenge/pathology reports"),
    ("viral_load_score", "int", "pending_papers",
     "ordinal tissue/swan viral load from challenge studies"),
    ("shedding_score", "int", "pending_papers",
     "ordinal shedding intensity from challenge studies"),
    ("shedding_duration_days", "float", "pending_papers",
     "days of detectable shedding (challenge studies)"),
    ("shedding_titre", "string", "pending_papers",
     "peak titre + units from challenge studies"),
    ("low_replication_class", "bool", "pending_papers",
     "reported low/no productive replication in challenge studies"),
    ("low_susceptibility_comparator", "bool", "pending_papers",
     "species used as a low-susceptibility comparator in experiments"),
    ("reservoir_class", "enum", "pending_papers",
     "maintenance/reservoir claims in the literature (complements the "
     "detection-heuristic reservoir_status)"),
]

MORTALITY_BANDS = [(0.05, 1), (0.2, 2), (0.5, 3), (0.8, 4)]


def mortality_ordinal(p: float) -> int:
    for hi, lvl in MORTALITY_BANDS:
        if p < hi:
            return lvl
    return 5


def clean_subtypes(strains: list[str]) -> list[str]:
    out = set()
    for s in strains:
        if not s:
            continue
        for m in re.findall(r"h\dn\d(?:\s+(?:lpai|hpai))?", s, flags=re.I):
            out.add(m.upper().replace(" LPAI", " (LPAI)").replace(" HPAI", " (HPAI)"))
    return sorted(out)


def main() -> int:
    det = pl.read_parquet(DETECTIONS)
    det = det.filter(pl.col("scientific_name").is_not_null())
    det = det.with_columns(
        pl.col("date_iso").dt.year().cast(pl.Int32, strict=False).alias("yr")
    )
    per_species = det.group_by(["scientific_name", "taxon_id"]).agg(
        pl.len().alias("n_det"),
        pl.col("yr").drop_nulls().n_unique().alias("span_years"),
        pl.col("country").drop_nulls().n_unique().alias("n_countries"),
        pl.col("date_iso").min().alias("first"),
        pl.col("date_iso").max().alias("last"),
        pl.col("strain").drop_nulls().unique().alias("strains"),
    )
    phen = pl.read_parquet(PHENOTYPE).select(
        ["scientific_name", "mortality_count", "live_count", "harvest_count",
         "mortality_rate", "phenotype_class", "confidence"]
    )
    susc = pl.read_parquet(SUSCEPT).select(
        ["scientific_name", "susceptibility_score", "susceptibility_class"]
    )
    iucn_by: dict[str, str] = {}
    if IUCN.exists():
        iucn_by = json.loads(IUCN.read_text()).get("status", {})
    else:
        print(f"warning: {IUCN} not found — iucn_status trait will be empty "
              f"(run scripts/species/fetch_iucn_status.py first)")

    rows = []  # (sci, taxon_id, trait, value, value_type, basis, confidence, evidence)

    def add(sci, tid, trait, value, vtype, basis, conf, evidence):
        rows.append({"scientific_name": sci, "taxon_id": tid, "trait": trait,
                     "value": value, "value_type": vtype, "basis": basis,
                     "confidence": conf, "evidence": evidence})

    phen_by = {r["scientific_name"]: r for r in phen.iter_rows(named=True)}
    susc_by = {r["scientific_name"]: r for r in susc.iter_rows(named=True)}

    for r in per_species.iter_rows(named=True):
        sci, tid = r["scientific_name"], r["taxon_id"]
        ev = (f"{r['n_det']} detections {str(r['first'])[:10]}…{str(r['last'])[:10]}, "
              f"{r['n_countries']} countries")
        add(sci, tid, "hpai_detected", "yes", "bool", "detection records",
            "high", ev)
        subs = clean_subtypes(r["strains"])
        if subs:
            add(sci, tid, "h5n1_subtype_detected", ", ".join(subs), "string",
                "detection strain field", "high",
                f"subtypes: {', '.join(subs[:6])}")
        add(sci, tid, "detection_span_years", r["span_years"], "int",
            "detection records", "high", ev)
        if r["span_years"] >= 5 and r["n_det"] >= 100 and r["n_countries"] >= 10:
            status = "suspected_reservoir"
        elif r["span_years"] >= 3 or r["n_det"] >= 20:
            status = "detected_recurrent"
        else:
            status = "detected_sporadic"
        add(sci, tid, "reservoir_status", status, "enum",
            "heuristic on span/count/geography", "medium", ev)

        if sci in susc_by:
            s = susc_by[sci]
            add(sci, tid, "susceptibility_class", s["susceptibility_class"],
                "enum", "susceptibility model", "model", "see model docs")
            add(sci, tid, "predicted_susceptibility_score",
                s["susceptibility_score"], "float", "susceptibility model",
                "model", "see model docs")

        if sci in iucn_by:
            add(sci, tid, "iucn_status", iucn_by[sci], "enum",
                "IUCN Red List via Wikidata P141", "high",
                f"category {iucn_by[sci]} (preferred statement; see "
                f"fetch_iucn_status.py meta)")

        if sci in phen_by:
            p = phen_by[sci]
            total = (p["mortality_count"] or 0) + (p["live_count"] or 0) \
                    + (p["harvest_count"] or 0)
            prop = p["mortality_rate"]
            evp = (f"field counts: {p['mortality_count']} dead / "
                   f"{p['live_count']} live / {p['harvest_count']} harvested")
            add(sci, tid, "field_mortality_evidence", p["mortality_count"],
                "int", "field detection records", p["confidence"], evp)
            if prop is not None:
                add(sci, tid, "mortality_proportion", round(prop, 3), "float",
                    "mortality/(mortality+live+harvest)", p["confidence"], evp)
                add(sci, tid, "mortality_score", mortality_ordinal(prop),
                    "int", f"ordinal of mortality_proportion "
                           f"(1:<5%, 2:<20%, 3:<50%, 4:<80%, 5:≥80%)",
                    p["confidence"], f"proportion={prop:.3f}")
            add(sci, tid, "tolerance_class", p["phenotype_class"], "enum",
                "phenotype table (mortality-derived)", p["confidence"], evp)
            # derived severe outcome
            pc = p["phenotype_class"]
            if pc in ("susceptible", "highly_susceptible") and prop is not None \
                    and prop >= 0.5:
                add(sci, tid, "hpai_severe_outcome", "yes", "enum",
                    "derived: susceptible class + mortality ≥ 50%",
                    p["confidence"], f"phenotype_class={pc}, proportion={prop:.2f}")
            elif pc in ("tolerant", "highly_tolerant") and prop is not None \
                    and prop < 0.2:
                add(sci, tid, "hpai_severe_outcome", "no", "enum",
                    "derived: tolerant class + mortality < 20%",
                    p["confidence"], f"phenotype_class={pc}, proportion={prop:.2f}")

    df = pl.DataFrame(rows)
    df.write_parquet(OUT)
    wide = df.pivot(on="trait", index=["scientific_name", "taxon_id"],
                    values="value", aggregate_function="first")
    wide.write_csv(OUT_WIDE)

    fill = (df.group_by("trait").len()
              .sort("len", descending=True)
              .rename({"len": "n_species"}).to_dicts())
    OUT_REG.write_text(json.dumps({
        "generated": datetime.fromtimestamp(
            __import__("time").time(), tz=timezone.utc).isoformat(timespec="seconds"),
        "traits": [
            {"trait": t, "value_type": vt, "status": st, "definition": d,
             "n_species": next((f["n_species"] for f in fill if f["trait"] == t), 0)}
            for t, vt, st, d in TRAIT_REGISTRY
        ],
    }, indent=2))
    print(f"species_traits: {df.height} rows over {df['scientific_name'].n_unique()} "
          f"species × {df['trait'].n_unique()} traits")
    for f in fill:
        print(f"  {f['trait']:36} {f['n_species']:4}")
    pending = [t for t, _, st, _ in TRAIT_REGISTRY if st == "pending_papers"]
    print(f"paper-phase traits (schema declared, values pending): "
          f"{len(pending)} — see registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
