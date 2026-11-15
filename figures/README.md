# figures/

Scientific figures for the project. Layout (D163, see `docs/FIGURE_AGENT.md`):

```text
figures/
├── src/          # editable source of truth: .svg, .drawio, .py
├── preview/      # PNG previews (agent-inspected, regenerable)
├── export/       # submission artifacts: svg/pdf/png (regenerable)
├── manifests/    # per-figure JSON: spec summary, data provenance, imported assets
├── attribution/  # per-figure credit lines (one per imported asset)
└── assets/<fig>/ # imported open-library SVGs for a given figure (copied by
                  # scripts/figures/search_assets.py --import)
```

**The editable source is the figure. PNG is a preview/export, not the source.**

Legacy figures (pre-D163) live flat in this directory — they predate the
layout; new work goes in the subdirectories.

## Tooling

```bash
# search + import an asset
python3 scripts/figures/search_assets.py --query "duck silhouette" --license-priority --limit 12
python3 scripts/figures/search_assets.py --import assets/phylopic/...svg --figure figname

# render preview / exports
python3 scripts/figures/render_figure.py figures/src/figname.svg [--export]

# structural + license audit
python3 scripts/figures/audit_figure.py figures/src/figname.svg --figure figname

# attribution for a figure / project rollup
python3 scripts/figures/build_attribution.py --figure figname
python3 scripts/figures/build_attribution.py --rollup   # → docs/ASSET_CREDITS.md

# publish a rendered figure to a research page (copies PNG/SVG into web/public/
# figures/ and updates the registry the pages read)
python3 scripts/figures/publish_figure.py --figure figname --page <briefing-slug>

# publish a rendered video (fframes project output) to a research page
python3 scripts/figures/publish_figure.py --video path/to/out.mp4 --page <briefing-slug>
```

## Mass regeneration

One command runs the whole media pipeline (agent figure proposals → explainer
videos → derived layers), safely re-runnable:

```bash
pixi run python scripts/papers/regenerate_media.py            # stale-checked
pixi run python scripts/papers/regenerate_media.py --force    # rebuild all videos
pixi run python scripts/papers/regenerate_media.py --steps proposals,layers
```

Per-item isolation: one bad briefing never stops the run; the report lists
ok/FAIL per step. Explainer videos verify their own beats post-render.

## Web integration

Research pages (`#/research/<slug>`) render a **Figures & media** section from
`web/public/figures/index.json` — the registry `publish_figure.py` maintains.
Entries carry `page` (briefing slug), `url`/`svg` paths, `caption`, and
attribution for embedded CC BY assets. Videos live under
`web/public/videos/` and render in a `<video>` element. Multiple figures per
page are supported; re-publishing a name updates its entry in place.

fframes video projects live in `figures/video/<name>/` (Rust crates; build
with the `LIBRARY_PATH`/`LD_LIBRARY_PATH` x264-163 workaround from
FIGURE_AGENT §22). Example: `figures/video/qinghai-mortality/`.

Pi skills: `.pi/skills/{scientific-diagram, scientific-data-figure,
scientific-assets, svg-diagram, drawio}`.

## Design system

All figures follow [docs/FIGURE_DESIGN.md](../docs/FIGURE_DESIGN.md) —
Lato typography, fixed color tokens matched to the web app, layout and
icon rules, and a publish review checklist. Shared matplotlib style:
`figures/style.py` (`apply_style()`, `C` tokens, `panel_label`, `source_line`,
`save`). New figure scripts should import it instead of hand-rolling styles.
Gap maps are spec-driven (`figures/specs/*.json` + `make_gap_map.py`).
