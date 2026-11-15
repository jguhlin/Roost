---
name: scientific-diagram
description: Create editable scientific diagrams — methods figures, workflows, mechanism schematics, model architecture, graphical abstracts. Covers figure specification, SVG-vs-drawio representation choice, open-asset retrieval, local render, visual + scientific audit, revision, export with manifest and attribution. Use when the user asks for a diagram, methods figure, workflow, pipeline schematic, mechanism illustration, model architecture, or graphical abstract — especially for publication. Editable source is the figure; PNG is only a preview.
---

# Scientific Diagram

Produce publication-grade, editable scientific diagrams. Full handoff context:
`docs/FIGURE_AGENT.md`. Source-of-truth rule: **the editable source is the
figure — PNG is a preview/export.**

## Workflow (all stages mandatory unless trivially simple)

### 1. Figure spec
Before drawing anything, write `figures/manifests/<figname>.spec.md`:
- What claim/concept must the reader understand?
- Essential vs contextual information; conceptual vs data-bearing
- Journal/presentation context; what must remain editable
- Planned representation and asset needs

### 2. Representation choice
- **SVG** (`svg-diagram` skill) → simple/medium conceptual diagrams;
  transparent, Git-diffable source
- **drawio** (`drawio` skill) → 10+ objects, multi-stage pipelines,
  architecture, figures that will get manual layout edits
- **Python** → anything quantitative (switch to `scientific-data-figure`)
- Never raster-first.

### 3. Assets
Search the local index BEFORE hand-drawing any biological object:
```bash
python3 scripts/figures/search_assets.py --query "..." --license-priority permissive --limit 12
```
Rules: prefer CC0/PD, then permissive, then CC BY; avoid ShareAlike/NC for
publication figures; record every imported asset in the figure manifest;
never approximate a vetted scientific illustration with a generic AI shape.

### 4. Draft
- Text stays text; arrows stay connectors (never raster marks)
- No labels baked into imported images
- Design tokens: one sans-serif family, 2–3 stroke widths, restrained palette
- Semantic defaults: solid arrow = asserted flow; dashed/open = optional,
  indirect, predicted; boundary = compartment; faded = context; bracket =
  grouping. Override only with a stronger field convention.

### 5. Validate + render + audit
```bash
python3 vendor/svg-diagram/scripts/validate_svg.py figures/src/<fig>.svg --verbose
python3 scripts/figures/render_figure.py figures/src/<fig>.svg          # → figures/preview/
python3 scripts/figures/audit_figure.py figures/src/<fig>.svg --figure <figname>
```
Inspect the PNG preview yourself (read the image). **Visual audit:** text
clipping, tiny text, overlaps, connector collisions, spacing, alignment,
contrast, colour-only encodings. **Scientific audit (distinct, mandatory):**
does every arrow assert something true; causal vs associative distinguished;
optional/hypothetical paths marked; no unsupported scale/chronology/
hierarchy/certainty implied; no biologically wrong implication introduced by
an imported asset. Revise until both audits pass.

### 6. Export + provenance
```bash
python3 scripts/figures/render_figure.py figures/src/<fig>.svg --export  # → figures/export/ (svg+pdf+png)
python3 scripts/figures/build_attribution.py --figure <figname>          # → figures/attribution/<figname>.txt
```
Leave behind in `figures/`: editable source in `src/`, exports in `export/`,
preview in `preview/`, manifest (spec + assets + mock status) in
`manifests/`, credits in `attribution/`. If ANY part of the figure is not
grounded in verified science/data, set `"mock": true` in the manifest.

## Project conventions
- Existing legacy figures live flat in `figures/` (pre-D163); new figures use
  the subdirectory layout.
- Credits rollup: `docs/ASSET_CREDITS.md` (regenerate with
  `scripts/figures/build_attribution.py --rollup`).
- Full design rules and licensing policy: `docs/FIGURE_AGENT.md` §10, §15.
