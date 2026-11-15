# Roost Future Features

This document tracks planned future features for the Roost web application.
These items are beyond the current implementation scope but represent valuable enhancements.

## Shipped: Autonomous Research Agent Platform (2026-10-01)

A pi-like research agent platform — the LLM orchestrates its own investigation:

- **12 tools** (search corpus, citation chaining, field data, model, gene evidence,
  species traits, contradictions, disagreements, Wikipedia, web search, + more)
- **7 aliases** for LLM-invented tool names (self-correcting)
- **8 skills** (contradiction investigation, evidence synthesis, gene deep-dive,
  species comparison, gap assessment, hypothesis generation, outbreak investigation)
- **Self-assessment + refinement** (agent critiques own work, refines up to 3 rounds)
- **Meta-question classification** (belongs here vs own briefing)
- **Question scoring** (4,974 open questions ranked by importance/feasibility/data)
- **Autonomous mode** (agent picks its own questions to investigate)
- **Sub-briefing spawning** (child investigations from meta-questions)
- **Paper discovery** (web search results checked against corpus, novel papers logged)
- **Persistent call history** (every tool call in queryable parquet)
- **17+ research briefings** produced and live on the site

See `DATA_MANIFEST.md §10f` for the full architecture.

**Not yet built:** scheduled re-assessment when new papers arrive, multi-agent
collaboration, auto-intake of discovered papers.

## High Priority

### 1. Syntenic View of Immune Genes ✅ (2026-09-28)
Visualize genomic context and conservation of immune gene clusters across species.

**Shipped:** `#/synteny` explorer + gene-page "Genomic context" cards. Annotation
coordinates from the gene-presence build (117 species); blocks = recurring
co-located core gene-sets (STAT1–STAT4, TAP1–TAP2, RAG1–RAG2, IFITM cluster, …).
Named flanking genes from the current NCBI annotation (via the `datasets` CLI)
plus strand arrows ship for curated blocks / cached assemblies.
See `DATA_MANIFEST.md §7b`; regenerate with `scripts/genes/export_synteny.py`
followed by `scripts/genes/fetch_synteny_flanks.py`.

**Value:** Helps researchers understand genomic context affecting gene function.

### 2. Risk Prediction Map
Integrate GBIF species occurrence data for exposure modeling.

**Technical approach:**
- Fetch GBIF occurrence data for detected species
- Build species distribution models (SDMs) or use existing ones
- Overlay with surveillance data to identify high-risk areas with no detections
- Create heatmaps of potential exposure based on species ranges

**Value:** Predictive tool for prioritizing surveillance efforts.

### 3. Direct BLAST Integration ✅ (2026-09-28 — static, WASM)
Run sequence searches from the site, without any server.

**Shipped:** `#/blast` — protein search (BLOSUM62, affine gaps 11/1,
Karlin-Altschul E-values) against 2,990 reference proteins (799 genes ×
key species) via a Rust→WASM Smith-Waterman kernel (`web/wasm-blast`)
running in a web worker — nothing is uploaded, the page stays fully
static. Paste a sequence, get ranked hits with alignments linking to
gene/species pages. Nucleotide queries are out of scope (translate first).
Regenerate the DB: `scripts/genes/export_blast_refs.py`; rebuild the kernel:
`wasm-pack build --target web --release` in `web/wasm-blast`.

## Medium Priority

### 4. Gene Expression Browser
Tissue expression data from existing avian expression datasets.

**Technical approach:**
- Integrate data from GEO/ArrayExpress avian expression studies
- Build expression matrix for the 19-gene panel across tissues
- Visualize as heatmaps with species comparison
- Link to primary data sources

**Value:** Understanding tissue-specific expression helps explain susceptibility.

### 5. Species Comparison Tool ✅ (2026-09-28)
Side-by-side comparison of 2–5 species.

**Shipped:** `#/compare` — searchable multi-species picker (URL-synced `s=` param,
shareable links). Overview table (taxonomy, IUCN, detections, countries,
first/last detection, susceptibility, genome assembly level/N50, OrthoFinder
orthogroup counts) plus the gene presence matrix (46 curated panel genes by
default, all 811 searched genes on demand; “differences only” filter). CSV
export of everything. Entry point: “⚖ Compare” button on species pages.

### 6. Conservation Status Integration ✅ (2026-09-28)
IUCN Red List status for species.

**Shipped:** `scripts/species/fetch_iucn_status.py` pulls IUCN categories from
Wikidata P141 (open mirror; the official IUCN API needs a token) for 682/719
catalogue species. Badges render on species cards, the species modal, the
species full page, and search results; a "⚠ Threatened" filter (VU/EN/CR/EW/EX,
URL-synced `threat=1`) narrows any list view. See `DATA_MANIFEST.md §10a`.

### 7. Automated Data Updates
Weekly pipeline runs with change tracking.

**Status: partially in place.** `pixi run refresh` is the one-command cycle (fetch
automatic sources → ingest → dedup → profiles → web export, with a data-activity
event log feeding `#/history`); EMPRES-i is now fully automatic (FAO cloud
function, `scripts/fetch_empresi.py`). Still out of scope for now: scheduled
execution (cron/GitHub Actions), freshness alerts, and incremental fetch via
ETags — see refresh_all.py's automation roadmap.

## Structural Biology

### 8. Protein Structure Viewer ✅ (2026-09-28, verified)
Interactive 3D visualization of host factor proteins.

**Shipped (pre-existing, now verified end-to-end):** 3Dmol.js (CDN) via
`MolecularViewer.svelte` on gene pages — "3D Structure" card, open by default
when a structure exists, PDB fetched live from RCSB, cartoon style + controls,
structure selector with relevance notes (`gene_pdb_structures.json`: 15 genes
incl. ANP32A×polymerase 6XZR/6XZQ, MX1, DDX58, PB2/HA/NA). Headless render
verified (swiftshader): 1124×800 canvas painted, no page errors.
Remaining for #9: species-specific AlphaFold variants + superposition.

### 9. ANP32 Protein Comparison ✅ (2026-09-28)
Focused structural analysis of ANP32A/B/E across species.

**Shipped:** `#/anp32` (linked from ANP32A/B/E gene pages). The 33-aa insert is
measured directly from protein sequences — 463 birds (OrthoFinder OG MSAs)
vs every HPAI-confirmed mammal with a genome (NCBI datasets protein FASTAs)
against UniProt human references: anchored flanking-window span with NW
fallback; acidic-duplication gap runs merged. Per-paralog insert histograms,
insert sequence strip (ruddy duck lacks it), per-species table with IUCN
chips, and structures (AlphaFold human ANP32A with junction highlighted +
cryo-EM chicken ANP32A LCAR × polymerase 6XZR) via the 3Dmol viewer.
Regenerate: `scripts/genes/export_anp32_comparison.py` (see DATA_MANIFEST §10b).

### 10. Protein-Protein Docking Simulations
Model interactions between host factors and viral proteins.

**Technical approach:**
- Pre-compute docking models for key interactions:
  - ANP32A with influenza polymerase (PB2-PB1-PA complex)
  - MX1 with viral nucleoprotein
  - RIG-I/MDA5 with viral RNA
- Use HDOCK, ClusPro, or AlphaFold-Multimer for predictions
- Store results as PDB files for viewer
- Show binding energy estimates and interface residues
- Compare across species to predict adaptation potential

**Value:** Predicts which species may be susceptible based on molecular compatibility.

### 11. Variant Impact Prediction
Structural consequences of genetic variants in host factors.

**Technical approach:**
- Map known SNPs/variants from population genomics onto structures
- Use ESMFold or similar for rapid variant structure prediction
- Predict stability changes (ΔΔG) using FoldX or similar
- Highlight variants near functional sites
- Cross-reference with phenotype data where available

**Value:** Connects genomic variation to potential functional impact.

### 12. Immune Gene Structural Clustering
Phylogenetic analysis based on protein structure similarity.

**Technical approach:**
- Compute structure-based alignments (TM-align, Foldseek)
- Build structural phylogenies for each gene family
- Compare with sequence-based phylogenies
- Identify convergent evolution in immune function
- Visualize structural conservation across bird lineages

**Value:** Structure-based analysis may reveal functional relationships missed by sequence alone.

## Lower Priority

### 13. REST/GraphQL API
When data exceeds gigabytes or requires complex queries.

**Technical approach:**
- Build FastAPI backend with Parquet/DuckDB
- GraphQL layer for flexible queries
- Rate limiting and API keys
- OpenAPI documentation

**Value:** Enables programmatic access for power users and integrations.

### 14. Temporal Analysis & Animation
Outbreak spread animations over time.

**Technical approach:**
- Build time-series player for detection map
- Animate detection appearance chronologically
- Show spread patterns and velocity estimates
- Export as GIF/video

**Value:** Powerful for presentations and understanding outbreak dynamics.

### 15. Citation Export
BibTeX/RIS export for papers page.

**Technical approach:**
- Add export buttons for individual papers and filtered sets
- Generate properly formatted citation files
- Include DOI resolution
- Support multiple citation formats

**Value:** Streamlines reference management for researchers.

## Technical Debt & Infrastructure

### Performance Optimizations
- [ ] Implement virtual scrolling for large species lists
- [ ] Add service worker for offline support
- [ ] Optimize DuckDB queries with indexes
- [ ] Lazy-load non-critical components

### Accessibility
- [ ] Full keyboard navigation
- [ ] Screen reader support
- [ ] Color contrast improvements
- [ ] Focus indicators

### Testing
- [ ] Unit tests for utility functions
- [ ] Integration tests for data loading
- [ ] E2E tests for critical paths
- [ ] Visual regression tests

### Documentation
- [ ] API documentation for data files
- [ ] Contributing guide
- [ ] Data schema documentation
- [ ] Deployment guide

---

## Implementation Notes

### Data Dependencies
Several features require additional data sources:
- **Risk prediction:** GBIF occurrence data (~100MB compressed)
- **Expression:** GEO datasets (variable size)
- **Conservation:** IUCN API access (free registration)
- **BLAST:** Sequence database (~10GB for birds)
- **Protein structures:** AlphaFold DB (~50MB for 19-gene panel × key species)
- **Docking results:** Pre-computed PDB files (~100MB for key interactions)
- **Variant data:** dbSNP/population genomics (~variable)

### Infrastructure Requirements
- **Current:** Static hosting only (GitHub Pages, Netlify)
- **With API:** Server hosting (Fly.io, Railway, etc.)
- **With BLAST:** Compute resources for alignment
- **With docking:** GPU compute for AlphaFold-Multimer (can pre-compute)
- **With viewer:** WASM-compatible hosting (standard modern hosting works)

### Prioritization Criteria
1. User research impact
2. Technical feasibility with current stack
3. Data availability
4. Maintenance burden

---

*Last updated: 2026-08-26*

## Authors × keywords cloud (2026-10-05, requested)
- We already generate per-paper keywords (`data/papers/paper_keywords.parquet`,
  stated + generated, 10.9k rows / 1,015 papers) and hold full author rosters
  (`authors_full`, 98.6% coverage).
- Build an authors × keywords cloud on the Papers or Numbers page: authors as
  nodes sized by paper count, colored/clustered by their keyword footprint
  (e.g. Kuiken T → seabird/pathology; Fusaro A → phylogeography). Reuse
  author_network.json edges for layout. Suggested viz: beeswarm or
  force-graph with keyword facets as filters.

## Vaccine model overhaul (2026-10-08, deferred — user direction)
**UPDATE 2026-10-15 — DEEP OVERHAUL SHIPPED**: three layers live on
#/vaccines: (1) HISTORICAL — `scripts/model/build_vaccine_campaigns.py`
→ `vaccine_campaigns.json`: 28 quote-grounded real deployments
(vaccination_campaigns section) era-joined + region-bucketed, rendered by
CampaignPanels (era timeline w/ sector chips, region spans, filterable
ledger). Corpus yield for campaigns is genuinely ~28 (trial-heavy
literature; broadened repass +3 only — accept). (2) TARGETS — strategy
matrix (platform × sector × DIVA × species) in vaccine_outcomes + the
protection-gap join. (3) OUTCOMES — the outcomes ledger (shipped
2026-10-14). The curated model JSON stages remain as the pipeline frame.

**UPDATE 2026-10-14 — outcomes synthesis SHIPPED**:
`scripts/model/build_vaccine_outcomes.py` → `data/model/vaccine_outcomes.json`
+ web twin — 73 quote-grounded vaccination outcomes (56 worked / 8 partial /
5 failed / 4 unclear), 11 wild/captive/zoo programs (kākāpō, king penguin,
condor ×2, shy albatross), 283 platform claims (33 DIVA), protection-gap
join (8 vaccinated vs 28 susceptible-unvaccinated candidates). Rendered on
#/vaccines (OutcomesPanels.svelte). Rerun after extraction passes /
mine_vaccines runs / competence rebuilds. The full overhaul below remains
deferred.

Current v? is too simplistic (deterministic keyword-scan base + 283 mined
claims). When picked up, rebuild as a layered model in the SPREAD_MODEL.md
style:
- **Historical** — vaccination campaigns timeline (China, Indonesia, Egypt,
  Vietnam, EU shifts, wild-bird programs: condors, Northern bald ibis).
- **Targets** — which species/strategies (poultry routine vs emergency ring,
  DIVA, wild captive vs free-ranging), informed by host_competence gap matrix
  (which species need protection, where evidence is thin).
- **Applications & outcomes** — what has been done + effects: coverage→
  outbreak effects, escape/mismatch, trade bans, surveillance interference
  (DIVA), cost. Sources: `paper_spread.intervention_response` (vaccination
  rows, quote-grounded), `vaccine_claims.jsonl` (own miner, resume-safe),
  campaign Phase-D verification.
- New extraction sections follow the proven SECTIONS-dict pattern
  (`llm_extract_spread.py`); builder merges verified claims as today
  (deterministic base + verified rebadge).
- Eras linkage: campaigns × era windows (post-2017 China H5+H7, 2020s EU
  turnaround, 2024-25 cattle-response debates).
Infrastructure is ready (see AGENTS.md "Spread model v2"); no work needed
until picked up.
