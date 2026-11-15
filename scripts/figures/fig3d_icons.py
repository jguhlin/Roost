#!/usr/bin/env python3
"""Figure 3 panel D candidate #3 — icon map of the genome gap (standalone).

WHAT THIS SHOWS
---------------
Each H5N1-detected host species with no reference genome is drawn as its
PhyloPic silhouette at a representative location (mean of its geolocated
detections; species whose detections lack coordinates fall back to the
mean centroid of its detection countries). Overlapping icons are jiggled
apart greedily along an expanding spiral, so dense clusters (USA: 49
species) fan out instead of stacking into ink.

Same universe and Pacific-centred frame as fig3d_map / fig3d_grid
(shared machinery imported from fig3d_map).

ICONS
-----
- web/public/images/phylopic/<Sci_Name>.png (transparent silhouettes,
  downloaded by scripts/fetch_phylopic.py; index:
  web/public/data/phylopic.json). 120 of the 221 gap species have a
  match; the remainder are skipped and reported (ICON_FALLBACK is the
  knob for a future generic-bird/mammal fallback).
- Icons are tinted ICON_COLOR to tie into fig3 A/C's "no genome" red.
- Attribution: every distinct PhyloPic contributor is written to
  figures/attribution/fig3d_icons.txt — required if this ships.

ITERATION KNOBS (CONFIG)
------------------------
ICON_HEIGHT_DEG, JIGGLE_MIN_GAP, JIGGLE_STEP, ICON_COLOR, ALPHA,
SHOW_ANTARCTICA, frame, sizes. Placement seed is fixed (deterministic).

OUTPUTS
-------
figures/preview/fig3d_grid.png's sibling: fig3d_icons.png
figures/export/fig3d_icons.{png,svg,pdf}
figures/attribution/fig3d_icons.txt
Console: coverage stats + skipped species.

Run:  pixi run python scripts/figures/fig3d_icons.py
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))
from style import C, apply_style  # noqa: E402  (house tokens)
from fig3d_map import (  # noqa: E402  (shared, documented machinery)
    canon, load_universe, recenter, load_countries, shift_lon,
    species_country_counts,
)

apply_style()

# ======================================================================
# CONFIG — knobs for this variant
# ======================================================================
ICON_HEIGHT_DEG = 3.2    # icon height in degrees of latitude
CLEARANCE = 1.06         # margin on bounding-box clearance between icons
JIGGLE_STEP = 0.9        # spiral radius growth per turn
SPIRAL_TURNS = 120       # golden-angle attempts before allowing overlap
FILL_HOLLOWS = True      # fill outline-only silhouettes (hollow bodies)
ICON_COLOR = (146, 26, 26)   # dark red — fig3's "no genome" family
ALPHA = 0.92
SHOW_ANTARCTICA = True
MIN_LAT, MAX_LAT = (-78, 84) if SHOW_ANTARCTICA else (-59, 84)
FIG_W_IN, FIG_H_IN = 9.2, 5.1
BG_COLOR = "#ffffff"     # ocean (white)
LAND_COLOR = "#ffffff"
EDGE_COLOR = "#1f2937"   # black country lines (journal style)
DPI_EXPORT = 300
PHYLOPIC_DIR = ROOT / "web/public/images/phylopic"
PHYLOPIC_INDEX = ROOT / "web/public/data/phylopic.json"

# ======================================================================
# ICONS
# ======================================================================
def load_silhouettes(universe: dict[str, None]):
    """{(canon sci): (PIL image, attribution)} for matched gap species."""
    idx = json.loads(PHYLOPIC_INDEX.read_text())
    out = {}
    for key, v in idx.items():
        c = canon(v.get("sci") or key.replace("_", " "))
        if c not in universe or v.get("status") != "ok":
            continue
        p = PHYLOPIC_DIR / f"{key}.png"
        if not p.exists():
            p = PHYLOPIC_DIR / f"{v['sci'].replace(' ', '_')}.png"
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        if FILL_HOLLOWS:
            # outline-only art leaves enclosed hollow bodies; fill them so
            # the map never shows through a silhouette
            from PIL import ImageDraw
            mask = im.split()[3].point(lambda a: 255 if a == 0 else 0)
            ImageDraw.floodfill(mask, (0, 0), 255)
            px = np.array(im)
            holes = (np.array(mask) == 0)   # alpha-0 not reached from edge
            px[..., 3][holes] = 255
            im = Image.fromarray(px)
        r, g, b = ICON_COLOR
        px = np.array(im)
        px[..., 0][px[..., 3] > 0] = r
        px[..., 1][px[..., 3] > 0] = g
        px[..., 2][px[..., 3] > 0] = b
        out[c] = (Image.fromarray(px), v.get("attribution") or "unknown")
    return out


# ======================================================================
# PLACEMENT
# ======================================================================
def species_locations(universe: set[str]):
    """Representative (shifted_lon, lat) per species.

    Primary: mean of its geolocated detections. Fallback for coordinate-
    less species: mean centroid of its detection countries (country
    centroids from the NE polygons, shifted into the frame).
    """
    det = pl.read_parquet(ROOT / "web/public/data/detections.parquet")
    det = (det.filter(pl.col("scientific_name").is_not_null())
           .with_columns(pl.col("scientific_name").map_elements(
               canon, return_dtype=pl.String).alias("_canon"))
           .filter(pl.col("_canon").is_in(list(universe))))

    pts: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
    with_xy = det.filter(pl.col("latitude").is_not_null()
                         & pl.col("longitude").is_not_null())
    for r in with_xy.select(["_canon", "latitude", "longitude"]).iter_rows(named=True):
        pts[r["_canon"]].append((shift_lon(r["longitude"]), r["latitude"]))

    loc = {c: (float(np.mean([p[0] for p in v])),
               float(np.mean([p[1] for p in v])))
           for c, v in pts.items()}

    # country-centroid fallback for coordinate-less species
    need = universe - set(loc)
    if need:
        cc = species_country_counts(universe)
        world = load_countries()
        cent = {row["_iso3"]: (shift_lon(row.geometry.centroid.x),
                               row.geometry.centroid.y)
                for _i, row in world.iterrows()}
        for code, spp in cc.items():
            members = [c for c in spp if c in need]
            if not members or code not in cent:
                continue
            for c in members:
                loc.setdefault(c, cent[code])
    return loc


def half_extents(icons):
    """Per-species (half-width, half-height) in degrees, from the PNG's
    own aspect ratio — bird silhouettes are wider than tall, and that is
    exactly where circular-gap jiggling fails."""
    he = {}
    for c, (im, _attr) in icons.items():
        aspect = im.width / im.height
        he[c] = (ICON_HEIGHT_DEG * aspect / 2.0, ICON_HEIGHT_DEG / 2.0)
    return he

def jiggle(points: dict[str, tuple[float, float]],
           he: dict[str, tuple[float, float]]):
    """Greedy de-overlap on axis-aligned bounding boxes: two icons are
    clear when they separate on EITHER axis (|dx| >= summed half-widths
    or |dy| >= summed half-heights). Spiral push uses the golden angle."""
    placed = []          # [(x, y, hw, hh)]
    out = {}
    for c, (x, y) in sorted(points.items()):        # deterministic order
        hw, hh = he.get(c, (ICON_HEIGHT_DEG, ICON_HEIGHT_DEG / 2))
        ok = False
        for t in range(SPIRAL_TURNS + 1):
            xx, yy = x, y
            if t:
                ang = t * 2.399963                   # golden angle spiral
                rad = JIGGLE_STEP * math.sqrt(t)     # even area coverage
                xx += rad * math.cos(ang)
                yy += rad * math.sin(ang)
            xx = min(178.0, max(-178.0, xx))
            yy = min(MAX_LAT - 2.0, max(MIN_LAT + 2.0, yy))
            if all(abs(xx - px) >= (hw + phw) * CLEARANCE
                   or abs(yy - py) >= (hh + phh) * CLEARANCE
                   for px, py, phw, phh in placed):
                placed.append((xx, yy, hw, hh))
                out[c] = (xx, yy)
                ok = True
                break
        if not ok:                                    # give up: allow overlap
            placed.append((x, y, hw, hh))
            out[c] = (x, y)
    return out


# ======================================================================
# RENDER
# ======================================================================
def main() -> int:
    index, universe, n_studied = load_universe()
    icons = load_silhouettes({c: None for c in universe})
    loc = species_locations(universe)

    drawable = {c: loc[c] for c in icons if c in loc}
    skipped_no_icon = sorted(universe - set(icons))
    skipped_no_loc = sorted(set(icons) - set(loc))

    fig, ax = plt.subplots(figsize=(FIG_W_IN, FIG_H_IN))
    ax.set_facecolor(BG_COLOR)
    gdf = recenter(load_countries())
    if not SHOW_ANTARCTICA:
        gdf = gdf[gdf["_iso3"] != "ATA"]
    gdf.plot(ax=ax, color=LAND_COLOR, edgecolor=EDGE_COLOR, linewidth=0.35)

    pts = jiggle(drawable, half_extents(icons))
    # zoom scales each silhouette so its height = ICON_HEIGHT_DEG of latitude
    base_px = fig.dpi * FIG_H_IN                      # figure height in px
    for c, (x, y) in pts.items():
        im, _attr = icons[c]
        zoom = (ICON_HEIGHT_DEG / (MAX_LAT - MIN_LAT)) * base_px / im.height * 0.92
        ab = AnnotationBbox(OffsetImage(im, zoom=zoom, alpha=ALPHA),
                            (x, y), frameon=False, zorder=5)
        ax.add_artist(ab)

    ax.set_xlim(-180, 180)
    ax.set_ylim(MIN_LAT, MAX_LAT)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color("#1f2937"); sp.set_linewidth(0.8)
    ax.set_title("H5N1-detected host species with no reference genome "
                 "(one silhouette per species, at its detections)",
                 loc="left", fontsize=9.5, fontweight="bold", color=C["ink"])

    fig.tight_layout(pad=0.3)
    PREVIEW = ROOT / "figures/preview/fig3d_icons.png"
    EXPORT = ROOT / "figures/export"
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    fig.savefig(PREVIEW, dpi=160, facecolor=C["surface"])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(EXPORT / f"fig3d_icons.{ext}", dpi=DPI_EXPORT,
                    facecolor=C["surface"])

    # attribution sidecar (required if this ever ships)
    attrs = collections.Counter(a for _im, a in icons.values())
    attr_path = ROOT / "figures/attribution/fig3d_icons.txt"
    attr_path.parent.mkdir(parents=True, exist_ok=True)
    attr_path.write_text(
        "PhyloPic silhouettes used by figures/export/fig3d_icons.*\n"
        f"({sum(attrs.values())} images, via scripts/fetch_phylopic.py)\n\n"
        + "\n".join(f"{n:3d} images — {name}" for name, n in
                    sorted(attrs.items(), key=lambda kv: -kv[1])))

    print(f"wrote {PREVIEW.relative_to(ROOT)} + export set")
    print(f"  drawn: {len(pts)} species with icons+location "
          f"(of {len(universe)} gap species)")
    print(f"  skipped: {len(skipped_no_icon)} without silhouette match, "
          f"{len(skipped_no_loc)} without any location")
    print(f"  attribution -> {attr_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
