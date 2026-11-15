# Database Design

This document specifies the data model, schema, and provenance system for the Avian Influenza Host Genomics Resource.

---

## 1. Design Principles

### 1.1 Core Philosophy

1. **Versioned dataset is the primary product.** The database exists to produce downloadable, citable, archived datasets. The web interface is a view over them.
2. **Provenance is non-negotiable.** Every value must track its source. "Gene absent" vs "gene not found in fragmented assembly" are different claims.
3. **Static generation.** Output is pre-computed, not dynamically queried. A static site can't rot into a broken database.
4. **Single taxonomic backbone.** Pick one (Clements/eBird or IOC), freeze it, use Avibase as crosswalk. Every ingest maps to this.

### 1.2 What This Is Not

- Not a real-time dashboard (link to CDC/WOAH/DashFLUboard for that)
- Not a GISAID mirror (their terms prohibit redistribution)
- Not a sequence database (link to NCBI/ENA for sequences)

---

## 2. Core Entities

### 2.1 Species

The central entity. One row per species in the taxonomic backbone.

```
species
├── taxon_id (primary key, from backbone)
├── scientific_name
├── common_name
├── family
├── order
├── conservation_status (IUCN)
├── backbone_version
└── avibase_id (crosswalk key)
```

### 2.2 Genome

One row per genome assembly. Multiple genomes may exist per species.

```
genome
├── accession (primary key)
├── taxon_id (foreign key → species)
├── assembly_level (Chromosome/Scaffold/Contig/Complete)
├── contig_n50
├── scaffold_n50
├── total_length
├── annotation_status (Full/Updated/None)
├── source (GenBank/RefSeq)
├── release_date
├── is_representative (boolean: best assembly for this species)
└── microchromosomes_resolved (boolean or null)
```

**Selection logic for `is_representative`:**
1. Prefer RefSeq over GenBank
2. Prefer annotated over unannotated
3. Prefer Chromosome > Scaffold > Contig
4. Prefer higher scaffold N50
5. Prefer more recent

### 2.3 Detection

One row per outbreak/detection event, reconciled across sources.

```
detection
├── detection_id (primary key, synthetic)
├── taxon_id (foreign key → species)
├── event_date
├── location_country
├── location_region
├── location_lat
├── location_lon
├── count_dead
├── count_affected
├── virus_subtype
├── virus_clade
├── confirmation_status (Confirmed/Suspected/Unconfirmed)
├── source_wahis (boolean)
├── source_empresi (boolean)
├── source_aphis (boolean)
├── source_literature (boolean)
├── source_refs (array of DOIs/URLs)
├── reconciliation_status (Single/Reconciled/Conflict)
└── reconciliation_notes
```

### 2.4 Gene

One row per immune gene in the panel.

```
gene
├── gene_id (primary key, from Avimm or curated)
├── symbol
├── name
├── category (Sensor/Effector/Signaling/Tolerance/Adaptive)
├── tier (1/2/3/4)
├── chicken_ensembl_id
├── chicken_refseq_id
├── orthogroup_id
└── notes
```

### 2.5 GenePresence

The species × gene matrix. One row per species × gene combination.

```
gene_presence
├── taxon_id (foreign key → species)
├── gene_id (foreign key → gene)
├── genome_accession (foreign key → genome, the source assembly)
├── status (Present/Absent/Partial/Unknown)
├── confidence (High/Medium/Low)
├── evidence_type (Annotation/BLAST/HMM/Manual)
├── copy_number (integer or null)
├── has_frameshift (boolean)
├── has_premature_stop (boolean)
├── protein_length
├── percent_identity_to_chicken
├── notes
└── provenance_flags (see §3)
```

### 2.6 ExpressionDataset

Tracking available RNA-seq challenge data.

```
expression_dataset
├── dataset_id (accession)
├── taxon_ids (array)
├── virus_subtypes (array)
├── tissues (array)
├── timepoints
├── sample_count
├── cell_type (Bulk/SingleCell/Spatial)
├── platform
├── publication_doi
├── data_location (SRA/GEO/NGDC/ENA)
└── notes
```

---

## 3. Provenance System

### 3.1 Provenance Flags

Every cell in GenePresence carries provenance flags encoded as a bitmask or JSON:

```json
{
  "assembly_quality": "scaffold",
  "microchromosomes_resolved": false,
  "annotation_source": "projection",
  "search_method": "tblastn",
  "evalue": 1e-50,
  "coverage": 0.92,
  "manual_review": false,
  "known_issue": null
}
```

### 3.2 Distinguishing Absence Types

The database must distinguish:

| Observation | Status | Confidence | Interpretation |
|-------------|--------|------------|----------------|
| Annotated gene present | Present | High | Gene exists |
| BLAST hit, high identity | Present | High | Gene exists |
| BLAST hit, partial | Partial | Medium | Gene fragmented or assembly artifact |
| No BLAST hit, assembly N50 > 10Mb | Absent | High | Gene likely lost |
| No BLAST hit, assembly N50 < 1Mb | Unknown | Low | Cannot distinguish loss from assembly gap |
| Region not assembled (known gap) | Unknown | Low | Assembly limitation |

### 3.3 Source Tracking for Detections

Each detection record carries per-source booleans and references:

```json
{
  "sources": {
    "wahis": {"present": true, "event_id": "12345", "fetched": "2026-08-01"},
    "empresi": {"present": true, "event_id": "E-2026-001", "fetched": "2026-08-01"},
    "aphis": {"present": false},
    "literature": {"present": true, "refs": ["doi:10.1234/example"]}
  },
  "reconciliation": {
    "status": "reconciled",
    "count_range": [100, 150],
    "notes": "WAHIS and literature agree; EMPRES-i count lower"
  }
}
```

---

## 4. Schema Details

### 4.1 Primary Tables (PostgreSQL-style)

```sql
CREATE TABLE species (
    taxon_id INTEGER PRIMARY KEY,
    scientific_name TEXT NOT NULL,
    common_name TEXT,
    family TEXT,
    "order" TEXT,
    conservation_status TEXT,
    backbone_version TEXT NOT NULL,
    avibase_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE genome (
    accession TEXT PRIMARY KEY,
    taxon_id INTEGER REFERENCES species(taxon_id),
    assembly_level TEXT CHECK (assembly_level IN ('Complete', 'Chromosome', 'Scaffold', 'Contig')),
    contig_n50 BIGINT,
    scaffold_n50 BIGINT,
    total_length BIGINT,
    annotation_status TEXT,
    source TEXT CHECK (source IN ('GenBank', 'RefSeq')),
    release_date DATE,
    is_representative BOOLEAN DEFAULT FALSE,
    microchromosomes_resolved BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE gene (
    gene_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    name TEXT,
    category TEXT CHECK (category IN ('Sensor', 'Effector', 'Signaling', 'Tolerance', 'Adaptive', 'Dependency')),
    tier INTEGER CHECK (tier BETWEEN 1 AND 4),
    chicken_ensembl_id TEXT,
    chicken_refseq_id TEXT,
    orthogroup_id TEXT
);

CREATE TABLE gene_presence (
    taxon_id INTEGER REFERENCES species(taxon_id),
    gene_id TEXT REFERENCES gene(gene_id),
    genome_accession TEXT REFERENCES genome(accession),
    status TEXT CHECK (status IN ('Present', 'Absent', 'Partial', 'Unknown')),
    confidence TEXT CHECK (confidence IN ('High', 'Medium', 'Low')),
    evidence_type TEXT,
    copy_number INTEGER,
    has_frameshift BOOLEAN,
    has_premature_stop BOOLEAN,
    protein_length INTEGER,
    percent_identity_to_chicken REAL,
    provenance JSONB,
    notes TEXT,
    PRIMARY KEY (taxon_id, gene_id)
);

CREATE TABLE detection (
    detection_id SERIAL PRIMARY KEY,
    taxon_id INTEGER REFERENCES species(taxon_id),
    event_date DATE,
    location_country TEXT,
    location_region TEXT,
    location_lat REAL,
    location_lon REAL,
    count_dead INTEGER,
    count_affected INTEGER,
    virus_subtype TEXT,
    virus_clade TEXT,
    confirmation_status TEXT,
    source_wahis BOOLEAN DEFAULT FALSE,
    source_empresi BOOLEAN DEFAULT FALSE,
    source_aphis BOOLEAN DEFAULT FALSE,
    source_literature BOOLEAN DEFAULT FALSE,
    source_refs TEXT[],
    reconciliation_status TEXT,
    reconciliation_notes TEXT
);
```

### 4.2 Export Formats

**CSV/Parquet downloads:**

1. `species.csv` — flat species table
2. `genomes.csv` — all assemblies with quality metrics
3. `gene_matrix.csv` — species × gene presence matrix (wide format)
4. `gene_presence_long.csv` — long format with full provenance
5. `detections.csv` — reconciled detection events
6. `coverage_matrix.csv` — species × (has_genome, has_annotation, has_detection, has_expression)

**Each release:**
- Zenodo DOI
- Version number (semver)
- Changelog
- Schema documentation

---

## 5. Update Cadence

| Data Type | Source | Update Frequency |
|-----------|--------|------------------|
| Genomes | NCBI Datasets download | Weekly |
| Detections (APHIS) | Direct download | Weekly during outbreaks |
| Detections (WAHIS) | Export + process | Monthly |
| Detections (EMPRES-i) | Export + process | Monthly |
| Literature | Manual curation | As papers appear |
| Gene presence | Recompute on new genomes | Per genome release |

---

## 6. Coverage Matrix

The first and most important view. One row per species:

| Species | Has Detection | Has Genome | Assembly Quality | Has Annotation | Has Expression Data |
|---------|---------------|------------|------------------|----------------|---------------------|
| Anas platyrhynchos | Yes | Yes | Chromosome | Yes | Yes (PRJEB41063, E-MTAB-2909) |
| Gallus gallus | Yes | Yes | Chromosome | Yes | Yes (multiple) |
| Morus bassanus | Yes | Yes | Scaffold | No | No |
| Sula variegata | Yes | No | - | - | No |

This answers: "Which species have both genomic resources AND phenotype data?"

---

## 7. Directory Structure

```
data/
├── raw/
│   ├── ncbi/
│   │   ├── avian_genomes.zip
│   │   └── avian_genome_summary.tsv
│   ├── wahis/
│   ├── empresi/
│   ├── aphis/
│   └── literature/
├── processed/
│   ├── species.parquet
│   ├── genomes.parquet
│   ├── detections.parquet
│   ├── gene_presence.parquet
│   └── coverage_matrix.parquet
├── exports/
│   └── v0.1.0/
│       ├── species.csv
│       ├── genomes.csv
│       ├── gene_matrix.csv
│       ├── detections.csv
│       └── CHANGELOG.md
└── GENOME_INVENTORY_SUMMARY.md
```

---

## 8. Implementation Notes

### 8.1 Storage Choice

For a solo project with static output:
- **Parquet** for processed data (fast reads, schema enforcement, compresses well)
- **DuckDB** for ad-hoc queries during development
- **CSV** for exports (universal compatibility)

No need for PostgreSQL in production unless building a dynamic API.

### 8.2 Taxonomy Stability

1. Choose backbone at project start (recommend: Clements/eBird 2026)
2. Store `backbone_version` on every species record
3. On backbone updates: add new species, mark deprecated ones, never delete
4. Use Avibase for crosswalking incoming data that uses other taxonomies

### 8.3 Genome Selection

Script to select representative genome per species:

```python
def select_representative(genomes_for_species):
    """Select best genome for a species."""
    return sorted(genomes_for_species, key=lambda g: (
        g.source == 'RefSeq',           # Prefer RefSeq
        g.annotation_status is not None, # Prefer annotated
        {'Complete': 4, 'Chromosome': 3, 'Scaffold': 2, 'Contig': 1}[g.assembly_level],
        g.scaffold_n50 or 0,
        g.release_date or date.min
    ), reverse=True)[0]
```
