# Roost Project TODOs

## Data Source Sign-ups (Manual Review Required)

These databases require registration and terms acceptance before integration.

### High Priority

- [ ] **GISAID** - Influenza sequences with host species metadata
  - Sign up: https://gisaid.org/register/
  - Requirements: Institutional email, Data Access Agreement
  - Approval time: ~1-2 days
  - Value: Detailed sequence-linked host data, strain typing, ~23k isolates
  - Integration: Add `load_gisaid()` function once credentials obtained

- [ ] **WAHIS (WOAH)** - Official disease notifications
  - Sign up: https://wahis.woah.org/#/home
  - Requirements: Free registration
  - API access: May need to contact wahis.admin@woah.org
  - Value: Official notifications from 180+ countries
  - Integration: Update `fetch_external_data.py` with auth

### Medium Priority

- [ ] **FAO EMPRES-i** - Global outbreak events
  - Access: https://empres-i.apps.fao.org/
  - Bulk data: Contact empres-ah@fao.org
  - Value: Global outbreak event data with coordinates
  - Note: We already have linked dataset, this would add real-time updates

- [ ] **EFSA Data Portal** - European surveillance
  - Portal: https://data.efsa.europa.eu/
  - Bulk requests: data.collection@efsa.europa.eu
  - Value: 276,000+ EU surveillance records annually
  - Note: May require justification for bulk access

### GPS Tracking of Infected Birds

- [ ] **Dryad - Rough-legged Hawk HPAI Mortality** (HIGH VALUE)
  - DOI: https://doi.org/10.5061/dryad.n2z34tn92
  - Requirements: Dryad account (free)
  - Value: 71 GPS-tracked hawks, 29 mortalities, 11 confirmed HPAI deaths
  - Data: 40MB GPS telemetry with cause-of-death annotations
  - Contact: Neil Paprocki (npaprocki@usgs.gov)

- [ ] **Movebank - Griffon Vulture HPAI Outbreak (France 2022)**
  - Studies: "Eurasian Griffon vulture in France (Grands Causses 2018)"
            "Eurasian Griffon vulture in France (Aude 2021)"
  - Requirements: Request permission from data owners
  - Value: GPS tracking during H5N1 outbreak, 31 adult vultures
  - Reference: Hirschinger et al. 2025, Emerg Infect Dis 31(8)

### Lower Priority (Nice to Have)

- [ ] **eBird API** - Bird occurrence data
  - Sign up: https://ebird.org/register
  - API key: https://ebird.org/api/keygen
  - Value: Bird occurrence data for range/exposure modeling
  - Note: Useful for ecological context, not direct detections

## Automation Tasks

- [ ] Set up cron job for weekly ArcGIS data refresh
  ```bash
  # Add to crontab:
  0 6 * * 1 cd /path/to/Roost && pixi run python scripts/refresh_arcgis_data.py
  ```

- [ ] Add APHIS CSV auto-download (currently manual)
  - URL: https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv
  - Frequency: Weekly during outbreak season

## Data Quality Tasks

- [ ] Improve species name harmonization for SDM dataset
  - Currently 169/274 species mapped
  - Need to handle more common name → scientific name mappings

- [ ] Add province field extraction for Canada data
  - Currently not parsing location beyond coordinates

- [ ] Deduplicate records across overlapping sources
  - APHIS US vs OAFD US 2022 may have overlap
  - SDM vs EMPRES-i linked may have overlap

## Connections Feature (gene-relationship mining WIP — D76/D78)

Untracked work-in-progress; do not ship without finishing these.

- [ ] **Fix `web/tests/connections.spec.js` failures (2)** — tests run ahead of the UI:
  - "list cards show stage chip…": DDX58's `[data-testid="gene-stage-chip"]` renders 0 elements under the empty-approvals interception (`relWith([])`) — stage assignment has no data source independent of approved relationships.
  - "species selector highlights exact-species evidence…": `#species-context` selector never renders on the network page (30s timeout).
- [ ] **Decide the stage-chip data path** — `wiki_genes.json` carries no `stage` field; stage currently only exists on the connections side (`gene_relationships.json` / `data/papers/connections/` outputs).
- [ ] **Wire review gate → publish**: `scripts/papers/connections.py` produces pending candidates in `data/papers/connections/` (`candidates.jsonl`); confirm the approved-edges publication path into `web/public/data/gene_relationships.json`.
- [ ] **Track the files** — `scripts/papers/connections.py`, `web/tests/connections.spec.js`, `gene_relationships.json`, and `scripts/tests/test_connections.py` are all untracked; commit once tests pass.

## Future Integrations

- [ ] Add South America WOAH notifications (104 species reported)
- [ ] Netherlands PMC study supplementary data (51 species confirmed)
- [ ] UK DEFRA wild bird detections (40 species, 375 records Dec 2024-Mar 2025)

## Figure System (D163 — see docs/FIGURE_AGENT.md)

Done: skills installed (`.pi/skills/{svg-diagram,drawio,scientific-diagram,
scientific-data-figure,scientific-assets,fframes-video}`), asset mirrors +
SQLite FTS index (`assets/manifest.sqlite`), figure pipeline scripts
(`scripts/figures/`), `figures/{src,preview,export,manifests,attribution}`
layout, credits rollup (`docs/ASSET_CREDITS.md`), cargo-fframes installed.

- [x] ~~Manual asset downloads~~ → **automated D164**: Togo mirrors from
      the dbarchive directory listing (svg_format.zip is gone) and Servier
      from the direct all-kits zip — both via
      `scripts/figures/mirror_togo_servier.sh`
- [ ] **Extend NIH BioArt mirror**: raise `BIOART_END` in
      `scripts/figures/mirror_assets.sh` (currently 600 of ~5k entries)
- [ ] **Extend PhyloPic mirror**: raise `PHYLOPIC_LIMIT` (currently 2500 of
      >13k; permissive-only) once more silhouettes are needed
- [ ] **Install draw.io Desktop** for the drawio skill's CLI path (Mermaid
      convert, ELK layout, embedded-diagram export)
- [ ] **Phase 3**: port Scientific Figure Skills templates (Manhattan/QQ,
      genomic-region, forest, phylo-trait panels) into
      `.pi/skills/scientific-data-figure/references/` as the paper figures
      need them
- [ ] **Phase 4 (optional)**: AutoFigure-Edit / PaperBanana experiments —
      vendored under `vendor/`, not run
- [ ] **Phase 5**: first real fframes video abstract (template verified in
      /tmp/fframes-smoke; skill at `.pi/skills/fframes-video`)
- [ ] Migrate legacy flat `figures/*.svg` (fig2/fig3/fig4, gene panels) into
      `figures/src/` with manifests + attribution as they get revised
