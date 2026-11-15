#!/usr/bin/env python3
"""
Stage placement for hit-but-unclassified panel genes (D82).

Pool: panel genes whose identifiers matched the corpus (search status hit)
but which carry no stage assignment (source 'none'). 220 no-hit genes stay
unplaced on principle — no corpus evidence, no placement.

Per gene:
  1. PROPOSER — sees the gene's actual corpus passages (top windows by
     recency) and proposes ONE model stage with a verbatim quote, or
     "insufficient".
  2. SKEPTIC — double-checks the quote actually supports stage membership.

Output: data/papers/connections/contextual_stages.json
  {GENE: {"stage", "note", "quote", "papers", "ts"}}
consumed by assign_stages.py contextual_pass — which fills ONLY genes still
source='none' (never model/keyword/claims/override).

Usage:
  pixi run python scripts/model/place_unclassified.py [--workers N] [--gene SYM]
"""

import argparse
import importlib.util
import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
OUT = ROOT / "data" / "papers" / "connections" / "contextual_stages.json"

spec = importlib.util.spec_from_file_location(
    "connections", ROOT / "scripts" / "papers" / "connections.py")
conn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conn)

STAGES = ["entry", "sensing", "signaling", "cytokine_storm", "effectors",
          "dependency", "celldeath", "adaptive", "hostrange"]


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


PROPOSER_SYS = f"""You assign avian-influenza host genes to infection-model stages using ONLY the supplied passages from real research papers.

Model stages: {", ".join(STAGES)}
- entry: attachment, receptors, cleavage activation
- sensing: viral RNA/DNA detection (RIG-I, MDA5, TLRs, cGAS)
- signaling: interferon relay (JAK/STAT, IRFs, MAVS, TBK1)
- cytokine_storm: interleukins, chemokines, inflammasome products
- effectors: interferon-stimulated restriction factors (MX1, IFITM, OAS, PKR)
- dependency: host machinery the virus co-opts (ANP32, polymerase cofactors)
- celldeath: apoptosis, pyroptosis, necroptosis
- adaptive: antibodies, MHC, T/B cell machinery
- hostrange: species-barrier determinants

RULES (absolute):
- Judge ONLY from the supplied passages about THIS gene. No outside knowledge.
- If the passages only mention the gene in passing, or its role does not fit
  any stage, reply "insufficient" — do not guess.
- A placement REQUIRES a "quote" copied VERBATIM from the passages showing
  the gene's role. Copy-paste; no paraphrase; no merging sentences.

Return ONLY JSON:
{{"stage": "one stage id or insufficient", "reason": "one sentence", "quote": "verbatim from passages, or empty"}}"""

SKEPTIC_SYS = """You double-check a proposed stage placement for a gene.

Given the gene, the proposed stage, and the single quoted sentence, decide:
- "confirm": the sentence explicitly shows this gene acts in the proposed stage's process.
- "deny": it does not (mention-only, different process, or speculation).

Judge ONLY the supplied sentence; no outside knowledge. Copy your "quote" VERBATIM from the supplied sentence, or leave it empty.

Return ONLY JSON: {"verdict": "confirm|deny", "reason": "one sentence", "quote": "verbatim or empty"}"""


def load_pool():
    sa = json.loads((ROOT / "web" / "public" / "data" /
                     "gene_stage_assignment.json").read_text())
    st = json.loads((ROOT / "data" / "papers" / "connections" /
                     "search_status.json").read_text())["genes"]
    none_genes = {g for g, v in sa.items() if v.get("source") == "none"}
    return sorted(g for g in none_genes if st.get(g, {}).get("status") == "hit")


def gene_windows(gene, per_paper=1, cap=6):
    """Top windows for a gene: newest papers first, one window per paper."""
    if not conn.WINDOWS_PATH.exists():
        return []
    wins = []
    for line in conn.WINDOWS_PATH.read_text().splitlines():
        try:
            w = json.loads(line)
        except Exception:
            continue
        if w.get("gene") == gene:
            wins.append(w)
    by_paper = defaultdict(list)
    for w in wins:
        by_paper[w["paper_id"]].append(w)
    papers = json.loads((ROOT / "web" / "public" / "data" /
                         "papers.json").read_text())["papers"]
    year = {p["id"]: (p.get("year") or 0) for p in papers}
    ordered = sorted(by_paper, key=lambda pid: -year.get(pid, 0))
    out = []
    for pid in ordered:
        out.extend(by_paper[pid][:per_paper])
        if len(out) >= cap:
            break
    return out[:cap]


def build_prompt(gene, windows):
    lines = [f"GENE: {gene}", ""]
    for i, w in enumerate(windows, 1):
        try:
            text = conn.window_text(w)
        except Exception:
            continue
        if len(text) > 2200:
            text = text[:2200] + " …"
        lines.append(f"[PASSAGE {i}] (paper {w['paper_id']})\n{text}")
    return "\n\n".join(lines)


def run(url, model, workers, only=None):
    pool = load_pool()
    if only:
        pool = [g for g in pool if g == only]
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text())
        except Exception:
            pass
    todo = [g for g in pool if g not in existing]
    print(f"[place] pool: {len(pool)} hit-but-unclassified genes "
          f"(done: {len(pool) - len(todo)}, todo: {len(todo)})")
    if not todo:
        print("[place] nothing to do")
        return

    def work(gene):
        windows = gene_windows(gene)
        if not windows:
            return {"gene": gene, "verdict": "insufficient",
                    "reason": "no windows on disk"}
        prompt = build_prompt(gene, windows)
        passages_norm = [_norm(build_prompt(gene, windows))]
        try:
            content = conn.muse_chat(PROPOSER_SYS, prompt, url, model)
        except Exception as e:
            return {"gene": gene, "error": str(e)[:100]}
        parsed = conn.extract_json_object(content)
        if parsed is None:
            try:
                content = conn.muse_chat(PROPOSER_SYS +
                                         "\nYour previous reply was not "
                                         "valid JSON. Output ONLY the JSON "
                                         "object.", prompt, url, model)
                parsed = conn.extract_json_object(content)
            except Exception as e:
                return {"gene": gene, "error": str(e)[:100]}
        if not isinstance(parsed, dict):
            return {"gene": gene, "error": "unparseable"}
        stage = str(parsed.get("stage") or "").lower().strip()
        q = re.sub(r"\s+", " ", str(parsed.get("quote") or "")).strip()
        if stage not in STAGES:
            return {"gene": gene, "verdict": "insufficient",
                    "reason": str(parsed.get("reason") or "")[:200]}
        if len(q) < 12 or _norm(q) not in passages_norm[0]:
            return {"gene": gene, "verdict": "insufficient",
                    "reason": "unquotable placement"}
        return {"gene": gene, "verdict": "stage", "stage": stage,
                "reason": str(parsed.get("reason") or "")[:300], "quote": q,
                "windows": windows}

    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, g): g for g in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            results.append(r)
            if i % 15 == 0 or i == len(todo):
                print(f"  proposer [{i}/{len(todo)}]")

    placements = [r for r in results if r.get("verdict") == "stage"]
    print(f"[place] stage proposals: {len(placements)} → skeptic")

    def skeptic(r):
        payload = (f"GENE: {r['gene']}\nPROPOSED STAGE: {r['stage']}\n"
                   f"RATIONALE: {r['reason']}\nQUOTED SENTENCE:\n{r['quote']}")
        try:
            content = conn.muse_chat(SKEPTIC_SYS, payload, url, model)
        except Exception as e:
            return {"verdict": "deny", "reason": str(e)[:80]}
        parsed = conn.extract_json_object(content)
        if not isinstance(parsed, dict) or str(
                parsed.get("verdict") or "").lower() not in ("confirm", "deny"):
            return {"verdict": "deny", "reason": "malformed"}
        v = parsed["verdict"].lower()
        q = re.sub(r"\s+", " ", str(parsed.get("quote") or "")).strip()
        if v == "confirm" and (len(q) < 12
                               or _norm(q) not in _norm(r["quote"])):
            v = "deny"
        return {"verdict": v, "reason": str(parsed.get("reason") or "")[:200]}

    confirmed = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(skeptic, r): r for r in placements}
        for fut in as_completed(futs):
            r = futs[fut]
            r["skeptic"] = fut.result()
            if r["skeptic"]["verdict"] == "confirm":
                papers = sorted({w["paper_id"] for w in r["windows"]})
                existing[r["gene"]] = {
                    "stage": r["stage"],
                    "note": (f"contextual placement: {r['reason']} "
                             f"| skeptic: {r['skeptic']['reason']} "
                             f"| quote: {r['quote'][:120]}"),
                    "quote": r["quote"][:300],
                    "papers": papers,
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                confirmed += 1

    OUT.write_text(json.dumps(existing, indent=1, ensure_ascii=False))
    print(f"[place] double-confirmed placements: {confirmed} → "
          f"{OUT.relative_to(ROOT)} ({len(existing)} total)")
    print("[place] next: pixi run python scripts/genes/assign_stages.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=conn.DEFAULT_URL)
    ap.add_argument("--model", default=conn.DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--gene", help="single gene (diagnostics)")
    args = ap.parse_args()
    run(args.url, args.model, args.workers, args.gene)


if __name__ == "__main__":
    main()
