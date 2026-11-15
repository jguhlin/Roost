# Analysis Framework

This document specifies the analytical methods for comparative host genomics of avian influenza susceptibility, designed to produce results that transfer across species.

---

## 1. Overview

### 1.1 The Central Question

**Why do some bird species survive H5N1 while others die?**

More precisely:
- Which genomic features predict species-level susceptibility?
- Do those features explain within-species variation?
- Which findings transfer to unstudied species?

### 1.2 Why Standard Approaches Fail

| Approach | Problem |
|----------|---------|
| Single-species GWAS | Results don't transfer; population structure confounds |
| One-to-one ortholog expression | Misses immune gene family dynamics (the interesting part) |
| "Presence of RIG-I = resistance" | Transgenic experiments show this is wrong |
| Raw detection counts | Measures ornithologists, not susceptibility |

### 1.3 The Framework

1. **Build orthogroups, not 1:1 mappings**
2. **Model gene features, not just presence**
3. **Include viral genotype as covariate**
4. **Correct for phylogeny**
5. **Separate resistance from tolerance**
6. **Use effort-corrected phenotypes**

---

## 2. Phenotype Modeling

### 2.1 Phenotype Types

"Immune to H5N1" is not a phenotype. These are:

| Phenotype | Measurement | Interpretation |
|-----------|-------------|----------------|
| **Infection resistance** | PCR-negative + seronegative after exposure | Prevents infection entirely |
| **Replication resistance** | Lower viral titer/AUC | Controls viral load |
| **Dissemination resistance** | Virus localized, no neuroinvasion | Prevents systemic spread |
| **Shedding resistance** | Lower oral/cloacal titer, shorter duration | Reduces transmission |
| **Disease tolerance** | Same viral burden, less pathology | Survives despite infection |
| **Acquired immunity** | Seroconversion, protection on rechallenge | Prior exposure benefit |

A bird that survives while shedding heavily is **tolerant**, not resistant — and may be more epidemiologically dangerous.

### 2.2 The Detection Problem

Raw detection counts from WAHIS/EMPRES-i measure:

```
Detections = f(True susceptibility × Abundance × Colonial breeding ×
               Coastal accessibility × Surveillance intensity × Testing policy)
```

Without a denominator, top "susceptible" species will be large, colonial, coastal, heavily birdwatched.

**Solution:** Use GBIF/eBird occurrence data as exposure denominator.

```
Effort-corrected risk = Detections / Expected observations
```

This is a real quantity. Raw counts aren't.

### 2.3 Effort Correction

```python
def compute_effort_corrected_risk(species_id, detections_df, occurrences_df):
    """
    Compute detection rate relative to expected encounters.
    """
    detections = detections_df[detections_df.taxon_id == species_id].count_dead.sum()

    # GBIF occurrences in affected regions during outbreak period
    occurrences = occurrences_df[
        (occurrences_df.taxon_id == species_id) &
        (occurrences_df.region.isin(affected_regions)) &
        (occurrences_df.date.between(outbreak_start, outbreak_end))
    ].shape[0]

    if occurrences == 0:
        return None  # Cannot compute

    return detections / occurrences
```

### 2.4 Conspicuous Absences

The most informative signal may be species with:
- High modeled exposure
- Near-zero detections

These are tolerance/resistance candidates. Anseriformes is the known answer; the question is who else.

---

## 3. Comparative Genomics

### 3.1 Why Orthogroups, Not Orthologues

One-to-one ortholog mapping fails precisely for immune genes:

| Gene Family | Problem |
|-------------|---------|
| MHC-B | Birth-death evolution, CNV, microchromosomal |
| IFITM | Lineage-specific duplication, positive selection |
| Interferons | Tandem clusters, rapid divergence |
| Defensins | Copy number variation |
| NLRs | Species-specific expansions |

**Gene loss/gain is phenotype-relevant.** RIG-I absence in Galliformes is not "missing data" — it's the signal.

### 3.2 Building Orthogroups

Use OrthoFinder or similar with these modifications:

1. Include all B10K/VGP avian genomes
2. Use chicken (GRCg7b) as primary reference
3. Keep many-to-many and one-to-many relationships
4. Flag species where gene is absent vs not found
5. For absent calls, require assembly N50 > threshold

```bash
# Pseudocode workflow
orthofinder -f protein_sequences/ -t 32 -a 8
```

### 3.3 Gene Features to Extract

For each species × gene (or orthogroup), compute:

| Feature | Type | Notes |
|---------|------|-------|
| presence | boolean | Is gene present? |
| copy_number | integer | How many copies? |
| is_intact | boolean | Full-length, no frameshifts/stops? |
| protein_length | integer | Amino acid count |
| domain_architecture | string | Pfam domains present |
| key_residue_states | varies | e.g., ANP32A insertion isoform |
| percent_identity | float | To chicken reference |
| dN/dS | float | Selection pressure |
| is_pseudogene | boolean | Intact but nonfunctional? |

### 3.4 Assembly Quality Flags

Gene absence claims must be qualified by assembly quality:

```python
def absence_confidence(genome, gene_region_gc, gene_on_microchromosome):
    """
    High confidence absence requires good assembly.
    """
    if genome.assembly_level in ['Chromosome', 'Complete']:
        if genome.microchromosomes_resolved or not gene_on_microchromosome:
            return 'high'

    if genome.scaffold_n50 > 10_000_000:
        if gene_region_gc < 0.55:  # Not in GC-rich hard region
            return 'medium'

    return 'low'  # Cannot distinguish absence from assembly gap
```

---

## 4. Statistical Models

### 4.1 OrthoGLMM Framework

The natural framework for species-level comparative analysis with phylogenetic structure.

**Basic model:**

```
y_species ~ gene_features + phylogenetic_covariance
```

Where:
- `y` is the phenotype (effort-corrected detection rate, mortality rate, etc.)
- `gene_features` are presence/absence, copy number, domain variants
- Phylogenetic covariance accounts for shared ancestry

### 4.2 Extended Model

For richer data (expression datasets):

```
y_sample = β₀ + β₁·G_species + β₂·V_virus + β₃·T_time + β₄·(G×V) +
           u_phylogeny + u_experiment + ε
```

Where:
- `G_species` = gene feature for that species
- `V_virus` = viral clade/genotype
- `T_time` = time post-infection
- `G×V` = host-by-virus interaction
- `u_phylogeny` = random effect for phylogenetic covariance
- `u_experiment` = random effect for study/batch

### 4.3 Separating Resistance from Tolerance

**Resistance model:**
```
viral_burden ~ gene_features + covariates
```
→ Gene that lowers viral burden = resistance candidate

**Tolerance model:**
```
disease_severity ~ viral_burden + gene_features + gene_features×viral_burden + covariates
```
→ Gene associated with lower pathology *at same viral burden* = tolerance candidate

This distinction is essential. Otherwise a survival-associated gene might just indicate lower exposure.

### 4.4 Implementation

```python
# Using R's MCMCglmm or brms via rpy2, or Python's pymc

import pymc as pm
import numpy as np

def fit_phylo_glmm(y, X, phylo_vcv, species_idx):
    """
    Phylogenetically-controlled GLMM.

    y: outcome vector
    X: design matrix of gene features
    phylo_vcv: phylogenetic variance-covariance matrix
    species_idx: species index for each observation
    """
    n_species = phylo_vcv.shape[0]
    n_features = X.shape[1]

    with pm.Model() as model:
        # Fixed effects
        beta = pm.Normal('beta', mu=0, sigma=1, shape=n_features)

        # Phylogenetic random effect
        sigma_phylo = pm.HalfNormal('sigma_phylo', sigma=1)
        u_phylo = pm.MvNormal('u_phylo', mu=np.zeros(n_species),
                              cov=sigma_phylo**2 * phylo_vcv,
                              shape=n_species)

        # Linear predictor
        mu = pm.math.dot(X, beta) + u_phylo[species_idx]

        # Likelihood (Gaussian for continuous, Binomial for binary, etc.)
        sigma = pm.HalfNormal('sigma', sigma=1)
        y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=y)

        # Sample
        trace = pm.sample(2000, tune=1000, cores=4)

    return trace
```

---

## 5. Expression Analysis

### 5.1 Cross-Study Integration

Do NOT combine published normalized expression matrices. Instead:

1. Download raw reads from all datasets
2. Process through unified pipeline
3. Map to species-specific genomes where available
4. Quantify at orthogroup level

### 5.2 Dual Quantification

For each sample, estimate:

| Quantity | Method |
|----------|--------|
| Host gene expression | Salmon/kallisto to species transcriptome |
| Host transcript isoforms | Salmon/kallisto |
| Viral read count | Map to challenge virus genome |
| Viral segment abundance | Per-segment counts |
| Within-host viral variants | Variant calling on viral reads |
| Host allele-specific expression | Where SNPs available |

### 5.3 Timing Decomposition

For each gene/orthogroup, estimate:

| Parameter | Meaning |
|-----------|---------|
| baseline | Expression in uninfected controls |
| induction_rate | How fast does it respond? |
| peak_magnitude | Maximum fold change |
| time_to_peak | When does it peak? |
| duration | How long is it elevated? |
| decay_rate | Return to baseline |

High expression at day 3 post-infection can mean:
- Effective early response (good)
- Consequence of uncontrolled virus (bad)

Must condition on viral burden.

### 5.4 Cell Type Deconvolution

Bulk RNA-seq averages over cell types. A gene associated with survival could be:
- Antiviral in epithelial cells (good)
- Inflammatory damage in macrophages (bad)
- Vascular pathology in endothelial cells (bad)

Use single-cell references (CRA006707, 2026 spatial atlas) to deconvolve bulk samples:

```python
# Using BayesPrism, CIBERSORTx, or similar
cell_fractions = deconvolve(bulk_expression, sc_reference_signatures)
```

---

## 6. Candidate Prioritization

### 6.1 Multi-Evidence Scoring

A high-priority candidate should have multiple independent lines of support:

| Evidence Type | Weight | Example |
|---------------|--------|---------|
| Causal perturbation | 5 | ANP32A editing |
| Within-species association | 4 | Gene variant correlates with survival |
| Cross-species association | 4 | Phylo-corrected presence predicts outcome |
| Repeated differential expression | 3 | Up in multiple resistant species |
| Correct cell type + timing | 2 | Early, epithelial, before viral divergence |
| Sequence/CNV variation | 2 | Consistent with function |
| No generic inflammation signal | 1 | Not just IL6/IL1B late response |

### 6.2 Tiered Output

| Tier | Criteria | Example Genes |
|------|----------|---------------|
| 1 | Causal perturbation evidence | ANP32A/B/E |
| 2 | Replicated across species + experiments | IFIT5, IFITM1/3, OAS |
| 3 | Replicated within one species/lineage | MDA5-MAVS pathway |
| 4 | Plausible but expression-only | Many ISGs |
| Context-specific | Works only for specific clade/tissue/host | Some MHC associations |

### 6.3 Negative Filters

Downweight candidates that:
- Appear only in late-stage, terminal samples
- Correlate with viral burden rather than predict it
- Have inconsistent direction across studies
- Are generic stress/inflammation markers
- Lack appropriate cell-type expression

---

## 7. Validation Framework

### 7.1 Holdout Validation

For any predictive model:

1. Train on species with good data (chicken, duck, mallard, etc.)
2. Test on held-out species with phenotype data
3. Report prediction accuracy on held-out set

### 7.2 Cross-Clade Validation

Models trained on H5N1 clade 2.2 should be tested on:
- H5N1 clade 2.3.4.4b
- H5N8
- H7N1

A host gene that only works for one viral clade is less useful.

### 7.3 Model Validation Thresholds

Before escalating from comparative-genomic inference to within-population genomic prediction:

- Need ≥100 individuals with matched genotype + infection outcome + serology
- Heritability estimates for AI response currently unavailable in wild birds
- Must separate acquired immunity from heritable resistance

---

## 8. Analytical Pipeline

### 8.1 Phase 1: Comparative Gene Content

```
B10K/VGP genomes → OrthoFinder → Orthogroups
                                      ↓
                        Gene feature matrix
                        (presence, CNV, domains)
                                      ↓
                        Join to species phenotypes
                        (effort-corrected detections)
                                      ↓
                        Phylogenetic comparative model
                                      ↓
                        Candidate genes associated with
                        rank-order species susceptibility
```

### 8.2 Phase 2: Expression Integration

```
Challenge RNA-seq datasets → Unified reprocessing
                                      ↓
                        Orthogroup-level expression
                                      ↓
                        Timing decomposition
                        + viral load conditioning
                        + cell type deconvolution
                                      ↓
                        Expression features per species
                                      ↓
                        Join to Phase 1 candidates
                                      ↓
                        Refined candidate ranking
```

### 8.3 Phase 3: Within-Species Validation

```
Within-species outcome datasets → Resistance vs tolerance models
(PRJEB48271, PRJNA1413929)                    ↓
                               Do same genes explain
                               individual-level variation?
                                      ↓
                               Final candidate panel
```

---

## 9. Key Caveats

### 9.1 What This Framework Cannot Do

- Discover SNP-level associations in species without population resequencing
- Predict outcomes for a species with no genomic data
- Distinguish heritable resistance from acquired immunity without serology
- Transfer MHC allele associations between distantly related species

### 9.2 Known Confounders

| Confounder | Mitigation |
|------------|------------|
| Phylogeny | Phylogenetic random effects |
| Exposure variation | Effort correction |
| Viral genotype | Include as covariate |
| Study batch | Study random effects |
| Assembly quality | Provenance flags |
| Annotation completeness | Explicit unknown status |

### 9.3 The RIG-I Warning

RIG-I is present in ducks (resistant) and absent in chickens (susceptible). Obvious conclusion: add RIG-I to chickens → resistance.

**Actual result:** Transgenic RIG-I chickens had *worse* outcomes with virulent viruses — more inflammation, more pathology, higher mortality.

**Lesson:** "Gene in resistant species but not susceptible species" is not sufficient evidence for beneficial transfer. Context matters.
