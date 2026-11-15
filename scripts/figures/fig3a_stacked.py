#!/usr/bin/env python3
"""Figure 3 panel A — alternative rendering: stacked bars (exploration).

One row per order (species-count order), universe = species with detected
H5N1; bird orders with a single detected species fold into "other birds";
the two mammal categories (Carnivora; other mammals — generic-Mammalia
index entries fold in) stay separate at the bottom as class-level entries. Stacks: studied species split by gene-link depth (>=20 / 5-19 /
1-4, blues), genome-available unstudied (amber), no genome (red).

Standalone file on purpose: to be examined next to the grid version of
panel A (fig3_gaps) before deciding which encoding ships.

  reads:  web/public/data/species_index.json       (universe + genomes)
          web/public/data/gene_host_species.json   (studied set)
          web/public/data/species.parquet          (class -> mammals)
  writes: figures/preview/fig3a_stacked.png
          figures/export/fig3a_stacked.{png,svg,pdf}
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
from style import C, apply_style, source_line  # noqa: E402

apply_style()

import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

# "index"  = full species index (721; matches fig3_gaps panel B)
# "detected" = species with recorded detections only (717; the standalone)
UNIVERSE_MODE = "detected"
PANEL_ASSET = ROOT / "figures/src/assets/fig3/panel_a_stacked.png"

si = json.loads((ROOT / "web/public/data/species_index.json").read_text())
ghs = json.loads((ROOT / "web/public/data/gene_host_species.json").read_text())
spq = pl.read_parquet(ROOT / "web/public/data/species.parquet")
MAMMAL_ORDERS = set(spq.filter(pl.col("class") == "Mammalia")["order"]
                    .unique().to_list())

def canon(name: str) -> str:
    parts = str(name).strip().split()
    return " ".join(parts[:2]).lower()

# this chart's universe: species with detected H5N1 (the index also carries
# a handful of tracked-but-undetected hosts, excluded here to match the title)
_keep = (lambda s: s.get("det")) if UNIVERSE_MODE == "detected" \
    else (lambda s: True)
index = {canon(s["sci"]): s for s in si if _keep(s)}
studied_genes = collections.Counter()
for v in ghs.values():
    for sp in v.get("species", []):
        studied_genes[canon(sp)] += 1
genome = {c for c, s in index.items() if s.get("genome_acc")}

def row_label(s) -> str:
    """Bird orders by name; mammals split into three system categories:
    Carnivora (the big clade), Mammalia (generic index entries — two
    pinnipeds), and other mammals."""
    o = s.get("ord")
    if o == "Carnivora":
        return "carnivora"
    if o == "Mammalia" or o in MAMMAL_ORDERS:
        return "other mammals"      # generic-Mammalia entries fold in too
    return o or "—"

def bucket(c):
    n = studied_genes.get(c, 0)
    if n >= 20:
        return "ge20"
    if n >= 5:
        return "5_19"
    if n >= 1:
        return "1_4"
    if c in genome:
        return "genome_unstudied"
    return "no_genome"

rows = collections.defaultdict(collections.Counter)
for c, s in index.items():
    rows[row_label(s)][bucket(c)] += 1

# bird orders by species count; single-species bird orders fold into an
# "other birds" bucket; the three mammal categories stay separate at the
# bottom (class-level entries, deliberately unfused)
MAMMAL_ROWS = ["carnivora", "other mammals"]
bird_labels = sorted((k for k in rows if k.lower() not in MAMMAL_ROWS),
                     key=lambda k: -sum(rows[k].values()))
_singles = [k for k in bird_labels if sum(rows[k].values()) < 2]
if _singles:
    agg = collections.Counter()
    for k in _singles:
        agg.update(rows.pop(k))
    rows["other birds"] = agg
bird_labels = sorted((k for k in rows if k.lower() not in MAMMAL_ROWS
                      and k != "other birds"),
                     key=lambda k: -sum(rows[k].values())) + ["other birds"]
mammal_labels = [m for m in MAMMAL_ROWS if m in rows]
labels = bird_labels + mammal_labels

SERIES = [
    ("ge20", "studied ≥20 genes", "#1d4ed8"),
    ("5_19", "studied 5–19", "#60a5fa"),
    ("1_4", "studied 1–4", "#bfdbfe"),
    ("genome_unstudied", "genome, unstudied", "#d97706"),
    ("no_genome", "no genome", "#dc2626"),
]

def render(ax, labels, rows, *, panel: bool):
    """Draw the stacked bars; panel=True drops the title and shrinks type
    so the chart can sit inside fig3 panel A at 1:1 print scale."""
    y = list(range(len(labels)))[::-1]
    left = [0.0] * len(labels)
    for key, lab, color in SERIES:
        vals = [rows[k].get(key, 0) for k in labels]
        ax.barh(y, vals, left=left, height=0.68, color=color,
                edgecolor="none", label=lab)
        left = [l + v for l, v in zip(left, vals)]
    fs_y = 5.2 if panel else 7
    ax.set_yticks(y)
    ax.set_yticklabels([k.lower() for k in labels], fontsize=fs_y)
    # birds carry the emphasis (Roost's focus); the mammal tail rows sit back
    for lbl, k in zip(ax.get_yticklabels(), labels):
        lbl.set_color(C["faint"] if k.lower() in MAMMAL_ROWS else C["ink"])
    ax.set_xlabel("Species" if panel else "species", fontsize=7 if panel else 8,
                  color=C["muted"])
    ax.set_xlim(0, max(sum(v.values()) for v in rows.values()) * 1.10)
    ax.tick_params(axis="x", labelsize=6.4 if panel else 7,
                   colors=C["muted"], length=2.5)
    ax.tick_params(axis="y", length=0, pad=1.5)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#cbd5e1")
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.6)
    ax.set_axisbelow(True)
    if not panel:
        ax.set_title("Species with detected H5N1 per order by knowledge "
                     "state", loc="left", fontsize=8.5, fontweight="bold",
                     color=C["ink"])
    ax.legend(loc="lower right", fontsize=5.6 if panel else 6.6,
              frameon=False, handlelength=1.0, handleheight=0.9,
              labelspacing=0.3)

# ---- panel-mode asset for fig3 panel A (index universe, 1:1 scale) ----
if UNIVERSE_MODE == "detected" and PANEL_ASSET.exists():
    pass  # standalone run below regenerates with detected universe
if True:  # keep indentation flat for the panel render
    _mode_saved = UNIVERSE_MODE
    fig_p, ax_p = plt.subplots(figsize=(3.42, 2.17))
    render(ax_p, labels, rows, panel=True)
    fig_p.tight_layout(pad=0.25)
    PANEL_ASSET.parent.mkdir(parents=True, exist_ok=True)
    fig_p.savefig(PANEL_ASSET, dpi=600, facecolor=C["surface"])
    plt.close(fig_p)

fig, ax = plt.subplots(figsize=(4.7, 6.9))
render(ax, labels, rows, panel=False)
fig.tight_layout(pad=0.4)
PREVIEW = ROOT / "figures/preview/fig3a_stacked.png"
EXPORT = ROOT / "figures/export"
PREVIEW.parent.mkdir(parents=True, exist_ok=True)
EXPORT.mkdir(parents=True, exist_ok=True)
fig.savefig(PREVIEW, dpi=200, facecolor=C["surface"])
for ext in ("png", "svg", "pdf"):
    fig.savefig(EXPORT / f"fig3a_stacked.{ext}", facecolor=C["surface"])
print(f"wrote {PREVIEW.relative_to(ROOT)} + export set")
print(f"  rows={len(labels)} folded-singles={len(_singles)} "
      f"species={sum(sum(v.values()) for v in rows.values())}")
