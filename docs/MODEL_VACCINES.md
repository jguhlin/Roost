# The Vaccine Model — Design & Protocol

**Version 0.1 · 2026-09-15 · status: skeleton live, keyword-tier evidence, LLM mining queued**

## Why a third model pillar (not a stage in the gene model)

| Model | Question | Unit of evidence |
|---|---|---|
| Infection (`avian_h5n1_model.json`) | What happens inside the bird? | gene × species |
| Spread (`h5n1_spread_model.json`) | How does it move between birds? | species × route × time |
| **Vaccine** (`h5n1_vaccine_model.json`) | **How do we intervene?** | **vaccine × species × experiment** |

Vaccination is an intervention layer, not a host-response stage: its literature
is organized around platforms, challenge trials and protection metrics, not
around genes. Forcing it in as a "Stage 7" would bury 467+ candidate papers.
Instead the vaccine page is its own model with **gene bridge links** both ways
(stage cards link to gene pages; the adjuvant/response stages carry the sensor
and MHC genes). 570 of ~1,200 corpus papers mention vaccination.

## The nine stages

platforms → antigen → delivery → adjuvant → response → protection → diva → deployment → escape

Full definitions live in `scripts/model/build_vaccine_model.py` (`STAGES`),
rendered by `web/src/routes/Vaccines.svelte` (`#/vaccines`).

## Evidence tiers (the three-pass mining protocol)

1. **🟡 keyword (now, deterministic)** — `build_vaccine_model.py` scans the
   whole markdown corpus per stage keyword list on every run. New papers are
   picked up automatically; no LLM needed.
2. **🟢 verified (when the literature LLM returns)** — `mine_vaccines.py`,
   cheap→expensive in three passes:
   - **TRIAGE** (`--triage`): one cheap call per paper — primary /
     vaccine-relevant / mention-only / not-vaccine. Mention-only papers are
     skipped before expensive extraction; primaries mine first.
   - **PROPOSER**: structured extraction, one record per vaccine × species ×
     experiment. Hard rules: never compute or convert numbers ("8/10" stays
     "8/10"), vaccinated and control arms never merge, every number carries
     a verbatim quote, units stay as printed, nulls and no-protection results
     are extracted too. Enums: platform (12 values), delivery_route,
     transmission_assessed, diva_compatible, gene context.
   - **SKEPTIC**: audits each record against its own quotes with verdict
     modes — **ok** (→ 🟢), **unverified** (plausible but not quote-anchored
     → human review), **contradicted** (quote/logic disproves — dropped).
     Catches arm-swapped numbers, unit mismatches, impossible ranges.
   Output `data/papers/vaccine_claims.jsonl`; the next
   `build_vaccine_model.py` run rebadges stages keyword → verified.

### Rescan semantics (papers keep arriving)

- The queue is rebuilt from the fresh corpus scan on **every** run — newly
  ingested papers enter automatically, ranked by keyword hits.
- `vaccine_claims.jsonl` is the mined-state ledger: papers with verdict ≠
  `error` are done; default mode mines **new papers only**.
- `--all` / `--redo --limit N` re-sweep the backlog (e.g. after a schema
  change); `--papers A,B` targets specific papers; `--dry` always safe.

```
# when the LLM is back:
pixi run python scripts/model/mine_vaccines.py --triage --dry    # plan
pixi run python scripts/model/mine_vaccines.py --triage         # classify
pixi run python scripts/model/mine_vaccines.py --tier primary   # mine first
pixi run python scripts/model/mine_vaccines.py                  # rest
pixi run python scripts/model/build_vaccine_model.py            # rebadge + ship
```

## The gene × vaccine bridge

BF2 (B21 haplotype: survival AND vaccine response), BLB2/CD74 (MHC-II antigen
processing), RAG1/AICDA (receptor diversity, affinity maturation), TLR21
(avian CpG sensor — the adjuvant target), TLR3/DDX58 (RNA-mimic adjuvants,
duck-vs-chicken asymmetry), IFNB1/IRF8 (innate bridge, APC fitness).
Rendered on the vaccine page; each links to its gene page.

## Gap registry (V1–V6)

V1 NZ taonga-species program design (true gap — our genomes to inform),
V2 transmission-block efficacy of commercial vaccines, V3 avian immune
imprinting, V4 MHC × response beyond chicken, V5 mRNA economics at poultry
scale, V6 oral-bait wildlife delivery (true gap).

## LLM cross-cutting questions (mining targets)

Lives in the model JSON (`llm_plan.cross_cutting_questions`) and renders on
the page — 10 questions from transmission-block-by-platform through the
kākāpō-program stack to vaccine-driven antigenic drift.

## Source plan for species-specific vaccine response (D72)

What feeds the readiness scores, and what to grab next:

| Source | Status | What it upgrades |
|---|---|---|
| Presence matrix (BLAST pipeline, 208 spp) | ✅ live | module completeness (current tier) |
| ImmunomeDB (363 B10K spp, 520 immune genes, local) | ✅ joined (D73): backbone column + 317 backbone-only species | cross-validation of calls; immune-backbone score for +317 species. Caveat: no B-locus genes (no BF/BLB/TAP/B2M) — cannot score MHC modules directly |
| B10K/NCBI assemblies via existing blast_presence.py | compute, not source | the real species-breadth lever for MHC modules (run module genes on new assemblies) |
| IPD-MHC (EBI) | verified: birds = Gallus only | chicken B-locus allele reference (B21/B13…), haplotype-level modeling; no multi-species bird coverage (BirdBase retired) |
| Kākāpō MHC-II β study (Immunogenetics 2013) | queued for intake | actual BLB-locus/allele data for the planner flagship |
| Layer-chicken antibody-response genetics (2024), divergent E. coli vaccine-Ab lines (2019) | queued | gene×response priors — the calibration layer's chicken anchor |
| Duck-vs-chicken reviews (Viruses 2019, mallard PRR 2020, tufted ducks 2023, mucosal 2012) | queued | cross-species transferability calibration (tier: genome-presence → literature-calibrated) |
