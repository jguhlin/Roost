#!/usr/bin/env python3
"""
LLM-powered paper analysis with multi-step extraction and verification.

This script:
1. Loops through all papers in docs/papers_md/
2. Runs discrete extraction steps (metadata, study, genes, species, etc.)
3. Verifies each extraction step separately
4. Combines results into final verified output

Usage:
    pixi run analyze-papers-llm
    pixi run analyze-papers-llm --paper anp32_editing2023.md
    pixi run analyze-papers-llm --skip-verified
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).parent.parent.parent
MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
OUTPUT_DIR = PROJECT_ROOT / "data" / "papers" / "llm_analyses"
VERIFIED_DIR = PROJECT_ROOT / "data" / "papers" / "verified"

# Ensure output directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VERIFIED_DIR.mkdir(parents=True, exist_ok=True)

# Default LLM endpoint (OpenAI-compatible API)
DEFAULT_LLM_BASE_URL = "http://localhost:8001/v1"
DEFAULT_MODEL = "gemma4"

# =============================================================================
# EXTRACTION PROMPTS - Each focused on one thing
# =============================================================================

PROMPTS = {
    "metadata": {
        "extract": """Extract bibliographic metadata from this research paper.

Return JSON:
{{
  "title": "full title of the paper",
  "authors": ["list", "of", "author", "names"],
  "journal": "journal name or organization",
  "year": 2023,
  "doi": "10.xxxx/xxxxx or null if not found",
  "paper_type": "research_article|review|case_report|letter|preprint|dispatch|brief_report|commentary|short_communication|strategy|guideline|report|technical_report|circular|perspective|editorial|news|other"
}}

PAPER (first 3000 characters):
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify this metadata extraction against the paper.

PAPER HEADER:
{paper_content}

EXTRACTED:
{extracted}

Be flexible - if the core metadata (title, authors, year) is correct, mark as verified even if paper_type classification is debatable.

Return JSON:
{{
  "status": "verified|partial|incorrect",
  "corrections": {{"field": "corrected_value"}} or {{}},
  "issues": ["list of problems found"]
}}

Respond ONLY with valid JSON.""",
        "use_header": True,
        "temp_extract": 0.2,
        "temp_verify": 0.1,
    },

    "study": {
        "extract": """Extract study information from this research paper.

What were the authors trying to do? What type of study is this? What are the main conclusions?

Return JSON:
{{
  "objectives": ["what the authors were trying to do - 2-4 items"],
  "study_type": "type1,type2 (can combine multiple)",
  "conclusions": ["main conclusions - 2-5 items"]
}}

Study types (can combine with commas, e.g., "phylogenetic,surveillance"):
- experimental: lab experiments, animal trials
- observational: field studies, epidemiological surveys
- genomic: genome sequencing, genetic analysis
- computational: modeling, bioinformatics
- review: systematic reviews, literature reviews
- surveillance: outbreak monitoring, disease tracking
- phylogenetic: evolutionary analysis, phylogenetic trees
- meta_analysis: combining data from multiple studies
- commentary: opinion pieces, editorials, commentaries
- letter: letters to editor, correspondence
- perspective: viewpoint articles, perspectives
- strategy: strategic plans, policy documents, guidelines
- case_report: individual case descriptions
- other: anything that doesn't fit above

PAPER:
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify this study extraction against the paper.

PAPER:
{paper_content}

EXTRACTED:
{extracted}

Focus on whether the objectives and conclusions accurately capture the paper's content.
Be flexible with study_type - if it roughly describes the paper's approach, accept it.

Return JSON:
{{
  "status": "verified|partial|incorrect",
  "corrections": {{"field": ["corrected", "values"]}} or {{}},
  "issues": ["list of problems"]
}}

Respond ONLY with valid JSON.""",
        "use_header": False,
        "temp_extract": 0.3,
        "temp_verify": 0.2,
    },

    "genes": {
        "extract": """Extract gene/protein information from this HPAI research paper.

Capture THREE tiers of gene involvement — recall matters more than precision here
(the verification step filters noise):
1. central: the paper's primary study subjects
2. supporting: genes with a substantive role in results/discussion — including
   siblings and pathway members discussed ALONGSIDE the central genes (e.g. a paper
   about JAK1 signalling that also discusses JAK2 must list BOTH)
3. background: genes discussed meaningfully in the introduction/discussion context

Also check this checklist of panel genes — include any that appear with substance
(but do NOT add any that never appear):
{panel_symbols}

Include genes NOT on the checklist if the paper discusses them — novel discoveries welcome.

IMPORTANT - Do NOT include:
- Antibodies or immunoglobulins (IgG, IgA, monoclonal antibodies, etc.)
- Mutations (e.g., PB2-E627K, T271A) - these go in the mutations section
- Virus subtype names (H5, N1) unless the actual gene (Hemagglutinin, Neuraminidase) is discussed
- Genes appearing ONLY in primer tables or methods reagent lists
- External knowledge - only extract what the paper actually says

If this is an epidemiological/surveillance paper that doesn't discuss genes, return empty list.

Return JSON:
{{
  "genes": [
    {{"name": "gene name", "role": "what paper says about it", "importance": "central|supporting|background"}}
  ]
}}

PAPER:
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify this gene extraction against the paper.

PAPER:
{paper_content}

EXTRACTED:
{extracted}

Check:
1. Are these genes ACTUALLY discussed in the paper text (not just inferred from H5N1 nomenclature)?
2. Are antibodies/immunoglobulins incorrectly listed as genes?
3. Are mutations incorrectly listed as genes?
4. Are the roles based on paper content (not external knowledge)?

An empty gene list is CORRECT for epidemiological/surveillance papers that don't discuss molecular biology.

Return JSON:
{{
  "status": "verified|partial|incorrect|not_applicable",
  "genes_verified": [
    {{"name": "gene", "status": "verified|incorrect|missing_context", "correction": null}}
  ],
  "missing_genes": ["important genes not extracted"],
  "issues": []
}}

Use "not_applicable" if no genes are discussed (epidemiological paper).

Respond ONLY with valid JSON.""",
        "use_header": False,
        "temp_extract": 0.3,
        "temp_verify": 0.2,
    },

    "species": {
        "extract": """Extract species/host information from this HPAI research paper.

List actual animal species (birds, mammals) that were infected, sampled, or studied as hosts.

IMPORTANT:
- Do NOT include cell lines (HEK-293, MDCK, etc.) or in vitro models
- Do NOT include species only mentioned in background/references
- Only include species where actual infection, sampling, or host susceptibility was studied
- If this is a mechanistic/molecular paper with no actual animal hosts studied, return empty list
- Limit to TOP 20 most important species if there are many

Return JSON:
{{
  "species": [
    {{"name": "species name", "finding": "what was found", "infection_status": "confirmed|suspected|susceptible|resistant|sampled|mentioned|unknown"}}
  ]
}}

infection_status guide:
- confirmed: PCR/lab confirmed infection
- suspected: likely infected based on symptoms/mortality
- susceptible: shown to be susceptible in experiments
- resistant: shown to be resistant
- sampled: sampled/tested (regardless of result)
- mentioned: discussed in context of the study
- unknown: status unclear

If no actual host species were studied (e.g., purely molecular/mechanistic study), return:
{{"species": []}}

PAPER:
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify this species extraction against the paper.

PAPER:
{paper_content}

EXTRACTED:
{extracted}

Check:
1. Are these actual host species studied in the paper (not just mentioned in background)?
2. Are cell lines correctly excluded?
3. Are the findings reasonably accurate?

Be flexible with infection_status classification - the important thing is capturing WHICH species were studied, not the exact status label.

An empty species list is CORRECT for mechanistic/molecular papers.

Return JSON:
{{
  "status": "verified|partial|incorrect|not_applicable",
  "species_verified": [
    {{"name": "species", "status": "verified|incorrect", "correction": null}}
  ],
  "issues": []
}}

Use "not_applicable" if no host species were studied (mechanistic paper).

Respond ONLY with valid JSON.""",
        "use_header": False,
        "temp_extract": 0.3,
        "temp_verify": 0.2,
    },

    "mutations": {
        "extract": """Extract mutation information from this HPAI research paper.

List viral mutations or host genetic variants discussed.

Return JSON:
{{
  "mutations": [
    {{"name": "mutation name (e.g. PB2-E627K)", "effect": "what the paper says about its effect"}}
  ]
}}

If no mutations are discussed, return: {{"mutations": []}}

PAPER:
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify this mutation extraction against the paper.

PAPER:
{paper_content}

EXTRACTED:
{extracted}

Are these mutations and their effects accurately described?

Return JSON:
{{
  "status": "verified|partial|incorrect|not_applicable",
  "mutations_verified": [
    {{"name": "mutation", "status": "verified|incorrect", "correction": null}}
  ],
  "issues": []
}}

Respond ONLY with valid JSON.""",
        "use_header": False,
        "temp_extract": 0.3,
        "temp_verify": 0.2,
    },

    "findings": {
        "extract": """Extract key quantitative findings from this research paper.

List specific results with numbers, statistics, or measurements.
Categorise each finding:
- \"infection\" = a biological/epidemiological result about the virus, host,
  disease, immunity, or resistance (mortality %, viral titre, shedding duration,
  transmission rate, fold-change of an immune gene after infection, DEG counts,
  seroprevalence, antibody titres, host-range differences).
- \"methods\" = a technical/sequencing/QC parameter of how the study was done
  (alignment rate, mapping rate, reads per sample, sequencing depth, library
  prep, QC thresholds, number of cells sequenced, database size).

Only include \"methods\" findings when the paper reports them as a notable
methodological result; the focus must be infection findings.
Each finding must be a complete, self-contained sentence fragment readable
outside the paper — never a truncated table dump, gene list, or figure caption.

Return JSON:
{{
  "findings": [
    {{"finding": "specific result", "value": "number or statistic", "context": "conditions/comparison", "category": "infection|methods"}}
  ]
}}

PAPER:
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify these quantitative findings against the paper.

PAPER:
{paper_content}

EXTRACTED:
{extracted}

Are these numbers and findings accurate?

Return JSON:
{{
  "status": "verified|partial|incorrect",
  "findings_verified": [
    {{"finding": "...", "status": "verified|incorrect", "correction": null}}
  ],
  "issues": []
}}

Respond ONLY with valid JSON.""",
        "use_header": False,
        "temp_extract": 0.3,
        "temp_verify": 0.2,
    },

    "novelty": {
        "extract": """Extract novel claims and limitations from this research paper.

What does the paper claim is new or first? What limitations do the authors acknowledge?

Return JSON:
{{
  "novel_claims": ["things claimed as new or first-time findings"],
  "limitations": ["limitations acknowledged by authors"],
  "contradictions": ["any contradictions with prior research mentioned"]
}}

PAPER:
{paper_content}

Respond ONLY with valid JSON.""",

        "verify": """Verify novelty claims and limitations against the paper.

PAPER:
{paper_content}

EXTRACTED:
{extracted}

Are these claims actually made in the paper?

Return JSON:
{{
  "status": "verified|partial|incorrect",
  "corrections": {{}},
  "issues": []
}}

Respond ONLY with valid JSON.""",
        "use_header": False,
        "temp_extract": 0.3,
        "temp_verify": 0.2,
    },
}

# Order of extraction steps
EXTRACTION_STEPS = ["metadata", "study", "genes", "species", "mutations", "findings", "novelty"]


def file_hash(path: Path) -> str:
    """Get MD5 hash of file contents."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def truncate_text(text: str, max_chars: int = 60000) -> str:
    """Truncate text to fit within context window."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... paper truncated for length ...]"


async def call_llm(
    client: httpx.AsyncClient,
    prompt: str,
    temperature: float,
    base_url: str,
    model: str,
) -> str:
    """Call the LLM API and return the response text."""
    url = f"{base_url}/chat/completions"

    # Reasoning models (qwen3.8) burn completion budget on thinking — allow
    # a large budget via env (LLM_MAX_TOKENS) so the JSON survives, and let
    # LLM_DISABLE_THINKING=1 switch thinking off entirely (sglang
    # chat_template_kwargs): extraction needs reading, not reasoning, and
    # thinking-off calls run ~10x faster at 48-worker concurrency.
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4096"))

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if os.environ.get("LLM_DISABLE_THINKING"):
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    response = await client.post(url, json=payload, timeout=300.0)
    response.raise_for_status()

    data = response.json()
    msg = data["choices"][0]["message"]
    # D120: muse-glimmer returns its answer in reasoning_content with
    # content empty — without this fallback every extraction call returns
    # "" and the pass silently produces nothing (the vaccine-triage lesson).
    return msg.get("content") or msg.get("reasoning_content") or ""


def parse_json_response(response_text: str) -> dict:
    """Parse JSON from LLM response, handling common formatting issues."""
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        start_idx = 1 if lines[0].startswith("```") else 0
        end_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        text = "\n".join(lines[start_idx:end_idx])

    # Try to find JSON object in the text
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "error": f"JSON parse error: {e}",
            "raw_response": response_text[:2000],
        }


async def run_step(
    client: httpx.AsyncClient,
    step_name: str,
    paper_content: str,
    paper_header: str,
    base_url: str,
    model: str,
    max_retries: int = 2,
) -> dict:
    """Run a single extraction + verification step with retry logic."""
    config = PROMPTS[step_name]
    content = paper_header if config.get("use_header") else paper_content

    # panel symbol checklist for the genes step (D40) — built once
    global _PANEL_SYMBOLS
    if "_PANEL_SYMBOLS" not in globals():
        try:
            _p = json.loads((PROJECT_ROOT / "web" / "public" / "data" /
                             "gene_catalogue.json").read_text())
            syms = [s for s in _p.get("gene_catalogue", {})
                    if len(s) >= 3 and s.isalpha() and not s.startswith("LOC")]
            _PANEL_SYMBOLS = ", ".join(sorted(syms))
        except Exception:
            _PANEL_SYMBOLS = ""
    fmt_args = {"paper_content": content}
    if "{panel_symbols}" in config["extract"]:
        fmt_args["panel_symbols"] = _PANEL_SYMBOLS

    # Extract with retry for JSON parse errors
    extract_prompt = config["extract"].format(**fmt_args)
    extracted = None
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            extract_response = await call_llm(
                client, extract_prompt, config["temp_extract"], base_url, model
            )
            extracted = parse_json_response(extract_response)

            if "error" not in extracted:
                break  # Success

            # JSON parse error - retry with slightly higher temperature
            last_error = extracted["error"]
            if attempt < max_retries and "JSON parse error" in last_error:
                continue

        except Exception as e:
            last_error = f"Extraction failed: {e}"
            if attempt < max_retries:
                continue
            return {"error": last_error, "step": step_name}

    if extracted is None or "error" in extracted:
        return {"error": last_error or extracted.get("error", "Unknown error"), "step": step_name, "raw": extracted.get("raw_response") if extracted else ""}

    # Verify
    verify_prompt = config["verify"].format(
        paper_content=content,
        extracted=json.dumps(extracted, indent=2)
    )
    try:
        verify_response = await call_llm(
            client, verify_prompt, config["temp_verify"], base_url, model
        )
        verification = parse_json_response(verify_response)
    except Exception as e:
        return {
            "extracted": extracted,
            "verification": {"error": f"Verification failed: {e}"},
            "step": step_name,
        }

    if "error" in verification:
        return {
            "extracted": extracted,
            "verification": {"error": verification["error"]},
            "step": step_name,
        }

    # Apply corrections if any
    corrected = extracted.copy()
    if verification.get("corrections"):
        for field, value in verification["corrections"].items():
            if field in corrected:
                corrected[field] = value

    return {
        "extracted": extracted,
        "corrected": corrected,
        "verification": verification,
        "step": step_name,
        "status": verification.get("status", "unknown"),
    }


async def analyze_paper(
    client: httpx.AsyncClient,
    paper_path: Path,
    base_url: str,
    model: str,
    skip_if_verified: bool = False,
) -> dict:
    """Analyze a single paper with multi-step extraction and verification."""
    paper_id = paper_path.stem
    output_path = OUTPUT_DIR / f"{paper_id}.json"
    verified_path = VERIFIED_DIR / f"{paper_id}.json"

    # Check if already verified
    if skip_if_verified and verified_path.exists():
        with open(verified_path) as f:
            existing = json.load(f)
        current_hash = file_hash(paper_path)
        if existing.get("file_hash") == current_hash:
            print(f"  Skipping {paper_id} (already verified)", flush=True)
            return {"status": "skipped", "paper_id": paper_id}

    print(f"  Analyzing: {paper_id}", flush=True)

    # Read paper content
    full_content = paper_path.read_text(encoding="utf-8", errors="ignore")
    paper_header = full_content[:3000]
    paper_content = truncate_text(full_content)

    # Run all extraction steps
    results = {}
    all_verified = True

    for step in EXTRACTION_STEPS:
        print(f"    [{step}] extracting + verifying...", flush=True)
        step_result = await run_step(
            client, step, paper_content, paper_header, base_url, model
        )
        results[step] = step_result

        if "error" in step_result:
            print(f"      Error: {step_result['error'][:50]}...", flush=True)
            all_verified = False
        else:
            status = step_result.get("status", "unknown")
            print(f"      Status: {status}", flush=True)
            if status not in ["verified", "not_applicable"]:
                all_verified = False

    # Build final output
    verified_result = {
        "paper_id": paper_id,
        "file_hash": file_hash(paper_path),
        "analyzed_at": datetime.now().isoformat(),
        "model": model,
        "all_verified": all_verified,
        "steps": results,
        # Flatten corrected data for easy access
        "metadata": results.get("metadata", {}).get("corrected", {}),
        "study": results.get("study", {}).get("corrected", {}),
        "genes": results.get("genes", {}).get("corrected", {}).get("genes", []),
        "species": results.get("species", {}).get("corrected", {}).get("species", []),
        "mutations": results.get("mutations", {}).get("corrected", {}).get("mutations", []),
        "findings": results.get("findings", {}).get("corrected", {}).get("findings", []),
        "novelty": results.get("novelty", {}).get("corrected", {}),
    }

    # Save intermediate results
    with open(output_path, "w") as f:
        json.dump({"paper_id": paper_id, "steps": results}, f, indent=2)

    # Save verified result
    with open(verified_path, "w") as f:
        json.dump(verified_result, f, indent=2)

    status = "verified" if all_verified else "partial"
    print(f"    Overall: {status}", flush=True)

    return {
        "status": "complete",
        "paper_id": paper_id,
        "all_verified": all_verified,
    }


async def repair_paper(
    client: httpx.AsyncClient,
    paper_path: Path,
    base_url: str,
    model: str,
) -> dict:
    """Re-run ONLY broken steps of an existing analysis and patch in place.

    A step is broken when its result carries an "error" and no "extracted"
    payload (e.g. the empty-content JSON parse errors from reasoning models).
    Healthy steps are never re-run or clobbered.
    """
    paper_id = paper_path.stem
    analysis_path = OUTPUT_DIR / f"{paper_id}.json"
    if not analysis_path.exists():
        return {"status": "no_analysis", "paper_id": paper_id}

    analysis = json.loads(analysis_path.read_text())
    steps = analysis.get("steps", {})
    broken = [s for s in EXTRACTION_STEPS
              if isinstance(steps.get(s), dict)
              and "error" in steps[s] and "extracted" not in steps[s]]
    if not broken:
        return {"status": "clean", "paper_id": paper_id}

    full_content = paper_path.read_text(encoding="utf-8", errors="ignore")
    paper_header = full_content[:3000]
    paper_content = truncate_text(full_content)

    print(f"  Repairing {paper_id}: {', '.join(broken)}", flush=True)
    for step in broken:
        step_result = await run_step(client, step, paper_content, paper_header,
                                     base_url, model)
        steps[step] = step_result
        if "error" in step_result:
            print(f"    [{step}] STILL BROKEN: {str(step_result['error'])[:60]}", flush=True)
        else:
            print(f"    [{step}] repaired ({step_result.get('status', '?')})", flush=True)

    analysis["steps"] = steps
    analysis_path.write_text(json.dumps(analysis, indent=2))

    # refresh the flattened verified view alongside, same shape as analyze_paper
    verified_path = VERIFIED_DIR / f"{paper_id}.json"
    if verified_path.exists():
        verified = json.loads(verified_path.read_text())
        verified["steps"] = steps
        for step in broken:
            verified[step] = steps[step].get("corrected", {})
        verified["genes"] = steps.get("genes", {}).get("corrected", {}).get("genes", [])
        verified["species"] = steps.get("species", {}).get("corrected", {}).get("species", [])
        verified["mutations"] = steps.get("mutations", {}).get("corrected", {}).get("mutations", [])
        verified["findings"] = steps.get("findings", {}).get("corrected", {}).get("findings", [])
        verified["repaired_at"] = datetime.now().isoformat()
        verified_path.write_text(json.dumps(verified, indent=2))

    return {"status": "repaired", "paper_id": paper_id, "steps": broken}


async def process_all_papers(
    papers: list[Path],
    base_url: str,
    model: str,
    skip_if_verified: bool = False,
    concurrency: int = 1,
) -> list[dict]:
    """Process all papers with controlled concurrency."""
    async with httpx.AsyncClient() as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def limited_analyze(paper_path: Path) -> dict:
            async with semaphore:
                return await analyze_paper(
                    client, paper_path, base_url, model, skip_if_verified
                )

        tasks = [limited_analyze(p) for p in papers]
        return await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(
        description="LLM-powered paper analysis with multi-step extraction"
    )
    parser.add_argument(
        "--paper",
        help="Analyze a specific paper (filename)",
    )
    parser.add_argument(
        "--skip-verified",
        action="store_true",
        help="Skip papers that have already been verified",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of papers to analyze concurrently (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of papers to process",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
        help=f"LLM API base URL (default: {DEFAULT_LLM_BASE_URL})",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Repair mode: re-run only steps whose result carries an error "
             "and no extracted payload; patch the analysis in place. "
             "Without --paper, processes every analysis with a broken step.",
    )

    args = parser.parse_args()

    # Get list of papers to process
    if args.paper:
        paper_path = MD_DIR / args.paper
        if not paper_path.exists():
            print(f"Error: Paper not found: {paper_path}")
            sys.exit(1)
        papers = [paper_path]
    else:
        papers = sorted(MD_DIR.glob("*.md"))
        papers = [p for p in papers if p.stat().st_size > 500]

    if args.limit:
        papers = papers[: args.limit]

    print(f"LLM endpoint: {args.base_url}", flush=True)
    print(f"Model: {args.model}", flush=True)
    print(f"Mode: {'repair broken steps' if args.repair else 'full analysis'}", flush=True)
    print(f"Papers to analyze: {len(papers)}", flush=True)
    print(f"Steps per paper: {len(EXTRACTION_STEPS)} (extract + verify each)", flush=True)
    print(flush=True)

    if args.repair:
        async def _run():
            async with httpx.AsyncClient() as client:
                semaphore = asyncio.Semaphore(args.concurrency)

                async def limited(paper_path: Path) -> dict:
                    async with semaphore:
                        return await repair_paper(client, paper_path,
                                                  args.base_url, args.model)

                return await asyncio.gather(*[limited(p) for p in papers])

        results = asyncio.run(_run())
        repaired = [r for r in results if r["status"] == "repaired"]
        still_broken = [r for r in repaired
                        if any("error" in (json.loads((OUTPUT_DIR / f"{r['paper_id']}.json").read_text())["steps"][s])
                               and "extracted" not in json.loads((OUTPUT_DIR / f"{r['paper_id']}.json").read_text())["steps"][s]
                               for s in r["steps"])]
        print("\n" + "=" * 60)
        print("REPAIR SUMMARY")
        print("=" * 60)
        print(f"Papers examined: {len(results)}")
        print(f"  clean (nothing to do): {sum(1 for r in results if r['status'] == 'clean')}")
        print(f"  repaired: {len(repaired)}")
        print(f"  with residual broken steps: {len(still_broken)}")
        return

    # Run analysis
    results = asyncio.run(
        process_all_papers(
            papers,
            base_url=args.base_url,
            model=args.model,
            skip_if_verified=args.skip_verified,
            concurrency=args.concurrency,
        )
    )

    # Summary
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)

    complete = [r for r in results if r["status"] == "complete"]
    skipped = [r for r in results if r["status"] == "skipped"]
    fully_verified = [r for r in complete if r.get("all_verified")]

    print(f"Complete: {len(complete)}")
    print(f"  Fully verified: {len(fully_verified)}")
    print(f"  Partially verified: {len(complete) - len(fully_verified)}")
    print(f"Skipped: {len(skipped)}")


if __name__ == "__main__":
    main()
