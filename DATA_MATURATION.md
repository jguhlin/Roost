# Data Maturation Plan

> Keeping the website's interior database(s) **lean** — one authoritative copy of
> each fact, everything else derived — because the real cost of duplication is
> **drift**: copies that silently disagree with each other.

**Created:** 2026-09-11, from a full duplication audit of `web/public/data/`
(the shipped interior DB, ~103 MB) against the canonical `data/` store.
**Status:** COMPLETE — all six phases ✅ (2026-09-11).

**Final scoreboard:** web/public/data 103 → 78 MB · presence cluster
~62 MB → 0.4 MB (3 files, one writer each) · genome staging 11.6 → 4.3 GB
· dist 27 GB (stale) → 93 MB (fresh, lean) · interior −24 MB mirrors ·
7 latent bugs fixed (index wipes ×2, susceptibility Binder Error, wiki 404,
dead map filter, mentions-as-papers, broken pipeline reads ×2) · e2e suite
27 → 31 tests, all green.

Companion docs: `DATA_MANIFEST.md` (sources & pipelines), `DATA_INVENTORY.md`.

---

## Principles

1. **One source of truth per fact.** Parquet tables for tabular data
   (DuckDB-WASM already ships); JSON only for document-shaped content
   (papers, wiki text, gene profiles, i18n, models).
2. **Derive, don't copy.** If a file can be computed from another shipped file
   (`GROUP BY`, count, join, subset), it should not exist as a static file.
3. **No pipeline intermediates in production.** Working files (`.bak`,
   `*_missing`, `*_full`, extracts) belong in `data/`, never `web/public/data/`.
4. **One writer per file.** Multiple scripts writing the same file
   (e.g. `species_index.json`) is a drift factory; consolidate writers.
5. **Regenerable orphans are deleted, not archived, on the website.**
   Unique/hand-curated data is archived into `data/` before removal.
6. **Deletion is safe only after verifying:** (a) zero runtime references in
   `web/src`/`index.html`/`public/viewer`, (b) zero test references, and
   (c) a generator script exists (or the data is archived).

---

## Audit findings (2026-09-11)

### Cluster 1 — Gene presence: one matrix, ~4 shipped copies (~62 MB)

| File | Size | Role | Evidence |
|---|---|---|---|
| `gene_presence.json` | 22 MB | 209 species × 811 gene matrix + catalogue + `key_genes` | `key_genes.AICDA.species` duplicates matrix **207/207 identical** |
| `evidence/*.json` (592) | 40 MB | Per-gene: same `{status,level,method}` calls + BLAST HSP detail | `evidence/ANP32A.json` statuses match matrix **14/14** |
| `gene_presence_summary.json` | 68 KB | Per-gene counts | Pure aggregate; `gene_presence.json.summary` embeds it |
| `species_presence_summary.json` | 36 KB | Per-species counts (D102 lightweight payload) | Near-duplicate of embedded `summary` (differs: no `critical_absences`, `high_absences` capped at 12) |
| `genes.parquet` + `genes.csv` | 124 KB | Same 1,308 rows, two formats, incl. presence count columns | Identical schemas |
| `species_gene_matrix.json` | 36 KB | 26-species subset + susceptibility join | **Orphan** (0 runtime refs) |

### Cluster 2 — Species: one table, four copies (already drifted)

- `species.parquet` (655), `species_index.json` (655, column subset),
  `species_index_enhanced.json` (301, orphan), `susceptibility.parquet`
  (657 rows, **12 shared columns** with species.parquet).
- **Drift proof:** all 655 index entries had empty `ord`/`fam` —
  `export_web_data.py` reads `order_name`/`family_name`, columns that no
  longer exist. The Sep 11 export **also wiped all mammal entries and every
  curated IUCN/NZ/maori field** — `add_mammal_species.py` had put mammals
  into the index by design ("appear in species search and details, not in
  the avian phylogeny"); `Species.svelte`'s `detected_mammals.json` fetch
  was a post-hoc workaround that only covers the Mammals filter, leaving
  global search (`db.js`) without mammals entirely. *(Fixed in Phase 1 —
  mammals restored, generator now merge-preserves.)*
- Mammal sources were threefold: `detected_mammals.json` (64, git-tracked,
  detections-derived), `add_mammal_species.py::MAMMAL_SPECIES` (curated
  high-risk overlay), `mammals.json` (static list for Map) — see Phase 6.
- `species_wiki_supplement.json` (415 wiki-only species) is merged into the
  index at runtime by `db.js` — separate format, no ID overlap (by design).

### Cluster 3 — Detections: master + 4 derived map layers

`detections.parquet` (39,793) is master. `detections.geojson` (18,866 pts,
re-embedding 6 joined fields per point), `detections_by_country.geojson`
(156), `detections_by_species.geojson` (558), `hotspots.geojson` (410) —
the last three are pure `GROUP BY`s, derivable client-side in DuckDB.

### Cluster 4 — Genomes: three sequence copies per staged assembly

`public/data/genomes/<acc>/` stages `genome.fna` (~1.3 GB) +
`genome.fna.gz` (~0.4 GB) + `genome.2bit` (~0.3 GB). GenomeBrowser prefers
`.2bit`, falls back to `.fna`; **nothing fetches `.fna.gz`**. A
`--with-genomes` dist is 27 GB, ~half redundant sequence. `dist` is also
**stale** (its `gene_presence.json` is 1.8 MB vs 22 MB). `genomes.parquet`
best-genome info is re-embedded as 7 columns in `species.parquet`.

### Cluster 5 — Papers ↔ genes: bipartite relation in ≥5 files, disagreeing

`papers.json` (2.8 MB master) + `papers.json.bak` (2.8 MB pre-rename
snapshot, 468 `input_*` IDs — rename was intentional, IDs deprecated).
The gene↔paper link ships in `wiki_genes.json` (3.3 MB), `wiki_index.json`
(duplicated `paper_count`/`central_count`, verified identical), `genes.csv`
+ `genes.parquet` (`papers` col), `genes.json` (panel counts), plus orphans
`gene_discovery.json`, `gene_citations.json`, `species_papers.json`,
`paper_deg_summaries.json` (used).
**Drift proof — "papers" for ANP32A:** 441 (`genes.csv`) vs 23
(`wiki_genes.json`) vs 15 (`genes.json`) vs 5 (`gene_citations.json`).

### Cluster 6 — i18n: pipeline intermediates shipped (16 MB dir)

Runtime-fetched (keep): `{lang}.json`, `{lang}_i18n.json`,
`{lang}_content.json`, `extraction.json`, `final_extract.json`,
`papers/{lang}.json`. Intermediates (relocate): `*_full.json` ×5
(`es_full`/`ko_full` byte-identical to live files; ja/zh/hi stale divergent),
`*_missing.json` ×4, `content_extract.json`.

### Cluster 7 — Dangling references

- `SpeciesFullPage.svelte:174` fetches `data/species_wiki.json` — **file
  does not exist** (real file: `wiki_species.json`).
- `db.js` `loadGenePresence()` fetches `gene_presence.parquet` — does not
  exist (commented "future").
- `mammals.json` vs `detected_mammals.json` overlap (two mammal lists).

### Cluster 8 — Interior `data/` store (same pattern, lower stakes)

Seven tables as parquet+TSV(+JSON) triplets (~24 MB TSV mirrors),
`detections_merged_backup.parquet`, `species_profiles_complete.tsv`.
Genome store keeps `fna` + `fna.gz` + `2bit` + `blastdb` + `diamond_db` per
assembly (pipeline artifacts; `.gz` regenerable from `.fna`).

---

## Maturation plan

### Phase 1 — Fix the live drift + remove verified orphans ✅ (2026-09-11)

- [x] Fix `export_web_data.py:generate_search_index` — read `order`/`family`
      (fallback to legacy `order_name`/`family_name`), and **merge-preserve**
      enrichment fields (iucn, trend, range, maori_name, NZ fields, …) from
      the existing index instead of clobbering them (same pattern
      `add_detections.py` already uses).
- [x] **Restore mammals to the index** (regression fix, not a removal): the
      generator now rebuilds mammal entries from `detected_mammals.json`
      (fresh detection counts, genome badges) + overlays curated metadata
      from `add_mammal_species.py::MAMMAL_SPECIES` (IUCN, notes, range,
      common names, family) and appends zero-detection high-risk species.
      Convention: `ord: "Mammalia"` (what the D113 class filter expects),
      `class: "Mammalia"`. Result: **721 entries = 655 birds + 66 mammals**,
      4 mammals with full curation, 29 birds with IUCN restored, 0 dupes.
      Phylogeny unaffected (birdtree is birds-only).
- [x] Fold `species_index_enhanced.json` (IUCN/trend/range/population/
      maori_name for 298 species) into `species_index.json`, then remove the
      enhanced file. `db.js:_indexToSpecies` already maps these fields.
- [x] Regenerate `species_index.json`; verified ord/fam populated, mammals
      present, enrichment preserved, JSON valid.
- [x] Delete regenerable orphans (0 runtime refs, generators exist):
      `gene_discovery.json` (canonical: `data/papers/gene_discovery.jsonl`),
      `gene_lit_claims.json` (`papers/campaign.py` export),
      `species_papers.json` + `species_gene_matrix.json`
      (`papers/build_species_data.py` / `build_species_gene_matrix.py`),
      `species_index_enhanced.json` (folded in).
- [x] Relocate pipeline intermediates to `data/i18n_workspace/` (10 files:
      `*_full.json` ×5, `*_missing.json` ×4, `content_extract.json`); update
      `scripts/i18n_translate.py` and `scripts/translate_deep_content.py`
      paths so the workflow still functions.
- [x] Archive `papers.json.bak` → `data/papers/papers_pre_rename.bak.json`
      (pre-rename snapshot; IDs intentionally deprecated 2026-09).
- [x] Archive `gene_citations.json` → `data/papers/` (no generator found —
      treat as possibly hand-curated; do not destroy).
- [x] Verified: zero residual references in `web/src`/`tests`/`viewer`;
      edited scripts compile; `web/public/data` 103 MB → 99 MB.

### Phase 2 — Gene-presence consolidation (~62 MB shipped)

**Architecture (decided 2026-09-11):** interior canonical =
`data/genes/gene_presence_v2.jsonl` (raw calls) + `host_panel_v2.json` +
`gene_config.json`; single exporter = `scripts/genes/export_presence.py`
(one writer for `gene_presence.json` + both summary files). Website ships:
compact matrix (JSON interim → parquet end-state) + small catalogue/summary
JSONs + `evidence/` detail fetched on demand. `gene_presence.json` also
contains a **second full copy of the matrix** — `gene_catalogue[*].species`
transposes all 811 genes — which the audit initially missed.

**Backup before Phase 2:** `data/backups/webdata_2026-09-11_pre-phase2.tar.gz`
(snapshots `web/public/data` at 99 MB, pre-change).

- [x] **Step 1 — Kill the in-file duplication in `gene_presence.json`**
      (generator + one consumer):
      - Drop `gene_catalogue[*].species` (full transpose of the matrix) and
        with it `key_genes[*].species` (46-gene subset copy);
        `gene_presence_summary.json` computed from the matrix directly.
      - Compact JSON separators for all three outputs (machine-consumed).
      - Consumer: `Genes.svelte` derives the per-gene transpose client-side
        from the matrix it already fetches (`GeneFullPage.presence` shape
        unchanged). No other consumer touches the species maps (verified:
        SpeciesDetail/SpeciesFullPage/Model*/Phylogeny/EvidenceDrawer).
      - Verified: matrix + summary content identical to backup (parsed
        comparison), integrity_check + pytest + e2e green.
      - Result: `gene_presence.json` 22.3 MB → **13.1 MB** (−41%);
        `gene_presence_summary.json` 117→49 KB; `species_presence_summary.json`
        36→28 KB; web data 99 → 90 MB.
      - Note: regeneration also picked up this morning's 08:39 upstream
        BLAST run (14 strictly-better mammal calls: STING/DDX58/IFITM3/OASL
        in cow/cat/mouse/pig/fox) — the shipped file had gone stale vs the
        interior `gene_presence_v2.jsonl`; every diff vs the backup is one
        of those upgrades. Pre-change state preserved in the backup tarball.
- [x] **Step 2 — Parquet matrix + DuckDB loader:**
      - `export_presence.py` writes `gene_presence.parquet` (long format:
        species, gene, status, level, method, importance; zstd + dictionary
        encoding) built from the rolled matrix, with a consistency gate
        (parquet rows == JSON matrix calls; verified 131,755/131,755 exact).
      - `db.js`: `loadGenePresence()` now real; helpers added —
        `getPresenceCallsForSpecies`, `getPresenceCallsForGene`,
        `getSpeciesGeneSummary` (mirrors compact summary incl. critical/high
        absences), `getGenePresenceSummary`. BigInt counts normalised to
        Number; absence list via `string_agg` (DuckDB-WASM `list()` does not
        survive JSON conversion as an array).
      - `window.__db` test hook (mirrors `window.__cy` convention); new e2e
        test asserts known ground truth (Gallus: 811/805/2/4, DDX58 critical
        absence; DDX58 searched across 205 species).
      - `export_web_data.py` provenance docs now list the parquet.
      - Result: matrix ships as **54 KB parquet** (240× smaller than the
        13.1 MB JSON it will replace). Gates: pytest 81/81, integrity ✓,
        e2e 28/28.
- [x] **Step 3 — Migrate consumers to DuckDB; delete the big JSON**
      - Exporter now writes `gene_catalogue.json` (341 KB: catalogue +
        key_genes + header counts incl. `species_list` for dropdowns) +
        `gene_presence.parquet` (54 KB) + the 2 compact summaries.
        **`gene_presence.json` (13.1 MB) deleted — the matrix now ships in
        exactly one form.** Catalogue verified identical to pre-Phase-2
        content minus the removed species maps.
      - Consumers (8 components): Model/ModelMermaid query only the sensor
        genes + aliases (~3.7k rows) and pivot to the legacy shape;
        ModelCyto defers DuckDB entirely — graph builds from catalogue
        metadata, per-species presence loads lazily via dynamic `import()`
        on selection (memory-heavy page + DuckDB-WASM crashed the renderer
        when combined); Phylogeny overlay = one ~200-row query (also fixes
        the Step 1 regression where the overlay went empty after species
        maps left the catalogue — caught by re-reading consumers with an
        untruncated grep); SpeciesDetail/SpeciesFullPage load panel + SQL
        summary lazily, shape-preserving; Genes.svelte reads the small
        catalogue; GeneFullPage fetches its own presence per gene instead
        of inheriting eager 200-species maps on all 1,308 records.
      - Pipeline (12 scripts) repointed to `gene_catalogue.json`;
        `gene_agent` reads per-gene statuses from the parquet; `campaign.py`
        no longer writes `impact_if_absent_lit` into the shipped catalogue
        (second writer, zero site consumers) — exported to
        `data/papers/impact_if_absent_lit.json` instead.
      - `utils/presence.js` (new): cached catalogue fetch + pivots;
        deliberately db-import-free so catalogue-only pages don't load
        duckdb-wasm.
      - Gates: pytest 81/81, integrity ✓ (catalogue↔summary + binomial
        checks moved to catalogue/parquet), e2e **28/28** (after raising the
        test renderer heap cap — see decisions 2026-09-11-b).
      - Result: web data **90 → 78 MB** (Phase 2 total: 103 → 78 MB).
- [x] **Step 4 — Residual summary files retired:**
      - `species_presence_summary.json` (28 KB) deleted — SpeciesFullPage's
        early-payload fetch removed; the SQL rollup is the single source
        (template guards already handled the load gap).
      - `gene_presence_summary.json` (49 KB) deleted — the Genes genome
        view (D105 gate + detail table) now runs one `GROUP BY` over the
        parquet via `db.getGenePresenceSummaries()` (dynamic import keeps
        duckdb-wasm off the page until the view is used).
      - Integrity check validates catalogue↔parquet consistency directly.
      - New e2e test drives the genome view end-to-end (incl. DDX58's
        genuine absence count > 0).
      - Gates: pytest 81/81, integrity ✓, e2e **29/29**.
      - Result: presence artifacts on the site are now exactly two files —
        `gene_presence.parquet` (54 KB, the matrix) + `gene_catalogue.json`
        (341 KB, metadata). Presence cluster from the audit: ~62 MB → 0.4 MB.
- [x] **Step 5 — One genes tabular format:** converged on parquet.
      - `genes.csv` (94 KB) deleted; Downloads page now offers parquet only
        (description notes Excel can import Parquet).
      - `export_gene_panel.py` fixed en route: it still read the Step-4-
        retired `gene_presence_summary.json` (would have crashed on next
        run) — presence columns now derive from `gene_presence.parquet`
        via GROUP BY. Cross-validated: DDX58 counts identical across the
        DuckDB rollup, the new parquet, and the old CSV.
      - Integrity check switched from genes.csv to genes.parquet.
      - Gates: pytest 81/81, integrity ✓, e2e 29/29.
- [x] **Step 6 — evidence/ reviewed — KEEP as-is:** per-gene detail files
      (HSPs, sequences, exon evidence — data that exists nowhere else in
      shipped form) fetched on demand by one component (EvidenceDrawer).
      The re-stated per-call statuses are the price of self-contained
      files; stripping them would couple the drawer to the matrix for
      ~15 KB/gene on lazy loads. No change.

**Phase 2 result (2026-09-11):** presence data shipped = `gene_presence.parquet`
(54 KB) + `gene_catalogue.json` (341 KB) + `genes.parquet` download (28 KB).
Audit Cluster 1 went from ~62 MB / 6 representations to ~0.4 MB / 3 files,
each with exactly one writer. Web data overall: 103 → 78 MB.

### Phase 3 — Species consolidation ✅ (2026-09-11)

- [x] **One writer for `species_index.json`** — `export_web_data.py:
      generate_search_index` is now its ONLY writer, merging in one pass:
      profiles parquet (birds) + `detected_mammals.json` (mammals) +
      **`data/manual/species_overlay.json`** (new, git-tracked home for the
      curated mammal/NZ lists formerly hardcoded in `add_mammal_species.py` /
      `add_nz_species.py`, which are now overlay editors) + merge-preserve of
      the existing index. `add_detections.py`'s two index writers removed;
      `merge_genome_data`'s best-genome logic folded into the generator —
      **448 birds regained genome badges in the index** (it had zero).
      Verified: 723 species (655 birds + 66 mammals + 2 NZ concern), NZ
      cases carry parquet-fresh counts + curated case detail/maori names,
      kākāpō & takahē indexed with conservation status, 33 IUCN preserved,
      0 duplicates.
- [x] **`susceptibility.parquet` slimmed + JOIN fix:** runtime-verified the
      Species page's sort-by-susceptibility was **broken** (`ORDER BY
      susceptibility_score` on a table without that column → Binder Error →
      empty grid; `loadSusceptibility` had zero callers). Now ships 6 columns
      (score/class/confidence/has_rigi/rigi_modifier + join key; the 12
      columns duplicated from species.parquet dropped), and Species.svelte
      `LEFT JOIN`s it — sort works, SpeciesCard badges get real classes.
      Downloads page R example corrected to the join pattern.
- [x] **Dangling `species_wiki.json` fetch fixed** in SpeciesFullPage →
      `wiki_species.json` with correct `{species:{}}` unwrapping + canonical
      matching (the research badge silently never rendered before).
- [x] **Dead `loadGenePresence()`** — made real in Phase 2 Step 2 (closed).
- Gates: pytest 81/81, integrity ✓, e2e **30/30** (new test: susceptibility
      sort + wiki badge; one known-flaky Cytoscape memory test passed on
      standalone + full-suite rerun).

### Phase 4 — Detections/map derivation ✅ (2026-09-11)

- [x] **Map renders from DuckDB, not static geojson:** Map.svelte queries
      `detections.parquet` (`LEFT JOIN species` for common names) and builds
      the point features client-side. Zero runtime geojson fetches remain.
      Findings en route: the Hotspots/By-Country layer buttons were dead UI
      (`selectedLayer` never read) — removed; the `#/map?species=…` deep
      link documented in the router was never implemented — now works
      (incl. SPA hash-change navigation, clearable filter chip); the header
      count said "156 countries" by counting ALL detection countries while
      showing only georeferenced points — now truthful (148).
- [x] **Static geojson layers → Downloads-only artifacts (decision):** the
      map never fetched `hotspots`/`by_species`; `detections_by_country`
      was fetched solely for a count. All four remain Downloads-page
      offerings — deliberate denormalized export products with one writer
      (`export_geojson.py`), like `genes.parquet`. The susceptibility join
      fields per point stay IN the download (a feature for downloaders);
      the runtime join happens in SQL instead.
- Gates: pytest 81/81, integrity ✓, e2e **31/31** (new test: DuckDB-driven
      map + stats poll + species deep link + filter clear).

### Phase 5 — Genome staging + dist ✅ (2026-09-11)

- [x] **Staging = `genome.2bit` + `annotation.gff.bgz`(+`.tbi`) only:**
      removed the `genome.fna`/`.fai` (a fallback that can't trigger when
      2bit exists; the fallback CODE stays in GenomeBrowser.svelte for
      custom deployments) and `genome.fna.gz`/`.gzi` (zero consumers
      anywhere) symlinks from `web/public/data/genomes/*/`. Dereferenced
      staging: ~11.6 GB → **4.3 GB**. Writers updated so re-running the
      pipeline won't recreate the bloat: `prepare_igv.py` stages nothing
      (still writes the interior `.fai`/ORF maps the pipeline needs),
      `bgzip_genomes.sh` stops staging the bgzf pair (interior copy kept
      as a pipeline artifact).
- [x] **`dist` rebuilt fresh:** 27 GB stale artifact (Sep 6 data, retired
      files, triple-stored sequences) → lean **93 MB** with all current
      artifacts (verified: 723-species index incl. 66 mammals, catalogue +
      parquet, no retired files, unused 78 MB wasm bundle dropped).
      `--with-genomes` would now add ~4.3 GB (was ~17 GB claim / 27 GB
      actual). make_dist.sh guidance updated.
- Operational note: `bg_run` on this machine executes fish — bash-isms in
  wrapper commands silently no-op or parse-error; run scripts directly.
- Gates: pytest 81/81, integrity ✓, e2e 30/31 → the single failure is the
  known memory-flaky deep-link test, which ran concurrently with the 27 GB
  dist delete and passes standalone (verified twice after the build).
- Build surfaced a known limitation (no action): the INEFFECTIVE_DYNAMIC
  IMPORT warning — db.js is dynamically imported by Genes/ModelCyto but
  statically by App/others, so the lazy pattern avoids DuckDB
  *initialization*, not bundle inclusion. Fine as designed.

### Phase 6 — Interior store + remaining ✅ (2026-09-11)

- [x] **Interior TSV mirrors retired:** 11 TSVs deleted (aphis_detections,
      coverage_matrix ×3, detections_merged, phenotype_table,
      species_profiles_detected/complete, species_table,
      susceptibility_scores ×2 — ~24 MB); the `write_csv` lines in the 7
      generator scripts are commented with a one-line regeneration recipe;
      parquet/json remain canonical. `detections_merged_backup.parquet`
      relocated to `data/backups/` (zero-loss; dedup's runtime backup
      behavior untouched).
- [x] **Three mammal lists — DECIDED: distinct facts, not duplication:**
      `data/manual/species_overlay.json` (curation),
      `detected_mammals.json` (detections-derived table, the mammal
      equivalent of species.parquet), `mammals.json` (literature-derived
      sci→common display dictionary for the Papers page, single
      writer/consumer). Each is single-writer; merging would conflate
      curation/detection/literature-mention semantics.
- [x] **`det` semantics — DECIDED:** `detection_count` = **animals
      affected** by design (documented in build_species_profiles.py:
      1 per wild-bird event, birds affected per premises flock, case
      counts per WAHIS/WHISPers event — "numbers affected" per species).
      The index inherits this consistently. The audit's "drift" framing
      was wrong: it is one semantic, deliberately chosen. Open product
      note: the Species-page "Most detections" sort label could read
      "Most animals affected" for clarity.
- [x] **Gene→paper count unified:** `genes.parquet`'s `papers` column was
      `total_mentions` mislabeled as papers (ANP32A: 441 mentions vs 23
      papers!). Now paper counts, max-merged with the wiki corpus counts —
      ANP32A 23=23, DDX58 73=73; consistency gate (parquet ≥ wiki for every
      gene) passes.
- [x] **`provenance.json` linked from Credits** (machine-readable source
      list with licenses/record counts; regenerated every export).
- Gates: pytest 81/81, integrity ✓, e2e **31/31**.

### Post-plan verification — user-visible numbers (2026-09-11)

Audit question: does the site pull from data in the right spots, and are any
numbers hardcoded (or hardcoded-but-refreshed)?

**Already dynamic (verified):** Home hero + Methods live numbers
(`stats.json`, regenerated every export); Species page counts
(totalDetected/totalAll from the index); Papers counts (papers.json);
Genomes table (genomes.parquet); gene-panel counts (per-species queries);
Genes detail-table counts (DuckDB GROUP BY).

**Was hardcoded and STALE — fixed to live values:**

| Location | Was | Now |
|---|---|---|
| Downloads `records` | 20,669 / 296 / 7,312 (all wrong) | `stats.json`-driven: 39,793 / 655 / 18,866 / 723 |
| Downloads `size` | byte literals (586000…) | live `HEAD` content-length on every load |
| Model + ModelMermaid heading | "Sensor matrix — 15 genomes" | `matrix.species.length` species (208 rows — truthful: one species has no sensor-gene calls) |
| Methods mermaid diagram | "Gene presence 15 species" | `$derived` interpolation of `stats.presence_species` |
| Genes copy ×3 | "391 sequenced species/genomes" | catalogue-header `total_species`/`total_assemblies` (209 — the 391 was a pre-rollup-era assembly count) |
| Genes corpus line | "of the 1,206 corpus papers" | `stats.papers` |
| Home fallbacks | `stats.sources || 14`, `georeferenced || 7312` | `?? '—'` (fallbacks were dead but misleading) |

Supporting exporter change: `stats.json` gains `searchable_species` (length
of the freshly generated index — birds + mammals + overlay-only), read by
the Downloads page. `gene_catalogue.json` header gains `total_assemblies`.

**Deliberately static (descriptions, not data):** prose like "1.0° grid" or
format labels — not counts. `i18n` translations may lag one export behind
English copy; acceptable.

### URL-state sweep (2026-09-11, post-plan)

Every interactive view is now deep-linkable with the same contract:
restore-on-load, interaction→URL, SPA-navigation applies params,
absent-param = default, echo-guarded (no feedback loops).

| Page | Params |
|---|---|
| Species | q, class, order, sort, all |
| Genes | q, kind, genome, tier, stage, host, view, sort, dir, category, page, gene / #/genes/{sym} |
| Phylogeny | gene, color, calls, genome, detected, q |
| Mutations | q, protein, kind, scope, sort, mut / #/mutations/{id} |
| Genomes | tab, assembly, annotated, order |
| Map | species, lat, lng, z (camera; converging round-trip, debounced) |
| Papers | q, f (facet chips), p (page) / #/papers/{id} |

Bugs fixed en route (beyond the URL wiring): dead Species class/all
buttons, search BigInt sort crash + dedup failure, supplement/index
duplicate keys, Genes restore serialized behind DuckDB init + late-
subscription clobber, Papers pagination reset racing URL restores,
Map camera echo (suppression + rounding), SQL-injectable filter values
(Genomes), three stale copy numbers on Genes/Methods.

Tests: 27 → 37 e2e, one per data/URL contract. Known flaky under full-suite
memory load: the Cytoscape deep-link and connection-badge tests (heap cap
raised; pass standalone).

---

## Decisions registry (append-only)

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-11 | **Mammals restored to `species_index.json`** (66 entries: 64 detected + 2 high-risk zero-detection) | `add_mammal_species.py` states the design: mammals are indexed like birds (search, details), just excluded from the avian phylogeny. Their absence was an export regression, not a design choice |
| 2026-09-11 | Mammal index entries carry `ord: "Mammalia"` + `class: "Mammalia"`; real order/family detail via curated overlay | Matches the D113 class-filter convention in `Species.svelte`; avoids breaking `ord === 'Mammalia'` filtering |
| 2026-09-11 | `Species.svelte`'s direct `detected_mammals.json` fetch kept (not yet deduplicated) | It still powers the Mammals-filter path; consolidating the three mammal lists is Phase 6 |
| 2026-09-11 | `papers.json.bak` archived, not deleted | Pre-rename snapshot; old `input_*` IDs deprecated but content preserved zero-loss in `data/papers/` |
| 2026-09-11 | `gene_citations.json` archived, not deleted | No generator script found — possibly hand-curated; archived to `data/papers/` |
| 2026-09-11 | `provenance.json` kept | Regenerated by export; license attribution for a public site is worth shipping (link from Credits in Phase 6) |
| 2026-09-11 | i18n intermediates relocated to `data/i18n_workspace/` | Pipeline working files must not ship; scripts updated to the new path |
| 2026-09-11 | `gene_presence.json` retired; matrix ships ONLY as `gene_presence.parquet` (54 KB) + small `gene_catalogue.json` | One shipped copy of the matrix; DuckDB queries replace JSON slicing |
| 2026-09-11 | ModelCyto loads presence lazily (dynamic `import()` of db.js on species selection) | Cytoscape + DuckDB-WASM on one page crashed the renderer under load; the page needs presence data only after user interaction |
| 2026-09-11-b | Playwright launchOptions: `--js-flags=--max-old-space-size=4096` | "Target crashed" on the deep-link Cytoscape test only under full-suite load; renderer heap cap, not a product bug (passes standalone/at file level); suite already serial for memory reasons |
| 2026-09-11 | `campaign.py` impact_if_absent_lit → `data/papers/impact_if_absent_lit.json` | Was written in-place into the shipped catalogue (second writer); nothing on the site reads it |
| 2026-09-11 | Presence summary files retired; rollups derive from the parquet | The parquet is the single shipped presence artifact; summary JSONs were projections with consumers already on DuckDB |
| 2026-09-11 | `data/manual/species_overlay.json` created; add_*_species scripts are overlay editors | Curated species data needs a git-tracked single home; the index gets ONE writer (export_web_data.py) |
| 2026-09-11 | `susceptibility.parquet` slimmed to 6 columns; runtime LEFT JOIN | 12 columns duplicated species.parquet; the duplication masked a live Binder-Error bug (sort-by-susceptibility returned an empty grid) |
| 2026-09-11 | Genome-badge merge folded into `generate_search_index` from `add_detections.merge_genome_data` | Same info, one writer; restored genome badges for 448 birds that the post-export index had lost |
| 2026-09-11 | Geojson layers are Downloads-only; Map queries DuckDB | Runtime had 2 of 4 layers (one just for a count); downloads are deliberate denormalized products with one writer |
| 2026-09-11 | Map dead UI removed (layer buttons), species deep link implemented | Buttons wrote an unread state; `#/map?species=` was documented but never wired |
| 2026-09-11 | Genome staging ships 2bit+gff only; interior store untouched | `.fna.gz` had zero consumers; `.fna` fallback can't trigger when 2bit exists; interior keeps pipeline artifacts (Phase 6 will revisit) |
| 2026-09-11 | `dist/wasm` dropped from distributions | 78 MB molecule-viewer bundle nothing in src imports (viewer uses the 3D Mol CDN) |
| 2026-09-11 | Interior TSV mirrors retired (11 files, writes commented in generators) | Pure write-mirrors with zero readers; parquet canonical, one-line regeneration recipe in each script |
| 2026-09-11 | Mammal lists kept as three distinct single-writer files | Curation vs detection vs literature-mention are different facts; merging would conflate semantics |
| 2026-09-11 | `detection_count` = animals affected (kept) | Deliberate, documented semantic in build_species_profiles.py; index inherits it consistently — the audit mis-framed it as drift |
| 2026-09-11 | `genes.parquet` papers column: mentions → paper counts | 441 "papers" for ANP32A was 441 mentions; now max-merged with wiki corpus counts (23=23) with a consistency gate |
| 2026-09-11 | Download sizes via live HEAD; records via stats.json | Byte/record literals were months stale (20,669 vs 39,793); HEAD + stats can never drift |
| 2026-09-11 | Copy counts interpolated from data everywhere | "15 genomes"/"391 species"/"1,206 papers" were frozen pre-rollup numbers; now bound to stats/catalogue headers |
