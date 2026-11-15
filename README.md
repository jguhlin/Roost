# Roost

Avian Influenza Host Genomics Resource — a database linking bird genomes, HPAI detections, and gene annotations to accelerate comparative immunity research.

## The Problem

There is no avian influenza **host genomics** resource. The viral side is saturated (GISAID, Nextstrain). The epi side is covered (WAHIS, CDC). But the host layer — which species has a genome, which genes they have, how that maps to outcomes — doesn't exist.

Phylogeny predicts susceptibility; ecological traits don't. The obvious missing covariate is **gene content**.

## What This Does

Roost builds a **coverage matrix** answering: *"Which bird species have both genomic resources AND phenotype data?"*

| Metric | Count |
|--------|-------|
| Total bird species | 11,284 |
| With genome | 1,979 (17.5%) |
| With HPAI detection | 296 species (20,669 records, 116 countries) |
| **Genome + Detection** | **133** |
| Papers analyzed (LLM, verified) | 142 |
| Quantified findings extracted | 1,729 |
| Unique mutations cataloged | ~400 |

## Quick Start

```bash
# Install pixi (if needed)
curl -fsSL https://pixi.sh/install.sh | bash

# Clone and setup
git clone <repo>
cd Roost
pixi install

# Download data and build (takes ~5 min)
# First download NCBI taxonomy:
curl -o data/taxdump.tar.gz https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz
mkdir -p data/taxonomy && tar -xzf data/taxdump.tar.gz -C data/taxonomy

# Then run pipeline:
pixi run build-all

# Export data for the website:
python scripts/export_web_data.py
python scripts/papers/build_paper_index.py    # papers index
python scripts/papers/build_gene_data.py       # gene pages data
python scripts/papers/build_species_data.py    # species ↔ papers links

# Run the website:
cd web && npm install && npm run dev
```

## Project Structure

```
Roost/
├── pixi.toml               # Environment and tasks
├── README.md               # This file
├── DATA_MANIFEST.md        # Data sources and regeneration
├── scripts/
│   ├── parse_taxonomy.py        # NCBI taxonomy → Aves species
│   ├── build_species_table.py   # Join taxonomy + genomes
│   ├── ingest_aphis.py          # APHIS detections
│   ├── build_coverage_matrix.py # Final matrix
│   └── papers/                  # Research-paper pipeline
│       ├── download_pdfs.py     #   PDF acquisition (PMC, batch)
│       ├── convert_pdfs.py      #   PDF → markdown (pymupdf4llm)
│       ├── llm_analyze_papers.py#   Structured LLM extraction (Anthropic, dual-pass)
│       ├── build_paper_index.py #   papers.json for web
│       ├── build_gene_data.py   #   genes.json + gene_citations.json
│       └── build_species_data.py#   species_papers.json
├── web/                    # Svelte 5 + Vite website (Phase 5)
│   └── src/routes/         #   Home, Species, Genomes, Genes, Map,
│                           #   Phylogeny, Papers, Downloads, Resources
├── docs/
│   ├── DATA_CATALOG.md          # All data sources
│   ├── DATABASE_DESIGN.md       # Schema spec
│   ├── ANALYSIS_FRAMEWORK.md    # OrthoGLMM methods
│   ├── GENE_PANEL.md            # Panel definition, tiers, formal intake method (§12)
│   ├── BUILD_SPEC.md            # Build phases
│   ├── PLAN_WIKI.md             # Wiki-style knowledge pages (Phase 7)
│   ├── papers_md/               # 143 papers converted to markdown
│   └── papers_pdfs/             # 144 source PDFs
└── data/                   # Generated (not in git)
    ├── coverage_matrix.parquet
    ├── species_table.parquet
    └── papers/            # LLM analyses + aggregates
```

## Available Tasks

```bash
pixi run refresh               # Periodic update: fetch all automatic sources
                                # (APHIS, DEFRA, WAHIS, WHISPers, EMPRES-i…),
                                # re-ingest + dedup, rebuild profiles + web data
pixi run build-all              # Full pipeline
pixi run parse-taxonomy         # Parse NCBI taxonomy
pixi run build-species-table    # Build species + genome table
pixi run ingest-aphis           # Ingest APHIS detections
pixi run build-coverage-matrix  # Build final matrix
```

## Key Outputs

### Coverage Matrix (`data/coverage_matrix.parquet`)

One row per bird species with:
- Taxonomy (order, family, genus)
- Genome availability and quality
- HPAI detection counts
- Expression dataset availability

### Top Species (Genome + Detections)

| Species | Detections | Assembly | Annotated |
|---------|------------|----------|-----------|
| Mallard | 3,441 | Complete | Yes |
| Canada goose | 1,958 | Chromosome | Yes |
| Green-winged teal | 1,443 | Chromosome | No |
| Snow goose | 1,164 | Scaffold | No |
| Bald eagle | 967 | Scaffold | Yes |

## Data Sources

| Source | Coverage | Status |
|--------|----------|--------|
| NCBI Taxonomy | 11,284 bird species | ✅ Ingested |
| NCBI Genomes | 3,845 assemblies | ✅ Ingested |
| APHIS Wild Birds | US HPAI since 2022 | ✅ Ingested |
| APHIS Mammals | US mammal HPAI cases (824 animals) | ✅ Ingested |
| APHIS Flocks | US premises + birds affected (208M birds) | ✅ Ingested (Tableau export) |
| UK DEFRA/APPA | 2024–2026 wild birds | ✅ Ingested |
| Our World in Data | H5N1 human cases | ✅ Ingested |
| Research corpus | 142 papers, 7-step LLM extraction | ✅ Verified |
| WAHIS | Global official | 🔲 Planned |
| EMPRES-i (live) | Global outbreaks | 🔲 Planned |
| GISAID | 23K isolates | 🔲 Requires login |

See [DATA_MANIFEST.md](DATA_MANIFEST.md) for details.

## Documentation

- [INTAKE.md](docs/INTAKE.md) — **Operating manual: paper / case / news / genome intake protocols** (read before adding any data)
- [DATA_CATALOG.md](docs/DATA_CATALOG.md) — Complete data source reference
- [DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) — Schema and provenance system
- [ANALYSIS_FRAMEWORK.md](docs/ANALYSIS_FRAMEWORK.md) — OrthoGLMM and comparative methods
- [GENE_PANEL.md](docs/GENE_PANEL.md) — Panel definition (488 literature-scope host genes), tiers, and the formal discovery/intake method (§12)
- [BUILD_SPEC.md](docs/BUILD_SPEC.md) — Build phases and acceptance criteria

## Roadmap

- [x] Phase 0: Foundation (taxonomy, genomes)
- [x] Phase 1: Coverage matrix
- [x] Phase 2: APHIS detection ingest + multi-source deduplication
- [x] Phase 3: Gene presence matrix (RIG-I, ANP32A, IFITM) with provenance
- [x] Phase 4: Additional sources (DEFRA, OWID, ArcGIS refresh)
- [x] Phase 5: Website (Svelte + DuckDB-WASM + MapLibre, 9 pages)
- [x] Phase 6: Research corpus + LLM paper analysis (142 papers)
- [ ] Phase 7: Wiki-style knowledge pages ([PLAN_WIKI.md](docs/PLAN_WIKI.md))
- [ ] Global detection data (WAHIS, EMPRES-i live)

## License

Dual-licensed by component type:

- **Code** (pipeline scripts, web app, tests, tooling) — MIT, see
  [LICENSE](LICENSE).
- **Generated text, documentation, prompts, agent notes, and figures** —
  Creative Commons Attribution-NonCommercial 4.0 International, see
  [LICENSE-CC-BY-NC-4.0](LICENSE-CC-BY-NC-4.0).

Third-party assets (icons, silhouettes, fonts) keep their own licenses —
per-item attribution lives in [figures/attribution/](figures/attribution/)
and [docs/ASSET_CREDITS.md](docs/ASSET_CREDITS.md).

## Citation

TBD
