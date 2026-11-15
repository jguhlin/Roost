# Figure 1 — Design Brief v3 (Roost overview figure)

**Status: BUILT — v3.2. Source: `scripts/figures/make_fig1.py` →
`figures/src/fig1_overview.svg` (+ caption sidecar) → `render_figure.py
--export` → `figures/export/fig1_overview.{svg,pdf,png}` (2400 px wide =
333 dpi at 183 mm). Panel C is REAL as of v3.2: two live-site captures
embedded (ANP32 explorer + ANP32A record evidence card), callout anchors
derived from capture-time DOM geometry (no pixel inspection).**

History: v1 wireframe (4 panels, card-based) proved the content fits; v2
tightened counts; **v3 replaced the visual grammar** after review — boxes →
typography, streams, one dominant anchor object, real biology in the record
panel, three panels instead of four. **v3.1 review fixes:** stats rendered as
three measured columns (build-time Lato metrics — collision-proof against
number drift); hero 46 px (ROOST stays the strongest object); Panel A
sub-lines 15 px; verb set is now all-result nouns — *literature evidence*
(+ small `via agents + QA` annotation) / *species × occurrence* / *presence +
orthology*; bird & mammal strips carry their own outcome lines (*supports
avian polymerase* / *does not support avian polymerase*) so arrow geometry
no longer implies symmetric causation; `contributes to host range`;
`extracted evidence mentions`; Panel A title → "from fragmented **evidence**
to host-side knowledge".

## 0. The one message

> **Roost turns 1,366 papers and 3,894 genome assemblies into a traceable map
> of host genes, mechanisms and species relevant to H5N1 — every claim
> traceable to its source.**

Three-figure arc: **Fig 1** what Roost is and connects · **Fig 2** what
becomes visible in the literature (full ANP32/PB2 polymerase story —
deliberately saved) · **Fig 3** cross-species blind spot.

## 0b. v3 composition rules (from review)

- **ROOST is the visual anchor** — a single filled navy object; the product
  of the figure, not an endpoint chip.
- **Three data universes feed the anchor** — streams as typography + icons +
  curved arrows, never equal-sized card rows.
- **Scale lives inside Panel A** as typography beneath the anchor (no KPI
  wall; "SCALE" is not a result).
- **Panel B is actual biology** — protein strips with the +33-aa insertion
  visibly highlighted, not a bullet checklist.
- **Panel C is the largest element** — aggressively cropped screenshot,
  leader-line callouts, no browser chrome.
- **Container budget: three** (ROOST card, protein strips as diagram
  elements, screenshot frame). Everything else: typography, icons, arrows,
  hairlines, one amber accent reserved for the sequence feature + evidence.
- Contrast tiers: primary info = large Black numbers/statements (ink/hue);
  annotations = small tracked caps (muted/faint).

## 1. Specs

| Spec | Value |
|---|---|
| Print | 183 mm double-column master (Nature E&E target; adapt at submission) |
| Canvas | 1400×1040 px SVG; no text below 13.5 px (≈5 pt in print); display numbers 8–20 pt |
| Type | Lato Regular/Semibold/Black only |
| Colors | House tokens + `genomics` teal `#0f766e` (stable token in `figures/style.py`); amber `#d97706` = sequence feature + evidence only |
| Terminology | "gene–genome assessments" (never "determinations"); "assemblies" not "genomes"; every species count carries its qualifier |
| Export | `render_figure.py figures/src/fig1_overview.svg --export` |

## 2. Layout (v3)

```
A · FROM FRAGMENTED DATA TO HOST-SIDE KNOWLEDGE
   LITERATURE            SURVEILLANCE           GENOMES
    [icon]                 [icon]                [icon]
    1,366 papers · 22 src  44,842 det · 106 ctry 3,894 assemblies cat.
    literature evidence    species × occurrence  2,358 screened to date
        \                      |                      /
         ─── curves converge ──┼─────────────────────
                        ┌─────▼─────┐
                        │   ROOST   │   ← single filled navy anchor
                        │ species·genes·mechanisms·evidence·…│
                        └─────┬─────┘
                    2,048 species indexed        ← typography, not cards
     4,277 genes tracked · 997 in ≥2 papers · 2.95M assessments

B · ONE GENE, CONNECTED          C · THE LIVE RESOURCE
   ANP32A (spans panel)          ┌────────────────────────┐
   BIRDS      → MECHANISM        │  aggressively cropped   │
   [protein    polymerase        │  screenshot + leader-   │
    +33-aa]    compatibility     │  line callouts ①②③     │
   MAMMALS     ↓ COMPARATIVE     └────────────────────────┘
   [protein]   1,868/2,335
    no insert  ↓ EVIDENCE
               15 papers ── view record ──▶
```

## 3. Panel A — integration + scale

Streams (typography + 44 px flat icons, no boxes): LITERATURE (blue) 1,366
papers · 22 sources / AGENTS + QA; SURVEILLANCE (slate) 44,842 detections ·
106 countries · 714 species / SPECIES × OCCURRENCE; GENOMES (teal) 3,894
assemblies catalogued · 2,358 screened to date / PRESENCE + ORTHOLOGY. Curved 4 px arrows converge on ROOST (filled `ink` card, white
type: ROOST / host genomics knowledgebase / species · genes · mechanisms /
evidence · occurrence · genomics). Below: hero `2,048 species indexed`
(primary) + one mixed-weight stats line (numbers Black, labels muted).

## 4. Panel B — one record: ANP32A (real biology, provenance point)

Header spans panel: ANP32A + full name. Left column = the biology: bird
protein strip with amber **+33-aa** insert (+ tick label, "chicken · duck ·
turkey") vs mammal strip ("no insert", "human · cattle · mouse") — species
names supported by `gene_profiles/ANP32A.json`. Arrows into right column =
the resource tiers: MECHANISM (amber eyebrow) "influenza polymerase
compatibility — a host-range determinant" → COMPARATIVE GENOMICS (teal)
`1,868 / 2,335` assemblies full-length → EVIDENCE (amber) `15 source-linked
papers · 235 literature mentions` → *view record →* into Panel C. No PB2
627K / cattle / per-paper chips (Figure 2's job).

### 4b. Count definitions (single source of truth)

All presence numbers computed from `data/genes/gene_presence_v2.parquet` at
build: 2,948,288 gene–genome assessments (rows); 2,358 assemblies screened
(distinct accessions); ANP32A full-length in 1,868 of 2,335 assessed
(E4+E5 found; fragment/not-found remainder per parquet). 2,048 species indexed =
canonicalized species index. 3,894 catalogued = inventory; 714 = species
with recorded detections. **997 = genes studied in ≥2 papers** (strict
study-subject definition from the gene registry: 3,510 studied − 2,517
single-paper; buckets sum exactly). **Orthogroups (40,494) removed from
Figure 1** — panel-intersecting OGs are implementation detail, not headline
scale; the long-tail distribution (71.7% single-paper) is reserved as a
Figure 2 / Results panel: 1 paper 2,517 (71.7%) · 2–3 615 · 4–9 248 ·
10–19 80 · 20+ 50.

**Site reconciliation (so numbers never look contradictory):** the gene
browser's 1,529 = gene *pages* (wiki universe, any-role paper links;
`wiki_genes.json total_genes`); its 1,019 = `papers_with_genes` (**papers**
with ≥1 extracted gene, not genes); 1,018 wiki genes have ≥2 any-role
papers — a looser definition than the registry's 997 study-subject genes.
All three are correct under their definitions; Figure 1 prints only
registry/parquet numbers.

**Do-not-print rule:** the progress-file 2,110 and current-panel 811 from
`by_the_numbers.json` describe different populations — never mix with data
counts. (Site-side fix queued: relabel or parquet-derive.)

## 5. Panel C — the live resource (v3.2: real)

Two deterministic captures (never hand-cropped), produced by
`scripts/figures/capture_fig1_panel_c.mjs` against the dev server
(`localhost:5177`, light theme, deviceScaleFactor 2, structures card hidden
via DOM, external 3D-model hosts blocked):

1. **explorer_main** — `#/anp32`: paralogue cards (A/B/E histograms) + the
   insert-sequence strip. 2472×916 px → placed 604×224.
2. **papers_inset** — `#/genes/ANP32A`: the record's *Literature evidence*
   card header band ("What the research corpus says about ANP32A — 10 papers,
   7 mechanism edges" + first mechanism rows with `[paper]` links).
   2536×430 px → placed 604×102.

Both embed as base64 `<image>` data URIs (self-contained SVG; rsvg renders
them to PDF/PNG). `geometry.json` records each capture's clip rect plus
element anchors (mechanism line, strip h2, evidence subtitle) in capture
space; `make_fig1.py` maps anchors → SVG coordinates at build time. Badges
①②③ stack on the right rail following anchor order, halo-stroked labels,
dashed leaders to 3.5 px anchor dots.

(explorer_table — the per-species table top — is captured too and kept as a
spare asset; not currently placed.)

**Evidence-count alignment (v3.2):** the record page's typed-evidence view
(`gene_evidence/ANP32A.json`) says **10 papers / 7 mechanism edges**, while
`genes.json` says **15 papers / 255 mentions** (any-link view). Both are
correct under their definitions — but since the record card is now visible
in the figure, Panel B's evidence tier prints the typed-view numbers
(10 papers with typed evidence · 7 mechanism edges · 255 mentions) and the
caption carries both, explicitly defined. Same rule as the site
reconciliation table: never print two numbers for one concept side by side.

Capture spec kept for re-runs: `#/anp32` light theme 2× DPR, content-width
crops ≥ 2400 px (≈ 770 dpi at print size). URL stays in the caption:
https://josephguhlin.com/Roost/#/anp32

## 6. Caption

Generated at build into `figures/src/fig1_overview_caption.txt` (numbers
interpolated from artifacts). Bold title: "Roost links literature-derived
host-factor evidence, H5N1 surveillance, and comparative genomics across
2,048 indexed species." (A) streams + scale; (B) ANP32A record; (C) explorer
URL + callouts; data-freeze line last.

## 7. Verification record

audit_figure PASS (auditor now text-anchor-aware and data-URI-aware) ·
`svg_text_lint.py` clean except the six intended callout texts over the
screenshots (3 halo labels + 3 badge numerals) ·
manifest present (`figures/manifests/fig1_overview.json`, no third-party
assets — screenshots are our own UI) · anchors derived from DOM geometry,
mapped in-code · rendered export OCR-verified: screenshots rasterize, badges
①②③ and labels present, numbers match artifacts · no model in this
environment can view pixels — final eyeball check via the unlisted review
page `web/public/figures/fig1_review.html` (served at
`/figures/fig1_review.html`, not linked from any route, no index.json
entry).

## 8. Refresh

```
node scripts/figures/capture_fig1_panel_c.mjs   # needs dev server on :5177
pixi run python scripts/figures/make_fig1.py \
  && pixi run python scripts/figures/render_figure.py \
       figures/src/fig1_overview.svg --export
```

Numbers-page triage rule applies to the figure: any figure-vs-site
disagreement → rebuild, never hand-edit.

## 9. Open

1. by_the_numbers.json 2,110/811 relabel (site-side).
2. Human eyeball pass on the v3.2 render (badge/label occlusion over the
   screenshots is the main thing no geometry check can judge).
3. At submission time: consider swapping explorer_main for explorer_table if
   reviewers want the presence grid rather than sequences in Panel C.
