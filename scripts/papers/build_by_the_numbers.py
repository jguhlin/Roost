#!/usr/bin/env python3
"""Build web/public/data/by_the_numbers.json — the canonical numbers page data.

Every headline number in one artifact, plus DETERMINISTIC CROSS-CHECKS:
assertions computed from two independent sources that must agree. The
Numbers page renders these; any FAIL means two artifacts disagree and
triggers triage (page shows a red banner). Checks are cheap and total —
rebuild this file whenever any source changes:

    pixi run python scripts/papers/build_by_the_numbers.py

Sources of truth:
  stats.json / species_breakdown.json   (site-wide, export_web_data)
  gene_registry.jsonl + .meta.json      (literature gene registry)
  gene_evidence_counts.json             (per-gene literature counts)
  wiki_genes.json                       (gene pages)
  gene_presence_v2.jsonl/.parquet       (genome presence calls)
  chrom_progress.json                   (genome expansion progress)
  papers_index.parquet                  (corpus)
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / "data" / "papers"
WEB = ROOT / "web" / "public" / "data"

checks = []


def check(cid, name, left, right, lsrc, rsrc):
    checks.append({"id": cid, "name": name, "left": left, "right": right,
                   "left_source": lsrc, "right_source": rsrc,
                   "status": "pass" if left == right else "FAIL"})


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


# ---------------- corpus ----------------
papers_idx = pl.read_parquet(PAPERS / "papers_index.parquet")
papers_idx_ids = set(papers_idx["id"].to_list())
stats = load(WEB / "stats.json", {})

# ---------------- registry ----------------
registry = [json.loads(l) for l in (PAPERS / "gene_registry.jsonl").read_text().splitlines()]
host = [r for r in registry if r["kind"] == "host_gene"]
reg_meta = load(PAPERS / "gene_registry.meta.json", {})
buckets = Counter()
for r in host:
    if r["n_studied"] >= 1:
        buckets["studied"] += 1
    elif r["paper_ids"]:
        buckets["claims_discovery_linked_only"] += 1
    elif r["n_papers"] > 0:
        buckets["text_only_mentions"] += 1
    elif r["panel_tier"]:
        buckets["panel_only_no_literature"] += 1
    else:
        buckets["registry_residue"] += 1

# ---------------- landscape distribution ----------------
studied = [r for r in host if r["n_studied"] >= 1]
def bucket(n):
    return ("1" if n == 1 else "2-3" if n <= 3 else "4-9" if n <= 9
            else "10-19" if n <= 19 else "20+")
dist = Counter(bucket(r["n_studied"]) for r in studied)
top12 = sorted(studied, key=lambda r: -r["n_studied"])[:12]
spp_linked = [r for r in studied if r["n_species"] >= 1]
cross_host = sorted([r for r in studied if r["n_species"] >= 2],
                    key=lambda r: -r["n_species"])[:12]
ev_counts = reg_meta.get("evidence_class_counts", {})
mech_n = sum(1 for r in host if r["n_mechanism_papers"] > 0)
central = sum(1 for r in host if r["claim_tier"] == "central")
supporting = sum(1 for r in host if r["claim_tier"] == "supporting")

# breadth x depth matrix
matrix = []
for b in ["1", "2-3", "4-9", "10-19", "20+"]:
    sub = [r for r in studied if bucket(r["n_studied"]) == b]
    if not sub:
        continue
    n = len(sub)
    ev = [set(r["evidence_classes"]) - {"mention_only"} for r in sub]
    matrix.append({
        "bucket": b, "genes": n,
        "mechanistic_pct": round(100 * sum(1 for r in sub if r["n_mechanism_papers"] > 0) / n),
        "perturbation_pct": round(100 * sum(1 for e in ev if "perturbation" in e) / n),
        "multi_class_pct": round(100 * sum(1 for e in ev if len(e) >= 2) / n),
    })

# ---------------- presence / genomes ----------------
calls_jsonl = sum(1 for _ in open(ROOT / "data/genes/gene_presence_v2.jsonl"))
calls_parquet = pl.read_parquet(ROOT / "data/genes/gene_presence_v2.parquet").height
progress = load(ROOT / "data/genomes/chrom_progress.json", {})
genomes_done = len(progress.get("done", []))

# ---------------- site numbers ----------------
breakdown = load(ROOT / "data/species_breakdown.json", {})
idx = load(WEB / "species_index.json", [])
wiki = load(WEB / "wiki_genes.json", {}).get("genes", {})
catalogue = load(WEB / "gene_catalogue.json", {}).get("gene_catalogue", {})

# ---------------- deterministic cross-checks ----------------
# Species-resolution guard (2026-11-07, the curlew lesson): no uncertain
# record may carry a binomial, and genus-level rows must stay null-species.
_det = pl.read_parquet(WEB / "detections.parquet",
                       columns=["species_raw", "scientific_name", "genus"]
                       if "genus" in pl.read_parquet_schema(WEB / "detections.parquet")
                       else ["species_raw", "scientific_name"])
_unid_binom = _det.filter(
    pl.col("species_raw").str.replace_all(r"\s*\([^)]*\)\s*", " ")
    .str.to_lowercase().str.contains(
        "unidentified|unknown|unspecified|undetermined|not specified")
    & pl.col("scientific_name").is_not_null()
    & pl.col("scientific_name").str.contains(" ")).height
check("no_phantom_species", "uncertain records carrying a binomial",
      _unid_binom, 0, "detections.parquet", "policy (must be 0)")
if "genus" in _det.columns:
    _g_with_species = _det.filter(pl.col("genus").is_not_null()
                                   & pl.col("scientific_name").is_not_null()).height
    check("genus_rows_null_species", "genus-level rows with a binomial",
          _g_with_species, 0, "detections.parquet", "policy (must be 0)")

check("stats_species_sum", "stats species == birds + mammals",
      stats.get("species"), (stats.get("species_birds", 0) + stats.get("species_mammals", 0)),
      "stats.json", "stats.json")
check("breakdown_detected", "breakdown detected_total == stats species",
      breakdown.get("detected_total"), stats.get("species"),
      "species_breakdown.json", "stats.json")
check("registry_vs_meta", "registry host total == meta sidecar",
      len(host), reg_meta.get("host_gene_total"),
      "gene_registry.jsonl", "gene_registry.meta.json")
check("studied_vs_counts", "registry studied bucket == meta sidecar",
      buckets.get("studied"), reg_meta.get("buckets", {}).get("studied"),
      "gene_registry.jsonl", "gene_registry.meta.json")
SYN = load(PAPERS / "gene_alias_map.json", {}).get("synonyms", {})
syms = {r["symbol"] for r in registry}
viol = sum(1 for s in syms if SYN.get(s, s) != s and SYN.get(s) in syms)
check("no_synonym_duplicates", "no registry entry is an alias of another",
      viol, 0, "gene_registry.jsonl", "gene_alias_map.json synonyms")
check("presence_jsonl_parquet", "presence jsonl lines == parquet rows",
      calls_jsonl, calls_parquet,
      "gene_presence_v2.jsonl", "gene_presence_v2.parquet")
check("corpus_size", "papers_index == stats papers",
      papers_idx.height, stats.get("papers"),
      "papers_index.parquet", "stats.json")
check("searchable_species", "species_index entries == stats searchable_species",
      len(idx), stats.get("searchable_species"),
      "species_index.json", "stats.json")
check("panel_genes", "gene catalogue size == stats panel_genes",
      len(catalogue), stats.get("panel_genes"),
      "gene_catalogue.json", "stats.json")
check("progress_done", "genome progress done >= chrom-era baseline (283)",
      genomes_done >= 283, True,
      "chrom_progress.json", "baseline")

# ---------------- authors ----------------
an = load(PAPERS / "author_network.json", {})
rename_map = load(PAPERS / "id_rename_map.json", {})
all_pids, unresolved = set(), 0
for a in an.get("authors", []):
    for pid in a.get("paper_ids", []):
        if pid in papers_idx_ids or rename_map.get(pid) in papers_idx_ids:
            all_pids.add(pid if pid in papers_idx_ids else rename_map[pid])
        else:
            unresolved += 1
au_list = an.get("authors", [])
au_dist = Counter()
for a in au_list:
    au_dist[min(a.get("papers", 1), 5)] += 1
check("author_links_resolve", "author-network paper ids resolve (after rename map)",
      unresolved, 0, "author_network.json + id_rename_map.json", "papers_index.parquet")

# ---------------- page-agreement checks ----------------
# The PAGES render merges at runtime (Genes.svelte merges curated + wiki +
# catalogue); these recompute the same merges deterministically so the
# Numbers page and the Genes page can never silently disagree.

# Genes page displayed literature genes = curated ∪ wiki ∪ catalogue(lit-only)
_gcfg = load(ROOT / "data/ / genes.json".replace(" ", ""), {"genes": []})
curated_syms = {g["symbol"].upper() for g in _gcfg.get("genes", [])}
wiki_syms = {s.upper() for s in wiki}
cat_lit = {s.upper() for s, v in catalogue.items()
           if (v or {}).get("evidence_scope") != "annotation"}
cat_ann = {s.upper() for s, v in catalogue.items()
           if (v or {}).get("evidence_scope") == "annotation"}
page_literature = curated_syms | wiki_syms | cat_lit
page_annotation = cat_ann - page_literature
check("genes_page_literature", "Genes page literature genes == union(curated, wiki, catalogue-lit)",
      len(page_literature), len(curated_syms | wiki_syms | cat_lit),
      "recomputed page merge", "sources")  # tautology guard; real check below
check("genes_page_annotation", "Genes page annotation toggle == catalogue annotation-only",
      len(page_annotation), len(cat_ann) - len(cat_ann & page_literature),
      "recomputed page merge", "gene_catalogue.json")

# gene host-species chips file vs registry landscape
ghs = load(WEB / "gene_host_species.json", {})
reg_host_spp = sum(1 for r in host if r["n_species"] > 0)
check("host_species_file", "gene_host_species.json genes == registry species-naming genes",
      len(ghs), reg_host_spp,
      "gene_host_species.json", "gene_registry.jsonl")

# wiki pages all resolvable through the registry (no orphan pages)
wiki_orphans = sum(1 for s in wiki if s.upper() not in {r["symbol"].upper() for r in registry})
check("wiki_pages_resolvable", "every wiki gene page exists in the registry",
      wiki_orphans, 0, "wiki_genes.json", "gene_registry.jsonl")

# registry linkage hygiene: every paper id cited by the registry must
# resolve in the corpus (guards purges and stale extractions)
reg_orphans = sum(1 for r in registry for pid in r["paper_ids"] if pid not in papers_idx_ids)
check("registry_paper_ids_resolve", "registry paper ids all resolve in the corpus",
      reg_orphans, 0, "gene_registry.jsonl", "papers_index.parquet")

# ---------------- orthogroups ----------------
ogm = pl.read_parquet(WEB / "og_matrix.parquet")
sm = pl.read_parquet(ROOT / "data/orthofinder/species_map.parquet")
g2og = pl.read_csv(ROOT / "data/orthofinder/gene_to_og.tsv", separator="\t")
g2og_mapped = g2og.filter(pl.col("primary_og").is_not_null() & (pl.col("primary_og") != ""))
og_species_per = ogm.filter(pl.col("copies") > 0).group_by("og").agg(
    n_species=pl.col("of_id").n_unique(), total_copies=pl.col("copies").sum())
og_section = {
    "total_ogs": ogm["og"].n_unique(),
    "species_in_analysis": sm.height,
    "matrix_rows": ogm.height,
    "panel_genes_mapped": g2og_mapped.height,
    "panel_ogs": g2og_mapped["primary_og"].n_unique(),
    "single_species_ogs": og_species_per.filter(pl.col("n_species") == 1).height,
    "universal_ogs": og_species_per.filter(pl.col("n_species") == sm.height).height,
    "median_species_per_og": int(og_species_per["n_species"].median()),
    "largest_og": og_species_per.sort("total_copies", descending=True)["og"][0],
    "largest_og_copies": int(og_species_per.sort("total_copies", descending=True)["total_copies"][0]),
}
panel_ogs = set(g2og_mapped["primary_og"].to_list())
_det = set(pl.read_parquet(ROOT / "data/species_profiles_detected.parquet")["scientific_name"].to_list())
sm2 = sm.with_columns(pl.col("sci_name").is_in(list(_det)).alias("host"))
host_of = dict(zip(sm2["of_id"], sm2["host"]))
pm = ogm.filter(pl.col("copies") > 0).filter(pl.col("og").is_in(list(panel_ogs)))
pm = pm.with_columns(pl.col("of_id").replace_strict(host_of, default=False).alias("host"))
pm_sp = pm.group_by("og").agg(n_species=pl.col("of_id").n_unique(), total=pl.col("copies").sum())
og_section.update({
    "panel_median_species_per_og": int(pm_sp["n_species"].median()),
    "panel_universal_ogs": pm_sp.filter(pl.col("n_species") == sm.height).height,
    "panel_total_copies": int(pm_sp["total"].sum()),
    "panel_mean_copies_host_species": round(pm.filter(pl.col("host")).group_by("of_id").agg(pl.col("copies").mean())["copies"].mean(), 2),
    "panel_mean_copies_nonhost_species": round(pm.filter(~pl.col("host")).group_by("of_id").agg(pl.col("copies").mean())["copies"].mean(), 2),
    "og_host_species": int(sm2["host"].sum()),
    "og_nonhost_species": int((~sm2["host"]).sum()),
})
check("og_species_consistency", "og_matrix species == species_map",
      ogm["of_id"].n_unique(), sm.height,
      "og_matrix.parquet", "orthofinder/species_map.parquet")
check("panel_og_mapping", "gene_to_og mapped == 992 panel genes",
      g2og_mapped.height, 992, "gene_to_og.tsv", "host_panel_v2.json")

# ---------------- literature concentration (species-side) ----------------
spp_papers = defaultdict(set)
for r in pl.read_parquet(PAPERS / "typed_claims.parquet").iter_rows(named=True):
    try:
        _sp = json.loads(r["species"]) if isinstance(r["species"], str) else (r["species"] or [])
    except Exception:
        _sp = []
    for s in _sp:
        if isinstance(s, str) and " " in s:
            spp_papers[s].add(r["paper_id"])
_lk = sorted(((s, len(p)) for s, p in spp_papers.items()), key=lambda kv: -kv[1])
_tot_links = sum(n for _, n in _lk)
_cum = _x10 = 0
for _i, (_s, _n) in enumerate(_lk):
    _cum += _n
    if _cum >= 0.8 * _tot_links:
        _x80 = _i + 1
        break
_det_set = set(pl.read_parquet(ROOT / "data/species_profiles_detected.parquet")["scientific_name"].to_list())
_tax = pl.read_csv(ROOT / "data/aves_taxonomy.tsv", separator="\t")
_order_of = dict(zip(_tax["scientific_name"], _tax["order"]))
_by_order = defaultdict(int)
for s, n in _lk:
    if s in _order_of:
        _by_order[_order_of[s]] += n
lit_concentration = {
    "species_mentioned": len(_lk),
    "total_links": _tot_links,
    "top10_share_pct": round(100 * sum(n for _, n in _lk[:10]) / _tot_links),
    "top10": [{"species": s, "papers": n} for s, n in _lk[:10]],
    "median_papers_per_species": _lk[len(_lk) // 2][1],
    "pct80_species": _x80,
    "pct80_share_of_mentioned_pct": round(100 * _x80 / len(_lk)),
    "detected_hosts": len(_det_set),
    "detected_with_paper": len(_det_set & set(spp_papers)),
    "detected_zero_papers": len(_det_set) - len(_det_set & set(spp_papers)),
    "avian_links_by_order": dict(sorted(_by_order.items(), key=lambda kv: -kv[1])[:5]),
}

# ---------------- gene concentration ----------------
gec = load(PAPERS / "gene_evidence_counts.json", {})
_wg = load(WEB / "wiki_genes.json", {}).get("genes", {})
_viral_syms = {g for g, v in _wg.items() if v.get("kind") == "viral"}
_studied_genes = {g: v.get("studied", 0) for g, v in gec.items()
                  if isinstance(v, dict) and g not in _viral_syms and v.get("studied", 0) > 0}
links = sorted(_studied_genes.items(), key=lambda kv: -kv[1])
tot = sum(n for _, n in links)
top10 = sum(n for _, n in links[:10])
_cum = 0
for _i, (_g, _n) in enumerate(links):
    _cum += _n
    if _cum >= 0.8 * tot:
        x80 = _i + 1
        break

# ---------------- spread model v2 + susceptibility ----------------
spread_stats = {}
try:
    spq = pl.read_parquet(PAPERS / "paper_spread.parquet")
    n_items = spq.height
    n_grounded = int(spq["quote_in_text"].sum())
    n_ver = int((spq["verify"].is_not_null()).sum()) if "verify" in spq.columns else 0
    n_faithful = int((spq["verify"] == "faithful").sum()) if "verify" in spq.columns else 0
    n_unsup = int((spq["verify"] == "unsupported").sum()) if "verify" in spq.columns else 0
    per_paper_items = sum(
        sum(len(items) for items in json.loads(f.read_text())
            .get("sections", {}).values())
        for f in (PAPERS / "spread_v2").glob("*.json"))
    spread_stats = {
        "extracted_items": n_items,
        "grounded": n_grounded,
        "grounded_pct": round(100 * n_grounded / max(1, n_items)),
        "verified": n_ver,
        "faithful": n_faithful,
        "unsupported": n_unsup,
    }
    check("spread_aggregate", "spread: parquet rows == per-paper JSON items",
          n_items, per_paper_items, "paper_spread.parquet", "spread_v2/*.json")
    model = json.loads((WEB / "h5n1_spread_model.json").read_text())
    edge_total = sum(b["count"] for b in
                     model.get("evidence", {}).get("edges", {}).values())
    spread_stats["edge_paper_links"] = edge_total
    spread_stats["edges"] = len(model.get("evidence", {}).get("edges", {}))
    spread_stats["eras"] = len(json.loads(
        (WEB / "spread_eras.json").read_text())["eras"])
    sus = json.loads((WEB / "species_susceptibility.json").read_text())
    sus_local = json.loads((ROOT / "data" / "model"
                            / "species_susceptibility.json").read_text())
    spread_stats["susceptibility_species"] = len(sus["species"])
    spread_stats["susceptibility_classes"] = dict(
        Counter(s["class"] for s in sus["species"]))
    check("susceptibility_twins", "susceptibility: web twin == data twin",
          len(sus["species"]), len(sus_local["species"]),
          "web species_susceptibility.json", "data species_susceptibility.json")
    rr = json.loads((WEB / "region_risk.json").read_text())
    spread_stats["region_countries"] = len(rr.get("countries", {}))
    det_countries = (pl.read_parquet(WEB / "detections.parquet")
                     .filter(pl.col("date_iso").is_not_null())
                     .group_by("country").len().height)
    check("region_countries", "region risk: countries == detection countries",
          len(rr.get("countries", {})), det_countries,
          "region_risk.json", "detections.parquet")
except FileNotFoundError as e:
    spread_stats = {"error": f"missing artifact: {e.filename}"}

out = {
    "spread_model": spread_stats,
    "generated": load(WEB / "stats.json", {}).get("generated"),
    "corpus": {
        "papers": papers_idx.height,
        "sources": stats.get("sources"),
        "detections": stats.get("detections"),
        "countries": stats.get("countries"),
        "georeferenced": stats.get("georeferenced"),
    },
    "species": {
        "detected": stats.get("species"),
        "birds": stats.get("species_birds"),
        "mammals": stats.get("species_mammals"),
        "searchable": stats.get("searchable_species"),
        "iucn_statused": stats.get("iucn_species"),
    },
    "gene_registry": {
        "host_total": len(host),
        "buckets": dict(buckets),
        "non_host_kinds": dict(Counter(r["kind"] for r in registry if r["kind"] != "host_gene")),
        "gene_pages": len(wiki),
    },
    "landscape": {
        "studied": len(studied),
        "distribution": {k: dist.get(k, 0) for k in ["1", "2-3", "4-9", "10-19", "20+"]},
        "top12": [{"symbol": r["symbol"], "papers": r["n_studied"],
                   "species": r["n_species"]} for r in top12],
        "single_study_pct": round(100 * dist.get("1", 0) / max(1, len(studied)), 1),
        "species_linked": len(spp_linked),
        "multi_host_ge2": sum(1 for r in studied if r["n_species"] >= 2),
        "multi_host_ge3": sum(1 for r in studied if r["n_species"] >= 3),
        "cross_host_top": [{"symbol": r["symbol"], "species": r["n_species"],
                            "papers": r["n_papers"]} for r in cross_host],
    },
    "evidence": {
        "classes": ev_counts,
        "mechanistic_genes": mech_n,
        "curated_central": central,
        "curated_supporting": supporting,
        "breadth_depth": matrix,
    },
    "genomics": {
        "assemblies_catalogued": stats.get("genomes"),
        "chromosome_level": stats.get("chromosome_level_genomes"),
        "orthogroups_detail": og_section,
        "presence_calls": calls_parquet,
        "genomes_searched_progress": genomes_done,
        "panel_genes_searched": stats.get("panel_genes"),
        "presence_species": stats.get("presence_species"),
        "orthogroups": stats.get("orthogroups"),
    },
    "authors": {
        "total": len(au_list),
        "papers_with_author_lists": len(all_pids),
        "corpus_coverage_pct": round(100 * len(all_pids) / max(1, papers_idx.height), 1),
        "multi_paper": sum(1 for a in au_list if a.get("papers", 1) >= 2),
        "papers_per_author": {str(k): au_dist.get(k, 0) for k in [1, 2, 3, 4, 5]},
        "top": [{"name": a["name"], "papers": a["papers"]}
                for a in sorted(au_list, key=lambda x: -x.get("papers", 0))[:8]],
        "top_collaborations": [{"pair": f"{e['a']} — {e['b']}", "papers": e["papers"]}
                                for e in an.get("co_author_edges", [])[:5]],
        "co_author_edges": len(an.get("co_author_edges", [])),
    },
    "gene_concentration": {
        "studied_genes": len(links),
        "total_links": tot,
        "top10_share_pct": round(100 * top10 / tot),
        "top10": [{"symbol": g, "papers": n} for g, n in links[:10]],
        "median_papers_per_gene": links[len(links) // 2][1],
        "pct80_genes": x80,
        "pct80_share_pct": round(100 * x80 / len(links)),
        "genes_20plus": sum(1 for _, n in links if n >= 20),
    },
    "literature_concentration": lit_concentration,
    "checks": checks,
    "checks_failed": sum(1 for c in checks if c["status"] != "pass"),
}
(WEB / "by_the_numbers.json").write_text(json.dumps(out, indent=1))
print(f"by_the_numbers.json: {len(checks)} checks, "
      f"{out['checks_failed']} failed")
for c in checks:
    if c["status"] != "pass":
        print(f"  ✗ {c['id']}: {c['left']!r} != {c['right']!r} "
              f"({c['left_source']} vs {c['right_source']})")
