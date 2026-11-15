#!/usr/bin/env python3
"""Claim-cluster adjudication — contradictions, consensus, open questions.

Groups typed claims by entity key (gene/species/clade/method — exact match,
no embeddings), then ONE LLM call per cluster (≥2 distinct papers) judges:
  - contradictions: which papers conflict, on what exactly, and whether
    it's a real conflict vs context (species/era/dose) vs apparent
  - consensus: what the cluster agrees on
  - open questions: what remains unresolved

Outputs:
  data/papers/claim_clusters.parquet      (cluster, n_papers, n_claims)
  data/papers/contradictions.parquet      (cluster, paper_a, paper_b, topic,
                                           what_conflicts, verdict, explanation)
  data/papers/cluster_verdicts.parquet    (cluster, consensus[], open_questions[])

Run AFTER llm_type_claims.py:
  pixi run python scripts/papers/llm_claims_adjudicate.py [--min-papers 2]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

TYPED = ROOT / "data" / "papers" / "typed_claims.parquet"
EXTRAS = ROOT / "data" / "papers" / "paper_extras.parquet"
OUT_C = ROOT / "data" / "papers" / "claim_clusters.parquet"
OUT_X = ROOT / "data" / "papers" / "contradictions.parquet"
OUT_V = ROOT / "data" / "papers" / "cluster_verdicts.parquet"
DONE = ROOT / "data" / "papers" / "adjudication_done.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """You are adjudicating a research-literature cluster for the avian-
influenza database. Every claim below concerns the same key: {key}.
Each claim carries its paper id in [brackets], plus year, study type and
scope. The VALID paper ids in this cluster are:
{id_list}

You MUST use ONLY ids from this list. Copy them EXACTLY — character for
character, including hyphens and underscores. Never abbreviate, never use
the paper title, never invent an id.

Identify:

1. CONTRADICTIONS — pairs of claims that genuinely conflict. STRICT RULES:
   - paper_a and paper_b MUST be two DISTINCT ids from the list above.
   - If only one paper makes a claim, that is NOT a contradiction — omit it.
   For each real contradiction: what_conflicts (the specific question),
   verdict: "real" (methods comparable, results incompatible) |
   "context-dependent" (conflict dissolves once context is accounted for) |
   "apparent" (compatible as stated), reason_type: one of temporal (claims
   from different dates/eras — one may simply be newer data) |
   methodological | species-context | geographic | dose-route | sample-size |
   definitional (terms mean different things) | data-currency | other,
   tags: 1-4 short keyword tags, and a one-sentence explanation.
2. CONSENSUS — points where the cluster's claims agree.
3. OPEN QUESTIONS — what this cluster leaves unresolved.

Return JSON:
{{"contradictions": [{{"paper_a": "exact-id-from-list", "paper_b": "exact-id-from-list",
   "topic": "...", "what_conflicts": "...",
   "verdict": "real|context-dependent|apparent",
   "reason_type": "temporal|methodological|species-context|geographic|dose-route|sample-size|definitional|data-currency|other",
   "tags": ["..."], "explanation": "..."}}],
 "consensus": ["..."], "open_questions": ["..."]}}
Empty arrays where none. Be strict: only flag a contradiction when the claims
address the SAME question in comparable systems.

CLAIMS:
{claims}"""


def build_clusters(min_papers: int):
    typed = pl.read_parquet(TYPED)
    extras = pl.read_parquet(EXTRAS).select(["id", "title", "year", "study_type",
                                             "host_taxa", "setting"])
    meta = {r["id"]: r for r in extras.iter_rows(named=True)}
    clusters: dict[str, list[dict]] = defaultdict(list)
    for r in typed.iter_rows(named=True):
        m = meta.get(r["paper_id"], {})
        claim = {
            "paper": r["paper_id"], "year": m.get("year"),
            "study_type": (m.get("study_type") or ["?"])[0]
                if isinstance(m.get("study_type"), list) else m.get("study_type"),
            "text": r["text"], "stance": r["stance"], "scope": r["scope"],
        }
        keys = set()
        for col, kind in (("genes", "gene"), ("species", "species"),
                          ("clades", "clade"), ("methods", "method")):
            for v in json.loads(r[col] or "[]"):
                if isinstance(v, str) and 1 < len(v) < 40:
                    keys.add(f"{kind}:{v.strip()}")
        for k in keys:
            clusters[k].append(claim)
    # keep clusters with >= min distinct papers, biggest first
    out = []
    for k, claims in clusters.items():
        papers = {c["paper"] for c in claims}
        if len(papers) >= min_papers:
            out.append((k, claims, len(papers)))
    out.sort(key=lambda t: -t[2])
    return out


async def adjudicate(client, sem, key, claims, valid_ids=None):
    async with sem:
        body = "\n".join(
            f"- [{c['paper']} {c['year']} {c['study_type']}] {c['text']}"
            f"{' (' + c['scope'] + ')' if c['scope'] else ''}"
            for c in claims[:60])
        id_list = " | ".join(sorted({c["paper"] for c in claims})[:30])
        prompt = PROMPT.format(key=key, claims=body, id_list=id_list)
        for attempt in range(2):
            try:
                out = await call_llm(client, prompt, 0.1, BASE, MODEL)
                parsed = parse_json_response(out)
                if parsed and ("contradictions" in parsed
                               or "consensus" in parsed):
                    # deterministic post-validation: fix or drop bad IDs
                    if valid_ids:
                        from resolve_paper_ids import resolve_id
                        titles = {}  # not available here; prefix/substring only
                        for x in (parsed.get("contradictions") or []):
                            for side in ("paper_a", "paper_b"):
                                raw = x.get(side, "")
                                fixed = resolve_id(raw, valid_ids, titles)
                                if fixed:
                                    x[side] = fixed
                        parsed["contradictions"] = [
                            x for x in (parsed.get("contradictions") or [])
                            if x.get("paper_a") and x.get("paper_b")
                            and x["paper_a"] != x["paper_b"]
                        ]
                    return key, parsed
            except Exception:
                pass
            await asyncio.sleep(3)
        return key, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--chunk", type=int, default=25)
    ap.add_argument("--min-papers", type=int, default=3,
                    help="clusters need ≥ this many distinct papers")
    args = ap.parse_args()

    clusters = build_clusters(args.min_papers)
    done = set(json.loads(DONE.read_text())) if DONE.exists() else set()
    todo = [(k, c) for k, c, _ in clusters if k not in done]
    print(f"{len(clusters)} clusters ≥{args.min_papers} papers; "
          f"{len(todo)} to adjudicate (done: {len(done)})", file=sys.stderr)
    if not todo:
        return 0

    # valid paper IDs for deterministic post-validation
    try:
        _papers = json.loads((ROOT / "web" / "public" / "data" /
                              "papers.json").read_text())["papers"]
        valid_id_set = sorted(p["id"] for p in _papers)
    except Exception:
        valid_id_set = None

    async def run():
        sem = asyncio.Semaphore(args.concurrency)
        limits = httpx.Limits(max_connections=args.concurrency * 2,
                              max_keepalive_connections=args.concurrency)
        c_rows, x_rows, v_rows = [], [], []
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        async with httpx.AsyncClient(timeout=httpx.Timeout(900.0),
                                     limits=limits) as client:
            for start in range(0, len(todo), args.chunk):
                chunk = todo[start:start + args.chunk]
                results = await asyncio.gather(
                    *[adjudicate(client, sem, k, c, valid_ids=valid_id_set)
                      for k, c in chunk])
                for (key, claims), (k2, verdict) in zip(chunk, results):
                    c_rows.append({"cluster": key, "n_papers":
                                   len({c["paper"] for c in claims}),
                                   "n_claims": len(claims), "adjudicated_at": ts})
                    if verdict is None:
                        continue
                    for x in verdict.get("contradictions", []):
                        x_rows.append({"cluster": key, **{kk: str(vv)[:500] for
                                       kk, vv in x.items()}, "ts": ts})
                    v_rows.append({"cluster": key,
                                   "consensus": json.dumps(
                                       verdict.get("consensus", [])),
                                   "open_questions": json.dumps(
                                       verdict.get("open_questions", [])),
                                   "ts": ts})
                    done.add(key)
                for out, rows in ((OUT_C, c_rows), (OUT_X, x_rows), (OUT_V, v_rows)):
                    if rows:
                        fresh = pl.DataFrame(rows, infer_schema_length=None)
                        if out.exists():
                            old = pl.read_parquet(out).filter(
                                ~pl.col("cluster").is_in(
                                    [r["cluster"] for r in rows]))
                            fresh = pl.concat([old, fresh], how="diagonal")
                        fresh.write_parquet(out)
                DONE.write_text(json.dumps(sorted(done)))
                print(f"  {min(start + args.chunk, len(todo))}/{len(todo)} "
                      f"clusters · {len(x_rows)} contradictions so far",
                      file=sys.stderr)
    asyncio.run(run())
    print("adjudication done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
