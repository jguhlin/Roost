#!/usr/bin/env python3
"""Spread synthesis (2026-10-15): the item-level corpus ledgers.

The vaccine synthesis consolidated outcomes; this does the same for spread:
the 3,900+ structured extraction items aggregated into research-usable
ledgers, each quote-grounded and provenance-labeled:

  introductions       introduction events by year, route, direction, era
  mammal_chains       mammal-to-mammal evidence per species + setting
  virus_ledger        reassortment events + adaptation mutations
  transmission_params quantitative parameters with contexts
  silent_spread       detection-lag evidence (circulation before first report)
  establishment       regional establishment outcomes tally
  response            non-vaccine interventions with outcomes
  surveillance        coverage statements by region/modality
  impact_recovery     documented population consequences

Output: data/model/spread_synthesis.json + web twin.
Rerun after any extraction pass (`pixi run spread-rebuild` tail).

Usage: pixi run python scripts/model/build_spread_synthesis.py
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
from region_norm import region_bucket  # noqa: E402
SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"
PAPERS = ROOT / "web" / "public" / "data" / "papers.json"
ERAS = ROOT / "data" / "model" / "spread_eras.json"
OUT = ROOT / "data" / "model" / "spread_synthesis.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "spread_synthesis.json"

PROV = "PAPER_EXTRACTED (llm_extract_spread v2, quote-grounded)"

YEAR_RE = re.compile(r"(19|20)\d{2}")
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july',
          'august', 'september', 'october', 'november', 'december']


def _ym(s):
    """('October 2022', 'late 2021') -> (2022, 10) / (2021, 6-default)."""
    if not s:
        return None
    s = str(s).lower()
    y = YEAR_RE.search(s)
    m = next((i + 1 for i, mo in enumerate(MONTHS) if mo[:3] in s), None)
    return (int(y.group(0)), m) if y else None


def detection_lag(silent_items):
    """Median months between evidence-backed circulation start and the
    first report (prior belief) — the corpus's own detection-lag estimate."""
    lags = []
    worst = []
    for it in silent_items:
        a, b = _ym(it.get("circulation_window")), _ym(it.get("prior_belief"))
        if not (a and b and a[0] and b[0]):
            continue
        months = (b[0] - a[0]) * 12 + ((b[1] or 6) - (a[1] or 6))
        if -6 < months < 60:
            lags.append(months)
            worst.append({"region": it.get("region"), "months": months,
                          "evidence": it.get("evidence")})
    if not lags:
        return None
    lags.sort()
    worst.sort(key=lambda w: -w["months"])
    n = len(lags)
    return {"n": n, "median": lags[n // 2], "p25": lags[n // 4],
            "p75": lags[3 * n // 4], "max": lags[-1],
            "worst": worst[:5]}


def _year(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    m = YEAR_RE.search(str(s))
    return int(m.group(0)) if m else None


def era_for(year):
    if year is None:
        return None
    for era in ERAS_DATA:
        start = _year(era["window"]["start"])
        end = _year(era["window"].get("end")) or 2100
        if start <= year <= end:
            return era["id"]
    return None


ERAS_DATA = []


def rows(df, section):
    out = []
    d = df.filter(pl.col("section") == section)
    for r in d.iter_rows(named=True):
        try:
            it = json.loads(r["payload"])
        except Exception:
            continue
        it["_paper"] = r["paper_id"]
        it["_grounded"] = bool(r.get("quote_in_text"))
        it["_year"] = _year(it.get("date_window") or it.get("date"))
        out.append(it)
    return out


def main() -> None:
    global ERAS_DATA
    df = pl.read_parquet(SPREAD)
    papers = {p["id"]: p for p in json.loads(PAPERS.read_text())["papers"]}
    ERAS_DATA = json.loads(ERAS.read_text())["eras"]

    intro = rows(df, "introduction_events")
    for it in intro:
        it["_era"] = era_for(it["_year"])
        it["_title"] = (papers.get(it["_paper"]) or {}).get("title", "")

    mam = rows(df, "mammal_chains")
    mam_species = Counter()
    for it in mam:
        mam_species[(it.get("species") or "?")] += 1

    reassort = rows(df, "reassortment_events")
    adapt = rows(df, "adaptation_mutations")
    params = rows(df, "transmission_params")
    silent = rows(df, "silent_spread")
    estab = rows(df, "establishment")
    response = rows(df, "intervention_response")
    response = [it for it in response
                if "vaccin" not in (it.get("intervention") or "").lower()]
    surv = rows(df, "surveillance_coverage")
    impact = rows(df, "impact_recovery")

    # ---- derived findings (computed, never hardcoded) ----
    lag = detection_lag(silent)
    surv_modal = Counter((it.get("modality") or "other") for it in surv)
    n_loss = sum(1 for it in impact if it.get("loss"))
    n_rec = sum(1 for it in impact if it.get("recovery"))
    b_items = [it for it in estab if "2.3.4.4b" in (it.get("lineage") or "")]
    o_items = [it for it in estab if "2.3.4.4b" not in (it.get("lineage") or "")]
    def _est_pct(items):
        if not items:
            return 0
        return round(100 * sum(1 for x in items
                                if x.get("outcome") == "established") / len(items))
    r0_vals = []
    for it in params:
        if (it.get("parameter") or "").lower() in ("r0", "rt"):
            try:
                v = float(str(it.get("value")).lstrip(">~<≈ "))
                r0_vals.append((v, it.get("context")))
            except (TypeError, ValueError):
                continue
    findings = {
        "detection_lag": lag,
        "surveillance_lens": {
            "counts": dict(surv_modal.most_common()),
            "mortality_based": surv_modal.get("mortality", 0),
            "active": surv_modal.get("active", 0),
            "environmental": surv_modal.get("environmental", 0),
            "sentinel": surv_modal.get("sentinel", 0),
        },
        "loss_recovery": {"loss": n_loss, "recovery": n_rec},
        "establishment_2344b": {
            "n": len(b_items), "share_pct": round(100 * len(b_items) / len(estab))
            if estab else 0,
            "established_pct": _est_pct(b_items),
            "other_established_pct": _est_pct(o_items),
            "burned_out": sum(1 for x in b_items
                              if x.get("outcome") == "burned_out"),
        },
        "r0_range": {
            "n": len(r0_vals),
            "min": min(v for v, _ in r0_vals) if r0_vals else None,
            "max": max(v for v, _ in r0_vals) if r0_vals else None,
            "low": min(r0_vals, key=lambda x: x[0]) if r0_vals else None,
            "high": max(r0_vals, key=lambda x: x[0]) if r0_vals else None,
        },
    }

    intro.sort(key=lambda it: (it["_year"] or 9999, it["_paper"]))
    est_tally = Counter((it.get("outcome") or "unclear") for it in estab)
    silent_kinds = Counter((it.get("evidence") or "other") for it in silent)
    # honest-window note: 2.3.4.4b events pre-dating the curated panzootic
    # window (emergence-phase circulation, e.g. H5N8→H5N1 2020 Europe) —
    # the join stays window-based; the count makes the pattern visible
    emergence_phase = sum(
        1 for it in intro
        if it.get("_era") == "zoonotic_2321c"
        and "2.3.4.4" in (it.get("lineage") or ""))

    # ---- region-normalized route × establishment join ----
    # (the last unmapped synthesis join: do migration-route regions
    # establish differently than trade-route regions?)
    region_matrix = {}
    for it in intro:
        b = region_bucket(it.get("dest_region"))
        if not b:
            continue
        e = region_matrix.setdefault(b, {"introductions": Counter(),
                                         "establishment": Counter()})
        e["introductions"][it.get("route") or "unknown"] += 1
    for it in estab:
        b = region_bucket(it.get("region"))
        if not b:
            continue
        e = region_matrix.setdefault(b, {"introductions": Counter(),
                                         "establishment": Counter()})
        e["establishment"][it.get("outcome") or "unclear"] += 1
    region_matrix_out = {
        b: {"introductions": dict(v["introductions"].most_common()),
            "establishment": dict(v["establishment"].most_common()),
            "established_pct": round(100 * v["establishment"].get(
                "established", 0) / max(1, sum(v["establishment"].values())))}
        for b, v in region_matrix.items()
    }

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "provenance": PROV,
        "findings": findings,
        "introductions": {
            "items": [
                {k: it.get(k) for k in
                 ("lineage", "date_window", "source_region", "dest_region",
                  "route", "direction", "location_detail", "basis")}
                | {"paper_id": it["_paper"], "year": it["_year"],
                   "era": it["_era"], "grounded": it["_grounded"]}
                for it in intro
            ],
            "by_route": dict(Counter((it.get("route") or "?") for it in intro)),
            "by_direction": dict(Counter((it.get("direction") or "unknown")
                                         for it in intro)),
            "by_era": dict(Counter(it["_era"] or "unmapped" for it in intro)),
            "years": {str(y): n for y, n in
                      sorted(Counter(it["_year"] for it in intro
                                     if it["_year"]).items())},
            "emergence_phase_note": {
                "count": emergence_phase,
                "note": "2.3.4.4b-lineage events dated before the curated "
                        "panzootic window (2021-10) — emergence-phase "
                        "circulation; the era ledger may warrant an "
                        "emergence sub-chapter",
            },
        },
        "mammal_chains": {
            "items": [
                {k: it.get(k) for k in ("species", "setting", "evidence_kind",
                                        "scale", "date")}
                | {"paper_id": it["_paper"], "year": it["_year"],
                   "grounded": it["_grounded"]}
                for it in mam
            ],
            "by_species": dict(mam_species.most_common()),
            "by_evidence": dict(Counter((it.get("evidence_kind") or "?")
                                        for it in mam)),
        },
        "virus_ledger": {
            "reassortments": [
                {k: it.get(k) for k in ("genotype_or_name", "segments",
                                        "donor_lineages", "host_context",
                                        "date_window")}
                | {"paper_id": it["_paper"], "grounded": it["_grounded"]}
                for it in reassort
            ],
            "adaptations": [
                {k: it.get(k) for k in ("mutation", "gene", "phenotype",
                                        "host_context", "clade")}
                | {"paper_id": it["_paper"], "grounded": it["_grounded"]}
                for it in adapt
            ],
        },
        "transmission_params": {
            "items": [
                {k: it.get(k) for k in ("parameter", "value", "unit", "context")}
                | {"paper_id": it["_paper"], "grounded": it["_grounded"]}
                for it in params
            ],
            "by_parameter": dict(Counter((it.get("parameter") or "?")
                                         for it in params)),
        },
        "silent_spread": {
            "items": [
                {k: it.get(k) for k in ("evidence", "region",
                                        "circulation_window", "prior_belief")}
                | {"paper_id": it["_paper"], "grounded": it["_grounded"]}
                for it in silent
            ],
            "by_evidence": dict(silent_kinds),
        },
        "establishment": {
            "items": [
                {k: it.get(k) for k in ("region", "lineage", "outcome", "basis")}
                | {"paper_id": it["_paper"], "grounded": it["_grounded"]}
                for it in estab
            ],
            "outcomes": dict(est_tally),
            "region_matrix": region_matrix_out,
        },
        "response": {
            "items": [
                {k: it.get(k) for k in ("intervention", "target_species",
                                        "setting", "outcome", "metric")}
                | {"paper_id": it["_paper"], "year": it["_year"],
                   "grounded": it["_grounded"]}
                for it in response
            ],
            "by_intervention": dict(Counter((it.get("intervention") or "?")
                                            for it in response)),
            "outcomes": dict(Counter((it.get("outcome") or "unclear")
                                     for it in response)),
        },
        "surveillance": {
            "items": [
                {k: it.get(k) for k in ("region", "modality",
                                        "coverage_statement", "gap")}
                | {"paper_id": it["_paper"], "grounded": it["_grounded"]}
                for it in surv
            ],
            "by_modality": dict(Counter((it.get("modality") or "?")
                                        for it in surv)),
        },
        "impact_recovery": {
            "items": [
                {k: it.get(k) for k in ("species", "location", "loss",
                                        "recovery", "timeframe")}
                | {"paper_id": it["_paper"], "year": it["_year"],
                   "grounded": it["_grounded"]}
                for it in impact
            ],
        },
        "grounded_totals": {
            sec: sum(1 for it in rows(df, sec) if it["_grounded"])
            for sec in ("introduction_events", "mammal_chains",
                        "reassortment_events", "adaptation_mutations",
                        "transmission_params", "silent_spread",
                        "establishment", "intervention_response",
                        "surveillance_coverage", "impact_recovery")
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"introductions: {len(intro)} (eras: {doc['introductions']['by_era']})")
    print(f"  direction: {doc['introductions']['by_direction']}")
    if lag:
        print(f"FINDING detection lag: median {lag['median']} mo "
              f"(n={lag['n']}, IQR {lag['p25']}-{lag['p75']}, "
              f"max {lag['max']})")
    print(f"FINDING surveillance: mortality {findings['surveillance_lens']['mortality_based']}"
          f" vs active {findings['surveillance_lens']['active']}")
    print(f"FINDING loss:recovery {n_loss}:{n_rec}")
    print(f"FINDING 2.3.4.4b establishment: {findings['establishment_2344b']}")
    print(f"FINDING R0 range: {findings['r0_range']['min']}-{findings['r0_range']['max']}"
          f" (n={findings['r0_range']['n']})")
    print(f"  2.3.4.4b emergence-phase (pre-2021-10): {emergence_phase}")
    print(f"mammal chains: {len(mam)} — top: {mam_species.most_common(4)}")
    print(f"virus ledger: {len(reassort)} reassortments, {len(adapt)} adaptations")
    print(f"params: {len(params)} — {doc['transmission_params']['by_parameter']}")
    print(f"silent spread: {len(silent)}; establishment: {dict(est_tally)}")
    print(f"region matrix: {len(region_matrix_out)} buckets mapped "
          f"({sum(sum(v['introductions'].values()) for v in region_matrix_out.values())}"
          f" intros, "
          f"{sum(sum(v['establishment'].values()) for v in region_matrix_out.values())}"
          f" est items)")
    print(f"response (non-vaccine): {len(response)} — "
          f"{doc['response']['by_intervention']}")
    print(f"surveillance: {len(surv)}; impact: {len(impact)}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
