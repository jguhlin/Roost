#!/usr/bin/env python3
"""Layer A — spread eras ledger (SPREAD_MODEL.md Phase 7).

Deterministic merge of two channels:

  CURATED   editorial era/chapter definitions (windows, lineages, regions,
            one-line narratives) — the only hand-written part, lives in
            this file.
  MEASURED  anchors computed from web/public/data/detections.parquet
            (44.9k dated detections, 107 countries): first detection per
            region bucket and per country inside each era window, counts,
            top hosts. Lineage→paper links come from
            data/papers/connections/clade_registry.json (paper mentions).

Provenance is explicit per field: `window`/`narrative` are CURATED;
`measured.*` is MEASURED (first-detection stamps are surveillance stamps —
arrival precedes detection, the ledger never claims otherwise).

Output: data/model/spread_eras.json (+ twin web/public/data/spread_eras.json).
Rerun after detections rebuilds or clade registry scans.

Usage: pixi run python scripts/model/build_spread_eras.py
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
DET = ROOT / "web" / "public" / "data" / "detections.parquet"
REG = ROOT / "data" / "papers" / "connections" / "clade_registry.json"
OUT = ROOT / "data" / "model" / "spread_eras.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "spread_eras.json"

# ---------------------------------------------------------------- regions
# coarse buckets over the 107 ISO-3 codes seen in detections; subantarctic
# islands grouped with Antarctica. Country lists are exhaustive so an
# unmapped code fails loudly below.
REGIONS: dict[str, list[str]] = {
    "east_southeast_asia": [
        "CHN", "HKG", "TWN", "JPN", "KOR", "MNG", "PRK", "MAC",
        "PHL", "VNM", "LAO", "KHM", "MMR", "THA", "MYS", "SGP", "IDN",
        "IND", "PAK", "BGD", "NPL", "LKA", "BTN",
    ],
    "west_central_asia_mena": [
        "AFG", "KAZ", "UZB", "TKM", "KGZ", "TJK", "IRN", "IRQ", "SYR",
        "JOR", "LBN", "KWT", "SAU", "ARE", "QAT", "OMN", "BHR", "YEM",
        "TUR", "ISR", "PSE", "GEO", "ARM", "AZE",
    ],
    "europe": [
        "ALA", "DEU", "GBR", "GGY", "IMN", "JEY", "NLD", "BEL", "LUX",
        "FRA", "ESP", "PRT", "ITA", "AUT", "CHE", "SWE", "NOR", "DNK",
        "FIN", "ISL", "FRO", "IRL", "POL", "CZE", "SVK", "HUN", "ROU",
        "BGR", "GRC", "ALB", "BIH", "HRV", "SRB", "SVN", "MKD", "MNE",
        "EST", "LVA", "LTU", "MDA", "UKR", "BLR", "CYP", "RUS",
        "SJM",
    ],
    "africa": [
        "EGY", "NGA", "CMR", "CIV", "GMB", "SEN", "MRT", "TGO", "TUN",
        "DZA", "MAR", "LBY", "UGA", "KEN", "TZA", "ZMB", "ZWE", "MOZ",
        "BWA", "NAM", "ZAF", "MDG", "ETH", "SDN", "GHA", "BEN", "MLI",
        "BFA", "NER", "CHA", "GAB", "COG", "COD", "AGO",
    ],
    "north_america": [
        "USA", "CAN", "MEX", "GTM", "HND", "CRI", "PAN", "CUB", "CYM",
        "JAM", "HTI", "DOM", "BLZ", "NIC", "SLV", "GRL", "SPM", "BMU",
    ],
    "south_america": [
        "ARG", "BOL", "BRA", "CHL", "COL", "ECU", "PER", "URY", "VEN",
        "PRY", "GUF", "SUR", "GUY", "FLK",
    ],
    "antarctica_subantarctic": ["ATA", "SGS", "HMD", "SHN", "BVT", "IOT"],
    "oceania": ["AUS", "NZL", "PNG", "FJI", "NCL"],
}
COUNTRY_TO_REGION = {c: r for r, cs in REGIONS.items() for c in cs}


# ---------------------------------------------------------------- eras
# CURATED. Windows are ISO dates; end=null → open. narratives stay
# conservative — one line, no contested specifics (measured stamps carry
# the detail). designations link to clade_registry paper counts.
ERAS: list[dict] = [
    {
        "id": "gd_emergence",
        "label": "Goose-Guangdong emergence",
        "window": {"start": "1996-01-01", "end": "2003-06-30"},
        "lineages": ["gs/GD (clade 0/1 precursor)"],
        "regions": ["east_southeast_asia"],
        "narrative": "H5N1 A/goose/Guangdong/1/96-lineage virus emerges in "
                     "southern China poultry; regional spread and the first "
                     "known human cases (Hong Kong, 1997).",
        "chapters": [],
        "designations": [],  # registry scan doesn't reach pre-2004 corpus
        "note": "pre-dates detections data (2004-) — CURATED only",
    },
    {
        "id": "first_panzootic",
        "label": "First panzootic (clade 1/2 westward)",
        "window": {"start": "2003-07-01", "end": "2006-12-31"},
        "lineages": ["clade 1", "clade 2.1", "clade 2.2", "clade 2.2.1"],
        "regions": ["east_southeast_asia", "west_central_asia_mena",
                    "europe", "africa"],
        "narrative": "Spread from SE Asia through Siberia (2005 Qinghai "
                     "Lake wild-bird die-off, clade 2.2) into Europe and "
                     "Africa in 2005-06; first African detections.",
        "chapters": [
            {"id": "qinghai_westward", "label": "Qinghai Lake & westward "
             "spread", "window": {"start": "2005-04-01", "end": "2006-06-30"},
             "regions": ["europe", "africa", "west_central_asia_mena"],
             "hosts": None},
        ],
        "designations": ["1", "1.1", "2", "2.1", "2.2", "2.2.1", "2.2.2",
                         "2.2.1.1", "2.2.1.2"],
    },
    {
        "id": "enzootic_consolidation",
        "label": "Enzootic consolidation (2.3.x era)",
        "window": {"start": "2007-01-01", "end": "2013-12-31"},
        "lineages": ["clade 2.3.2", "clade 2.3.4", "clade 1.1",
                     "clade 2.2.1.2"],
        "regions": ["east_southeast_asia", "africa",
                    "west_central_asia_mena"],
        "narrative": "Regional enzootic persistence (China, Vietnam, "
                     "Indonesia, Bangladesh, Egypt); divergent clade 2.3.x "
                     "radiation; sporadic spillover beyond enzootic zones.",
        "chapters": [],
        "designations": ["2.3", "2.3.2", "2.3.2.1", "2.3.2.1a", "2.3.2.1b",
                         "2.3.4", "2.3.4.1", "2.3.4.2", "2.3.3", "2.1.3"],
    },
    {
        "id": "na_incursion",
        "label": "North American incursion (2.3.4.4 reassortants)",
        "window": {"start": "2014-01-01", "end": "2015-12-31"},
        "lineages": ["clade 2.3.4.4 (H5N2/H5N8 reassortants)"],
        "regions": ["north_america"],
        "narrative": "H5Nx reassortants (Eurasian HA + North American "
                     "lineage internal genes) cross Beringia into Pacific "
                     "flyway; the 2015 US Midwest poultry outbreak.",
        "chapters": [
            {"id": "midwest_poultry_2015", "label": "US Midwest poultry "
             "outbreak", "window": {"start": "2015-03-01",
                                    "end": "2015-06-30"},
             "regions": ["north_america"], "hosts": None,
             "no_measured": "commercial-poultry outbreak records are not "
                     "in the detections feed; outbreak evidence is "
                     "paper-based"},
        ],
        "designations": ["2.3.4.4", "2.3.4.4A"],
    },
    {
        "id": "eurasia_wave_h5n8",
        "label": "H5N8 Eurasia wave (first 2.3.4.4b sweep)",
        "window": {"start": "2016-01-01", "end": "2017-12-31"},
        "lineages": ["clade 2.3.4.4b", "clade 2.3.4.4c"],
        "regions": ["europe", "west_central_asia_mena", "africa",
                    "east_southeast_asia"],
        "narrative": "H5N8 2.3.4.4b reaches Europe winter 2016-17 and "
                     "spreads along flyways; largest European wave to that "
                     "date.",
        "chapters": [],
        "designations": ["2.3.4.4b", "2.3.4.4c"],
    },
    {
        "id": "zoonotic_2321c",
        "label": "Clade 2.3.2.1c zoonotic wave",
        "window": {"start": "2019-01-01", "end": "2020-05-31"},
        "lineages": ["clade 2.3.2.1c"],
        "regions": ["east_southeast_asia"],
        "narrative": "2.3.2.1c surge in Asian poultry with heightened "
                     "human zoonosis (China, Vietnam, Cambodia, Laos); "
                     "immediately precedes and is displaced by 2.3.4.4b.",
        "chapters": [],
        "designations": ["2.3.2.1c", "2.3.2.1d"],
    },
    {
        "id": "emergence_2344b",
        "label": "2.3.4.4b emergence",
        "window": {"start": "2020-06-01", "end": "2021-09-30"},
        "lineages": ["clade 2.3.4.4b H5N8", "H5N1 reassortant"],
        "regions": ["europe", "africa", "north_america",
                    "west_central_asia_mena"],
        "narrative": "H5N8 clade 2.3.4.4b reassorted to H5N1 in late 2020 "
                     "and seeded poultry and wild birds across Europe, "
                     "Africa, and North America — the takeover began a "
                     "year before the formal panzootic window marks it.",
        "chapters": [],
        "designations": ["2.3.4.4b"],
        "note": "Added 2026-10-15 on corpus evidence: 79 introduction "
                "events carry a 2.3.4.4b lineage within this window "
                "(2020 ×24, 2021 ×54).",
    },
    {
        "id": "panzootic_2344b",
        "label": "2.3.4.4b panzootic (ongoing)",
        "window": {"start": "2021-10-01", "end": None},
        "lineages": ["clade 2.3.4.4b", "genotypes A/B/D"],
        "regions": ["europe", "north_america", "south_america",
                    "antarctica_subantarctic", "africa",
                    "east_southeast_asia", "west_central_asia_mena",
                    "oceania"],
        "narrative": "Global panzootic: Atlantic-route arrival into Europe "
                     "and North America (2021-22), spread to all continents "
                     "with wild-bird mass mortality and marine-mammal "
                     "spillover; dairy-cattle establishment (2024).",
        "chapters": [
            {"id": "atlantic_arrival", "label": "Atlantic flyway arrival",
             "window": {"start": "2021-10-01", "end": "2022-06-30"},
             "regions": ["europe", "north_america"], "hosts": None},
            {"id": "americas_continental", "label": "Americas continental "
             "spread", "window": {"start": "2022-07-01",
                                  "end": "2023-12-31"},
             "regions": ["north_america", "south_america"], "hosts": None},
            {"id": "antarctic_arrival", "label": "Antarctic & subantarctic",
             "window": {"start": "2023-10-01", "end": None},
             "regions": ["antarctica_subantarctic"], "hosts": None},
            {"id": "cattle_b313", "label": "Dairy cattle B3.13 (US)",
             "window": {"start": "2024-03-01", "end": None},
             "regions": ["north_america"], "hosts": None,
             "no_measured": "cattle-outbreak detections are not in the "
                     "surveillance feed; evidence is paper-based via "
                     "B3.13 registry links"},
            {"id": "oceania_2026", "label": "Oceania detections",
             "window": {"start": "2025-01-01", "end": None},
             "regions": ["oceania"], "hosts": None},
        ],
        "designations": ["2.3.4.4b", "B3.13", "B3.2", "D1.1", "D1.2",
                         "D1.3", "2.3.4.4B"],
    },
]


# ---------------------------------------------------------------- helpers

def _win(w: dict):
    start = date.fromisoformat(w["start"])
    end = date.fromisoformat(w["end"]) if w.get("end") else date(2100, 1, 1)
    return start, end


def measured_block(det: pl.DataFrame, w: dict, regions: list[str],
                   hosts: list[str] | None) -> dict:
    start, end = _win(w)
    countries = [c for r in regions for c in REGIONS[r]]
    d = det.filter(
        (pl.col("date_iso") >= start) & (pl.col("date_iso") <= end)
        & pl.col("country").is_in(countries))
    if hosts:
        d = d.filter(pl.col("scientific_name").is_in(hosts))

    out = {"detections": d.height, "regions": {}, "countries": {},
           "top_hosts": {}}
    if d.height == 0:
        return out
    # per region: first detection stamp + count
    d = d.with_columns(
        pl.col("country").replace_strict(COUNTRY_TO_REGION,
                                         default="unmapped")
        .alias("region"))
    unmapped = d.filter(pl.col("region") == "unmapped")["country"].unique()
    if len(unmapped):
        raise SystemExit(f"unmapped countries: {unmapped.to_list()} — "
                         "add them to REGIONS")
    for r in sorted(regions):
        sub = d.filter(pl.col("region") == r)
        if sub.height:
            out["regions"][r] = {"first": str(sub["date_iso"].min()),
                                 "count": sub.height}
    # per country first-stamps (all countries with a first IN window)
    cf = d.group_by("country").agg(pl.col("date_iso").min().alias("first"),
                                   pl.len().alias("count")).sort("first")
    out["countries"] = {row["country"]: {"first": str(row["first"]),
                                         "count": row["count"]}
                        for row in cf.iter_rows(named=True)}
    th = (d.filter(pl.col("scientific_name").is_not_null())
            .group_by("scientific_name").agg(pl.len().alias("n"))
            .sort("n", descending=True).head(6))
    out["top_hosts"] = {r["scientific_name"]: r["n"]
                        for r in th.iter_rows(named=True)}
    return out


def papers_block(registry: dict, designations: list[str]) -> dict:
    des = registry.get("designations", {})
    by_des = {k: des[k]["papers"] for k in designations
              if k in des and des[k].get("papers")}
    return {"designation_papers": by_des,
            "total": sum(by_des.values())}


def main() -> None:
    # curated-region sanity: fail loudly on unknown region buckets
    for era in ERAS:
        for scope in [era, *era["chapters"]]:
            bad = [r for r in scope["regions"] if r not in REGIONS]
            if bad:
                raise SystemExit(f"{era['id']}: unknown regions {bad}")

    det = (pl.read_parquet(DET)
           .filter(pl.col("date_iso").is_not_null())
           .with_columns(pl.col("country").fill_null("")))
    registry = json.loads(REG.read_text())

    eras = []
    for era in ERAS:
        m = measured_block(det, era["window"], era["regions"], None)
        e = {
            "id": era["id"], "label": era["label"],
            "window": {"start": era["window"]["start"],
                       "end": era["window"].get("end")},
            "lineages": era["lineages"], "regions": era["regions"],
            "narrative": era["narrative"],
            "note": era.get("note"),
            "provenance": {"window/narrative": "CURATED",
                           "measured": "MEASURED (detections "
                                       "first-stamps; arrival precedes "
                                       "detection)"},
            "chapters": [
                {**{k: v for k, v in ch.items()
                    if k not in ("note", "no_measured")},
                 **({"note": ch["no_measured"], "measured": None}
                    if ch.get("no_measured") else
                    {"measured": measured_block(det, ch["window"],
                                                ch["regions"],
                                                ch.get("hosts"))})}
                for ch in era["chapters"]
            ],
            "measured": m,
            "papers": papers_block(registry, era["designations"]),
        }
        eras.append(e)

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": {
            "detections": str(DET.relative_to(ROOT)),
            "clade_registry": str(REG.relative_to(ROOT)),
        },
        "eras": eras,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False, indent=1))

    print(f"{len(eras)} eras, "
          f"{sum(len(e['chapters']) for e in eras)} chapters")
    for e in eras:
        regs = ", ".join(f"{r}:{v['first']}" for r, v
                         in e["measured"]["regions"].items())
        print(f"  {e['id']:<24} {e['window']['start']}→"
              f"{e['window']['end'] or 'open':<10} "
              f"det={e['measured']['detections']:>5} "
              f"papers={e['papers']['total']:>4}  {regs}")
    print(f"\n→ {OUT.relative_to(ROOT)}\n→ {OUT_WEB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
