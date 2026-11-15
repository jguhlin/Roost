#!/usr/bin/env python3
"""Fig: which chicken ANP32 isoforms support influenza polymerase? (v2, house style)

Data figure for `#/research/what-is-the-minimal-anp32-isoform-requirement-for-productive`.
Functional matrix with token styling.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from style import apply_style, C, source_line, save  # noqa: E402

apply_style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NAME = "fig-anp32-isoforms"

GREEN = dict(fc=C["good_bg"], ec=C["good"], tc="#14532d")
RED = dict(fc=C["alert_bg"], ec=C["alert"], tc="#7f1d1d")
AMBER = dict(fc=C["caution_bg"], ec=C["caution"], tc="#78350f")
GRAY = dict(fc="#f1f5f9", ec="#94a3b8", tc=C["muted"])

cols = ["ANP32A\n(chicken)", "ANP32B\n(chicken)", "ANP32E\n(chicken)", "none\n(triple KO)"]
rows = ["Virus replication\n(infectious virus)",
        "Polymerase support\n(minireplicon)",
        "Rescue in heterologous\ncells (eHAP DKO)"]

cells = [
    [dict(st=GREEN, text="productive H5N1 + H7N9\nreplication — A alone is\nnecessary + sufficient"),
     dict(st=RED, text="no replication\n(non-functional paralog)"),
     dict(st=RED, text="no compensation\nfor loss of A"),
     dict(st=RED, text="cells refractory —\nno detectable virus")],
    [dict(st=GREEN, text="robust activity;\nspecies-matched A required"),
     dict(st=RED, text="no support"),
     dict(st=AMBER, text="insufficient alone\n(partial redundancy)"),
     dict(st=RED, text="none")],
    [dict(st=GREEN, text="chicken A supports avian\nAIV07 + cattle/Texas\nprecursor polymerase"),
     dict(st=RED, text="FLAG-chANP32B does NOT\nrescue in eHAP1 A/B DKO"),
     dict(st=GRAY, text="not tested alone\nin this corpus"),
     dict(st=GRAY, text="—")],
]

fig, ax = plt.subplots(figsize=(11.5, 6.6), dpi=160)
ax.set_xlim(0, 4), ax.set_ylim(0, 3), ax.invert_yaxis(), ax.axis("off")
ax.set_title("ANP32A alone is necessary and sufficient — the others don't compensate",
             fontsize=15, fontweight="bold", color=C["ink"], loc="left", pad=14)

for j, c in enumerate(cols):
    ax.text(j + 0.5, -0.22, c, ha="center", va="bottom", fontsize=11,
            fontweight="bold", color=C["ink"])
for i, r in enumerate(rows):
    ax.text(-0.08, i + 0.5, r, ha="right", va="center", fontsize=10, color=C["ink"])

for i in range(3):
    for j in range(4):
        st, text = cells[i][j]["st"], cells[i][j]["text"]
        ax.add_patch(FancyBboxPatch((j + 0.05, i + 0.09), 0.90, 0.82,
                      boxstyle="round,pad=0.01,rounding_size=0.04",
                      fc=st["fc"], ec=st["ec"], lw=2.0, zorder=2))
        ax.text(j + 0.5, i + 0.5, text, ha="center", va="center",
                fontsize=9.5, color=st["tc"], zorder=3)

ax.text(2.0, 3.35,
        "Dose-dependent escape: N129I-D130N editing slows — but does not stop — the virus; "
        "compensatory PA-349K + PB2-M631L emerges at high dose",
        ha="center", va="center", fontsize=10, color=C["muted"], style="italic",
        bbox=dict(boxstyle="round,pad=0.5", fc=C["caution_bg"],
                  ec=C["caution"], lw=1.2))

legend = [(C["good_bg"], C["good"], "supports"), (C["alert_bg"], C["alert"], "does not support"),
          (C["caution_bg"], C["caution"], "partial/conditional"), ("#f1f5f9", "#94a3b8", "not tested")]
for k, (fc, ec, lab) in enumerate(legend):
    x0 = 0.02 + k * 0.235
    ax.add_patch(FancyBboxPatch((x0, 3.24), 0.035, 0.15,
                  boxstyle="round,pad=0.005,rounding_size=0.01",
                  fc=fc, ec=ec, lw=1.5, transform=ax.transAxes, clip_on=False))
    ax.text(x0 + 0.05, 3.315, lab, fontsize=9.5, color=C["muted"],
            transform=ax.transAxes, va="center")

source_line(fig, "Sources: chicken PGC-derived fibroblast KO studies; eHAP/eHAP1 complementation; "
                 "ANP32A-editing escape experiment (briefing corpus).  Figure: fig-anp32-isoforms (v2).")

save(fig, NAME, ROOT)
