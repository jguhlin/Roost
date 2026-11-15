#!/usr/bin/env python3
"""Export the gene panel for the website Downloads page.

Builds web/public/data/genes.parquet — one row per gene in the panel
universe (curated + wiki corpus + presence catalogue), with:

  symbol, name, category, kind (host|viral), evidence_scope, tier,
  papers (corpus papers with gene evidence), aliases,
  presence_full / presence_fragment / presence_missing / species_searched

Presence counts derive from gene_presence.parquet (the single matrix —
Phase 2 Step 4 retired the static summary JSON this used to read).
Phase 2 Step 5: parquet only; genes.csv is retired.

Usage: pixi run python scripts/genes/export_gene_panel.py
"""

import json
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent.parent
WEB = ROOT / "web" / "public" / "data"


def presence_summary() -> dict:
    """{symbol: {full, fragment, not_found, total}} from the matrix parquet."""
    pq = pl.read_parquet(WEB / "gene_presence.parquet")
    agg = (
        pq.group_by("gene")
        .agg(
            pl.len().alias("total"),
            (pl.col("status") == "FULL").sum().alias("full"),
            (pl.col("status") == "FRAGMENT").sum().alias("fragment"),
            (pl.col("status") == "NOT_FOUND").sum().alias("not_found"),
        )
        .to_dicts()
    )
    return {r["gene"]: r for r in agg}


def main() -> None:
    curated = json.loads((WEB / "genes.json").read_text())["genes"]
    wiki = json.loads((WEB / "wiki_genes.json").read_text())["genes"]
    cat = json.loads((WEB / "gene_catalogue.json").read_text())["gene_catalogue"]
    summary = presence_summary()

    def canon(s):
        return (s or "").upper().replace("-", "").replace("_", "").replace(" ", "")

    rows = {}
    for g in curated:
        rows[canon(g["symbol"])] = {
            "symbol": g["symbol"], "name": g.get("name", ""), "category": g.get("category", ""),
            "kind": "viral" if g.get("category") in ("Viral Protein", "Viral Segment") else "host",
            "evidence_scope": "literature", "tier": g.get("tier"),
            # Phase 6: papers must be a PAPER count — this was total_mentions
            # (441 for ANP32A), i.e. mention counts mislabeled as papers.
            # The wiki max-merge below then unifies with corpus counts.
            "papers": g.get("paper_count") or 0,
            "aliases": "; ".join(g.get("aliases") or []),
        }
    for sym, w in wiki.items():
        c = canon(sym)
        r = rows.setdefault(c, {"symbol": sym, "name": "", "category": "", "kind": "host",
                                "evidence_scope": "literature", "tier": None, "papers": 0, "aliases": ""})
        r["papers"] = max(r["papers"], w.get("paper_count") or 0)
        if w.get("kind") == "viral":
            r["kind"] = "viral"
        if not r["name"] and w.get("name"):
            r["name"] = w["name"]
        if not r["category"] and w.get("category"):
            r["category"] = w["category"]
    for sym, info in cat.items():
        c = canon(sym)
        r = rows.setdefault(c, {"symbol": sym, "name": info.get("name") or "", "category": info.get("category") or "",
                                "kind": "host", "evidence_scope": info.get("evidence_scope", "annotation"),
                                "tier": None, "papers": 0, "aliases": ""})
        if info.get("evidence_scope") == "literature":
            r["evidence_scope"] = "literature"
        # catalogue aliases (MHC-B nomenclature etc.) ship in the panel
        # download too — curated/wiki rows don't carry them
        extra = [a for a in (info.get("aliases") or [])
                 if a.lower() not in {x.strip().lower()
                                      for x in r["aliases"].split(";") if x.strip()}]
        if extra:
            r["aliases"] = "; ".join(
                x for x in [r["aliases"], "; ".join(extra)] if x)
        s = summary.get(sym)
        if s:
            r.update({"presence_full": s["full"], "presence_fragment": s["fragment"],
                      "presence_missing": s["not_found"], "species_searched": s["total"]})

    out = []
    for r in rows.values():
        r.setdefault("presence_full", None)
        r.setdefault("presence_fragment", None)
        r.setdefault("presence_missing", None)
        r.setdefault("species_searched", None)
        out.append(r)
    out.sort(key=lambda r: (-r["papers"], r["symbol"]))

    cols = ["symbol", "name", "category", "kind", "evidence_scope", "tier", "papers",
            "aliases", "presence_full", "presence_fragment", "presence_missing", "species_searched"]
    df = pl.DataFrame(out, schema_overrides={"tier": pl.Int64}, infer_schema_length=None)[cols]
    df.write_parquet(WEB / "genes.parquet")

    lit = sum(1 for r in out if r["evidence_scope"] == "literature")
    print(f"genes: {len(out)} rows ({lit} literature, {len(out) - lit} annotation) "
          f"| with presence data: {sum(1 for r in out if r['species_searched'])}")
    print(f"wrote {WEB / 'genes.parquet'}")


if __name__ == "__main__":
    main()
