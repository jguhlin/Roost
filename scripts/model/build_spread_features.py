#!/usr/bin/env python3
"""Detections-derived spread features (SPREAD_MODEL.md Phase 6/7, [DET]).

Everything the 44.9k-row detections feed can say about spread WITHOUT the
LLM — the MEASURED side that literature extraction is validated against
and several direct model inputs. All features era-scoped via the Layer A
ledger windows:

  seasonality      month-of-year detection counts per era × region —
                   the measured seasonality curve (the `seasonality`
                   section can only quote about it; this measures it)
  persistence      country×species pairs recurring across years —
                   local-maintenance candidates (MEASURED establishment)
  diffusion        per era, ordered arrival chronology with days-since-
                   start and km-from-first (geocoded subset), plus a
                   crude early-wave km/day slope
  mass_events      detection_count >= threshold events, split
                   poultry/wildlife (species taxonomy + flock sources)
  mammal_share     yearly share of detections in Mammalia (proper
                   taxonomy via species.parquet)
  species_accum    per-era distinct species + new-species count
  sampling_mix     year × sampling_type — ascertainment drift

Output: data/model/spread_features.json (+ web twin).
Rerun after detections rebuilds or era-window edits (reads spread_eras).

Usage: pixi run python scripts/model/build_spread_features.py
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys_path = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(sys_path))
from build_spread_eras import COUNTRY_TO_REGION, ERAS, REGIONS  # noqa: E402

DET = ROOT / "web" / "public" / "data" / "detections.parquet"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
OUT = ROOT / "data" / "model" / "spread_features.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "spread_features.json"

MASS_THRESHOLD = 100
POULTRY_ORDERS = {"Galliformes", "Anseriformes"}  # Anseriformes = mostly
# domestic flocks via aphis_flocks; poultry class decided by source+order
FLOCK_SOURCES = {"aphis_flocks"}
DIFFUSION_MAX_ARRIVALS = 40
PERSISTENCE_MIN_YEARS = 2


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _win(w: dict):
    start = date.fromisoformat(w["start"])
    end = date.fromisoformat(w["end"]) if w.get("end") else date(2100, 1, 1)
    return start, end


def seasonality(det: pl.DataFrame) -> dict:
    out = {}
    for era in ERAS:
        start, end = _win(era["window"])
        d = det.filter((pl.col("date_iso") >= start)
                       & (pl.col("date_iso") <= end))
        if not d.height:
            continue
        d = d.with_columns(
            pl.col("country").replace_strict(COUNTRY_TO_REGION,
                                             default="unmapped")
            .alias("region"))
        if d.filter(pl.col("region") == "unmapped").height:
            raise SystemExit("unmapped country in seasonality — "
                             "update REGIONS")
        by_region = (d.group_by("region", pl.col("date_iso").dt.month()
                                .alias("month"))
                     .agg(pl.len().alias("n"))
                     .sort("month"))
        out[era["id"]] = {
            "total": d.height,
            "by_month": {str(m): n for m, n in
                         d.group_by(pl.col("date_iso").dt.month())
                         .agg(pl.len()).sort("date_iso")
                         .iter_rows()},
            "by_region_month": {f"{r}.{m}": n for r, m, n
                                in by_region.iter_rows()},
        }
    return out


def persistence(det: pl.DataFrame) -> dict:
    pairs = (det.group_by("country", "scientific_name")
             .agg(pl.col("date_iso").dt.year().n_unique().alias("years"),
                  pl.col("date_iso").min().alias("first"),
                  pl.col("date_iso").max().alias("last"),
                  pl.len().alias("n"))
             .filter((pl.col("years") >= PERSISTENCE_MIN_YEARS)
                     & pl.col("scientific_name").is_not_null())
             .sort("years", descending=True))
    return {
        "min_years": PERSISTENCE_MIN_YEARS,
        "pairs": [{"country": r["country"], "species": r["scientific_name"],
                   "years": r["years"], "first": str(r["first"]),
                   "last": str(r["last"]), "records": r["n"]}
                  for r in pairs.iter_rows(named=True)],
        "provenance": "MEASURED (detections recurring across years)",
    }


def diffusion(det: pl.DataFrame) -> dict:
    out = {}
    for era in ERAS:
        start, end = _win(era["window"])
        d = det.filter((pl.col("date_iso") >= start)
                       & (pl.col("date_iso") <= end)
                       & pl.col("latitude").is_not_null())
        if not d.height:
            continue
        first = (d.group_by("country")
                 .agg(pl.col("date_iso").min().alias("first"),
                      pl.col("latitude").first().alias("lat"),
                      pl.col("longitude").first().alias("lon"))
                 .sort("first").head(DIFFUSION_MAX_ARRIVALS))
        rows = first.iter_rows(named=True)
        origin = next(rows, None)
        if origin is None:
            continue
        arrivals = []
        pts = []
        for r in [origin] + list(rows):
            days = (r["first"] - start).days
            km = haversine_km(origin["lat"], origin["lon"],
                              r["lat"], r["lon"])
            arrivals.append({"country": r["country"], "first": str(r["first"]),
                             "days_since_start": days,
                             "km_from_first": round(km)})
            if days <= 180:
                pts.append((days, km))
        slope = None
        if len(pts) >= 5:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            den = sum((x - mx) ** 2 for x in xs)
            if den:
                s = sum((x - mx) * (y - my) for x, y in pts) / den
                slope = round(s, 2) if s > 0 else None  # negative = no
                # outward-radial pattern; don't ship a meaningless slope
        out[era["id"]] = {"first_stamp": str(origin["first"]),
                          "origin_country": origin["country"],
                          "arrivals": arrivals,
                          "early_wave_km_per_day": slope,
                          "note": "crude radial slope, first 180 days, "
                                  "first-detection stamps only"}
    return out


def mass_events(det: pl.DataFrame) -> dict:
    d = (det.filter(pl.col("detection_count") >= MASS_THRESHOLD))
    orders = (pl.read_parquet(SPECIES)
              .select("scientific_name", "order"))
    d = d.join(orders, on="scientific_name", how="left")
    ev = []
    for r in d.sort("detection_count", descending=True).iter_rows(named=True):
        ev.append({
            "date": str(r["date_iso"]), "country": r["country"],
            "species": r["scientific_name"] or None,
            "count": r["detection_count"],
            "class": "poultry" if r["source"] in FLOCK_SOURCES else "wildlife",
            "source": r["source"],
        })
    wildlife = [e for e in ev if e["class"] == "wildlife"]
    return {
        "threshold": MASS_THRESHOLD,
        "events": ev,
        "wildlife_count": len(wildlife),
        "poultry_count": len(ev) - len(wildlife),
        "largest_wildlife": wildlife[:10],
        "provenance": "MEASURED (detections detection_count field)",
    }


def mammal_share(det: pl.DataFrame) -> dict:
    orders = (pl.read_parquet(SPECIES)
              .select("scientific_name", "class"))
    d = det.join(orders, on="scientific_name", how="left")
    per_year = (d.group_by(pl.col("date_iso").dt.year().alias("y"))
                .agg(((pl.col("class") == "Mammalia").sum() * 100
                      / pl.len()).round(1).alias("mammal_pct"),
                     (pl.col("class") == "Mammalia").sum().alias("mammal_n"),
                     pl.len().alias("n"))
                .sort("y"))
    return {
        "by_year": [{"year": r["y"], "mammal_pct": r["mammal_pct"],
                     "mammal_n": r["mammal_n"], "total": r["n"]}
                    for r in per_year.iter_rows(named=True)],
        "provenance": "MEASURED (species.parquet class join)",
    }


def species_accumulation(det: pl.DataFrame) -> dict:
    out = {}
    seen: set[str] = set()
    for era in ERAS:
        start, end = _win(era["window"])
        d = det.filter((pl.col("date_iso") >= start)
                       & (pl.col("date_iso") <= end)
                       & pl.col("scientific_name").is_not_null())
        sp = set(d["scientific_name"].to_list())
        new = sp - seen
        seen |= sp
        out[era["id"]] = {"species": len(sp), "new_species": len(new)}
    return out


def sampling_mix(det: pl.DataFrame) -> dict:
    per_year = (det.group_by(pl.col("date_iso").dt.year().alias("y"),
                             "sampling_type").agg(pl.len().alias("n"))
                .sort("y"))
    out: dict[int, dict] = {}
    for r in per_year.iter_rows(named=True):
        out.setdefault(r["y"], {})[r["sampling_type"] or "unknown"] = r["n"]
    return {"by_year": {str(k): v for k, v in sorted(out.items())}}


def main() -> None:
    det = (pl.read_parquet(DET)
           .filter(pl.col("date_iso").is_not_null()))

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": {"detections": str(DET.relative_to(ROOT)),
                   "species": str(SPECIES.relative_to(ROOT))},
        "seasonality": seasonality(det),
        "persistence": persistence(det),
        "diffusion": diffusion(det),
        "mass_events": mass_events(det),
        "mammal_share": mammal_share(det),
        "species_accumulation": species_accumulation(det),
        "sampling_mix": sampling_mix(det),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"seasonality eras: {len(doc['seasonality'])}")
    panz = doc["seasonality"].get("panzootic_2344b", {})
    print(f"  panzootic peak months: "
          f"{sorted(panz.get('by_month', {}).items(), key=lambda kv: -kv[1])[:3]}")
    print(f"persistence pairs (>= {PERSISTENCE_MIN_YEARS}y): "
          f"{len(doc['persistence']['pairs'])}")
    for era, f in doc["diffusion"].items():
        print(f"diffusion {era}: origin {f['origin_country']} "
              f"{f['first_stamp']}, slope {f['early_wave_km_per_day']} km/day")
    print(f"mass events: {doc['mass_events']['poultry_count']} poultry / "
          f"{doc['mass_events']['wildlife_count']} wildlife "
          f"(>= {MASS_THRESHOLD})")
    ms = doc["mammal_share"]["by_year"]
    print(f"mammal share 2024-26: "
          f"{[m['mammal_pct'] for m in ms if m['year'] >= 2024]}")
    print(f"sampling_mix years: {len(doc['sampling_mix']['by_year'])}")
    print(f"\n→ {OUT.relative_to(ROOT)}\n→ {OUT_WEB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
