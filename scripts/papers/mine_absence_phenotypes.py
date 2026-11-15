#!/usr/bin/env python3
"""
Gene absence-phenotype mining (D73): extract loss-of-function evidence
from paper markdowns. Replaces speculation in the gene catalogue's
impact_if_absent with cited, grounded evidence.

Per paper, per gene — ONLY when the paper reports what happens when the gene
is absent / knocked out / knocked down / silenced / naturally missing:

  {gene, host, class: avian|mammalian|other,
   manipulation: knockout|knockdown|siRNA|CRISPR|natural-absence|
                 loss-of-function-mutation|antagonist-blocked,
   phenotype: observed outcome,
   quote: one VERBATIM sentence (grounding gate, D42)}

Output: data/papers/gene_absence_phenotypes.jsonl (one record per paper)
Aggregation: gene → {avian: [...], mammalian: [...]} → feeds gene catalogue.

Usage:
  mine_absence_phenotypes.py                 # process papers without records
  mine_absence_phenotypes.py --paper PID     # single paper (debug)
  mine_absence_phenotypes.py --aggregate     # build per-gene summary only
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
OUT = ROOT / "data" / "papers" / "gene_absence_phenotypes.jsonl"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"

PROMPT = """You are extracting loss-of-function evidence from a scientific paper about avian influenza.

For EACH gene where the paper reports what happens when that gene is ABSENT, KNOCKED OUT, KNOCKED DOWN, SILENCED, NATURALLY MISSING, or NON-FUNCTIONAL, extract:

- gene: the gene symbol (uppercase, e.g. DDX58, IFIH1, MX1, ANP32A, BST2)
- host: the species or taxon where the manipulation/observation happened
- class: "avian" | "mammalian" | "other"
- manipulation: one of knockout | knockdown | siRNA | CRISPR | natural-absence | loss-of-function-mutation | antagonist-blocked
- phenotype: the OBSERVED outcome when the gene is absent/non-functional (be specific: viral load change, symptom change, survival, cytokine level)
- quote: ONE verbatim sentence from the paper supporting this

RULES:
- ONLY extract evidence explicitly reported in the text — if the paper merely MENTIONS a gene or speculates about its role, do NOT include it
- Every record MUST have a verbatim quote that appears in the text
- If the paper reports no loss-of-function evidence for any gene, return []
- Do not invent gene names; use standard symbols
- One record per (gene × host × manipulation) combination

Return ONLY a JSON array: [{"gene": "...", "host": "...", "class": "...", "manipulation": "...", "phenotype": "...", "quote": "..."}]
Return [] if none. Output the JSON array as the FINAL thing in your reply — no text after it."""


def extract_json(text):
    """Extract the last complete JSON array from a response that may contain
    reasoning prose first (muse-glimmer outputs its thinking before the answer)."""
    candidates = []
    for m in re.finditer(r'\[\s*\{.*\}\s*\]', text, re.DOTALL):
        candidates.append(m.group(0))
    for cand in reversed(candidates):
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            continue
    return None


def load_done():
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                rec = json.loads(line)
                done.add(rec["paper_id"])
            except Exception:
                pass
    return done


def extract(md_text, url, model):
    """One LLM call: absence evidence from a paper."""
    # focus on methods+results if the paper is long
    text = md_text[:60000]
    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": text + "\n\n(Reply with ONLY the JSON array.)"},
            ],
            "max_tokens": 8000, "temperature": 0.1,
        }, timeout=600)
        msg = r.json()["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content and msg.get("reasoning_content"):
            content = msg["reasoning_content"].strip()
        records = extract_json(content) if content else None
        if records is not None:
            return [r for r in records if isinstance(r, dict) and r.get("gene")]
        return []
    except Exception as e:
        print(f"    error: {str(e)[:80]}")
    return []


def verify_quotes(records, md_text):
    """Grounding gate: drop records whose quote is not verbatim in the text."""
    kept = []
    norm = re.sub(r'\s+', ' ', md_text)
    for r in records:
        q = re.sub(r'\s+', ' ', (r.get("quote") or "")).strip()
        if len(q) > 15 and q in norm:
            kept.append(r)
        else:
            # tolerate smart-quote/punctuation variance: fuzzy substring check
            q2 = re.sub(r'[""''—–]', '', q).lower()
            n2 = re.sub(r'[""''—–]', '', norm).lower()
            if len(q2) > 15 and q2 in n2:
                kept.append(r)
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.aggregate:
        aggregate()
        return

    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    done = load_done()

    # Map paper ids to md files
    mds = {f.stem: f for f in MD_DIR.glob("*.md")}
    queue = []
    for p in papers:
        pid = p["id"]
        if args.paper and pid != args.paper:
            continue
        if pid in done or pid not in mds:
            continue
        queue.append((pid, mds[pid]))
    if args.limit:
        queue = queue[:args.limit]

    print(f"papers to mine: {len(queue)} (skipping {len(done)} already done)")

    def work(item):
        pid, md_path = item
        text = md_path.read_text(errors="replace")
        if len(text) < 500:
            return pid, []
        records = extract(text, args.url, args.model)
        records = verify_quotes(records, text)
        return pid, records

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        with OUT.open("a") as out_f:
            for i, (pid, records) in enumerate(ex.map(work, queue), 1):
                out_f.write(json.dumps({
                    "paper_id": pid, "records": records,
                }, ensure_ascii=False) + "\n")
                if i % 25 == 0:
                    print(f"  [{i}/{len(queue)}]")

    print("done — aggregate with --aggregate")


def aggregate():
    """Per-gene summary: avian vs mammalian evidence with paper citations."""
    from collections import defaultdict
    per_gene = defaultdict(lambda: {"avian": [], "mammalian": [], "other": []})
    papers = {p["id"]: p for p in json.loads(PAPERS_JSON.read_text())["papers"]}
    n_records = 0
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            pid = rec["paper_id"]
            pmeta = papers.get(pid, {})
            for r in rec.get("records", []):
                cls = r.get("class", "other")
                if cls not in ("avian", "mammalian", "other"):
                    cls = "other"
                per_gene[r["gene"].upper()][cls].append({
                    "host": r.get("host", ""),
                    "manipulation": r.get("manipulation", ""),
                    "phenotype": r.get("phenotype", ""),
                    "quote": r.get("quote", ""),
                    "paper_id": pid,
                    "paper_title": (pmeta.get("title") or "")[:100],
                    "year": pmeta.get("year"),
                })
                n_records += 1

    summary = {}
    for gene, groups in sorted(per_gene.items()):
        summary[gene] = {
            cls: recs for cls, recs in groups.items() if recs
        }
    out = ROOT / "data" / "papers" / "gene_absence_summary.json"
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(f"genes with absence evidence: {len(summary)} "
          f"({n_records} records) → {out}")
    # preview
    for gene, groups in list(summary.items())[:5]:
        print(f"  {gene}: avian={len(groups.get('avian', []))} "
              f"mammalian={len(groups.get('mammalian', []))}")


if __name__ == "__main__":
    main()
