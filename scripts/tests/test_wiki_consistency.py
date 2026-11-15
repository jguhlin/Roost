"""D98: wiki_genes.json is the canonical gene record — set equality invariants.

The user contract:
  - gene sets must be consistent across sources (\"all the same / equal\")
  - a gene that must have a wiki entry lacking one is an ERROR

Invariants enforced on the built artifacts:
  1. Every curated gene (genes.json, non-viral) has a wiki host entry.
  2. Every presence-catalogue literature-scope gene has a wiki host entry.
  3. No presence-catalogue annotation gene is a wiki host gene
     (scope is derived from wiki membership — export_presence.py D98).
  4. Every wiki host gene with evidence in gene_evidence_counts has >=2
     papers (threshold discipline) — curated genes excepted.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "public" / "data"


def _canon(s: str) -> str:
    return (s or "").upper().replace("-", "").replace("_", "").replace(" ", "")


def _load(name):
    return json.loads((WEB / name).read_text())


def test_files_exist():
    for name in ("wiki_genes.json", "gene_catalogue.json", "gene_presence.parquet", "genes.json"):
        assert (WEB / name).exists(), f"{name} missing"


def test_curated_genes_have_wiki_entries():
    wiki = _load("wiki_genes.json")["genes"]
    wiki_host = {_canon(s) for s, w in wiki.items() if w.get("kind") != "viral"}
    curated = _load("genes.json")["genes"]
    missing = [g["symbol"] for g in curated
               if g.get("category") not in ("Viral Protein", "Viral Segment")
               and _canon(g["symbol"]) not in wiki_host]
    assert not missing, f"curated genes without wiki entries: {missing}"


def test_catalogue_literature_genes_have_wiki_entries():
    wiki = _load("wiki_genes.json")["genes"]
    wiki_host = {_canon(s) for s, w in wiki.items() if w.get("kind") != "viral"}
    catalogue = _load("gene_catalogue.json")["gene_catalogue"]
    missing = [sym for sym, info in catalogue.items()
               if info.get("evidence_scope") == "literature"
               and _canon(sym) not in wiki_host]
    assert not missing, (
        f"{len(missing)} literature-scope genes have no wiki entry "
        f"(e.g. {sorted(missing)[:8]}) — rerun scripts/genes/export_presence.py "
        "after scripts/papers/build_wiki_pages.py"
    )


def test_catalogue_annotation_genes_are_not_wiki_host_genes():
    wiki = _load("wiki_genes.json")["genes"]
    wiki_host = {_canon(s) for s, w in wiki.items() if w.get("kind") != "viral"}
    catalogue = _load("gene_catalogue.json")["gene_catalogue"]
    wrong = [sym for sym, info in catalogue.items()
             if info.get("evidence_scope") != "literature"
             and _canon(sym) in wiki_host]
    assert not wrong, (
        f"{len(wrong)} annotation-scope genes are wiki host genes "
        f"({sorted(wrong)[:8]}) — evidence_scope must be derived from wiki "
        "membership (export_presence.py)"
    )


def _species_linked_genes():
    """Mirror the builder's 2026-10-05 eligibility rule EXACTLY: genes with
    >=1 typed claim naming a host species get wiki pages even below the
    2-paper threshold (evidence-rich singletons, by design). Uses the
    builder's own normalize_gene_name so alias chains (GP96 -> HSP90B1,
    RIG-I -> DDX58, …) resolve identically on both sides."""
    tc = ROOT / "data" / "papers" / "typed_claims.parquet"
    if not tc.exists():
        return set()
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "papers"))
        from build_wiki_pages import normalize_gene_name
    except Exception:
        def normalize_gene_name(s):
            return s
    import polars as pl
    linked = set()
    for r in pl.read_parquet(tc).iter_rows(named=True):
        try:
            sp = json.loads(r["species"]) if isinstance(r["species"], str) else (r["species"] or [])
        except Exception:
            sp = []
        if not any(isinstance(s, str) and " " in s for s in sp):
            continue
        try:
            gs = json.loads(r["genes"]) if isinstance(r["genes"], str) else (r["genes"] or [])
        except Exception:
            gs = []
        for g in gs:
            n = normalize_gene_name(str(g))
            if n:
                linked.add(_canon(n))
    return linked


def test_wiki_genes_meet_evidence_threshold():
    """Non-curated wiki genes need >=2 corpus papers — EXCEPT the
    species-linked singletons the builder deliberately admits (typed
    claim naming a host species; policy 2026-10-05). A 1-paper page that
    is neither means evidence was lost or the threshold was bypassed."""
    wiki = _load("wiki_genes.json")["genes"]
    curated = {g["symbol"].upper() for g in _load("genes.json")["genes"]}
    species_linked = _species_linked_genes()
    counts_path = ROOT / "data" / "papers" / "gene_evidence_counts.json"
    if counts_path.exists():
        counts = json.loads(counts_path.read_text())
    else:
        counts = {}
    thin = []
    for sym, w in wiki.items():
        if w.get("kind") == "viral" or sym.upper() in curated:
            continue
        if _canon(sym) in species_linked:
            continue  # deliberate singleton policy
        papers = max(w.get("paper_count", 0), counts.get(sym, {}).get("papers", 0))
        if papers < 2:
            thin.append((sym, papers))
    assert not thin, f"wiki genes below the 2-paper threshold (not species-linked): {thin[:10]}"


def test_no_noise_genes_in_wiki():
    """Reporter/housekeeping genes must never get wiki pages."""
    wiki = _load("wiki_genes.json")["genes"]
    noise = {"GFP", "GAPDH", "ACTB", "TUBB", "IGG"}
    present = sorted(noise & {s.upper() for s in wiki})
    assert not present, f"noise genes leaked into wiki: {present}"
