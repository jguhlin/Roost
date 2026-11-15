#!/usr/bin/env python3
"""Spread-model evidence extraction v2 (SPREAD_MODEL.md Phase 6).

Per-paper iterative, quote-grounded extraction of spread-relevant structured
facts, replacing the D57 one-shot (extract_spread_data.py). Sections:

  introduction_events  discrete spread/introduction events with lineage,
                       date window, source→dest, route, direction
  host_roles           species roles in transmission + competence params
                       (mortality, shedding days, titer, seroprevalence, clade)
  transmission_params  R0/Rt/efficiency/odds ratios/diffusion rates
  persistence          environmental survival (matrix, temp, duration)
  mass_events          die-offs with scale, duration, trajectory, %pop
  seasonality          temporal pattern statement (single-shot)
  reassortment_events  segment constellations + donor lineages
  adaptation_mutations mutation × gene × phenotype × host context
  migration_links      species × flyway × timing claims
  trade_movements      LBMs / poultry / game birds / fighting cocks
  anthropogenic_mechanics  manure, equipment, vehicles, personnel, feed
  risk_factors         farm density / water / biosecurity / outdoor (OR/HR)
  mammal_chains        mammal-to-mammal transmission (mink, sea lions, cattle)
  silent_spread        evidence of undetected circulation
  establishment        region × lineage → established/burned_out/recurring
  surveillance_coverage  sampling coverage, gaps, sentinels, env detection
  intervention_response  what was done + outcome (vaccination, culling, …)
  impact_recovery      population consequences + recovery trajectories
  contact_structure    gregariousness, aggregation, mixed assemblages

Protocol per section (iterative exclusion, same family as
llm_iterative_extract.py): strongest item -> "we have these" -> next ->
FALSE. Every item carries a verbatim quote; quotes are checked against the
source markdown (normalized containment) and flagged quote_in_text.

Output: one JSON per paper at data/papers/spread_v2/{pid}.json
(sections -> items[]). --aggregate flattens them into
data/papers/paper_spread.parquet (paper_id, section, idx, payload, quote,
quote_in_text, extracted_at) for build_spread_edges v2 / Phase 7 layers.

Resume-safe: existing per-paper JSONs are skipped (delete to redo).
Wired into enrich_pipeline.py so every new paper flows through.

Usage:
  pixi run python scripts/papers/llm_extract_spread.py [--workers 24]
      [--limit N] [--ids id1,id2] [--sections a,b] [--aggregate]
Env: LLM_BASE_URL (default http://localhost:8005/v1),
     LLM_MODEL (default muse-glimmer-30b), LLM_MAX_TOKENS, LLM_DISABLE_THINKING
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
OUT_DIR = ROOT / "data" / "papers" / "spread_v2"
PARQUET = ROOT / "data" / "papers" / "paper_spread.parquet"

BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
MAX_CHARS = 60_000
MAX_ROUNDS = 6

# scope priority: epi first, then wild/mammal, then the rest with fulltext
SCOPE_PRIORITY = ["avian-epi", "epidemiology", "avian", "mammalian",
                  "mixed", "human", "vaccination", "viral-biology"]


# ---------------------------------------------------------------- sections

def _q() -> str:
    return '"quote": "<=300-char VERBATIM quote from the paper>"'


SECTIONS: dict[str, dict] = {
    "introduction_events": {
        "first": """State the single most important SPREAD/INTRODUCTION EVENT this paper documents
or reconstructs: a virus lineage arriving in, dispersing to, or being
introduced across a region (phylogeographic inference, outbreak
investigation, surveillance first-detection, genomic reconstruction).
NOT general statements about transmission mechanisms.
Judge direction from the hosts/sectors named: wild birds→poultry =
wild_to_domestic; poultry/backyard spillback to wild birds =
domestic_to_wild; wild→wild movement = wild_to_wild; not stated = unknown.
Return JSON:
{"item": {"lineage": "<clade/genotype, e.g. 2.3.4.4b, B3.2, D1.1, or 'unspecified'>",
          "date_window": "<e.g. 'Oct 2021', '2020-2021', 'autumn 2016'>",
          "source_region": "<origin as the paper states/infers>",
          "dest_region": "<destination>",
          "route": "<migration|trade|unknown|local_amplification|reassortment>",
          "direction": "<wild_to_domestic|domestic_to_wild|wild_to_wild|unknown>",
          "basis": "<genomic|surveillance|outbreak_investigation|experimental>",
          {_QUOTE_}}}
— or exactly {{"item": false}} if the paper documents no such event.""",
        "next": """We already have these events:
{known}
State ONE additional DISTINCT spread/introduction event (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "host_roles": {
        "first": """State the single most spread-relevant HOST ROLE finding: a species assigned
a role in H5N1/AIV transmission, OR a competence parameter that matters for
spread (shedding duration/titre in a transmission context, field mortality
during an outbreak, seroprevalence indicating exposure).
Return JSON:
{"item": {"species": "<species or group as stated>",
          "roles": ["<reservoir|amplifier|bridge|dead_end|sentinel>"],
          "params": {"mortality_pct": <number or null>, "shedding_days": <number or null>,
                     "peak_titer": "<string or null>", "seroprevalence_pct": <number or null>,
                     "n": "<sample size or null>"},
          "clade": "<clade/genotype if stated, e.g. 2.3.4.4b, B3.13, else null>",
          {_QUOTE_}}}
— or exactly {{"item": false}} if the paper gives no species role or
competence parameter.""",
        "next": """We already have these host-role/competence findings:
{known}
State ONE additional DISTINCT species finding (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "transmission_params": {
        "first": """State the single most important QUANTITATIVE TRANSMISSION PARAMETER this
paper reports: R0/Rt, transmission efficiency/rate, contact-associated risk
(odds/hazard ratio for outbreak occurrence), geographic diffusion rate,
or similar.
Return JSON:
{"item": {"parameter": "<R0|Rt|transmission_efficiency|contact_rate|odds_ratio|hazard_ratio|diffusion_rate|other>",
          "value": <number or "x–y">, "unit": "<unit>",
          "context": "<host(s)/setting, e.g. 'ferret airborne', 'farm density per km2'>",
          {_QUOTE_}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these parameters:
{known}
State ONE additional DISTINCT parameter (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "persistence": {
        "first": """State the single most important ENVIRONMENTAL PERSISTENCE measurement:
how long infectious virus survives in water/on surfaces/in feed etc., with
conditions.
Return JSON:
{"item": {"matrix": "<water|fomite|feed|surface|air|feces|other>",
          "temperature_c": <number or null>, "salinity": "<string or null>",
          "duration": "<e.g. '37 days', '15-20 days'>",
          {_QUOTE_}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these persistence measurements:
{known}
State ONE additional DISTINCT measurement (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "mass_events": {
        "first": """State the single most significant MASS MORTALITY/OUTBREAK EVENT this paper
documents: wildlife colony die-off, farm outbreak, market event, marine
mammal mortality — with scale.
Return JSON:
{"item": {"kind": "<colony|farm|market|wildlife|marine_mammal|captive>",
          "location": "<place>", "date": "<date or window>",
          "scale": "<e.g. '>=19,326 adult deaths', '2.8M poultry culled', '17,000 sea lions'>",
          "duration_days": <number or null>,
          "trajectory": "<pulse|sustained|escalating|unknown>",
          "pct_population": "<e.g. '40% of colony' or null>",
          "species": "<species>",
          {_QUOTE_}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these events:
{known}
State ONE additional DISTINCT event (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "seasonality": {
        "first": """State this paper's SEASONALITY/TIMING finding about spread: when
transmission/outbreaks peak and what drives timing.
Return JSON (single item, no iteration):
{{"item": {{"statement": "<one sentence>",
          "pattern": "<autumn_peak|year_round|breeding_season|multi_peak|spring|none_stated>",
          "era": "<pre-2021|post-2021|both|unspecified>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if the paper says nothing about timing.""",
        "next": None,  # single-shot
    },
    "reassortment_events": {
        "first": """State the single most important REASSORTMENT EVENT this paper documents:
a genotype formed by segment reassortment (Eurasian × North American
lineages, or any donor constellation), with what's known of segment origins.
Return JSON:
{{"item": {{"genotype_or_name": "<e.g. 'H5N2 2014 NA reassortant', 'B3.13', or 'unnamed'>",
          "segments": "<which segments came from where, as stated>",
          "donor_lineages": "<donor clades/hosts as stated>",
          "host_context": "<host(s) where found>",
          "date_window": "<as stated>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these reassortment events:
{known}
State ONE additional DISTINCT event (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "adaptation_mutations": {
        "first": """State the single most important HOST-ADAPTATION MUTATION this paper
links to spread or host shift: PB2 627K/701N, HA cleavage-site changes,
receptor-binding changes, polymerase temperature adaptation, etc.
Return JSON:
{{"item": {{"mutation": "<e.g. 'PB2 E627K', 'HA multibasic cleavage site'>",
          "gene": "<gene>",
          "phenotype": "<receptor_binding|polymerase_adaptation|virulence|transmissibility|environmental_stability|host_range|other>",
          "host_context": "<host(s)/setting>",
          "clade": "<clade/genotype or null>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these adaptation mutations:
{known}
State ONE additional DISTINCT mutation (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "migration_links": {
        "first": """State the single most important MIGRATION-BASED SPREAD LINK this paper
claims: a species/population moving along a flyway or route connecting an
infected source region to a recipient region, with timing.
Return JSON:
{{"item": {{"species": "<species or group>",
          "flyway_or_route": "<as stated>",
          "timing": "<season/timing as stated>",
          "link_claim": "<what regions/populations the migration connects>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these migration links:
{known}
State ONE additional DISTINCT link (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "trade_movements": {
        "first": """State the single most important TRADE/MOVEMENT channel this paper
links to H5N1 spread: live bird markets, poultry trade, game-bird or
fighting-cock movement, pet bird trade, with route/volume if stated.
Return JSON:
{{"item": {{"kind": "<live_bird_market|poultry_trade|game_birds|fighting_cocks|pet_trade|other>",
          "route": "<origin→dest or region as stated>",
          "volume": "<as stated or null>",
          "evidence_link": "<how trade is tied to spread>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these trade/movement channels:
{known}
State ONE additional DISTINCT channel (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "anthropogenic_mechanics": {
        "first": """State the single most important HUMAN-MEDIATED MECHANISM this paper
links to spread between premises/regions: manure/litter spreading, shared
equipment, vehicles, personnel movement, contaminated feed, rendering —
the farm-to-farm mechanics.
Return JSON:
{{"item": {{"mechanism": "<manure_spreading|shared_equipment|vehicles|personnel|feed|rendering|other>",
          "setting": "<farm/dairy/market/other context>",
          "evidence_link": "<how the mechanism is tied to spread>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these mechanisms:
{known}
State ONE additional DISTINCT mechanism (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "risk_factors": {
        "first": """State the single most important RISK FACTOR this paper quantifies for
H5N1 outbreak occurrence/spread: farm density, proximity to waterfowl
habitat, biosecurity level, outdoor access, market proximity — with the
effect measure.
Return JSON:
{{"item": {{"factor": "<farm_density|water_proximity|biosecurity_level|outdoor_access|market_proximity|poultry_density|other>",
          "measure": "<OR/HR/RR + CI or p as stated>",
          "outcome": "<risk of what>",
          "setting": "<region/host context>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these risk factors:
{known}
State ONE additional DISTINCT factor (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "mammal_chains": {
        "first": """State the single most important MAMMAL-TO-MAMMAL TRANSMISSION finding
this paper reports: mink farm, sea lion colony, elephant seal rookery,
dairy cattle, zoo/rehab outbreaks — evidence of transmission BETWEEN
mammals (not just bird→mammal spillover).
Return JSON:
{{"item": {{"species": "<mammal species>",
          "setting": "<farm|colony|rookery|dairy|zoo|rehab|other>",
          "evidence_kind": "<genomic|epidemiological|experimental|observation>",
          "scale": "<n infected/dead, or sustained-transmission statement>",
          "date": "<as stated>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these mammal-chain findings:
{known}
State ONE additional DISTINCT finding (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "silent_spread": {
        "first": """State the single most important SILENT-SPREAD finding this paper
reports: evidence H5N1 circulated BEFORE first detection — retrospective
serosurveys, back-dated genomic estimates, wastewater positives, residual
archived samples.
Return JSON:
{{"item": {{"evidence": "<retrospective_serosurvey|backdated_genomic|wastewater|archived_samples|other>",
          "region": "<region>",
          "circulation_window": "<inferred period>",
          "prior_belief": "<what the first detection had suggested>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these silent-spread findings:
{known}
State ONE additional DISTINCT finding (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "establishment": {
        "first": """State the single most important ESTABLISHMENT OUTCOME this paper
reports for a region+lineage: became established (persistent circulation),
burned out, or recurs seasonally.
Return JSON:
{{"item": {{"region": "<region/country>",
          "lineage": "<clade/genotype>",
          "outcome": "<established|burned_out|recurring|unclear>",
          "basis": "<surveillance|serology|genomic|other>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these establishment outcomes:
{known}
State ONE additional DISTINCT outcome (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "susceptibility_verdicts": {
        "first": """State the single most important SUSCEPTIBILITY VERDICT this paper gives
for a named host species: did infection REPLICATE in that species
(infection_confirmed — virus isolated/detected, experimental challenge
success, genomic evidence of replication), was there EXPOSURE WITHOUT
demonstrated infection (exposure_only — antibodies/serology, environmental
co-occurrence), or is RESISTANCE/TOLERANCE reported (resistance_suspected —
exposure without infection, poor replication, species stays healthy)?
Return JSON:
{{"item": {{"species": "<scientific or common name as stated>",
          "verdict": "<infection_confirmed|exposure_only|resistance_suspected|unclear>",
          "evidence_kind": "<virus_isolation|experimental_challenge|genomic|serology|field_observation|molecular|other>",
          "clade": "<clade/genotype if stated, else empty>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if the paper states nothing species-specific.""",
        "next": """We already have these verdicts:
{known}
State ONE additional DISTINCT species verdict (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "vaccination_campaigns": {
        "first": """State the single most important VACCINATION CAMPAIGN this paper documents,
references, or reviews: a real deployment — national/regional program,
emergency ring vaccination, or a wild-species campaign — NOT a laboratory
trial. Historical campaigns mentioned as context or in review COUNT.
Capture period, targets, and the reported real-world effect.
Judge sector: poultry_routine (routine/preventive), emergency_ring
(outbreak response), wildlife (free-ranging), zoo_captive.
Return JSON:
{{"item": {{"name": "<campaign/program name as stated, or 'unnamed'>",
          "region": "<country/region as stated>",
          "period": "<e.g. '2005-2008', 'since 2017', '2020-2021'>",
          "sector": "<poultry_routine|emergency_ring|wildlife|zoo_captive|other>",
          "vaccine_type": "<inactivated|LAIV|vectored|mRNA|DNA|recombinant|unspecified>",
          "diva": "<true|false|unspecified>",
          "coverage": "<as stated, e.g. '>90%', 'targeted ring'>",
          "effect": "<as stated: outbreak reduction, elimination, escape event, trade impact, surveillance interference, species protection>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if the paper documents no campaign.""",
        "next": """We already have these campaigns:
{known}
State ONE additional DISTINCT campaign (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "surveillance_coverage": {
        "first": """State the single most important SURVEILLANCE-COVERAGE statement this
paper makes: what is sampled where (mortality-based, active, serology,
environmental/wastewater, sentinel species), and any stated GAP that makes
detection lag or miss circulation.
Return JSON:
{{"item": {{"region": "<region/country>",
          "modality": "<mortality|active|serology|environmental|wastewater|sentinel|other>",
          "coverage_statement": "<what is covered>",
          "gap": "<stated gap or null>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these coverage statements:
{known}
State ONE additional DISTINCT statement (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "intervention_response": {
        "first": """State the single most important INTERVENTION + OUTCOME this paper
reports for an H5N1 outbreak response: vaccination (wild or domestic),
culling/depopulation, carcass removal, biosecurity upgrades, movement
bans, colony closure — and whether it WORKED.
Return JSON:
{{"item": {{"intervention": "<vaccination|culling|depopulation|carcass_removal|biosecurity|movement_ban|colony_closure|other>",
          "target_species": "<species>",
          "setting": "<wild|farm|zoo|captive>",
          "outcome": "<worked|partial|failed|unclear>",
          "metric": "<outcome metric as stated>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these interventions:
{known}
State ONE additional DISTINCT intervention (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "impact_recovery": {
        "first": """State the single most important POPULATION-IMPACT or RECOVERY finding
this paper reports for a wild population hit by H5N1: fraction of
colony/population lost, breeding disruption, subsequent recovery or lack
thereof.
Return JSON:
{{"item": {{"species": "<species>",
          "location": "<site/region>",
          "loss": "<% population/colony or count>",
          "recovery": "<recovery statement or null>",
          "timeframe": "<as stated>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these impact/recovery findings:
{known}
State ONE additional DISTINCT finding (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
    "contact_structure": {
        "first": """State the single most spread-relevant CONTACT-STRUCTURE finding this
paper reports: gregariousness, colony/staging aggregation sizes, mixed-
species assemblages, or wildlife–livestock contact that drives
transmission opportunity.
Return JSON:
{{"item": {{"species": "<species or group>",
          "context": "<colony|staging|wintering|mixed_flock|livestock_contact|other>",
          "group_size": "<as stated or null>",
          "mixing": "<which species/hosts mix>",
          {_QUOTE_}}}}
— or exactly {{"item": false}} if none.""",
        "next": """We already have these contact-structure findings:
{known}
State ONE additional DISTINCT finding (same JSON shape).
— or {{"item": false}} if there are no more.""",
    },
}

HEADER = """Paper: {title}
Scope: {scope}   Year: {year}

Excerpt (markdown, may include HTML artifacts):
---
{text}
---

Extract ONLY what this paper explicitly states. Every quote must be VERBATIM
from the excerpt above. Reply ONLY with the JSON object, no prose."""


# ---------------------------------------------------------------- grounding

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = re.sub(r"<[^>]+>", " ", s)          # strip HTML tags (<sup>, <i>, …)
    for a, b in (("‐", "-"), ("‑", "-"), ("–", "-"), ("—", "-"),
                 ("“", '"'), ("”", '"'), ("’", "'")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).lower().strip()


def quote_in_text(text: str, quote: str) -> bool:
    q = _norm(quote)
    if len(q) < 25:
        return False
    hay = _norm(text)
    if q in hay:
        return True
    # partial containment: a 60-char window from the middle (models drop
    # markup/linebreaks when quoting)
    probe = q[10:70]
    return len(probe) >= 40 and probe in hay


# ---------------------------------------------------------------- extraction

async def extract_section(client, sem, pid: str, text: str, header: str,
                           section: str) -> list[dict]:
    spec = SECTIONS[section]
    items: list[dict] = []

    def mk_prompt(task: str) -> str:
        # prompts are written template-style ({{…}} escapes) but we substitute
        # by .replace — normalize the doubled braces back to single
        task = (task.replace("{_QUOTE_}", _q())
                    .replace("{{", "{").replace("}}", "}"))
        return header + "\n\nTASK — " + task

    prompt = mk_prompt(spec["first"])
    for round_i in range(MAX_ROUNDS):
        try:
            out = await call_llm(client, prompt, 0.1, BASE, MODEL)
        except Exception as e:
            print(f"    {pid}/{section} round {round_i}: LLM error {str(e)[:80]}",
                  file=sys.stderr)
            break
        parsed = parse_json_response(out)
        if not isinstance(parsed, dict) or "error" in parsed:
            break
        item = parsed.get("item")
        if item is False or item is None:
            break
        if not isinstance(item, dict):
            break
        quote = str(item.get("quote") or "")
        item["quote"] = quote[:300]
        item["quote_in_text"] = quote_in_text(text, quote)
        items.append(item)
        if spec["next"] is None:
            break  # single-shot section
        known = "\n".join(
            f"- {json.dumps({k: v for k, v in it.items()
                             if k not in ('quote', 'quote_in_text')},
                            ensure_ascii=False)[:220]}"
            for it in items)
        prompt = mk_prompt(spec["next"].replace("{known}", known))
    return items


async def extract_paper(client, sem, paper: dict, mds: dict,
                        sections: list[str]) -> dict | None:
    pid = paper["id"]
    md = mds.get(pid)
    if not md:
        return None
    text = md[:MAX_CHARS]
    header = HEADER.format(
        title=(paper.get("title") or "")[:200],
        scope=paper.get("scope") or "?",
        year=paper.get("year") or "?",
        text=text,
    )
    out = {"paper_id": pid,
           "extracted_at": datetime.now(timezone.utc).isoformat(),
           "sections": {}}
    for section in sections:
        async with sem:
            out["sections"][section] = await extract_section(
                client, sem, pid, text, header, section)
    return out


async def run(papers, mds, sections, workers, limit, ids):
    if ids:
        papers = [p for p in papers if p["id"] in ids]
    done = {p.stem for p in OUT_DIR.glob("*.json")}
    queue = [p for p in papers if p["id"] in mds and p["id"] not in done]
    if limit:
        queue = queue[:limit]
    print(f"{len(queue)} papers to extract ({len(done)} already done), "
          f"sections: {', '.join(sections)}", file=sys.stderr)
    if not queue:
        return

    sem = asyncio.Semaphore(workers)
    stats = Counter()
    async with httpx.AsyncClient() as client:
        async def work(p):
            try:
                rec = await extract_paper(client, sem, p, mds, sections)
            except Exception as e:
                print(f"  {p['id']}: FAILED {str(e)[:100]}", file=sys.stderr)
                return
            if rec is None:
                return
            (OUT_DIR / f"{p['id']}.json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=1))
            n_items = sum(len(v) for v in rec["sections"].values())
            n_grounded = sum(1 for v in rec["sections"].values() for it in v
                             if it.get("quote_in_text"))
            stats["papers"] += 1
            stats["items"] += n_items
            stats["grounded"] += n_grounded
            print(f"  {p['id']}: {n_items} items "
                  f"({n_grounded} grounded) → spread_v2/{p['id']}.json",
                  file=sys.stderr)

        tasks = [asyncio.create_task(work(p)) for p in queue]
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            await t
            if i % 25 == 0:
                print(f"  [{i}/{len(queue)}] items={stats['items']} "
                      f"grounded={stats['grounded']}", file=sys.stderr)

    print(f"\ndone: {stats['papers']} papers, {stats['items']} items, "
          f"{stats['grounded']} quote-grounded "
          f"({(stats['grounded'] / max(stats['items'], 1) * 100):.0f}%)",
          file=sys.stderr)


def aggregate() -> None:
    import polars as pl
    rows = []
    for f in sorted(OUT_DIR.glob("*.json")):
        rec = json.loads(f.read_text())
        for section, items in rec["sections"].items():
            for idx, item in enumerate(items):
                rows.append({
                    "paper_id": rec["paper_id"],
                    "section": section,
                    "idx": idx,
                    "payload": json.dumps(
                        {k: v for k, v in item.items()
                         if k not in ("quote", "quote_in_text")},
                        ensure_ascii=False),
                    "quote": item.get("quote", ""),
                    "quote_in_text": bool(item.get("quote_in_text")),
                    "extracted_at": rec["extracted_at"],
                })
    df = pl.DataFrame(rows, schema={
        "paper_id": pl.String, "section": pl.String, "idx": pl.Int64,
        "payload": pl.String, "quote": pl.String,
        "quote_in_text": pl.Boolean, "extracted_at": pl.String,
    })
    # join the verification ledger (llm_verify_spread) when present so
    # downstream consumers can prefer/filter on adjudicated faithfulness
    ledger = ROOT / "data" / "papers" / "spread_verify.jsonl"
    if ledger.exists():
        vrows = []
        for line in ledger.read_text().splitlines():
            try:
                d = json.loads(line)
                vrows.append((d["paper_id"], d["section"], d["idx"],
                              d["verdict"]))
            except Exception:
                continue
        if vrows:
            vdf = pl.DataFrame(vrows, schema={
                "paper_id": pl.String, "section": pl.String,
                "idx": pl.Int64, "verify": pl.String}, orient="row")
            df = df.join(vdf, on=["paper_id", "section", "idx"], how="left")
    df.write_parquet(PARQUET)
    per_section = df.group_by("section").agg(
        pl.len().alias("rows"),
        pl.col("quote_in_text").sum().alias("grounded"),
        pl.col("paper_id").n_unique().alias("papers"),
    ).sort("rows", descending=True)
    print(per_section)
    print(f"\n→ {PARQUET} ({df.height} rows)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None,
                    help="comma-separated paper ids (overrides scope order)")
    ap.add_argument("--sections", default=",".join(SECTIONS),
                    help="comma-separated subset of sections")
    ap.add_argument("--aggregate", action="store_true",
                    help="only rebuild paper_spread.parquet from spread_v2/")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.aggregate:
        aggregate()
        return 0

    sections = [s for s in args.sections.split(",") if s in SECTIONS]
    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    mds = {p.stem: p.read_text(errors="ignore")
           for p in MD_DIR.glob("*.md")}

    def prio(p):
        sc = p.get("scope") or ""
        return (SCOPE_PRIORITY.index(sc) if sc in SCOPE_PRIORITY
                else len(SCOPE_PRIORITY))
    papers.sort(key=prio)

    ids = set(args.ids.split(",")) if args.ids else None
    asyncio.run(run(papers, mds, sections, args.workers, args.limit, ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
