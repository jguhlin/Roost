#!/usr/bin/env python3
"""
CAMPAIGN: full re-run over all papers (D74). Five phases, all resume-safe,
all outputs cited and flowing to their display homes.

Phase A — corpus preflight (D75):
  data/papers/corpus_manifest.json ← per-paper ready/missing_source/
  conversion_failed/too_short (lawful OA recovery first)
  Home: gates every text-mining phase; missing ≠ negative evidence

Phase B — summary rebuild:
  papers.json ← {summary: 2 sentences, main_conclusion: 1 sentence}
  Home: Papers page cards + paper detail

Phase C1 — gene claims (iterative exclusion loop):
  data/papers/gene_claims.jsonl ← [{gene, role, tier, quote}] per paper
  Home: wiki_genes.json rebuild → gene pages (findings/roles with citations)

Phase C2 — conclusions (same loop):
  data/papers/paper_conclusions.jsonl ← [{conclusion, quote}]
  Home: papers.json main_conclusion enrichment + gene page conclusions

Phase C3 — absence phenotypes (already built, D73):
  data/papers/gene_absence_phenotypes.jsonl
  Home: gene catalogue impact_if_absent_lit → gene pages

Phase D — model verification:
  data/papers/model_verdicts.jsonl ← per paper × per stage verdicts
  Home: model v0.6 update proposals + "where literature diverges"

Usage:
  campaign.py preflight           # Phase A only (corpus recovery + manifest)
  campaign.py summaries            # Phase B only
  campaign.py genes                # Phase C1+C2+C3
  campaign.py connections          # Phase E: connection mining (D76)
  campaign.py verify               # Phase D
  campaign.py export               # merge everything into served data
  campaign.py all                   # A → B → C → D → E → export
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent

sys_path = str(ROOT / "scripts" / "papers")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
try:
    from llm_provenance import track as _llm_track
except ImportError:
    _llm_track = lambda *a, **k: None
MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
DATA_PAPERS = ROOT / "data" / "papers"
GENE_CONFIG = ROOT / "data" / "genes" / "gene_config.json"

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

# ---------------------------------------------------------------- helpers

def chat(system, user, url, model, max_tokens=8000, temperature=0.1):
    """Single LLM call; tolerates muse-glimmer's verbose-then-JSON style."""
    r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user + "\n\n(Reply with ONLY the JSON. No text after it.)"},
        ],
        "max_tokens": max_tokens, "temperature": temperature,
    }, timeout=900)
    msg = r.json()["choices"][0]["message"]
    content = (msg.get("content") or "").strip()
    if not content and msg.get("reasoning_content"):
        content = msg["reasoning_content"].strip()
    return content


def extract_json(text):
    """Last complete JSON value (array or object) in the text."""
    if not text:
        return None
    candidates = []
    for m in re.finditer(r'\[\s*\{.*\}\s*\]', text, re.DOTALL):
        candidates.append(m.group(0))
    for m in re.finditer(r'\{\s*".*"\s*\}', text, re.DOTALL):
        candidates.append(m.group(0))
    for cand in reversed(candidates):
        try:
            return json.loads(cand)
        except Exception:
            continue
    # bare false / [] responses
    if re.fullmatch(r'\s*(false|\[\])\s*', text, re.IGNORECASE):
        return False
    return None


def load_papers():
    return json.loads(PAPERS_JSON.read_text())["papers"]


def save_papers(papers):
    PAPERS_JSON.write_text(json.dumps({"papers": papers}, indent=1, ensure_ascii=False))


def md_map():
    return {f.stem: f for f in MD_DIR.glob("*.md")}


def known_genes():
    """Panel symbols (gene catalogue) + config aliases + viral list."""
    genes = set()
    # canonical panel: the gene catalogue from gene_catalogue.json
    gp = json.loads((ROOT / "web" / "public" / "data" / "gene_catalogue.json").read_text())
    genes.update(k.upper() for k in gp.get("gene_catalogue", {}).keys())
    # config aliases (MDA5→IFIH1 etc.) + wiki aliases
    cfg = json.loads(GENE_CONFIG.read_text())
    for a in cfg.get("aliases", {}):
        genes.add(str(a).upper())
        genes.add(str(cfg["aliases"][a]).upper())
    for canon, aliases in cfg.get("wiki_aliases", {}).items():
        genes.add(str(canon).upper())
        for a in aliases:
            genes.add(str(a).upper())
    # D74: explicit viral gene list — viral claims are never dropped
    genes.update({
        "PB2", "PB1", "PB1-F2", "PA", "PA-X", "HA", "NP", "NA",
        "M1", "M2", "M42", "NS1", "NS2", "NS3", "HE",
    })
    # model uses common aliases too
    genes.update({"RIG-I", "MDA5", "LGP2", "PKR", "IPS1", "MAVS"})
    return genes


DISCOVERY_PATH = DATA_PAPERS / "gene_discovery.jsonl"


def log_discovery(pid, symbol, role):
    """Non-panel gene seen in a paper — the pattern over many papers becomes
    a candidate (user: 'a large pattern over many papers becomes more than
    incidental'). Appended per occurrence; aggregate counts on export."""
    with DISCOVERY_PATH.open("a") as f:
        f.write(json.dumps({
            "paper_id": pid, "gene": symbol, "role": (role or "")[:200],
        }, ensure_ascii=False) + "\n")


def append_jsonl(path, records):
    with path.open("a") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def jsonl_done_ids(path):
    done = set()
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                done.add(json.loads(line)["paper_id"])
            except Exception:
                pass
    return done


# ---------------------------------------------------------------- Phase B

SUMMARY_PROMPT = """You write paper summaries for an avian influenza research resource.

Read the paper and write:
1. A summary of EXACTLY TWO sentences: what the paper did and what it found.
2. A main_conclusion of EXACTLY ONE sentence: the single most important takeaway.

RULES:
- Be specific: include concrete numbers (species counts, mortality rates, fold-changes, sample sizes), virus clades/subtypes, species names, gene names
- Do NOT start with "This paper", "This study", "The study", "We", or "The authors"
- Do NOT speculate beyond what the paper reports
- Keep each sentence under 45 words
- If the paper is a review, summarize its scope and key synthesis points

Return ONLY JSON: {"summary": "...", "main_conclusion": "..."}"""


def rebuild_summaries(url, model, workers, limit, paper=None):
    papers = load_papers()
    mds = md_map()
    done = {p["id"] for p in papers if p.get("summary_v2")}
    queue = [p for p in papers if p["id"] in mds and p["id"] not in done]
    if paper:
        queue = [p for p in queue if p["id"] == paper]
    if limit:
        queue = queue[:limit]
    print(f"[B] summaries to rebuild: {len(queue)} (done: {len(done)})")

    def work(p):
        text = mds[p["id"]].read_text(errors="replace")[:90000]
        try:
            content = chat(SUMMARY_PROMPT, text, url, model)
            result = extract_json(content)
            if isinstance(result, dict) and result.get("summary"):
                s = result["summary"].strip()
                c = (result.get("main_conclusion") or "").strip()
                if len(s) > 40:
                    return p["id"], s, c
        except Exception as e:
            print(f"  {p['id']}: {str(e)[:60]}")
        return p["id"], None, None

    updated = 0
    by_id = {p["id"]: p for p in papers}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (pid, s, c) in enumerate(ex.map(work, queue), 1):
            if s:
                by_id[pid]["summary"] = s
                by_id[pid]["main_conclusion"] = c
                by_id[pid]["summary_v2"] = True
                updated += 1
            if i % 25 == 0:
                print(f"  [{i}/{len(queue)}] {updated} rebuilt")
                save_papers(papers)  # checkpoint

    save_papers(papers)
    print(f"[B] rebuilt {updated}/{len(queue)} (total v2: {updated + len(done)})")
    _llm_track("summaries", model, "summary-v2", updated,
               notes=f"rebuilt {updated} paper summaries")


# ---------------------------------------------------------------- Phase C1/C2

GENE_ROUND1 = """You extract gene-level claims from a scientific paper about avian influenza.

Identify ONE gene that this paper substantively discusses (central to a finding, supporting evidence, or clearly characterized). Then state what the paper says about that gene's role in infection, immunity, or host response.

Return ONLY JSON:
{"gene": "SYMBOL", "role": "one sentence: what the paper says about this gene", "tier": "central|supporting|background", "quote": "one verbatim sentence from the paper about this gene"}

If the paper discusses NO genes at all, return {"gene": false}."""

GENE_ROUNDN = """You extract gene-level claims from a scientific paper about avian influenza.

Previously extracted genes (DO NOT repeat these): {exclude}

Identify ONE MORE gene that this paper substantively discusses, not in the list above. If every discussed gene is already in the list, return {"gene": false}.

Return ONLY JSON:
{"gene": "SYMBOL", "role": "one sentence: what the paper says about this gene", "tier": "central|supporting|background", "quote": "one verbatim sentence from the paper about this gene"}

If no genes remain, return {"gene": false}."""

CONCL_ROUND1 = """Extract ONE key conclusion from this avian influenza paper — a specific, evidence-backed takeaway (with numbers where possible), NOT a restatement of the aim.

Return ONLY JSON: {"conclusion": "one sentence", "quote": "verbatim supporting sentence"}
If the paper supports no clear conclusion, return {"conclusion": false}."""

CONCL_ROUNDN = """Previously extracted conclusions (DO NOT repeat):\n{exclude}\n\nExtract ONE MORE key conclusion from this paper, distinct from all above. If all conclusions have been captured, return {"conclusion": false}.

Return ONLY JSON: {"conclusion": "one sentence", "quote": "verbatim supporting sentence"}"""


def iterative_extract(pid, md_path, round1_prompt, roundn_prompt, url, model,
                      max_rounds=15, verify=None):
    """The user's exclusion loop: extract one item, exclude it, repeat until false."""
    text = md_path.read_text(errors="replace")[:90000]
    items = []
    excluded = []
    prompt = round1_prompt
    for round_i in range(max_rounds):
        try:
            content = chat(prompt, text, url, model, max_tokens=4000)
            result = extract_json(content)
        except Exception as e:
            print(f"    {pid} round {round_i}: {str(e)[:60]}")
            break
        if not isinstance(result, dict):
            break
        if "gene" in result and result.get("gene") is False:
            break
        if "conclusion" in result and result.get("conclusion") is False:
            break
        item_key = (result.get("gene") or result.get("conclusion") or "").strip()
        if not item_key:
            break
        # verify gene symbol if requested; unknowns feed the discovery bucket
        if verify and "gene" in result:
            sym = str(result["gene"]).upper().strip()
            if sym not in verify:
                log_discovery(pid, sym, result.get("role"))
                excluded.append(sym)
                prompt = roundn_prompt.replace("{exclude}", ", ".join(excluded[:40]))
                continue
            result["gene"] = sym
        # grounding: quote must be in text
        q = re.sub(r'\s+', ' ', (result.get("quote") or "")).strip()
        norm = re.sub(r'\s+', ' ', text)
        if len(q) > 15 and (q in norm or
                            re.sub(r'[""''—–]', '', q.lower()) in re.sub(r'[""''—–]', '', norm.lower())):
            items.append(result)
            excluded.append(item_key)
        else:
            # ungrounded — still exclude so the loop progresses
            excluded.append(item_key)
        prompt = roundn_prompt.replace("{exclude}", ", ".join(excluded[:40]))
    return items


def run_gene_claims(url, model, workers, limit, paper=None):
    papers = load_papers()
    mds = md_map()
    out = DATA_PAPERS / "gene_claims.jsonl"
    done = jsonl_done_ids(out)
    verify = known_genes()
    queue = [p for p in papers if p["id"] in mds and p["id"] not in done]
    if paper:
        queue = [p for p in queue if p["id"] == paper]
    if limit:
        queue = queue[:limit]
    print(f"[C1] gene-claim papers: {len(queue)} (done: {len(done)}, "
          f"panel symbols: {len(verify)})")

    def work(p):
        items = iterative_extract(p["id"], mds[p["id"]], GENE_ROUND1, GENE_ROUNDN,
                                  url, model, verify=verify)
        return {"paper_id": p["id"], "records": items}

    with ThreadPoolExecutor(max_workers=workers) as ex, out.open("a") as f:
        for i, rec in enumerate(ex.map(work, queue), 1):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 10 == 0:
                print(f"  [{i}/{len(queue)}]")
    print(f"[C1] gene claims done → {out}")
    _llm_track("gene_claims", model, "claims-v2", len(queue),
               notes=f"gene-claim extraction for {len(queue)} papers")


def run_conclusions(url, model, workers, limit, paper=None):
    papers = load_papers()
    mds = md_map()
    out = DATA_PAPERS / "paper_conclusions.jsonl"
    done = jsonl_done_ids(out)
    queue = [p for p in papers if p["id"] in mds and p["id"] not in done]
    if paper:
        queue = [p for p in queue if p["id"] == paper]
    if limit:
        queue = queue[:limit]
    print(f"[C2] conclusions papers: {len(queue)} (done: {len(done)})")

    def work(p):
        items = iterative_extract(p["id"], mds[p["id"]], CONCL_ROUND1, CONCL_ROUNDN,
                                  url, model, max_rounds=8)
        return {"paper_id": p["id"], "records": items}

    with ThreadPoolExecutor(max_workers=workers) as ex, out.open("a") as f:
        for i, rec in enumerate(ex.map(work, queue), 1):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 10 == 0:
                print(f"  [{i}/{len(queue)}]")
    print(f"[C2] conclusions done → {out}")


# ---------------------------------------------------------------- Phase D

def load_models():
    inf = json.loads((ROOT / "data" / "model" / "avian_h5n1_model.json").read_text())
    spread = json.loads((ROOT / "data" / "model" / "h5n1_spread_model.json").read_text())
    return inf, spread


def model_stage_summary(model, kind):
    lines = []
    for stage in model["stages"]:
        genes = ", ".join(g for g, _ in stage.get("genes", [])[:8])
        lines.append(f"- {stage['id']} ({stage.get('title', stage['id'])}): {stage.get('desc', '')[:150]}"
                     + (f" [genes: {genes}]" if genes else ""))
    return "\n".join(lines)


VERIFY_PROMPT = """You are verifying a scientific model against a paper.

MODEL ({kind} model — avian influenza):
{stages}

TASK: For each stage above, judge what THIS paper does to it:
- "agrees": the paper's findings support the stage as described
- "disagrees": the paper contradicts the stage
- "changes": the paper modifies details of the stage (describe how)
- "adds": the paper adds new elements to the stage
- "not_relevant": the paper doesn't speak to this stage

RULES:
- Every verdict except not_relevant MUST include a verbatim quote from the paper
- Be conservative: only verdict a stage if the paper genuinely speaks to it
- Return one entry per stage id

Return ONLY a JSON array:
[{{"stage": "stage_id", "verdict": "agrees|disagrees|changes|adds|not_relevant", "note": "one sentence", "quote": "verbatim sentence or empty for not_relevant"}}]"""


def run_model_verify(url, model, workers, limit, paper=None):
    papers = load_papers()
    mds = md_map()
    inf, spread = load_models()
    out = DATA_PAPERS / "model_verdicts.jsonl"
    done = jsonl_done_ids(out)
    # molecular papers only: scope hints
    queue = [p for p in papers
             if p["id"] in mds and p["id"] not in done
             and p.get("scope") in ("avian", "mammalian", "viral-biology", "mixed",
                                    "avian-epi", "vaccination")]
    if paper:
        queue = [p for p in queue if p["id"] == paper]
    if limit:
        queue = queue[:limit]
    print(f"[D] model-verify papers: {len(queue)} (done: {len(done)})")

    def work(p):
        text = mds[p["id"]].read_text(errors="replace")[:90000]
        results = {}
        for kind, model_json in (("infection", inf), ("spread", spread)):
            try:
                prompt = VERIFY_PROMPT.format(
                    kind=kind, stages=model_stage_summary(model_json, kind))
                content = chat(prompt, text, url, model, max_tokens=6000)
                verdicts = extract_json(content)
                if isinstance(verdicts, list):
                    # grounding: keep quotes only if verbatim
                    norm = re.sub(r'\s+', ' ', text)
                    for v in verdicts:
                        q = re.sub(r'\s+', ' ', (v.get("quote") or "")).strip()
                        if v.get("verdict") != "not_relevant" and (
                                not q or (q not in norm and
                                re.sub(r'[""''—–]', '', q.lower()) not in
                                re.sub(r'[""''—–]', '', norm.lower()))):
                            v["verdict"] = "not_relevant"  # ungrounded → demote
                    results[kind] = verdicts
            except Exception as e:
                print(f"    {p['id']} {kind}: {str(e)[:60]}")
        return {"paper_id": p["id"], "verdicts": results}

    with ThreadPoolExecutor(max_workers=workers) as ex, out.open("a") as f:
        for i, rec in enumerate(ex.map(work, queue), 1):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if i % 10 == 0:
                print(f"  [{i}/{len(queue)}]")
    print(f"[D] model verdicts → {out}")


# ---------------------------------------------------------------- export

def export():
    """Merge campaign outputs into served data + display homes."""
    papers = load_papers()
    by_id = {p["id"]: p for p in papers}

    # 0. connections publish gate (D76/D77): approved relationships only
    subprocess.run([sys.executable,
                    str(ROOT / "scripts" / "papers" / "connections.py"),
                    "export"], check=False)
    # 0b. serve gene profiles (D92)
    subprocess.run([sys.executable,
                    str(ROOT / "scripts" / "papers" /
                        "serve_gene_profiles.py")], check=False)

    # 1. conclusions → papers.json (display on paper cards/detail)
    concl_path = DATA_PAPERS / "paper_conclusions.jsonl"
    if concl_path.exists():
        n = 0
        for line in concl_path.read_text().splitlines():
            rec = json.loads(line)
            p = by_id.get(rec["paper_id"])
            if p is not None and rec.get("records"):
                p["conclusions_list"] = [r["conclusion"] for r in rec["records"]]
                n += 1
        print(f"[export] conclusions_list → {n} papers")

    # 2. absence summary → per-gene literature impact (interior artifact).
    #    Phase 2 Step 3: this used to be written in-place into the shipped
    #    gene catalogue (a second writer, and nothing on the site reads
    #    impact_if_absent_lit). Now exported next to its source in data/papers/.
    abs_path = DATA_PAPERS / "gene_absence_summary.json"
    if abs_path.exists():
        abs_data = json.loads(abs_path.read_text())
        catalogue = json.loads((ROOT / "web" / "public" / "data" /
                                "gene_catalogue.json").read_text()).get("gene_catalogue", {})
        lit_out = {}
        for gene, groups in abs_data.items():
            if gene not in catalogue:
                continue
            lit_out[gene] = {
                "counts": {cls: len(recs) for cls, recs in groups.items()},
                "detail": {
                    cls: [
                        {"phenotype": r["phenotype"], "paper_id": r["paper_id"],
                         "year": r.get("year"), "manipulation": r["manipulation"],
                         "host": r["host"]}
                        for r in recs[:8]]
                    for cls, recs in groups.items()},
            }
        lit_path = DATA_PAPERS / "impact_if_absent_lit.json"
        lit_path.write_text(json.dumps(lit_out, indent=1, ensure_ascii=False))
        print(f"[export] impact_if_absent_lit → {len(lit_out)} genes "
              f"in data/papers/impact_if_absent_lit.json")

    # 3. gene claims summary (counts) — visible on gene pages via wiki rebuild
    gc_path = DATA_PAPERS / "gene_claims.jsonl"
    if gc_path.exists():
        from collections import Counter
        gene_counts = Counter()
        for line in gc_path.read_text().splitlines():
            rec = json.loads(line)
            for r in rec.get("records", []):
                gene_counts[r["gene"]] += 1
        out = ROOT / "web" / "public" / "data" / "gene_lit_claims.json"
        out.write_text(json.dumps(
            {g: {"papers": c} for g, c in gene_counts.most_common()}, indent=1))
        print(f"[export] gene_lit_claims → {len(gene_counts)} genes")

    # 3b. discovery bucket: non-panel genes recurring across papers (D74 q3)
    disc_path = DATA_PAPERS / "gene_discovery.jsonl"
    if disc_path.exists():
        from collections import defaultdict
        seen = defaultdict(lambda: {"papers": set(), "roles": []})
        for line in disc_path.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            seen[d["gene"]]["papers"].add(d["paper_id"])
            if d.get("role") and len(seen[d["gene"]]["roles"]) < 3:
                seen[d["gene"]]["roles"].append(d["role"])
        candidates = sorted(
            ((g, len(v["papers"]), v["roles"]) for g, v in seen.items()),
            key=lambda x: -x[1])
        disc_out = ROOT / "web" / "public" / "data" / "gene_discovery.json"
        disc_out.write_text(json.dumps(
            [{"gene": g, "papers": n, "example_roles": roles}
             for g, n, roles in candidates], indent=1, ensure_ascii=False))
        recurring = [c for c in candidates if c[1] >= 3]
        print(f"[export] discovery bucket: {len(candidates)} non-panel genes "
              f"({len(recurring)} recurring ≥3 papers)")

    # 3c. absence summary → served (species-aware model view)
    abs_src = DATA_PAPERS / "gene_absence_summary.json"
    if abs_src.exists():
        import shutil
        shutil.copy(abs_src, ROOT / "web" / "public" / "data" / "gene_absence_summary.json")
        print("[export] gene_absence_summary → web/public/data/")

    # 4. wiki rebuild (gene pages get claims via findings/roles refresh)
    print("[export] rebuilding wiki pages…")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "papers" / "build_wiki_pages.py")],
                   check=False)

    # 5. save papers.json
    save_papers(papers)
    print(f"[export] papers.json saved ({len(papers)} papers)")

    # 6. model verdict tally (informational — model edits reviewed manually)
    mv = DATA_PAPERS / "model_verdicts.jsonl"
    if mv.exists():
        from collections import Counter
        tally = {"infection": Counter(), "spread": Counter()}
        for line in mv.read_text().splitlines():
            rec = json.loads(line)
            for kind, verdicts in rec.get("verdicts", {}).items():
                for v in verdicts:
                    if v.get("verdict") and v["verdict"] != "not_relevant":
                        tally[kind][f"{v.get('stage')}:{v['verdict']}"] += 1
        print("[export] model verdict tally (top):")
        for kind in tally:
            for k, c in tally[kind].most_common(8):
                print(f"  {kind} {k}: {c}")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["preflight", "summaries", "genes",
                                      "connections", "verify", "export", "all"])
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--paper", help="single paper id (iterate/test mode)")
    ap.add_argument("--no-network", action="store_true",
                    help="preflight only: local pass, no OA recovery")
    args = ap.parse_args()

    if args.phase in ("preflight", "all"):
        extra = ("--no-network",) if args.no_network else ()
        subprocess.run([sys.executable,
                        str(ROOT / "scripts" / "papers" / "corpus_preflight.py"),
                        *extra],
                       check=False)
    if args.phase in ("summaries", "all"):
        rebuild_summaries(args.url, args.model, args.workers, args.limit, args.paper)
    if args.phase in ("genes", "all"):
        run_gene_claims(args.url, args.model, args.workers, args.limit, args.paper)
        run_conclusions(args.url, args.model, args.workers, args.limit, args.paper)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "papers" / "mine_absence_phenotypes.py")],
                       check=False)
    if args.phase in ("connections", "all"):
        conn = ROOT / "scripts" / "papers" / "connections.py"
        subprocess.run([sys.executable, str(conn), "search"], check=False)
        subprocess.run([sys.executable, str(conn), "classify",
                        "--url", args.url, "--model", args.model,
                        "--workers", str(args.workers)], check=False)
        # clade discovery lane (D91): scan for novel genotype/clade/subtype
        # designations + LLM verification
        subprocess.run([sys.executable,
                        str(ROOT / "scripts" / "papers" /
                            "clade_discovery.py"),
                        "--llm", "--url", args.url, "--model", args.model],
                       check=False)
    if args.phase in ("verify", "all"):
        run_model_verify(args.url, args.model, args.workers, args.limit, args.paper)
    if args.phase in ("export", "all"):
        export()


if __name__ == "__main__":
    main()
