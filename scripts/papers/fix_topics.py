#!/usr/bin/env python3
"""
Topic normalization + generation (D66):
1. Merge singular/plural duplicates (Duck→Ducks, Chicken→Chickens)
2. Generate topics for papers missing them (501 papers)
   Deterministic from species_focus + category + title keywords,
   with optional LLM for stubborn cases.

Usage: pixi run python scripts/papers/fix_topics.py [--llm]
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"

# Canonical topic mapping: singular → plural, variants → standard
TOPIC_MERGE = {
    "Duck": "Ducks", "Chicken": "Chickens", "Turkey": "Turkeys",
    "PB2 Mutation": "PB2 Mutations", "Seabird": "Seabirds",
    "Raptor": "Raptors", "Mammal": "Mammals", "Virus": "Viruses",
    "Vaccine": "Vaccination", "Wild Bird": "Wild Birds",
    "Marine Mammal": "Marine Mammals",
    "Host Genomic": "Host Genomics",
}

# Standard topic vocabulary for generation
SPECIES_TOPICS = {
    "chicken": "Chickens", "duck": "Ducks", "turkey": "Turkeys",
    "goose": "Geese", "swan": "Swans", "quail": "Quail",
    "gallus gallus": "Chickens", "anas platyrhynchos": "Ducks",
    "meleagris gallopavo": "Turkeys",
    "cattle": "Cattle", "bovine": "Cattle", "cow": "Cattle", "dairy": "Cattle",
    "cat": "Cats", "feline": "Cats", "dog": "Dogs", "canine": "Dogs",
    "fox": "Foxes", "mink": "Mink", "ferret": "Ferrets",
    "mouse": "Mice", "murine": "Mice", "swine": "Swine", "pig": "Swine", "porcine": "Swine",
    "human": "Humans", "patient": "Humans",
    "sea lion": "Marine Mammals", "seal": "Marine Mammals", "dolphin": "Marine Mammals",
    "whale": "Marine Mammals",
    "gull": "Gulls", "tern": "Terns", "pelican": "Pelicans",
    "cormorant": "Cormorants", "skua": "Skuas", "gannet": "Gannets",
    "eagle": "Raptors", "falcon": "Raptors", "hawk": "Raptors", "owl": "Raptors",
    "vulture": "Raptors",
    "kakapo": "Kākāpō", "kiwi": "Kiwi", "kea": "Kea", "takahe": "Takahē",
    "penguin": "Penguins", "parrot": "Parrots", "passerine": "Songbirds",
    "songbird": "Songbirds", "shorebird": "Shorebirds", "wader": "Shorebirds",
    "waterfowl": "Waterfowl", "poultry": "Poultry",
}

CATEGORY_TOPICS = {
    "Immunology": "Innate Immunity",
    "Pathogenesis": "Pathogenesis",
    "Epidemiology": "Epidemiology",
    "Avian Influenza": "Avian Influenza",
    "Mammalian Spillover": "Mammalian Spillover",
    "Host Genomics": "Host Genomics",
    "Vaccines": "Vaccination",
    "Wild Birds": "Wild Birds",
    "Poultry": "Poultry",
    "Viral Evolution": "Viral Evolution",
    "Cross-species Transmission": "Cross-Species",
    "Human Infection": "Humans",
    "Methods": "Methods",
}

GENE_TOPICS = {
    "pb2": "PB2", "ha": "Hemagglutinin", "na": "Neuraminidase",
    "ns1": "NS1", "m1": "Matrix Protein", "anp32": "ANP32",
    "rig-i": "RIG-I", "rige-i": "RIG-I", "ddx58": "RIG-I",
    "mda5": "MDA5", "ifih1": "MDA5", "mx1": "MX1",
    "ifitm": "IFITM", "oasl": "OASL", "stat1": "STAT1",
    "tlr": "TLRs", "mhc": "MHC", "ifn": "Interferon",
    "cytokine": "Cytokines", "interleukin": "Cytokines",
}

REGION_TOPICS = {
    "united states": "United States", "usa": "United States",
    "south korea": "South Korea", "korea": "South Korea",
    "china": "China", "japan": "Japan", "europe": "Europe",
    "africa": "Africa", "asia": "Asia", "south america": "South America",
    "australia": "Australia", "new zealand": "New Zealand",
    "antarctica": "Antarctica", "canada": "Canada", "mexico": "Mexico",
    "india": "India", "vietnam": "Vietnam", "thailand": "Thailand",
    "indonesia": "Indonesia", "egypt": "Egypt", "nigeria": "Nigeria",
    "united kingdom": "United Kingdom", "uk": "United Kingdom",
    "france": "France", "germany": "Germany", "spain": "Spain",
    "italy": "Italy", "netherlands": "Netherlands",
}


def normalize_topics(topics):
    """Merge singulars → plurals, dedupe."""
    seen = set()
    out = []
    for t in topics or []:
        t = TOPIC_MERGE.get(t, t)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def generate_topics(paper):
    """Deterministic topic generation from metadata."""
    topics = []
    blob = f"{paper.get('title') or ''} {paper.get('summary') or ''}".lower()
    species = " ".join(paper.get("species_focus") or []).lower()
    full = f"{blob} {species}"

    # Species topics (highest priority)
    for pattern, topic in SPECIES_TOPICS.items():
        if pattern in full and topic not in topics:
            topics.append(topic)

    # Category → topic
    cat = paper.get("category") or ""
    if cat in CATEGORY_TOPICS and CATEGORY_TOPICS[cat] not in topics:
        topics.append(CATEGORY_TOPICS[cat])

    # Gene topics
    for pattern, topic in GENE_TOPICS.items():
        if re.search(rf"\b{pattern}\b", full) and topic not in topics:
            topics.append(topic)

    # Region topics
    for pattern, topic in REGION_TOPICS.items():
        if pattern in full and topic not in topics:
            topics.append(topic)

    # Scope-based extras
    scope = paper.get("scope") or ""
    if scope == "avian-epi" and "Epidemiology" not in topics:
        topics.append("Epidemiology")
    if "review" in full and "Review" not in topics:
        topics.append("Review")
    if re.search(r"clade 2\.3\.4\.4", full) and "Clade 2.3.4.4b" not in topics:
        topics.append("Clade 2.3.4.4b")
    if re.search(r"surveillance|monitoring", full) and "Surveillance" not in topics:
        topics.append("Surveillance")

    # Cap at 8 topics
    return topics[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="LLM for papers still empty")
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    # Pass 1: normalize existing topics
    n_merged = 0
    for x in papers:
        old = x.get("topics") or []
        new = normalize_topics(old)
        if new != old:
            x["topics"] = new
            n_merged += 1

    # Pass 2: generate topics for papers missing them
    n_generated = 0
    for x in papers:
        if not x.get("topics") or len(x["topics"]) == 0:
            topics = generate_topics(x)
            if topics:
                x["topics"] = topics
                n_generated += 1

    PAPERS_JSON.write_text(json.dumps(data, indent=1))

    with_topics = sum(1 for x in papers if x.get("topics") and len(x["topics"]) > 0)
    print(f"normalized {n_merged} · generated {n_generated}")
    print(f"papers with topics: {with_topics}/{len(papers)} ({100*with_topics//len(papers)}%)")

    # Topic distribution
    all_topics = Counter()
    for x in papers:
        for t in x.get("topics") or []:
            all_topics[t] += 1
    print(f"\ntop 20 topics:")
    for t, n in all_topics.most_common(20):
        print(f"  {n:4d}  {t}")
    print(f"distinct topics: {len(all_topics)}")

    # remaining empty
    empty = [x["id"] for x in papers if not x.get("topics")]
    if empty:
        print(f"\nstill no topics: {len(empty)}")


if __name__ == "__main__":
    main()
