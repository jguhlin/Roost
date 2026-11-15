# Figure 2 — Design Brief v1 (literature synthesis figure)

**Status: BUILT — v2 (scientific-article redesign). Source:
`scripts/figures/make_fig2.py` → `figures/src/fig2_synthesis.svg` (+
caption sidecar) → `render_figure.py --export` →
`figures/export/fig2_synthesis.{svg,pdf,png}`. Review copy (unlisted):
`web/public/figures/fig2_review.html`. The old site figure
`fig2_epi_curve` is unrelated and untouched.**

v2 changes (over v1.1 — after review: "less infographic, more scientific
article"):

v2.3 de-infographizing: panel B labels now carry genes + papers only
("innate sensing — 59 genes / 64 papers") — edge counts removed from the
figure (kept in the caption); panel D's on-figure citation line removed
(refs live in the caption); the site URL removed from the stamp; the
"innate sensing → panel D" cross-reference removed; panel A carries the
bare panel letter (no descriptive title — the axes explain it); axis
labels use title case (Host Genes, Papers per Gene, Screened Host
Species).
- **A**: now a real matplotlib bar chart (house style, log y, count labels
  only) rendered at print scale and embedded (600 dpi PNG). All annotation
  prose removed from the figure — the 71.6% headline, top-gene list,
  species-link counts moved to the caption. Linear-share strip dropped.
  Bins are **enumerated** — every integer paper count 1–19, then ≥20
  (2,518 / 429 / 186 / 94 / 64 / … / ≥20 = 50) — with a build assertion
  that the enumerated bins sum to the registry total and the BTN buckets.
- **B**: unchanged.
- **C**: kept; edge label collision fixed ("10 quotes", halo'd, below the
  edge; no longer crosses the ANP32A→PB2 line).
- **D**: matplotlib horizontal stacked-bar chart (house style, 600 dpi,
  embedded like panel A) — DDX58 detection per bird order by evidence
  class (best call per species, orders with ≥6 screened H5N1-host
  species; 15 orders, 426 species): **annotated (E5)** / **putative —
  BLAST (E4)** / fragment (E3) / not found (E2). Galliformes bold with
  its E2 count labelled in-segment. Literature: one factual line with
  citations. Kicker removed. Mammals excluded (avian-reference search
  yields fragmentary mammalian alignments; Carnivora 0/36 "present",
  34 fragments = reference bias).
- **Alias discovery (important)**: the pipeline's Layer 0 matched NCBI
  gene records by exact symbol, but NCBI records RIG-I as **RIGI** in
  most bird taxa (e.g. *Anas platyrhynchos* "RNA sensor RIG-I") — so 74
  of 443 screened host species that ARE annotation-backed were
  miscalled E4-putative (the earlier "zero E5 anywhere" observation was
  this artifact). Fixes:
  1. `data/genes/gene_config.json` aliases now include RIGI / RIG-I /
     RIG-1 → DDX58 (the D28 canonical alias home).
  2. `blast_presence.py` Layer 0 is alias-aware (resolves NCBI symbols
     through the alias map) — future runs classify at the source.
  3. `scripts/figures/check_ddx58_annotations.py` re-derived annotation
     state for the 443 in-scope species (cached at
     `data/genes/ddx58_alias_annotation.json`, incremental/idempotent);
     make_fig2.py reads the cache and asserts coverage.
  Result: 74 annotation-backed + 289 putative across the panel; **no
  galliform has a RIGI record**, so the Galliformes gene-loss finding is
  now supported by both annotation absence and search absence.
- Caption absorbs all removed figure prose (top genes, species links,
  galliform detail incl. 15 high-confidence absences and the sole
  brush-turkey detection, ≤17%-in-every-other-order bound, refs).

## 0. The one message

> Integrating 1,300+ papers reveals where evidence is genuinely deep, and
> where dispersed studies converge on mechanisms invisible to any single
> publication.

Three-figure arc: **Fig 1** what Roost is · **Fig 2** what becomes visible
(this figure) · **Fig 3** where the gaps are.

## 1. Panels

| Panel | Content | Source artifacts |
|---|---|---|
| A | Evidence-depth long tail: log-count bars 1 / 2–3 / 4–9 / 10–19 / 20+ papers per gene; headline 2,518 (71.6%) single-paper vs 997 ≥2; top-5 genes; species-link counts | `data/papers/gene_registry.jsonl` (asserted == `by_the_numbers.json` landscape at build) |
| B | Six recurrent mechanism modules by independent papers: innate sensing 64, IFN response 40, apoptosis 16, cytokine/inflammasome 14, polymerase compatibility 12, endosomal entry 5 (261/299 edges classified) | `web/public/data/gene_relationships.json` (reviewed edges), deterministic precedence classification in-script |
| C | Positive control — canonical ANP32–PB2 barrier: ANP32A(+33aa)/B/E cards → PB2 node (10 evidence quotes on ANP32A–PB2 edge); PB2-E627K 179 papers, D701N 115, M631L (cattle) 52 | `gene_relationships.json` + `wiki_mutations.json` |
| D | Under-recognized — innate-sensing divergence: literature side (64-paper module; species-difference quotes: chickens lack RIG-I/DDX58+RNF135; duck RIG-I lacks K172; 7 module papers document species differences) vs genome side (DDX58 strip: absent across screened Galliformes — chicken, turkey, quail, pheasant, peacock, partridge; present in mallard, swan goose, eagle, zebra finch; 249/2,358 assemblies no-hit, 48 high-confidence) | `gene_relationships.json` + `gene_presence_v2.parquet` (build-time assertions: chicken E2, duck found) |

## 2. Count definitions (single source of truth)

- "Studied" genes = registry study-subject counts (`n_studied ≥ 1`); the
  build asserts registry distribution == BTN landscape — a drift fails the
  build (Numbers-page triage rule enforced mechanically).
- Module classification = **first-match precedence** over edge endpoints
  (sensing → IFN → apoptosis → cytokine → polymerase → endosome) with fixed
  regexes defined in `make_fig2.py`; each edge counts once. Paper counts are
  distinct `paper_id`s in a module's edge evidence.
- Panel C marker counts = `wiki_mutations.json` `paper_count` per canonical
  PB2 mutation.
- Panel D genome calls = best status per species across assemblies
  (E5 > E4 > E3 > E2) from `gene_presence_v2.parquet`; "absent" prints only
  for E2_searched_not_found.

## 3. Rejected panel-D candidates (documented so we don't re-litigate)

- **ER stress / UPR**: quote-text clustering suggested 15 papers, but
  head-level mechanistic edges = 3 (HSP90/NLRP3/NS1) — quote-mention
  inflation, not a module.
- **Lipid/cholesterol**: 5 noisy edges (vaccine-LNP and digestive-tract
  items) — not defensible.
- **Apoptosis** (16 papers): real but well-recognized pathology — kept as a
  landscape bar in B, not the value-add panel.
- Sensing divergence chosen because it converges from **two independent
  layers** (literature species-difference quotes + Galliformes-wide DDX58
  loss in the genome screen) — the claim is visible only in the integration.

## 3b. Panel D evidence classes (v2.2 — final user semantics)

The annotation's judgement stands alone; among BLAST detections the split
is whether the species' annotation exists at all:

| class | definition | count (panel scope) |
|---|---|---|
| via annotation | NCBI gene record under DDX58 or synonym (RIGI/RIG-I) — used as-is | 68 |
| BLAST — annotation misses it | full-length hit; taxon has NCBI gene records (n_records > 0) but not RIG-I | 120 |
| BLAST — no annotation | full-length hit; taxon has no NCBI gene records (putative) | 169 |
| fragment | partial hit | per order |
| not found | searched, absent | per order; Galliformes 16/19 (15 high-confidence) |

Encodings: all three detection classes are flat solid fills on a
corroboration-ordered teal ramp — #0f766e (annotation) → #14b8a6 (BLAST,
annotation misses it) → #5eead4 (BLAST, no annotation) — so a found gene
never looks missing; fragment #94a3b8 slate; not found ink. No borders or
hatching anywhere: the ramp (tailwind teal 700/500/300) is spaced in
lightness (L∗ ≈ 44 / 66 / 80) so the palest detection still holds
against the white ground, hue separates detections (teal) from partial
(slate) from absent (ink). Earlier treatments that read as absence —
hatching, then a border on the pale segment — were removed.
Chart polish: n= labels removed (x-axis carries counts), y-label pitch
increased (fig 1.98 in, bars 0.58, tick pad 2).

**Data plumbing for this split:**
1. `gene_config.json` aliases: RIGI / RIG-I / RIG-1 → DDX58 (D28 home).
2. `blast_presence.py` Layer 0 is alias-aware and no longer short-circuits
   — E5 evidence records `blast_status`/`blast_hit` as provenance (does
   not drive categories).
3. `check_ddx58_annotations.py` (v2): per-taxon NCBI re-check storing the
   synonym match AND `n_records` (taxon annotated at all?); cache at
   `data/genes/ddx58_alias_annotation.json`. 443 species: 74 RIG-I-matched,
   237 annotated taxa, 206 unannotated.
4. Parquet writes infer schema over ALL rows (blast_presence +
   parallel_runner merge) — the old 100k-row window silently dropped
   new evidence fields on tail-appended delta rows.
5. DDX58-scoped presence re-run — **COMPLETE (2026-10-12)**: 2,412
   genomes re-searched, 2,083 calls merged (parquet 2,948,316; +28 pairs),
   all three merge gates PASS (chicken NOT_FOUND/high, duck FULL, ANP32A
   chicken FULL). The parquet now natively carries the alias-aware
   tri-state: 185 DDX58 species at E5 (gene_id + "RNA sensor RIG-I"
   description + coordinates + blast_status/blast_hit provenance), 1,372
   E4 / 317 E3 / 217 E2 species best-calls. Panel D rebuilt from the
   parquet — categories held: via-annotation 68, BLAST-annotation-missed
   119, BLAST-no-annotation 169 (429 panel species, +3 with fresh calls);
   Galliformes 16/19 not-found, 15 high-confidence. Site sync pass:
   by_the_numbers.json rebuilt (18/18 checks green), all three figures
   regenerated on the new freeze.

## 4. Verification record

`svg_text_lint.py` CLEAN · audit_figure PASS · OCR of the rendered export
confirms all panels, numbers, chips and sources · build-time assertions:
registry == BTN, chicken-DDX58 absent, duck-DDX58 found, chip labels
pinned (chicken absent / mallard present / both states) · no model here can
view pixels — eyeball pass via the unlisted review page.

## 5. Refresh

```
pixi run python scripts/figures/make_fig2.py \
  && pixi run python scripts/figures/render_figure.py \
       figures/src/fig2_synthesis.svg --export
```

Any figure-vs-site disagreement → rebuild, never hand-edit.

## 6. Open

1. Human eyeball pass (review page).
2. If reviewers want a fifth "scattered/single-edge observations" bar in
   panel B (the 38 unclassified edges), the data is already computed.
3. Possible upgrade: replace panel D's quote cards with per-quote source
   links (paper chips) once the record pages expose stable anchors.
