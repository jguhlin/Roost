#!/usr/bin/env python3
"""Paper steward agent — iterative triage over per-paper records.

Each round: review the record (post previous fixes) → propose actions →
apply safe ones → for flagged issues, an INVESTIGATE sub-call sees the
issue + local context and proposes a concrete fix. Rounds continue until
the model returns no actions (done) or max rounds hit (residue escalates
to the human queue). Ledger records every round; nothing applies silently.

Auto-apply appliers (scoped):
  papers.json: set_metadata (journal/year/doc_type/category), set_stream,
    set_tier, improve_summary, add_topics, remove_topics
  paper_extras.parquet: set_mutation_genes [{mutation, gene}]
  discovery: find_related -> searxng -> PAPER_WISHLIST.md
Everything else (or unresolved after MAX_ROUNDS) -> steward_queue.jsonl.

Usage:
  LLM_BASE_URL=http://localhost:8005/v1 pixi run python \
      scripts/papers/paper_steward.py --paper mink_spain2022
  ... --limit 5    (least-recently-stewarded records)
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / "data" / "papers"
RECORDS = PAPERS / "records"
QUEUE = PAPERS / "steward_queue.jsonl"
LEDGER = PAPERS / "steward_ledger.jsonl"
WISHLIST = ROOT / "PAPER_WISHLIST.md"
PAPERS_JSON = ROOT / "web/public/data/papers.json"
EXTRAS = PAPERS / "paper_extras.parquet"
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
SEARXNG = os.environ.get("SEARXNG_URL", "http://localhost:8888/search")
MAX_ROUNDS = 8

SCHEMA = """Return ONLY a JSON array of action objects:
 {"action":"set_metadata","field":"journal|year|doc_type|category","value":"...","reason":"..."}
 {"action":"add_keywords","keywords":["..."]}
 {"action":"set_stream","stream":"host-immunity|epi-surveillance|pathology|modelling|policy-management|tangential|true-off-topic","reason":"..."}
 {"action":"set_tier","tier":1,"reason":"..."}
 {"action":"improve_summary","summary":"..."}
 {"action":"add_topics","topics":["..."]} / {"action":"remove_topics","topics":["..."]}
 {"action":"set_mutation_genes","fixes":[{"mutation":"T271A","gene":"PB2"}]}
 {"action":"find_related","query":"...","why":"..."}
 {"action":"flag_issue","issue":"..."}
Empty array [] when the record needs nothing. No commentary."""

FINAL_ROUND_NOTE = """
THIS IS YOUR FINAL ROUND. If — and only if — you are mid-investigation and
absolutely need more rounds to finish resolving the record, return exactly:
 [{"action":"request_more_rounds","reason":"..."}]
and NOTHING else. Otherwise return your final actions or []."""

INVESTIGATE = """You flagged an issue in a paper record and must now resolve it.
Issue: {issue}
Relevant record context: {context}
Propose the concrete fix as actions using this schema (JSON array only):
 {"action":"remove_topics","topics":["..."]} {"action":"add_topics","topics":["..."]}
 {"action":"set_mutation_genes","fixes":[{"mutation":"...","gene":"..."}]}
 {"action":"set_metadata","field":"...","value":"..."} {"action":"improve_summary","summary":"..."}
If it genuinely needs a human, return [{"action":"flag_issue","issue":"UNRESOLVABLE: ..."}]."""

SAFE_FIELDS = {"journal", "year", "doc_type", "category"}
rec_extras_cache = {}  # pid -> freshly-fixed mutations (view freshness)


def llm(prompt, system="You maintain bibliographic records. Strict JSON only."):
    body = json.dumps({"model": MODEL, "temperature": 0.1, "max_tokens": 2048,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def parse_actions(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        arr = json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("["), raw.rfind("]")
        try:
            arr = json.loads(raw[s:e + 1]) if 0 <= s < e else []
        except json.JSONDecodeError:
            arr = []  # malformed model output — treat as no actions
    return [a for a in arr if isinstance(a, dict) and a.get("action")]


def searxng(query):
    try:
        url = f"{SEARXNG}?q={urllib.parse.quote(query)}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Roost/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("results", [])[:5]
    except Exception:
        return []


def append_wishlist(why, query, title, url):
    row = f"| {time.strftime('%Y-%m-%d')} | {why[:60]} | {query[:60]} | {title[:60]} | {url[:80]} |\n"
    WISHLIST.write_text(WISHLIST.read_text().replace("\n## Acquired", row + "\n## Acquired"))


def fix_mutation_genes(pid, fixes):
    import polars as pl
    ex = pl.read_parquet(EXTRAS)
    row = ex.filter(pl.col("id") == pid)
    if not row.height:
        return "no extras row"
    muts = json.loads(row.row(0, named=True).get("mutations") or "[]")
    by_mut = {m.get("mutation"): m for m in muts}
    n = 0
    for f in fixes:
        m = by_mut.get(f.get("mutation"))
        if m is not None and f.get("gene"):
            m["gene"] = f["gene"]; n += 1
    if not n:
        return "no matching mutations"
    ex = ex.with_columns(pl.when(pl.col("id") == pid)
                         .then(pl.lit(json.dumps(muts)))
                         .otherwise(pl.col("mutations")).alias("mutations"))
    ex.write_parquet(EXTRAS)
    rec_extras_cache[pid] = muts  # refresh the in-memory view
    return f"fixed {n} mutation genes"


def apply_action(pid, a, p, deferred):
    act = a["action"]
    if act == "set_metadata" and a.get("field") in SAFE_FIELDS:
        p[a["field"]] = a["value"]; return f"set {a['field']}"
    if act == "set_stream":
        p["_stream"] = a.get("stream"); p["_stream_reason"] = a.get("reason", "")
        return f"stream={a.get('stream')}"
    if act == "set_tier":
        p["_tier"] = a.get("tier"); return f"tier={a.get('tier')}"
    if act == "improve_summary" and a.get("summary"):
        p["summary"] = a["summary"][:500]; return "summary improved"
    if act == "add_topics" or act == "remove_topics":
        topics = set(p.get("topics") or [])
        topics |= set(a.get("topics") or []) if act == "add_topics" else set()
        topics -= set(a.get("topics") or []) if act == "remove_topics" else set()
        p["topics"] = sorted(topics); return f"{act} {a.get('topics')}"
    if act == "set_mutation_genes":
        return fix_mutation_genes(pid, a.get("fixes") or [])
    if act == "find_related":
        res = searxng(a.get("query", ""))
        top = res[0] if res else {}
        append_wishlist(a.get("why", "related"), a.get("query", ""),
                        top.get("title", ""), top.get("url", ""))
        return f"wishlisted: {top.get('title', '?')[:40]}"
    deferred.append(a)
    return f"QUEUED {act}"


def steward(pid, papers_by_id):
    rec_path = RECORDS / f"{pid}.json"
    if not rec_path.exists():
        return None
    rec = json.loads(rec_path.read_text())
    p = papers_by_id[pid]
    view = lambda: {
        "metadata": {k: v for k, v in p.items() if k not in ("authors_full",)},
        "authors_n": len(rec["authors"]["roster"]),
        "analysis_steps": rec["analysis"],
        "findings_sample": rec["findings"][:8],
        "keywords": [k["keyword"] for k in rec["keywords"]][:20],
        "claims": rec["claims"],
        "extras": {**rec.get("extras", {}),
                   "mutations": rec_extras_cache.get(pid, rec.get("extras", {}).get("mutations"))},
        "genes_sample": rec["genes"][:25], "species": rec["species"][:15],
    }
    rounds, applied, seen = [], [], set()
    rnd, resets, MAX_RESETS = 1, 0, 2
    while rnd <= MAX_ROUNDS:
        schema = SCHEMA + (FINAL_ROUND_NOTE if rnd == MAX_ROUNDS else
                           f"\n(Round {rnd} of {MAX_ROUNDS}.)")
        raw = llm("Paper record (JSON, includes prior fixes):\n"
                  + json.dumps(view(), indent=1)[:9000] + "\n\n" + schema)
        actions = [a for a in parse_actions(raw)
                   if (a["action"], str(a.get("field") or a.get("summary") or
                                         a.get("keywords") or a.get("issue"))[:40]) not in seen
                   or a["action"] in ("flag_issue", "find_related")]
        for a in parse_actions(raw):
            seen.add((a["action"], str(a.get("field") or a.get("summary") or
                                        a.get("keywords") or a.get("issue"))[:40]))
        # final-round escape hatch: agent-requested round reset (bounded)
        if rnd == MAX_ROUNDS and len(actions) == 1 \
                and actions[0].get("action") == "request_more_rounds" \
                and resets < MAX_RESETS:
            resets += 1
            rounds.append({"round": rnd, "result":
                           f"reset granted ({resets}/{MAX_RESETS}): "
                           f"{str(actions[0].get('reason'))[:80]}"})
            rnd += 1
            continue
        if not actions:
            rounds.append({"round": rnd, "result": "clean"})
            break
        deferred, did = [], []
        for a in actions:
            if a["action"] == "flag_issue":
                # investigate: agent resolves its own flag
                ctx = json.dumps({"topics": p.get("topics"), "extras": rec["extras"],
                                  "summary": p.get("summary")})[:3000]
                fixes = parse_actions(llm(
                    INVESTIGATE.replace("{issue}", str(a.get("issue", "")))
                               .replace("{context}", ctx)))
                fixes = [f for f in fixes if f.get("action") != "flag_issue"]
                if fixes:
                    for f in fixes:
                        did.append("fix:" + apply_action(pid, f, p, deferred))
                else:
                    deferred.append(a); did.append("UNRESOLVABLE flag")
            else:
                did.append(apply_action(pid, a, p, deferred))
        with open(QUEUE, "a") as f:
            for d in deferred:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M"),
                                    "paper": pid, **d}) + "\n")
        rounds.append({"round": rnd, "actions": did})
        applied += did
        rnd += 1
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M"), "paper": pid,
                            "rounds": rounds}) + "\n")
    return applied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args()
    pj = json.loads(PAPERS_JSON.read_text())
    papers = pj["papers"] if isinstance(pj, dict) else pj
    by_id = {p["id"]: p for p in papers}
    led = set()
    if LEDGER.exists():
        led = {json.loads(l)["paper"] for l in LEDGER.read_text().splitlines() if l.strip()}
    ids = [args.paper] if args.paper else [p["id"] for p in papers if p["id"] not in led][:args.limit]
    for pid in ids:
        res = steward(pid, by_id)
        print(f"  {pid}: {res if res is not None else 'no record'}")
    PAPERS_JSON.write_text(json.dumps(pj, indent=1))
    print(f"steward complete ({len(ids)} papers, iterative, MAX_ROUNDS={MAX_ROUNDS})")


if __name__ == "__main__":
    main()
