---
name: scientific-data-figure
description: Create publication-quality figures from real quantitative data — plots, results figures, Manhattan/QQ/volcano/forest plots, heatmaps, model comparisons, calibration, multi-panel data figures. Inspects data first, writes plotting code as the source of truth, audits axes/units/statistics, exports SVG/PDF/PNG with provenance. Use whenever a figure must represent actual numbers. Never fabricates or smooths values; mock-ups must be labelled.
---

# Scientific Data Figure

Priority order (from Scientific Figure Skills, vendored at
`vendor/scientific-figure-skills/`; full handoff `docs/FIGURE_AGENT.md` §5):

```text
truth > reproducibility > interpretability > journal compliance > visual elegance > novelty
```

## Workflow

1. **Inspect the data first.** Read the actual file(s). Identify variables,
   types, units, sample sizes, and the intended comparison. Never plot from
   memory or assumption.
2. **Write a figure spec** (`figures/manifests/<figname>.spec.md`): the claim
   the figure supports, the comparison shown, statistical meaning of every
   encoding.
3. **Plotting code is the source of truth.** Create
   `figures/src/<figname>.py` (matplotlib; project deps numpy/pandas already
   available). The script reads data by path, applies only explicit
   transforms, and writes `figures/export/<figname>.{svg,pdf,png}` +
   `figures/preview/<figname>.png`. Data path(s), transform notes, and data
   file hashes go into `figures/manifests/<figname>.json`.
4. **Audit** (`python3 scripts/figures/audit_figure.py figures/src/<figname>.py --figure <figname>`):
   - axes labelled with units; tick/limit sanity; legend completeness
   - statistical annotations justified by the data (n, test, CI)
   - visual encoding supports the actual claim (no truncated-axis tricks
     unless flagged; error bars defined in caption)
   - grayscale/colour-deficient safe; no red-vs-green sole distinction
5. **Inspect the rendered PNG yourself** (read the image); revise.
6. **Never fabricate or smooth values.** If representative/mock data must be
   used (e.g. schema demos), set `"mock": true` in the figure manifest and
   say so in the response.

## Domain templates (this project)
Manhattan/QQ; genomic-region plots; effect-size/forest; genotype/phenotype
summaries; phylogenetic trait panels; heatmaps; calibration; pred-vs-observed;
variance-component summaries; multi-panel method/result composites. Existing
examples: `scripts/figures/make_paper_figures.py`, `make_map_figure.py`,
legacy outputs in `figures/`.

## Reference
`vendor/scientific-figure-skills/codex/skills/scientific-figure-suite/` —
protocols, templates (volcano, forest, survival, calibration, time-series
bands, multi-panel), audit checklists. Port incrementally; don't copy
host-specific adapters wholesale.
