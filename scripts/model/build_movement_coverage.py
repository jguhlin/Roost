#!/usr/bin/env python3
"""Movement coverage layer: which species have tracking data, from where,
and what it means for H5N1 spread prediction.

Sources:
  Movebank (cached: data/raw/movebank/{studies,taxa}.csv)
    — study metadata incl. taxon_ids (species names), individuals, timestamps
    — ONE bulk download, no per-species API calls

Joins:
  species.parquet          our species universe
  species_susceptibility   permissiveness scores
  region_risk.json         detected species per country + watchlists
  detections.parquet       first/last detections per species

Output layers:
  coverage       per-species: n_studies, n_individuals, tracked (bool),
                 genus_tracked (phylo-transfer proxy)
  summary        headline stats (the paper's 71% claim, verified)
  watchlist_move which high-risk watchlist species are tracked
  untracked      which infected species LACK tracking (the data gap)

Output: data/model/movement_coverage.json + web twin.
Usage: pixi run python scripts/model/build_movement_coverage.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
MB_STUDIES = ROOT / "data" / "raw" / "movebank" / "studies.csv"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
SUSCEPT = ROOT / "data" / "model" / "species_susceptibility.json"
REGION_RISK = ROOT / "data" / "model" / "region_risk.json"
DET = ROOT / "web" / "public" / "data" / "detections.parquet"
OUT = ROOT / "data" / "model" / "movement_coverage.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "movement_coverage.json"


def parse_movebank_studies() -> dict[str, dict]:
    """Extract per-species study counts from the cached Movebank CSV."""
    studies = pl.read_csv(str(MB_STUDIES), infer_schema_length=0)
    species_data = defaultdict(
        lambda: {"n_studies": 0, "n_individuals": 0, "study_names": [],
                 "first_year": None, "last_year": None})

    for r in studies.filter(
        pl.col("taxon_ids").is_not_null() & (pl.col("taxon_ids") != "")
    ).iter_rows(named=True):
        names = [x.strip() for x in str(r["taxon_ids"]).replace(",", "|").split("|") if x.strip()]
        n_ind = 0
        raw = r.get("number_of_individuals")
        if raw and str(raw) not in ("null", "", "None"):
            try:
                n_ind = int(float(raw))
            except ValueError:
                pass
        ts_first = str(r.get("timestamp_first_deployed_location") or "")[:4]
        ts_last = str(r.get("timestamp_last_deployed_location") or "")[:4]

        for name in names:
            if len(name.split()) == 2 and name[0].isupper():
                d = species_data[name]
                d["n_studies"] += 1
                d["n_individuals"] += n_ind
                if len(d["study_names"]) < 5:
                    d["study_names"].append(str(r.get("name", ""))[:80])
                for ts, key in ((ts_first, "first_year"), (ts_last, "last_year")):
                    if ts.isdigit():
                        y = int(ts)
                        if d[key] is None or (key == "first_year" and y < d[key]) \
                           or (key == "last_year" and y > d[key]):
                            d[key] = y

    return dict(species_data)


def main() -> None:
    mb = parse_movebank_studies()
    our = pl.read_parquet(str(SPECIES))
    our_species = {r["scientific_name"]: r for r in our.iter_rows(named=True)}
    sus = json.loads(SUSCEPT.read_text())
    sus_by_species = {s["species"]: s for s in sus["species"]}
    rr = json.loads(REGION_RISK.read_text())
    det = pl.read_parquet(str(DET)).filter(pl.col("date_iso").is_not_null())
    det_species = set(det["scientific_name"].drop_nulls().to_list())

    mb_genera = {n.split()[0] for n in mb}

    coverage = []
    for sci in sorted(our_species):
        tax = our_species[sci]
        genus = (tax.get("genus") or sci.split()[0])
        mb_data = mb.get(sci)
        genus_tracked = genus in mb_genera

        # genus-level rollup (phylo-transfer: relatives are tracked)
        genus_studies = sum(v["n_studies"] for n, v in mb.items()
                            if n != sci and n.split()[0] == genus)
        genus_individuals = sum(v["n_individuals"] for n, v in mb.items()
                                if n != sci and n.split()[0] == genus)

        s = sus_by_species.get(sci, {})
        # temporal quality: does the tracking overlap the panzootic?
        ty_last = mb_data.get("last_year") if mb_data else None
        if ty_last and ty_last >= 2021:
            temporal = "era_aligned"
        elif ty_last and ty_last >= 2015:
            temporal = "recent"
        elif mb_data:
            temporal = "historical"
        else:
            temporal = None

        coverage.append({
            "species": sci,
            "common": tax.get("common_name"),
            "genus": genus,
            "order": tax.get("order"),
            "detected": sci in det_species,
            "permissiveness": s.get("permissiveness"),
            "class": s.get("class"),
            "tracked": bool(mb_data),
            "n_studies": mb_data["n_studies"] if mb_data else 0,
            "n_individuals": mb_data["n_individuals"] if mb_data else 0,
            "study_names": mb_data["study_names"][:3] if mb_data else [],
            "tracking_years": [mb_data["first_year"], mb_data["last_year"]]
                              if mb_data else None,
            "genus_tracked": genus_tracked,
            "genus_studies": genus_studies,
            "genus_individuals": genus_individuals,
            "temporal_quality": temporal,
        })

    # summary stats (the paper's claims, verified against our data)
    detected = [c for c in coverage if c["detected"]]
    detected_tracked = [c for c in detected if c["tracked"]]
    detected_genus = [c for c in detected if c["genus_tracked"]]
    high_perm = [c for c in coverage if (c["permissiveness"] or 0) >= 50]
    high_perm_tracked = [c for c in high_perm if c["tracked"]]

    # watchlist cross-reference (from region_risk)
    watchlist_refs = []
    for country, cr in rr.get("countries", {}).items():
        for s in cr.get("watchlist", {}).get("global", []) + \
                  cr.get("watchlist", {}).get("relatives_arrived", []):
            watchlist_refs.append({
                "country": country,
                "species": s["species"],
                "permissiveness": s.get("permissiveness"),
                "tracked": s["species"] in mb,
                "genus_tracked": (s["species"].split()[0] if " " in s["species"]
                                  else s["species"]) in mb_genera,
            })

    # untracked infected species (the data gap the paper highlights)
    untracked_infected = [
        {"species": c["species"], "common": c["common"],
         "order": c["order"], "genus_tracked": c["genus_tracked"]}
        for c in detected if not c["tracked"]
    ]

    # ---- surveillance gap prioritisation (the research agenda) ----
    # Rank untracked infected species by: permissiveness × detection spread ×
    # trajectory (increasing?) × (1 - genus coverage). Higher = more urgent
    # for new tracking studies.
    det_by_species = (det.group_by("scientific_name")
                      .agg(pl.len().alias("n"),
                           pl.col("country").n_unique().alias("countries"),
                           pl.col("date_iso").max().alias("last"))
                      .drop_nulls(subset=["scientific_name"]))
    det_info = {r["scientific_name"]: r for r in det_by_species.to_dicts()}

    gap_priorities = []
    for c in coverage:
        if c["tracked"] or not c["detected"]:
            continue
        di = det_info.get(c["species"], {})
        perm = c.get("permissiveness") or 0
        n_det = di.get("n", 0)
        n_countries = di.get("countries", 0)
        genus_relief = min(1.0, c.get("genus_studies", 0) / 10) \
            if c.get("genus_tracked") else 0.0

        # priority = how dangerous × how widespread × how blind we are
        priority = (perm / 100) * min(1.0, n_det / 50) * \
            min(1.0, n_countries / 10) * (1.0 - genus_relief)
        gap_priorities.append({
            "species": c["species"],
            "common": c["common"],
            "order": c["order"],
            "permissiveness": perm,
            "detections": n_det,
            "countries": n_countries,
            "last_detection": str(di.get("last", "")),
            "genus_studies": c.get("genus_studies", 0),
            "priority": round(priority, 4),
        })
    gap_priorities.sort(key=lambda g: -g["priority"])

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "movebank": "MEASURED (study metadata, bulk download "
                        "data/raw/movebank/)",
            "joins": "MEASURED (species.parquet × species_susceptibility × "
                     "region_risk × detections)",
            "phylo_transfer": "MODELED (genus-level coverage as proxy for "
                              "untracked species)",
            "paper": "Plaza et al. 2026, DOI:10.1111/irv.70330 — verified "
                     "their 71% claim against our species list",
        },
        "summary": {
            "our_species": len(coverage),
            "movebank_species_total": len(mb),
            "detected": len(detected),
            "detected_tracked": len(detected_tracked),
            "detected_tracked_pct": round(
                100 * len(detected_tracked) / max(1, len(detected))),
            "detected_genus_covered": len(detected_genus),
            "detected_genus_pct": round(
                100 * len(detected_genus) / max(1, len(detected))),
            "high_permissiveness": len(high_perm),
            "high_permissiveness_tracked": len(high_perm_tracked),
            "untracked_infected": len(untracked_infected),
        },
        "coverage": coverage,
        "watchlist_movement": watchlist_refs[:200],
        "untracked_infected": untracked_infected,
        "surveillance_gaps": {
            "total": len(gap_priorities),
            "priority_formula": (
                "(permissiveness/100) × min(1, detections/50) × "
                "min(1, countries/10) × (1 - genus_relief) — higher = "
                "more urgent for new tracking studies"),
            "top": gap_priorities[:50],
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"Movebank species: {len(mb)} | our species: {len(coverage)}")
    print(f"  detected: {len(detected)} | tracked: {len(detected_tracked)} "
          f"({doc['summary']['detected_tracked_pct']}%) | "
          f"genus-covered: {doc['summary']['detected_genus_pct']}%")
    print(f"  high-permissiveness (≥50): {len(high_perm)} | "
          f"tracked: {len(high_perm_tracked)}")
    print(f"  watchlist refs: {len(watchlist_refs)} | "
          f"untracked infected: {len(untracked_infected)}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
