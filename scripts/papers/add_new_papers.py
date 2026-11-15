#!/usr/bin/env python3
"""Add new papers discovered from web search."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"

# New papers to add (from web search 2026-08-26)
NEW_PAPERS = [
    {
        "id": "cross_species_adaptation2026",
        "title": "Evolution of H5N1 Cross-Species Transmission: Adaptive Mutations Driving Avian-to-Human Infection",
        "authors": "Man Y, et al.",
        "journal": "Advanced Genetics (Wiley)",
        "year": 2026,
        "doi": "10.1002/ggn2.202500051",
        "url": "https://advanced.onlinelibrary.wiley.com/doi/10.1002/ggn2.202500051",
        "topics": ["Cross-Species Transmission", "PB2 Mutations", "Host Genomics"],
        "category": "Cross-Species Transmission",
        "summary": "Reviews adaptive mutations driving avian-to-human H5N1 transmission, focusing on PB2 and HA changes.",
        "cited_for": "Cross-species transmission mechanisms"
    },
    {
        "id": "pb2_anp32_taylor2026",
        "title": "The mouse-lethal H5N1 influenza virus carrying the PB2-384L/443R/460M characteristics acquired in avian hosts can effectively utilize human ANP32A/B proteins",
        "authors": "Li Y, et al.",
        "journal": "Emerging Microbes & Infections",
        "year": 2026,
        "doi": "10.1080/22221751.2026.2685917",
        "url": "https://www.tandfonline.com/doi/full/10.1080/22221751.2026.2685917",
        "topics": ["ANP32A", "ANP32B", "PB2 Mutations", "Host Genomics"],
        "category": "Host Genomics",
        "summary": "Demonstrates that novel PB2 mutations (384L/443R/460M) acquired in birds enable effective use of human ANP32A/B proteins.",
        "cited_for": "Novel PB2-ANP32 interactions"
    },
    {
        "id": "gannet_behaviour_survival2026",
        "title": "Effects of highly pathogenic avian influenza on the behaviour and survival of a colonial breeding seabird",
        "authors": "Lane JV, et al.",
        "journal": "Proceedings B Royal Society",
        "year": 2026,
        "doi": "10.1098/rspb.2026.0128",
        "url": "https://royalsocietypublishing.org/rspb/article/293/2073/20260128/482271/Effects-of-highly-pathogenic-avian-influenza-on",
        "topics": ["Seabirds", "Northern Gannet", "Behavior", "Survival"],
        "category": "Seabirds",
        "summary": "Studies behavioral changes and survival impacts in northern gannets during HPAI outbreaks. Confirms antibody responses in survivors.",
        "cited_for": "Gannet survival and immunity"
    },
    {
        "id": "seabird_eggs_antibodies2025",
        "title": "Examining avian influenza virus exposure in seabirds of the northwest Atlantic in 2022 and 2023 via antibodies in eggs",
        "authors": "Pratter I, et al.",
        "journal": "FACETS",
        "year": 2025,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11858004/",
        "topics": ["Seabirds", "Antibodies", "Surveillance", "Atlantic"],
        "category": "Seabirds",
        "summary": "Assessed antibodies against AIV in 523 eggs from 11 seabird species. American common eiders had highest prevalence.",
        "cited_for": "Seabird exposure assessment methods"
    },
    {
        "id": "france_seabirds_h5n12023",
        "title": "Highly Pathogenic Clade 2.3.4.4b H5N1 Influenza Virus in Seabirds in France, 2022-2023",
        "authors": "Briand FX, et al.",
        "journal": "Emerging Infectious Diseases",
        "year": 2025,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12016834/",
        "topics": ["Seabirds", "France", "Genotypes", "Larids", "Sulids"],
        "category": "Seabirds",
        "summary": "Characterized genotypes EA-2020-C in gannets and EA-2022-BB in gulls. Demonstrates genotype variation by host species.",
        "cited_for": "Genotype-host associations in seabirds"
    },
    {
        "id": "king_penguin_vaccine2026",
        "title": "Vaccination against H5 HP avian influenza virus leads to persistent immune response in wild king penguins",
        "authors": "Viblanc VA, et al.",
        "journal": "Nature Communications",
        "year": 2026,
        "doi": "10.1038/s41467-026-69094-9",
        "url": "https://www.nature.com/articles/s41467-026-69094-9",
        "topics": ["Vaccination", "Penguins", "Immune Response", "Conservation"],
        "category": "Conservation",
        "summary": "Self-amplifying mRNA vaccine against H5 clade 2.3.4.4b tested in wild king penguin chicks. Showed persistent immune response over 250 days.",
        "cited_for": "Wild bird vaccination feasibility"
    },
    {
        "id": "europe_autumn2025_unprecedented",
        "title": "Unprecedented high level of highly pathogenic avian influenza in wild birds in Europe during the 2025 autumn migration",
        "authors": "EFSA/ECDC",
        "journal": "Eurosurveillance",
        "year": 2025,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12648623/",
        "topics": ["Wild Birds", "Migration", "Europe", "Surveillance"],
        "category": "Surveillance",
        "summary": "1,443 HPAI detections in wild birds across 26 European countries - four times higher than 2024. EA-2024-DI.2.1 dominant genotype.",
        "cited_for": "2025 European outbreak scale"
    },
    {
        "id": "hokkaido_diversity2025",
        "title": "Genetic Diversity of Highly Pathogenic Avian Influenza Viruses Isolated in Hokkaido, Japan, During Winter 2024-2025",
        "authors": "Isoda N, et al.",
        "journal": "Influenza and Other Respiratory Viruses",
        "year": 2025,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12472925/",
        "topics": ["Wild Birds", "Japan", "Genomics", "Marine Mammals"],
        "category": "Wild Birds",
        "summary": "HPAIVs from Hokkaido seabirds were genetically related to strains in marine mammals on the eastern coast. Shows wildlife-to-mammal links.",
        "cited_for": "Japan seabird-mammal viral linkage"
    },
    {
        "id": "cattle_evolution_biorxiv2026",
        "title": "The emergence and molecular evolution of H5N1 influenza viruses in United States dairy cattle",
        "authors": "Worobey M, et al.",
        "journal": "bioRxiv (preprint)",
        "year": 2026,
        "doi": "10.64898/2026.03.30.713641",
        "url": "https://www.biorxiv.org/content/10.64898/2026.03.30.713641v1",
        "topics": ["Cattle", "Molecular Evolution", "Genomics", "USA"],
        "category": "Cross-Species Transmission",
        "summary": "Comprehensive analysis of H5N1 molecular evolution in US dairy cattle. Details emergence of B3.13 and D1.1 genotypes.",
        "cited_for": "Cattle outbreak evolutionary dynamics"
    },
    {
        "id": "cattle_emergence_review2025",
        "title": "The emergence of highly pathogenic avian influenza H5N1 in dairy cattle: implications for public health, animal health, and pandemic preparedness",
        "authors": "Nichols J, et al.",
        "journal": "Animal Frontiers",
        "year": 2025,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12321667/",
        "topics": ["Cattle", "Public Health", "Pandemic Preparedness"],
        "category": "Cross-Species Transmission",
        "summary": "Review of H5N1 emergence in dairy cattle with public health and pandemic preparedness implications.",
        "cited_for": "Cattle outbreak review"
    },
    {
        "id": "cattle_genomic_char2024",
        "title": "Genomic characterization of highly pathogenic avian influenza A H5N1 virus newly emerged in dairy cattle",
        "authors": "Nguyen TQ, et al.",
        "journal": "Emerging Microbes & Infections",
        "year": 2024,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11271078/",
        "topics": ["Cattle", "Genomics", "B3.13 Genotype"],
        "category": "Cross-Species Transmission",
        "summary": "Early genomic characterization of H5N1 B3.13 genotype in US dairy cattle outbreak.",
        "cited_for": "Initial cattle outbreak genomics"
    },
    {
        "id": "cattle_texas2024",
        "title": "Avian Influenza A(H5N1) Virus among Dairy Cattle, Texas, USA",
        "authors": "Caserta LC, et al.",
        "journal": "Emerging Infectious Diseases",
        "year": 2024,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11210641/",
        "topics": ["Cattle", "Texas", "Outbreak", "Genomics"],
        "category": "Cross-Species Transmission",
        "summary": "Initial characterization of H5N1 in Texas dairy cattle. B3.13 genotype identified.",
        "cited_for": "Texas cattle outbreak"
    },
    {
        "id": "mammal_spillovers_signatures2025",
        "title": "Distinctive viral genome signatures are linked to repeated mammalian spillovers of H5N1 in North America",
        "authors": "Shu B, et al.",
        "journal": "bioRxiv (preprint)",
        "year": 2025,
        "doi": "10.64898/2025.12.09.693147",
        "url": "https://www.biorxiv.org/content/10.64898/2025.12.09.693147.full.pdf",
        "topics": ["Mammal Spillover", "Genomics", "North America"],
        "category": "Cross-Species Transmission",
        "summary": "Identifies distinctive genomic signatures associated with repeated mammalian spillover events in North America.",
        "cited_for": "Spillover genomic signatures"
    },
    {
        "id": "mink_spain2022",
        "title": "Highly pathogenic avian influenza A(H5N1) virus infection in farmed minks, Spain, October 2022",
        "authors": "Aguero M, et al.",
        "journal": "Eurosurveillance",
        "year": 2023,
        "doi": None,
        "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9853945/",
        "topics": ["Mink", "Spain", "Mammal Transmission"],
        "category": "Cross-Species Transmission",
        "summary": "First documented H5N1 outbreak in farmed minks with evidence of mammal-to-mammal transmission.",
        "cited_for": "Mink outbreak - mammal transmission concern"
    }
]


def main():
    # Load existing papers
    with open(PAPERS_JSON) as f:
        data = json.load(f)

    existing_ids = {p["id"] for p in data["papers"]}

    # Add new papers
    added = 0
    for paper in NEW_PAPERS:
        if paper["id"] not in existing_ids:
            data["papers"].append(paper)
            print(f"Added: {paper['id']}")
            added += 1
        else:
            print(f"Already exists: {paper['id']}")

    # Save updated data
    with open(PAPERS_JSON, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nAdded {added} new papers. Total: {len(data['papers'])}")


if __name__ == "__main__":
    main()
