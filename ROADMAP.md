# Roost Development Roadmap

This document tracks planned improvements and future work.

---

## Current State (2026-08-29)

### Data Acquisition
- **22 sources registered** in `scripts/sources.py`
- **Unified fetch framework** in `scripts/fetch.py`
- **Canonical schemas** in `scripts/schemas.py`
- Detection, tracking, genomics, surveillance categories

### Data Holdings (after deduplication)
- 20,669 detection records (296 species, 116 countries)
- 7,312 georeferenced events
- 1,979 species with genomes (3,845 assemblies)
- 81 species with phenotype data
- 127 high-confidence susceptibility predictions

### Analysis & Export Products
- Species profiles: 11,284 total, 290+ with detections
- Susceptibility scores: 290+ species (127 high-confidence)
- Species data sheets: per-species JSON files
- GeoJSON layers: detections, species, countries, hotspots
- Publication tables: guild, family, geographic, temporal summaries

### Website (Phase 5) ✅
- 9 routes, Svelte 5 + DuckDB-WASM + MapLibre, Playwright tests
- Build passing; code-splitting still to do

### Research Corpus (Phase 6) ✅
- 142 verified LLM analyses (7 steps each)
- 1,729 quantified findings, 648 novel claims, 135 contradictions
- Web integration: papers.json, genes.json, gene_citations.json, species_papers.json

---

## Phase 1: Data Quality ✅ COMPLETE

### Species Name Harmonization ✅
- [x] 313 common name → scientific name mappings
- [x] 20 taxonomic synonym mappings
- [x] Case normalization and fuzzy matching
- [x] Improved mapping from 74.5% → 78.8%

**Files:** `scripts/harmonize_species.py`

### Deduplication ✅
- [x] Removed known duplicate sources (github_usa, github_italy)
- [x] Quality-based near-duplicate removal
- [x] 51,298 → 20,477 records (removed 60% duplicates)
- [x] Backup preserved at `detections_merged_backup.parquet`

**Files:** `scripts/deduplicate.py`

### Coordinate Validation ✅
- [x] All coordinates within valid ranges
- [x] No suspicious zero coordinates
- [x] 39.9% coordinate coverage

**Files:** `scripts/validate_coordinates.py`

---

## Phase 2: Analysis Layer ✅ COMPLETE

### Species Profile Builder ✅
- [x] Unified profiles joining taxonomy + detections + genomes + phenotype
- [x] 11,284 total species, 328 with detections
- [x] 70 species with complete data
- [x] Data completeness scoring (0-100)

**Files:** `scripts/build_species_profiles.py`
**Output:** `data/species_profiles.parquet`

### Susceptibility Scoring ✅
- [x] Composite score: mortality + RIG-I + genome quality
- [x] 328 species scored, 127 high-confidence
- [x] Validated: Galliformes susceptible, Anseriformes tolerant

**Files:** `scripts/build_susceptibility_scores.py`
**Output:** `data/susceptibility_scores.parquet`

### Extended Analysis ✅
- [x] Family-level susceptibility patterns (50 families)
- [x] Ecological guild analysis (20 guilds)
- [x] Geographic hotspots (US, UK, France, Netherlands)
- [x] Temporal trends (winter peak)
- [x] Reservoir species identification

**Files:** `scripts/analyze_susceptibility.py`
**Output:** `data/analysis/` (publication-ready tables)

---

## Phase 3: Visualization & Export ✅ COMPLETE

### Summary Statistics ✅
- [x] Generate publication-ready summary tables
- [x] Create species-level data sheets (328 species)
- [x] Data quality metrics and reports

**Files:** `scripts/generate_summary_stats.py`, `scripts/generate_species_sheets.py`
**Output:** `data/summary/`, `data/species_sheets/`

### Geographic Visualization ✅
- [x] GeoJSON export for detection points (8,163 features)
- [x] Species centroids with susceptibility scores (230 species)
- [x] Country-level aggregates (46 countries)
- [x] Detection hotspots (1-degree grid)

**Files:** `scripts/export_geojson.py`
**Output:** `data/geojson/`

### Data Export ✅
- [x] Standard export formats (TSV, JSON, GeoJSON, Parquet)
- [ ] API for programmatic access (future)
- [ ] Integration with existing tools (Nextstrain, etc.)

---

## Phase 4: Additional Data Sources (Partial)

### Priority Downloads (No Registration)
- [x] UK DEFRA wild bird detections (2024-2026, 1,573 records)
- [x] Our World in Data H5N1 human cases (11,360 records)
- [x] Australia wild bird data (scraped → data/manual supplement, 205 records)
- [x] New Zealand detections + species (data/manual supplement, 3 records)
- [x] South Africa OCIMS seabird strandings (1,914 records, ArcGIS, incremental)
- [x] FAO Sub-Saharan Africa HPAI confirmed events (data/manual supplement, 20 records)
- [x] Manual supplements mechanism — data/manual/*.json are first-class pipeline inputs
- [x] WOAH WAHIS avian influenza events — public API discovered (no registration needed):
      ~2k events with per-species case/death totals; harvester + supplement builder wired into refresh
      (covers China, Russia, South America, Uganda — all WOAH members)
- [ ] USGS WHISPers API (US wildlife mortality events)
- [ ] Additional ArcGIS dashboards (EU countries - ECDC requires auth)
- [ ] NCBI Virus sequences for HPAI (avoided - 7MB+ JSON crashes)

### Requires Registration
- [ ] GISAID (23K isolates) - HIGH VALUE
- [ ] Dryad RLHA hawk tracking - HIGH VALUE
- [ ] Movebank Griffon Vulture outbreak
- [ ] WAHIS official notifications
- [ ] EFSA bulk surveillance data

### Future Integration
- [ ] Real-time APHIS updates
- [ ] Automated ArcGIS refresh (cron)
- [ ] GISAID sync (if registered)

---

## Phase 6: Research Corpus + LLM Analysis ✅ COMPLETE

- [x] PDF acquisition pipeline (PMC, batch, manual download lists)
- [x] PDF → markdown conversion (pymupdf4llm)
- [x] Dual-pass LLM extraction (Anthropic, temp 0.3 → 0.2)
- [x] 7-step schema: metadata, study, genes, species, mutations, findings, novelty
- [x] Verification workflow (142/142 verified)
- [x] Web integration (papers.json, genes.json, gene_citations.json, species_papers.json)
- [x] Analysis reports (papers_analysis_report.md, species_susceptibility_patterns.md)

**Files:** `scripts/papers/`

---

## Phase 7: Knowledge Synthesis — Wiki Pages 🔲 NEXT

Turn the LLM corpus into canonical, cross-linked knowledge pages.
Design doc: **`docs/PLAN_WIKI.md`**

### Entity canonicalization
- [x] Gene symbol normalization (427 raw → 75 canonical entities)
- [x] Species name normalization (684 raw → 177 entities, binomial extraction)
- [x] Mutation normalization (PROTEIN-POSREF→ALT form; 275 canonical)

### Build pipeline
- [x] `build_wiki_pages.py` → `web/public/data/wiki_*.json`
- [x] Gene pages (symbol, category, roles, findings, mutations, citations)
- [x] Mutation pages (protein, effect, papers, species context)
- [x] Species research synthesis (`wiki_species.json` + Research tab)
- [ ] Location/outbreak synthesis (from detection + paper geography)

### Web pages
- [x] Mutations route (#/mutations) with filter + detail
- [x] Genes page "From the literature" section (roles, key numbers, conclusions, species)
- [x] Species detail "Research" tab (conclusions, key numbers, study types, claims)
- [x] Cross-linking gene ↔ mutation (chips + deep links), search routing to all entities
- [x] Wiki index integrated into global SearchBar (⌘K)
- [ ] Paper deep links from citations
- [ ] Location/outbreak synthesis

---

## Automation (Phase 8) — Core Done ✅ / Extensions Pending

`pixi run refresh` runs the full cycle in one command (fetch → ArcGIS →
ingest → dedup → harmonize → profiles → susceptibility → geojson → web
export → gene data → wiki pages → web build → tests → freshness), logs to
`data/refresh_logs/`, and prints a before/after summary.

- [x] Orchestrator: `scripts/refresh_all.py` (+ `refresh-data` for data-only)
- [x] Guard: `export_web_data.py` no longer clobbers rich `genes.json`
- [x] Freshness alerts: `pixi run freshness` — content age per source
      (newest record in merged table) + fetch-pipeline health; exit 1 on stale.
      Found: CWHC dashboard stopped adding records 2026-03 (true positive)
- [x] Incremental fetch: conditional GET (ETag/304, checksum fallback) for
      direct downloads; date-filter + OID merge for ArcGIS (VS 174k rows:
      80s → 3s when unchanged); full snapshot every 7d as drift safety;
      ArcGIS query errors are loud (no silent "no new records")
- [ ] Manual-source reminders (GISAID, Dryad, Movebank logins)
- [ ] Auto-commit exports + deploy hook (Vercel/Netlify/GH Pages)
- [x] systemd user timer: `~/.config/systemd/user/roost-refresh.timer` runs
      `pixi run refresh-data` weekly (Mon 09:00, Persistent=true) — see
      `systemctl --user list-timers roost-refresh.timer`. APHIS mammals
      (direct CSV) and flocks (Tableau export via Playwright) are part of
      the auto-fetch set; GitHub Actions schedule still deferred

---

## Technical Debt

### Code Quality
- [ ] Add unit tests for ingestion scripts
- [ ] Add integration tests for full pipeline
- [ ] Type hints throughout
- [ ] Consistent error handling

### Documentation
- [ ] API documentation for schemas
- [ ] Data dictionary for all fields
- [ ] Ingestion pipeline diagram
- [ ] Contributing guide

### Infrastructure
- [ ] CI/CD for data validation
- [ ] Automated data freshness checks
- [ ] Backup and versioning strategy

---

## Schema Evolution

When adding new fields:
1. Add to `scripts/schemas.py`
2. Update relevant ingestion scripts
3. Re-run ingestion to populate
4. Update DATA_MANIFEST.md

When changing field types:
1. Create migration script
2. Update schemas
3. Re-process affected data
4. Document in CHANGELOG

---

## Contributing

To add a new data source:

1. Add entry to `scripts/sources.py`:
```python
register(DataSource(
    id="new_source",
    name="New Data Source",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://...",
    description="...",
    # ... other fields
))
```

2. Add field mapping to `scripts/schemas.py`:
```python
SOURCE_FIELD_MAPS["new_source"] = {
    "SourceColumn": "canonical_column",
    # ...
}
```

3. Test with: `pixi run fetch new_source --dry-run`

4. Update DATA_MANIFEST.md with source details
