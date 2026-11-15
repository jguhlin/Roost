#!/usr/bin/env python3
"""
Model R2: structural thinking round (D58).

For each model stage, feed the LLM:
  - current stage definition + nodes
  - node context packs (top evidence)
  - evidence count summaries
  - synthesis insights touching this stage's genes

Ask it to propose: new nodes, revised descriptions, connection changes,
gap closures, confidence updates. Output: data/model/r2_proposals.md for
human review → apply → model version bump.

Also implements user feedback (clade tagging, expanded Stage 0,
inflammasome pathway, sub-cellular compartments).

Usage:
  pixi run python scripts/model/model_r2.py --model infection
  pixi run python scripts/model/model_r2.py --model spread
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
MODEL_INF = ROOT / "data" / "model" / "avian_h5n1_model.json"
MODEL_SPREAD = ROOT / "data" / "model" / "h5n1_spread_model.json"
PACKS = ROOT / "data" / "model" / "node_packs"
SPREAD_EV = ROOT / "data" / "model" / "spread_evidence.jsonl"
COUNTS = ROOT / "data" / "papers" / "gene_evidence_counts.json"
INSIGHTS = ROOT / "data" / "papers" / "synthesis" / "insights.jsonl"
OUT = ROOT / "data" / "model" / "r2_proposals.md"


def call_llm(prompt, url, model_name, max_tokens=3000):
    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a research model curator. You read evidence and propose structural model updates. Be specific and grounded. Reply in clear markdown."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens, "temperature": 0.3,
        }, timeout=300)
        msg = r.json()["choices"][0]["message"]
        return (msg.get("content") or msg.get("reasoning_content") or "").strip()
    except Exception as e:
        return f"(LLM error: {e})"


def load_node_pack(sym):
    p = PACKS / f"{sym}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def infection_stage_proposal(stage, counts, insights, url, model_name):
    nodes_info = []
    for sym, note in stage["genes"]:
        c = counts.get(sym, {})
        pack = load_node_pack(sym)
        ctx = ""
        if pack and pack.get("contexts"):
            best = pack["contexts"][0]
            ctx = (best.get("explanation") or "")[:200]
        nodes_info.append(
            f"- {sym} ({note}): {c.get('papers', 0)} papers "
            f"({c.get('studied', 0)} studied) | {ctx}"
        )

    stage_insights = []
    stage_genes = [s[0] for s in stage["genes"]]
    for ins in insights:
        if any(g in str(ins.get("papers", [])) for g in stage_genes):
            stage_insights.append(f"- [{ins['kind']}] {ins['insight'][:150]}")

    prompt = f"""You are updating the avian H5N1 response model. Review this stage and propose structural updates.

## Current stage: {stage['title']}
{stage['desc']}

## Current nodes and evidence:
{chr(10).join(nodes_info)}

## Synthesis insights touching this stage:
{chr(10).join(stage_insights[:5]) if stage_insights else "(none)"}

## Propose (be specific, cite evidence strength):
1. **New nodes**: genes not currently in this stage that the evidence suggests belong here
2. **Revisions**: descriptions or connections that should change
3. **Gap closures**: any of these gaps now addressed?
4. **Stage restructuring**: does this stage need splitting, merging, or reordering?
5. **Confidence note**: overall evidence quality for this stage (strong/moderate/weak)

Only propose changes that the evidence supports. Say "no changes needed" if the stage is solid."""

    return call_llm(prompt, url, model_name)


def spread_model_proposal(spread_model, evidence_rows, url, model_name):
    rel = [r for r in evidence_rows if not r.get("not_relevant") and not r.get("error")]

    flyways = Counter()
    mechanisms = Counter()
    species = Counter()
    findings = []
    for r in rel:
        for f in r.get("flyways", []): flyways[f] += 1
        for m in r.get("spread_mechanisms", []): mechanisms[m] += 1
        for s in r.get("species_roles", []):
            if isinstance(s, dict):
                species[f"{s.get('species', '?')} ({s.get('role', '?')})"] += 1
        kf = r.get("key_spread_finding", "")
        if kf and len(kf) > 20:
            findings.append(f"- [{r.get('_pid', '?')}] {kf[:180]}")

    stages_desc = "\n".join(f"- {s['title']}: {s['desc'][:100]}" for s in spread_model["stages"])

    prompt = f"""You are updating the H5N1 spread & migration model based on extracted evidence from {len(rel)} research papers.

## Current model stages:
{stages_desc}

## Evidence aggregates:
- Flyways mentioned: {dict(flyways.most_common(10))}
- Spread mechanisms: {dict(mechanisms.most_common(8))}
- Species roles mentioned: {dict(species.most_common(15))}

## Key findings from papers (sample):
{chr(10).join(findings[:15])}

## Propose:
1. **New stages or elements** the evidence supports but the model lacks
2. **Revisions** to existing stage descriptions based on findings
3. **Connection updates**: which stages connect differently than modelled
4. **Seasonality insight**: what does the evidence say about timing?
5. **NZ/Australasia risk assessment**: based on the evidence, what's the threat picture?
6. **Missing evidence**: what should we search for that the corpus doesn't cover?"""

    return call_llm(prompt, url, model_name, max_tokens=4000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["infection", "spread", "both"], default="both")
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model_name", default="muse-glimmer-30b")
    args = ap.parse_args()

    counts = json.loads(COUNTS.read_text()) if COUNTS.exists() else {}
    insights = []
    if INSIGHTS.exists():
        insights = [json.loads(l) for l in INSIGHTS.read_text().splitlines()]

    output = ["# Model R2 Proposals — Structural Updates\n",
              "---\n"]

    if args.model in ("infection", "both"):
        inf_model = json.loads(MODEL_INF.read_text())
        output.append("## Infection Model Updates\n")
        for stage in inf_model["stages"]:
            print(f"  Stage: {stage['title']}…", flush=True)
            proposal = infection_stage_proposal(stage, counts, insights, args.url, args.model_name)
            output.append(f"### {stage['title']}\n\n{proposal}\n")

    if args.model in ("spread", "both"):
        spread_model = json.loads(MODEL_SPREAD.read_text())
        evidence = [json.loads(l) for l in SPREAD_EV.read_text().splitlines()]
        output.append("\n## Spread Model Updates\n")
        print("  Spread model…", flush=True)
        proposal = spread_model_proposal(spread_model, evidence, args.url, args.model_name)
        output.append(f"### Comprehensive Update\n\n{proposal}\n")

    OUT.write_text("\n".join(output))
    print(f"\n→ {OUT}")
    print("Review proposals, then apply changes to model JSONs → version bump → rebuild web")


if __name__ == "__main__":
    main()
