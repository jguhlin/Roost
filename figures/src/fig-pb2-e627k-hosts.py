#!/usr/bin/env python3
"""Fig: functional consequence of PB2 E627K across host species (v2, house style).

Data figure for the briefing
`#/research/what-is-the-functional-consequence-of-pb2-e627k-in-different-host`.

v2: house style (Lato, tokens, panel labels); panel A keeps the qualitative
log ordering, panel B the three host contexts as token-colored cards.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from style import apply_style, C, panel_label, source_line, save  # noqa: E402

apply_style()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NAME = "fig-pb2-e627k-hosts"

fig = plt.figure(figsize=(10.5, 7.0), dpi=160)
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.05], hspace=0.55)

# ---- Panel A: human minireplicon (qualitative ordering) ----
axA = fig.add_subplot(gs[0])
conditions = ["avian euDG 2.3.4.4b\n(PB2 627E, native)", "bovine B3.13\nreconstructed",
              "avian euDG\n+ PB2 E627K"]
vals = [1.0, 1.8, 25.0]
bars = axA.bar(conditions, vals, width=0.5,
               color=[C["primary"], C["faint"], C["alert"]],
               edgecolor=C["ink"], linewidth=0.6, zorder=3)
axA.set_yscale("log")
axA.set_ylim(0.5, 90)
axA.set_ylabel("relative polymerase activity\n(human-cell minireplicon, log)")
panel_label(axA, "A", "Human cells: E627K is a major gain of function")
for b, lab in zip(bars, ["baseline", "~2×", "≈25×"]):
    axA.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.3, lab,
             ha="center", fontsize=13, fontweight="bold", color=C["ink"])
axA.text(0.985, 0.05,
         "ordering from [matthew2025]: E627K ≫ native euDG and reconstructed B3.13\n"
         "(heights qualitative, log scale)",
         transform=axA.transAxes, ha="right", fontsize=10, color=C["muted"])

# ---- Panel B: three host contexts ----
axB = fig.add_subplot(gs[1])
axB.set_xlim(0, 10), axB.set_ylim(0, 2.1), axB.axis("off")
panel_label(axB, "B", "Same substitution, three host contexts", pad=6)

boxes = [
    (0.1, "HUMAN", C["alert"], C["alert_bg"],
     "E627K: large activity boost,\nreplication + pathogenicity ↑\nclassic mammalian marker"),
    (3.4, "CATTLE (B3.13)", C["caution"], C["caution_bg"],
     "E627K largely absent — adaptation\nruns through PB2 M631L + PA K497R;\navian-like ancestor ~10× weaker"),
    (6.7, "AVIAN", C["good"], C["good_bg"],
     "627E maintained; ANP32A with the\n33-aa insert supports the polymerase.\nE627K not required."),
]
for x, head, ec, fc, body in boxes:
    axB.add_patch(FancyBboxPatch((x, 0.25), 3.1, 1.55,
                  boxstyle="round,pad=0.02,rounding_size=0.1",
                  fc=fc, ec=ec, lw=2.0, zorder=2))
    axB.text(x + 1.55, 1.58, head, ha="center", fontsize=13.5,
             fontweight="bold", color=ec, zorder=3)
    axB.text(x + 1.55, 0.86, body, ha="center", va="center", fontsize=10.5,
             color=C["ink"], zorder=3, linespacing=1.5)
axB.text(5.0, 0.06,
         "epistasis: in cattle backgrounds E627K is masked by alternative mammalizing mutations",
         ha="center", fontsize=10, color=C["muted"], style="italic")

source_line(fig, "Sources: briefing corpus — [matthew2025]; [pb2_cattle_adaptation2026]; "
                 "[mammal_adaptations_review2025].  Figure: fig-pb2-e627k-hosts (v2).")

save(fig, NAME, ROOT)
