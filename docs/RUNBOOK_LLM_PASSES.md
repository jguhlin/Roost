# LLM Pass Runbook — 2026-09-17 (PREPARED, NOT RUN)

> **RUN STATUS 2026-09-17: COMPLETE** — all LLM stages executed. Final numbers:
> intake 158 PDFs → 86 papers + 3 supplements + 66 dupes archived;
> full pass 397/397; mutation hosts 3,357 records (442 papers) + dual-host
> audit (6 corrected); vaccine: triage 552, 186 claims / 75 papers, model
> rebadged 844 verified links; clade backlog 52 cleared (29✓/23✗);
> campaign full corpus (1,290 papers); spread 987 extractions + edges;
> translations ~15.4k records filled (6 locales); suite 43/43 green.
> Incidents + fixes logged as D120–D124 in INTAKE.md.

Everything below is staged from dry-run verification on 2026-09-17.
No LLM passes have been executed. Ledgers (`vaccine_triage.jsonl`,
`vaccine_claims.jsonl`) do not exist yet — the vaccine pass is entirely unmined.

**Server**: `muse-glimmer-30b` @ `http://localhost:8005/v1` (sglang, 131k ctx) — UP.
**Capacity**: 64 concurrent queries (user-stated budget for all stages below).

## Verified inventory — what needs an LLM pass

| # | Pass | Pending | Est. LLM calls | Source of truth |
|---|------|---------|----------------|-----------------|
| 1 | Fast pass (new PDFs → md + match + summary) | **158 PDFs** (171 novel by md5; 6 byte-identical to corpus; 14 more need re-download — see `data/papers/recovery_needed.json`) + **3 supplements** | ~350 + 3 supplement-classify calls | `pdfs_to_process/` |
| 2 | Full pass (7-step extract × verify) | **302 existing papers** (294 never analyzed, 5 partial, 3 fast-only) + up to ~171 from stage 1 | ~6,600 | `data/papers/verified/` vs `docs/papers_md/` (669 verified of 971, rename-map resolved) |
| 3 | Vaccine TRIAGE | **467-paper queue** (0 triaged, 0 mined) + new papers from stage 1 | ~550–600 (1/paper) | `mine_vaccines.py --dry` |
| 4 | Vaccine PROPOSER + SKEPTIC | tier-gated by stage 3 (primaries first) | ~1,500–3,000 | `data/papers/vaccine_triage.jsonl` |
| 4.5 | Mutation host-class resolution | **271 papers / 1,930 (paper × mutation) effect records** (0 mined; grows as stage 2 lands) | ~271 proposer + ~1,930 skeptic | `mine_mutation_hosts.py --dry`; ledger `data/papers/mutation_host_claims.jsonl` |
| 5 | Campaign aggregation (summaries, gene claims, conclusions, model verdicts) | new papers from stages 1–2 | ~5/paper | `campaign.py`, resume-safe |
| 5.5 | Spread evidence extraction (flyways, species roles, mechanisms) | **475 scoped papers** (413 in ledger; full-refresh semantics — every run re-extracts all scoped) + new intake | ~550–650 | `extract_spread_data.py`; ledger `data/model/spread_evidence.jsonl` |
| 6 | Clade verification | 52 novel designations awaiting LLM | 52 | `clade_discovery.py --check` |
| 6.5 | Paper-text translations (6 locales) | **~2,600 records/loc or now** (roles 2,294, findings 211, conclusions 90) + all new-paper text after stages 2/5 | ~15,600 now, grows | `translate_papers.py --check` |
| 7 | Topic backfill | 2 no-topic + 4 sparse papers | ~6 | `assign_topics.py --check` |
| 8 | Gene enrichment agent | **0** — 291/290 done | — | `gene_agent.py` |

Post-LLM deterministic rebuilds (no LLM): `build_vaccine_model.py` (rebages
stages keyword→verified from claims), `build_wiki_pages.py`, paper/gene/species
web exports, topic translations.

## Stage 1 — Fast pass: new PDFs (~75 min, sequential)

Script has no `--workers`; runs one PDF at a time (~25 s each). Needs env
override — its default points at the retired 8001/gemma4 server:

```bash
LLM_URL=http://localhost:8005/v1/chat/completions \
LLM_MODEL=muse-glimmer-30b \
pixi run python scripts/papers/process_with_llm.py
```

- `--dry` first if you want a no-side-effect preview (classifies supplements,
  skips the PDF pipeline entirely).
- Duplicates (filename/content match) auto-archive to
  `pdfs_to_process/_already_matched/`; DOI content-matching is head-only
  (D120 fix — reference-list DOIs no longer cause false matches).
- **Supplements** (`.xlsx/.xls/.csv`, D119): previewed via fastexcel, LLM-
  classified (species_sightings / detection_surveillance / mortality_events /
  … + join keys + ingest_candidate), staged under
  `data/supplements/{manuscript-code}/` with `preview.json` + `classify.json`.
  The 3 present are WHISPers sightings 2021–2025, WAHIS mortality, WAHIS
  events — flagged for detections/WAHIS expansion, nothing auto-joins.
- **Odd pile** (D119/D120): conversion failures, non-paper docs, and
  LLM-down ID failures → `pdfs_to_process/_deferred/` + intake ledger
  (`data/papers/intake_ledger.jsonl`, review via `--ledger-report`).
  Nothing that misses the neat piles is silently dropped.
- Typed intake fires automatically: corrections → `data/papers/correction_pdfs/`,
  news clips → `docs/news_md/`, theses tagged in md.

## Stage 2 — Full pass over the corpus (resume-safe, ~3–5 h)

```bash
pixi run analyze-papers-llm-skip -- \
  --base-url http://localhost:8005/v1 --model muse-glimmer-30b --concurrency 24
```

(`llm_analyze_papers.py` also defaults to the dead 8001/gemma4 endpoint — the
flags above are mandatory.) 302 papers now + new ones once stage 1 lands them in
`docs/papers_md/`; re-invoke the same command after stage 1 and it picks up only
the remainder. `--skip-verified` never redoes the 669 verified papers.
If any analyses report broken steps: `--repair` patches them in place.

## Stage 3 — Vaccine triage (cheap, 1 call/paper — minutes at high workers)

```bash
pixi run python scripts/model/mine_vaccines.py --triage --workers 56
```

Queue is rebuilt from the keyword scan each run, so stage-1 papers enter
automatically. ~467 candidates now (top: m2e_nanovaccines 356 hits,
practical_aspects_poultry 190, dissertation 179 — theses are in scope by design).

## Stage 4 — Vaccine mining (tier-gated, most expensive)

```bash
# primaries first (papers whose own results are vaccine experiments):
pixi run python scripts/model/mine_vaccines.py --new-only --tier primary --workers 32
# then constraint-relevant non-vaccine studies:
pixi run python scripts/model/mine_vaccines.py --new-only --tier vaccine-relevant --workers 32
```

Each paper = 1 proposer (~3k tokens) + 1 skeptic call per extracted record.
Mention-only tier is skipped by design. All state in the claims ledger;
interrupt/re-run is safe (`--new-only` is the default).

## Stage 4.5 — Mutation host-class resolution (fixes the V598T mislabel)

**The bug**: `wiki_mutations.json` `host_scope` was derived from the species a
paper STUDIED, not the host in which the effect was OBSERVED — so a wild-bird
surveillance paper reporting "PB2-V598T increases virulence in mice" was badged
`avian`. Mammalian susceptibility/lethality effects are explicitly out of
scope for Roost, so they must be classified, quantified, and filtered — not
silently kept or dropped. Regex can only resolve ~875 of 1,930 records
(706 mammal-worded / 169 avian-worded); the LLM pass resolves the rest with
quote anchors + skeptic audit.

```bash
pixi run python scripts/model/mine_mutation_hosts.py --dry    # queue: 271 papers
pixi run python scripts/model/mine_mutation_hosts.py --workers 32
# re-run after stage 2 adds newly analyzed papers (queue rebuilds automatically)
```

Then `build_wiki_pages.py` (stage 8) rebadges `host_scope` to effect-level
truth (`host_scope_source: effect_claims`), emits `effect_hosts` counts +
per-paper `host_class`/`host_species` rows, and prints the mammal-only count.
The frontend (Mutations browser + full page) hides mammalian-only mutations
and mammalian-effect paper rows by default, with a toggle + counts for
transparency (D118).

## Stage 5 — Campaign aggregation for new papers (resume-safe)

```bash
pixi run python scripts/papers/campaign.py all --workers 48
```

Defaults already point at 8005/muse-glimmer. Runs summaries → gene claims →
conclusions → connections → model verdicts, skipping done work.

## Stage 5.5 — Spread model evidence (full-refresh pass)

`extract_spread_data.py` = per-paper LLM extraction (flyways, species roles,
spread mechanisms, geography, seasonality, key finding) feeding the spread
model's evidence block (`build_spread_edges.py`, deterministic, stage 8).
**Not resume-safe**: it rewrites `spread_evidence.jsonl` wholesale — every run
re-extracts every scoped paper (~475 + intake). Run it ONCE, after intake has
registered all new papers (so they're in papers.json with scope tags), not
per-wave:

```bash
pixi run python scripts/model/extract_spread_data.py --workers 32   # ~1 call/paper
```

Optional afterwards: `model_r3.py` — the infection-model refinement round
(two LLM passes per stage: proposer + skeptic over approved connection
evidence; output `data/model/r3_proposals.md` is human-review only, model
edits stay curator-approved). Worth a round after campaign lands new
gene claims:

```bash
pixi run python scripts/model/model_r3.py --workers 8
```

## Stage 6–7 — Small LLM chores

```bash
pixi run python scripts/papers/clade_discovery.py --llm              # verifies only NEW novel tokens
pixi run python scripts/papers/clade_discovery.py --verify-backlog   # D120: clears the 52 'novel' backlog (--llm alone does NOT)
pixi run python scripts/papers/assign_topics.py --llm --workers 8   # 2+4 papers
```

## Stage 6.5 — Translations (incremental, content-hash keyed)

Run AFTER stage 5 (campaign generates the findings/roles text to translate).
Defaults already point at 8005/muse-glimmer. Existing debt is large — the
runbook budget includes it; can also trickle in the background at low workers.

```bash
pixi run python scripts/papers/translate_papers.py --check            # coverage
pixi run python scripts/papers/translate_papers.py --all --workers 48
```

## Stage 8 — Deterministic merges (no LLM, after 3–5)

```bash
pixi run python scripts/model/build_vaccine_model.py   # keyword→verified rebadge
pixi run python scripts/model/build_spread_edges.py    # spread evidence block (after 5.5)
pixi run python scripts/papers/build_wiki_pages.py      # + mutation host_scope rebadge (D118)
python scripts/export_web_data.py
python scripts/papers/build_paper_index.py && python scripts/papers/build_gene_data.py && python scripts/papers/build_species_data.py
```

## Concurrency budget (64 slots total)

| While running | Its load | Remaining for |
|---|---|---|
| Stage 2 full pass @ c=24 | ~24 in-flight | triage (56) is short — run it before/after, not during |
| Stage 4 mining @ 32 | ~32–40 (skeptic bursts) | clade+topics (8) fit alongside |
| Stages 1, 5–8 | ≤ 1–48 as flagged | — |

Rule of thumb: keep the sum of in-flight requests ≤ 64; long-context proposer
calls are the KV-cache-heavy ones, hence mining capped at 32.

## Gotchas

- **14 PDFs were deleted in the D120 incident** (false content-matches via
  reference-list DOIs + one substring mis-match). Re-download pointers live in
  `data/papers/recovery_needed.json`; until they return, the batch is 158 not 172.

- **Default endpoints lie**: `process_with_llm.py` (8001/gemma4-31b via env) and
  `llm_analyze_papers.py` (8001/gemma4 via flag) predate the current server —
  always pass the overrides above. `mine_vaccines.py`, `campaign.py`,
  `assign_topics.py`, `clade_discovery.py` already default correctly.
- **News clips are out of vaccine scope by design** (§3 routing): the queue scans
  `docs/papers_md/` only; `docs/news_md/` (2 docs) is not in the vaccine scan.
  Theses/dissertations ARE included (tagged, synthesis down-weights venue).
- **`--dry` is the safe default** on `mine_vaccines.py` — everything in this
  runbook was verified with dry runs; nothing has been mined.
- After stage 2 completes for the new batch: run the "mentioned but never
  searched" gene-discovery report (INTAKE §1 discovery hook).
