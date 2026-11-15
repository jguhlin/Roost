#!/usr/bin/env python3
"""Roost Research Agent — a pi-like platform for scientific investigation.

Architecture:
  ToolRegistry    declarative tools with JSON schemas, callable by name
  SkillRegistry   reusable investigation patterns (like pi skills)
  CallRecorder    persistent parquet — every tool call from every briefing
  AgentLoop       LLM-directed loop with auto-compact and gap-report fallback

Tools (add new ones by registering):
  search_corpus       extraction tables by gene/species/topic
  query_field         detections + mortality patterns
  get_model           pathway mechanism edges
  search_external     searxng (graceful degradation)
  check_contradictions adjudicated conflicts
  get_paper_detail    paper metadata
  get_gene_evidence   per-gene literature card
  query_species_traits species-level trait lookup
  check_disagreements explicit disagreements between papers

Skills (add new ones by adding to the skills dict):
  gene_deep_dive        all evidence for one gene
  species_comparison    compare 2-5 species on a trait
  contradiction_analysis why two papers disagree
  gap_assessment        what's missing in the field for a topic

Usage:
  # freeform question
  pixi run python scripts/papers/research_agent.py --question "..."

  # use a skill (pre-configured investigation pattern)
  pixi run python scripts/papers/research_agent.py --skill gene_deep_dive --param gene=ANP32A

  # from open questions
  pixi run python scripts/papers/research_agent.py --top-open 5
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

DATA = ROOT / "data" / "papers"
WEB = ROOT / "web" / "public" / "data"
PAPERS_JSON = WEB / "papers.json"
CONTRA = WEB / "papers" / "contradictions.json"
DETECTIONS = WEB / "detections.parquet"
PATHWAY_EDGES = WEB / "pathway_edges.json"
GENE_EV_DIR = WEB / "gene_evidence"
OUT_DIR = WEB / "research_briefings"
CALL_LOG = DATA / "research_agent_calls.parquet"
SEARXNG = "http://localhost:8888/search"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
UA = "Roost-research-agent/3.0"
MAX_ITERATIONS = 12
COMPACT_EVERY = 4


# ============================================================ tool registry ==
class ToolRegistry:
    """Declarative tool definitions. Add new tools by registering.
    Supports aliases for common LLM-invented tool names."""

    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._aliases: dict[str, tuple[str, str]] = {}  # alias -> (real_name, hint)
        self._data = {}
        self._load_data()

    def register_alias(self, alias: str, real_name: str, hint: str = ""):
        self._aliases[alias] = (real_name, hint)

    def _load_data(self):
        self._data["papers"] = {p["id"]: p for p in
                                json.loads(PAPERS_JSON.read_text())["papers"]}
        for name, fname in [
            ("findings", "paper_key_findings.parquet"),
            ("mechanisms", "paper_mechanisms.parquet"),
            ("quantitative", "paper_quantitative.parquet"),
            ("phenotypes", "paper_species_traits.parquet"),
            ("disagreements", "paper_disagreements.parquet"),
        ]:
            f = DATA / fname
            if f.exists():
                self._data[name] = pl.read_parquet(f)
        if CONTRA.exists():
            self._data["contradictions"] = json.loads(CONTRA.read_text())

    def register(self, name: str, description: str, args_schema: dict,
                 handler):
        self._tools[name] = {"description": description,
                             "args": args_schema, "handler": handler}

    def descriptions(self) -> str:
        lines = []
        for name, t in self._tools.items():
            args = ", ".join(f"{k}:{v}" for k, v in t["args"].items())
            lines.append(f"  {name}({args}) — {t['description']}")
        return "\n".join(lines)

    def execute(self, name: str, args: dict) -> list:
        # resolve aliases
        if name in self._aliases:
            real_name, hint = self._aliases[name]
            # inject hint into results so the agent learns
            result = self.execute(real_name, args)
            if isinstance(result, list):
                result = [{"note": f"'{name}' resolved to '{real_name}'. {hint}"}] + result
            return result

        tool = self._tools.get(name)
        if not tool:
            # unknown tool: tell the agent what IS available
            available = "\n".join(f"  {n}: {t['description'][:60]}"
                                  for n, t in self._tools.items())
            return [{"error": f"tool '{name}' not found.",
                     "available_tools": available}]
        try:
            return tool["handler"](**args) or []
        except Exception as e:
            return [{"error": str(e)[:150]}]

    def names(self):
        return list(self._tools.keys())


# ============================================================= tool handlers ==
def _search_corpus(genes=None, species=None, topics=None, limit=15):
    d = _get_data()
    genes = {g.upper() for g in (genes or []) if len(g) > 1}
    species = {s.lower() for s in (species or []) if len(s) > 2}
    topics = {t.lower() for t in (topics or []) if len(t) > 2}
    hits = []
    if "findings" in d:
        for r in d["findings"].iter_rows(named=True):
            text = str(r.get("finding") or r.get("text") or "").lower()
            score = (sum(3 for g in genes if g.lower() in text) +
                     sum(2 for s in species if s in text) +
                     sum(1 for t in topics if t in text))
            if score > 0:
                hits.append((score, r["paper_id"],
                             str(r.get("finding") or r.get("text") or "")[:200]))
    hits.sort(key=lambda h: -h[0])
    return [{"pid": h[1], "text": h[2], "relevance": h[0]}
            for h in hits[:limit]]


def _query_field(species=None):
    species = [s.lower() for s in (species or []) if len(s) > 3]
    out = []
    phen = ROOT / "data" / "phenotype_table.parquet"
    if phen.exists() and species:
        pt = pl.read_parquet(phen)
        for sp in species[:6]:
            m = pt.filter(pl.col("scientific_name").str.to_lowercase()
                          .str.contains(sp, literal=False))
            for r in m.head(3).iter_rows(named=True):
                out.append({"species": r["scientific_name"],
                            "class": r.get("phenotype_class"),
                            "mortality": round(r.get("mortality_rate") or 0, 2),
                            "n_dead": r.get("mortality_count")})
    return out


def _get_model(genes=None):
    genes = {g.upper() for g in (genes or []) if len(g) > 1}
    if not PATHWAY_EDGES.exists():
        return []
    pe = json.loads(PATHWAY_EDGES.read_text())
    return [{"from": e["from"], "to": e["to"],
             "interaction": e["interaction"],
             "paper_id": e.get("paper_id"), "verified": e.get("verified")}
            for e in pe.get("edges", [])
            if e["from"].upper() in genes or e["to"].upper() in genes]


def _find_related(paper_id=None, genes=None, species=None, concepts=None):
    """Find papers related to a given paper or set of entities —
    citation chaining across genes, species, concepts, methods, pathways.
    The 'read deeply, then branch out' tool."""
    d = _get_data()
    scores = {}

    if paper_id:
        # 1. papers sharing gene involvement with this paper
        ev_dir = GENE_EV_DIR
        genes_of_paper = set()
        for f in ev_dir.glob("*.json"):
            ev = json.loads(f.read_text())
            for p in ev.get("papers", []):
                if p.get("id") == paper_id:
                    genes_of_paper.add(f.stem)
                    break
        for gene in genes_of_paper:
            f = ev_dir / f"{gene}.json"
            if f.exists():
                ev = json.loads(f.read_text())
                for p in ev.get("papers", []):
                    if p["id"] != paper_id:
                        scores[p["id"]] = scores.get(p["id"], 0) + 2

        # 2. typed claims entity overlap — genes, species, clades, methods
        tc_file = DATA / "typed_claims.parquet"
        if tc_file.exists():
            tc = pl.read_parquet(tc_file)
            source = tc.filter(pl.col("paper_id") == paper_id)
            if source.height > 0:
                # collect ALL entity types from this paper's claims
                src_entities = set()  # (type, value) tuples
                for r in source.iter_rows(named=True):
                    for col, etype in [("genes", "gene"), ("species", "species"),
                                       ("clades", "clade"), ("methods", "method"),
                                       ("places", "place")]:
                        for v in json.loads(r.get(col) or "[]"):
                            if v:
                                src_entities.add((etype, str(v).lower()))
                # also extract concepts from claim text (multi-word phrases)
                src_text = " ".join(str(r.get("text") or "") for r in source.iter_rows(named=True)).lower()
                for other in tc.filter(pl.col("paper_id") != paper_id).iter_rows(named=True):
                    other_entities = set()
                    other_text = str(other.get("text") or "").lower()
                    for col, etype in [("genes", "gene"), ("species", "species"),
                                       ("clades", "clade"), ("methods", "method"),
                                       ("places", "place")]:
                        for v in json.loads(other.get(col) or "[]"):
                            if v:
                                other_entities.add((etype, str(v).lower()))
                    overlap = len(src_entities & other_entities)
                    if overlap >= 1:
                        scores[other["paper_id"]] = scores.get(other["paper_id"], 0) + overlap * 2
                    # concept overlap: check if source text shares significant phrases
                    # with other text
                    src_words = set(src_text.split())
                    other_words = set(other_text.split())
                    shared_concepts = src_words & other_words - {"the", "a", "an", "in", "of", "and", "to", "with", "for", "is", "are", "was", "by", "that", "this", "which", "from", "at", "or", "as", "on", "it", "be", "not", "have", "has"}
                    if len(shared_concepts) >= 5:
                        scores[other["paper_id"]] = scores.get(other["paper_id"], 0) + 1

        # 3. papers that explicitly disagree with this one
        if "disagreements" in d:
            for r in d["disagreements"].filter(
                    pl.col("paper_id") == paper_id).iter_rows(named=True):
                text = str(r.get("text") or "")
                for pid in d["papers"]:
                    if pid != paper_id and pid.lower() in text.lower():
                        scores[pid] = scores.get(pid, 0) + 3

        # 4. keywords overlap (topical similarity)
        kw_file = DATA / "paper_keywords.parquet"
        if kw_file.exists():
            kw = pl.read_parquet(kw_file)
            src_kw = set(kw.filter(pl.col("paper_id") == paper_id)["keyword"].to_list())
            if src_kw:
                for r in kw.filter(pl.col("paper_id") != paper_id).iter_rows(named=True):
                    if r["keyword"].lower() in src_kw:
                        scores[r["paper_id"]] = scores.get(r["paper_id"], 0) + 1

    # also handle direct gene/concept queries
    if genes:
        for gene in {g.upper() for g in genes if len(g) > 1}:
            f = GENE_EV_DIR / f"{gene}.json"
            if f.exists():
                ev = json.loads(f.read_text())
                for p in ev.get("papers", []):
                    scores[p["id"]] = scores.get(p["id"], 0) + 2

    if concepts:
        # search findings for concept phrases
        if "findings" in d:
            for concept in concepts:
                concept_lower = concept.lower()
                if len(concept_lower) < 3:
                    continue
                for r in d["findings"].iter_rows(named=True):
                    text = str(r.get("finding") or "").lower()
                    if concept_lower in text:
                        scores[r["paper_id"]] = scores.get(r["paper_id"], 0) + 2

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:12]
    return [{"pid": pid, "relevance": score,
             "title": d["papers"].get(pid, {}).get("title", "")[:60],
             "year": d["papers"].get(pid, {}).get("year")}
            for pid, score in ranked if pid in d["papers"]]
    """Search Wikipedia for background/context on a topic."""
    if not query:
        return []
    try:
        url = (f"https://en.wikipedia.org/w/api.php?action=query&list=search&"
               f"srsearch={urllib.parse.quote(query)}&format=json&srlimit=3")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            return [{"title": h.get("title", ""),
                     "snippet": re.sub(r'<[^>]+>', '', h.get("snippet", ""))[:200]}
                    for h in data.get("query", {}).get("search", [])[:3]]
    except Exception:
        return [{"error": "wikipedia unavailable"}]


def _search_wikipedia(query=None):
    """Search Wikipedia for background/context on a topic."""
    if not query:
        return []
    try:
        url = (f"https://en.wikipedia.org/w/api.php?action=query&list=search&"
               f"srsearch={urllib.parse.quote(query)}&format=json&srlimit=3")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            return [{"title": h.get("title", ""),
                     "snippet": re.sub(r'<[^>]+>', '', h.get("snippet", ""))[:200]}
                    for h in data.get("query", {}).get("search", [])[:3]]
    except Exception:
        return [{"error": "wikipedia unavailable"}]


def _search_searxng(query=None):
    """Search the web via searxng for papers/data we don't have."""
    if not query:
        return []
    try:
        url = f"{SEARXNG}?{urllib.parse.urlencode({'q': query, 'format': 'json'})}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            return [{"title": r.get("title", "")[:80],
                     "url": r.get("url", ""),
                     "snippet": r.get("content", "")[:150]}
                    for r in data.get("results", [])[:5]]
    except Exception:
        return [{"error": "searxng unavailable"}]
    if not query:
        return []
    try:
        url = f"{SEARXNG}?{urllib.parse.urlencode({'q': query, 'format': 'json'})}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            dead = data.get("unresponsive_engines", [])
            if sum(1 for e in dead if e and e[0] in
                   ("brave", "duckduckgo", "google cse")) >= 2:
                return [{"error": "engines degraded"}]
            return [{"title": r.get("title", "")[:80],
                     "url": r.get("url", ""),
                     "snippet": r.get("content", "")[:150]}
                    for r in data.get("results", [])[:5]]
    except Exception:
        return [{"error": "searxng unavailable"}]


def _check_contradictions(cluster_key=None):
    d = _get_data()
    if "contradictions" not in d or not cluster_key:
        return []
    return [{"topic": c["topic"][:80], "verdict": c["verdict"],
             "reason": c.get("reason"),
             "explanation": c.get("explanation", "")[:120]}
            for c in d["contradictions"].get("contradictions", [])
            if cluster_key.lower() in (c.get("cluster") or "").lower()][:8]


def _get_paper_detail(paper_id=None):
    d = _get_data()
    p = d["papers"].get(paper_id, {})
    if not p:
        return [{"error": "not found"}]
    return [{"id": paper_id, "title": p.get("title", ""),
             "year": p.get("year"), "journal": p.get("journal", ""),
             "summary": (p.get("summary") or "")[:200]}]


def _get_gene_evidence(gene=None):
    if not gene:
        return []
    f = GENE_EV_DIR / f"{gene}.json"
    if not f.exists():
        return [{"error": f"no evidence for {gene}"}]
    d = json.loads(f.read_text())
    return [{"gene": gene, "n_papers": d.get("n_papers", 0),
             "n_mechanisms": d.get("n_mechanism_edges", 0),
             "top_papers": [{"pid": p["id"], "role": p.get("role"),
                             "finding": p.get("finding", "")[:100]}
                            for p in d.get("papers", [])[:5]]}]


def _search_figure_assets(query=None, limit=None):
    """Search the mirrored open-asset library (12,440 icons/silhouettes/
    illustrations: PhyloPic organisms, Bioicons, Reactome, NIH BioArt, SciDraw,
    Togo, Servier, Health Icons) for figure-ready assets. Every result carries
    license + attribution — safe to embed in figures the agent proposes."""
    if not query:
        return []
    import sqlite3
    db = ROOT / "assets" / "manifest.sqlite"
    if not db.exists():
        return []
    sys.path.insert(0, str(ROOT / "scripts" / "figures"))
    import search_assets as SA
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        expr = SA.fts_expr(query)
        rows = con.execute(
            f"SELECT a.*, bm25(asset_fts) AS rank FROM asset_fts "
            f"JOIN assets a ON a.id = asset_fts.rowid "
            f"WHERE asset_fts MATCH ? "
            f"ORDER BY CASE WHEN a.public_domain=1 OR a.commercial_ok=1 THEN 0 ELSE 1 END, rank "
            f"LIMIT ?", (expr, min(int(limit or 8), 12))).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        out.append({
            "title": r["title"], "source": r["source"], "license": r["license"],
            "author": r["author"], "file": r["file_path"],
            "attribution_required": bool(r["requires_attribution"]),
        })
    return out


def _query_species_traits(species=None):
    if not species:
        return []
    traits = ROOT / "data" / "species_traits.parquet"
    if not traits.exists():
        return []
    st = pl.read_parquet(traits)
    m = st.filter(pl.col("scientific_name").str.to_lowercase()
                  .str.contains(species.lower(), literal=False))
    return [{k: v for k, v in r.items() if v is not None}
            for r in m.head(5).iter_rows(named=True)]


def _check_disagreements(genes=None, topics=None):
    d = _get_data()
    if "disagreements" not in d:
        return []
    hits = []
    for r in d["disagreements"].iter_rows(named=True):
        text = str(r.get("text") or "").lower()
        if any(g.lower() in text for g in (genes or [])) or \
           any(t.lower() in text for t in (topics or [])):
            hits.append({"pid": r["paper_id"],
                         "text": str(r.get("text") or "")[:200]})
    return hits[:10]


# Data singleton (lazy-loaded)
_data_cache = None
def _get_data():
    global _data_cache
    if _data_cache is None:
        _data_cache = {}
        _data_cache["papers"] = {p["id"]: p for p in
                                 json.loads(PAPERS_JSON.read_text())["papers"]}
        for name, fname in [
            ("findings", "paper_key_findings.parquet"),
            ("mechanisms", "paper_mechanisms.parquet"),
            ("quantitative", "paper_quantitative.parquet"),
            ("phenotypes", "paper_species_traits.parquet"),
            ("disagreements", "paper_disagreements.parquet"),
        ]:
            f = DATA / fname
            if f.exists():
                _data_cache[name] = pl.read_parquet(f)
        if CONTRA.exists():
            _data_cache["contradictions"] = json.loads(CONTRA.read_text())
    return _data_cache


# ============================================================= skills =====
SKILLS = {
    # --- INVESTIGATION SKILLS (entry points into the same loop) ---

    "contradiction_investigation": {
        "description": "Why do two findings conflict? Root-cause a literature contradiction",
        "params": {"topic": "The contested claim", "papers": "Paper IDs (optional)"},
        "system_hint": """You are investigating a CONTRADICTION. Follow this protocol:
1. IDENTIFY the exact claims that conflict — what specifically differs?
2. GET both papers' full evidence: methods, species, dose, clade, timing
3. CHECK if it's context-dependent (different species/era/method) or real
4. IF real: what data would resolve it? IF context: map the boundary
5. LOOK for other papers that support each side — who's in which camp?
Start with check_contradictions, then get_paper_detail for each side.""",
    },

    "evidence_synthesis": {
        "description": "What is the totality of evidence on a gene, pathway, or phenomenon?",
        "params": {"topic": "What to synthesise (gene, pathway, or phenomenon)"},
        "system_hint": """You are synthesising EVIDENCE on a topic. Follow this protocol:
1. MAP the landscape: search broadly, then narrow to specifics
2. GATHER all evidence types: findings, mechanisms, phenotypes, field data
3. WEIGH the evidence: which findings are strong (many papers, verified)?
4. IDENTIFY the consensus vs contested areas
5. NOTE what's missing: check open questions and disagreements
Use search_corpus extensively, get_gene_evidence for specific genes,
query_species_traits for phenotypes, check_contradictions for disputes.""",
    },

    "gene_deep_dive": {
        "description": "All evidence for one gene: papers, mechanisms, pathway, phenotypes",
        "params": {"gene": "Gene symbol (e.g. ANP32A, MX1, DDX58)"},
        "system_hint": """You are doing a GENE DEEP-DIVE. Follow this protocol:
1. START with get_gene_evidence for the gene's literature card
2. SEARCH corpus for the gene symbol and its known aliases
3. GET pathway context: what does it interact with? (get_model)
4. CHECK species differences: query_species_traits, query_field
5. FIND contradictions: is its role contested?
6. LOOK for loss-of-function evidence: what happens without it?""",
    },

    "species_comparison": {
        "description": "Compare 2-5 species on a trait (susceptibility, tolerance, etc.)",
        "params": {"species": "Comma-separated species names",
                    "trait": "What to compare"},
        "system_hint": """You are COMPARING SPECIES. Follow this protocol:
1. GET each species' traits (query_species_traits, query_field)
2. SEARCH corpus for each species with the trait
3. CHECK if the trait difference is genetic (search for the gene)
4. LOOK at phenotype data: mortality, outcome, viral load
5. IDENTIFY the mechanistic basis for the difference""",
    },

    "gap_assessment": {
        "description": "What's missing in the research on a topic?",
        "params": {"topic": "The topic to assess"},
        "system_hint": """You are assessing GAPS. Follow this protocol:
1. MAP what IS known (broad corpus search)
2. MAP what ISN'T known (check open questions, disagreements)
3. IDENTIFY coverage gaps: which species/genes/geographies are unstudied?
4. RANK the gaps by scientific value
5. PROPOSE specific studies that would fill each gap
If evidence is thin, produce a gap report — that IS the finding.""",
    },

    "hypothesis_generation": {
        "description": "Given existing evidence, what should we test next?",
        "params": {"topic": "The topic to generate hypotheses for"},
        "system_hint": """You are generating HYPOTHESES. Follow this protocol:
1. GATHER all evidence on the topic
2. IDENTIFY patterns and anomalies in the data
3. PROPOSE 2-4 specific, testable hypotheses with predictions
4. FOR each: what evidence supports it? What would falsify it?
5. RANK by testability and scientific value
Each hypothesis must have: a prediction, evidence for, evidence against,
and a proposed test.""",
    },

    "outbreak_investigation": {
        "description": "What happened at a specific outbreak site or event?",
        "params": {"location": "Geographic location or event name"},
        "system_hint": """You are investigating an OUTBREAK. Follow this protocol:
1. SEARCH for papers mentioning the location/event
2. QUERY field data for the affected species and timeframe
3. ESTABLISH the timeline: when, where, what species, how many died
4. IDENTIFY the viral genotype/clade involved
5. LOOK for follow-up studies on the outbreak's aftermath""",
    },
}


# =========================================================== call recorder ==
class CallRecorder:
    """Persistent tool-call history in parquet — queryable across briefings."""

    def __init__(self):
        self.records = []

    def record(self, briefing_slug, iteration, tool, args, result, duration_ms):
        self.records.append({
            "briefing": briefing_slug,
            "iteration": iteration,
            "tool": tool,
            "args": json.dumps(args, default=str)[:500],
            "n_results": len(result) if isinstance(result, list) else 1,
            "duration_ms": duration_ms,
            "timestamp": datetime.fromtimestamp(
                time.time(), tz=timezone.utc).isoformat(timespec="seconds"),
        })

    def flush(self):
        if not self.records:
            return
        fresh = pl.DataFrame(self.records, infer_schema_length=None)
        # cast to string to match schema across runs (iteration is now "round-iter")
        for col in ("iteration", "duration_ms", "n_results"):
            if col in fresh.columns:
                fresh = fresh.with_columns(pl.col(col).cast(pl.Utf8, strict=False))
        if CALL_LOG.exists():
            old = pl.read_parquet(CALL_LOG)
            for col in ("iteration", "duration_ms", "n_results"):
                if col in old.columns:
                    old = old.with_columns(pl.col(col).cast(pl.Utf8, strict=False))
            fresh = pl.concat([old, fresh], how="diagonal")
        fresh.write_parquet(CALL_LOG)
        self.records = []


# ============================================================ agent loop ====
async def agent_loop(client, question, registry, recorder, slug,
                     max_iterations=MAX_ITERATIONS, system_hint=None):
    """Full agentic loop: investigate -> draft -> self-assess -> refine or done.

    The agent critiques its own synthesis and decides whether to do another
    targeted investigation round or declare completion. Meta-questions that
    arise during synthesis feed back into the next investigation pass.
    """
    accumulated = []
    summaries = []
    meta_questions = []
    refinement_rounds = 0
    max_refinements = 3

    methodology = (
        "METHODOLOGY:\n"
        "1. UNDERSTAND the question and its entities\n"
        "2. SEARCH broadly, then narrow\n"
        "3. CHAIN: when you find relevant papers, use find_related to discover\n"
        "   connected papers (shared genes, citations, disagreements)\n"
        "4. EVALUATE: consistent? contradictory? sufficient?\n"
        "5. If insufficient: different terms, different tools, or find_related\n"
        "6. If contradictory: investigate why\n"
        "7. SYNTHESIZE when confident\n"
    )

    def build_prompt(state, recent, hints=None):
        tools_desc = registry.descriptions()
        hint = f"\nFOCUS: {system_hint}" if system_hint else ""
        meta = ""
        if hints:
            meta = "\nQUESTIONS FROM YOUR LAST SYNTHESIS (target these):\n" + \
                   "\n".join(f"  - {h}" for h in hints[:3])
        return f"""You are a research agent investigating:
QUESTION: {question}{hint}{meta}

{methodology}
Available tools:
{tools_desc}
  synthesize() — write the briefing

CURRENT UNDERSTANDING:
{state}

RECENT RESULTS:
{recent}

Next action? Return JSON: {{"action": "tool_name", "args": {{...}}, "reasoning": "why"}}"""

    async def run_investigation(hints=None):
        """One pass of the tool-calling loop."""
        nonlocal accumulated, summaries
        for iteration in range(max_iterations):
            if iteration > 0 and iteration % COMPACT_EVERY == 0:
                comp = await llm_json(client,
                    f"Summarise key findings into 5-8 bullets. Keep citations.\n"
                    f"EVIDENCE: {json.dumps(accumulated[-COMPACT_EVERY*3:], default=str)[:12000]}",
                    temp=0.1)
                if comp:
                    summaries.append(str(comp)[:2000])
                accumulated = accumulated[-5:]

            state = "\n".join(summaries[-2:]) if summaries else "(starting)"
            recent = json.dumps(accumulated[-3:], default=str)[:4000] if accumulated else "(none)"
            prompt = build_prompt(state, recent, hints)
            decision = await llm_json(client, prompt, 0.2)
            action = decision.get("action", "")
            args = decision.get("args", {})
            reasoning = decision.get("reasoning", "")
            print(f"  [{iteration + 1}] {action}: {reasoning[:55]}", file=sys.stderr)
            if action == "synthesize":
                break
            t0 = time.time()
            result = registry.execute(action, args)
            duration = int((time.time() - t0) * 1000)
            recorder.record(slug, f"{refinement_rounds}-{iteration + 1}",
                            action, args, result, duration)
            accumulated.append({"tool": action, "result": result})
            print(f"      -> {len(result) if isinstance(result, list) else 1} results ({duration}ms)",
                  file=sys.stderr)

    # ============ PHASE 1: INVESTIGATE ============
    print(f"  PHASE 1: investigate", file=sys.stderr)
    await run_investigation()

    # ============ PHASE 2-4: DRAFT -> ASSESS -> REFINE ============
    while refinement_rounds <= max_refinements:
        label = "initial" if refinement_rounds == 0 else f"refinement {refinement_rounds}"
        print(f"  PHASE 2: synthesize ({label})", file=sys.stderr)

        draft = await synthesize(client, question, accumulated, summaries)
        if not draft or "sections" not in draft:
            draft = await produce_gap_report(client, question, accumulated, registry)
            draft["_gap_report"] = True
            # still run self-assessment — maybe a refinement would find more
            print(f"  (gap report — still assessing)", file=sys.stderr)

        # ============ PHASE 3: SELF-ASSESS ============
        print(f"  PHASE 3: self-assess", file=sys.stderr)
        assessment = await self_assess(client, question, draft)
        verdict = assessment.get("decision", "done")
        gaps = assessment.get("missing", [])
        new_q = assessment.get("questions_raised", [])
        confidence = assessment.get("confidence", "medium")
        print(f"      verdict: {verdict} ({confidence})", file=sys.stderr)
        if gaps:
            print(f"      gaps: {gaps[:2]}", file=sys.stderr)
        if new_q:
            print(f"      new questions: {new_q[:2]}", file=sys.stderr)

        meta_questions.extend(new_q)

        # ============ PHASE 4: DECIDE ============
        if verdict == "done" or refinement_rounds >= max_refinements:
            print(f"  DONE after {refinement_rounds} refinements (confidence: {confidence})",
                  file=sys.stderr)
            draft["meta_questions"] = meta_questions
            draft["refinement_rounds"] = refinement_rounds
            draft["self_assessment"] = {
                "gaps_identified": gaps,
                "questions_raised": meta_questions,
                "confidence": confidence,
                "reasoning": assessment.get("reasoning", ""),
            }
            return draft, accumulated, summaries

        # REFINEMENT: target the gaps with specific tool calls
        refinement_rounds += 1
        print(f"  PHASE 4: refine (round {refinement_rounds})", file=sys.stderr)
        # only gaps, not meta-questions that are their own briefing
        gap_strings = [g if isinstance(g, str) else g.get("question", str(g))
                       for g in gaps]
        meta_hints = gap_strings[:3]

        for gap in meta_hints:
            print(f"      targeting: {gap[:55]}", file=sys.stderr)
            gap_prompt = f"""A gap in a research briefing:
GAP: {gap}
QUESTION: {question}

Which tool would best fill this? Return JSON:
{{"action": "tool_name", "args": {{...}}}}"""
            gap_decision = await llm_json(client, gap_prompt, 0.2)
            gap_action = gap_decision.get("action", "")
            gap_args = gap_decision.get("args", {})
            if gap_action and gap_action != "synthesize":
                t0 = time.time()
                result = registry.execute(gap_action, gap_args)
                duration = int((time.time() - t0) * 1000)
                recorder.record(slug, f"refine-{refinement_rounds}",
                                gap_action, gap_args, result, duration)
                accumulated.append({"tool": gap_action, "result": result,
                                    "targeting": gap[:60]})
                print(f"      -> {gap_action}: "
                      f"{len(result) if isinstance(result, list) else 1} results",
                      file=sys.stderr)

        # also run a short investigation pass targeting the gaps
        await run_investigation(hints=meta_hints)

    draft["meta_questions"] = meta_questions
    draft["refinement_rounds"] = refinement_rounds
    return draft, accumulated, summaries


async def self_assess(client, question, draft):
    """Meta-cognitive: critique own work, classify meta-questions, decide."""
    draft_text = json.dumps({
        "title": draft.get("title"),
        "summary": draft.get("summary"),
        "section_headings": [s.get("heading") for s in draft.get("sections", [])],
        "n_hypotheses": len(draft.get("hypotheses", [])),
    }, default=str)[:3000]

    prompt = f"""You are reviewing your own research briefing. Be critical but fair.

QUESTION: {question}
YOUR DRAFT: {draft_text}

Evaluate:
1. What IMPORTANT aspects are NOT covered?
2. What questions AROSE during synthesis that you did not answer?
3. For each question: does it BELONG in this report (sub-detail of the
   main question), or is it its OWN research question (worth a separate
   briefing)?
4. Confidence? (high/medium/low)
5. Should you refine, or is this sufficient?

"Nah, this is great and addresses the question sufficiently" is a VALID
answer. "Refine" means there are clear gaps that more tool calls could
fill — not perfectionism.

Return JSON:
{{"decision": "done|refine",
  "confidence": "high|medium|low",
  "missing": ["specific gap 1", "gap 2"],
  "questions_raised": [
    {{"question": "...",
     "scope": "this_report|own_briefing",
     "reasoning": "why it belongs here or deserves its own investigation"}}
  ],
  "reasoning": "why"}}"""

    result = await llm_json(client, prompt, 0.2)
    # normalise: if questions_raised is a list of strings, wrap them
    if isinstance(result.get("questions_raised"), list):
        normalised = []
        for q in result["questions_raised"]:
            if isinstance(q, str):
                normalised.append({"question": q, "scope": "own_briefing",
                                   "reasoning": ""})
            elif isinstance(q, dict):
                normalised.append(q)
        result["questions_raised"] = normalised
    return result


async def llm_json(client, prompt, temp):
    out = await call_llm(client, prompt, temp, BASE, MODEL)
    return parse_json_response(out) or {}


# =========================================================== synthesis ====
async def synthesize(client, question, evidence, summaries):
    parts = []
    for e in evidence:
        tool = e["tool"]
        result = e["result"]
        if isinstance(result, list):
            parts.append(f"[{tool}]")
            for r in result[:8]:
                parts.append(f"  {json.dumps(r, default=str)[:150]}")
    if summaries:
        parts.append(f"\nCOMPACTED FINDINGS:\n" + "\n".join(summaries))
    evidence_text = "\n".join(parts)[:20000]

    prompt1 = f"""Write a research briefing on this question.

RULES FOR THE BODY TEXT:
- Write clean, flowing prose — NEVER mention tool names, tool metadata,
  query parameters, hit counts, or evidence registry details
- Cite papers naturally in the text as [paper_id] (these become links)
- Do NOT label sources as (corpus), (field), (model) in the body —
  write as if YOU are the expert citing the literature
- Distinguish species, clade, and dose context in the prose itself

QUESTION: {question}

EVIDENCE (for your reference only — do not reproduce tool output verbatim):
{evidence_text}

Return JSON: {{"title": "...", "summary": "3-4 sentences",
 "sections": [{{"heading": "...", "body": "5-8 sentences citing [paper_id] naturally"}}],
 "unresolved": ["..."], "data_gaps": ["..."]}}"""

    prompt2 = f"""Given this question and evidence, propose hypotheses and a research plan.

QUESTION: {question}
EVIDENCE: {evidence_text[:10000]}

Return JSON: {{"hypotheses": [{{"hypothesis": "...", "prediction": "...",
 "evidence_for": ["[pid] X"], "evidence_against": ["[pid] Y"],
 "test": "...", "confidence": "high|medium|low"}}],
 "research_plan": [{{"study": "...", "method": "...", "model_system": "...",
 "feasibility": "high|medium|low", "priority": 1}}],
 "figure_proposals": [{{"kind": "gap-map|diagram|data-figure",
   "caption": "one-sentence takeaway",
   "title": "figure title",
   "note_box": "only for gap-maps: the one-line insight",
   "columns": ["label per column — the LAST column is where evidence is missing"],
   "rows": ["label per row — evidence types"],
   "cells": [[2, 1, 0], ...]}}]}}
FIGURE PROPOSALS (0-2 per briefing): a gap-map rates each column×row cell
2 (direct evidence found), 1 (adjacent/partial), 0 (nothing found) from the
evidence above; keep it 2-4 columns × 2-4 rows. Propose a diagram or
data-figure instead when a mechanism or numeric contrast — not an evidence
map — is the story. These are rendered automatically and attached to the
published briefing."""

    r1 = await llm_json(client, prompt1, 0.3)
    r2 = await llm_json(client, prompt2, 0.3)
    if r1:
        r1.update({k: v for k, v in (r2 or {}).items() if v})
    return r1


async def produce_gap_report(client, question, evidence, registry):
    """When there isn't enough evidence — still a reportable finding."""
    searches = [{"tool": e["tool"], "results": len(e["result"])}
                for e in evidence]
    prompt = f"""A research agent investigated this question but found
INSUFFICIENT EVIDENCE. Write a gap report — what was searched, found, and what's missing.

QUESTION: {question}
SEARCHES MADE: {json.dumps(searches)}
PARTIAL RESULTS: {json.dumps([e['result'][:3] for e in evidence[:5]], default=str)[:5000]}

Return JSON: {{"title": "...", "summary": "insufficient evidence because…",
 "sections": [{{"heading": "...", "body": "..."}}],
 "unresolved": ["..."], "data_gaps": ["..."],
 "figure_proposals": [{{"kind": "gap-map", "caption": "one-sentence takeaway",
   "title": "figure title", "note_box": "the one-line insight",
   "columns": ["label per column — the LAST is where evidence is missing"],
   "rows": ["label per row — evidence types"],
   "cells": [[2, 1, 0], ...]}}]}}
A gap report should almost always propose ONE gap-map figure: rate each
column×row 2 (direct evidence found), 1 (adjacent/partial), 0 (nothing) from
the partial results above; 2-4 columns × 2-4 rows; it is rendered
automatically and attached to the published report."""
    result = await llm_json(client, prompt, 0.3)
    if result and result.get("sections"):
        return result
    return {"title": f"Evidence gap: {question[:50]}",
            "summary": f"Agent made {len(evidence)} queries; insufficient evidence.",
            "sections": [{"heading": "Gap", "body": "Corpus lacks sufficient data."}],
            "unresolved": [question], "data_gaps": ["Need more papers on this topic"]}


# ============================================================ pipeline ====
def build_registry():
    registry = ToolRegistry()
    registry.register("search_corpus",
        "Search extraction tables (findings, mechanisms, quantitative)",
        {"genes": "list[str]", "species": "list[str]", "topics": "list[str]"},
        _search_corpus)
    registry.register("query_field",
        "Field mortality patterns from surveillance",
        {"species": "list[str]"}, _query_field)
    registry.register("get_model",
        "Pathway mechanism edges for genes",
        {"genes": "list[str]"}, _get_model)
    registry.register("search_external",
        "Web search for papers/data we don't have",
        {"query": "str"}, _search_searxng)
    registry.register("check_contradictions",
        "Adjudicated literature contradictions on a topic",
        {"cluster_key": "str"}, _check_contradictions)
    registry.register("get_paper_detail",
        "Full metadata for a specific paper",
        {"paper_id": "str"}, _get_paper_detail)
    registry.register("get_gene_evidence",
        "Per-gene literature card (papers, mechanisms, roles)",
        {"gene": "str"}, _get_gene_evidence)
    registry.register("query_species_traits",
        "Species-level trait lookup (tolerance, mortality, susceptibility)",
        {"species": "str"}, _query_species_traits)
    registry.register("search_figure_assets",
        "Search the mirrored open-asset library (12,440 icons/silhouettes: organisms, "
        "viruses, cells, lab equipment) for figure-ready assets with licenses. "
        "Use when proposing figures for this briefing.",
        {"query": "str", "limit": "int (optional)"},
        _search_figure_assets)
    registry.register("search_wikipedia",
        "Background and context from Wikipedia",
        {"query": "str"}, _search_wikipedia)
    registry.register("search_web",
        "Web search via searxng for papers we don't have",
        {"query": "str"}, _search_searxng)
    registry.register("find_related",
        "Citation chaining: find papers connected to a paper, gene, species, or concept. "
        "Searches shared genes, species, clades, methods, concepts, keywords, disagreements. "
        "Use after finding a relevant paper to discover connected work.",
        {"paper_id": "str (optional)", "genes": "list[str] (optional)",
         "concepts": "list[str] — concepts/methods/pathways (e.g. 'cytokine storm', 'sialic acid receptor')"},
        _find_related)
    # aliases for tool names the LLM commonly invents — maps to real tools
    registry.register_alias("pubmed_search", "search_web",
        hint="use search_web with 'site:pubmed.ncbi.nlm.nih.gov' in query")
    registry.register_alias("search_papers", "search_corpus")
    registry.register_alias("search_academic_literature", "search_web")
    registry.register_alias("gene_evidence_summary", "get_gene_evidence")
    registry.register_alias("systematic_literature_search", "search_corpus")
    registry.register_alias("study_methodology_comparison", "search_corpus")
    registry.register_alias("experimental_infection_study", "search_corpus")
    registry.register("check_disagreements",
        "Explicit disagreements between papers",
        {"genes": "list[str]", "topics": "list[str]"}, _check_disagreements)
    return registry


async def build_briefing(client, question, registry, recorder,
                         use_external=True, system_hint=None,
                         skill_name=None, skill_params=None):
    if skill_name and skill_params:
        vals = "-".join(v.replace(" ", "-") for v in skill_params.values())[:30]
        slug = f"{vals}-{skill_name.replace('_', '-')[:25]}"
    else:
        s = re.sub(r"[^a-z0-9\s-]", "", question.lower())[:70].strip()
        if len(s) == 70:
            last_space = s.rfind(" ")
            if last_space > 30:
                s = s[:last_space]
        slug = re.sub(r"\s+", "-", s.strip())
    print(f"\n=== {question[:70]}", file=sys.stderr)

    if not use_external:
        # remove external search from available tools
        pass  # the LLM just won't use it if searxng is degraded

    # agent_loop now includes synthesize + self-assess + refine internally
    briefing, evidence, summaries = await agent_loop(
        client, question, registry, recorder, slug,
        system_hint=system_hint)
    print(f"  agent completed: {len(evidence)} tool calls, "
          f"{briefing.get('refinement_rounds', 0)} refinements, "
          f"confidence {briefing.get('self_assessment', {}).get('confidence', '?')}",
          file=sys.stderr)

    if not briefing or "sections" not in briefing:
        briefing = await produce_gap_report(client, question, evidence, registry)
        briefing["_gap_report"] = True

    briefing["slug"] = slug
    briefing["question"] = question
    briefing["generated"] = datetime.fromtimestamp(
        time.time(), tz=timezone.utc).isoformat(timespec="seconds")
    briefing["agent_trace"] = {
        "tool_calls": recorder.records,
        "n_iterations": len(evidence),
        "pipeline": "v3 (tool registry + skills + call recorder)",
    }
    return briefing


async def main_async(args):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry = build_registry()
    recorder = CallRecorder()

    questions = []
    hints = {}

    if args.autonomous:
        # pick top-scored questions from the scoring pipeline, SKIPPING ones
        # that already have a recent briefing (dedup — regenerate explicitly
        # by re-asking the question instead)
        scored = DATA / "scored_questions.parquet"
        if not scored.exists():
            print("run scripts/papers/score_open_questions.py first", file=sys.stderr)
            return 1
        df = pl.read_parquet(scored).filter(pl.col("combined").is_not_null())

        def existing_recent(q: str) -> str | None:
            """Return the slug of a briefing covering this question, if recent."""
            import datetime as _dt
            ql = {w for w in re.split(r"[^a-z0-9]+", q.lower()) if len(w) > 4}
            cutoff = (_dt.datetime.now(_dt.timezone.utc)
                      - _dt.timedelta(days=args.autonomous_fresh_days)).isoformat()
            for f in (OUT_DIR).glob("*.json"):
                if f.name == "index.json":
                    continue
                try:
                    b = json.loads(f.read_text())
                except json.JSONDecodeError:
                    continue
                if (b.get("generated") or "") < cutoff:
                    continue
                bl = {w for w in re.split(r"[^a-z0-9]+",
                                          (b.get("question") or "").lower()) if len(w) > 4}
                if ql and bl and len(ql & bl) / max(len(ql | bl), 1) >= 0.55:
                    return b.get("slug")
            return None

        questions: list[str] = []
        skipped = 0
        for r in df.sort("combined", descending=True).iter_rows(named=True):
            if len(questions) >= args.autonomous:
                break
            dup = existing_recent(r["question"])
            if dup:
                skipped += 1
                print(f"  skip (recent briefing: {dup[:44]}) {r['question'][:48]}",
                      file=sys.stderr)
                continue
            questions.append(r["question"])
        print(f"autonomous: picked {len(questions)} top-scored questions "
              f"({skipped} skipped as recently briefed)", file=sys.stderr)
        for q in questions:
            print(f"  {q[:70]}", file=sys.stderr)

    elif args.skill:
        skill = SKILLS.get(args.skill)
        if not skill:
            print(f"unknown skill: {args.skill}", file=sys.stderr)
            return 1
        # build question from skill params
        params = dict(p.split("=", 1) for p in (args.params or []).split(";")
                      if "=" in p)
        question = f"{skill['description']}"
        for k, v in params.items():
            question += f" — {k}: {v}"
        questions = [question]
        hints[question] = skill["system_hint"]
    elif args.question:
        questions = [args.question]
    elif args.top_open and CONTRA.exists():
        d = json.loads(CONTRA.read_text())
        questions = [q["q"] for q in d.get("open_questions", [])[:args.top_open]]

    if not questions:
        print("no questions", file=sys.stderr)
        return 1

    print(f"building {len(questions)} briefings "
          f"(tools: {', '.join(registry.names())})", file=sys.stderr)

    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0)) as client:
        for q in questions:
            b = await build_briefing(client, q, registry, recorder,
                                     use_external=not args.no_external,
                                     system_hint=hints.get(q),
                                     skill_name=args.skill,
                                     skill_params=params if args.skill else None)
            if b:
                out = OUT_DIR / f"{b['slug']}.json"
                out.write_text(json.dumps(b, indent=1))
                print(f"  ✓ {b['slug']}.json", file=sys.stderr)
            else:
                print(f"  ✗ failed", file=sys.stderr)

    recorder.flush()

    # ---- sub-briefing spawning ----
    if args.spawn_subbriefs:
        print(f"\n=== SPAWNING SUB-BRIEFINGS", file=sys.stderr)
        sub_budget = 0
        for q in questions:
            slug = re.sub(r"\s+", "-",
                re.sub(r"[^a-z0-9\s-]", "", q.lower())[:60].strip())
            bf_path = OUT_DIR / f"{slug}.json"
            if not bf_path.exists():
                continue
            bf = json.loads(bf_path.read_text())
            for mq in bf.get("meta_questions", []):
                if isinstance(mq, dict) and mq.get("scope") == "own_briefing":
                    sub_q = mq["question"]
                    if len(sub_q) < 15:
                        continue
                    sub_budget += 1
                    if sub_budget > 3:  # cap sub-briefings
                        break
                    print(f"  sub-briefing: {sub_q[:60]}…", file=sys.stderr)
                    sub_b = await build_briefing(
                        client, sub_q, registry, recorder,
                        use_external=not args.no_external,
                        skill_name=None, skill_params=None)
                    if sub_b:
                        sub_b["_parent"] = slug
                        sub_out = OUT_DIR / f"{sub_b['slug']}.json"
                        sub_out.write_text(json.dumps(sub_b, indent=1))
                        print(f"    ✓ {sub_b['slug']}", file=sys.stderr)
        recorder.flush()

    # ---- paper discovery ----
    if args.discover_papers:
        print(f"\n=== PAPER DISCOVERY", file=sys.stderr)
        disc_file = DATA / "discovered_papers.jsonl"
        our_titles = {p.get("title", "").lower()[:60]
                      for p in json.loads(PAPERS_JSON.read_text())["papers"]}
        discovered = []
        for e in recorder.records:
            if e.get("tool") not in ("search_web", "search_external"):
                continue
            args_str = e.get("args", "")
            try:
                call_args = json.loads(args_str)
            except (ValueError, TypeError):
                continue
            query = call_args.get("query", "")
            if not query:
                continue
            results = _search_searxng(query)
            for r in results:
                if isinstance(r, dict) and r.get("title"):
                    title = r["title"].lower()[:60]
                    if title not in our_titles and title not in [d["title"][:60].lower() for d in discovered]:
                        discovered.append({
                            "title": r["title"][:120],
                            "url": r.get("url", ""),
                            "snippet": r.get("snippet", "")[:150],
                            "found_during": args_str[:60],
                            "discovered_at": datetime.fromtimestamp(
                                __import__("time").time(), tz=timezone.utc
                            ).isoformat(timespec="seconds"),
                        })
        if discovered:
            with disc_file.open("a") as f:
                for d in discovered:
                    f.write(json.dumps(d) + "\n")
            print(f"  discovered {len(discovered)} papers we don't have "
                  f"→ {disc_file.name}", file=sys.stderr)
            for d in discovered[:3]:
                print(f"    {d['title'][:50]}…", file=sys.stderr)
        else:
            print(f"  no novel papers discovered", file=sys.stderr)

    # rebuild index
    idx = []
    for f in sorted(OUT_DIR.glob("*.json")):
        if f.name == "index.json":
            continue
        b = json.loads(f.read_text())
        idx.append({"slug": b.get("slug", f.stem),
                    "title": b.get("title", f.stem),
                    "summary": b.get("summary", ""),
                    "generated": b.get("generated", ""),
                    "gap_report": bool(b.get("_gap_report")),
                    "hypotheses": b.get("hypotheses", []),
                    "research_plan": b.get("research_plan", []),
                    # md5[:12] i18n keys (eh/fh convention) — Landscape.svelte
                    # translates briefing titles/summaries via ft().
                    "th": hashlib.md5(b.get("title", "").encode("utf-8")).hexdigest()[:12],
                    "sh": hashlib.md5(b.get("summary", "").encode("utf-8")).hexdigest()[:12]})
    idx.sort(key=lambda e: e.get("generated", ""), reverse=True)
    (OUT_DIR / "index.json").write_text(json.dumps(idx, indent=1))
    print(f"\n{len(idx)} briefings indexed", file=sys.stderr)

    print(f"\ncall history: {CALL_LOG.name}", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question")
    ap.add_argument("--skill", choices=list(SKILLS.keys()))
    ap.add_argument("--params", help="skill params as key=value;key=value")
    ap.add_argument("--top-open", type=int)
    ap.add_argument("--autonomous", type=int, metavar="N",
                    help="autonomously pick and investigate the top N scored questions")
    ap.add_argument("--autonomous-fresh-days", type=int, default=14,
                    help="briefings younger than this many days count as covering "
                         "their question (autonomous picker skips them)")
    ap.add_argument("--spawn-subbriefs", action="store_true",
                    help="auto-investigate meta-questions marked own_briefing")
    ap.add_argument("--discover-papers", action="store_true",
                    help="log papers found via web search for intake")
    ap.add_argument("--no-external", action="store_true")
    args = ap.parse_args()
    if not any([args.question, args.skill, args.top_open, args.autonomous]):
        ap.error("specify --question, --skill, --top-open, or --autonomous")
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
