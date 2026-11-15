# Research Agent — Development Guide

Internal reference for continuing development on the autonomous research agent.
Last updated: 2026-10-04 (D163). See DATA_MANIFEST.md §10f for the data-facing
documentation and Methods page section 10 for the researcher-facing description.

> **Figure system:** the companion handoff [FIGURE_AGENT.md](FIGURE_AGENT.md)
> covers the local-first scientific-figure agent built on the same pattern —
> Pi-orchestrated SVG / draw.io / Python figures, mirrored open asset
> libraries (Bioicons, Reactome, PhyloPic, NIH BioArt, SciDraw, Health Icons)
> with a SQLite FTS index, per-figure manifests + attribution, and FFrames
> as the motion analogue. Skills live in `.pi/skills/`, mirrors in `assets/`,
> scripts in `scripts/figures/`.

## Quick Start

```bash
# score all open questions (required before --autonomous)
pixi run python scripts/papers/score_open_questions.py

# run a briefing on any question
pixi run python scripts/papers/research_agent.py \
  --question "Why do ducks survive H5N1?" --no-external

# run a skill (pre-configured investigation pattern)
pixi run python scripts/papers/research_agent.py \
  --skill gene_deep_dive --params "gene=ANP32A" --no-external

# fully autonomous (agent picks top-scored questions)
pixi run python scripts/papers/research_agent.py \
  --autonomous 5 --spawn-subbriefs --discover-papers
```

Environment: `LLM_MAX_TOKENS=8192` required (default 4096 truncates synthesis JSON).
Server: muse-glimmer-30b at `http://127.0.0.1:8005/v1` (sglang, 131k context).
Searxng: `http://localhost:8888/search?format=json` (rate-limited, agent degrades gracefully).

## File Map

| File | Purpose |
|------|---------|
| `scripts/papers/research_agent.py` | The agent itself (tool registry, skills, loop, synthesis) |
| `scripts/papers/score_open_questions.py` | Batched LLM scoring of open questions |
| `scripts/papers/build_aggregation.py` | Builds gene_evidence/, pathway_edges.json, landscape |
| `scripts/papers/enrich_pipeline.py` | Recurring pipeline (runs all LLM passes on pending papers) |
| `scripts/papers/process_new_papers.py` | PDF intake → registration + deterministic extraction |
| `scripts/papers/export_contradictions.py` | Adjudication output → contradictions.json |
| `scripts/papers/resolve_paper_ids.py` | Fuzzy paper-ID resolver (used by adjudicator + export) |
| `scripts/papers/validate_paper_refs.py` | Site-wide paper-ID validation gate |
| `scripts/papers/clean_paper_refs.py` | One-pass cleaner (strips suffixes, fuzzy-resolves) |
| `scripts/papers/llm_gene_aliases.py` | Gene alias resolution via LLM |
| `scripts/papers/normalize_species_names.py` | Species alias map + normalization |

## Data Files

| File | Content |
|------|---------|
| `web/public/data/research_briefings/{slug}.json` | Individual briefing (see schema below) |
| `web/public/data/research_briefings/index.json` | Auto-generated index for the landscape page |
| `web/public/data/papers/contradictions.json` | Adjudicated contradictions (input to agent) |
| `web/public/data/pathway_edges.json` | Verified mechanism edges (get_model tool reads this) |
| `web/public/data/gene_evidence/{GENE}.json` | Per-gene literature card (get_gene_evidence tool) |
| `data/papers/scored_questions.parquet` | All open questions ranked by combined score |
| `data/papers/research_agent_calls.parquet` | Persistent tool-call history across all briefings |
| `data/papers/paper_key_findings.parquet` | 9,331 findings (search_corpus tool reads this) |
| `data/papers/paper_mechanisms.parquet` | 2,999 verified mechanisms |
| `data/papers/paper_quantitative.parquet` | 7,691 quantitative results |
| `data/papers/paper_species_traits.parquet` | 778 species phenotype rows (normalized) |
| `data/papers/paper_limitations.parquet` | 2,650 author-stated limitations |
| `data/papers/paper_disagreements.parquet` | 389 explicit disagreements |
| `data/papers/typed_claims.parquet` | 9,983 typed claims (entities + stance) |
| `data/papers/gene_alias_map.json` | 1,244 gene aliases (verbose → canonical) |
| `data/papers/species_alias_map.json` | 16,208 species aliases |
| `data/papers/discovered_papers.jsonl` | Papers found via web search (for intake) |

## Briefing JSON Schema

```json
{
  "slug": "url-safe-slug",
  "question": "the original question",
  "title": "concise title",
  "summary": "3-4 sentence executive summary",
  "sections": [{"heading": "...", "body": "5-8 sentences with [paper_id] citations"}],
  "hypotheses": [{
    "hypothesis": "...", "prediction": "...",
    "evidence_for": ["[pid] found X"],
    "evidence_against": ["[pid] found Y"],
    "test": "what study would settle this",
    "confidence": "high|medium|low"
  }],
  "research_plan": [{
    "study": "...", "method": "...", "model_system": "...",
    "feasibility": "high|medium|low", "priority": 1
  }],
  "key_contradictions": [{"what": "...", "papers": ["id1", "id2"], "status": "..."}],
  "unresolved": ["question 1"],
  "data_gaps": ["what data would settle this"],
  "meta_questions": [{
    "question": "...", "scope": "this_report|own_briefing", "reasoning": "..."
  }],
  "refinement_rounds": 2,
  "self_assessment": {
    "gaps_identified": [...], "questions_raised": [...],
    "confidence": "medium", "reasoning": "..."
  },
  "agent_trace": {
    "tool_calls": [{"briefing": "...", "iteration": "0-1", "tool": "...",
                    "args": "...", "n_results": 10, "duration_ms": 50}],
    "n_iterations": 12,
    "pipeline": "v4 ..."
  },
  "_gap_report": false,
  "_parent": "parent-slug (for sub-briefings)",
  "generated": "ISO timestamp"
}
```

## Tool Registry

Add new tools by registering in `build_registry()`:

```python
registry.register(
    "my_tool",                    # name the LLM will call
    "What it does (shown to LLM)",
    {"arg1": "str", "arg2": "list[str]"},  # arg schema (shown to LLM)
    my_handler_function            # deterministic, no LLM inside
)
```

Add aliases for commonly-invented names:

```python
registry.register_alias("llm_invented_name", "real_tool_name",
                         hint="explanation shown to the agent")
```

Unknown tools return the list of available tools → agent self-corrects.

## Skills

Add by appending to `SKILLS` dict:

```python
"my_skill": {
    "description": "What this skill investigates",
    "params": {"param_name": "description"},
    "system_hint": "Investigation protocol: step 1..., step 2..., ..."
}
```

Usage: `--skill my_skill --params "param=value"`

## Agent Loop Phases

```
PHASE 1: INVESTIGATE
  Agent picks tools, chains into related papers, auto-compacts every 4 iterations
  Exits when agent calls synthesize() or hits MAX_ITERATIONS (12)

PHASE 2: SYNTHESIZE (per refinement round)
  Two separate LLM calls (briefing body, then hypotheses+plan)
  If synthesis fails → gap report (still assessed)

PHASE 3: SELF-ASSESS
  Agent critiques own draft: what's missing, what questions arose
  Classifies meta-questions: this_report (↳) vs own_briefing (→)

PHASE 4: DECIDE
  "done" → final output
  "refine" → targeted tool calls for gaps, then back to PHASE 2
  Max 3 refinement rounds
```

## Key Design Decisions

- **LLM is the orchestrator** — it decides which tool to invoke, not a fixed pipeline
- **Tools are deterministic** — no LLM inside any tool handler
- **Gap reports are findings, not failures** — "insufficient evidence" is reported
- **Meta-questions are classified** — the agent knows what belongs in this report
  vs what deserves its own investigation
- **Paper citations as [paper_id]** — rendered as clickable links on the page
- **Every tool call recorded** — persistent parquet, queryable across briefings
- **Clean prose mandate** — synthesis prompt forbids tool names, metadata, labels
- **Auto-compact** — evidence summarised every 4 iterations to keep context bounded

## Known Issues & Gotchas

- `LLM_MAX_TOKENS=8192` required — default 4096 truncates synthesis JSON
- Searxng rate-limits under heavy LLM traffic — agent degrades gracefully
- `_find_related` reads all gene_evidence files on first call (cached after)
- Sub-briefing spawning capped at 3 per run (recursion guard)
- The agent sometimes invents tool names — aliases catch known patterns,
  unknown tools return the available list so the agent self-corrects
- Gap reports from thin-corpus questions are CORRECT behaviour, not a bug

## Extending

### Adding a new tool
1. Write a handler function (deterministic, returns list of dicts)
2. Register it in `build_registry()`
3. The LLM discovers it automatically from the tool description

### Adding a new skill
1. Add to `SKILLS` dict with description, params, and system_hint protocol
2. The system_hint should describe the investigation methodology step by step

### Adding a new data source for the agent to query
1. Load it in `ToolRegistry._load_data()` or as a module-level lazy singleton
2. Write a handler that queries it
3. Register as a tool

### Wiring paper discovery to auto-intake
Currently `--discover-papers` logs to `discovered_papers.jsonl`. To auto-intake:
1. Read discovered_papers.jsonl
2. For each entry with a PDF URL, download to pdfs_to_process/
3. Run process_new_papers.py → enrich_pipeline.py

## Page Routes

- `#/research/{slug}` — full briefing page (Research.svelte)
- `#/landscape` — briefing index + gaps + contradictions + open questions
- `#/contradictions` — adjudicated contradictions with reason badges
- `#/papers?added={date}` — newly added papers batch view

## Build & Deploy

```bash
cd web && npx vite build  # rebuilds with latest briefings
# server on :5177
cd web/dist && python3 -m http.server 5177 --bind 0.0.0.0
```
