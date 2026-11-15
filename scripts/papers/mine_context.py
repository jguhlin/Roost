#!/usr/bin/env python3
"""
Corpus context miner (D41): ripgrep the paper corpus for a term, then ask
the local LLM to explain the CONTEXT each mention appears in — producing
cited, passage-grounded summaries.

Usage:
  pixi run python scripts/papers/mine_context.py --gene JAK2
  pixi run python scripts/papers/mine_context.py --term "duck OASL" --top 5
  pixi run python scripts/papers/mine_context.py --species "kakapo"
  pixi run python scripts/papers/mine_context.py --gene SYK,IRF8,BLB1

Output: data/papers/context_mining/{term}.json + console summary.
"""

import argparse
import json
import re
import subprocess
import unicodedata
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
OUT_DIR = ROOT / "data" / "papers" / "context_mining"
LLM_URL = "http://localhost:8001/v1/chat/completions"
MODEL = "gemma4-31b"
CONTEXT_CHARS = 900      # passage window around each match
MAX_PAPERS = 8           # papers per term sent to the LLM
MAX_PASSAGES = 3         # passages per paper


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def rg_passages(term: str) -> dict:
    """rg -i over the corpus, return {pid: [passage, ...]}."""
    pattern = re.escape(term)
    try:
        out = subprocess.run(
            ["rg", "-i", "--no-filename", "-C", "0", "--json", pattern, str(MD_DIR)],
            capture_output=True, text=True, timeout=120).stdout
    except FileNotFoundError:
        out = subprocess.run(
            ["grep", "-ri", pattern, str(MD_DIR)],
            capture_output=True, text=True, timeout=120).stdout
        return _from_grep(out)
    return _from_rg_json(out)


def _from_rg_json(out: str) -> dict:
    papers = {}
    for line in out.splitlines():
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") != "match":
            continue
        path = evt.get("data", {}).get("path", {})
        text = evt.get("data", {}).get("lines", {}).get("text", "")
        pid = Path(path.get("text", "")).stem
        papers.setdefault(pid, []).append(text.rstrip("\n"))
    return papers


def _from_grep(out: str) -> dict:
    papers = {}
    for line in out.splitlines():
        if ":" in line:
            path, _, text = line.partition(":")
            papers.setdefault(Path(path).stem, []).append(text)
    return papers


def paper_title(pid: str) -> str:
    p = ROOT / "data" / "papers" / "llm_analyses" / f"{pid}.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            return d["steps"]["metadata"]["extracted"].get("title", "") or pid
        except Exception:
            pass
    return pid


def llm_explain(term: str, pid: str, title: str, passages: list[str]) -> str:
    joined = "\n---\n".join(passages[:MAX_PASSAGES])
    prompt = f"""You are analysing passages from a research paper about avian influenza.

TERM UNDER INVESTIGATION: "{term}"
PAPER: {title}

PASSAGES:
{joined}

In 2-4 sentences: explain the CONTEXT in which "{term}" is discussed in this
paper — what role it plays, what finding it supports, and how it relates to
influenza biology. Ground every claim in the passages; if the passages are
insufficient, say so. Do not invent details."""

    try:
        r = httpx.post(LLM_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200, "temperature": 0.2,
        }, timeout=180)
        msg = r.json()["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content:
            # gemma reasoning models: thoughts live in reasoning_content
            rc = (msg.get("reasoning_content") or "").strip()
            if rc:
                content = rc.split("\n")[-1].strip() or rc[:400]
        return content or "(empty LLM response)"
    except Exception as e:
        return f"(LLM unavailable: {str(e)[:80]})"


LLM_URL_SAFE = LLM_URL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gene", default=None, help="gene symbol(s), comma-separated")
    ap.add_argument("--species", default=None)
    ap.add_argument("--term", default=None, help="free-text term")
    ap.add_argument("--top", type=int, default=MAX_PAPERS)
    ap.add_argument("--dry", action="store_true", help="rg only, no LLM")
    args = ap.parse_args()

    terms = []
    if args.gene:
        terms += [t.strip() for t in args.gene.split(",") if t.strip()]
    if args.species:
        terms += [t.strip() for t in args.species.split(",") if t.strip()]
    if args.term:
        terms.append(args.term)
    if not terms:
        ap.error("provide --gene, --species, or --term")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for term in terms:
        papers = rg_passages(norm(term))
        # rank papers by mention count
        ranked = sorted(papers.items(), key=lambda kv: -len(kv[1]))[:args.top]
        print(f"\n{'='*60}\nTERM: {term} — {len(papers)} papers mention it")
        if not ranked:
            print("  no corpus matches")
            continue

        results = []
        for pid, passages in ranked:
            n = len(passages)
            title = paper_title(pid)
            print(f"  {pid} ({n} hits): {title[:60]}")
            if args.dry:
                results.append({"paper_id": pid, "title": title, "mentions": n,
                                "passages": passages[:MAX_PASSAGES]})
                continue
            # fetch surrounding context windows from the md file
            md = (MD_DIR / f"{pid}.md")
            context_passages = []
            if md.exists():
                text = md.read_text(errors="ignore")
                for m in re.finditer(re.escape(term), text, re.IGNORECASE):
                    start = max(0, m.start() - CONTEXT_CHARS // 2)
                    context_passages.append(
                        text[start:m.end() + CONTEXT_CHARS // 2]
                        .replace("\n", " ")[:CONTEXT_CHARS])
                    if len(context_passages) >= MAX_PASSAGES:
                        break
            if not context_passages:
                context_passages = passages[:MAX_PASSAGES]
            explanation = llm_explain(term, pid, title, context_passages)
            print(f"    → {explanation[:180]}{'…' if len(explanation) > 180 else ''}")
            results.append({
                "paper_id": pid, "title": title, "mentions": n,
                "explanation": explanation,
                "passages": context_passages,
            })

        safe = re.sub(r"[^A-Za-z0-9]+", "_", norm(term)).strip("_")
        out = OUT_DIR / f"{safe}.json"
        out.write_text(json.dumps({
            "term": term, "mined": date.today().isoformat(),
            "papers_total": len(papers), "results": results,
        }, indent=1))
        print(f"  → {out}")


if __name__ == "__main__":
    main()
