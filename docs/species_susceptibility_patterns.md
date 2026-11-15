# HPAI H5N1 Species Susceptibility Patterns

**Generated:** 2026-08-26
**Based on:** 55 analyzed research papers

---

## Key Findings

### Resistance vs Susceptibility Markers

Two genes emerge as key markers distinguishing resistant from susceptible bird species:

| Gene | Resistant Species (upregulated) | Susceptible Species (not upregulated) |
|------|--------------------------------|-------------------------------------|
| **OAS** | Rock pigeon, cranes (Hooded, White-necked, Japanese) | Chicken, raptors (Mountain hawk-eagle, Peregrine falcon, Golden eagle) |
| **IFIT5** | Rock pigeon, cranes | Chicken, raptors |

**Source:** novel_host_factors2025

---

## Species Classification

### Known HPAI-Resistant Species
| Species | Evidence | Key Genes |
|---------|----------|-----------|
| **Ducks (Anseriformes)** | Low mortality, reservoir hosts | RIG-I present, robust innate immunity |
| **Rock Pigeon** | High OAS/IFIT5 upregulation | OAS, IFIT5 |
| **Japanese Crane** | High OAS/IFIT5 upregulation | OAS, IFIT5, HERC3 |
| **Hooded Crane** | High OAS/IFIT5 upregulation | OAS, IFIT5 |
| **White-necked Crane** | High OAS/IFIT5 upregulation | OAS, IFIT5 |

### Known HPAI-Susceptible Species
| Species | Evidence | Missing/Deficient Genes |
|---------|----------|------------------------|
| **Chicken (Galliformes)** | High mortality in outbreaks | RIG-I ABSENT, non-functional Mx |
| **Turkey** | High mortality in outbreaks | Similar to chicken |
| **Golden Eagle** | Low OAS/IFIT5 response | Weak innate response |
| **Peregrine Falcon** | Low OAS/IFIT5 response | Weak innate response |
| **Mountain Hawk-Eagle** | Low OAS/IFIT5 response | Weak innate response |
| **Northern Goshawk** | Low OAS/IFIT5 response | Variable response |

### Uncertain Susceptibility
| Species | Status | Notes |
|---------|--------|-------|
| **Okinawa Rail** | Likely susceptible | Low OAS/IFIT5 upregulation, MDA5 non-functional |
| **Japanese White Stork** | Likely susceptible | Low OAS/IFIT5 upregulation |

---

## Penguin Status

Penguins have emerged as a species of significant conservation concern:

### Documented Mortality Events
| Species | Location | Year | Deaths | Source |
|---------|----------|------|--------|--------|
| Humboldt Penguin | Chile | 2023 | ~3,000 | wild_bird_role2025 |
| African Penguin | South Africa | 2021 | >200 | wild_bird_role2025 |
| Gentoo Penguin | Antarctic | 2023 | 38+ | antarctica_skua2024 |
| Adelie Penguin | Antarctica | 2024 | Unknown | antarctica_panzootic2025 |

### Immune Response
- **King Penguin vaccination trial** (king_penguin_vaccine2026): mRNA vaccine against H5 clade 2.3.4.4b showed persistent immune response over 250 days
- Captive Sphenisciformes showed weak response to inactivated vaccines
- African penguins showed antibody persistence over several months

### Conservation Implications
- Dense colonial breeding = high transmission risk
- Long chick-rearing period = prolonged exposure
- No natural immunity to HPAI (isolated populations)
- Vaccination may be viable conservation tool

---

## Parrot (Psittaciformes) Status

### Current Knowledge
Limited data in current paper database. Key findings from genome analysis:

**Kakapo (Strigops habroptila)**:
| Gene | Status | Significance |
|------|--------|--------------|
| RIG-I (DDX58) | **PRESENT** | Unlike chickens, kakapo retains RIG-I |
| MX1 | **NOT ANNOTATED** | Status unknown, needs verification |
| ANP32A | Unknown | 33-aa insertion status needs checking |

**Evolutionary context**: Psittaciformes diverged ~82 million years ago. Unlike Galliformes (which lost RIG-I), parrots likely retain ancestral immune genes.

### Predicted Susceptibility
Based on RIG-I presence, parrots may be:
- More resistant than chickens
- Similar to ducks in innate sensing capability
- Still potentially vulnerable due to no prior exposure

---

## Key Conflicts & Agreements in Data

### Agreements
1. **RIG-I absence → susceptibility**: Consistent finding that chickens lack RIG-I and are highly susceptible
2. **OAS/IFIT5 as markers**: Multiple papers confirm these as differentiating resistant from susceptible species
3. **ANP32 as species barrier**: All papers agree ANP32A is critical for polymerase function
4. **PB2 mutations for adaptation**: Consistent finding of E627K, D701N, M631L

### Potential Conflicts
1. **Raptor susceptibility**: Some raptors show variable OAS/IFIT5 responses despite high mortality
   - Peregrine falcon shows some IFIT5 upregulation but still susceptible
   - May indicate additional factors beyond these two genes

2. **MX1 effectiveness**:
   - Human MxA strongly inhibits influenza
   - Chicken Mx is non-functional
   - Status in wild birds varies and is under-characterized

3. **Vaccine efficacy by species**:
   - Flamingos: 7+ year antibody persistence
   - Penguins: Initially thought weak responders, but king penguin trial shows good response
   - May depend on vaccine type (inactivated vs mRNA)

---

## Gene-Species Interaction Matrix

| Gene | Chicken | Duck | Pigeon | Cranes | Penguins | Raptors |
|------|---------|------|--------|--------|----------|---------|
| RIG-I | ABSENT | Present | Present | Present | Unknown | Unknown |
| MDA5 | Compensates | Normal | Normal | Normal | Unknown | Unknown |
| MX1 | Non-functional | Unknown | Unknown | Unknown | Unknown | Unknown |
| OAS | Low | Unknown | HIGH | HIGH | Unknown | Low |
| IFIT5 | Low | HIGH | HIGH | HIGH | Unknown | Variable |
| ANP32A | 33-aa insert | 33-aa insert | Unknown | Unknown | Unknown | Unknown |

---

## Research Priorities

1. **Characterize penguin immune genes**: OAS, IFIT5, RIG-I status
2. **Parrot/Psittaciformes panel**: Verify RIG-I, MX1, ANP32 in multiple species
3. **Crane immune mechanisms**: Why do cranes show strong OAS/IFIT5 response?
4. **Raptor variation**: Explain variable susceptibility despite low marker expression
5. **Vaccine cross-species efficacy**: Test mRNA vaccines in more species

---

*This analysis is part of the Roost Avian Influenza Host Genomics Resource.*
