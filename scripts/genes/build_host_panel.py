#!/usr/bin/env python3
"""
Build host_panel_v2 — the tiered host-gene panel for the presence pipeline.

Merges:
  - curated panel (data/genes/gene_panel.json, 18-19 genes, tier 1)
  - wiki corpus host genes (web/public/data/wiki_genes.json, kind=host, >=2 papers)

Each entry: symbol, name, tier, category, paralog family, aliases, source
provenance, chicken gene IDs where known. Output is versioned; all presence
calls are keyed to a panel version.

Usage: pixi run python scripts/genes/build_host_panel.py
"""

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENE_DIR = ROOT / "data" / "genes"
CURATED = GENE_DIR / "gene_panel.json"
WIKI = ROOT / "web" / "public" / "data" / "wiki_genes.json"
BACKBONE = GENE_DIR / "avimm_uniprot_backbone.json"
OUT = GENE_DIR / "host_panel_v2.json"

PANEL_VERSION = f"v3.{date.today().strftime('%Y%m%d')}"

# Paralog families needing family-aware interpretation (plan §2)
PARALOG_FAMILIES = {
    "ANP32A": "ANP32", "ANP32B": "ANP32", "ANP32E": "ANP32",
    "IFITM": "IFITM", "IFIT5": "IFIT",
    "MX1": "MX",
    "OAS": "OAS",
    "TLR3": "TLR", "TLR7": "TLR", "TLR21": "TLR", "TLR": "TLR",
    "IRF3": "IRF", "IRF7": "IRF", "IRF9": "IRF",
    "TRIM25": "TRIM", "TRIM32": "TRIM", "TRIM14": "TRIM",
    "IFNA": "IFN", "IFNB": "IFN", "IFNG": "IFN",
}

# Wiki-only genes to exclude from the search panel (not DNA-level entities
# or too generic to search)
SKIP_WIKI = {
    "SA",        # sialic acid = glycan family, not one gene
    "ANP32",     # family-level (members searched individually)
    "TLR",       # family-level
    "KPNA",      # importin family — resolve members later
}

# Curated chicken gene IDs (from gene_panel.json) + wiki additions we can
# resolve later via NCBI; wiki-only entries carry null IDs for now
CHICKEN_IDS = {
    "ANP32A": 395532, "ANP32B": 395338, "ANP32E": 771113,
    "DDX58": 395092, "IFIH1": 395251, "IFIT5": 395574,
    "MX1": 395370, "OAS": 395508, "RSAD2": 373953, "HERC3": 422139,
    "TRIM25": 395343, "TRIM32": 419873, "IRF7": 395296, "IRF3": 395190,
    "MAVS": 428302, "IFITM": 100856941, "NS1": None, "PB2": None,
}


def main():
    curated = json.loads(CURATED.read_text())
    wiki = json.loads(WIKI.read_text())["genes"]

    entries = {}
    for g in curated:
        entries[g["symbol"]] = {
            "symbol": g["symbol"],
            "name": g.get("name", g["symbol"]),
            "tier": 1,
            "category": g.get("category", "Dependency"),
            "paralog_family": PARALOG_FAMILIES.get(g["symbol"]),
            "aliases": [],
            "chicken_gene_id": None,  # legacy curated IDs were WRONG (D5) — resolve by symbol
            "chicken_refseq": None,
            "sources": ["curated_panel"],
            "notes": g.get("notes"),
        }

    # Wiki host genes (kind=host) not already present
    added = 0
    for symbol, w in wiki.items():
        if w.get("kind") != "host" or symbol in entries or symbol in SKIP_WIKI:
            continue
        entries[symbol] = {
            "symbol": symbol,
            "name": w.get("name", symbol),
            "tier": 2,
            "category": w.get("category", "Host Gene"),
            "paralog_family": PARALOG_FAMILIES.get(symbol),
            "aliases": [],
            "chicken_gene_id": None,  # legacy dict IDs unreliable (D5) — resolve by symbol
            "chicken_refseq": None,
            "sources": ["wiki_corpus"],
            "paper_count": w.get("paper_count", 0),
            "notes": f"Literature-derived ({w.get('host_scope', '?')} evidence scope)",
        }
        added += 1

    # Tier 3: UniProt GO immune-system backbone (comprehensive chicken set)
    added_t3 = 0
    if BACKBONE.exists():
        backbone = json.loads(BACKBONE.read_text())["genes"]
        for gid, info in backbone.items():
            sym = info["symbol"].upper()
            if sym in entries or sym in SKIP_WIKI:
                continue
            # skip uninformative LOC symbols unless they have a real name
            pname = info.get("protein_name", "")
            if sym.startswith("LOC") and not pname:
                continue
            entries[sym] = {
                "symbol": sym,
                "name": pname or sym,
                "tier": 3,
                "category": "Immune (GO:0002376)",
                "paralog_family": PARALOG_FAMILIES.get(sym),
                "aliases": [s.strip() for s in (info.get("synonyms") or "").split(";") if s.strip()],
                "chicken_gene_id": int(gid),
                "chicken_refseq": None,
                "uniprot": info.get("uniprot"),
                "sources": ["uniprot_go_backbone"],
                "notes": "Chicken immune-system process (GO:0002376) via UniProt",
            }
            added_t3 += 1

    panel = sorted(entries.values(), key=lambda e: (e["tier"], e["symbol"]))
    out = {
        "panel_version": PANEL_VERSION,
        "generated": date.today().isoformat(),
        "total_genes": len(panel),
        "tier1": sum(1 for e in panel if e["tier"] == 1),
        "tier2": sum(1 for e in panel if e["tier"] == 2),
        "tier3": sum(1 for e in panel if e["tier"] == 3),
        "paralog_families": sorted({e["paralog_family"] for e in panel if e["paralog_family"]}),
        "genes": panel,
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"host_panel_v2: {len(panel)} genes "
          f"(tier1={out['tier1']}, tier2={out['tier2']}, tier3={out['tier3']}) → {OUT}")
    fams = out["paralog_families"]
    print(f"paralog families: {', '.join(fams)}")


if __name__ == "__main__":
    main()
