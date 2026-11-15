# Data Manifest

> A synthesis layer for avian influenza research.
> We join bird flu data (detections, genomics, infected tracking) with links to
> migration, occurrence, and ecology resources — not duplicating, but connecting.

Data files are not stored in git — this manifest is the source of truth.

**Last updated:** 2026-08-26

---

## Quick Stats

### Core Data (Downloaded & Processed)

| Category | Records | Species | Coverage |
|----------|---------|---------|----------|
| **HPAI Detections** | 20,669 (deduplicated) | 296 | Global, 2004-2026 |
| **Raw Detection Records** | 52,794 | 666 | 8 sources merged |
| **Avian Genomes** | 3,845 | 2,044 | NCBI assemblies |
| **Species Profiles** | 11,284 | All Aves | Taxonomy + genomics |
| **Georeferenced Events** | 7,312 | - | 35.4% of detections |

### Linked Resources (External Reference)

| Resource | Scale | Use Case | Link |
|----------|-------|----------|------|
| **Movebank** | 7,500+ studies | Migration patterns | movebank.org |
| **GBIF** | 3.1B occurrences | Species distribution | gbif.org |
| **eBird** | 500M observations | Occurrence/phenology | ebird.org |
| **BirdLife** | All species | Range maps | datazone.birdlife.org |
| **USGS GPS Telemetry** | 3M locations | Waterfowl movement context | sciencebase.gov |

---

## Quick Regeneration

```bash
# Periodic refresh — fetches all automatic sources (now including EMPRES-i
# via the FAO cloud function), re-ingests, rebuilds everything, runs tests:
pixi run refresh              # full cycle incl. web build + tests
pixi run refresh --skip-web   # data pipeline only

# Full rebuild
pixi run build-all

# Or step by step:
pixi run parse-taxonomy        # NCBI taxonomy
pixi run build-species-table   # Genome catalog
pixi run ingest-detections     # Merge all detection sources (51K records)
pixi run load-gps              # GPS telemetry (3M locations)
pixi run load-hpai-tracking    # HPAI georeferenced data
pixi run build-phenotype       # Derive mortality phenotype
pixi run build-coverage-matrix # Data coverage analysis
```

---

## 1. NCBI Taxonomy

### Source
- **URL:** https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz
- **Size:** ~75 MB compressed
- **Update frequency:** Daily (we update weekly)

### Local Files
```
data/
├── taxdump.tar.gz              # Raw download
└── taxonomy/                   # Extracted
    ├── nodes.dmp               # Parent-child relationships
    ├── names.dmp               # Scientific/common names
    └── ...
```

### Download Command
```bash
curl -o data/taxdump.tar.gz https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz
mkdir -p data/taxonomy && tar -xzf data/taxdump.tar.gz -C data/taxonomy
```

### Generated Output
```
data/aves_taxonomy.tsv          # 16,564 rows (11,284 species + 5,280 subspecies)
```

**Columns:** `taxon_id, scientific_name, common_name, rank, genus, family, order`

---

## 2. NCBI Genome Assemblies

### Source
- **Tool:** NCBI datasets CLI
- **Query:** All Aves genomes (dehydrated = metadata only)
- **Size:** ~2.5 MB (metadata), ~500 GB if hydrated

### Download Command
```bash
pixi run datasets download genome taxon "Aves" --dehydrated --filename data/avian_genomes.zip
unzip -o data/avian_genomes.zip -d data/avian_genomes
```

### Local Files
```
data/
├── avian_genomes.zip
├── avian_genomes/
│   └── ncbi_dataset/
│       └── data/
│           └── assembly_data_report.jsonl
├── avian_genome_summary.tsv    # Full 178-column export (289 MB)
└── avian_genome_core.tsv       # Core columns only (341 KB)
```

### Generated Output
```
data/genomes.parquet            # 3,845 assemblies with is_representative flag
data/species_table.parquet      # 11,284 species with best genome per species
```

**Key stats:**
- 3,845 total assemblies
- 2,044 unique species with genomes
- 652 chromosome-level
- 263 annotated

---

## 3. APHIS Wild Bird Detections

### Source
- **URL:** https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv
- **Coverage:** US wild bird HPAI detections since Jan 2022
- **Update frequency:** Weekly during outbreaks

### Download Command
```bash
mkdir -p data/raw
curl -o data/raw/aphis_wild_birds.csv \
  https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv
```

### Local Files
```
data/
└── raw/
    └── aphis_wild_birds.csv    # 19,625 records
```

**Columns:** `State, County, Collection Date, Date Detected, HPAI Strain, Bird Species, WOAH Classification, Sampling Method, Submitting Agency`

### Generated Output
```
data/aphis_species_mapping.tsv  # APHIS name → NCBI taxon_id mapping
data/aphis_detections.parquet   # Aggregated by species (170 species)
data/aphis_full.parquet         # Full records with taxon_id (19,625 rows)
```

**Mapping stats:**
- 184 APHIS species names mapped
- 96.3% of records successfully mapped to NCBI taxonomy
- 170 unique species with detections

---

## 3a. APHIS Mammal Detections

### Source
- **URL:** https://www.aphis.usda.gov/sites/default/files/hpai-mammals.csv
- **Page:** https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza/hpai-detections/mammals
- **Coverage:** US HPAI detections in wild + captive mammals, 2022–present (one row per animal)
- **Update frequency:** Weekly
- **Fetch:** `pixi run fetch aphis_mammals` (plain HTTP; the Drupal page's `data-csv-url`)

**Columns:** `State, County, Date Collected, Date Detected, HPAI Strain, Species`

### Notes
- "(captive)" suffix moved to sampling method (captive vs wild) at ingest
- Repeated identical rows are aggregated per event with `detection_count` = animals
- Species mapped via shared `MAMMAL_ALIASES` (45 of 57 names, 96% of animals)
- Not in NCBI Aves taxonomy → `taxon_id` null, `scientific_name` still set

---

## 3c. APHIS Commercial & Backyard Flock Detections

### Source
- **URL (Tableau):** https://publicdashboards.dl.usda.gov/t/MRP_PUB/views/VS_Avian_HPAIConfirmedDetections2022/HPAI2022ConfirmedDetections
- **Page:** https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza/hpai-detections/commercial-backyard-flocks
- **Coverage:** US confirmed HPAI premises 2022–present, with birds affected (208M+ cumulative)
- **Update frequency:** Weekly
- **Fetch:** `pixi run fetch aphis_flocks` → `scripts/fetch_aphis_flocks.py` (Playwright)

### How the export works
No static CSV exists. The page embeds a Tableau dashboard; the data lives in a
hidden **`ExportToCsv`** sheet exported via toolbar → Download → Crosstab → CSV.
The raw export is **UTF-16 tab-delimited** and its final column (birds affected)
has **no header** — the fetcher decodes it and writes UTF-8 CSV with an explicit
`Birds Affected` column.

**Columns (normalized):** `Special ID, County Name, State, Production, Confirmed Diagnosis, Control Area Released, Birds Affected`

### Notes
- One row per premises; `record_ref` = Special ID protects distinct premises from dedup collapse
- `detection_count` = birds affected (matches "numbers affected" into species totals)
- Production type → domestic species: chickens → *Gallus gallus*, turkeys →
  *Meleagris gallopavo*, ducks → *Anas platyrhynchos*; backyard/mixed premises
  (WOAH Poultry / Non-Poultry, live markets, gamebirds) stay unmapped
- Full-fidelity side table: `data/aphis_flocks.parquet` (incl. control-area status)

---

## 3b. Open Avian Flu Dataset (OAFD)

### Source
- **URL:** https://zenodo.org/records/8246456
- **DOI:** 10.5281/zenodo.8246456
- **Creator:** Francesco Branda (ORCID 0000-0002-9485-3877)
- **License:** CC-BY-4.0
- **Coverage:** Global HPAI data 2021-2023

### Download Command
```bash
mkdir -p data/raw/external
curl -L -o data/raw/external/avian-flu-main.zip \
  https://zenodo.org/api/records/8246456/files/avian-flu-main.zip/content
unzip -o data/raw/external/avian-flu-main.zip -d data/raw/external/
```

### Local Files
```
data/raw/external/avian-flu-main/
├── Americas/
│   └── USA/
│       └── hpai-wild-birds.csv      # 4,362 records (2022)
├── Europe/
│   └── Italy/
│       └── HPAI/
│           ├── 2021-2022/
│           │   └── hpai-wild-birds-2021-2022.csv  # 91 records
│           ├── 2022-2023/
│           │   └── hpai-wild-birds-2022-2023.csv  # 176 records
│           └── ...
└── ...
```

**Key differences from APHIS:**
- OAFD US 2022 predates APHIS data (early outbreak)
- Italy data has no sampling method (detection only, no phenotype)
- Species names include scientific names in parentheses

---

## 3c. Merged Detection Data

### Generation Command
```bash
pixi run ingest-detections    # Merges all sources with provenance
pixi run build-phenotype      # Derives mortality phenotype
```

### Merged Output
```
data/
├── detections_merged.parquet       # 24,254 records from all sources
├── detections_merged.tsv
└── detections_provenance.json      # Source-level statistics
```

### Source Summary (After Deduplication)

| Source | Records | Species | Mapped | Date Range | Has Coords |
|--------|---------|---------|--------|------------|------------|
| APHIS US | 9,696 | 182 | 170 | 2023-2024 | No |
| SDM HPAI | 6,629 | 231 | 132 | 2005-2024 | Yes (100%) |
| EMPRES-i Linked | 1,862 | 110 | 112 | 2004-2022 | No |
| UK DEFRA | 1,463 | 89 | 56 | 2024-2026 | No |
| Canada CWHC | 685 | 68 | 28 | 2022-2026 | Yes (100%) |
| Italy Wild | 180 | 37 | 33 | 2021-2023 | No |
| Iceland USGS | 115 | 20 | 18 | 2010-2011 | No |
| OAFD US 2022 | 39 | 21 | 21 | 2022 | No |

**Total:** 20,669 records (after deduplication from 52,794 raw), 297 species mapped to NCBI

See `DATA_INVENTORY.md` for full provenance details.

### Sampling Types (After Deduplication)
| Type | Records | Percentage |
|------|---------|------------|
| Mortality | ~10,000 | ~50% |
| Unknown | ~6,600 | ~32% |
| Harvest | ~2,600 | ~13% |
| Live | ~1,400 | ~7% |

### Species Name Harmonization
The ingestion script harmonizes species names across sources:
1. **APHIS mapping:** Use existing `aphis_species_mapping.tsv`
2. **Parenthetical extraction:** Parse "Common name (Genus species)" for European data
3. **Taxonomy lookup:** Match scientific names to `aves_taxonomy.tsv`

---

## 3d. GPS Telemetry (Contextual)

> **Note:** General waterfowl tracking provides migration context. Only mortality
> data is directly relevant to HPAI. For broader tracking, link to Movebank.

### USGS Waterfowl GPS (2019-2020) — Migration Context
**Source:** USGS ScienceBase (doi:10.5066/P13E7PCP)
**Locations:** 2,797,469 | **Individuals:** 412 | **Species:** 9

Downloaded for spatial/temporal context — understanding where reservoir species
move helps interpret HPAI spread patterns. Not HPAI-specific data.

| Species | Locations | Lat Range | Notes |
|---------|-----------|-----------|-------|
| Anser albifrons | 1.2M | 36-64°N | Major reservoir species |
| Anas acuta | 533K | 34-71°N | Pintail, wide range |
| Anas platyrhynchos | 171K | 37-48°N | Mallard, key reservoir |

### USGS Life History GPS — Includes Mortality (CORE)
**Source:** USGS ScienceBase (doi:10.5066/P9XBZKZ8)
**Locations:** 224,888 | **Includes:** 23,140 "Dead" state locations

This dataset includes **mortality tracking** — birds tracked until death.
The "Dead" state records (7 individuals) provide actual death locations.

| Life History State | Locations | Bird Flu Relevance |
|-------------------|-----------|-------------------|
| **Dead** | **23,140** | **Core — mortality locations** |
| Migration | 2,376 | Context — spread pathways |
| Local/Molt/Nest | 192K | Context — exposure sites |

**File:** `data/gps_telemetry/hourly_life_history_gps.parquet`

---

## 3e. HPAI Tracking (Georeferenced)

### ACAP HPAI Seabird Database
**File:** `data/hpai_tracking/acap_hpai_events.parquet`
**Records:** 112 | **Species:** 20 (Procellariiformes)

Confirmed H5N1 events in albatrosses and petrels with coordinates.
- Source: Zenodo ACAP HPAI Database
- Coverage: Global, 2021-2026
- Confirmed: 107 | Suspected: 5

### GPS Mortality Events
**File:** `data/hpai_tracking/gps_mortality_events.parquet`
**Events:** 7 individuals with death locations

Extracted from GPS life history data - last known locations of tracked birds.

### Detection Records with Coordinates
**File:** `data/hpai_tracking/detections_with_coordinates.parquet`
**Records:** 9,561 | **Species:** 219

Sources contributing coordinates:
- SDM Europe: 11,353 records (EPSG:3035 → WGS84)
- Canada CWHC: 753 records
- Italy ISS: 239 records
- Ireland DAFM: coordinates available but not yet extracted

Script: `scripts/load_hpai_tracking.py`
Task: `pixi run load-hpai-tracking`

---

## 3f. Surveillance Data

### USGS Izembek Alaska (2011-2024)
**File:** `data/raw/external/usgs-izembek/sampling.csv`
**Samples:** 13,014 | **Species:** ~50

AIV screening results from waterfowl at Izembek NWR, Alaska.
- 480 samples with AIV subtypes (low-path: H3N8, H4N6, etc.)
- 0 HP IAV positive (pre-2022 H5N1 arrival)
- Source: USGS ScienceBase (doi:10.5066/F7JD4W2W)

### BBS Survey Routes
**File:** `data/raw/external/usgs-bbs/Routes.csv`
**Routes:** 5,824 with coordinates

Breeding Bird Survey route locations for ecological context.

---

## 4. Coverage Matrix (Primary Output)

### Generated From
- `data/species_table.parquet` (taxonomy + genomes)
- `data/aphis_detections.parquet` (phenotype)
- Expression dataset list (hardcoded in script)

### Output Files
```
data/
├── coverage_matrix.parquet     # Full matrix (11,284 species)
├── coverage_matrix.tsv         # TSV export
├── coverage_matrix_with_data.tsv  # Only species with any data (2,016)
└── coverage_by_order.tsv       # Order-level summary
```

**Columns:**
```
taxon_id, scientific_name, common_name, order, family,
has_genome, assembly_level, scaffold_n50, has_annotation,
has_expression, datasets,
has_detection, detection_count, states_detected,
accession
```

**Key intersections:**
- 133 species with genome + detection
- 10 species with genome + expression
- 5 species with all three

---

## 5. Expression Datasets (Curated)

These are not downloaded automatically — they require manual SRA/GEO access.

| Accession | Species | Virus | Samples | Location |
|-----------|---------|-------|---------|----------|
| PRJEB41063 | Chicken, turkey, duck, crow, goose, pigeon | H5N1/H9N2 | ~497 | ENA |
| E-MTAB-2908 | Chicken | H5N1/H5N2 | 20 | ArrayExpress |
| E-MTAB-2909 | Mallard | H5N1/H5N2 | 20 | ArrayExpress |
| CRA006707 | Chicken (single-cell) | H5N1/H9N2 | 16,642 cells | NGDC |
| PRJEB48271 | Multiple chicken breeds | H7N1/H5N8 | varies | ENA |
| PRJNA640810 | Black swan | HPAI | varies | SRA |
| PRJDB17017 | 11 species fibroblasts | H5N1 | varies | DDBJ |

---

## 6. Gene Panel Reference Sequences

### Source
- **NCBI Protein database** via E-utilities
- Reference proteins from chicken (Gallus gallus) and duck (Anas platyrhynchos)

### Generation Commands
```bash
pixi run gene-panel       # Generate gene_panel.json and .tsv
pixi run fetch-sequences  # Download protein sequences from NCBI
```

### Local Files
```
data/genes/
├── gene_panel.json            # Full gene definitions
├── gene_panel.tsv             # Tabular format
└── sequences/
    ├── ANP32A_chicken.fasta
    ├── ANP32B_chicken.fasta
    ├── ANP32E_chicken.fasta
    ├── DDX58_duck.fasta       # RIG-I (absent in chicken)
    ├── RNF135_duck.fasta      # RIPLET (absent in chicken)
    ├── IFIH1_chicken.fasta    # MDA5
    ├── ...
    └── gene_panel_references.fasta  # Combined
```

### Gene Panel Summary

| Tier | Count | Examples |
|------|-------|----------|
| 1 | 6 | ANP32A/B/E, IFIT5, IFITM1/3 |
| 2 | 11 | RIG-I, MDA5, MAVS, IFNAR1, STAT1/2, OAS |
| 3 | 1 | MX1 (controversial) |

**Key insight:** DDX58 (RIG-I) and RNF135 are ABSENT in chicken — present in duck. This is the classic species difference that partially explains duck tolerance.

---

## 7. Gene Presence Detection

### Source
- **NCBI Gene database** via datasets CLI
- **Method:** Direct gene symbol queries per species
- **Provenance:** Full evidence tracking with confidence levels

### Generation Command
```bash
pixi run detect-genes           # Full run (~3 hours)
pixi run detect-genes-test      # Test with subset
```

### Local Files
```
data/genes/
├── gene_presence_calls.json     # Full provenance (3,636 calls)
├── gene_presence_calls.parquet  # Tabular format
└── gene_presence_matrix.parquet # Pivot table (species × genes)
```

### Results Summary (202 annotated species × 18 genes)

| Status | Count | Percentage |
|--------|-------|------------|
| Present | 1,987 | 55% |
| Absent | 1,618 | 44% |
| Unknown | 31 | 1% |

### Gene Detection Rates

| Gene | Present | Notes |
|------|---------|-------|
| IFIH1 (MDA5) | 169 | Primary sensor in chickens |
| RNASEL | 168 | OAS pathway effector |
| ANP32E | 168 | Polymerase cofactor |
| PLAU | 168 | Tolerance candidate |
| ANP32A | 159 | Key polymerase cofactor |
| DDX58 (RIG-I) | 149 | Absent in Galliformes |
| RNF135 (RIPLET) | 128 | Co-absent with RIG-I |
| IFIT5 | 40 | Limited annotation |
| ANP32B | 4 | Rare or different naming |
| IFITM1/3 | 3/8 | Limited annotation |

### Current Evidence Breakdown

| Method | Status | Count | Confidence |
|--------|--------|-------|------------|
| `ncbi_gene_db` | Present | 1,987 | High |
| `annotation` | Absent | 1,594 | High (1,234) / Medium (360) |
| `annotation` | Unknown | 31 | Low |
| `inferred` | Absent | 24 | High |

**Absent calls by assembly level:**
- Chromosome-level: 1,246 (high confidence)
- Scaffold-level: 370 (medium confidence)
- Complete Genome: 2 (high confidence)

### Evidence Hierarchy

Gene presence calls follow a strict evidence hierarchy:

| Method | Status | Confidence | Meaning |
|--------|--------|------------|---------|
| `ncbi_gene_db` | Present | High | Gene found in NCBI Gene database via symbol query |
| `inferred` | Absent | High | Known phylogenetic absence (e.g., RIG-I in Galliformes) |
| `annotation` | Absent | High | Not found in chromosome-level annotated genome |
| `annotation` | Absent | Medium | Not found in scaffold-level annotated genome |
| `annotation` | Unknown | Low | Not found in contig-level genome (may be assembly gap) |
| `blast` | Present/Partial | varies | Sequence similarity search (future) |
| `none` | Unknown | Low | No annotation available, needs BLAST |

### Evidence Fields by Method

**ncbi_gene_db** (Present):
```json
{
  "ncbi_gene_id": "103810204",
  "symbol": "ANP32E",
  "description": "acidic nuclear phosphoprotein 32 family member E",
  "chromosomes": ["12"]
}
```

**annotation** (Absent):
```json
{
  "searched": true,
  "found": false
}
```

**inferred** (Absent):
```json
{
  "reason": "DDX58/RIG-I lost in Galliformes lineage"
}
```

**blast** (Future):
```json
{
  "query_accession": "NP_001292185.1",
  "subject_accession": "...",
  "identity": 85.2,
  "coverage": 98.1,
  "e_value": 1e-150
}
```

### Interpreting "Absent" Calls

An "Absent" call does NOT always mean the gene is truly missing:

| Assembly Level | Confidence | Interpretation |
|----------------|------------|----------------|
| Chromosome | High | Likely true absence |
| Scaffold | Medium | May be assembly gap or annotation gap |
| Contig | Low | Cannot distinguish from assembly gap |

**True biological absence** is only confident when:
1. Chromosome-level assembly with full annotation, OR
2. Known phylogenetic loss (e.g., RIG-I in Galliformes)

### Provenance Fields
Each gene call includes:
- `status`: Present, Absent, Unknown
- `confidence`: High, Medium, Low
- `method`: ncbi_gene_db, annotation, inferred, blast, none
- `evidence`: Method-specific supporting data
- `assembly_accession`: Genome assembly used
- `assembly_level`: Chromosome, Scaffold, Contig
- `annotation_status`: Full annotation, etc.
- `call_date`: Timestamp for versioning

---

## 7a. OrthoFinder Orthology (Orthogroups)

### Source
- **Run:** `orthofinder_aves463_root16_20260928` — OrthoFinder 3.1.5 over 463 avian proteomes (6,824,866 proteins → 40,494 orthogroups), root-corrected species tree, reviewed export
- **Manifest SHA256:** `00be8d47c37cd1d56c7eb4118184fc34ed73bbbb6091b6d6af08b291a551a754` (extraction verified against `MANIFEST_core.json`)

### Outputs (web/public/data, not in git)
| File | Content | Size |
|------|---------|------|
| `orthogroups/OG*.json` | Per-OG payload: members (leaf key, of_id, accession, product), copy counts (463-array), newick tree | 68 MB (720 OGs) |
| `orthogroups/OG*.fa.zst` | Per-OG MSA, zstd-19, decompressed in-browser (fzstd), ≤150 representative species | 6.9 MB |
| `orthogroups/og_summary.json` | Slim per-OG stats for gene pages | — |
| `og_matrix.parquet` | Dense long (og, of_id, copies) for all 40,494 OGs × 463 species; DuckDB-ready | 6.3 MB |
| `orthofinder_gene_to_og.tsv` | Panel-gene → OG mapping: tier, votes, confidence, chicken cross-check (799 genes → 720 OGs) | 77 KB |
| `orthofinder/species_map.json` | of_id (0–462) → sci name, assembly, leaf label | 101 KB |
| `orthofinder/species_og_stats.json` | Per-species badge stats: n_ogs, n_proteins, n_panel_ogs (463 species) | 31 KB |
| `orthofinder/species_tree.txt` | Root-corrected species tree (leaf order = display order) | 29 KB |
| `gene_orthogroups.json` | Gene page lookup: symbol → primary OG + confidence | 100 KB |

### Regeneration
```bash
pixi run python scripts/orthofinder/build_species_map.py
pixi run python scripts/orthofinder/map_panel_to_og.py
pixi run python scripts/orthofinder/export_og_data.py      # per-OG payloads + og_summary
pixi run python scripts/orthofinder/export_og_matrix.py   # og_matrix.parquet
```

### Confidence tiers
521 high · 103 medium · 2 curated (IFITM1/IFITM3 → OG0016003) · 366 review. Panel-gene payloads cover the 720 OGs of mapped panel genes; the matrix covers all 40,494 OGs. BLAST-based presence (§7, 255 assemblies) and OG copy number (463 species) are shown side-by-side and never silently merged.

---

## 7b. Micro-Synteny Blocks (Host Panel)

### Source
- **Derived from §7 annotation coordinates** (`gene_presence_v2.parquet`: 44,201 located calls,
  117 species, 709 genes; proper chromosomes only — unlocalized/unplaced scaffolds dropped).

### Method
- Segments: panel genes on the same chromosome chained while ≤0.5 Mb apart (window ≤2 Mb).
- Blocks: recurring co-located **core gene-sets** — a seed pair (≥3 species support; literature-famous
  immune loci seeded first: TAP1–TAP2, IFITM, TLR2A/B, RAG1–RAG2, …) grown by intersecting the
  gene-sets of segments containing it. Union-find is deliberately avoided: bird chromosomes are
  broadly syntenic and transitive linkage merges the whole panel into one blob.
- Ships when the core recurs in ≥3 species → **100 blocks**, top: CD74–CSF1R (91 sp),
  STAT1–STAT4 (90 sp), CD28–CTLA4 (90 sp), RAG1–RAG2 (+TRAF6, 86 sp), TAP1–TAP2 (51 sp),
  IFITM cluster with B4GALNT4 (3 sp).

### Outputs (web/public/data/synteny, not in git)
| File | Content | Size |
|------|---------|------|
| `blocks.json` | 100 blocks: core genes + per-species tracks (chrom, coordinates, panel neighbours in window) | 2.3 MB |
| `gene_context.json` | Per-gene panel neighbours within ±2.5 Mb (≤8 species, chicken/mallard preferred) | 1.7 MB |
| `flanks.json` | Curated blocks × key species: merged current-annotation genes (strand; drift-aligned; unaligned tracks flagged) + `gene_index` {symbol → block} for gene-page detail upgrades | ~0.4 MB |

### Flanking-gene detail (`fetch_synteny_flanks.py`)
For ~18 famous immune blocks × ≤4 key species each, the **current** NCBI annotation of the
same assembly is fetched via the `datasets` CLI (`--include gff3`, cached slim per assembly
under `data/synteny/flanks/cache/`). Detailed tracks draw every named protein-coding gene from
that annotation (case-insensitive symbols; mouse `Ifitm1`), translate panel genes missing from
it by the anchor's observed drift, and flag tracks resolved only by coordinate overlap as
unaligned (⚠). Panel coordinates may stem from older annotation releases of the same assembly —
coordinates are never mixed within a track. The script also patches strand (`o`) into
`blocks.json` track members and `gene_context.json` entries from the cached gene lists
(1,044 members + 2,208 context genes across the 14 cached assemblies; other assemblies stay
strandless), enabling strand arrows on panel-only tracks and gene-page context cards, whose
curated-block rows upgrade to detailed windows via `flanks.json`'s `gene_index`.

### Web
- `#/synteny` explorer (nav “Synteny”): searchable block list, species tracks positioned by real
  coordinates, phylogenetic species order, deep links `#/synteny/{block_id}`.
- Gene pages: “Genomic context” card (neighbour mini-tracks) linking to the explorer.

### Regeneration
```bash
pixi run python scripts/genes/export_synteny.py
pixi run python scripts/genes/fetch_synteny_flanks.py   # flanking-gene detail (downloads, cached)
```

---

## 8. Phenotype Table (Mortality Rate)

### Source
- **Merged detection data** from APHIS US (2023-2024) + OAFD US (2022)
- **Method:** Mortality rate = morbidity_mortality_count / total_detections
- **Note:** Italy data excluded (no sampling method information)

### Logic
The sampling method reveals how birds were found:
- **Morbidity/Mortality:** Bird was sick or dead → susceptible
- **Hunter harvest / Live:** Bird was alive when sampled → tolerant (reservoir)

### Generation Command
```bash
pixi run ingest-detections    # First: merge all detection sources
pixi run build-phenotype      # Then: derive phenotype from merged data
```

### Local Files
```
data/
├── phenotype_table.parquet    # 85 species with mortality phenotype
├── phenotype_table.tsv
└── phenotype_table.json       # Full provenance with sources
```

### Phenotype Classes

| Class | Mortality Rate | Interpretation |
|-------|----------------|----------------|
| highly_tolerant | < 5% | Reservoir species (mallard, teal) |
| tolerant | 5-20% | Some disease but mostly survive |
| intermediate | 20-50% | Mixed outcomes |
| susceptible | 50-90% | Often fatal |
| highly_susceptible | ≥ 90% | Almost always fatal (eagles, crows) |

### Results Summary (Multi-Source)

| Phenotype Class | Species | Detections |
|-----------------|---------|------------|
| highly_susceptible | 59 | 9,881 |
| highly_tolerant | 10 | 5,276 |
| tolerant | 5 | 4,647 |
| susceptible | 8 | 1,925 |
| intermediate | 3 | 834 |

**Multi-source validation:** 69 of 85 species have data from both APHIS and OAFD sources.

### Key Species Examples

**Highly Tolerant (reservoirs):**
- Anas crecca (Green-winged teal): 1.9% mortality (n=1,443)
- Spatula discors (Blue-winged teal): 1.8% mortality (n=1,206) [APHIS + OAFD]
- Spatula clypeata (Northern shoveler): 0.5% mortality (n=372) [APHIS + OAFD]

**Highly Susceptible:**
- Branta canadensis (Canada goose): 99.1% mortality (n=2,349) [APHIS + OAFD]
- Coragyps atratus (Black vulture): 99.9% mortality (n=1,322) [APHIS + OAFD]
- Haliaeetus leucocephalus (Bald eagle): 99.9% mortality (n=1,224) [APHIS + OAFD]
- Bubo virginianus (Great horned owl): 100% mortality (n=752) [APHIS + OAFD]

### Gene-Phenotype Overlap

Species with both gene presence AND phenotype data: **18 species**

Key validation:
- All 12 Galliformes lack RIG-I (DDX58) and RNF135 as expected
- 94% of Anseriformes have RIG-I present
- Tolerant ducks have RIG-I; susceptible chickens lack it

---

## 9. Data To Download (Bird Flu Specific)

| Dataset | Value | Requirements | Status |
|---------|-------|--------------|--------|
| **Dryad RLHA HPAI** | 71 GPS-tracked hawks, 11 HPAI deaths | Free Dryad account | TODO |
| **Movebank Griffon Vulture** | 31 vultures during H5N1 outbreak | Permission request | TODO |
| **GISAID** | 23K viral isolates with host metadata | Institutional DAA | TODO |
| **WAHIS (WOAH)** | Official notifications, 180+ countries | Free registration | TODO |
| **EFSA Data Portal** | 276K EU surveillance records/year | Bulk request | TODO |
| **UK DEFRA** | Wild bird detections | Public | TODO |

### To Download (Genomics)

| Dataset | Coverage | Access |
|---------|----------|--------|
| **B10K Project** | 363 annotated genomes | CNGB mirror |
| **NCBI Virus** | Public sequences | Redistributable |
| **BV-BRC** | Bacterial/viral resources | Open |

---

## 10. Linked Resources (External Reference)

These are contextual resources for migration, occurrence, and ecology.
Link to them; don't duplicate.

### Bird Occurrence & Distribution

| Resource | Scale | URL | Use Case |
|----------|-------|-----|----------|
| **GBIF** | 3.1B occurrences | https://gbif.org | Species distribution modeling |
| **eBird** | 500M observations | https://ebird.org | Occurrence, phenology, trends |
| **BirdLife Datazone** | All species | https://datazone.birdlife.org | Range maps, conservation |
| **IUCN Red List** | Global | https://iucnredlist.org | Conservation status |

### Migration & Tracking

| Resource | Scale | URL | Use Case |
|----------|-------|-----|----------|
| **Movebank** | 7,500+ studies | https://movebank.org | Migration routes, flyways |
| **Movebank Data Repository** | Archived datasets | https://datarepository.movebank.org | Published tracking data |
| **USGS Bird Banding Lab** | 77M records | https://usgs.gov/labs/bird-banding-laboratory | Historical movement |
| **Eurasian African Bird Migration Atlas** | Palearctic | https://migrationatlas.org | Old World routes |

### Ecology & Environment

| Resource | Scale | URL | Use Case |
|----------|-------|-----|----------|
| **Breeding Bird Survey** | N. America | https://usgs.gov/bbs | Population trends |
| **Christmas Bird Count** | Americas | https://audubon.org/cbc | Winter distribution |
| **Wetlands International** | Global | https://wetlands.org | Waterbird populations |
| **Ramsar Sites** | Global | https://rsis.ramsar.org | Wetland locations |

### Phylogenetics & Taxonomy

| Resource | URL | Use Case |
|----------|-----|----------|
| **Bird Tree** | https://birdtree.org | Phylogenetic trees |
| **IOC World Bird List** | https://worldbirdnames.org | Taxonomic authority |
| **Avibase** | https://avibase.bsc-eoc.org | Taxonomic synonyms |

### Viral & Epidemiological

| Resource | URL | Use Case |
|----------|-----|----------|
| **Nextstrain Avian Flu** | https://nextstrain.org/avian-flu | Phylogenetics (GISAID-derived) |
| **FluDB (IRD)** | https://fludb.org | Sequence search |
| **EMPRES-i** | https://empres-i.apps.fao.org | Outbreak events — latest layer fetched automatically via the FAO cloud function (`scripts/fetch_empresi.py`; manual browser export as fallback, see `data/raw/external/empresi-latest/README.md`) |

---

## 10a. IUCN Conservation Status

### Source
Wikidata property P141 (IUCN conservation status) via the Wikidata Query
Service SPARQL endpoint — an open mirror of the IUCN Red List categories.
(The official IUCN API needs a token; GBIF's `iucnRedListCategory` is no
longer populated.) Names from `species_index.json` are matched against
P225 taxon names; unmatched names (genus splits, e.g. *Astur* vs
*Accipiter*) get a second pass hopping the P1420 synonym link.

### Generated Output (web/public/data/species, not in git)
| File | Content | Size |
|------|---------|------|
| `iucn_status.json` | `{status: {sci: LC|NT|VU|EN|CR|EW|EX|DD}, meta}` — 683/718 species (95.1%): 560 LC, 47 NT, 44 VU, 32 EN | 19 KB |

Unmatched are domestic taxa (Bos taurus, Capra hircus — genuinely Not
Evaluated) plus rare splits without synonym wiring on Wikidata.
Best statement wins per species: preferred rank → latest assessment date
(P585) → most severe category.

### Regeneration
```bash
pixi run python scripts/species/fetch_iucn_status.py   # ~8 SPARQL queries, ~30 s
```

## 10b. ANP32 Species-Barrier Comparison

### Source
Birds: OrthoFinder OG MSAs (`orthofinder/…/Results_Aves463_Root16/MultipleSequence
Alignments/OG0004189|OG0003684|OG0006217.fa`, ungapped, one entry per species).
Mammals: every HPAI-confirmed mammal with a genome (49 species from
`detected_mammals.json`) — ANP32A/B/E protein FASTAs via the NCBI `datasets`
CLI, cached slim under `data/anp32/cache/`. References: UniProt human
ANP32A/B/E (P39687 / Q92688 / Q9BTT0).

### Method
Insert = span excess between conserved flanking windows of the human reference
(18-aa windows, ≤2–3 mismatches; junction site picked by scanning for the max
bird-span excess). Exact residues extracted by removing the conserved middle;
Needleman–Wunsch merged-gap fallback for divergent sequences. The acidic
duplication routinely splits the NW gap run — runs <6 residues apart are merged.

### Generated Output (web/public/data/anp32, not in git)
| File | Content |
|------|---------|
| `comparison.json` | per-species ANP32A/B/E protein length, insert length / start / sequence (+fragment flag); per-paralog histograms; human references |

### Regeneration
```bash
pixi run python scripts/genes/export_anp32_comparison.py   # ~20 min first run (mammal protein downloads, cached)
```

## 10c. Static BLAST reference database + WASM kernel

### Source
`data/blast/panel_refs.json` — one protein per (gene × key species), the
longest sequence of that species in the gene's orthogroup FASTA
(OrthoFinder results, same source as the orthogroup MSAs). Priority
species: chicken, mallard, turkey, zebra finch, quail, swan goose,
white-tailed eagle, kiwi.

### WASM kernel
`web/wasm-blast` — Rust crate (wasm-pack, target web): Smith-Waterman with
BLOSUM62, affine gaps 11/1 (NCBI blastp defaults), Karlin-Altschul
E-values (λ = 0.267, K = 0.041). Runs in a web worker
(`web/src/workers/blast.worker.js`); the compiled wasm is committed at
`web/src/wasm/blast/` so the site builds without a Rust toolchain.

### Generated Output (web/public/data/blast, not in git)
| File | Content |
|------|---------|
| `panel_refs.json` | 2,990 sequences · 799 genes · 27 species (~1.9 MB) |

### Regeneration
```bash
pixi run python scripts/genes/export_blast_refs.py
(cd web/wasm-blast && wasm-pack build --target web --release &&
 cp pkg/roost_blast.js pkg/roost_blast_bg.wasm ../src/wasm/blast/)
```

## 10d. Species Trait Capture (internal workbench)

Long-format trait table assembled from deterministic sources, ready for the
paper-processing phase to fill the remaining (LLM-extracted) traits. Not
exported to the web — internal analysis only.

### Generated Output (data/, not in git)
| File | Content |
|------|---------|
| `species_traits.parquet` | 4,913 rows · 829 species × 11 filled traits: scientific_name, taxon_id, trait, value, value_type, basis, confidence, evidence |
| `species_traits_wide.csv` | one row per species, one column per trait |
| `species_trait_registry.json` | all 22 trait definitions, value types, fill status (11 filled / 11 pending paper extraction) |

### Traits filled deterministically
`hpai_detected` (829 species, with detection counts/span/geography),
`h5n1_subtype_detected` (475 — subtypes from the strain field; clade detail needs
papers), `detection_span_years`, `reservoir_status` (heuristic: 38 suspected
reservoirs incl. mallard/mute swan/greylag; 312 recurrent; 479 sporadic),
`susceptibility_class` + `predicted_susceptibility_score` (701, joined from the
susceptibility model), `tolerance_class` / `mortality_proportion` /
`mortality_score` / `field_mortality_evidence` (111, from the mortality phenotype
table), `hpai_severe_outcome` (92 yes / 13 no, derived: susceptible-class +
mortality ≥ 50%, or tolerant-class + mortality < 20%).

### Traits pending the paper phase
`h5n1_clade_subtype`, `experimental_challenge_available`, `serology_evidence`,
`clinical_score`, `viral_load_score`, `shedding_score`, `shedding_duration_days`,
`shedding_titre`, `low_replication_class`, `low_susceptibility_comparator`,
`reservoir_class` — schema and value types declared in the registry; extraction
source: `data/papers/analyses/*.json` (`species_detections` fields).

### Regeneration
```bash
pixi run python scripts/build_species_traits.py
```

## 10e. Paper Database (internal workbench)

One ripgrep pass over the 1,083-paper markdown corpus (docs/papers_md,
~67 MB) produces a queryable per-paper database for the trait-mining /
LLM-processing phase.

### Generated Output (data/papers, not in git)
| File | Content |
|------|---------|
| `paper_db.parquet` | 1,083 papers × [id, title, authors (list), journal, year, doi, url, paper_type, category, topics, summary, language_guess, n_genes, genes (list), gene_hits (JSON), strains (JSON), species (list, from LLM analyses), analysis_available, chars] |
| `paper_db_meta.json` | build stats, pattern rules, exclusion lists |

Key fields:
- **gene_hits**: per gene {n, snippets[]} — snippet = the FULL matched
  paragraph (uncapped per research decision; lines truncated only at 4,000
  chars for table dumps). This is the LLM feed: process a gene in a paper
  without ingesting the whole paper. 514 papers carry panel-gene mentions
  across 504 distinct genes (top: CD4 143, CD8 137, GAPDH 98, MX1 92,
  TLR3 84…).
- **strains**: clades (2.3.4.4b…) + subtypes (H5N1…) with counts and first
  context snippet — 1,009 papers — the detection-strain evaluation base.
- **paper_type** (deterministic heuristics): scientific_published 831,
  government 86, other 145, scientific_preprint 18, thesis 3.
- Matching rules: case-sensitive; symbols + curated protein aliases
  (RIG-I→DDX58, MDA5→IFIH1, PKR→EIF2AK2…); mouse-style Title variants
  (Ddx58, Ifih1) except English-colliding forms (Kit, Jun…); 2-char
  FP-prone symbols (C, II, BF, BG) and viral segment names (HA/NA/NP/PA)
  not grepped.

### Regeneration
```bash
pixi run python scripts/papers/build_paper_db.py
```

## 10f. New-Paper Intake + LLM Enrichment (internal workbench)

Two-stage pipeline for papers dropped into `pdfs_to_process/`:

**Stage 1 — deterministic** (`scripts/papers/process_new_papers.py`):
PDF → markdown + Crossref metadata (DOI from text) → registration in
papers.json → regex candidates (mutations, n=, geography) → template social
snippet → `data/papers/paper_extras.parquet`. Junk/off-topic/weak-metadata
PDFs routed to `_deferred/` with intake-ledger reasons. Junk routing found
3 off-topic, 3 fragments, 3 needing manual metadata in the first 45-PDF run.

**Stage 2 — LLM** (`scripts/papers/llm_enrich_new_papers.py`): 7 focused
full-text queries per paper against muse-glimmer-30b (127.0.0.1:8005, sglang,
131k context) at 48-way concurrency — categorize (study_type + host_taxa +
setting), summarize (→ papers.json / Papers page), effect directions
({exposure, outcome, direction, evidence}), mutation gene-attribution,
sample-size hashmap ({total_n, groups, hosts, time_span}), gene involvement
(studied/perturbed/measured + finding + quote — the gene-page / pathway-
annotation feed), and the social snippet (author et al. + year + DOI link,
≤270 chars, queued in `social_queue.jsonl`). Deterministic originals kept as
`*_deterministic`; provenance in `llm_provenance.json`.

First run: 45 PDFs → 33 papers registered (+ History `papers_added` event),
231 LLM queries (15 errors retried-safe): summaries 33/33, sample hashmaps
33/33, social 33/33; effect directions / gene involvement / mutations filled
where applicable (3 / 6 / 6 papers — the rest genuinely have none).

## 10f. Autonomous Research Agent (internal workbench)

A pi-like research agent platform: the LLM is the orchestrator, choosing
which tool to invoke next based on what it's learned. Not a fixed pipeline.

### Architecture
```
research_agent.py (scripts/papers/)
├── ToolRegistry (12 declarative tools + 7 aliases)
│   ├── search_corpus       — extraction tables (findings, mechanisms, quantitative)
│   ├── find_related        — citation chaining across genes/species/clades/methods/concepts
│   ├── query_field         — detections + mortality patterns
│   ├── get_model           — pathway mechanism edges
│   ├── get_gene_evidence   — per-gene literature card
│   ├── query_species_traits — species tolerance/susceptibility
│   ├── check_contradictions — adjudicated conflicts
│   ├── check_disagreements  — explicit paper-vs-paper disputes
│   ├── get_paper_detail    — paper metadata
│   ├── search_web          — searxng (graceful degradation)
│   ├── search_wikipedia    — Wikipedia API for background
│   └── search_external     — searxng (alias for search_web)
│
│   Aliases (LLM-invented names → real tools, with teaching notes):
│     pubmed_search → search_web, search_papers → search_corpus,
│     gene_evidence_summary → get_gene_evidence, etc.
│   Unknown tool → returns list of available tools (agent self-corrects)
│
├── SkillRegistry (8 investigation patterns, like pi skills)
│   ├── contradiction_investigation — root-cause a literature conflict
│   ├── evidence_synthesis    — totality of evidence on a topic
│   ├── gene_deep_dive        — everything about one gene
│   ├── species_comparison    — compare 2-5 species on a trait
│   ├── gap_assessment        — what's missing in the field
│   ├── hypothesis_generation — what should we test next?
│   ├── outbreak_investigation — what happened at a specific event?
│   └── (all skills provide domain-specific protocols as system hints)
│
├── CallRecorder (persistent parquet: data/papers/research_agent_calls.parquet)
│   └── every tool call: briefing, iteration, tool, args, n_results,
│       duration_ms, timestamp — queryable across all briefings
│
├── Agent Loop (LLM-directed, not a fixed pipeline)
│   ├── PHASE 1: INVESTIGATE — agent chooses tools, chains into related papers
│   ├── PHASE 2: SYNTHESIZE — draft the briefing (clean prose, paper citations)
│   ├── PHASE 3: SELF-ASSESS — "what did I miss? what questions arose?"
│   │   └── classifies meta-questions: "this_report" vs "own_briefing"
│   ├── PHASE 4: DECIDE — "done" OR "refine" (targeted gap investigation)
│   │   └── up to 3 refinement rounds; gap reports also assessed
│   └── Auto-compact every 4 iterations (summarise evidence, keep bounded)
│
├── Question Scoring (score_open_questions.py)
│   └── batched LLM scoring of ~4,974 open questions on:
│       importance (40%), feasibility (30%), data_availability (30%)
│       → scored_questions.parquet (queryable, sorted)
│
├── Autonomous Mode (--autonomous N)
│   └── reads scored_questions.parquet, picks top N, investigates
│       without human question selection
│
├── Sub-briefing Spawning (--spawn-subbriefs)
│   └── meta-questions marked "own_briefing" investigated as children
│       parent slug stored in _parent field; max 3 per run
│
└── Paper Discovery (--discover-papers)
    └── web search results checked against papers.json titles
        novel papers → data/papers/discovered_papers.jsonl for intake
```

### Outputs
- `web/public/data/research_briefings/{slug}.json` — structured briefing:
  title, summary, sections (with [paper_id] citations that render as
  links), hypotheses (testable, evidence for/against, confidence),
  research_plan (studies with feasibility), key_contradictions,
  unresolved questions, data_gaps, meta_questions (classified by scope),
  agent_trace (tool calls, refinement history)
- `web/public/data/research_briefings/index.json` — auto-generated index
- `web/public/data/research_briefings/` rendered at `#/research/{slug}`
  (full page with linked citations, hypothesis cards, research plan,
  collapsible evidence trail with color-coded tool table)
- `data/papers/scored_questions.parquet` — all open questions ranked
- `data/papers/research_agent_calls.parquet` — persistent call history
- `data/papers/discovered_papers.jsonl` — papers found via web search

### Usage
```bash
# freeform question
pixi run python scripts/papers/research_agent.py --question "Why do ducks survive H5N1?"

# skill-based (pre-configured investigation pattern)
pixi run python scripts/papers/research_agent.py \
  --skill gene_deep_dive --params "gene=ANP32A"

# from scored open questions
pixi run python scripts/papers/research_agent.py --top-open 5

# fully autonomous (agent picks its own questions)
pixi run python scripts/papers/research_agent.py \
  --autonomous 5 --spawn-subbriefs --discover-papers

# score all open questions first (required for --autonomous)
pixi run python scripts/papers/score_open_questions.py
```

### Self-assessment and refinement
The agent critiques its own synthesis:
- "Nah, this is great and addresses the question sufficiently" → DONE
- "These specific gaps remain" → REFINE (targeted tool calls for each gap)
- Gap reports (insufficient evidence) are reported as findings, not
  failures — with "what's missing" and "what data would fill it"

### Meta-question classification
Questions that arise during synthesis are classified:
- `this_report` (↳ blue) — sub-detail, belongs in the current briefing
- `own_briefing` (→ purple) — its own research question, worth investigating
  separately (auto-spawned with --spawn-subbriefs)

### Future enhancements (not built)
- Scheduled re-assessment: re-run briefings when new papers arrive
- Multi-agent collaboration: two agents on the same question from different
  angles
- Paper auto-intake: discovered papers automatically downloaded and
  processed
- Interactive mode: human guides the agent mid-investigation

## 11. Known Data Gaps

### Geographic Coverage
- **Africa:** Limited detection data outside South Africa
- **South America:** 104 species in WOAH notifications, not yet downloaded
- **Asia:** GISAID has coverage, but requires registration
- **Oceania:** Scattered national reports

### Temporal Coverage
- **Pre-2020:** Limited to EMPRES-i linked dataset (2012-2021)
- **2024-2026:** Most active outbreak period, good coverage

### Data Type Gaps
- **Pathology reports:** Tissue tropism, lesion data
- **Experimental infections:** Challenge study outcomes
- **Environmental samples:** Water, sediment testing
- **Poultry farm data:** Commercial flock outcomes

---

## Data Flow Diagram

```
NCBI Taxonomy (taxdump.tar.gz)
         │
         ▼
    parse_taxonomy.py
         │
         ▼
   aves_taxonomy.tsv ──────────────┐
                                   │
NCBI Datasets (Aves genomes)       │
         │                         │
         ▼                         ▼
   avian_genome_core.tsv ──► build_species_table.py
                                   │
                                   ▼
                           species_table.parquet
                           genomes.parquet
                                   │
                                   │
APHIS CSV ─────┐                   │
               ├──► ingest_detections.py
OAFD Zenodo ───┤           │
               │           ▼
Italy OAFD ────┘   detections_merged.parquet
                           │
                           ▼
                   build_phenotype_table.py
                           │
                           ▼
                   phenotype_table.parquet
                                   │
Expression (hardcoded) ────────────┤
                                   │
                                   ▼
                        build_coverage_matrix.py
                                   │
                                   ▼
                        coverage_matrix.parquet
```

---

## Versioning

| Date | Event | Records | Sources |
|------|-------|---------|---------|
| 2026-08-26 | Add UK DEFRA 2024-2026, fix deduplication | 20,669 | 8 |
| 2026-08-20 | Add GPS telemetry, HPAI tracking, ACAP seabirds | 20,477 | 7 |
| 2026-08-19 | Initial multi-source merge | ~10,000 | 3 |

---

## Validation Checksums

Generate with: `md5sum data/*.parquet`

```
# Run after build to verify:
pixi run python -c "
import polars as pl
cm = pl.read_parquet('data/coverage_matrix.parquet')
print(f'Species: {len(cm)}')
print(f'With genome: {cm.filter(pl.col(\"has_genome\")).height}')
print(f'With detection: {cm.filter(pl.col(\"has_detection\")).height}')
"
```

Expected output:
```
Species: 11284
With genome: 1979
With detection: 170
```
