# Plan: Wiki-Style Knowledge Pages (Phase 7)

**Goal:** Turn the verified LLM extraction corpus (142 papers × 7 steps) into
canonical, cross-linked "encyclopedia" pages for genes, species, mutations, and
eventually locations — the knowledge layer of the "Wikipedia for bird flu".

---

## 1. What the corpus contains

Each paper in `data/papers/llm_analyses/{paper_id}.json` has 7 verified steps:

| Step | Fields | Volume (142 papers) |
|------|--------|---------------------|
| `metadata` | title, authors, journal, year, doi, type | 142 |
| `study` | objectives, study_type, conclusions | 141 verified |
| `genes` | name, role, importance (central/mentioned) | 427 raw names, 37 central in ≥2 papers |
| `species` | name, finding, infection_status | 684 raw names, 1,052 evidence rows |
| `mutations` | name, effect | 427 raw, ~400 after normalization |
| `findings` | finding, value, context (quantified!) | 1,729 |
| `novelty` | novel_claims, limitations, contradictions | 648 / 135 |

Key signal (after aggregation):

- **Genes:** PB2 (46 papers), NP (~56 combined), HA (~76), NA (~69), PA (~49),
  PB1 (~45), ANP32A/B/E (7–8 each, mostly *central*), RIG-I (7)
- **Species:** Chicken (~27+), Human (~32), Duck (~14), Turkey, dairy cattle,
  gannet, terns, peregrine falcon, kelp gull …
- **Mutations:** PB2-E627K (31 papers), PB2-D701N (22), PB2-M631L (15),
  PB2-Q591K (8), HA-T156A (6), NA-H275Y (5) …
- **Infection statuses:** confirmed 847 · susceptible 81 · sampled 39 ·
  resistant 28 · unknown 57

## 2. The canonicalization problem

LLM outputs use free-form names. Before aggregation we must normalize:

| Entity | Raw examples | Canonical form |
|--------|--------------|----------------|
| Gene | `NP (NUCLEOPROTEIN)`, `NP`, `Nucleoprotein` | `NP` |
| Gene | `RIG-I`, `DDX58`, `RIG-1` | `DDX58` (RIG-I alias) |
| Species | `chicken`, `Chicken`, `Chicken (ANP32A-GE)` | `Gallus gallus` + qualifier |
| Species | `Human`, `Humans`, `human` | `Homo sapiens` |
| Mutation | `PB2 M631L`, `PB2-M631L` | `PB2-M631L` |

Strategies:

1. **Alias table** for the ~50 genes in the curated panel (`build_gene_data.py`
   already defines aliases). Viral segments/proteins get a fixed map
   (HA, NA, NP, PA, PB1, PB2, M1, M2, NS1, NS2/NEP, PB1-F2).
2. **Species:** reuse `SPECIES_NAME_MAP` in `build_species_data.py` plus
   case-insensitive lookup, binomial extraction via regex
   (`Genus species` in parentheses), and a generic→specific split
   ("Wild birds", "Poultry" stay as *categories*, not species pages).
3. **Mutations:** regex `^(GENE|PROTEIN)[ -]([A-Z][0-9]+[A-Z*])$` →
   `GENE-POSREF→ALT` canonical; keep original string as alias.

## 3. Architecture

```
data/papers/llm_analyses/*.json        (verified extractions; source of truth)
        │
        ▼  scripts/papers/build_wiki_pages.py
web/public/data/wiki_genes.json        { SYMBOL: { summary, roles[], findings[],
        │                               mutations[], papers[] } }
web/public/data/wiki_mutations.json    { PB2-E627K: { protein, effect, papers[],
        │                               species[] } }
web/public/data/wiki_index.json        entity index for global search
        ▼
Svelte routes (hash-based)
  #/genes          gene panel + per-gene "From the literature" section
  #/mutations      NEW route: mutation browser + detail panel
  #/species/{id}   species modal gains a "Research" tab (next step)
```

Design rules (Wikipedia-like):

- **Every claim carries its citation.** Roles, findings, and effects are stored
  per-paper with paper_id; the UI links each bullet to `#/papers`.
- **Neutral synthesized summary** at the top (hand-written panel descriptions
  where available, else generated from the highest-mention paper roles).
- **Evidence tiers:** `primary` (gene is the paper's subject) vs `mentioned`;
  `central` importance outranks `mentioned`.
- **Contradictions surfaced, not hidden** — the novelty step explicitly tracks
  them (135 total); candidate for a "Conflicting evidence" section later.

## 3b. Host-scope classification

Roost is an *avian* host genomics resource; mammalian evidence matters but is
secondary. Every mutation/gene entity now carries a `host_scope` derived from
its supporting papers' species lists:

| Scope | Meaning | Count (mutations) |
|-------|---------|-------------------|
| `avian` | all host evidence is birds | 58 |
| `both` | avian + mammalian evidence | 169 |
| `mammalian` | mammals only | 47 |
| `viral` | no host species (in vitro / pure viral) | 1 |

- Avian/mammal classification per species name via curated maps + bird/mammal
  word lists (`guess_avian`); 111 avian / 38 mammalian / 28 unclassified species
- UI: scope tags everywhere — `avian` and `mammalian` render as separate tags
  (never a combined "both"), avian-first default sort (toggle for most-evidence),
  host-scope filter, and split "🪶 Studied in birds" / "🐁 Also studied in mammals"
  sections on full pages

## 4. Implementation steps

1. ✅ `scripts/papers/build_wiki_pages.py` — canonicalizers + aggregators →
   `wiki_genes.json` (75 genes), `wiki_mutations.json` (275 mutations),
   `wiki_species.json` (177 species), `wiki_index.json`
2. ✅ `#/mutations` route: browser with slim card + full-page mutation view
   (`#/mutations/PB2-E627K`) with host-context split and scope badges
3. ✅ Genes page: slim quick-summary card in the panel + full-page gene view
   (`#/genes/ANP32A`) with literature synthesis, 3D viewer, and papers
4. ✅ Species detail "Research" tab (conclusions, key numbers, study types,
   evidence rows, notable claims)
5. ✅ Mutation pages: species context + text-matched key findings
6. ✅ `wiki_index.json` folded into the global SearchBar (⌘K) — species,
   genes, and mutations in one search, with type badges and routing
7. ✅ Deep links: `#/genes/ANP32A`, `#/mutations/PB2-E627K` auto-select
8. 🔲 Location/outbreak synthesis (join paper geography with detections)
9. 🔲 Paper deep links from citations (currently #/papers generic)
10. 🔲 Quarterly regeneration hook in pixi (`analyze-papers-llm` → build steps)

## 5. Data volumes

| File | Entities | Size |
|------|----------|------|
| `wiki_genes.json` | 57 canonical genes (18 curated + 39 corpus-discovered; roles, key numbers, conclusions, mutations, species) | ~290 KB |
| `wiki_mutations.json` | 275 mutations (effects, species, key numbers) | ~300 KB |
| `wiki_species.json` | 177 species (conclusions, key numbers, study types, evidence, claims) | ~950 KB |
| `wiki_index.json` | compact search index | ~43 KB |

All lazily loaded (species file only on Research tab; index on first search).
The Gene Panel page merges the curated panel with corpus-discovered genes at
runtime (curated records first, `lit`-badged corpus entries after); noise
(housekeeping genes, qPCR controls) and naming chaos (Greek letters, matrix
segment variants) are canonicalized in the builder.

## 6. Open questions

- Commit policy for `docs/papers_pdfs/` (144 PDFs, licensing + repo size).
- Should mutation pages link out to FluSurv/Nextstrain when those land?
- Human/cattle/mammal species: separate "mammalian hosts" section vs. same
  namespace (data model already supports `avian: false`).
