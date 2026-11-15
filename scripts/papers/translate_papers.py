#!/usr/bin/env python3
"""Translate paper summaries with full context for all locales.

For each untranslated paper, sends title + summary + key findings (context)
to the LLM along with the localization glossary, producing accurate,
context-aware translations. Uses the existing i18n/papers/{lang}.json
structure. Incremental saves; skips already-translated papers.

Context per paper: title, English summary, up to 3 key findings, and
the paper's topic/category for domain framing.

Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python \
    scripts/papers/translate_papers.py [--lang zh] [--limit N] [--dry-run]
"""
import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS_JSON = ROOT / "web/public/data/papers.json"
I18N_PAPERS = ROOT / "web/public/data/i18n/papers"
FINDINGS = ROOT / "data/papers/paper_key_findings.parquet"
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

GLOSSARY = """Product: Roost — scientific resource on avian influenza (HPAI/H5N1)
host genomics. Papers cover virology, immunology, genomics, epidemiology,
poultry science, wildlife health, and conservation.
Korean: genome=유전체, host=숙주, detection=검출, spillover=종간 감염.
Chinese: genome=基因组, host=宿主, detection=检测, spillover=跨物种传播.
Translate as a native scientist reading the paper would phrase it.
Preserve: H5N1, HPAI, LPAI, clade numbers (2.3.4.4b), gene symbols (ANP32A),
country names in local convention. Keep scientific species names in Latin.
Titles: translate the meaning, not word-for-word. Summaries: 2-4 sentences,
formal register. cited_for: one phrase."""

SYSTEM = ("You are a bilingual scientific translator specializing in avian "
          "influenza and host genomics literature. " + GLOSSARY +
          " Return ONLY a JSON object for each paper: "
          '{"title": "...", "summary": "...", "cited_for": "..."} '
          "No reasoning, no commentary.")


def llm(prompt, max_tokens=6144):
    body = json.dumps({"model": MODEL, "temperature": 0.1,
                       "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    if not text:
        rc = (msg.get("reasoning_content") or "").strip()
        s, e = rc.find("{"), rc.rfind("}")
        text = rc[s:e + 1] if 0 <= s < e else ""
    return text


def parse_obj(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e + 1]) if 0 <= s < e else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default=None, help="single language (default: all)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    langs = [args.lang] if args.lang else ["zh", "ko", "ja", "fr", "es", "hi"]
    lang_names = {"zh": "Simplified Chinese", "ko": "Korean", "ja": "Japanese",
                  "fr": "French", "es": "Spanish", "hi": "Hindi"}

    papers = json.loads(PAPERS_JSON.read_text())
    papers = [p for p in (papers.get("papers", papers)) if isinstance(p, dict)]

    # context: key findings per paper
    findings = {}
    try:
        fnd = pl.read_parquet(FINDINGS)
        for pid, grp in fnd.group_by("paper_id"):
            findings[pid[0]] = grp["finding"].head(3).to_list()
    except Exception:
        pass

    I18N_PAPERS.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        out_path = I18N_PAPERS / f"{lang}.json"
        existing = json.loads(out_path.read_text()) if out_path.exists() else {"papers": {}}
        done = {pid for pid, v in existing.get("papers", {}).items()
                if isinstance(v, dict) and v.get("summary")}
        todo = [p for p in papers if p["id"] not in done
                and len((p.get("summary") or "").strip()) > 20]
        if args.limit:
            todo = todo[:args.limit]
        print(f"\n{lang}: {len(todo)} papers to translate "
              f"({len(done)} already done)")

        for i, p in enumerate(todo):
            ctx = {"title": p.get("title", ""),
                   "summary": (p.get("summary") or "")[:500],
                   "category": p.get("category", ""),
                   "key_findings": findings.get(p["id"], [])[:3],
                   "year": p.get("year"), "journal": p.get("journal", "")}
            prompt = (f"Translate this paper's metadata to {lang_names[lang]}.\n"
                      + json.dumps(ctx, ensure_ascii=False))
            try:
                result = parse_obj(llm(prompt))
            except Exception as e:
                print(f"  {p['id']}: error {str(e)[:50]}")
                time.sleep(1)
                continue
            if result.get("summary"):
                existing.setdefault("papers", {})[p["id"]] = {
                    "title": result.get("title", p.get("title", "")),
                    "summary": result["summary"],
                    "cited_for": result.get("cited_for",
                                            p.get("cited_for", "")),
                }
                out_path.write_text(json.dumps(existing, ensure_ascii=False, indent=1))
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(todo)} translated", flush=True)
        n = len(existing.get("papers", {}))
        print(f"{lang}: complete — {n} papers translated")


if __name__ == "__main__":
    main()
