# Figure Agent — Local-First Scientific Figures with Pi

Comprehensive handoff: skills, generation methods, open assets, licensing, and
implementation strategy. Companion to [RESEARCH_AGENT.md](RESEARCH_AGENT.md)
(the research-briefing agent); this document covers the figure-generation agent.

- Researched/consolidated: 4 October 2026
- Implemented in this repo: 4 October 2026 (see §23 *Local implementation status*)

## Purpose

Build a local-first, agent-driven scientific figure system around Pi. The
intended experience is analogous to FFrames for video: describe the scientific
communication goal, let the coding agent construct a deterministic/editable
source representation, render it, inspect the result, revise it, and leave
behind source files that can be version-controlled and edited manually.

Reference concept: FFrames — <https://fframes.studio/> (repo:
<https://github.com/dmtrKovalenko/fframes>, MIT, Rust + SVG, renders on GPU;
ships its own coding-agent skill via `npx skills add https://fframes.studio`).

The central recommendation is **not** one monolithic AI figure generator. Use
Pi as the orchestrator and route each figure to the representation that best
preserves scientific accuracy and editability:

| Representation | Use for |
|---|---|
| Raw SVG | clean diagrams whose source should stay transparent and version-controlled |
| Native draw.io | structured methods diagrams, workflows, architectures, figures that will get manual layout edits |
| Python plotting | anything derived from quantitative data |
| Open scientific vector assets | cells, organisms, lab equipment, molecules, anatomy |
| Heavier AI systems (AutoFigure-Edit, PaperBanana) | only when a richer illustration is genuinely needed |

**Source-of-truth rule: the editable source is the figure. PNG is a
preview/export, not the source.**

## Contents

| § | Focus | § | Focus |
|---|---|---|---|
| 1 | Recommended stack at a glance | 12 | Hosted/non-local alternatives |
| 2 | Pi integration and project layout | 13 | Local asset database |
| 3 | Standalone SVG (`svg-diagram`) | 14 | Figure-generation loop |
| 4 | Native draw.io | 15 | Design rules |
| 5 | Real data figures | 16 | Pi skill decomposition |
| 6 | AutoFigure-Edit | 17 | Concrete build plan |
| 7 | PaperBanana ecosystem | 18 | Example Pi prompts |
| 8 | Morphly | 19 | What not to do |
| 9 | Open scientific asset libraries | 20 | Recommended first implementation |
| 10 | Asset licensing policy | 21 | Resource index |
| 11 | BioRender constraints | 22 | FFrames |
| | | 23 | Local implementation status (this repo) |

## 1. Recommended stack at a glance

| Layer | Component | Role | Local? | Free/open? |
|---|---|---|---|---|
| Agent | Pi | planning, file inspection, orchestration, revision | yes\* | yes |
| Simple diagrams | `svg-diagram` skill | generate/validate/render standalone SVG | yes | MIT |
| Structured diagrams | draw.io skill + draw.io Desktop | native `.drawio`, SVG/PDF/PNG export | yes | open source |
| Data figures | Scientific Figure Skills + Python | reproducible plots, audit, packaging | yes | MIT |
| Scientific assets | mirrored libraries (§9) + SQLite index | searchable open biological/scientific vectors | yes after download | mixed open licenses |
| Manual vector cleanup | Inkscape / draw.io / Morphly | human edits and final polish | yes | free/open |
| Text → editable illustration | AutoFigure-Edit | experimental methods-to-SVG pipeline | can be | MIT |
| Academic illustration R&D | PaperBanana implementations | planner/critic-style illustration generation | mixed | open-source implementations |
| Hosted alternatives | SciFig, FigPad, BioRender | convenient browser generation/editing | no | freemium/paid |

\* Pi itself runs locally, but prompts/files go to the configured model
provider unless Pi is pointed at a local model or private endpoint.

**Recommended default routing**

- Methods workflow / model architecture / analysis pipeline → draw.io or raw SVG
- Simple conceptual diagram → raw SVG
- Results figure from real data → Python through Scientific Figure Skills
- Biological mechanism / organism / lab setup → SVG/draw.io assembled from open asset libraries
- Graphical abstract → draw.io/SVG + open assets; AutoFigure-Edit only if the vector approach is insufficient
- Final manual cleanup → Inkscape, draw.io Desktop, or Morphly

## 2. Pi: where the figure workflow lives

- Website: <https://pi.dev/>
- Source: <https://github.com/earendil-works/pi>
- npm: <https://www.npmjs.com/package/@earendil-works/pi-coding-agent>
  (the former `@mariozechner/pi-coding-agent` package is deprecated; existing
  installations keep working, new docs/scripts use the current namespace)

Pi discovers Agent Skills from (project-local first):

```text
.pi/skills/<skill-name>/SKILL.md
.agents/skills/<skill-name>/SKILL.md
~/.pi/agent/skills/<skill-name>/SKILL.md
~/.agents/skills/<skill-name>/SKILL.md
```

Pi's normal `read`, `write`, `edit`, `bash` tools are enough for the whole
workflow. A custom extension can come later if a first-class asset-search or
preview command becomes useful.

### Project layout (as implemented here)

```text
project/
├── .pi/
│   ├── skills/
│   │   ├── svg-diagram/            # vendored from pkt-lab/svg-diagram
│   │   ├── drawio/                 # vendored from jgraph/drawio-mcp
│   │   ├── scientific-diagram/     # our wrapper (routing, spec, audit loop)
│   │   ├── scientific-data-figure/ # our wrapper (data → plot)
│   │   └── scientific-assets/      # our asset-index interface
│   └── prompts/                    # optional reusable figure prompts
│
├── vendor/                         # gitignored upstream clones (regenerable)
│   ├── svg-diagram/
│   ├── drawio-mcp/
│   ├── scientific-figure-skills/
│   ├── Morphly/                    # + scrapers reused for our mirrors
│   ├── bioicons/  healthicons/     # full-library clones (license ground truth)
│   ├── PaperBanana/  paperbanana ×2/  AutoFigure-Edit/
│   └── fframes/                    # (skill; binary via cargo)
│
├── assets/                         # gitignored mirrored libraries (regenerable)
│   ├── manifest.sqlite             # FTS5 index — COMMITTED (rebuilt by script)
│   ├── bioicons/  reactome/  healthicons/
│   ├── phylopic/  nih-bioart/  scidraw/
│   └── togo/, servier/ — mirrored via mirror_togo_servier.sh (§9.4, §9.8)
│
├── figures/
│   ├── src/                        # editable source: .svg .drawio .py
│   ├── preview/                    # PNG previews (agent-inspected)
│   ├── export/                     # submission artifacts: svg/pdf/png
│   ├── manifests/                  # per-figure asset/provenance JSON
│   └── attribution/                # per-figure credits TXT
│
└── scripts/figures/
    ├── mirror_assets.sh            # re-run all Morphly fetchers → assets/
    ├── build_asset_index.py        # manifests → assets/manifest.sqlite (FTS5)
    ├── search_assets.py            # query the index (compact JSON)
    ├── render_figure.py            # svg/py → png preview (librsvg/matplotlib)
    ├── audit_figure.py             # structural + license checks
    └── build_attribution.py        # figure manifest → attribution TXT
```

Design choice: **source, preview, and submission export live in separate
directories.** `vendor/` and the bulk of `assets/` are regenerable and
gitignored; the SQLite index, attribution files, and credits docs are committed.

## 3. Method A: standalone SVG (`svg-diagram`)

- Repo: <https://github.com/pkt-lab/svg-diagram> — MIT — verified, vendored
- Upstream skill: `vendor/svg-diagram/skills/svg-diagram/SKILL.md`
- Upstream helpers: `vendor/svg-diagram/scripts/{validate_svg.py,render_svg.py}`
- Installed here: `.pi/skills/svg-diagram/`

The skill already implements the FFrames-like loop: write SVG → structural
validation → render PNG locally (`librsvg`/Cairo) → inspect raster → fix
overlap/arrows/spacing/text overflow → keep SVG as editable source.

Constraints worth keeping: GitHub-safe standalone SVG (no `<foreignObject>`,
no scripts, no external references), plan layout on a grid before drawing.

**Best uses:** model diagrams; genomics/GWAS/phylogenetics pipelines;
experimental pipelines; statistical-method diagrams; small graphical
abstracts; figures where exact coordinates + Git diffs matter.

**Weaknesses:** raw SVG gets cumbersome for very large diagrams; connector
routing is manual; rich illustrations need imported assets (→ §9).

## 4. Method B: native draw.io

- Repo: <https://github.com/jgraph/drawio-mcp> — verified, vendored
- Agent skill (no MCP needed): `vendor/drawio-mcp/plugins/claude-code/skills/drawio/`
- Plugin docs: `vendor/drawio-mcp/plugins/README.md`
- App: <https://www.drawio.com/> (Desktop used for CLI convert/layout/export)
- Installed here: `.pi/skills/drawio/`

Produces native `.drawio` files; Desktop CLI converts Mermaid → `.drawio`,
applies ELK layout, exports SVG/PDF/PNG with the diagram XML embedded
(`--embed-diagram`) so exports stay re-openable in draw.io.

**Best uses:** methods diagrams with 10+ objects; multi-stage analysis
pipelines; process flowcharts; system/model architecture; figures requiring
frequent rearrangement; collaboration with people who drag objects manually.

**Rule:** use draw.io when semantic object editability and connector routing
matter more than human-readable text source.

## 5. Method C: real data figures

- Repo: <https://github.com/enesgul23/scientific-figure-skills> — MIT — verified, vendored
- Upstream layouts: `vendor/scientific-figure-skills/{claude-code,codex}/skills/scientific-figure-suite/`
- Python deps: numpy, pandas, matplotlib, Pillow, PyYAML

Stated priority order (keep this):

```text
truth > reproducibility > interpretability > journal compliance > visual elegance > novelty
```

Workflows include: statistical plots, model-performance figures,
omics/bioinformatics, clinical/biomedical, geospatial, multi-panel
composition, mechanisms, graphical abstracts, figure auditing, captions/alt
text, project-level figure memory and claim tracking. Templates: volcano,
heatmap, forest, calibration, survival, time-series bands, multi-panel.

**Pi strategy:** treat as reference implementation; the codex skill tree is
the least host-specific. Our wrapper is
`.pi/skills/scientific-data-figure/SKILL.md`; templates and audit ideas are
ported incrementally as the actual research programme needs them
(this repo: Manhattan/QQ, genomic-region, forest, genotype/phenotype,
phylo-trait panels, heatmaps, calibration, pred-vs-observed).

**Critical policy:** the agent must never invent values to make a figure look
better. Any figure not based on supplied/verified data is labelled a mock-up
internally (figure manifest `"mock": true`).

## 6. Method D (optional): AutoFigure-Edit

- Repo: <https://github.com/ResearAI/AutoFigure-Edit> — MIT — verified, vendored (code only, not run)
- Method text or existing figure → editable SVG; includes an SVG editor
- Uses segmentation + SVG reconstruction; current versions target
  OpenAI-compatible routes; heavier compute than A/B/C

**Use when:** the desired figure is visually richer than box/arrow; an
existing raster scientific figure must become editable; a
methods-description-to-illustration workflow is worth the compute.

Do **not** use it for ordinary data plots or simple flow diagrams.

## 7. Method E (optional): PaperBanana ecosystem

- Paper: <https://arxiv.org/abs/2601.23265>
- Official: <https://github.com/dwzhu-pku/PaperBanana> — verified, vendored
- SVG/community fork: <https://github.com/stuinfla/paperbanana> — verified, vendored
- Alternate impl: <https://github.com/llmsresearch/paperbanana> — verified, vendored

Multi-agent academic-illustration workflow (retrieval, planning,
styling/visualization, critique); benchmark of 292 methodology-diagram cases
from NeurIPS 2025 papers.

**Recommendation:** borrow the architecture, don't take a hard dependency
(forks vary; some assume external image/model services). Ideas to import:

1. retrieve/reference good examples before drafting;
2. separate content planning from visual styling;
3. render an intermediate;
4. run a visual/scientific critic;
5. revise against explicit defects.

## 8. Local manual editor + asset-pack system: Morphly

- Repo: <https://github.com/SAADAT-Abu/Morphly> — app MIT — verified, vendored
- Site: <https://morphly.pages.dev/> — local/offline; exports SVG/PDF/PNG/JPEG

Morphly implements the open scientific asset-pack architecture this project
adopts: packs for NIH BioArt, Bioicons, PhyloPic, Reactome, Health Icons,
SciDraw; per-asset license metadata; attribution appended on export.

Its `scraper/` directory is the **mirroring engine we reuse** (BSD-style
pragmatic code, MIT app license): `bioart_scraper.py`,
`bioicons_fetcher.py`, `healthicons_fetcher.py`, `phylopic_fetcher.py`,
`reactome_fetcher.py`, `scidraw_fetcher.py`, `assetlib.py` (retry/slugify/
SVG-sanitise/manifest-writer). Each fetcher writes `<lib>/manifest.json`
beside sanitised SVGs, with per-entry: `id, title, category, keywords,
description, license, license_url, requires_attribution, share_alike,
collection, creator, credit, citation, source, source_page, local_files`.

**Use Morphly as:** (a) a human editor for final local adjustments; (b) the
reference implementation for our asset manifest, downloaders, license badges,
and attribution generation. Morphly's MIT does **not** cover artwork — each
artwork keeps its source license.

## 9. Open scientific asset libraries

All mirrors live under `assets/<name>/` with `manifest.json` provenance.
Preference: permissive/public licenses first; provenance retained for every
asset (§10).

### 9.1 NIH/NIAID BioArt — mirrored `assets/nih-bioart/`
<https://bioart.niaid.nih.gov/> · terms: <https://bioart.niaid.nih.gov/terms>
Cells, pathogens, anatomy, organisms, laboratory/scientific illustrations;
SVG/AI/EPS/PNG per entry. Free for educational, research, informational, and
commercial purposes; check the per-entry license for attribution
requirements. **First choice for detailed professional illustrations.**

### 9.2 Bioicons — mirrored `assets/bioicons/` (+ full repo clone `vendor/bioicons/`)
<https://bioicons.com/> · repo: <https://github.com/duerrsimon/bioicons>
Biology, chemistry, cell biology, sequencing, epigenetics, lab equipment,
clinical imagery. **Site code is MIT; each icon keeps its own license** —
per-icon license tracked in the manifest. Prefer CC0/MIT/permissive icons.

### 9.3 Reactome Icon Library — mirrored `assets/reactome/`
<https://reactome.org/icon-lib> · license: <https://reactome.org/license>
Thousands of SVG/PNG icons: proteins, compounds, receptors, cell elements,
cell types, tissues, transporters, therapeutics. Pathway
illustrations/icon library/art: **CC BY 4.0, attribution required**.

### 9.4 Togo Picture Gallery / DBCLS — mirrored `assets/togo/` (SVGs only)
Archive: <https://dbarchive.biosciencedbc.jp/data/togo-pic/image/>
License: **CC BY 4.0**, required attribution: `© 2016 DBCLS TogoTV / CC-BY-4.0`.
Life-science images, organisms, lab equipment, instrumentation (PNG/AI/SVG).
The old `svg_format.zip` is gone, but the dbarchive **directory listing
serves files directly** — `mirror_togo_servier.sh` walks it and downloads
the ~2,100 SVGs (skips .ai/.png to save disk).

### 9.5 PhyloPic — mirrored `assets/phylopic/` (permissive subset)
<https://www.phylopic.org/> · usage: <https://www.phylopic.org/articles/image-usage>
>13,000 organism silhouettes, per-image licenses. Our mirror takes
**public-domain/CC0/CC BY only** (fetcher excludes SA/NC by default).
Phylogenies, evolutionary comparisons, organism panels, comparative genomics,
ecology.

### 9.6 Health Icons — mirrored `assets/healthicons/` (+ repo clone `vendor/healthicons/`)
<https://healthicons.org/> · repo: <https://github.com/resolvetosavelives/healthicons>
SVG/PNG, **public domain / CC0** — no attribution required (credit anyway
when convenient). Health/clinical concepts, devices, people, diagnostics.

### 9.7 SciDraw — mirrored `assets/scidraw/`
<https://scidraw.io/> · licensing: <https://scidraw.io/licensing>
Scientific drawings, organisms, behavioural setups, neuroscience, cells,
experimental illustrations. **CC BY 4.0, attribution required.** Use when a
detailed drawing beats a minimal icon.

### 9.8 Servier Medical Art — mirrored `assets/servier/` (SVG subset)
<https://smart.servier.com/> · citation:
<https://smart.servier.com/how-to-cite-servier-medical-art/>
>3,000 medical/scientific illustrations, **CC BY 4.0**. Anatomy, physiology,
clinical mechanisms, pathology. Direct zip (no form needed after all):
`https://smart.servier.com/wp-content/uploads/ServierMedicalArt-all-kits.zip`
(~165 MB, includes AI/PPT/PNG — `mirror_togo_servier.sh` keeps only SVG,
categorised into `assets/servier/<category>/`). Required attribution:

```text
Image(s) provided by Servier Medical Art (https://smart.servier.com),
licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
```

### 9.9 Attribution quick reference

| Library | License | Attribution |
|---|---|---|
| NIH BioArt | free use (per-entry terms) | per entry (usually "NIH/NIAID BioArt") |
| Bioicons | per-icon (CC0/MIT/CC BY…) | per icon + author |
| Reactome | CC BY 4.0 | required (citation string in manifest) |
| Togo | CC BY 4.0 | `© 2016 DBCLS TogoTV / CC-BY-4.0` |
| PhyloPic | per-image (PD/CC0/CC BY in our mirror) | per image (PD/CC0 optional) |
| Health Icons | CC0 / public domain | not required |
| SciDraw | CC BY 4.0 | required (per image) |
| Servier | CC BY 4.0 | required (fixed string) |

## 10. Asset licensing policy

Licensing is part of figure correctness, not an afterthought.

**Preference order** (when scientifically/visually comparable):

1. Public domain / CC0
2. MIT/BSD/other clearly permissive asset license
3. CC BY
4. CC BY-SA only when downstream licensing implications are acceptable

Avoid CC BY-NC for figures that may appear in commercial journals, books,
paid courses, or commercial reports. Never use assets with unclear provenance
in publication-ready outputs. Enforced mechanically: `search_assets.py
--license-priority` and the `commercial_ok` / `share_alike` / `public_domain`
columns in the index.

**Minimum per-asset metadata** (all present in `assets/manifest.sqlite`):

```json
{
  "asset_id": "reactome:R-HSA-...",
  "title": "Chromosome",
  "source": "Reactome",
  "source_url": "https://reactome.org/icon-lib",
  "local_file": "assets/reactome/cell-element/chromosome-xxx.svg",
  "author": "Reactome designers",
  "license": "CC BY 4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/",
  "attribution": "…",
  "modified": false,
  "keywords": ["chromosome", "dna", "genetics"]
}
```

Every finished figure carries a machine-readable manifest
(`figures/manifests/<fig>.json`) **plus** a human attribution file
(`figures/attribution/<fig>.txt`), and rollups land in
[docs/ASSET_CREDITS.md](ASSET_CREDITS.md).

## 11. BioRender: useful product, not an asset source

<https://www.biorender.com/> · AI editable figures:
<https://help.biorender.com/hc/en-gb/articles/37585527817629> · terms:
<https://www.biorender.com/individual-terms>

BioRender's terms prohibit extracting/redistributing content as standalone
reusable assets. Therefore: do not scrape it, do not put its assets in
`assets/`, use it only within its own plan conditions. The open libraries
above are the correct local alternative.

## 12. Hosted/non-local alternatives

Useful for comparison/inspiration/occasional fallback; not the core.

- **SciFig** <https://scifig.ai/> — text/sketch/paper/photo/CSV → editable
  PPTX/layered SVG; data-chart path can return plotting code. Hosted.
- **FigPad** <https://figpad.ai/> (docs <https://figpad.ai/tutorials>) — SVG and
  editable PPTX export; **raster generation followed by vectorization**, so
  "SVG" output is not a semantically authored SVG. Hosted/freemium.
- **CorelDRAW text-to-vector** (Sept 2026 update) — prompt-to-editable-vector;
  paid, cloud-backed. Optional one-off missing-illustration creation only.

## 13. Local asset database

Implemented at `assets/manifest.sqlite` — SQLite (ubiquitous, scriptable)
with **FTS5** over `title + description + keywords + scientific_name +
category`. Schema (`scripts/figures/build_asset_index.py`):

```text
assets(id, source, source_id, title, scientific_name, description, keywords,
       category, file_path, source_url, license, license_url, author,
       attribution, requires_attribution, share_alike, public_domain,
       commercial_ok, collection, citation)
asset_fts (FTS5 virtual table over the text fields above)
```

Search returns **compact JSON** — never dumps SVG content into context:

```bash
python3 scripts/figures/search_assets.py \
  --query "bird chromosome sequencing" \
  --license-priority permissive --limit 12
```

```json
[{"title": "Chromosome", "source": "Reactome",
  "path": "assets/reactome/cell-element/chromosome-…svg",
  "license": "CC BY 4.0", "attribution": "…", "score": 0.91}]
```

Only after selection does Pi read/import the actual SVG. Start with FTS, not
embeddings — scientific asset names/tags are unusually amenable to
full-text search; add local semantic embeddings later only if inadequate.

## 14. The figure-generation loop

Every route converges on the same staged process:

1. **Scientific intent** — record the claim/concept, essential vs contextual
   info, conceptual vs data-bearing, journal context, what must stay
   editable. Produce `figures/manifests/<fig>.spec.md` (or `.json`).
2. **Representation selection** — `SVG` / `.drawio` / `Python` / `SVG+assets`
   (routing table in §1). Never raster-first unless deliberately invoking an
   illustration system.
3. **Asset retrieval** — search local index; prefer open/permissive; record
   provenance; recolour only within license; never draw a generic AI
   approximation when a vetted open illustration exists.
4. **Draft** — text stays text; arrows stay connectors; no baked-in labels on
   imported images; design tokens for fonts/strokes/palette/spacing;
   meaningful group IDs.
5. **Structural validation** — valid XML; no missing referenced assets; no
   text outside canvas; no disconnected arrows; no duplicate IDs; correct
   dimensions; citations available.
6. **Render preview** — local PNG via `rsvg-convert` / Cairo / Inkscape CLI /
   draw.io Desktop CLI / matplotlib.
7. **Visual audit** — text clipping; unreadably small text; overlaps;
   connector collisions; inconsistent spacing; dominant-but-unimportant
   elements; alignment; contrast; colour-only encodings.
8. **Scientific audit** — does every arrow assert something true; causal vs
   associative visually distinguished; optional/hypothetical paths marked;
   quantities/axes/units correct; no unsupported spatial/chronological/
   hierarchical/certainty implications; no anatomically/biologically wrong
   implications introduced by an asset.
9. **License audit** — list third-party assets; confirm licenses; flag
   ShareAlike/NonCommercial; generate attribution; store beside source.
10. **Export** — keep at minimum: `source` (SVG/drawio/Python), `vector`
    (SVG/PDF), `preview` (PNG), `manifest` (JSON), `credits` (TXT/MD).

## 15. Design rules (defaults, not journal mandates)

**Typography:** small set of broadly-available sans-serifs; labels as live
text; avoid tiny text; sentence case unless convention says otherwise.

**Lines/arrows:** 2–3 stroke widths max; arrow style encodes meaning only
with a legend/convention; orthogonal or deliberate curves, never accidental
diagonal spaghetti.

**Colour:** group, don't decorate; restrained palette; grayscale and
colour-deficient safe; never red-vs-green as sole distinction.

**Composition:** strong L→R or T→B reading order; align to grid; consistent
padding; emphasis reserved for result/central mechanism; minimal
shadows/gradients for journal figures.

**Scientific visual semantics** (override when a field has a stronger
convention):

```text
solid arrow       = asserted flow/effect
open/dashed arrow = optional, indirect, predicted, secondary
solid boundary    = defined module/compartment
faded element     = context, not central
bracket           = grouping/comparison
```

## 16. Pi skill decomposition (as installed in `.pi/skills/`)

Three cooperating skills plus two vendored generators:

- **`svg-diagram`** (vendored as-is) — standalone SVG generator+validator.
- **`drawio`** (vendored, adapted) — native `.drawio` authoring + export.
- **`scientific-diagram`** (ours) — triggers on diagram / workflow / mechanism
  schematic / methods figure / graphical abstract / model architecture.
  Chooses SVG vs draw.io; writes the figure spec; invokes asset search;
  render → audit → revise; exports + manifest + attribution.
- **`scientific-data-figure`** (ours) — triggers on plot / results figure /
  Manhattan / volcano / forest / heatmap / model comparison / multi-panel.
  Inspects data; identifies variables and statistical meaning; plotting code
  as source of truth; audits labels/axes/units; SVG/PDF/PNG + provenance.
  Scientific Figure Skills is the reference implementation.
- **`scientific-assets`** (ours) — internal: search SQLite index; filter by
  license; ranked shortlist; copy/link selected SVG into the figure
  workspace; append attribution to the figure manifest.

## 17. Concrete build plan

- **Phase 1 — MVP** *(done 2026-10-04)*: vendor `svg-diagram` + draw.io skill;
  render tooling (`rsvg-convert`, Inkscape installed); `figures/{src,preview,
  export,manifests,attribution}`; wrapper skills enforcing render→inspect→
  revise; first assets (Bioicons/Reactome/PhyloPic/Health Icons).
- **Phase 2 — Asset system** *(done 2026-10-04)*: Morphly scrapers → mirrors;
  metadata normalised to SQLite; FTS search; automatic attribution output;
  license-policy checker.
- **Phase 3 — Data-figure workflow** *(in progress)*: Scientific Figure Skills
  vendored; port protocols incrementally; domain templates (Manhattan/QQ,
  genomic-region, forest, genotype/phenotype, phylo-trait, heatmap,
  calibration, pred-vs-observed, variance-component, multi-panel composite).
- **Phase 4 — Richer illustration experiments** *(not started)*: only after
  the deterministic stack is solid — AutoFigure-Edit; local
  PaperBanana-compatible pipelines; local vector generation for assets that
  genuinely don't exist in open libraries.
- **Phase 5 — Motion** *(not started)*: FFrames (§22) for animated figures /
  video abstracts, sharing the same source-of-truth philosophy.

## 18. Example Pi prompts

**Methods diagram**

```text
Create an editable methods figure for this analysis. First write a figure spec
that identifies all scientifically meaningful relationships. Use the local
scientific asset library where useful (scripts/figures/search_assets.py).
Choose SVG or draw.io based on complexity. Render a PNG preview, inspect it
for overlap, routing, text size, visual hierarchy, and scientific ambiguity,
revise it, then leave the editable source, SVG/PDF export, PNG preview,
manifest, and attribution file in figures/.
```

**Data figure**

```text
Create a publication-quality figure from data/results.csv. Do not fabricate
or smooth values. Inspect the dataset first, identify the intended
comparison, and write plotting code as the source of truth. Export SVG and
PDF plus a PNG preview. Audit axes, units, statistical annotations,
legibility, and whether the visual encoding supports the actual claim.
```

**Biological schematic with assets**

```text
Create an editable biological schematic showing [concept]. Search the local
scientific-asset index before drawing any biological object from scratch.
Prefer public-domain/CC0 assets, then CC BY. Record every selected asset and
license in the figure manifest. Keep text and arrows editable. Render and
visually/scientifically audit before export.
```

**Graphical abstract**

```text
Create a graphical abstract from this manuscript summary. First reduce the
story to 3-5 visual beats. Use open scientific vector assets and a restrained
journal-style design. Avoid generic AI art unless no appropriate asset
exists. Keep the source editable, render a preview, critique both scientific
faithfulness and visual hierarchy, then revise.
```

## 19. What not to do

- Do not use BioRender as a source of extracted standalone icons.
- Do not make raster generation the default — harder to edit, easier to hallucinate.
- Do not vectorize a raster when a semantically authored SVG/draw.io source
  can be created directly.
- Do not use a generated illustration as evidence. Figures communicate
  evidence; they don't invent it.
- Do not let an agent silently alter data — plot transforms must be
  explicit/reproducible.
- Do not drop attribution metadata after importing an asset.
- Do not assume repository code licenses cover bundled third-party artwork.
- Do not let aesthetics override scientific semantics — a clean wrong arrow
  is still wrong.
- Do not treat an SVG as automatically good because it is vector —
  vectorized hallucinations remain hallucinations.

## 20. Recommended first implementation

```text
Pi
 ├─ scientific-diagram skill
 │    ├─ svg-diagram          (vendored)
 │    ├─ draw.io skill        (vendored)
 │    └─ render + visual/scientific audit loop
 ├─ scientific-assets skill
 │    └─ SQLite FTS index over mirrored libraries
 │         ├─ NIH BioArt   ├─ Bioicons    ├─ Reactome
 │         ├─ PhyloPic     ├─ Health Icons├─ Togo (manual)
 │         ├─ SciDraw      └─ Servier (manual)
 └─ scientific-data-figure skill
      └─ Scientific Figure Skills + Python
```

This gives a genuinely local equivalent of "vibe coding scientific figures"
while preserving editability, reproducibility, provenance, and scientific
control.

## 21. Resource index

**Agent / inspiration**
- FFrames: <https://fframes.studio/> · <https://github.com/dmtrKovalenko/fframes>
- Pi: <https://pi.dev/> · <https://github.com/earendil-works/pi> ·
  npm [@earendil-works/pi-coding-agent](https://www.npmjs.com/package/@earendil-works/pi-coding-agent)

**Skills and generation engines**
- svg-diagram: <https://github.com/pkt-lab/svg-diagram>
- drawio-mcp (incl. agent skill): <https://github.com/jgraph/drawio-mcp>
- Scientific Figure Skills: <https://github.com/enesgul23/scientific-figure-skills>
- AutoFigure-Edit: <https://github.com/ResearAI/AutoFigure-Edit>
- PaperBanana: paper <https://arxiv.org/abs/2601.23265> ·
  official <https://github.com/dwzhu-pku/PaperBanana> ·
  SVG fork <https://github.com/stuinfla/paperbanana> ·
  alt <https://github.com/llmsresearch/paperbanana>
- Morphly: <https://github.com/SAADAT-Abu/Morphly> · <https://morphly.pages.dev/>

**Open assets** — see §9 for all URLs and licenses.

**Hosted comparison tools** — see §12.

## 22. FFrames (motion, later)

FFrames is the reference concept for this whole design — and it's real,
local, and MIT:

- Site: <https://fframes.studio/> · Repo: <https://github.com/dmtrKovalenko/fframes>
- "Video vibe coding framework that is actually fast. Write your video in
  Rust and SVG, render it on the GPU."
- Install: `cargo install --locked cargo-fframes` (the `fframes` crate itself
  is the library; `cargo-fframes` is the CLI subcommand). Then
  `cargo fframes new my-video --template multi-scene --format landscape`;
  every project command runs as `cargo run --release -- <command>`. First
  build downloads prebuilt Skia + ffmpeg libs (arm64/x86_64 Linux/macOS).
- Agent skill: upstream ships it in-repo — `skills/fframes-video/` (also
  installable via `npx skills add https://fframes.studio`). Vendored to
  `.pi/skills/fframes-video/`.
- **Build gotcha (this machine)**: the prebuilt ffmpeg-sys links against
  `libx264.so.163` (not the system ABI). A copy lives in the Julia
  depot (`$FFX264`). Build any fframes project with that
  dir in `LIBRARY_PATH` and run with it in `LD_LIBRARY_PATH`:
  ```bash
  export FFX264=~/.julia/artifacts/587de110e5f58fd435dc35b294df31bb7a75f692/lib
  export LIBRARY_PATH="$FFX264:$LIBRARY_PATH"      # link time
  export LD_LIBRARY_PATH="$FFX264:$LD_LIBRARY_PATH" # run time
  ```
- **Verified D163**: `cargo fframes new fframes-smoke --template
  single-scene` → `render --draft` wrote a valid h264 MP4 (960×540, 6 s) in
  0.5 s. A durable fix (own libx264-163 in `~/.local/lib`, or ffmpeg
  source build via `FFMPEG_FORCE_BUILD=1`) is a TODO if videos become
  routine.
- Agent-oriented inspection: `inspect` reports missing fonts/images, text cut
  off by the canvas, invalid SVG, panics — per time and scene — so an agent
  that "cannot watch" can still audit a video. Frame extraction to PNGs and
  numeric metrics complete the loop.

This is the natural Phase 5: animated figures / video abstracts with the
same editable-source philosophy (Rust + SVG source of truth, deterministic
renders, machine-checkable output). Skill vendored to
`.pi/skills/fframes-video/`; binary at `~/.cargo/bin/cargo-fframes`.

## 23. Local implementation status (2026-10-04)

Verified and vendored under `vendor/` (all upstream URLs checked 200):

| Component | Local path | State |
|---|---|---|
| svg-diagram | `vendor/svg-diagram` → skill at `.pi/skills/svg-diagram` | installed |
| draw.io skill | `vendor/drawio-mcp` → `.pi/skills/drawio` | installed (draw.io Desktop CLI not yet installed; XML/Mermaid authoring works, SVG export falls back to `rsvg-convert` on unembedded-diagram XML only — install Desktop for full CLI) |
| Scientific Figure Skills | `vendor/scientific-figure-skills` | vendored; wrapper skill installed |
| Morphly | `vendor/Morphly` | vendored; scrapers power `assets/` mirrors |
| AutoFigure-Edit | `vendor/AutoFigure-Edit` | vendored, not run |
| PaperBanana (3 repos) | `vendor/PaperBanana`, `vendor/paperbanana`, `vendor/paperbanana-llmsresearch` | vendored, reference only |
| Bioicons repo | `vendor/bioicons` | full clone (license ground truth) |
| Health Icons repo | `vendor/healthicons` | full clone (CC0) |
| FFrames | `~/.cargo/bin/cargo-fframes` (`cargo install --locked cargo-fframes`) + skill `.pi/skills/fframes-video` | binary build; repo vendored `vendor/fframes` |
| Asset index | `assets/manifest.sqlite` | built, FTS5 |
| Render stack | `rsvg-convert`, Inkscape, matplotlib | installed |

Asset mirrors under `assets/` — **12,444 assets indexed** (final counts,
2026-10-04): bioicons **2,830**, togo **2,094**, phylopic **2,365**
(permissive subset of >13k), reactome **2,257**, servier **1,014**, scidraw
**614** (complete library: 543 CC BY 4.0 + 71 CC0), healthicons **749**,
nih-bioart **521** (of 546 mirrored entries; range 1–600, extendable).
Licenses: 7,726 CC BY 4.0 · 2,558 CC0 · 1,376 CC BY 3.0 · 703 PD · 39 MIT ·
39 CC BY-SA · 3 BSD. All eight libraries mirrored — Togo via the dbarchive
directory listing (SVGs only), Servier via the all-kits PPTX zip unwrapped:
24 direct media SVGs + 990 slide illustrations converted
PPTX→PDF→SVG (`mirror_togo_servier.sh`; per-illustration SVG is not
distributed — art ships as native PowerPoint shapes). Full breakdown in
[docs/ASSET_CREDITS.md](ASSET_CREDITS.md).

Scripts: `scripts/figures/{mirror_assets.sh, mirror_togo_servier.sh,
build_togo_servier_manifest.py, build_asset_index.py,
search_assets.py, render_figure.py, audit_figure.py, build_attribution.py}`.

Pipeline verified end-to-end on `fig-smoke-methods` (§22.5): search →
import (Reactome chromosome asset, CC BY 4.0) → SVG author → validator
caught a real text-overflow → fix → render (preview + export svg/pdf/png) →
audit clean → attribution TXT + credits rollup.

Skills: `.pi/skills/{svg-diagram, drawio, scientific-diagram,
scientific-data-figure, scientific-assets, fframes-video}`.

FFrames status: **working** — `cargo fframes new` + `render --draft`
produced a valid h264 MP4 (960×540, 6 s) using the `libx264.so.163`
workaround in §22.

Everything regenerable (`vendor/`, `assets/` bulk SVGs) is gitignored; the
SQLite index, credits, and attribution files are committed.

## 24. Snapshot / verification note

Researched and consolidated 4 October 2026; every repository URL above was
re-verified (HTTP 200) and cloned locally on that date. Projects are new and
changing quickly — before making a tool or asset source a long-lived
dependency, re-verify its repository, license, and install instructions. For
publication, verify the license of every actual asset used rather than
relying on library-level summaries in this handoff.
