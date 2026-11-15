# Recommended Assets — what to reach for, per recurring figure need

Curated from the 12,444-asset mirror after the 2026-10-04 audit. Search
tips: common bird/mammal names auto-expand via the corpus species alias map
(e.g. "bar-headed goose" → *Anser indicus*); when a common name misses, try
the scientific name. Verify license + attribution with
`search_assets.py --import` (it records everything in the figure manifest).

## Host / organism silhouettes

| Need | Best asset | License | Query |
|---|---|---|---|
| Chicken | `nih-bioart/animals/000133_domestic-chicken-silhouette_g589.svg` | PD | `chicken` |
| Chicken (alt) | `phylopic/birds/gallus-gallus-domesticus-f16a316c.svg` | CC0 | `gallus gallus` |
| Duck | `nih-bioart/animals/000135_duck-silhouette_g592.svg` | PD | `duck` |
| Goose (generic — no *A. indicus* in permissive set) | `phylopic/birds/anser-anser-1d7e3c02.svg` | PD | `anser anser` |
| Cattle / dairy cow | `nih-bioart/animals/000100_dairy-cow-silhouette_g431.svg` | PD | `dairy cow` |
| Mouse | `scidraw/mouse/mouse-ded16e1d.svg` | CC BY 4.0 | `mouse` |
| Human figure | `nih-bioart/people/000390_person-standing_g1328.svg` | PD | `person standing` |
| Seal | `togo/202312_Larga_seal.svg` | CC BY 4.0 | `seal` / `larga seal` |
| Seabirds (gulls, pelicans…) | phylopic per scientific name (`larus`, `pelecanus`) | mixed | `larus` etc. |

## Virology

| Need | Best asset | License | Query |
|---|---|---|---|
| Influenza virion | `bioicons/viruses/servier_influenza-virus.svg` (recolored) | CC BY 3.0 | `influenza virus` |
| Influenza virion (CC0!) | `scidraw/other/influenza-virus-6883e674.svg` | CC0 | `influenza virus` |
| Virion cross-section | `bioicons/viruses/servier_influenza-virus-interior.svg` | CC BY 3.0 | `virus interior` |
| Generic virus panel | reactome `cell-type/…` + bioicons `viruses/…` | CC BY 4.0/3.0 | `virus` |

## Cells, tissues, anatomy

| Need | Best asset | License | Query |
|---|---|---|---|
| Epithelium (column/cuboid/goblet) | bioicons `tissues/servier_epithelium-*.svg` | CC BY 3.0 | `epithelium cell` |
| Human respiratory tract | `nih-bioart/anatomy/000245_human-upper-respiratory-…svg` | PD | `respiratory tract` |
| Antibody (icon) | `nih-bioart/proteins/000018_antibody_g59.svg` | PD | `antibody` |
| Antibodies (pair) | bioicons `blood-immunology/servier_antibodies.svg` | CC BY 3.0 | `antibodies` |

## Lab / methods

| Need | Best asset | License | Query |
|---|---|---|---|
| Syringe / vaccination | `healthicons/devices/syringe-vaccine.svg` | CC0 | `syringe vaccine` |
| Sequencer | `nih-bioart/equipment/000386_next-gen-sequencer_g1316.svg` | PD | `sequencer` |
| Microscope | `healthicons/…` / `bioicons/…` | CC0 | `microscope` |
| Lab equipment (broad) | togo `2020*`/`2021*` series, servier `medical-specialties/…` | CC BY 4.0 | `equipment`, `lab` |

## Molecular / pathway

| Need | Best asset | License | Query |
|---|---|---|---|
| Chromatin / nucleosomes | `reactome/background/chromosome-and-nucleosomes-014738.svg` | CC BY 4.0 | `chromosome` |
| Specific proteins (CDs, receptors) | reactome `protein/*` (~2.2k icons) | CC BY 4.0 | `<protein name>` |
| DNA/RNA abstract | reactome `nucleic-acids` kit via servier | CC BY 4.0 | `nucleic` |

## Conventions

- Silhouettes render at 48–86 px, single-hue (`muted` or semantic token);
  multi-color assets get recolored on import (record `modified: true`).
- Commons-name misses → try scientific (alias expansion covers most).
- License hygiene is automated: `--import` writes attribution into the
  manifest; `build_attribution.py` emits per-figure TXT + the rollup;
  the on-page registry credits every asset (CC0/PD included).
