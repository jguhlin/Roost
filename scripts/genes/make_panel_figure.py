#!/usr/bin/env python3
"""
Publication figure: gene panel presence across bird clades.

Reads figures/panel_data.json (written by make_panel_heatmap.py) and renders
compact print-ready figures — order level (main) and family level
(supplementary) — as SVG (editable text) + PNG (600 dpi).

Layout, left → right:
  phylogeny (pruned BirdTree) · clade names · coverage bars
  (genome-searched vs imputed species, cumulative sqrt scale) ·
  heatmap (individual key genes + tier aggregates + full-panel summary) ·
  colourbar. Each cell split diagonally: upper-left triangle = observed
  species mean, lower-right = imputed species mean.

Vertical zones (top→bottom): staggered group labels (2 rows) · group
brackets · rotated column labels · prevalence strip · heatmap rows · legend.

Usage: pixi run python scripts/genes/make_panel_figure.py
Output: figures/gene_panel_clades_{order,family}.{svg,png}
"""

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Polygon, Rectangle

ROOT = Path(__file__).resolve().parent.parent.parent
FIG = ROOT / "figures"

CMAP = LinearSegmentedColormap.from_list(
    "panel", ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"])
GREY = "#e4e8ee"
OBS_C, IMP_C = "#2b6cb0", "#6a00a8"

# ultra-short group labels for the (narrow) column brackets; brackets whose
# labels would still overflow alternate between two label rows
GROUP_SHORT = {
    "Critical": "critical",
    "Tier-1 · Dependency": "T1-depend",
    "Tier-1 · Sensor": "T1-sensor",
    "Tier-1 · Effector": "T1-effect",
    "Tier-1 · Signaling": "T1-signal",
    "Tier-1 · Tolerance": "T1-toler",
    "High importance": "high importance",
    "Tier-2 · Host Gene": "T2-host",
    "Tier-2 · Immune Response": "T2-immR",
    "Tier-2 · Host Factor": "T2-hostF",
    "Tier-2 · Pattern Recognition": "T2-PRR",
    "Tier-2 · ISG": "T2-ISG",
    "Tier-2 · Antiviral Response": "T2-antiv",
    "Tier-3 · Immune (GO)": "T3-immune",
    "Summary": "panel",
}
AGG_SHORT = {
    "Host Gene": "host gene", "Immune Response": "immune resp.",
    "Host Factor": "host factor", "Pattern Recognition": "pattern rec.",
    "ISG": "ISG", "Antiviral Response": "antiviral",
    "Immune (GO)": "immune (GO)", "FULL PANEL": "full panel",
}


def colw(c, gene_w, agg_w):
    return gene_w if c["kind"] == "gene" else (agg_w if c["kind"] == "agg" else agg_w + 0.05)


def draw(level, stem):
    D = json.loads((FIG / "panel_data.json").read_text())
    cols, rows, tree = D["cols"], D[level]["rows"], D[level]["tree"]
    N = len(rows)
    order_view = level == "order"

    # ---- geometry (inches) --------------------------------------------------
    row_h = 0.168 if order_view else 0.082
    gene_w, agg_w = 0.078, 0.17
    TREE_W, LBL_W, COV_W = 0.92, 1.42, 0.62
    M_L, M_R, M_T, FOOT_H = 0.05, 0.20, 0.05, 0.34
    # vertical zones: group labels (2 staggered rows) → brackets → rotated
    # column labels → prevalence strip → heatmap
    GRP_A, GRP_B, BRK_Y, STRIP_Y = 0.11, 0.23, 0.30, 0.90
    HEAD_H = 1.04
    CB_W = 0.11
    CB_X_EXTRA = 0.16  # gap + colorbar + its label
    heat_w = sum(colw(c, gene_w, agg_w) + 0.012 for c in cols) + 0.10
    W = M_L + TREE_W + LBL_W + COV_W + heat_w + CB_X_EXTRA + CB_W + M_R
    H = M_T + HEAD_H + N * row_h + FOOT_H

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "svg.fonttype": "none",
        "pdf.fonttype": 42, "text.color": "#1c2733",
    })
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)  # y grows downward, matching the zone constants
    ax.axis("off")

    fs_lab = 6.3 if order_view else 3.6
    fs_col = 4.3 if order_view else 3.1
    fs_grp = 4.2 if order_view else 3.0

    Y = lambda i: M_T + HEAD_H + i * row_h
    CY = lambda i: Y(i) + row_h / 2
    X0 = M_L
    LBL_X = X0 + TREE_W
    COV_X = LBL_X + LBL_W
    HEAT_X = COV_X + COV_W + 0.08

    colx, cx = [], HEAT_X + 0.05
    for c in cols:
        colx.append(cx)
        cx += colw(c, gene_w, agg_w) + 0.012
    HEAT_END = cx

    # ---- phylogeny ----------------------------------------------------------
    xd = (TREE_W - 0.10) / (tree["max_depth"] or 1)
    segs = []
    for dp, cy, dc in tree["h"]:
        y = CY(cy)
        segs.append([(X0 + dp * xd, y), (X0 + dc * xd, y)])
    for dp, ymin, ymax in tree["v"]:
        x = X0 + (dp + 1) * xd
        segs.append([(x, CY(ymin)), (x, CY(ymax))])
    ax.add_collection(LineCollection(segs, colors="#7d94a8", linewidths=0.5,
                                     capstyle="round"))

    # ---- rows: labels, coverage bars, cells ---------------------------------
    maxN = max(r["n_obs"] + r["n_imp"] for r in rows) or 1
    for i, r in enumerate(rows):
        y = Y(i)
        ax.plot([X0 + tree["max_depth"] * xd, LBL_X - 0.05], [CY(i)] * 2,
                color="#7d94a8", lw=0.4, zorder=1)
        ax.text(LBL_X, CY(i), r["name"], ha="left", va="center",
                fontsize=fs_lab, fontweight="bold" if order_view else "normal")
        bh = min(row_h * 0.55, 0.10)
        by = CY(i) - bh / 2
        ax.add_patch(Rectangle((COV_X, by), COV_W - 0.10, bh, fc="#eef1f5",
                               ec="none"))
        s_obs = math.sqrt(r["n_obs"] / maxN)
        s_tot = math.sqrt((r["n_obs"] + r["n_imp"]) / maxN)
        if r["n_obs"]:
            ax.add_patch(Rectangle((COV_X, by), s_obs * (COV_W - 0.10), bh,
                                   fc=OBS_C, ec="none"))
        if r["n_imp"]:
            ax.add_patch(Rectangle((COV_X + s_obs * (COV_W - 0.10), by),
                                   (s_tot - s_obs) * (COV_W - 0.10), bh,
                                   fc=IMP_C, ec="none"))
        for j, c in enumerate(cols):
            w = colw(c, gene_w, agg_w)
            x0, hgt = colx[j], row_h - 0.014
            vo, vi = r["vals_obs"][j], r["vals_imp"][j]
            ax.add_patch(Rectangle((x0, y + 0.007), w, hgt,
                                   fc=GREY if vo is None else CMAP(vo / 100),
                                   ec="white", lw=0.25))
            if r["n_imp"] and vi is not None:
                ax.add_patch(Polygon(
                    [[x0 + w, y + 0.007], [x0 + w, y + 0.007 + hgt],
                     [x0, y + 0.007 + hgt]],
                    closed=True, fc=CMAP(vi / 100), ec="white", lw=0.25))

    # ---- prevalence strip ----------------------------------------------------
    for j, c in enumerate(cols):
        w = colw(c, gene_w, agg_w)
        m = D[level]["col_means"][j]
        ax.add_patch(Rectangle((colx[j], STRIP_Y), w, 0.10,
                               fc=GREY if m is None else CMAP(m / 100),
                               ec="white", lw=0.25))

    # ---- rotated column labels (zone BRK_Y+0.05 … STRIP_Y-0.01) -------------
    for j, c in enumerate(cols):
        w = colw(c, gene_w, agg_w)
        if c["kind"] == "gene":
            lbl = c["label"]
        else:
            lbl = AGG_SHORT.get(c["label"].split(" (")[0],
                                c["label"].split(" (")[0])
        ax.text(colx[j] + w / 2, STRIP_Y - 0.015, lbl, rotation=90,
                ha="center", va="bottom", fontsize=fs_col,
                fontweight="bold" if c["kind"] != "gene" else "normal")
    ax.text(HEAT_X - 0.045, STRIP_Y + 0.05, "mean\npresence", rotation=90,
            ha="center", va="center", fontsize=fs_col - 0.3, color="#5b6b7b")

    # ---- group brackets + staggered short labels ----------------------------
    groups, seen = [], set()
    for j, c in enumerate(cols):
        if c["group"] not in seen:
            seen.add(c["group"])
            groups.append((c["group"], j))
    groups.append((None, len(cols)))
    for gi, ((g, j0), (_, j1)) in enumerate(zip(groups, groups[1:])):
        x0 = colx[j0] - 0.006
        x1 = colx[j1 - 1] + colw(cols[j1 - 1], gene_w, agg_w) + 0.006
        ax.plot([x0, x1], [BRK_Y, BRK_Y], color="#33475a", lw=0.7,
                solid_capstyle="butt")
        ax.plot([x0, x0], [BRK_Y, BRK_Y + 0.035], color="#33475a", lw=0.7)
        ax.plot([x1, x1], [BRK_Y, BRK_Y + 0.035], color="#33475a", lw=0.7)
        lab = GROUP_SHORT.get(g, g)
        # stagger: narrow groups alternate rows; wide groups hug the bracket
        span = x1 - x0
        approx_w = len(lab) * fs_grp * 0.0105  # ≈ char width in inches
        if approx_w <= span:
            ax.text((x0 + x1) / 2, BRK_Y + 0.05, lab, ha="center",
                    va="bottom", fontsize=fs_grp, fontweight="bold",
                    color="#33475a")
        else:
            yy = GRP_A if gi % 2 == 0 else GRP_B
            ax.text(x0, yy - 0.055, lab, ha="left", va="bottom",
                    fontsize=fs_grp, fontweight="bold", color="#33475a")
            ax.plot([x0, x0], [yy, BRK_Y], color="#33475a55", lw=0.35)

    # ---- colourbar (dedicated axes — no space stealing) ----------------------
    sm = mpl.cm.ScalarMappable(cmap=CMAP, norm=Normalize(0, 100))
    grad = np.linspace(1, 0, 256).reshape(-1, 1)
    cb_x = HEAT_END + 0.07
    heat_h = N * row_h
    cax = fig.add_axes([cb_x / W, M_T + HEAD_H / H, 0.10 / W, heat_h / H])
    cax.imshow(grad, cmap=CMAP, aspect="auto", extent=[0, 1, 100, 0])
    cax.set_xticks([])
    cax.set_yticks([0, 25, 50, 75, 100])
    cax.tick_params(labelsize=4.2, width=0.4, length=1.5, pad=1.0)
    for s in cax.spines.values():
        s.set_linewidth(0.4)
    cax.set_ylabel("% genes FULL", fontsize=4.2, labelpad=1.5)

    # ---- legend ---------------------------------------------------------------
    ly = H - FOOT_H + 0.07
    lx = M_L
    g1w, g1h = 0.16, 0.11
    ax.add_patch(Rectangle((lx, ly), g1w, g1h, fc=CMAP(0.75), ec="#33475a",
                           lw=0.4))
    ax.add_patch(Polygon([[lx + g1w, ly], [lx + g1w, ly + g1h],
                          [lx, ly + g1h]], closed=True, fc=CMAP(0.3),
                         ec="#33475a", lw=0.4))
    ax.text(lx + g1w + 0.05, ly + g1h / 2,
            "cell mean: ▲ observed / ▼ imputed species",
            ha="left", va="center", fontsize=4.6)
    g2x = lx + 2.10
    ax.add_patch(Rectangle((g2x, ly), 0.08, g1h, fc=OBS_C, ec="none"))
    ax.add_patch(Rectangle((g2x + 0.08, ly), 0.08, g1h, fc=IMP_C, ec="none"))
    ax.text(g2x + 0.21, ly + g1h / 2,
            "species per clade: genome-sequenced (blue) / imputed (purple)",
            ha="left", va="center", fontsize=4.6)
    ax.text(W - M_R, ly + g1h / 2,
            f"{D['meta']['panel_version']} · {D['meta']['genes']} genes",
            ha="right", va="center", fontsize=4.2, color="#5b6b7b")

    for ext, kwargs in (("svg", {}), ("png", {"dpi": 600})):
        out = FIG / f"{stem}.{ext}"
        fig.savefig(out, facecolor="white", **kwargs)
        print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB, "
              f"{W:.2f}×{H:.2f} in)")
    plt.close(fig)


def main():
    draw("order", "gene_panel_clades_order")
    draw("family", "gene_panel_clades_family")


if __name__ == "__main__":
    main()
