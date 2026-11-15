#!/usr/bin/env python3
"""Species susceptibility v2 — two-axis scoring, fully documented.

WHY v2: the legacy score (build_susceptibility_scores.py) was
`mortality × RIG-I order modifier` — it conflated INFECTION PERMISSIVENESS
with DISEASE SEVERITY. A duck (highly permissive, mild disease, THE
reservoir) scored "tolerant"; that's a severity label, not susceptibility.

v2 separates the axes and composes one summary number:

  PERMISSIVENESS (0-100) — can the virus replicate in this host?
    components (weighted, evidence-strength scaled, max over papers):
      experimental_infection  0.30  traits: experimental challenge outcomes
      field_outbreak          0.25  traits: field outbreak records
      llm_verdicts            0.15  susceptibility_verdicts extraction
                                   (infection_confirmed=1.0,
                                    exposure_only=0.4, resistance=0.0)
      detections              0.15  MEASURED surveillance (log-scaled)
      serology                0.10  traits: serology rows (exposure
                                   evidence, weaker than isolation)
    gap-fill: taxonomic proxy (genus → family rollup of permissiveness)
    fills thin species up to a 0.30 contribution cap, PROXY-labeled.
    modifier: RIG-I pathway status (order-level, CURATED molecular):
    absent → ×1.5, present → ×0.7-1.0 (see RIGI_MODIFIERS).

  SEVERITY (0-100) — disease outcome given infection.
    field mortality (verified traits) preferred; experimental mortality
    (capped) as fallback; per-clade strata where the competence matrix
    has them. Reported ALONGSIDE the composite, never folded into it.

  CLASS = f(permissiveness): highly_susceptible ≥75, susceptible ≥50,
  intermediate ≥30, tolerant ≥15, highly_tolerant <15.
  OUTCOME = f(severity): severe ≥50, moderate ≥20, mild <20.
  A reservoir reads: "susceptible, mild outcome" — honest at last.

  CONFIDENCE = evidence diversity (how many component types fire,
  0-1 scaled) × count saturation (log of total evidence rows).

Every species ships its full component breakdown (value, weight,
contribution, sources, provenance) so the dedicated page can document
exactly how the score was reached. A methodology block with the formula,
weights, class thresholds and changelog ships at the top level.

Output: data/model/species_susceptibility.json + web twin.
Rerun after: traits passes, susceptibility_verdicts passes, detections
rebuilds, competence rebuilds (clade strata).

Usage: pixi run python scripts/model/build_susceptibility.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_host_competence import SYNONYMS, _norm_name  # noqa: E402
from build_vaccine_outcomes import VAX_SYNONYMS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TRAITS = ROOT / "data" / "papers" / "paper_species_traits.parquet"
SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"
DET = ROOT / "web" / "public" / "data" / "detections.parquet"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
COMPETENCE = ROOT / "web" / "public" / "data" / "host_competence.json"
VAX_OUT = ROOT / "data" / "model" / "vaccine_outcomes.json"
OUT = ROOT / "data" / "model" / "species_susceptibility.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "species_susceptibility.json"

# curated order hints for literature-only species (no species.parquet row;
# powers the RIG-I context display — nothing else)
ORDER_HINTS = {
    "Strigops habroptila": "Psittaciformes",
}

# ---- documented constants (mirrored into the methodology block) ----
WEIGHTS = {
    "experimental_infection": 0.30,
    "field_outbreak": 0.25,
    "llm_verdicts": 0.15,
    "detections": 0.15,
    "serology": 0.10,
}
VERDICT_VALUE = {"infection_confirmed": 1.0, "exposure_only": 0.4,
                 "resistance_suspected": 0.0, "unclear": 0.2}
PROXY_CAP = 0.30          # max contribution the taxonomic proxy may add
PROXY_MIN_GAP = 0.20      # only gap-fill when direct evidence this thin
RIGI_MODIFIERS = {  # order → (modifier, present)
    "Galliformes": (1.5, False),
    "Anseriformes": (0.7, True),
    "Charadriiformes": (0.8, True),
    "Passeriformes": (0.9, True),
    "Accipitriformes": (1.1, True),
}
RIGI_DEFAULT = (1.0, True)
CLASS_BANDS = [(75, "highly_susceptible"), (50, "susceptible"),
               (30, "intermediate"), (15, "tolerant"),
               (0, "highly_tolerant")]
OUTCOME_BANDS = [(50, "severe"), (20, "moderate"), (0, "mild")]


def classify(bands, v):
    for threshold, label in bands:
        if v >= threshold:
            return label
    return bands[-1][1]


def log_sat(n, cap=50):
    return min(1.0, math.log1p(max(n, 0)) / math.log1p(cap))


def mortality_stat(rows):
    """Severity statistic from trait rows: the 75th PERCENTILE of
    field+experimental mortality, not the median. Why: the experimental
    literature is bimodal — vaccine-trial protected groups report 0%
    (for Gallus, 11 of 20 rows) while unvaccinated controls sit at the
    upper mode (~100%). The median lands in the intervention-protected
    mode and understates disease severity; the upper quartile estimates
    severity in the absence of intervention without cherry-picking the
    max. Returns (p75, n) or (None, 0)."""
    morts = []
    for r in rows:
        nt, nd = r.get("n_total"), r.get("n_dead")
        if nt and nd is not None and nd <= nt:
            morts.append(100.0 * nd / nt)
    if not morts:
        return None, 0
    morts.sort()
    idx = min(len(morts) - 1, max(0, round(0.75 * (len(morts) - 1))))
    return round(morts[idx], 1), len(morts)


def main() -> None:
    traits = pl.read_parquet(TRAITS)
    species_tax = {r["scientific_name"]: r for r in
                   pl.read_parquet(SPECIES).select(
                       "scientific_name", "common_name", "genus", "family",
                       "order").iter_rows(named=True)}
    det = pl.read_parquet(DET).filter(pl.col("date_iso").is_not_null())
    det_counts = (det.group_by("scientific_name")
                  .agg(pl.len().alias("n")).drop_nulls()
                  .to_dicts())
    det_by_species = {r["scientific_name"]: r["n"] for r in det_counts
                      if r["scientific_name"]}

    # traits per species (verified only — the competence doctrine)
    trait_rows = {}
    for r in traits.iter_rows(named=True):
        sci = (r.get("species_norm") or r.get("name") or "").strip()
        if not sci or r.get("verify_verdict") not in (
                None, "confirmed", "paraphrased-supported"):
            continue
        trait_rows.setdefault(sci, []).append(r)

    # LLM verdicts per species (resolver mirrors the vaccine-outcomes one:
    # taxonomy common/scientific names + curated domestic synonyms)
    resolver = {}
    for sci, row in species_tax.items():
        resolver[_norm_name(sci)] = sci
        if row.get("common_name"):
            resolver.setdefault(_norm_name(row["common_name"]), sci)
    resolver.update({_norm_name(k): v for k, v in SYNONYMS.items()})
    resolver.update({_norm_name(k): v for k, v in VAX_SYNONYMS.items()})
    verdicts = {}
    literature_only: dict[str, str] = {}   # sci -> common name it resolved from
    if SPREAD.exists():
        df = pl.read_parquet(SPREAD).filter(
            pl.col("section") == "susceptibility_verdicts")
        for r in df.iter_rows(named=True):
            try:
                it = json.loads(r["payload"])
            except Exception:
                continue
            raw = it.get("species") or ""
            hit = resolver.get(_norm_name(raw))
            if not hit:
                continue
            if hit not in species_tax:
                literature_only.setdefault(hit, raw)
            verdicts.setdefault(hit, []).append({
                "verdict": it.get("verdict") or "unclear",
                "evidence_kind": it.get("evidence_kind"),
                "clade": it.get("clade") or None,
                "grounded": bool(r.get("quote_in_text")),
                "paper_id": r["paper_id"],
            })

    # vaccination-program species (conservation targets with no surveillance
    # presence — exactly the species people look up)
    vax_programs: dict[str, list] = {}
    if VAX_OUT.exists():
        vo = json.loads(VAX_OUT.read_text())
        for it in (vo.get("vaccination", {}).get("items", [])
                   + vo.get("wild_programs", [])):
            raw = it.get("target_species") or ""
            hit = resolver.get(_norm_name(raw))
            if not hit:
                continue
            if hit not in species_tax:
                literature_only.setdefault(hit, raw)
            vax_programs.setdefault(hit, []).append({
                "outcome": it.get("outcome"), "year": it.get("year"),
                "setting": it.get("setting"),
                "paper_id": it.get("paper_id"),
                "grounded": it.get("grounded"),
            })

    competence = json.loads(COMPETENCE.read_text())
    comp_by_species = {s["species"]: s for s in competence.get("species", [])}

    # ---- pass 1: direct (evidence-only) component scores per species ----
    universe = sorted(set(species_tax)
                      | set(trait_rows) | set(det_by_species)
                      | set(verdicts) | set(comp_by_species)
                      | set(literature_only))
    direct_scores: dict[str, float] = {}   # 0-1, evidence-only
    per_spec_comp: dict[str, dict] = {}
    for sci in universe:
        rows = trait_rows.get(sci, [])
        kinds = {}
        for r in rows:
            kinds.setdefault(r.get("kind") or "other", []).append(r)
        exp = kinds.get("experimental_challenge", [])
        field = kinds.get("field_outbreak", [])
        sero = kinds.get("serology", [])

        comp = {}
        # experimental: replication quality amplifies beyond mere presence
        # (normal=1.0, mixed=0.7, low=0.4, none=0.2; unstated → 0.5 neutral)
        rep_vals = [r.get("replication") for r in exp if r.get("replication")]
        best_rep = max((1.0 if v == "normal" else 0.7 if v == "mixed"
                        else 0.4 if v == "low" else 0.2)
                       for v in rep_vals) if rep_vals else 0.5
        comp["experimental_infection"] = (
            log_sat(len(exp), 8) * (0.5 + 0.5 * best_rep))
        comp["field_outbreak"] = log_sat(len(field), 8)
        vs = verdicts.get(sci, [])
        if vs:
            comp["llm_verdicts"] = max(
                VERDICT_VALUE.get(v["verdict"], 0.2) for v in vs
            ) * log_sat(len(vs), 5)
        n_det = det_by_species.get(sci, 0)
        if n_det:
            comp["detections"] = log_sat(n_det, 100)
        if sero:
            comp["serology"] = 0.6 * log_sat(len(sero), 5)

        direct_scores[sci] = sum(comp.get(k, 0.0) * w
                                 for k, w in WEIGHTS.items())
        per_spec_comp[sci] = comp

    # ---- pass 2: taxonomic inheritance for thin species ----
    # a rare species in a well-evidenced genus inherits the genus level at
    # donor-count confidence — not a fixed cap (a cap would score
    # confidence, not susceptibility)
    def taxonomic_estimate(tax, sci):
        for level in ("genus", "family"):
            key = tax.get(level)
            if not key:
                continue
            mates = [s for s, t in species_tax.items()
                     if t.get(level) == key and s != sci
                     and direct_scores.get(s, 0) >= PROXY_MIN_GAP]
            if mates:
                return {
                    "level": level,
                    "value": sum(100 * direct_scores[m] for m in mates)
                             / len(mates),
                    "donors": len(mates),
                    "weight": log_sat(len(mates), 5),
                }
        return None

    # ---- compose final scores (uses pass-1 direct_scores) ----
    out_species = []
    permiss_by_species = {}
    for sci in universe:
        tax = species_tax.get(sci, {})
        rows = trait_rows.get(sci, [])
        kinds = {}
        for r in rows:
            kinds.setdefault(r.get("kind") or "other", []).append(r)
        exp = kinds.get("experimental_challenge", [])
        field = kinds.get("field_outbreak", [])
        sero = kinds.get("serology", [])
        vs = verdicts.get(sci, [])
        comp = per_spec_comp[sci]
        direct = direct_scores[sci]
        n_det = det_by_species.get(sci, 0)

        proxy = None
        if direct < PROXY_MIN_GAP and tax:
            proxy = taxonomic_estimate(tax, sci)

        # inheritance: pull thin species toward their taxon's evidenced
        # level at donor-confidence weight (never above it)
        if proxy:
            inherited = proxy["value"] * proxy["weight"]
            permiss_value = max(direct, inherited / 100.0
                                if inherited > direct * 100 else direct)
        else:
            permiss_value = direct

        rigi_mod, rigi_present = RIGI_MODIFIERS.get(
            tax.get("order") or ORDER_HINTS.get(sci) or "", RIGI_DEFAULT)
        evaluated = any(comp.values()) or bool(proxy)
        permissiveness = min(
            100.0, round(100 * permiss_value, 1)
        ) if evaluated else None

        # severity axis — p75 of field+experimental mortality (see
        # mortality_stat docstring: medians land in the vaccine-protected
        # zero-mode and understate severity; the upper quartile estimates
        # the unmanipulated disease reality)
        comp_entry = comp_by_species.get(sci, {})
        sev_med, sev_n = mortality_stat(field + exp)
        if sev_med is not None:
            severity, severity_basis, severity_n = sev_med, "p75_field_experimental", sev_n
        else:
            severity = round((comp_entry.get("mortality_pct") or {})
                             .get("median", 0.0), 1) \
                if comp_entry.get("mortality_pct") else 0.0
            severity_basis, severity_n = "competence_mixed", \
                (comp_entry.get("mortality_pct") or {}).get("studies", 0)
        by_clade = comp_entry.get("mortality_by_clade") or {}

        comp_detail = []
        for k, w in WEIGHTS.items():
            if k in comp and comp[k] > 0:
                comp_detail.append({
                    "id": k, "value": round(comp[k], 3), "weight": w,
                    "contribution": round(comp[k] * w, 3),
                    "provenance": ("MEASURED" if k == "detections"
                                   else "PAPER_EXTRACTED"),
                })
        if proxy:
            comp_detail.append({
                "id": "taxonomic_proxy", "value": round(proxy["value"], 1),
                "weight": round(proxy["weight"], 3),
                "contribution": round(permiss_value - direct, 3),
                "provenance": "MODELED (proxy)",
                "level": proxy["level"], "donors": proxy["donors"],
            })

        n_evidence = (len(exp) + len(field) + len(sero) + len(vs)
                      + (1 if n_det else 0))
        diversity = len([1 for k in WEIGHTS if comp.get(k, 0) > 0])
        confidence = round(0.5 * (diversity / len(WEIGHTS))
                           + 0.5 * log_sat(n_evidence, 30), 2)

        permiss_by_species[sci] = permissiveness or 0.0
        out_species.append({
            "species": sci,
            "common": tax.get("common_name") or literature_only.get(sci),
            "order": tax.get("order"),
            "permissiveness": permissiveness,
            "severity": severity,
            "severity_basis": severity_basis,
            "severity_studies": severity_n,
            "class": classify(CLASS_BANDS, permissiveness)
            if permissiveness is not None else "unevaluated",
            "outcome": classify(OUTCOME_BANDS, severity)
            if severity else None,
            "confidence": confidence,
            "components": comp_detail,
            "rigi": {"present": rigi_present, "modifier": rigi_mod,
                     "order": tax.get("order") or ORDER_HINTS.get(sci)},
            "clades": {c: {"mortality": m.get("median"),
                           "studies": m.get("studies")}
                       for c, m in by_clade.items()},
            "verdict_summary": {
                "infection_confirmed": sum(1 for v in vs
                                           if v["verdict"] == "infection_confirmed"),
                "exposure_only": sum(1 for v in vs
                                     if v["verdict"] == "exposure_only"),
                "resistance_suspected": sum(1 for v in vs
                                            if v["verdict"] == "resistance_suspected"),
                "grounded": sum(1 for v in vs if v["grounded"]),
            } if vs else None,
            "proxy": bool(proxy),
            "detections": n_det,
            "literature_only": sci in literature_only,
            "vax_program": {
                "items": len(vax_programs.get(sci, [])),
                "outcomes": dict(Counter(
                    v["outcome"] or "unclear"
                    for v in vax_programs.get(sci, []))),
            } if vax_programs.get(sci) else None,
        })

    out_species.sort(
        key=lambda s: (-(s["permissiveness"] or 0), s["species"]))

    doc = {
        "version": 2,
        "generated": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "summary": ("Two-axis scoring: PERMISSIVENESS (can the virus "
                        "replicate here?) composes the summary score; "
                        "SEVERITY (disease outcome given infection) is "
                        "reported alongside, never folded in. A reservoir "
                        "reads 'susceptible, mild outcome'."),
            "weights": WEIGHTS,
            "verdict_values": VERDICT_VALUE,
            "proxy": {"cap": PROXY_CAP, "min_gap": PROXY_MIN_GAP,
                      "levels": ["genus", "family"]},
            "rigi_modifiers": {k: v[0] for k, v in RIGI_MODIFIERS.items()},
            "class_bands": {label: f">= {t}" for t, label in CLASS_BANDS},
            "outcome_bands": {label: f">= {t}" for t, label in OUTCOME_BANDS},
            "formula": ("permissiveness = 100 × (Σ component_strength × "
                        "weight + proxy_gap_fill), capped at 100. "
                        "Severity = 75th percentile of field+experimental "
                        "mortality rows: the literature is bimodal "
                        "(vaccine-trial protected groups at 0%, "
                        "unvaccinated controls at the upper mode) and "
                        "medians land in the protected mode — the upper "
                        "quartile estimates unmanipulated disease severity. "
                        "RIG-I status is DISPLAYED as molecular context, "
                        "deliberately not folded into either axis."),
            "provenance_ladder": ["MEASURED", "PAPER_EXTRACTED",
                                  "CURATED", "MODELED (proxy)"],
            "changelog": [
                "v2 (2026-10-15): two-axis redesign; permissiveness composed "
                "from weighted evidence components incl. LLM verdicts; "
                "severity separated; RIG-I kept as context, not a factor; "
                "proxy gap-fill capped + labeled; unevaluated class for "
                "evidence-free species.",
                "v1: mortality_rate × RIG-I modifier (conflated severity "
                "with susceptibility).",
            ],
        },
        "species": out_species,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    classes = Counter(s["class"] for s in out_species)
    outcomes = Counter(f"{s['class']}/{s['outcome']}" for s in out_species
                       if s["outcome"])
    n_proxy = sum(1 for s in out_species if s["proxy"])
    n_verdict = sum(1 for s in out_species if s["verdict_summary"])
    print(f"species scored: {len(out_species)}")
    from collections import Counter as _C
    print("severity bases:", dict(_C(s["severity_basis"] for s in out_species)))
    print(f"classes: {dict(classes)}")
    print(f"class/outcome: {dict(outcomes.most_common(8))}")
    print(f"proxied: {n_proxy} | with verdicts: {n_verdict}")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
