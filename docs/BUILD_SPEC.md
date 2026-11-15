# Build Specification

This document specifies what to build, in what order, and what "done" looks like at each phase.

---

## 1. Project Structure

### 1.1 The Insight

**There is no avian influenza host genomics resource.** The viral side is saturated. The epi side is covered. But the host layer — which species has a genome, which genes they have, how that maps to outcomes — doesn't exist.

### 1.2 The Opportunity

Phylogeny predicts susceptibility; ecological traits don't (published 2026). The obvious missing covariate is **gene content**. Nobody has built that layer.

### 1.3 Architecture Principle

**Both faces render from the same build artifact.** One nightly/weekly pipeline produces a versioned species table. The researcher site and public site are two views of it. This is what makes it a solo project.

---

## 2. Phase 0: Foundation

### 2.1 Deliverables

- [ ] Taxonomic backbone frozen (Clements/eBird or IOC)
- [ ] Avibase crosswalk configured
- [ ] Directory structure created
- [ ] Pixi environment with core tools
- [ ] Initial genome inventory downloaded

### 2.2 Acceptance Criteria

```
✓ Can map any species name to canonical taxon_id
✓ Can list all avian genomes with quality metrics
✓ Environment reproducible via pixi install
```

### 2.3 Files Produced

```
/
├── pixi.toml
├── data/
│   ├── raw/ncbi/avian_genomes.zip
│   └── avian_genome_core.tsv
└── docs/
    ├── DATA_CATALOG.md
    ├── DATABASE_DESIGN.md
    ├── ANALYSIS_FRAMEWORK.md
    ├── GENE_PANEL.md
    └── BUILD_SPEC.md
```

---

## 3. Phase 1: Coverage Matrix

### 3.1 Goal

Answer: **"Which bird species have both genomic resources AND phenotype data?"**

This is useful on day one, before any immune gene is called.

### 3.2 Deliverables

- [ ] Species table populated from taxonomic backbone
- [ ] Genome table populated from NCBI inventory
- [ ] Representative genome selected per species
- [ ] Detection table ingested from APHIS (US data)
- [ ] Coverage matrix computed

### 3.3 Coverage Matrix Columns

| Column | Source | Notes |
|--------|--------|-------|
| taxon_id | Backbone | Primary key |
| scientific_name | Backbone | — |
| common_name | Backbone | — |
| has_detection | APHIS/WAHIS | Any confirmed H5 detection |
| has_genome | NCBI | Any assembly exists |
| best_assembly_level | NCBI | Chromosome/Scaffold/Contig |
| scaffold_n50 | NCBI | Quality metric |
| has_annotation | NCBI | Any gene annotation |
| has_expression_data | Curated | Any challenge RNA-seq |

### 3.4 Acceptance Criteria

```
✓ Can query: "Show species with detection AND chromosome-level genome"
✓ Can query: "Show species with detection but NO genome"
✓ Matrix exportable as CSV/parquet
✓ Matrix includes 2000+ species
```

### 3.5 Ingest Sequence

1. **NCBI genome inventory** — already downloaded
2. **Taxonomic backbone** — Clements/eBird download
3. **APHIS detections** — US wild bird table
4. **Expression dataset inventory** — manual curation from DATA_CATALOG

---

## 4. Phase 2: Detection Reconciliation

### 4.1 Goal

Reconcile the 2-order-of-magnitude discrepancy between sources.

| Source | Reported Deaths |
|--------|-----------------|
| EMPRES-i+ | ~8,928 |
| WAHIS | ~141,651 |
| Literature | ~1,285,036 |

### 4.2 Deliverables

- [ ] WAHIS ingest pipeline
- [ ] EMPRES-i ingest pipeline
- [ ] Literature reference table (manual curation)
- [ ] Reconciliation logic per species
- [ ] Effort correction using GBIF occurrences

### 4.3 Detection Record Structure

```python
{
    "detection_id": "DET-2024-001",
    "taxon_id": 8839,
    "event_date": "2024-03-15",
    "location": {"country": "PE", "region": "Lima", "lat": -12.0, "lon": -77.0},
    "count_dead": 15000,
    "virus_clade": "2.3.4.4b",
    "sources": {
        "wahis": {"event_id": "W123", "count": 12000},
        "empresi": {"event_id": "E456", "count": 8000},
        "literature": {"doi": "10.1234/x", "count": 15000}
    },
    "reconciled_count": 15000,
    "reconciliation_notes": "Literature count most comprehensive"
}
```

### 4.4 Acceptance Criteria

```
✓ Single record per outbreak event, not per source
✓ Per-source counts preserved
✓ Reconciled count computed with logic documented
✓ Coverage matrix updated with reconciled detection status
```

---

## 5. Phase 3: Gene Presence Matrix

### 5.1 Goal

For the ~65-70 gene panel, determine presence/absence/status across all species with genomes.

### 5.2 Deliverables

- [ ] Gene panel table populated from GENE_PANEL.md
- [ ] BLAST/HMM pipeline for gene detection
- [ ] Gene presence matrix computed
- [ ] Provenance flags for each call

### 5.3 Pipeline

```
For each species with representative genome:
    For each gene in panel:
        1. TBLASTN chicken protein against species genome
        2. If hit: extract region, check for frameshifts/stops
        3. Classify: Present/Absent/Partial/Unknown
        4. Record provenance (method, e-value, coverage, assembly quality)
```

### 5.4 Key Genes for Phase 3

Prioritize presence/absence calls for:

| Priority | Genes | Rationale |
|----------|-------|-----------|
| 1 | DDX58 (RIG-I), RNF135 | Binary presence explains major species difference |
| 2 | ANP32A/B/E | Host dependency; isoform matters |
| 3 | IFITM cluster | Copy number informative |
| 4 | OAS/OASL family | Copy number informative |
| 5 | IFIH1 (MDA5), MAVS | Core sensing pathway |

### 5.5 Acceptance Criteria

```
✓ Gene presence matrix covers all species with scaffold N50 > 1Mb
✓ Provenance distinguishes "absent" from "not found in poor assembly"
✓ Matrix includes confidence levels
✓ Exportable as CSV/parquet
```

---

## 6. Phase 4: Researcher Interface

### 6.1 Goal

Static site rendering the coverage matrix and species/gene pages.

### 6.2 Pages

| Page | Content |
|------|---------|
| **Coverage Matrix** | Interactive table, sortable/filterable |
| **Species Page** | Per-species: genome info, detection summary, gene presence, links |
| **Gene Page** | Per-gene: cross-species presence, chicken annotation, references |
| **Downloads** | Versioned CSV/parquet files |
| **About** | Methods, data sources, citation |

### 6.3 Species Page Content

```
# Anas platyrhynchos (Mallard)

## Taxonomy
Order: Anseriformes | Family: Anatidae
Conservation: Least Concern

## Genome
Representative: GCF_015476345.1
Level: Chromosome | Scaffold N50: 74.9 Mb | Annotated: Yes

## H5N1 Detections
Total events: 847 | Countries: 42 | Peak: 2022-2023

## Immune Gene Status
| Gene | Status | Confidence | Notes |
|------|--------|------------|-------|
| DDX58 (RIG-I) | Present | High | Functional |
| ANP32A | Present | High | Avian isoform |
| IFITM1 | Present | High | — |

## Expression Data
- E-MTAB-2909: H5N1/H5N2 challenge, lung/ileum
- PRJEB41063: H5N1 challenge, lung/ileum/brain

## External Links
[NCBI] [Ensembl] [B10K] [GBIF]
```

### 6.4 Acceptance Criteria

```
✓ Static site builds from data files
✓ Coverage matrix interactive and searchable
✓ Each species with data has a page
✓ Downloads include version and schema doc
✓ Site deployable to GitHub Pages or similar
```

---

## 7. Phase 5: Public Interface

### 7.1 Goal

Non-researcher-facing pages. Three pages maximum.

### 7.2 Pages

| Page | Content |
|------|---------|
| **"Why do some birds survive?"** | RIG-I and ANP32A story for general audience |
| **Species Lookup** | Plain-language risk cards |
| **"I found a dead bird"** | Route to official channel (MPI, etc.) |

### 7.3 What NOT to Build

- No case map (link to CDC/WOAH/DashFLUboard)
- No real-time dashboard
- No account system

### 7.4 Acceptance Criteria

```
✓ Explainer is accurate, accessible, not stale
✓ Species lookup returns plain-language summary
✓ Dead bird page routes to correct authority by country
✓ Prominent disclaimer: "We are not the reporting authority"
```

---

## 8. Sequence Summary

```
Phase 0: Foundation
    │
    ├── Freeze taxonomy
    ├── Set up pixi
    └── Download genome inventory
          │
          ▼
Phase 1: Coverage Matrix
    │
    ├── Species table
    ├── Genome table
    └── Detection ingest (APHIS)
          │
          ▼
Phase 2: Detection Reconciliation
    │
    ├── WAHIS ingest
    ├── EMPRES-i ingest
    └── Effort correction
          │
          ▼
Phase 3: Gene Presence Matrix
    │
    ├── Gene panel table
    ├── BLAST pipeline
    └── Presence calls
          │
          ▼
Phase 4: Researcher Interface
    │
    ├── Static site generation
    ├── Coverage matrix page
    ├── Species/gene pages
    └── Downloads
          │
          ▼
Phase 5: Public Interface
    │
    ├── Explainer
    ├── Species lookup
    └── Report dead bird
```

---

## 9. Definition of Done

### 9.1 Phase 1 Test

**Can someone answer a question with your site that they could not have answered in an afternoon of googling?**

For Phase 1: *"Which bird species have both a decent genome and a real detection record, and which don't?"*

Nobody can answer that today without doing the work.

### 9.2 MVP Acceptance

The resource is worth existing when:

1. Coverage matrix is queryable
2. At least 100 species have gene presence data
3. Detection data reconciled for at least one major source
4. Downloads versioned with DOI
5. Site stable and deployable

---

## 10. Non-Goals (Explicit)

| Won't Build | Reason |
|-------------|--------|
| Real-time case dashboard | Exists (CDC, WOAH, DashFLUboard) |
| GISAID mirror | Terms prohibit |
| User accounts | Unnecessary complexity |
| Dynamic API | Static output sufficient |
| Full Avimm reimplementation | Use as source, don't rebuild |
| Within-species GWAS | Requires population data we don't have |

---

## 11. Sustainability

### 11.1 Failure Modes

| Risk | Mitigation |
|------|------------|
| Portal dies when grant ends | Versioned dataset is primary product; site is view |
| Data goes stale | Weekly automated genome refresh; monthly detection check |
| Scope creep | Explicit non-goals; Phase 1 MVP ships first |
| Nobody uses it | Coverage matrix useful immediately; validates demand |

### 11.2 Governance Model

Copy: **BirdLife Seabird Tracking Database**
- Same taxa
- Same contributor community
- 20 years of solved data-ownership problems

For pre-publication data, copy: **EMBL-EBI Pathogens Portal Data Hubs**

---

## 12. Technical Stack (Suggested)

| Component | Tool | Notes |
|-----------|------|-------|
| Environment | Pixi | Reproducible |
| Data processing | Python + DuckDB | Parquet-native |
| BLAST | NCBI BLAST+ | Standard |
| Static site | Astro or Hugo | Fast, Markdown-friendly |
| Hosting | GitHub Pages | Free, stable |
| Archival | Zenodo | DOI per release |

---

## 13. Current Status

### 13.1 Completed

- [x] Pixi environment set up
- [x] NCBI genome inventory downloaded (3,845 assemblies)
- [x] Core docs written (DATA_CATALOG, DATABASE_DESIGN, ANALYSIS_FRAMEWORK, GENE_PANEL, BUILD_SPEC)

### 13.2 Next Steps

1. Freeze taxonomic backbone (Clements/eBird 2026)
2. Build species table with Avibase crosswalk
3. Select representative genome per species
4. Ingest APHIS detection data
5. Compute initial coverage matrix

### 13.3 Blocking Questions

1. Clements/eBird vs IOC for backbone?
2. Hosting preference (GitHub Pages, Cloudflare, other)?
3. Initial geographic scope (US-only APHIS, or global from start)?
