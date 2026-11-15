# Paper intake: tiers, streams, and the agentic router (design)

*Status: design (2026-10-05). Triggered by the 2026-10-05 intake batch:
junk contamination, repeats, theses, genome announcements, and policy papers
all arriving in one folder and all getting the same treatment.*

## The problem

One intake path currently serves very different documents: a data-dense PhD
thesis, a 1-page genome announcement, a mechanistic knockout study, and a
ministerial policy review. Processing them identically either wastes LLM
budget (analyzing announcements nobody will query) or under-serves the
corpus (skipping thesis chapters with real host-gene evidence).

## Two orthogonal axes

**FORMAT** (what the document physically is — `doc_type`):
article / preprint / review / book-chapter / report / thesis / announcement.
*Current state: 600 of 1,320 papers have `doc_type='?'` — needs backfill.*

**TOPIC STREAM** (what it is about — orthogonal to format):
- `host-immunity` — host genes, immune response, resistance (the core; feeds gene evidence)
- `epi-surveillance` — outbreak reports, phylodynamics, monitoring
- `pathology` — lesions, mortality, lethality, tissue tropism
- `modelling` — general-purpose mathematical/computational models
- `policy-management` — country responses, control measures, economics
- `tangential` — off the core mission but recordable: flu/orthomyxoviruses in
  non-avian species, comparative virology with shared methods, general
  immunology, zoonosis-adjacent work. **Record (T1), searchable, no gene
  analysis.** Can be upgraded later (rerun router at T2) if scope shifts.
- `true-off-topic` — not avian AND not influenza/orthomyxo in ANY species AND
  not host-gene mechanistic: personal documents (the CV incident), IP/legal/
  admin, wheat blast, pure SARS-CoV-2 variant-surveillance, image processing.
  **Delete/defer, never record.**

Streams other than `host-immunity` are **recorded and searchable but do not
feed the gene-evidence pipeline** (their species/geography still enriches
detections context). The discard/record boundary is: *would a future
researcher querying this corpus ever legitimately expect this document?*
Policy on culling — yes. A curriculum vitae — no.

## Processing tiers

| Tier | Applies to | Treatment | Cost |
|---|---|---|---|
| **T0 junk** | true-off-topic: scraping artifacts, IP/legal, personal docs (CVs), garbage titles | delete (guards already exist: filename patterns, garbage-title, JUNK_RE) | ~0 |
| **T1 record-only** | genome announcements, data notes, brief reports, most policy/epi items, **and all `tangential` stream papers** | metadata + authors (DOI/LLM) + keywords + one relevance call ("mentions H5N1/host genes? → capture the sentence") — **no full analysis** | 1–2 LLM calls |
| **T2 standard** | regular host-immunity papers | current chain: 7-step analysis → key findings → claim typing → gene evidence | ~10 LLM calls |
| **T3 deep** | mechanistic/omics studies central to the resource (KO studies, GWAS, comparative genomics) | T2 + mechanism extraction + phenotype claims + adjudication participation + verification emphasis | ~15+ LLM calls |

Tier assignment: **stream × format × signals** (claim genes present, panel
gene mentions, mutation mentions). A thesis chapter on host genomics is T3
even though its FORMAT is thesis; a policy review is T1 regardless of
length.

## Theses: section-selective path

Theses (10 currently) are dense but locally relevant:
1. TOC/heading segmentation of the markdown
2. One LLM call: classify each chapter (methods-literature / host-genomics /
   immunology / field-work / other)
3. T2/T3 analysis on selected chapters only, indexed under the thesis id
   with `chapter` sub-keys
4. Record-level: whole-thesis metadata + keywords as T1

## Should intake be agentic? Yes — a bounded router

We keep hand-adding rules (today: junk filenames, garbage titles, SA
concept, dup detection). The rule-set is now a de facto agent policy —
better to make it explicit:

- **Router agent** (one structured-output LLM call per new doc, muse-glimmer
  on :8005): `format`, `stream`, `tier`, `is_repeat` (vs recent titles),
  `reason`. Deterministic guards (T0 patterns) run FIRST and bypass the
  agent — they're cheaper and more reliable.
- Router decides: delete / defer to human queue / T1 / T2 / T3 / thesis path.
- **Not** open-ended agency: no tool use, no web access, one call, schema-
  validated, ledgered. The research agent's conventions (provenance,
  research_agent_calls.parquet) apply.
- Human queue for ambiguous cases (the current `DEFER: needs manual review`
  bucket) — surfaced in the Numbers/Checks page.

## Existing pieces this builds on

- Junk guards + garbage-title rejection (process_new_papers.py, 2026-10-05)
- Duplicate detection (title match + rename map + `registry_paper_ids_resolve` check)
- 7-step analysis chain w/ hash-skip + repair mode
- Key findings (iterative) + keywords (stated + generated)
- Claim typing → adjudication
- study_type multi-label; doc_type (needs 600 backfills)
- Numbers-page checks as the tripwire when intake misroutes

## Migration checklist (when implemented)

1. Backfill `doc_type` for the 600 unknowns (LLM one-shot from fulltext head).
2. Add `stream` + `tier` fields; default existing corpus by study_type rules.
3. Router agent + guards-first pipeline in process_new_papers.py.
4. Thesis chapter segmentation path.
5. Numbers page: per-stream/per-tier corpus counts + intake-queue check.
