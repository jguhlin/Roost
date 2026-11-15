#!/usr/bin/env python3
"""
LLM metadata fixer (D63): fix bad titles, authors, summaries via LLM.
Targets papers with known-bad metadata (array fragments, privacy junk,
placeholder titles, smith_gannet numbered IDs).

One LLM call per paper: reads first 3k chars of markdown, extracts
real title + authors + one-line summary.

Usage: pixi run python scripts/papers/llm_fix_meta.py [--workers 32] [--limit N]
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

BAD_PATTERNS = [
    re.compile(r"^\[.*\]"),
    re.compile(r"your privacy|cookie|green line|observed farm", re.I),
    re.compile(r"bioRxiv preprint doi"),
    re.compile(r"^smith gannet\d* \d+$", re.I),
    re.compile(r"^\.?the (chicken|duck) is", re.I),
    re.compile(r"^\.?all of the", re.I),
]


def is_bad_title(t):
    if not t or len(t) < 25:
        return True
    if t.startswith(("Input ", "Task ")) and len(t.split()) <= 3:
        return True
    return any(p.search(t) for p in BAD_PATTERNS)


def llm_extract(pid, head, url, model):
    prompt = f"""Extract the metadata from this research paper's first page.

Reply ONLY with strict JSON:
{{"title": "<the actual paper title, as printed>",
  "authors": "<first 3-5 authors, comma-separated, or empty string>",
  "summary": "<one sentence describing what this paper is about>"}}

Rules:
- The title must be the ACTUAL research paper title, not a header, privacy notice,
  figure caption, or preamble text
- If you cannot find a clear title, use the first complete sentence that describes the study
- Authors: look for name lists after the title. Format: "Last FI, Last FI, ..."
- Summary: what the paper studies/founds, in plain language

Paper ID: {pid}
First page:
{head[:3000]}"""

    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You extract research paper metadata. Reply ONLY with the JSON object."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1000, "temperature": 0.1,
        }, timeout=180)
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            text = msg["reasoning_content"].strip()

        # find last JSON
        candidates = re.findall(r"\{[^{}]*\}", text, re.DOTALL)
        for cand in reversed(candidates):
            try:
                d = json.loads(cand)
                title = d.get("title", "")
                if title and len(title) > 20 and "<" not in title:
                    return {
                        "title": title[:200].strip(),
                        "authors": (d.get("authors") or "").strip()[:200],
                        "summary": (d.get("summary") or "").strip()[:400],
                    }
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    todo = []
    for p in papers:
        if is_bad_title(p.get("title") or ""):
            md = MD_DIR / f"{p['id']}.md"
            if md.exists():
                todo.append(p)
    if args.limit:
        todo = todo[:args.limit]

    print(f"{len(papers)} papers · {len(todo)} need LLM title extraction")

    def work(p):
        md = MD_DIR / f"{p['id']}.md"
        head = md.read_text(errors="ignore")[:3500]
        return p, llm_extract(p["id"], head, args.url, args.model)

    n_fixed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (p, got) in enumerate(ex.map(work, todo), 1):
            if got.get("title"):
                p["title"] = got["title"]
                if got.get("authors") and not p.get("authors"):
                    p["authors"] = got["authors"]
                if got.get("summary") and not p.get("summary"):
                    p["summary"] = got["summary"]
                n_fixed += 1
            if i % 20 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] fixed {n_fixed}")

    PAPERS_JSON.write_text(json.dumps(data, indent=1))

    still_bad = [p["id"] for p in papers if is_bad_title(p.get("title") or "")]
    print(f"\nfixed {n_fixed} · still bad: {len(still_bad)}")
    if still_bad[:5]:
        print("  examples:", [(pid, next(x.get('title', '')[:40] for x in papers if x['id'] == pid)) for pid in still_bad[:5]])


if __name__ == "__main__":
    main()
