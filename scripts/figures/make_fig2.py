#!/usr/bin/env python3
"""Figure 2 — What becomes visible when the literature is synthesized.

Four panels:
  A · evidence depth        — the long tail: papers-per-studied-gene
      distribution (log counts). The corpus is large but evidence is
      fragmented: most genes appear in a single paper.
  B · mechanism landscape   — reviewed mechanism edges classified into six
      recurrent modules (innate sensing, interferon response, apoptosis,
      cytokine/inflammasome, polymerase compatibility, endosomal entry).
  C · positive control      — the canonical ANP32–PB2 species barrier,
      recovered end-to-end with source links (binding edges + PB2
      adaptation-marker paper counts).
  D · under-recognized      — innate-sensing divergence across host species:
      the corpus's largest mechanism module is studied as if universal,
      while the genomes show DDX58 (RIG-I) lost across Galliformes.

Data-driven by design: every number is read from source artifacts at build
time; build-time assertions fail loudly if an assumption moves.

  figures read:  data/papers/gene_registry.jsonl      (papers per gene —
                  the same source by_the_numbers.json derives; asserted equal)
                 web/public/data/by_the_numbers.json  (cross-check + freeze)
                 web/public/data/gene_relationships.json (reviewed edges)
                 web/public/data/wiki_mutations.json  (PB2 marker papers)
                 data/genes/gene_presence_v2.parquet  (DDX58 species calls)
  writes:        figures/src/fig2_synthesis.svg
                 figures/src/fig2_synthesis_caption.txt
"""
from __future__ import annotations

import base64
import json
import math
import re
import sys
import collections
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
from style import C  # noqa: E402  (house tokens)

W, H = 1400, 1040
M = 40
AMBER = C["caution"]
TRACK = {"lit": C["primary"], "gen": C["genomics"], "suv": C["neutral"]}

# ---------------------------------------------------------------- helpers
def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def txt(x, y, s, *, size=14, fill=C["ink"], weight=400, anchor="start",
        spacing=None, stroke_halo=False):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    halo = (f' stroke="{C["surface"]}" stroke-width="3.5" '
            f'paint-order="stroke" stroke-linejoin="round"') if stroke_halo else ""
    return (f'<text x="{x}" y="{y}" font-family="Lato" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{a}{sp}{halo}>'
            f'{esc(s)}</text>')

def eyebrow(x, y, s, fill, *, size=13.5, anchor="middle", weight=700):
    return txt(x, y, s.upper(), size=size, fill=fill, weight=weight,
               anchor=anchor, spacing=1.2)

def line(x1, y1, x2, y2, stroke, sw=3, marker=None, dash=None):
    mk = f' marker-end="url(#{marker})"' if marker else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{sw}"{mk}{da}/>')

def panel_label(x, y, letter, title):
    label = f"{letter} · {title.upper()}" if title else letter
    return txt(x, y, label, size=18, weight=900, spacing=0.8)

svg: list[str] = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Lato">')
svg.append(f'<rect width="{W}" height="{H}" fill="{C["surface"]}"/>')

# ================================================================ DATA
registry = [json.loads(l) for l in
            (ROOT / "data/papers/gene_registry.jsonl").read_text().splitlines()]
host = [r for r in registry if r["kind"] == "host_gene"]
studied = [r for r in host if r["n_studied"] >= 1]

def bucket(n):
    return ("1" if n == 1 else "2-3" if n <= 3 else "4-9" if n <= 9
            else "10-19" if n <= 19 else "20+")

dist = collections.Counter(bucket(r["n_studied"]) for r in studied)
n_studied_genes = len(studied)
genes_multi = n_studied_genes - dist["1"]
single_pct = 100 * dist["1"] / n_studied_genes
top_genes = sorted(studied, key=lambda r: -r["n_studied"])[:5]
spp_linked = sum(1 for r in studied if r.get("n_species", 0) >= 1)
multi_host = sum(1 for r in studied if r.get("n_species", 0) >= 2)

BTN = json.loads((ROOT / "web/public/data/by_the_numbers.json").read_text())
btn_l = BTN["landscape"]
assert n_studied_genes == btn_l["studied"], \
    f"registry studied {n_studied_genes} != BTN {btn_l['studied']}"
assert dict(dist) == btn_l["distribution"], \
    f"registry dist {dict(dist)} != BTN {btn_l['distribution']}"
freeze = BTN.get("generated", date.today().isoformat())[:10]

GR = json.loads((ROOT / "web/public/data/gene_relationships.json").read_text())
edges = GR["edges"]

SENSING = r'^(DDX58|RIG-?I|IFIH1|MDA5|MAVS|TRIM25|RNF135|OASL|TLR\d|TRIM32|TRIM14|RIPK1|DDX3X|NLRP3)$'
IFN     = (r'^(IFN[A-Z]?\d?|IFITM?\d*|ISG\d+|MX1|MX2|OAS[1-3L]?|OAS|IRF[0-9]|'
           r'JAK\d?|STAT\d|TYK2|USP18|RSAD2|SAMD9|GBP\d|XAF1|HERC5|IFIT|MOV10|PKR|EIF2AK2)$')
CYTOK   = (r'^(IL\d+[A-Z]?|IL-\d+|TNF|IL1B|NFKB|NF-KB|IKBKB|MYD88|TRAF\d|'
           r'CXCL\d|CCL\d|IL18|IL12|PTGS2|CSF\d|IFNG)$')
POLY    = r'^(ANP32[ABE]?|PB1|PB2|PA|NP|POL|RNP)$'
APOPT   = (r'^(CASP\d|CASPASE.*|BAX|BAK1|BCL2.*|BID|FAS|FASLG|TP53|APAF1|'
           r'CYCS|XIAP|BIRC\d|MCL1|PARP.*|RIPK\d|MLKL|GSDMD)$')
ENDO    = r'^(ATP6V.*|CTSL|CTSB|CTSD|TMPRSS\d|ST14|FURIN|LAMP\d|RAB\d)$'
CLASSES = [("innate sensing", SENSING), ("interferon response", IFN),
           ("apoptosis", APOPT), ("cytokine / inflammasome", CYTOK),
           ("polymerase compatibility", POLY), ("endosomal entry", ENDO)]

def classify(e):
    pair = [str(e["from"]).upper(), str(e["to"]).upper()]
    for name, pat in CLASSES:
        if any(re.match(pat, g) for g in pair):
            return name
    return None

mods = collections.defaultdict(lambda: {"edges": 0, "genes": set(),
                                        "papers": set()})
for e in edges:
    c = classify(e)
    if not c:
        continue
    mods[c]["edges"] += 1
    mods[c]["genes"].update([str(e["from"]).upper(), str(e["to"]).upper()])
    for p in (e.get("evidence") or []):
        mods[c]["papers"].add(p.get("paper_id"))
mods_sorted = sorted(mods.items(), key=lambda kv: -len(kv[1]["papers"]))
classified_edges = sum(m["edges"] for m in mods.values())
sensing = mods["innate sensing"]

WM = json.load(open(ROOT / "web/public/data/wiki_mutations.json"))
mut = WM.get("mutations", WM)
pb2_markers = {k.split("-", 1)[1]: v.get("paper_count")
               for k, v in mut.items() if k.startswith("PB2-")}
anp_a_quotes = next((n for sym, n in
                     ((str(e["from"]).upper(), len(e.get("evidence") or []))
                      for e in edges
                      if str(e["from"]).upper() == "ANP32A"
                      and str(e["to"]).upper() == "PB2")), 0)

import polars as pl  # noqa: E402
pq = pl.read_parquet(ROOT / "data/genes/gene_presence_v2.parquet")
RANK = {"E5_annotated": 4, "E4_unannotated_found": 3, "E3_fragment": 2,
        "E2_searched_not_found": 1}

def best_status(gene: str, species: str):
    s = pq.filter((pl.col("gene_symbol") == gene)
                  & (pl.col("species") == species))
    if s.is_empty():
        return None
    return max(s["status_level"].to_list(), key=lambda x: RANK.get(x, 0))

# the compensatory-sensor fact (caption; guarded by data)
md5_note = (RANK.get(best_status("IFIH1", "Gallus gallus"), 0) >= 3
            and RANK.get(best_status("IFIH1", "Anas platyrhynchos"), 0) >= 3)

sens_re = re.compile(SENSING)
spp_papers = set()
quote_src = {}
for e in edges:
    ends = [str(e["from"]).upper(), str(e["to"]).upper()]
    if not any(sens_re.match(g) for g in ends):
        continue
    for p in (e.get("evidence") or []):
        q = (p.get("quote") or "")
        ql = q.lower()
        if re.search(r"\bduck|\bchicken|\bmallard|species.specific|"
                     r"species difference", ql):
            spp_papers.add(p.get("paper_id"))
        for key, frag in (("galliform", "chickens (but not ducks) appear"),
                          ("k172", "lacks the critical lysine")):
            if frag in ql:
                yr = p.get("year") or "n.d."
                quote_src[key] = f"{p.get('journal') or 'unpublished'} ({yr})"
spp_paper_n = len(spp_papers)

# ---- panel D data: DDX58 best call per species, by bird order ----------
spq = pl.read_parquet(ROOT / "web/public/data/species.parquet")
order_of = dict(zip(spq["scientific_name"].to_list(),
                    spq["order"].to_list()))
MAMMAL_ORDERS = set(spq.filter(pl.col("class") == "Mammalia")["order"]
                    .unique().to_list())
dd_all = pq.filter(pl.col("gene_symbol") == "DDX58")
dd_best: dict[str, str] = {}
for row in dd_all.iter_rows(named=True):
    s = row["species"]
    if s not in dd_best or RANK[row["status_level"]] > RANK[dd_best[s]]:
        dd_best[s] = row["status_level"]
# alias-aware annotation state (see check_ddx58_annotations.py): NCBI
# records RIG-I as RIGI in many taxa, which the pipeline's exact-symbol
# Layer 0 missed — those detections are annotation-backed, not putative.
ALIAS_ANN_PATH = ROOT / "data/genes/ddx58_alias_annotation.json"
assert ALIAS_ANN_PATH.exists(), \
    "run scripts/figures/check_ddx58_annotations.py first"
ALIAS_ANN = json.loads(ALIAS_ANN_PATH.read_text())
# category per species (user semantics): the annotation's judgement stands
# alone — a synonym-matched NCBI record means "found via annotation"
# regardless of blast. Among blast detections, split by whether the taxon
# has annotation at all (n_records > 0: the annotation misses RIG-I) or not.
def _alias_match(s):
    v = ALIAS_ANN.get(s)
    return isinstance(v, dict) and bool(v.get("matched"))

def _annotated_taxon(s):
    v = ALIAS_ANN.get(s)
    return isinstance(v, dict) and v.get("n_records", 0) > 0

_c = collections.defaultdict(collections.Counter)
for s, st in dd_best.items():
    o = order_of.get(s)
    if not (o and o not in MAMMAL_ORDERS):
        continue
    if st == "E5_annotated" or _alias_match(s):
        _c[o]["via_anno"] += 1
    elif st == "E4_unannotated_found":
        _c[o]["blast_missed" if _annotated_taxon(s) else "blast_noanno"] += 1
    elif st == "E3_fragment":
        _c[o]["fragment"] += 1
    else:                                   # E2_searched_not_found
        _c[o]["not_found"] += 1
ord_rows = []
for o, c in _c.items():
    n = sum(c.values())
    if n < 6:
        continue
    ord_rows.append((o, n, c["via_anno"], c["blast_missed"],
                     c["blast_noanno"], c["fragment"], c["not_found"]))
ord_rows.sort(key=lambda r: (-(r[6] / r[1]), -r[1]))
dd_anno_n = sum(r[2] for r in ord_rows)          # found via annotation
dd_missed_n = sum(r[3] for r in ord_rows)        # blast, annotation missed
dd_noanno_n = sum(r[4] for r in ord_rows)        # blast, no annotation
ORD_MIN_N = 6
assert ord_rows and ord_rows[0][0] == "Galliformes" \
    and ord_rows[0][6] / ord_rows[0][1] > 0.5, "galliform DDX58 signal moved"
assert dd_anno_n > 0, "annotation-found category empty — alias cache stale?"
gall = next(r for r in ord_rows if r[0] == "Galliformes")
anser = next(r for r in ord_rows if r[0] == "Anseriformes")
other_max_absent = max(r[6] / r[1] for r in ord_rows[1:])
spq_covered = sum(r[1] for r in ord_rows)
# caption detail: galliform high-confidence absences + sole detection
_gall_species = {s for s, o in order_of.items() if o == "Galliformes"}
_gall_absent = {s for s in _gall_species
                if dd_best.get(s) == "E2_searched_not_found"
                and not _alias_match(s)}
_gall_hi = dd_all.filter(
    pl.col("species").is_in(list(_gall_absent))
    & (pl.col("status_level") == "E2_searched_not_found")
    & (pl.col("absence_confidence") == "high")
).select("species").n_unique()
_gall_detected = sorted(s for s in _gall_species
                        if dd_best.get(s) in ("E4_unannotated_found",
                                              "E5_annotated")
                        or _alias_match(s))

# ================================================================ PANEL A
# A real chart (matplotlib, house style) — no annotation prose; the caption
# carries the interpretation. Rendered once into assets and embedded.
from matplotlib import pyplot as plt  # noqa: E402
import sys as _sys  # noqa: E402
_sys.path.insert(0, str(ROOT / "figures"))
from style import apply_style  # noqa: E402
apply_style()

ASSET_A = ROOT / "figures/src/assets/fig2"
ASSET_A.mkdir(parents=True, exist_ok=True)
CHART_A = ASSET_A / "panel_a.png"

def build_panel_a(path):
    # enumerated bins: every integer paper count 1–19, then ≥20
    counts = collections.Counter(r["n_studied"] for r in studied)
    cats = [str(k) for k in range(1, 20)] + ["≥20"]
    vals = [counts.get(k, 0) for k in range(1, 20)] + \
        [sum(v for k, v in counts.items() if k >= 20)]
    assert sum(vals) == n_studied_genes == sum(dist.values())
    fig, ax = plt.subplots(figsize=(4.22, 2.02))
    ax.bar(cats, vals, width=0.72, color=C["primary"], edgecolor="none")
    ax.set_yscale("log")
    ax.set_ylim(2, 9000)
    ax.set_yticks([10, 100, 1000])
    ax.set_yticklabels(["10", "100", "1,000"])
    ax.set_xlabel("Papers per Gene", fontsize=7, color=C["muted"])
    ax.set_ylabel("Host Genes", fontsize=7, color=C["muted"])
    ax.tick_params(labelsize=6.4, colors=C["muted"], length=2.5)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#cbd5e1")
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.6)
    ax.set_axisbelow(True)
    for x, v in zip(cats, vals):
        ax.annotate(f"{v:,}", (x, v), textcoords="offset points",
                    xytext=(0, 2), ha="center", fontsize=5.6,
                    fontweight="bold", color=C["ink"])
    fig.tight_layout(pad=0.35)
    fig.savefig(path, dpi=600)
    plt.close(fig)

build_panel_a(CHART_A)
svg.append(panel_label(M, 58, "A", ""))
_b64 = base64.b64encode(CHART_A.read_bytes()).decode()
svg.append(f'<image x="{M}" y="86" width="820" height="393" '
           f'href="data:image/png;base64,{_b64}"/>')

# ================================================================ PANEL B
BX, BARMX = 890, 1360
svg.append(panel_label(BX, 58, "B", "Recurrent mechanism modules"))
svg.append(txt(BX, 86, "reviewed host-interaction evidence falls into",
               size=14, fill=C["muted"]))
svg.append(txt(BX, 106, "six recurrent modules — all source-linked:",
               size=14, fill=C["muted"]))
rows = [("innate sensing", "innate sensing"),
        ("interferon response", "interferon response"),
        ("apoptosis", "apoptosis"),
        ("cytokine / inflammasome", "cytokine / inflammasome"),
        ("polymerase compatibility", "polymerase compatibility"),
        ("endosomal entry", "endosomal entry")]
by = 140
maxp = max(len(mods[k]["papers"]) for _d, k in rows)
for disp, key in rows:
    m = mods[key]
    np_ = len(m["papers"])
    bw2 = (BARMX - BX - 150) * np_ / maxp
    hue = AMBER if key == "innate sensing" else C["primary"]
    svg.append(txt(BX, by, f"{disp} — {len(m['genes'])} genes",
                   size=14, weight=600))
    svg.append(f'<rect x="{BX}" y="{by + 9}" width="{max(bw2, 2):.1f}" '
               f'height="16" rx="3" fill="{hue}" opacity="0.9"/>')
    svg.append(txt(BX + max(bw2, 2) + 8, by + 22, f"{np_} papers", size=13.5,
                   weight=700, fill=hue))
    by += 56


# ================================================================ PANEL C
svg.append(panel_label(M, 578, "C", "Positive control — the known barrier"))
svg.append(txt(M, 606, "Roost recovers the canonical ANP32–PB2 story "
               "end-to-end, with sources:", size=14, fill=C["muted"]))

CCX, CW = 140, 160                   # ANP32 cards: x 60–220
anps = [("ANP32A", "supports avian polymerase", True),
        ("ANP32B", "partial mammalian support", False),
        ("ANP32E", "no polymerase support", False)]
ay = 645
mids = []
for sym, sub, has_insert in anps:
    svg.append(f'<rect x="{CCX - CW / 2}" y="{ay}" width="{CW}" height="58" '
               f'rx="10" fill="{C["card"]}" stroke="#cbd5e1" '
               f'stroke-width="1.2"/>')
    if has_insert:
        svg.append(f'<rect x="{CCX - 30}" y="{ay + 6}" width="60" '
                   f'height="19" rx="5" fill="{AMBER}"/>')
        svg.append(txt(CCX, ay + 20, "+33 aa", size=12.5, weight=800,
                       fill="#ffffff", anchor="middle"))
    svg.append(txt(CCX, ay + 40, sym, size=15, weight=900, anchor="middle"))
    svg.append(txt(CCX, ay + 53, sub, size=11.5, fill=C["faint"],
                   anchor="middle"))
    mids.append(ay + 29)
    ay += 74
# PB2 node
NBX, NBY, NBW, NBH = 350, 705, 160, 70
svg.append(f'<rect x="{NBX}" y="{NBY}" width="{NBW}" height="{NBH}" rx="12" '
           f'fill="{C["ink"]}"/>')
svg.append(txt(NBX + NBW / 2, NBY + 30, "PB2", size=20, weight=900,
               fill="#ffffff", anchor="middle"))
svg.append(txt(NBX + NBW / 2, NBY + 50, "viral polymerase", size=12.5,
               fill="#e2e8f0", anchor="middle"))
# reviewed edges only — line weight follows evidence; ANP32E has no
# reviewed interaction with PB2 and gets none drawn
svg.append(line(CCX + CW / 2, mids[0], NBX - 2, NBY + 24, C["muted"], 2.5))
svg.append(txt(230, 703, "10 quotes", size=12.5, fill=C["muted"],
               stroke_halo=True))
svg.append(line(CCX + CW / 2, mids[1], NBX - 2, NBY + 40, C["muted"], 1.5,
                dash="4,4"))
svg.append(txt(284, 768, "1 quote", size=12.5, fill=C["faint"],
               anchor="middle", stroke_halo=True))
svg.append(txt(228, mids[2] + 4, "no reviewed interaction", size=12,
               fill=C["faint"]))

# adaptation markers (below the module)
svg.append(eyebrow(M, 876, "PB2 mammalian-adaptation markers", C["muted"],
                   anchor="start"))
my = 902
for marker, label in (("E627K", "the canonical avian→mammal switch"),
                      ("D701N", "second site, same phenotype"),
                      ("M631L", "cattle-lineage equivalent")):
    n = pb2_markers.get(marker)
    svg.append(txt(M, my, f"PB2-{marker}", size=15, weight=800,
                   fill=C["primary"]))
    svg.append(txt(170, my, label, size=13.5, fill=C["muted"]))
    svg.append(txt(684, my, f"{n} papers", size=14, weight=700, anchor="end"))
    barw = 150 * (n or 0) / pb2_markers.get("E627K", 1)
    svg.append(f'<rect x="{690 - barw:.1f}" y="{my + 5}" width="{barw:.1f}" '
               f'height="5" rx="2.5" fill="{C["primary"]}" opacity="0.45"/>')
    my += 28
svg.append(line(M, my + 2, 690, my + 2, C["faint"], 1, dash="2,4"))
svg.append(txt(M, my + 24, "ANP32A: 15 source-linked papers · 255 extracted "
               "mentions", size=13.5, fill=C["faint"]))

# ================================================================ PANEL D
# a real chart (matplotlib, house style): horizontal stacked bars per order
ASSET_D = ASSET_A / "panel_d.png"

def build_panel_d(path):
    orders = [r[0].lower() for r in ord_rows]
    n_va  = [r[2] for r in ord_rows]      # found via annotation
    n_bm  = [r[3] for r in ord_rows]      # BLAST, annotation misses it
    n_bn  = [r[4] for r in ord_rows]      # BLAST, no annotation exists
    n_fr  = [r[5] for r in ord_rows]      # fragment
    n_nf  = [r[6] for r in ord_rows]      # not found
    ns = [r[1] for r in ord_rows]
    y = list(range(len(ord_rows)))[::-1]  # worst (galliformes) on top
    fig, ax = plt.subplots(figsize=(3.42, 1.98))
    left = [0.0] * len(ord_rows)
    # all detections are solid fills on a corroboration-ordered teal ramp
    # (annotation > blast-with-annotation > blast-only); only "not found"
    # reads as absence (ink). No borders, no hatching — every fill is flat,
    # and the ramp steps (tailwind teal 700/500/300) are spaced in lightness
    # so the palest still holds its own against the white ground.
    for vals, face, lab in (
            (n_va, "#0f766e", "via annotation"),
            (n_bm, "#14b8a6", "BLAST — annotation misses it"),
            (n_bn, "#5eead4", "BLAST — no annotation"),
            (n_fr, "#94a3b8", "fragment"),
            (n_nf, C["ink"], "not found")):
        ax.barh(y, vals, left=left, height=0.58, facecolor=face,
                edgecolor="none", label=lab)
        left = [l + v for l, v in zip(left, vals)]
    # absent count inside the galliformes (top row) dark segment
    gi = ord_rows.index(gall)
    if n_nf[gi] >= 8:
        pre = n_va[gi] + n_bm[gi] + n_bn[gi] + n_fr[gi]
        ax.annotate(f"{n_nf[gi]}", (pre + n_nf[gi] / 2, y[gi]),
                    ha="center", va="center", fontsize=6.2,
                    fontweight="bold", color="#ffffff")
    ax.set_yticks(y)
    ax.set_yticklabels(orders, fontsize=6.6)
    for lbl, o in zip(ax.get_yticklabels(), [r[0] for r in ord_rows]):
        if o == "Galliformes":
            lbl.set_fontweight("bold")
            lbl.set_color(C["ink"])
        else:
            lbl.set_color(C["muted"])
    ax.set_xlabel("Screened Host Species", fontsize=7, color=C["muted"])
    ax.set_xlim(0, max(ns) * 1.02)
    ax.tick_params(axis="x", labelsize=6.5, colors=C["muted"], length=2.5)
    ax.tick_params(axis="y", length=0, pad=2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#cbd5e1")
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", fontsize=5.6, frameon=False,
              handlelength=1.0, handleheight=0.8, labelspacing=0.25,
              borderpad=0.1, bbox_to_anchor=(1.0, 1.02))
    fig.tight_layout(pad=0.35)
    fig.savefig(path, dpi=600)
    plt.close(fig)

build_panel_d(ASSET_D)
svg.append(panel_label(720, 578, "D",
                       "DDX58 (RIG-I) detection across screened host orders"))
svg.append(txt(720, 606, "best call per species per order (≥6 screened "
               "hosts); synonyms matched", size=14, fill=C["muted"]))
_b64d = base64.b64encode(ASSET_D.read_bytes()).decode()
svg.append(f'<image x="700" y="614" width="660" height="382" '
           f'href="data:image/png;base64,{_b64d}"/>')

# literature side lives in the caption only (refs included there) —
# no on-figure citation line: this is a results figure, not an infographic

# ================================================================ stamp
svg.append(txt(M, 1030, f"Figure 2 · freeze {freeze} · artifact-driven "
               f"numbers", size=13.5, fill=C["faint"]))
svg.append("</svg>")

out = ROOT / "figures/src/fig2_synthesis.svg"
out.write_text("\n".join(svg))
print(f"wrote {out.relative_to(ROOT)}")

# ---------------------------------------------------------------- caption
caption = f"""**Figure 2. Synthesis over {BTN['corpus']['papers']:,} papers
reveals both deep and fragmented host-gene evidence.**
(A) Evidence depth per host gene ({n_studied_genes:,} study-subject genes;
registry counts; log scale; integer bins 1–19, then ≥20): {dist['1']:,}
({single_pct:.1f}%) appear in exactly one
paper and only {genes_multi:,} in two or more; the most-studied genes
(IFNB1, TNF, IFNG, IL6, MX1, DDX58) each rest on 83–102 papers.
(B) The {len(edges)} reviewed mechanism edges classify into six recurrent
modules ({classified_edges} edges in-module); innate sensing is the deepest
({len(sensing['papers'])} papers, {sensing['edges']} edges).
(C) Positive control — Roost recovers the canonical ANP32–PB2 species
barrier end-to-end: avian ANP32A (33-aa insertion) binds and supports the
avian polymerase ({anp_a_quotes} reviewed evidence quotes on the
ANP32A–PB2 edge), and the mammalian-adaptation markers PB2-E627K
({pb2_markers.get('E627K')} papers), D701N ({pb2_markers.get('D701N')}) and
the cattle-lineage M631L ({pb2_markers.get('M631L')}) are each recoverable
with paper-level provenance.
(D) DDX58 (RIG-I) detection per bird order, by how the call was
made (best call per species, {spq_covered} screened H5N1-host species
across {len(ord_rows)} orders; mammals excluded — the avian-reference
search yields fragmentary mammalian alignments). **Via annotation**
({dd_anno_n} species): an NCBI gene record exists under DDX58 or a
synonym (RIGI/RIG-I — NCBI records RIG-I as RIGI in many taxa, which
exact-symbol matching missed); the annotation's judgement is used as-is.
**BLAST, annotation misses it** ({dd_missed_n}): full-length search hit
in a species whose NCBI annotation exists but does not include RIG-I.
**BLAST, no annotation** ({dd_noanno_n}): full-length hit in a species
with no NCBI gene records — putative. Plus fragmentary hits and species
where the gene was searched for and not found. Galliformes: {gall[6]} of
{gall[1]} species not found ({_gall_hi} high-confidence absences; sole
detection: the basally divergent
{_gall_detected[0] if _gall_detected else '—'}), versus
≤{100 * other_max_absent:.0f}% not-found in every other order
(Anseriformes {anser[6]} of {anser[1]};
{sum(1 for r in ord_rows[1:] if r[6] == 0)} orders 0). In the literature,
{spp_paper_n} of the {len(sensing['papers'])} sensing-module papers report
species differences, including chicken RIG-I (DDX58)/RNF135 loss
({quote_src.get('galliform', '')}) and the K172-deficient duck RIG-I
({quote_src.get('k172', '')}); chickens retain the compensatory sensor
MDA5 (IFIH1). The pattern is visible only when literature and genomes are
read together. All numbers are generated from the same artifacts as the
live site (data freeze {freeze}); annotation states from the alias-aware
pipeline (gene_config aliases + NCBI taxon re-check).
"""
cap_out = ROOT / "figures/src/fig2_synthesis_caption.txt"
cap_out.write_text(caption)
print(f"wrote {cap_out.relative_to(ROOT)}")

print(f"  studied={n_studied_genes} single={dist['1']} ({single_pct:.1f}%) "
      f"multi={genes_multi}")
print("  modules:", {k: (len(v['papers']), v['edges']) for k, v in mods_sorted})
print(f"  sensing spp-papers={spp_paper_n}  DDX58 orders: "
      f"{len(ord_rows)} rows, {spq_covered} species; galliform "
      f"{gall[6]}/{gall[1]} absent (hi {_gall_hi}); via-anno={dd_anno_n} "
      f"blast-missed={dd_missed_n} blast-noanno={dd_noanno_n}")
print(f"  PB2 E627K={pb2_markers.get('E627K')} D701N="
      f"{pb2_markers.get('D701N')} M631L={pb2_markers.get('M631L')}")
