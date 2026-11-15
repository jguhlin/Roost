#!/usr/bin/env python3
"""Vaccine outcomes synthesis (2026-10-14): what the corpus says vaccination
achieved, structured for the Vaccines page.

Merges two complementary channels:
  intervention_response (llm_extract_spread, quote-grounded)
      — field outcomes: worked/partial/failed + metrics, target species,
        wild/captive/farm programs (the conservation story)
  vaccine_claims.jsonl (mine_vaccines, verified)
      — platform/immunology depth: challenge design, mortality & shedding
        deltas vax-vs-control, DIVA, duration of immunity

Also joins the host-competence matrix for the protection-gap view:
susceptible species with NO vaccination evidence are program candidates.

Output: data/model/vaccine_outcomes.json + web twin.
Rerun after extraction passes, mine_vaccines runs, or competence rebuilds.

Usage: pixi run python scripts/model/build_vaccine_outcomes.py
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

SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"
CLAIMS = ROOT / "data" / "papers" / "vaccine_claims.jsonl"
PAPERS = ROOT / "web" / "public" / "data" / "papers.json"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
COMPETENCE = ROOT / "web" / "public" / "data" / "host_competence.json"
OUT = ROOT / "data" / "model" / "vaccine_outcomes.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "vaccine_outcomes.json"

from build_host_competence import SYNONYMS, _norm_name  # noqa: E402

WILD_SETTINGS = {"wild", "captive", "zoo"}

# vaccine-paper phrasings the taxonomy resolver can't reach
VAX_SYNONYMS = {
    "california condor": "Gymnogyps californianus",
    "californian condor": "Gymnogyps californianus",
    "kākāpō": "Strigops habroptila",
    "kakapo": "Strigops habroptila",
    # legacy NCBI spelling — resolves to the canonical (IOC/index) name
    "Strigops habroptilus": "Strigops habroptila",
    "king penguin": "Aptenodytes patagonicus",
    "shy albatross": "Thalassarche cauta",
    "pekín duck": "Anas platyrhynchos", "pekín ducks": "Anas platyrhynchos",
    "duck": "Anas platyrhynchos", "ducks": "Anas platyrhynchos",
    "broiler flock": "Gallus gallus", "layer chicken": "Gallus gallus",
    "brown layer chicken": "Gallus gallus",
    "goose": "Anser anser", "geese": "Anser anser",
    "cow": "Bos taurus", "dairy cow": "Bos taurus",
    "lactating dairy cow": "Bos taurus",
    "balb/c mouse": "Mus musculus",
}


def _num(v):
    """Claims carry '20%' / '0.5' / None — coerce to float or None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().rstrip("%").strip()
    try:
        return float(s)
    except ValueError:
        return None


def main() -> None:
    papers = {p["id"]: p for p in json.loads(PAPERS.read_text())["papers"]}

    # ---- channel 1: intervention_response (all kinds, vaccination split) --
    df = pl.read_parquet(SPREAD)
    iv = df.filter(pl.col("section") == "intervention_response")
    interventions: Counter = Counter()
    vax_items = []
    for r in iv.iter_rows(named=True):
        it = json.loads(r["payload"])
        kind = (it.get("intervention") or "unknown").strip()
        interventions[kind] += 1
        if "vaccin" not in kind.lower():
            continue
        vax_items.append({
            "paper_id": r["paper_id"],
            "title": (papers.get(r["paper_id"]) or {}).get("title", ""),
            "year": (papers.get(r["paper_id"]) or {}).get("year"),
            "target_species": it.get("target_species"),
            "setting": it.get("setting"),
            "outcome": it.get("outcome"),
            "metric": (it.get("metric") or "")[:400],
            "grounded": bool(r.get("quote_in_text")),
        })

    by_year = Counter(v["year"] for v in vax_items if v["year"])
    wild_programs = [v for v in vax_items if (v["setting"] or "") in WILD_SETTINGS]

    # ---- channel 2: vaccine_claims (platform/immunology depth) -----------
    platforms: Counter = Counter()
    field_lab: Counter = Counter()
    diva = 0
    claims_n = 0
    efficacy_rows = []
    claims_rows = []
    if CLAIMS.exists():
        for line in CLAIMS.read_text().splitlines():
            try:
                c = json.loads(line)
            except Exception:
                continue
            claims_rows.append(c)
            claims_n += 1
            platforms[(c.get("platform") or "unspecified")] += 1
            field_lab[(c.get("field_or_lab") or "unspecified")] += 1
            if c.get("diva_compatible"):
                diva += 1
            mv, mc = c.get("mortality_vaccinated"), c.get("mortality_control")
            if mv is not None or mc is not None:
                efficacy_rows.append({
                    "paper_id": c.get("paper_id"),
                    "platform": c.get("platform"),
                    "species": c.get("species"),
                    "challenge_clade": c.get("challenge_clade"),
                    "mortality_vaccinated": mv,
                    "mortality_control": mc,
                    "shedding_vaccinated": c.get("shed_titer_vaccinated"),
                    "shedding_control": c.get("shed_titer_control"),
                    "seroconversion_pct": c.get("seroconversion_pct"),
                    "duration_of_immunity_days": c.get("duration_of_immunity_days"),
                    "field_or_lab": c.get("field_or_lab"),
                })

    # ---- protection-gap join: susceptible but unvaccinated ---------------
    tax = {r["scientific_name"]: r for r in
           pl.read_parquet(SPECIES).select(
               "scientific_name", "common_name").iter_rows(named=True)}
    resolver = {}
    for sci, row in tax.items():
        resolver[_norm_name(sci)] = sci
        if row.get("common_name"):
            resolver.setdefault(_norm_name(row["common_name"]), sci)
    resolver.update({_norm_name(k): v for k, v in SYNONYMS.items()})
    resolver.update({_norm_name(k): v for k, v in VAX_SYNONYMS.items()})

    def resolve(raw: str | None) -> str | None:
        return resolver.get(_norm_name(raw or ""))

    vaccinated = {resolve(v["target_species"]) for v in vax_items} - {None}
    comp = json.loads(COMPETENCE.read_text())
    gaps = []
    for s in comp.get("species", []):
        sus = s.get("susceptibility") or {}
        if sus.get("class") not in ("susceptible", "highly_susceptible"):
            continue
        if s["species"] in vaccinated:
            continue
        gaps.append({
            "species": s["species"],
            "susceptibility": sus.get("score"),
            "mortality_pct": (s.get("mortality_pct") or {}).get("median"),
            "llm_roles": bool(s.get("llm_roles")),
        })
    gaps.sort(key=lambda g: (-(g["susceptibility"] or 0)))

    # ---- strategy matrix: platform × target sector × DIVA (the
    # "targets" layer — what is being built, for whom) ----
    strat = {}
    for c in claims_rows:
        plat = c.get("platform") or "unspecified"
        sector = c.get("wild_or_domestic") or "unspecified"
        key = (plat, sector)
        e = strat.setdefault(key, {"claims": 0, "diva": 0,
                                   "species": set()})
        e["claims"] += 1
        if c.get("diva_compatible"):
            e["diva"] += 1
        if c.get("species"):
            e["species"].add(str(c["species"])[:40])
    strategy_matrix = [
        {"platform": k[0], "sector": k[1], "claims": v["claims"],
         "diva": v["diva"], "species": sorted(v["species"])[:6]}
        for k, v in sorted(strat.items(), key=lambda kv: -kv[1]["claims"])
    ]

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "vaccination_outcomes": "PAPER_EXTRACTED (intervention_response, "
                                   "quote-grounded)",
            "platform_claims": "mine_vaccines verified claims",
            "protection_gaps": "MODELED join: competence susceptibility × "
                               "vaccination targets (absence = candidate)",
        },
        "vaccination": {
            "items": vax_items,
            "papers": len({v["paper_id"] for v in vax_items}),
            "outcomes": dict(Counter(v["outcome"] or "unclear" for v in vax_items)),
            "targets": dict(Counter(v["target_species"] or "?"
                                    for v in vax_items)),
            "settings": dict(Counter(v["setting"] or "?" for v in vax_items)),
            "by_year": {str(y): n for y, n in sorted(by_year.items())},
        },
        "wild_programs": wild_programs,
        "response_landscape": dict(interventions),
        "platforms": {
            "claims": claims_n,
            "by_platform": dict(platforms.most_common()),
            "field_or_lab": dict(field_lab),
            "diva_compatible": diva,
            "efficacy_rows": efficacy_rows,
            "strategy_matrix": strategy_matrix,
        },
        "protection_gaps": {
            "vaccinated_species": sorted(vaccinated),
            "candidates": gaps,
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"vaccination outcomes: {len(vax_items)} items "
          f"({doc['vaccination']['papers']} papers), "
          f"outcomes {doc['vaccination']['outcomes']}")
    print(f"wild/captive/zoo programs: {len(wild_programs)}")
    print(f"platform claims: {claims_n} ({diva} DIVA-compatible, "
          f"{len(efficacy_rows)} with mortality deltas)")
    print(f"protection gaps: {len(gaps)} susceptible species with no "
          f"vaccination evidence; vaccinated: {len(vaccinated)}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
