# Gene Panel

This document specifies the immune gene panel for comparative analysis, organized by function, evidence tier, and annotation priority — and the formal method by which literature-discovered genes enter the panel (§14–§16).

---

## 0. Panel Definition (2026-09-06)

"The panel" is the gene universe served on `#/genes`, built by a canonical-ID
merge of three sources (mirrored in `Genes.svelte`). **wiki_genes.json is
the canonical record** (D98): literature scope == wiki host membership,
Everywhere (§12.8).

| Source | File | Count | Role |
|--------|------|-------|------|
| Curated | `web/public/data/genes.json` | 18 | Hand-curated causal-evidence genes (§2–§8) |
| Wiki corpus | `web/public/data/wiki_genes.json` | 568 (555 host / 13 viral) | Genes with ≥2 corpus papers — parsed genes steps + discovery-log safety net (D97) |
| Presence catalogue | `web/public/data/gene_presence.json` | 592 (159 lit / 433 ann) | Panel genes searched across genomes; scope derived from wiki |

Scope split (the literature-first doctrine):

- **555 literature-scope host genes** = wiki host canonical IDs (curated ⊆
  wiki; catalogue-literature ⊆ wiki). These are the default view.
- **433 annotation-scope genes** — presence-catalogue genes without wiki
  entries. Hidden behind the `+ annotation-only` toggle; never published as
  literature findings.
- **13 viral genes** — separate kind (`Viral Protein`/`Viral Segment`).

Wiki entries are canonical-ID deduplicated ("IL-15"/"IL15" merge to one
entry); a literature-scope gene without a wiki entry is a hard build error
(`test_wiki_consistency.py`).

Panel tiers (`data/genes/host_panel_v2.json`): tier 1 = 18 curated,
tier 2 = 32 wiki-corpus additions, tier 3 = 546 UniProt backbone.

## 1. Panel Design Principles

### 1.1 Goals

1. **Comprehensive but tractable** — cover major resistance/tolerance mechanisms without exhaustively listing every immune gene
2. **Evidence-tiered** — prioritize genes with strongest causal or comparative evidence
3. **Annotation-aware** — include chicken IDs for functional anchor transfer
4. **Feature-rich** — capture presence, copy number, domain architecture, key variants

### 1.2 Sources

- Avian Immunome Database (Avimm) — ~1,170 chicken immune genes
- Literature-curated candidates from challenge experiments
- Known host-dependency factors
- Genes with proven perturbation effects

### 1.3 What to Capture Per Gene

| Feature | Description |
|---------|-------------|
| Presence/absence | Is gene found in genome? |
| Copy number | How many paralogues? |
| Intact/pseudogene | Full-length or disrupted? |
| Protein length | Amino acid count |
| Domain architecture | Pfam domains present |
| Key variant states | Specific residues with known function |
| Chicken reference ID | Ensembl/RefSeq for anchor |
| Orthogroup ID | Cross-species grouping |

---

## 2. Tier 1: Strongest Evidence

Genes with causal perturbation evidence or direct in-vivo H5N1 results.

### 2.1 Host Dependency Factors

These are not immune genes — they are host factors required for viral replication. Disrupting them creates resistance.

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **ANP32A** | Acidic nuclear phosphoprotein 32A | Gene-edited chickens: 9/10 uninfected at standard dose | 33-aa insertion distinguishes avian from mammalian |
| **ANP32B** | Acidic nuclear phosphoprotein 32B | Cellular studies; escape route when ANP32A blocked | Chicken ANP32B differs from mammalian |
| **ANP32E** | Acidic nuclear phosphoprotein 32E | Triple knockout blocks viral growth in cells | No edited birds yet |

**Key variant:** ANP32A 33-amino-acid insertion (avian-specific). Three chicken isoforms differ in SUMO-interaction motif.

### 2.2 Direct In-Vivo Evidence (H5N1)

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **IFIT5** | Interferon-induced protein with tetratricopeptide repeats 5 | Transgenic chicks: reduced H5N1 disease/pathology | Direct antiviral effector |
| **IFITM1** | Interferon-induced transmembrane protein 1 | Transgenic chicks: complete protection at low dose | Blocks viral entry/fusion |
| **IFITM3** | Interferon-induced transmembrane protein 3 | Transgenic chicks: reduced shedding and pathology | Same mechanism as IFITM1 |

---

## 3. Tier 2: Strong Comparative Evidence

Genes repeatedly implicated across species or experiments.

### 3.1 OAS/OASL–RNase L Pathway

Viral RNA sensing → 2'-5' oligoadenylate synthesis → RNase L activation → RNA degradation.

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **OAS1** | 2'-5'-oligoadenylate synthetase 1 | 11-species comparison: early induction in resistant birds | May be multi-copy; annotation varies |
| **OASL** | 2'-5'-oligoadenylate synthetase-like | Same as above | Lacks RNase L activation in some forms |
| **RNASEL** | Ribonuclease L | Downstream effector | Cleaves viral and host RNA |

**Annotation caveat:** OAS family annotation is inconsistent across bird genomes. Analyze entire orthogroup.

### 3.2 MDA5–LGP2–MAVS Pathway

Cytoplasmic viral RNA sensing. Critical in galliform birds lacking RIG-I.

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **IFIH1** | Interferon-induced helicase C domain-containing protein 1 (MDA5) | Chicken cell knockdown: impaired IFN response | Primary sensor in chickens |
| **DHX58** | DExH-box helicase 58 (LGP2) | Modulates MDA5 signaling | Regulatory role |
| **MAVS** | Mitochondrial antiviral signaling protein | Knockdown: blocks interferon induction | Signal adaptor |
| **TBK1** | TANK-binding kinase 1 | Phosphorylates IRF3/IRF7 | Downstream kinase |
| **IRF7** | Interferon regulatory factor 7 | Master regulator of type I IFN | Late amplification |

### 3.3 Type I Interferon Response

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **IFNAR1** | Interferon alpha/beta receptor 1 | Knockout chickens: severely compromised antiviral state | Essential receptor |
| **IFNAR2** | Interferon alpha/beta receptor 2 | Co-receptor | — |
| **JAK1** | Janus kinase 1 | Signal transduction | — |
| **TYK2** | Tyrosine kinase 2 | Signal transduction | — |
| **STAT1** | Signal transducer and activator of transcription 1 | Key transcription factor | — |
| **STAT2** | Signal transducer and activator of transcription 2 | Partners with STAT1 | — |
| **IRF9** | Interferon regulatory factor 9 | Forms ISGF3 complex | — |

### 3.4 Additional Interferon-Stimulated Genes

| Gene | Full Name | Category | Notes |
|------|-----------|----------|-------|
| **IFITM2** | Interferon-induced transmembrane protein 2 | Entry restriction | Same family as IFITM1/3 |
| **EIF2AK2** | Eukaryotic translation initiation factor 2-alpha kinase 2 (PKR) | Translational shutoff | — |
| **RSAD2** | Radical S-adenosyl methionine domain-containing 2 (viperin) | Lipid metabolism disruption | Broad antiviral |
| **ISG15** | Interferon-stimulated gene 15 | ISGylation | Conjugated to viral/host proteins |
| **ZC3HAV1** | Zinc finger CCCH-type antiviral protein 1 (ZAP) | Viral RNA targeting | — |
| **DDX60** | DExD/H-box helicase 60 | RNA binding | — |

---

## 4. Tier 3: RIG-I Pathway (Context-Dependent)

These genes are biologically important but not straightforward resistance targets.

| Gene | Full Name | Evidence | Caveat |
|------|-----------|----------|--------|
| **DDX58** | DExD/H-box helicase 58 (RIG-I) | Present in ducks, absent in chickens | Transgenic RIG-I in chickens worsened outcomes |
| **RNF135** | Ring finger protein 135 (RIPLET) | Ubiquitinates RIG-I | Lost with RIG-I in galliformes |
| **TRIM25** | Tripartite motif-containing 25 | Alternative RIG-I ubiquitination | — |

**Critical warning:** "Add RIG-I to chickens" failed experimentally. Increased inflammation, pathology, and mortality with virulent viruses. Context and regulatory network matter.

---

## 5. Tolerance and Immunopathology Genes

Genes that may explain survival despite similar viral burden — or cause pathological inflammation.

### 5.1 Best Tolerance Candidate

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **PLAU** | Plasminogen activator, urokinase | Downregulated in resistant chickens (H5N8 2.3.4.4b) | Fibrinolysis, vascular, inflammation |
| **VCAM1** | Vascular cell adhesion molecule 1 | Same study | Endothelial activation |
| **TNFRSF1A** | TNF receptor superfamily member 1A | Same study | Inflammatory signaling |
| **PGF** | Placental growth factor | Same study | Vascular permeability |

### 5.2 Inflammatory Regulators

Genes where *lower* or *controlled* expression may be protective.

| Gene | Full Name | Category | Notes |
|------|-----------|----------|-------|
| **NFKB1** | Nuclear factor kappa B subunit 1 | Transcription factor | Master inflammatory regulator |
| **RELA** | RELA proto-oncogene, NF-kB subunit | Transcription factor | NF-kB p65 subunit |
| **IL1B** | Interleukin 1 beta | Cytokine | Pro-inflammatory |
| **IL6** | Interleukin 6 | Cytokine | Pro-inflammatory |
| **IFNG** | Interferon gamma | Cytokine | Immune activation |

### 5.3 Cell Death Pathways (PANoptosis)

| Gene | Full Name | Category | Notes |
|------|-----------|----------|-------|
| **CASP1** | Caspase 1 | Inflammasome effector | Processes IL1B |
| **CASP8** | Caspase 8 | Apoptosis initiator | — |
| **RIPK1** | Receptor-interacting serine/threonine kinase 1 | Necroptosis | — |
| **NLRP3** | NLR family pyrin domain-containing 3 | Inflammasome sensor | — |
| **ZBP1** | Z-DNA binding protein 1 | PANoptosis initiator | — |

### 5.4 Feedback Regulators

| Gene | Full Name | Category | Notes |
|------|-----------|----------|-------|
| **SOCS1** | Suppressor of cytokine signaling 1 | Negative regulator | Dampens JAK-STAT |
| **SOCS3** | Suppressor of cytokine signaling 3 | Negative regulator | — |
| **USP18** | Ubiquitin-specific peptidase 18 | Negative regulator | Blocks IFNAR signaling |

---

## 6. Endosomal Sensors

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **TLR3** | Toll-like receptor 3 | dsRNA sensing | — |
| **TLR7** | Toll-like receptor 7 | ssRNA sensing | Notably not expressed in black swan |
| **MYD88** | MYD88 innate immune signal transduction adaptor | Signal adaptor | — |

---

## 7. Adaptive Immunity

Relevant for acquired immunity and MHC-based presentation, though less transferable across species.

### 7.1 MHC Class I

| Gene | Full Name | Notes |
|------|-----------|-------|
| **BF2** | MHC class I alpha chain | B21 haplotype associated with relative protection |
| **B2M** | Beta-2 microglobulin | Light chain |
| **TAP1** | Transporter, ATP-binding cassette, major histocompatibility complex 1 | Peptide loading |
| **TAP2** | Transporter, ATP-binding cassette, major histocompatibility complex 2 | Peptide loading |

### 7.2 MHC Class II

| Gene | Full Name | Notes |
|------|-----------|-------|
| **BLB1** | MHC class II beta chain | — |
| **BLB2** | MHC class II beta chain | — |
| **DMB2** | MHC class II DM beta | Peptide editing |

### 7.3 T Cell Markers

| Gene | Full Name | Notes |
|------|-----------|-------|
| **CD4** | CD4 molecule | Helper T cell |
| **CD8A** | CD8 alpha chain | Cytotoxic T cell |
| **CD8B** | CD8 beta chain | — |
| **CD40** | CD40 molecule | Costimulation |
| **CD80** | CD80 molecule | Costimulation |
| **CD86** | CD86 molecule | Costimulation |

---

## 8. Entry and Receptor Biology

| Gene | Full Name | Evidence | Notes |
|------|-----------|----------|-------|
| **B4GALNT2** | Beta-1,4-N-acetyl-galactosaminyltransferase 2 | Engineering: altered glycans reduced infection | No natural protective allele known |
| **ST3GAL** family | Sialyltransferases | Affect α2,3-linked sialic acids | Avian receptor preference |
| **ST6GAL** family | Sialyltransferases | Affect α2,6-linked sialic acids | Mammalian receptor preference |

---

## 9. Genes to Track Cautiously

Include in panel but do not treat as validated resistance markers.

### 9.1 MX1

| Gene | Issue |
|------|-------|
| **MX1** (Myxovirus resistance 1) | S631N allele inconsistent across studies. No clear protective effect in vivo. |

### 9.2 GWAS Candidates (Unvalidated)

Identified in outbreak-survivor GWAS but not yet replicated:

- CORO2B
- RNFT1
- PALM2
- PRCC
- ZNF639
- BCL6
- MAPK1
- DPP10
- NLGN4
- NRXN3

Track for replication; do not use as primary markers.

---

## 10. Panel Summary

### 10.1 By Category

| Category | Gene Count | Key Examples |
|----------|------------|--------------|
| Host dependency | 3 | ANP32A, ANP32B, ANP32E |
| Viral sensing | 10 | IFIH1, DHX58, MAVS, TLR7, DDX58 |
| Interferon signaling | 9 | IFNAR1, JAK1, STAT1, STAT2, IRF7/9 |
| Antiviral effectors | 12 | IFIT5, IFITM1/2/3, OAS, RSAD2, ISG15 |
| Tolerance/pathology | 15 | PLAU, NFKB1, IL1B, CASP1, SOCS1 |
| Adaptive immunity | 12 | BF2, B2M, TAP1/2, CD4/8 |
| Entry/receptor | 5+ | B4GALNT2, ST3GAL family |

**Total core panel:** ~65-70 genes/gene families

### 10.2 By Tier

| Tier | Description | Genes |
|------|-------------|-------|
| 1 | Causal perturbation or direct H5N1 in-vivo | ANP32A/B/E, IFIT5, IFITM1/3 |
| 2 | Strong comparative evidence | OAS/OASL, MDA5-MAVS pathway, IFNAR-STAT pathway |
| 3 | Important but context-dependent | RIG-I/RNF135, MHC |
| 4 | Expression-only or unvalidated | Many ISGs, GWAS candidates |

---

## 11. Annotation Priority

### 11.1 Phase 1 (Highest Priority)

Call presence/absence/copy number for:
- ANP32A/B/E
- DDX58 (RIG-I) + RNF135
- IFITM cluster (IFITM1/2/3/5/10)
- OAS/OASL family
- IFIH1 (MDA5)
- IFNAR1

These are the highest-signal genes where presence/absence alone is informative.

### 11.2 Phase 2

Full feature extraction (domains, key residues) for:
- ANP32A isoform (33-aa insertion variant)
- MHC-B gene count
- Interferon cluster structure
- Defensin/cathelicidin copy number

### 11.3 Phase 3

Expression context from reprocessed RNA-seq:
- Baseline levels
- Induction kinetics
- Cell type specificity
- Viral load conditioning

---

## 12. Panel Discovery & Intake Method (Formal)

How a gene moves from "mentioned in a paper" to "on the panel with genome
presence calls". The method is deterministic and collision-first: nothing is
searched twice, and nothing enters the panel without corpus evidence.

### 12.1 Sources of Discovery

1. **Corpus LLM extraction** (`data/papers/gene_discovery.jsonl`, ~2,600
   records / ~1,260 raw symbols): every full-text paper's genes step records
   `{paper_id, gene, role, importance}`. `importance=central` means the gene
   is a primary subject of the paper.
2. **Connection mining** (`scripts/papers/connections.py`): relationship
   candidates introduce counterpart genes.
3. **Curated additions** (§2–§8): manual, each with causal evidence.

### 12.2 Canonicalization

All symbols pass `normalize_gene_name` (`build_wiki_pages.py`):
strip parentheticals (`NP (NUCLEOPROTEIN)` → `NP`), Greek→Latin
(`IFN-Β` → `IFN-B`), alias map (`MDA5`→`IFIH1`, `PKR`→`EIF2AK2`,
`RIG-I`→`DDX58`, `viperin`→`RSAD2`, …). Collision matching uses the
canonical ID: uppercase, `-`/`_`/space stripped — the same key the web merge
uses, so a collision here is a collision on the page.

### 12.3 Noise Filter

Before any collision check, drop: rRNA/clones/vector markers (`12S RRNA`,
`16S RDNA`, `LOC*`, `AC*`, `2A`, `40K`), antibodies (IgG/IgM…), housekeeping
controls (GAPDH, ACTB, TUBB), numeric-only tokens. Viral symbols route to the
viral track, not the host panel.

### 12.4 Collision Policy (resolution order — first hit wins)

1. **PANEL COLLISION** — canonical ID matches any gene in the panel universe
   (symbol *or alias*, all three sources). → `in_panel`. No action: the gene
   already has a page; corpus evidence enriches its wiki entry, never forks a
   duplicate.
2. **SEARCH COLLISION** — canonical ID matches a symbol with existing rows in
   `data/genes/gene_presence_v2.jsonl` (598 searched). → `already_searched`.
   **Never re-search**: a gene with BLAST/DIAMOND calls is already
   present-or-absent with recorded provenance; a second search can only
   duplicate work or introduce conflicting calls.
3. **ANNOTATION COLLISION** — canonical ID matches the UniProt GO immune
   backbone (`avimm_uniprot_backbone.json`, 567 symbols). → `annotated`:
   present via annotation, hidden behind the annotation toggle. Escape hatch:
   corpus evidence (≥2 papers or a central role) *elevates* it to literature
   scope, which qualifies it for a first-time search.
4. **NEW CANDIDATE** — no collision anywhere. → evidence gate.

### 12.5 Evidence Gate for New Candidates

- **Search queue**: ≥2 corpus papers *or* `central` importance in any paper.
- **Watchlist**: single-paper `mentioned` genes — recorded, not searched.

Rationale: one passing mention in one paper is not panel-grade evidence
(“genes should come out of the literature as being relevant, not the other
way around”).

### 12.6 DIAMOND/BLAST Search Rules

Only genes that survive §12.4 with disposition `search_queue` or
`elevate_to_search` enter the presence pipeline (`scripts/genes/blast_presence.py`):

- Evidence ladder (per gene × genome): `FULL` blastn e≤1e-20, id≥80%, cov≥60%
  (or tblastn e≤1e-10, id≥40%, cov≥50%); `FRAGMENT` cov 20–60%; `NOT_FOUND`
  below thresholds.
- Genome searchability s = control genes recovered / 12; absence confidence
  high (s≥0.90), medium (s≥0.75), low below.
- Missing corpus text is never negative evidence — absence calls come only
  from the search, with searchability attached.

A queued gene also needs reference sequences (chicken transcript+protein,
  duck where available) before searching; genes without references are
  reported as blocked, not silently dropped.

### 12.7 Outputs (contract for the future machinery)

- `data/genes/panel_intake_report.json` — every candidate symbol with its
  disposition (`noise | viral | in_panel | already_searched | annotated |
  elevate_to_search | search_queue | watchlist`), paper count, central flag.
- `data/genes/diamond_search_queue.json` — only genes needing a search, with
  reason + evidence counts.

Planned entry point: `scripts/genes/panel_intake.py` (deterministic, no LLM;
  the LLM extraction upstream stays quote-grounded and review-gated as in
  DECISION_PIPELINE.md). Machinery to be implemented — method above is the
  contract.

### 12.8 Invariants

- A gene never in the panel universe and never searched gets at most one
  search, ever; results are append-only provenance.
- Annotation-scope genes never appear in literature-facing UI unless elevated
  by corpus evidence.
- Pending/rejected connection candidates never publish; human decisions
  override muse decisions (unchanged, see DECISION_PIPELINE.md).
- **Wiki canonicity (D98)**: `wiki_genes.json` is the single canonical gene
  record. Literature scope == wiki host membership — everywhere. The presence
  catalogue derives `evidence_scope` from the wiki (`export_presence.py`),
  never from independent signals. A curated or literature-scope gene without
  a wiki entry is a **hard error** (`check_gene_set_consistency` in
  `build_wiki_pages.py`, the export gate, and `test_wiki_consistency.py`).
- **No silent evidence loss (D97)**: genes logged to `gene_discovery.jsonl`
  (campaign/connections) enter wiki evidence even when the analysis' genes
  step failed to parse (133/664 analyses); the discovery log is the safety
  net, filtered by the §12.3 noise rules (incl. GFP, a reporter transgene).

## 13. Chicken Reference IDs

For functional anchor transfer, use these chicken identifiers:

| Gene | Ensembl ID | RefSeq ID | Chromosome |
|------|------------|-----------|------------|
| ANP32A | ENSGALG00000014113 | NM_001305256 | 1 |
| ANP32B | ENSGALG00000002633 | NM_001318436 | 28 |
| ANP32E | ENSGALG00000006947 | NM_001006544 | 2 |
| IFIH1 | ENSGALG00000003831 | NM_001193638 | 8 |
| MAVS | ENSGALG00000007653 | NM_001012893 | Z |
| IFNAR1 | ENSGALG00000012495 | NM_204858 | 1 |
| STAT1 | ENSGALG00000004456 | NM_001012914 | 1 |
| IFITM3 | ENSGALG00000046389 | NM_001039283 | 5 |

*Note: Verify against current GRCg7b annotation. IDs may differ between Ensembl releases.*

---

## 14. Key Variants to Track

### 14.1 ANP32A Insertion

The 33-amino-acid insertion distinguishes avian from mammalian ANP32A. Three chicken isoforms:

| Isoform | Insert Status | SUMO Motif | Polymerase Support |
|---------|---------------|------------|-------------------|
| X1 | Full insert | Complete | Strongest |
| X2 | Truncated | Partial | Intermediate |
| X3 | Absent | Absent | Mammalian-like |

Track which isoform(s) each species expresses.

### 14.2 RIG-I Presence

Binary: present or absent (with RNF135).

| Taxon | RIG-I | RNF135 | Notes |
|-------|-------|--------|-------|
| Galliformes | Absent | Absent | Lost together |
| Anseriformes | Present | Present | Functional |
| Most other birds | Present | Present | — |

### 14.3 MHC Diversity

Not specific alleles (not transferable), but:
- Number of BF genes
- Number of BLB genes
- Evidence of MHC-B contig assembly quality
