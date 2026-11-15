# Roost Animation — Data & Example Discovery Report

**Purpose:** factual inventory for a 60–75 s scientific animation connecting literature-derived biological knowledge to comparative genomics across the avian phylogeny. Everything below was verified against live artifacts in this repository on 2026-11-10. No animation code was written; no application files were modified.

---

## 1. Literature & LLM processing — what is actually implemented

### 1.1 Corpus & ingestion (implemented)

| Fact | Value | Source |
|---|---|---|
| Papers registered | **1,528** | `data/papers/corpus_manifest.json`; `by_the_numbers.json → corpus.papers` |
| Papers converted to markdown | 1,366 | `docs/papers_md/` (count) |
| Verified LLM analyses | 1,860 files | `data/papers/verified/` (count) |
| Per-paper aggregate records | 1,528 | `data/papers/records/{id}.json` |
| Detections (surveillance) | 44,931 records, 106 countries, 40,780 georeferenced | `web/public/data/detections.parquet`; `stats.json` |
| Species with detections | 713 (651 birds + 62 mammals) | `stats.json` |

**Ingestion paths** (all in `scripts/papers/`): `download_pmc.py` (PMC article scraping), `download_pdfs.py` (targeted PMC/bioRxiv PDFs with magic-byte validation), `search_papers.py` + `snowball.py` (citation snowballing via EuropePMC/OpenAlex), plus manual PDF drops into `pdfs_to_process/`. Conversion is `convert_pdfs.py` (pymupdf4llm, PDF → markdown). Intake design doc: `docs/PAPER_INTAKE.md` (junk guards, manifest preflight via `corpus_preflight.py`).

### 1.2 LLM & extraction method (implemented)

- **Model:** `muse-glimmer-30b`, a **local** sglang-served OpenAI-compatible endpoint (`http://localhost:8005/v1`, 131k context). Every extraction script defaults to it (`grep DEFAULT_MODEL scripts/papers/*.py`). No external API calls for corpus analysis.
- **Method:** discrete **extract → verify double-pass** per section (`scripts/papers/llm_analyze_papers.py`, `PROMPTS` dict). Seven base steps: `metadata, study, genes, species, mutations, findings, novelty`. Each step extracts JSON, then a second LLM call verifies against the paper text and can correct/flag fields. Output schema per paper: `{paper_id, file_hash, analyzed_at, model, all_verified, steps, ...}` in `data/papers/verified/{id}.json`.
- **Downstream passes** (all implemented, resume-safe): `llm_key_findings.py`, `llm_type_claims.py` (claim typing → `claim_clusters.parquet`, 1,184 clusters), `llm_extract_mechanisms.py` (→ `pathway_edges.json`), `llm_extract_spread.py` (19 sections → `data/papers/spread_v2/`), `llm_verify_spread.py` (adjudication → `spread_verify.jsonl`), `llm_extract_phenotypes.py`.
- **Entities extracted:** genes (3 tiers: central/supporting/mention; `data/papers/gene_claims.jsonl` — gene → role + **verbatim quote** + paper_id), species, mutations, quantitative findings (finding + value + context, e.g. "325-fold titre reduction"), study metadata, 19 spread-model sections (host roles, mammal chains, introduction events, transmission parameters, susceptibility verdicts...).

### 1.3 Evidence traceability (implemented)

Every claim chains to a source: **quote → paper_id → PDF → file_hash**.
- `data/papers/gene_claims.jsonl`: `{paper_id, records: [{gene, role, tier, quote}]}`.
- `web/public/data/gene_relationships.json`: 464 mechanistic edges (237 nodes), 1,011 evidence items, each `{paper_id, quote_h, quote, year, journal, evidence_type}`; 39 edges legacy-curated, 425 review-approved mined (`connections/` review pipeline).
- Spread extraction: 3,896 items, **89% quote-grounded**, all adjudicated (86% faithful, 0.09% unsupported) — `by_the_numbers.json → spread_model`.
- Adjudicated claim clusters: `data/papers/claim_clusters.parquet`, `cluster_verdicts.parquet`.

### 1.4 Reportable headline statistics (all real, artifact-backed)

| Statistic | Value | Artifact |
|---|---|---|
| Publications processed | 1,528 papers, 22 detection sources | `by_the_numbers.json` |
| Genes in registry | 4,348 host genes (3,560 literature-studied) | `data/papers/gene_registry.jsonl` |
| Gene–paper evidence links | 8,631 total; 1,565 gene pages live | `by_the_numbers.json → gene_concentration` |
| Mechanistic network | 237 nodes / 464 edges / 1,011 quoted evidence items | `gene_relationships.json` |
| Spread-model items | 3,896 quote-grounded, 1,883 paper–edge links | `by_the_numbers.json` |
| Presence calls | 2,951,184 (1,428 panel genes × 2,048 species) | `data/genes/gene_presence_v2.parquet` |
| Orthology | 463 species, 40,494 orthogroups, 18.7M matrix rows | `by_the_numbers.json → genomics` |

### 1.5 Implemented vs planned

- **Implemented:** everything above; per-paper steward agent (`paper_steward.py`), author network (8,773 authors, 41,666 co-author edges), contradiction adjudication, region-risk model.
- **Planned/pending** (do not animate as done): i18n translation queues, mutation-censorship boundary work, phase 7/8 UI polish items in `AGENTS.md`, `FUTURE_TODO.md`. The Z-linkage sex-bias hypothesis (below) is explicitly flagged "Untested — G6" in the model.

---

## 2. Real gene network examples (strongest candidates)

### Example A — DDX58 / RIG-I: the lost sensor ⭐ *primary candidate*

- **Story:** Ducks (the reservoir) carry RIG-I, the intracellular RNA sensor; chickens, turkeys and quail — the galliform clade — **lack the gene entirely** and compensate with MDA5 (IFIH1). Roost's BLAST pipeline independently reproduces this: **39 gamebird species (all Phasianidae + Odontophoridae in the panel) are high-confidence non-detections** (searchability 0.92–1.00; chicken GCF_016699485.2 at 1.00, turkey 0.917, quail 1.000), while the basal galliforms RETAIN it (cracid + megapode = blast-found) and **all 20 Anseriformes sampled are FULL** (16 annotation + 4 blast). The loss is therefore bounded to the higher gamebird radiation — a derived, clade-wide event, not a galliform-wide one. Guineafowl (Numididae) shows only a fragment.
- **Literature:** 89 papers in registry (`gene_evidence_counts.json`). Canonical: **Barber MR, Aldridge JR Jr, Webster RG, Magor KE. 2010, PNAS 107(13):5913–5918, DOI 10.1073/pnas.1001755107** ("Association of RIG-I with innate immunity of ducks to influenza" — *citation corrected 2026-11-10 against PubMed PMID 20308570; the corpus record previously carried a wrong title/journal/DOI*). The paper shows duck RIG-I clears infection and presents evidence RIG-I "may be absent" in chickens. Corpus-verified quote (Smith et al. 2015, BMC Genomics, DOI 10.1186/s12864-015-1778-8): *"Chickens (but not ducks) lack the intracellular receptor for viral ssRNA, RIG-I (also called DDX58)"*. The 2026 TRIM25/IRF7 mBio paper quotes duck IFN biology "in ducks lacking RIG-I".
- **Network structure:** 16 edges — DDX58→MAVS (binds, 5 evid), DDX58→IFN (activates, 7), DDX58→IRF3/IRF7→NLRP3; IFIH1 (MDA5) parallels into MAVS (4 evid). Data: `web/public/data/gene_relationships.json`.
- **Classification:** gene loss = **established literature knowledge** (Barber 2010) + Roost high-confidence computational confirmation. Bonus hypothesis (label as such): model axis `sex` — *"DDX58 sits on Z in all chromosome-level bird assemblies → males (ZZ) carry two copies"* — flagged untested G6 in `avian_h5n1_model.json → axes`.
- **Files:** presence `data/genes/gene_presence_v2.parquet` (gene_symbol=DDX58); evidence `data/papers/gene_registry.jsonl`; quotes `data/papers/gene_claims.jsonl`; record `data/papers/records/barber2010.json`.

### Example B — ANP32A: the 33-aa host-range insert

- **Story:** Influenza polymerase needs host ANP32A; the avian-specific 33-aa insertion (partial exon-5 duplication) is what makes avian ANP32A permissive. Roost **measured this insert in 511 species** (`web/public/data/anp32/comparison.json`, NW-alignment against human references): 316 birds carry the full 33-aa insert (chicken insert at residues 150–182), while **all 13 palaeognaths sampled (ostrich, 2 rhea, emu, cassowary, 2 kiwi, 5 tinamous, mesite) lack it** — vs. ~95% of sampled neognaths (316/333 complete sequences) that have it. Genome-edited ANP32A knockout chickens are refractory to IAV (1,365-fold titre reduction).
- **Literature:** 47 papers. **Long et al. 2019, eLife, DOI 10.7554/eLife.45066** (species-specific ANP32 use; structured findings in `records/long_anp32_2019.json` incl. exact fold-reductions); **Nature Communications 2023, DOI 10.1038/s41467-023-41476-3** (edited chickens, viable and protected); ANP32A↔PB2/polymerase edges carry 10–13 quoted evidence items each (`gene_relationships.json`).
- **Classification:** insert function & chicken editing = **established knowledge**. The palaeognath-absence pattern = **novel Roost-computed observation** (needs validation before over-claiming — see caveats).
- **Files:** `web/public/data/anp32/comparison.json` (per-species `insert_len`, `insert_seq`, `insert_start`); page `web/src/routes/Anp32.svelte`.

### Example C — OASL: the duck's antiviral mimic

- **Story:** Mammalian OASL is enzymatically inactive; duck/goose OASL nonetheless restricts viruses — it directly **activates RIG-I** (Roost network edge OASL→DDX58, 5 quoted evidences) and inhibits cGAS (6 evid). Part of why ducks clear H5N1 non-lytically.
- **Literature:** 36 papers. **Yang et al. 2016, J Interferon Cytokine Res, DOI 10.1089/jir.2015.0167** (goose OASL cloned, upregulated on infection, inhibits NDV); *two faces of OASL* review 2024, DOI 10.1016/j.coviro.2023.101329.
- **Classification:** antiviral function = established; the "ducks: both sensors + OASL mimic → non-lytic clearance" framing is Roost's model synthesis (`avian_h5n1_model.json → axes.species_outcome`) — present as model interpretation.

### Example D — IFITM3: entry blocker with patchy bird distribution

- **Story:** IFITM3 blocks viral entry; 57 papers via aliases (chicken IFITM work: `chicken_ifitm_ndv2025` — central-tier quotes). Roost presence data shows it **full in galliforms/waterfowl but not-found in zebra finch & collared flycatcher (low confidence)** — a lead, not a claim.
- **Classification:** function = established; passerine absences = low-confidence computational lead (searchability 0.5–0.67).

### Example E — MX1: the most-studied gene (111 papers)

- **Story:** Mx1 dynamin is the classic interferon-induced restriction factor; Roost literature graph has 111 papers on it (top of `landscape.top12`). Network: IFN→STAT1→MX1→inhibits polymerase. Useful as the "interferon cascade" spine of the animation rather than a standalone surprise.

---

## 3. Comparative genomics & phylogeny

### 3.1 Phylogenetic tree (real, with branch lengths)

- **Source:** BirdTree **Ericson** consensus distribution, 9,993 species — `data/birdtree_ericson.tre` (463 MB), served as `web/public/data/phylogeny.json` (`{newick, metadata, stats, citation, source}`). Citation: **Jetz, Thomas, Joy, Hartmann & Mooers 2012, Nature 491:444–448**. Newick has real branch lengths (my Subtitle: I parsed and extracted subtrees successfully — see §4).
- `metadata` per species: taxon_id, detection_count, has_genome. 542 species with detections, 1,622 with genomes. Note label spellings follow BirdTree (e.g. kākāpō = `Strigops_habroptila` — a spelling variant that defeats exact `habroptilus` lookups).

### 3.2 Genomes & presence pipeline (implemented)

- 2,048 species searched across ~2,058 assemblies; 1,428-gene host panel (18 tier-1 innate-immunity genes incl. DDX58, IFIH1, OASL, ANP32A/B/E, IFITM1/3, MX1, MAVS, STAT1) — `data/genes/host_panel_v2.json`.
- **Method:** per (gene × genome): makeblastdb → blastn (chicken + duck transcripts) + tblastn (proteins) → evidence ladder (`scripts/genes/blast_presence.py`):
  - `E5_annotated` (GFF annotation), `E4_unannotated_found` (BLAST full), `E3_fragment`, `E2_searched_not_found`.
  - **Genome searchability** s = control genes recovered / 12; absence confidence high (s≥0.90) / medium (s≥0.75) / low. **Roost explicitly distinguishes confirmed absence from failed detection** — this discipline is itself animation-worthy.
  - Validation gates encoded in the script: DDX58×chicken must be NOT_FOUND at s≥0.9; DDX58×duck FULL; ANP32A×both FULL.
- **Orthology:** OrthoFinder across 463 species: 40,494 OGs; 799 panel genes mapped to 720 OGs (`web/public/data/gene_orthogroups.json`, `og_matrix.parquet` 18.7M rows).
- **Limitations on absence evidence:** absence calls below s=0.75 are *leads, not losses* — e.g. the apparent DDX58 loss in tinamous (searchability 0.50, confidence **low**) must not be claimed; MX1 "loss" in kiwi/emu is medium confidence. Any animation showing a "missing gene" cell should visually carry the confidence state (the data supports it: `absence_confidence` column).

### 3.3 Genes with the most compelling real cross-taxa patterns

| Gene | Pattern (verified this session) | Confidence |
|---|---|---|
| DDX58 | Lost across Galliformes (chicken/turkey/quail HIGH; guineafowl fragment); FULL in duck, goose, eagles, finch, ratites | High (galliform); established |
| ANP32A insert | 33-aa insert in 316/333 complete neognath seqs; **0/13 palaeognaths**; chicken 150–182 | Computed, novel pattern |
| MX1 | FULL chicken/duck/galliforms; LOST kiwi & emu (medium), bald eagle (low); fragment in most ratites | Mixed |
| IFITM3 | FULL in galliforms/waterfowl; not-found in zebra finch, flycatcher, tinamou, ostrich (all low confidence) | Low |
| IFIT5 | Near-universal (435/463 species in OG0008288) — the "always there" contrast gene | High |

---

## 4. Recommended species subsets (real subtrees, real branch lengths)

All three extract cleanly from `phylogeny.json` (I verified by parsing the newick and pruning to each set; branch lengths in millions-of-years-scaled units from Jetz et al.). Presence matrix joins verified per species.

### Subset 1 — "The natural experiment" (Galloanserae, 17 species) ⭐ recommended
Chicken, turkey, Japanese quail, guineafowl, pheasant, peafowl, chukar, northern bobwhite (Galliformes — RIG-I **absent**, high confidence) vs. mallard, greylag/swan goose, mute swan, Canada goose, Muscovy, common eider, pochard, goldeneye (Anseriformes — RIG-I **present**, OASL mimic). 
**Story:** same ancestor ~65–90 Mya, opposite innate-immune architectures; one clade became the world's poultry, the other the virus reservoir. Visually: the tree grows, the RIG-I node lights up on the duck branch and goes dark across the galliform radiation; MDA5 compensates (Barber 2010). 
**Data:** presence rows verified for all; PhyloPic silhouettes present for 16/17 (only chukar missing — genus-level substitutes exist on PhyloPic).

### Subset 2 — "Deep branches without the insert" (Palaeognathae + outgroups, 17 species)
Ostrich, greater + lesser rhea, emu, cassowary, 2–3 kiwi, 3 tinamous + mesite, with chicken, mallard, zebra finch, white-tailed eagle as neognath outgroups. 
**Story:** the deepest living bird lineages (ratites/tinamous) split from other birds >100 Mya — and Roost's measurements show all 12 palaeognaths sampled with complete sequences lack the ANP32A 33-aa insert the virus polymerase prefers (mesite is a neognath despite its ratite-like habits — excluded from this count). Frame as *computed observation + open question*, not established fact. Caveat: 18 scattered neognaths also lack it (starling, herring gull, flycatcher, ruddy duck...), so this is an enrichment pattern (94.6% of complete neognath sequences carry it), not a synapomorphy. 
**Data:** `anp32/comparison.json` rows for every species above verified. Imagery weaker: 10/17 exact PhyloPic matches (tinamous + lesser rhea + cassowary + mesite missing — genus-level PhyloPic fallbacks likely).

### Subset 3 — "Panzootic victims vs reservoir" (cross-order, 17 species)
Bald eagle (1,116 detections; 442 in 2022 alone when clade 2.3.4.4b arrived — verified from `detections.parquet`), white-tailed eagle (312), red-tailed hawk (765), golden eagle, osprey, herring gull (1,132), common guillemot, razorbill, brown pelican, cormorant, crane ×2, stork ×2 — vs mallard reservoir (1,842 detections, susceptibility 14.6 "highly_tolerant" vs eagle 99.9 "highly_susceptible"). 
**Story:** not monophyletic — that's the point: the panzootic kills across the whole tree, and gene content (not phylogenetic closeness) predicts who dies. Pair with the detections timeline (all-species yearly counts: 2019 = 18 → 2022 = 8,710) for the map-light-up moment. 
**Data:** `host_competence.json` (susceptibility classes + has_rigi), `detections.parquet`.

---

## 5. Animation feasibility — reusable assets

| Asset | File | Reuse |
|---|---|---|
| Mechanistic network | `web/public/data/gene_relationships.json` (237 nodes/464 edges, staged, quoted evidence) | Stage-by-stage reveal; edges carry evidence counts |
| Staged host-response model | `web/public/data/avian_h5n1_model.json` (9 stages: entry → sensing → signaling → effectors …) | Narrative scaffold for the animation's second act |
| Phylogeny | `web/public/data/phylogeny.json` (newick + metadata) | `web/src/lib/components/phylogeny/PhyloTree.svelte` has a standalone newick parser to lift; growing-tree animation straightforward |
| Presence matrix | `data/genes/gene_presence_v2.parquet` + `web/public/data/clade_matrix.json` (gene × order percentages) | Cell-fill animation with evidence-ladder states |
| ANP32 insert measurements | `web/public/data/anp32/comparison.json` (per-species insert sequences) | Sequence-strip visual (page `Anp32.svelte` precedent) |
| Orthology matrix | `web/public/data/og_matrix.parquet` (18.7M rows) + `gene_orthogroups.json` | Copy-number dots; DDX58 present in 334/463 species |
| Species silhouettes | `web/public/images/phylopic/` — **521 offline PNGs**; mapping + attribution in `phylopic.json` | 20/22 of my candidate species covered; `license` field is often `null` — verify per image (PhyloPic is CC0/CC-BY/Public Domain by node) |
| Graph layouts | `web/src/routes/ModelCyto.svelte` (cytoscape **elk** layered + fcose) | Deterministic elk layout exportable as coordinates |
| Detections timeline/map | `web/public/data/detections.parquet` (lat/lon/date/strain/species) | Map wave animation; 2022 North-America eagle spike verified |
| Susceptibility | `web/public/data/species_susceptibility.json`, `host_competence.json` | Two-axis outcome colors (permissiveness × severity) |
| Sequence alignment viewer | `web/src/lib/components/.../MsaViewer.svelte` (2D canvas) | Precedent for frame-level canvas rendering |

**Suggested export path (no implementation yet):** a small Python stage that (1) prunes the newick to the chosen subset (pattern verified this session), (2) joins presence/susceptibility/PhyloPic per species, (3) emits a single deterministic `animation_scene.json` (tree + matrices + timeline), consumed by either an fframes/SVG scene renderer or matplotlib frames. Everything downstream of that scene file is pure presentation — keeping the science data-derived (site policy: numbers on pages never hardcoded; same doctrine should apply to animation).

---

## 6. Candidate comparison & recommendation

| Example | Science strength | Visual strength | Evidence quality | Risk |
|---|---|---|---|---|
| **A. RIG-I loss in galliforms** | ★★★★★ canonical, reservoir-vs-poultry | ★★★★★ gene present/absent on tree + MDA5 pivot | High (BLAST s≥0.92 + Barber 2010 + 89 papers) | Low |
| **B. ANP32A 33-aa insert & palaeognaths** | ★★★★ (insert = established; ratite pattern novel) | ★★★★ sequence strip + insert-length histogram | High for insert; medium for ratite pattern (needs validation) | Medium — must label as computed observation |
| **C. OASL duck mimic** | ★★★ | ★★★ (edge activation RIG-I) | High (quoted) | Low |
| **D. IFITM3 passerine loss** | ★★ | ★★★ | **Low confidence absences** | High — don't claim |
| **E. Panzootic victims timeline** | ★★★★ (44,931 detections) | ★★★★★ map wave + eagle spike | High (measured surveillance) | Low |

**Recommended primary example: A (DDX58/RIG-I)** — the only story that is simultaneously (i) established literature, (ii) independently confirmed by Roost's own high-confidence genomic pipeline with an explicit evidence ladder, and (iii) naturally paired with the susceptibility outcome data (chicken susceptible/no-RIG-I vs mallard tolerant/RIG-I+, `host_competence.json`). **Weave B as the second act** (ANP32A: from literature → genome-edited chickens → Roost measuring 511 species) and close on **E** (the panzootic wave across the tree of life it threatens). This gives the full pipeline arc the brief asks for: papers → LLM extraction → gene network → comparative genomics → phylogeny → real-world stakes.

---

## 7. Missing data, uncertainties, flagged caveats

1. **Tinamou DDX58 "loss" (Tinamus, Nothoprocta) is LOW confidence** (searchability 0.50) — assembly quality, not claimable biology. Same for IFITM3 passerine absences and eagle MX1.
2. **Ratite ANP32A-insert absence** is measured from OrthoFinder MSA-derived proteins; insert_len=0 can reflect fragmented/short assemblies (75 species excluded as fragments already, but 17 neognaths also show 0). Before featuring prominently: spot-check 2–3 ratite sequences against NCBI and cite as "Roost measurement, pending wet-lab/curatorial validation."
3. **Barber 2010's structured record was thin and its metadata WRONG** (title/journal/DOI did not resolve — corrected 2026-11-10 to the PNAS paper above; the record's LLM-written "pseudogene" summary claim was unsupported and has been replaced with abstract-verified wording). Quotes for RIG-I absence live in *other* papers' verified analyses, e.g. Smith et al. 2015 (`comparative_analysis_host_responses_2024` — year in that record also corrected 2024→2015).
4. **stats.json vs by_the_numbers.json presence-call counts differ** (2,741,391 vs 2,951,184 — different filters); cite `by_the_numbers.json` (matches raw parquet rows; 21/21 checks green).
5. **PhyloPic licenses**: attribution names present; `license` field frequently `null` — per-image license check needed before publishing animation frames.
6. **Susceptibility scores are MODELED composites** (`host_competence.json` labels provenance "MODELED (composite)") — always render as model output, never as measured fact.
7. Detections bias: surveillance-heavy (APHIS/US data dominates); "detection counts" ≠ mortality counts. The 2025 spike (12,781) partly reflects expanded source ingestion — say "records", not "deaths".
