# Actionable Items for Avian Influenza Host Genomics Resource

## 1. DATA SOURCES TO INGEST

### Viral & Outbreak Data (Backbone - freely redistributable)
- [ ] **BV-BRC / NCBI Virus** — host species, date, location, sequence (openly redistributable backbone)
- [ ] **WOAH WAHIS** — event-level notifications, species, counts, dates
- [ ] **FAO EMPRES-i+** — outbreak and epi data
- [ ] **USDA APHIS** — wild bird detections (dense, tabular, US only)
- [ ] **EFSA/ECDC quarterlies** — mostly PDF, annexes sometimes tabular
- [ ] **National agency pages** — NZ MPI, Wildlife Health Australia, DEFRA, CFIA (scrape and curate)
- [ ] **iNaturalist** — near-real-time global wildlife mortality (noisy but catches unofficial events)
- [ ] **Nextstrain avian-flu builds** — segment builds for H5N1/H5NX/H7N9/H9N2

### Host Genomic Resources
- [ ] **B10K (Bird 10,000 Genomes)** — 363 annotated genomes (~92% of bird families); b10k.genomics.cn
- [ ] **VGP (Vertebrate Genomes Project)** — high-contiguity assemblies; vertebrategenomesproject.org
- [ ] **NCBI Datasets API** — accession, assembly level, contiguity, annotation status per taxon (nightly refresh)
- [ ] **Avian Immunome DB (Avimm)** — >1,000 chicken immune genes mapped across B10K genomes
- [ ] **Harmonised 394-species host list** — from Sci Data (doi:10.1038/s41597-025-06451-1)
- [ ] **ChickenGTEx** — 7,015 bulk RNA-seq, 127,598 single cells, 2,869 WGS; chicken.farmgtex.org
- [ ] **FAANG chicken** — PRJEB14330, GSE158430 (217 datasets: ChIP-seq, ATAC-seq, RNA-seq, RRBS)

### Experimental Challenge Datasets (RNA-seq)
- [ ] **PRJEB41063** — 497 samples; chicken, turkey, duck, crow, goose, pigeon; H5N1/H9N2; BEST BACKBONE
- [ ] **E-MTAB-2908 / E-MTAB-2909** — matched chicken/duck H5N1/H5N2 challenge
- [ ] **PRJNA767080** — Pekin duck tissue time-course, H5N1
- [ ] **CRA006707** — chicken lung single-cell RNA-seq (NGDC, not GEO); 16,642 immune cells
- [ ] **PRJEB48271** — multiple chicken breeds, H7N1/H5N8 clade 2.3.4.4b, resistant vs susceptible
- [ ] **PRJNA1413929** — early nasal/lung transcriptomics, resilient vs susceptible outcomes
- [ ] **PRJNA664709** — chicken and tufted-duck, 8 LPAI subtypes, 216 tissue libraries
- [ ] **PRJDB17017** — fibroblast cells from 11 bird species, H5N1 clade 2.5
- [ ] **PRJNA640810 / PRJEB44719** — black swan and mute swan genomes + transcriptomes
- [ ] **Mallard/teal shedding datasets** — ileum, bursa, cloacal shedding measurements
- [ ] **OMIX017644 / PRJCA066382** — 2026 multi-species single-cell/spatial atlas, H5N6

### Phenotype / Mortality Data
- [ ] **GBIF / eBird** — occurrence records as denominator layer for effort-corrected analysis
- [ ] **Seabird mass-mortality literature** — South America 2022-2023 counts, Antarctic detections
- [ ] **Seabird seroprevalence** — black-iris gannets, murres, puffins, eiders

---

## 2. INFRASTRUCTURE TO BUILD

### Foundation (Build First)
- [ ] **Freeze taxonomic backbone** — pick Clements/eBird or IOC; wire Avibase as crosswalk
- [ ] **Build ingest pipelines** — BV-BRC → harmonised host list → USDA APHIS → WAHIS → EMPRES-i+
- [ ] **Create canonical species table** — provenance stamped per field, not per dataset
- [ ] **Static site generation** — from versioned builds (fails gracefully, costs nothing to host)

### Researcher-Facing v1
- [ ] **Coverage matrix** — every bird species × (has detections / has assembly / microchromosomes resolved / has annotation / has host-response data)
- [ ] **Species pages** — genome availability, quality flags, detection counts, conservation status, outbound links
- [ ] **Gene pages** — cross-species alignments, orthology confidence, selection statistics, chicken FAANG/ChickenGTEx regulatory tracks
- [ ] **Provenance panel** — on every cell; distinguish "absent" vs "not found in fragmented assembly"
- [ ] **Downloads** — species × gene matrix, harmonised phenotype table, orthogroup alignments, HMM profiles, annotation liftover tracks (CSV + parquet, Zenodo DOI per release)

### Public-Facing v1
- [ ] **"Why do some birds survive this?"** — RIG-I and ANP32A story for general audience
- [ ] **Species lookup** — plain-language risk cards tied to local avifauna
- [ ] **"I found a dead bird"** — route to official channel (MPI hotline in NZ), prominent disclaimer
- [ ] **NO case map** — link to CDC, WOAH, DashFLUboard instead

---

## 3. ANALYSES TO PERFORM

### Comparative Genomics
- [ ] **Immune-gene presence/absence matrix** — across B10K/VGP genomes using Avimm as target list
- [ ] **Focus on key loci**: RIG-I/RNF135 status, ANP32A isoform, IFITM copy number, MHC-B architecture
- [ ] **Build orthogroups** — not just one-to-one orthologues; capture copy number, domain architecture, gene loss
- [ ] **Phylogenetic comparative models** — test which gene features predict rank-order species susceptibility
- [ ] **Gene loss/gain mapping** — treat presence/absence as phenotype-relevant feature

### Expression Analysis
- [ ] **Reprocess all RNA-seq through unified pipeline** — don't combine published normalized matrices
- [ ] **Quantify host and virus simultaneously** — viral reads, segment abundance, consensus genotype, within-host variants
- [ ] **Build expression modules** — baseline, early response, peak, duration, conditional on viral load
- [ ] **Cell-type deconvolution** — using CRA006707 and 2026 spatial atlas as anchors

### Statistical Models
- [ ] **OrthoGLMM framework** — extend from binary species phenotype to continuous outcomes
- [ ] **Model structure**: y = host_features + virus_clade + time + dose + tissue + phylogeny + study
- [ ] **Separate resistance from tolerance** — condition pathology on viral burden
- [ ] **Keep viral genotype in models** — HA/NA clade, polymerase substitutions, NS1 variation

### Phenotype Reconciliation
- [ ] **Event-level reconciled table** — dedup key, per-record provenance, cross-source flag
- [ ] **Effort-corrected abundance** — use GBIF/eBird as denominator
- [ ] **Identify "conspicuous absences"** — high exposure, near-zero detections (tolerance candidates)
- [ ] **Within-species geographic variation** — same species, different populations, different outcomes

---

## 4. CANDIDATE GENES TO PRIORITIZE

### Tier 1: Strongest Evidence
- [ ] **ANP32A/B/E** — host-dependency factors; gene editing shows causal resistance
- [ ] **IFIT5** — direct H5N1 evidence in chicks
- [ ] **IFITM1/2/3** — direct H5N1 evidence in chicks
- [ ] **OAS/OASL-RNASEL** — strong comparative evidence
- [ ] **IFIH1/MDA5, DHX58/LGP2, MAVS** — cytoplasmic sensing network
- [ ] **IFNAR1-JAK1-STAT1/STAT2-IRF9** — type-I interferon response

### Tier 2: Tolerance/Pathology
- [ ] **PLAU** — best current outcome-associated tolerance candidate
- [ ] **VCAM1, TNFRSF1A, PGF** — vascular/inflammatory markers
- [ ] **NF-κB regulators** — NFKB1, RELA
- [ ] **Inflammasome/PANoptosis** — CASP1, CASP8, RIPK1, NLRP3

### Genes to Treat Cautiously
- [ ] **RIG-I/DDX58** — important but context-dependent; transgenic experiments show harm
- [ ] **MX1 S631N** — inconsistent; do not treat as validated resistance marker
- [ ] **MHC-B21** — partial protection, population-specific

---

## 5. PARTNERSHIPS & SAMPLE COLLECTION

### Prospective Biobank (Highest Value)
- [ ] **Partner with DOC/MPI and Te Niwha (NZ)** — for taonga species sampling
- [ ] **Partner with RSPB (gannets), APHA** — UK seabird survivors
- [ ] **Partner with South American/Antarctic teams** — FAO subantarctic monitoring

### Sample Collection Protocol
For each confirmed case, exposed survivor, and managed threatened bird, collect:
- [ ] Host whole-genome sequencing (low-pass or full WGS)
- [ ] Complete viral genome from same individual
- [ ] Serial oral/cloacal qPCR + infectious titre
- [ ] Disease phenotype (symptoms, pathology, tissue distribution, survival time)
- [ ] H5 and NP serology, neutralization titre
- [ ] Covariates (age, sex, body condition, population, prior vaccination)
- [ ] Biobank (blood, serum, swabs, lung, trachea, ileum, spleen, brain)
- [ ] Functional material (fibroblasts, PBMCs, organoid-compatible tissue)

### Key Sampling Categories
1. PCR-positive severe or fatal cases
2. PCR-positive mildly affected survivors
3. Seropositive post-outbreak survivors
4. Repeatedly PCR-negative birds with documented exposure
5. Matched pre-outbreak or low-exposure controls

---

## 6. GOVERNANCE & SUSTAINABILITY

- [ ] **Versioned dataset as primary product** — citable, archived, survives if site dies
- [ ] **Separate researcher/public cadence** — researcher: slow, versioned; public: daily-ish freshness
- [ ] **Copy BirdLife Seabird Tracking Database governance** — 20 years of solved data-ownership problems
- [ ] **Iwi/hapū governance** — for taonga species genomic data from outset

---

## 7. VALIDATION & ESCALATION THRESHOLDS

### Before Escalating to Quantitative Genetics
- [ ] Need ≥~100 individuals with matched genotype + infection outcome + serology
- [ ] Heritability estimates for AI response traits currently unavailable
- [ ] Must separate acquired immunity from heritable resistance via paired serology + genotype

### Model Validation
- [ ] Test ChickenGTEx-trained sequence-to-function model on held-out duck regulatory data
- [ ] Benchmark: gene presence/absence + coding features should explain meaningful fraction of rank-order susceptibility

---

## 8. IMMEDIATE NEXT STEPS (Ordered)

1. **Freeze taxonomic backbone** — pick one, wire Avibase crosswalk
2. **Build BV-BRC/NCBI Virus ingest** — openly redistributable backbone
3. **Build genome inventory via NCBI Datasets API** — nightly refresh
4. **Create coverage matrix** — species × (detections / assembly / annotation / response data)
5. **Ingest harmonised 394-species host list**
6. **Build event-level reconciled phenotype table** — address 2-order-of-magnitude discrepancy
7. **Ship researcher v1** — matrix + species pages + downloads

---

## KEY INSIGHT

**The gap is clear**: there is no avian influenza *host genomics* resource. Not partial, not stale — absent. Phylogeny predicts susceptibility; traits don't. The obvious missing covariate between "phylogeny" and "trait" is **gene content** — and nobody has built that layer. The reconciled phenotype table (addressing the 8,928 vs 141,651 vs 1,285,036 detection count discrepancy) is the single highest-value contribution.
