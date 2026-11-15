# Data Inventory

> Comprehensive inventory of all data holdings in the Roost project.
> **Last updated:** 2026-08-26

---

## Quick Stats

| Metric | Value |
|--------|-------|
| **Total Detection Records** | 20,669 |
| **Unique Species (raw names)** | 666 |
| **Species Mapped to NCBI** | 297 |
| **Countries Covered** | 116 |
| **Georeferenced Records** | 7,312 (35.4%) |
| **Species Profiles** | 11,284 total, 296 with detections |
| **Data Sources** | 8 active (22 registered) |

---

## Detection Data by Source

| Source | Records | Species | NCBI Mapped | Countries | Date Range | Coords | Official URL |
|--------|---------|---------|-------------|-----------|------------|--------|--------------|
| **aphis_us** | 9,696 | 182 | 170 | 1 (USA) | 2023-01-10 to 2024-09-09 | 0% | [USDA APHIS](https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv) |
| **sdm_hpai** | 6,629 | 231 | 132 | 45 | 2005-11-21 to 2024-04-19 | 100% | [GitHub SDM](https://github.com/sarahhayes/avian_flu_sdm) |
| **empresi_linked** | 1,862 | 110 | 112 | 69 | 2004-01-10 to 2022-11-03 | 0% | [Recherche Data Gouv](https://doi.org/10.57745/JNA7N9) |
| **uk_defra** | 1,463 | 89 | 56 | 1 (UK) | 2024-W01 to 2026-W33 | 0% | [GOV.UK](https://www.gov.uk/government/publications/avian-influenza-in-wild-birds) |
| **canada_cwhc** | 685 | 68 | 28 | 1 (Canada) | 2022-04-20 to 2026-03-04 | 100% | [ArcGIS Dashboard](https://cfia-ncr.maps.arcgis.com/apps/dashboards/89c779e98cdf492c899df23e1c38fdbc) |
| **italy_wild** | 180 | 37 | 33 | 1 (Italy) | 2021-10-30 to 2023-07-19 | 0% | [Zenodo OAFD](https://zenodo.org/records/8246456) |
| **iceland_usgs** | 115 | 20 | 18 | 1 (Iceland) | 2010-09-05 to 2011-10-14 | 0% | [USGS ScienceBase](https://doi.org/10.5066/P9ZJKQHU) |
| **oafd_us_2022** | 39 | 21 | 21 | 1 (USA) | 2022-01-26 to 2022-09-30 | 0% | [Zenodo OAFD](https://zenodo.org/records/8246456) |

---

## Source Provenance Details

### USDA APHIS (aphis_us)
- **Full Name:** USDA APHIS Wild Bird HPAI Detections
- **Type:** Official government data
- **Update Frequency:** Weekly during outbreaks
- **License:** Public domain (US Government)
- **Key Fields:** State, County, Date Detected, HPAI Strain, Bird Species, Sampling Method
- **Sampling Types:** Mortality (55%), Harvest (32%), Live (13%)
- **Notes:** Primary source for US wild bird detections since Jan 2023

### SDM HPAI (sdm_hpai)
- **Full Name:** Species Distribution Modeling HPAI Wild Bird Detections
- **Type:** Research compilation (FAO EMPRES-i + WOAH WAHIS)
- **DOI:** N/A (GitHub research repository)
- **Coverage:** 47 countries, primarily Europe
- **Coordinates:** EPSG:3035 converted to WGS84
- **Notes:** Best global georeferenced dataset for pre-2024 data

### UK DEFRA (uk_defra)
- **Full Name:** UK DEFRA/APHA Wild Bird AI Findings
- **Type:** Official government data
- **Update Frequency:** Weekly
- **Files:** 2024, 2025, 2026 annual Excel files
- **Key Fields:** Week, District, County, Species, Latin Name, Virus Isolated
- **Notes:** High-quality recent UK data (2024-present)

### Canada CWHC (canada_cwhc)
- **Full Name:** Canadian Wildlife Health Cooperative HPAI Dashboard
- **Type:** Official national wildlife health monitoring
- **Data Source:** ArcGIS FeatureServer export
- **Coordinates:** Full coverage (100%)
- **Notes:** Weekly updates, excellent coordinate data

### EMPRES-i Linked (empresi_linked)
- **Full Name:** FAO EMPRES-i Linked Epidemiological and Genomic Data
- **DOI:** 10.57745/JNA7N9
- **Type:** Research dataset linking events to sequences
- **Coverage:** Global, 69 countries
- **Notes:** Historical data 2004-2022, links to GISAID sequences

### Italy Wild (italy_wild)
- **Full Name:** Italy HPAI Wild Bird Detections
- **Type:** National surveillance via Open Avian Flu Dataset
- **DOI:** 10.5281/zenodo.8246456
- **Notes:** 2021-2023 seasons, no sampling type info

### Iceland USGS (iceland_usgs)
- **Full Name:** USGS Iceland AIV Surveillance
- **DOI:** 10.5066/P9ZJKQHU
- **Type:** Research surveillance study
- **Coverage:** 2010-2018, pre-HPAI outbreak
- **Notes:** 381 positives, all live-capture sampling

### OAFD US 2022 (oafd_us_2022)
- **Full Name:** Open Avian Flu Dataset - US Wild Birds 2022
- **DOI:** 10.5281/zenodo.8246456
- **Type:** Community-curated compilation
- **Notes:** Early 2022 US outbreak data (pre-APHIS tracking)

---

## Registered Sources (Not Yet Loaded)

These sources are registered in `scripts/sources.py` but require manual download or authentication:

| Source ID | Name | Reason |
|-----------|------|--------|
| gisaid | GISAID Avian Influenza | Requires institutional DAA |
| dryad_rlha | Dryad RLHA Hawk Tracking | Requires Dryad account |
| movebank_griffon | Movebank Griffon Vulture | Permission request needed |
| ebird | eBird Observations | API key required |
| vs_surveillance | VS Wild Bird Surveillance | Loaded but excluded (no species-level data) |
| acap_hpai | ACAP Seabird Database | Available, not integrated |
| owid_h5n1_human | OWID H5N1 Human Cases | Surveillance only, not wild bird detections |

---

## Output Files

### Detection Data
```
data/
├── detections_merged.parquet    # 20,669 records (deduplicated)
├── detections_merged.tsv        # TSV export
├── detections_provenance.json   # Full source metadata
└── deduplication_stats.json     # Deduplication statistics
```

### Species Profiles
```
data/
├── species_profiles.parquet           # 11,284 species (all Aves)
├── species_profiles_detected.parquet  # 296 species with detections
├── species_profiles_detected.tsv      # TSV export
├── species_profiles_complete.tsv      # 67 species with full data
└── species_profiles_summary.json      # Summary statistics
```

### Analysis Outputs
```
data/
├── analysis/                    # Extended analysis results
├── geojson/                     # Geographic layers
├── species_sheets/              # Per-species JSON files
└── summary/                     # Publication-ready tables
```

---

## Data Quality Notes

### Deduplication
- Original records: 52,794
- After deduplication: 20,669
- Removed: 32,125 (60.8%)
- Method: Near-duplicate detection by species + date + location

### Species Harmonization
- Raw species names: 666
- Mapped to NCBI taxonomy: 297 (45%)
- Uses `aves_taxonomy.tsv` (11,284 species)

### Geographic Coverage
- 116 countries represented
- 35.4% of records are georeferenced
- Best coverage: SDM HPAI (100%), Canada CWHC (100%)

### Temporal Coverage
- Earliest record: 2004-01-10 (EMPRES-i)
- Latest record: 2026-W33 (UK DEFRA)
- Peak detection years: 2022-2024 (H5N1 clade 2.3.4.4b pandemic)

---

## Versioning

| Date | Event | Records | Sources |
|------|-------|---------|---------|
| 2026-08-26 | Added UK DEFRA 2024-2026, OWID human cases | 20,669 | 8 |
| 2026-08-20 | Initial multi-source merge | 20,477 | 7 |
| 2026-08-19 | Initial build with APHIS only | ~10,000 | 1 |

---

## Regeneration Commands

```bash
# Full pipeline
pixi run fetch              # Download latest data
pixi run ingest-detections  # Merge all sources
pixi run deduplicate        # Remove duplicates
pixi run build-profiles     # Build species profiles
pixi run susceptibility     # Calculate scores
pixi run export-geojson     # Export maps
pixi run species-sheets     # Per-species data
pixi run summary-stats      # Summary tables
```

---

## License Information

| Source | License | Redistribution |
|--------|---------|----------------|
| APHIS US | Public Domain | Yes |
| UK DEFRA | OGL v3.0 | Yes |
| Canada CWHC | Open Government License | Yes |
| SDM HPAI | Academic use | Check with authors |
| OAFD/Zenodo | CC-BY-4.0 | Yes with attribution |
| EMPRES-i Linked | Research dataset | Check with authors |
| USGS | Public Domain | Yes |
