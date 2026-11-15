# Roost Session Status (2026-08-29)

## Gene enrichment — paper IDs + profiles + frontend (2026-09-05, D92)

- **Phase 1 — Paper ID renaming**: 468 papers renamed from meaningless IDs
  (input_2024_154 → title-derived slugs like computational_host_range_2024).
  All referencing data files updated (gene_claims, connections, wiki, etc).
  Paper translation keys updated across all 6 locales. Backup +
  mapping preserved.
- **Phase 2 — Markdown artifacts**: 11 cleanups (**, *, backticks stripped
  from wiki data).
- **Phase 3 — Gene enrichment agent**: Pipeline approach (deterministic
  tool execution: gene info + paper search + read top 5 papers → single
  LLM synthesis). Transcripts recorded per gene. Rich profiles with
  overview, function, species differences, tiered findings (⭐ core /
  📊 mentioned/screen), strain interactions, cross-study patterns, and
  clinical relevance. Running for 291 literature genes (131 done, 45%).
- **Phase 4 — Frontend**: GeneProfile component on gene pages with
  two-tier findings (⭐ expanded / 📊 collapsed), species-difference panel,
  cross-study pattern badge, direction badges, paper citations.
  Translation infrastructure wired (hash-keyed profile text, gpt() helper,
  serve with _h hash fields). Profile translations running alongside.
- All suites green throughout.

## Clade discovery lane (2026-09-05, D91)

`scripts/papers/clade_discovery.py` — continuously detect and classify
genotype/clade/subtype designations in the corpus:

- Broad scan (explicit "genotype X"/"clade X" + numeric clade notation
  requiring "clade" context + subtypes + PB2/HA/NA mutations)
- Persistent registry: 189 designations (39 clades, 55 genotypes, 59
  subtypes, 29 mutations); Muse LLM verified 91 novel, rejected 19 false
  positives; 52 low-count awaiting verification
- Notable verified: H1N1 (377 papers), H3N2 (215), H7N7 (104), clade 2.2
  (68), H5N3 (71), clade 2.1 (12), 2.1.3.2 (10), novel PB2 mutations
- Wired into `campaign.py connections` phase — runs every pipeline wave
- LLM provenance tracked

## Topic assignment + strain tagging + LLM provenance (2026-09-05, D90)

- **Topic gap fixed**: 554/1206 papers (46%) had no topics — merged-batch
  heuristic hadn't fired. New `assign_topics.py`: deterministic pass
  (vaccine detection from title/summary/MD; strain topics from text scan)
  + Muse LLM pass (654 sparse papers → 312 LLM-assigned; controlled
  vocabulary of ~80 topics + strain tags). Final: **2 papers with no
  topics** (from 554); 195 vaccine-tagged (was 0 with the "Vaccines"
  label); **639 strain-tagged** (was 73); 262 distinct topics (was 227).
- **Strain topics now dominate correctly**: Clade 2.3.4.4 (552 papers),
  2.3.4.4b (523), H5N8 (186), H5N6 (114), Genotype D1.1, B3.13 etc.
- **LLM provenance tracking** (`llm_provenance.py` +
  `data/papers/llm_provenance.json`): every LLM extraction pass now
  records task, model, prompt version, timestamp, affected count, notes.
  Wired into connections.py (classify/review-auto/appeal), campaign.py
  (summaries/gene-claims), model_r3.py, assign_topics.py,
  build_wiki_pages.py. CLI: `llm_provenance.py --summary`.
- Topic translations refreshed across all locales; build + full
  Playwright suite green.

## Strain dimension + novel-strain detection (2026-09-05, D89)

User question: strain x species x gene interactions (e.g. duck-lethal vs
duck-benign strains) and novel-strain risk. Findings & additions:

- **Mammal coverage is strong**: 904/959 papers mention mammals; gene
  evidence: Human 62, Mouse 54, Ferret 10, Swine 8, Cattle 2 genes.
- **Strain x gene existed partially** (461 protein mutations tracked:
  PB2-E627K x92 papers, D701N x68); **strain x species x gene was the gap**.
- New `scripts/papers/strain_scan.py`: deterministic registry scan (clades,
  D1.x/B3.x/A3/G5 genotypes, subtypes, PB2 signature mutations) over 959
  papers → 858 papers strain-tagged, 21 strains, 2,256 strain x species x
  gene co-occurrence triples (review signals, not published claims) +
  **novel genotype token detection** (unregistered "genotype X"/"clade X"
  tokens flagged: B3.1 x353, B3.3, A1, SA1, EA2 …) for the review queue.
- Post-hoc join enriched 225/636 candidates with strain context; published
  evidence now carries `strain` (99/323 records) — duck x strain x gene
  queries are answerable from the published data.
- Future mining runs should extract strain in the Muse context (alongside
  species/timepoints) so new evidence carries it natively.

## Wave 2 full LLM mining run (2026-09-05, D88)

Second complete cycle over the enlarged corpus: source search (157 recent
candidates → gate accepted 20), snowball over the 511 new seeds (0 new —
the newly merged papers' citations largely re-discover already-held work:
the citation neighborhood is saturating, as expected). Corpus: 1186 →
**1206 papers**; 959 text-minable. Mining: +2 approvals through the
quote-grounded gate (183 published edges / 323 evidence records); appeal
upheld all wave-2 rejections. Wiki, translations, build, Playwright 27/27,
pytest 46/46 all green.

## First full intake cycle: +491 papers through the automated gate (2026-09-05, D87)

- **Citation snowball (571 seeds) → 597 candidates**; automated merge review
  via muse-glimmer (`auto_merge_review.py`): Q1 relevance (verified verbatim
  title-quote + one re-quote retry), Q2 source type, Q3 scope; deterministic
  duplicate removal (title-similarity >= 0.8; the LLM duplicate question was
  removed after it hallucinated self-duplicates). 507 accepted → 491 merged
  (16 dups), 106 rejected with logged reasons. Corpus: 695 → **1186 papers**.
- **Downstream chain ran end-to-end**: preflight recovered +278 OA texts
  (957 ready / 227 missing_source); summaries via Muse; search +236 windows
  (+153 eligible); classify +14 mechanistic candidates (636 total; all
  quote-grounded, auto-reviewed + appealed); export → 182 edges / 321
  evidence; literature panel 289 → **291 genes** (self-maintaining scope
  worked); wiki + all six translation locales refreshed to the new corpus.
- All suites green: build ✓, Playwright 27/27, pytest 46/46.

## Source expansion: EuropePMC + OpenAlex + medRxiv + citation snowball (2026-09-05, D86)

- `search_papers.py` now searches six sources: PubMed, PMC, bioRxiv,
  medRxiv, **EuropePMC** (superset incl. Agricola + regional vet journals;
  note: use FIRST_PDATE facet — PUB_DATE returns 0 hits), and **OpenAlex**
  (worldwide works incl. non-English vet journals, with OA flags). Live
  90-day test: EuropePMC 157 + OpenAlex 266 new candidates after dedup.
- New `scripts/papers/snowball.py`: citation mining over the 571 held
  papers with PMCID/DOI via EuropePMC CITES: / OpenAlex cites:, relevance-
  filtered (H5N1/HPAI titles), deduped, `via:`-attributed, resume-safe.
  25-seed test: 14 on-topic candidates (e.g. bovine H5N1 mammary-gland
  tropism citing our Wisconsin cattle paper). Full run in background.
- All output flows into the standard `new_papers.json` →
  `merge_papers.py --review` gate — nothing enters the corpus unreviewed.

## Literature-first panel doctrine (2026-09-04, D85)

User direction: genes should come OUT of the literature as relevant, not in
from annotation. Implemented as an `evidence_scope` split in
gene_presence.json (derived in export_presence.py from panel sources + corpus
search status):

- **literature (289 panel genes)**: corpus evidence or curated/wiki/discovery
  origin — the default panel everywhere
- **annotation (303 panel genes)**: UniProt GO-backbone with no H5N1 corpus
  mentions — context, not evidence:
  - Genes page defaults to the literature panel (505 records incl. wiki-only
    genes); "+ annotation-only · 303" toggle reveals the rest
  - Annotation gene pages carry a "genome annotation — not yet discussed in
    the H5N1 corpus" badge
  - ModelCyto extended panel excludes annotation genes (graph 315 → 234
    genes; the unclassified evidence-gap bucket now reflects literature
    genes only)
- FTH rescued via FTH1 alias (only genuine body-text rescue found while
  probing no-hit genes — family-phrase matches were rejected as inference).
- All suites green after the change (build, Playwright 27/27, pytest 46/46).

## Host-association layer (2026-09-04, D84)

`scripts/genes/build_host_association.py` — deterministic per-gene host-class
annotations (aves / mammalia / both / other / none / viral) derived from wiki
host flags, species-studied lists, mined evidence species, and gene-claims
roles; alias spellings fold to canonical symbols (RIGI→DDX58 fixed a
duplicate-record overwrite). Output: gene_host_association.json (807 genes;
panel breakdown: 80 both, 66 aves, 78 mammalia, 32 other, rest no host
evidence — mostly the no-corpus-hit genes).

Surfaced:
- Gene cards: host-class chip with evidence-record counts (host-class-chip)
- Gene full pages: host association line (class + bird/mammal record counts
  + studied-in species list)
- ModelCyto: "Host evidence" lens (all / birds / mammals / both) dims genes
  lacking the selected host evidence (193/315 dim under 'aves'; both-class
  genes like DDX58 stay lit)

All suites green (build, Playwright 27/27, pytest 46/46).

## i18n hardening: raw-key fix + quote policy + full wiring (2026-09-04, D83)

- **Raw i18n keys (e.g. `lib_components_genes_GeneFullPage.description`,
  `lib_components_common_Footer.roost`) fixed**: es/ko store bundles were
  missing 190/192 UI keys (wrong key scheme copied into _i18n), and 70 keys
  had lost their English fallback (stale final_extract.json). English was
  reconstructed (extraction union + de-slugging wire-key names), 190 keys
  translated for es+ko, fallbacks refreshed for every locale. Live probe:
  zero raw keys in es/ko/zh; footer renders properly.
- **Evidence-quote policy**: quotes stay VERBATIM in the original language
  (tooltip shows original, with translation appended after an em-dash);
  the text around them localizes via a new `vocab` translation field
  (60 strings: mechanism labels, species, evidence types, stage labels ×
  6 languages) through a new vt() store helper.
- **topics / findings / conclusions / roles fully wired**: wiki_genes.json
  now carries content-hash (fh) keys on roles (377 genes) and conclusions
  (187) — matching the existing translation files — so ft() localizes them
  everywhere (verified live in Korean); paper-detail topic chips use
  ptopic().
- Fixed build_wiki_pages crash (hashlib was function-local); caught a
  masked pipeline failure (`cmd | tail` hides exit codes).
- All suites green: build ✓, Playwright 27/27, pytest 46/46; translation
  coverage 100% across all fields × 6 locales.

## Unclassified-gene placement + es/ko locales (2026-09-04, D82)

- **Papers-page i18n bug fixed**: loadLocale() never fetched
  data/i18n/papers/{lang}.json, so paper titles/summaries stayed English.
  Now loaded per locale (verified live in zh); evidence quotes localize on
  gene pages via new quote_h keys + et() helper.
- **es (Español) + ko (한국어) COMPLETE** — locale selector + every
  translation pipeline at 100%: UI strings 503/503 each (i18n_translate
  made incremental so batch failures never lose coverage; stubborn strings
  finished via single-item plain-prompt pass), deep content, and all paper
  data (695 papers, 252 topics, 266 findings, 142 conclusions, 1266 roles,
  260 evidence quotes). Verified live: papers page renders in Spanish and
  Korean. Six locales total: en/zh/hi/ja/fr/es/ko.
- **Stage placement for hit-but-unclassified genes**
  (`scripts/model/place_unclassified.py`): the 77 panel genes with corpus
  hits but no stage got a quote-grounded proposer + skeptic pass. Only 2
  placements survived double-confirmation (PTPRC→adaptive, BTN3A3→
  effectors); 66 honestly "insufficient" (mention-only in the corpus).
  220 no-hit genes stay unplaced by design — no evidence, no placement.
- **Graph placement final: 294/592 genes** (52 model, 215 keyword, 19
  claims-llm, 4 r3 overrides, 2 reviewed, 2 contextual) + 181 relationship
  edges. assign_stages gained contextual_pass (fills only 'none' genes).
- Tests: 46 Python (contextual-pass suite added); build + 27/27 Playwright.

## Pathway improvement R3 + evidence translations (2026-09-04, D81)

- **`scripts/model/model_r3.py`** — pathway improvement grounded in the 141
  approved relationships: per-stage proposer (may only cite verbatim quotes
  from the mined evidence; may only add genes from the reviewed-connection
  candidate pool) + per-proposal skeptic double-check. 37 proposals →
  22 double-confirmed (all gene adds without quotable stage evidence were
  denied — e.g. CIITA, IL18). Report: data/model/r3_proposals.md with
  ✅/❌ per proposal, quotes, and gaps per stage.
- **`scripts/model/apply_r3_confirmed.py --apply`** — wrote the 4
  double-confirmed gene additions through the explicit-review path
  (gene_overrides.json): RNF135→hostrange (sensing alternative noted;
  rationale: RIG-I accessory co-lost in chickens), TBK1/IRF9/IFNAR1→
  signaling. assign_stages override_pass applied them; the Cytoscape graph
  shows them in their stage buckets (extended panel). Fully reversible.
- **Evidence translations COMPLETE** — translate_papers.py extended with
  an `evidence` field: all 260 distinct public reviewed quotes are
  content-hash-keyed translation targets alongside findings/roles/
  conclusions. Final coverage — all four languages at 100%: zh/hi/ja/fr ×
  (695 papers, 252 topics, 266 findings, 142 conclusions, 1266 roles,
  260 evidence quotes). A handful of JSON-fragile quotes needed a plain
  (non-batch) prompt fallback.
- Production build + Playwright 27/27 after the stage changes.

## Appeal pass: deeper investigation of rejections (2026-09-04, D80)

`connections.py review appeal` — two-prompt re-examination of all 299
muse-rejected candidates with MORE context than the first reviewer had:

- **Stage 1 (investigator)**: full source passage (not just the original
  quote) + the recorded rejection reason + a declared nomenclature-equivalence
  list (RIG-I=DDX58, PKR=EIF2AK2, FluPol/polymerase↔PB2 only when tied to the
  subunit, "interacts with"=binding only for direct molecular interactions).
  Overturns require a NEW verbatim quote from the passage — verified
  programmatically; unquotable proposals downgrade to uncertain.
- **Stage 2 (skeptic)**: every overturn re-checked against its single quoted
  sentence; confirm requires the sentence itself to state mechanism+direction.
- **Outcome**: 55 overturn proposals → 34 double-confirmed approvals
  (reviewer: muse-appeal), 21 skeptic denials, 245 upheld, 3 uncertain.
  Full two-stage audit in data/papers/connections/appeals.jsonl.
- **Net state**: 319 approved / 265 rejected / 38 pending-for-human;
  published 181 edges (141 with reviewed evidence, 319 quote-cited
  records); wiki/search/counts/stages refreshed; production build +
  27/27 Playwright + 44 Python tests green (6 new appeal-rail tests).

## Muse first-pass review of mined connections (2026-09-04, D79)

`connections.py review auto` — muse-glimmer-30b as a cautious first-pass
reviewer over all 271 proposed relationships (temp 0.1, 32k tokens):

- **Anti-hallucination rails**: reviewer sees only the verified evidence pack;
  every approve/reject must carry a quote copied verbatim from it — a quote
  that does not match downgrades the verdict to *uncertain* (stays pending).
  The prompt forbids outside-knowledge approvals and invented papers/genes.
- **Outcome**: 285 approved / 299 rejected / 38 pending (uncertain or
  malformed — reserved for human review). Decisions carry
  `reviewer: "muse"` provenance; human decisions always win; `review reset`
  undoes any of them; reruns skip decided groups.
- **Published after review** (`connections.py export`): 166 edges
  (40 curated-only, 126 with reviewed evidence, 285 quote-cited evidence
  records, public quotes ≤300 chars); 77 genes with reviewed connections;
  2 previously-unclassified genes classified via reviewed stage proposals;
  location overlay for 33 genes; wiki/search/counts refreshed.
  Top approved: NS1⊣DDX58 (15 evidence), NLRP3→IL18 (13), TBK1→IRF3 (13),
  TRIM25→IRF7 (9), JAK1→STAT1 (7).
- 6 reviewer-layer tests added (quote enforcement, human precedence, resume);
  38 Python tests and the 27-test Playwright suite green on the live
  approved data (STAT1 fan-out gained the reviewed STAT1→CIITA edge).

## Corpus Mining & Connection Review (2026-09-04, D75–D78)

Full corpus-mining and review pipeline landed (see `.ralph/corpus-connections.md`
for the complete verification log):

- **Corpus preflight** (`scripts/papers/corpus_preflight.py`, `campaign.py
  preflight`): lawful OA recovery via EuropePMC fullTextXML + JATS→Markdown
  converter; 679/695 papers ready (6 recovered, incl. one junk bot-block PDF
  detected and replaced); explicit missing_source records for the 14 lawfully
  unobtainable; missing text is never negative evidence.
- **Connection miner** (`scripts/papers/connections.py`, `campaign.py
  connections`): boundary-aware `rg --json` search (592-gene status records:
  288 hit / 299 no_hit / 5 unsearchable), paragraph±1 windows with overlap
  dedupe, dictionary-gated exact-case matching (KIT/STING vs mTOR/cGAS);
  Muse classification of ALL 5406 eligible gene-paper windows (2635 contextual
  / 622 grounded mechanistic candidates / 1786 no_relation / 355 quarantined);
  alias-normalised grounding (verbatim quotes, canonical endpoints, mechanism
  whitelist); stable IDs; resume-safe (tunnel drop → exit 2, findings pending).
- **Review gate**: internal `review_report.md` grouped by proposed
  relationship (271 relationships, 69 with ≥2 independent papers; top:
  NLRP3→IL18 ×10, NS1→DDX58 ×10, PB2→ANP32A ×9); `connections.py review
  approve|reject|reset` CLI + hand-editable `review_decisions.json`.
  ALL 622 candidates remain pending — nothing publishes without approval.
- **Publishing + downstream**: `gene_relationships.json` (52 legacy-curated
  edges + approved-only evidence, quotes ≤300 chars); Cytoscape reads the
  published file (no more inline edge arrays) with neutral top-level nodes
  and extended-panel gating for reviewed-only genes; enriched edge tooltips;
  species-selector evidence styling (highlight/neutral/dim); gene cards,
  gene pages (relationship sections, View-in-pathway deep links), wiki
  exports, search index, evidence counts, stage proposals (classify-only)
  and location overlays all consume approved data; non-panel counterparts →
  discovery queue.
- **Tests**: 32 Python (corpus + alias/mining/review suites — they caught a
  real export provenance bug) + 27 Playwright (19 existing incl. updated
  graph assertions, 8 new connection acceptance tests via route
  interception).

## APHIS Full-Suite Integration (2026-09-02)

Added the two missing APHIS datasets and fixed a serious pre-existing dedup bug:

- **APHIS Mammals** (`hpai-mammals.csv`): plain direct download behind the
  mammals Drupal page (`data-csv-url`). 824 animals / 612 events, 45 species
  mapped via extended `MAMMAL_ALIASES`. "(captive)" → sampling method.
- **APHIS Commercial & Backyard Flocks**: no static CSV exists — reverse-
  engineered the Tableau dashboard (workbook `VS_Avian_HPAIConfirmedDetections2022`,
  hidden `ExportToCsv` sheet, toolbar → Download → Crosstab → CSV).
  `scripts/fetch_aphis_flocks.py` (Playwright) exports + normalizes the UTF-16
  tab-delimited file whose final column (birds affected) has no header.
  2,243 premises / 208.3M birds affected 2022–2026; new `SCRAPE` access method
  in fetch.py routes it like any other source.
- **Wild birds page**: its CSV export is the same `hpai-wild-birds.csv` we
  already fetched — no change needed.
- **Species numbers now match affected animals**: `detection_count` sums
  (birds affected / case counts) instead of record counts in species profiles.
  Chicken 179.8M, turkey 22.6M, mallard 2.2M (domestic ducks fold into
  *Anas platyrhynchos*; `species_raw` keeps the production label).
- **Dedup null-key bug (pre-existing, serious)**: `pl.concat_str` propagated
  nulls, so records with unmapped species or unparseable dates shared a single
  null dedup key — 9,401 vs_surveillance records were silently reduced to 0,
  plus chunks of sdm_hpai/oafd. Key is now fully null-safe and includes
  lowercased `species_raw` + `record_ref` (flock Special IDs, mammal event ids).
- Flocks production types → domestic species map (chicken/turkey/duck);
  backyard/mixed premises stay unmapped by design. Side table:
  `data/aphis_flocks.parquet`. Wiki mutation pages now restricted to the known
  gene universe (kills primer-artifact pages like HA3F/SMA3F).

| Metric | Before | After |
|--------|--------|-------|
| Detections | 26,367 | **34,283** |
| Species | 525 | **657** |
| Countries | 102 | **106** |
| Georeferenced | 11,629 | **13,483** |
| Sources | 19 | **21** |

All wired into `pixi run refresh` (AUTO_SOURCES + fetch routing) and the
freshness checker (aphis_mammals 35d, aphis_flocks 28d thresholds).

## Project Overview
Roost is an Avian Influenza Host Genomics Resource — a "Wikipedia for bird flu" combining
detection records, genomic data, susceptibility analysis, and an LLM-analyzed research corpus,
served through an interactive website.

## Completed Phases

### Phase 1: Data Quality ✅
- Species harmonization via NCBI taxonomy
- Deduplication (52,794 → 19,206 records)
- Coordinate validation (all valid)

### Phase 2: Analysis Layer ✅
- Species profiles (11,284 species, 290+ with detections)
- Susceptibility scoring (RIG-I pathway + mortality rates)
- Extended analysis (guild, family, geographic, temporal patterns)

### Phase 3: Visualization & Export ✅
- GeoJSON export (detections, species, countries, hotspots)
- Species data sheets (per-species JSON)
- Summary statistics (publication-ready tables)

### Phase 4: Additional Data Sources ✅
- UK DEFRA/APHA 2024–2026 wild bird data (1,573 records, 89 species)
- Our World in Data H5N1 human cases (11,360 records)
- Refreshed existing sources (APHIS +6 records)
- Australia (scraped), New Zealand additions

### Phase 5: Website ✅
- Svelte 5 + Vite + Tailwind 4 + DuckDB-WASM + MapLibre GL
- 9 routes: Home, Species, Genomes, Genes, Map, Phylogeny, Papers, Downloads, Resources
- Species detail modal (overview / detections / genome / genes tabs)
- Hash-based router, client-side DuckDB queries over parquet, search index
- Playwright page-loading tests for all 9 pages
- Build passing (1.3 MB JS bundle — code-splitting pending)

### Phase 6: Research Corpus + LLM Analysis ✅
- 144 PDFs → 143 markdown papers in `docs/`
- 142 dual-pass LLM analyses (Anthropic, temp 0.3 → 0.2), all steps verified
- 7 extraction steps per paper: metadata, study, genes, species, mutations,
  findings (quantified), novelty (claims / limitations / contradictions)
- Aggregates: 1,729 quantified findings, 648 novel claims, 135 contradictions,
  ~400 unique mutations, 427 raw gene names, 684 raw species names
- Web data: `papers.json` (114 indexed), `genes.json`, `gene_citations.json`,
  `species_papers.json` (26 species ↔ 57 papers), `gene_trends.json`
- Reports: `docs/papers_analysis_report.md`, `docs/species_susceptibility_patterns.md`

## Current Data Holdings
- 20,669 detection records (296 species, 116 countries, 7,312 georeferenced)
- 52,794 raw records from 12+ sources before dedup
- 1,979 species with genomes (3,845 assemblies, 652 chromosome-level)
- 81 species with phenotype data
- 127 high-confidence susceptibility predictions
- 142 verified LLM paper analyses

## Pipeline Commands (pixi)
```bash
pixi run fetch              # Download data
pixi run ingest-detections  # Merge all detection sources
pixi run deduplicate        # Remove duplicates
pixi run build-profiles     # Build species profiles
pixi run susceptibility     # Calculate scores
pixi run analyze            # Extended analysis
pixi run export-geojson     # GeoJSON layers
pixi run species-sheets     # Species data sheets
pixi run summary-stats      # Summary statistics
pixi run analyze-papers-llm # LLM paper analysis (dual-pass)
```

Web pipeline (not in pixi yet):
```bash
python scripts/export_web_data.py
python scripts/papers/build_paper_index.py
python scripts/papers/build_gene_data.py
python scripts/papers/build_species_data.py
python scripts/papers/build_wiki_pages.py   # Phase 7 — see docs/PLAN_WIKI.md
cd web && npm run build
```

## In Progress (uncommitted work)
- `scripts/papers/analyze_paper.py`, `build_gene_data.py` — richer gene metadata
  (importance scores, evidence types, PDB structures)
- Web: SpeciesDetail modal enhancements, Genes page literature section,
  SearchBar / search store / format utils improvements

## Next: Phase 7 — Knowledge Synthesis
Turn the LLM extraction corpus into wiki-style pages for genes, species,
mutations, and locations. Design in `docs/PLAN_WIKI.md`.

## WOAH WAHIS Integration (2026-08-30) — the big one

Reverse-engineered the WAHIS public API (no registration needed) and harvested
**1,970 avian influenza events** — official notifications with per-species
case/death totals, wild/domestic flags, outbreak coordinates, lab results.
Supplement: 4,415+ records, 85% species-mapped, 101 countries.

| Region | Before | After |
|--------|--------|-------|
| Detections (all) | 20,923 | **24,696** |
| Species | 334 | **485** |
| Countries | 119 | **143** |
| Georeferenced | 7,490 | **11,263** |
| South America | 0 | **156** (Chile/Peru/Brazil/Argentina/Colombia) |
| Russia | 36 | **104** |
| China | 19 | **42** |

Plus this session: country-code harmonization to ISO3 (Canada's 908 and UK's
2,834 records were invisible under mixed 'Canada'/'CAN', 'UK'/'United Kingdom'
labels; pseudo-country count 146 → 102 real), USGS WHISPers lab-confirmed
mortality events (1,301 records, 48 states), species mapping 85% → 97% via
shared alias module, paper deep-links (#/papers/{id} focused view) wired
into every citation chip.

## Data Refresh (2026-08-30)
Ran the first full refresh via `pixi run refresh` (new orchestrator):

| Metric | Before (Aug 26) | After (Aug 29) | Final (Aug 30, +Africa/NZ/AUS) |
|--------|-----------------|----------------|-------------------------------|
| Detections | 20,669 | 20,670 | **20,868** |
| Detected species | 296 | 308 | **328** |
| Countries | 116 | 116 | **118** |
| Georeferenced | 7,312 | 7,312 | **7,490** |
| Genomes | 3,845 | 3,851 | 3,851 |

New sources (2026-08-30): South Africa OCIMS seabird strandings (1,914
ArcGIS records, incremental), FAO Sub-Saharan Africa HPAI confirmed events
(20 records/5 countries). Fixed: manual additions (NZ/AUS) had been silently
wiped by pipeline rebuilds — now durable via `data/manual/` supplements loaded
as a first-class source by ingest; ArcGIS pagination no longer stops early on
services that cap pages at 1,000 records.

## Key-Numbers Quality & Paper-ID Fixes (2026-08-31)

**Problem**: wiki key numbers included methods/QC metrics (alignment rates,
paired-end reads per sample, QC bounds) alongside infection findings; one
paper's LLM extraction produced markdown-table dumps as gene roles
("3L2 CXCLi1 CXCR4 … log2 fold c") with a dead `paper_2024` id.

**Fixes**:
- `scripts/papers/fix_analysis_ids.py` — renamed 1,372 analysis files
  (llm_analyses/analyses/internal) to title-slug ids + updated internal
  paper_id; quarantined 118 orphaned analyses (papers no longer in corpus).
  Wiki citations now carry real titles/years/journals and working links.
- `scripts/papers/classify_findings.py` — categorises every finding as
  `infection` (default) or `methods` (alignment/mapping rate, reads/sample,
  QC thresholds, aligner configs — 45 tagged); drops garbage extractions
  (markdown table dumps, truncated fragments — 7 findings, 5 roles blanked).
  Covered by `scripts/tests/test_classify_findings.py` (19 tests).
- `build_wiki_pages.py` — `key_findings` now infection-only;
  `methods_findings` (capped 3) kept visible in a collapsed
  "Sequencing & methods" section for readers who want the technical picture.
- `llm_analyze_papers.py` findings prompt now requires a `category` per
  finding and forbids truncated table dumps / gene-list captions.
- Frontend (SpeciesDetail, GeneFullPage): key numbers show infection
  findings; methods/QC findings in a collapsed `<details>`; species findings
  now wired through `ft()` for locale translation.

## Panel Presence Campaign Complete (2026-09-07)

Full chain green end-to-end:

- **LLM repair**: 143/143 papers with broken extraction steps repaired by
  qwen3.8-27b (48 workers, thinking disabled — reasoning was eating the
  completion budget, the original failure cause). 0 broken steps across all
  664 analyses. Wiki evidence now 3.7k proper genes-step rows vs 275
  discovery-log fallbacks.
- **Presence search** (verso `gene_panel_presence`, 10/10 nodes): 817 genes
  × 15 species = 12,255 calls; chicken 813 FULL, duck s=0.75, kiwi
  assemblies s=0.5–0.75 with searchability recorded per call. 482
  reference-less symbols quarantined as the blocked backlog (§12.6).
- **Deliverables**: `data/genes/exports/gene_presence_calls.{json,tsv}` +
  `presence_summary.json` — flat, import-ready; regenerated via verso
  (cache-hit re-runs take seconds).
- **STING unification**: legacy STING→STING1 redirect had forked the gene
  (3 wiki pages + duplicate 15-species searches). One entry now (25 papers);
  81/81 tests.
- Wiki: 919 genes (906 host). Catalogue: 422 literature / 389 annotation,
  wiki-canonical both directions.

## Panel Intake Method Formalized (2026-08-31)

`docs/GENE_PANEL.md` §12 now formally specifies the gene-panel discovery &
intake method (machinery deliberately deferred):

- **§0 Panel definition** — grounded on the live `#/genes` universe: 804
  merged genes (18 curated + 352 wiki-only + 434 panel-only), of which
  **488 literature-scope host genes** (16 curated host ∪ 351 wiki host ∪
  291 presence-literature), 301 annotation-only, 13 viral.
- **Collision-first intake** (§12.4): panel collision (canonical-ID incl.
  aliases) → search collision (presence_v2 already searched — never
  re-search) → annotation collision (UniProt backbone; elevation via corpus
  evidence) → evidence-gated new candidate (≥2 papers or central role).
- **Search rules** (§12.6) restate the evidence ladder and searchability
  gates; queued genes need reference sequences.
- **§12.7** fixes the output contract (`panel_intake_report.json`,
  `diamond_search_queue.json`, future `scripts/genes/panel_intake.py`).

## Per-Paper DEG Summaries (2026-08-31)

DEG lists/counts are properties of a paper's experiment, not of each gene.
`scripts/papers/build_deg_summaries.py` derives per-paper summaries from
llm_analyses (no LLM run needed): quantified DEG-count findings (infection
category only; FDR/selection-criteria findings excluded as methods) + top
expressed genes (expression-change roles, symbols validated against the gene
catalogue — no antibodies, parentheticals, or comma lists). 116 papers covered.

Papers page focus panel now shows a "Differential expression (this paper)"
section: count chips (e.g. "3,101 — DEGs in DK/49-infected ducks vs control")
plus gene chips linking to gene pages. Gene pages keep only quantified
per-gene findings (fold changes, titres) via the infection/methods split.

Classifier tightened: "identification/selection criteria", significance
thresholds, and cut-offs now classify as methods (94 tagged, up from 45);
re-runs always re-classify.

## Known Issues
- Gene/species/mutation names from LLM extraction need canonicalization
  ("NP (NUCLEOPROTEIN)" ≡ "NP"; "PB2 M631L" ≡ "PB2-M631L")
- NCBI Virus queries return massive JSON (7MB+) — avoided
- USGS Izembek sampling.csv is corrupted (HTML instead of CSV)
- JS bundle > 500 kB; code-splitting (lazy DuckDB/maplibre) recommended

## Notes
- All pipeline output in `data/`; web-exported data in `web/public/data/`
- Papers markdown (`docs/papers_md/`) and PDFs (`docs/papers_pdfs/`) are
  untracked in git — decide on policy (size/licensing) before committing
