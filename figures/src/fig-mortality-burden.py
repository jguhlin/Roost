#!/usr/bin/env python3
"""Fig: true mortality burden of H5N1 2.3.4.4b (v2, house style).

Data figure for `#/research/what-is-the-true-mortality-burden-of-h5n1-clade-2344b-in-wild-bird`.
Official notifications vs field counts (log), plus the why-the-gap panel.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from style import apply_style, C, panel_label, source_line, save  # noqa: E402

apply_style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NAME = "fig-mortality-burden"

fig = plt.figure(figsize=(10.5, 6.8), dpi=160)
gs = fig.add_gridspec(2, 1, height_ratios=[1.55, 1.0], hspace=0.58)

# ---- the under-count, as numbers ----
ax = fig.add_subplot(gs[0])
labels = ["Sandwich terns\nWAHIS notifications\n(since Oct 2021)",
          "Sandwich terns\nfield count, NL + BE\n(2 months, 2022)",
          "Peruvian pelicans\nfield count, Peru\n(2023)"]
vals = [35, 20531, 61844]
bars = ax.bar(labels, vals, width=0.5,
              color=[C["muted"], C["alert"], C["alert"]],
              edgecolor=C["ink"], linewidth=0.6, zorder=3)
ax.set_yscale("log")
ax.set_ylim(10, 300000)
ax.set_ylabel("count (log scale)")
panel_label(ax, "A", "Official notifications vs field mortality")
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v * 1.35, f"{v:,}",
            ha="center", fontsize=14, fontweight="bold", color=C["ink"])
ax.annotate("", xy=(1, 32000), xytext=(0, 300),
            arrowprops=dict(arrowstyle="->", color=C["alert"], lw=1.8,
                            connectionstyle="arc3,rad=-0.2"))
ax.text(0.52, 48000, "≈586× under-counted", color=C["alert"],
        fontsize=13, fontweight="bold", ha="center")
ax.tick_params(axis="x", labelsize=10.5)

# ---- why the gap ----
ax2 = fig.add_subplot(gs[1])
ax2.set_xlim(0, 10), ax2.set_ylim(0, 2), ax2.axis("off")
panel_label(ax2, "B", "Why the gap", pad=6)
facts = [
    ("host range", ">130 non-waterfowl species newly infected since 2022 "
     "[migratory_geospatial2025]", C["primary"]),
    ("recurrence", "US outbreaks recur annually, ~6-month seasonal span (2022–2025)",
     C["primary"]),
    ("cryptic deaths", "remote colonies + migratory habitats: carcasses never counted",
     C["alert"]),
    ("surveillance", "passive reporting sensitivity is low; lab confirmation rarer still",
     C["alert"]),
]
for i, (k, v, c) in enumerate(facts):
    y = 1.58 - i * 0.46
    ax2.add_patch(FancyBboxPatch((0.05, y - 0.14), 1.5, 0.36,
                  boxstyle="round,pad=0.02,rounding_size=0.08",
                  fc=C["card"], ec=c, lw=1.8))
    ax2.text(0.8, y, k, ha="center", va="center", fontsize=10,
             fontweight="bold", color=c)
    ax2.text(1.75, y, v, ha="left", va="center", fontsize=10.5, color=C["ink"])

source_line(fig, "Sources: NL/BE Sandwich tern surveys; risk_southern_ocean_practical_2023 "
                 "(Peruvian pelicans); migratory_geospatial2025.  Figure: fig-mortality-burden (v2).")

save(fig, NAME, ROOT)
