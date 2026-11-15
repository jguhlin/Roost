#!/usr/bin/env python3
"""Build the evidence block for the spread model (SPREAD_MODEL.md Phase 3).

Derives per-edge corpus evidence from data/model/spread_evidence.jsonl and
writes it as an `evidence` block INSIDE data/model/h5n1_spread_model.json
(plus the shipped twin). The LLM verification rounds own the narrative
fields; this script owns the `evidence` block exclusively.
Run order: LLM round -> build_spread_edges.py -> export.

Provenance: MEASURED (counts of corpus extractions per mapped mechanism).
The mapping below is deliberately conservative and documented — a mechanism
only supports an edge when the corpus extraction says the paper argues that
flow.

Usage: pixi run python scripts/model/build_spread_edges.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent.parent
MODEL = ROOT / "data" / "model" / "h5n1_spread_model.json"
SHIPPED = ROOT / "web" / "public" / "data" / "h5n1_spread_model.json"
EVIDENCE = ROOT / "data" / "model" / "spread_evidence.jsonl"
VERDICTS = ROOT / "data" / "papers" / "model_verdicts.jsonl"
PARAMS = ROOT / "data" / "model" / "spread_parameters.json"
PAPERS = ROOT / "web" / "public" / "data" / "papers.json"
SPREAD_PARQUET = ROOT / "data" / "papers" / "paper_spread.parquet"

# mechanism -> edges it supports (stage ids from the model) — LEGACY
# D57 topic-scan channel, kept only as fallback if the v2 parquet is absent
MECHANISM_EDGES = {
    "wild_bird_migration": [
        ("routes", "amplification"),   # migration delivers virus to colonies
        ("reservoir", "amplification"),  # reservoirs seed colonies along routes
    ],
    "poultry_trade": [
        ("anthropogenic", "routes"),   # trade can seed new flyways
        ("bridge", "anthropogenic"),   # trade moves virus into/through farms
    ],
    "farm_to_farm": [
        ("bridge", "anthropogenic"),   # virus established on farms spreads
    ],
    "live_markets": [
        ("bridge", "anthropogenic"),
    ],
    "environmental": [
        ("environmental", "reservoir"),  # water persistence maintains reservoir
    ],
    "fomites": [
        ("bridge", "anthropogenic"),
    ],
    "unknown": [],
}

# ---------------------------------------------------------------------------
# v2 field-derived mapping (2026-10-14): structured items from
# llm_extract_spread (paper_spread.parquet) -> model edges, mapped by their
# FIELDS (route/kind/role/context), never by topic keywords. One paper counts
# once per edge (set semantics); mapped_from records which sections fed it.
# Sections without single-edge semantics (surveillance_coverage,
# intervention_response, impact_recovery, risk_factors, transmission_params,
# reassortment_events) are deliberately unmapped — Layer D parameterizes
# edges with them instead.
MAMMAL_RE = re.compile(
    r"mammal|human|ferret|mink|mice|mouse|cattle|bovine|feline|canine|cat|dog|"
    r"swine|pig|pinniped|seal|sea lion|fox|dolphin|whale|raccoon|skunk|bear",
    re.I,
)


def _edges_host_roles(it):
    roles = set(it.get("roles") or [])
    out = []
    if roles & {"reservoir", "amplifier"}:
        out.append(("reservoir", "amplification"))
    if "bridge" in roles:
        out.append(("reservoir", "bridge"))
    return out


def _edges_intro(it):
    r = (it.get("route") or "").lower()
    if r == "migration":
        return [("routes", "amplification")]
    if r == "trade":
        return [("anthropogenic", "routes")]
    if r == "spillover":
        return [("amplification", "spillover")]
    return []


def _edges_mass(it):
    k = (it.get("kind") or "").lower()
    if k in ("colony", "wildlife", "marine_mammal"):
        return [("amplification", "spillover")]   # die-offs -> exposure
    if k == "farm":
        return [("bridge", "anthropogenic")]       # virus reaches farms
    return []


def _edges_contact(it):
    c = (it.get("context") or "").lower()
    if c == "livestock_contact":
        return [("bridge", "anthropogenic")]
    if c in ("colony", "mixed_flock", "staging", "wintering"):
        return [("reservoir", "amplification")]    # shared-site mixing
    return []


def _edges_adaptation(it):
    ctx = it.get("host_context") or ""
    if MAMMAL_RE.search(ctx):
        return [("anthropogenic", "spillover")]    # mammalian adaptation
    return []


SECTION_EDGES = {
    # sections whose every item maps one way
    "migration_links": lambda it: [("routes", "amplification")],
    "seasonality": lambda it: [("timing", "routes")],
    "persistence": lambda it: [("environmental", "reservoir")],
    "trade_movements": lambda it: [("anthropogenic", "routes")],
    "anthropogenic_mechanics": lambda it: [("bridge", "anthropogenic")],
    "mammal_chains": lambda it: [("amplification", "spillover")],
    "establishment": lambda it: [("regional_risk", "routes")],
    "silent_spread": lambda it: [("regional_risk", "routes")],
    # field-conditional sections
    "host_roles": _edges_host_roles,
    "introduction_events": _edges_intro,
    "mass_events": _edges_mass,
    "contact_structure": _edges_contact,
    "adaptation_mutations": _edges_adaptation,
}


def map_v2_items(papers):
    """paper_spread.parquet -> {edge: {papers, mapped_from, grounded}}."""
    import polars as pl

    out = {}
    df = pl.read_parquet(SPREAD_PARQUET)
    for r in df.iter_rows(named=True):
        pid = r["paper_id"]
        if pid not in papers:
            continue
        section = r["section"]
        fn = SECTION_EDGES.get(section)
        if not fn:
            continue
        try:
            it = json.loads(r["payload"])
        except Exception:
            continue
        for edge in fn(it):
            e = out.setdefault(edge, {"papers": set(), "mapped_from": {}})
            e["papers"].add(pid)
            e["mapped_from"][section] = e["mapped_from"].get(section, 0) + 1
    # grounded: per paper-edge — the paper has >=1 grounded row in a section
    # that fed this edge (deduped, so a paper counts at most once per edge)
    out_g = {}
    df2 = df.filter(pl.col("paper_id").is_in(list(papers)) & pl.col("quote_in_text"))
    grounded_map = {}
    for r in df2.iter_rows(named=True):
        grounded_map.setdefault(r["paper_id"], set()).add(r["section"])
    for edge, e in out.items():
        g = sum(
            1 for pid in e["papers"]
            if any(s in grounded_map.get(pid, ()) for s in e["mapped_from"])
        )
        out_g[edge] = {**e, "grounded": g}
    return out_g

# diverge topic keywords -> edge ids marked contested (both sides cited)
CONTESTED_BY_TOPIC = {
    "reservoir pathology": [("reservoir", "amplification")],
    "bridge host": [("bridge", "anthropogenic")],
    "flyway limits": [("anthropogenic", "routes"), ("routes", "amplification")],
}


def main() -> None:
    model = json.loads(MODEL.read_text())
    papers = {p["id"] for p in json.loads(PAPERS.read_text())["papers"]}

    edge_papers = defaultdict(set)
    edge_mech = defaultdict(Counter)
    edge_season = defaultdict(set)
    edge_v2 = {}          # {edge: {papers, mapped_from, grounded}}
    provenance = "legacy D57 topic scan (spread_evidence.jsonl)"

    if SPREAD_PARQUET.exists():
        # channel 1 (v2): field-derived mapping of structured extraction items
        edge_v2 = map_v2_items(papers)
        provenance = ("PAPER_EXTRACTED (field-derived section→edge mapping, "
                      "llm_extract_spread v2)")
        for edge, e in edge_v2.items():
            edge_papers[edge] |= e["papers"]
            edge_mech[edge].update(e["mapped_from"])
    else:
        # fallback: legacy D57 corpus extraction (mechanism-level)
        for line in EVIDENCE.read_text().splitlines():
            d = json.loads(line)
            pid = d.get("_pid")
            if not pid or pid not in papers:
                continue
            for mech in d.get("spread_mechanisms", []):
                for edge in MECHANISM_EDGES.get(mech, []):
                    edge_papers[edge].add(pid)
                    edge_mech[edge][mech] += 1
            seas = d.get("seasonality")
            if seas and seas not in ("not_stated", "missing"):
                edge_season[("timing", "routes")].add(pid)

    # channel 2: campaign Phase-D model verdicts (STAGE-level, quote-grounded).
    # Verdicts speak to stages, not edges — assigning them to every touching
    # edge would triple-count each paper and blur edge precision. They land in
    # a per-stage `stages` block; edges surface endpoint stage-support counts
    # as context only (channels.verdicts), never as edge `papers`.
    verdict_papers = defaultdict(set)    # stage -> {pid}
    verdict_tally = defaultdict(Counter)  # stage -> Counter(verdict)
    if VERDICTS.exists():
        for line in VERDICTS.read_text().splitlines():
            d = json.loads(line)
            pid = d.get("paper_id")
            if not pid or pid not in papers:
                continue
            for v in ((d.get("verdicts") or {}).get("spread") or []):
                if not isinstance(v, dict):
                    continue
                stage, verdict = v.get("stage"), v.get("verdict")
                if verdict not in ("agrees", "adds", "changes", "disagrees"):
                    continue
                verdict_papers[stage].add(pid)
                verdict_tally[stage][verdict] += 1

    contested = set()
    for div in model.get("diverges", []):
        topic = (div.get("topic") or "").lower()
        for key, edges in CONTESTED_BY_TOPIC.items():
            if key in topic:
                contested.update(edges)

    evidence = {"generated": model.get("updated"), "provenance": provenance,
                "edges": {}, "stages": {}}
    for c in model.get("connections", []):
        edge = (c["from"], c["to"])
        ext = edge_papers.get(edge, set()) | edge_season.get(edge, set())
        pids = sorted(ext)
        # endpoint stage-support: context only (stage-level verdicts, not edge claims)
        support = sum(len(verdict_papers.get(s, set())) for s in edge)
        block = evidence["edges"][f"{edge[0]}->{edge[1]}"] = {
            "papers": pids,
            "count": len(pids),
            "mechanisms": dict(edge_mech.get(edge, {})),
            "grounded": edge_v2.get(edge, {}).get("grounded", 0),
            "channels": {
                "extraction": len(ext),
                "endpoint_stage_support": support,
            },
        }
        if edge in contested:
            block["contested"] = True
            block["contested_by"] = [
                d.get("topic") for d in model.get("diverges", [])
                if any(key in (d.get("topic") or "").lower()
                       and edge in edges_
                       for key, edges_ in CONTESTED_BY_TOPIC.items())
            ]

    # stage-level verdict evidence (what model_verdicts actually measure)
    for s in model.get("stages", []):
        sid = s["id"]
        if sid in verdict_papers:
            evidence["stages"][sid] = {
                "papers": sorted(verdict_papers[sid]),
                "count": len(verdict_papers[sid]),
                "tally": dict(verdict_tally[sid]),
            }

    # Layer D: quantitative parameters per edge (built by
    # build_spread_parameters; verify-filtered, faithful first)
    if PARAMS.exists():
        evidence["parameters"] = json.loads(PARAMS.read_text())["edges"]
    model["evidence"] = evidence
    model["updated"] = datetime.now(timezone.utc).date().isoformat()
    MODEL.write_text(json.dumps(model, indent=1, ensure_ascii=False))
    SHIPPED.write_text(json.dumps(model, indent=1, ensure_ascii=False))

    total = sum(b["count"] for b in evidence["edges"].values())
    contested_n = sum(1 for b in evidence["edges"].values() if b.get("contested"))
    stage_n = len(evidence["stages"])
    stage_p = sum(b["count"] for b in evidence["stages"].values())
    print(f"evidence block: {len(evidence['edges'])} edges, "
          f"{total} edge-paper links, {contested_n} contested; "
          f"stage-level verdicts: {stage_n} stages, {stage_p} paper links")
    for key, b in sorted(evidence["edges"].items(), key=lambda kv: -kv[1]["count"]):
        flag = " ★contested" if b.get("contested") else ""
        ch = b.get("channels", {})
        print(f"  {key:<30} {b['count']:>3} papers  "
              f"[ext={ch.get('extraction', 0)} stage-support={ch.get('endpoint_stage_support', 0)}] "
              f"{b['mechanisms'] or ''}{flag}")


if __name__ == "__main__":
    main()
