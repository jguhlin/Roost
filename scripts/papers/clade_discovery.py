#!/usr/bin/env python3
"""
Clade discovery lane (D91): continuously detect and classify genotype/clade/
subtype designations in the corpus, known and novel.

Architecture:
  1. BROAD SCAN — regex over all ready papers for designation patterns
     (genotypes like D1.1/B3.13/G5, clades like 2.3.4.4b, subtypes like H5Nx,
     plus any "genotype X" / "clade X" / "lineage X" pattern).
  2. REGISTRY — data/papers/connections/clade_registry.json tracks every
     designation ever seen: first-seen date, paper count, context sample,
     status (known | novel | retired), LLM-verified description.
  3. LLM VERIFICATION — novel designations (>5 papers) get a Muse pass to
     confirm they're real genotype/clade names (not regex false positives)
     and describe what they are.
  4. ALERTS — designations that are new since the last scan, or that crossed
     a paper-count threshold, are surfaced in the output.

Usage:
  pixi run python scripts/papers/clade_discovery.py            # scan only
  pixi run python scripts/papers/clade_discovery.py --llm      # + verify novel
  pixi run python scripts/papers/clade_discovery.py --check    # registry report
"""

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
MANIFEST = ROOT / "data" / "papers" / "corpus_manifest.json"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
REGISTRY_PATH = ROOT / "data" / "papers" / "connections" / "clade_registry.json"

sys_path = str(ROOT / "scripts" / "papers")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
try:
    from llm_provenance import track as _llm_track
except ImportError:
    _llm_track = lambda *a, **k: None

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

# --- Pattern catalog -------------------------------------------------------

# Explicit "genotype X" / "clade X" / "subclade X" / "lineage X" mentions
EXPLICIT_DESIGNATION = re.compile(
    r"(?:genotype|clade|subclade|lineage|g-type)\s+"
    r"([A-Z]{1,2}[0-9](?:\.[0-9]+)?)", re.IGNORECASE)

# Numeric clade notation (WHO/H5): requires explicit "clade" context nearby
# (bare dot-numbers are software versions / section numbers)
NUMERIC_CLADE_CONTEXT = re.compile(
    r"(?:clade|subclade)\s+([0-9](?:\.[0-9]+){1,3}[a-z]?)", re.IGNORECASE)

# Subtype notation: H5N1, H5N2, H5N5, H5N6, H5N8, H7N9, H9N2, etc.
SUBTYPE = re.compile(r"\b([Hh][0-9][Nn][0-9])\b")

# PB2/H common mutation notations
MUTATION = re.compile(
    r"\b((?:PB2|HA|NA|PA|NS1|M1|NP|PB1)[-]?(?:E|D|K|N|T|A|V|I|G|S|R|M|L|P|Q|H|Y|C|F|W)"
    r"[0-9]{3,4}(?:[A-Z])?)\b")

# Known genotype naming patterns without the "genotype" prefix
BARE_GENOTYPE = re.compile(
    r"\b([A-Z][0-9]\.[0-9]+)\b(?!\s*(?:%|percent|fold))")

# --- Registry ---------------------------------------------------------------


def load_registry():
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except Exception:
            pass
    return {"designations": {}, "last_scan": None}


def save_registry(reg):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(reg, indent=1, ensure_ascii=False))


KNOWN = {
    "H5N1", "H5N2", "H5N5", "H5N6", "H5N8", "H7N9", "H9N2",
    "2.3.4.4b", "2.3.4.4h", "2.3.4.4", "2.3.2.1", "2.3.2.1a", "2.3.2.1c",
    "1.1.3", "7.2", "clade.0", "clade.1", "clade.2", "clade.3",
    "D1.1", "D1.2", "D1.3", "B3.13", "B3.6", "B3.2", "B3.5", "B3.1",
    "A3", "G5", "G1", "A1a", "EA2", "SA1", "SA2",
    "PB2-627K", "PB2-627E", "PB2-701N", "PB2-631L", "PB2-591K",
    "HA-156A", "HA-226L",
}


def classify_token(token):
    """Categorize a detected designation."""
    t = token.upper()
    if re.match(r"^[Hh][0-9][Nn][0-9]$", t):
        return "subtype"
    if re.match(r"^[0-9]", t):
        return "clade"
    if "-" in t and any(m in t for m in ("PB2", "HA", "NA", "PA", "NS1")):
        return "mutation"
    if re.match(r"^[A-Z][0-9]", t):
        return "genotype"
    return "other"


def scan_corpus():
    """Broad scan for all designation tokens across ready papers."""
    manifest = json.loads(MANIFEST.read_text())
    ready = [r["paper_id"] for r in manifest["papers"] if r["status"] == "ready"]

    token_papers = defaultdict(set)    # token → {paper_ids}
    token_contexts = defaultdict(list) # token → sample sentences

    for pid in ready:
        p = MD_DIR / f"{pid}.md"
        if not p.exists():
            continue
        text = p.read_text(errors="replace")

        # subtype notations
        for m in SUBTYPE.finditer(text):
            tok = m.group(1).upper()
            token_papers[tok].add(pid)
            if len(token_contexts[tok]) < 3:
                start = max(0, m.start() - 40)
                token_contexts[tok].append(text[start:m.end() + 40].strip())

        # explicit designations
        for m in EXPLICIT_DESIGNATION.finditer(text):
            tok = m.group(1).upper()
            token_papers[tok].add(pid)
            if len(token_contexts[tok]) < 3:
                start = max(0, m.start() - 30)
                token_contexts[tok].append(text[start:m.end() + 50].strip())

        # numeric clades: require "clade X" / "subclade X" context
        for m in NUMERIC_CLADE_CONTEXT.finditer(text):
            tok = m.group(1)
            token_papers[tok].add(pid)
            if len(token_contexts[tok]) < 3:
                start = max(0, m.start() - 30)
                token_contexts[tok].append(
                    text[start:m.end() + 50].strip()[:100])

        # bare genotype patterns (D1.1 etc. — only if >1 paper to filter noise)
        for m in BARE_GENOTYPE.finditer(text):
            tok = m.group(1).upper()
            token_papers[tok].add(pid)
            if len(token_contexts[tok]) < 3:
                start = max(0, m.start() - 40)
                token_contexts[tok].append(text[start:m.end() + 40].strip())

        # signature mutations
        for m in MUTATION.finditer(text):
            tok = m.group(1).upper().replace("-", "-")
            token_papers[tok].add(pid)
            if len(token_contexts[tok]) < 3:
                start = max(0, m.start() - 40)
                token_contexts[tok].append(text[start:m.end() + 40].strip())

    return token_papers, token_contexts


def update_registry(token_papers, token_contexts):
    """Update the registry with scan results; return novel + alert tokens."""
    reg = load_registry()
    reg["last_scan"] = datetime.now().isoformat(timespec="seconds")
    designations = reg.setdefault("designations", {})

    novel = []      # new since last scan
    grown = []      # crossed threshold since last scan
    ALERT_THRESHOLD = 10

    for tok, papers in sorted(token_papers.items()):
        count = len(papers)
        kind = classify_token(tok)
        known = tok in KNOWN or tok in designations

        if tok not in designations:
            designations[tok] = {
                "kind": kind,
                "status": "known" if tok in KNOWN else "novel",
                "first_seen": datetime.now().isoformat(timespec="seconds"),
                "papers": count,
                "context_samples": token_contexts.get(tok, [])[:2],
            }
            if count >= 3 and tok not in KNOWN:
                novel.append((tok, count, kind))
        else:
            old_count = designations[tok].get("papers", 0)
            designations[tok]["papers"] = count
            if old_count < ALERT_THRESHOLD <= count:
                grown.append((tok, count, kind))

    # prune singletons (noise)
    to_remove = [t for t, d in designations.items() if d["papers"] <= 1
                 and d.get("status") == "novel"]
    for t in to_remove:
        del designations[t]

    save_registry(reg)
    return novel, grown, reg


# --- LLM verification --------------------------------------------------------

VERIFY_PROMPT = """You are a virology expert verifying genotype/clade designations from avian influenza literature. For each token, decide if it is a REAL genotype, clade, or subtype designation (not a false positive from text scanning).

Known real patterns:
- Subtypes: H5N1, H5N2, H5N6, H5N8, H7N9, etc.
- WHO clades: 2.3.4.4b, 2.3.2.1a, 2.3.4.4h, etc. (numeric hierarchical)
- Genotypes (NA-segment based): A1a, A3, B3.13, D1.1, G5, EA2, SA1, etc.
- Signature mutations: PB2-E627K, HA-T156A, etc.

False positives to reject: random dot-numbers, figure/table references, statistical values, gene names that look like genotypes.

Return ONLY JSON: {"verified": true/false, "description": "what it is (one sentence)", "significance": "why it matters for H5N1 (one sentence)"}"""


def llm_verify_novel(novel_tokens, contexts, url, model):
    """Ask Muse to verify novel designations and describe them."""
    results = {}
    reg = load_registry()

    def work(tok, count, kind):
        ctx = "\n".join(contexts.get(tok, [])[:2]) or "(no context captured)"
        payload = (f"TOKEN: {tok}\nTYPE: {kind}\n"
                   f"PAPERS MENTIONING IT: {count}\n"
                   f"CONTEXT SAMPLES:\n{ctx}")
        try:
            r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": VERIFY_PROMPT},
                    {"role": "user", "content": payload +
                     "\n\n(Reply with ONLY the JSON.)"},
                ],
                "max_tokens": 32000, "temperature": 0.1,
            }, timeout=900)
            msg = r.json()["choices"][0]["message"]
            text = (msg.get("content") or
                    msg.get("reasoning_content") or "").strip()
            # extract JSON
            import json as j
            m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
            if m:
                d = j.loads(m.group(0))
                return tok, d
        except Exception as e:
            print(f"    {tok}: {str(e)[:60]}")
        return tok, None

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(work, tok, count, kind)
                for tok, count, kind in novel_tokens]
        for fut in as_completed(futs):
            tok, d = fut.result()
            if d and d.get("verified"):
                results[tok] = d
                if tok in reg["designations"]:
                    reg["designations"][tok]["status"] = "verified"
                    reg["designations"][tok]["llm_description"] = \
                        d.get("description", "")[:300]
                    reg["designations"][tok]["llm_significance"] = \
                        d.get("significance", "")[:300]
                    reg["designations"][tok]["verified_by"] = model
            elif tok in reg["designations"]:
                reg["designations"][tok]["status"] = "false_positive"

    save_registry(reg)
    if results:
        _llm_track("clade_verification", model, "clade-verify-v1",
                   len(results),
                   notes=f"verified {len(results)} novel designations")
    return results


def check():
    reg = load_registry()
    desigs = reg.get("designations", {})
    from collections import Counter
    by_status = Counter(d["status"] for d in desigs.values())
    by_kind = Counter(d["kind"] for d in desigs.values())
    print(f"registry: {len(desigs)} designations | last scan: "
          f"{reg.get('last_scan', 'never')[:10]}")
    print(f"by status: {dict(by_status)} | by kind: {dict(by_kind)}")
    verified = [(t, d) for t, d in sorted(desigs.items(),
                key=lambda kv: -kv[1]["papers"])
                if d["status"] == "verified"]
    if verified:
        print(f"\nLLM-verified novel designations:")
        for tok, d in verified[:10]:
            print(f"  {tok:12s} ({d['papers']:3d} papers) — "
                  f"{d.get('llm_description', '?')[:80]}")
    novel_unverified = [(t, d) for t, d in sorted(desigs.items(),
                        key=lambda kv: -kv[1]["papers"])
                        if d["status"] == "novel" and d["papers"] >= 3]
    if novel_unverified:
        print(f"\nunverified novel (≥3 papers):")
        for tok, d in novel_unverified[:10]:
            print(f"  {tok:12s} ({d['papers']:3d} papers) — "
                  f"context: {d['context_samples'][0][:60] if d.get('context_samples') else '?'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true",
                    help="verify novel designations via Muse")
    ap.add_argument("--verify-backlog", action="store_true",
                    help="D120: LLM-verify registry entries already sitting "
                         "at status 'novel' (the 52-entry debt; --llm only "
                         "verifies tokens NEW in the current scan)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    if args.check:
        check()
        return

    if args.verify_backlog:
        reg = load_registry()
        backlog = [(tok, d["papers"], d.get("kind", "other"))
                   for tok, d in reg["designations"].items()
                   if d.get("status") == "novel" and d.get("papers", 0) >= 2]
        backlog.sort(key=lambda t: -t[1])
        print(f"[clade-discovery] backlog verification: {len(backlog)} "
              f"unverified novel designations (≥2 papers)")
        contexts = {tok: d.get("context_samples", [])
                    for tok, d in reg["designations"].items()}
        verified = llm_verify_novel(backlog, contexts, args.url, args.model)
        print(f"  verified: {len(verified)} | "
              f"false positives: {len(backlog) - len(verified)}")
        return

    print("[clade-discovery] scanning corpus…")
    token_papers, token_contexts = scan_corpus()
    print(f"  raw tokens: {len(token_papers)}")

    novel, grown, reg = update_registry(token_papers, token_contexts)
    print(f"  registry: {len(reg['designations'])} designations | "
          f"novel: {len(novel)} | crossed {10}-paper threshold: {len(grown)}")

    if novel:
        print(f"\n  NEW designations this scan:")
        for tok, count, kind in novel[:15]:
            print(f"    {tok:12s} ({count:3d} papers, {kind}) — "
                  f"{(token_contexts.get(tok, ['?'])[0])[:60]}")

    if grown:
        print(f"\n  ALERT — crossed paper threshold:")
        for tok, count, kind in grown:
            print(f"    {tok:12s} now in {count} papers ({kind})")

    if args.llm and novel:
        print(f"\n[clade-discovery] LLM verification of {len(novel)} novel…")
        verified = llm_verify_novel(novel, token_contexts,
                                    args.url, args.model)
        print(f"  verified: {len(verified)} | "
              f"false positives: {len(novel) - len(verified)}")
        for tok, d in verified.items():
            print(f"    ✓ {tok}: {d.get('description', '')[:80]}")

    print(f"\n→ {REGISTRY_PATH.name} "
          f"({len(reg['designations'])} designations)")


if __name__ == "__main__":
    main()
