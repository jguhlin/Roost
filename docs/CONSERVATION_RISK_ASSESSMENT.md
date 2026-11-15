# Conservation Risk Assessment — Action Items & Findings

**Generated from the Roost genomics pipeline · 2026-09-02 · Model v0.4**

This document records every actionable finding, data gap, and next step
identified through the gene-presence pipeline and model building. It is the
operational checklist for conservation-relevant genomics work.

---

## 1 · Confirmed Findings (evidence-backed)

### 1.1 ANP32A 33-aa Insertion (Polymerase Dependency)

**Finding**: Kākāpō possesses the full avian ANP32A insertion (369aa extracted).
The avian influenza polymerase can replicate in kākāpō cells.

| Species | ANP32A status | Risk implication |
|---------|--------------|------------------|
| Kākāpō | ✅ Full insertion confirmed | Viral replication supported |
| NI brown kiwi | ⚠ Partial (248aa) | Needs full-length confirmation |
| Rowi | ⚠ Partial (248aa) | Needs full-length confirmation |
| Takahē | ❓ Fragment only (111aa) | Cannot assess |
| Weka | ❓ Fragment only (111aa) | Cannot assess |
| Kea | ❓ Fragment only (90aa) | Cannot assess |
| Kākāriki | ❓ Fragment only (90aa) | Cannot assess |
| Hoiho | ❓ Fragment only (109aa) | Cannot assess |
| Hihi | ❓ Fragment only (146aa) | Cannot assess |
| GS kiwi | ❓ Fragment only (73aa) | Cannot assess |
| LS kiwi | ❓ Fragment only (73aa) | Cannot assess |
| Chicken | ✅ Full (281aa) | Known susceptible (positive control) |
| Duck | ✅ Full (281aa) | Reservoir — tolerates via other mechanisms |
| Turkey | ✅ Full (281aa) | Known susceptible |
| Zebra finch | ✅ Full (282aa) | Susceptible |

**ACTION NEEDED**: Full-length ANP32A re-extraction across all 15 species
using exon-stitched ORF recovery (not single-ORF DIAMOND fragments).
This is the single highest-priority bioinformatics task for NZ risk assessment.

**Causality evidence**: Gene-edited chickens with disrupted ANP32A insertion
(N129I/D130N) survive H5N1 challenge (17 corpus papers). This is proven
causality, not correlation.

---

### 1.2 DDX58/RIG-I Sensor Status

**Finding**: Kākāpō and all NZ parrots/kākāriki/takahē/weka/hihi possess RIG-I.
Chicken and turkey lost it lineage-wide. DDX58 is Z-linked in birds.

| Species | RIG-I | Evidence quality |
|---------|-------|-----------------|
| Kākāpō | ✓ FULL | 18 exons, e=8.5e-131, chrZ — NCBI annotates gene-DDX58 |
| Kākāriki | ✓ FULL | verified |
| Takahē | ✓ FULL | verified |
| Weka | ✓ FULL | verified |
| Hihi | ✓ FULL | verified |
| Zebra finch | ✓ FULL | verified |
| Duck | ✓ FULL | annotated |
| Chicken | ✗ ABSENT | confirmed absence (galliform loss) |
| Turkey | ✗ ABSENT | confirmed absence (galliform loss) |
| NI brown kiwi | ⚠ FRAGMENT | 8 exons, e=3.9e-111 — likely assembly truncation |
| Rowi | ⚠ FRAGMENT | needs verification |
| GS kiwi | ⚠ FRAGMENT | needs verification |
| LS kiwi | ⚠ FRAGMENT | needs verification |
| Kea | ⚠ FRAGMENT | 11 exons, e=7.3e-49 — likely assembly quality |
| Hoiho | ⚠ FRAGMENT | needs verification |

**ACTION NEEDED**: Verify kiwi/kea/hoiho RIG-I fragments via targeted
exon-level blastn against the exon boundaries established for kākāpō.
Determine: assembly gap or true partial loss?

**Z-linkage**: DDX58 on Z in all chromosome-level assemblies. Males (ZZ)
carry two copies. Sex-biased susceptibility predicted but untested —
flagged as gap G6.

---

### 1.3 MDA5/IFIH1 Status

**Finding**: MDA5 is FULL in all 15 species. This is the universal backup
sensor — no bird lineage has lost it. Chicken's MDA5-only strategy is the
baseline, not the exception.

---

### 1.4 Combined Risk Picture (Kākāpō Example)

| Factor | Status | Direction |
|--------|--------|-----------|
| RIG-I sensor | ✅ present | DETECTION: good |
| MDA5 sensor | ✅ present | DETECTION: good |
| ANP32A insertion | ✅ present | REPLICATION: bad (virus can copy) |
| MX1 function | ❓ aa631 unknown | EFFECTOR: cannot assess |
| OASL | ✅ present | duck-style RIG-I mimic? |
| Cytokine storm genes | ❓ not assessed | PATHOLOGY: unknown |

**Kākāpō net assessment**: Will detect the virus AND support its replication.
Outcome depends on whether the immune response clears before the cytokine
storm — the tolerance-vs-lethality question that requires either challenge
studies or comparative transcriptomics.

---

## 2 · Data Gaps (blocking risk assessment)

### 2.1 Full-Length Gene Extractions Needed

**Problem**: Our DIAMOND-based extraction produces single-ORF fragments for
multi-exon genes. Many NZ species have fragmentary genome assemblies,
compounding the issue.

| Gene | Why it matters | Species needing re-extraction | Method |
|------|---------------|-------------------------------|--------|
| **ANP32A** | Polymerase dependency | 11 NZ species | exon-stitched blastn |
| **MX1** | Effector function (aa631) | ALL 15 (only 148aa fragments) | full CDS recovery |
| **DDX58** | Sensor verification | 7 fragment species | exon-level confirmation |
| **IFITM3** | Entry restriction | unknown coverage | check extraction quality |
| **FURIN** | HPAI systemic spread | not yet searched | add to panel |

### 2.2 MX1 Position 631

This is the single most important un-assessed functional motif. Chicken MX1
with Asn631 is antiviral; Ser631 is non-functional. If NZ species carry
Ser631, their "present" MX1 badge is misleading — the gene is there but
useless against influenza.

**Blocker**: Our MX1 extraction only recovered 148aa fragments (expected
~700aa). Full-length recovery requires either:
- Targeted exon-stitching using chicken RefSeq MX1 exon coordinates
- Or re-running extraction with longer minimum ORF and multiple HSP chaining
- Or extracting from NCBI annotation directly (for annotated genomes)

---

## 3 · Model Gaps (from D56 model v0.4)

### Lit-search targets (papers exist, we haven't ingested them)

| Gap ID | Topic | Search terms | Priority |
|--------|-------|-------------|----------|
| G1 | BST2/tetherin in birds | tetherin avian influenza | medium |
| G2 | Avian apoptosis (CASP3/6) | chicken apoptosis influenza | HIGH |
| G3 | MHC-B disease associations | chicken MHC H5N1 | HIGH |
| G5 | Sialic acid receptor genetics | ST6GAL chicken sialyltransferase | medium |
| G6 | DDX58 Z-linkage sex bias | sex-biased influenza susceptibility | HIGH for NZ |
| G8 | TLR15 ligand | TLR15 ligand identification | low |

### True gaps (little/no avian literature exists)

| Gap ID | Topic | Why it matters |
|--------|-------|----------------|
| T1 | NZ endemic immune responses | No data for kiwi/kea/hoiho/takahē — we ARE the data |
| T5 | 41°C temperature dependence | Bird-specific IFN kinetics unstudied |
| — | Cytokine storm regulators in birds | TNF/IL6/IL1B regulation in ducks vs chickens |
| — | IgY response kinetics | Avian antibody diversity during H5N1 |

---

## 4 · Panel Growth Candidates (awaiting decision)

98 genes with ≥3 corpus papers, not in current 587-panel. Top candidates:

| Gene | Papers | Role | Priority |
|------|--------|------|----------|
| TNF | 29 | central inflammatory driver | HIGH |
| NFKBIA | 27 | NF-κB inhibitor (cytokine brake) | HIGH |
| ISG15 | 22 | ISGylation effector | HIGH |
| IFIT1 | 11 | RNA binding, viral RNA degradation | medium |
| CXCL10 | 10 | chemokine, immune cell recruitment | medium |
| SOCS1 | 8 | cytokine signalling brake | HIGH |
| CASP1 | 7 | inflammasome executioner | HIGH (cytokine storm) |
| IL8 | 10 | neutrophil chemotaxis | medium |
| JAK1 | 7 | IFN receptor kinase (PB2 target!) | HIGH |

**Recommended action**: Add TNF, NFKBIA, ISG15, SOCS1, CASP1, JAK1 in the
next panel growth round (6 genes). These complete the cytokine storm stage
and the PB2-evasion story.

---

## 5 · Infrastructure Needs

### 5.1 Full-Length Gene Extraction Pipeline

Current extraction produces fragments for multi-exon genes. Need:
- Exon-stitching: use annotated exon coordinates (from RefSeq) to guide
  targeted blastn, then stitch HSPs into full-length CDS
- OR: extract from GFF annotations directly for annotated genomes
- OR: minimum-ORF adjustment + multi-HSP chaining with proper gap handling

**Priority**: ANP32A first (polymerase dependency), then MX1 (functional motif).

### 5.2 Functional Motif Checking Pipeline

Beyond ANP32A 33-aa and MX1 aa631:
- OASL: does duck OASL have the LRR-containing C-terminal that enables
  RIG-I mimicry? (Chicken OASL lacks it.)
- TLR7: any bird-specific polymorphisms affecting ssRNA recognition?
- IFITM3: specific residues that determine restriction potency

**Implementation**: for each motif, define reference position, extract
aligned sequences, check residue identity, report per-species functional
status (green/amber/red/black — matching the sensor matrix UI).

### 5.3 Clade Tagging

Add viral clade (2.3.4.4b, 2.3.2.1, etc.) to paper metadata so evidence
can be filtered by clade era. Older clade findings may not apply to the
current panzootic.

---

## 6 · Literature Search Priority Queue

Ranked by conservation impact for NZ species:

1. **Duck OASL mechanism papers** — how does duck OASL activate RIG-I?
   Does kākāpō OASL have the same capacity?
2. **Chicken MHC-B / H5N1 survival associations** — which haplotypes survive?
   Do NZ species have analogous MHC diversity?
3. **Cytokine storm regulation in tolerant vs susceptible birds** — what
   makes a duck not spiral into IL-6 overproduction?
4. **MX1 position 631 across species** — which birds have Asn631?
5. **PB2-E627K mammalian adaptation** — what enables the cattle spillover?
6. **H5N1 in parrots/psittacines** — any case reports or experimental data
   for parrot family (closest relatives to kākāpō)?
7. **Furin expression in bird vascular endothelium** — which species are
   at risk for systemic spread?

---

*This document is the operational companion to the model. Update every
pipeline batch. Cross-reference: MODEL_AVIAN_H5N1_RESPONSE.md (the model),
GENE_PRESENCE_LOG.md (decision history), INTAKE.md (protocols).*
