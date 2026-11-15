#!/usr/bin/env python3
"""Figure 1 — Roost overview figure (v3 composition).

Three panels:
  A · integration + scale — three data streams (typography + icons, no boxes)
      converge on a dominant filled ROOST object; scale reads as typography.
  B · one record — ANP32A as a mini biological diagram: avian vs mammalian
      protein strips with the +33-aa insertion highlighted (amber), flowing
      to mechanism → comparative genomics → evidence.
  C · the live resource — large aggressively-cropped screenshot (placeholder
      until capture) with leader-line callouts.

Data-driven by design (docs/FIGURE1_DESIGN_BRIEF.md §8): every number is read
from source artifacts at build time — nothing hardcoded. Re-run after any
pipeline stage to refresh.

Print awareness: canvas 1400 px → 183 mm → 1 px ≈ 0.37 pt. No text below
13.5 px (≈ 5 pt at final size); display numbers 8–20 pt.

  figures read:  web/public/data/by_the_numbers.json   (corpus/species/genes)
                 web/public/data/stats.json            (presence species)
                 data/genes/gene_presence_v2.parquet   (presence authority)
                 web/public/data/genes.json            (ANP32A record counts)
                 web/public/data/gene_evidence/ANP32A.json (typed evidence view)
  panel C:       figures/src/assets/fig1c/*.png + geometry.json, captured by
                 scripts/figures/capture_fig1_panel_c.mjs (dev server, 2× DPR,
                 DOM-geometry anchors — no pixel inspection anywhere)
  writes:        figures/src/fig1_overview.svg
                 figures/src/fig1_overview_caption.txt
"""
from __future__ import annotations

import base64
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "figures"))
from style import C  # noqa: E402  (house tokens)

DOMAIN = "https://josephguhlin.com/Roost"          # build-time variable
ANP32_URL = f"{DOMAIN}/#/anp32"

W, H = 1400, 1040
M = 40
AMBER = C["caution"]          # single warm accent: sequence feature + evidence
TRACK = {"lit": C["primary"], "suv": C["neutral"], "gen": C["genomics"]}
AH = 2.5                      # marker tip overshoot (userSpaceOnUse)

# ---------------------------------------------------------------- helpers
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, s, *, size=14, fill=C["ink"], weight=400, anchor="start",
        spacing=None):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="Lato" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{a}{sp}>{esc(s)}</text>')

def eyebrow(x, y, s, fill, *, size=13.5, anchor="middle", weight=700):
    """Small-caps-style tracked label (annotation tier)."""
    return txt(x, y, s.upper(), size=size, fill=fill, weight=weight,
               anchor=anchor, spacing=1.2)

def line(x1, y1, x2, y2, stroke, sw=3, marker=None, dash=None):
    mk = f' marker-end="url(#{marker})"' if marker else ""
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{sw}"{mk}{da}/>')

def curve(d, stroke, sw=3.5, marker=None):
    mk = f' marker-end="url(#{marker})"' if marker else ""
    return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}"{mk}/>'

def panel_label(x, y, letter, title):
    return txt(x, y, f"{letter} · {title.upper()}", size=18, weight=900,
               spacing=0.8)

# flat single-hue glyphs sitting directly on the background --------------
def icon_doc(x, y, hue):
    return (f'<g stroke="{hue}" stroke-width="2.8" fill="none">'
            f'<path d="M{x+11} {y+4} h16 l9 9 v29 h-25 z"/>'
            f'<path d="M{x+27} {y+4} v9 h9"/>'
            f'<path d="M{x+17} {y+22} h13 M{x+17} {y+30} h13 M{x+17} {y+38} h9"/></g>')

def icon_globe(x, y, hue):
    return (f'<g stroke="{hue}" stroke-width="2.8" fill="none">'
            f'<circle cx="{x+22}" cy="{y+22}" r="19"/>'
            f'<ellipse cx="{x+22}" cy="{y+22}" rx="9" ry="19"/>'
            f'<path d="M{x+3} {y+22} h38 M{x+8} {y+11} h28 M{x+8} {y+33} h28"/></g>')

def icon_dna(x, y, hue):
    return (f'<g stroke="{hue}" stroke-width="2.8" fill="none" stroke-linecap="round">'
            f'<path d="M{x+11} {y+3} c 16 12 -16 20 0 32 c 16 12 -16 20 0 8"/>'
            f'<path d="M{x+33} {y+3} c -16 12 16 20 0 32 c -16 12 16 20 0 8"/>'
            f'<path d="M{x+14} {y+12} h16 M{x+12} {y+23} h20 M{x+14} {y+34} h16"/></g>')

# ---------------------------------------------------------------- data
BTN = json.loads((ROOT / "web/public/data/by_the_numbers.json").read_text())
STATS = json.loads((ROOT / "web/public/data/stats.json").read_text())

import polars as pl  # noqa: E402
PRES = ROOT / "data/genes/gene_presence_v2.parquet"
pq = pl.read_parquet(PRES)
assessments = pq.height
assemblies_screened = pq.get_column("assembly_accession").n_unique()

anp = pq.filter(pl.col("gene_symbol") == "ANP32A")
anp_assessed = anp.get_column("assembly_accession").n_unique()
anp_found = (anp.filter(pl.col("status_level").is_in(["E4_unannotated_found",
                                                      "E5_annotated"]))
             .get_column("assembly_accession").n_unique())

GENES = json.loads((ROOT / "web/public/data/genes.json").read_text())["genes"]
_anp = next(g for g in GENES if g["symbol"] == "ANP32A")
anp_papers = _anp.get("paper_count") or len(_anp.get("papers", []))
anp_mentions = _anp.get("total_mentions", 0)

# Typed-evidence view — the numbers the gene-record page itself displays
# (gene_evidence/ANP32A.json: approved evidence only). Panel B prints these
# so the figure can sit next to its own screenshot without contradiction;
# genes.json's wider any-link counts (15 papers / 255 mentions) stay in the
# caption, explicitly defined.
ANP_EV = json.loads(
    (ROOT / "web/public/data/gene_evidence/ANP32A.json").read_text())
anp_ev_papers = ANP_EV.get("n_papers") or len(ANP_EV.get("papers", []))
anp_ev_mech = ANP_EV.get("n_mechanism_edges") or len(ANP_EV.get("mechanisms", []))

papers = BTN["corpus"]["papers"]
sources = BTN["corpus"]["sources"]
detections = BTN["corpus"]["detections"]
countries = BTN["corpus"]["countries"]
species_detected = BTN["species"]["detected"]
host_genes = BTN["gene_registry"]["host_total"]
assemblies_catalogued = BTN["genomics"]["assemblies_catalogued"]
# strict literature-evidence depth (registry: study-subject papers only)
_studied = BTN["landscape"]["studied"]
genes_multi = _studied - BTN["landscape"]["distribution"]["1"]
species_indexed = STATS["presence_species"]
freeze = BTN.get("generated", date.today().isoformat())[:10]

svg: list[str] = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Lato">')
svg.append(f'<rect width="{W}" height="{H}" fill="{C["surface"]}"/>')
for mid, hue in (("ah-lit", TRACK["lit"]), ("ah-suv", TRACK["suv"]),
                 ("ah-gen", TRACK["gen"]), ("ah-ink", C["ink"]),
                 ("ah-mut", C["muted"])):
    svg.append(f'<marker id="{mid}" viewBox="0 0 11 9" refX="8.5" refY="4.5" '
               f'markerWidth="11" markerHeight="9" markerUnits="userSpaceOnUse" '
               f'orient="auto-start-reverse">'
               f'<path d="M0 0 L11 4.5 L0 9 z" fill="{hue}"/></marker>')

# ============================================================ PANEL A
svg.append(panel_label(M, 58, "A", "From fragmented evidence to host-side knowledge"))

colx = [236, 700, 1164]
streams = [
    ("lit", "literature", icon_doc, f"{papers:,}",
     [f"papers · {sources} sources"], "literature evidence", "via agents + QA"),
    ("suv", "surveillance", icon_globe, f"{detections:,}",
     [f"detections · {countries} countries",
      f"{species_detected} species with detections"], "species × occurrence", None),
    ("gen", "genomes", icon_dna, f"{assemblies_catalogued:,}",
     [f"assemblies catalogued",
      f"{assemblies_screened:,} screened to date"],
     "presence + orthology", None),
]
for (key, name, icon, big, subs, verb, note), cx in zip(streams, colx):
    hue = TRACK[key]
    svg.append(eyebrow(cx, 100, name, hue, size=15, weight=800))
    svg.append(icon(cx - 22, 118, hue))
    svg.append(txt(cx, 206, big, size=36, weight=900, fill=hue, anchor="middle"))
    yy = 232
    for s in subs:
        svg.append(txt(cx, yy, s, size=15, fill=C["muted"], anchor="middle"))
        yy += 20
    if note:
        svg.append(txt(cx, yy, note, size=13.5, fill=C["faint"], anchor="middle"))
    svg.append(eyebrow(cx, 278, verb, hue, size=14, weight=700))  # shared baseline

# streams converge (curved) into the ROOST object
svg.append(curve("M236,290 C236,324 390,334 556,347.5", TRACK["lit"], 4, "ah-lit"))
svg.append(line(700, 290, 700, 347.5, TRACK["suv"], 4, "ah-suv"))
svg.append(curve("M1164,290 C1164,324 1010,334 844,347.5", TRACK["gen"], 4,
                 "ah-gen"))

# ROOST — the one filled container; the visual anchor
RX, RY, RW, RH = 480, 350, 440, 142
svg.append(f'<rect x="{RX}" y="{RY}" width="{RW}" height="{RH}" rx="20" '
           f'fill="{C["ink"]}"/>')
svg.append(txt(700, 404, "ROOST", size=44, weight=900, fill="#ffffff",
               anchor="middle", spacing=3))
svg.append(eyebrow(700, 428, "host genomics knowledgebase", "#bfdbfe"))
svg.append(line(RX + 30, 442, RX + RW - 30, 442, "#ffffff", 1, dash="2,4"))
svg.append(txt(700, 462, "SPECIES · GENES · MECHANISMS", size=13.5,
               weight=600, fill="#e2e8f0", anchor="middle", spacing=1.2))
svg.append(txt(700, 481, "EVIDENCE · OCCURRENCE · GENOMICS", size=13.5,
               weight=600, fill="#e2e8f0", anchor="middle", spacing=1.2))

# scale as typography beneath the anchor: hero + three measured columns
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.textpath import TextToPath  # noqa: E402
_ttp = TextToPath()

def text_w(s: str, size: float, weight: int = 400) -> float:
    """Exact advance width in px for Lato at `size` (build-time metrics)."""
    fp = FontProperties(family="Lato", weight=weight, size=size)
    w, _h, _d = _ttp.get_text_width_height_descent(s, fp, ismath=False)
    return w

svg.append(line(700, RY + RH, 700, 538 - AH, C["ink"], 3.5, "ah-ink"))
svg.append(txt(652, 578, f"{species_indexed:,}", size=46, weight=900,
               fill=C["primary"], anchor="end"))
svg.append(txt(666, 578, "species indexed", size=16, fill=C["muted"]))
# three equal columns, laid out from measured widths (numbers Black, labels muted)
cols_b = [(f"{host_genes:,}", "host genes tracked"),
          (f"{genes_multi:,}", "genes studied in ≥2 papers"),
          (f"{assessments / 1e6:.2f}M", "gene–genome assessments")]
GAP = 72
widths = [max(text_w(n, 16, 900), text_w(l, 14)) for n, l in cols_b]
start = 700 - (sum(widths) + GAP * (len(cols_b) - 1)) / 2
for (num, lab), cw in zip(cols_b, widths):
    cc = start + cw / 2
    svg.append(txt(cc, 606, num, size=16, weight=900, anchor="middle"))
    svg.append(txt(cc, 626, lab, size=14, fill=C["muted"], anchor="middle"))
    start += cw + GAP

# ============================================================ PANEL B
svg.append(panel_label(M, 648, "B", "One gene, connected across the resource"))
svg.append(txt(370, 690, "ANP32A", size=28, weight=900, fill=C["primary"],
               anchor="middle"))
svg.append(txt(370, 711, "acidic nuclear phosphoprotein 32A", size=14,
               fill=C["muted"], anchor="middle"))

# --- left column: the biology (protein strips with per-strip outcomes) ---
LX = 200                     # left column centre
SH = 24                      # strip height
svg.append(eyebrow(LX, 746, "birds", C["ink"], size=15, weight=800))
svg.append(f'<rect x="{LX-90}" y="758" width="180" height="{SH}" rx="12" '
           f'fill="#e2e8f0"/>')
svg.append(f'<rect x="{LX+35}" y="756" width="36" height="{SH+4}" rx="4" '
           f'fill="{AMBER}"/>')
svg.append(line(LX + 53, 784, LX + 53, 796, AMBER, 1.5))
svg.append(txt(LX + 53, 812, "+33 aa", size=14, weight=700, fill=AMBER,
               anchor="middle"))
svg.append(txt(LX, 834, "supports avian polymerase", size=14, weight=600,
               anchor="middle"))
svg.append(txt(LX, 856, "chicken · duck · turkey", size=14, fill=C["faint"],
               anchor="middle"))
svg.append(eyebrow(LX, 888, "mammals", C["ink"], size=15, weight=800))
svg.append(f'<rect x="{LX-90}" y="900" width="180" height="{SH}" rx="12" '
           f'fill="#e2e8f0"/>')
svg.append(txt(LX, 900 + SH + 24, "no insert", size=14, fill=C["muted"],
               anchor="middle"))
svg.append(txt(LX, 900 + SH + 46, "does not support avian polymerase",
               size=14, weight=600, anchor="middle"))
svg.append(txt(LX, 900 + SH + 68, "human · cattle · mouse", size=14,
               fill=C["faint"], anchor="middle"))

# strips → mechanism (arrows into the right column)
svg.append(curve(f"M{LX+90},770 C330,770 358,764 424,766", C["muted"], 2.5,
                 "ah-mut"))
svg.append(curve(f"M{LX+90},912 C330,912 358,800 424,782", C["muted"], 2.5,
                 "ah-mut"))

# --- right column: the resource tiers ---
RC = 550
svg.append(eyebrow(RC, 748, "mechanism", AMBER, size=14))
svg.append(txt(RC, 772, "influenza polymerase compatibility", size=15,
               weight=600, anchor="middle"))
svg.append(txt(RC, 792, "contributes to host range", size=14, fill=C["muted"],
               anchor="middle"))
svg.append(line(RC, 808, RC, 824 - AH, C["muted"], 2.5, "ah-mut"))
svg.append(eyebrow(RC, 846, "comparative genomics", TRACK["gen"], size=14))
svg.append(txt(RC, 874, f"{anp_found:,} / {anp_assessed:,}", size=21,
               weight=900, anchor="middle"))
svg.append(txt(RC, 894, "assemblies with full-length ANP32A", size=14,
               fill=C["muted"], anchor="middle"))
svg.append(line(RC, 912, RC, 928 - AH, C["muted"], 2.5, "ah-mut"))
svg.append(eyebrow(RC, 950, "evidence", AMBER, size=14))
svg.append(txt(RC, 974, f"{anp_ev_papers} papers with typed evidence", size=15,
               weight=600, anchor="middle"))
svg.append(txt(RC, 994, f"{anp_ev_mech} mechanism edges · {anp_mentions} mentions",
               size=14, fill=C["muted"], anchor="middle"))
# view record → C (tip lands on the record-evidence inset itself)
svg.append(txt(672, 946, "view record", size=13.5, weight=700,
               fill=C["primary"], anchor="end"))
svg.append(line(680, 952, 740 - AH, 952, C["primary"], 2.5, "ah-ink"))

# ============================================================ PANEL C
svg.append(panel_label(740, 648, "C", "The live resource"))
DX, DY, DW = 740, 664, 620
ASSET = ROOT / "figures/src/assets/fig1c"
_geo_path = ASSET / "geometry.json"

if _geo_path.exists():
    GEO = json.loads(_geo_path.read_text())
    PAD, GAP = 8, 12
    IW = DW - 2 * PAD

    def _b64(name: str) -> str:
        return base64.b64encode((ASSET / f"{name}.png").read_bytes()).decode()

    def place(name: str, ix: float, iy: float, iw: float):
        """Embed a capture at width `iw`; return its placed (w, h)."""
        cl = GEO["captures"][name]["clip"]
        ih = iw * cl["h"] / cl["w"]
        svg.append(f'<image x="{ix:.1f}" y="{iy:.1f}" width="{iw:.1f}" '
                   f'height="{ih:.1f}" '
                   f'href="data:image/png;base64,{_b64(name)}"/>')
        svg.append(f'<rect x="{ix:.1f}" y="{iy:.1f}" width="{iw:.1f}" '
                   f'height="{ih:.1f}" fill="none" stroke="#cbd5e1" '
                   f'stroke-width="1"/>')
        return iw, ih

    def anchor_svg(cap: str, key: str, iy: float, ih: float):
        """Map a capture-space anchor (css px) into SVG coordinates."""
        cl = GEO["captures"][cap]["clip"]
        a = GEO["captures"][cap]["anchors"][key]
        return (DX + PAD + a["x"] * IW / cl["w"],
                iy + a["y"] * ih / cl["h"])

    mh = place("explorer_main", DX + PAD, DY + PAD, IW)[1]
    iy2 = DY + PAD + mh + GAP
    ih2 = place("papers_inset", DX + PAD, iy2, IW)[1]
    DH = PAD + mh + GAP + ih2 + PAD
    svg.append(f'<rect x="{DX}" y="{DY}" width="{DW}" height="{DH:.1f}" rx="14" '
               f'fill="none" stroke="#cbd5e1" stroke-width="1.5"/>')

    def halo(x, y, s, *, size=13.5, weight=600, fill=C["ink"], anchor="end"):
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Lato" '
                f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
                f'text-anchor="{anchor}" stroke="{C["surface"]}" '
                f'stroke-width="3.5" paint-order="stroke" '
                f'stroke-linejoin="round">{esc(s)}</text>')

    callouts = [
        ("comparative genomics", anchor_svg("explorer_main", "comparative",
                                            DY + PAD, mh)),
        ("mechanism", anchor_svg("explorer_main", "mechanism", DY + PAD, mh)),
        ("source evidence", anchor_svg("papers_inset", "evidence", iy2, ih2)),
    ]
    # badge stack on the right rail: follow anchor order top→bottom, keep
    # ≥34 px separation, clamp inside the frame
    order = sorted(range(3), key=lambda i: callouts[i][1][1])
    ys = {}
    for i in order:
        want = min(max(callouts[i][1][1], DY + 26), DY + DH - 26)
        if order.index(i) > 0:
            prev = order[order.index(i) - 1]
            want = max(want, ys[prev] + 34)
        ys[i] = want
    for i, (lab, (ax, ay)) in enumerate(callouts, 1):
        by = ys[i - 1]
        svg.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="3.5" '
                   f'fill="{C["ink"]}"/>')
        svg.append(line(1283, by, ax + 10, ay, C["faint"], 1.5, dash="3,4"))
        svg.append(halo(1276, by + 5, lab))
        svg.append(f'<circle cx="1300" cy="{by:.1f}" r="15" '
                   f'fill="{C["ink"]}"/>')
        svg.append(txt(1300, by + 5, str(i), size=13, weight=900, fill="#ffffff",
                       anchor="middle"))
else:
    DH = 346
    svg.append(f'<rect x="{DX}" y="{DY}" width="{DW}" height="{DH}" rx="14" '
               f'fill="{C["card"]}" stroke="#cbd5e1" stroke-width="1.5" '
               f'stroke-dasharray="6,5"/>')
    mcx = DX + DW / 2 - 60
    svg.append(txt(mcx, 800, "screenshot — aggressively cropped around useful content",
                   size=14, weight=600, fill=C["muted"], anchor="middle"))
    svg.append(txt(mcx, 824, "ANP32 explorer · ANP32A tab · light theme · capture 2× DPR",
                   size=14, fill=C["faint"], anchor="middle"))
    svg.append(txt(mcx, 846, "run scripts/figures/capture_fig1_panel_c.mjs to produce",
                   size=14, fill=C["faint"], anchor="middle"))
    for i, (yy, lab) in enumerate(((720, "comparative genomics"),
                                   (830, "mechanism"),
                                   (940, "source evidence")), 1):
        svg.append(line(1283, yy, 1220, yy, C["faint"], 1.5, dash="3,4"))
        svg.append(f'<circle cx="1300" cy="{yy}" r="15" fill="{C["ink"]}"/>')
        svg.append(txt(1300, yy + 5, str(i), size=13, weight=900, fill="#ffffff",
                       anchor="middle"))
        svg.append(txt(1278, yy + 5, lab, size=13.5, weight=600, anchor="end"))

# ============================================================ stamp
src = (f"Figure 1 · data freeze {freeze} · numbers generated from the "
       f"site's data artifacts")
svg.append(txt(M, 1030, src, size=13.5, fill=C["faint"]))
svg.append(txt(W - M, 1030, DOMAIN.replace("https://", ""), size=13.5,
               fill=C["faint"], anchor="end"))
svg.append("</svg>")

out = ROOT / "figures/src/fig1_overview.svg"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(svg))
print(f"wrote {out.relative_to(ROOT)}")

# ---------------------------------------------------------------- caption
caption = f"""**Figure 1. Roost links literature-derived host-factor evidence, H5N1
surveillance, and comparative genomics across {species_indexed:,} indexed
species.** (A) Three previously disconnected data streams are integrated:
{papers:,} papers from {sources} sources are converted to structured evidence
by language-model agents (findings, typed claims, mechanisms, species links;
Methods); {detections:,} H5N1 detections across {countries} countries
({species_detected} species with recorded detections) contribute
species-by-occurrence evidence; and {assemblies_catalogued:,} catalogued genome
assemblies ({assemblies_screened:,} screened to date) contribute gene
content. Together these index {species_indexed:,} species, {host_genes:,} host
genes ({genes_multi:,} studied in two or more papers), and {assessments:,}
gene–genome assessments. (B) One record in full:
avian ANP32A carries a 33-amino-acid insertion that mammals lack, with
evidence for a role in influenza polymerase compatibility and host range;
full-length ANP32A is detected in {anp_found:,} of {anp_assessed:,} assemblies
assessed, traced to {anp_papers} source-linked papers ({anp_mentions}
extracted mentions; {anp_ev_papers} carry typed studied/perturbed evidence,
{anp_ev_mech} mechanism edges). (C) The live resource — the ANP32 explorer
at {ANP32_URL} (① comparative genomics: the insert measured per species;
② mechanism) and the ANP32A record view (③ source evidence). All numbers are
generated from the same artifacts as the live site (data freeze {freeze}).
"""
cap_out = ROOT / "figures/src/fig1_overview_caption.txt"
cap_out.write_text(caption)
print(f"wrote {cap_out.relative_to(ROOT)}")

print(f"  papers={papers} sources={sources} detections={detections} "
      f"countries={countries} host_genes={host_genes} multi={genes_multi}")
print(f"  species_indexed={species_indexed} assemblies={assemblies_catalogued} "
      f"screened={assemblies_screened} assessments={assessments} "
      f"multi={genes_multi}")
print(f"  ANP32A papers={anp_papers} mentions={anp_mentions} "
      f"typed={anp_ev_papers} mech_edges={anp_ev_mech} "
      f"found={anp_found}/{anp_assessed}")
