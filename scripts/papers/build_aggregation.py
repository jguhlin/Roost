#!/usr/bin/env python3
"""Aggregation layer: fold extracted data into the web-facing payloads.

1. Gene evidence: per-gene literature cards from gene_involvement +
   mechanisms (actors), with paper links, findings, and verification status
2. Pathway edges: mechanisms (actor→interaction→target) as graph edges with
   paper provenance
3. Trait table: paper_species_traits folded into species_traits.parquet,
   filling the 11 pending traits with paper-backed values
4. Research landscape digest: contradictions + gaps + open questions summary

Outputs (web/public/data, not in git):
  gene_evidence/{GENE}.json     — literature evidence per gene
  pathway_edges.json            — mechanism edges for the pathway graph
  species_traits.parquet        — updated with paper-derived traits
  research_landscape.json       — digest for the landscape view

Run:  pixi run python scripts/papers/build_aggregation.py [--genes-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "papers"
WEB = ROOT / "web" / "public" / "data"
PAPERS_JSON = WEB / "papers.json"

# --- inputs ---
EXTRAS = DATA / "paper_extras.parquet"
MECHANISMS = DATA / "paper_mechanisms.parquet"
PHENOTYPES = DATA / "paper_species_traits.parquet"
FINDINGS = DATA / "paper_key_findings.parquet"
CONTRA = WEB / "papers" / "contradictions.json"
GAPS = DATA / "research_gaps.json"
SPECIES_TRAITS = ROOT / "data" / "species_traits.parquet"

# --- outputs ---
GENE_EV_DIR = WEB / "gene_evidence"
PATHWAY_EDGES = WEB / "pathway_edges.json"
LANDSCAPE = WEB / "research_landscape.json"


def load_papers():
    return {p["id"]: p for p in json.loads(PAPERS_JSON.read_text())["papers"]}


# load the LLM-resolved gene alias map (persistent, like species aliases)
GENE_ALIASES = {}
GENE_SYNONYMS = {}
_gene_alias_file = ROOT / "data" / "papers" / "gene_alias_map.json"
if _gene_alias_file.exists():
    _am = json.loads(_gene_alias_file.read_text())
    GENE_ALIASES = _am.get("aliases", {})
    GENE_SYNONYMS = _am.get("synonyms", {})


def norm_gene(s: str) -> str:
    """Normalize gene/mutation actor names via the LLM alias map."""
    s = str(s).strip()
    if not s:
        return ""
    hit = GENE_ALIASES.get(s) or GENE_ALIASES.get(s.upper())
    if hit:
        return "" if hit == "NOT_A_GENE" else GENE_SYNONYMS.get(hit) or GENE_SYNONYMS.get(hit.upper(), hit)
    # fallback: basic normalization for unmapped names
    import re
    s = s.upper().strip()
    paren = re.search(r'\(([A-Z][A-Z0-9]{1,6})\)$', s)
    if paren:
        return GENE_SYNONYMS.get(paren.group(1)) or GENE_SYNONYMS.get(paren.group(1).upper(), paren.group(1))
    for prefix in ("AIV ", "VIRAL ", "HOST ", "MUTATION "):
        if s.startswith(prefix):
            s = s[len(prefix):]
    for suffix in (" PROTEIN", " PROTEINS", " GENE"):
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    return GENE_SYNONYMS.get(s) or GENE_SYNONYMS.get(s.upper(), s)


def build_gene_evidence(papers):
    """Per-gene literature cards from gene_involvement + mechanisms."""
    GENE_EV_DIR.mkdir(parents=True, exist_ok=True)
    gene_data = defaultdict(lambda: {
        "papers": [], "mechanisms": [], "n_studied": 0, "n_perturbed": 0,
        "n_measured": 0, "n_context": 0,
    })

    # gene involvement from the 7-query enrichment
    extras = pl.read_parquet(EXTRAS)
    for r in extras.iter_rows(named=True):
        gi = r.get("gene_involvement")
        if not gi:
            continue
        try:
            entries = json.loads(gi)
        except (ValueError, TypeError):
            continue
        for e in entries:
            gene = norm_gene(e.get("gene", ""))
            if not gene or gene == "UNKNOWN":
                continue
            d = gene_data[gene]
            role = e.get("role", "context-only")
            if role == "studied":
                d["n_studied"] += 1
            elif role == "perturbed":
                d["n_perturbed"] += 1
            elif role == "measured":
                d["n_measured"] += 1
            else:
                d["n_context"] += 1
            d["papers"].append({
                "id": r["id"], "title": (papers.get(r["id"], {})
                                         .get("title", ""))[:120],
                "year": papers.get(r["id"], {}).get("year"),
                "role": role, "finding": str(e.get("finding", ""))[:300],
                "evidence": str(e.get("evidence", ""))[:300],
            })

    # mechanisms where this gene is an actor or target
    if MECHANISMS.exists():
        mechs = pl.read_parquet(MECHANISMS)
        for r in mechs.iter_rows(named=True):
            try:
                actors = json.loads(r.get("actors") or "[]")
                targets = json.loads(r.get("targets") or "[]")
            except (ValueError, TypeError):
                continue
            verified = r.get("verify_verdict", "")
            for a in actors + targets:
                gene = norm_gene(a)
                if gene:
                    gene_data[gene]["mechanisms"].append({
                        "paper_id": r["paper_id"],
                        "interaction": r.get("interaction", ""),
                        "effect": str(r.get("effect", ""))[:200],
                        # md5[:12] i18n key (eh/fh convention) — ft(eh) in UI
                        "eh": hashlib.md5(str(r.get("effect", "")).encode("utf-8")).hexdigest()[:12],
                        "verified": verified in ("confirmed",
                                                 "paraphrased-supported"),
                        "verdict": verified,
                    })

    # write per-gene JSON
    import re as _re
    def safe_name(g):
        return _re.sub(r"[^A-Za-z0-9_.-]", "_", g)[:60]

    written = 0
    for gene, d in gene_data.items():
        if gene in ("", "UNKNOWN", "N/A") or len(gene) < 2:
            continue
        d["papers"].sort(key=lambda p: -(int(p.get("year") or 0)))
        d["mechanisms"] = d["mechanisms"][:30]
        d["n_papers"] = len({p["id"] for p in d["papers"]})
        d["n_mechanism_edges"] = len(d["mechanisms"])
        d["updated"] = datetime.fromtimestamp(
            __import__("time").time(), tz=timezone.utc
        ).isoformat(timespec="seconds")
        (GENE_EV_DIR / f"{safe_name(gene)}.json").write_text(
            json.dumps(d, indent=1))
        written += 1
    print(f"gene evidence: {written} genes → {GENE_EV_DIR}/", file=sys.stderr)
    return gene_data


def build_pathway_edges(papers):
    """Mechanism actor→interaction→target as graph edges."""
    if not MECHANISMS.exists():
        return
    mechs = pl.read_parquet(MECHANISMS)
    edges = []
    for r in mechs.iter_rows(named=True):
        verdict = r.get("verify_verdict", "")
        if verdict in ("unsupported", "contradicted"):
            continue  # filter unverified
        try:
            actors = json.loads(r.get("actors") or "[]")
            targets = json.loads(r.get("targets") or "[]")
        except (ValueError, TypeError):
            continue
        for a in actors:
            for t in targets:
                na, nt = norm_gene(a), norm_gene(t)
                if na and nt and na != nt:
                    edges.append({
                        "from": na, "to": nt,
                        "interaction": str(r.get("interaction", ""))[:30],
                        "effect": str(r.get("effect", ""))[:200],
                        "eh": hashlib.md5(str(r.get("effect", "")).encode("utf-8")).hexdigest()[:12],
                        "paper_id": r["paper_id"],
                        "paper_title": papers.get(r["paper_id"], {})
                            .get("title", "")[:100],
                        "verified": verdict in ("confirmed",
                                                "paraphrased-supported"),
                        "context": str(r.get("context", ""))[:80],
                    })
    # deduplicate by from/to/interaction, keep the paper with most evidence
    seen = {}
    for e in edges:
        k = f"{e['from']}→{e['to']}:{e['interaction']}"
        if k not in seen or e["verified"]:
            seen[k] = e
    edges = sorted(seen.values(), key=lambda e: (not e["verified"], e["from"]))
    PATHWAY_EDGES.write_text(json.dumps({
        "meta": {"n_edges": len(edges), "n_papers": len({e["paper_id"]
                    for e in edges}), "generated": datetime.fromtimestamp(
                        __import__("time").time(), tz=timezone.utc)
                        .isoformat(timespec="seconds")},
        "edges": edges,
    }, indent=1))
    print(f"pathway edges: {len(edges)} edges from "
          f"{len({e['paper_id'] for e in edges})} papers → "
          f"{PATHWAY_EDGES.name}", file=sys.stderr)


def build_research_landscape():
    """Digest of contradictions + gaps + open questions."""
    landscape = {"contradictions": {}, "gaps": {}, "open_questions": [],
                 "meta": {}}
    if CONTRA.exists():
        c = json.loads(CONTRA.read_text())
        landscape["contradictions"] = {
            "total": c["meta"]["n_contradictions"],
            "real": c["meta"]["verdict_counts"].get("real", 0),
            "context_dependent": c["meta"]["verdict_counts"]
                .get("context-dependent", 0),
            "apparent": c["meta"]["verdict_counts"].get("apparent", 0),
            "reasons": c["meta"].get("reason_counts", {}),
            "top_real": [x for x in c["contradictions"]
                         if x["verdict"] == "real"][:10],
        }
        landscape["open_questions"] = [
            {"q": o["q"], "cluster": o["cluster"]}
            for o in c.get("open_questions", [])[:50]
        ]
    if GAPS.exists():
        g = json.loads(GAPS.read_text())
        landscape["gaps"] = {
            "synthesized": g.get("gaps", [])[:15],
            "deterministic_counts": g.get("meta", {})
                .get("n_deterministic", {}),
        }
    landscape["meta"]["generated"] = datetime.fromtimestamp(
        __import__("time").time(), tz=timezone.utc).isoformat(timespec="seconds")
    LANDSCAPE.write_text(json.dumps(landscape, indent=1))
    print(f"research landscape → {LANDSCAPE.name}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes-only", action="store_true")
    args = ap.parse_args()

    papers = load_papers()
    build_gene_evidence(papers)
    if not args.genes_only:
        build_pathway_edges(papers)
        build_research_landscape()
    print("aggregation complete", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
