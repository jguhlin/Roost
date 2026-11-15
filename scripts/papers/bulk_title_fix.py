#!/usr/bin/env python3
"""
Bulk LLM title extraction (D64): for papers with bad titles (array fragments,
summaries-as-titles, junk), send the full markdown to muse-glimmer and get
the actual paper title + authors + summary.

Simple prompt format (proven to work with muse-glimmer's reasoning style).

Usage: pixi run python scripts/papers/bulk_title_fix.py [--workers 16]
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

BAD_RE = re.compile(
    r"^\[|your privacy|cookie|no research|insufficient|cannot extract"
    r"|^\.?the (chicken|duck)|^\.?all of|^vSolid|virus titers"
    r"|Zotero login|Manual review|Needs manual"
    r"|^\d+\.\s+[A-Z][a-z]+ [A-Z]",  # reference entries
    re.I,
)


def is_bad(title):
    if not title or len(title) < 25:
        return True
    return bool(BAD_RE.search(title))


def extract_via_llm(pid, doc_text, url, model):
    """Simple, proven prompt format for muse-glimmer."""
    # truncate to fit context comfortably
    text = doc_text[:40000]

    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system",
                 "content": "Reply ONLY with a JSON object. No other text, no reasoning, just the JSON."},
                {"role": "user",
                 "content": f"""Read this research paper and extract metadata. Reply with JSON:
{{"title": "<the actual paper title as printed>", "authors": "<first 3 authors or empty>", "summary": "<one sentence>", "is_paper": true/false}}

Paper content:
{text[:30000]}"""},
            ],
            "max_tokens": 3000, "temperature": 0.0,
        }, timeout=300)
        msg = r.json()["choices"][0]["message"]
        raw = (msg.get("content") or "").strip()
        if not raw and msg.get("reasoning_content"):
            # take the last non-empty line of reasoning that looks like JSON
            rc = msg["reasoning_content"].strip()
            for line in reversed(rc.split("\n")):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    raw = line
                    break
            if not raw:
                # try to find JSON anywhere in reasoning
                m = re.search(r"\{[^{}]*\"title\"[^{}]*\}", rc, re.DOTALL)
                if m:
                    raw = m.group(0)

        if not raw:
            return {}

        candidates = re.findall(r"\{[^{}]*\}", raw, re.DOTALL)
        for cand in reversed(candidates):
            try:
                d = json.loads(cand)
                title = (d.get("title") or "").strip()
                if title and len(title) > 20 and not is_bad(title):
                    return {
                        "title": title[:200],
                        "authors": (d.get("authors") or "").strip()[:200],
                        "summary": (d.get("summary") or "").strip()[:400],
                        "is_paper": d.get("is_paper", True),
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
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    todo = []
    for p in papers:
        if is_bad(p.get("title") or ""):
            md = MD_DIR / f"{p['id']}.md"
            if md.exists() and md.stat().st_size > 500:
                todo.append(p)
            elif md.exists():
                print(f"  SKIP {p['id']}: markdown too small ({md.stat().st_size}b)")

    print(f"{len(papers)} papers · {len(todo)} need LLM title extraction")

    def work(p):
        md = MD_DIR / f"{p['id']}.md"
        doc = md.read_text(errors="ignore")
        return p, extract_via_llm(p["id"], doc, args.url, args.model)

    n_fixed = n_not_paper = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (p, got) in enumerate(ex.map(work, todo), 1):
            if got.get("is_paper") is False:
                p["title"] = f"[Not a research paper — {p['id']}]"
                n_not_paper += 1
            elif got.get("title"):
                p["title"] = got["title"]
                if got.get("authors") and not p.get("authors"):
                    p["authors"] = got["authors"]
                if got.get("summary") and not p.get("summary"):
                    p["summary"] = got["summary"]
                n_fixed += 1
            if i % 10 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] fixed={n_fixed} not_paper={n_not_paper}")

    PAPERS_JSON.write_text(json.dumps(data, indent=1))

    still = [x["id"] for x in papers if is_bad(x.get("title") or "")]
    print(f"\nfixed {n_fixed} · not-paper {n_not_paper} · still bad: {len(still)}")
    if still[:5]:
        print("  remaining:", [(pid, next((x.get('title') or '')[:40] for x in papers if x['id'] == pid)) for pid in still[:5]])


if __name__ == "__main__":
    main()
