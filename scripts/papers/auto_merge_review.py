#!/usr/bin/env python3
"""
Automated merge review via muse-glimmer (D87).

Every candidate paper answers explicit confirmation questions before it may
enter the corpus:

  Q1 RELEVANCE — does the title clearly concern avian influenza (H5/H5N1/
     HPAI/A(H5N1)) or its direct host/virology/immunology/surveillance?
  Q2 SOURCE TYPE — research article, preprint, review, or official report
     (NOT news, blog, advocacy, or pure commentary)?
  Q3 SCOPE — primary subject in scope (birds, spillover mammals incl.
     cattle/humans, virus biology, vaccines/antivirals, surveillance)?
  Q4 DUPLICATE — is this plausibly the same study as another candidate
     (preprint + published version)? First-seen wins.

Accept requires: yes/yes/yes/no respectively AND a title-quote that
grounds the relevance call (verbatim substring of the supplied title —
programmatic check, no paraphrase).

Approved papers are merged through the standard merge_papers flow;
rejected ones are logged with reasons. Resume-safe via auto_merge_log.json.

Usage:
  pixi run python scripts/papers/auto_merge_review.py              # review all
  pixi run python scripts/papers/auto_merge_review.py --apply      # + merge approved
  pixi run python scripts/papers/auto_merge_review.py --limit 20
"""

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
NEW_PAPERS = ROOT / "scripts" / "papers" / "new_papers.json"
LOG = ROOT / "scripts" / "papers" / "auto_merge_log.json"
REJECTED = ROOT / "scripts" / "papers" / "auto_merge_rejected.json"

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

SYSTEM = """You are the intake reviewer for an avian-influenza research database. For each candidate paper you must answer four confirmation questions using ONLY the supplied title, venue, year, and discovery provenance. Never use outside knowledge about the paper's content.

Q1 RELEVANCE: does the TITLE clearly concern avian influenza — H5/H5N1/HPAI/A(H5Nx) viruses, or their direct host response, virology, epidemiology, immunology, or surveillance? Titles about seasonal human influenza alone, other pathogens, or non-influenza topics are NOT relevant unless avian influenza is explicitly named.
Q2 SOURCE TYPE: from the venue and title, is this a research article, preprint, review, systematic review, or official surveillance/scientific report? News articles, blogs, advocacy/opinion essays, and press releases are NOT acceptable.
Q3 SCOPE: is the primary subject within scope — wild/domestic birds, spillover mammals (cattle, marine mammals, cats, humans), virus biology (replication, evolution, receptors), host genetics/immunity, vaccines/antivirals, or outbreak surveillance?
RULES:
- Judge ONLY from the supplied text. If uncertain, answer the question "unclear" and REJECT — the corpus must stay precise.
- "title_quote" MUST be a verbatim substring of THIS candidate's title that grounds Q1. If you cannot quote one, reject.

Return ONLY JSON:
{"q1_relevant": "yes|no|unclear",
 "q2_source_type": "research|preprint|review|report|news|opinion|unclear",
 "q3_in_scope": "yes|no|unclear",
 "verdict": "accept|reject",
 "reason": "one sentence",
 "title_quote": "verbatim fragment of THIS title supporting relevance, or empty"}"""


def extract_obj(text):
    if not text:
        return None
    best = None
    depth = start = 0
    in_str = esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        v = json.loads(text[start:i + 1])
                        if isinstance(v, dict):
                            best = v
                    except Exception:
                        pass
                    start = None
    return best


def chat(user):
    r = httpx.post(f"{DEFAULT_URL.rstrip('/')}/chat/completions", json={
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user +
             "\n\n(Reply with ONLY the JSON object.)"},
        ],
        "max_tokens": 32000, "temperature": 0.1,
    }, timeout=900)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    return (msg.get("content") or msg.get("reasoning_content") or "").strip()


_FOLD = {"\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
         "\u2014": "-", "\u2212": "-", "\u2018": "'", "\u2019": "'",
         "\u201c": '"', "\u201d": '"', "\u00a0": " "}


def norm(s):
    s = s or ""
    for k, v in _FOLD.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip().lower()


def title_tokens(t):
    return set(re.findall(r"[a-z0-9]+", (t or "").lower()))


def find_duplicate(paper, accepted_keys):
    """Deterministic near-duplicate check: token-Jaccard >= 0.8 against
    already-accepted candidates (first-seen wins; preprint+published pairs
    collapse)."""
    tt = title_tokens(paper.get("title"))
    if not tt:
        return None
    for key, ot in accepted_keys:
        j = len(tt & ot) / max(1, len(tt | ot))
        if j >= 0.8:
            return key
    return None


def review_one(paper):
    title = paper.get("title") or ""
    payload = (f"CANDIDATE:\n"
               f"title: {title}\n"
               f"venue: {paper.get('journal') or 'Unknown'}\n"
               f"year: {paper.get('year')}\n"
               f"discovered via citations of: {', '.join((paper.get('via') or [paper.get('query') or '?'])[:3])}")
    try:
        content = chat(payload)
    except Exception as e:
        return {"verdict": "error", "reason": str(e)[:100]}
    parsed = extract_obj(content)
    if parsed is None:
        try:
            content = chat("Your previous reply was not valid JSON. "
                           "Output ONLY the JSON object.\n\n" + payload)
            parsed = extract_obj(content)
        except Exception as e:
            return {"verdict": "error", "reason": str(e)[:100]}
    if not isinstance(parsed, dict):
        return {"verdict": "error", "reason": "unparseable"}

    # programmatic gates — the LLM cannot waive these
    q = str(parsed.get("title_quote") or "").strip()
    quote_ok = len(q) >= 5 and norm(q) in norm(title)
    # everything else passed but the quote failed → one re-quote retry
    if not quote_ok and parsed.get("verdict") == "accept" \
            and parsed.get("q1_relevant") == "yes" \
            and parsed.get("q3_in_scope") == "yes":
        try:
            again = extract_obj(chat(
                f"You said this title is relevant but your title_quote was "
                f"not a verbatim substring. Copy a fragment EXACTLY from "
                f"this title and re-answer.\nTITLE: {title}\n\n"
                "Return ONLY the same JSON object with a corrected "
                "title_quote."))
            if isinstance(again, dict):
                q2 = str(again.get("title_quote") or "").strip()
                if len(q2) >= 5 and norm(q2) in norm(title):
                    q, quote_ok, parsed = q2, True, again
        except Exception:
            pass
    accept = (parsed.get("verdict") == "accept"
              and parsed.get("q1_relevant") == "yes"
              and str(parsed.get("q2_source_type")) in
              ("research", "preprint", "review", "report")
              and parsed.get("q3_in_scope") == "yes"
              and quote_ok)
    return {
        "verdict": "accept" if accept else "reject",
        "q1": parsed.get("q1_relevant"), "q2": parsed.get("q2_source_type"),
        "q3": parsed.get("q3_in_scope"),
        "reason": str(parsed.get("reason") or "")[:250],
        "quote_ok": quote_ok,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="merge accepted papers via merge_papers.py --all")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = json.loads(NEW_PAPERS.read_text())
    candidates = data.get("new_papers", [])
    done = {}
    if LOG.exists():
        try:
            done = json.loads(LOG.read_text())
        except Exception:
            pass
    todo = [p for p in candidates
            if (p.get("doi") or norm(p.get("title"))) not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"auto-merge review: {len(candidates)} candidates, "
          f"{len(done)} reviewed, {len(todo)} to review")
    if not todo:
        print("nothing to review")
    else:
        def work(p):
            key = p.get("doi") or norm(p.get("title"))
            res = review_one(p)
            return key, {**res, "title": (p.get("title") or "")[:120],
                         "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}

        n = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(work, p) for p in todo]
            for i, fut in enumerate(as_completed(futs), 1):
                key, res = fut.result()
                done[key] = res
                n += res["verdict"] in ("accept", "reject")
                if i % 25 == 0 or i == len(todo):
                    acc = sum(1 for r in done.values()
                              if r.get("verdict") == "accept")
                    print(f"  [{i}/{len(todo)}] accepted so far: {acc}")
                    LOG.write_text(json.dumps(done, indent=1,
                                              ensure_ascii=False))

    LOG.write_text(json.dumps(done, indent=1, ensure_ascii=False))
    accepted = []
    accepted_keys = []   # (key, title_tokens) for deterministic dedup
    dups = 0
    for p in candidates:
        key = p.get("doi") or norm(p.get("title"))
        if done.get(key, {}).get("verdict") != "accept":
            continue
        dup = find_duplicate(p, accepted_keys)
        if dup:
            done[key] = {"verdict": "reject",
                         "reason": f"deterministic duplicate of accepted "
                                   f"candidate (title similarity ≥ 0.8)",
                         "title": (p.get("title") or "")[:120],
                         "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
            dups += 1
            continue
        accepted.append(p)
        accepted_keys.append((key, title_tokens(p.get("title"))))
    if dups:
        print(f"deterministic dedup removed {dups} near-duplicate(s)")
    rejected = [{"title": r.get("title"), "reason": r.get("reason"),
                 "q1": r.get("q1"), "q2": r.get("q2"), "q3": r.get("q3"),
                 "q4_dup": r.get("q4_dup")}
                for r in done.values() if r.get("verdict") == "reject"]
    REJECTED.write_text(json.dumps(rejected, indent=1, ensure_ascii=False))

    from collections import Counter
    tally = Counter(r.get("verdict") for r in done.values())
    print(f"review tally: {dict(tally)} → accepted {len(accepted)} papers")
    if rejected:
        print("sample rejections:")
        for r in rejected[:5]:
            print(f"  ✗ {r['title'][:60]} — {r['reason'][:70]}")

    if not args.apply or not accepted:
        if not args.apply:
            print("\n(dry run — pass --apply to merge accepted papers)")
        return

    # write ONLY accepted candidates back, then run the standard merge
    data["new_papers"] = accepted
    data["total_found"] = len(accepted)
    NEW_PAPERS.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"\nmerging {len(accepted)} accepted papers …")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "papers" /
                                        "merge_papers.py"), "--all"],
                   check=False)


if __name__ == "__main__":
    main()
