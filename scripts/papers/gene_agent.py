#!/usr/bin/env python3
"""
Gene enrichment agent (D92 Phase 3): multi-turn Muse agent that searches
papers, reads text, and writes rich gene profiles with citations.

The agent has three tools — search, read, gene_info — and NO shell access.
Each turn's tool calls and LLM responses are recorded as a transcript.
The agent writes profiles to data/papers/gene_profiles/{SYMBOL}.json.

Usage:
  pixi run python scripts/papers/gene_agent.py --gene DDX58
  pixi run python scripts/papers/gene_agent.py --batch 5
  pixi run python scripts/papers/gene_agent.py --check
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import httpx

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
GENE_PRESENCE = ROOT / "web/public/data/gene_catalogue.json"
RELATIONSHIPS = ROOT / "web/public/data/gene_relationships.json"
WIKI_GENES = ROOT / "web/public/data/wiki_genes.json"
EVIDENCE_COUNTS = ROOT / "web/public/data/gene_evidence_counts.json"
STAGE_ASSIGN = ROOT / "web/public/data/gene_stage_assignment.json"
HOST_ASSOC = ROOT / "web/public/data/gene_host_association.json"
OUT_DIR = ROOT / "data/papers/gene_profiles"
TRANSCRIPT_DIR = OUT_DIR / "transcripts"
DONE_DIR = OUT_DIR / "done"

sys_path = str(ROOT / "scripts" / "papers")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
try:
    from llm_provenance import track as _llm_track
except ImportError:
    _llm_track = lambda *a, **k: None

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

import hashlib
def h12(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


# ============================================================ tools (sandboxed)

def tool_search_papers(query, max_results=10):
    """Search paper markdown files via ripgrep. Returns [{paper_id, line_match}]."""
    cmd = ["rg", "-i", "--json", "-m", str(max_results),
           "-e", query, str(MD_DIR)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        return {"error": str(e)[:100]}
    results = []
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") != "match":
            continue
        path = ev["data"]["path"]["text"]
        pid = Path(path).stem
        text = ev["data"]["lines"]["text"].strip()[:200]
        results.append({"paper_id": pid, "match": text})
    return {"results": results[:max_results]}


def tool_get_paper_text(paper_id, start=0, length=3000):
    """Read a chunk of paper markdown. Returns text or error."""
    md = MD_DIR / f"{paper_id}.md"
    if not md.exists():
        return {"error": f"no markdown for {paper_id}"}
    text = md.read_text(errors="replace")
    chunk = text[start:start + length]
    return {"paper_id": paper_id, "start": start, "length": len(chunk),
            "total": len(text), "text": chunk}


def _presence_species(symbol):
    """Per-gene species→status map from the parquet matrix (Phase 2 Step 3:
    the catalogue no longer ships a transpose copy)."""
    try:
        import polars as pl
        pq = ROOT / "web/public/data/gene_presence.parquet"
        df = pl.read_parquet(pq).filter(pl.col("gene") == symbol)
        return dict(zip(df["species"], df["status"]))
    except Exception:
        return {}


def tool_get_gene_info(symbol):
    """Get catalogue info, presence, connections, host association for a gene."""
    info = {"symbol": symbol}
    gp = json.loads(GENE_PRESENCE.read_text())["gene_catalogue"]
    if symbol in gp:
        info["name"] = gp[symbol].get("name", "")
        info["importance"] = gp[symbol].get("importance", "")
        info["aliases"] = gp[symbol].get("aliases", [])
        info["presence_species"] = _presence_species(symbol)
    sa = json.loads(STAGE_ASSIGN.read_text())
    if symbol in sa:
        info["stage"] = sa[symbol].get("stage")
        info["stage_source"] = sa[symbol].get("source")
    ha = json.loads(HOST_ASSOC.read_text())["genes"]
    if symbol in ha:
        info["host_association"] = ha[symbol]
    rel = json.loads(RELATIONSHIPS.read_text())
    edges = [e for e in rel.get("edges", [])
             if symbol in (e["from"], e["to"])]
    if edges:
        info["connections"] = [
            {"to" if e["from"] == symbol else "from":
             e["to"] if e["from"] == symbol else e["from"],
             "mechanism": e["mechanism"],
             "evidence_count": len(e.get("evidence", []))}
            for e in edges]
    ec = json.loads(EVIDENCE_COUNTS.read_text())
    if symbol in ec:
        info["evidence_counts"] = ec[symbol]
    return info


TOOLS = {
    "search_papers": tool_search_papers,
    "get_paper_text": tool_get_paper_text,
    "get_gene_info": tool_get_gene_info,
}

TOOL_DESCRIPTIONS = """You have three tools available. Call them by returning a JSON object:

{"tool": "search_papers", "query": "IFIT5 duck upregulated", "max_results": 10}
→ Returns papers matching the search (paper IDs + matching lines).

{"tool": "get_paper_text", "paper_id": "some_paper_2024", "start": 0, "length": 3000}
→ Returns a chunk of the paper's text (use start to paginate).

{"tool": "get_gene_info", "symbol": "IFIT5"}
→ Returns gene catalogue info, species presence, connections, host association.

Use search to find relevant papers, then read them to extract findings.
You may call tools as many times as needed. When done, return your final answer as:

{"tool": "write_profile", "profile": {...}}"""


# ============================================================ agent

SYSTEM_PROMPT = """You are a research scientist writing a gene profile for an avian-influenza database.

WORKFLOW (follow exactly — you have limited turns):
1. Call get_gene_info once to see the gene's existing data.
2. Call search_papers once or twice with the gene symbol + "avian influenza" or "H5N1".
3. Call get_paper_text on 2-3 of the most relevant papers (read 3000 chars each).
4. IMMEDIATELY write your profile with write_profile. Do NOT search more.

You have about 8 tool-call turns. Use them wisely. The profile is MORE important than exhaustive searching.

NEVER copy text from papers. Paraphrase into clear scientific prose, and ALWAYS cite the paper_id.

The profile MUST include these fields:

1. "overview" — 2-3 sentences: what this gene does specifically in the context of H5N1/avian influenza host response. Written for a researcher who knows immunology but not this gene.

2. "function" — what the protein does molecularly (1-2 sentences).

3. "species_differences" — how this gene differs across species. CRITICAL: include resistant vs susceptible species differences (e.g., ducks vs chickens, if the gene is present/absent/functional in different species). If a species difference is a KEY finding (like "ducks have functional IFIT5 but chickens don't"), highlight it.

4. "key_findings" — list of 5-10 findings, each with:
   - "text": paraphrased finding (1-2 sentences, your own words)
   - "paper_id": the paper this comes from (required)
   - "tier": "core" if the paper focused on this gene (⭐), or "mentioned" if the gene appeared in a broader screen/table (📊)
   - "direction": "upregulated"/"downregulated"/"protective"/"required"/"antiviral"/"proviral"/"neutral"/"unclear"

5. "strain_interactions" — list of strain-specific effects if any (e.g., "PB2-627K variant shows enhanced replication in IFIT5-knockout cells"). Each with paper_id.

6. "clinical_relevance" — 1-2 sentences on why this matters for H5N1 control/treatment.

7. "cross_study_patterns" — if the gene appears in ≥3 papers in screening contexts (transcriptomics, proteomics), note the pattern (e.g., "consistently upregulated in resistant species across 4 independent transcriptomics studies").

RULES:
- ALWAYS return a valid JSON profile — even if evidence is limited or no papers are found
- If no papers mention this gene, write: "overview": "Limited data available..." and "key_findings": []
- If only gene catalogue info is available, describe the known function and species presence from that
- Cite paper_ids exactly as they appear in your tool results
- NEVER copy text from papers — always paraphrase
- Be specific: include fold-changes, species names, time points, strain names when available
- If evidence is limited, say so honestly
- Classify each finding honestly as "core" (paper focused on this gene) or "mentioned" (broader screen)

CRITICAL: Your response MUST be a valid JSON object starting with {"overview": — not reasoning text, not a plan, not an echo of the input. Return the profile IMMEDIATELY."""


def run_agent_for_gene(symbol, url, model, max_turns=15):
    """Deterministic pipeline: fetch data → search papers → read top papers
    → single LLM synthesis call. Transcript records every tool execution."""
    transcript = []
    profile = None

    # Step 1: gene info
    gene_info = tool_get_gene_info(symbol)
    transcript.append({"step": "get_gene_info", "symbol": symbol,
                       "keys": list(gene_info.keys())})

    # Step 2: search for papers
    aliases = gene_info.get("aliases", [])
    search_terms = [symbol] + aliases[:2]
    all_hits = {}
    for term in search_terms:
        result = tool_search_papers(f"{term} avian influenza H5N1", 15)
        for hit in result.get("results", []):
            all_hits[hit["paper_id"]] = hit["match"]
    transcript.append({"step": "search_papers",
                       "queries": search_terms,
                       "papers_found": len(all_hits)})

    # Step 3: read top 5 papers (by evidence count)
    papers_by_id = {p["id"]: p for p in
                    json.loads(PAPERS_JSON.read_text())["papers"]}
    ranked = sorted(all_hits.keys(),
                    key=lambda pid: -papers_by_id.get(pid, {}).get("year", 0))
    paper_texts = {}
    for pid in ranked[:5]:
        result = tool_get_paper_text(pid, 0, 4000)
        if "text" in result:
            paper_texts[pid] = result["text"][:4000]
    transcript.append({"step": "get_paper_text",
                       "papers_read": list(paper_texts.keys())})

    # Step 4: wiki data for this gene
    wiki = json.loads(WIKI_GENES.read_text())["genes"]
    wiki_entry = wiki.get(symbol, {})
    wiki_roles = wiki_entry.get("roles", [])[:8]
    wiki_findings = wiki_entry.get("key_findings", [])[:6]

    # Step 5: single LLM synthesis call
    context_parts = [
        f"GENE: {symbol}",
        f"GENE INFO: {json.dumps(gene_info, ensure_ascii=False, default=str)[:2000]}",
        f"\nWIKI ROLES (from prior extraction):",
    ]
    for r in wiki_roles:
        context_parts.append(
            f"  - [{r.get('tier', '?')}] {r.get('role', '?')} "
            f"(paper: {r.get('paper_id', '?')}, {r.get('year', '?')})")
    context_parts.append(f"\nWIKI KEY FINDINGS:")
    for f in wiki_findings:
        context_parts.append(
            f"  - {f.get('finding', '?')} (paper: {f.get('paper_id', '?')})")
    context_parts.append(f"\nPAPERS FOUND ({len(all_hits)} total, reading top {len(paper_texts)}):")
    for pid, text in paper_texts.items():
        year = papers_by_id.get(pid, {}).get("year", "?")
        title = papers_by_id.get(pid, {}).get("title", "?")[:80]
        context_parts.append(f"\n--- PAPER {pid} ({year}): {title} ---")
        context_parts.append(text[:3000])

    if not paper_texts:
        context_parts.append(
            "\nNOTE: No papers were found mentioning this gene. "
            "Write a minimal profile from the gene info above: describe "
            "the known function, species presence (from gene_info), and "
            "note that direct H5N1 evidence is limited. "
            "Return valid JSON with at minimum an 'overview' field.")

    prompt = "\n".join(context_parts)

    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt +
                 "\n\nWrite the profile NOW. Return ONLY the JSON."},
            ],
            "max_tokens": 32000, "temperature": 0.1,
        }, timeout=900)
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        content = (msg.get("content") or
                   msg.get("reasoning_content") or "").strip()
    except Exception as e:
        transcript.append({"step": "llm_synthesis", "error": str(e)[:150]})
        return None, transcript

    transcript.append({"step": "llm_synthesis",
                       "response_length": len(content),
                       "response_head": content[:300]})

    # Parse the profile JSON — robust extraction from LLM output
    # Strategy: try multiple approaches in order

    # A. Strip markdown code fences first
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', content, flags=re.MULTILINE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # B. Try direct parse of the cleaned text
    for text in (content, cleaned):
        try:
            v = json.loads(text)
            if isinstance(v, dict) and "overview" in v:
                return v, transcript
        except Exception:
            pass

    # C. Scan for balanced JSON objects containing "overview"
    # (works with text before/after the JSON)
    for text in (cleaned, content):
        depth = 0
        start = None
        in_str = False
        esc = False
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
                            if isinstance(v, dict) and "overview" in v:
                                return v, transcript
                        except Exception:
                            pass
                        start = None

    # D. Last resort: find "overview" key and try to build the object
    # by scanning backward to the nearest `{` and forward to matching `}`
    m = re.search(r'"overview"\s*:', content)
    if m:
        # scan backward for opening brace
        brace_depth = 0
        for i in range(m.start(), -1, -1):
            if content[i] == '{':
                # scan forward for the matching close
                d = 0
                in_s = False
                esc2 = False
                for j in range(i, len(content)):
                    if in_s:
                        if esc2:
                            esc2 = False
                        elif content[j] == '\\':
                            esc2 = True
                        elif content[j] == '"':
                            in_s = False
                        continue
                    if content[j] == '"':
                        in_s = True
                    elif content[j] == '{':
                        d += 1
                    elif content[j] == '}':
                        d -= 1
                        if d == 0:
                            try:
                                v = json.loads(content[i:j + 1])
                                if isinstance(v, dict) and "overview" in v:
                                    return v, transcript
                            except Exception:
                                pass
                            break
                break

    # E. If still no profile, try to construct a minimal one from
    # whatever fields we can find via regex
    fields = {}
    for field in ('overview', 'function', 'species_differences',
                  'clinical_relevance', 'cross_study_patterns'):
        fm = re.search(
            f'"{field}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"', content)
        if fm:
            fields[field] = fm.group(1).replace('\\n', '\n').replace(
                '\\"', '"').replace('\\t', '\t')
    # findings via regex
    findings = []
    for fm in re.finditer(
            r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"'
            r'.*?"paper_id"\s*:\s*"([^"]+)"'
            r'.*?"tier"\s*:\s*"([^"]+)"', content, re.DOTALL):
        findings.append({"text": fm.group(1).replace('\\n', '\n'),
                         "paper_id": fm.group(2), "tier": fm.group(3)})
    if findings:
        fields["key_findings"] = findings
    if "overview" in fields:
        return fields, transcript

    return None, transcript


def get_gene_queue():
    """Literature genes ordered by importance, excluding done ones."""
    gp = json.loads(GENE_PRESENCE.read_text())["gene_catalogue"]
    st = json.loads((ROOT / "data/papers/connections/search_status.json").read_text())
    lit = {g for g, r in st["genes"].items() if r["status"] == "hit"}
    importance = {"critical": 0, "high": 1, "standard": 2}
    genes = [(g, importance.get(gp.get(g, {}).get("importance", "standard"), 3))
             for g in lit if g in gp]
    genes.sort(key=lambda x: (x[1], x[0]))
    done = set()
    if DONE_DIR.exists():
        done = {f.stem for f in DONE_DIR.glob("*.json")}
    return [g for g, _ in genes if g not in done], len(done), len(genes)


def run_one(gene, url, model):
    """Run agent for one gene and save results."""
    profile, transcript = run_agent_for_gene(gene, url, model)

    # always save transcript (even on failure) for debugging
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    (TRANSCRIPT_DIR / f"{gene}.json").write_text(
        json.dumps({"gene": gene, "turns": transcript,
                    "success": bool(profile),
                    "ts": datetime.now().isoformat(timespec="seconds")},
                   indent=1, ensure_ascii=False))

    if not profile:
        return gene, None, transcript

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    DONE_DIR.mkdir(exist_ok=True)

    # Save profile
    profile["symbol"] = gene
    profile["generated"] = datetime.now().isoformat(timespec="seconds")
    profile["model"] = model
    (OUT_DIR / f"{gene}.json").write_text(
        json.dumps(profile, indent=1, ensure_ascii=False))

    # Save transcript
    (TRANSCRIPT_DIR / f"{gene}.json").write_text(
        json.dumps({"gene": gene, "turns": transcript,
                    "ts": datetime.now().isoformat(timespec="seconds")},
                   indent=1, ensure_ascii=False))

    # Mark done
    (DONE_DIR / f"{gene}.json").write_text('{"done": true}')

    return gene, profile, transcript


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gene", help="single gene")
    ap.add_argument("--batch", type=int, default=0,
                    help="process N genes from the queue")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    if args.check:
        queue, done, total = get_gene_queue()
        print(f"gene profiles: {done} done, {len(queue)} todo, {total} total")
        if queue:
            print(f"next up: {queue[:10]}")
        return

    if args.gene:
        gene, profile, transcript = run_one(args.gene, args.url, args.model)
        if profile:
            print(f"✓ {gene}: profile written "
                  f"({len(profile.get('key_findings', []))} findings, "
                  f"{len(transcript)} turns)")
        else:
            print(f"✗ {gene}: no profile extracted")
            print(json.dumps(transcript[-1], default=str)[:200])
        return

    if args.batch:
        queue, done, total = get_gene_queue()
        todo = queue[:args.batch]
        print(f"batch: {len(todo)} genes (done: {done}, remaining: {len(queue)})")
        succeeded = 0
        for gene in todo:
            result_gene, profile, transcript = run_one(gene, args.url, args.model)
            if profile:
                n_findings = len(profile.get('key_findings', []))
                print(f"  ✓ {result_gene}: {n_findings} findings")
                succeeded += 1
            else:
                # one retry
                print(f"  ↻ {gene}: retrying...")
                result_gene, profile, transcript = run_one(gene, args.url, args.model)
                if profile:
                    n_findings = len(profile.get('key_findings', []))
                    print(f"  ✓ {result_gene}: {n_findings} findings (retry)")
                    succeeded += 1
                else:
                    print(f"  ✗ {gene}: failed after retry")
        _llm_track("gene_enrichment", args.model, "agent-v1",
                   succeeded, notes=f"enriched {succeeded}/{len(todo)} genes")


if __name__ == "__main__":
    main()
