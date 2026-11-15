#!/usr/bin/env python3
"""
Convert new-format pipeline analyses (data/papers/analyses/) into the
verified steps format the wiki builder consumes (data/papers/llm_analyses/)
and register any missing papers in papers.json.

New format: {paper_id, genes: {sym: {mentions, importance_score,
  evidence_type, contexts: [{passage,...}]}}, mutations: {m: {mentions,
  passages}}, key_findings: [str], metadata: {...}}

Old steps format: {paper_id, steps: {metadata, study, genes, species,
  mutations, findings, novelty}} each {step, status, extracted, verification}.

Verified (pre-existing) analyses in llm_analyses/ always win — this script
only ADDS papers not already there.

Usage: pixi run python scripts/papers/convert_analyses.py
"""

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SRC = ROOT / "data" / "papers" / "analyses"
DST = ROOT / "data" / "papers" / "llm_analyses"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"


def clean(s: str, n: int = 220) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n].rsplit(" ", 1)[0] if len(s) > n else s


def title_from_id(pid: str) -> str:
    return pid.replace("_", " ").title()


def convert(a: dict) -> dict:
    genes = []
    for sym, g in (a.get("genes") or {}).items():
        ctx = ""
        if isinstance(g, dict):
            ctxs = g.get("contexts") or []
            if ctxs:
                ctx = clean(ctxs[0].get("passage", ""))
        genes.append({
            "name": sym,
            "role": ctx or (g.get("evidence_type", "") if isinstance(g, dict) else "") or "mentioned",
            "importance": "central" if isinstance(g, dict) and (g.get("importance_score") or 0) >= 0.5 else "supporting",
        })

    mutations = []
    for m, mu in (a.get("mutations") or {}).items():
        eff = ""
        if isinstance(mu, dict):
            ps = mu.get("passages") or []
            if ps:
                eff = clean(ps[0])
        mutations.append({"name": m, "effect": eff or "described in paper"})

    findings = []
    for kf in (a.get("key_findings") or [])[:8]:
        if isinstance(kf, str):
            findings.append({"finding": clean(kf, 160), "value": "", "context": ""})

    meta = a.get("metadata") or {}
    pid = a.get("paper_id", "unknown")

    def step(name, extracted, status="extracted"):
        # HONEST provenance: regex extraction (analyze_single.py) — NOT the
        # verified multi-step LLM pipeline. full_llm_pass marks papers still
        # needing llm_analyze_papers.py treatment.
        return {"step": name, "status": status, "extracted": extracted,
                "verification": {"verified": False, "method": "regex_extraction_v1",
                                  "full_llm_pass": "pending"},
                "corrected": {}}

    return {
        "paper_id": pid,
        "steps": {
            "metadata": step("metadata", {
                "title": meta.get("title") or title_from_id(pid),
                "authors": meta.get("authors") or "",
                "year": meta.get("year"),
                "journal": meta.get("journal") or "",
                "doi": meta.get("doi") or None,
                "paper_type": meta.get("category") or "research",
            }),
            "study": step("study", {"design": "", "main_result": ""}),
            "genes": step("genes", {"genes": genes}),
            "species": step("species", {"species": []}),
            "mutations": step("mutations", {"mutations": mutations}),
            "findings": step("findings", {"findings": findings}),
            "novelty": step("novelty", {"novelty": ""}),
        },
    }


def main():
    existing = {p.stem for p in DST.glob("*.json")}
    papers_data = json.loads(PAPERS_JSON.read_text())
    known_ids = {p["id"] for p in papers_data.get("papers", [])}

    converted = skipped = 0
    new_paper_records = []
    for path in sorted(SRC.glob("*.json")):
        try:
            a = json.loads(path.read_text())
        except Exception:
            continue
        pid = a.get("paper_id") or path.stem
        if not pid or pid == "unknown":
            continue
        if pid in existing:
            skipped += 1
            continue

        DST.joinpath(f"{pid}.json").write_text(json.dumps(convert(a), indent=1))
        existing.add(pid)
        converted += 1

        if pid not in known_ids:
            meta = a.get("metadata") or {}
            new_paper_records.append({
                "id": pid,
                "title": meta.get("title") or title_from_id(pid),
                "authors": meta.get("authors") or "",
                "year": meta.get("year"),
                "journal": meta.get("journal") or "",
                "doi": meta.get("doi") or None,
                "url": "",
                "source": "pdf_batch",
                "added": date.today().isoformat(),
            })
            known_ids.add(pid)

    if new_paper_records:
        papers_data["papers"] = sorted(
            papers_data["papers"] + new_paper_records,
            key=lambda p: (p.get("year") or 0, p["id"]),
            reverse=True,
        )
        PAPERS_JSON.write_text(json.dumps(papers_data, indent=1))

    print(f"Converted: {converted} new → llm_analyses/")
    print(f"Skipped (already verified): {skipped}")
    print(f"Registered in papers.json: {len(new_paper_records)}")


if __name__ == "__main__":
    main()
