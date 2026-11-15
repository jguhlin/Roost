#!/usr/bin/env python3
"""Figure 3 panel D candidate #2 — gridded genome-gap heatmap (standalone).

WHAT THIS SHOWS
---------------
Companion to fig3d_map.py (country choropleth). Instead of political
units, every H5N1 detection of a no-genome host species is placed by its
coordinates and binned into a lat/lon grid; each cell is coloured by the
number of DISTINCT gap-species detected inside it. This surfaces the
biogeographic shape of the gap — coastlines, flyways, the Antarctic
peninsula — rather than country tallying.

Universe and framing are identical to fig3d_map (220 detected species
with no reference genome; Pacific-centred with NZ at the map centre), so
the two figures compare like-for-like. Shared machinery (universe loader,
longitude shift, seam-safe country outlines) is imported from
fig3d_map.py — change CONFIG there and both move together.

NOTE ON PROJECTION
------------------
Plate Carrée (simple lat/lon squares), same as fig3d_map. High-latitude
cells therefore over-represent area; fine for pattern reading, revisit
with an equal-area projection if any quantitative claim depends on it.

ITERATION KNOBS (CONFIG below)
------------------------------
CELL_DEG (grid size in degrees), BIN_EDGES, CENTRAL_LON (imported),
SHOW_ANTARCTICA, MIN_LAT / MAX_LAT frame, COLORMAP, sizes, colors.

OUTPUTS
-------
figures/preview/fig3d_grid.png
figures/export/fig3d_grid.{png,svg,pdf}
Console: universe stats, coverage (n cells, share of detections with
coordinates), max cell count and where it is.

Run:  pixi run python scripts/figures/fig3d_grid.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))
from style import C, apply_style  # noqa: E402  (house tokens)
from fig3d_map import (  # noqa: E402  (shared, documented machinery)
    CENTRAL_LON, canon, load_universe, recenter, load_countries, shift_lon,
)

apply_style()

# ======================================================================
# CONFIG — knobs for this variant
# ======================================================================
CELL_DEG = 4.5          # grid cell size in degrees (lat & lon)
CELL_INSET = 0.45       # shrink each cell so land shows between cells
SMOOTH = True           # continuous log-stretched ramp (False -> binned)
BIN_EDGES = [1, 2, 4, 8, 16]   # binned mode only (SMOOTH=False)
SHOW_ANTARCTICA = True  # detections reach the Antarctic peninsula
MIN_LAT, MAX_LAT = (-78, 84) if SHOW_ANTARCTICA else (-59, 84)
# ColorBrewer YlOrRd: the canonical multi-hue "heat" ramp for WHITE
# backgrounds (Harrower & Brewer 2003; R's image()/filled.contour()
# default). Single-hue "Reds" starts near-white and vanishes on white
# land; YlOrRd starts at clearly-visible pale yellow, keeps monotonic
# luminance to dark red (perceptual order), its low-chroma light end
# signals "low" per Zeileis & Murrell (R Journal 2023), and the red
# terminus matches fig3 A/B's no-genome encoding.
COLORMAP = "YlOrRd"
FIG_W_IN, FIG_H_IN = 10.4, 5.1
BG_COLOR = "#d6e4f0"     # ocean: light blue (classic cartographic water)
LAND_COLOR = "#4b5563"   # land: dark gray (lighter than v7's near-black)
EDGE_COLOR = "#ffffff"   # white country borders
CELL_EDGE = "none"
DPI_EXPORT = 300

# ======================================================================
# DATA — detection points for the gap universe
# ======================================================================
def gap_species_points(universe: set[str]) -> pl.DataFrame:
    """(species, lat, lon-shifted) rows for universe species with coords."""
    det = pl.read_parquet(ROOT / "web/public/data/detections.parquet")
    det = (det.filter(pl.col("latitude").is_not_null()
                      & pl.col("longitude").is_not_null()
                      & pl.col("scientific_name").is_not_null())
           .with_columns(pl.col("scientific_name").map_elements(
               canon, return_dtype=pl.String).alias("_canon")))
    det = det.filter(pl.col("_canon").is_in(list(universe)))
    return det.select(["_canon", "latitude", "longitude"])


def grid_counts(pts: pl.DataFrame):
    """{ (cell_x, cell_y): n distinct species } on the shifted grid."""
    grid: dict[tuple[int, int], set[str]] = collections.defaultdict(set)
    for r in pts.iter_rows(named=True):
        x = shift_lon(r["longitude"])          # Pacific-centred
        y = r["latitude"]
        cx = int(np.floor(x / CELL_DEG) * CELL_DEG)
        cy = int(np.floor(y / CELL_DEG) * CELL_DEG)
        grid[(cx, cy)].add(r["_canon"])
    return {k: len(v) for k, v in grid.items()}


# ======================================================================
# RENDER
# ======================================================================
PANEL_ASSET = ROOT / "figures/src/assets/fig3/panel_d_grid.png"

def render(fig, ax, counts, *, panel: bool):
    """Shared drawing; panel=True drops the standalone title/legend size
    so the chart can sit inside fig3 panel D at 1:1 print scale."""
    gdf = recenter(load_countries())
    if not SHOW_ANTARCTICA:
        gdf = gdf[gdf["_iso3"] != "ATA"]
    gdf.plot(ax=ax, color=LAND_COLOR, edgecolor=EDGE_COLOR, linewidth=0.35,
             zorder=1)
    vmax = max(counts.values()) if counts else 1
    vmin = min(counts.values()) if counts else 1
    if SMOOTH:
        # smooth continuous LINEAR ramp; ticks = min / mid / max absolute
        # numbers. The ramp is TRUNCATED (bottom 15% dropped) so the
        # lowest-count cell is light-orange — visible on white ocean as
        # well as on dark land.
        from matplotlib.colors import LinearSegmentedColormap, Normalize
        _full = plt.get_cmap(COLORMAP)
        cmap = LinearSegmentedColormap.from_list(
            f"{COLORMAP}_trunc", _full(np.linspace(0.15, 1.0, 256)))
        norm = Normalize(vmin=vmin, vmax=vmax)
    else:
        n_edges = [0] + BIN_EDGES + [max(BIN_EDGES) * 2]
        cmap = plt.get_cmap(COLORMAP, len(n_edges) - 1)
        norm = BoundaryNorm(n_edges, ncolors=len(n_edges) - 1)
    for (cx, cy), n in counts.items():
        ax.add_patch(plt.Rectangle(
            (cx + CELL_INSET / 2, cy + CELL_INSET / 2),
            CELL_DEG - CELL_INSET, CELL_DEG - CELL_INSET,
            facecolor=cmap(norm(n)), edgecolor=CELL_EDGE, linewidth=0,
            zorder=3))
    ax.set_xlim(-180, 180)
    ax.set_ylim(MIN_LAT, MAX_LAT)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color("#1f2937")
        sp.set_linewidth(0.8 if panel else 0.6)
    # standard heatmap colorbar, off the map (right edge, outside axes)
    import matplotlib.cm as cm
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    mid = round((vmin + vmax) / 2)
    ticks = sorted({vmin, mid, vmax}) if SMOOTH else BIN_EDGES
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", shrink=0.94,
                        pad=0.012, aspect=14, ticks=ticks)
    cbar.ax.tick_params(labelsize=6 if panel else 7.5, length=2,
                        colors=C["muted"])
    cbar.outline.set_edgecolor("#cbd5e1")
    cbar.outline.set_linewidth(0.6)
    cbar.set_label("species without genomes per cell" if not panel
                   else "species / cell", fontsize=6.4 if panel else 8,
                   color=C["muted"])
    if not panel:
        ax.set_title("H5N1 detections of host species with no reference "
                     f"genome ({CELL_DEG}° cells, distinct species per cell)",
                     loc="left", fontsize=9.5, fontweight="bold",
                     color=C["ink"])


def main() -> int:
    import matplotlib.pyplot as _plt
    index, universe, n_studied = load_universe()
    pts = gap_species_points(universe)
    counts = grid_counts(pts)

    # panel-mode asset for fig3 panel C (full-width slot, no title)
    pf, pax = _plt.subplots(figsize=(8.6, 2.62))
    pax.set_facecolor(BG_COLOR)
    render(pf, pax, counts, panel=True)
    pf.tight_layout(pad=0.15)
    PANEL_ASASET = PANEL_ASSET
    PANEL_ASSET.parent.mkdir(parents=True, exist_ok=True)
    pf.savefig(PANEL_ASSET, dpi=600, facecolor=C["surface"])
    _plt.close(pf)
    print(f"wrote {PANEL_ASSET.relative_to(ROOT)} (panel asset)")

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))
    ax.set_facecolor(BG_COLOR)
    render(fig, ax, counts, panel=False)

    fig.tight_layout(pad=0.3)
    PREVIEW = ROOT / "figures/preview/fig3d_grid.png"
    EXPORT = ROOT / "figures/export"
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    fig.savefig(PREVIEW, dpi=160, facecolor=C["surface"])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(EXPORT / f"fig3d_grid.{ext}", dpi=DPI_EXPORT,
                    facecolor=C["surface"])
    print(f"wrote {PREVIEW.relative_to(ROOT)} + export set")

    hot = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
    print(f"  universe: {len(universe)} species; "
          f"detections with coords: {pts.height:,}; cells: {len(counts)}")
    print(f"  hottest cells (x, y -> n): {hot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
