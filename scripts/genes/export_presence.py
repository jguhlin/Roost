#!/usr/bin/env python3
"""
Export the gene presence matrix for the web application.

Reads data/genes/gene_presence_v2.jsonl and produces:
  web/public/data/gene_catalogue.json — gene catalogue + key genes (small)
  web/public/data/gene_presence.parquet — full calls matrix (DuckDB);
    per-species/per-gene rollups are derived client-side from it

Identity/labeling decisions come from data/genes/gene_config.json
(aliases, importance overrides, display names, catalogue aliases) so the
portal can grow without code changes (D28).

Usage: pixi run python scripts/genes/export_presence.py
"""

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CALLS_FILE = ROOT / "data" / "genes" / "gene_presence_v2.jsonl"
PANEL_FILE = ROOT / "data" / "genes" / "host_panel_v2.json"
CONFIG_FILE = ROOT / "data" / "genes" / "gene_config.json"
WIKI_GENES = ROOT / "web" / "public" / "data" / "wiki_genes.json"
FUNCTIONS_FILE = ROOT / "data" / "genes" / "gene_functions.json"
OUT = ROOT / "web" / "public" / "data" / "gene_catalogue.json"

# ---------------------------------------------------------------------------
# Importance tiers — a gene's ROLE in H5N1 biology (independent of the status
# of any particular search). Displayed as a badge.
#   critical: loss/gain directly tied to H5N1 outcome (RIG-I, MDA5, ANP32A)
#   high:     strong literature evidence for HPAI outcome relevance
#   standard: immune pathway member, presence tracked for completeness
# Status (FULL/FRAGMENT/NOT_FOUND) is separate — what the data says for THIS
# species. Both facts are shown independently.
# ---------------------------------------------------------------------------
CRITICAL = {"DDX58", "IFIH1", "ANP32A"}
HIGH = {
    "ANP32B", "ANP32E", "MX1", "IFIT5", "IFITM3", "OASL", "RSAD2",
    "STAT1", "STAT2", "TLR3", "TLR7", "TLR21", "MAVS", "IRF3", "IRF7",
    "TRIM25", "IFNB1", "IFNA4",
}

# Evidence rank for alias merging (higher wins)
STATUS_RANK = {"FULL": 3, "FRAGMENT": 2, "NOT_FOUND": 1}
LEVEL_ORDER = ["E5", "E4", "E3", "E2", "E1", "E0"]


def level_rank(level: str) -> int:
    """E5_annotated -> 5 (bigger is better)."""
    for i, prefix in enumerate(LEVEL_ORDER):
        if level.startswith(prefix):
            return len(LEVEL_ORDER) - i
    return 0


SEARCH_STATUS = ROOT / "data" / "papers" / "connections" / "search_status.json"


def literature_genes():
    """Genes with corpus evidence (search status hit) — literature confers
    panel scope; GO-backbone genes without corpus hits are annotation-only
    context (user doctrine, D85)."""
    lit = set()
    if SEARCH_STATUS.exists():
        try:
            st = json.loads(SEARCH_STATUS.read_text())["genes"]
            lit = {g for g, r in st.items() if r.get("status") == "hit"}
        except Exception:
            pass
    return lit


def load_config() -> dict:
    cfg = {"aliases": {}, "importance_overrides": {}, "display_names": {},
           "impact_if_absent": {}, "functions": {}, "catalogue_aliases": {}}
    if CONFIG_FILE.exists():
        raw = json.loads(CONFIG_FILE.read_text())
        cfg["aliases"] = {k: v for k, v in raw.get("aliases", {}).items()
                          if not k.startswith("_")}
        cfg["catalogue_aliases"] = {k: v for k, v in raw.get("catalogue_aliases", {}).items()
                                   if not k.startswith("_")}
        io = raw.get("importance_overrides", {})
        cfg["importance_overrides"] = {
            tier: [g for g in genes if not g.startswith("_")]
            for tier, genes in io.items() if isinstance(genes, list)
        }
        cfg["display_names"] = {k: v for k, v in raw.get("display_names", {}).items()
                                if not k.startswith("_")}
        cfg["impact_if_absent"] = {k: v for k, v in raw.get("impact_if_absent", {}).items()
                                   if not k.startswith("_")}
        cfg["functions"] = {k: v for k, v in raw.get("functions", {}).items()
                            if not k.startswith("_")}
    # UniProt-fetched functions for GO-backbone genes (fetch_uniprot_functions.py)
    if FUNCTIONS_FILE.exists():
        uniprot_fns = json.loads(FUNCTIONS_FILE.read_text())
        merged = dict(uniprot_fns)
        merged.update(cfg["functions"])  # curated wins
        cfg["functions"] = merged
    return cfg


def wiki_host_genes() -> set[str]:
    """Canonical IDs of wiki host genes — the single source of truth for
    literature scope (D98). Viral entries never confer host scope."""
    wiki = json.loads(WIKI_GENES.read_text())["genes"]
    return {_canon_id(s) for s, w in wiki.items() if w.get("kind") != "viral"}


def _canon_id(symbol: str) -> str:
    return (symbol or "").upper().replace("-", "").replace("_", "").replace(" ", "")


def main():
    cfg = load_config()
    aliases = cfg["aliases"]
    display_names = cfg["display_names"]
    functions = cfg["functions"]
    override_high = set(cfg["importance_overrides"].get("high", []))
    override_critical = set(cfg["importance_overrides"].get("critical", []))

    def importance_of(gene: str) -> str:
        if gene in CRITICAL or gene in override_critical:
            return "critical"
        if gene in HIGH or gene in override_high:
            return "high"
        return "standard"

    LIT = literature_genes()
    WIKI_HOST = wiki_host_genes()  # D98: wiki membership defines literature scope
    if not WIKI_HOST:
        raise SystemExit("[presence] wiki_genes.json has no host entries — "
                         "run scripts/papers/build_wiki_pages.py first")

    calls = [json.loads(l) for l in open(CALLS_FILE)]

    # data sovereignty filter: genomes marked 'restricted' in the manifest
    # (generated without iwi approval) must never appear in public-facing data
    _man = json.load(open(ROOT / "data/genomes/genomes.json"))
    _restricted = {g["species"] for g in _man["genomes"] if g.get("status") == "restricted"}
    if _restricted:
        _n = len(calls)
        calls = [c for c in calls if c.get("species") not in _restricted]
        print(f"[presence] sovereignty filter: removed {_n - len(calls)} calls "
              f"from restricted genomes ({_restricted})")

    # host panel metadata (name, category, aliases for every gene)
    panel = json.load(open(PANEL_FILE))
    panel_genes = panel["genes"] if isinstance(panel, dict) else panel
    panel_meta = {g["symbol"]: g for g in panel_genes}

    # deduplicate: keep latest per (species, gene), then canonicalise aliases.
    # Alias merge = best-evidence-wins across {alias, canonical} calls.
    by_key = {}
    for c in calls:
        by_key[(c["species"], c["gene_symbol"])] = c

    merged_counts = defaultdict(int)
    canonical_by_key = {}
    for (species, gene), c in by_key.items():
        canon = aliases.get(gene, gene)
        if canon != gene:
            merged_counts[(species, gene)] = 1
        existing = canonical_by_key.get((species, canon))
        if existing is None or (
            STATUS_RANK[c["search_status"]], level_rank(c["status_level"])
        ) > (
            STATUS_RANK[existing["search_status"]], level_rank(existing["status_level"])
        ):
            canonical_by_key[(species, canon)] = c

    # group by species — ALL genes, each with importance + evidence
    species_data = defaultdict(dict)
    for (species, gene), c in canonical_by_key.items():
        species_data[species][gene] = {
            "status": c["search_status"],          # FULL | FRAGMENT | NOT_FOUND
            "level": c["status_level"],            # E0–E5 evidence level
            "method": c.get("method", c.get("evidence", {}).get("method")),
            "importance": importance_of(gene),      # critical | high | standard
            # absence-confidence ladder (only meaningful on NOT_FOUND):
            # high = genome searchability ≥0.90, medium ≥0.75, low below.
            # NULL for detected genes. Surfaces in the phylogeny gene
            # overlay so low-confidence non-detections are never mistaken
            # for established losses.
            "conf": c.get("absence_confidence"),
            "searchability": (round(c["searchability"], 3)
                               if c.get("searchability") is not None else None),
        }

    # D111: species-level rollup — subspecies assemblies (26 trinomials,
    # e.g. Gallus gallus gallus, Zonotrichia leucophrys gambelii/nuttalli)
    # and the Patagioenas hybrid merge into their binomial with
    # best-evidence-wins (FULL > FRAGMENT > NOT_FOUND). Raw per-assembly
    # calls stay untouched in the jsonl; only the display layer rolls up.
    ROLL_RANK = {"FULL": 2, "FRAGMENT": 1, "NOT_FOUND": 0}

    def binomial_of(name: str) -> str:
        if " x " in name:                     # hybrid: first parent's binomial
            return " ".join(name.split(" x ")[0].split()[:2])
        parts = name.split()
        return " ".join(parts[:2]) if len(parts) >= 2 else name

    rolled = defaultdict(dict)
    for species, genes in species_data.items():
        target = binomial_of(species)
        for gene, info in genes.items():
            cur = rolled[target].get(gene)
            if cur is None or ROLL_RANK[info["status"]] > ROLL_RANK[cur["status"]]:
                rolled[target][gene] = info
            elif (cur and info["status"] == cur["status"]
                  and ROLL_RANK[info["status"]] == ROLL_RANK.get(cur["status"], -1)
                  and str(info.get("method", "")) == "annotation"
                  and str(cur.get("method", "")) != "annotation"):
                pass  # keep non-annotation evidence on ties
    species_data = rolled

    # per-species summary
    summary = {}
    for species, genes in species_data.items():
        n_full = sum(1 for g in genes.values() if g["status"] == "FULL")
        n_frag = sum(1 for g in genes.values() if g["status"] == "FRAGMENT")
        n_absent = sum(1 for g in genes.values() if g["status"] == "NOT_FOUND")
        critical_absent = [g for g, v in genes.items()
                           if v["status"] == "NOT_FOUND" and v["importance"] == "critical"]
        high_absent = [g for g, v in genes.items()
                       if v["status"] == "NOT_FOUND" and v["importance"] == "high"]
        summary[species] = {
            "total_genes_searched": len(genes),
            "full": n_full,
            "fragment": n_frag,
            "not_found": n_absent,
            "critical_absences": critical_absent,
            "high_absences": high_absent,
        }

    # per-gene status transpose — kept OUT of the shipped catalogue: the
    # species matrix above is the single copy; per-gene species views are
    # derived client-side (D-phase2: duplication removed 2026-09-11)
    gene_statuses = defaultdict(dict)
    for sp, genes in species_data.items():
        for g, info in genes.items():
            gene_statuses[g][sp] = info["status"]

    # gene catalogue — every gene with display name, importance and
    # host-panel metadata (category, aliases, notes) for auto-generated gene
    # pages. LOC* symbols are flagged as unannotated loci.
    gene_catalogue = {}
    for gene in sorted({g for _, g in canonical_by_key}):
        meta = panel_meta.get(gene, {})
        sources = meta.get("sources") or []
        gene_catalogue[gene] = {
            "name": display_names.get(gene, meta.get("name", gene)),
            "importance": importance_of(gene),
            "category": meta.get("category"),
            "aliases": sorted(set((meta.get("aliases") or [])
                                   + cfg["catalogue_aliases"].get(gene, []))),
            "notes": meta.get("notes"),
            "unannotated_locus": gene.startswith("LOC"),
            "impact_if_absent": cfg["impact_if_absent"].get(gene),
            "function": functions.get(gene),
            # D98: literature scope == wiki membership (single definition).
            # Legacy signals (host-panel sources, search-status hits) no
            # longer confer scope independently.
            "evidence_scope": ("literature" if _canon_id(gene) in WIKI_HOST
                               else "annotation"),
        }

    # key genes (shown in modal) = critical + high importance
    key_genes = {g: v for g, v in gene_catalogue.items() if v["importance"] != "standard"}

    # Phase 2 Step 4: no static summary files — both rollups are derived
    # client-side from gene_presence.parquet (db.getSpeciesGeneSummary /
    # db.getGenePresenceSummaries), so the parquet is the only shipped
    # presence artifact besides the small catalogue JSON.

    # The shipped presence data is (a) gene_presence.parquet (the full
    # matrix, queried via DuckDB) and (b) this small catalogue JSON
    # (metadata + header counts). The 13 MB gene_presence.json is retired.
    OUT.write_text(json.dumps({
        "generated": date.today().isoformat(),
        "total_species": len(species_data),
        "total_assemblies": len({c.get("assembly_accession") for c in calls
                                  if c.get("assembly_accession")}),
        "total_gene_calls": len(canonical_by_key),
        "total_genes": len(gene_catalogue),
        "alias_merges": sum(merged_counts.values()),
        # species universe for dropdowns (avoids DuckDB on memory-heavy
        # pages that only need the list, e.g. the Cytoscape model)
        "species_list": sorted(species_data.keys()),
        "gene_catalogue": gene_catalogue,
        "key_genes": key_genes,
    }, separators=(",", ":")))

    # Long-format parquet of the same matrix (single shipped copy once
    # consumers migrate to DuckDB — Phase 2 Step 3). Built from the rolled
    # species_data so it matches the JSON `species` section row-for-row.
    try:
        import polars as pl
    except ImportError:
        pl = None
    if pl is not None:
        rows = [
            {"species": sp, "gene": g, "status": info["status"],
             "level": info["level"], "method": info.get("method"),
             "importance": info["importance"],
             "conf": info.get("conf"),
             "searchability": info.get("searchability")}
            for sp, genes in species_data.items()
            for g, info in genes.items()
        ]
        pq = pl.DataFrame(rows, schema_overrides={
            # mostly-null columns need explicit types: `conf` is None for
            # every detected gene, so inference sees all-nulls then trips on
            # the first "high"; same guard for method/searchability.
            "method": pl.Utf8, "conf": pl.Utf8, "searchability": pl.Float64,
        }).sort(["gene", "species"])
        assert pq.height == sum(len(g) for g in species_data.values()), \
            "parquet rows != matrix calls"
        pq_path = OUT.parent / "gene_presence.parquet"
        pq.write_parquet(pq_path, compression="zstd")
        print(f"Parquet matrix: {pq.height:,} calls × {pq.width} cols "
              f"→ {pq_path.name} ({pq_path.stat().st_size / 1024:.0f} KB, zstd)")
    else:
        print("polars unavailable — gene_presence.parquet skipped")

    print(f"Exported {len(species_data)} species × {len(canonical_by_key)} calls → {OUT}")
    print(f"Genes: {len(gene_catalogue)} total, {len(key_genes)} key (critical+high)")
    if merged_counts:
        print(f"Alias merges: {sum(merged_counts.values())} calls "
              f"({len(set(g for _, g in merged_counts))} aliases: "
              f"{sorted(set(g for _, g in merged_counts))})")
    n_loci = sum(1 for g in gene_catalogue.values() if g["unannotated_locus"])
    print(f"Unannotated loci flagged: {n_loci}")
    for sp, s in sorted(summary.items()):
        critical = f" ⚠ {s['critical_absences']}" if s["critical_absences"] else ""
        print(f"  {sp[:28]:30s} FULL:{s['full']:3d} FRAG:{s['fragment']:3d} NF:{s['not_found']:3d}{critical}")

    # D98 hard gate: every literature-scope catalogue gene must have a wiki
    # entry, and no wiki host gene may be scoped annotation. With scope
    # derived from wiki membership above this holds by construction — the
    # gate exists to catch manual edits and pipeline drift.
    lit = [g for g, v in gene_catalogue.items() if v["evidence_scope"] == "literature"]
    ann_in_wiki = [g for g, v in gene_catalogue.items()
                   if v["evidence_scope"] == "annotation" and _canon_id(g) in WIKI_HOST]
    if ann_in_wiki:
        raise SystemExit(f"[presence] consistency FAILED: {len(ann_in_wiki)} "
                         f"annotation-scoped genes are wiki host genes "
                         f"({sorted(ann_in_wiki)[:6]})")
    print(f"[presence] consistency OK: {len(lit)} literature / "
          f"{len(gene_catalogue) - len(lit)} annotation; all literature genes "
          "have wiki entries")


if __name__ == "__main__":
    main()
