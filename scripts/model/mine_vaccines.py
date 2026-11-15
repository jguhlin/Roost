#!/usr/bin/env python3
"""
Vaccine literature mining (D68/D70) — the LLM-side pass. QUEUE-BASED, resumable,
cheap→expensive in three passes:

  1. TRIAGE  (--triage) — 1 cheap call per paper: primary / vaccine-relevant /
     mention-only / not-vaccine. Skips mention-only papers before expensive
     extraction; primary papers mine first.
  2. PROPOSER — structured extraction, one record per vaccine × species ×
     experiment. Hard rules: never compute/convert numbers, groups never
     merge (vaccinated vs control), every number carries a verbatim quote.
  3. SKEPTIC — audits each record against its quotes with verdict modes:
     ok (verified 🟢) / unverified (human review) / contradicted (dropped).

Design for "LLM later, papers keep arriving":
  * The QUEUE is rebuilt deterministically every run from the keyword scan
    (same machinery as build_vaccine_model.py) — so newly ingested papers
    enter automatically, ranked by keyword hits.
  * State lives in data/papers/vaccine_claims.jsonl (mined-state ledger) and
    data/papers/vaccine_triage.jsonl (triage ledger). Papers already present
    with verdict != "error" are DONE; re-mined only with --redo. --new-only
    restricts to papers never mined.
  * Until the LLM is up: --dry (default-safe) lists the queue and exits.

Output merges into the vaccine model via build_vaccine_model.py.

Usage:
  pixi run python scripts/model/mine_vaccines.py --dry                # queue
  pixi run python scripts/model/mine_vaccines.py --triage --dry        # plan triage
  pixi run python scripts/model/mine_vaccines.py --triage              # classify all
  pixi run python scripts/model/mine_vaccines.py --tier primary        # mine primaries
  pixi run python scripts/model/mine_vaccines.py --new-only            # new papers
  pixi run python scripts/model/mine_vaccines.py --papers A,B          # specific
  pixi run python scripts/model/mine_vaccines.py --redo --limit 5      # re-mine top 5
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "model"))

MD_DIR = ROOT / "docs" / "papers_md"
CLAIMS = ROOT / "data" / "papers" / "vaccine_claims.jsonl"
BUILD = ROOT / "scripts" / "model" / "build_vaccine_model.py"

spec = importlib.util.spec_from_file_location("bvm", BUILD)
bvm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bvm)  # STAGES / LLM_PLAN keywords + schema live here

STAGE_KEYWORDS = {s["id"]: s["keywords"] for s in bvm.STAGES}
FIELDS = bvm.LLM_PLAN["fields"]
ENUMS = bvm.LLM_PLAN["enums"]
TRIAGE_PATH = ROOT / "data" / "papers" / "vaccine_triage.jsonl"

# --- Pass 1: TRIAGE (cheap) — classify before spending extraction calls ---
TRIAGE_SYS = """You triage avian-influenza papers for a vaccine-evidence mining pipeline.
Given a paper's title/abstract window, reply ONLY as JSON:
{"tier": "primary"|"vaccine-relevant"|"mention-only"|"not-vaccine",
 "stages": [stage ids],
 "is_vaccine_paper_reason": "≤15 words"}
Tiers:
- primary: the paper's own experiments/results are about influenza vaccination
- vaccine-relevant: not a vaccine study, but reports data that constrains
  vaccination (e.g. MHC haplotype × outcomes, immune signatures, mucosal IgA)
- mention-only: vaccine discussed but no data
- not-vaccine
Stage ids: """ + ", ".join(STAGE_KEYWORDS) + "\nWhen unsure between tiers, pick the lower one."

# --- Pass 2: PROPOSER — structured extraction ---
STAGE_IDS_LINE = ("\"stages\" MUST be a list of model-stage ids drawn ONLY "
                  "from: " + ", ".join(STAGE_KEYWORDS) +
                  " — the model stages this record evidences (a "
                  "challenge-protection experiment tags [\"protection\"], "
                  "a DIVA-compatible vectored platform tags "
                  "[\"platforms\", \"diva\"])")

PROPOSER_SYS = ("""You extract structured vaccine-evidence from avian-influenza papers.
Reply ONLY as a JSON array — ONE OBJECT PER vaccine × species × experiment
(a distinct vaccine or condition = a distinct object; multi-arm trials yield
several objects sharing the paper_id). Fields:
""" + json.dumps(FIELDS, indent=0)
    + "\nControlled vocabularies (use these exact values):\n" + json.dumps(ENUMS)
    + "\n" + STAGE_IDS_LINE + "\n\n"
    + """HARD RULES — violating any makes the record worthless:
1. NEVER compute, convert, or extrapolate numbers. If the text says "8/10 died",
   record "8/10" — do NOT write 80. Percentages/titers: copy as printed, with
   the printed unit. Absent → null. No derived fields, no averages over groups.
2. GROUPS NEVER MERGE. Vaccinated-arm numbers go in *_vaccinated fields,
   control-arm in *_control. If you cannot tell which arm a number belongs to,
   null it — a swapped number is worse than a missing one.
3. Every non-null numeric field needs a verbatim quote (≤200 chars) in "quotes"
   that contains that number. Max 8 quotes per record. The quote must be the
   paper's own text, never a paraphrase.
4. Units travel with values: "shed_unit" is the paper's own unit string
   (e.g. "log10 EID50/ml", "TCID50", "copies/ml swab") — never normalized.
5. Null and negative results ARE results: no-protection, no-difference, and
   challenge-without-protection experiments are extracted like any other.
6. "challenge_clade" only if the paper states it (2.3.4.4b, D1.1, B3.13, GS/GD
   lineage…); "homologous_or_heterologous" only if stated or unambiguous.
7. "genes_mentioned": host genes with a vaccine context — one entry per gene,
   context from the enum (adjuvant_target | response_marker | haplotype_effect
   | correlate_of_protection | vector_component | other). Viral segments
   (HA/NA/NP/M) are antigens, not genes_mentioned.
8. Species: scientific binomial as printed; add wild_or_domestic if stated.
9. "verdict": ≤2 lines — design quality (randomized? control? blinded? n),
   and the single biggest transferability caveat for OTHER species.
If the passage contains no vaccine experiment or vaccine-relevant data, return []."""
)

# --- Pass 3: SKEPTIC — quote-anchored verification with verdict modes ---
SKEPTIC_SYS = """You audit extracted vaccine-evidence records against their own verbatim quotes.
For each field with a number, check its quote. Reply ONLY as JSON:
{"ok": true}
or {"ok": false, "mode": "contradicted"|"unverified", "bad": [field names], "why": "≤30 words"}

- contradicted: a quote or the record's own logic disproves the field
  (numbers swapped between arms, wrong species, unit not in quote,
  impossible value — mortality outside 0–100%, negative n, GMT below assay
  cut-off without the paper saying so).
- unverified: the number is plausible but NO quote contains it (extraction
  may be right, but it is not quote-anchored — humans review these).
Also fail the WHOLE record (bad: ["species"]) if the quotes clearly come from
a different species than the record claims. Do not re-extract; only audit.
Distinguish carefully: a mortality quote for the CONTROL group attached to a
mortality_vaccinated field is contradicted (swap), not merely unverified."""


def scan_queue() -> list[tuple[str, int, list[str]]]:
    """Whole-corpus keyword scan → [(paper_id, hits, stage_ids)] ranked by hits.
    New papers are picked up here automatically on every run."""
    stage_by_paper = {}
    hits_by_paper = Counter()
    for sid, kws in STAGE_KEYWORDS.items():
        pattern = "|".join(re.escape(k) for k in kws)
        out = subprocess.run(
            ["rg", "-i", "-c", "-e", pattern, "--glob", "*.md", str(MD_DIR)],
            capture_output=True, text=True, timeout=180).stdout
        for line in out.splitlines():
            path, _, n = line.rpartition(":")
            stem = Path(path).stem
            if stem.startswith("_"):
                continue
            stage_by_paper.setdefault(stem, set()).add(sid)
            hits_by_paper[stem] += int(n)
    ranked = sorted(hits_by_paper.items(), key=lambda kv: -kv[1])
    return [(p, h, sorted(stage_by_paper[p])) for p, h in ranked]


def mined_papers() -> set[str]:
    done = set()
    if CLAIMS.exists():
        for line in CLAIMS.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("verdict") not in ("error", "unparsed"):
                done.add(rec.get("paper_id"))
    return done


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


def windows(md_text: str, kws: list[str], width=900, per_kw=2) -> str:
    """Passage windows around stage keywords — keeps prompts bounded."""
    low = md_text.lower()
    spans = []
    for kw in kws:
        for m in list(re.finditer(re.escape(kw.lower()), low))[:per_kw]:
            spans.append((max(0, m.start() - width // 2), m.start() + width // 2))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return "\n[…]\n".join(md_text[s:e] for s, e in merged[:12]) or md_text[:4000]


def triage_paper(paper_id, stages, url, model_name):
    """Pass 1: cheap classification call. Returns the triage record or None."""
    md = MD_DIR / f"{paper_id}.md"
    if not md.exists():
        return None
    text = md.read_text(errors="replace")
    kws = [k for s in stages for k in STAGE_KEYWORDS[s]]
    window = windows(text, kws, width=700, per_kw=1)[:6000]
    try:
        rec = call_llm(url, model_name, TRIAGE_SYS,
                       f"Paper: {paper_id}\n\n{window}", max_tokens=2048)
    except Exception as e:
        return {"paper_id": paper_id, "tier": "error", "why": str(e)[:200]}
    if isinstance(rec, dict):
        rec["paper_id"] = paper_id
        rec["triage_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return rec
    return {"paper_id": paper_id, "tier": "unparsed"}


def run_triage(targets, args):
    """Triage pass → data/papers/vaccine_triage.jsonl (skip already-triaged)."""
    done = set()
    if TRIAGE_PATH.exists():
        done = {json.loads(l).get("paper_id")
                for l in TRIAGE_PATH.read_text().splitlines() if l.strip()}
    todo = [(p, s) for p, h, s in targets if p not in done]
    print(f"triage: {len(todo)} papers to classify ({len(done)} already done)")
    if args.dry:
        for p, s in todo[:20]:
            print(f"  {p}")
        return {}
    tiers = {}
    TRIAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRIAGE_PATH, "a") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(triage_paper, p, s, args.url, args.model): p for p, s in todo}
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"paper_id": pid, "tier": "error", "why": str(e)[:200]}
            if rec:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                tiers[pid] = rec.get("tier")
    print(f"triage written → {TRIAGE_PATH}")
    return tiers


def load_triage() -> dict:
    if not TRIAGE_PATH.exists():
        return {}
    out = {}
    for l in TRIAGE_PATH.read_text().splitlines():
        try:
            rec = json.loads(l)
            out[rec["paper_id"]] = rec.get("tier")
        except Exception:
            continue
    return out


def mine_paper(paper_id, stages, url, model_name):
    md = (MD_DIR / f"{paper_id}.md")
    if not md.exists():
        return None
    text = md.read_text(errors="replace")
    kws = [k for s in stages for k in STAGE_KEYWORDS[s]]
    try:
        recs = call_llm(url, model_name, PROPOSER_SYS,
                        f"Paper: {paper_id}\n\n{windows(text, kws)}",
                        max_tokens=16384)
    except Exception as e:
        return [{"paper_id": paper_id, "verdict": "error", "why": str(e)[:200]}]
    if recs is None:
        # D120 telemetry: JSON genuinely not recovered — retryable.
        return [{"paper_id": paper_id, "verdict": "unparsed",
                 "why": "proposer JSON not recovered (truncated thinking or "
                        "malformed array)"}]
    if recs == []:
        # Legitimate empty answer ('[]', finish_reason=stop): the windows
        # contain no vaccine×species×experiment records. Mark done so the
        # paper is not re-mined on every run (D120).
        return [{"paper_id": paper_id, "verdict": "no-records"}]
    out = []
    for rec in recs if isinstance(recs, list) else []:
        rec["paper_id"] = paper_id
        rec["mined_ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:  # skeptic pass — verdict modes: ok / unverified / contradicted
            v = call_llm(url, model_name, SKEPTIC_SYS,
                         json.dumps(rec, ensure_ascii=False), max_tokens=600)
            if v and v.get("ok") is True:
                rec["verified"] = True
            elif v and v.get("mode") == "contradicted":
                rec["verified"] = False          # quote/logic disproves — drop from 🟢
            elif v and v.get("mode") == "unverified":
                rec["verified"] = None           # plausible, not quote-anchored — human review
            else:
                rec["verified"] = None
            if v and not v.get("ok"):
                rec["skeptic"] = {"mode": v.get("mode"), "why": (v.get("why") or "")[:200],
                                  "bad": v.get("bad", [])[:10]}
        except Exception:
            rec["verified"] = None
        out.append(rec)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="list queue, mine nothing (safe default)")
    ap.add_argument("--triage", action="store_true",
                    help="run the cheap classification pass first (recommended "
                         "before mining: primary papers get extraction calls, "
                         "mention-only papers are skipped)")
    ap.add_argument("--tier", choices=["primary", "vaccine-relevant", "all"],
                    default="all", help="mine only this triage tier")
    ap.add_argument("--all", action="store_true", help="mine the full queue, not just new papers")
    ap.add_argument("--new-only", action="store_true", help="only papers never mined (default)")
    ap.add_argument("--papers", help="comma-separated paper ids to (re)mine")
    ap.add_argument("--redo", action="store_true", help="re-mine even if already done")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    queue = scan_queue()
    done = mined_papers()
    if args.papers:
        want = {p.strip() for p in args.papers.split(",")}
        targets = [q for q in queue if q[0] in want]
    elif args.all or args.redo:
        targets = queue
    else:  # new-only / dry
        targets = [q for q in queue if q[0] not in done]

    tiers = {}
    if args.triage:
        tiers = run_triage(targets, args)
        # D120: --triage means TRIAGE. Previously it fell through into
        # unfiltered whole-queue mining (the runbook command '--triage
        # --workers 56' silently launched 464 mining calls). Mining now
        # requires an explicit --tier/--all/--papers/--redo.
        print("triage complete — mine with: --new-only --tier primary "
              "(then --tier vaccine-relevant)")
        return
    tiers.update(load_triage())
    if args.tier != "all":
        targets = [q for q in targets if tiers.get(q[0]) == args.tier]
    # mine primary papers first, then vaccine-relevant, then untriaged
    rank = {"primary": 0, "vaccine-relevant": 1, "mention-only": 2,
            "not-vaccine": 3}
    if tiers:
        targets.sort(key=lambda q: (rank.get(tiers.get(q[0]), 2), -q[1]))
    if args.limit:
        targets = targets[:args.limit]

    print(f"queue: {len(queue)} candidate papers | already mined: {len(done)} "
          f"| this run: {len(targets)}"
          + (f" | tier={args.tier}" if args.tier != "all" else ""))
    if args.dry:
        for p, h, s in targets[:40]:
            print(f"  {h:4} hits  [{(tiers.get(p) or '—'):16}] {p}  [{','.join(s)}]")
        if len(targets) > 40:
            print(f"  … +{len(targets) - 40} more")
        print("dry run — nothing mined. Re-run without --dry when the LLM is up.")
        return

    n_ok = n_rec = 0
    CLAIMS.parent.mkdir(parents=True, exist_ok=True)
    with open(CLAIMS, "a") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(mine_paper, p, s, args.url, args.model): p
                for p, h, s in targets}
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                recs = fut.result() or []
            except Exception as e:
                recs = [{"paper_id": pid, "verdict": "error", "why": str(e)[:200]}]
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            n_ok += 1 if recs else 0
            n_rec += len([r for r in recs if r.get("verdict") != "error"])
            print(f"  {pid}: {len(recs)} record(s)")
    print(f"mined {n_ok}/{len(targets)} papers → {n_rec} claim records "
          f"({CLAIMS})\nnext: pixi run python scripts/model/build_vaccine_model.py "
          f"to rebadge stages verified")


if __name__ == "__main__":
    main()
