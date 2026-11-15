#!/usr/bin/env python3
"""Vaccine campaigns layer (deep overhaul, 2026-10-15): the historical arm.

Joins the vaccination_campaigns extraction (real deployments, quote-grounded)
to the era ledger so campaigns read on the same timeline as the spread
chapters. Also carries the region-normalized tallies and DIVA/coverage
patterns that the Vaccines page renders:

  campaigns      per-item: name/region/period/sector/type/diva/effect,
                 era join, region bucket, years parsed
  by_era         era -> campaigns, sectors, regions (timeline anchors)
  by_region      region bucket -> campaign counts + periods
  by_sector      sector counts + representative effects
  diva           DIVA-stated share (surveillance-interference relevance)

Region buckets reuse the spread-era REGIONS mapping (country codes where
stated; free-text names matched against the bucket country lists).

Output: data/model/vaccine_campaigns.json + web twin.
Rerun after campaigns extraction passes or era-window edits.

Usage: pixi run python scripts/model/build_vaccine_campaigns.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_spread_eras import COUNTRY_TO_REGION  # noqa: E402

SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"
ERAS = ROOT / "data" / "model" / "spread_eras.json"
PAPERS = ROOT / "web" / "public" / "data" / "papers.json"
OUT = ROOT / "data" / "model" / "vaccine_campaigns.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "vaccine_campaigns.json"

YEAR_RE = re.compile(r"(?:19|20)\d{2}")
PROV = "PAPER_EXTRACTED (vaccination_campaigns section, quote-grounded)"


def years_of(period):
    """'since 2012' -> [2012]; '2005-2008' -> [2005, 2008]."""
    ys = [int(y) for y in YEAR_RE.findall(str(period or ""))]
    return (min(ys), max(ys)) if ys else (None, None)


def era_for(y0, y1, eras):
    if y0 is None:
        return None
    for era in eras:
        s = int(era["window"]["start"][:4])
        e = int((era["window"].get("end") or "2100-01-01")[:4])
        # era of first campaign year; open-ended eras absorb
        if s <= y0 <= e or (y1 and s <= y1 <= e and y0 <= s):
            return era["id"]
    return None


def region_bucket(region_text):
    """Free-text region -> spread-era bucket via common-name matching."""
    t = (region_text or "").lower()
    if not t:
        return None
    for name, bucket in _build_name_lookup().items():
        if name in t:
            return bucket
    for bucket in ("europe", "africa", "asia", "oceania"):
        if bucket in t:
            return {"asia": "east_southeast_asia"}.get(bucket, bucket)
    return None


def _build_name_lookup():
    names = {
        "china": "east_southeast_asia", "vietnam": "east_southeast_asia",
        "indonesia": "east_southeast_asia", "bangladesh": "west_central_asia_mena",
        "egypt": "africa", "nigeria": "africa", "africa": "africa",
        "france": "europe", "netherlands": "europe", "europe": "europe",
        "european": "europe", "italy": "europe", "germany": "europe",
        "uk": "europe", "united kingdom": "europe", "russia": "europe",
        "israel": "west_central_asia_mena", "pakistan": "west_central_asia_mena",
        "india": "west_central_asia_mena", "korea": "east_southeast_asia",
        "japan": "east_southeast_asia", "hong kong": "east_southeast_asia",
        "usa": "north_america", "united states": "north_america",
        "us ": "north_america", "mexico": "north_america",
        "canada": "north_america", "brazil": "south_america",
        "peru": "south_america", "south america": "south_america",
        "argentina": "south_america", "chile": "south_america",
        "ecuador": "south_america", "new zealand": "oceania",
        "australia": "oceania", "global": None, "worldwide": None,
    }
    return names


def main() -> None:
    eras = json.loads(ERAS.read_text())["eras"]
    papers = {p["id"]: p for p in json.loads(PAPERS.read_text())["papers"]}

    df = pl.read_parquet(SPREAD).filter(
        pl.col("section") == "vaccination_campaigns")
    campaigns = []
    for r in df.iter_rows(named=True):
        try:
            it = json.loads(r["payload"])
        except Exception:
            continue
        y0, y1 = years_of(it.get("period"))
        campaigns.append({
            "paper_id": r["paper_id"],
            "year": (papers.get(r["paper_id"]) or {}).get("year"),
            "name": it.get("name") or "unnamed",
            "region": it.get("region"),
            "region_bucket": region_bucket(it.get("region")),
            "period": it.get("period"),
            "period_start": y0, "period_end": y1,
            "sector": it.get("sector") or "other",
            "vaccine_type": it.get("vaccine_type") or "unspecified",
            "diva": it.get("diva") or "unspecified",
            "coverage": it.get("coverage"),
            "effect": (it.get("effect") or "")[:300],
            "era": era_for(y0, y1, eras),
            "grounded": bool(r.get("quote_in_text")),
        })
    campaigns.sort(key=lambda c: (c["period_start"] or 9999, c["region"] or ""))

    by_era = {}
    for era in eras:
        cs = [c for c in campaigns if c["era"] == era["id"]]
        if not cs:
            continue
        by_era[era["id"]] = {
            "label": era["label"],
            "window": era["window"],
            "campaigns": len(cs),
            "sectors": dict(Counter(c["sector"] for c in cs)),
            "regions": dict(Counter(c["region_bucket"] or "unmapped"
                                    for c in cs)),
            "types": dict(Counter(c["vaccine_type"] for c in cs)),
        }

    by_region = {}
    for c in campaigns:
        if not c["region_bucket"]:
            continue
        e = by_region.setdefault(c["region_bucket"], {"campaigns": 0,
                                                      "periods": []})
        e["campaigns"] += 1
        if c["period_start"]:
            e["periods"].append((c["period_start"], c["period_end"] or c["period_start"]))
    for v in by_region.values():
        ps = v.pop("periods")
        v["first"] = min(p[0] for p in ps)
        v["last"] = max(p[1] for p in ps)

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "provenance": PROV,
        "campaigns": campaigns,
        "by_era": by_era,
        "by_region": dict(sorted(by_region.items(),
                                 key=lambda kv: -kv[1]["campaigns"])),
        "by_sector": dict(Counter(c["sector"] for c in campaigns)
                          .most_common()),
        "by_type": dict(Counter(c["vaccine_type"] for c in campaigns)
                        .most_common()),
        "diva": {
            "true": sum(1 for c in campaigns if c["diva"] == "true"),
            "false": sum(1 for c in campaigns if c["diva"] == "false"),
            "unspecified": sum(1 for c in campaigns
                               if c["diva"] == "unspecified"),
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"campaigns: {len(campaigns)} "
          f"({sum(1 for c in campaigns if c['grounded'])} grounded, "
          f"{len({c['paper_id'] for c in campaigns})} papers)")
    print(f"sectors: {doc['by_sector']}")
    print(f"eras covered: {list(by_era)}")
    print("regions:", [(k, v['campaigns'], f"{v['first']}-{v['last']}")
          for k, v in list(doc['by_region'].items())[:8]])
    print(f"diva: {doc['diva']}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
