#!/usr/bin/env python3
"""Layer D: parameterized edges — numbers on the graph.

Attaches the corpus's quantitative parameters (R0/Rt, transmission
efficiency, odds/hazard ratios, diffusion rates) and environmental
persistence durations to the model edges they quantify, turning
"396 papers support this edge" into "this edge runs at R0 1.7–3.8 in
farm contexts (n papers, verified)".

Mapping is CONTEXT-KEYWORD derived (the param's context names the
setting); params may map to multiple edges or none. Only verified items
(verify in faithful/partial, or unadjudicated) are attached, faithful
first.

Output: data/model/spread_parameters.json (+ web twin), consumed by
build_spread_edges into evidence.parameters and rendered on the model
page / cyto drawer.

Usage: pixi run python scripts/model/build_spread_parameters.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"
OUT = ROOT / "data" / "model" / "spread_parameters.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "spread_parameters.json"

# context keyword -> edges (ordered specificity; first hit wins per kw,
# but a context may carry several keywords and thus several edges)
CONTEXT_EDGES = [
    (("farm", "farms", "poultry premises", "between farms", "farm-to-farm",
      "backyard"), [("bridge", "anthropogenic")]),
    (("cattle", "dairy", "bovine", "milk"), [("anthropogenic", "spillover")]),
    (("mammal", "human", "ferret", "mink", "cat", "swine", "pinniped",
      "seal"), [("anthropogenic", "spillover"), ("amplification", "spillover")]),
    (("colony", "colonies", "seabird", "colonal", "nesting"),
     [("amplification", "spillover")]),
    (("waterfowl", "duck", "mallard", "migration", "flyway", "migratory",
      "wild bird", "wild birds"), [("routes", "amplification")]),
    (("market", "live bird", "lbm", "trade"),
     [("anthropogenic", "routes"), ("bridge", "anthropogenic")]),
    (("water", "wetland", "lake", "environment", "surface", "fomite",
      "feed", "feces", "salinity", "temperature"),
     [("environmental", "reservoir")]),
    (("spread", "diffusion", "dispersal", "transmission"),
     [("routes", "amplification")]),
]


def edges_for(context: str) -> list[tuple[str, str]]:
    c = (context or "").lower()
    out = []
    for kws, edges in CONTEXT_EDGES:
        if any(k in c for k in kws):
            for e in edges:
                if e not in out:
                    out.append(e)
    return out[:3]  # cap: avoid kitchen-sink attachment


def parse_value(v):
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip().lstrip(">~<≈ ")
    try:
        return float(s)
    except ValueError:
        return None


def main() -> None:
    df = pl.read_parquet(SPREAD).filter(
        pl.col("section").is_in(["transmission_params", "persistence"]))
    by_edge: dict[tuple, list] = defaultdict(list)
    unmapped = []
    for r in df.iter_rows(named=True):
        try:
            it = json.loads(r["payload"])
        except Exception:
            continue
        verify = r.get("verify")
        if verify == "unsupported":
            continue
        if r["section"] == "transmission_params":
            item = {
                "kind": "param",
                "parameter": it.get("parameter"),
                "value": it.get("value"),
                "numeric": parse_value(it.get("value")),
                "unit": it.get("unit") or "",
                "context": (it.get("context") or "")[:160],
                "paper_id": r["paper_id"],
                "verify": verify,
            }
        else:
            item = {
                "kind": "persistence",
                "matrix": it.get("matrix"),
                "duration": it.get("duration"),
                "temperature_c": it.get("temperature_c"),
                "context": "",
                "paper_id": r["paper_id"],
                "verify": verify,
            }
        targets = edges_for(item.get("context") or item.get("matrix") or "")
        if not targets:
            unmapped.append(item)
            continue
        for e in targets:
            by_edge[e].append(item)

    out_edges = {}
    for edge, items in by_edge.items():
        items.sort(key=lambda x: (x.get("verify") != "faithful",
                                  x.get("numeric") is None))
        params = [i for i in items if i["kind"] == "param"]
        persist = [i for i in items if i["kind"] == "persistence"]
        nums = [i["numeric"] for i in params if i.get("numeric") is not None]
        out_edges[f"{edge[0]}->{edge[1]}"] = {
            "params": params[:12],
            "persistence": persist[:8],
            "summary": {
                "n_params": len(params),
                "n_persistence": len(persist),
                "min": min(nums) if nums else None,
                "max": max(nums) if nums else None,
                "faithful": sum(1 for i in items
                                if i.get("verify") == "faithful"),
            },
        }

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "provenance": ("PAPER_EXTRACTED (transmission_params + persistence "
                       "sections; verify-filtered, faithful first); "
                       "context-keyword edge mapping"),
        "edges": out_edges,
        "unmapped": len(unmapped),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False))

    print(f"edges parameterized: {len(out_edges)} "
          f"({len(unmapped)} items unmapped)")
    for key, e in sorted(out_edges.items(),
                         key=lambda kv: -kv[1]["summary"]["n_params"]):
        s = e["summary"]
        rng = f", range {s['min']}–{s['max']}" if s["min"] is not None else ""
        print(f"  {key:<28} {s['n_params']:>3} params{rng}"
              f"  +{s['n_persistence']} persistence"
              f"  ({s['faithful']} faithful)")
    print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
