#!/usr/bin/env python3
"""LLM leak-audit: feed rendered page text (non-EN locale) to the local LLM
and collect English-leak findings. Deterministic-ish: temperature ≤ 0.05,
multiple passes, findings merged by (page, excerpt).

Usage: pixi run python scripts/i18n/llm_audit.py <locale> [--passes N] [--min-chars N]
Input: /tmp/i18n_pages/<locale>/*.txt  (produced by render_pages.mjs)
Output: /tmp/i18n_pages/<locale>/_findings.json (merged, deduped)
"""
import json
import glob
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

LLM = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = "muse-glimmer-30b"
TEMP = 0.05

LANG_NAMES = {"zh": "Chinese", "ko": "Korean", "ja": "Japanese",
              "fr": "French", "es": "Spanish", "hi": "Hindi"}

# things that LOOK like English but are legitimate
ALLOW_HINTS = (
    "Latin scientific names (Gallus gallus, Anas platyrynchos), gene symbols "
    "(DDX58, ANP32A, IFIT5), accession numbers (GCA_/GCF_), brand names (Roost, BLAST, "
    "DuckDB, Parquet, OrthoFinder, NCBI, IUCN), file names, URLs, version strings "
    "(v0.6), numbers, clade names (2.3.4.4b), chemical/protein notation, "
    "paper identifiers, and table data values are NOT leaks."
)

SYSTEM = (
    "You are a strict localization QA auditor. You will see the rendered text of a web page "
    "that is supposed to be fully in {lang}. Find every English phrase, word, or sentence "
    "that leaks through untranslated. {allow} "
    "Ignore short technical tokens that are identical across languages. "
    "Report ONLY genuine untranslated English UI text. "
    "Return STRICT JSON array: [\"excerpt1\", \"excerpt2\", ...] where each excerpt is the "
    "exact English text as it appears (enough context to locate it, max ~90 chars). "
    "Return [] if the page is fully translated. No markdown, no commentary."
)


def call_llm(page_name, lang, text, max_chars=9000):
    prompt = (f"Page: {page_name}\n\n{text[:max_chars]}")
    if len(text) > max_chars:
        # second half for long pages
        prompt += "\n…[truncated]"
    body = json.dumps({
        "model": MODEL, "temperature": TEMP, "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": SYSTEM.format(lang=LANG_NAMES[lang], allow=ALLOW_HINTS)},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    req = urllib.request.Request(f"{LLM}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    out = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    s, e = out.find("["), out.rfind("]")
    if s < 0 or e <= s:
        return []
    try:
        arr = json.loads(out[s:e + 1])
        return [a for a in arr if isinstance(a, str) and 2 < len(a) < 200]
    except json.JSONDecodeError:
        return []


def main():
    locale = sys.argv[1]
    passes = 2
    if "--passes" in sys.argv:
        passes = int(sys.argv[sys.argv.index("--passes") + 1])
    pages = sorted(glob.glob(f"/tmp/i18n_pages/{locale}/*.txt"))
    if not pages:
        sys.exit(f"no rendered pages for {locale} — run render_pages.mjs first")
    findings = defaultdict(list)
    for p in pages:
        name = os.path.basename(p)[:-4]
        text = open(p).read()
        if len(text) < 200:
            continue
        for pass_i in range(passes):
            try:
                hits = call_llm(name, locale, text)
            except Exception as e:
                print(f"  {name} pass{pass_i}: ERR {str(e)[:50]}", flush=True)
                time.sleep(1)
                continue
            for h in hits:
                h = h.strip()
                # ignore pure-symbol/number junk
                if re.fullmatch(r"[\W\d]+", h):
                    continue
                findings[name].append(h)
            time.sleep(0.2)
        n_unique = len(set(findings[name]))
        print(f"  {name}: {n_unique} unique findings", flush=True)
    # merge: keep excerpts found in ≥1 pass; annotate count (confidence signal)
    merged = {}
    for page, excerpts in findings.items():
        seen = {}
        for e in excerpts:
            key = e.lower()[:60]
            seen.setdefault(key, {"excerpt": e, "count": 0})
            seen[key]["count"] += 1
        merged[page] = sorted(seen.values(), key=lambda x: -x["count"])
    out_path = f"/tmp/i18n_pages/{locale}/_findings.json"
    json.dump(merged, open(out_path, "w"), ensure_ascii=False, indent=1)
    total = sum(len(v) for v in merged.values())
    print(f"\n{total} unique findings across {len(merged)} pages → {out_path}")
    for page, items in sorted(merged.items()):
        for it in items:
            print(f"  [{it['count']}×] {page}: {it['excerpt'][:88]}")


if __name__ == "__main__":
    main()
