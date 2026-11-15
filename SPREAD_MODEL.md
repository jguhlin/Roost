# Spread Model — Design & Roadmap

> The spread model explains **how H5N1 moves** — through wild birds, poultry,
> environments, and into mammals. This document plans its evolution from a
> curated static diagram into the site's data-joined epidemic view.

**Created:** 2026-09-11, after shipping `#/spread-cyto` (beta, v0.4).
**Status:** Phases 0–5 ✅ (2026-09-11) · Phases 6–8 planned (2026-10-08) — the layered model.
Companion docs: `DATA_MANIFEST.md` (sources).

---

## Audience & job

- **Researchers**: "what does the literature support, and where does it
  disagree?" — a synthesis claim-graph with traceable evidence.
- **Conservationists / wildlife managers**: "how did the wave move, where is
  it going, what's at risk?" — data-driven geography and risk.
- **The curious public**: an honest, navigable story of the panzootic.

**The moat is the join.** Textbook spread diagrams exist; what no one else
has is a spread model wired into 39,793 dated detections, host genomics,
susceptibility phenotypes, a mutations database, and a verified paper
corpus. Every feature below exists to strengthen that join.

## Baseline (v0.4, shipped)

- `#/spread-cyto` (beta): 9 stage buckets → 44 element nodes → 10 stage-level
  edges (ELK layered layout); 6 species nodes deep-link to species profiles;
  `?node=` selection; diverges + additions panels.
- `#/model` spread tab: narrative render of the same JSON.
- Model data: `data/model/h5n1_spread_model.json` (interior + shipped, one
  writer — the LLM verification rounds), enriched v0.4 (short/accent/kind +
  connection labels).
- Evidence base: `data/model/spread_evidence.jsonl` — 413 papers with
  per-paper extraction (`spread_mechanisms`, `species_roles`, `flyways`,
  `key_finding`, `_pid`).

## Design principles

1. **Data-driven, never simulated.** Animation may only replay what the
   detection data records. No parameter-free "outbreak simulation" buttons —
   that implies precision the science doesn't have.
2. **Disagreements are first-class.** The wild-bird-vs-trade spread debate is
   *the* live controversy; contested routes get distinct visual treatment,
   never averaging away.
3. **Every node and edge carries provenance.** Counts cite the detections
   table; claims cite papers; contested claims cite both sides.
4. **One writer per artifact** (the maturation doctrine). New derived views
   compute client-side from shipped parquet wherever possible; curated
   mappings live in `data/manual/`.
5. **The DAG stays readable.** Stage-level arrows with expandable evidence;
   per-species-pair edges would spaghetti it.
6. **The provenance ladder — every displayed quantity is exactly one of:**
   - **MEASURED** — a query over shipped data (counts, dates, firsts).
   - **CURATED** — a human/LLM-verified claim from the overlay, citing papers.
   - **MODELED** — a derived proxy (e.g. edge weight = corpus paper count),
     with its derivation visible and caveated.

   There is no fourth kind. Where we must "make do," we curate with a
   citation; where we can "model it," we derive with the formula on show.
   Nothing on the page is silently invented.

---

## Phase 0.5 — Date normalization ✅ (2026-09-11)

`detections.date_detected` ships in two formats: ISO (28,557 records) and
US `M/D/YYYY` (11,235 records) — and the split is perfectly by source:
**only `aphis_us` uses slash format** (a US agency; unambiguous M/D),
everyone else ISO. Mixed formats break any timeline query (a year-slice
produces `1/10` as a "year").

**The work**
- Export side (`export_web_data.py`, detections copy step): add a derived
  `date_iso` column — parse ISO as-is, `aphis_us` as M/D/YYYY; keep the raw
  column untouched. Same normalization applied to the interior
  `detections_merged.parquet` in `ingest_detections.py` so both stay in sync.
- Integrity gate: every dated record parses; `MIN(date_iso)`/`MAX(date_iso)`
  sanity (expect 2004-01 → present).
- Downstream consumers (scrubber, first-detection stamps, Map popups,
  species first/last detection) switch to `date_iso`.

**Acceptance — met.** Shipped 2026-09-11:
- Four formats found & handled: ISO (28,557), US M/D/YYYY (11,235, aphis_us),
  ISO week `\d{4}-W\d\d-\d` (uk_defra/gisaid), and year-ranges
  (`1973-2023`, gisaid literature records — legitimately null: a range is
  not a point date; 453 records total stay null, 98.9% coverage).
- Histogram over `date_iso`: sparse 2004–2019 (8–353/yr), 2016-17 blip,
  panzootic 2021+ (2.8k → 8.7k → 9.3k) — exactly the adaptive-resolution
  split Phase 1 assumed. Range: 2004-01-10 → 2026-09-02.
- Interior `detections_merged.parquet` normalization: deferred to the next
  ingest pass (ingest_detections.py should derive the same column at source;
  the shipped table is canonical for the web until then).
- Gates: pytest 81/81, integrity ✓, e2e 39/39.

## Phase 1 — Time: the wave, replayed ✅ (2026-09-11)

The single highest-value upgrade: a **date scrubber** on `#/spread-cyto`
that animates the panzootic through your own detection records.

**What it shows**
- A time axis with a draggable playhead + play/pause. **Adaptive
  resolution** (resolved open question 3): yearly ticks pre-2021 (the sparse
  EMPRES-era: ~1.8k records across 17 years), monthly 2021+ (the panzootic
  era: dense APHIS/SDM/WAHIS/DEFRA streams). The build asserts the density
  split after Phase 0.5 normalization.
- Two kinds of event stamps, visually distinct (resolved open question 1):
  - **MEASURED stamps** — first detection per country (156 derivable today:
  VNM 2004-01, the 2005-06 westward wave through ROU/HRV/TUR/UKR, …),
  derived at runtime via DuckDB from `date_iso`.
  - **CURATED stamps** — narrative events the data can't show (colony
  crashes, first mammal clusters, policy events) from
  `data/manual/spread_events.json`, each citing paper ids that must resolve
  in `papers.json` (integrity-gated).
- Stage/bucket nodes light up when the playhead enters periods where their
  elements have detections ("Amplification: seabird colony crashes 2021-23").
- Element nodes badge with first-detection dates and running counts for the
  selected window.

**Data (all derivable, nothing new shipped)**
- `detections.parquet` → DuckDB over `date_iso`: `GROUP BY country, period`
  and per-species first/last detection — computed client-side, cached.
- 724 species already carry derivable first-detection dates (stage
  activation); 156 countries (arrival stamps).

**Acceptance — met.** Shipped 2026-09-11 on `#/spread-cyto`:
- Adaptive periods (yearly pre-2021, monthly after) built at runtime from
  `date_iso` (DuckDB); sparkline density behind the slider; play/pause.
- MEASURED fading: species nodes fade until their first *dated* detection
  (verified: all 6 linked species fade at t=2005 — their dated records
  start 2006 — and none fade at Oct 2023). Bucket labels carry cumulative
  detection counts.
- CURATED flags: 8 events from `data/manual/spread_events.json` (exported
  by the new `export_curated_overlays` step), stacked when co-dated, each
  opening a panel with paper chips that resolve in papers.json.
- `?t=` deep-linkable + SPA-reactive, debounced writes.
- DuckDB date gotcha recorded: DATE columns arrive as millisecond numbers.
- Gates: pytest 81/81, integrity ✓, e2e 40/40.

## Phase 2 — Data-join styling: size, color, chips ✅ (2026-09-11)

Nodes stop being uniform text boxes; they wear the data.

**What it shows**
- Node size ∝ detection count (log scale, capped); host nodes colored by
  **susceptibility class** from `susceptibility.parquet` (already shipped,
  already joined client-side on Species).
- Amplification nodes annotated with mortality % from the phenotype data.
- Per-node chips: detections · countries · genomes available
  (`species.parquet`), e.g. "8,201 · 14 countries · 412 genomes".
- Flyway stage nodes badge with the countries your detections place on them.

**Data** — existing shipped tables only (`species`, `susceptibility`,
`genomes` parquet; `species_index.json` for lookups). No new artifacts.

**Acceptance — met.** Shipped 2026-09-11:
- All 6 species nodes sized by log₁₀ detections (mallard caps at 96px with
  2.2M; wigeon 67px at 668), bordered by susceptibility class on the
  5-color scale, carrying chips ("2.2M · 55 countries · 31 genomes",
  gannet: "…100% mortality"). Numbers come from the same species×
  susceptibility join the Species page uses — asserted in e2e.
- The graph now shows the ecological story at a glance: the reservoir
  (mallard) is green-tolerant-huge; the amplifier (gannet) is
  red-susceptible with 100% mortality.
- Legend row under the graph; selected-node panel repeats chip + class.

## Phase 3 — Evidence layer: weighted, cited, contested ✅ (2026-09-11)

Edges become claims with provenance — the synthesis core.

**What it shows**
- **Edge weight/label = corpus evidence**: paper counts per connection from
  `spread_evidence.jsonl` (`spread_mechanisms` → stage-edge mapping).
- **Citation chips** on tap: the supporting papers, each linking to
  `#/papers/{id}` (the pattern genes/mutations already use).
- **Contested styling**: connections named in `diverges` (and edges whose
  mechanisms split, e.g. migration-32 vs trade-6 papers) render with a
  hatched/amber style + both-sides citations.
- A small legend: solid = established · amber = contested · dashed = inferred.

**Data** (resolved open question 2)
- `scripts/model/build_spread_edges.py` derives per-edge paper IDs + counts
  from `spread_evidence.jsonl` (413 papers, `spread_mechanisms` mapped to
  stage edges) and writes them as an `evidence` block INSIDE the model JSON.
  Block ownership: the LLM verification rounds own narrative fields; the
  build script owns the `evidence` block exclusively. Run order after every
  round: **LLM round → build_spread_edges.py → export**. Integrity gate:
  every cited `_pid` resolves in `papers.json`.

**Acceptance — met.** Shipped 2026-09-11:
- `scripts/model/build_spread_edges.py` derives the evidence block (42
  edge-paper links over 9 edges; run order: LLM round → build → export).
  Mechanism→edge mapping is conservative and documented in the script.
- Results: timing→routes 16 papers; reservoir/routes→amplification 10 each
  (wild_bird_migration) — **both flagged contested** via the flyway-limits
  diverge; bridge→anthropogenic 3 papers contested; 3 edges inferred
  (0 corpus extraction — the W5 weakness, now visible in the graph itself).
- Page: edge width ∝ paper count; contested = amber dashed; inferred =
  grey dashed thin; tap → panel with mechanism split + paper chips linking
  `#/papers/{id}`; legend updated.
- Integrity gate added: every cited `_pid` resolves in papers.json; edges
  without evidence reported as informational.

## Phase 4 — The mechanistic join: mutations on the spillover path ✅ (2026-09-11)

**What it shows**
- The amplification→spillover and anthropogenic→spillover edges carry
  **adaptation-marker chips** from `wiki_mutations.json` (PB2-E627K, HA
  changes, polymerase adaptations) — each opening `#/mutations/{id}`.
- Host nodes near spillover offer "does it have RIG-I?" → the gene panel
  (`?tab=genes` deep link, already URL-addressable).

**Data** — existing `wiki_mutations.json` + `gene_catalogue.json`; a curated
mapping `edge → mutation ids` in the model JSON (LLM round or manual).

**Acceptance — met.** Shipped 2026-09-11:
- `data/manual/spread_mutations.json` (CURATED): 7 mutation links across
  two spillover edges — wild-bird→mammal (PB2-E627K ·92 papers, PB2-D701N,
  PB2-T271A, PB2-M631L) and poultry/cattle→mammal (PB2-E627K, HA-G228S,
  HA-N224K). Every id resolves in wiki_mutations.json.
- Tap a spillover edge → purple mutation chips, each linking to
  `#/mutations/{id}`. The 🧬 hint on edge labels flags which edges carry
  markers.
- Host nodes offer "🧬 Gene panel →" deep links (`?tab=genes`) — the
  RIG-I/MDA5 question is one click from every species in the graph.
- New `anthropogenic→spillover` connection added to the model (the cattle
  outbreak pathway — real, backed by PB2-D701N in the D1.1 cluster).
- Gates: pytest 81/81, integrity ✓ (incl. evidence block), e2e 43/43.

## Phase 5 — Regional risk views: NZ as the template ✅ (2026-09-11)

**What it shows**
- The `nz_risk` stage becomes a **risk panel template**: for a chosen
  region — flyway exposure (detections on its flyway), months-to-first-case
  inference, at-risk endemic species (from the species overlay:
  conservation status, population estimates, vaccination targets), and
  preparedness links.
- Region picker (`?region=nz|au|sa`); content driven by the same joins.

**Data** — species overlay + detections by country + a curated
`data/manual/flyways.json` (flyway → country codes; also serves Phase 1's
map lane idea).

**Acceptance — met.** Shipped 2026-09-11:
- `?region=nz|au|sa` selects a risk panel on `#/spread-cyto`. Three regions
  live: NZ (arrived, Jul 2026), AU (arrived, Aug 2026), SA (established,
  Oct 2023).
- MEASURED: first detection, detection count, species count from
  `date_iso` via DuckDB. Flyway exposure from curated
  `data/manual/flyways.json` (6 flyways → ISO3 lists; W7 resolved).
- CURATED: `data/manual/spread_regions.json` — narrative, risk summary,
  flyway note per region. At-risk species render from the overlay (kākāpō
  with CR status, ~250 pop, vaccination-target badge).
- Adding a region = one entry in `spread_regions.json` + flyway ISO3
  mapping if new. No code changes.
- URL-addressable + SPA-reactive (`?region=` param).
- Gates: pytest 81/81, integrity ✓, e2e 44/44.

---

## Diagnosis: why v0.4 plateaus (2026-10-08)

An audit before Phase 6 found the evidence layer is thinner than the graph implies:

- **Stale + one-shot.** `spread_evidence.jsonl` (D57) was generated once
  (2026-09-02) and is wired into NO recurring pipeline — every paper added
  since (263+ and counting) has never been spread-extracted.
- **Thin fields.** Of 987 attempted: 174 relevant, 65 hard parse errors;
  **5 `species_roles` entries total** across all papers; seasonality
  "not_stated" in 142/174; the prompt only saw the first 4,000 chars.
- **A 7-entry mechanism→edge dictionary** (`MECHANISM_EDGES`) is the entire
  inferential machinery between corpus and graph; 4 of 11 edges carry zero
  evidence (incl. both spillover edges).
- **The good machinery doesn't feed it.** `model_verdicts.jsonl` (1,015
  papers, per-stage verdicts with quotes), `paper_species_traits.parquet`
  (778 quote-verified host-phenotype rows), `paper_quantitative.parquet`
  (7,691 numbers) and `typed_claims.parquet` (10,748 place/stance-tagged
  claims) all exist — none touch the spread model.
- **No time axis, no lineage axis.** One static graph represents 20+ years,
  five viral waves and dozens of lineages as a single picture. 2005 Qinghai
  (2.2), 2016-17 (2.3.4.4a), 2021 panzootic (2.3.4.4b), 2024 cattle (D1.1),
  2023 Peru sea lions (B3.2) are different actors on different routes.

## Phase 6 — Evidence re-extraction: the layered corpus side

**Status:** PLANNED (2026-10-08). Replaces the D57 one-shot with a
resume-safe, quote-grounded, iterative extraction wired into the recurring
pipeline — same protocol family as `llm_iterative_extract.py` /
`llm_extract_phenotypes.py`.

**What it produces** — `data/papers/paper_spread.parquet` (built via
`scripts/papers/llm_extract_spread.py --aggregate` from per-paper JSONs in
`data/papers/spread_v2/`; the extractor itself is `llm_extract_spread.py`,
standing stage in `enrich_pipeline.py`), one row per
extracted item, sections:

| section | shape | feeds |
|---|---|---|
| `introduction_events` | `{lineage, date_window, source_region, dest_region, route, basis, direction: wild_to_domestic\|domestic_to_wild\|wild_to_wild\|unknown, location_detail, quote}` | Layer B (events), validation join |
| `host_roles` | `{species, roles[], params: {mortality_pct, shedding_days, peak_titer, seroprevalence_pct, n}, clade, quote}` | Layer C (competence matrix) |
| `transmission_params` | `{parameter: R0\|Rt\|efficiency\|odds_ratio\|diffusion_rate\|…, value, unit, context, quote}` | Layer D (parameterized edges) |
| `persistence` | `{matrix: water\|fomite\|feed\|surface, temperature_c, salinity, duration_days, quote}` | Layer D (environmental edge) |
| `mass_events` | `{kind: colony\|farm\|market\|wildlife, location, date, count_dead, duration_days, trajectory: pulse\|sustained\|escalating, pct_population, species, quote}` | era stamps, amplification nodes; kill curves for response planning |
| `seasonality` | `{statement, pattern, era, quote}` (single-shot) | timing content per era; cross-checked against measured curves |
| `reassortment_events` | `{genotype_or_name, segments, donor_lineages, host_context, date_window, quote}` | virus layer; 2014 NA incursion, genotype letters |
| `adaptation_mutations` | `{mutation, gene, phenotype: receptor_binding\|polymerase_adaptation\|virulence\|transmissibility\|…, host_context, clade, quote}` | virus layer; joins mutations data |
| `migration_links` | `{species, flyway_or_route, timing, link_claim, quote}` | routes; flyway attribution as its own claim |
| `trade_movements` | `{kind: live_bird_market\|poultry_trade\|game_birds\|fighting_cocks\|…, route, volume, evidence_link, quote}` | routes; ~150 LBM papers, near-invisible today |
| `anthropogenic_mechanics` | `{mechanism: manure_spreading\|shared_equipment\|vehicles\|personnel\|feed\|rendering, setting, evidence_link, quote}` | routes; farm-to-farm mechanics (cattle story) |
| `risk_factors` | `{factor: farm_density\|water_proximity\|biosecurity_level\|…, measure OR/HR, outcome, setting, quote}` | explanatory associations, distinct from transmission quantities |
| `mammal_chains` | `{species, setting, evidence_kind: genomic\|epidemiological\|…, scale, date, quote}` | THE 2022-26 story: mink, sea lions, elephant seals, cattle |
| `silent_spread` | `{evidence: retrospective_serosurvey\|backdated_genomic\|wastewater\|…, region, circulation_window, prior_belief, quote}` | parameterizes detection lag for the validation join |
| `establishment` | `{region, lineage, outcome: established\|burned_out\|recurring\|unclear, basis, quote}` | Layer A chapter outcomes |
| `surveillance_coverage` | `{region, modality: mortality\|active\|serology\|environmental\|sentinel\|…, coverage_statement, gap, quote}` | interpreting the join; sentinels + early warning |
| `intervention_response` | `{intervention: vaccination\|culling\|carcass_removal\|biosecurity\|…, target_species, setting, outcome: worked\|partial\|failed, metric, quote}` | conservation gold: has anything like this worked |
| `impact_recovery` | `{species, location, loss, recovery, timeframe, quote}` | population consequences; what a bad year costs |
| `contact_structure` | `{species, context: colony\|staging\|mixed_flock\|livestock_contact, group_size, mixing, quote}` | turns competence into superspreading |

**[DET] companions** (deterministic, no LLM):
- `build_spread_features.py` → `spread_features.json`: measured seasonality
curves per era×region (panzootic peak Oct-Dec), persistence pairs (1,296
recurring ≥2y), diffusion chronology + early-wave slope (panzootic
30.6 km/day), mass events ≥100 dead (1,461 poultry / 463 wildlife),
mammal share by year (2-4%), species accumulation, sampling mix.
- `build_host_competence.py` extensions: per-clade mortality stratification
(55 species; Gallus 2.3.4.4b = 11.8% vs 0% unstratified), coverage-gap
matrix (759 species × 8 evidence types), taxonomic proxy rollup for 59
thin species (genus→family→order, marked proxy).

**Phase 8 goal artifact — species risk card**: for species X in region Y →
proxy susceptibility (rollup) + exposure timing (migration links ×
measured seasonality) + local sentinels/when + analogous events with kill
curves + interventions that worked. The conservationist's one page.

**Protocol** (all sections):
- Full markdown input (1,149/1,366 papers have it), not a 4,000-char excerpt.
- Iterative rounds per section: strongest item → "we have these" → next →
  FALSE. Quote required for every item; ungrounded quotes demoted
  (whitespace/HTML-tag-normalized substring check, as in traits extraction).
- Robust JSON parsing via the shared `parse_json_response` helper
  (reasoning-mode safe) — no hand-rolled regex over nested objects.
- Resume via done-file per (paper, section); partial paper = retry whole
  paper. Scope: `avian-epi` + `epidemiology` first, then `avian`, `mammalian`.
- Lineage/clade strings validated against the `clade_discovery.py` registry
  vocabulary where present (deterministic Tier-1 assist).

**Pipeline wiring:** becomes a standing stage in `enrich_pipeline.py` and the
new-paper refresh runbook; D57 `extract_spread_data.py` retired to archive
once the v2 evidence base covers its scope. `build_spread_edges.py` also
reads `model_verdicts.jsonl` — as **stage-level evidence**: verdicts speak to
stages, not edges, so they land in an `evidence.stages` block (papers +
agree/add/disagree tallies per stage; 8 stages, 1,807 paper links today) and
edges surface only an `endpoint_stage_support` context count. Early attempt
at mapping verdicts onto edges triple-counted papers and contested 9/10
edges — rejected; edge counts stay extraction-only until v2 edge events exist.

**Acceptance:**
- [ ] `paper_spread.parquet` with all 19 sections; zero ungrounded quotes
      surviving (all rows `quote_in_text` or dropped).
- [ ] `host_roles` coverage ≥ 20× D57 (i.e. ≥ 100 rows, D57 had 5) from
      the epi-scoped corpus; `mammal_chains` ≥ 15 rows (the 2022-26 story);
      `introduction_events` ≥ 60 rows (Layer B viable).
- [ ] `spread_features.json` + `host_competence.json` coverage/proxy
      blocks regenerated post-extraction (clade joins denser).
- [ ] `build_spread_edges.py` reports both layers (edge extraction counts +
      `evidence.stages` verdict block); no previously evidence-carrying edge
      drops to 0.
- [ ] Spread extraction runs on every new paper via `enrich_pipeline.py`.

## Phase 7 — Layered model representation: eras, events, competence, parameters

**Status:** PLANNED. The model JSON grows from one static graph to four
layers, all under the provenance ladder. **Regions are generic** — a region
is an overlay instance like any other; no region-named stages or fields
(equal-treatment policy, 2026-10-08).

**Layer A — Eras & waves ledger (CURATED + MEASURED). BUILT 2026-10-08**
as `scripts/model/build_spread_eras.py` → `data/model/spread_eras.json`
(+ web twin). 7 eras / 7 chapters: Goose-Guangdong emergence → first
panzootic (2.2 westward) → enzootic 2.3.x consolidation → 2014-15 NA
incursion → 2016-17 H5N8 wave → 2.3.2.1c zoonotic wave → 2021- 2.3.4.4b
panzootic (chapters: Atlantic arrival / Americas / Antarctic & subantarctic /
cattle B3.13 / Oceania). Two channels, provenance explicit per field:
window+narrative CURATED; `measured` blocks MEASURED from detections
(first detection stamp per region/country **within the window** — arrival
precedes detection, the ledger never claims otherwise); papers counted from
clade-registry designation links. Chapters for events the surveillance feed
doesn't carry (2015 Midwest poultry, 2024 cattle B3.13) ship `measured: null`
with a note — evidence stays paper-based, never a misleading wild-bird
count. Rerun after detections rebuilds / registry scans. The scrubber gains
era anchors; the "timing" stage's content (seasonality collapse post-2021)
becomes a statement about an era, not a bucket.

**Layer B — Introduction/route events (extraction-derived, MODELED).**

**Edge mapping SHIPPED 2026-10-14** (`build_spread_edges.py` v2 channel):
per-edge corpus evidence now comes from the structured v2 items mapped by
FIELDS, replacing the 189-link legacy topic scan with 2,021+ paper-edge
links (paper counted once per edge; `mapped_from` records feeding
sections; `grounded` = papers with a quote-backed row). Mapping table:

| Edge | Sections/conditions |
|---|---|
| reservoir→amplification | host_roles role∈{reservoir,amplifier}; contact_structure context∈{colony,mixed_flock,staging,wintering} |
| reservoir→bridge | host_roles role=bridge |
| bridge→anthropogenic | contact_structure livestock_contact; mass_events kind=farm; anthropogenic_mechanics (all) |
| amplification→spillover | mammal_chains (all); mass_events kind∈{colony,wildlife,marine_mammal}; introduction_events route=spillover |
| routes→amplification | migration_links (all); introduction_events route=migration |
| timing→routes | seasonality (all — prompt-wrapper bug fixed 2026-10-14, backfilled) |
| regional_risk→routes | establishment + silent_spread (all) |
| environmental→reservoir | persistence (all) |
| anthropogenic→routes | trade_movements (all); introduction_events route=trade |
| anthropogenic→spillover | adaptation_mutations with mammalian host_context (regex) |

Deliberately UNMAPPED (no single-edge semantics; Layer D consumes them):
surveillance_coverage, intervention_response, impact_recovery,
risk_factors, transmission_params, reassortment_events. Verdicts stay in
`evidence.stages` (stage-level); `endpoint_stage_support` remains context
only. `spread_evidence.jsonl` (D57) is fallback-only now.
Aggregated from `paper_spread.introduction_events`: events plotted on
time × region, each linking to its paper(s). **Validation join (the novel
feature):** literature-claimed introduction dates vs MEASURED first-detection
stamps from `detections.parquet` per country — agreement/disagreement is
itself displayed. No other spread diagram can do this.

**Layer C — Host competence matrix. BUILT 2026-10-08 (base) /
roles LLM-pending** as `scripts/model/build_host_competence.py` →
`data/model/host_competence.json` (+ web twin, 167 species): per-species
papers, records by kind (outbreak/experimental/surveillance/serology),
mortality median-range from verified rows, shedding days, clades seen,
evidence quotes, susceptibility join, detections stamp — every block
carrying explicit provenance (PAPER_EXTRACTED / MODELED / MEASURED).
Phase 6 `host_roles` extraction merges LLM-assigned roles into this matrix
(roles are the piece deterministic data cannot supply). Species nodes in
`#/spread-cyto` summarize this table; the table is browsable (a
"vectors & reservoirs" view). Every number cites a paper or a query.

**Layer D — Parameterized mechanistic edges (MODELED where derived).**
Edges carry whatever the corpus quantifies (persistence matrices,
transmission efficiencies, odds ratios for spillover risk factors, R0/Rt
where they exist), each with derivation + caveat on show. Contested edges
keep both-sides citation lists (now fed by `model_verdicts` disagrees).

**Region generalization (ships with this phase):** stage `nz_risk` →
`regional_risk` (generic elements: flyway connectivity, poultry interface,
naive-fauna vulnerability, surveillance posture); region specifics live only
in `data/manual/spread_regions.json` overlay instances (nz/au/sa today, any
region addable). Mermaid + i18n keys follow (`mermaid.regional`,
`model.spread.regional_risk.*`; stale `*.nz_risk.*` keys purged).

**Acceptance:**
- [ ] `eras[]` in the model JSON, each with ≥1 paper citation; scrubber
      renders era anchors on `#/spread-cyto`.
- [ ] Introduction-events panel: events with dates/routes/papers; validation
      join visible for ≥ 20 countries.
- [ ] Host competence table live on the spread view, ≥ 40 species rows with
      ≥ 1 quantitative parameter cited.
- [ ] No `nz_risk`/region-named keys anywhere in model, code, or i18n.
- [ ] Integrity: every cited pid resolves; pytest + e2e green.

## Phase 8 — Reading experience: layered rendering

**Status:** PLANNED (after 6+7 land). Era scrubber anchors + era switcher on
`#/spread-cyto`; edge panels show parameters with units + provenance tags;
host-competence table view; introduction-event timeline lane under the
scrubber with validation ticks. The narrative `/model` tab renders eras as
sections. Nothing here changes artifacts — pure client-side derivation
(maturation doctrine).

---

## Future / exploratory (not committed)

- **Map lanes**: flyway corridors drawn on the Map page (stylized), linked
  from flyway nodes.
- **Tree × spread**: phylogeny leaves tinted by first-detection date
  (arrival order across the tree) — uses the birdtree + detections join.
- **Counterfactual toggles** (vaccination, trade restriction): only if
  grounded in corpus claims, clearly labeled as literature-supported
  projections — never free simulation.

## Anti-goals

- No synthetic outbreak dynamics or SEIR-style animation without parameters.
- No per-species-pair edge soup on the main graph.
- No unattributed numbers anywhere on the page.
- No second data pipeline: everything derives from shipped artifacts +
  `data/manual/` overlays + the existing LLM verification rounds.

## Resolved questions (2026-09-11)

1. **Event stamps** → hybrid, per the provenance ladder: MEASURED stamps
   derived from `date_iso` at runtime + CURATED stamps in
   `data/manual/spread_events.json` citing papers; visually distinct ticks.
2. **Edge-evidence ownership** → `scripts/model/build_spread_edges.py` owns
   an `evidence` block inside the model JSON; LLM rounds own narrative
   fields; explicit run order; integrity-gated citations.
3. **Scrubber resolution** → adaptive: yearly pre-2021 / monthly 2021+,
   asserted at build time after date normalization (Phase 0.5).

## Decisions registry (append-only)

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-11 | Spread model stays a synthesis view, not a simulation | Data-driven replay only; simulated dynamics imply precision the field doesn't have |
| 2026-09-11 | `#/spread-cyto` is beta, parallel to the narrative tab | Iteration without breaking the canonical /model view |
| 2026-09-11 | Timeline data derives client-side (DuckDB) from detections.parquet | Maturation doctrine: no new shipped aggregates |
| 2026-09-11 | `date_iso` derived column at export (Phase 0.5) | date_detected ships mixed ISO + US formats, split perfectly by source (only aphis_us slashes); timelines need one canonical column |
| 2026-09-11 | Hybrid event stamps (measured + curated, distinct) | Data shows arrivals; corpus shows events; conflating them would blur provenance |
| 2026-09-11 | Adaptive scrubber resolution (yearly pre-2021, monthly after) | EMPRES-era is 17 sparse years; the panzootic era is dense — one resolution would either blur or lie |
| 2026-09-11 | Provenance ladder: measured / curated / modeled | "Make do or model it," formalized — every quantity tagged, nothing silently invented |
| 2026-09-11 | W1 county-centroid geocoding chosen as top priority | 11.8k mappable rows exist behind clean county names; derivation is honest (labeled "located to county") and unlocks the map/timeline across the US+UK |
| 2026-10-08 | Spread model goes layered (eras / events / competence / parameters) | One static graph cannot represent 20+ yr × 5 waves × many lineages; time and lineage become first-class axes |
| 2026-10-08 | D57 one-shot extraction retired; v2 is iterative, quote-grounded, resume-safe, pipeline-wired | 174 thin rows, 65 parse errors, 5 species-roles total, 263 unprocessed papers — the corpus side was the bottleneck |
| 2026-10-08 | `model_verdicts.jsonl` becomes stage-level evidence (`evidence.stages`), not an edge channel | 1,015 papers carry per-stage verdicts with quotes; edge-mapping them triple-counts papers and contests everything — stage is what they actually measure |
| 2026-10-08 | Stage `nz_risk` → `regional_risk`; regions are overlay instances only | Equal-treatment policy: no region-named stages/fields; any region enters through `spread_regions.json` |
| 2026-10-08 | Literature-vs-detections validation join displayed (introduction events × first-detection stamps) | Cross-checking corpus claims against 44,862 MEASURED records is the join nobody else has |
| 2026-10-08 | Layer A eras ledger ships CURATED windows + MEASURED in-window first-stamps; feed-absent events (cattle B3.13, 2015 Midwest poultry) carry `measured: null` + note | A wild-bird count is not cattle-outbreak evidence; honesty per-field beats a number |
| 2026-10-08 | Layer C competence base ships deterministic (traits × susceptibility × detections); LLM roles merge in later | Roles are the only piece deterministic data can't supply; competence numbers already exist quote-grounded |
