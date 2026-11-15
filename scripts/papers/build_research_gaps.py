#!/usr/bin/env python3
"""Research-gap detection — deterministic coverage matrix + one LLM synthesis.

Gap detection is primarily a COVERAGE question, answerable without the LLM:
build sparse matrices (topic × host-group, topic × geography, topic ×
clade), find empty cells whose row and column marginals are both large
("serology×raptors = 0 papers while each side is well-studied"), then ONE
LLM call digests the deterministic candidates + the adjudication's open
questions into a ranked, rationalized gap list.

Outputs: data/papers/research_gaps.json (internal)
Run:  pixi run python scripts/papers/build_research_gaps.py
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

KEYWORDS = ROOT / "data" / "papers" / "paper_keywords.parquet"
EXTRAS = ROOT / "data" / "papers" / "paper_extras.parquet"
TRAITS = ROOT / "data" / "papers" / "paper_species_traits.parquet"
PAPER_DB = ROOT / "data" / "papers" / "paper_db.parquet"
SPECIES_TABLE = ROOT / "data" / "species_table.parquet"
VERDICTS = ROOT / "data" / "papers" / "cluster_verdicts.parquet"
OUT = ROOT / "data" / "papers" / "research_gaps.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

# host-group buckets from avian order
ORDER_GROUPS = {
    "Anseriformes": "waterfowl", "Galliformes": "poultry/gamebirds",
    "Charadriiformes": "shorebirds/gulls", "Suliformes": "seabirds",
    "Procellariiformes": "seabirds", "Sphenisciformes": "penguins",
    "Falconiformes": "raptors", "Accipitriformes": "raptors",
    "Strigiformes": "raptors", "Passeriformes": "passerines",
    "Columbiformes": "doves/pigeons", "Gruiformes": "rails/cranes",
    "Pelecaniformes": "wading birds", "Ciconiiformes": "wading birds",
    "Phoenicopteriformes": "wading birds", "Carnivora": "mammals-carnivore",
    "Cetartiodactyla": "mammals-ungulate", "Rodentia": "mammals-rodent",
    "Primates": "mammals-primate", "Chiroptera": "bats",
    "Perissodactyla": "mammals-ungulate", "Afrosoricida": "mammals-other",
}


def matrix_gaps(rows: list[tuple], min_marginal: int = 6, top: int = 40):
    """rows: (paper_id, dim_a, dim_b). Empty cells with big marginals."""
    cell = defaultdict(set)
    pa, pb = defaultdict(set), defaultdict(set)
    for pid, a, b in rows:
        cell[(a, b)].add(pid)
        pa[a].add(pid)
        pb[b].add(pid)
    gaps = []
    for a in sorted(pa):
        for b in sorted(pb):
            if (a, b) not in cell and len(pa[a]) >= min_marginal \
                    and len(pb[b]) >= min_marginal:
                gaps.append({"a": a, "b": b,
                             "a_papers": len(pa[a]), "b_papers": len(pb[b]),
                             "score": min(len(pa[a]), len(pb[b]))})
    gaps.sort(key=lambda g: -g["score"])
    return gaps[:top], {f"{a}×{b}": len(p) for (a, b), p in cell.items()}


def main() -> int:
    kw = pl.read_parquet(KEYWORDS)
    extras = pl.read_parquet(EXTRAS).select(
        ["id", "study_type", "host_taxa", "geography", "summary"])
    meta = {r["id"]: r for r in extras.iter_rows(named=True)}

    # topic per paper = primary study_type + top generated keyword
    topic_by = {}
    for r in kw.filter(pl.col("origin") == "generated").iter_rows(named=True):
        topic_by.setdefault(r["paper_id"], []).append(r["keyword"].lower())
    def topic(pid):
        st = meta.get(pid, {}).get("study_type") or []
        primary = st[0] if isinstance(st, list) and st else "other"
        return primary

    # host group per paper
    host_by = defaultdict(set)
    for pid, m in meta.items():
        ht = m.get("host_taxa") or ""
        if ht and ht != "other":
            host_by[pid].add(ht.replace(" birds", ""))
    if TRAITS.exists():
        st_tbl = pl.read_parquet(SPECIES_TABLE).select(
            ["scientific_name", "order"])
        order_by = {r["scientific_name"]: r["order"]
                    for r in st_tbl.iter_rows(named=True)}
        for r in pl.read_parquet(TRAITS).iter_rows(named=True):
            sp = r.get("species_norm")
            if sp and sp in order_by:
                g = ORDER_GROUPS.get(order_by[sp])
                if g:
                    host_by[r["paper_id"]].add(g)

    # geography + clades
    geo_by = defaultdict(set)
    for pid, m in meta.items():
        try:
            for c in (json.loads(m.get("geography") or "{}")
                      .get("countries") or [])[:5]:
                geo_by[pid].add(c["name"])
        except Exception:
            pass
    clade_by = defaultdict(set)
    if PAPER_DB.exists():
        for r in pl.read_parquet(PAPER_DB).iter_rows(named=True):
            try:
                for v in json.loads(r.get("strains") or "{}"):
                    if "2.3" in v or v.startswith("H"):
                        clade_by[r["id"]].add(v)
            except Exception:
                pass

    # build gap matrices
    out = {"deterministic_gaps": {}, "matrices": {}}
    for name, dim in (("host", host_by), ("geography", geo_by),
                      ("clade", clade_by)):
        rows = [(pid, topic(pid), v)
                for pid in set(meta) & dim_set(dim)
                for v in dim[pid]]
        gaps, cells = matrix_gaps(rows)
        out["deterministic_gaps"][name] = gaps
        out["matrices"][name] = dict(list(cells.items())[:400])

    # open questions digest from adjudication
    oqs = []
    if VERDICTS.exists():
        for r in pl.read_parquet(VERDICTS).iter_rows(named=True):
            for q in json.loads(r.get("open_questions") or "[]")[:3]:
                if isinstance(q, str) and len(q) > 20:
                    oqs.append({"cluster": r["cluster"], "q": q[:250]})
    out["open_questions_sample"] = oqs[:60]

    # ONE synthesis call
    digest = json.dumps({
        "deterministic_gaps": {k: v[:15] for k, v in
                               out["deterministic_gaps"].items()},
        "open_questions": [o["q"] for o in oqs[:30]],
    }, indent=1)[:14000]

    async def synth():
        prompt = f"""You are identifying RESEARCH GAPS in the avian-influenza
literature for a host-factor database. Below: (a) deterministic coverage
gaps — empty cells in topic×host/geography/clade matrices where BOTH sides
are well-studied (so the gap is surprising), and (b) open questions the
literature itself flags.

Synthesize the 10-15 most important, tractable research gaps. Rank by
scientific value. For each: title, why it matters (1-2 sentences), what
study would fill it, and whether it is supported by a deterministic
coverage gap, an open question, or both.

Return JSON: {{"gaps": [{{"title": "...", "why": "...",
"study_needed": "...", "evidence": "coverage|open-question|both"}}]}}

DATA:
{digest}"""
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await call_llm(client, prompt, 0.3, BASE, MODEL)
            return parse_json_response(resp)

    try:
        gaps = asyncio.run(synth())
        out["gaps"] = (gaps or {}).get("gaps", [])
    except Exception as e:
        out["gaps"] = []
        out["synthesis_error"] = str(e)[:200]

    out["meta"] = {
        "generated": datetime.fromtimestamp(
            __import__("time").time(), tz=timezone.utc)
                .isoformat(timespec="seconds"),
        "n_deterministic": {k: len(v) for k, v in
                            out["deterministic_gaps"].items()},
        "n_synthesized": len(out["gaps"]),
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"research gaps: {out['meta']['n_deterministic']} deterministic "
          f"candidates, {len(out['gaps'])} synthesized → {OUT.name}",
          file=sys.stderr)
    return 0


def dim_set(d):
    return set(d)


if __name__ == "__main__":
    sys.exit(main())
