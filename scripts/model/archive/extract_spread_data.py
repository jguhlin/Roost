#!/usr/bin/env python3
"""
Spread model data extraction (D57): per-paper LLM extraction of
migration/spread metadata from epi-scoped corpus papers.

Extracts: flyway, species roles, spread mechanisms, geography, seasonality,
key finding → data/model/spread_evidence.jsonl

Usage: pixi run python scripts/model/extract_spread_data.py [--url ... --model ... --workers N]
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"
OUT = ROOT / "data" / "model" / "spread_evidence.jsonl"

PROMPT = """You are extracting migration and spread data from avian influenza research papers.

From the paper excerpt below, extract ONLY what is explicitly stated. Reply with strict JSON:
{{
  "flyways": ["<flyway names mentioned, e.g. Atlantic, Mississippi, Central, Pacific, East Asian-Australasian>"],
  "species_roles": [{{"species": "<name>", "role": "<reservoir|amplifier|bridge|dead_end|sentinel|vector>"}}],
  "spread_mechanisms": ["<mechanisms: wild_bird_migration|poultry_trade|live_markets|farm_to_farm|environmental|fomites|unknown>"],
  "geography": ["<countries/regions>"],
  "seasonality": "<spring|autumn|winter|summer|year_round|not_stated>",
  "key_spread_finding": "<one sentence: what this paper contributes to understanding H5N1 spread>"
}}

If the paper doesn't discuss spread/migration, return {{"not_relevant": true}}.

Title: {title}
Excerpt: {excerpt}"""


def extract(pid, title, excerpt, url, model):
    prompt = PROMPT.replace("{title}", title[:200]).replace("{excerpt}", excerpt[:3000])
    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You extract structured data from research papers. Reply ONLY with the JSON object."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1500, "temperature": 0.1,
        }, timeout=180)
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            text = msg["reasoning_content"].strip()
        # find last JSON object
        candidates = re.findall(r"\{[^{}]*\}", text, re.DOTALL)
        for cand in reversed(candidates):
            try:
                d = json.loads(cand)
                if "flyways" in d or "not_relevant" in d:
                    d["_pid"] = pid
                    d["_title"] = title[:120]
                    return d
            except json.JSONDecodeError:
                continue
        # try nested
        m = None
        for m in re.finditer(r"\{.*\}", text, re.DOTALL):
            pass
        if m:
            try:
                d = json.loads(m.group(0))
                d["_pid"] = pid
                d["_title"] = title[:120]
                return d
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return {"_pid": pid, "_title": title[:120], "error": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = [p for p in data["papers"]
              if p.get("scope") in ("avian-epi", "epidemiology", "avian", "mammalian")
              and p.get("title")]

    # prioritize epi papers
    epi = [p for p in papers if p.get("scope") in ("avian-epi", "epidemiology")]
    other = [p for p in papers if p.get("scope") in ("avian", "mammalian")]
    ordered = epi + other

    if args.limit:
        ordered = ordered[:args.limit]

    print(f"{len(ordered)} papers to extract ({len(epi)} epi + {len(other)} avian/mammalian)")

    def work(p):
        md = MD_DIR / f"{p['id']}.md"
        excerpt = md.read_text(errors="ignore")[:4000] if md.exists() else ""
        if not excerpt:
            excerpt = p.get("summary") or ""
        return extract(p["id"], p.get("title") or "", excerpt, args.url, args.model)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        n_relevant = n_not = n_err = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for i, result in enumerate(ex.map(work, ordered), 1):
                f.write(json.dumps(result) + "\n")
                if result.get("error"):
                    n_err += 1
                elif result.get("not_relevant"):
                    n_not += 1
                else:
                    n_relevant += 1
                if i % 20 == 0 or i == len(ordered):
                    print(f"  [{i}/{len(ordered)}] relevant={n_relevant} not_relevant={n_not} errors={n_err}")

    print(f"\nDone: {n_relevant} relevant, {n_not} not relevant, {n_err} errors → {OUT}")


if __name__ == "__main__":
    main()
