# AGENTS.md — active agent notes

## Standing directives

### Data-driven site policy (2026-10-05)
- The site must remain **data-driven**: numbers displayed on pages come from
  generated artifacts (`web/public/data/*.json`), never hardcoded into
  components. If a number appears in a `.svelte` file, that's a bug — move it
  into the data build.
- **By-the-numbers page** (`#/numbers`, footer nav): rebuilt via
  `pixi run python scripts/papers/build_by_the_numbers.py`. Run it after any
  pipeline stage that changes a headline artifact (stats, registry, presence,
  papers, authors).
- **Triage rule**: the Numbers page carries deterministic cross-checks
  (artifact-vs-artifact AND page-render merges). If ANY check fails, or any
  page displays a number that disagrees with `by_the_numbers.json`, treat it
  as a triage event: identify the stale side, rebuild it, re-run the checks.
  Never "fix" a disagreement by editing a displayed number.

### LLM server
- Papers-pipeline LLM: **http://localhost:8005/v1** (sglang,
  `muse-glimmer-30b`, 131k ctx, OpenAI-compatible). Scripts default to
  8001 — pass `LLM_BASE_URL=http://localhost:8005/v1` (or `--base-url`).
  Check `curl localhost:8005/v1/models` before LLM passes.

### Per-paper records + steward agent (2026-10-06)
- **Records**: `data/papers/records/{id}.json` — every deterministic output
  per paper (metadata, authors, intake ledger, analysis steps, findings,
  keywords, claims, mechanisms, extras, genes, species). Internal (not
  web-served). Rebuild: `pixi run python scripts/papers/build_paper_records.py`
  after any papers-pipeline stage.
- **Steward**: `scripts/papers/paper_steward.py` — reviews a record and
  proposes/applies updates (stream/tier/metadata/summary, find_related via
  searxng → `PAPER_WISHLIST.md`). Safe actions auto-apply with ledger
  (`steward_ledger.jsonl`); everything else queues to
  `steward_queue.jsonl` for human review. Run:
  `LLM_BASE_URL=http://localhost:8005/v1 pixi run python scripts/papers/paper_steward.py --paper <id>`
  (or `--limit N` for the least-reviewed). Intake design: docs/PAPER_INTAKE.md.

## In-flight background work

### Genome presence expansion — COMPLETE (2026-10-06)
- **2,064 done / 15 retrying** (download failures re-queued, task running).
- Final: 1,579,096 presence calls; all validation gates PASS.
- KEEP_GENOMES archive bug fixed (rmtree preceded zstd); retry pass and all
  future runs retain FASTAs as genome.fna.zst. The ~2,050 genomes done before
  the fix were deleted post-search — a `REDO_DONE=1` sweep would rebuild the
  local library if ever wanted.
- Remaining follow-up: export-web runs in the LLM chain tail; remove this
  section once stats + Numbers show the final state.
- host_panel_v2.json dedup: DONE 2026-10-15 (see Small polishes).

## New-paper refresh runbook (NOT automatic — run in order after intake)
1. `process_new_papers.py` (register + junk guards)
2. `llm_analyze_papers.py --skip-verified` (8005)
3. `llm_key_findings.py` → `llm_type_claims.py`
4. `llm_extract_mechanisms.py` (⚠️ pathway edges — often skipped; run it or
   pathways go stale for new papers)
5. `build-wiki` → `build_aggregation.py` → `connections.py export`
6. `build_gene_registry.py` → `build_paper_records.py`
7. `build_author_journal_db.py` → `build_author_network.py`
8. `export-web` → `build_by_the_numbers.py` (checks must be green)
Steps 2–4 are LLM; 5–8 take seconds. TODO: one pixi task chaining all of it.
Run 2026-10-14 for the accumulated intake: manifest rebuilt via
`corpus_preflight.py` (1,366 papers; 5 junk-guarded rows dropped), tail
steps 5–8 green, numbers 18/18. Gotchas hit: (a) 37 papers had STRING
years in papers.json (intakes pre-normalization) — normalized in place;
`build_wiki_pages.py` sort now guards non-int years. (b) The D98 wiki
threshold test now MIRRORS the builder's 2026-10-05 species-linked
singleton policy (imports its normalize_gene_name — alias chains must
resolve identically on both sides).

## Steward sweep
- `paper_steward.py --limit N` for iterative triage sweeps (least-recently-
  stewarded first). Cadence: after every intake batch + monthly. Everything
  ledgered; escalations land in `steward_queue.jsonl`.

## Genome expansion: resume semantics + storage (2026-10-06)
- **New genomes**: fully resumable — todo/progress delta; merges are
  (gene, assembly)-scoped, never clobber.
- **New panel genes**: run a gene-delta pass:
  `KEEP_GENOMES=1 PANEL_GENES=GENE1,GENE2 REDO_DONE=1 pixi run python scripts/genes/parallel_runner.py --workers N`
  — searches ONLY those genes across all todo genomes (blast_presence
  `--genes` scoping), including previously-done ones.
- **KEEP_GENOMES=1**: after a successful search, the raw FASTA is zstd-19
  compressed in place (`genome.fna.zst`, ~4x smaller) and rebuildable
  blast/diamond DBs dropped; fetch decompresses on demand → gene deltas
  never re-download. ~600-700 GB for all ~1,800 genomes at zstd.

## LLM allocation (7-day blocks — will drop without warning)
- Endpoint :8005 is a 7-day allocation. Before any LLM pass:
  `curl -s localhost:8005/v1/models` (expect muse-glimmer-30b).
- All LLM passes are resume-safe (done-files / hash-skip / ledgers): after a
  new allocation comes up, just re-run the same command; it continues.
- Pending LLM work if the endpoint drops mid-queue:
  mechanisms final expansion (running), 57 residual analysis repairs
  (`llm_analyze_papers.py --repair`), steward sweeps (cadence), keyword
  queue triage (1,267 escalations), any new intake batches.

## LLM health check (mandatory preflight)
- The :8005 server's NORMAL config since 2026-10-07 is REASONING mode:
  responses carry empty `content`, text in `reasoning_content`. Scripts with
  the fallback work; ones without fail silently (0 applied, N failed).
- Before ANY LLM pass: `pixi run python scripts/papers/llm_health.py`
  (exit 0 either mode, reports which). If REASONING mode, ensure the script's
  call helper has the fallback (backfill_metadata_llm.py has the reference
  implementation).
- YIELD EXPECTATION (learned 2026-10-15): extraction yield varies with
  ENDPOINT STATE, not prompt style — the same rich prompts yielded ~3
  items/section/paper during the original runs and ~1 on later endpoint
  builds. Don't chase yield with prompt tweaks; re-run when the endpoint
  behaves more generously (resume-safe per section).

## A11y layer (2026-10-08)
- **App-shell hooks in place**: skip-to-content link, route-change focus
  management + per-route `document.title`, sr-only `aria-live` announcer
  (`lib/stores/a11y.svelte.js` — call `announce(msg)` from any page for
  async state), labelled nav landmarks, `prefers-reduced-motion` CSS,
  Modal focus trap + labelled close.
- **Phase 2 DONE — compiler a11y warnings: 0** (was 20). Key fixes:
  SpeciesSearch is a complete ARIA-APG combobox (aria-activedescendant,
  keyboard-selectable options, keyboard-reachable empty option);
  Genes.svelte nested-button cards restructured (also fixed chip clicks
  bubbling into gene selection); History SVG bars are role=button with
  keyboard + labels; Model stage headers are keyboard accordions
  (aria-expanded); Research videos have real VTT caption tracks
  (generated from figcaption text — regenerate if videos change);
  Resources external links labelled; Synteny hover container
  role=presentation; SpeciesDetail field captions are divs not labels.
- **New UI strings exposed to users MUST go through `t()`** (incl.
  `aria-label`s — the i18n scanner checks attributes). A11y keys live in
  the inline en dict under `a11y.*`.
- **Regression tests**: `web/tests/a11y.spec.js` (Playwright, 7 tests —
  includes combobox keyboard + no-nested-buttons guards). Keep green.
- **Phase 3 DONE — standing axe gate**: `web/tests/a11y_axe.spec.js`
  (@axe-core/playwright, WCAG 2.1 A/AA) sweeps all 29 canonical routes.
  Runs in its own Playwright project (`a11y-axe`, config array-ordered
  AFTER `chromium` — do NOT use `dependencies`, upstream failures would
  skip it). Scoped routes: `/methods` excludes the vendored
  verso-dag-viewer bundle; `/clade` include-scans header+#clade-controls
  (28k-node matrix unwalkable). Violations append to
  `test-results/axe-violations.jsonl` for triage. NOTE: on a box running
  the genome pipeline concurrently, 1-3 heavy DuckDB tests may flake
  under CPU contention (all pass solo) — rerun before diagnosing.
- **Known follow-ups**: dark-mode contrast is HAND-maintained (light/dark
  class pairs): axe-core ≤4.14 mis-resolves Tailwind v4's oklch stylesheet
  backgrounds (reports #efefef), so the dark pass runs structural rules
  only with color-contrast disabled; re-enable when axe ships a fix.
  Dark mode is CLASS-based (`.dark` on <html>, synced from system pref in
  main.js + `@custom-variant dark` in app.css) — ready for a manual toggle.
  Other follow-ups: the vendored DAG viewer's node labels (upstream);
  locale files need the new keys — run `scripts/i18n_translate.py` when the
  :8005 allocation is back (resume-safe).
- **Announcer wired (2026-10-08)**: Species/Papers/Genes pages announce
  result counts to the `aria-live` region on load and filter settle
  (`announce(t('a11y.announce.*.results', {n}))`). SpeciesDetail dialog is
  named via Modal's `ariaLabel` prop. Both covered in a11y.spec.js. Non-a11y warnings are fixed
  (Modal snippets, MsaViewer $state, unused props, GeneFullPage pdb
  re-seed — that one was a real state bug across gene switches).
- **tc() takes NO params (2026-10-30 lesson)**: `tc(key)` reads only the
  content layer ({lang}.json / {lang}_content.json) and ignores extra
  args — `tc('home.stats.mammals', {n})` rendered NOTHING in en (no en
  content files exist). Keys with placeholders must go through `t()`.
  Also: `t('missing.key')` returns the KEY (always truthy), so
  `t(k) || fallback` shows raw keys — Downloads descriptions did exactly
  this for every file until the keys were added to en_i18n (2026-10-30).

## Standing future work (2026-10-15, user-confirmed queue)
- **Vaccine stage curation SHIPPED (2026-10-15)**: every model stage now
  carries `evidence.extracted` — real counts/distributions from the
  synthesis artifacts (platform claims, antigen mentions, delivery
  routes, adjuvants, immunogenicity endpoints, field outcomes, DIVA,
  campaigns by sector, escape-linked adaptation items) — rendered as
  🟢 chips on the stage cards alongside the keyword tier. Curated
  definitions stay authoritative; evidence merges in. GOTCHA: claims
  `antigens`/`adjuvant` fields are sometimes strings not lists — coerce
  before iterating or you get character-level garbage.
- **Numbers-gate integration SHIPPED (2026-10-15)**: build_by_the_numbers
  now carries a spread_model section (items/grounded/verified/edge
  links/eras/susceptibility/region countries) + 3 new cross-checks
  (spread parquet==per-paper JSONs, susceptibility twin sync, region
  countries==detection countries) — 21 checks total. First run CAUGHT a
  real gap: 4 countries with unnamed-species detections were dropped
  from region_risk (BOL/CYM/Georgia/KHM) — fixed to include presence-
  without-hosts with a note. Region-risk + vaccine builders joined the
  spread-rebuild chain (now 12 steps, ends at numbers).
- **Region-scoped risk view SHIPPED (2026-10-15)**:
  `scripts/model/build_region_risk.py` → `region_risk.json` + web twin —
  102 countries + 8 region rollups: presence (first stamp, era, records,
  bucket seasonality), detected species × susceptibility v2, WATCHLIST
  in two tiers (relatives-arrived: perm ≥40 with genus detected here;
  global: perm ≥60), corpus intro routes, campaigns. Route `#/region-risk`
  (RegionRisk.svelte, world view + country drill-down; 32nd canonical
  route; Footer nav). Rerun after detections/susceptibility/synthesis
  rebuilds. The kākāpō question, generalized: high-risk species not yet
  detected here, with the absence-of-evidence caveat rendered.
- **Extraction VERIFIED (2026-10-15, full corpus)**: `scripts/papers/
  llm_verify_spread.py` adjudicates every item for quote fidelity (judge
  sees quote+payload only; contradiction/invention counts as drift,
  quote-silent fields do not). Result: 86% faithful, 0.09% unsupported
  (4 items), partials concentrated in free-text fields. Verdicts in
  `spread_verify.jsonl` (resume-safe) and a `verify` column joins into
  paper_spread.parquet at aggregate — downstream can filter on it.
  GOTCHA: section repasses reuse idx keys → STALE verdicts; drop the
  section's ledger rows before re-verifying. YIELD LESSON (rich-vs-terse
  prompt A/B on 4 sections): prompt style barely moved faithfulness;
  yield is ENDPOINT-STATE-driven (original runs ~3 items/section/paper,
  current endpoint ~1 — same prompts). Corpus now 3,896 items, all
  verified. BACKUP LESSON: spread_v2_backup_<section>/ holds ONE
  generation (second --backup overwrites the first) — timestamp the dir
  if you need multiple generations.
- **Vaccine deep overhaul SHIPPED (2026-10-15)**: `build_vaccine_campaigns.py`
  (28 quote-grounded deployments, era-joined + region-bucketed; rendered by
  CampaignPanels on #/vaccines) + strategy matrix in `build_vaccine_outcomes.py`
  (platform × sector × DIVA × species) + the earlier outcomes ledger/protection-gap
  join. Rerun both after extraction passes; campaigns joins the era ledger.
- **Era emergence_2344b SHIPPED (2026-10-15, user-approved)**: 8th era
  (2020-06-01→2021-09-30; zoonotic_2321c now ends 2020-05-31). Measured
  first-stamps independently confirm the biology: europe 2020-06-11 →
  mena 2020-09-11 → north_america 2020-10-28 → africa 2021-01-14.
  2,011 detections, 577 papers, 59 introduction events joined.
- **Layer D parameterized edges SHIPPED (2026-10-15)**:
  `scripts/model/build_spread_parameters.py` → `spread_parameters.json`
  + merged into model evidence.parameters — 131 corpus params (R0/Rt,
  rates, ORs) + persistence durations mapped to 6 edges by context
  keywords, verify-filtered faithful-first. Rendered: param chips on Model
  connections + parameter block in cyto edge drawer. Rerun in
  spread-rebuild chain (add after build_spread_synthesis).
- **Region-norm join SHIPPED**: shared `scripts/model/region_norm.py`;
  synthesis carries establishment.region_matrix (8 buckets × routes ×
  outcomes: MENA 100% / Africa 95% / E-SE Asia 69% established).
- **LLM allocation-dependent work** (endpoint :8005, 7-day blocks):
  steward sweeps (cadence — CORPUS FULLY STEWARDED 2026-10-15: 1,367
  ledger entries ≥ 1,366 registered, zero due; rerun monthly or after
  intakes), keyword-queue triage (1,267 escalations),
  mechanisms repairs, any new intake batches. All resume-safe.
- **i18n translation batch (PENDING, queued 2026-10-30)**: when :8005 returns,
  run `LLM_BASE_URL=http://localhost:8005/v1 pixi run python
  scripts/i18n/fill_locale_gaps.py` — ~435 inline-dict keys per locale fall
  back to English (47 pre-dating the 2026-10-30 wiring pass + ~390 newly
  wired template strings; details in the i18n integrity section below).
  Resume-safe; verify with a re-render + leak diff afterwards.
  Second, smaller queue: zh/hi/ja/fr additionally miss ~300–380 legacy
  en_i18n.json keys (extend the gap-filler to that layer or hand-curate).
  Third (bigger, needs design): data-layer English — gene descriptions/roles,
  model + vaccine stage definitions, mutation-effect sentences, contradiction
  adjudication text — needs content-layer translation (pt()/tc() path),
  catalogued in the i18n wiring-pass notes.

## Small polishes (2026-10-15, ALL DONE)
- **Paper supplement (2026-10-30)**: `scripts/genes/build_gene_tiers_supplement.py`
  → `docs/supplemental/gene_tiers.tsv` (1,828 genes × tiers/importance/lit/
  cross-genome rates). Rerun after panel/registry/presence rebuilds. Folds
  legacy alias symbols (gene_config aliases) + best-status-wins per
  (gene, assembly) before computing rates — raw parquet rows double-count
  aliases (RIGI/DDX58, MDA5/IFIH1) and would inflate denominators.
- host_panel_v2.json: loci/synonym dedup was already applied (dropped_junk
  43, folded 9); removed remaining 6 single-letter/empty wiki_corpus noise
  entries (kept C = CEBPG) → 1,828 genes.
- D57 extract_spread_data.py → scripts/model/archive/ (superseded).
- web/tests/tab-content.spec.js: 4 interaction tests (tabs, risk-card
  modal, vaccines layers, susceptibility pages) — the click-then-scan
  pattern is now permanent, guarding against route-passes-panel-blank.
  Suite now 74 tests (70 + 4).
- Locale stragglers resolved: fill_locale_gaps now accepts single-word
  exact echoes (cognates — integrity suite's allowlist agrees); es/fr
  complete.
- Yield-restoration experiment RESOLVED: restoring the rich prompts did
  NOT recover yield (contact 433→153 items on identical prompts) — yield
  is endpoint-state-driven, not prompt-driven. Corpus accepted at 3,896
  items, 86% faithful, every item verified. Downstream rebuilt
  (1,883 edge links). Original high-yield extraction files are not
  recoverable (single-generation backups); if the endpoint later returns
  to higher-yield behavior, re-running the four sections will recover
  them — resume-safe.

## Spread model v2 — layered (2026-10-08, EXTRACTION COMPLETE)
- Roadmap: `SPREAD_MODEL.md` Phases 6–8 (diagnosis + layered design:
  eras ledger, introduction events, host-competence matrix, parameterized
  edges; literature-vs-detections validation join).
- **Extractor shipped**: `scripts/papers/llm_extract_spread.py` — iterative,
  quote-grounded, resume-safe (per-paper JSONs in `data/papers/spread_v2/`),
  standing stage in `enrich_pipeline.py`; `--aggregate` builds
  `data/papers/paper_spread.parquet`. D57 `extract_spread_data.py` is
  legacy — do not run it; retire to archive once v2 covers scope.
- **FULL RUN DONE 2026-10-14**: 1,149 papers × 19 sections → 3,938 items,
  90% quote-grounded. All acceptance gates passed (host_roles 445,
  mammal_chains 110, introduction_events 447). `llm_roles` merged into
  `host_competence.json` (roles/clades/papers per species; synonym map in
  `build_host_competence.py`; group labels skipped by design).
- **Post-extraction chain**: `pixi run spread-rebuild` (aggregate + edges
  + eras + competence + features + numbers; call BARE — pixi appends
  args to the last chained command).
- **Edge mapping SHIPPED (2026-10-14)**: per-edge evidence is now
  field-derived from v2 items (mapping table in SPREAD_MODEL.md Phase 7
  Layer B) — 2,124 paper-edge links (was 189 legacy); every edge carries
  `mapped_from` + `grounded` + PAPER_EXTRACTED provenance; verdicts stay
  stage-level; spread_evidence.jsonl (D57) is fallback-only. Gotcha found:
  the seasonality section prompt lacked the `{"item": …}` wrapper → zero
  items corpus-wide; fixed + backfilled (`backfill_seasonality.py`,
  103 items / 86 grounded — autumn_peak 36, year_round 15). The Model
  page connections list renders this evidence (counts + grounded +
  mapped-from chips + contested flags). Playwright gotcha: suite runs can
  leave a stale vite on :5177 that hangs the next run — `ss -tln | grep
  5177` and kill before rerunning.
- **Spread synthesis SHIPPED (2026-10-15)**: `scripts/model/
  build_spread_synthesis.py` → `spread_synthesis.json` + web twin — the
  item-level corpus ledgers (introductions w/ era join + emergence-
  phase note, mammal chains, reassortments + adaptations, transmission
  params, silent-spread, establishment tally, non-vaccine response,
  impact/recovery, surveillance) PLUS computed FINDINGS block (detection
  lag median 8 mo IQR 3-13; mortality-vs-active surveillance lens; loss:
  recovery 95:18; 2.3.4.4b establishment 44% share/75% sticks; R0 span
  1-16). Rendered as 4th tab "Corpus synthesis" on #/spread-layers with
  findings callout cards. Rerun via `pixi run spread-rebuild` (chain
  includes it).
- **Susceptibility v2 SHIPPED (2026-10-15)**: `scripts/model/
  build_susceptibility.py` → `species_susceptibility.json` + web twin.
  TWO-AXIS redesign (v1 = mortality × RIG-I conflated severity with
  susceptibility — the reservoir paradox was invisible): PERMISSIVENESS
  (weighted evidence composite: experimental infection 0.30 w/ replication
  boost, field outbreaks 0.25, corpus verdicts 0.15, detections 0.15,
  serology 0.10 + genus→family inheritance at donor-confidence for thin
  species) is the summary score; SEVERITY reported alongside, never folded
  in; RIG-I displayed as context only; `unevaluated` class for
  evidence-free species. Every species ships its component breakdown + a
  methodology block (formula/weights/bands/changelog) in the artifact.
  Pages: `#/susceptibility` (overview + methodology) and
  `#/susceptibility/{name}` (dedicated: axes, breakdown, clades, RIG-I,
  verdicts); linked from the competence risk card; 31st canonical route.
  LLM section `susceptibility_verdicts` (infection_confirmed /
  exposure_only / resistance_suspected, quote-grounded) feeds the verdict
  component — rerun `build_susceptibility.py` after verdict passes. In
  the spread-rebuild chain. Verdict pass done 2026-10-15: 394 items, 88%
  grounded, 32 species resolved (synonym resolver required — plain
  name matching caught only 20); headline two-axis reads now correct:
  mallard highly_susceptible/severe, human susceptible/mild, cattle
  susceptible (54 infection_confirmed), cat highly_susceptible/severe.
- **Susceptibility gotchas learned (2026-10-15, user-driven)**: (1)
  literature-only species (vaccination targets with zero surveillance
  presence — kākāpō/Strigops) enter via SYNONYMS+VAX_SYNONYMS resolution;
  common name stored from the resolving synonym; `unevaluated` not 0.0
  when no evidence fires (102 species de-faked). (2) Zero-detection
  species note rendered; regional virus presence ≠ species exposure.
  (3) SEVERITY = p75 of field+experimental mortality — the data is
  BIMODAL (vaccine-protected groups at 0%, unvaccinated controls at the
  upper mode; Gallus: 11/20 rows zero) so medians land in the protected
  mode and understate severity. Basis+n shown per species. (4) Order
  hints for literature-only taxa (Strigops→Psittaciformes) power the
  RIG-I display.
- **Direction repass (2026-10-15)**: `backfill_section.py --section X
  [--force] [--backup]` is the standing targeted-repass tool (generalized
  from the seasonality one-off). introduction_events prompt gained a
  direction enum (prose guidance BEFORE the JSON template — long rule
  text inside the template broke JSON compliance and collapsed yield
  447→171; fixed → 260 events, 63% direction-stated: w→d 45, w→w 113,
  d→w spillback 6). Count < 447 = stricter precision, not loss. LESSON:
  never put explanations inside the JSON example; always --backup with
  --force (the first force pass destroyed the original items).
- **De-NZ done**: spread stage `nz_risk` → `regional_risk` (generic
  elements; region specifics live only in `spread_regions.json` instances).
  Touched: both model JSONs + shipped twins, `build_vaccine_model.py`,
  `Model.svelte`/`ModelMermaid.svelte` mermaid, en dict keys
  (`mermaid.regional`, `model.spread.regional_risk.title`); stale
  `*nz_risk*`/`mermaid.nz` keys purged from all locale files (next
  translation batch fills the generic ones).
- **Evidence block**: `build_spread_edges.py` now also emits
  `evidence.stages` (stage-level verdict evidence from
  `model_verdicts.jsonl` — verdicts are STAGE evidence, deliberately NOT
  mapped onto edges; edge counts stay extraction-only). Run after any LLM
  round: LLM round → `build_spread_edges.py` → export.
- **Layer A SHIPPED (deterministic, no LLM)**: `scripts/model/build_spread_eras.py`
  → `data/model/spread_eras.json` + web twin (7 eras, 7 chapters, measured
  region first-stamps from detections, paper links via clade registry).
  Rerun after detections rebuilds or `clade_discovery.py` scans. Chapters
  without feed coverage (cattle B3.13, 2015 Midwest poultry) ship
  `measured: null` + note — never a misleading wild-bird count.
- **Layer C base SHIPPED (deterministic, no LLM)**:
  `scripts/model/build_host_competence.py` → `data/model/host_competence.json`
  + web twin (167 species: mortality/shedding/clades from verified traits,
  susceptibility join, detections stamps, per-block provenance). LLM
  `host_roles` merge in via Phase 6 once :8005 returns.
  Rerun after trait passes / susceptibility rebuilds / detections rebuilds.
- **Capture design final (2026-10-08)**: 19 LLM sections (virus/hosts/
  routes/events/measurement) in `llm_extract_spread.py`; **[DET] features
  shipped**: `build_spread_features.py` → `spread_features.json` (measured
  seasonality, persistence 1,296 pairs, diffusion 30.6 km/day panzootic,
  mass events 1,461/463, mammal share, accumulation, sampling mix) and
  `build_host_competence.py` extensions (per-clade mortality, gap matrix
  759×8, proxy rollup for 59 thin species). Phase 8 goal: species risk
  card. All DET artifacts rerun after detections/susceptibility rebuilds.
- **PENDING**: Phase 7/8 rendering — era scrubber UI, competence table,
  species risk card; consumes shipped twins `spread_eras.json`,
  `host_competence.json`, `spread_features.json` (in web/public/data,
  not yet consumed by UI).
- **Phase 7/8 RENDERED (2026-10-14)**: new route `#/spread-layers`
  (SpreadLayers.svelte + components/spread/{EraTimeline,CompetenceTable,
  FeaturePanels}): era band + chapters + paper links, sortable competence
  table with species risk-card modal (per-clade mortality, extracted
  roles, proxy block, evidence grid), measured dynamics (seasonality /
  diffusion / persistence / mass events / mammal share / sampling mix).
  Route in Footer + Model/SpreadCyto cross-links; in both canonical-route
  lists (axe sweep + render_pages — 30 routes now). All strings via t()
  (`spread.*`, `nav.spread_layers`); svelte-check clean (new files, real
  errors); i18n_scan 0.
- **Readability iterations (2026-10-15, user feedback)**: (1) all
  sub-12px text eliminated across layers/model/cyto pages — audit via
  computed-style probe (leaf-node font-size histogram), not eyeballing;
  (2) Mermaid.svelte renders at NATURAL size (useMaxWidth:false in
  mermaid.initialize + max-content CSS — the default width:100%+viewBox
  scaling is what shrinks wide diagrams to unreadable text); (3)
  SpreadCyto node labels 13/10/9 → 16/13/11px; (4) findings teaser
  strip above the spread-layers tabs (3 clickable stats → synthesis
  findings); (5) zebra + sticky-header tables. GOTCHA: template
  enhancements without script definitions (eraDesignations ReferenceError
  blanked the page via route boundary) — svelte-check catches these;
  run it after ANY template edit, even "just adding a loop".
- **Infection mermaid DEPRECATED (2026-10-15, user)**: Model.svelte host
  tab renders ModelCyto (embedded prop — hides page hero) instead of the
  mermaid diagrams; diagrams{} sources kept in code, unreferenced →
  tree-shaken from the bundle. ModelMermaid.svelte route already
  unreferenced. View chips on the page now filter only the
  literature-evidence panel. Chat widget OFF in dev
  (web/.env.development VITE_LOCAL_LLM commented out; re-enable =1).
  SPREAD TAB TOO (same day): spread-overview mermaid → SpreadCyto
  embedded (timeline scrubber + evidence drawers on the model page);
  vaccine pipeline was already VaccineCyto (D125). NO mermaid renders on
  the model/vaccine pages now — Mermaid.svelte remains for any future
  static use.
- **Locale gap-fill (2026-10-14)**: `scripts/i18n/fill_locale_gaps.py`
  is the standing "next translation batch" tool — finds en-dict keys
  missing from each `{lang}_i18n.json`, translates via :8005 with the
  doctrine accept-filter (echo/placeholder/token-leak), resume-safe.
  NOTE: i18n_translate.py + extraction.json is the legacy D68 track
  (523 keys, 0 overlap with the current dict) — use the gap-filler.
- **Context-aware improvement + render-audit (2026-10-15)**: `scripts/
  i18n/improve_translations.py` re-reviews translations GROUPED BY PAGE
  FAMILY with curated section context (scientific/operational/a11y
  registers) — 1,604 upgraded across 6 locales (chunked: large families
  truncate single-shot JSON). `render_pages.mjs` + `llm_audit.py` per
  locale is the deep leak check — 2026-10-15 sweep: new pages CLEAN;
  pre-existing leaks fixed on spread-cyto (4 strings: diverges/additions
  headers, narrative link, timeline units) + zh sort.hint kept
  "clade loss" untranslated inside itself. Audit findings format note:
  "Page: <route>" lines are the auditor's labels, not leaks.
- **axe gotchas learned 2026-10-14**: (1) `test.setTimeout` called at
  module/loop level silently does NOT apply — must be inside the test
  body (the old 90s SLOW budget never took effect). (2) A full axe pass
  over DuckDB-table routes measures ~50s (color-contrast style
  resolution) — SLOW routes now budget 240s inside the body; page itself
  hydrates <10s at stable DOM (not a page regression if timeouts grow).
  (endpoint was resetting through the tunnel as of this note); then
  Phase 7 layers (eras/events/competence) in the model JSON + rendering.

## Bird of the Day card (2026-11, homepage engagement)
- `scripts/genes/build_bird_of_the_day.py` → `web/public/data/
  bird_of_the_day.json` (wired INTO export_web_data.py — refreshes every
  export; reads the just-exported parquet + species_index, so it must run
  after them). Flat roster: 1,996 birds × 18 tier-1 genes, status string
  P/F/A per gene; BIRDS ONLY via aves_taxonomy.tsv species-rank filter
  (51 mammals excluded — a mammal on this card is a bug); incomplete-panel
  species excluded (great cormorant's 3-gene outlier).
- Determinism: FRONTEND picks `candidates[floor(UTCms/86400000) % len]` —
  same bird everywhere per day; dataset updates shift the cycle (accepted).
- Component `web/src/lib/components/common/BirdOfTheDay.svelte` (runes,
  JSDoc-typed — new files stay svelte-check-clean): italic sci name is the
  headline and LINKS to `#/species-full/{sci}` (NOT `#/species/{id}` —
  that opens the SpeciesDetail modal, which FAILS for genome-only/det=0
  species; known modal gap, separate fix if ever needed); CTA links
  `?tab=genes`. Up to 2 vernaculars in small print (nm[] embedded by the
  builder from species_names.json, echoes skipped; 79 species show none);
  LLM `summary` from `data/species_insights/{taxid}.json` lazy-fetched
  per-day pick (exists for all 11,349 index species); NO assembly chips
  (user: don't show genome info); PhyloPic silhouette when available.
  Tiles link to gene pages; group labels via `t('home.bird.cat.' + c)`
  (fixed 5-cat vocabulary + other — keep keys in sync). Tests:
  tests/bird_of_day.spec.js recomputes the pick independently + guards
  counts/links.

## Mobile-width overflow fixes + country picker (2026-11, user feedback)
- **min-w-0 fix class**: grid items (`lg:col-span-*`) and flex items holding
  `truncate` (nowrap) text MUST carry `min-w-0` or their min-content = full
  unwrapped text and the page blows out 6× on phones (Genes 2491px,
  Mutations 4901px — both fixed 2026-11-04). Fixed pages: Genes,
  Mutations, Numbers (6 tables → overflow-x-auto wrappers), Papers
  (3 filter selects → max-w), SpreadLayers (tab strip → flex-wrap),
  Methods (mermaid wrapper → overflow-x-auto), RegionRisk (select).
- **Permanent gate**: `web/tests/mobile_width.spec.js` — all 33 canonical
  routes at 390px assert html+body scrollWidth ≤ viewport (body.scrollWidth
  is the honest signal under the overflow-x:clip guard). Own Playwright
  project (`mobile-width`, heap-isolated like a11y-axe). Run it after any
  layout change; failure message names the widest unclipped element.
- **Phantom-overflow roots found (2026-11-04)**: vendored
  verso-dag-viewer's shadow canvas escapes its element box (now wrapped in
  overflow-x-auto in Methods) and long unbreakable `<code>` path tokens
  (`[overflow-wrap:anywhere]` on Numbers intro). Bisection probe pattern:
  hide-subtree → watch body.scrollWidth drop → descend culprit.
- **Phantom scroll guard**: `html, body { overflow-x: clip }` in app.css
  (methods/numbers had scrollWidth>viewport with NO unclipped element).
  `clip` ≠ `hidden`: no scroll container created, sticky nav unaffected.
- **Georgia → GEO**: ingest_detections name_to_iso lacked "georgia";
  someone had symptom-patched REGIONS in build_spread_eras with a literal
  "Georgia" entry — removed. Doctrine reminder: fix the harmonizer, not
  the consumer. New shared scripts/model/iso3_names.py (pycountry-derived
  static ISO3→name) stamps `name` on region_risk country entries (BOTH
  construction paths — the presence-without-hosts path was missed first
  time); RegionRisk picker now sorts by name and shows "Name (CODE)".
  Rebuild chain after country-label fixes: ingest-detections → export-web
  → build_spread_eras → build_region_risk → build_by_the_numbers (21/21).

## No region-specific schema — equal treatment (2026-10-08)
- The NZ-specific layer is REMOVED: overlay lists are now `mammals` /
  `manual_detections` / `species_of_concern`; fields are country-agnostic
  (`vaccination_target`, `conservation`, `population_estimate`, `case`,
  `countries`). Region attribution flows through the same `countries`
  field detections use — never a country-named field.
- Do NOT reintroduce `<region>_`-prefixed fields or lists; a species from
  any country enters through the same overlay lists + generic fields.
- genomes.json roles: "NZ priority…" → "conservation priority…"
  (`fetch_genomes.py --set concern` is the new selector).
- UI keys: `species.card.vaccination.target`, `common.searchbar.vaccination.target`;
  locale files purged of stale `*.nz.*` keys — next translation batch fills
  the generic ones.

## Genome staging farm: dangling-link hygiene (2026-10-08, FIXED)
- `vite build` no longer crashes on dangling `web/public/data/genomes`
  symlinks (19 pruned; root cause: pre-KEEP_GENOMES-fix rmtree deleted
  2bit/gff targets while public links remained).
- Self-healing now lives at three layers: `parallel_runner.py`
  `prune_public_links(acc)` on archive/delete, `fetch_gffs.py` /
  `genomes_to_2bit.sh` prune+relink on re-stage, `make_dist.sh` prunes on
  farm restore. If a bare `vite build` ever ENOENTs on public/data again,
  check `find web/public/data -xtype l` first.
- **Full restoration done same day**: all 9 affected genomes are back.
  7 NZ endemics regenerated from their `genome.fna.zst` archives
  (`genomes_to_2bit.sh ACC…` now decompresses on demand); kea + NI brown
  kiwi re-fetched via datasets CLI — **both sha256-matched the manifest**, so
  they're byte-identical to what the 817 presence calls each ran against
  (no re-search needed). Farm: 15 genomes w/ 2bit (15/15 pass
  `scripts/genes/verify_2bit.py`), 11 with GFF tracks. `fetch_gffs.py` now
  accepts `status=archived`.

## Dev-server port split (2026-10-15)
- **5177** — LAN dev server (`npm run dev -- --host 0.0.0.0 --port 5177`): the one
  users browse via the LAN dev-server address (http://<lan-host>:5177). Run as a background task.
- **5178** — Playwright test fixture (localhost-only, `webServer` in
  playwright.config.js). Do NOT move tests back to 5177: the fixture steals
  the port from the LAN server and every test run kills user browsing.
- The route tree is wrapped in `<svelte:boundary>` — a component crash logs
  `[route boundary]` and degrades instead of taking the app down. Client
  crashes previously killed whole sessions (shadowed-`t` class, cytoscape
  detached-container race; both fixed 2026-10-15).

## i18n integrity pipeline (2026-10-08)

### Wiring pass 2026-10-30 — hardcoded-English sweep (scanner was reading a false 0)
- **`scripts/i18n_scan.py` FIXED**: the old text-node regex was line-bound
  (`>text<` on ONE line) so standalone/multi-line text nodes were invisible,
  and `is_english` required 2 EN_WORDS — it read "0 across 0 files" while
  ~200 real strings sat in templates. Now: whole-template DOTALL matching,
  script/style/comment blanking (offsets→line numbers preserved), relaxed
  threshold (≥1 EN_WORD + ≥2 words). Reads 0 = clean AGAIN (standing gate
  restored; currently 1 deliberate skip — FeaturePanels numeric tooltip).
- **`scripts/i18n/render_pages.mjs` FIXED twice**: (1) playwright `hasText`
  is case-insensitive substring — `hasText:'ES'` matched the Species/Genes/
  Genomes nav buttons, clicked "Species", and the ES render silently captured
  ENGLISH (locale never switched; check `localStorage.roost-locale` when
  auditing). Now exact-match `^ES$` via `.filter({hasText: regex})`. (2) fixed
  1.2s settle → `waitForFunction(body>900 chars, 10s)` — DuckDB-WASM routes
  (methods/numbers/downloads/…) need seconds to hydrate.
  Also: import now resolves playwright-core from `web/node_modules` (script
  dir has none) via `createRequire`.
- **Map.svelte SPA-killer FIXED**: MapLibre `map.remove()` throws during
  teardown races; the exception escaped the route boundary and left EVERY
  later route blank (map → any nav = dead app until reload; headless renders
  from /map onward were chrome-only because of this). Now guarded try/catch
  + `map = null` in onDestroy.
- **~200 template strings WIRED** across 36 files (model, vaccines, numbers,
  anp32 full page, methods full page, genomes, model-cyto controls, genes
  cards incl. `{n} papers`/`{n} connections`, history, orthogroups, research,
  blast, compare, credits, spread-cyto, clade, landscape, synteny, resources,
  downloads, papers, susceptibility, contradictions, map, phylogeny,
  species, glossary, chat widget, vaccine-cyto, phylo tree, gene/species
  components, App). Keys live in the inline en dict (marked
  "i18n wiring pass 2026-10-30" sections); ~1545 dict keys total, 0 dups
  (svelte-check object-literal errors were duplicate keys — one agent edit
  duplicated a vocab block; deduped, keep-first).
- **t()-with-dynamic-key trap, two live instances fixed**: `t('downloads.tool.'
  + source.name)` and `t('resources.desc.' + resource.id)` — the latter key
  didn't even exist (`resource.id` undefined → every Resources description
  showed the raw key). Both now have full key sets keyed by stable names.
  LESSON (again): `t(dynamicKey) || fallback` NEVER falls back — t() returns
  the raw key, which is truthy. Static-coverage audit must resolve dynamic
  prefixes (keys ending `.` + concat).
- **Locale coverage after the pass**: ~435 inline-dict keys per locale fall
  back to English (47 pre-date this pass; ~390 are the newly wired strings).
  `fill_locale_gaps.py` picks them ALL up when :8005 returns (resume-safe) —
  that is the single pending LLM action for UI completeness. Legacy
  en_i18n.json layer additionally misses ~300-380 keys in zh/hi/ja/fr only.
- **Data-layer English (catalog, NOT fixable by template wiring)** — shows on
  non-English pages, needs content-layer translation via :8005:
  gene descriptions/roles from the wiki corpus (genes cards/profiles), model +
  vaccine stage `desc`/definitions from data/model/*.json, citation-heavy
  narrative strings. Same treatment path as paper summaries (pt() layer) or
  {lang}_content.json via tc().

### Data-layer translation infrastructure (2026-10-30, LLM pass 2)
- **Hash convention**: md5(english)[:12] stamped on every translatable corpus
  string — `fh` (wiki findings/roles, existing), now also `eh` (mutation
  effects), `th/wh/ex` (contradiction topic/what/explanation), `th/sh`
  (research-briefing title/summary). Builders stamp: build_wiki_pages.py,
  export_contradictions.py, research_agent.py (index rebuild). Components
  translate via `ft(hash) || english` — zero new store code.
- **Wired render sites**: Mutations (effects+titles via eh/pt), Genes card
  descriptions (fh; 869/1,298 pre-covered), Contradictions (titles via pt,
  adjudication text via th/wh/ex + verdict chips/filter/summary keys),
  Landscape briefings (th/sh), Model avian stages — content keys are
  `model.stage.{id}.*` (the old code pointed avian stages at
  `model.spread.*` — always-missed lookups), Vaccines stages
  `vaccine.stage.{id}.*` via tc().
- **`scripts/i18n/translate_data_layer.py`** — standing batch translator for
  the above (mutation effects, wiki roles, topics vocab, model/vaccine stage
  text, contradictions, briefings) → papers/{lang}.json findings/roles/topics
  + {lang}_content.json. Doctrine-filtered, resume-safe. GOTCHA that cost a
  full run: un-escaped `{placeholder}` in an f-string prompt → NameError per
  batch, silently counted as rejects — escape braces ({{…}}) in prompts.
- **fill_locale_gaps.py --layer en_i18n**: covers the legacy en_i18n.json key
  space (zh/hi/ja/fr had ~300-380 gaps each; filled 2026-10-30).
- Paper topic vocabulary: 912 distinct topics exist, 289 were translated →
  the data-layer batch covers the rest via the topics map.
- **Results (2026-10-30 full run)**: findings map 1.7k → ~5.8k/locale
  (mutation effects + contradictions + briefings), roles ~complete
  (4,920-4,935), topics 770-817/912 (residuals are gene-symbol topics
  that correctly stay English), stage text +41 keys in every content layer.
  Visible English on a full ko sweep: 1,649 → 871 lines (47% down; the
  pre-infrastructure baseline was 376 but only because 10 routes rendered
  blank behind the Map teardown bug).
- **Remaining English (catalogued, second-order)**: stage `evidence.extracted`
  bullet strings inside avian_h5n1/vaccine model JSONs (citation-key
  sentences), paper-id chips, Numbers check names/artifact ids, ~130-165
  permanent doctrine-reject UI keys per locale (org names/proper nouns).
  Same hash-stamp pattern extends to these if wanted later.
- BUG CLASS to watch: an unbalanced Svelte expression brace in one lazy
  route (Orthogroups) 500'd its module and left EVERY page blank — vite
  serves the app shell but the router import chain dies. svelte-check
  reports it as route-file errors; ALWAYS diff per-file error counts, not
  just the total. And never judge a bg pipeline by its tail — pipe to a
  log file and echo the real exit code.

- **Full-taxonomy species index (2026-11-02, the hihi question)**:
  species_index.json now carries the FULL Aves taxonomy tail (11,284
  species-rank rows from aves_taxonomy.tsv; subspecies excluded) — not
  just detection/genome/research species. Every bird is searchable
  (Methods promise finally true); taxonomy-only records are minimal and
  rank below data-rich ones (search scores by det count). Genome backfill
  ALSO backfills catalogue common names; the overlay backfills curated
  fields. Hihi (Notiomystis cincta) — no detections/research but HAS a
  genome + full gene panel (1,428 genes, 972 present) + OrthoFinder
  orthogroups — was simply invisible; added to species_of_concern overlay
  (common name, VU, population). SpeciesFullPage index-fallback now
  carries iucn/conservation/population/countries and renders an IUCN chip
  from overlay conservation text (CONV map, watch NT vs NE).
- **Common-name pass (2026-11-02)**: `scripts/fetch_common_names.py` —
  Wikidata SPARQL vernacular mirror (same channel as the IUCN status
  one) fills the taxonomy tail: +5,286 English names, unnamed species
  6,428 → 1,142 (10%, Wikidata has no English label for those). Artifact
  `data/aves_common_names.json` (git-tracked, checkpoint-per-batch,
  resume-safe); export_web_data.py merges it on every rebuild; index
  patched live. Search now finds huia / kokako / stitchbird by name.
  Rerun after taxonomy refreshes.
- **MAMMALIAN-ONLY MUTATION CENSORSHIP (2026-11, data governance)**:
  mutations with host_scope == 'mammalian' (175 of 870) are REMOVED from
  every shipped artifact — wiki_mutations.json (695 ship), wiki_index
  mutations section, wiki_genes per-gene mutation chips, and the curated
  spread_mutations.json edge refs (HA-G228S/HA-N224K dropped from
  data/manual + web copy). The full set lives in the INTERIOR private DB
  `data/papers/wiki_mutations_private.json` (never web-served; pipeline
  records/ledgers retain everything else). Enforced in
  build_wiki_pages.py (split + strip + private write) — rebuilds keep it.
  Deliberately NOT censored: free-text findings sentences in
  pathway_edges.json (4 mentions) + spread_synthesis.json (3) and one
  research-briefing narrative — literature prose, not mutation records.
  Frontend mutations page drops 870→695 automatically (data-driven).
  Also fixed while here: verify_downloads STATS expectations now read real
  sources (papers.json / gene_catalogue total_genes) instead of stale
  hardcodes; stats.json regenerated (searchable_species 11,348). All 21
  by-the-numbers checks + verify_downloads green.
- **Clade papers-sort family fold (2026-11)**: build_clade_matrix.py
  FAMILY_FOLD (POLYMERASE→PB2/PB1/PA, IFN→IFNA1/IFNB1/IFNG) — members
  max-merge the family count; family rows flagged and hidden from the
  papers sort. Builders joined papers+importance into matrix rows.
- **Gene page layout (2026-11-02, user review)**: headline cards (key
  finding, impact-if-lost, ANP32 cross-link) moved to the TOP of
  GeneFullPage, above the LLM profile and everything else. New
  "Orthogroup · OG…" button beside Pathway/Phylogeny in the header button
  row when a mapping exists (data-testid=view-in-orthogroup).
- **Species-view UX fixes (2026-11-02, user review)**: short view tabs now
  sync to the hash (#/species/56069?tab=genes — shareable, back works;
  read on open, navigate on click). "View all N genes →" button at the TOP
  of the gene panel + bottom link, both carrying ?tab=genes (the old link
  dropped the tab). Full-page Research tab rendered {f} objects →
  [object Object]; now renders the short view's pattern (value chip +
  ft(f.fh) finding + paper link). EvidenceDrawer: "No HSP evidence stored"
  is honest (evidence/*.json covers 15 reference species/gene, not all
  2,048) but now explains scope + shows the pipeline call (status chip /
  level / method) passed as a call prop. Panel count 1,428 VERIFIED =
  post-alias-merge searched genes (1,828 is pre-merge loci). Also wired
  previously-missed chips: present/fragment/absent/critical-absence/
  "{n} immune genes searched".
- **Multilingual vernacular names (2026-11-02)**:
  `scripts/fetch_species_names_multilingual.py` — Wikidata labels for ALL
  index species in the 6 UI locales, merged into species_names.json
  (existing LLM-reviewed entries win). 43k names fetched, then ~14k
  sci-name ECHOES stripped (Wikidata's label for obscure taxa is often
  just the Latin binomial — filter `label.lower() == sci.lower()`;
  fetch_common_names.py had the same gap, 1,247 index echoes removed).
  Honest coverage after cleaning: en 8,959 / ja 8,830 / fr 6,828 /
  zh 5,395 / es 2,267 / ko 1,108 / hi 577. Thin locales = Wikidata
  lacks labels, NOT a fetch bug; GBIF vernacular API (language-tagged)
  is the natural backfill for es/ko/hi if wanted. Verified: searching
  스티치버드 / マガモ finds the species in any locale.
- **Map data/decoupling fix (2026-11-02)**: host chromium LOST WebGL
  entirely (snap/GL state — all --use-gl flags fail). The map's stats
  line depended on MapLibre's 'load' event → froze at 0. Now loadLayers()
  runs unconditionally from onMount; refresh() sets stats BEFORE
  registerPointLayers (which touches maplibre internals and can throw on
  a broken transform); setDetections stashes pendingDetections until
  mapReady. Map page renders counts headless; the map test passes without
  WebGL. If headless WebGL returns, nothing changes.
- **Pass-4 (2026-10-30)**: vaccine `claims_resolved[].claim` (23) stamped
  `ch` + wired via ft() (builder build_vaccine_model.py patched);
  pathway-edge + gene-evidence mechanism effects (334 + 2,197 stamps,
  builders connections→build_aggregation patched, gene_evidence/*.json
  post-hoc stamped) wired via ft(eh) in Model / GeneFullPage /
  MutationFullPage; ModelCyto carries eh for its (currently unrendered)
  effect field. anp32.par.*, bar_height, mutations.n_papers — persistent
  symbol-heavy rejects — hand-filled all locales. Topic-reject audit:
  remaining ~107 are Latin binomials / standard virus names (correctly
  English). Numbers check names deliberately stay English (artifact
  contract identifiers).
- **Pass-3 cleanups (2026-10-30)**: Synteny `{n} species` + Core-genes
  heading + method note wired; Orthogroups counts/tiers/stats-line wired
  (tier labels via t()); History paper-highlight titles via pt(h.id);
  SpreadCyto legend lines wired; 37 credits.desc.* org keys added (LLM
  echoes org descriptions — hand-filled 15/locale); persistent single-word
  rejects hand-filled. Methods page gained section "11 · Multilingual
  translation pipeline" (methods.h2.i18n + 4 paragraphs — layer
  architecture, local-LLM/sustainability link, doctrine filter, context
  pass, verification layers, scale numbers).
- **Context quality (2026-10-30 follow-up)**: gap-fill translates bare
  key→value pairs — key names carried implicit context (worked for most:
  numbers.checks.right → 正确值 not “right-hand”), but that's luck-of-naming.
  improve_translations.py (the page-family context pass) got 14 NEW curated
  FAMILY_CONTEXT entries (anp32/numbers/model.cyto/model/genomes/methods/
  orthogroups/contradictions/history/mutations/landscape/synteny/footer +
  explicit sense notes: "'Right' = correct expected value", "'Center'/'Fit'
  are verbs", "'Open' = open research questions") and re-reviewed all 18
  new families: 1,596 translations improved across locales. Data-layer
  sentence audit (manual read of matched pairs): domain vocabulary correct,
  hedges preserved ("described as" → 被描述为…相关), symbols/strains/
  clades verbatim, natural syntax; stage text handles concepts (DIVA →
  区分感染动物与接种动物) correctly. Ledger skips unchanged families, so
  future key additions auto-enter the next context review.

- **Matomo analytics (2026-11)**: `web/src/lib/analytics.js` — gated by
  *.josephguhlin.com hostname AND VITE_MATOMO_URL/SITE_ID (.env.production;
  id 3, https://josephguhlin.com/matomo/). Cookieless (disableCookies),
  hash-SPA virtual pageviews, link/download tracking. DEV NEVER TRACKS
  (verified: _paq undefined on localhost/LAN). Tracked surfaces: site
  searches (global bar + species gene-filter + papers search, all with
  result counts → trackSiteSearch categories global/species-genes/papers),
  entity views (Gene/Mutation/Species/Orthogroup → trackEvent with
  symbol/name), UI events (locale switch, evidence-drawer opens, map
  species filter, compare add). Adding more: import { trackEvent,
  trackSearch } from analytics.js — both no-op unless _paq exists.
- **Footer logo lockup (2026-11)**: 🪺 at 45px + two-line wordmark.
- **Beta banner (2026-11)**: dismissible welcome card above home stats;
  email click-to-reveal (reversed-fragment assembly — never contiguous in
  HTML or bundle; verify fragments when changing).
- **Glossary pagination (2026-11)**: 60/page, ?p= URL-synced, search
  resets to page 1; duplicate-abbr entries keyed on abbr+def (HEV×2 etc.).
- **Home of the figure credits**: PhyloPic attribution reads `attribution`
  field (not `contributor` — was silently empty before 2026-11).
- **Methods page (2026-11)**: 40 `${t(` template-literal bugs fixed (Svelte
  renders the $ literally); big mermaids in bounded scroll regions
  (role=region tabindex=0 — axe requires it); prose bumps text-xs→text-sm.

Three standing layers — run after ANY translation batch or UI change:

1. **Static scanners** (fast, no browser):
   - `pixi run python scripts/i18n_scan.py` — hardcoded-English detector for
     templates (text nodes, attributes, multi-line, options). Reads 0 = clean.
   - key-coverage audit: every `t('key')` call must exist in the inline en
     dict or `en_i18n.json` (the `t()` returns the KEY when missing — always
     truthy — so `t(k) || fallback` silently shows the key otherwise).
   - implicit-`t` check: any `.svelte` using `t(` must import it (compiles
     fine as implicit global; ReferenceError at runtime otherwise).

2. **Deterministic data tests** — `pixi run python
   scripts/tests/test_i18n_integrity.py` (pytest-compatible). Five classes:
   token leakage (`<|…|>`, assistant markers, md fences) across ALL stores
   (6 UI locales + 6 paper DBs + 6 content layers + en fallbacks), English
   echo (value == English, cognate allowlist), prettified-key garbage
   (value == key name), {n}/{c} placeholder drift, <br/> markup drift.
   Translation scripts MUST reject contaminated output at write time
   (`'<|' not in value`, echo-check) — see the accept filter pattern in
   scripts/i18n/llm_audit.py.

3. **LLM leak-audit** (renders pages, asks the model — catches what scanners
   can't see: script-block data, helper-produced labels, anything the
   heuristics threshold away):
   ```
   cd web && node ../scripts/i18n/render_pages.mjs http://localhost:5177 ko
   pixi run python scripts/i18n/llm_audit.py ko --passes 2
   ```
   Renders all 29 routes in a headless chromium (clicks the locale button,
   dumps innerText to /tmp/i18n_pages/<locale>/), then feeds each page to the
   LLM at temperature 0.05 with a strict find-English-leaks prompt (Latin
   names/gene symbols/brands exempted). Findings merged + deduped to
   _findings.json; `count` = found in N passes (2× = high confidence).
   Run per locale; expect brand-name false positives (GitHub, BLAST).

Known quirks that bit us (all now guarded):
- hash-only navigation does NOT reload the SPA — render/verify with a
  changed query string or full reload.
- Dev JSON staleness: i18n fetches use `cache:'reload'` + `?v=Date.now()`
  bust in dev. If a locale still shows old strings after hard refresh,
  navigate with any query-param change.
- Legacy-mode components (`export let`) don't track module-`$state` — the
  App.svelte route tree is keyed `{#key getLocale()+':'+i18nRev()}` so
  children remount on locale switch / translation load.
