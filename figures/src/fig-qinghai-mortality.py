#!/usr/bin/env python3
"""Fig: Qinghai Lake 2005 H5N1 mortality — conflicting estimates (v2, house style).

Data figure for the briefing
`#/research/Qinghai-Lake-mortality-discrep-contradiction-investigati`.

v2 redesign (FIGURE_DESIGN.md): the two numbers ARE the figure — display
type, one supporting bar panel (log, labeled), candidate explanations as a
clean card list, timeline strip for context.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from style import apply_style, C, panel_label, source_line, save  # noqa: E402

apply_style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NAME = "fig-qinghai-mortality"

fig = plt.figure(figsize=(10.5, 7.2), dpi=160)
gs = fig.add_gridspec(3, 1, height_ratios=[1.05, 1.0, 0.62], hspace=0.62)

# ===================== Beat 1: the two numbers =====================
axN = fig.add_subplot(gs[0])
axN.set_xlim(0, 10), axN.set_ylim(0, 3), axN.axis("off")
axN.text(0.0, 2.95, "Same event. Two magnitudes.", fontsize=30,
         fontweight="bold", color=C["ink"], va="top")
axN.text(0.0, 2.42, "2005 Qinghai Lake mass mortality — H5N1 Gs/Gd clade 2.2",
         fontsize=15.5, color=C["muted"], va="center")

# left card: the low estimate
axN.add_patch(FancyBboxPatch((0.0, 0.28), 4.1, 1.72,
              boxstyle="round,pad=0.02,rounding_size=0.12",
              fc=C["card"], ec="#cbd5e1", lw=1.2))
axN.text(0.35, 1.62, "Beatriz et al. 2025", fontsize=12.5,
         color=C["muted"], va="center")
axN.text(0.35, 0.98, "1,500", fontsize=76, fontweight="black",
         color=C["muted"], va="center")
axN.text(0.35, 0.48, "“death of 1,500 birds”", fontsize=12.5,
         color=C["faint"], va="center", style="italic")

# right card: the high estimate
axN.add_patch(FancyBboxPatch((5.9, 0.28), 4.1, 1.72,
              boxstyle="round,pad=0.02,rounding_size=0.12",
              fc=C["primary_bg"], ec=C["primary"], lw=2.0))
axN.text(6.25, 1.62, "Alejandro et al. 2025", fontsize=12.5,
         color=C["primary"], va="center")
axN.text(6.25, 0.98, ">6,184", fontsize=76, fontweight="black",
         color=C["primary"], va="center")
axN.text(6.25, 0.48, "“waterfowl, 4 May – 29 Jun 2005 · bar-headed goose hardest hit”",
         fontsize=11.5, color=C["muted"], va="center", style="italic")

# divergence badge on the seam
axN.add_patch(FancyBboxPatch((4.32, 0.72), 1.36, 0.84,
              boxstyle="round,pad=0.02,rounding_size=0.42",
              fc=C["alert"], ec="none"))
axN.text(5.0, 1.22, "≈4.1×", fontsize=26, fontweight="black",
         color="white", ha="center", va="center")
axN.text(5.0, 0.92, "divergence", fontsize=11, color="#fecaca",
         ha="center", va="center")

# ===================== Beat 2: magnitude context =====================
axB = fig.add_subplot(gs[1])
labels = ["Beatriz 2025\nbirds", "Alejandro 2025\nwaterfowl"]
vals = [1500, 6194]
bars = axB.barh(labels, vals, height=0.42,
                color=[C["muted"], C["primary"]], edgecolor=C["ink"], lw=0.6)
axB.set_xscale("log")
axB.set_xlim(500, 30000)
axB.invert_yaxis()
for b, lab in zip(bars, ["1,500", ">6,184"]):
    axB.text(b.get_width() * 1.18, b.get_y() + b.get_height() / 2, lab,
             fontsize=15, fontweight="bold", color=C["ink"], va="center")
panel_label(axB, "A", "Same virus, same lake — the counts differ by more than fourfold (log scale)")
axB.set_xlabel("reported wild-bird deaths")

# candidate explanations card (right of bars)
axB.text(0.98, 0.04,
         "candidate explanations\n"
         "1  temporal scope — early report vs cumulative tally\n"
         "2  taxonomic scope — “birds” vs “waterfowl”\n"
         "3  surveillance intensity at the lake\n"
         "4  mortality definition — confirmed vs field-attributed",
         transform=axB.transAxes, ha="right", va="bottom", fontsize=10.5,
         color=C["muted"],
         bbox=dict(boxstyle="round,pad=0.55", fc=C["caution_bg"],
                   ec=C["caution"], lw=1.2))

# ===================== Beat 3: timeline strip =====================
axT = fig.add_subplot(gs[2])
axT.set_xlim(2004.4, 2025.6), axT.set_ylim(0, 1), axT.axis("off")
panel_label(axT, "B", "Detection at the same site varies sharply by year")
axT.annotate("", xy=(2025.4, 0.42), xytext=(2004.5, 0.42),
             arrowprops=dict(arrowstyle="-|>", color=C["faint"], lw=1.4))
events = [
    (2005.0, "2005 · the contested event\nclade 2.2 mass mortality", C["alert"], 0.62),
    (2022.4, "Jun 2022 · 2.3.4.4b emerges\n8/726 fecal samples (1.1%)", C["primary"], 0.18),
    (2023.4, "2023 · no HP H5\ndetected", C["faint"], 0.62),
]
# goose silhouette at the 2005 marker (Anser anser, PhyloPic, PD — representative
# waterfowl; the event's bar-headed goose isn't in the mirror's permissive set)
_goose = plt.imread(str(ROOT / "figures/src/assets/fig-qinghai-mortality/anser-anser.png"))
axT.imshow(_goose, extent=(2003.6, 2007.2, 0.46, 0.86), aspect="auto", zorder=2,
           origin="upper")
for x, txt, col, y in events:
    axT.plot([x], [0.42], "o", ms=10, color=col, zorder=3)
    axT.annotate(txt, (x, 0.42), xytext=(x, y), ha="center",
                 va="bottom" if y < 0.42 else "top",
                 fontsize=9.8, color=C["ink"], linespacing=1.35)
axT.set_xticks([2005, 2010, 2015, 2020, 2025])
axT.tick_params(axis="x", labelsize=10, colors=C["faint"])
for s in axT.spines.values():
    s.set_visible(False)

source_line(fig, "Sources: briefing corpus — Beatriz et al. 2025; Alejandro et al. 2025; "
                 "xiaoqing2024 (Qinghai surveillance).  Figure: fig-qinghai-mortality (v2).")

save(fig, NAME, ROOT)
