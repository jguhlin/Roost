# Roost — Scientific Consistency & Animation Readiness Report

**Task:** targeted validation and repair pass before storyboard development.
**Companion documents:** [`discovery.md`](discovery.md), [`user_journeys.md`](user_journeys.md) (both updated where corrections landed).
**Date of pass:** 2026-11-10. No animation was produced; changes are data repairs, metadata corrections, and restrained UI confidence presentation.

**Overall test status at close:** validation suite **17/17 passed** (`scripts/tests/test_animation_readiness.py`); by-the-numbers **23/23 checks green**; Playwright regression subset **6/6** + new overlay spec **3/3**; i18n scanner clean (0 hardcoded strings); svelte-check delta vs. baseline **+0 substantive errors** (2 line-shifted pre-existing `never`-inference diagnostics only; repo baseline is 2,939, unchanged in kind).

---

## Issue-by-issue register

### 1. Susceptibility terminology (mallard "highly_tolerant" vs "highly_susceptible")

**Root cause — genuinely different axes, colliding vocabulary, unlabeled.** Three shipped artifacts:
- `web/public/data/susceptibility.parquet` — **legacy v1** (`build_susceptibility_scores.py`): mortality-weighted composite × RIG-I modifier. Its class vocabulary (`highly_susceptible…highly_tolerant`) describes **disease outcome**. Mallard = 14.6 "highly_tolerant" (rarely diseased).
- `web/public/data/species_susceptibility.json` — **v2, authoritative** (`build_susceptibility.py`): two-axis. `class` derives from **permissiveness** (can the virus replicate?). Mallard = 85.8 "highly_susceptible" = *highly permissive* — correct for a reservoir, with severity reported separately (76.8, basis p75, n=1 study).
- `host_competence.json` susceptibility block — joins the legacy v1 parquet.

The v2 redesign (2026-10-15) fixed the conflation in the model but five render sites still showed v1 labels with no axis qualifier: SpeciesCard chip, SpeciesDetail stat card, CompetenceTable, SpreadCyto, Compare. A user could read "Mallard: highly_tolerant" (grid) and "Mallard: highly_susceptible" (susceptibility page) as a contradiction.

**Correction (presentation-layer, data untouched — the disagreement is by design and pinned by test):**
- New i18n keys `susc.legacy.tip` / `susc.legacy.short` explain the axis ("mortality-weighted × RIG-I status — describes disease outcome, not infection permissiveness; a reservoir reads tolerant here yet is highly permissive").
- SpeciesCard chip now shows "(legacy model)" + tooltip. SpeciesDetail stat card labelled "Susceptibility · legacy model" + link to the two-axis page `#/susceptibility/{name}`. CompetenceTable dt labelled "Susceptibility · legacy model" + tooltip.
- `build_susceptibility_scores.py` docstring documents the axis + supersession (future rebuilds inherit the framing).
- Test `t_susceptibility_vocabularies_distinct_axes` **pins** the mallard disagreement (v1 "highly_tolerant" vs v2 permissiveness ≥75) so nobody later "fixes" one artifact onto the other.

**Files modified:** `web/src/lib/stores/i18n.svelte.js`, `SpeciesCard.svelte`, `SpeciesDetail.svelte`, `CompetenceTable.svelte`, `scripts/build_susceptibility_scores.py`.
**Not done (deliberate):** migrating the grid/Compare/SpreadCyto to v2 wholesale — a product decision beyond minimal repair; the v1 numbers stay, now correctly labeled.
**Dimension glossary now enforced:** permissiveness (v2 axis 1) ≠ severity (v2 axis 2 / v1 axis) ≠ resistance (only ever literature verdicts: `resistance_suspected`) ≠ surveillance detections (MEASURED records) ≠ model output (all scores carry MODELED provenance + confidence).

### 2. Dataset counts & taxonomy

| Issue | Root cause | Correction | Before → after |
|---|---|---|---|
| Mallard 1,838 vs 1,842 | `host_competence.json` stale (built 2026-10-15; detections rebuilt 2026-11-10) | Reran `build_host_competence.py` + `build_susceptibility.py` | 1,842 → **1,836 dated** (canonical raw records = 1,838; the builder counts rows with non-null `date_iso` — documented definition, pinned by test) |
| Chicken 314 vs 310 | same staleness | same rerun | 310 → **314** (dated == raw) |
| `species_index.det` = 182,165,286 for chicken | `build_species_profiles.py` summed `detection_count`, which for `aphis_flocks` rows holds **flock sizes** (max 5.35 M; mean 91,900) — the sum was animals-affected, displayed as detections | Added `detection_records` (row count) to the agg; index `det`, UI badge, sorts and `--min-detections` now use records; animals-affected kept as `detection_count` with clarified comments; profile sort switched to records | chicken badge 182,165,286 → **314**; mallard 2,222,663 → **1,838**; max index det 3,443 (sane) |
| Same flock-size sum leaked into 5 MORE consumers (found during re-validation) | global searchbar + Home top-species ordering (`db.js searchSpecies/searchSpeciesAll/getTopSpecies`), Genomes page filter/sort/badge, **phylogeny tree colour scale** (`phylogeny.json` metadata max was 182 M), Landscape bridges list (`data_lit_bridges.py`) | all switched to `detection_records`; `fetch_phylogeny.py` + `data_lit_bridges.py` fixed and both artifacts regenerated (newick byte-identical; bridges now output `det_records`) | tree colour max 182,165,286 → 3,443; bridges top species now snow goose 797 records |
| Kākāpō `habroptila`/`habroptilus` | IOC/index spelling vs NCBI spelling across artifacts; susceptibility keyed the NCBI form, so `#/susceptibility/Strigops%20habroptila` 404-ed | `VAX_SYNONYMS` + `ORDER_HINTS` canonicalized to `habroptila` (legacy alias kept); reran vaccine_outcomes → susceptibility | susceptibility entry now keyed `Strigops habroptila` (unevaluated, RIG-I present); page link resolves |
| ANP32A "12+334 vs 387" | denominator mixing: 387 complete = 12 palaeognath + 375 neognath; the 334 (316 with-insert + 18 zero) excludes 41 *other-length* inserts (29/15/60/27/41/40/19/12/68 aa); 60 further species are fragments | documented; test pins the decomposition | canonical caption: **"387 complete avian ANP32A sequences: 316 with the 33-aa insert (94.6% of the 334 classifiable neognath sequences), 18 with none, 41 with variant-length inserts; all 12 complete palaeognath sequences are in the zero-insert group"** |
| Presence counts (2,951,184 vs 2,741,391) | **units**: raw parquet = gene×**assembly** rows (2,388 assemblies, 3 panel versions); web twin = best call per (species, gene) after alias merge + subspecies→binomial rollup + sovereignty filter; stats.json had read a stale catalogue (2026-10-10) | reran `export_presence.py` (also adds `conf`/`searchability`, below); stats.json refreshed via export | stats presence_calls 2,741,391 (stale) → **2,742,163** (fresh catalogue); raw 2,951,184 (unchanged, = by_the_numbers); presence_species 2,048 → **2,055**; panel_genes 1,427 (catalogue current; was 1,428 in the older export — both artifacts now agree) |

**Canonical definitions (now enforced by tests):** "detections" in UI = surveillance **record** count; host_competence = **dated** records; presence totals must state unit (raw assembly-level vs display species-level).

**Files modified:** `scripts/build_species_profiles.py`, `scripts/genes/build_species_index.py`, `scripts/export_web_data.py`, `scripts/model/build_vaccine_outcomes.py`, `scripts/model/build_susceptibility.py`; artifacts regenerated (see §Tests).

### 3. Genomic interpretation

**DDX58.**
- *Loss vs pseudogene vs non-detection:* the corpus record `barber2010` had LLM-written metadata asserting chickens "carry a non-functional RIG-I/DDX58 pseudogene". Verification against the real paper (below) shows the source claims RIG-I "**may be absent**" — the pseudogene wording was confabulation. Roost's own BLAST evidence is a **non-detection at searchability 1.00** (all 12 control genes recovered), which is compatible with deletion OR a remnant too degenerate to hit thresholds; the data cannot distinguish. Export + UI wording now say "not detected (high confidence)", never "deleted" or "pseudogene".
- *Basal galliforms:* re-verified — cracid (*Penelope pileata*) and megapode (*Alectura lathami*) retain DDX58 (blast FULL); guineafowl is a fragment; **pinned by test** `t_ddx58_basal_galliforms_retain`.
- *High-confidence non-detections:* 47 rows / **39 species**, every one Phasianidae or Odontophoridae (searchability 0.917–1.00) — pinned by test against the OrthoFinder family map. The other 177 not-found rows are low confidence (incl. the tinamou false lead — must never be shown as loss).
- *No ancestral inference:* all statements are tip-pattern only; the exports explicitly note "no ancestral-state reconstruction performed". Any internal-branch loss animation remains [ANIM-ONLY, tip-derived].

**IFITM3.** Aliases verified: the gene enters via alias resolution (45 of 57 papers via IFITM-family alias folding; `gene_evidence_counts.via_alias`). Guard test asserts **zero high-confidence absences** anywhere — its non-detections (zebra finch, flycatcher, tinamou, ostrich, kākāpō — all searchability 0.5–0.67) are research questions, not losses. Both corpus quotes verified verbatim in `docs/papers_md/` sources (the siIFITM3 quote spans a line break — matched on joined text).

**ANP32A.** Sequence spot-check of the palaeognath calls: **16 palaeognaths measured, all 16 insert_len=0** (12 complete + 4 fragments). Internal consistency check: neognath full-length-with-insert = 281 aa; 281 − 33 = 248 aa, and 7 of the complete palaeognaths are **exactly 248 aa with the insert site anchored at 139** (kiwi ×2, emu, Chilean tinamou, rhea ×2, ostrich) — the zero-insert calls on those are robust, not truncation artifacts. 2 more are anchored at 137/122 (206/230 aa). **Weaker:** 3 complete-but-short with unanchored site (cassowary 224, Crypturellus 206/215) and 4 tinamou fragments — count them, don't feature them. Neognath zero-insert species re-checked (18, incl. mesite — a neognath). Status unchanged: **novel computational observation** (MSA-derived, needs sequence-level validation before prominent use).

### 4. Evidence-confidence presentation (implemented)

The confidence ladder existed only in the internal parquet (`absence_confidence`, `searchability`) — invisible in the UI, so a NOT_FOUND on a half-searchable assembly looked identical to a high-confidence absence.

**Changes (restrained, additive):**
- `export_presence.py` now carries `conf` + `searchability` through alias merge and subspecies rollup into the web twin (explicit polars schema to survive mostly-null columns).
- **Phylogeny gene overlay** (`?gene=`): non-detections split into `NOT_FOUND_HI` (deep red `#b91c1c`) vs low/medium (light red `#fca5a5`); banner counts "(N high-confidence)"; legend gained two labeled entries with explanatory tooltips (`phylo.legend.nf.hi/.lo.tip` — the ≥90%-control-genes vs <75–90% definitions).
- **Clade drill-down:** species chips now distinguish ✗ (high confidence, solid border) from ✗? (low/medium, dashed border) with the same tooltips.
- Accessibility: text labels + `title` tooltips (screen readers read the legend text; color is never the only channel). New UI strings all via `t()`; i18n scanner clean.

**Not changed:** aggregate clade heat-matrix cells (order-level %, by design aggregate); EvidenceDrawer (already shows per-call thresholds). The distinction is deliberately NOT mapped onto "not evaluated" — species without calls render gray "Not searched" as before, which satisfies the five-state requirement (detected / fragment / not-found-high / not-found-low / not-searched).

### 5. Literature evidence & provenance

| Claim | Verification | Result |
|---|---|---|
| `barber2010` title/journal/DOI | DOI 10.4049/jimmunol.0902471 → **HTTP 404**; title yields **0 PubMed hits**; PubMed author search → the real paper | **Corrected** to Barber MR, Aldridge JR Jr, Webster RG, Magor KE, "Association of RIG-I with innate immunity of ducks to influenza", *PNAS* 107(13):5913–5918, **DOI 10.1073/pnas.1001755107**, PMID 20308570 (PMC2851864). Summary rewritten from the published abstract (duck RIG-I clears infection; ~200-fold induction on H5N1 challenge; DF-1 transfection rescue; "RIG-I may be absent in chickens"). Record + papers.json twin updated, with `_meta_correction` provenance. Note: no fulltext in corpus — the paper is correctly cited as the canonical reference but corpus quotes for the chicken loss come from Smith et al. 2015. |
| "pseudogene in chickens" | unsupported (above) | removed; animation wording guidance set |
| `long_anp32_2019` DOI | Crossref | **Corrected**: 10.7554/eLife.45066.001 (sub-article part DOI) → **10.7554/eLife.45066** |
| `comparative_analysis_host_responses_2024` year | Crossref: 10.1186/s12864-015-1778-8 = Smith et al. **2015** BMC Genomics | **Corrected** year 2024→2015 (paper ID unchanged); this is the source of the corpus's RIG-I-loss quote |
| `anp32_editing2023` | Crossref | verified: Idoko-Akoh et al., Nat Commun 14:6136, DOI 10.1038/s41467-023-41476-3 |
| IFITM3 quotes (2), OASL quotes (2), DDX58 quote (1) | grep against `docs/papers_md/` | all **verbatim** in source text |

### 6. Journey re-validation

- **A (mallard → kākāpō):** all figures re-verified post-fix; `journey1_species.json` regenerated (mallard 1,838/1,836; chicken 314; kākāpō keyed `habroptila`, `unevaluated`, RIG-I FULL; canonical-count note embedded). Species grid badge now shows record counts; susceptibility chip labeled legacy; `#/susceptibility/Strigops habroptila` resolves.
- **B (IFITM3):** quotes verbatim-verified; zero-high-confidence-absence fact now both exported (`journey2_literature.json`, regenerated with corrected paper records incl. Smith 2015 + corrected DOIs) and test-pinned.
- **C (DDX58):** `journey3_ddx58.json` regenerated with the corrected Barber reference, non-detection wording note, and the tip-pattern-only interpretation note. Web twin shows 36 high-confidence absences after alias merge/rollup (39 raw) — both numbers documented in the export.

All exports re-validated by `t_animation_exports` (parses, tip counts 24/15, 387-row ANP32A table, 12 palaeognaths all zero, Barber DOI matches).

### 7. Tests & builds performed

| Check | Result |
|---|---|
| `scripts/tests/test_animation_readiness.py` (new, 17 checks) | **17/17 PASS** |
| `pixi run python scripts/papers/build_by_the_numbers.py` | **23 checks, 0 failed** (includes refreshed presence/catalogue cross-checks) |
| Playwright `tab-content.spec.js` + `species-count-consistency.spec.js` | **6/6 PASS** (susceptibility pages, competence card, stats-driven counts) |
| Playwright `phylo_gene_overlay.spec.js` (new, 3 tests) | **3/3 PASS** — legend renders both confidence entries; DDX58 banner shows **36 high-confidence** absences (1,537 present · 312 fragment · 206 absent · 2,055 species with calls); IFITM3 shows **0** |
| `scripts/i18n_scan.py` | 0 hardcoded strings |
| svelte-check | repo baseline 2,939 pre-existing diagnostics; after changes 2,941 — the +2 are the same `never`-inference diagnostics at shifted line numbers (verified by stash-diff on the exact files); **0 substantive new errors** |
| Rebuild chain | `build_species_profiles` → `export_presence` → `vaccine_outcomes` → `host_competence` → `susceptibility` → `export_web_data` → `by_the_numbers` — all exit 0 |

\* *overlay spec result inserted at completion — see Test Log below.*

**Incident during validation (instructive):** the first overlay-spec run failed on every route — the error context showed a **duplicate `t` import in Clade.svelte** (my earlier edit added one where one already existed further down the file), a compile error that blanked the whole SPA (the known AGENTS bug class: one route's parse error kills the router import chain). Additionally the first Playwright run had executed against a **stale vite fixture from Oct 29 serving 12-day-old code** on port 5178 (the AGENTS-documented gotcha). Fixed the import, killed the stale fixture (`ss -tln` check, PID verified against the LAN server on 5177 before killing), reran. The new spec thereby proved its worth twice over.

---

## Final verified values for animation captions

| Caption fact | Value | Source of truth |
|---|---|---|
| Papers in corpus | **1,528** | by_the_numbers / papers.json |
| Genes with literature evidence | **3,560 studied** (4,348 host genes in registry) | by_the_numbers |
| Surveillance records | **44,931 records, 106 countries** | stats.json / detections.parquet |
| Species in presence panel | **2,055** (1,427 panel genes) | gene_catalogue (fresh export) |
| Presence calls | **2,951,184** gene×assembly (raw) / **2,742,163** best-per-(species,gene) display calls | by_the_numbers / catalogue — always state the unit |
| Mallard | **1,838 records** since 2006-02-23; complete genome GCF_047663525.1; DDX58 FULL; permissiveness 85.8 (MODELED) | detections.parquet / species_index / susceptibility v2 |
| Chicken | **314 records**; DDX58 NOT_FOUND at searchability 1.00 (high confidence) | same |
| Kākāpō | **0 detections**; susceptibility `unevaluated`; RIG-I present; ~350 individuals | species_index / susceptibility v2 / overlay |
| DDX58 gamebird loss | **39 species, all Phasianidae/Odontophoridae**, searchability ≥0.917; cracid + megapode retain; 20/20 waterfowl FULL | gene_presence_v2 + tests |
| Barber et al. 2010 | **PNAS 107:5913–5918, DOI 10.1073/pnas.1001755107** — "RIG-I may be absent in chickens" | PubMed PMID 20308570 |
| ANP32A insert | **316/334 classifiable neognaths carry it; 0/12 complete palaeognaths; 41 variant-length; 60 fragments excluded** | anp32/comparison.json + test |

---

## Readiness classifications

| Example | Status | Conditions |
|---|---|---|
| DDX58 galliform loss (Journey C) | **READY** | Say "not detected, high confidence" / "lost functional RIG-I" (Smith 2015 wording + own BLAST); never "pseudogene"/"deletion"; loss-event marker on internal branches is animation-only (tip data) |
| Mallard reservoir profile (Journey A) | **READY** | "Highly permissive (modeled)" — never "resistant"; detections = records |
| Kākāpō absence-of-evidence (Journey A coda) | **READY** | `unevaluated` is the point; IFITM3/MX1 gaps are low-confidence, label as such |
| IFITM3 literature→genomics question (Journey B) | **READY** | Zero high-confidence absences is the finding; frame gaps as questions; Smith 2015/2025 quotes verified verbatim |
| ANP32A 33-aa insert function + edited chickens | **READY** | established literature (Long 2019, Idoko-Akoh 2023 — both DOI-verified) |
| ANP32A palaeognath absence pattern | **CONDITIONAL** | Roost-computed; robust for the 7 anchored full-length (248 aa) species, weaker for 3 unanchored + 4 fragments; needs sequence-level validation before featuring as biology; present as "measured in our data — open question" |
| DDX58 Z-linkage sex bias | **NOT READY** | explicitly untested hypothesis (G6) in the model; only as a labeled hypothesis graphic, or omit |
| Susceptibility severity numbers (mallard 76.8 etc.) | **CONDITIONAL** | MODELED p75 with n=1 study for mallard — show class + provenance, not the raw number, unless caveated |

---

## Remaining unresolved issues

1. **v1→v2 susceptibility migration** (grid/Compare/SpreadCyto/SpeciesDetail chips still read the legacy parquet, now labeled): a product-level migration decision, not a bug fix.
2. **`aphis_flocks` animals-affected** now lives only in `detection_count` (kept deliberately); if the UI ever wants "birds affected" as a metric it needs its own labeled presentation — never as detections.
3. **`verify_downloads` STATS expectations**: the earlier hardcoded expectations were already made data-driven (AGENTS 2026-11); current run green. No action.
4. **PhyloPic per-image licenses** remain unverified (many `license: null`) — still required before publishing animation frames.
5. **Corpus quotes ≠ corpus fulltext for Barber 2010** (no PDF in corpus): fine for citation; if the animation wants a Barber quote overlay, use Smith et al. 2015's sentence (in-corpus, verbatim-verified) instead.
6. **Panel gene count 1,427 vs 1,428** (older export): reflects current catalogue membership after alias/scope rules; both stats.json and by_the_numbers agree at 1,427; if the team wants the historical 1,428 explained, diff `gene_catalogue.json` against the 2026-10-10 backup.
7. **Migrating confidence display into EvidenceDrawer** (per-gene-page chips) — deferred; the phylogeny + clade drill-down now carry the distinction where the journeys need it.

## Test log (final)

- `test_animation_readiness.py`: **17/17 PASS** (2026-11-10)
- by-the-numbers: **23/23 PASS**
- Playwright tab-content + species-count-consistency: **6/6 PASS**
- Playwright phylo_gene_overlay (new): **3/3 PASS** — DDX58 banner reads "1,537 present · 312 fragment · 206 absent (36 high-confidence) · 2,055 species with calls"; IFITM3 reads 0 high-confidence; legend renders both confidence entries
- i18n_scan: 0; svelte-check: no substantive new errors (stash-diff verified)

## Files modified (complete list)

**Scripts:** `scripts/build_species_profiles.py`, `scripts/genes/build_species_index.py`, `scripts/genes/export_presence.py`, `scripts/export_web_data.py`, `scripts/model/build_vaccine_outcomes.py`, `scripts/model/build_susceptibility.py`, `scripts/build_susceptibility_scores.py` (docstring only), `scripts/fetch_phylogeny.py`, `scripts/papers/data_lit_bridges.py`.
**UI:** `web/src/lib/stores/i18n.svelte.js`, `web/src/lib/stores/db.js`, `web/src/routes/Species.svelte`, `web/src/routes/Phylogeny.svelte`, `web/src/routes/Clade.svelte`, `web/src/routes/Home.svelte`, `web/src/routes/Genomes.svelte`, `web/src/routes/Landscape.svelte`, `web/src/lib/components/species/SpeciesCard.svelte`, `web/src/lib/components/species/SpeciesDetail.svelte`, `web/src/lib/components/spread/CompetenceTable.svelte`, `web/src/lib/components/phylogeny/PhyloTree.svelte`.
**Data/metadata:** `data/papers/records/barber2010.json`, `long_anp32_2019.json`, `comparative_analysis_host_responses_2024.json`; `web/public/data/papers.json`; regenerated: species_profiles*, species_index.json, gene_catalogue.json, gene_presence.parquet, vaccine_outcomes, host_competence, species_susceptibility, phylogeny.json (metadata only — newick unchanged), data_lit_bridges.json, stats.json, by_the_numbers.json.
**New files:** `scripts/tests/test_animation_readiness.py`, `web/tests/phylo_gene_overlay.spec.js`.
**Animation exports regenerated:** all of `docs/animation/` (journey1/2/3 + CSVs + newicks unchanged in structure, numbers corrected).
