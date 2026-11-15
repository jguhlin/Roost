#!/usr/bin/env python3
"""
Comprehensive metadata quality pass (D65): fix summaries and categories
for ALL papers with array-fragment summaries or wrong categories.

For each paper: LLM reads the first ~15k chars and returns:
  - proper one-sentence summary (not a findings array)
  - correct category from our standard set

Usage: pixi run python scripts/papers/fix_metadata_quality.py [--workers 32]
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

ARR_RE = re.compile(r"^\[")
CATEGORIES = [
    "Immunology", "Mammalian Spillover", "Pathogenesis", "Epidemiology",
    "Vaccines", "Wild Birds", "Poultry", "Viral Evolution",
    "Cross-species Transmission", "Human Infection", "Host Genomics",
    "Avian Influenza", "Methods", "Other",
]


def is_bad_summary(s):
    if not s:
        return True
    s = str(s)
    if ARR_RE.match(s):
        return True  # array fragment
    if len(s) < 30:
        return True
    if s.startswith(("No research", "The provided text", "This document")):
        return True
    return False


def llm_meta(pid, title, head, url, model):
    prompt = f"""Paper title: {title}

Based on the title and this excerpt, provide:
1. A ONE-SENTENCE summary of what this paper is about (plain language, max 200 chars)
2. The best category from: {", ".join(CATEGORIES)}

Reply ONLY with JSON:
{{"summary": "<one sentence>", "category": "<category>"}}"""

    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You classify research papers. Reply ONLY with the JSON object."},
                {"role": "user", "content": prompt + f"\n\nExcerpt:\n{head[:12000]}"},
            ],
            "max_tokens": 800, "temperature": 0.1,
        }, timeout=180)
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            rc = msg["reasoning_content"].strip()
            m = re.search(r"\{[^{}]*\}", rc, re.DOTALL)
            if m:
                text = m.group(0)

        if text:
            candidates = re.findall(r"\{[^{}]*\}", text, re.DOTALL)
            for cand in reversed(candidates):
                try:
                    d = json.loads(cand)
                    summary = (d.get("summary") or "").strip()
                    category = (d.get("category") or "").strip()
                    if summary and len(summary) > 20 and not summary.startswith("["):
                        if category not in CATEGORIES:
                            category = "Other"
                        return {"summary": summary[:300], "category": category}
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return {}


def flatten_summary(s):
    """Flatten array-string to readable text as fallback."""
    s = str(s).strip()
    if s.startswith("[") and s.endswith("]"):
        # extract quoted strings
        parts = re.findall(r"'([^']{10,200})'", s)
        if parts:
            return ". ".join(p.strip() for p in parts[:2])[:300]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    # Pass 1: deterministic flatten of array summaries
    n_flattened = 0
    for p in papers:
        s = p.get("summary")
        if s and is_bad_summary(s):
            flat = flatten_summary(s)
            if flat and not is_bad_summary(flat):
                p["summary"] = flat
                n_flattened += 1

    # Pass 2: LLM fix for papers still needing it (bad summary OR suspicious category)
    todo = []
    for p in papers:
        needs_summary = is_bad_summary(p.get("summary"))
        needs_category = not p.get("category") or p.get("category") == "Other"
        if needs_summary or needs_category:
            md = MD_DIR / f"{p['id']}.md"
            if md.exists() and md.stat().st_size > 1000:
                todo.append(p)

    print(f"{len(papers)} papers · {n_flattened} flattened · {len(todo)} need LLM metadata")

    def work(p):
        md = MD_DIR / f"{p['id']}.md"
        head = md.read_text(errors="ignore")[:15000]
        return p, llm_meta(p["id"], p.get("title") or "", head, args.url, args.model)

    n_summary = n_category = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (p, got) in enumerate(ex.map(work, todo), 1):
            if got.get("summary") and is_bad_summary(p.get("summary")):
                p["summary"] = got["summary"]
                n_summary += 1
            if got.get("category") and (not p.get("category") or p.get("category") == "Other"):
                p["category"] = got["category"]
                n_category += 1
            if i % 50 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] summaries={n_summary} categories={n_category}")

    PAPERS_JSON.write_text(json.dumps(data, indent=1))

    from collections import Counter
    still_bad = sum(1 for p in papers if is_bad_summary(p.get("summary")))
    cats = Counter(p.get("category") for p in papers)
    print(f"\nfixed: {n_summary} summaries, {n_category} categories")
    print(f"still bad summaries: {still_bad}")
    print("categories:", dict(cats.most_common(15)))


if __name__ == "__main__":
    main()
