#!/usr/bin/env python3
"""
Vaccine model builder (D68) — Roost's third model pillar.

  infection model  = what happens inside the bird   (gene-driven)
  spread model     = how it moves between birds     (species/ecology-driven)
  vaccine model    = how we intervene              (intervention-driven)

The literature LLM is currently down, so this build is DETERMINISTIC:
per-stage evidence = keyword scans over the markdown corpus (rg),
tiered as 'keyword' (🟡). When the LLM returns, mine_vaccines.py
(written alongside) re-extracts verified per-paper claims into
data/papers/vaccine_claims.jsonl and this builder merges them,
rebadging stages to 'verified' (🟢). Stage definitions live HERE
(curated) — evidence merges in, never overwrites curation.

Output (both files, canonical + shipped):
  data/model/h5n1_vaccine_model.json
  web/public/data/h5n1_vaccine_model.json

Usage: pixi run python scripts/model/build_vaccine_model.py
"""

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
CLAIMS_JSONL = ROOT / "data" / "papers" / "vaccine_claims.jsonl"  # LLM output, later
MODEL = ROOT / "data" / "model" / "h5n1_vaccine_model.json"
SHIPPED = ROOT / "web" / "public" / "data" / "h5n1_vaccine_model.json"

# ---------------------------------------------------------------------------
# Curated stage definitions. Genes cross-link into the infection model /
# gene pages (#/genes/SYM). Keywords drive the deterministic corpus scan.
# ---------------------------------------------------------------------------
STAGES = [
    {
        "id": "platforms",
        "title": "1 · Vaccine Platforms",
        "short": "Platforms",
        "accent": "#0ea5e9",
        "desc": "The platform landscape for avian influenza vaccination: classical inactivated whole-virus (the poultry workhorse), live-attenuated influenza vaccines (LAIV), viral-vectored (HVT, NDV, fowlpox, MVA — one shot, hatchery-compatible, DIVA-friendly when vectored on non-flu backbones), and the new generation: mRNA, DNA, M2e-nanoparticle and other subunit designs aiming for conserved-antigen breadth. Platform choice constrains everything downstream: cost per bird, delivery route, DIVA compatibility, and update speed when the drifts arrive.",
        "genes": [],
        "keywords": ["inactivated vaccine", "live-attenuated", "LAIV",
                     "vectored vaccine", "HVT", "fowlpox", "NDV vector",
                     "MVA vector", "mRNA vaccine", "DNA vaccine",
                     "nanoparticle vaccine", "M2e", "virus-like particle",
                     "recombinant protein vaccine", "subunit vaccine"],
        "metrics": ["platform", "backbone/vector", "valency", "dose schedule",
                    "cost/practicality notes for poultry deployment"],
    },
    {
        "id": "antigen",
        "title": "2 · Antigen Choice & Match",
        "short": "Antigen",
        "accent": "#8b5cf6",
        "desc": "What the immune system is shown: HA (the classic — neutralization target, but drift-prone and clade-matched), NA, internal proteins NP/M1 (T-cell targets, conserved, DIVA markers), and conserved epitopes like M2e (universal-vaccine ambitions, weak immunogenicity alone). Antigenic match between vaccine strain and circulating clade (2.3.4.4b, D1.1, B3.13…) decides clinical efficacy; mismatch is the classic failure mode — and the selection pressure that drives escape.",
        "genes": [],
        "keywords": ["antigenic match", "HA clade", "vaccine strain match",
                     "hemagglutinin vaccine", "NA vaccine", "nucleoprotein vaccine",
                     "M2e", "conserved epitope", "universal vaccine",
                     "antigenic drift", "vaccine escape", "HI test",
                     "antigenic mismatch"],
        "metrics": ["antigen(s)", "clade/genotype matched", "sequence identity to challenge strain",
                    "breadth (heterologous protection tested?)"],
    },
    {
        "id": "delivery",
        "title": "3 · Delivery & Administration",
        "short": "Delivery",
        "accent": "#14b8a6",
        "desc": "How vaccine reaches the bird at poultry scale: mass application (hatchery coarse spray, drinking water) vaccinates ≈24 billion chickens annually worldwide; in-ovo injection is routine at the hatchery; individual injection serves breeders, zoos and wildlife. Delivery route sets the immune compartment primed — spray hits respiratory mucosa (IgA, the transmission-relevant arm), injection primes systemic IgY. Wildlife programs (condor, penguin) need individual-dose workflows: darting, hand-injection, pre-bait trials.",
        "genes": [],
        "keywords": ["in ovo", "hatchery vaccination", "spray vaccination",
                     "drinking water vaccination", "subcutaneous vaccination",
                     "wing web", "route of administration", "prime-boost",
                     "mucosal vaccination"],
        "metrics": ["route", "dose volume/schedule", "age at vaccination",
                    "species studied", "field-vs-lab deployment"],
    },
    {
        "id": "adjuvant",
        "title": "4 · Adjuvants & Innate Priming",
        "short": "Adjuvant",
        "accent": "#f59e0b",
        "desc": "The innate-immune lever on vaccine response. Oil emulsions (standard for inactivated poultry vaccines) hold antigen and provoke inflammation; innate agonists target the bird's sensing machinery directly — CpG motifs read by the avian TLR21 (no TLR9 in birds), dsRNA mimics via TLR3/MDA5/RIG-I (in ducks), cytokine adjuvants (IFN, IL-2 family). This is where the vaccine model plugs hardest into the gene model: adjuvant = chosen sensor, sensor = gene.",
        "genes": ["TLR21", "TLR3", "MYD88", "DDX58", "IFIH1", "IFNB1", "IRF7"],
        "keywords": ["adjuvant", "CpG", "TLR21 agonist", "oil emulsion",
                     "Freund", "cytokine adjuvant", "interferon adjuvant",
                     "immunostimulant"],
        "metrics": ["adjuvant class", "sensor targeted", "dose-sparing evidence",
                    "innate-response kinetics"],
    },
    {
        "id": "response",
        "title": "5 · Immune Response Elicited",
        "short": "Response",
        "accent": "#ec4899",
        "desc": "What vaccination actually builds in a bird: circulating HI/neutralizing IgY (the licensed correlate — but a correlate of clinical protection, not transmission), mucosal IgA at the airway and gut (the transmission-relevant barrier), CD8 T-cell responses to conserved internal proteins, breadth across clades, and the complications: immune imprinting (first infection shapes all later responses), maternal IgY interference in chicks, and the MHC story — chicken BF2 haplotype B21 predicts both H5N1 survival and vaccine response quality. The gene × vaccine bridge lives here.",
        "genes": ["BF2", "BLB2", "CD74", "RAG1", "AICDA", "IRF8"],
        "keywords": ["neutralizing antibody", "HI antibody", "seroconversion",
                     "mucosal IgA", "cell-mediated immunity", "CD8 T cell",
                     "immune imprinting", "maternal antibody", "correlate of protection",
                     "GMT", "antibody titer"],
        "metrics": ["HI GMT / seroconversion rate", "IgA response (mucosal?)",
                    "T-cell assays", "cross-clade titers", "duration of immunity",
                    "MHC haplotype effects"],
    },
    {
        "id": "protection",
        "title": "6 · Protection Outcomes",
        "short": "Protection",
        "accent": "#22c55e",
        "desc": "The endpoint hierarchy: (1) clinical protection — morbidity/mortality (what licensure measures), (2) shedding reduction — viral titers and duration in swabs (what matters for flock-level load), (3) transmission reduction — the R-driving endpoint, sterilizing or near-sterilizing immunity (what actually stops a panzootic). Many registered vaccines do (1) while barely moving (3) — vaccinated birds can shed and transmit silently, which is why vaccination without surveillance can make things worse. Meta-analytic evidence exists in the corpus for HPAI vaccine efficacy by platform and antigen match.",
        "genes": [],
        "keywords": ["clinical protection", "mortality reduction", "shedding reduction",
                     "sterilizing immunity", "transmission reduction",
                     "challenge study", "vaccine efficacy", "protected contact",
                     "breakthrough infection"],
        "metrics": ["challenge strain & dose", "% mortality vaccine-vs-control",
                    "shedding tres/duration (swab site)", "transmission chain study?",
                    "n, randomization, blinding"],
    },
    {
        "id": "diva",
        "title": "7 · DIVA & Surveillance",
        "short": "DIVA",
        "accent": "#64748b",
        "desc": "Differentiating Infected from Vaccinated Animals — the surveillance precondition for vaccination. Infected birds seroconvert to ALL flu proteins; most vaccines show only one. Strategies: vaccinate on NP or M2e while surveillance ELISAs target NP-free antigens (or vice versa), use vectored vaccines whose marker protein unvaccinated infected birds never make, or unvaccinated sentinel birds per flock. Without DIVA, trade partners can't distinguish a vaccinated-and-clean flock from a silent-infection one — the export economics that keep many countries unvaccinated.",
        "genes": [],
        "keywords": ["DIVA", "differentiating infected from vaccinated",
                     "marker vaccine", "sentinel birds", "NP-ELISA",
                     "vaccination surveillance", "serological monitoring"],
        "metrics": ["DIVA strategy used", "assay (antigen, sensitivity/specificity)",
                    "trade/export implications"],
    },
    {
        "id": "deployment",
        "title": "8 · Deployment Strategies",
        "short": "Deployment",
        "accent": "#ef4444",
        "desc": "Where vaccines actually meet birds. Poultry: preventive routine vaccination (endemic countries: China, Egypt, Indonesia, Vietnam, Mexico) vs emergency ring vaccination around outbreaks (EU 2023+ policy shift); the economics (dose cost vs cull cost) and the political economy of export bans. Wildlife: the conservation programs of record — California condor (2023, first US wild-bird HPAI vaccination after the 21-death die-off) and king penguin sub-Antarctic trials — plus zoo collections. NZ/Aotearoa: currently unvaccinated, no outbreaks — the operational question is a pre-emptive program for taonga species (kākāpō, takahē) if H5N1 arrives.",
        "genes": [],
        "keywords": ["ring vaccination", "preventive vaccination", "vaccination policy",
                     "vaccination campaign", "poultry vaccination program",
                     "condor vaccination", "penguin vaccination",
                     "zoo vaccination", "wildlife vaccination",
                     "vaccine bank"],
        "metrics": ["country/region & policy context", "coverage achieved",
                    "campaign outcome (outbreaks averted?)", "cost",
                    "wildlife program design"],
    },
    {
        "id": "escape",
        "title": "9 · Escape & Evolutionary Risk",
        "short": "Escape",
        "accent": "#7c3aed",
        "desc": "Vaccination as a selection pressure. Antigenically mismatched vaccines protect the bird while permitting replication of escape variants — the Chinese H5 Re- era shows vaccine-driven antigenic drift in circulation. Multi-valent updates, antigenic-cartography-guided strain selection, and transmission-blocking (not just clinical) vaccines are the mitigation. In birds, immune imprinting (original antigenic sin) may narrow responses to drift variants — the corpus carries the human-side evidence; avian evidence is a registered gap.",
        "genes": [],
        "keywords": ["vaccine-driven selection", "antigenic cartography",
                     "escape variant", "vaccine update", "multivalent vaccine",
                     "original antigenic sin", "immune imprinting",
                     "selection pressure"],
        "metrics": ["evidence for variant emergence post-vaccination",
                    "antigenic distance (cartography units)", "update cadence"],
    },
]

# Gene × vaccine bridge: genes where host genetics modulates vaccine response.
GENE_BRIDGE = [
    {"gene": "BF2", "why": "MHC-I haplotype B21: better H5N1 survival AND stronger vaccine response — the chicken MHC-B/vaccine-response literature (Kaufman minimal-MHC story)"},
    {"gene": "BLB2", "why": "Dominantly expressed MHC-II — CD4 helper/T-cell response quality to vaccine antigens"},
    {"gene": "CD74", "why": "MHC-II invariant chain — antigen processing of subunit/inactivated vaccines"},
    {"gene": "RAG1", "why": "V(D)J recombination — the receptor diversity pool every antibody response draws from"},
    {"gene": "AICDA", "why": "Somatic hypermutation/affinity maturation — GMT rise after boost"},
    {"gene": "TLR21", "why": "Bird CpG sensor (TLR9 replacement) — the adjuvant target for CpG-adjuvanted and mRNA platforms"},
    {"gene": "TLR3", "why": "dsRNA sensor — adjuvant route for RNA-mimic adjuvants"},
    {"gene": "DDX58", "why": "RIG-I (ducks) — innate priming by LAIV/replicating platforms; lost in Galliformes (response asymmetry)"},
    {"gene": "IFNB", "why": "Type-I IFN — the innate bridge adjuvants and live platforms ride on"},
    {"gene": "IRF8", "why": "Dendritic/NK transcription factor — antigen-presenting-cell fitness"},
]

GAPS = [
    {"id": "V1", "what": "NZ taonga-species vaccine program design (kākāpō, takahē, kākā — no data, no licensed avian-influenza wildlife vaccine workflow in NZ)", "kind": "true-gap"},
    {"id": "V2", "what": "Transmission-block efficacy for current commercial poultry vaccines (most publish clinical + shedding, not chain-transmission)", "kind": "lit-search"},
    {"id": "V3", "what": "Avian immune imprinting for influenza (human evidence in corpus; avian evidence thin)", "kind": "lit-search"},
    {"id": "V4", "what": "MHC haplotype × vaccine-response in non-chicken species (duck/turkey/passerine MHC expansions differ)", "kind": "lit-search"},
    {"id": "V5", "what": "mRNA platform economics for 20B-dose/yr poultry scale", "kind": "lit-search"},
    {"id": "V6", "what": "Wild-bird oral-bait vaccination feasibility (fox-rabies model transferred to birds)", "kind": "true-gap"},
]

# What we extract per candidate paper once the literature LLM is back.
# Single source of truth: mine_vaccines.py imports this schema + enums.
LLM_PLAN = {
    "_doc": ("Three-pass mining, cheap→expensive. (1) TRIAGE — is this a "
            "vaccine paper at all, and which stages (1 short call)? "
            "(2) PROPOSER — structured extraction, one record per vaccine × "
            "species × experiment; never computes derived numbers, records "
            "raw counts/units and verbatim quotes for every numeric claim. "
            "(3) SKEPTIC — checks each numeric claim against its quote "
            "(group conflation, unit mismatch, impossible ranges); verdicts "
            "ok / unverified (needs human) / contradicted (dropped). "
            "Output data/papers/vaccine_claims.jsonl."),
    "fields": [
        # identity & stage tags
        "paper_id", "stages",
        # vaccine
        "platform (enum)", "backbone_or_vector", "antigens", "valency",
        "adjuvant", "adjuvant_target",
        "delivery_route (enum)", "dose_schedule", "age_at_vaccination",
        "days_last_dose_to_challenge",
        # host
        "species (binomial)", "wild_or_domestic",
        # challenge
        "challenge_strain", "challenge_clade", "challenge_dose",
        "challenge_route", "homologous_or_heterologous",
        # outcomes — always per group, never merged
        "n_vaccinated", "n_control",
        "mortality_vaccinated (count/total as reported)", "mortality_control",
        "shed_titer_vaccinated", "shed_titer_control", "shed_unit (as reported)",
        "shed_duration_vaccinated", "shed_duration_control", "swab_site",
        "transmission_assessed (enum)", "transmission_result",
        "hi_gmt_vaccinated", "hi_gmt_control", "seroconversion_pct (as reported)",
        "mucosal_iga", "t_cell_response", "duration_of_immunity_days",
        # surveillance
        "diva_compatible (enum)", "diva_strategy",
        # genetics
        "mhc_haplotype_effects", "genes_mentioned [{gene, context (enum)}]",
        # study quality
        "design (n, control, blind)", "field_or_lab", "verdict", "quotes",
    ],
    "enums": {
        "platform": ["inactivated", "laiv", "vectored_hvt", "vectored_ndv",
                     "vectored_fowlpox", "vectored_mva", "mrna", "dna",
                     "subunit", "nanoparticle", "vlp", "other"],
        "delivery_route": ["in_ovo", "spray", "drinking_water", "injection_im",
                           "injection_sc", "oral", "other"],
        "transmission_assessed": ["chain", "contact", "sentinel", "inferred_from_shedding", "none"],
        "diva_compatible": ["yes", "no", "partial"],
        "gene_context": ["adjuvant_target", "response_marker", "haplotype_effect",
                         "correlate_of_protection", "vector_component", "other"],
    },
    "cross_cutting_questions": [
        "Which platforms block TRANSMISSION (not just clinical disease) — and in which species?",
        "Does antigenic mismatch shift protection from transmission-blocking to silent-shedding?",
        "MHC-B haplotype (B21/B13…) as predictor of vaccine response quality — chicken, and transferable?",
        "Do conserved-antigen designs (M2e, NP) buy breadth at the cost of potency in birds?",
        "What did the condor and king-penguin programs actually measure — real-world effectiveness data?",
        "Immune imprinting in birds: does prior LPAI exposure blunt H5 vaccine response (and vice versa)?",
        "Sex/Z-linked asymmetry in vaccine response (corpus: sex-differences paper) — management lever?",
        "For a kākāpō program: which platform/delivery/DIVA stack is closest to deployable, and what's missing?",
        "Where has vaccination changed circulating-virus evolution (antigenic cartography evidence)?",
        "Spray/mucosal vaccines for IgA: transmission-correlation evidence?",
    ],
}


# Development tracker: candidates, licensed products, deployed programs.
# Anchored to corpus papers (verified by rg); web_verified flags what still
# needs a live check once /web-tools keys are configured.
TRACKER = [
    {"name": "Inactivated H5 whole-virus vaccines", "platform": "inactivated",
     "antigen": "HA (whole virus, oil-emulsion)", "species": ["chicken", "duck"],
     "status": "licensed+deployed",
     "region": "China, Egypt, Indonesia, Vietnam, Mexico (endemic-country national programs)",
     "diva": "no — requires companion marker strategy",
     "corpus": ["practical_aspects_poultry_2022", "vaccine_efficacy_meta2024"],
     "note": "The global workhorse. Efficacy tracks antigenic match; mismatch → clinical protection with continued shedding."},
    {"name": "HVT-H5 vectored (Vectormune HVT-AI, Ceva)", "platform": "vectored (HVT)",
     "antigen": "HA insert on herpesvirus-of-turkey backbone", "species": ["chicken"],
     "status": "licensed",
     "region": "US, Egypt, Mexico (hatchery in-ovo use)",
     "diva": "yes — non-influenza backbone (AI-vaccinated birds test NP-negative unless infected)",
     "corpus": ["herpesvirus_turkey_vectored_vaccine_2024", "spackman_2024_efficacy_commercial_2024"],
     "note": "Single dose, in-ovo compatible, no interference from maternal antibodies to flu.", "web_verified": False},
    {"name": "Vaxxitek HVT+H5 (Boehringer Ingelheim)", "platform": "vectored (HVT)",
     "antigen": "HA insert (H5)", "species": ["chicken"], "status": "licensed",
     "region": "multiple", "diva": "yes — vector backbone",
     "corpus": ["smith_gannet2024_45"], "note": "Competing HVT-H5 product.", "web_verified": False},
    {"name": "Egypt national H5 vaccination program", "platform": "inactivated (various)",
     "antigen": "HA", "species": ["chicken", "duck", "turkey"],
     "status": "deployed program (2006→)", "region": "Egypt",
     "diva": "mixed — sentinel/monitoring schemes",
     "corpus": ["practical_aspects_poultry_2022"],
     "note": "Longest-running national program; vaccine-matching vs clade 2.2.2.x drift documented."},
    {"name": "Mexico H7N3 DIVA campaign", "platform": "inactivated", "antigen": "HA (H7N3)",
     "species": ["chicken"], "status": "historical (2012–14, eliminated)", "region": "Mexico (Jalisco)",
     "diva": "yes — homologous vaccine + NP-based unvaccinated-sentinel design",
     "corpus": ["smith_gannet2024_48", "smith_gannet2024_38"],
     "note": "The canonical proof that vaccination + DIVA + surveillance can END an HPAI epizootic."},
    {"name": "France duck H5 vaccination campaign", "platform": "inactivated (H5)",
     "antigen": "HA", "species": ["duck"], "status": "deployed program (2023→)",
     "region": "France (foie-gras sector)", "diva": "yes — program design includes monitoring",
     "corpus": ["france_duck_vaccination2025", "jinha2025"],
     "note": "First EU HPAI routine vaccination campaign; the policy-shift test case."},
    {"name": "California condor emergency vaccination", "platform": "inactivated (licensed AI vaccine)",
     "antigen": "HA", "species": ["Gymnogyps californianus"],
     "status": "deployed program (2023→)", "region": "US (southwest populations)",
     "diva": "n/a — closed managed population",
     "corpus": ["condor_vaccination2025"],
     "note": "First US wild-bird HPAI vaccination, after the 2023 die-off (21 deaths). Individual-dose workflow."},
    {"name": "King penguin vaccination trial", "platform": "inactivated", "antigen": "HA",
     "species": ["Aptenodytes patagonicus"], "status": "field trial",
     "region": "sub-Antarctic (Crozet)", "diva": "n/a",
     "corpus": ["king_penguin_vaccine2026"],
     "note": "Wild-colony individual dosing — the closest wildlife template for NZ taonga programs."},
    {"name": "Bovine H5 vaccine (US, conditional-license landscape)", "platform": "inactivated",
     "antigen": "HA (H5 clade 2.3.4.4b)", "species": ["Bos taurus"], "status": "licensed (conditional) → deployment decisions pending",
     "region": "US", "diva": "n/a — dairy monitoring",
     "corpus": ["cattle_mrna_vaccine2026", "wisconsin_cattle_d1.1_2026"],
     "note": "Dairy-cattle spillover response; vaccination-to-prevent-milk-shedding economics.", "web_verified": False},
    {"name": "mRNA HA vaccine (poultry model)", "platform": "mRNA", "antigen": "HA",
     "species": ["chicken"], "status": "preclinical",
     "region": "lab", "diva": "possible — no flu proteins in vaccine",
     "corpus": ["mrna_vaccine_encoding_hemagglutinin_2024"],
     "note": "Update-speed promise vs 20B-dose/yr cost barrier (gap V5)."},
    {"name": "Cattle mRNA H5 candidate", "platform": "mRNA", "antigen": "HA",
     "species": ["Bos taurus"], "status": "trial",
     "region": "US", "diva": "possible",
     "corpus": ["cattle_mrna_vaccine2026"], "note": "Mammary-tropism rationale."},
    {"name": "Pan-multiepitope DNA vaccine", "platform": "DNA", "antigen": "conserved multiepitope (NP/M2e/HA epitopes)",
     "species": ["chicken", "duck"], "status": "preclinical",
     "region": "lab", "diva": "possible",
     "corpus": ["pan_multiepitope_dna_vaccine_2024"], "note": "Breadth-first design; IL15 genetic adjuvant angle in corpus."},
    {"name": "M2e nanovaccine", "platform": "nanoparticle subunit", "antigen": "M2e (conserved ion-channel ectodomain)",
     "species": ["chicken"], "status": "preclinical",
     "region": "lab", "diva": "yes — not in circulating virions assayed by standard tests",
     "corpus": ["m2e_nanovaccines_supplemented_2024"], "note": "Universal-antigen play; weak immunogenicity alone → carrier/adjuvant engineering."},
    {"name": "Inactivated zoonotic H5N8 (EU-oriented)", "platform": "inactivated", "antigen": "HA (H5N8)",
     "species": ["chicken"], "status": "preclinical/trial",
     "region": "EU", "diva": "no",
     "corpus": ["inactivated_zoonotic_h5n8_vaccine_2025"], "note": "Reverse-genetics-derived seed; zoonosis-risk framing."},
    {"name": "LAIV (live-attenuated influenza, NS-segment designs)", "platform": "LAIV",
     "antigen": "whole virus (attenuated)", "species": ["chicken", "duck"],
     "status": "research",
     "region": "lab", "diva": "no",
     "corpus": ["single_cell_transcriptomics_2025", "sex_differences_vaccine_induced_2026"],
     "note": "Mucosal/CD8-strong; recombination & trade-policy barriers; TGFB1/LAIV signature in corpus."},
]

# How vaccination couples into the spread model (numbers pending V2 mining).
SPREAD_INTEGRATION = {
    "_doc": "Vaccination is a lever on the spread model, not a stage of it: it "
            "scales transmission terms. Quantities land when the LLM mining "
            "pass extracts transmission-block efficacy (gap V2).",
    "links": [
        {"spread_stage": "amplification",
         "mechanism": "coverage × transmission-efficacy lowers effective shedding load in poultry amplification hosts",
         "formula": "R_eff ≈ R₀ × (1 − efficacy_transmission × coverage)"},
        {"spread_stage": "anthropogenic",
         "mechanism": "vaccinated-poultry movement changes trade-risk calculus; DIVA-compatibility determines whether surveillance can see through the program"},
        {"spread_stage": "spillover",
         "mechanism": "reduced poultry load lowers spillover rate into mammals and wild birds"},
        {"spread_stage": "regional_risk",
         "mechanism": "pre-emptive protection of closed threatened populations (kākāpō planner on this page) — no outbreak-driven vaccination option for closed populations"},
    ],
    "evidence_status": "formula standard; efficacy numbers = mining target (V2)",
}


# Load-bearing factual claims per stage. Each claim carries an rg probe; the
# builder resolves it to corpus papers (backed_by). Claims resolving to ZERO
# papers fail the audit (audit_vaccine_claims.py) — nothing ships uncited.
CLAIMS = {
    "platforms": [
        {"claim": "Inactivated whole-virus vaccines are the deployed workhorse of national programs", "probe": "inactivated vaccine"},
        {"claim": "HVT/NDV/fowlpox-vectored vaccines are licensed and DIVA-friendly via non-flu backbones", "probe": "vectored.*DIVA|DIVA.*vector"},
        {"claim": "mRNA, DNA and M2e-nanoparticle designs pursue conserved-antigen breadth", "probe": "mRNA vaccine|DNA vaccine|M2e"},
    ],
    "antigen": [
        {"claim": "HA is the neutralization target; antigenic mismatch is the classic efficacy failure mode", "probe": "antigenic match|mismatch"},
        {"claim": "NP/M1 are conserved T-cell targets and DIVA markers; M2e conserved but weakly immunogenic alone", "probe": "M2e"},
    ],
    "delivery": [
        {"claim": "Mass application vaccinates ≈24 billion chickens annually worldwide", "probe": "24 billion|billion chickens"},
        {"claim": "In-ovo injection is routine hatchery practice", "probe": "in ovo"},
        {"claim": "Route sets the compartment primed — mucosal IgA vs systemic IgY", "probe": "mucosal IgA|mucosal vaccination"},
    ],
    "adjuvant": [
        {"claim": "Oil emulsions are standard for inactivated poultry vaccines", "probe": "oil emulsion|mineral oil"},
        {"claim": "CpG motifs are sensed by the avian TLR21 — TLR9 is absent in birds", "probe": "TLR21.*CpG|CpG.*TLR21|absence of TLR9|lost.*TLR9"},
    ],
    "response": [
        {"claim": "Chicken BF2 haplotype B21 associates with both H5N1 survival and vaccine response", "probe": "B21"},
        {"claim": "Maternal IgY transfers to egg yolk and interferes with chick vaccination", "probe": "maternal antibod|maternal IgY"},
        {"claim": "Immune imprinting shapes later responses to drifted strains", "probe": "imprinting|original antigenic sin"},
    ],
    "protection": [
        {"claim": "Vaccines can protect clinically while permitting shedding and onward transmission", "probe": "vaccinated birds.*shed|shedding.*vaccin|silent"},
        {"claim": "Meta-analytic HPAI vaccine-efficacy estimates exist, varying by platform and match", "probe": "meta.analy"},
    ],
    "diva": [
        {"claim": "DIVA strategies: marker antigens, NP-ELISA differentiation, sentinel birds", "probe": "DIVA"},
        {"claim": "Without DIVA, trade partners cannot distinguish vaccinated-clean from silently infected flocks — export economics keep countries unvaccinated", "probe": "trade.*vaccin|export.*vaccin|vaccin.*export"},
    ],
    "deployment": [
        {"claim": "Endemic-country national programs run in China, Egypt, Indonesia, Vietnam, Mexico", "probe": "vaccination programme|national vaccination|mass vaccination"},
        {"claim": "The EU shifted toward vaccination from 2023 — France's duck campaign is the test case", "probe": "France.*vaccin|vaccin.*France|French duck"},
        {"claim": "California condors were the first US wild birds vaccinated against HPAI after the 2023 die-off (~21 deaths)", "probe": "condor.*vaccin|vaccin.*condor|21 .*condor"},
        {"claim": "King penguins: individual-dose field trial in sub-Antarctic colonies", "probe": "penguin.*vaccin|vaccin.*penguin"},
    ],
    "escape": [
        {"claim": "Chinese Re-series vaccination selected for antigenic drift in circulating strains", "probe": "Re-[0-9]|vaccine-induced antigenic drift|vaccine-driven"},
        {"claim": "Multivalent updates and antigenic-cartography-guided strain selection are the mitigations", "probe": "antigenic cartography"},
    ],
}


def resolve_claims(stage_id: str) -> list[dict]:
    """Resolve each claim's probe (a REGEX) → corpus papers, top 3 by hits.
    Direct rg — probes are regex, unlike scan_stage's literal keywords."""
    out = []
    for c in CLAIMS.get(stage_id, []):
        try:
            res = subprocess.run(
                ["rg", "-i", "-c", "-e", c["probe"], "--glob", "*.md", str(MD_DIR)],
                capture_output=True, text=True, timeout=120).stdout
        except FileNotFoundError:
            res = ""
        hits = []
        for line in res.splitlines():
            path, _, n = line.rpartition(":")
            stem = Path(path).stem
            if not stem.startswith("_"):
                hits.append((stem, int(n)))
        hits.sort(key=lambda kv: -kv[1])
        rec = {"claim": c["claim"], "backed_by": [p for p, _ in hits[:3]],
               "backing_count": len(hits),
               # md5[:12] i18n key (eh/fh convention) — Vaccines.svelte ft(ch)
               "ch": hashlib.md5(c["claim"].encode("utf-8")).hexdigest()[:12]}
        if not hits:
            print(f"  ⚠ UNSOURCED CLAIM [{stage_id}]: {c['claim'][:70]}")
        out.append(rec)
    return out


def scan_stage(keywords: list[str], top: int = 8) -> dict:
    """rg the markdown corpus for the stage keywords → per-paper hit counts."""
    pattern = "|".join(re.escape(k) for k in keywords)
    try:
        out = subprocess.run(
            ["rg", "-i", "-c", "-e", pattern, "--glob", "*.md", str(MD_DIR)],
            capture_output=True, text=True, timeout=120).stdout
    except FileNotFoundError:
        return {"count": 0, "papers": []}
    hits = []
    for line in out.splitlines():
        path, _, n = line.rpartition(":")
        stem = Path(path).stem
        if stem.startswith("_dup") or stem.startswith("_"):
            continue
        hits.append((stem, int(n)))
    hits.sort(key=lambda kv: -kv[1])
    return {"count": len(hits), "papers": hits[:top]}


def merge_verified(stage: dict) -> dict:
    """When the LLM has run: count vaccine_claims.jsonl records tagged
    for this stage and upgrade the evidence tier keyword → verified."""
    if not CLAIMS_JSONL.exists():
        return {"claims": 0}
    n = 0
    for line in CLAIMS_JSONL.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if stage["id"] in (rec.get("stages") or []):
            n += 1
    return {"claims": n}


def extracted_evidence() -> dict:
    """Per-stage PAPER_EXTRACTED evidence from the shipped synthesis
    artifacts (vaccine outcomes/campaigns + spread extraction). Counts
    and distributions only — curation stays authoritative for
    definitions."""
    import polars as pl

    out: dict[str, dict] = {}
    vo = ROOT / "data" / "model" / "vaccine_outcomes.json"
    vc = ROOT / "data" / "model" / "vaccine_campaigns.json"
    claims_path = ROOT / "data" / "papers" / "vaccine_claims.jsonl"
    spread = ROOT / "data" / "papers" / "paper_spread.parquet"
    vo_d = json.loads(vo.read_text()) if vo.exists() else {}
    vc_d = json.loads(vc.read_text()) if vc.exists() else {}

    plat, antigens, delivery, adjuvants = {}, {}, {}, {}
    n_sero = n_gmt = n_tcell = n_efficacy = 0
    if claims_path.exists():
        for line in claims_path.read_text().splitlines():
            try:
                c = json.loads(line)
            except Exception:
                continue
            p = c.get("platform")
            if p:
                plat[p] = plat.get(p, 0) + 1
            for a in (c.get("antigens") if isinstance(c.get("antigens"), list)
                      else [c.get("antigens")] if c.get("antigens") else []):
                k = str(a).strip()[:24]
                if len(k) > 2:
                    antigens[k] = antigens.get(k, 0) + 1
            d = c.get("delivery_route")
            if d:
                delivery[str(d).strip()[:24]] = delivery.get(str(d).strip()[:24], 0) + 1
            adj = c.get("adjuvant")
            adj_list = adj if isinstance(adj, list) else ([adj] if adj else [])
            for a in adj_list:
                k = str(a).strip()[:24]
                if len(k) > 2:
                    adjuvants[k] = adjuvants.get(k, 0) + 1
            n_sero += bool(c.get("seroconversion_pct"))
            n_gmt += bool(c.get("hi_gmt_vaccinated"))
            n_tcell += bool(c.get("t_cell_response"))
            n_efficacy += bool(c.get("mortality_vaccinated") is not None
                               or c.get("mortality_control") is not None)
    vp = vo_d.get("platforms", {})
    out["platforms"] = {"claims_by_platform": plat}
    out["antigen"] = {"antigen_mentions": dict(sorted(antigens.items(),
                                                       key=lambda kv: -kv[1])[:8])}
    out["delivery"] = {"routes": dict(sorted(delivery.items(),
                                              key=lambda kv: -kv[1])[:6])}
    out["adjuvant"] = {"adjuvants": dict(sorted(adjuvants.items(),
                                                key=lambda kv: -kv[1])[:6])}
    out["response"] = {"seroconversion_reported": n_sero,
                       "hi_gmt_reported": n_gmt,
                       "t_cell_reported": n_tcell}
    out["protection"] = {
        "efficacy_rows": len(vp.get("efficacy_rows", [])),
        "field_outcomes": vo_d.get("vaccination", {}).get("outcomes", {}),
    }
    out["diva"] = {"diva_compatible_claims": vp.get("diva_compatible", 0),
                   "diva_stated_campaigns": vc_d.get("diva", {}).get("true", 0)}
    out["deployment"] = {
        "campaigns": len(vc_d.get("campaigns", [])),
        "by_sector": vc_d.get("by_sector", {}),
        "regions": len(vc_d.get("by_region", {})),
    }
    if spread.exists():
        df = pl.read_parquet(spread).filter(
            pl.col("section") == "adaptation_mutations")
        n_escape = 0
        escape_papers = set()
        for r in df.iter_rows(named=True):
            if any(k in (r["payload"] or "").lower()
                   for k in ("vaccin", "escape", "antigenic")):
                n_escape += 1
                escape_papers.add(r["paper_id"])
        out["escape"] = {"adaptation_items": n_escape,
                        "papers": len(escape_papers)}
    return out


def main() -> None:
    extracted = extracted_evidence()
    stages = []
    for st in STAGES:
        stage = dict(st)
        scan = scan_stage(st["keywords"])
        merged = merge_verified(st)
        stage["evidence"] = {
            "tier": "verified" if merged["claims"] > 0 else "keyword",
            "candidate_papers": scan["count"],
            "top_papers": [{"paper": p, "hits": h} for p, h in scan["papers"]],
            **merged,
        }
        if st["id"] in extracted:
            stage["evidence"]["extracted"] = extracted[st["id"]]
        stage["claims_resolved"] = resolve_claims(st["id"])
        stages.append(stage)

    model = {
        "version": "0.1",
        "updated": str(date.today()),
        "source": "docs/MODEL_VACCINES.md",
        "_doc": ("Vaccine model v0.1 — skeleton with deterministic keyword-tier "
                 "evidence (literature LLM down). Stage curation is stable; "
                 "evidence badges upgrade keyword→verified when "
                 "mine_vaccines.py runs. Genes cross-link to #/genes/SYM."),
        "stages": stages,
        "gene_bridge": GENE_BRIDGE,
        "tracker": TRACKER,
        "spread_integration": SPREAD_INTEGRATION,
        "gaps": GAPS,
        "llm_plan": LLM_PLAN,
    }
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    for path in (MODEL, SHIPPED):
        path.write_text(json.dumps(model, indent=1, ensure_ascii=False))
    total = sum(s["evidence"]["candidate_papers"] for s in stages)
    n_claims = sum(s["evidence"]["claims"] for s in stages)
    print(f"vaccine model v{model['version']} → {len(stages)} stages, "
          f"{len(GENE_BRIDGE)} gene-bridge links, {len(TRACKER)} tracker entries, "
          f"{len(GAPS)} gaps, {n_claims} verified claims")
    for s in stages:
        ev = s["evidence"]
        print(f"  {s['id']:12} {ev['tier']:8} {ev['candidate_papers']:4} pp "
              f"{ev['claims']:3} claims (top: "
              f"{ev['top_papers'][0]['paper'] if ev['top_papers'] else '—'})")
    print(f"wrote {MODEL}\nwrote {SHIPPED}")


if __name__ == "__main__":
    main()
