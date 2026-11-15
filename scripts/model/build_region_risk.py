#!/usr/bin/env python3
"""Region-scoped risk (2026-10-15): species X in region Y — the conservation
operational view.

For every country in the detections feed (plus 8-bucket rollups):
  presence        virus timeline: first stamp, current era, totals,
                  seasonality (bucket curve from measured features)
  detected        species detected here × susceptibility (permissiveness,
                  severity, class/outcome), first/last stamps
  watchlist       HIGH-PERMISSIVENESS species NOT yet detected here, in two
                  honest tiers: 'relatives_arrived' (genus detected in
                  region — phylogenetic exposure) and 'global' (top global
                  susceptibility regardless), both labeled as absence-of-
                  evidence, not evidence-of-absence
  routes          corpus introduction events into the region's bucket
  programs        vaccination campaigns in the region (where the corpus
                  names it)

Everything deterministic over shipped artifacts. Output:
data/model/region_risk.json + web twin. Rerun after detections rebuilds,
susceptibility rebuilds, or synthesis passes.

Usage: pixi run python scripts/model/build_region_risk.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_spread_eras import COUNTRY_TO_REGION, ERAS  # noqa: E402
from iso3_names import ISO3_NAMES  # noqa: E402
from region_norm import region_bucket  # noqa: E402

# ---- arrival-risk scoring constants (documented, deterministic) ----
AR_WEIGHTS = {
    "source_proximity": 0.30,
    "bridge_pressure": 0.25,
    "movement_intelligence": 0.20,
    "seasonal_signal": 0.15,
    "era_activity": 0.10,
}
PANZOOTIC_START = "2021-10-01"

DET = ROOT / "web" / "public" / "data" / "detections.parquet"
SUSCEPT = ROOT / "data" / "model" / "species_susceptibility.json"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
FEATURES = ROOT / "web" / "public" / "data" / "spread_features.json"
SYNTH = ROOT / "web" / "public" / "data" / "spread_synthesis.json"
CAMPAIGNS = ROOT / "web" / "public" / "data" / "vaccine_campaigns.json"
OUT = ROOT / "data" / "model" / "region_risk.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "region_risk.json"

WATCHLIST_PERM = 40.0     # relatives tier floor (intermediate+ under the
                         # conservative v2 calibration)
WATCHLIST_GLOBAL = 60.0   # 'global' tier floor
DETECTED_CAP = 60         # cap rendered species rows per country (biggest feeders)


def _era_for(iso_date: str) -> str | None:
    if not iso_date:
        return None
    for era in ERAS:
        s = era["window"]["start"]
        e = era["window"].get("end") or "2100-12-31"
        if s <= iso_date <= e:
            return era["id"]
    return None


def arrival_risk_score(country_data, bucket, season_by_bucket, era_firsts, movement_sus):
    """Composite arrival-risk score (0-100) for a country.

    Deterministic — every factor computed from shipped artifacts:
      source_proximity    detections in the same region bucket (log-scaled)
      bridge_pressure     high-permissiveness species present in the bucket
                          but undetected in this country
      movement_intelligence  fraction of those tracked (higher = more
                          predictable = LOWER surprise risk, but HIGHER
                          confidence in the prediction)
      seasonal_signal     does the region have a clear seasonal peak?
      era_activity        is the virus actively detected post-panzootic start?
    """
    import math

    all_countries = era_firsts  # the full countries dict

    # 1. source proximity: detections in the region bucket
    region_dets = sum(1 for c, v in all_countries.items()
                      if v.get("region") == bucket)
    proximity = min(1.0, math.log1p(region_dets) / math.log1p(15))

    # 2. bridge pressure: high-permissiveness species detected in the
    #    bucket but NOT in this country
    bucket_species = set()
    for c, v in all_countries.items():
        if v.get("region") == bucket:
            for s in v.get("detected", []):
                if (s.get("permissiveness") or 0) >= 40:
                    bucket_species.add(s["species"])
    local_species = {s["species"] for s in country_data.get("detected", [])}
    bridges = bucket_species - local_species
    pressure = min(1.0, len(bridges) / 20) if bridges else 0.0

    # 3. movement intelligence: fraction of bridges tracked
    tracked = sum(1 for s in bridges if movement_sus.get(s, {}).get("tracked"))
    genus_tracked = sum(1 for s in bridges
                        if movement_sus.get(s, {}).get("genus_tracked"))
    intel = (tracked + 0.5 * (genus_tracked - tracked)) / max(1, len(bridges)) \
        if bridges else 0.0

    # 4. seasonal signal: does the bucket have a clear peak month?
    season = season_by_bucket.get(bucket, {})
    if season:
        vals = sorted(season.values(), reverse=True)
        peak_share = vals[0] / max(1, sum(vals)) if vals else 0
        seasonal = min(1.0, peak_share / 0.25)  # 25%+ in one month = strong
    else:
        seasonal = 0.0

    # 5. era activity: detections in this bucket since panzootic start
    era_countries = sum(1 for c, v in all_countries.items()
                        if v.get("region") == bucket
                        and v.get("first_detection", "") >= PANZOOTIC_START)
    era = min(1.0, era_countries / 5) if era_countries else 0.0

    score = 100 * sum(w * f for w, f in zip(
        AR_WEIGHTS.values(),
        [proximity, pressure, intel, seasonal, era]))
    return round(min(100, max(0, score)), 1), {
        "source_proximity": round(proximity, 2),
        "bridge_pressure": round(pressure, 2),
        "movement_intelligence": round(intel, 2),
        "seasonal_signal": round(seasonal, 2),
        "era_activity": round(era, 2),
        "bridge_species_count": len(bridges),
        "bridge_species_tracked": tracked,
    }


def main() -> None:
    det = (pl.read_parquet(DET)
           .filter(pl.col("date_iso").is_not_null()
                   & pl.col("scientific_name").is_not_null()))
    sus = json.loads(SUSCEPT.read_text())
    sus_by_species = {s["species"]: s for s in sus["species"]}
    tax = {r["scientific_name"]: r for r in pl.read_parquet(SPECIES).select(
        "scientific_name", "common_name", "genus", "family", "order")
        .iter_rows(named=True)}
    features = json.loads(FEATURES.read_text())
    synth = json.loads(SYNTH.read_text())
    campaigns = json.loads(CAMPAIGNS.read_text()) if CAMPAIGNS.exists() else {}

    # movement lookup for arrival-risk scoring
    MOV = ROOT / "data" / "model" / "movement_coverage.json"
    movement_sus = {}
    if MOV.exists():
        mvd = json.loads(MOV.read_text())
        for c in mvd.get("coverage", []):
            movement_sus[c["species"]] = c

    # region-bucket seasonality (panzootic era by_region_month "bucket.N")
    season_by_bucket = {}
    panz = features.get("seasonality", {}).get("panzootic_2344b", {})
    for key, n in (panz.get("by_region_month") or {}).items():
        bucket, month = key.rsplit(".", 1)
        season_by_bucket.setdefault(bucket, {})[month] = n

    # introduction routes per bucket
    intro_by_bucket: dict[str, Counter] = {}
    for it in synth.get("introductions", {}).get("items", []):
        b = region_bucket(it.get("dest_region"))
        if b:
            intro_by_bucket.setdefault(b, Counter())[
                it.get("route") or "unknown"] += 1

    # campaigns per bucket + country-name match
    campaigns_by_bucket: dict[str, list] = {}
    for c in campaigns.get("campaigns", []):
        if c.get("region_bucket"):
            campaigns_by_bucket.setdefault(c["region_bucket"], []).append({
                "region": c.get("region"), "period": c.get("period"),
                "sector": c.get("sector"), "effect": (c.get("effect") or "")[:160],
            })

    # global susceptibility ladder for watchlists
    ranked = sorted(
        (s for s in sus["species"] if s.get("permissiveness") is not None),
        key=lambda s: -s["permissiveness"])

    # per-country
    per_country = (det.group_by("country", "scientific_name")
                   .agg(pl.col("date_iso").min().alias("first"),
                        pl.col("date_iso").max().alias("last"),
                        pl.len().alias("n"))
                   .sort("n", descending=True))

    countries = {}
    for country_key, sub in per_country.group_by("country"):
        country = country_key[0] if isinstance(country_key, tuple) else country_key
        sub = sub.sort("first")
        first_overall = sub["first"].min()
        bucket = COUNTRY_TO_REGION.get(country)
        if not bucket:
            continue  # unmapped countries fail loudly elsewhere; skip here
        detected_species = sub.to_dicts()

        rows = []
        genera_detected = set()
        for r in detected_species:
            sci = r["scientific_name"]
            s = sus_by_species.get(sci)
            g = (tax.get(sci) or {}).get("genus")
            if g:
                genera_detected.add(g)
            rows.append({
                "species": sci,
                "common": (tax.get(sci) or {}).get("common_name"),
                "first": str(r["first"]), "last": str(r["last"]),
                "records": r["n"],
                "permissiveness": (s or {}).get("permissiveness"),
                "severity": (s or {}).get("severity"),
                "class": (s or {}).get("class"),
                "outcome": (s or {}).get("outcome"),
            })
        rows.sort(key=lambda x: -(x["permissiveness"] or 0))

        detected_set = {r["species"] for r in rows}
        watch_relatives = []
        watch_global = []
        for s in ranked:
            if len(watch_relatives) >= 15 and len(watch_global) >= 15:
                break
            if s["species"] in detected_set:
                continue
            genus = (tax.get(s["species"]) or {}).get("genus")
            entry = {
                "species": s["species"],
                "common": s.get("common"),
                "permissiveness": s["permissiveness"],
                "severity": s.get("severity"),
                "class": s["class"],
                "literature_only": s.get("literature_only", False),
                "vax_program": bool(s.get("vax_program")),
                "genus_detected_here": bool(genus and genus in genera_detected),
            }
            if (len(watch_relatives) < 15 and s["permissiveness"] >= WATCHLIST_PERM
                    and entry["genus_detected_here"]):
                watch_relatives.append(entry)
            elif len(watch_global) < 15 and s["permissiveness"] >= WATCHLIST_GLOBAL:
                watch_global.append(entry)

        countries[country] = {
            "region": bucket,
            "name": ISO3_NAMES.get(country, country),
            "first_detection": str(first_overall),
            "first_era": _era_for(str(first_overall)),
            "total_records": int(sub["n"].sum()),
            "species_count": len(rows),
            "seasonality": season_by_bucket.get(bucket),
            "intro_routes": dict(intro_by_bucket.get(bucket, {})),
            "campaigns": campaigns_by_bucket.get(bucket, [])[:6],
            "detected": rows[:DETECTED_CAP],
            "watchlist": {
                "relatives_arrived": watch_relatives,
                "global": watch_global,
                "note": "Absence of detections, not detection of absence — "
                        "surveillance intensity varies by country.",
            },
        }

    # countries with detections but NO named-species rows: presence still
    # counts — include with empty detected/watchlist context
    all_det_countries = set(
        pl.read_parquet(DET)["country"].drop_nulls().to_list())
    for c in sorted(all_det_countries - set(countries)):
        bucket = COUNTRY_TO_REGION.get(c)
        if not bucket:
            continue
        sub_c = pl.read_parquet(DET).filter(
            (pl.col("country") == c) & pl.col("date_iso").is_not_null())
        countries[c] = {
            "region": bucket,
            "name": ISO3_NAMES.get(c, c),
            "first_detection": str(sub_c["date_iso"].min()),
            "first_era": _era_for(str(sub_c["date_iso"].min())),
            "total_records": sub_c.height,
            "species_count": 0,
            "seasonality": season_by_bucket.get(bucket),
            "intro_routes": dict(intro_by_bucket.get(bucket, {})),
            "campaigns": campaigns_by_bucket.get(bucket, [])[:6],
            "detected": [],
            "watchlist": {"relatives_arrived": [], "global": [],
                          "note": "Detections recorded without species "
                                  "identification — presence known, hosts "
                                  "not."},
            "species_unnamed": True,
        }

    # ---- second pass: arrival risk scores (needs ALL countries built) ----
    for country, cdata in countries.items():
        bucket = cdata["region"]
        ar_score, ar_breakdown = arrival_risk_score(
            cdata, bucket, season_by_bucket, countries, movement_sus)
        # Countries WITH detections have already been "arrived" — showing a
        # pre-arrival risk score is wrong (user review 2026-11: NZ rated
        # "low" despite the virus arriving July 2026)
        has_det = (cdata.get("total_records") or 0) > 0
        cdata["arrival_risk"] = {
            "score": ar_score,
            "band": ("arrived" if has_det else
                     "high" if ar_score >= 60 else
                     "moderate" if ar_score >= 35 else
                     "low" if ar_score >= 15 else "minimal"),
            **ar_breakdown,
        }

    # 8-bucket rollups
    regions = {}
    for bucket in set(COUNTRY_TO_REGION.values()):
        cs = {c: v for c, v in countries.items() if v["region"] == bucket}
        if not cs:
            continue
        firsts = [v["first_detection"] for v in cs.values()]
        regions[bucket] = {
            "countries": len(cs),
            "first_detection": min(firsts),
            "total_records": sum(v["total_records"] for v in cs.values()),
            "species_count": max(v["species_count"] for v in cs.values()),
            "seasonality": season_by_bucket.get(bucket),
            "intro_routes": dict(intro_by_bucket.get(bucket, {})),
        }

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "presence": "MEASURED (detections)",
            "susceptibility": "MODELED/PAPER_EXTRACTED (species_susceptibility v2)",
            "watchlist": "MODELED join: global permissiveness × regional absence",
            "seasonality": "MEASURED (panzootic-era bucket curves)",
        },
        "countries": countries,
        "regions": regions,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"countries: {len(countries)} | region rollups: {len(regions)}")
    for c in ("NZL", "USA", "EGY", "AUS"):
        v = countries.get(c)
        if not v:
            continue
        w = len(v["watchlist"]["relatives_arrived"]), len(v["watchlist"]["global"])
        print(f"  {c}: first={v['first_detection']} species={v['species_count']} "
              f"watchlist(rel,global)={w} routes={v['intro_routes']}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
