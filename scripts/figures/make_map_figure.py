#!/usr/bin/env python3
"""
Paper figure 4 — global spread of wild-bird HPAI detections (NZ-centred).

Panel a: country choropleth of wild-bird detection events (log10 scale)
Panel b: georeferenced detection points coloured by era — the spread front

Projection: Equal Earth centred on longitude 160°E (New Zealand ~centred),
reprojected with pyproj — no cartopy needed. Boundaries: Natural Earth 110m
(UN geoportal export was JS-walled; visually equivalent at this scale).

Usage: pixi run python scripts/figures/make_map_figure.py
Output: figures/fig4_world_spread.{svg,png}
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_paper_figures import save_checked  # overlap-gated saver

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
INK, MUT = "#1c2733", "#5b6b7b"

EQEARTH_NZ = "+proj=eqearth +lon_0=160"   # antimeridian ≈ 20°W
ERAS = [
    ("≤ 2021-09 (pre-2.3.4.4b)", "2000-01", "2021-09", "#440154"),
    ("2021-10 – 2024 (pandemic)", "2021-10", "2024-12", "#21918c"),
    ("2025 →", "2025-01", "2100-01", "#fde725"),
]

# detections 'country' (ISO3) → Natural Earth ISO_A3 fixes
ISO_FIX = {"USA": "USA", "GBR": "GBR", "CZE": "CZE", "SDN": "SDN",
           "KOR": "KOR", "COG": "COG", "TWN": "TWN"}


def load_points():
    det = pl.read_parquet(DATA / "detections_merged.parquet")
    tax = pl.read_csv(DATA / "aves_taxonomy.tsv", separator="\t").select(
        ["scientific_name", "order"])
    d = (det.filter(pl.col("source") != "aphis_flocks")
         .join(tax, on="scientific_name", how="inner")
         .filter(pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()))
    # parse dates (ymd / mdy; georeferenced sources are ymd)
    ds = pl.col("date_detected").str.strip_chars()
    d = d.filter(ds.str.contains(r"^\d{4}-\d{2}-\d{2}$"))
    d = d.with_columns(
        pl.col("date_detected").str.strptime(pl.Date, "%Y-%m-%d").alias("date"))
    return d


def main():
    import geopandas as gpd
    from shapely.geometry import Point

    world = gpd.read_file(DATA / "geojson" / "ne_110m_countries.geojson")
    world = world.to_crs(EQEARTH_NZ)

    det = pl.read_parquet(DATA / "detections_merged.parquet")
    wild = det.filter(pl.col("source") != "aphis_flocks")
    by_c = wild.group_by("country").agg(pl.len().alias("n")).sort("n", descending=True)
    counts = dict(zip(by_c["country"], by_c["n"]))
    matched = sum(n for c, n in counts.items()
                  if c in set(world["ISO_A3_EH"].fillna(world["ISO_A3"])))
    print(f"choropleth: {len(counts)} countries with data, "
          f"{matched}/{wild.height} records matched to boundaries")

    world["n"] = world["ISO_A3"].map(counts).fillna(0) \
        if world["ISO_A3"].map(counts).notna().any() else world["ISO_A3"].map(counts).fillna(0)
    # prefer ISO_A3_EH where ISO_A3 is missing (France, Norway)
    fix = world["ISO_A3"].isna() | (world["ISO_A3"] == "-99")
    world.loc[fix, "n"] = world.loc[fix, "ISO_A3_EH"].map(counts).fillna(0)

    pts = load_points()
    print(f"points: {pts.height} georeferenced dated wild-bird detections")
    import datetime
    def era_of(s):
        ym = s[:7]
        for lab, lo, hi, c in ERAS:
            if lo <= ym <= hi:
                return lab
        return ERAS[0][0]
    era = [era_of(str(dt)) for dt in pts["date"].to_list()]
    gpts = gpd.GeoDataFrame(
        {"era": era},
        geometry=gpd.points_from_xy(pts["longitude"], pts["latitude"]),
        crs="EPSG:4326").to_crs(EQEARTH_NZ)

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "svg.fonttype": "none",
        "pdf.fonttype": 42, "text.color": INK,
    })
    W, H = 7.2, 6.6
    fig = plt.figure(figsize=(W, H))
    ax_a = fig.add_axes([0.02, 0.55, 0.83, 0.42])
    ax_b = fig.add_axes([0.02, 0.085, 0.83, 0.42])
    for ax in (ax_a, ax_b):
        ax.set_facecolor("#eef3f8")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.5)
            s.set_color("#9db1c3")

    # (a) choropleth
    import matplotlib.colors as mcolors
    cmap = plt.cm.magma.copy()
    cmap.set_under("#dfe5ec")
    world.plot(column="n", ax=ax_a, cmap=cmap,
               norm=mcolors.LogNorm(vmin=1, vmax=max(counts.values())),
               edgecolor="#1c273355", linewidth=0.25)
    ax_a.set_title("wild-bird detection events by country (log scale)",
                   fontsize=6.5, loc="left", pad=2.5)

    # (b) points by era
    world.plot(ax=ax_b, color="#dfe5ec", edgecolor="#1c273355", linewidth=0.25)
    for lab, _, _, c in ERAS:
        sub = gpts[gpts["era"] == lab]
        sub.plot(ax=ax_b, color=c, markersize=1.1, alpha=0.75, linewidth=0)
    ax_b.set_title("georeferenced detections by era (n = "
                   f"{pts.height:,}; point-referenced sources only)",
                   fontsize=6.5, loc="left", pad=2.5)

    # colourbar (panel a) + era legend (panel b)
    sm = mpl.cm.ScalarMappable(cmap=cmap,
                               norm=mcolors.LogNorm(vmin=1, vmax=max(counts.values())))
    cax = fig.add_axes([0.86, 0.60, 0.022, 0.32])
    cbar = fig.colorbar(sm, cax=cax)
    cbar.ax.tick_params(labelsize=4.6, width=0.4, length=1.5, pad=1.2)
    cbar.outline.set_linewidth(0.4)
    cbar.set_label("events (log)", fontsize=5.0)
    handles = [mpl.lines.Line2D([], [], marker="o", ls="", color=c, ms=3,
                                label=lab) for lab, _, _, c in ERAS]
    ax_b.legend(handles=handles, loc="lower left", fontsize=5.2, frameon=True,
                framealpha=0.85, edgecolor="#d8e0e8", handletextpad=0.3,
                borderpad=0.4, labelspacing=0.3)

    fig.text(0.012, 0.965, "a", fontsize=8, fontweight="bold")
    fig.text(0.012, 0.505, "b", fontsize=8, fontweight="bold")
    fig.text(0.02, 0.018,
             "Equal Earth projection centred on 160°E. Boundaries: Natural Earth "
             "110m (UN geoportal export unavailable; visually equivalent at this "
             "scale). Poultry flock outbreaks and mammals excluded; ISO-week "
             "reports dated to mid-week. Panel b restricted to sources "
             "reporting coordinates (SDM-HPAI, WAHIS, CWHC, DAFF, NZ-DOC); "
             "US point density reflects APHIS state-level geocoding.",
             fontsize=4.6, color=MUT)

    save_checked(fig, "fig4_world_spread")
    plt.close(fig)


if __name__ == "__main__":
    main()
