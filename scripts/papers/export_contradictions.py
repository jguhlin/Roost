#!/usr/bin/env python3
"""Export adjudication results for the public contradictions page.

bundles contradictions (with paper titles/years on each side, verdicts
normalized), cluster consensus and open questions into
web/public/data/papers/contradictions.json.

Run:  pixi run python scripts/papers/export_contradictions.py
"""
from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from resolve_paper_ids import resolve_id, resolve_contradictions  # noqa: E402
X = ROOT / "data" / "papers" / "contradictions.parquet"
V = ROOT / "data" / "papers" / "cluster_verdicts.parquet"
C = ROOT / "data" / "papers" / "claim_clusters.parquet"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
OUT = ROOT / "web" / "public" / "data" / "papers" / "contradictions.json"

VERDICT_NORM = {
    "real": "real", "context-dependent": "context-dependent",
    "apparent": "apparent",
}


def main() -> int:
    papers = {p["id"]: p for p in
              json.loads(PAPERS_JSON.read_text())["papers"]}

    def paper_meta(pid: str) -> dict:
        p = papers.get(str(pid), {})
        return {"id": pid, "title": (p.get("title") or "")[:120],
                "year": p.get("year")}

    x = pl.read_parquet(X).to_dicts()
    v = pl.read_parquet(V)
    c = pl.read_parquet(C)
    n_clusters = c.height

    # --- deterministic paper-ID fuzzy matching ---
    valid_ids = list(papers.keys())
    titles = {pid: p.get("title", "") for pid, p in papers.items()}
    x, fuzzy_stats = resolve_contradictions(x, valid_ids, titles)
    print(f"  ID resolution: {fuzzy_stats}", file=sys.stderr)

    verdict_counts = {}
    reason_counts = {}
    items = []
    dropped = {"self_pair": 0, "unresolvable": 0}
    for r in x:
        verdict_raw = str(r.get("verdict", "")).strip().lower()
        verdict = VERDICT_NORM.get(verdict_raw, "unclassified")
        pa, pb = str(r.get("paper_a", "")), str(r.get("paper_b", ""))
        if pa == pb or not pa or not pb:
            dropped["self_pair"] += 1
            continue
        if pa not in papers or pb not in papers:
            dropped["unresolvable"] += 1
            continue
        reason = str(r.get("reason_type", "")).strip().lower() or "other"
        tags = r.get("tags")
        if isinstance(tags, str):
            import ast
            try:
                tags = json.loads(tags)
            except (ValueError, TypeError):
                try:
                    tags = ast.literal_eval(tags)
                except (ValueError, SyntaxError, TypeError):
                    tags = [tags]
        if not isinstance(tags, list):
            tags = []
        tags = [str(t)[:24] for t in tags if isinstance(t, (str, int))][:4]
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        items.append({
            "cluster": r.get("cluster"),
            "topic": str(r.get("topic", ""))[:200],
            "what": str(r.get("what_conflicts", ""))[:400],
            "verdict": verdict,
            "reason": reason,
            "tags": tags,
            "explanation": str(r.get("explanation", ""))[:500],
            # md5[:12] i18n keys (same convention as eh/fh) — let the web
            # Contradictions page translate adjudication text via ft().
            "th": hashlib.md5(str(r.get("topic", "")).encode("utf-8")).hexdigest()[:12],
            "wh": hashlib.md5(str(r.get("what_conflicts", "")).encode("utf-8")).hexdigest()[:12],
            "ex": hashlib.md5(str(r.get("explanation", "")).encode("utf-8")).hexdigest()[:12],
            "a": paper_meta(pa),
            "b": paper_meta(pb),
        })
    # real first, then context-dependent, then apparent, then rest
    order = {"real": 0, "context-dependent": 1, "apparent": 2,
             "unclassified": 3}
    items.sort(key=lambda i: (order[i["verdict"]], i["cluster"] or ""))

    open_qs = []
    cons = []
    for r in v.to_dicts():
        for q in json.loads(r.get("open_questions") or "[]")[:12]:
            if isinstance(q, str) and len(q) > 15:
                open_qs.append({"cluster": r["cluster"], "q": q[:300]})
        for s in json.loads(r.get("consensus") or "[]")[:12]:
            if isinstance(s, str) and len(s) > 15:
                cons.append({"cluster": r["cluster"], "s": s[:300]})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "meta": {
            "generated": datetime.fromtimestamp(
                __import__("time").time(), tz=timezone.utc)
                    .isoformat(timespec="seconds"),
            "n_clusters": n_clusters,
            "n_contradictions": len(items),
            "verdict_counts": verdict_counts,
            "reason_counts": reason_counts,
            "dropped": dropped,
            "n_open_questions": len(open_qs),
            "n_consensus": len(cons),
            "method": "LLM adjudication of typed claim clusters "
                      "(scripts/papers/llm_claims_adjudicate.py); see Methods",
        },
        "contradictions": items,
        "open_questions": open_qs,
        "consensus": cons,
    }))
    print(f"wrote {OUT.name}: {len(items)} contradictions "
          f"({verdict_counts}), {len(open_qs)} open questions, "
          f"{len(cons)} consensus points, {n_clusters} clusters",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
