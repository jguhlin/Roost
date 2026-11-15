#!/usr/bin/env python3
"""
Metadata enrichment pass (D54): per-paper LLM call filling language,
doc_type (peer-reviewed|preprint|thesis|book-chapter|review|report|news),
and species focus into papers.json.

Hybrid: deterministic venue/DOI checks first (bioRxiv → preprint; existing
doc-type markers from markdown win), LLM only for language + species +
ambiguous type. Skips papers already enriched.

Usage:
  pixi run python scripts/papers/enrich_metadata.py [--url ... --model ... --limit N]
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

PREPRINT_VENUES = re.compile(r"biorxiv|medrxiv|preprint|research square", re.I)
REVIEW_HINTS = re.compile(r"\breview\b", re.I)


def deterministic_type(pid: str, paper: dict) -> tuple[str, str | None]:
    """venue/marker-based typing — returns (doc_type, language_or_None)."""
    lang = None
    md = MD_DIR / f"{pid}.md"
    if md.exists():
        head = md.read_text(errors="ignore")[:400]
        if "doc-type: thesis" in head:
            return "thesis", "en"
        if "doc-type: book-chapter" in head:
            return "book-chapter", "en"
        if "doc-type: book-full" in head:
            return "book-full", "en"
        # language from script ratio
        cyr = len(re.findall(r"[\u0400-\u04FF]", head))
        cjk = len(re.findall(r"[\u4E00-\u9FFF\u3040-\u30FF]", head))
        lang = None
        if cyr > 30:
            lang = "ru"
        elif cjk > 30:
            lang = "zh"
    venue = f"{paper.get('journal') or ''} {paper.get('doi') or ''}"
    if PREPRINT_VENUES.search(venue):
        return "preprint", lang
    return "article", lang


def llm_enrich(pid: str, title: str, head: str, url, model) -> dict:
    prompt = f"""Classify this research document. Reply ONLY with strict JSON:
{{"language": "<ISO 639-1 code, e.g. en, ru, zh, es>",
 "doc_type": "<peer-reviewed|preprint|thesis|book-chapter|review|report|correction>",
 "species_focus": ["<species names as written, max 5>"]}}

Title: {title}
Excerpt: {head[:1500]}"""
    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You classify research documents. Reply ONLY with the JSON object."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 800, "temperature": 0.1,
        }, timeout=120)
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            text = msg["reasoning_content"].strip()
        m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if m:
            d = json.loads(m.group(0))
            # strip placeholder echoes (model restating the schema)
            lang = d.get("language", "")
            if not lang or len(lang) > 2 or "<" in lang:
                lang = None
            dt = d.get("doc_type", "")
            if "<" in dt or "|" in dt:
                dt = None
            sf = [s for s in (d.get("species_focus") or [])
                  if isinstance(s, str) and len(s) < 60 and "<" not in s][:5]
            return {"language": lang, "doc_type": dt, "species_focus": sf}
    except Exception:
        pass
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    todo = []
    for p in papers:
        if p.get("language") and p.get("doc_type"):
            continue  # already enriched
        dt, lang = deterministic_type(p["id"], p)
        p.setdefault("doc_type", dt)
        if lang:
            p.setdefault("language", lang)
        md = MD_DIR / f"{p['id']}.md"
        head = md.read_text(errors="ignore")[:2000] if md.exists() else ""
        if head and (not p.get("language") or p.get("doc_type") in ("article", None)
                     or "species_focus" not in p):
            todo.append((p, head))
    if args.limit:
        todo = todo[:args.limit]

    print(f"{len(papers)} papers · {len(todo)} need LLM enrichment")

    def work(item):
        p, head = item
        got = llm_enrich(p["id"], p.get("title") or "", head, args.url, args.model)
        if got.get("language") and not p.get("language"):
            p["language"] = got["language"]
        if got.get("doc_type") and p.get("doc_type") in ("article", None):
            # don't override deterministic types
            if got["doc_type"] in ("preprint", "review", "report", "correction"):
                p["doc_type"] = got["doc_type"]
        if got.get("species_focus") and not p.get("species_focus"):
            p["species_focus"] = [s for s in got["species_focus"] if isinstance(s, str)][:5]
        return p["id"], got.get("doc_type"), got.get("language")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (pid, dt, lang) in enumerate(ex.map(work, todo), 1):
            if i % 50 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] last: {pid} → {dt}/{lang}")

    PAPERS_JSON.write_text(json.dumps(data, indent=1))
    from collections import Counter
    types = Counter(p.get("doc_type") for p in papers)
    langs = Counter(p.get("language") for p in papers)
    print("doc types:", dict(types))
    print("languages:", dict(langs))


if __name__ == "__main__":
    main()
