# Figure 3 — Design Brief v1 (knowledge-gap figure)

**Status: BUILT — v1.5. A = the species GRID restored (v1.2 encoding:
blue depth tiers / amber genome-unstudied / red-X no genome; species-count
block order matching B with Carnivora broken out; within-block category
sort — stacked-bars experiment rolled back, still available standalone as
fig3a_stacked); B unchanged; C = the grid map, full-width panel render of
fig3d_grid.py (dark-gray land, light-blue ocean, white borders, truncated
YlOrRd heat ramp); the 2×2 matrix remains removed (numbers in caption A).
Refresh order: fig3d_grid.py → make_fig3.py → render.**

v1.3 (superseded): panel D was the grid map at half width; C was
matrix-only; B retitled "Species per order vs. host genetics studies".

**Status: BUILT — v1.2 (encoding + ranking pass). Source: `scripts/figures/make_fig3.py`
→ `figures/src/fig3_gaps.svg` (+ caption sidecar) → `render_figure.py
--export` → `figures/export/fig3_gaps.{svg,pdf,png}`. Review copy
(unlisted): `web/public/figures/fig3_review.html`.**

v1.1 iteration changes (over v1):
- **A — study-depth tiers**: blue cells now encode gene-link depth
  (≥20 genes solid · 5–19 @ 0.65 · 1–4 @ 0.4; 6 / 13 / 40 species). Even
  the studied set is shallow — two-thirds of “studied” species rest on
  ≤4 gene links. Legend split into two rows (tiers + genome states).
- **B**: removed a stray literal “order” label (now “mammals” under
  Carnivora only); the zero-study note is now computed over **all** larger
  bird orders (≥17 species), not the top-10 tie-broken subset — now four
  orders / 99 species (adds Psittaciformes + Procellariiformes).
- **C/D**: footer sharpened (“all 442 queryable in Roost today”); caption
  no longer hardcodes the ≥20-gene species list (computed).
- Structural verification now pins the exact grid mix: 721 cells =
  442 teal + 59 blue (40/13/6 tiers) + 220 gray.

## 0. The one message

> Host-genetic knowledge lags far behind available genomic resources — and
> Roost identifies exactly where existing data could be used immediately.

Three-figure arc: **Fig 1** what Roost is · **Fig 2** what becomes visible ·
**Fig 3** where the field should look next (this figure). The claim is an
**index of research opportunity, never a susceptibility score** — printed
on the figure itself.

## 1. Panels

| Panel | Content | Numbers (freeze 2026-10-10) |
|---|---|---|
| A | Every indexed species as one cell in a taxonomically ordered grid (big orders labelled row-blocked; small orders grouped; mammals last). Blue = studied, teal = genome-unstudied, gray = neither | 721 cells: 59 / 442 / 220 (render-level count verified) |
| B | Attention vs diversity: per-order species bars (teal) with studied overlay (blue), top 10 orders; zero-study orders flagged in red | e.g. Charadriiformes 130/2, Passeriformes 115/6, Anseriformes 111/9; Pelecaniformes + Suliformes = 62 species, zero studies |
| C | Genome × study 2×2 matrix with the hot cell highlighted (amber); headline stat + the two studied-without-genome species | 57 / **442** / 2 / 220; 88.6% of 499 genome-available; Lynx lynx, Tyto furcata |
| D | Tractable now: endangered (IUCN CR/EN) + chromosome-level genome + zero studies, programmatically selected | California condor, Baer's pochard, tiger, Siberian crane, whooping crane, takahē; +74 more threatened in gap; 344/442 gap species are LC |

## 1b. v1.2 changes (user-directed)

- **Panel A ordering**: block order = species-count order, identical to
  panel B's rows (Carnivora broken out of the mammals tail at its size
  position; remaining mammals = "other mammals"). Within each block,
  cells sort by category — studied first (dark-to-light blue by gene-link
  depth), then genome-unstudied (amber), then no genome (red X) — so each
  block's leading blue run reads as its studied count at a glance.
- **Encoding**: genome-unstudied = **amber fill** (#d97706); no genome =
  **red X** (#dc2626 cross, no fill) — absence is marked, not filled;
  studied keeps the blue depth tiers. Legend wording "no indexed genome"
  → "no genome". Structural check pins the exact mix: 442 amber, 59 blue
  (40/13/6 tiers), 220 red X.

## 2. Count definitions (single source of truth)

- **Universe** = `web/public/data/species_index.json` — the site's own
  species index page (H5N1-detected + tracked hosts), 721 species.
- **Studied** = species named as a host in typed study-subject claims
  (`gene_host_species.json`, the gene-record "Detected host species" data),
  canonicalized to genus-species (folds subspecies like *Gallus gallus
  domesticus*). 173 host species overall; 59 intersect the index.
- **Genome available** = index `genome_acc` present (499 species).
- **Threatened** = IUCN CR/EN/VU/NT via `species/iucn_status.json`.
- Mammal orders derived from `species.parquet` class column — never
  hardcoded.

## 3. Defensive choices

- Panel D examples are **programmatically filtered** (EN/CR + chromosome
  level + unstudied) and priority-sorted — the build cannot drift into
  hand-picking species.
- Build asserts the 2×2 cells sum to the universe and match the set
  arithmetic (`genome ∩ studied`, `genome − studied`, …).
- The disclaimer ("research opportunity — not a susceptibility score")
  prints on the figure, not just the caption.
- Detection is NOT an axis in panel A: the index is detection-derived
  (717/721 detected), so it carries no discriminating power here — the
  interesting axes are genome × attention.

## 4. Verification record

`svg_text_lint.py` CLEAN · audit_figure PASS (no warnings) · grid rendered
with exactly 721 cells in the expected mix (442 teal / 59 blue at 40/13/6
depth tiers / 220 gray — matching the cross-tab and tier computation to the
cell) · OCR confirms panels, labels, chips and stats · no model here can
view pixels — eyeball pass via the unlisted review page.

## 5. Refresh

```
pixi run python scripts/figures/make_fig3.py \
  && pixi run python scripts/figures/render_figure.py \
       figures/src/fig3_gaps.svg --export
```

## 5b. Standalone exploration figures (not in the shipped figure yet)

### fig3a_stacked — panel A as stacked bars
`scripts/figures/fig3a_stacked.py` → `figures/{preview,export}/fig3a_stacked.*`
+ served unlisted at `/figures/fig3a_stacked.png`. One row per order
(species-count order); single-species bird orders folded into "other
birds"; mammal tail = carnivora + other mammals (generic-Mammalia folds
in); birds in ink, mammals faint; blues = studied depth tiers, amber =
genome-unstudied, red = no genome. Universe = detected species (717).

### fig3d_map — the genome gap, geographically (panel D candidate)
`scripts/figures/fig3d_map.py` → `figures/{preview,export}/fig3d_map.*` +
served unlisted at `/figures/fig3d_map.png`. Pacific-centred (CENTRAL_LON
=160°E, NZ at centre; seam at 20°W splits only Greenland + Iceland —
handled by pre-clipping) choropleth: countries coloured by number of
H5N1-detected species with **no reference genome** (220-species universe
from panel C's "no genome" cell; species counted once per detection
country; join detections.country ISO3 → NE110 ADM0_A3, with
COUNTRY_ALIASES for strays). First-cut results: 57 countries carry the
gap; top = USA 49, South Africa 26, Chile 22, Brazil 14, Australia 12.
**Iteration knobs are a CONFIG block at the top of the script**
(CENTRAL_LON, COLORMAP, BIN_EDGES, LABEL_TOP_N, SHOW_ANTARCTICA, sizes,
colors); unmatched ISO3 codes print on every run — fix via
COUNTRY_ALIASES, never by editing data. Unmatched so far (all
sub-territories absent from 110m): ATA (excluded by design), HKG, HMD,
SGS, SHN.

### fig3d_grid — the genome gap as a spatial grid (panel D candidate #2)
`scripts/figures/fig3d_grid.py` → `figures/{preview,export}/fig3d_grid.*` +
served unlisted at `/figures/fig3d_grid.png`. Same universe and Pacific
frame as fig3d_map (shares its loader/shift/seam machinery by import —
CONFIG changes to fig3d_map propagate here); instead of political
countries, every detection of a gap species is placed by coordinates and
binned into 5° cells (CONFIG: CELL_DEG, BIN_EDGES, SHOW_ANTARCTICA,
frame, colors). Cell colour = distinct gap-species detected inside. 1,239
geolocated detections → 163 cells; hottest: US Great Plains/Mississippi
flyway (−100°,40°; 35 species), South Africa Western Cape (20°,−35°; 23),
Patagonia (−75°,−40°; 20), Central America Caribbean (−85°,25°; 13),
US Southwest (13+12). Complements the country choropleth: country-level
tallies include detections without coordinates; the grid shows
biogeographic shape (coasts, flyways, Antarctic peninsula). Plate Carrée
— high-latitude cells over-represent area (documented in the script).

### fig3d_icons — the genome gap as species silhouettes (panel D candidate #3)
`scripts/figures/fig3d_icons.py` → `figures/{preview,export}/fig3d_icons.*`
+ served unlisted at `/figures/fig3d_icons.png`. One PhyloPic silhouette
per gap species (red-tinted to match fig3's no-genome encoding), placed
at the mean of its geolocated detections (country-centroid fallback),
with greedy spiral jiggling to de-overlap dense clusters. 120 of 220
species have local silhouettes (fetch via scripts/fetch_phylopic.py;
mammals dominate the unmatched 100 — ICON_FALLBACK knob reserved).
Attribution sidecar: figures/attribution/fig3d_icons.txt (required if
this ships). Shares the fig3d_map frame machinery.

fig3d_grid v7 (all map variants inherit the seam fix):
- **Seam bug fixed (fig3d_map.recenter)** — two stacked errors: the seam
  was computed at the map CENTRE (splitting Russia harmlessly) instead of
  the frame EDGE (20°W), and even correctly-clipped pieces had their
  clip-edge vertex at −180 with the body at +127..+180 → horizontal
  bands. Fixes: correct seam formula + wrap-lift (negative vertices
  raised +360 when a piece's width > 180°). Verified: widest feature now
  Russia 170°; GRL 53°. This is what the "long stretch lines at the top"
  were — Greenland and Iceland.
- **Map styling v8** (grid variant): light-blue ocean #d6e4f0, dark-gray
  land #4b5563, white borders — the classic cool-water/neutral-land
  cartographic convention; YlOrRd heat cells pop on both surfaces. (v7
  interim: near-black land + white ocean.)
(v6: YlOrRd rationale — ColorBrewer multi-hue for white backgrounds,
monotonic luminance, low-chroma light end per Zeileis & Murrell 2023,
red terminus matching the no-genome encoding. v5 linear + min/mid/max
ticks 1/18/34, cells 4.5°; v4 log; v3 colorbar off-map; v2 2.5°.)

**Map styling v2 (all three variants):** journal-style geography — white
ocean, white land, black country lines (#1f2937, 0.35–0.8 px), black
figure frame (axis spines restored). Icon map additionally:
FILL_HOLLOWS (outline-only PhyloPic art flood-filled solid) and a
**bounding-box jiggle** — clearance tested per axis against each PNG's
own aspect-derived half-extents (bird silhouettes run to 4.3° wide vs
3.2° tall; a circular gap cannot express that). Verified: 0
bbox-overlapping pairs across all 120 icons; half-width spread 0.3–4.3°,
median 1.8°.

## 6. Open

1. Human eyeball pass (review page) — grid density and B's paired bars are
   the main aesthetic unknowns.
2. Optional upgrade: encode study *depth* (genes studied per species) as
   blue-cell opacity in A — data already loaded (`studied_genes` counter).
3. Optional: a per-order phylogenetic ordering (currently size-sorted) if
   reviewers prefer evolutionary context over size ranking.
