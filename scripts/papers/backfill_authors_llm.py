#!/usr/bin/env python3
"""LLM pass: extract full author lists from paper fulltext (no-DOI papers).

For papers marked `authors_source: "llm_pending"` in papers.json (no DOI,
no Crossref), send the head of docs/papers_md/{id}.md to the LLM and ask
for a structured author list. Idempotent: skips papers that already have
authors_full. Writes results incrementally (every paper) so interruptions
never lose work.

Usage: LLM_BASE_URL=http://localhost:8005/v1 \
  pixi run python scripts/papers/backfill_authors_llm.py [--limit N]
"""
import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"
BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

PROMPT = """From the paper text below, extract the COMPLETE author list as JSON.
Return ONLY a JSON array: [{"family": "Surname", "given": "Initials or given names"}].
Rules:
- family = surname; given = given names/initials (e.g. "G." or "Gang")
- include EVERY author, in order; no "et al."
- if the text shows no author list, return []
- consortium/group names: put the group name in family, empty given
- plain JSON, no markdown fences, no commentary."""


def call_llm(text: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You extract bibliographic metadata. Output strict JSON only."},
            {"role": "user", "content": PROMPT + "\n\n---\n" + text},
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(r.read())
    return out["choices"][0]["message"]["content"].strip()


def parse_authors(raw: str) -> list:
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        arr = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("["), raw.rfind("]")
        if start < 0 or end <= start:
            return []
        arr = json.loads(raw[start:end + 1])
    out = []
    for a in arr if isinstance(arr, list) else []:
        if isinstance(a, dict) and a.get("family"):
            out.append({"family": str(a["family"]).strip(),
                        "given": str(a.get("given", "") or "").strip()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--head-chars", type=int, default=6000,
                    help="chars of paper head to send (authors are up front)")
    args = ap.parse_args()

    pj = json.loads(PAPERS_JSON.read_text())
    papers = pj["papers"] if isinstance(pj, dict) else pj
    pending = [p for p in papers
               if isinstance(p, dict)
               and p.get("authors_source") in ("llm_pending", "crossref_failed")
               and not p.get("authors_full")]
    if args.limit:
        pending = pending[:args.limit]
    print(f"llm_pending papers: {len(pending)} | endpoint {BASE_URL} model {MODEL}")

    done = skipped = failed = 0
    for p in pending:
        md = MD_DIR / f"{p['id']}.md"
        if not md.exists():
            p["authors_source"] = "llm_no_fulltext"
            skipped += 1
            continue
        text = md.read_text(errors="ignore")[:args.head_chars]
        try:
            authors = parse_authors(call_llm(text))
        except Exception as e:
            print(f"  {p['id']}: LLM error {str(e)[:100]}")
            failed += 1
            time.sleep(2)
            continue
        if authors:
            p["authors_full"] = authors
            p["authors_source"] = "llm"
            done += 1
            print(f"  {p['id']}: {len(authors)} authors")
        else:
            p["authors_source"] = "llm_not_found"
            skipped += 1
        # incremental save — never lose work
        PAPERS_JSON.write_text(json.dumps(pj, indent=1))
    print(f"llm author pass: extracted={done} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
