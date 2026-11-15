#!/usr/bin/env python3
"""
Stage assignment (D84): map all panel genes to infection-model stages so the
full 593-gene panel can render on the ModelCyto graph.

Sources, deterministic before LLM:
  1. keyword rules over UniProt function text + protein_name + notes
  2. LLM pass over gene-claims roles (for genes keywords miss)
  3. unassigned → null (stay off the graph or an 'unassigned' bucket)

Output: web/public/data/gene_stage_assignment.json
  {SYMBOL: {"stage": "sensing", "source": "keyword"|"claims"|"llm"|"model"}}

Usage:
  assign_stages.py                    # keyword pass only (fast)
  assign_stages.py --llm              # + claims LLM pass
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
GP = ROOT / "web" / "public" / "data" / "gene_catalogue.json"
MODEL = ROOT / "data" / "model" / "avian_h5n1_model.json"
CLAIMS = ROOT / "data" / "papers" / "gene_claims.jsonl"
BACKBONE = ROOT / "data" / "genes" / "avimm_uniprot_backbone.json"
OUT = ROOT / "web" / "public" / "data" / "gene_stage_assignment.json"

# ordered rules: first match wins; patterns over function+name text
KEYWORD_RULES = [
    ("sensing", r"toll-like|rig-i|retinoic acid.inducible|mda5| melanoma differentiation|cytosolic (dna )?sensor|pattern recognition|prd.*receptor|viral rna sensor|nucleotide.sensor|cyclic gmp|stimulator of interferon|ddx58|ifih1|zbp1|aim2|nlrc|inflammasome sensor|foreign dna sensor"),
    ("entry", r"viral entry|receptor binding|sialic acid|cell entry|endocyt.*virus|fusion|virus penetration|ha receptor|surface receptor|lectin"),
    ("signaling", r"interferon regulatory|irf[0-9]|jak|stat[0-9]|map kinase|nf-?kappa|nfkb|tbk1|ikk|signal transduc|adapter protein|transcription factor.*immune|interferon.(alpha|beta|gamma) (production|signaling)|second messenger"),
    ("cytokine_storm", r"interleukin|chemokine|cytokine|tnf|il-[0-9]|il[0-9][a-z]|ccl[0-9]|cxcl[0-9]|inflammatory mediator|pro-inflammatory|anti-inflammatory"),
    ("effectors", r"interferon.stimulated|isg15|mx[12] protein|ifitm|2'.5'.oligoadenylate|oas |ribonuclease l|protein kinase r|viperin|restriction factor|antiviral protein|interferon.induced.*protein|tetherin|ifit[0-9]"),
    ("celldeath", r"apoptosis|programmed cell death|pyroptosis|necroptosis|caspase|cell death|autophagy|ripk|bcl-2|bak|bax|death domain"),
    ("adaptive", r"immunoglobulin|t.cell receptor|mhc|histocompatibility|antibody|b.cell|t.cell|antigen presentation|antigen processing|v(d)j|rag[12]|somatic hypermutation|germinal center|cd[0-9]+ |complement c[0-9]"),
    ("dependency", r"polymerase.*(activity|cofactor|binding)|host factor.*replication|replication.*(host|cellular) (factor|protein)|viral rna synthesis|cap.snatching|anp32|chaperone.*viral"),
    ("hostrange", r"species (barrier|restriction|specificity)|host range|zoonotic|cross-species"),
]

STAGES = [s for s, _ in KEYWORD_RULES]


def keyword_pass():
    gp = json.loads(GP.read_text())
    cat = gp["gene_catalogue"]
    bb = json.loads(BACKBONE.read_text())["genes"] if BACKBONE.exists() else {}
    bb_names = {g["symbol"]: g.get("protein_name", "") for g in bb.values()}

    # model genes: stage from the model itself (authoritative)
    assignment = {}
    model = json.loads(MODEL.read_text())
    for st in model["stages"]:
        for sym, _ in st.get("genes", []):
            assignment.setdefault(sym, {"stage": st["id"], "source": "model"})

    for sym, g in cat.items():
        if sym in assignment:
            continue
        text = " ".join([
            g.get("function", "") or "",
            g.get("name", "") or "",
            bb_names.get(sym, ""),
        ]).lower()
        for stage, pattern in KEYWORD_RULES:
            if re.search(pattern, text):
                assignment[sym] = {"stage": stage, "source": "keyword"}
                break
    return assignment, cat


def claims_llm_pass(assignment, url, model, workers):
    """For genes still unassigned: ask the LLM which stage their claims describe."""
    unassigned = [s for s in assignment if assignment[s]["source"] == "none"]
    if not unassigned:
        return
    claims_by_gene = {}
    if CLAIMS.exists():
        for line in CLAIMS.read_text().splitlines():
            rec = json.loads(line)
            for r in rec.get("records", []):
                claims_by_gene.setdefault(r["gene"], []).append(r["role"][:150])

    stage_desc = {st["id"]: st["title"] for st in json.loads(MODEL.read_text())["stages"]}
    prompt = f"""Assign each gene to the infection-model stage its described role best fits.
Stages: {json.dumps(stage_desc)}
Rules: role text is from avian-influenza papers. Pick ONE stage per gene, or "none" if truly unclear.
Reply ONLY as JSON: {{"GENE": "stage_id", ...}}

Genes and their roles:
"""

    def work(sym):
        roles = claims_by_gene.get(sym, [])
        if not roles:
            return sym, None
        q = prompt + json.dumps({sym: roles[:5]}, ensure_ascii=False, indent=1)
        try:
            r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
                "model": model,
                "messages": [{"role": "user", "content": q}],
                "max_tokens": 1000, "temperature": 0.1,
            }, timeout=300)
            content = r.json()["choices"][0]["message"].get("content", "")
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                v = d.get(sym)
                if v in stage_desc:
                    return sym, v
        except Exception:
            pass
        return sym, None

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sym, stage in ex.map(work, unassigned):
            if stage:
                assignment[sym] = {"stage": stage, "source": "claims-llm"}
                n += 1
    print(f"  claims-llm assigned {n}/{len(unassigned)}")


def reviewed_pass(assignment):
    """Reviewed stage proposals (from approved connection evidence) classify
    ONLY genes still unclassified (source 'none'). Core model assignments are
    untouchable here — they can only be overridden by the explicit,
    hand-edited gene_overrides.json below (documented review override)."""
    rel_path = ROOT / "web" / "public" / "data" / "gene_relationships.json"
    if not rel_path.exists():
        return 0
    try:
        proposals = json.loads(rel_path.read_text()).get("stage_proposals", {})
    except Exception:
        return 0
    n = 0
    for sym, prop in proposals.items():
        cur = assignment.get(sym)
        if cur and cur.get("source") not in ("none", None):
            continue
        stage = prop.get("stage")
        if stage in STAGES:
            assignment[sym] = {"stage": stage, "source": "reviewed",
                               "note": f"proposed {prop.get('proposed')} "
                                       f"({prop.get('papers', 0)} papers)"}
            n += 1
    return n


def contextual_pass(assignment):
    """Contextual placements (D82): quote-grounded LLM placements (double-
    confirmed) for genes that still have NO assignment. Fills source='none'
    genes only — never touches model/keyword/claims/override decisions."""
    path = ROOT / "data" / "papers" / "connections" / \
        "contextual_stages.json"
    if not path.exists():
        return 0
    try:
        placements = json.loads(path.read_text())
    except Exception:
        return 0
    n = 0
    for sym, rec in placements.items():
        cur = assignment.get(sym)
        if cur and cur.get("source") != "none" and cur.get("stage"):
            continue
        stage = rec.get("stage")
        if stage in STAGES:
            assignment[sym] = {"stage": stage, "source": "contextual",
                               "note": (rec.get("note") or "")[:250]}
            n += 1
    return n


def override_pass(assignment):
    """Explicit review overrides — the ONLY way approved data can replace a
    core model assignment. data/papers/connections/gene_overrides.json:
    {"GENE": {"stage": "stage_id", "note": "why"}} (hand-edited)."""
    path = ROOT / "data" / "papers" / "connections" / "gene_overrides.json"
    if not path.exists():
        return 0
    try:
        overrides = json.loads(path.read_text())
    except Exception:
        return 0
    n = 0
    for sym, o in overrides.items():
        stage = o.get("stage")
        if stage in STAGES:
            assignment[sym] = {"stage": stage, "source": "override",
                               "note": (o.get("note") or "")[:200]}
            n += 1
    return n


def preserve_prior(assignment):
    """Keep prior LLM/claims assignments for genes this run left unassigned
    (the LLM pass is optional and Muse-dependent; reruns must not lose it)."""
    if not OUT.exists():
        return
    try:
        prior = json.loads(OUT.read_text())
    except Exception:
        return
    keep_sources = {"claims-llm", "llm", "reviewed", "override"}
    for sym, rec in prior.items():
        cur = assignment.get(sym)
        if (cur is None or cur.get("source") == "none") \
                and rec.get("source") in keep_sources:
            assignment[sym] = rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=48)
    args = ap.parse_args()

    assignment, cat = keyword_pass()
    # mark the rest
    for sym in cat:
        if sym not in assignment:
            assignment[sym] = {"stage": None, "source": "none"}

    from collections import Counter
    tally = Counter(a["stage"] for a in assignment.values())
    print(f"keyword pass: {dict(tally)}")

    if args.llm:
        claims_llm_pass(assignment, args.url, args.model, args.workers)
        tally = Counter(a["stage"] for a in assignment.values())
        print(f"after LLM: {dict(tally)}")

    n = reviewed_pass(assignment)
    print(f"reviewed proposals classified {n} previously-unclassified genes")
    preserve_prior(assignment)
    n = contextual_pass(assignment)
    print(f"contextual placements filled {n} still-unclassified genes")
    n = override_pass(assignment)
    print(f"explicit overrides applied: {n}")

    OUT.write_text(json.dumps(assignment, indent=1))
    print(f"→ {OUT} ({len(assignment)} genes)")


if __name__ == "__main__":
    main()
