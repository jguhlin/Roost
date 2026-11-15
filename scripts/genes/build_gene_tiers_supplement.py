#!/usr/bin/env python3
"""Build Supplemental Table 1 (Gene Tiers) for the manuscript.

One row per host panel gene: curation tier and importance class, literature
coverage (papers, species, mechanism papers) and cross-genome detection rates
from the presence parquet. Fully data-driven — rerun after any panel,
registry or presence rebuild:

    pixi run python scripts/genes/build_gene_tiers_supplement.py

Outputs:
    docs/supplemental/gene_tiers.csv   (Supplemental Table 1, CSV)
    docs/supplemental/gene_tiers.tsv   (same data, TSV)
    docs/supplemental/README.md        (column definitions + provenance)

Column semantics (see README for full definitions):
    importance critical — loss/gain directly tied to H5N1 outcome
        (CRITICAL set: DDX58/RIG-I, IFIH1/MDA5, ANP32A + config overrides)
    importance high     — strong literature evidence for HPAI outcome
        relevance (HIGH set + gene_config importance_overrides.high)
    panel tier 1/2/3    — curation tier from host_panel_v2.json
    detection_rate_pct  — % of searched genomes with any evidence
        (E3 fragment, E4 search-found, E5 annotated), alias-folded,
        best-status-wins per (gene, assembly)
    full_length_rate_pct — % of searched genomes with a full-length call
        (E4 or E5)
"""

import csv
import json
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "docs" / "supplemental"
OUT_CSV = OUT_DIR / "gene_tiers.csv"
OUT_TSV = OUT_DIR / "gene_tiers.tsv"
OUT_README = OUT_DIR / "README.md"

COLUMNS = [
    "gene_symbol", "gene_name", "functional_category", "kind",
    "panel_tier", "importance_class",
    "literature_papers", "species_studied_in_literature",
    "mechanism_papers",
    "genomes_searched", "genomes_detected",
    "detection_rate_pct", "full_length_rate_pct",
]

panel = json.loads((ROOT / "data/genes/host_panel_v2.json").read_text())["genes"]
cat = json.loads((ROOT / "web/public/data/gene_catalogue.json").read_text())["gene_catalogue"]
reg = {}
for line in (ROOT / "data/papers/gene_registry.jsonl").read_text().splitlines():
    d = json.loads(line)
    reg[d["symbol"]] = d

df = pl.read_parquet(ROOT / "data/genes/gene_presence_v2.parquet")

# Fold legacy alias symbols onto canonical panel symbols (gene_config
# aliases — the same map the presence export merges with), then resolve
# one call per (gene, assembly) with best-evidence-wins before counting.
cfg = json.loads((ROOT / "data/genes/gene_config.json").read_text())
alias2canon = {a: c for a, c in cfg.get("aliases", {}).items()
               if not str(a).startswith("_")}
panel_syms = {g["symbol"] for g in panel}
canon = {s: alias2canon.get(s, s) for s in df["gene_symbol"].unique().to_list()}
unmapped = {s for s, c in canon.items() if c not in panel_syms}
if unmapped:
    print(f"[warn] {len(unmapped)} parquet symbols resolve outside the panel "
          f"(dropped from per-gene rates): {sorted(unmapped)[:8]}")
RANK = {"E5_annotated": 4, "E4_unannotated_found": 3, "E3_fragment": 2,
        "E2_searched_not_found": 1}
df = (df.with_columns(canonical=pl.col("gene_symbol").replace(canon))
        .filter(pl.col("canonical").is_in(list(panel_syms)))
        .with_columns(rank=pl.col("status_level").replace_strict(RANK, return_dtype=pl.Int32)))
best = (df.sort("rank").group_by(["canonical", "assembly_accession"]).last()
          .with_columns(detected=pl.col("rank") >= 2, full=pl.col("rank") >= 3))
det = (best.group_by("canonical")
          .agg(searched=pl.len(), detected=pl.col("detected").sum(),
               full=pl.col("full").sum())
          .with_columns(det_rate=pl.col("detected") / pl.col("searched"),
                        full_rate=pl.col("full") / pl.col("searched")))
presence = {r["canonical"]: r for r in det.to_dicts()}
call_rows = best.height

IMP_ORDER = {"critical": 0, "high": 1, "standard": 2, None: 3}
rows = []
for g in panel:
    sym = g["symbol"]
    c = cat.get(sym, {})
    r = reg.get(sym, {})
    p = presence.get(sym, {})
    rows.append({
        "gene_symbol": sym,
        "gene_name": c.get("name") or g.get("name") or sym,
        "functional_category": g.get("category") or c.get("category") or "",
        "kind": "host" if g.get("kind", "host") == "host" else g.get("kind"),
        "panel_tier": g.get("tier"),
        "importance_class": c.get("importance") or "standard",
        "literature_papers": r.get("n_papers", 0),
        "species_studied_in_literature": r.get("n_species", 0),
        "mechanism_papers": r.get("n_mechanism_papers", 0),
        "genomes_searched": p.get("searched", 0),
        "genomes_detected": p.get("detected", 0),
        "detection_rate_pct": round(100 * p.get("det_rate", 0.0), 1),
        "full_length_rate_pct": round(100 * p.get("full_rate", 0.0), 1),
    })

rows.sort(key=lambda r: (r["panel_tier"] or 9,
                         IMP_ORDER.get(r["importance_class"], 3),
                         -(r["literature_papers"] or 0), r["gene_symbol"]))

OUT_DIR.mkdir(parents=True, exist_ok=True)
for path, delim in ((OUT_CSV, ","), (OUT_TSV, "\t")):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter=delim,
                           lineterminator="\n" if delim == "\t" else "\r\n")
        w.writeheader()
        w.writerows(rows)

n = len(rows)
crit = sum(1 for r in rows if r["importance_class"] == "critical")
high = sum(1 for r in rows if r["importance_class"] == "high")
t1 = sum(1 for r in rows if r["panel_tier"] == 1)
genomes = df["assembly_accession"].n_unique()

OUT_README.write_text(f"""# Supplemental Table 1 — Host gene tiers, literature coverage and cross-genome detection

Files: `gene_tiers.csv` / `gene_tiers.tsv` — {n} host panel genes, one row per gene.
Generated by `scripts/genes/build_gene_tiers_supplement.py`; presence basis
{genomes} genomes ({call_rows:,} merged gene–genome calls, alias-folded,
best-status-wins). Panel: {t1} tier-1 genes; importance: {crit} critical,
{high} high, remainder standard.

## Columns

| Column | Definition |
|---|---|
| gene_symbol | Canonical HGNC symbol (aliases folded) |
| gene_name | Full gene name |
| functional_category | Panel functional category (Sensor, Effector, Dependency, Signaling, …) |
| kind | host / viral |
| panel_tier | Curation tier, 1 (host dependencies) to 3 (1={t1}) |
| importance_class | critical — loss/gain directly tied to HPAI outcome (DDX58, IFIH1, ANP32A); high — strong literature evidence for outcome relevance; standard — immune-pathway member tracked for completeness |
| literature_papers | Corpus papers whose extracted study roles name this gene |
| species_studied_in_literature | Distinct host species named alongside this gene in the corpus |
| mechanism_papers | Papers contributing quote-grounded mechanism edges naming this gene |
| genomes_searched | Genomes with a presence call for this gene (aliases merged) |
| genomes_detected | Genomes with any evidence: annotated (E5), search-found (E4) or fragment (E3) |
| detection_rate_pct | genomes_detected / genomes_searched × 100 |
| full_length_rate_pct | Genomes with a full-length call (E4/E5) / genomes_searched × 100 |

Sorted by panel tier, then importance (critical first), then literature weight.
""", encoding="utf-8")

print(f"Supplemental Table 1: {n} genes ({t1} tier-1, {crit} critical, {high} high)")
print(f"presence basis: {genomes} genomes, {call_rows:,} merged gene-genome calls")
print(f"written: {OUT_CSV.name}, {OUT_TSV.name}, README.md")
