#!/usr/bin/env python3
"""first_detection_timeline.py — cumulative species-first-detection curve.

The claim this figure supports: HPAI's host range expanded in waves — a
slow Southeast-Asia/Europe trickle (2004-2013), the H5N8-era broadening
(2014-2019), then the 2.3.4.4b panzootic's explosive addition of hosts
(2020-2026, including the mammal wave from 2020 on). Every point is a
REAL first detection record in the Roost registry — no smoothing, no
interpolation.

Data: data/species_first_records.json (713 species with ≥1 HPAI detection,
first/last stamps computed from the deduplicated detection registry).
'First detection' = earliest dated record for that species in Roost's
merged sources; species whose records carry no parseable date (120) are
excluded from the timeline and noted in the caption.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "species_first_records.json"
OUT = ROOT / "figures" / "export"
PREVIEW = ROOT / "figures" / "preview"
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)

# ---- data ------------------------------------------------------------------
regs = json.loads(SRC.read_text())["registrations"]

# class split: mammals via order column of the detected profiles is cleanest,
# but the registry carries registered_via from aphis_mammals only partially —
# use NCBI-class via the known mammal list in the profiles table
import polars as pl
prof = pl.read_parquet(ROOT / "data" / "species_profiles_detected.parquet",
                       columns=["scientific_name", "class"])
mammals = set(prof.filter(pl.col("class") == "Mammalia")["scientific_name"].to_list())

events = []  # (date, is_mammal, sci)
undated = 0
for r in regs:
    fd = r.get("first_detection")
    sci = r["scientific_name"]
    if not fd:
        undated += 1
        continue
    d = date.fromisoformat(str(fd)[:10])
    events.append((d, sci in mammals, sci))
events.sort(key=lambda e: e[0])
print(f"{len(events)} dated first-detections ({undated} undated excluded), "
      f"{sum(1 for _, m, _ in events if m)} mammals")

# cumulative curves
dates = [e[0] for e in events]
cum_total = np.arange(1, len(events) + 1)
cum_mammal = np.cumsum([1 if m else 0 for _, m, _ in events])
cum_bird = cum_total - cum_mammal

# new-species-per-year bars
per_year_total = defaultdict(int)
per_year_mammal = defaultdict(int)
for d, m, _ in events:
    per_year_total[d.year] += 1
    if m:
        per_year_mammal[d.year] += 1
years = sorted(per_year_total)

# ---- figure ----------------------------------------------------------------
plt.rcParams.update({"text.color": "#e2e8f0", "axes.labelcolor": "#e2e8f0", "xtick.color": "#a0aec0", "ytick.color": "#a0aec0", "axes.edgecolor": "#4a5568", "font.family": "sans-serif"})
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(10.5, 7.2), sharex=True,
    gridspec_kw={"height_ratios": [2.1, 1], "hspace": 0.08})

BIRD = "#56B4E9"       # blue
MAMMAL = "#E69F00"     # warm orange (not red/green pair)
TOT = "#F7FAFC"

# panel A — cumulative host species
ax1.plot(dates, cum_total, color=TOT, lw=2.2, label="All hosts", zorder=3)
ax1.fill_between(dates, cum_bird, color=BIRD, alpha=0.30, zorder=1)
ax1.plot(dates, cum_bird, color=BIRD, lw=1.8, label="Birds", zorder=2)
ax1.plot(dates, cum_mammal, color=MAMMAL, lw=1.8, label="Mammals", zorder=2)
ax1.set_ylabel("Host species with HPAI detections\n(cumulative)", fontsize=10)

# era shading + annotations (windows from the spread-eras ledger)
for x0, x1, label in [
    ("2003-06-30", "2013-12-31", "H5N1 Goose/GD lineage\nspreads from Asia"),
    ("2014-01-01", "2019-12-31", "H5N8 clade 2.3.4.4\nera broadening"),
    ("2020-06-01", None, "2.3.4.4b panzootic —\nexplosive host addition"),
]:
    d0 = date.fromisoformat(x0)
    d1 = date.fromisoformat(x1) if x1 else dates[-1]
    ax1.axvspan(d0, d1, color="#F7FAFC", alpha=0.06, zorder=0)
    ax1.text(date.fromordinal((d0.toordinal() + d1.toordinal()) // 2),
             0.97, label, transform=ax1.get_xaxis_transform(),
             ha="center", va="top", fontsize=8, color="#CBD5E0")

ax1.legend(loc="upper left", frameon=False, fontsize=9)
ax1.grid(axis="y", color="#374151", lw=0.5)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# panel B — new host species per year
w = 300
yr_x = [date(y, 7, 1) for y in years]
bird_bar = [per_year_total[y] - per_year_mammal.get(y, 0) for y in years]
mammal_bar = [per_year_mammal.get(y, 0) for y in years]
ax2.bar(yr_x, bird_bar, width=w, color=BIRD, alpha=0.85, label="Birds")
ax2.bar(yr_x, mammal_bar, width=w, bottom=bird_bar, color=MAMMAL,
        alpha=0.95, label="Mammals")
ax2.set_ylabel("New host species\nfirst detected", fontsize=10)
ax2.grid(axis="y", color="#374151", lw=0.5)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

ax2.xaxis.set_major_locator(mdates.YearLocator(2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
plt.setp(ax2.get_xticklabels(), rotation=45, ha="right", fontsize=9)

fig.suptitle("Species entering the documented HPAI host record, 2004–2026",
             fontsize=12.5, y=0.965)
fig.text(0.01, 0.005,
         f"Roost registry: {len(events)} host species with dated entries in the documented HPAI record "
         f"({undated} species undated, excluded). Dates = earliest dated detection in merged surveillance sources "
         f"(APHIS, WAHIS, EMPRES-i, DEFRA, WHISPERS, …) — NOT the species' true first infection, which typically "
         f"predates surveillance coverage for every source.",
         fontsize=7, color="#718096")

for ext in ("svg", "pdf", "png"):
    fig.savefig(OUT / f"first_detection_timeline.{ext}", dpi=200, bbox_inches="tight", transparent=True)
fig.savefig(PREVIEW / "first_detection_timeline.png", dpi=150, bbox_inches="tight", facecolor="#1a202c")
print("written: figures/export/first_detection_timeline.{svg,pdf,png}")
