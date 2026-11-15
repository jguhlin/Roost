#!/usr/bin/env python3
"""Cross-briefing synthesis — consensus vs conflict theme cards (LLM).

Groups briefings deterministically (connected components over shared cited
papers, ≥2 shared citations), then asks the LLM once per group for a theme
card: consensus, conflicts, open questions. No LLM grouping — the join is
deterministic; the LLM only writes the card.

Output: web/public/data/research_synthesis.json
  {"meta": {...}, "themes": [{"id", "title", "briefings": [slugs],
    "theme": "...", "consensus": [...], "conflicts": [...],
    "open_questions": [...], "confidence": "high|medium|low"}]}
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from llm_analyze_papers import call_llm, parse_json_response  # noqa: E402

BRIEF_DIR = ROOT / "web" / "public" / "data" / "research_briefings"
OUT = ROOT / "web" / "public" / "data" / "research_synthesis.json"
BASE = os.environ.get("LLM_URL", "http://127.0.0.1:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
CONCURRENCY = 4
MIN_SHARED = 2

CITE = re.compile(r"\[([a-z0-9_\-\.]+)\]")


def briefing_citations(b: dict) -> set[str]:
    cites: set[str] = set()
    for sec in b.get("sections") or []:
        cites.update(CITE.findall(sec.get("body", "")))
    for h in b.get("hypotheses") or []:
        for f in (h.get("evidence_for") or []) + (h.get("evidence_against") or []):
            cites.update(CITE.findall(str(f)))
    return cites


def group_briefings(briefings: list[dict]) -> list[list[dict]]:
    """Connected components over shared citations (>= MIN_SHARED papers)."""
    n = len(briefings)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if len(briefings[i]["_cites"] & briefings[j]["_cites"]) >= MIN_SHARED:
                union(i, j)
    groups: dict[int, list[dict]] = defaultdict(list)
    for i, b in enumerate(briefings):
        groups[find(i)].append(b)
    return sorted(groups.values(), key=len, reverse=True)


def card_prompt(group: list[dict]) -> str:
    parts = []
    for b in group:
        hyps = "\n".join(f"    - {h['hypothesis']}" for h in b.get("hypotheses", [])[:4])
        parts.append(f"""### {b['title']}
question: {b.get('question', '')}
summary: {b.get('summary', '')}
hypotheses:
{hyps}""")
    joined = "\n\n".join(parts)
    return f"""You are synthesising {len(group)} research briefings from an avian influenza
(H5N1) literature agent. They were grouped because they share cited papers.

{joined}

Write ONE synthesis theme card for this group as JSON:
{{
  "theme": "short theme name (3-8 words)",
  "consensus": ["statement the briefings agree on, with [paper_id] where possible", "..."],
  "conflicts": ["statement of disagreement/uncertainty between or within briefings", "..."],
  "open_questions": ["the sharpest still-open question(s) this group leaves", "..."],
  "confidence": "high|medium|low"
}}
Rules: 2-5 items per list, plain scientific prose, cite [paper_id]s from the
briefings when a claim rests on them, do not invent papers or results."""


async def synth_group(client, sem, group):
    async with sem:
        for attempt in range(3):
            try:
                out = await call_llm(client, card_prompt(group), 0.2, BASE, MODEL)
                parsed = parse_json_response(out)
                if isinstance(parsed, dict) and parsed.get("consensus"):
                    return parsed
            except Exception as e:
                print(f"  attempt {attempt+1} failed: {e}", file=sys.stderr)
                await asyncio.sleep(4)
        return None


async def run() -> int:
    briefings = []
    for f in sorted(BRIEF_DIR.glob("*.json")):
        if f.name == "index.json":
            continue
        b = json.loads(f.read_text(encoding="utf-8"))
        b["_cites"] = briefing_citations(b)
        briefings.append(b)
    print(f"{len(briefings)} briefings loaded")

    groups = group_briefings(briefings)
    print(f"{len(groups)} theme groups "
          f"(sizes: {[len(g) for g in groups]})")

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(synth_group(client, sem, g) for g in groups))

    themes = []
    for g, card in zip(groups, results):
        slugs = [b["slug"] for b in g]
        if card is None:
            themes.append({"id": "+".join(slugs[:3])[:60], "briefings": slugs,
                           "title": g[0]["title"],
                           "theme": "synthesis unavailable (LLM call failed)",
                           "consensus": [], "conflicts": [],
                           "open_questions": [b["question"] for b in g[:3]],
                           "confidence": "low"})
            continue
        themes.append({
            "id": "+".join(slugs[:3])[:60],
            "briefings": slugs,
            "title": card.get("theme", "theme"),
            "theme": card.get("theme", ""),
            "consensus": card.get("consensus", []),
            "conflicts": card.get("conflicts", []),
            "open_questions": card.get("open_questions", []),
            "confidence": card.get("confidence", "medium"),
        })

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "n_briefings": len(briefings),
            "n_themes": len(themes),
            "grouping": f"connected components over shared [paper_id] citations "
                        f"(>= {MIN_SHARED} shared)",
            "model": MODEL,
        },
        "themes": themes,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    ok = sum(1 for t in themes if t["consensus"])
    print(f"synthesis → {OUT.relative_to(ROOT)} "
          f"({len(themes)} themes, {ok} with cards)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
