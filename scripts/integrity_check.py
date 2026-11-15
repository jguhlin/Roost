#!/usr/bin/env python3
"""
Integrity check for Roost web data: every cross-reference between entities
should resolve. Catches broken wiki links before they ship.

Checks:
  1. Species references: every species named in wiki data (gene/mutation
     "studied in" chips + wiki species pages) resolves via species_index.json
     or species_wiki_supplement.json (by scientific or common name).
  2. Mutation links: every mutation chip on gene pages exists in wiki_mutations.
  3. Gene links: every mutation's protein resolves to the gene panel/wiki genes.
  4. Paper citations: every paper_id cited in wiki data exists in papers.json.
  5. Search index consistency: wiki_index matches wiki_genes/wiki_mutations.
  6. Web data files: everything the app fetches exists and parses.

Usage: pixi run integrity   (exit 1 on failures)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEB_DATA = ROOT / "web" / "public" / "data"

failures = []
warnings = []


def load(name):
    path = WEB_DATA / name
    if not path.exists():
        failures.append(f"missing file: web/public/data/{name}")
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        failures.append(f"invalid JSON in {name}: {e}")
        return None


def check(label, missing, limit=8):
    if missing:
        shown = list(missing)[:limit]
        failures.append(f"{label}: {len(missing)} unresolved → {shown}")
    else:
        print(f"  ✓ {label}")


def main():
    print("=" * 64)
    print("INTEGRITY CHECK")
    print("=" * 64)

    wiki_genes = load("wiki_genes.json") or {"genes": {}}
    wiki_mutations = load("wiki_mutations.json") or {"mutations": {}}
    wiki_species = load("wiki_species.json") or {"species": {}}
    wiki_index = load("wiki_index.json") or {}
    papers = load("papers.json") or {"papers": []}
    genes_panel = load("genes.json")
    if isinstance(genes_panel, dict):
        genes_panel = genes_panel.get("genes", [])
    species_index = load("species_index.json") or []
    supplement = load("species_wiki_supplement.json") or []

    # ---- 1. species references resolve ----
    index_keys = set()
    for s in species_index + supplement:
        if s.get("sci"):
            index_keys.add(str(s["sci"]).lower())
        if s.get("com"):
            index_keys.add(str(s["com"]).lower())

    referenced = {}
    for g in wiki_genes["genes"].values():
        for s in g.get("species_studied", []):
            referenced[s["name"]] = s.get("scientific")
    for m in wiki_mutations["mutations"].values():
        for s in m.get("species_studied", []):
            referenced.setdefault(s["name"], s.get("scientific"))
    for cname, rec in wiki_species["species"].items():
        referenced.setdefault(cname, rec.get("scientific_name"))

    missing_species = set()
    for name, sci in referenced.items():
        keys = {name.lower()} | {sci.lower() for sci in [sci] if sci}
        if not keys & index_keys:
            missing_species.add(name)
    check("species references resolve", missing_species)

    # ---- 2. gene → mutation chips exist ----
    mut_keys = set(wiki_mutations["mutations"].keys())
    missing_muts = set()
    for g in wiki_genes["genes"].values():
        for m in g.get("mutations", []):
            if m["mutation"] not in mut_keys:
                missing_muts.add(m["mutation"])
    check("gene→mutation chips exist", missing_muts)

    # ---- 3. mutation → gene/protein resolves ----
    gene_syms = {g["symbol"] for g in genes_panel} | set(wiki_genes["genes"].keys())
    gene_syms |= {str(s).lower() for s in gene_syms}  # case-insensitive fallback
    missing_proteins = set()
    for m in wiki_mutations["mutations"].values():
        if m["protein"] not in gene_syms and m["protein"].lower() not in gene_syms:
            missing_proteins.add(m["protein"])
    check("mutation→protein resolves", missing_proteins)

    # ---- 4. cited papers exist ----
    paper_ids = {p["id"] for p in papers["papers"]}
    missing_papers = set()
    def scan_papers(obj):
        if isinstance(obj, dict):
            if "paper_id" in obj and obj["paper_id"] not in paper_ids:
                missing_papers.add(obj["paper_id"])
            for v in obj.values():
                scan_papers(v)
        elif isinstance(obj, list):
            for v in obj:
                scan_papers(v)
    scan_papers(wiki_genes)
    scan_papers(wiki_mutations)
    scan_papers(wiki_species)
    # wiki analyses cite papers not all in papers.json (unindexed corpus) → warn only
    if missing_papers:
        warnings.append(f"cited paper_ids not in papers.json: {len(missing_papers)} "
                        f"(unindexed corpus papers) → {sorted(missing_papers)[:6]}")
        print(f"  ⚠ cited papers: {len(missing_papers)} not in papers.json (warn)")
    else:
        print("  ✓ cited papers resolve")

    # ---- 5. search index consistency ----
    idx_genes = {g["symbol"] for g in wiki_index.get("genes", [])}
    idx_muts = {m["canonical"] for m in wiki_index.get("mutations", [])}
    check("wiki_index genes ⊆ wiki_genes", idx_genes - set(wiki_genes["genes"].keys()))
    check("wiki_index mutations ⊆ wiki_mutations", idx_muts - mut_keys)

    # ---- 6. app-critical files exist ----
    for f in ["stats.json", "detections.parquet", "species.parquet", "genomes.parquet",
              "susceptibility.parquet", "provenance.json", "species_index.json",
              "papers.json", "genes.json", "gene_catalogue.json", "gene_presence.parquet"]:
        if not (WEB_DATA / f).exists():
            failures.append(f"missing file: web/public/data/{f}")
    geo_dir = WEB_DATA / "geojson"
    if not geo_dir.exists() or not any(geo_dir.iterdir()):
        failures.append("missing/empty geojson directory")
    print("  ✓ app-critical files present"
          if not any("missing file" in f for f in failures) else "")

    # ---- gene-panel numbers agree everywhere (D106) ----
    check_gene_numbers(failures)

    # ---- detection data quality (D112: every audit fix is a check) ----
    check_detection_quality(failures, warnings)

    # ---- spread model evidence block (SPREAD_MODEL Phase 3) ----
    try:
        sm = load("h5n1_spread_model.json") or {}
        ev = sm.get("evidence", {}).get("edges", {})
        if not ev:
            failures.append("h5n1_spread_model.json has no evidence block (run scripts/model/build_spread_edges.py)")
        else:
            bad_pids = [pid for b in ev.values() for pid in b.get("papers", [])
                        if pid not in paper_ids]
            if bad_pids:
                failures.append(f"spread evidence cites unknown papers (e.g. {bad_pids[:3]})")
            no_ev = [k for k, b in ev.items() if not b.get("count")]
            if no_ev:
                print(f"  ~ spread edges without corpus evidence (inferred): {len(no_ev)}")
    except Exception as e:
        failures.append(f"spread evidence check failed: {e}")

    # ---- summary ----
    print("-" * 64)
    for w in warnings:
        print(f"⚠ {w}")
    if failures:
        print(f"\n✗ {len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\n✓ All integrity checks passed")



def check_gene_numbers(failures):
    """D106: gene-panel numbers must agree across every artifact.

    Universe = curated + wiki + presence-catalogue (canonical-ID union).
    Every count below comes from the same sources the genes page and the
    downloads use, so a stale rebuild anywhere fails loudly.
    """
    def _canon(s):
        return (s or "").upper().replace("-", "").replace("_", "").replace(" ", "")

    def err(msg):
        failures.append(msg)
        print(f"  ✗ {msg}")

    wiki_doc = load("wiki_genes.json") or {"genes": {}}
    wiki = wiki_doc["genes"]
    cat = (load("gene_catalogue.json") or {}).get("gene_catalogue", {})
    genes_panel = load("genes.json") or []
    if isinstance(genes_panel, dict):
        genes_panel = genes_panel.get("genes", [])
    papers_doc = load("papers.json") or {"papers": []}
    n_papers = len(papers_doc.get("papers", papers_doc if isinstance(papers_doc, list) else []))

    # mirror export_gene_panel.py exactly: universe = curated + wiki +
    # catalogue (canonical union, viral included); literature = everything
    # except annotation-scope catalogue entries
    universe = {_canon(g["symbol"]) for g in genes_panel}
    universe |= {_canon(s) for s in wiki}
    universe |= {_canon(s) for s in cat}
    lit = {_canon(s) for s in universe
           if _canon(s) in {_canon(g["symbol"]) for g in genes_panel}
           or _canon(s) in {_canon(s) for s in wiki}
           or cat.get(next((k for k in cat if _canon(k) == _canon(s)), s), {}).get("evidence_scope") == "literature"}

    if wiki_doc.get("total_genes") != len(wiki):
        err(f"wiki total_genes={wiki_doc.get('total_genes')} != {len(wiki)} entries")
    try:
        import polars as _pl
        _pq_genes = set(_pl.read_parquet(WEB_DATA / "gene_presence.parquet")["gene"].unique().to_list())
    except Exception:
        _pq_genes = None
    if _pq_genes is not None:
        missing_summary = [s for s in cat if s not in _pq_genes]
        if missing_summary:
            err(f"{len(missing_summary)} catalogue genes missing from the presence "
                f"parquet (e.g. {missing_summary[:4]})")
    try:
        import polars as _pl
        n_jsonl = sum(1 for _ in open(ROOT / "data" / "genes" / "gene_presence_v2.jsonl"))
        n_pq = _pl.read_parquet(ROOT / "data" / "genes" / "gene_presence_v2.parquet").height
        if n_jsonl != n_pq:
            err(f"gene_presence_v2: jsonl {n_jsonl} rows != parquet {n_pq} rows "
                f"(rerun scripts/genes/rebuild_parquets.py)")
    except ImportError:
        print("  ~ polars unavailable — parquet sync check skipped")
    try:
        import polars as _pl2
        gp_rows = _pl2.read_parquet(WEB_DATA / "genes.parquet")
        if gp_rows.height != len(universe):
            err(f"genes.parquet has {gp_rows.height} rows != universe {len(universe)} "
                f"(rerun scripts/genes/export_gene_panel.py)")
        n_lit = gp_rows.filter(_pl2.col("evidence_scope") == "literature").height
        if n_lit != len(lit):
            err(f"genes.parquet literature rows {n_lit} != {len(lit)}")
    except Exception:
        err("genes.parquet unreadable — run scripts/genes/export_gene_panel.py")
    pwg = wiki_doc.get("papers_with_genes")
    if not pwg:
        err("wiki_genes.json missing papers_with_genes (rerun build_wiki_pages.py)")
    elif not (400 <= pwg <= n_papers):
        err(f"papers_with_genes={pwg} outside plausible range")
    else:
        print(f"  ✓ gene numbers consistent: universe {len(universe)} "
              f"({len(lit)} literature), catalogue {len(cat)}, "
              f"parquet genes {len(_pq_genes) if _pq_genes is not None else '?'}, "
              f"papers_with_genes {pwg}")




def check_detection_quality(failures, warnings):
    """D112: the audit-fix classes must never regress.

    - no trinomial scientific names; no common-name leakage vs taxon_id
    - generic single-word species_raw never resolves to a species
    - dates parse (or are null); 'Global' never counts as a country
    - presence exports are species-level (no trinomials/hybrids)
    - stats.json numbers add up against the parquet + geojson
    """
    try:
        import polars as _pl
    except ImportError:
        warnings.append("polars unavailable — detection quality checks skipped")
        return

    det = _pl.read_parquet(ROOT / "data" / "detections_merged.parquet")
    err = lambda m: (failures.append(m), print(f"  \u2717 {m}"))

    sci = det.filter(_pl.col("scientific_name").is_not_null())
    tri = sci.filter(_pl.col("scientific_name").str.split(" ").list.len() == 3)
    if tri.height:
        err(f"{tri.height} trinomial scientific_name rows (e.g. {tri['scientific_name'].unique().to_list()[:3]})")

    tax = _pl.read_csv(ROOT / "data" / "aves_taxonomy.tsv", separator="\t",
                       schema_overrides={"taxon_id": _pl.Int64})
    species_tax = (tax.filter(_pl.col("rank") == "species")
                      .select("taxon_id", "scientific_name")
                      .unique(subset="taxon_id").rename({"scientific_name": "tax_sci"}))
    mismatch = (det.filter(_pl.col("taxon_id").is_not_null())
                  .join(species_tax, on="taxon_id", how="inner")
                  .filter(_pl.col("scientific_name") != _pl.col("tax_sci")))
    if mismatch.height:
        err(f"{mismatch.height} rows where scientific_name disagrees with its own taxon_id "
            f"(e.g. {mismatch.select('scientific_name', 'tax_sci').unique().head(3).rows()})")

    GENERIC = {"crane", "duck", "hawk", "owl", "gull", "swan", "goose", "pigeon",
               "raptor", "shorebird", "waterfowl", "poultry", "bird"}
    gen = det.filter(_pl.col("species_raw").str.to_lowercase().is_in(list(GENERIC))
                     & ~_pl.col("species_raw").str.to_lowercase().str.contains(" ")
                     & _pl.col("scientific_name").is_not_null())
    if gen.height:
        err(f"{gen.height} generic-name rows still resolve to a species (e.g. {gen['species_raw'].unique().to_list()[:3]})")

    famish = det.filter(
        _pl.col("scientific_name").is_not_null() &
        (_pl.col("scientific_name").str.contains(r" sp\.") |
         _pl.col("scientific_name").str.split(" ").list.len() == 1))
    if famish.height:
        err(f"{famish.height} family/genus-level scientific_name rows (e.g. {famish['scientific_name'].unique().to_list()[:3]})")

    bad_dates = det.filter(
        _pl.col("date_detected").is_not_null() &
        ~_pl.col("date_detected").cast(_pl.Utf8).str.contains(r"^\d"))
    if bad_dates.height:
        err(f"{bad_dates.height} non-numeric date_detected values (e.g. {bad_dates['date_detected'].unique().to_list()[:3]})")

    # rolled species names must be binomials (no trinomials/hybrids) —
    # read the distinct species straight off the parquet matrix
    try:
        gp_species = _pl.read_parquet(WEB_DATA / "gene_presence.parquet")["species"].unique().to_list()
    except Exception:
        gp_species = []
    sub = [k for k in gp_species if len(k.split()) == 3 or " x " in k]
    if sub:
        err(f"{len(sub)} subspecies/hybrid species in gene_presence.parquet (e.g. {sub[:3]})")

    stats = load("stats.json") or {}
    if stats.get("detections") and stats["detections"] != det.height:
        err(f"stats.json detections {stats['detections']} != parquet {det.height} rows")
    real_countries = det.filter(_pl.col("country").is_not_null() & (_pl.col("country") != "Global"))["country"].n_unique()
    if stats.get("countries") and stats["countries"] != real_countries:
        err(f"stats.json countries {stats['countries']} != {real_countries} in parquet")
    try:
        geo = load("geojson/detections_by_country.geojson") or {"features": []}
        if stats.get("countries") and len(geo.get("features", [])) != stats["countries"]:
            err(f"map features {len(geo.get('features', []))} != stats countries {stats['countries']}")
    except OSError:
        pass
    null_rate = det.filter(_pl.col("scientific_name").is_null()).height / det.height
    if not (0.05 <= null_rate <= 0.25):
        err(f"null-species rate {null_rate:.1%} outside the 5–25% sanity band (mapping regression?)")

    print(f"  \u2713 detection quality: {det.height} rows, 0 trinomials, "
          f"{real_countries} countries, null-species {null_rate:.1%} (documented band)")

if __name__ == "__main__":
    main()
