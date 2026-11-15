#!/usr/bin/env python3
"""
Combinatorial insight synthesis (D42): pair/triple paper summaries in
random, themed, shuffled combinations and ask the LLM whether an emergent
insight exists. Most combos yield nothing — that's the design. Survivors
are stored as UNVERIFIED HYPOTHESES with paper provenance, never
auto-published to the wiki.

Sampling strategies:
  random    — any two papers
  same_gene — papers sharing a gene, different contexts
  cross_taxa — avian paper × mammalian paper (host-range lens)
  contrast  — resistant/tolerant species paper × susceptible one
  insight2  — recombine previously-kept hypotheses (iteration round 2+)

Usage:
  pixi run python scripts/papers/synthesize.py --pairs 40 --url http://localhost:8001/v1
  pixi run python scripts/papers/synthesize.py --pairs 20 --strategy same_gene --model sglang-model
"""

import argparse
import json
import random
import re
from datetime import datetime
from pathlib import Path

import httpx
TEMP = 0.4

ROOT = Path(__file__).parent.parent.parent
LLM_DIR = ROOT / "data" / "papers" / "llm_analyses"
OUT = ROOT / "data" / "papers" / "synthesis" / "insights.jsonl"
DIGEST = ROOT / "data" / "papers" / "synthesis" / "DIGEST.md"

VIRAL = {"HA", "NA", "NP", "PA", "PB1", "PB2", "NS1", "NS2", "M1", "M2"}


def load_papers():
    papers = []
    for p in sorted(LLM_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        st = d.get("steps", {})
        meta = st.get("metadata", {}).get("extracted", {})
        genes = [g.get("name", "") for g in
                 st.get("genes", {}).get("extracted", {}).get("genes", [])]
        species = [s.get("name", "") for s in
                   st.get("species", {}).get("extracted", {}).get("species", [])]
        findings = [f.get("finding", "") for f in
                    st.get("findings", {}).get("extracted", {}).get("findings", [])]
        status_words = " ".join(
            s.get("infection_status", "") or "" for s in
            st.get("species", {}).get("extracted", {}).get("species", [])).lower()
        summary = st.get("study", {}).get("extracted", {}).get("main_result", "")
        papers.append({
            "pid": p.stem,
            "title": meta.get("title") or p.stem,
            "year": meta.get("year"),
            "journal": (meta.get("journal") or "").strip(),
            "paper_type": meta.get("paper_type") or "",
            "genes": [g for g in genes if g],
            "species": [s for s in species if s],
            "findings": [f for f in findings if f][:4],
            "summary": summary,
            "resistant": any(w in status_words for w in ("resistant", "tolerant")),
            "susceptible": "susceptible" in status_words,
            "mammalian": any(w in status_words for w in ("human", "cattle", "mouse",
                          "swine", "ferret", "cat", "dog", "mink", "marine mammal"))
                       or any(k in " ".join(species).lower() for k in
                              ("human", "cattle", "bovine", "mouse", "murine", "swine",
                               "porcine", "ferret", "feline", "canine", "mink", "sea lion", "seal", "dolphin")),
        })
    return papers


def render(paper):
    bits = [f"Paper: {paper['title']} ({paper['year'] or 'n.d.'}) [id: {paper['pid']}]",
            f"Journal: {paper['journal'] or 'unlisted'} · Type: {paper['paper_type'] or 'research'} ·"
            f" Published: {paper['year'] or 'unknown date'}"]
    if paper["summary"]:
        bits.append(f"Main result: {paper['summary'][:300]}")
    if paper["findings"]:
        bits.append("Findings: " + "; ".join(f[:120] for f in paper["findings"][:3]))
    if paper["genes"]:
        bits.append("Genes: " + ", ".join(paper["genes"][:8]))
    if paper["species"]:
        bits.append("Species: " + ", ".join(paper["species"][:4]))
    return "\n".join(bits)


def temporal_frame(pair):
    """Explicit date ordering + era context so the model reasons temporally."""
    a, b = sorted(pair, key=lambda p: p["year"] or 9999)
    lines = ["TEMPORAL CONTEXT (reason with these dates):",
             f"- Earlier study: {a['pid']} ({a['year'] or 'date unknown'}, {a['journal'] or 'unlisted'})",
             f"- Later study:   {b['pid']} ({b['year'] or 'date unknown'}, {b['journal'] or 'unlisted'})",
             "- H5N1 biology moved fast: pre-2021 work often reflects pre-2.3.4.4b lineages;",
             "  the 2020-2021 panzootic start, ~2023 mammalian spillovers, and the 2024 US cattle",
             "  outbreak changed host range. If the studies disagree, consider lineage/date first.",
             "- Venue matters: preprints (bioRxiv etc.) are unreviewed — weight accordingly."]
    return "\n".join(lines)


def sample_pairs(papers, strategy, n, rng):
    out = []
    if strategy == "random":
        for _ in range(n):
            out.append(tuple(rng.sample(papers, 2)))
    elif strategy == "same_gene":
        by_gene = {}
        for p in papers:
            for g in p["genes"]:
                gl = re.sub(r"\s*\([^)]*\)", "", g).upper().strip()
                if gl and gl not in VIRAL:
                    by_gene.setdefault(gl, []).append(p)
        eligible = [ps for ps in by_gene.values() if len(ps) >= 2]
        for _ in range(n):
            if not eligible:
                break
            ps = rng.choice(eligible)
            if len(set(x["pid"] for x in ps)) >= 2:
                pair = rng.sample(ps, 2)
                out.append(tuple(pair))
    elif strategy == "cross_taxa":
        avian = [p for p in papers if not p["mammalian"]]
        mamm = [p for p in papers if p["mammalian"]]
        for _ in range(n):
            if avian and mamm:
                out.append((rng.choice(avian), rng.choice(mamm)))
    elif strategy == "contrast":
        res = [p for p in papers if p["resistant"]]
        sus = [p for p in papers if p["susceptible"] or "chicken" in " ".join(p["species"]).lower()]
        for _ in range(n):
            if res and sus:
                out.append((rng.choice(res), rng.choice(sus)))
    elif strategy == "contradiction":
        # same-gene pairs interrogated for DISAGREEING conclusions
        by_gene = {}
        for p in papers:
            for g in p["genes"]:
                gl = re.sub(r"\s*\([^)]*\)", "", g).upper().strip()
                if gl and gl not in VIRAL and (p.get("findings") or p["summary"]):
                    by_gene.setdefault(gl, []).append(p)
        eligible = [ps for ps in by_gene.values() if len(ps) >= 2]
        for _ in range(n):
            if not eligible:
                break
            ps = rng.choice(eligible)
            if len(set(x["pid"] for x in ps)) >= 2:
                out.append(tuple(rng.sample(ps, 2)))
    return [t for t in out if len({x["pid"] for x in t}) == len(t)]


def llm_insight(pair, url, model, timeout):
    prompt = f"""You are a research synthesis engine for avian influenza (H5N1) biology.

Two independent studies follow, with publication dates and journals. Your job: determine
whether combining them yields a genuine, TESTABLE cross-paper insight — a contradiction,
a convergent mechanism, a host-range pattern, a temporal shift only visible with dates in
hand, a gap only visible when both are read together, or a concrete next experiment.

ANTI-HALLUCINATION RULES (strict):
- Ground every element in the material given. No outside knowledge claims.
- Your JSON must include "grounding_quotes": for EACH paper, one VERBATIM substring
  (10-60 chars) copied exactly from that paper's card. These are checked mechanically —
  if a quote does not appear verbatim in the input, the insight is discarded automatically.
- Reason with the publication dates and journals provided — an apparent contradiction
  between a 2013 study and a 2025 study may be lineage evolution, not error.
- Partial convergence counts: if the papers connect on one real point, report that point.
- If nothing genuinely connects them, reply exactly NO_INSIGHT. Do not strain — but do
  not discard a real connection for being modest.

If there is something real, reply in strict JSON:
  {{"insight": "...", "kind": "convergence|contradiction|host_range|temporal|gap|experiment",
    "evidence": "which claims from which paper support it",
    "grounding_quotes": {{"{pair[0]['pid']}": "exact 10-60 char substring copied from that paper's card above", "{pair[1]['pid']}": "same for the other paper"}},
    "confidence": "low|medium|high"}}

{temporal_frame(pair)}

STUDY A:
{render(pair[0])}

STUDY B:
{render(pair[1])}

Respond with NO_INSIGHT or the JSON object only."""
    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a precise research synthesis engine. "
                 "Reply ONLY with NO_INSIGHT or a strict JSON object — never restate the prompt."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 3000, "temperature": TEMP,
        }, timeout=timeout)
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            text = msg["reasoning_content"].strip()
        return text
    except Exception as e:
        return f"__ERROR__ {str(e)[:100]}"


def parse_insight(text):
    if not text:
        return None
    # reasoning-style models may work through the problem in content —
    # the actual verdict lands at the END. Judge by the tail, not the head.
    tail = text.strip()[-600:]
    if re.search(r"\bNO_INSIGHT\b", tail[-80:]) or tail.strip().endswith("NO_INSIGHT"):
        return None
    # find the LAST JSON object in the text
    candidates = re.findall(r"\{[^{}]*\}", text, re.DOTALL)
    for cand in reversed(candidates):
        try:
            d = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if d.get("insight") and d.get("kind"):
            return d
    # also try the biggest/last balanced object with nesting
    m = None
    for m in re.finditer(r"\{.*\}", text, re.DOTALL):
        pass
    if m:
        try:
            d = json.loads(m.group(0))
            if d.get("insight") and d.get("kind"):
                return d
        except json.JSONDecodeError:
            return None
    return None


def verify_grounding(ins, pair):
    """Mechanical anti-hallucination gate: every grounding quote must appear
    verbatim in its paper's rendered card. No LLM judgement involved —
    fabrication is structurally impossible to pass."""
    quotes = ins.get("grounding_quotes") or {}
    if not quotes:
        return False, "no grounding quotes"
    by_pid = {p["pid"]: render(p) for p in pair}
    for pid, quote in quotes.items():
        q = (quote or "").strip()
        if len(q) < 8:
            return False, f"quote too short for {pid}"
        # normalise whitespace for containment
        card = re.sub(r"\s+", " ", by_pid.get(pid, ""))
        if re.sub(r"\s+", " ", q) not in card:
            return False, f"fabricated quote for {pid}: {q[:50]!r}"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=30)
    ap.add_argument("--strategy", default="random",
                    choices=["random", "same_gene", "cross_taxa", "contrast", "contradiction"])
    ap.add_argument("--url", default="http://localhost:8001/v1")
    ap.add_argument("--model", default="gemma4-31b")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--temperature", type=float, default=0.4)
    ap.add_argument("--workers", type=int, default=1, help="parallel LLM calls")
    args = ap.parse_args()
    global TEMP
    TEMP = args.temperature

    rng = random.Random(args.seed)
    papers = load_papers()
    print(f"{len(papers)} papers loaded · strategy={args.strategy} · {args.pairs} combos")

    pairs = sample_pairs(papers, args.strategy, args.pairs, rng)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    kept, rejected, grounded_out, errors = [], 0, 0, 0
    from concurrent.futures import ThreadPoolExecutor

    def work(item):
        i, pair = item
        text = llm_insight(pair, args.url, args.model, args.timeout)
        if text.startswith("__ERROR__"):
            return ("error", i, pair, text, None)
        ins = parse_insight(text)
        if ins:
            ok, why = verify_grounding(ins, pair)
            return ("kept" if ok else "grounding_fail", i, pair, why, ins if ok else ins)
        return ("rejected", i, pair, "", None)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for status, i, pair, note, ins in ex.map(work, enumerate(pairs, 1)):
            if status == "error":
                errors += 1
                print(f"  [{i}/{len(pairs)}] {pair[0]['pid']} × {pair[1]['pid']}: {note[:60]}")
            elif status == "kept":
                kept.append({
                    **ins,
                    "papers": [p["pid"] for p in pair],
                    "titles": [p["title"][:80] for p in pair],
                    "journals": [p["journal"] for p in pair],
                    "years": [p["year"] for p in pair],
                    "strategy": args.strategy,
                    "status": "unverified_hypothesis",
                    "grounding_verified": True,
                    "generated": datetime.now().isoformat(timespec="minutes"),
                })
                print(f"  [{i}/{len(pairs)}] ✓ {pair[0]['pid']} × {pair[1]['pid']}: {ins['insight'][:90]}")
            elif status == "grounding_fail":
                grounded_out += 1
                print(f"  [{i}/{len(pairs)}] ✗ GROUNDING FAIL ({note})")
            else:
                rejected += 1

    with open(OUT, "a") as f:
        for k in kept:
            f.write(json.dumps(k) + "\n")

    print(f"\nDone: {len(kept)} grounded insights (of {len(pairs)} combos, "
          f"{rejected} rejected, {grounded_out} grounding-failed, {errors} errors) → {OUT}")

    # refresh digest
    if kept:
        rows = [json.loads(l) for l in open(OUT)]
        with open(DIGEST, "w") as f:
            f.write(f"# Synthetic insight digest — {len(rows)} candidates\n\n")
            f.write("UNVERIFIED HYPOTHESES — human triage required. Never auto-published.\n\n")
            for i, r in enumerate(rows, 1):
                f.write(f"## {i}. [{r['kind']}] {r['insight'][:120]}\n")
                f.write(f"- confidence: {r.get('confidence')} · strategy: {r['strategy']}\n")
                f.write(f"- papers: {', '.join(r['papers'])}\n")
                f.write(f"- evidence: {r.get('evidence', '')[:300]}\n\n")
        print(f"Digest → {DIGEST}")


if __name__ == "__main__":
    main()
