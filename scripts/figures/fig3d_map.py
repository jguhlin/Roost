#!/usr/bin/env python3
"""Figure 3 panel D candidate — world map of the genome gap (standalone).

WHAT THIS SHOWS
---------------
A Pacific-centred world choropleth: each country coloured by the number of
H5N1-detected host species that have **no reference genome** in the Roost
index. This is the geographic face of panel C's "no genome" cell (221
species): where in the world the sequenced-resources gap actually sits.

UNIVERSE (mirror of fig3_gaps panel A/C definitions)
----------------------------------------------------
- species from web/public/data/species_index.json (the site's index page)
- ...with `det` (recorded H5N1 detection; 717 of 721)
- ...and no `genome_acc` (no genome in the index)
Species are counted once per country where they have >=1 detection
(detections.parquet, joined by canonical genus-species name).
Studied species are part of the universe (2 of them) — the map is
"detected, no genome", studied or not; the split lives in the caption.

GEOGRAPHY
---------
- Base: Natural Earth 110m countries (web/public/data/geojson/
  ne_110m_countries.geojson), joined to detections' ISO3 `country`
  via ADM0_A3 (fallbacks: ISO_A3, ISO_A3_EH).
- Pacific-centred by rotating longitudes (CENTRAL_LON below); countries
  crossing the resulting seam are split by clipping so no polygon smears
  across the map. With CENTRAL_LON=160 the seam sits at 20°W and only
  Greenland + Iceland are affected.

ITERATION KNOBS (top of CONFIG)
-------------------------------
CENTRAL_LON, COLORMAP, BIN_EDGES, LABEL_TOP_N, SHOW_ANTARCTICA,
FIG_W_IN / FIG_H_IN, EDGE_COLOR, BG_COLOR — see CONFIG block.

OUTPUTS
-------
figures/preview/fig3d_map.png          (fast look)
figures/export/fig3d_map.{png,svg,pdf} (submission set)
Console: universe stats + any unmatched country codes (fix by adding to
COUNTRY_ALIASES — never by editing data files).

Run:  pixi run python scripts/figures/fig3d_map.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
from style import C, apply_style  # noqa: E402  (house tokens)

apply_style()

# ======================================================================
# CONFIG — the knobs you tweak between iterations
# ======================================================================
CENTRAL_LON = 160        # map centre (deg E); seam falls at CENTRAL_LON-180
COLORMAP = "Reds"        # sequential ramp; "no genome" is red in fig3 A/C
BIN_EDGES = [1, 2, 4, 8, 16, 32]   # count bins; None => continuous
SHOW_ANTARCTICA = False  # detections exist (ATA) but it dwarfs the frame
LABEL_TOP_N = 0          # number of countries to annotate with their count
                         # (0 = no badges — counts live in the colorbar)
FIG_W_IN, FIG_H_IN = 9.2, 5.1
BG_COLOR = "#ffffff"     # ocean (white)
LAND_NOCOUNT = "#ffffff"  # countries with zero gap species
EDGE_COLOR = "#1f2937"   # black country lines (journal style)
DPI_EXPORT = 300

# detections.country (ISO3) -> Natural Earth ADM0_A3, where they differ.
# Populated from the "unmatched" report this script prints — add entries
# here, never edit the data files.
COUNTRY_ALIASES = {
    "ALA": "FI",    # Åland -> mapped with Finland (110m has no Åland)
    "TAI": "TWN",
    "KOS": "KOS",   # Kosovo: not in 110m; unmatched is acceptable
}

# ======================================================================
# DATA
# ======================================================================
def canon(name: str) -> str:
    """Genus-species canonical form (folds subspecies/trinomials)."""
    parts = str(name).strip().split()
    return " ".join(parts[:2]).lower() if len(parts) >= 2 else str(name).lower()


def load_universe() -> tuple[dict[str, dict], set[str], int]:
    """Return (index-by-canon, no-genome-detected canon set, n_studied)."""
    si = json.loads((ROOT / "web/public/data/species_index.json").read_text())
    ghs = json.loads((ROOT / "web/public/data/gene_host_species.json").read_text())
    studied = {canon(sp) for v in ghs.values() for sp in v.get("species", [])}
    index = {canon(s["sci"]): s for s in si}
    universe = {c for c, s in index.items()
                if s.get("det") and not s.get("genome_acc")}
    n_studied = len(universe & studied)
    return index, universe, n_studied


def species_country_counts(universe: set[str]) -> dict[str, set[str]]:
    """{ISO3 country code: set of universe species detected there}."""
    det = pl.read_parquet(ROOT / "web/public/data/detections.parquet")
    det = det.filter(pl.col("country").is_not_null()
                     & pl.col("scientific_name").is_not_null())
    rows = det.select(["country", "scientific_name"]).iter_rows(named=True)
    cc: dict[str, set[str]] = collections.defaultdict(set)
    for r in rows:
        c = canon(r["scientific_name"])
        if c in universe:
            cc[r["country"]].add(c)
    return cc


# ======================================================================
# GEOGRAPHY — Pacific-centred Plate Carre'e with seam splitting
# ======================================================================
def shift_lon(lon: float, central: float = CENTRAL_LON) -> float:
    """Rotate longitude so `central` becomes 0; output in [-180, 180)."""
    return ((lon - central + 540.0) % 360.0) - 180.0


def load_countries() -> "pl.DataFrame":
    """Country polygons + ISO3 key, as a small polars frame."""
    import geopandas as gpd
    gj = ROOT / "web/public/data/geojson/ne_110m_countries.geojson"
    gdf = gpd.read_file(gj)
    if not SHOW_ANTARCTICA:
        gdf = gdf[gdf["ADM0_A3"] != "ATA"]
    key = (gdf["ADM0_A3"].fillna(gdf.get("ISO_A3"))
           .fillna(gdf.get("ISO_A3_EH")))
    return gdf.assign(_iso3=key)


def recenter(gdf, central: float = CENTRAL_LON):
    """Shift longitudes; split polygons that would smear across the seam.

    The seam (antimeridian of the new frame) sits at `central - 180`. A
    country spanning that meridian would get vertices at +180 and -180 and
    draw as a band across the whole map. We pre-clip every such country
    into an east and west piece (in original coordinates) and shift each
    piece separately — the same visual treatment the dateline gives Russia
    on Atlantic-centred maps.
    """
    from shapely.geometry import box
    from shapely.ops import transform as shp_transform

    # the new frame's +-180 boundary falls at original (central - 180):
    # e.g. a 160E centre puts the seam at 20 deg W. (A sign error here
    # once split countries at the CENTRE instead, leaving Greenland and
    # Iceland unsplit — they drew as horizontal bands across the top.)
    seam = ((central - 180 + 540) % 360) - 180
    west_of = box(-180, -90, seam, 90)          # original-coord clip boxes
    east_of = box(seam, -90, 180, 90)

    def _shift(geom):
        out = shp_transform(lambda x, y, z=None:
                            (np.array([shift_lon(v, central) for v in x]), y),
                            geom)
        # a piece with vertices on both sides of the frame edge (the
        # seam-clip edge lands at -180 while the body sits near +180)
        # draws as a horizontal band across the map; lift the negative
        # side by +360 so the piece reassembles at the right edge
        b = out.bounds
        if b[2] - b[0] > 180:
            out = shp_transform(
                lambda x, y, z=None: (np.where(np.asarray(x, dtype=float) < 0,
                                               np.asarray(x, dtype=float)
                                               + 360.0, x), y),
                out)
        return out

    pieces = []
    for _i, row in gdf.iterrows():
        g = row.geometry
        if g.bounds[2] - g.bounds[0] > 359:      # already wraps the world
            pass
        elif seam > g.bounds[0] and seam < g.bounds[2]:
            for side in (g.intersection(west_of), g.intersection(east_of)):
                if not side.is_empty:
                    r = row.copy()
                    r["geometry"] = _shift(side)
                    pieces.append(r)
            continue
        r = row.copy()
        r["geometry"] = _shift(g)
        pieces.append(r)
    import geopandas as gpd
    return gpd.GeoDataFrame(pieces, crs=gdf.crs)


# ======================================================================
# RENDER
# ======================================================================
def main() -> int:
    index, universe, n_studied = load_universe()
    counts = species_country_counts(universe)

    gdf = recenter(load_countries())
    iso3 = counts.keys()
    # map detection ISO3 -> NE key via aliases where needed
    def ne_key(code: str) -> str | None:
        code = COUNTRY_ALIASES.get(code, code)
        return code if code in set(gdf["_iso3"]) else None

    val = {c: len(spp) for c, spp in counts.items()}
    matched = {c: v for c, v in val.items() if ne_key(c)}
    unmatched = sorted(set(val) - set(matched))
    gdf["_count"] = gdf["_iso3"].map(lambda k: max(
        (v for c, v in matched.items() if ne_key(c) == k), default=0))

    total_species = len(universe)
    n_countries = len(matched)
    top = sorted(matched.items(), key=lambda kv: -kv[1])[:LABEL_TOP_N]

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))
    ax.set_facecolor(BG_COLOR)

    if BIN_EDGES:
        bounds = [0] + BIN_EDGES + [max(BIN_EDGES) * 2]
        cmap = plt.get_cmap(COLORMAP, len(bounds) - 1)   # discrete ramp
        norm = BoundaryNorm(bounds, ncolors=len(bounds) - 1)
    else:
        cmap = plt.get_cmap(COLORMAP)
        norm = plt.Normalize(0, max(1, max(gdf["_count"].max(), 1)))

    # land: zero-count base first, then the valued countries on top
    base = gdf[gdf["_count"] == 0].plot(ax=ax, color=LAND_NOCOUNT,
                                        edgecolor=EDGE_COLOR, linewidth=0.4)
    hot = gdf[gdf["_count"] > 0]
    hot.plot(ax=ax, column="_count", cmap=cmap, norm=norm,
             edgecolor=EDGE_COLOR, linewidth=0.4)

    # label the top countries with small count badges
    for code, v in top:
        row = gdf[gdf["_iso3"] == ne_key(code)].dissolve()
        cx, cy = row.geometry.iloc[0].centroid.x, \
            row.geometry.iloc[0].centroid.y
        ax.annotate(f"{v}", (cx, cy), ha="center", va="center",
                    fontsize=6.5, fontweight="bold",
                    color=C["ink"] if v < BIN_EDGES[1] else "#ffffff")

    ax.set_xlim(-180, 180)
    ax.set_ylim(-59, 84)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color("#1f2937"); sp.set_linewidth(0.8)

    # colorbar with bin labels
    if BIN_EDGES:
        labels = ([f"{BIN_EDGES[i]}-{BIN_EDGES[i+1]-1}"
                   for i in range(len(BIN_EDGES) - 1)]
                  + [f"≥{BIN_EDGES[-1]}"])
        handles = [Patch(facecolor=cmap(norm(b)), edgecolor="none",
                         label=lab)
                   for b, lab in zip([1] + BIN_EDGES[1:], labels)]
        ax.legend(handles=handles, loc="lower left", fontsize=6.2,
                  frameon=False, title="species without genomes",
                  title_fontsize=6.6, alignment="left",
                  bbox_to_anchor=(0.0, 0.0))
    ax.set_title("H5N1-detected host species with no reference genome, "
                 "by detection country",
                 loc="left", fontsize=9.5, fontweight="bold", color=C["ink"])

    fig.tight_layout(pad=0.3)
    PREVIEW = ROOT / "figures/preview/fig3d_map.png"
    EXPORT = ROOT / "figures/export"
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    fig.savefig(PREVIEW, dpi=160, facecolor=C["surface"])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(EXPORT / f"fig3d_map.{ext}", dpi=DPI_EXPORT,
                    facecolor=C["surface"])
    rel = lambda p: p.relative_to(ROOT)  # noqa: E731
    print(f"wrote {rel(PREVIEW)} + export set")

    print(f"  universe: {total_species} detected species, no genome "
          f"({n_studied} of them studied)")
    print(f"  countries with >=1 gap species: {n_countries}"
          + (f"; unmatched ISO3 codes: {unmatched}" if unmatched else ""))
    print(f"  top: {top}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
