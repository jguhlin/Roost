#!/usr/bin/env python3
"""
Paper figures 2 & 3 from the Roost datasource.

Fig 2 — Order-resolved HPAI detection dynamics, 2004–2026
  (a) monthly detection counts stacked by host order
  (b) host-order composition share (3-month rolling)
  (c) distinct species detected per year
Fig 3 — Susceptibility vs genomic knowledge
  (a) per-order mean susceptibility score vs genome-searched species
      fraction (point size = scored species; labels de-overlapped)
  (b) susceptibility class composition per order

Usage: pixi run python scripts/figures/make_paper_figures.py
Output: figures/fig2_epi_curve.{svg,png}, figures/fig3_susceptibility_gap.{svg,png}
"""

import datetime
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
FIG = ROOT / "figures"

INK, MUT, LINE = "#1c2733", "#5b6b7b", "#d8e0e8"

# Tol-derived qualitative palette (colour-blind safe, print safe, no pale
# yellows); 'Other' always grey
OI = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE",
      "#AA3377", "#332288", "#44AA99", "#882255", "#9AA0A6"]
# sources reporting per-event bird counts for wild birds ("birds affected")
COUNT_SOURCES = ["WHISPERS", "WAHIS", "gisaid_avilist", "uk_defra",
                 "ireland_occurrence"]
# excluded from the wild-bird figure: domestic poultry flock outbreaks
EXCLUDE_SOURCES = ["aphis_flocks"]
CLASS_COLORS = {  # ordered red → blue
    "highly_susceptible": "#b2182b", "susceptible": "#ef8a62",
    "intermediate": "#d8d8d8", "tolerant": "#92c5de",
    "highly_tolerant": "#2166ac",
}
CLASS_ORDER = ["highly_susceptible", "susceptible", "intermediate",
               "tolerant", "highly_tolerant"]

ORDERS = ["Anseriformes", "Accipitriformes", "Charadriiformes", "Galliformes",
          "Strigiformes", "Passeriformes", "Pelecaniformes", "Falconiformes",
          "Suliformes"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "svg.fonttype": "none",
    "pdf.fonttype": 42, "text.color": INK, "axes.edgecolor": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK,
})


def save_checked(fig, stem):
    """Save SVG+PNG; assert no overlapping text (fails loudly)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    texts = [t for t in fig.findobj(mtext.Text)
             if t.get_text().strip() and t.get_visible()]
    boxes = [(t.get_text()[:24], t.get_window_extent(r)) for t in texts]
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            b1, b2 = boxes[i][1], boxes[j][1]
            if b1.overlaps(b2):
                ox = min(b1.x1, b2.x1) - max(b1.x0, b2.x0)
                oy = min(b1.y1, b2.y1) - max(b1.y0, b2.y0)
                if ox > 1.5 and oy > 1.5:
                    bad.append((boxes[i][0], boxes[j][0], round(ox), round(oy)))
    if bad:
        raise SystemExit(f"TEXT OVERLAP in {stem}: {bad[:6]}")
    for ext, kw in (("svg", {}), ("png", {"dpi": 600})):
        out = FIG / f"{stem}.{ext}"
        fig.savefig(out, facecolor="white", **kw)
        print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB)")


def load_monthly(include_poultry=False):
    """Bird detections with parsed dates → monthly counts per order group.

    include_poultry: keep domestic poultry flock outbreaks (aphis_flocks) as
    their own group instead of excluding them.
    """
    """Bird detections with parsed dates → monthly counts per order group."""
    det = pl.read_parquet(DATA / "detections_merged.parquet")
    tax = pl.read_csv(DATA / "aves_taxonomy.tsv", separator="\t").select(
        ["scientific_name", "order"])
    d = det.join(tax, on="scientific_name", how="inner")
    n_total = det.height
    n_bird = d.height
    ds = pl.col("date_detected").str.strip_chars()
    d = d.with_columns(
        pl.when(ds.str.contains(r"^\d{4}-\d{2}-\d{2}$")).then(pl.lit("ymd"))
          .when(ds.str.contains(r"^\d{1,2}/\d{1,2}/\d{4}$")).then(pl.lit("mdy"))
          .when(ds.str.contains(r"^\d{4}-W\d{2}$")).then(pl.lit("iso"))
          .otherwise(pl.lit("?")).alias("p"))
    n_unparsed = d.filter(pl.col("p") == "?").height

    def iso_midweek(s):
        return datetime.date.fromisocalendar(int(s[:4]), int(s[6:8]), 4)

    parsed = pl.concat([
        d.filter(pl.col("p") == "ymd").with_columns(
            pl.col("date_detected").str.strptime(pl.Date, "%Y-%m-%d").alias("date")),
        d.filter(pl.col("p") == "mdy").with_columns(
            pl.col("date_detected").str.strptime(pl.Date, "%m/%d/%Y").alias("date")),
        d.filter(pl.col("p") == "iso").with_columns(
            pl.col("date_detected").map_elements(iso_midweek,
                                                 return_dtype=pl.Date).alias("date")),
    ])
    parsed = parsed.filter(pl.col("date").is_not_null())
    if include_poultry:
        poultry_src = pl.col("source") == "aphis_flocks"
    else:
        poultry_src = pl.lit(False)
    parsed = parsed.filter(poultry_src | ~pl.col("source").is_in(EXCLUDE_SOURCES)).with_columns(
        pl.col("date").dt.truncate("1mo").alias("month"),
        pl.when(poultry_src).then(pl.lit("Poultry flocks"))
          .when(pl.col("order").is_in(ORDERS)).then(pl.col("order"))
          .otherwise(pl.lit("Other")).alias("grp"),
    )
    tag = "incl. poultry flocks" if include_poultry else "wild-bird only"
    print(f"fig2 data ({tag}): {n_total} records → {n_bird} birds → "
          f"{parsed.height} dated events (undated excluded; unparsed {n_unparsed})")

    monthly = (parsed.group_by(["month", "grp"]).len()
               .sort(["month", "grp"]))
    per_year_species = (parsed.with_columns(pl.col("date").dt.year().alias("yr"))
                        .group_by("yr").agg(pl.col("scientific_name").n_unique().alias("n"))
                        .sort("yr"))
    birds_monthly = (parsed.filter(pl.col("source").is_in(COUNT_SOURCES) |
                                     (include_poultry &
                                      (pl.col("source") == "aphis_flocks")))
                     .group_by(pl.col("date").dt.truncate("1mo").alias("month"))
                     .agg(pl.col("detection_count").sum().alias("birds"))
                     .sort("month"))
    return monthly, per_year_species, birds_monthly, parsed


def fig2(include_poultry=False):
    monthly, per_year_species, birds_monthly, parsed = load_monthly(include_poultry)
    months = sorted(monthly["month"].unique().to_list())
    mo = np.array([datetime.datetime(m.year, m.month, m.day) for m in months],
                  dtype="datetime64[s]")
    groups = ORDERS + (["Poultry flocks"] if include_poultry else []) + ["Other"]
    palette = OI[:9] + (["#333333"] if include_poultry else []) + [OI[9]]
    mat = np.zeros((len(groups), len(months)))
    midx = {m: i for i, m in enumerate(months)}
    for row in monthly.iter_rows(named=True):
        mat[groups.index(row["grp"]), midx[row["month"]]] = row["len"]

    W, H = 7.2, 7.15
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor("white")
    ax_a = fig.add_axes([0.085, 0.665, 0.885, 0.225])
    ax_b = fig.add_axes([0.085, 0.44, 0.885, 0.17], sharex=ax_a)
    ax_c = fig.add_axes([0.085, 0.24, 0.885, 0.15], sharex=ax_a)
    ax_d = fig.add_axes([0.085, 0.06, 0.885, 0.15], sharex=ax_a)

    for ax in (ax_a, ax_b, ax_c, ax_d):
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=5.2, width=0.5, length=2)
    for ax in (ax_a, ax_b, ax_c):
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(labelbottom=False, bottom=False)
    ax_d.spines["bottom"].set_visible(True)

    # (a) stacked counts
    cum = np.cumsum(mat, axis=0)
    ax_a.fill_between(mo, 0, cum[0], color=palette[0], lw=0)
    for gi in range(1, len(groups)):
        ax_a.fill_between(mo, cum[gi - 1], cum[gi], color=palette[gi], lw=0)
    ax_a.set_ylabel("detection events / month", fontsize=6, labelpad=1.5)
    ax_a.set_xlim(np.datetime64("2004-01"), np.datetime64("2026-12"))
    ax_a.xaxis.set_major_locator(mdates.YearLocator(2))
    ax_a.tick_params(axis="y", labelsize=5.2)
    ymax = cum[-1].max()
    ax_a.set_ylim(0, ymax * 1.04)

    # (b) composition share (3-month rolling)
    k = np.ones(3) / 3.0
    sm = np.apply_along_axis(
        lambda r: np.convolve(r, k, mode="same"), 1, mat)
    share = sm / sm.sum(axis=0, keepdims=True)
    cums = np.cumsum(share, axis=0)
    ax_b.fill_between(mo, 0, cums[0], color=palette[0], lw=0)
    for gi in range(1, len(groups)):
        ax_b.fill_between(mo, cums[gi - 1], cums[gi], color=palette[gi], lw=0)
    ax_b.set_ylim(0, 1)
    ax_b.set_yticks([0, 0.5, 1])
    ax_b.set_yticklabels(["0", ".5", "1"], fontsize=5.2)
    ax_b.set_ylabel("order share", fontsize=6, labelpad=1.5)

    # (c) distinct species per year — x as datetime64 so the shared axis
    # limits from panel a hold (numeric years would override them and blank a/b)
    yrs = per_year_species["yr"].to_numpy()
    yr_x = np.array([datetime.datetime(int(y), 1, 1) for y in yrs],
                    dtype="datetime64[s]")
    ns = per_year_species["n"].to_numpy()
    ax_c.plot(yr_x, ns, color=INK, lw=0.9, marker="o", ms=2.2, mfc="white",
              mew=0.7)
    ax_c.set_ylabel("species / yr", fontsize=6, labelpad=1.5)
    ax_c.set_ylim(0, ns.max() * 1.1)
    ax_c.margins(x=0)

    # (d) birds reported affected (count-reporting wild-bird sources), log
    bm = {r["month"]: r["birds"] for r in birds_monthly.iter_rows(named=True)}
    bmo = np.array([datetime.datetime(m.year, m.month, m.day) for m in months],
                   dtype="datetime64[s]")
    bv = np.array([bm.get(m, 0) for m in months], dtype=float)
    ax_d.plot(bmo, np.maximum(bv, 0.5), color="#882255", lw=0.8)
    ax_d.fill_between(bmo, 0.5, np.maximum(bv, 0.5), color="#88225533", lw=0)
    ax_d.set_yscale("log")
    import matplotlib.ticker as mticker
    ax_d.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax_d.set_ylim(0.5, 2e8 if include_poultry else 1e6)
    ax_d.set_yticks([1, 100, 10000, 1000000] + ([100000000] if include_poultry else []))
    ax_d.set_yticklabels(["1", "10²", "10⁴", "10⁶"] + (["10⁸"] if include_poultry else []),
                         fontsize=5.0)
    ax_d.set_ylabel("birds affected / month", fontsize=6, labelpad=1.5)

    # shared annotations
    ax_a.axvline(np.datetime64("2021-10"), color="#b2182b", lw=0.6, ls=(0, (3, 2)))
    ax_a.text(np.datetime64("2021-11"), ymax * 0.97, "clade 2.3.4.4b\nemergence",
              fontsize=5.0, color="#b2182b", va="top")
    for ax in (ax_a, ax_b, ax_c, ax_d):
        ax.axvspan(np.datetime64("2026-01"),
                   np.datetime64("2026-12-31"), color="#00000008", lw=0)
    ax_d.text(np.datetime64("2026-01-15"), ax_d.get_ylim()[1], "2026 partial",
              fontsize=4.6, color=MUT, va="bottom", ha="left", rotation=90)

    # panel letters + legend
    for ax, lab in ((ax_a, "a"), (ax_b, "b"), (ax_c, "c"), (ax_d, "d")):
        fig.text(0.012, ax.get_position().y1 + 0.012, lab, fontsize=8,
                 fontweight="bold")
    handles = [mpl.patches.Patch(color=palette[i], label=g)
               for i, g in enumerate(groups)]
    fig.legend(handles=handles, ncol=6 if include_poultry else 5,
               loc="upper left",
               bbox_to_anchor=(0.085, 0.995), frameon=False,
               fontsize=6.2, handlelength=1.3, handleheight=1.0,
               columnspacing=1.6, handletextpad=0.5, labelspacing=0.35)
    stem = "fig2_epi_curve_with_poultry" if include_poultry else "fig2_epi_curve"
    if include_poultry:
        fig.text(0.085, 0.018,
                 f"variant INCLUDING domestic poultry flock outbreaks (aphis_"
                 f"flocks; mostly Gallus gallus): {parsed.height:,} dated events. "
                 f"Poultry events rank 4th by count (2,250) and dominate panel d "
                 f"by birds affected (208.5M vs ~1.6M wild). Farm outbreaks are a "
                 f"systematically-reported surveillance stream — not directly "
                 f"comparable to wildlife mortality findings.",
                 fontsize=4.6, color=MUT)
    else:
        fig.text(0.085, 0.018,
                 f"merged sources, deduplicated; {parsed.height:,} dated wild-bird "
                 f"events (domestic poultry flock outbreaks — n=2,250 events, "
                 f"208.5M birds — mammals & undated records excluded; ISO-week "
                 f"reports dated to mid-week). Wild Galliformes (quail, pheasant, "
                 f"wild turkey) account for only 1.4% of events — the order's "
                 f"apparent prominence before exclusion was domestic poultry. "
                 f"Panel d: only sources reporting per-event bird counts (WHISPERS, "
                 f"WAHIS, GISAID avi-list, UK DEFRA, Ireland); most surveillance "
                 f"sources count single birds. Top 9 orders shown, remainder as "
                 f"'Other'.",
                 fontsize=4.6, color=MUT)
    save_checked(fig, stem)
    plt.close(fig)


def fig3():
    s = pl.read_parquet(DATA / "susceptibility_scores_annotated.parquet")
    panel = json.loads((FIG / "panel_data.json").read_text())
    cov = {r["name"]: r for r in panel["order"]["rows"]}

    per_order = (s.group_by("order")
                 .agg([pl.len().alias("n"),
                       pl.col("susceptibility_score").mean().alias("mean"),
                       (pl.col("susceptibility_score").std() / pl.len().sqrt())
                         .alias("sem"),
                       pl.col("mortality_rate").mean().alias("mort")])
                 .filter(pl.col("n") >= 3)
                 .sort("mean", descending=True))
    rows = []
    for r in per_order.iter_rows(named=True):
        c = cov.get(r["order"])
        if not c:
            continue
        tot = c["n_obs"] + c["n_imp"]
        rows.append(dict(order=r["order"], n=r["n"], mean=r["mean"],
                         sem=r["sem"] or 0, mort=r["mort"] or 0,
                         frac=c["n_obs"] / tot if tot else 0))
    print(f"fig3 panel a: {len(rows)} orders (scored ≥3 species, in tree)")

    W, H = 7.2, 4.75
    fig = plt.figure(figsize=(W, H))
    ax_a = fig.add_axes([0.105, 0.205, 0.42, 0.66])
    ax_b = fig.add_axes([0.655, 0.205, 0.30, 0.66])

    # ---- (a) susceptibility vs genomic coverage -----------------------------
    for ax in (ax_a, ax_b):
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=5.2, width=0.5, length=2)
    med = float(np.median([r["mean"] for r in rows]))
    ax_a.axhspan(med, 100, color="#b2182b0d", lw=0, zorder=0)
    ax_a.axvline(35, color="#b2182b55", lw=0.5, ls=(0, (3, 2)))
    ax_a.axhline(med, color="#b2182b55", lw=0.5, ls=(0, (3, 2)))

    sizes = [max(9, 60 * np.sqrt(r["n"]) / np.sqrt(72)) for r in rows]
    big = [i for i, r in enumerate(rows) if r["n"] >= 5]
    small = [i for i in range(len(rows)) if i not in big]
    ax_a.scatter([100 * rows[i]["frac"] for i in small],
                 [rows[i]["mean"] for i in small],
                 s=[sizes[i] * 0.7 for i in small], facecolor="#9aa7b455",
                 edgecolor="white", linewidth=0.5, zorder=2)
    ax_a.scatter([100 * rows[i]["frac"] for i in big],
                 [rows[i]["mean"] for i in big],
                 s=[sizes[i] for i in big], facecolor="#33475aDD",
                 edgecolor="white", linewidth=0.6, zorder=3)
    ax_a.errorbar([100 * r["frac"] for r in rows], [r["mean"] for r in rows],
                  yerr=[r["sem"] for r in rows], fmt="none",
                  ecolor="#33475a88", elinewidth=0.5, capsize=1.0, zorder=2)

    # fix data limits BEFORE label placement — the relaxation must measure
    # under the final pixel geometry or later limit changes re-crowd labels
    ax_a.set_xlim(-4, 100)
    ax_a.set_ylim(0, 100)

    # label placement: own text objects + measured relaxation loop
    # (adjustText 1.4 left duplicate artists when arrows were enabled —
    #  ghosts collided downstream; this approach keeps full control)
    labels = [(100 * rows[i]["frac"], rows[i]["mean"], rows[i]["order"])
              for i in big]
    texts = []
    CAND = [(4, 3, "left"), (4, -10, "left"), (-4, 3, "right"),
            (-4, -10, "right"), (0, 11, "center"), (0, -13, "center"),
            (9, -2, "left"), (-9, -2, "right")]
    inv = ax_a.transData.inverted()
    from matplotlib.transforms import Bbox
    for lx, ly, name in labels:
        placed_ok = False
        for dpx, dpy, ha in CAND:
            dx, dy = inv.transform((dpx, dpy)) - inv.transform((0, 0))
            t = ax_a.text(lx + dx, ly + dy, name, fontsize=5.0, ha=ha,
                          va="center", zorder=5)
            fig.canvas.draw()
            ren = fig.canvas.get_renderer()
            tb = t.get_window_extent(ren)
            obs = [o.get_window_extent(ren) for o in texts]
            pts = [Bbox.from_bounds(px - 7, py - 7, 14, 14)
                   for px, py in (ax_a.transData.transform((px, py))
                                  for px, py, _ in labels)]
            if not any(tb.overlaps(o) for o in obs + pts):
                texts.append(t)
                placed_ok = True
                break
            t.remove()
        if not placed_ok:  # last resort: straight above
            dx, dy = inv.transform((0, 11)) - inv.transform((0, 0))
            texts.append(ax_a.text(lx, ly + dy, name, fontsize=5.0,
                                   ha="center", va="center", zorder=5))

    stuck = {}
    for _iter in range(30):
        fig.canvas.draw()
        ren = fig.canvas.get_renderer()
        bb = [t.get_window_extent(ren) for t in texts]
        hits = [(i, j) for i in range(len(texts)) for j in range(i + 1, len(texts))
                if bb[i].overlaps(bb[j])]
        hit = bool(hits)
        for i, j in hits:
                key = (i, j)
                stuck[key] = stuck.get(key, 0) + 1
                lo, hi = (j, i) if bb[j].y0 < bb[i].y0 else (i, j)
                xl, yl = texts[lo].get_position()
                xh, yh = texts[hi].get_position()
                if stuck[key] >= 8:      # grid escape: teleport to free spot
                    others = [bb[k] for k in range(len(texts)) if k != lo]
                    done = False
                    for gx in range(-30, 31, 5):
                        for gy in range(-20, 21, 5):
                            texts[lo].set_position((xl + gx, yl + gy))
                            if not any(texts[lo].get_window_extent(ren)
                                       .overlaps(o) for o in others):
                                done = True
                                break
                        if done:
                            break
                    if not done:
                        texts[lo].set_position((xl, yl))
                elif stuck[key] >= 3:    # horizontal fallback
                    dx = 4 if bb[lo].x0 < bb[hi].x0 else -4
                    texts[lo].set_position((xl + dx, yl))
                else:                    # vertical push apart
                    texts[lo].set_position((xl, yl - 4))
                    texts[hi].set_position((xh, yh + 4))
        if not hit:
            break


    # measured post-pass: push apart any labels still touching (vertical
    # first, horizontal fallback for stubborn pairs). adjustText turns
    # labelled texts into Annotation objects, whose position must be set
    # via xyann — set_position is silently ignored on redraw.
    def move_label(t, x, y):
        if isinstance(t, mtext.Annotation):
            t.xyann = (x, y)
        else:
            t.set_position((x, y))

    stuck = {}
    for _ in range(16):
        fig.canvas.draw()
        ren = fig.canvas.get_renderer()
        bb = [t.get_window_extent(ren) for t in texts]
        hit = False
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if not bb[i].overlaps(bb[j]):
                    continue
                hit = True
                key = (i, j)
                stuck[key] = stuck.get(key, 0) + 1
                lo, hi = (j, i) if bb[j].y0 < bb[i].y0 else (i, j)
                xl, yl = texts[lo].get_position()
                xh, yh = texts[hi].get_position()
                if stuck[key] >= 4:  # horizontal fallback
                    dx = 4 if bb[lo].x0 < bb[hi].x0 else -4
                    move_label(texts[lo], xl + dx, yl)
                else:
                    move_label(texts[lo], xl, yl - 3)
                    move_label(texts[hi], xh, yh + 3)
        if not hit:
            break
    ax_a.set_xlabel("genome-searched species per order (%)", fontsize=6.2,
                    labelpad=1.5)
    ax_a.set_ylabel("mean susceptibility score", fontsize=6.2, labelpad=1.5)
    ax_a.text(2, 96, "high susceptibility ·\nlow genomic data", fontsize=5.0,
              color="#b2182b", va="top", ha="left", style="italic")
    # size legend (n scored species) in the empty lower-right corner
    for n_ref, (sx, sy) in zip((5, 20, 50), ((62, 14), (62, 7.5), (62, 1.5))):
        r = max(9, 60 * np.sqrt(n_ref) / np.sqrt(72))
        ax_a.scatter([sx], [sy], s=r, facecolor="none", edgecolor="#33475a",
                     linewidth=0.5, zorder=2)
        ax_a.text(sx + 3.5, sy, f"{n_ref}", fontsize=4.6, va="center",
                  color=MUT)
    ax_a.text(62, 20.5, "scored species", fontsize=4.6, color=MUT)

    # ---- (b) class composition per order ------------------------------------
    order_list = [r["order"] for r in rows]
    counts = {cls: [] for cls in CLASS_ORDER}
    for o in order_list:
        sub = s.filter(pl.col("order") == o)
        for cls in CLASS_ORDER:
            counts[cls].append(sub.filter(
                pl.col("susceptibility_class") == cls).height)
    y = np.arange(len(order_list))[::-1]
    left = np.zeros(len(order_list))
    for cls in CLASS_ORDER:
        v = np.array(counts[cls], dtype=float)
        ax_b.barh(y, v, left=left, height=0.62, color=CLASS_COLORS[cls],
                  edgecolor="white", linewidth=0.3, label=cls)
        left += v
    ax_b.set_yticks(y)
    ax_b.set_yticklabels(order_list, fontsize=5.4)
    ax_b.set_xlabel("scored species", fontsize=6.2, labelpad=1.5)
    ax_b.set_xlim(0, left.max() * 1.30)
    for yi, tot in zip(y, left):
        ax_b.text(tot + left.max() * 0.02, yi, f"{int(tot)}", fontsize=5.0,
                  va="center", color=MUT)
    ax_b.legend(fontsize=5.0, frameon=False, loc="upper center",
                bbox_to_anchor=(0.5, -0.13), ncol=3,
                handlelength=1.0, handleheight=0.8, borderpad=0.2,
                labelspacing=0.25, columnspacing=1.2)
    ax_b.tick_params(axis="y", length=0)

    fig.text(0.012, 0.965, "a", fontsize=8, fontweight="bold")
    fig.text(0.625, 0.965, "b", fontsize=8, fontweight="bold")
    fig.text(0.105, 0.015,
             f"panel a: orders with ≥3 scored species (susceptibility_scores_"
             f"annotated, n={s.height}); labels only where n≥5 (grey points "
             f"unlabelled); x = share of the order's detected species with a "
             f"genome-searched gene panel. panel b: class composition of the "
             f"same scores.", fontsize=4.6, color=MUT)
    save_checked(fig, "fig3_susceptibility_gap")
    plt.close(fig)


if __name__ == "__main__":
    fig2(include_poultry=False)
    fig2(include_poultry=True)
    fig3()
