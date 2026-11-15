#!/usr/bin/env python3
"""
Species vaccine-response capacity (D69) — deterministic, genome-tier.

For every species in the presence matrix (207+), score the immune MODULES a
vaccine depends on, from gene presence calls (FULL=1, FRAGMENT=0.5, NOT_FOUND=0):

  mhc2_helper   — subunit/inactivated response: MHC-II processing + CD4 help
                  + receptor diversity / affinity maturation
  mhc1_cd8      — MHC-I peptide display + CD8 T-cell arm
  cpg_adjuvant  — CpG-adjuvant responsiveness (avian TLR21 is the TLR9 repl.)
  rna_laiv      — RNA-adjuvant / replicating-platform innate priming
                  (Galliformes legitimately score lower: DDX58/RIG-I lost)

This is a GENOME-TIER prediction (module completeness), not a literature
calibration: it says which machinery the species has, not what titers it will
make. Literature calibration (measured responses per species/platform) merges
in when the vaccine mining pass runs — the tier field upgrades then.

Output: web/public/data/vaccine_readiness.json

Usage: pixi run python scripts/genes/build_vaccine_readiness.py
"""

import json
from datetime import date
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent.parent
PQ = ROOT / "web" / "public" / "data" / "gene_presence.parquet"
OUT = ROOT / "web" / "public" / "data" / "vaccine_readiness.json"
IMMUNOMEDB = ROOT / "data" / "genes" / "immunomedb" / "immunomedb_presence.jsonl"

MODULES = [
    {
        "id": "mhc2_helper",
        "label": "MHC-II helper arm",
        "why": "Response to subunit / inactivated vaccines: class-II antigen "
               "processing, CD4 help, V(D)J diversity, affinity maturation.",
        "genes": ["BLB2", "BLB1", "CD74", "DMB2", "CIITA", "RAG1", "AICDA"],
    },
    {
        "id": "mhc1_cd8",
        "label": "MHC-I / CD8 arm",
        "why": "Class-I peptide display and cross-presentation — the T-cell "
               "arm vectored and conserved-antigen (NP) designs rely on.",
        "genes": ["BF2", "B2M", "TAP1", "TAP2", "TAPBP"],
    },
    {
        "id": "cpg_adjuvant",
        "label": "CpG-adjuvant responsiveness",
        "why": "TLR21 is the bird CpG-DNA sensor (mammalian TLR9 was lost in "
               "the avian lineage) — the target for CpG-adjuvanted and mRNA "
               "platforms.",
        "genes": ["TLR21", "MYD88"],
    },
    {
        "id": "rna_laiv",
        "label": "RNA-adjuvant / LAIV priming",
        "why": "Innate sensing a replicating or RNA-mimic-adjuvanted vaccine "
               "rides on. Galliformes score lower on biological fact: RIG-I "
               "(DDX58) is lost in chickens and relatives — ducks differ.",
        "genes": ["TLR3", "TLR7", "DDX58", "IFIH1", "MAVS", "IFNB", "IRF7"],
    },
]

WEIGHT = {"FULL": 1.0, "FRAGMENT": 0.5, "NOT_FOUND": 0.0}
# Species whose vaccine data anchors interpretation (evidence species).
ANCHORS = {
    "Gallus gallus": "primary evidence species — nearly all poultry vaccine trials",
    "Anas platyrhynchos": "second evidence species — duck vaccine/trial literature",
    "Meleagris gallopavo": "turkey — commercial vaccine target species",
    "Strigops habroptila": "kākāpō — NZ taonga species, no vaccine data (the planner target)",
}


def band(score: float) -> str:
    if score >= 0.85:
        return "strong"
    if score >= 0.7:
        return "capable"
    if score >= 0.5:
        return "reduced"
    return "concern"


def immunomedb_backbone():
    """ImmunomeDB join: per-species intact fraction of the 520-gene immune
    backbone (ANNOTATED / panel; PSEUDOGENIZED excluded from numerator).
    Returns ({species: score}, {species: order}, panel_size). All-B10K birds;
    2020 vintage — scores reflect B10K1-era annotation quality."""
    if not IMMUNOMEDB.exists():
        return {}, {}, 0
    counts, orders, genes = {}, {}, set()
    for line in IMMUNOMEDB.read_text().splitlines():
        r = json.loads(line)
        sp = r["latin_name"]
        c = counts.setdefault(sp, {"ANNOTATED": 0, "PSEUDOGENIZED": 0})
        c[r["status"]] = c.get(r["status"], 0) + 1
        orders[sp] = r.get("order")
        genes.add(r["gene_symbol"])
    panel = len(genes) or 1
    scores = {sp: round(c["ANNOTATED"] / panel, 3) for sp, c in counts.items()}
    return scores, orders, panel


def main() -> None:
    df = pl.read_parquet(PQ)
    # aves flag from the genomes catalog (mammals: B-locus symbols don't
    # resolve — their module scores are uninterpretable, not biology)
    is_aves = {}
    gpq = ROOT / "web" / "public" / "data" / "genomes.parquet"
    if gpq.exists():
        try:
            g = pl.read_parquet(gpq)
            cols = g.columns
            if "organism_name" in cols and "is_aves" in cols:
                for r in g.select("organism_name", "is_aves").to_dicts():
                    is_aves[r["organism_name"]] = bool(r["is_aves"])
        except Exception:
            pass
    needed = {g for m in MODULES for g in m["genes"]}
    sub = df.filter(pl.col("gene").is_in(sorted(needed)))
    # fail loudly if any module gene has no presence rows at all — otherwise
    # it scores 0 silently and deflates every species (D74 bug class)
    parquet_genes = set(sub["gene"].unique().to_list())
    ghost = sorted(needed - parquet_genes)
    if ghost:
        raise SystemExit(f"[readiness] module genes with no presence rows: {ghost} "
                         "— fix MODULES symbols to match the matrix")
    have = sub.group_by("species").agg(pl.col("gene").unique().alias("found"))
    have_map = {r["species"]: set(r["found"]) for r in have.to_dicts()}

    status_map = {}  # (species, gene) -> status
    for r in sub.select("species", "gene", "status").to_dicts():
        status_map[(r["species"], r["gene"])] = r["status"]

    species = {}
    all_sp = sorted({r["species"] for r in df.select("species").to_dicts()})
    for sp in all_sp:
        found = have_map.get(sp, set())
        if not found:
            continue  # no calls for module genes — not scored
        modules, missing, frags = {}, [], []
        for m in MODULES:
            vals = []
            for g in m["genes"]:
                st = status_map.get((sp, g))
                if st == "NOT_FOUND":
                    vals.append(0.0)
                    missing.append(g)
                elif st == "FRAGMENT":
                    vals.append(WEIGHT["FRAGMENT"])
                    frags.append(g)
                else:
                    vals.append(WEIGHT.get(st, 0.0))
            modules[m["id"]] = round(sum(vals) / len(vals), 3)
        overall = round(sum(modules.values()) / len(modules), 3)
        aves = is_aves.get(sp)
        rec = {
            "overall": overall,
            "band": band(overall) if aves is not False else "n/a",
            "modules": modules,
            "missing": sorted(set(missing)),
            "fragments": sorted(set(frags)),
            "anchor": ANCHORS.get(sp),
            "is_aves": aves,
        }
        if aves is False:
            rec["caveat"] = ("mammal: B-locus symbols (BF/BLB/TAP…) don't "
                             "resolve in mammalian genomes — module scores "
                             "uninterpretable for this species")
        species[sp] = rec

    ranked = dict(sorted(species.items(), key=lambda kv: -kv[1]["overall"]))

    # --- ImmunomeDB join (D73) ---
    im_scores, im_orders, im_panel = immunomedb_backbone()
    n_overlap = n_backbone = 0
    for sp, score in im_scores.items():
        if sp in ranked:
            ranked[sp]["backbone_immunomedb"] = score   # cross-validation column
            n_overlap += 1
        else:
            ranked[sp] = {                      # backbone-only species record
                "overall": None, "band": "n/a", "modules": None,
                "missing": [], "fragments": [], "is_aves": True,
                "backbone_immunomedb": score,
                "order": im_orders.get(sp),
                "source": "immunomedb-2020",
                "caveat": ("immune-backbone only (ImmunomeDB 2020/B10K1 "
                           "vintage) — MHC modules not scorable from this "
                           "source; run the BLAST module panel to score"),
            }
            n_backbone += 1
    # scored species first (by overall), backbone-only after (by backbone)
    ranked = dict(
        sorted((kv for kv in ranked.items() if kv[1]["overall"] is not None),
               key=lambda kv: -kv[1]["overall"])
        + sorted((kv for kv in ranked.items() if kv[1]["overall"] is None),
                 key=lambda kv: -(kv[1].get("backbone_immunomedb") or 0)))
    n_aves = sum(1 for v in ranked.values() if v["is_aves"] is not False)
    dist = {}
    for v in ranked.values():
        if v["is_aves"] is False:
            continue
        dist[v["band"]] = dist.get(v["band"], 0) + 1

    n = len(ranked)
    OUT.write_text(json.dumps({
        "_doc": ("Genome-tier vaccine-response capacity: immune-module "
                 "completeness from the presence matrix. Predicts which "
                 "machinery a species HAS for responding to each vaccine "
                 "class — not measured titers. Absences can reflect genome "
                 "quality as well as true loss (check each gene's evidence "
                 "ladder). Literature calibration merges when vaccine "
                 "mining runs (tier → calibrated)."),
        "generated": str(date.today()),
        "tier": "genome-presence",
        "weighting": "FULL=1, FRAGMENT=0.5, NOT_FOUND=0; module = mean; overall = mean of modules",
        "bands": {"strong": "≥0.85", "capable": "0.70–0.85",
                  "reduced": "0.50–0.70", "concern": "<0.50",
                  "n/a": "mammal — B-locus nomenclature caveat"},
        "modules": MODULES,
        "immunomedb": {"vintage": "2020-B10K1", "panel_genes": im_panel,
                      "species": len(im_scores), "overlap_scored": n_overlap,
                      "backbone_only": n_backbone,
                      "metric": "ANNOTATED / panel (pseudogenized excluded)"},
        "species": ranked,
    }, indent=1, ensure_ascii=False))

    print(f"readiness: {n} species scored ({n_aves} avian) | avian bands: {dist}")
    print(f"immunomedb join: {n_overlap} cross-validated + "
          f"{n_backbone} backbone-only species (panel {im_panel} genes)")
    for sp in list(ANCHORS):
        v = ranked.get(sp)
        if v:
            print(f"  {sp:22} overall {v['overall']:.2f} ({v['band']}) "
                  f"missing={v['missing'] or '—'}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
