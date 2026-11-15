# Landscape Pipeline — Refresh Tracker

Working checklist for the research-agent pipeline that feeds the landscape
page (`#/landscape`), contradictions page, and briefings. Companion doc:
[RESEARCH_AGENT.md](RESEARCH_AGENT.md) (agent internals) ·
[FIGURE_AGENT.md](FIGURE_AGENT.md) (figure system).

Rule: update this file at the start and end of every stage. Baseline counts
below were measured 2026-10-04 before the refresh began.

## Baseline (2026-10-04, pre-refresh)

| Asset | Count | Source |
|---|---|---|
| PDFs awaiting intake | 48 (517 MB) | `pdfs_to_process/` |
| Papers pending enrichment | 10 | `enrich_pipeline.pending_papers()` |
| Typed claims → clusters | 9,983 → 1,184 | `typed_claims.parquet`, `claim_clusters.parquet` |
| Contradictions | 995 (44 real / 119 apparent / 832 context) | `contradictions.json` (Oct 3) |
| Open questions | 4,974 (scored, 1,171 clusters) | `scored_questions.parquet` (Oct 4) |
| Briefings | 23 (16 gap reports); 94 `own_briefing` meta-questions queued | `research_briefings/` (Oct 3) |
| Landscape digest | built Oct 3 13:42 | `research_landscape.json` |

LLM: muse-glimmer-30b @ `127.0.0.1:8005/v1` (up) · searxng :8888 (up).
Env: `LLM_MAX_TOKENS=8192` required for briefings/synthesis.

## Queue (dependency order)

### Stage 1 — Intake + enrichment  ✅ DONE (2026-10-04)
- [x] 1a. `process_new_papers.py` — **0 new papers**: all 45 PDFs were
      already registered (duplicates); 1 deferred (`science.aem0441.pdf`, no
      DOI — manual review); skipped PDFs remain in `pdfs_to_process/` and
      re-skip harmlessly.
- [x] 1b. `enrich_pipeline.py` — complete:
      - phenotypes: complete → 778 species rows normalized (691 resolved,
        46 unresolved → `species_alias_unresolved.json`)
      - **mechanisms: 387-paper backlog cleared** (719 → 1,106 papers with
        mechanism extraction; ~55k mechanisms chunked)
      - 7-field enrichment: 0 pending · claim typing: 0 new (1,073 done)
      - tail of pipeline auto-ran: contradictions re-export (**unchanged
        995** — no new typed claims), `build_aggregation` rebuilt
        `research_landscape.json` (17:21), validation gate passed
        (1,323 paper IDs valid; 4 intake-ledger log warnings only)
- End-of-stage delta: corpus grew only in mechanisms; claims/contradictions
  unchanged → **Stage 2 (re-cluster/adjudicate) NOT needed** until new
  papers arrive. Stages 3–5 still worthwhile for briefings + digest.

**Manual review queue**: `science.aem0441.pdf` (deferred, no DOI) —
identify + register by hand or discard. Also: 46 unresolved species names
in `species_alias_unresolved.json` (curate into `species_alias_curated.json`).

### Stage 2 — Contradiction refresh (after 1) — SKIPPED this cycle
- [x] no new typed claims → re-cluster/adjudicate unnecessary; pipeline tail
      already re-exported `contradictions.json` (unchanged: 995 / 44 real).
- [ ] next run WITH new papers: re-cluster typed claims →
      `llm_claims_adjudicate.py` → `contradictions.json`

### Stage 3 — Re-score open questions (after 2)  ✅ DONE (2026-10-04)
- [x] `score_open_questions.py` — 4,974 questions re-scored
      (scored_at 2026-10-04T05:01Z). New top-5:
      1. 5.0 — Rate/antigenic impact of HA evolution in 2.3.4.4b vs WHO
         candidate vaccine viruses
      2. 5.0 — Inter-clade reassortment within 2.3.4.4b, geographic +
         temporal distribution
      3. 4.7 — Mammalian-adaptive markers (PB2-E627K/D701N/S714R…) and
         species barriers
      4. 4.7 — Timing + geographic origin of initial EA-2024-D1… introduction
      5. 4.6 — Persistence/absence of PB2 mammalian markers in H5N1
      Theme: clade 2.3.4.4b evolution + mammalian adaptation dominates.

### Stage 4 — Briefings (after 3)  ← RUNNING
- [x] 4a **wave 1** — 5 new briefings on the 2.3.4.4b cluster (3 full + 2
      gap): HA evolution vs CVVs, inter-clade reassortment (Egypt/E-Asia),
      EA-2024-D1 origin timing, PB2 markers ×2. Derived layers refreshed
      (links 122→181 across 10 briefings; synthesis 21 themes incl. a
      5-briefing ANP32A/2.3.4.4b mega-group; index 26, newest-first).
- [~] 4a **wave 2** — running with figure-proposal code; executor runs
      automatically after
- [ ] 4b. `--meta-briefings` — drain the queued `own_briefing` questions
- [ ] 4c. `--discover-papers` on the gap-report topics
      → `discovered_papers.jsonl` for the next intake cycle

### Stage 5 — Digest rebuild + gate (after 4)
- [ ] `pixi run python scripts/papers/build_aggregation.py`
      → `research_landscape.json`, `gene_evidence/`, `pathway_edges.json`
- [ ] `pixi run python scripts/papers/validate_paper_refs.py` (must pass)

### Stage 6 — Synthesis layer (new work; 6a/6b after 4, 6c/6d anytime)
- [x] 6a. **Cross-briefing synthesis** — `synthesize_briefings.py`: groups =
      connected components over shared [paper_id] citations (≥2); one LLM
      card per group → `research_synthesis.json` (19 themes); 🧠 Synthesis
      tab on the landscape page (D164 ad790610).
- [x] 6b. **Contradiction ↔ briefing cross-links** —
      `link_contradictions_briefings.py`: 122 links / 7 briefings / 78
      clusters; chips on landscape + section on research pages.
- [x] 6c. **Gap ledger** — `gap_ledger.py`: baseline 12 open gaps;
      run-over-run open/close diffs once the pipeline refreshes.
- [ ] 6d. **Data-vs-literature bridges** (deterministic) — species
      susceptibility table vs `paper_species_traits`; `GENE_PRESENCE_LOG`
      vs `gene_evidence` coverage
- [ ] 6e. wire `discovered_papers.jsonl` → auto-intake (see RESEARCH_AGENT
      §Extending)

## Parallel (non-pipeline) work in flight

- Togo + Servier asset mirrors (`mirror_togo_servier.sh`) — on completion:
  rebuild `assets/manifest.sqlite`, regen `docs/ASSET_CREDITS.md`, update
  FIGURE_AGENT.md §23 counts, commit D164.
- Vite dev server on :5177 (background task).

## Log

- 2026-10-04: tracker created; Stage 1 launched (48 PDFs + enrichment).
- 2026-10-04: 1a done — 0 new papers (45 duplicates, 1 deferred, see queue);
  fixed enrich_pipeline.py env-merge bug (TypeError when LLM_MAX_TOKENS
  already set); 1b relaunched.
- 2026-10-04: 1b done — 387-paper mechanism backlog cleared, 778 species
  rows normalized, contradictions re-export unchanged (995), landscape
  digest rebuilt, validation gate ✓. **Paused here per plan** — resume at
  Stage 3 (re-score; Stage 2 skipped, no new claims).
- 2026-10-04: Stage 3 (re-score) launched in background; in parallel, figure
  system wired into research pages: publish_figure.py + figures registry +
  Figures & media section in Research.svelte; first figure
  (fig-qinghai-mortality) + first video abstract (qinghai-mortality) built
  for the Qinghai Lake briefing. Briefings (Stage 4) deferred until the
  figure/video integration is complete.
- 2026-10-04: Stage 3 done — 4,974 re-scored; top theme 2.3.4.4b HA
  evolution + reassortment + PB2 mammalian markers. Media pipeline landed
  (D164 8d781361): publish_figure.py + Research.svelte media section +
  first figure + first fframes video abstract on the Qinghai briefing.
- 2026-10-04: media onboarding continued (D164 9fc79376): ANP32A species-
  barrier diagram (validated SVG + imported NIH BioArt icons) and PB2-E627K
  host figure on their briefings; fixed pre-existing briefing hash-nav
  staleness (slug-keyed $effect). 3 figures + 1 video live across 3 pages.
- 2026-10-04: (D164 113959d4) gap-map figure type introduced — fig-mhc-gap-map
  + fig-cytokine-gap-map on their gap-report briefings; ANP32A video abstract
  (14s). Totals: 5 figures + 2 videos across 5 briefing pages.
- 2026-10-04: (D164 440fbda3) spec-driven gap-map generator — all 16 gap-report
  briefings now have figures. Totals: 18 figures + 2 videos across 18 pages.
- 2026-10-04: (D164 5f1f61a1) four full briefings get real figures (mortality
  burden log-bars, ANP32 isoform matrix, dispersal 3-panel, B3.13-vs-D1.1
  comparison cards). **22/23 pages with media** — only the 1-section Qinghai
  species-barrier gap report remains (skip or fold into sibling page).
- 2026-10-04: (D164 ad790610) Stage 6 a/b/c landed: LLM cross-briefing
  synthesis (19 theme cards), 122 contradiction↔briefing links, gap-ledger
  baseline. Landscape page: Synthesis tab + media/conflict chips. Research
  pages: linked-contradictions section. Remaining: 6d bridges, 6e auto-intake.
- 2026-10-04: (D164 8e4d4c85) **design-system refinement pass**:
  FIGURE_DESIGN.md (type scale, tokens, icon policy, video beats, review
  checklist) + figures/style.py; flagships reworked (qinghai numbers-first
  v2, ANP32A v2 with real virus icon, PB2-E627K v2); all 15 gap maps
  regenerated in style; qinghai video v2 (hook/tension/resolution/outro).
  Follow-ups: migrate fig-mortality-burden/dispersal/anp32-isoforms to
  style.py; ANP32A video still v1 beats; music bed for videos.
- 2026-10-04: (D164 5353c62f) **editorial pass**: docs/MEDIA_PLAN.md —
  per-page answers to does-a-figure-help / best-type / how-many / video-use;
  credit-everything policy live on pages (CC0/PD credited anyway);
  dispersal stat panel → schematic map; cattle page gets 2nd figure
  (timeline). Videos deliberately withheld on pages where motion adds
  nothing (PB2, isoforms, burden).
- 2026-10-04: agent loop closed end-to-end (D164 37c0e167): search_figure_assets
  tool, figure_proposals in synthesis, deterministic executor. Person icon
  dropped from ANP32A figure (61c7eb18); ANP32A video → 2m48s educational
  explainer (264edded). Wave 1: 5 briefings (731b3bf3).
- 2026-10-04: **wave 2 closed the agent→figure loop** (D164 0984f23a):
  briefings carry figure_proposals; executor auto-rendered 2 gap maps
  (PB2 markers 4×3, HA-vs-CVV 4×4) onto their pages. Known issue: the
  autonomous picker re-investigates already-briefed questions — dedup
  against recent briefings is the next agent improvement.
- 2026-10-04: (D164 02a08568) both wave-2 briefings have explainer movies via
  make_explainer.py (codegen bugs fixed: Rust float literals, dot braces).
  Media totals: 27 figures + 4 videos; 2 briefings carry the full
  agent→figure+movie loop.
