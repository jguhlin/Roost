# Data Catalog

This document catalogs all public data sources relevant to avian influenza host genomics, organized by type and annotated with access method, redistribution rights, and update frequency.

---

## 1. Viral Sequences & Outbreak Notifications

### 1.1 BV-BRC / NCBI Virus (Primary Backbone)

**What:** Viral genome sequences with host species, date, location metadata.

**Why primary:** Openly redistributable. GISAID is larger but prohibits redistribution, constraining architecture. BV-BRC/NCBI Virus is the backbone precisely because it can be rehosted.

**Access:**
- NCBI Virus: https://www.ncbi.nlm.nih.gov/labs/virus/vssi/
- BV-BRC: https://www.bv-brc.org/

**Download:** Bulk FASTA + metadata TSV. Filter by Influenza A, H5 subtype, avian hosts.

**Update frequency:** Weekly sync recommended.

**Prior art:** The EMPRES-i × BV-BRC linkage (doi:10.57745/JNA7N9) proves the join to outbreak data works.

---

### 1.2 WOAH WAHIS

**What:** Official animal disease notifications. Event-level: species affected, counts, dates, locations.

**Access:** https://wahis.woah.org/

**Download:** Export interface; structured but requires cleanup.

**Coverage:** Global, official notifications only. Undercounts by ~1-2 orders of magnitude vs literature.

**Update frequency:** As notifications arrive; check weekly.

---

### 1.3 FAO EMPRES-i+

**What:** Global Animal Disease Information System. Outbreak events with species and geographic data.

**Access:** https://empres-i.apps.fao.org/

**Download:** CSV/Excel exports available.

**Coverage:** Overlaps WAHIS but uses different event granularity.

**Note:** The three-source discrepancy (EMPRES-i: 8,928 / WAHIS: 141,651 / literature: 1,285,036 dead wild birds) means reconciliation is required.

---

### 1.4 USDA APHIS Wild Bird Detections

**What:** US wild bird H5N1 detections. Dense, tabular, well-structured.

**Access:** https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza/hpai-detections/wild-birds

**Download:** Direct table download.

**Coverage:** US only, but high quality within that scope.

**Update frequency:** Weekly during active surveillance.

---

### 1.5 National Agency Pages

Heterogeneous quality. Scrape and curate.

| Agency | Country | URL | Format |
|--------|---------|-----|--------|
| MPI | New Zealand | mpi.govt.nz | HTML/PDF |
| Wildlife Health Australia | Australia | wildlifehealthaustralia.com.au | Reports |
| DEFRA/APHA | UK | gov.uk | Tables/PDF |
| CFIA | Canada | inspection.canada.ca | Tables |

---

### 1.6 EFSA/ECDC Quarterly Reports

**What:** European avian influenza situation reports.

**Access:** https://www.efsa.europa.eu/ (search "avian influenza overview")

**Download:** PDF with tabular annexes. Manual extraction required for some data.

**Update frequency:** Quarterly.

---

### 1.7 Nextstrain Avian Flu Builds

**What:** Phylogenetic builds from GISAID data. 8 segments × 4 subtypes.

**Access:** https://nextstrain.org/avian-flu

**Source:** https://github.com/nextstrain/avian-flu

**Use:** Visualization and clade assignment, not primary data. Link out, don't rehost.

---

### 1.8 iNaturalist Wildlife Mortality

**What:** Citizen science observations including dead birds. Near-real-time.

**Access:** https://www.inaturalist.org/

**Relevance:** A workflow built on iNaturalist detects H5N1 mass mortality events across Canada/US (biorxiv 2025.08.08.669145). Noisy but catches events that never enter official channels.

**Use:** Supplementary signal, not primary source.

### 1.9 South Africa OCIMS Seabird AI Response (INGESTED 2026-08)

**What:** Per-record seabird stranding/response data from the DEA/OCIMS avian
influenza reporting system — Cape cormorant crisis 2021 → present. Species,
counts, condition, coordinates, province.

**Access:** ArcGIS FeatureService (public):
https://services6.arcgis.com/FGcnAbfUGHEZZ7XP/arcgis/rest/services/AffectedBirds20260821/FeatureServer/2
Discovered via the "Seabird Response" dashboard item config (Sharing API):
https://dea-surveys.maps.arcgis.com/apps/dashboards/608a9c99f45c4be38bd7240cd853c113

**Coverage:** ~1.9k records, Oct 2021 → Aug 2026, actively updated. Surveillance
(strandings), not per-record lab confirmation — pair with FAO events (1.10).

**Registered:** `sa_ocims_strandings` (incremental via date filter).

### 1.10 FAO Situation Updates — Global + Sub-Saharan Africa (INGESTED 2026-08)

**What:** Confirmed HPAI events per country (admin regions, last-outbreak date,
event totals with W/wildlife + M/mammal breakdowns, species affected).

**Pages (same table schema, both parsed by `scripts/add_fao_detections.py`):**
- Global AIV with zoonotic potential (26 countries: Europe, Asia, Americas,
  Africa; `fao_global_aiv`)
- Sub-Saharan Africa (`fao_ssa_hpai`)

**Validation:** FAO global NZ row (2 events, Brown skua + Swamp harrier) exactly
matches our NZ-DOC records. 75 records across 20 countries → supplement
`data/manual/fao_detections.json`.

**Coverage caveats (verified 2026-08-30):** Chile/Colombia/Peru rows list only
generic species ("Non-poultry birds"/poultry) — no species-level records
possible; China, Russia, Uganda absent (no events reported in the current
window).

### 1.11 WOAH WAHIS — Avian Influenza Events (INGESTED 2026-08, public API)

**What:** Official immediate notifications + follow-ups: ~2k avian influenza
events globally (HPAI poultry / non-poultry incl. wild birds / bovine), each
with per-species case/death totals (wild flag), outbreak counts + coordinates,
lab results, event dates and resolution status. The systematic layer for
China, Russia, South America, Uganda — every WOAH member country.

**Access — no registration needed.** The SPA at wahis.woah.org uses a public
API (`/api/v1/pi/*` = "public interface"):
- `POST /api/v1/pi/event/filtered-list?language=en` — event list with filters
  (`firstDiseases` IDs: **668** HPAI poultry, **671** HPAI non-poultry/wild,
  **922** bovine HPAI; pageSize up to 500)
- `GET /api/v1/pi/disease/first-level-filters` — disease catalog with IDs
- `GET /api/v1/pi/review/event/{eventId}/all-information` — full detail
  (species totals in `quantitativeData.totals[]`, outbreaks with lat/long).
  **This route only returns data from a real browser context** — the harvester
  runs it via in-page fetch() in headless Chromium.

**Scripts:** `fetch_wahis_events.py` (harvest, incremental by reportId,
per-batch checkpointing) → `add_wahis_detections.py` (supplement builder,
species mapping via taxonomy common names + alias table) →
`data/manual/wahis_detections.json`.

**Registered:** `woah_wahis`, wired into `pixi run refresh`.

### 1.12 Russia — Rosselkhoznadzor HPAI Chronology (candidate, OCR required)

**What:** Official epizootic situation reports, 284 dated entries (2023 → present,
monthly-ish) covering H5N1 in poultry and wild ornithofauna.

**Access:** https://fsvps.gov.ru/jepizooticheskaja-situacija/rossija/jepidsituacija-po-ptichemu-grippu-v-rossijskoj-federacii/hronologija-po-ptichemu-grippu/

**Blocker:** entries link to JPG/PDF situation maps — no structured data;
requires OCR or manual transcription. Russian-language.

### 1.13 China region (partial)

- **Hong Kong AFCD**: press releases of H5-positive wild birds
  (afcd.gov.hk — reachable; listing is frameset-based, needs JS or a
  press-release parser).
- **Mainland MARA (mara.gov.cn)**: connection refused from this network;
  reports channel is via WOAH WAHIS.
- **Taiwan BAPHIQ**: connection refused.
- Current holdings: 72 records (HKG 47 / CHN 19 / TWN 6, mostly archived
  EMPRES-i 2012-21).

### 1.14 USGS WHISPers (INGESTED 2026-08)

**What:** Lab-confirmed HPAI wildlife mortality events from the USGS Wildlife
Health Information Sharing Partnership — 842 events (H5N1/H5N2/H5N8/H5/NOS),
species with latin names + TSN, affected counts, county/state, dates.

**Access:** public DRF JSON API — https://whispers.usgs.gov/api/eventsummaries/?diagnosis={id}
HPAI diagnosis IDs: 22 (NOS), 660 (H5N1), 661 (H5N2), 662 (H5N8), 685 (H5).

**Registered:** `usgs_whispers`; fetched + supplement built by
`scripts/fetch_whispers_events.py` (wired into `pixi run refresh`).
1,301 records after dedup, 48 states, 96% species auto-mapped.

**Note:** confirmed-AI diagnoses lag mortality events by months (events sit
as "Pending" first) — freshness threshold set to 150 days.

### 1.15 Manual supplements (data/manual/)

Curated records that enter the pipeline as a first-class source via
`load_manual_supplements()` in ingest_detections.py — they survive pipeline
rebuilds (the legacy add_* scripts that wrote into the parquet directly did
not). Currently: `nz_doc_detections.json` (3), `aus_daff_detections.json`
(205), `fao_ssa_detections.json` (20). Add new curated data here, not by
editing parquet files.

---

## 2. Host Genomes & Comparative Genomics

### 2.1 Bird 10,000 Genomes (B10K)

**What:** 363 annotated avian genomes covering ~92% of bird families.

**Access:**
- Portal: https://b10k.genomics.cn/
- Data mirror: CNGB (db.cngb.org)

**Key papers:** Feng et al., Nature 2020; Stiller et al. 2024

**Download:** Bulk genome downloads available. Phase II released.

**Use:** Backbone for cross-species comparative work.

---

### 2.2 Vertebrate Genomes Project (VGP)

**What:** High-contiguity, trio-binned assemblies. Quality standard above B10K.

**Access:**
- https://vertebrategenomesproject.org/
- Genome Ark: https://genomeark.org/

**Key assembly:** Chicken GRCg7b (contig N50 18.83 Mb, scaffold N50 90.86 Mb).

**Download:** Per-species from GenBank/Genome Ark.

**Use:** Reference-quality assemblies where available; preferred over B10K drafts.

---

### 2.3 NCBI Genome Datasets

**What:** Assembly metadata for all deposited genomes.

**Access:** https://www.ncbi.nlm.nih.gov/datasets/

**Download:** Bulk metadata via datasets CLI or direct download. Per-taxon queries.

**Fields:** Accession, assembly level (chromosome/scaffold/contig), contig N50, annotation status.

**Update:** Download full inventory, then periodic diff checks.

---

### 2.4 Ensembl / RefSeq Annotations

**What:** Gene annotations for chicken (GRCg7b) and limited other birds.

**Chicken stats:**
- Ensembl: ~17,007 protein-coding genes
- RefSeq: ~18,022 protein-coding genes
- GEGA enriched atlas: 24,102 PCGs + 44,428 lncRNAs (NAR Genomics 2024)

**Download:** GTF/GFF from Ensembl FTP or NCBI.

**Use:** Chicken as functional-annotation anchor; project to other species.

---

### 2.5 T2T / Near-Complete Assemblies

**What:** Telomere-to-telomere assemblies recovering "missing" microchromosomal genes.

**Available:** Silkie chicken, Mallard (2024/2025; PMC11745021)

**Relevance:** Several immune genes sit in GC-rich, poorly-assembled regions. T2T assemblies recover them.

---

### 2.6 Orthology Databases

| Database | Use | Caveat |
|----------|-----|--------|
| OrthoDB | Orthogroup assignment | Breaks down for rapidly-evolving immune families |
| OMA | Orthology inference | Same caveat |
| Ensembl Compara | Vertebrate orthology | Chicken-centric; limited bird coverage |

**Important:** One-to-one orthology fails precisely for the genes that matter (MHC, IFITM, interferons, defensins, NLRs). Build orthogroups, not 1:1 mappings.

---

## 3. Immune Gene Resources

### 3.1 Avian Immunome Database (Avimm)

**What:** >1,000 chicken immune genes with synonyms, annotations, sequences mapped across B10K genomes.

**Access:** https://avimm.ab.mpg.de/ (check current URL)

**Paper:** Bhogal et al., BMC Bioinformatics 2020 (PMC7661159)

**Use:** Seed the immune-gene target list. Not complete; treat as starting point.

---

### 3.2 IPD-MHC

**What:** MHC sequence database including chicken MHC-B haplotypes.

**Access:** https://www.ebi.ac.uk/ipd/mhc/

**Relevance:** B21 (protective) and B13 (susceptible) haplotype sequences. Anseriformes MHC sparsely characterized.

---

### 3.3 OMIA (Online Mendelian Inheritance in Animals)

**What:** Catalogued animal genetic traits.

**Relevant entry:** OMIA:001534-9031 (chicken Mx1 resistance/susceptibility)

**Use:** Cross-reference claimed resistance alleles.

---

## 4. Functional Genomics (Chicken-Centric)

### 4.1 ChickenGTEx (FarmGTEx)

**What:** 7,015 bulk RNA-seq, 127,598 single cells, 2,869 WGS across 28 tissues, 43 cell types. eQTL/sQTL catalogs.

**Access:**
- https://chicken.farmgtex.org/
- NGDC: ngdc.cncb.ac.cn/chickengtex

**Paper:** Guan et al., Nature Genetics 2025

**Download:** No single accession. Raw data distributed across many SRA/NGDC BioProjects. Sample IDs in supplementary tables.

**Use:** Functional anchor for cross-species regulatory transfer.

---

### 4.2 FAANG Chicken

**What:** Functional Annotation of Animal Genomes. Pilot PRJEB14330 (8 tissues). Extended: 217 datasets (ChIP-seq, ATAC-seq, RNA-seq, RRBS).

**Access:**
- GEO: GSE158430
- GitHub pipeline: github.com/kernco/functional-annotation

**Paper:** Kern et al., Science Advances 2023

**Additional:** FR-AgENCODE (Foissac et al., BMC Biology 2019) includes chicken CD4+/CD8+ T cells.

---

## 5. Experimental Challenge Datasets (RNA-seq)

### 5.1 Priority Datasets for Reanalysis

| Accession | Species | Virus | Tissues | Samples | Primary Use |
|-----------|---------|-------|---------|---------|-------------|
| **PRJEB41063** | Chicken, turkey, duck, crow, goose, pigeon | H5N1 clade 2.2/2.3.2.1, H9N2 | Lung, ileum, brain | ~497 | **Best cross-species backbone** |
| **E-MTAB-2908** | Chicken (White Leghorn) | H5N1/H5N2 | Lung, ileum | 20 birds | Matched chicken/duck |
| **E-MTAB-2909** | Duck (Gray Mallard) | H5N1/H5N2 | Lung, ileum | 20 birds | Matched chicken/duck |
| **PRJNA767080** | Pekin duck | H5N1 VN1203 vs H5N2 | Multiple tissues | Time-course | Duck tissue detail |
| **CRA006707** | Chicken | H5N1/H9N2 | Lung single-cell | ~16,642 cells | Cell-type assignment |
| **PRJEB48271** | Multiple chicken breeds | H7N1, H5N8 clade 2.3.4.4b | Lung, spleen | Resistant vs susceptible | **Within-species outcomes** |
| **PRJNA1413929** | Broiler chicken | H7N1 | Nasal turbinate, lung | 8-72 hours | Early response |
| **PRJNA664709** | Chicken, tufted duck | 8 LPAI subtypes | Lung, colon, spleen | 207 libraries | Host × virus genotype |
| **PRJDB17017** | 11 species fibroblasts | H5N1 clade 2.5 | Primary cells | 6-12 hours | Early conserved response |

**Note on CRA006707:** Deposited in China's NGDC/GSA, not GEO. Cite accordingly.

---

### 5.2 Single-Cell & Spatial (2026)

| Accession | Species | Virus | Type | Notes |
|-----------|---------|-------|------|-------|
| **OMIX017644 / PRJCA066382** | Chicken, duck, pigeon, pig, mouse | H5N6 clade 2.3.4.4b | Single-cell + spatial | ~1.5M cells. Strongest current modern-clade resource |

---

### 5.3 Extreme Phenotype References

| Accession | Species | Phenotype | Use |
|-----------|---------|-----------|-----|
| **PRJNA640810** | Black swan | Extreme susceptibility | Identify missing/maladaptive immunity |
| **PRJEB44719** | Black swan endothelial | Inflammatory pathology | Vascular/tolerance mechanisms |
| **GCF_009769625.2** | Mute swan | Relative resistance | Contrast with black swan |

---

### 5.4 Shedding & Transmission Phenotypes

| Dataset | Species | Phenotype | Notes |
|---------|---------|-----------|-------|
| Mallard ileum/bursa | Mallard | Shedding variation | Why some become high shedders |
| Blue-winged teal | Teal | Cloacal shedding 1-5 dpi | RNA-seq + shedding |
| USDA mallard challenge | Mallard | Oral/cloacal titres H5N1 2.3.4.4b | No host omics but strong phenotype; Ag Data Commons |

---

### 5.5 Chicken Outbreak Survivors

| Study | Cohort | Virus | Type | Caveat |
|-------|--------|-------|------|--------|
| 2015 US H5N2 GWAS | Hundreds WL chickens | H5N2 | SNP array | Controls were uninfected, not exposure-confirmed |
| WGS survivor study | 42 survivors vs 28 controls | H5N2 | WGS | Polygenic; no major locus; raw data access unclear |

---

## 6. Population & Diversity Resources

### 6.1 Chicken Domestication/Diversity

- **Rubin et al. 2010** — 44.5× across 8 domestic populations + red junglefowl
- **SYNBREED panel** — global breed diversity (Malomane et al., BMC Genomics 2019)
- **AVIANDIV** — EU project: aviandiv.tzv.fal.de

### 6.2 Waterfowl

- **Mallard + Pekin STR/SNP** — 23 mallard + 26 Pekin (PMC6218588)
- **Duck chromosome-level assemblies** — three in Nature Communications
- **North American wild mallard** — chromosome-level (G3 2023, jkad171)
- **Waterfowl immune-gene diversity panel** — 127 innate immune genes across mallard populations + Pekin + other ducks (OUP MBE 2022)

### 6.3 Wild Bird Diversity

- **Prairie chicken WGS** — 433 individuals (PNAS Nexus 2024, pgae298). Good methodological template for conservation-scale WGS.

---

## 7. Denominator / Effort Data

### 7.1 GBIF

**What:** Global biodiversity occurrence records.

**Access:** https://www.gbif.org/

**Use:** Denominator for effort-corrected detection rates. Detections ÷ expected abundance = meaningful; raw detections alone measure ornithologists.

---

### 7.2 eBird

**What:** Citizen science bird observations with effort data.

**Access:** https://ebird.org/science

**Use:** Effort-corrected abundance surfaces. Better temporal resolution than GBIF.

---

## 8. Phenotype / Mortality Literature

### 8.1 Mass Mortality Events (Key Numbers)

South America 2022-2023 (Canadian Journal of Microbiology 2025):
- ~257,000 cormorants (esp. Leucocarbo bougainvilliorum)
- ~247,000 boobies (esp. Sula variegata)
- ~63,000 Peruvian pelicans
- ~36,000 South American sea lions
- ~17,000 southern elephant seals
- ~9,600 terns
- ~9,000 gulls

Antarctic/Subantarctic:
- South Georgia/Falklands brown skuas (Oct 2023)
- Antarctica (2024; EID 2025, 31(8))

### 8.2 Seabird Seroprevalence (Survivors)

- **Northern gannets (Bass Rock):** 78% of black-eyed birds H5 seropositive (Lane et al., Ibis 2024)
- **Atlantic Canada:** Common Murre, Atlantic Puffin, Common Eider seroprevalence (cjm-2025-0195)
- **Black-iris gannets:** Symptom did not affect foraging/breeding success

### 8.3 Conservation Vaccination Programs

- **California condor:** Emergency-use killed H5 poultry vaccine (May 2023). 80% of vaccinated condors reached protective titers (Katzner et al., EID 2025)
- **New Zealand:** DOC vaccinating ~300 core breeding birds across 5 species (kakī, takahē, kākāpō, tūturuatu, kākāriki)

---

## 9. Taxonomy & Crosswalk

### 9.1 Avibase

**What:** The taxonomic crosswalk. Maps between Clements/eBird, IOC, Howard & Moore, etc.

**Access:** https://avibase.bsc-eoc.org/

**Critical:** Pick ONE backbone (Clements/eBird or IOC), freeze it, and use Avibase to map everything else on ingest. Every source uses a different taxonomy. Get this wrong and every join silently degrades.

### 9.2 Harmonised Host List

**What:** 394 wild bird species across 26 orders, harmonised from 23,358 GISAID isolates (1973-2023).

**Access:** Sci Data (doi:10.1038/s41597-025-06451-1)

**Use:** Taxonomy reconciliation already done. Ingest directly.

---

## 10. Wild Bird Detection & Occurrence Data

This section catalogs integrated detection records and GPS/occurrence data for wild birds.

### 10.1 Detection Data Sources (51,298 records, 487 species mapped)

| Source | Records | Species | Country | Update Freq |
|--------|---------|---------|---------|-------------|
| USDA APHIS Wild Birds | 19,625 | 100+ | USA | Weekly |
| OAFD US 2022 | 4,362 | 119 | USA | Static |
| GitHub fbranda USA | 4,362 | 119 | USA | Community |
| GitHub fbranda Italy | 267 | 33 | Italy | Community |
| Italy HPAI Wild Birds | 267 | 40 | Italy | Quarterly |
| GISAID Avilist (harmonised) | 394 | 394 | Global | Static |
| USGS Alaska | 77 | 20+ | USA | Static |
| EMPRES-i linked | 2,838 | 110 | Global | Periodic |
| SDM HPAI (FAO/WOAH) | 8,541 | 169 | Global | Annual |
| Canada CWHC | 755 | 68 | Canada | Weekly |
| VS Surveillance H5+ | 9,401 | - | USA | Ongoing |
| Iceland USGS (2010-2018) | 381 | 19 | Iceland | Static |
| Ireland H5 targets | 28 | 28 | Ireland | Static |

**Ingestion script:** `scripts/ingest_detections.py`

**Output files:**
- `data/detections_merged.parquet` — Unified detection records
- `data/detections_merged.tsv` — Tab-separated export
- `data/detections_provenance.json` — Source metadata

---

### 10.2 GPS Telemetry Data (3.02M locations)

High-resolution GPS tracking from tagged waterfowl.

| Dataset | Records | Species | Individuals | Coverage |
|---------|---------|---------|-------------|----------|
| USGS Waterfowl GPS (2019-2020) | 2,797,469 | 9 | 412 | Western N. America |
| USGS Hourly GPS w/Life History | 224,888 | 5 | - | California |

**Species tracked:**
- Greater White-fronted Goose (Anser albifrons): 1.2M locations
- Northern Pintail (Anas acuta): 533K locations
- Cinnamon Teal (Anas cyanoptera): 417K locations
- Mallard (Anas platyrhynchos): 171K locations
- Northern Harrier (Circus cyaneus): 162K locations
- Northern Shoveler (Anas clypeata): 114K locations
- Gadwall (Anas strepera): 91K locations
- American Wigeon (Anas americana): 78K locations
- Blue-winged Teal (Anas discors): 18K locations

**Geographic extent:** 19.97°N to 70.66°N (Mexico to Arctic Alaska)

**Source:** [USGS ScienceBase](https://www.sciencebase.gov/catalog/item/675a0bd3d34edfeb8710a8ff)

**Files:**
- `data/raw/external/usgs-gps-tracking/waterfowl_gps_covid_2019_2020.csv`
- `data/raw/external/usgs-gps-tracking/waterfowl_hourly_gps_2015_2020.csv`

---

### 10.3 Occurrence Data with Coordinates

| Dataset | Records | Species | Coord Type |
|---------|---------|---------|------------|
| Ireland Wild Bird Occurrences | 16,304 | 410 | WGS84 Lat/Long |
| Italy HPAI Wild Birds | 239 | 32 | WGS84 Lat/Long |
| Canada CWHC HPAI | 753 | 68 | WGS84 Lat/Long |
| SDM HPAI Global | 11,353 | 318 | LAEA Europe (converted) |
| BBS Survey Routes | 5,824 | 700+ | WGS84 Lat/Long |
| HPAI Waterfowl Occurrence | 26,724 | 15 | County + Shapefile |

**Ireland data:** Includes `target_H5_HPAI` flag identifying 28 species targeted for H5N1 surveillance.

**SDM coordinates:** Originally in Lambert Azimuthal Equal-Area (EPSG:3035), converted to WGS84.

**Files:**
- `data/raw/external/usgs-datasets/.../ireland-gov/h5n1_wild_bird_species.csv`
- `data/raw/external/github-avian-flu/hpai-wild-birds-*.csv`
- `data/raw/external/usgs-bbs/Routes.csv`
- `data/raw/external/usgs-hpai-occurrence/HPAIv_ExposedBirdOccurrenceByCnty.csv`

---

### 10.4 ArcGIS Dashboard Sources (Auto-refresh)

Live dashboards with API access for automated updates.

| Source | URL | Filter | Records |
|--------|-----|--------|---------|
| Canada CWHC | [ArcGIS](https://cfia-ncr.maps.arcgis.com/apps/dashboards/89c779e98cdf492c899df23e1c38fdbc) | High Path Birds | ~755 |
| VS Wild Bird Surveillance | [ArcGIS](https://services7.arcgis.com/2C1NQ7u6M6SXoa8p/...) | H5+ samples | ~174K |

**Refresh script:** `scripts/refresh_arcgis_data.py`

**Automation:** `pixi run refresh-arcgis`

---

### 10.5 Data Sources Requiring Registration

| Source | Access | Data Type | Registration |
|--------|--------|-----------|--------------|
| GBIF | [gbif.org](https://gbif.org) | Occurrence | Free account for bulk |
| eBird Basic Dataset | [ebird.org](https://ebird.org/data/download) | Occurrence | Request form |
| GISAID EpiFlu | [gisaid.org](https://gisaid.org) | Sequences | Institutional |
| WAHIS | [wahis.woah.org](https://wahis.woah.org) | Official reports | Free account |
| Movebank | [movebank.org](https://movebank.org) | GPS telemetry | Free account |

---

### 10.6 Total Georeferenced Records

| Category | Records |
|----------|---------|
| GPS telemetry (hourly+) | 3,022,357 |
| Lat/Long coordinates | 23,120 |
| County + shapefile | 26,724 |
| **Total** | **3,072,201** |

---

## 11. Data NOT to Rehost

### 10.1 GISAID EpiFlu

**What:** Primary repository for HPAI sequences. Larger than BV-BRC.

**Problem:** Terms of use prohibit redistribution. This constrains architecture.

**Approach:** Link only. Users must obtain GISAID access separately.

### 10.2 Other Link-Only Resources

- Nextstrain builds (derived from GISAID)
- ChickenGTEx portal (no umbrella accession)
- Case count dashboards (CDC, WOAH, DashFLUboard)
