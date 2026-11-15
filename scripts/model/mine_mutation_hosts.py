#!/usr/bin/env python3
"""
Mutation host-class mining — resolve WHERE each documented mutation effect was
observed (aves vs mammal), fixing the paper-level mislabel bug: a wild-bird
surveillance paper reporting "PB2-V598T increases virulence in mice" was badged
'avian' because host_scope came from the paper's study species, not from the
effect's host. Roost's mission is avian: mammalian susceptibility/lethality
effects are out of scope for display, but must be classified + quantified, not
silently dropped.

Design (same conventions as mine_vaccines.py — queue rebuilt deterministically
every run so newly full-passed papers enter automatically):
  * QUEUE  — data/papers/llm_analyses/*.json steps.mutations.extracted:
             one (mutation, effect) record per paper.
  * PASS 1 — PROPOSER: one call per paper, classifying every record:
             host_class (aves|mammal|both|non_host|unknown),
             host_species (verbatim), evidence_type, quote anchor from the
             paper markdown window (not just the summary effect string —
             summaries were where the ambiguity came from).
  * PASS 2 — SKEPTIC: one call per record, auditing host_class against the
             quote (contradicted = quote names a different host class;
             unverified = plausible but not quote-anchored).
  * LEDGER — data/papers/mutation_host_claims.jsonl, append-only, resume-safe:
             papers whose records all carry verdict != error are done;
             re-mine only with --redo.
  * --dry is the safe default: lists the queue, calls nothing.

Downstream: build_wiki_pages.py joins the ledger by canonical mutation name,
rebages wiki_mutations host_scope to effect-level truth, adds effect_hosts
counts + per-paper host_class rows, and prints the avian/mammal quantification
the frontend filter keys on.

Usage:
  pixi run python scripts/model/mine_mutation_hosts.py --dry          # queue
  pixi run python scripts/model/mine_mutation_hosts.py                # mine
  pixi run python scripts/model/mine_mutation_hosts.py --papers A,B   # subset
  pixi run python scripts/model/mine_mutation_hosts.py --redo --limit 5
"""

import argparse
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
ANALYSES = ROOT / "data" / "papers" / "llm_analyses"
MD_DIR = ROOT / "docs" / "papers_md"
CLAIMS = ROOT / "data" / "papers" / "mutation_host_claims.jsonl"

HOST_CLASSES = ["aves", "mammal", "both", "non_host", "unknown"]
EVIDENCE_TYPES = ["in_vivo", "cell_line", "sequence_only", "predicted", "review_claim"]

PROPOSER_SYS = """You classify WHERE the effect of an influenza mutation was observed.
Roost is an AVIAN host-genomics resource: the host in which an effect was
demonstrated — not the species the paper studied — decides its scope.
Given a paper's mutation records (name + extracted effect summary) plus text
windows from the paper, reply ONLY as a JSON ARRAY with ONE OBJECT PER record
(same order):
{"mutation": "<name as given>",
 "host_class": "aves"|"mammal"|"both"|"non_host"|"unknown",
 "host_species": "<verbatim host(s) the effect was shown in, e.g. 'mice', 'chickens', 'HEK293T (human)', 'ferrets'; null if none>",
 "evidence_type": "in_vivo"|"cell_line"|"sequence_only"|"predicted"|"review_claim",
 "quote": "<≤200-char verbatim quote from the paper text that anchors the host>",
 "why": "≤15 words"}
Rules:
1. Classify by the host OF THE EFFECT, never by the paper's study species.
   A duck-surveillance paper noting 'increased virulence in mice' is host_class
   'mammal' — the ducks are context, not the effect host.
2. Mammalian cell lines (HEK293T, MDCK, A549, Vero…) are 'mammal' with
   evidence_type 'cell_line'. Avian cell lines/embryos (DF-1, CEF, LMH, ECE)
   are 'aves' with evidence_type 'cell_line'.
3. 'both' only when THIS paper shows the effect in both an avian and a
   mammalian host/system.
4. non_host: no host context at all (pure sequence listing, viral-only
   replication, in-silico stability) — evidence_type sequence_only/predicted.
5. unknown when the windows genuinely do not say; never guess from the
   mutation's reputation (e.g. 'PB2 mutations mean mammals').
6. The quote must be the paper's own text. If no passage names the host,
   return quote null and host_class 'unknown' — an unanchored guess is worse
   than a null.
7. Host words to weigh carefully: humans/mice/ferrets/cats/dogs/cattle/foxes/
   seals/mink/swine → mammal; chicken/duck/turkey/quail/geese/wild birds/
   waterfowl/poultry → aves. Mixed lists from tables: pick the row the effect
   claim is about."""

SKEPTIC_SYS = """You audit mutation host-class claims against their verbatim quotes.
Reply ONLY as JSON:
{"ok": true}
or {"ok": false, "mode": "contradicted"|"unverified", "why": "≤30 words"}
- contradicted: the quote (or record logic) names a DIFFERENT host class than
  claimed — e.g. quote says 'in mice' but host_class is 'aves'; or an avian
  cell line claimed as mammal.
- unverified: plausible but the quote does not name any host (or quote is
  null/missing), so the class is not anchored.
Also contradicted: host_species inconsistent with host_class (host_class
'mammal' but host_species 'chickens'). Do not re-classify; only audit."""


def iter_mutation_records(d: dict):
    """Yield (name, effect) from one llm_analysis json, tolerant to shape."""
    raw = d.get("steps", {}).get("mutations", {}).get("extracted")
    if isinstance(raw, dict):
        raw = raw.get("mutations", [])
    for m in raw or []:
        if isinstance(m, dict):
            name, eff = str(m.get("name", "")).strip(), str(m.get("effect", "")).strip()
            if name:
                yield name, eff
        elif isinstance(m, str) and m.strip():
            yield m.strip(), ""


def scan_queue() -> dict[str, list[tuple[str, str]]]:
    """paper_id -> [(mutation, effect)] from every full-pass analysis."""
    out = {}
    for f in sorted(ANALYSES.glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        recs = list(iter_mutation_records(d))
        if recs:
            out[f.stem] = recs
    return out


def mined_papers() -> set[str]:
    """Papers whose records are all in the ledger with non-error verdicts."""
    ledger: dict[str, int] = {}
    okc: dict[str, int] = {}
    if CLAIMS.exists():
        for line in CLAIMS.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = rec.get("paper_id")
            if not pid:
                continue
            ledger[pid] = ledger.get(pid, 0) + 1
            if rec.get("host_class") and rec.get("host_class") != "unknown-error":
                okc[pid] = okc.get(pid, 0) + 1
    return {pid for pid, n in ledger.items() if n and okc.get(pid, 0) >= n}


def _loads_json(text: str):
    """Robust JSON recovery from muse-glimmer output: the model reasons in
    reasoning_content, echoing the schema early and emitting the real answer
    late — so prefer fenced blocks, then the LAST top-level balanced span.
    (D120: greedy first-match grabbed truncated schema echoes instead.)"""
    for m in re.finditer(r"```(?:json)?\s*([\[{].*?)```", text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    opens, spans = [], []
    for i, ch in enumerate(text):
        if ch in "[{":
            opens.append((i, ch))
        elif ch in "]}" and opens:
            s, c = opens.pop()
            if (c, ch) in (("[", "]"), ("{", "}")) and not opens:
                spans.append(text[s:i + 1])
    for cand in reversed(spans):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return None


def call_llm(url, model_name, system, user, max_tokens=3000):
    r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
        "model": model_name,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        # reasoning burns budget before the JSON lands — same lesson as
        # assign_topics/clade (32k); give every call room to finish thinking
        "max_tokens": max(8192, max_tokens), "temperature": 0.1,
    }, timeout=900)
    msg = r.json()["choices"][0]["message"]
    # muse-glimmer returns its answer in reasoning_content with content
    # empty — same fallback every other LLM script in the repo uses (D120).
    content = (msg.get("content") or msg.get("reasoning_content") or "")
    return _loads_json(content)


def windows(md_text: str, names: list[str], width=700, per_name=2) -> str:
    """Bounded quote windows around each mutation name — anchors the LLM to
    the paper's own wording instead of the lossy effect summary."""
    low = md_text.lower()
    spans = []
    for name in names:
        for m in list(re.finditer(re.escape(name.lower()), low))[:per_name]:
            spans.append((max(0, m.start() - width // 2), m.start() + width // 2))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return "\n[…]\n".join(md_text[s:e] for s, e in merged[:16])


def propose_paper(paper_id, recs, url, model_name):
    """Pass 1: classify all records of one paper in a single call."""
    md = MD_DIR / f"{paper_id}.md"
    ctx = windows(md.read_text(errors="replace"), [n for n, _ in recs]) \
        if md.exists() else ""
    payload = {"paper": paper_id,
               "mutation_records": [{"mutation": n, "effect_summary": e}
                                    for n, e in recs],
               "paper_text_windows": ctx or "(markdown unavailable — rely on "
                                           "effect summaries only; prefer unknown)"}
    out = call_llm(url, model_name, PROPOSER_SYS,
                   json.dumps(payload, ensure_ascii=False), max_tokens=16384)
    if not isinstance(out, list):
        return [{"paper_id": paper_id, "mutation": n, "error": "unparsed"}
                for n, _ in recs]
    claims = []
    by_name = {str(o.get("mutation", "")): o for o in out if isinstance(o, dict)}
    for name, eff in recs:
        o = by_name.get(name)
        if not o:
            claims.append({"paper_id": paper_id, "mutation": name,
                           "effect": eff, "host_class": "unknown",
                           "host_species": None, "evidence_type": None,
                           "quote": None, "why": "no LLM record returned"})
            continue
        claims.append({
            "paper_id": paper_id, "mutation": name, "effect": eff,
            "host_class": o.get("host_class") if o.get("host_class") in HOST_CLASSES else "unknown",
            "host_species": o.get("host_species"),
            "evidence_type": o.get("evidence_type") if o.get("evidence_type") in EVIDENCE_TYPES else None,
            "quote": (o.get("quote") or None),
            "why": (o.get("why") or "")[:120],
        })
    return claims


def skeptic_check(claim, url, model_name):
    """Pass 2: audit one claim against its quote. Sets 'verified' in place."""
    try:
        v = call_llm(url, model_name, SKEPTIC_SYS,
                     json.dumps(claim, ensure_ascii=False), max_tokens=400)
    except Exception:
        claim["verified"] = None
        return claim
    if v and v.get("ok") is True:
        claim["verified"] = True
    elif v and v.get("mode") == "contradicted":
        claim["verified"] = False
    else:
        claim["verified"] = None
    if v and not v.get("ok"):
        claim["skeptic"] = {"mode": v.get("mode"),
                            "why": (v.get("why") or "")[:200]}
    return claim


def mine_paper(paper_id, recs, url, model_name, skip_skeptic=False):
    claims = propose_paper(paper_id, recs, url, model_name)
    for c in claims:
        if c.get("error"):
            continue
        skeptic_check(c, url, model_name)
        c["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return claims


MAM_WORDS = re.compile(r"\b(mice|mouse|murine|ferret|hamster|human|humans|mammal\w*|mink|swine|cattle|bovine|HEK|293T|MDCK|A549|Vero|BHK)\b", re.I)
AV_WORDS = re.compile(r"\b(chicken|chickens|duck|turkey|quail|goose|geese|swan|poultry|birds?|waterfowl|DF-1|DF1|CEF|LMH|chANP32\w*|CERC)\b", re.I)

AUDIT_SYS = """You re-audit one mutation host-class claim. The text mentions both avian and
mammalian words — decide whether the EFFECT was OBSERVED in both systems in
this paper (dual assay), or whether one mention is mere context/reputation
(e.g. 'avian influenza virus replicating in mammalian cells' = avian modifies
the VIRUS; the host is mammalian).
Reply ONLY as JSON:
{"host_class": "aves"|"mammal"|"both"|"unknown",
 "host_species": "<observation host(s), verbatim>",
 "why": "≤20 words"}
Rules: host_class "both" ONLY when this paper measured the effect in an avian
system AND a mammalian system. Reputation language ('mammalian-adaptive
mutation', 'observed in mouse-adapted AIVs' as strain history) never counts
as observation. Cell lines count as their host (chANP32A-KO/DF-1 = avian;
HEK-293/293T = human/mammal)."""


def audit_both(args):
    """D121: re-audit single-class claims naming both host systems; edit
    ledger rows in place with audit provenance (verified → None for review)."""
    import re as _re
    rows = [json.loads(l) for l in CLAIMS.read_text().splitlines() if l.strip()]
    targets = []
    for i, r in enumerate(rows):
        if r.get("host_class") not in ("aves", "mammal"):
            continue
        text = f"{r.get('effect') or ''} {r.get('host_species') or ''} {r.get('quote') or ''}"
        if MAM_WORDS.search(text) and AV_WORDS.search(text):
            targets.append(i)
    print(f"audit-both: {len(targets)} single-class claims naming both systems")
    if args.dry:
        for i in targets[:20]:
            r = rows[i]
            print(f"  {r['paper_id'][:36]:36} {r.get('mutation', ''):16} {r.get('host_class')}")
        return

    def work(i):
        r = dict(rows[i])
        payload = json.dumps({k: r.get(k) for k in
                              ("paper_id", "mutation", "effect", "host_class",
                               "host_species", "quote")}, ensure_ascii=False)
        v = call_llm(args.url, args.model, AUDIT_SYS, payload, max_tokens=2048)
        return i, v

    changed = same = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, i) for i in targets]
        for fut in as_completed(futs):
            i, v = fut.result()
            if not v or v.get("host_class") not in HOST_CLASSES:
                continue
            r = rows[i]
            if v["host_class"] != r["host_class"] and v["host_class"] != "unknown":
                r["audit_d121"] = {"from": r["host_class"], "to": v["host_class"],
                                   "why": (v.get("why") or "")[:150],
                                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
                r["host_class"] = v["host_class"]
                r["host_species"] = v.get("host_species") or r.get("host_species")
                r["verified"] = None  # corrected → human review tier
                changed += 1
                print(f"  {r['paper_id'][:32]} {r.get('mutation', '')}: "
                      f"{r['audit_d121']['from']} → {r['audit_d121']['to']}")
            else:
                same += 1
    CLAIMS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                              for r in rows))
    print(f"audit-both: {changed} corrected, {same} confirmed, "
          f"{len(targets) - changed - same} inconclusive (left as-is)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="list queue, call nothing (safe default)")
    ap.add_argument("--audit-both", action="store_true",
                    help="D121: re-audit single-class claims whose text names "
                         "both an avian and a mammalian host/system — catches "
                         "PA-T97I-style dual-assay effects misfiled as single-"
                         "class, without touching reputation phrasing")
    ap.add_argument("--papers", help="comma-separated paper ids to (re)mine")
    ap.add_argument("--redo", action="store_true", help="re-mine done papers")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-skeptic", action="store_true",
                    help="skip pass 2 (debug; claims land unverified)")
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    queue = scan_queue()
    done = mined_papers()

    if args.audit_both:
        audit_both(args)
        return

    if args.papers:
        want = {p.strip() for p in args.papers.split(",")}
        targets = [(p, r) for p, r in queue.items() if p in want]
    elif args.redo:
        targets = sorted(queue.items())
    else:
        targets = sorted((p, r) for p, r in queue.items() if p not in done)

    n_recs = sum(len(r) for _, r in targets)
    print(f"queue: {len(queue)} papers with mutation records "
          f"({sum(len(r) for r in queue.values())} records) | "
          f"already mined: {len(done)} | this run: {len(targets)} papers, "
          f"{n_recs} records")
    if args.dry:
        for p, recs in targets[:25]:
            print(f"  {len(recs):3} records  {p}")
        if len(targets) > 25:
            print(f"  … +{len(targets) - 25} more")
        print("dry run — nothing mined. Re-run without --dry when ready.")
        return

    CLAIMS.parent.mkdir(parents=True, exist_ok=True)
    n_claims = 0
    host_tally = Counter()
    with open(CLAIMS, "a") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(mine_paper, p, r, args.url, args.model,
                          args.no_skeptic): p for p, r in targets}
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                claims = fut.result()
            except Exception as e:
                claims = [{"paper_id": pid, "mutation": "*",
                           "error": str(e)[:200]}]
            for c in claims:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
                if not c.get("error"):
                    n_claims += 1
                    host_tally[c.get("host_class", "unknown")] += 1
            fh.flush()
            print(f"  {pid}: {len(claims)} claim(s)")
    print(f"mined {n_claims} claims → {CLAIMS}")
    print(f"host_class tally: {dict(host_tally)}")
    print("next: pixi run python scripts/papers/build_wiki_pages.py "
          "to rebadge host_scope from effect-level claims")


if __name__ == "__main__":
    main()
