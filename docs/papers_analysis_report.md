# H5N1 Research Papers Analysis Report

**Generated:** 2026-08-26
**Updated:** 2026-08-26
**Papers Analyzed:** 55 full-text documents
**Database Total:** 128 papers tracked

---

## Executive Summary

Analysis of 53 H5N1 avian influenza research papers reveals key patterns in host genomics, cross-species transmission, and species susceptibility. The research strongly implicates **PB2 polymerase mutations** as the primary driver of mammalian adaptation, while **ANP32 proteins** remain the fundamental species barrier. Seabirds (gannets, terns, skuas) and cattle have emerged as critical new hosts in the 2021-2026 panzootic.

---

## Key Findings

### 1. Host Genomics & Species Barriers

#### Primary Host Factor: ANP32 Proteins
| Gene | Mentions | Role |
|------|----------|------|
| ANP32A | 289 | Primary host factor for avian influenza polymerase; 33-amino-acid insertion in birds |
| ANP32B | 55 | Redundant role in mammals; single knockout insufficient for resistance |
| ANP32E | 24 | Required for complete resistance (triple knockout needed) |

**Key Finding:** Creating resistance to avian influenza requires editing ALL THREE ANP32 genes (A, B, E). Single gene knockouts are rapidly overcome by viral adaptation (PA-349K/PB2-M631L mutations).

#### Viral Adaptation Mutations
| Gene | Mentions | Key Mutations |
|------|----------|---------------|
| PB2 | 815 | E627K, D701N, M631L, T271A - mammalian adaptation |
| PB1 | 109 | Various polymerase complex mutations |
| HA | 185 | Receptor binding specificity changes |
| NA | 145 | Neuraminidase reassortment |

**Critical PB2 Mutations for Mammalian Adaptation:**
- **E627K** - Classic mammalian adaptation marker
- **D701N** - Enhanced replication in mammals
- **M631L** - Cattle-specific adaptation
- **T271A** - Associated with dairy cattle isolates

#### Innate Immunity Genes
| Gene | Mentions | Species Difference |
|------|----------|-------------------|
| MX1 | 49 | Human MxA strongly inhibits; chicken Mx weak/non-functional |
| RIG-I | 9 | **Absent in chickens**; present in ducks and mammals |
| MDA5 | 2 | Compensates for RIG-I absence in chickens |
| IFIT5 | 25 | Protective in transgenic chickens |

**Why Chickens Are Susceptible:** Chickens lack RIG-I (DDX58 gene) - a primary influenza sensor. Ducks have RIG-I and mount stronger innate immune responses.

---

### 2. Species Affected

#### Avian Species (Top 15 by mentions)
| Species | Mentions | Impact |
|---------|----------|--------|
| Chicken | 833 | Highly susceptible; poultry outbreaks |
| Duck | 207 | Often asymptomatic carriers; reservoir |
| Northern Gannet | 183 | Mass mortality events; major seabird impact |
| Turkey | 130 | Highly susceptible poultry |
| Great Skua | 120 | Severe die-offs; Antarctica spread |
| American Crow | 97 | High mortality; synanthropic transmission |
| Sandwich Tern | 61 | Colony collapses; breeding failures |
| Bald Eagle | 47 | Secondary infection from prey |
| Mallard | 40 | Reservoir species; migratory spread |
| Common Murre | 22 | Seabird mortality |
| Atlantic Puffin | 18 | Colony impacts |
| Griffon Vulture | 15 | Scavenger mortality from infected carcasses |
| Kittiwake | 12 | Mass mortality Norway 2023 |

**Seabird Crisis:** Northern Gannets, Great Skuas, and Sandwich Terns experienced unprecedented mass mortality events across Europe and North America (2022-2024).

#### Mammalian Species
| Species | Mentions | Transmission Route |
|---------|----------|-------------------|
| Cattle | 835 | Novel host since 2024; mammary gland tropism |
| Human | 468 | Occupational exposure; mild symptoms (mostly) |
| Domestic Cat | 132 | Consumption of infected birds/raw milk |
| Swine | 118 | Concern for reassortment with human strains |
| Red Fox | 78 | Neurotropic infection; consumption of birds |
| Elephant Seal | 32 | Mass mortality Argentina; mammal-to-mammal spread |
| Fur Seal | 22 | South American die-offs |
| Sea Lion | 16 | Peru/Chile mortality events |
| Mink | 15 | Farm outbreaks; possible mammal-to-mammal |

**Cattle Outbreak (2024-2026):** Unprecedented spillover to US dairy cattle. Genotype B3.13 with mammary gland tropism. PB2-M631L mutation associated with cattle adaptation.

---

### 3. Effects & Pathology

| Effect | Mentions | Notes |
|--------|----------|-------|
| Transmission | 1,425 | Focus on spillover and cross-species |
| Mortality | 1,006 | Mass die-offs documented |
| Respiratory | 273 | Pneumonia common in mammals |
| Recovery | 222 | Some population recovery in 2nd season |
| Morbidity | 216 | Clinical illness patterns |
| Neurological | 216 | Prominent in foxes, raptors, marine mammals |
| Mammal adaptation | 79 | PB2 mutations tracked |
| Population decline | 6 | Long-term colony impacts |

**Pathology Patterns:**
- **Birds:** Systemic infection; neurological signs common in raptors
- **Mammals:** Neurotropic in foxes/marine mammals; mammary tropism in cattle
- **Humans:** Primarily conjunctivitis (89%); fever (46%); respiratory (41%)

---

### 4. Papers with Richest Genomics Content

| Paper | Genes Covered | Focus |
|-------|---------------|-------|
| pandemic_risk2025 | RIG-I, MX1, TRIM25, IRF3, IRF7, NF-kB, PB2, PB1 | Host defense pathways |
| anp32_editing2023 | ANP32A/B/E, IFN-α, PB2, PB1, NP, HA | Genome editing for resistance |
| pb2_cattle_adaptation2026 | ANP32A/B/E, MX1, PB2, PB1, NP, HA | Cattle-specific mutations |
| pb2_cattle_pathogenicity2025 | ANP32A/B/E, PB2, PB1, PA, NP, HA | Mammalian pathogenicity |
| pb2_mutations2026 | ANP32A/B, PB2, PB1, NP, HA, NA, sialic acid | Mutation characterization |
| cattle_mbio2024 | ANP32B, PB2, PB1, NP, HA, NA, sialic acid | Cattle outbreak origin |

---

## Gene Functions Summary

### Species Barrier Genes
- **ANP32A/B/E:** Host factors required for influenza polymerase activity. The 33-amino-acid insertion in avian ANP32A supports avian polymerase; mammalian versions lack this, creating species barrier.

### Innate Immunity
- **RIG-I (DDX58):** Primary viral RNA sensor. **Absent in chickens** - key susceptibility factor.
- **MDA5:** Alternative RNA sensor; compensates partially for RIG-I absence.
- **MX1/MxA:** Antiviral GTPase. Human version strongly inhibits influenza; chicken version non-functional.
- **IFIT5:** Interferon-stimulated gene. Transgenic expression improves chicken survival.
- **TRIM25:** E3 ligase activating RIG-I signaling.

### Viral Adaptation Genes
- **PB2:** Polymerase subunit. E627K/D701N mutations enable mammalian replication.
- **HA:** Hemagglutinin. Receptor binding changes (α2,3 → α2,6) for human adaptation.
- **NA:** Neuraminidase. Reassortment affects transmissibility.

---

## Data Files Generated

| File | Description |
|------|-------------|
| `data/papers/papers_index.parquet` | Master paper tracking with download status |
| `data/papers/paper_analysis.parquet` | Per-paper analysis results |
| `data/papers/gene_mentions.parquet` | Gene mention counts |
| `data/papers/species_mentions.parquet` | Species mention counts |
| `data/papers/effects_mentions.parquet` | Effect type counts |
| `data/papers/paper_analysis.json` | Full analysis with all details |

---

## Key Conclusions

1. **Species barriers are genomic:** ANP32 proteins and PB2 mutations determine host range
2. **Chickens are uniquely vulnerable:** Lack of RIG-I and functional Mx explains high mortality
3. **Cattle represent a new frontier:** 2024 spillover with specific PB2 adaptations
4. **Seabirds suffered unprecedented losses:** Gannets, terns, skuas hit hardest 2022-2024
5. **Marine mammals show mammal-to-mammal transmission:** Seals/sea lions in South America
6. **Human cases remain mild:** Unlike historical 60% mortality, current infections mostly conjunctivitis

---

*Report generated from analysis of 53 full-text research papers on H5N1 avian influenza.*
