# Roost Intake Protocols

Every class of incoming data has a defined intake pipeline. **Never skip steps** —
each protocol exists because a failure mode was hit and fixed (see GENE_PRESENCE_LOG.md
for decision history). This document is the operating manual.

---

## 1 · Paper Intake (PDFs → verified wiki evidence)

> Full architecture: [DECISION_PIPELINE.md](DECISION_PIPELINE.md) —
> typing → dedup → two-pass extraction → metadata → scope routing →
> policy-driven destinations. Scope routes, never excludes.

**Drop folder:** `pdfs_to_process/` — anything there gets processed.

### The TWO-PASS system (learned the hard way — D32, 2026-09-01)

| Pass | Speed | What it does | What it does NOT do |
|------|-------|--------------|---------------------|
| **Fast pass** — `process_with_llm.py` | ~25 s/paper | PDF→markdown, paper matching, LLM summary, **regex** entity extraction (analyze_single.py, 0 LLM calls) | No verified roles/findings; gene detection limited to known patterns |
| **Full pass** — `pixi run analyze-papers-llm --skip-verified` | ~10 min/paper | 7-step extraction × verification with retry (metadata, study, genes, species, mutations, findings, novelty) | — |

**Protocol:**
1. Drop PDFs → run fast pass (batch, ~50 min/139 papers) → immediate corpus availability
2. **Always schedule the full pass next** — background, 18 h budget, resume-safe (`--skip-verified` skips the `data/papers/verified/` markers)
3. If the full pass times out: relaunch; it resumes where it stopped
4. Convert any stragglers: `convert_analyses.py` — falls back to regex provenance **honestly stamped** (`verified: false, method: regex_extraction_v1`)
5. Rebuild wiki: `build_wiki_pages.py` → pages regenerate with citations
6. **NEVER stamp regex output as verified.** The false-stamp incident (D32) is why this doc exists.

### Typed intake (D48) — corrections, theses, news
The fast pass classifies each PDF before processing (`detect_doc_type`):
- **correction/erratum/retraction**: attached to the parent paper via
  `data/papers/corrections.json` + `{pid}_correction.md`; PDF archived to
  `data/papers/correction_pdfs/` — NEVER deleted like plain duplicates
- **thesis/dissertation**: processed normally, markdown tagged
  `<!-- doc-type: thesis -->` — not peer-reviewed; synthesis weights venue.
  VALUED for deep background chapters (stronger reviews than papers) —
  mine them for model context, cite as theses
- **foreign-language docs**: full pipeline handles them (multilingual LLM).
  Non-Latin titles get an English `title` with the original preserved in
  `title_original` (LLM translation, batch script or manual). Cyrillic
  titles also normalise to EMPTY strings in the dedup matcher — the
  empty-guard (D51) exists because of this; never remove it
- **news clips**: routed to `docs/news_md/{date}_{slug}.md` per §3 — never
  the paper pipeline

### Supplemental data files + odd-pile triage (D120)
- **`.xlsx`/`.xls`/`.csv` in the drop folder are supplement intake**: structural
  preview (fastexcel) + LLM classification (`content_class`, join keys,
  `ingest_candidate`: detections|wahis|null) → staged under
  `data/supplements/{manuscript-code}/` with `preview.json` + `classify.json`.
  Nothing auto-joins the species models — ingest candidates are flagged for
  deliberate later use. Heuristic column-name fallback when the LLM is down.
- **`_deferred/` odd pile**: conversion failures, odd non-paper docs (one
  cheap LLM classify call: poster/map/datasheet/…), and papers whose ID
  generation can't run (LLM down) are moved here + ledgered — never
  force-fitted, never deleted.
- **Intake ledger** `data/papers/intake_ledger.jsonl`: every disposition
  (paper/correction/thesis/news/supplement/deferred/duplicate) with
  classifier + reason. Review: `process_with_llm.py --ledger-report`.
- **Duplicates are archived to `_already_matched/`, never deleted** (this
  section always said that; the code had drifted to unlink).
- **DOI content-matching is HEAD-ONLY (first 3000 chars)**: reference-list
  DOIs at the tail made 8 citing papers falsely match one heavily-cited
  corpus paper. The D120 incident (unintended partial run with the LLM
  endpoint down) is recorded in `data/papers/recovery_needed.json` — 21
  junk-ID papers restored to the drop folder, 14 files need re-download.
- `--dry` classifies/previews and moves nothing. LLM-down never mints
  junk IDs (`paper_2024_*` debt was D92's rename job; never again).

### Matching & dedupe
- Filename → paper ID → DOI → title-fuzzy; unmatched papers get LLM-generated IDs (`input_YYYY_N`)
- Content-matched duplicates of already-analysed papers are skipped and archived to `pdfs_to_process/_already_matched/`
- **Metadata debt:** auto-ID'd papers have thin titles — a metadata backfill pass (DOI lookup) is worthwhile quarterly

### Discovery hook (novel genes)
After every full pass: generate the **"mentioned but never searched"** report —
corpus genes absent from the 592-panel are discovery candidates with citations.
(This is the cheapest novel-gene-discovery instrument — see GENE_PRESENCE_LOG D36 plan.)

---

## 2 · Detection / Case Intake (surveillance)

**Existing automation:** `pixi run refresh` — WAHIS API, WHISPers, FAO, OCIMS,
NZ MPI, Wildlife Health Australia → `ingest_detections.py` → normalized store.

**Protocol:**
1. Run `pixi run refresh` (idempotent; dedupes by source+date+species+location)
2. `freshness_check.py` — alerts on stale sources
3. `integrity_check.py` — validation gates
4. Re-export web data (`export_web_data.py`) + rebuild species index (`scripts/genes/build_species_index.py`)
5. New species with cases appear automatically (taxonomy join); run
   `fetch_phylopic.py` for new silhouettes (resume-safe)

**Adding a new source:** model on `add_wahis_detections.py` — write an adapter
that normalizes to the detection schema (species scientific name, date, location,
strain, source tag), then add to `refresh_all.py`.

---

## 3 · News Intake (protocol defined; pipeline TBD)

**Drop folder:** `docs/news_md/` — markdown clips of news/reports.

Standards for a news clip:
- Filename: `YYYY-MM-DD_slug.md`
- Must contain: date, source outlet/org, URL, and quoted key claims
- **News is NEVER wiki evidence on its own** — it links to species/countries but
  carries no gene/mutation claims unless the claim cites a paper (then intake that
  paper instead)
- Lab-confirmation status must be preserved ("suspected" vs "confirmed") — news
  is the only channel that often breaks suspected cases before official reports

Pipeline (when built): news_md → LLM extract (species, location, date, claim,
confirmation status) → pending-verification queue → auto-match against later
official case intake (a news item that never gains official confirmation gets
retired, not deleted).

---

## 4 · Genome Intake (new species / assemblies)

**Protocol (order matters):**
1. `fetch_genomes.py` — download assembly + build blastdb + diamond ORF db
2. `select_genomes.py` — panel membership/roles
3. Presence: `blast_presence.py` (L0 annotation + L1 blastn + L2 DIAMOND) → `gene_presence_v2.jsonl`
4. Comparative: `extract_batch.py` → `align_and_tree.py` → `mcl_cluster.py`
5. Evidence: `export_evidence.py` (DIAMOND HSPs + blastn exon tracks —
   blastn results cached per genome in `rna_hits.tsv`, keyed on panel version;
   reference changes invalidate automatically)
6. Browser assets: `prepare_igv.py` (faidx + ORF coords + web staging) and
   `fetch_gffs.py` (NCBI annotation overlay; GCA assemblies may legitimately have none)
7. Web: `export_presence.py` → `build_species_index.py` → build

**Caution:** a new assembly can flip calls — always re-run the full presence
chain for the new species only, and note changes in the log.

---

## 5 · Gene Panel Intake (new genes)

1. Add to `data/genes/gene_config.json` (functions, impact_if_absent, importance
   overrides, wiki_aliases) — config-driven, no code edits
2. References: `build_references.py` (duck-first, chicken fallback; strict symbol verification)
3. Run presence chain (§4 steps 3-5) for the new genes across all genomes
4. `export_presence.py` picks up config automatically

**Panel-version discipline:** every change bumps `panel_version`; calls record it.

---

## 6 · Quarterly hygiene

- [ ] Metadata backfill for auto-ID'd papers (DOI/title/year)
- [ ] `fetch_uniprot_functions.py` (resume-safe; refreshes stale accessions)
- [ ] `fetch_phylopic.py` (new silhouettes since last run)
- [ ] Re-run "mentioned but never searched" discovery report
- [ ] Layer-0 re-validation status check (annotation-integration bugs — see D35)
- [ ] ImmunomeDB vintage-layer reconfirmation (D17) for newly added genomes
- [ ] i18n health: `pixi run python scripts/i18n_check.py` — unwired strings,
      orphaned keys, paper-translation gaps; fill gaps with
      `pixi run python scripts/papers/translate_papers.py --all` (incremental,
      only new papers/findings/roles get translated)

### Paper translations (D71)

All paper-linked text is translatable and stored per-language, keyed by paper
identity (never inline in papers.json — metadata-fix scripts rewrite that file
regularly and must not carry translation state):

- `web/public/data/i18n/papers/{lang}.json` — `papers` (id → title/summary/
  cited_for), `topics` (shared vocabulary), `findings`/`conclusions`/`roles`
  (content-hash → translation; the `fh` field stamped into wiki_genes.json at
  export time is the lookup key)
- Content-hash keying means translations survive wiki regeneration and
deduplicate automatically; orphans (deleted papers / stale text) are flagged by
  `i18n_check.py`
- Run after each paper intake batch: `translate_papers.py --lang XX` or `--all`
- Frontend helpers: `pt(paperId, field)` for paper fields, `ptopic(topic)` for
  vocabulary chips, `ft(fh)` for findings/roles/conclusions — all fall back to
  English silently

---

*Last updated: 2026-09-01 — after the false-verification incident (D32) and the
GFF overlay build (D35). Keep this file current when protocols change.*

### Gene-recall tier architecture (D40, 2026-09-01)

Three complementary catchment tiers for corpus → gene attribution:

| Tier | Mechanism | Catches | Runs |
|------|-----------|---------|------|
| 1. LLM extraction (verified) | 7-step prompt now asks for central/supporting/background tiers + "siblings discussed alongside" + full panel-symbol checklist appended to the prompt | Novel genes (free-form) AND known-but-peripheral (JAK2-style) | Full pass per paper |
| 2. Text-scan (wiki builder) | panel symbols regex-counted in every markdown (≥3) → honest "discussed in text" evidence, `via: text_scan` | Panel genes missed by extraction | Automatic on every wiki build |
| 3. Regex fast-pass (analyze_single) | GENE_PATTERNS hardcoded list | Known genes only, fast triage | Fast pass per paper |

Re-extraction note: existing 272 verified analyses predate the improved
genes prompt; a full re-run (~20 h, backgroundable) upgrades recall if
needed. Text-scan already retro-covers panel genes (13 caught in D39).

### Paper asset registry (D50)
`build_paper_registry.py` → data/papers/paper_registry.json (INTERNAL —
never export to web/public or the downloads dumps): per-paper canonical
PDF path + md5, markdown path, correction PDFs/markdowns, dedup ledger
sources, news-clip shelf, and orphan flags. Rebuild after any batch.
Current: 635 papers (635 PDFs + 635 MDs, zero orphans), 2 corrections,
2 news clips.

### Copyright posture (D49)
- **Cite, never republish.** Book chapters (Avian Immunology et al.) are
  internal mining material: full markdowns live in docs/papers_md/ ONLY —
  never copy them (or passages beyond fair-use quotes) into web/public/.
- The website publishes: citations (title/editors/publisher), LLM-extracted
  findings/roles with attribution, and short grounded passages from OPEN
  papers we hold. Extracted knowledge is transformative; raw text is not.
- Credits page cites every reference work.

### Corpus search (ripgrep)

All 272 papers are markdown (`docs/papers_md/`, ~20 MB) — full-text search:

```bash
# papers mentioning a gene
rg -l -i "OASL" docs/papers_md/

# count mentions per paper (top hits)
rg -c -i "RIG-I" docs/papers_md/ | sort -t: -k2 -rn | head

# phrase + context
rg -i -C2 "duck OASL" docs/papers_md/ | less

# restrict to NZ species
rg -l -i "kākāpō|kakapo" docs/papers_md/

# every mention of a mutation
rg -c "E627K" docs/papers_md/ | sort -t: -k2 -rn | head
```

Files prefixed `_dup_` are duplicate-drop PDFs kept for search completeness
(their canonical analyses live under the matched paper ID — see the
`_already_matched` mapping in the pipeline logs).

### Context mining (D41) — rg + LLM

`scripts/papers/mine_context.py` — ripgrep the corpus for any gene/species/term,
then the local LLM explains the CONTEXT of each mention (passage-grounded,
2-4 sentences per paper, no invented details). Results to
`data/papers/context_mining/{term}.json`.

```bash
pixi run python scripts/papers/mine_context.py --gene JAK2 --top 5
pixi run python scripts/papers/mine_context.py --species kakapo
pixi run python scripts/papers/mine_context.py --term "duck OASL" --dry  # rg only
```

Note: the gemma server serialises — mine while no paper digest is running,
or expect slow responses. Reasoning-model quirk handled (content may arrive
via reasoning_content at low token budgets).

Duplicate policy (updated): duplicate PDFs are matched, logged to
`data/papers/dedup_log.txt`, and DELETED from the drop folder — no extra
copies kept anywhere (markdown search copies of the old 10 remain as
`_dup_*` files).

### LLM servers

| Server | URL | Model | Notes |
|--------|-----|-------|-------|
| aoraki44 (sglang, strong) | `http://localhost:8005/v1` (SSH tunnel to aoraki44) | `muse-glimmer-30b` | **SSH tunnel required** — localhost:8005 forwards to aoraki44:8005 (hostname doesn't resolve). ⚠ If this server is unreachable: the tunnel has dropped — remind the operator to re-establish it before debugging anything else. 131k context. Preferred for synthesis + full digests. |
| local gemma | `http://localhost:8001/v1` | `gemma4-31b` | Reasoning model (content may live in reasoning_content). Conservative — declines synthesis under grounding regime. Fine for fast-pass summaries. |

Point tools via `--url http://localhost:8005/v1 --model muse-glimmer-30b`.

### Model maintenance (D46)

The avian H5N1 response model is config-driven:
- `data/model/avian_h5n1_model.json` — stages, axes, gaps (edit here, not in code)
- `/model` page renders from it; badges overlay live from gene_evidence_counts
- `scripts/model/mine_model_nodes.py` — per-node context packs
  (dry-run done: 54 nodes — 34 well-studied, 5 single-study, 3 mentions-only,
  12 gaps). LLM mode (--top N) fills explanations when the server is free.
- After paper batches: copy updated model JSON + evidence counts to
  web/public/data; badges + node statuses refresh automatically.

### papers.json structure guard (D63)
papers.json MUST always be `{"papers": [...], "categories": [...]}` — a dict
with a "papers" key. Scripts that write `json.dump(papers_list, ...)` instead
of `json.dump({"papers": papers_list}, ...)` corrupt downstream consumers.
If you see `TypeError: list indices must be integers, not str` from any
pipeline script, papers.json has been flattened. Fix:
```python
data = json.load(open("web/public/data/papers.json"))
if isinstance(data, list):
    json.dump({"papers": data}, open(...))
```
