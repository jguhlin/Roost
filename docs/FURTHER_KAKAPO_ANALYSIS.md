# Kakapo (Strigops habroptila) Immune Gene Analysis

**Status:** Preliminary investigation complete; full gene detection pending
**Date:** 2026-08-26
**Priority:** High - critically endangered species with unknown HPAI susceptibility

---

## Summary

Kakapo is a critically endangered flightless parrot endemic to New Zealand (~250 individuals). Understanding its immune gene repertoire is critical for:
1. Assessing HPAI H5N1 susceptibility risk
2. Informing biosecurity protocols
3. Potential vaccination strategies if needed

## Genome Data Available

| Field | Value |
|-------|-------|
| Assembly | GCA_004011185.1 (alternate), GCA_004027225.1 (primary) |
| Individual | Jane (female) |
| Source | G10K-VGP, B10K, Kakapo Genetic Recovery Project |
| Taxon ID | 2489341 |
| Quality | Chromosome-level reference (VGP) |
| Annotation | NCBI Release 100 (2019-08-24) |

## Key Immune Genes - Current Status

### RIG-I (DDX58) - Viral RNA Sensor
| Status | **PRESENT** |
|--------|-------------|
| Gene ID | [115619851](https://www.ncbi.nlm.nih.gov/gene/115619851) |
| Location | Chromosome Z |
| Annotation | "probable ATP-dependent RNA helicase DDX58" |

**Significance:** RIG-I is **absent in chickens** (Galliformes), which is a major factor in their high HPAI susceptibility. Kakapo retaining RIG-I suggests better innate viral sensing capability.

**Next steps:**
- [ ] Verify full-length gene (no truncating mutations)
- [ ] Compare to duck RIG-I (known functional)
- [ ] Check for species-specific variants

### MX1 (Myxovirus Resistance) - Antiviral GTPase
| Status | **NOT ANNOTATED** |
|--------|-------------------|
| Gene ID | Not found in NCBI annotation |
| Concern | May be missing, divergent, or unannotated |

**Significance:** MX1 is a key interferon-induced antiviral protein. Human MxA strongly inhibits influenza; chicken Mx is non-functional.

**Next steps:**
- [ ] BLAST search using chicken/duck MX1 as query
- [ ] Check genome assembly for MX-like sequences
- [ ] If found, assess functional domains

### ANP32A/B/E - Host Factors for Viral Polymerase
| Status | **NOT CHECKED** |
|--------|-----------------|
| Gene IDs | Unknown |

**Significance:** ANP32 proteins are essential for influenza polymerase. The 33-amino-acid insertion in avian ANP32A supports avian virus replication.

**Next steps:**
- [ ] Identify kakapo ANP32A/B/E genes
- [ ] Check for 33-aa insertion in ANP32A
- [ ] Compare to chicken vs duck sequences

### Other Key Genes to Check
- [ ] IFIH1 (MDA5) - alternative RNA sensor
- [ ] MAVS - signaling adaptor
- [ ] IFIT5 - interferon-stimulated gene
- [ ] TRIM25 - RIG-I activator
- [ ] IFITM1/3 - membrane antiviral proteins

## Evolutionary Context

Kakapo belongs to Order **Psittaciformes** (parrots), which diverged from other birds ~82 million years ago. Key differences from Galliformes (chickens):

| Feature | Galliformes (Chicken) | Psittaciformes (Kakapo) |
|---------|----------------------|-------------------------|
| RIG-I | ABSENT (lost in ancestor) | PRESENT |
| MX1 | Present but non-functional | Unknown |
| HPAI susceptibility | HIGH | Unknown |

## Risk Assessment (Preliminary)

**Positive factors:**
- RIG-I present (functional viral sensing)
- High-quality genome enables analysis
- Isolated island population (low exposure risk)
- Intensive management allows intervention

**Concerns:**
- MX1 status unknown
- No natural exposure/immunity to influenza
- Small population = no buffer for mortality
- Flightless = cannot escape infected areas

## Recommended Actions

### Immediate (Gene Analysis)
1. Run gene detection pipeline on kakapo genome for all 19 panel genes
2. BLAST search for MX1/MX2 genes
3. Validate RIG-I is full-length and functional
4. Compare ANP32A insertion status to other parrots

### Medium-term (Susceptibility Assessment)
1. Compare immune gene repertoire to known susceptible vs resistant species
2. Model susceptibility based on gene presence/absence
3. Review parrot HPAI cases globally for phenotype data

### Conservation Implications
1. If susceptible: strengthen biosecurity protocols
2. Consider vaccination feasibility (see condor_vaccination2025 paper)
3. Prepare contingency plans for outbreak response

## Data Files

| File | Description |
|------|-------------|
| `data/avian_genome_summary.tsv` | Contains kakapo genome metadata |
| `data/genes/gene_presence_matrix.parquet` | Gene detection results (kakapo = UNKNOWN) |
| `data/species_profiles.parquet` | Species metadata including kakapo |

## References

1. Species-wide genomics of kākāpō provides tools to accelerate recovery. Nature Ecology & Evolution (2023). https://www.nature.com/articles/s41559-023-02165-y

2. Population genomics of the critically endangered kākāpō. Cell Genomics (2021). https://www.sciencedirect.com/science/article/pii/S2666979X21000021

3. Genetic reinstatement of RIG-I in chickens reveals insights into avian immune evolution. Frontiers in Immunology (2025). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12540166/

4. Absence of RIG-I leads to functional replacement by MDA5 in ducks. PNAS (2010). https://www.pnas.org/doi/10.1073/pnas.1001755107

---

*This analysis is part of the Roost Avian Influenza Host Genomics Resource.*
