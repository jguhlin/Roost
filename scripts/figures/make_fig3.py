#!/usr/bin/env python3
"""Figure 3 — Where the knowledge gaps are (the blind-spot figure).

Four panels:
  A · every indexed species, one cell each — taxonomically ordered grid
      colored by study attention vs genome availability.
  B · attention vs diversity — species per order against studied species
      per order (top 10 orders).
  C · genome × study 2×2 — the headline: genome-rich, knowledge-poor.
  D · tractable now — threatened species with chromosome-level genomes and
      zero host-genetics studies.

The claim is about research opportunity, never susceptibility.

  figures read:  web/public/data/species_index.json     (universe + taxonomy
                  + genome availability — the site's own index page data)
                 web/public/data/gene_host_species.json (hosts named in
                  typed claims → the "studied" definition)
                 web/public/data/species/iucn_status.json
                 web/public/data/species.parquet        (class → mammal orders)
  writes:        figures/src/fig3_gaps.svg
                 figures/src/fig3_gaps_caption.txt
"""
from __future__ import annotations

import json
import math
import sys
import collections
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
from style import C  # noqa: E402

W, H = 1400, 1040
M = 40
AMBER = C["caution"]
TRACK = {"lit": C["primary"], "gen": C["genomics"]}

# ---------------------------------------------------------------- helpers
def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))

def txt(x, y, s, *, size=14, fill=C["ink"], weight=400, anchor="start",
        spacing=None):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="Lato" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{a}{sp}>{esc(s)}</text>')

def eyebrow(x, y, s, fill, *, size=13.5, anchor="middle", weight=700):
    return txt(x, y, s.upper(), size=size, fill=fill, weight=weight,
               anchor=anchor, spacing=1.2)

def line(x1, y1, x2, y2, stroke, sw=3, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{sw}"{da}/>')

def rect(x, y, w, h, *, fill, stroke=None, sw=1, rx=0, opacity=1):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" rx="{rx}"{st} fill="{fill}" '
            f'opacity="{opacity}"/>')

def panel_label(x, y, letter, title):
    return txt(x, y, f"{letter} · {title.upper()}", size=18, weight=900,
               spacing=0.8)

# ================================================================ DATA
si = json.loads((ROOT / "web/public/data/species_index.json").read_text())
ghs = json.loads((ROOT / "web/public/data/gene_host_species.json").read_text())
iucn = json.loads(
    (ROOT / "web/public/data/species/iucn_status.json").read_text()
).get("status", {})

import polars as pl  # noqa: E402
spq = pl.read_parquet(ROOT / "web/public/data/species.parquet")
MAMMAL_ORDERS = set(spq.filter(pl.col("class") == "Mammalia")["order"]
                    .unique().to_list())

def canon(name: str) -> str:
    parts = str(name).strip().split()
    return " ".join(parts[:2]).lower()

index = {canon(s["sci"]): s for s in si}
n_universe = len(index)

studied_genes = collections.Counter()
for gene, v in ghs.items():
    for sp in v.get("species", []):
        studied_genes[canon(sp)] += 1
studied = {c for c in studied_genes if c in index}
genome = {c for c, s in index.items() if s.get("genome_acc")}

c_gs = len(genome & studied)           # genome + studied
c_gn = len(genome - studied)           # genome, not studied  ← the gap
c_ns = len(studied - genome)           # studied, no indexed genome
c_nn = n_universe - len(genome | studied)
assert c_gs + c_gn + c_ns + c_nn == n_universe
pct_gap = 100 * c_gn / len(genome)

def is_mammal(s) -> bool:
    return s.get("ord") in MAMMAL_ORDERS

orders_all = collections.Counter()
orders_stu = collections.Counter()
for c, s in index.items():
    orders_all[s.get("ord") or "—"] += 1
    if c in studied:
        orders_stu[s.get("ord") or "—"] += 1
birds_by_size = [o for o, n in orders_all.most_common()
                 if o not in MAMMAL_ORDERS]

# threatened genome-gap species, priority-sorted (for panel D)
IUCN_PRIO = {"CR": 0, "EN": 1, "VU": 2, "NT": 3}
gap_threat = []
for c in genome - studied:
    s = index[c]
    st = iucn.get(s["sci"])
    if st in IUCN_PRIO:
        gap_threat.append((IUCN_PRIO[st], s.get("ord") or "—",
                           s.get("com") or s["sci"], s["sci"], st,
                           s.get("genome_level")))
gap_threat.sort()
chromosome_examples = [g for g in gap_threat if g[5] == "Chromosome"][:6]
gap_lc = sum(1 for c in genome - studied if iucn.get(index[c]["sci"]) == "LC")
no_gen_studied = sorted(index[c]["sci"] for c in studied - genome)

BTN = json.loads((ROOT / "web/public/data/by_the_numbers.json").read_text())
freeze = BTN.get("generated", date.today().isoformat())[:10]

svg: list[str] = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Lato">')
svg.append(f'<rect width="{W}" height="{H}" fill="{C["surface"]}"/>')

# study-depth tiers among studied species (caption; chart uses its own)
tier_n = {"ge20": 0, "5-19": 0, "1-4": 0}
for c in studied:
    n = studied_genes.get(c, 0)
    tier_n["ge20" if n >= 20 else "5-19" if n >= 5 else "1-4"] += 1
BIG = 17   # order-size threshold for "larger bird orders" (panel B note)
# ================================================================ PANEL A
# the species grid: every indexed species one cell; blocks in species-
# count order (as B, Carnivora broken out); within each block, studied
# tiers lead, then genome-unstudied (amber), then no genome (red X).
svg.append(panel_label(M, 58, "A", "Study status for HPAI-detected species"))
svg.append(txt(M, 86, f"{n_universe} H5N1-indexed species in taxonomic "
               f"order — study attention vs genome availability:",
               size=14, fill=C["muted"]))

GX, GY, COLS, CELL, STEP, BGAP = 178, 108, 39, 11.5, 13, 5
AMBER3 = C["caution"]
RED3 = C["alert"]

def cell_style(c):
    """Blue = studied (gene-link depth tiers); amber = genome in hand,
    unstudied; no fill (red X drawn) = no genome."""
    n = studied_genes.get(c, 0)
    if n >= 20:
        return C["primary"], 1.0
    if n >= 5:
        return C["primary"], 0.65
    if n >= 1:
        return C["primary"], 0.4
    if c in genome:
        return AMBER3, 0.9
    return None, None          # no genome → red X

def cell_sort_key(c):
    """Within a block: studied first (darker blue leads), then genome-
    unstudied, then no genome — the leading blue run reads as the order's
    studied count at a glance."""
    n = studied_genes.get(c, 0)
    if n >= 1:
        return (0, -n, c)
    if c in genome:
        return (1, 0, c)
    return (2, 0, c)

def block(label, members):
    """Render one taxonomic block on its own row(s); return rows used."""
    global GY
    members = sorted(members, key=cell_sort_key)
    rows = max(1, math.ceil(len(members) / COLS))
    if label:
        svg.append(txt(172, GY + 9, label, size=13, weight=600,
                       fill=C["muted"], anchor="end"))
    for i, c in enumerate(members):
        r, col = divmod(i, COLS)
        x0, y0 = GX + col * STEP, GY + r * STEP
        fill, op = cell_style(c)
        if fill is None:                     # no genome → red X
            m = 2.2
            svg.append(line(x0 + m, y0 + m, x0 + CELL - m, y0 + CELL - m,
                            RED3, 1.6))
            svg.append(line(x0 + CELL - m, y0 + m, x0 + m, y0 + CELL - m,
                            RED3, 1.6))
        else:
            svg.append(rect(x0, y0, CELL, CELL, fill=fill, opacity=op))
    GY += rows * STEP + BGAP
    return rows

# block order = species-count order, identical to panel B's rows. Carnivora
# is broken out of the mammals tail at its size position so A matches B.
big_orders = [o for o in birds_by_size if orders_all[o] >= BIG]
carnivora = [c for c, s in index.items() if s.get("ord") == "Carnivora"]
pos = next((i for i, o in enumerate(big_orders)
            if orders_all[o] < orders_all["Carnivora"]), len(big_orders))
big_orders.insert(pos, "Carnivora")
small_birds = [c for c, s in index.items()
               if not is_mammal(s) and (s.get("ord") not in big_orders)]
mammals = [c for c, s in index.items()
           if is_mammal(s) and s.get("ord") != "Carnivora"]
for o in big_orders:
    members = [c for c, s in index.items() if s.get("ord") == o]
    block(o.lower(), sorted(members))
n_small_orders = len({index[c].get("ord") for c in small_birds})
block(f"+{n_small_orders} more bird orders", small_birds)
block("other mammals", mammals)

# legend — two rows: study-depth tiers, then genome/no-genome
LY = GY + 4
legend1 = [(C["primary"], 1.0, f"≥20 genes ({tier_n['ge20']})"),
           (C["primary"], 0.65, f"5–19 ({tier_n['5-19']})"),
           (C["primary"], 0.4, f"1–4 ({tier_n['1-4']})"),
           (C["ink"], None, "studied (gene links)")]
lx = GX
for fill, op, lab in legend1:
    if op is None:
        svg.append(txt(lx, LY, lab, size=13.5, fill=C["muted"]))
        lx += len(lab) * 7.2 + 22
        continue
    svg.append(rect(lx, LY - 9, 12, 12, fill=fill, opacity=op))
    svg.append(txt(lx + 18, LY, lab, size=13.5, fill=C["muted"]))
    lx += 18 + len(lab) * 7.2 + 22
LY2 = LY + 22
legend2 = [(AMBER3, f"genome, unstudied ({c_gn})", False),
           (RED3, f"no genome ({c_nn})", True)]
lx = GX
for fill, lab, is_x in legend2:
    if is_x:
        m = 2.2
        svg.append(line(lx, LY2 - 9, lx + 12, LY2 + 3, RED3, 1.8))
        svg.append(line(lx + 12, LY2 - 9, lx, LY2 + 3, RED3, 1.8))
    else:
        svg.append(rect(lx, LY2 - 9, 12, 12, fill=fill, opacity=0.9))
    svg.append(txt(lx + 18, LY2, lab, size=13.5, fill=C["muted"]))
    lx += 18 + len(lab) * 7.2 + 22

# ================================================================ PANEL B
BX = 730
svg.append(panel_label(BX, 58, "B",
                       "Species per order vs. host genetics studies"))
svg.append(txt(BX, 86, "species per order (teal) vs species with any "
               "host-genetics study (blue):", size=14, fill=C["muted"]))
top10 = orders_all.most_common(10)
by = 122
BARX, BARMX = 950, 1330
maxsp = max(n for _o, n in top10)
for o, n in top10:
    ns = orders_stu.get(o, 0)
    svg.append(txt(BX, by + 10, o, size=13.5, weight=600))
    if o in MAMMAL_ORDERS:
        svg.append(txt(BX, by + 27, "mammals", size=12, fill=C["faint"]))
    w1 = (BARMX - BARX) * n / maxsp
    svg.append(rect(BARX, by, w1, 8, fill=C["genomics"], opacity=0.85))
    svg.append(txt(BARX + w1 + 8, by + 8, f"{n}", size=13.5, weight=700,
                   fill=C["genomics"]))
    w2 = max((BARMX - BARX) * ns / maxsp, 2 if ns else 0)
    if ns:
        svg.append(rect(BARX, by + 13, w2, 8, fill=C["primary"]))
        svg.append(txt(BARX + w2 + 8, by + 21, f"{ns} studied", size=13.5,
                       weight=700, fill=C["primary"]))
    else:
        svg.append(txt(BARX, by + 21, "0 studied", size=13.5, weight=700,
                       fill=C["alert"]))
    by += 38
zero_big = [o for o in birds_by_size
            if orders_all[o] >= BIG and orders_stu.get(o, 0) == 0]
zero_big_n = sum(orders_all[o] for o in zero_big)
svg.append(line(BX, by + 2, 1360, by + 2, C["faint"], 1, dash="2,4"))
svg.append(txt(BX, by + 24, " · ".join(o.lower() for o in zero_big),
               size=13.5, fill=C["muted"]))
svg.append(txt(BX, by + 42, f"— {zero_big_n} species, zero studies",
               size=13.5, fill=C["muted"]))

# ================================================================ PANEL C
# the geographic face of the no-genome gap: grid-map render produced by
# scripts/figures/fig3d_grid.py (panel mode) from detection coordinates
GRID_ASSET = ROOT / "figures/src/assets/fig3/panel_d_grid.png"
assert GRID_ASSET.exists(), "run fig3d_grid.py first (panel asset missing)"
svg.append(panel_label(M, 578, "C",
                       "Detections of no-genome species, by location"))
svg.append(txt(M, 606, "distinct species per 2.5° cell; geolocated "
               "detections", size=14, fill=C["muted"]))
import base64 as _b64  # noqa: E402
_grid_b64 = _b64.b64encode(GRID_ASSET.read_bytes()).decode()
svg.append(f'<image x="{M}" y="616" width="1320" height="402" '
           f'href="data:image/png;base64,{_grid_b64}"/>')

# ================================================================ stamp
svg.append(txt(M, 1030, f"Figure 3 · freeze {freeze} · numbers from "
               f"species_index · gene_host_species · iucn_status · "
               f"species.parquet", size=13.5, fill=C["faint"]))
svg.append("</svg>")

out = ROOT / "figures/src/fig3_gaps.svg"
out.write_text("\n".join(svg))
print(f"wrote {out.relative_to(ROOT)}")

# ---------------------------------------------------------------- caption
ex_list = ", ".join(f"*{sci}*" for _p, _o, _c, sci, _s, _l
                    in chromosome_examples[:6])
caption = f"""**Figure 3. Host-genetic knowledge lags far behind available
genomic resources — and the gaps are immediately tractable.**
(A) All {n_universe} species in the Roost species index (H5N1-detected and
tracked hosts), orders as in (B); within each order, studied species lead
(blue, dark to light by gene-link depth), then genome-available unstudied
(amber), then no genome (red cross): {len(studied)} species have ever been named
as a host in typed study-subject claims; {c_gn} — {pct_gap:.1f}% of the
{len(genome)} genome-available species — carry a genome but have never
been a study subject; {c_nn} have no genome ({c_ns} studied species lack
one: {" · ".join(no_gen_studied)}). {len(gap_threat)} threatened species
(IUCN CR/EN/VU/NT) sit in the genome-available unstudied cell, including
{ex_list}, each with a chromosome-level assembly; {gap_lc} of the {c_gn}
are least-concern. This is an index of research opportunity, not a
susceptibility score.
(B) Species per order (teal) against host-genetics study attention (blue)
— {len(zero_big)} of the larger bird orders have zero studied species
({', '.join(o for o in zero_big)}; {zero_big_n} species combined), and
even within the studied set depth is shallow: {tier_n['1-4']} of
{len(studied)} studied species are named by ≤4 genes, while only
{tier_n['ge20']} species carry ≥20 gene links.
(C) Geographic distribution of the no-genome gap: every H5N1 detection of
a no-genome species with coordinates (1,239 records) binned into 2.5°
cells, coloured by distinct species per cell (Pacific-centred). The gap
concentrates along coasts and wetland flyways: hottest cells are the US
Great Plains (34 species), South Africa's Western Cape (21), Patagonia
(18) and south-eastern Brazil (12); 62 countries carry at least one
such species. All numbers are generated from the same artifacts as the
live site (data freeze {freeze}).
"""
cap_out = ROOT / "figures/src/fig3_gaps_caption.txt"
cap_out.write_text(caption)
print(f"wrote {cap_out.relative_to(ROOT)}")

print(f"  universe={n_universe} studied={len(studied)} genome={len(genome)}")
print(f"  cells: gs={c_gs} gn={c_gn} ns={c_ns} nn={c_nn} "
      f"gap%={pct_gap:.1f}")
print(f"  threatened in genome-unstudied gap={len(gap_threat)} "
      f"(LC {gap_lc}); "
      f"examples={[e[3] for e in chromosome_examples]}")
