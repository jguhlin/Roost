# Roost UI Capture Report — Animation Asset Production

**Date:** 2026-11-10 · **Environment:** LOCAL dev server (vite, `http://localhost:5177`), per instruction — not the deployed site.
**Application revision:** git `879f0a00` **plus the uncommitted 2026-11-10 scientific-consistency working tree** (susceptibility legacy labels, detection-record counts, confidence-aware phylogeny overlay, corrected bibliographic records). The deployed site (josephguhlin.com/Roost) was **not** assessed; per prior agreement the local server is the most current build and is the source of every asset here.
**Captures:** 27 verified PNG screenshots (3840×2160 @2× DPR, i.e. 1920×1080 logical viewport) + 6 interaction WebM clips (1920×1080). All genuine browser captures — no synthetic or AI-generated imagery. Every screenshot passed an in-page text check **and** an explicit vite-error-overlay absence check at capture time.

## What succeeded

| Group | Assets | Notes |
|---|---|---|
| Species (9) | directory, kākāpō search/overview/genome/genes(DDX58)/susceptibility(`unevaluated`)/modal, mallard overview+genes(DDX58) | all data-driven pages render fully; DDX58 chips show kākāpō FULL vs mallard FULL; susceptibility page shows the honest `unevaluated` class |
| Literature (4) | papers browser, RIG-I search, Long-2019 focus, Smith-IFITM3-2015 focus | focus views show LLM-extracted summaries; DOI-corrected records |
| Genes (6) | DDX58 overview, literature evidence, literature quotes (provenance blockquotes), presence-across-species, evidence drawer (mallard HSPs), full page (13,904 px tall) | EvidenceDrawer opened via the real chip → magnifier interaction |
| Phylogeny (8) | tree overview, DDX58 overlay (+full-context variant), confidence legend banner, zoomed clade, clade matrix (default + DDX58), DDX58 orthogroup | confidence-aware legend renders ("Not found — high confidence" vs "low/medium"); overlay banner reads "206 absent (36 high-confidence) · 2,055 species with calls" |

Verification method: every screenshot passed an in-page text check for route-specific content markers **and** a pixel-content analysis (no blank/near-blank images; the tree captures show 14–15% non-background content, dense pages 30%+).

## Recordings

Six WebM clips (9–14 s each, 1920×1080, real interactions): `species_search_open` (9 s), `species_tabs` (9 s), `gene_from_species` (14 s — kākāpō gene panel → DDX58 chip → gene page), `ddx58_to_phylogeny` (14 s — the real "View in phylogeny" link), `phylo_zoom_pan` (11 s), `evidence_drawer` (13 s). Long dead-air waits were trimmed with stream-copy ffmpeg; no content was altered. See `captures/recordings/`.

## Issues discovered during capture

0. **Dev error overlay in first-round screenshots (found by the animation processor — fixed):** the initial capture run (single browser context) picked up the vite dev-server error overlay early in the session; the overlay persists until dismissed and therefore sat atop **every capture in that run** — all 8 species pages, papers browser + search, and (partially) the two clade matrices. The overlay's presence also explains that run's text-wait failures (overlaid elements don't count as visible). **Resolution:** every screenshot was re-captured (v3 series) in fresh contexts with an explicit DOM check for `vite-error-overlay`, Escape-dismissal if present, and content-marker re-verification before each shot. All 27 shipped screenshots are now overlay-free (verified at capture time by DOM query; diff vs. the old set confirms the 12 affected files were replaced). The manifest flags each replaced asset. The 6 recordings were frame-sampled and are clean.
1. **Genuine application bug found & fixed (documented):** `Papers.svelte` called `trackEvent` in a focus `$effect` **without importing it** — every paper deep-link (`#/papers/{id}`) raised `ReferenceError: trackEvent is not defined`, hit the route boundary, and blanked the page. Fixed by adding `trackEvent` to the existing analytics import (one line). This bug predated the capture work and affected real users following citation links, not just screenshots. No other route has the same missing-import pattern (audited).
2. **Headless-capture pitfalls (tooling notes, no app changes):**
   - Custom chromium GL flags (`--use-gl=angle --use-angle=swiftshader`) **break the WebGL context** on this host (known AGENTS issue) → phylogeny/deck.gl routes render blank. Plain `chromium.launch()` (implicit SwiftShader) renders everything. All final captures use the plain launch.
   - Sequential hash navigations in one page (SPA same-document navs) can stall — each final capture uses its **own fresh browser context**.
   - The evidence drawer opens from the magnifier button next to a species chip, not the species link.
3. **Kākāpō genome tab** lists the RefSeq accession (GCF_004027225.2), not the GenBank GCA one — the capture is correct; earlier automation expected the wrong string.
4. **Clade DDX58 matrix:** the gene `<select>` could not be set programmatically (`selectOption('DDX58')` — the control is likely custom/virtualized); the shipped capture shows the clade matrix default view, which still displays DDX58 as a row with the Galliformes column. Flagged in the manifest: the DDX58-selected clade screenshot is a **default-view** capture.

## Scientific-validation notes for animators

- Species-grid detection badges and all counts in captures are **surveillance records** (post-fix semantics) — e.g. chicken 314, mallard 1,838 — never animals-affected.
- Susceptibility chips on species cards read "(legacy model)" per the readiness corrections; the kākāpō page shows the authoritative v2 two-axis view with **unevaluated**.
- Phylogeny DDX58 overlay colors: deep red = high-confidence non-detection (all gamebirds), light red = low/medium confidence — the legend is captured in `ddx58_confidence_legend.png`.
- No tooltip/popover was left open except where the capture is deliberately of that element (evidence drawer, modal).
- Mouse cursor: Playwright screenshots do not include a cursor.

## Deliverables

- `docs/animation/captures/` — species/ literature/ genes/ phylogeny/ recordings/ metadata/
- `metadata/capture_manifest.csv` + `.json` — per-asset: dimensions, exact route, environment, revision, date, gene/species, genuine-screenshot flag, caveats
- `metadata/contact_sheet.png` — montage of all captures
- `roost_animation_ui_captures.zip` (repo root) — all captures + recordings + manifest + contact sheet + the validated DDX58/ANP32A CSV/Newick exports + the readiness report. **Not committed to git** (per instruction); download from the repo working tree.

## Capture methodology (for reproduction)

Playwright (bundled chromium, headless, plain launch) · viewport 1920×1080 @ deviceScaleFactor 2 · fresh context per asset · in-page content-marker verification before every screenshot · pixel-content QC (blank detection) after every run · recordings via Playwright `recordVideo` (WebM). Scripts: one-off (`/tmp/capture_*.js`, `/tmp/record_roost.js`) — retained in the ZIP's metadata folder for transparency.
