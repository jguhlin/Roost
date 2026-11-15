---
name: scientific-assets
description: Interface to the local open scientific asset library (SQLite FTS index over mirrored Bioicons, Reactome, Health Icons, PhyloPic, NIH BioArt, SciDraw). Searches by keyword with license filtering, returns ranked compact JSON, copies selected SVGs into the figure workspace, and appends attribution to the figure manifest. Use internally whenever a diagram needs cells, organisms, lab equipment, molecules, anatomy, or clinical icons — before drawing biological objects from scratch.
---

# Scientific Assets

Local mirror of open scientific vector libraries with per-asset license
provenance. Never scrape BioRender or arbitrary websites; never import an
asset whose license isn't in the index.

## Index

`assets/manifest.sqlite` (SQLite + FTS5; rebuilt by
`scripts/figures/build_asset_index.py` from per-library `manifest.json`
files written by the Morphly fetchers).

Libraries: bioicons (per-icon licenses), reactome (CC BY 4.0), healthicons
(CC0), phylopic (permissive subset: PD/CC0/CC BY), nih-bioart (free-use per
entry), scidraw (CC BY 4.0). Togo and Servier are manual downloads
(`docs/FIGURE_AGENT.md` §9.4, §9.8).

## Search

```bash
python3 scripts/figures/search_assets.py --query "bird chromosome sequencing" \
  --license-priority permissive --limit 12
# → compact JSON: [{title, source, path, license, attribution, score}]
```

- `--license-priority permissive` orders CC0/PD/MIT first, CC BY next,
  excludes ShareAlike and NonCommercial
- `--require-commercial-ok`, `--no-share-alike`, `--source reactome`,
  `--source phylopic` … for hard filters
- Returns paths only — read the actual SVG only after selecting it
  (keeps context small)

## Selection rules

1. Scientific accuracy of the depiction beats aesthetics — a wrong-shaped
   pathogen icon is wrong no matter how pretty.
2. Prefer CC0/public domain, then permissive, then CC BY (attribution cost).
3. Avoid ShareAlike for publication figures unless the downstream license
   implications are accepted; never NonCommercial for journal/book outputs.
4. Recolour/modify only within license terms; if modified, set
   `"modified": true` in the figure manifest entry.

## Import into a figure

```bash
python3 scripts/figures/search_assets.py --import assets/reactome/cell-element/chromosome-123.svg \
  --figure <figname>          # copies SVG into figures/src/assets/<figname>/ and
                              # appends {asset_id, title, source, license, attribution,
                              # modified} to figures/manifests/<figname>.json
```

Then reference the copied file from the figure source (relative path), never
the library path directly.

## Attribution

`python3 scripts/figures/build_attribution.py --figure <figname>` emits
`figures/attribution/<figname>.txt` from the manifest (one credit line per
asset, exact citation strings from the library metadata). Rollup across all
figures: `--rollup` → `docs/ASSET_CREDITS.md`.

## Rebuild / extend the mirror

```bash
scripts/figures/mirror_assets.sh          # re-runs all fetchers (bounded)
python3 scripts/figures/build_asset_index.py   # manifests → manifest.sqlite
```
