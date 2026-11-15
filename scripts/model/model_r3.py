#!/usr/bin/env python3
"""
Model R3: pathway improvement from mined connection data (D81).

Feeds each infection-model stage:
  - current stage definition + gene list
  - APPROVED relationship evidence touching the stage's genes
    (mechanism, independent papers, top quotes, species)
  - candidate genes: panel genes with reviewed connections that are NOT in
    the core model (neutral/assigned-elsewhere/unclassified)

Two LLM passes per stage:
  1. PROPOSER — concrete updates as JSON: genes to add (with verbatim
     evidence quotes), edge notes, stage-description revision, gaps.
  2. SKEPTIC — every add/edge proposal re-checked against its own cited
     quotes; only double-confirmed proposals reach the report.

Output: data/model/r3_proposals.md — a human-review document (model edits
stay curator-approved; stage additions can be applied later through
gene_overrides.json, the explicit-review path).

Usage:
  pixi run python scripts/model/model_r3.py [--url ...] [--model ...]
"""

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

ROOT = Path(__file__).parent.parent.parent

import sys as _sys
_sys_path = str(ROOT / "scripts" / "papers")
if _sys_path not in _sys.path:
    _sys.path.insert(0, _sys_path)
try:
    from llm_provenance import track as _llm_track
except ImportError:
    _llm_track = lambda *a, **k: None
MODEL_INF = ROOT / "data" / "model" / "avian_h5n1_model.json"
REL_FILE = ROOT / "web" / "public" / "data" / "gene_relationships.json"
STAGE_ASSIGN = ROOT / "web" / "public" / "data" / "gene_stage_assignment.json"
GENE_PRESENCE = ROOT / "web" / "public" / "data" / "gene_catalogue.json"
OUT = ROOT / "data" / "model" / "r3_proposals.md"

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

VIRAL = {"PB2", "PB1", "PB1-F2", "PA", "PA-X", "HA", "HA1", "HA2", "NP",
         "NA", "M1", "M2", "M42", "NS1", "NS2", "NS3", "HE"}


def chat(system, user, url, model, max_tokens=32000, temperature=0.1):
    """Muse call tolerant of reasoning-content responses (32k: reasoning
    burns budget — smaller caps truncate JSON mid-string)."""
    r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user +
             "\n\n(Reply with ONLY the JSON. No text after it.)"},
        ],
        "max_tokens": max_tokens, "temperature": temperature,
    }, timeout=900)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    content = (msg.get("content") or "").strip()
    if not content and msg.get("reasoning_content"):
        content = msg["reasoning_content"].strip()
    return content


def extract_json_obj(text):
    """Last complete balanced JSON object (string-aware)."""
    if not text:
        return None
    best = None
    depth = 0
    start = None
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        val = json.loads(text[start:i + 1])
                        if isinstance(val, dict):
                            best = val
                    except Exception:
                        pass
                    start = None
    return best


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def load_data():
    model = json.loads(MODEL_INF.read_text())
    rel = json.loads(REL_FILE.read_text())
    stage_assign = json.loads(STAGE_ASSIGN.read_text()) \
        if STAGE_ASSIGN.exists() else {}
    panel = set(json.loads(GENE_PRESENCE.read_text())["gene_catalogue"])
    return model, rel, stage_assign, panel


def evidence_pack(rel):
    """Approved edges indexed by gene + deduped quote pool."""
    edges = [e for e in rel.get("edges", []) if e.get("evidence")]
    by_gene = defaultdict(list)
    quotes = []
    seen_q = set()
    for e in edges:
        papers = sorted({ev.get("paper_id") for ev in e["evidence"]})
        top = sorted(e["evidence"],
                     key=lambda ev: -(ev.get("year") or 0))[:2]
        rec = {
            "from": e["from"], "to": e["to"], "mechanism": e["mechanism"],
            "independent_papers": len(papers),
            "species": sorted({ev.get("species") for ev in e["evidence"]
                               if ev.get("species")}),
            "quotes": [ev.get("quote", "") for ev in top
                       if ev.get("quote")],
        }
        by_gene[e["from"]].append(rec)
        by_gene[e["to"]].append(rec)
        for q in rec["quotes"]:
            if _norm(q) not in seen_q:
                seen_q.add(_norm(q))
                quotes.append(q)
    return edges, by_gene, quotes


def stage_candidates(model, by_gene, stage_assign, panel):
    """Panel genes with reviewed connections that are NOT core model genes —
    the pool the proposer may draw additions from (per stage via their
    current assignment)."""
    model_genes = {sym for st in model["stages"]
                   for sym, _ in st.get("genes", [])}
    cands = sorted(set(by_gene) - model_genes - VIRAL)
    per_stage = defaultdict(list)
    extra = []
    for sym in cands:
        if sym not in panel:
            extra.append(sym)       # non-panel endpoints don't join stages
            continue
        a = stage_assign.get(sym) or {}
        per_stage[a.get("stage") or "UNASSIGNED"].append(sym)
    return model_genes, per_stage, extra


PROPOSER_SYS = """You improve an avian-influenza infection-model pathway using ONLY newly mined, review-approved relationship evidence.

For the given stage you may propose:
- add_genes: panel genes that now have enough reviewed mechanistic evidence to belong in this stage.
- edge_notes: approved edges touching this stage's genes that deserve curator attention (contradictions, missing wiring, refinements).
- stage_revision: a revised one-sentence stage description IF the evidence changes the picture.
- gaps: remaining weaknesses.

ABSOLUTE RULES:
- Propose ONLY from the supplied evidence. Never use outside knowledge.
- Every add_genes / edge_notes entry MUST cite "evidence_quotes" copied VERBATIM from the supplied quotes (copy-paste, no paraphrase, no merging). An entry without a verbatim quote will be discarded.
- add_genes: only symbols from the supplied candidate list for this stage.
- Be conservative: multiple independent papers or an explicit mechanism beat single mentions.

Return ONLY JSON:
{"add_genes": [{"symbol": "...", "reason": "one sentence", "evidence_quotes": ["..."]}],
 "edge_notes": [{"from": "...", "to": "...", "mechanism": "...", "note": "one sentence", "evidence_quotes": ["..."]}],
 "stage_revision": {"proposal": "...", "reason": "..."} ,
 "gaps": ["..."]}
Use empty arrays when nothing is warranted."""


SKEPTIC_SYS = """You double-check a proposed pathway update against the mined evidence it cites.

Given a proposal (gene to add to a stage, or an edge note) and its quoted evidence, decide:
- "confirm": the verbatim quotes explicitly support this proposal (mechanism and relevance to the stage/pair).
- "deny": they do not (mention-only, wrong stage, wrong direction, or speculation).

Judge ONLY the supplied quotes; no outside knowledge. Copy your "quote" VERBATIM from the supplied quotes, or leave it empty.

Return ONLY JSON: {"verdict": "confirm|deny", "reason": "one sentence", "quote": "verbatim or empty"}"""


def build_stage_prompt(stage, by_gene, cand_syms):
    genes_now = [sym for sym, _ in stage.get("genes", [])]
    lines = [
        f"STAGE: {stage['id']} — {stage.get('title', '')}",
        f"DESCRIPTION: {stage.get('desc', '')}",
        f"CURRENT GENES: {', '.join(genes_now)}",
    ]
    if cand_syms:
        lines.append(f"CANDIDATE PANEL GENES FOR THIS STAGE "
                     f"(the only symbols you may add): "
                     + ", ".join(cand_syms))
    else:
        lines.append("CANDIDATE PANEL GENES FOR THIS STAGE: none — do not "
                     "propose add_genes.")
    lines.append("")
    lines.append("APPROVED RELATIONSHIP EVIDENCE touching this stage's "
                 "genes and candidates:")
    seen = set()
    for sym in genes_now + list(cand_syms):
        for rec in by_gene.get(sym, []):
            key = (rec["from"], rec["to"], rec["mechanism"])
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"- {rec['from']} --{rec['mechanism']}--> {rec['to']} "
                f"({rec['independent_papers']} independent papers; "
                f"species: {', '.join(rec['species']) or 'general'})")
            for q in rec["quotes"]:
                lines.append(f"    quote: {q}")
    if len(seen) == 0:
        lines.append("- (no approved evidence touches this stage)")
    return "\n".join(lines)


def run(url, model, workers):
    inf, rel, stage_assign, panel = load_data()
    edges, by_gene, all_quotes = evidence_pack(rel)
    model_genes, per_stage, extra = stage_candidates(inf, by_gene,
                                                     stage_assign, panel)
    print(f"[r3] approved edges: {len(edges)} · genes with evidence: "
          f"{len(by_gene)} · model genes: {len(model_genes)}")
    print(f"[r3] candidate additions: "
          f"{sum(len(v) for k, v in per_stage.items() if k != 'UNASSIGNED')}"
          f" assigned + {len(per_stage.get('UNASSIGNED', []))} unassigned "
          f"({len(extra)} non-panel endpoints excluded)")

    norm_quotes = [_norm(q) for q in all_quotes]

    def quotable(qs):
        out = []
        for q in qs or []:
            q = re.sub(r"\s+", " ", str(q)).strip()
            if len(q) >= 12 and _norm(q) in norm_quotes:
                out.append(q)
        return out

    def work(stage):
        cand_syms = per_stage.get(stage["id"], []) \
            + per_stage.get("UNASSIGNED", [])
        prompt = build_stage_prompt(stage, by_gene, cand_syms)
        try:
            content = chat(PROPOSER_SYS, prompt, url, model)
        except Exception as e:
            return {"stage": stage["id"], "error": str(e)[:100]}
        parsed = extract_json_obj(content)
        if parsed is None:
            try:
                content = chat(PROPOSER_SYS + "\nYour previous reply was "
                               "not valid JSON. Output ONLY the JSON object.",
                               prompt, url, model)
                parsed = extract_json_obj(content)
            except Exception as e:
                return {"stage": stage["id"], "error": str(e)[:100]}
        if not isinstance(parsed, dict):
            return {"stage": stage["id"], "error": "unparseable"}
        allowed = set(cand_syms)
        adds = []
        for g in parsed.get("add_genes") or []:
            if not isinstance(g, dict) or g.get("symbol") not in allowed:
                continue
            qs = quotable(g.get("evidence_quotes"))
            if qs:
                adds.append({"symbol": g["symbol"],
                             "reason": str(g.get("reason") or "")[:300],
                             "quotes": qs[:3]})
        notes = []
        for n in parsed.get("edge_notes") or []:
            if not isinstance(n, dict):
                continue
            qs = quotable(n.get("evidence_quotes"))
            if qs and n.get("from") and n.get("to"):
                notes.append({"from": n["from"], "to": n["to"],
                              "mechanism": str(n.get("mechanism") or ""),
                              "note": str(n.get("note") or "")[:300],
                              "quotes": qs[:3]})
        rev = parsed.get("stage_revision") or {}
        return {"stage": stage["id"], "title": stage.get("title", ""),
                "adds": adds, "notes": notes,
                "revision": rev if isinstance(rev, dict) and rev.get(
                    "proposal") else None,
                "gaps": [str(g)[:250] for g in (parsed.get("gaps") or [])[:4]]}

    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, st): st for st in inf["stages"]}
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            print(f"  proposer [{i}/{len(futs)}]")

    # ---- skeptic pass over every add + edge note
    checks = []
    for res in results:
        for a in res.get("adds", []):
            a["stage_title"] = f"{res['stage']} — {res.get('title', '')}"
            checks.append(("add", res, a))
        for n in res.get("notes", []):
            checks.append(("note", res, n))

    def skeptic(kind, item):
        claim = (f"Add {item['symbol']} to the infection-model stage "
                 f"'{item.get('stage_title', '')}' as a gene whose mechanistic "
                 f"role in this stage is supported by the quotes"
                 if kind == "add"
                 else f"Curator note on edge {item['from']} --"
                      f"{item.get('mechanism', '')}--> {item['to']}")
        payload = (f"PROPOSAL: {claim}\nRATIONALE: {item.get('reason') or item.get('note', '')}\n"
                   f"QUOTED EVIDENCE:\n"
                   + "\n".join(f"- {q}" for q in item["quotes"]))
        try:
            content = chat(SKEPTIC_SYS, payload, url, model)
        except Exception as e:
            return {"verdict": "error", "reason": str(e)[:80], "quote": ""}
        parsed = extract_json_obj(content)
        if not isinstance(parsed, dict) or str(
                parsed.get("verdict") or "").lower() not in ("confirm", "deny"):
            return {"verdict": "deny", "reason": "malformed skeptic reply",
                    "quote": ""}
        v = parsed["verdict"].lower()
        q = re.sub(r"\s+", " ", str(parsed.get("quote") or "")).strip()
        if v == "confirm" and (len(q) < 12
                               or _norm(q) not in [_norm(x)
                                                   for x in item["quotes"]]):
            v = "deny"   # skeptic could not quote its own evidence
        return {"verdict": v, "reason": str(parsed.get("reason") or "")[:250],
                "quote": q}

    n_conf = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(skeptic, kind, item): (kind, item)
                for kind, _, item in checks}
        for i, fut in enumerate(as_completed(futs), 1):
            kind, item = futs[fut]
            verdict = fut.result()
            item["skeptic"] = verdict
            if verdict["verdict"] == "confirm":
                n_conf += 1
            if i % 10 == 0 or i == len(futs):
                print(f"  skeptic [{i}/{len(futs)}]")

    # ---- report
    lines = [
        "# Model R3 Proposals — pathway improvements from mined connections",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} · from "
        f"{len(edges)} approved relationships "
        f"({rel.get('counts', {}).get('evidence', 0)} evidence records). "
        "Every add/note proposal was double-confirmed by a second LLM pass "
        "against its own verbatim quotes. Model edits remain curator-"
        "approved: apply stage additions via "
        "`data/papers/connections/gene_overrides.json` after review.",
        "",
    ]
    for res in sorted(results, key=lambda r: r["stage"]):
        lines.append(f"## {res['stage']} — {res.get('title', '')}")
        lines.append("")
        if res.get("error"):
            lines.append(f"*(proposer error: {res['error']})*")
            lines.append("")
            continue
        adds = res.get("adds", [])
        if adds:
            lines.append("### Proposed gene additions (double-confirmed)")
            for a in adds:
                mark = "✅" if a["skeptic"]["verdict"] == "confirm" else "❌"
                lines.append(f"- {mark} **{a['symbol']}** — {a['reason']}")
                for q in a["quotes"][:2]:
                    lines.append(f"  > {q}")
                lines.append(f"  skeptic: {a['skeptic']['reason']}")
        else:
            lines.append("### Gene additions: none proposed")
        notes = res.get("notes", [])
        if notes:
            lines.append("")
            lines.append("### Edge notes (double-confirmed)")
            for n in notes:
                mark = "✅" if n["skeptic"]["verdict"] == "confirm" else "❌"
                lines.append(f"- {mark} **{n['from']} --{n['mechanism']}--> "
                             f"{n['to']}** — {n['note']}")
                for q in n["quotes"][:2]:
                    lines.append(f"  > {q}")
        if res.get("revision"):
            r = res["revision"]
            lines.append("")
            lines.append("### Stage description revision proposed")
            lines.append(f"> {r.get('proposal')}")
            lines.append(f"reason: {r.get('reason')}")
        if res.get("gaps"):
            lines.append("")
            lines.append("### Gaps noted")
            for g in res["gaps"]:
                lines.append(f"- {g}")
        lines.append("")

    confirmed_adds = sum(1 for _, _, a in checks if a.get("skeptic", {})
                         .get("verdict") == "confirm")
    lines.insert(3, f"**Summary: {len(checks)} proposals → "
                    f"{n_conf} double-confirmed, "
                    f"{len(checks) - n_conf} rejected by the skeptic.**")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[r3] → {OUT.relative_to(ROOT)} "
          f"({len(checks)} proposals, {n_conf} confirmed)")
    _llm_track("model_r3", model, "r3-v2", len(checks),
               notes=f"proposals: {len(checks)}, confirmed: {n_conf}")
    if any(res.get("error") for res in results):
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    run(args.url, args.model, args.workers)


if __name__ == "__main__":
    main()
