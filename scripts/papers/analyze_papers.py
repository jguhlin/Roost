#!/usr/bin/env python3
"""Analyze paper content to extract species, effects, and genes."""

import json
import re
from collections import Counter
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).parent.parent.parent
MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
OUTPUT_DIR = PROJECT_ROOT / "data" / "papers"
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"

# Known genes of interest for avian influenza host genomics
GENES = {
    # ANP32 family - species barrier
    "ANP32A": ["ANP32A", "ANP32-A", "acidic nuclear phosphoprotein 32A"],
    "ANP32B": ["ANP32B", "ANP32-B", "acidic nuclear phosphoprotein 32B"],
    "ANP32E": ["ANP32E", "ANP32-E"],
    # Innate immunity - RNA sensing
    "RIG-I": ["RIG-I", "DDX58", "RIG-1", "retinoic acid-inducible gene I"],
    "MDA5": ["MDA5", "IFIH1", "melanoma differentiation-associated gene 5"],
    "LGP2": ["LGP2", "DHX58"],
    # Mx genes - antiviral
    "MX1": ["MX1", "Mx1", "MxA", "myxovirus resistance 1"],
    "MX2": ["MX2", "Mx2", "MxB"],
    # Interferon system
    "IFITM1": ["IFITM1", "interferon-induced transmembrane protein 1"],
    "IFITM2": ["IFITM2"],
    "IFITM3": ["IFITM3"],
    "IFIT5": ["IFIT5", "ISG58"],
    "OAS": ["OAS1", "OAS2", "OAS3", "2'-5'-oligoadenylate synthetase"],
    "PKR": ["PKR", "EIF2AK2", "protein kinase R"],
    # TRIM family
    "TRIM25": ["TRIM25"],
    "TRIM32": ["TRIM32"],
    # Transcription factors
    "IRF3": ["IRF3", "interferon regulatory factor 3"],
    "IRF7": ["IRF7", "interferon regulatory factor 7"],
    "NF-kB": ["NF-κB", "NF-kB", "NFkB", "nuclear factor kappa B"],
    # Interferons
    "IFN-alpha": ["IFN-α", "IFN-alpha", "interferon alpha"],
    "IFN-beta": ["IFN-β", "IFN-beta", "interferon beta"],
    "IFN-gamma": ["IFN-γ", "IFN-gamma", "interferon gamma"],
    # Viral proteins
    "PB2": ["PB2", "polymerase basic 2"],
    "PB1": ["PB1", "polymerase basic 1"],
    "PA": ["PA gene", "polymerase acidic"],
    "NP": ["nucleoprotein", " NP "],
    "HA": ["hemagglutinin", " HA "],
    "NA": ["neuraminidase", " NA "],
    # Receptors
    "sialic acid": ["sialic acid", "Sia", "α2,3", "α2,6", "alpha-2,3", "alpha-2,6"],
}

# Avian species patterns
AVIAN_SPECIES = {
    # Waterfowl
    "Mallard": ["mallard", "Anas platyrhynchos"],
    "Mute Swan": ["mute swan", "Cygnus olor"],
    "Whooper Swan": ["whooper swan", "Cygnus cygnus"],
    "Greylag Goose": ["greylag", "Anser anser"],
    "Barnacle Goose": ["barnacle goose", "Branta leucopsis"],
    "Canada Goose": ["canada goose", "Branta canadensis"],
    # Seabirds
    "Northern Gannet": ["northern gannet", "gannet", "Morus bassanus"],
    "Sandwich Tern": ["sandwich tern", "Thalasseus sandvicensis"],
    "Common Tern": ["common tern", "Sterna hirundo"],
    "Black-legged Kittiwake": ["kittiwake", "Rissa tridactyla"],
    "Great Skua": ["great skua", "skua", "Stercorarius skua"],
    "Brown Skua": ["brown skua", "Stercorarius antarcticus"],
    "Common Murre": ["common murre", "guillemot", "Uria aalge"],
    "Atlantic Puffin": ["puffin", "Fratercula arctica"],
    # Raptors
    "White-tailed Eagle": ["white-tailed eagle", "Haliaeetus albicilla"],
    "Bald Eagle": ["bald eagle", "Haliaeetus leucocephalus"],
    "Red-tailed Hawk": ["red-tailed hawk", "Buteo jamaicensis"],
    "Griffon Vulture": ["griffon vulture", "Gyps fulvus"],
    "Great Horned Owl": ["great horned owl", "Bubo virginianus"],
    "Snowy Owl": ["snowy owl", "Bubo scandiacus"],
    # Corvids
    "American Crow": ["american crow", "crow", "Corvus brachyrhynchos"],
    "Common Raven": ["raven", "Corvus corax"],
    # Poultry
    "Chicken": ["chicken", "Gallus gallus", "poultry"],
    "Duck": ["duck", "domestic duck", "Anas domesticus", "Pekin duck"],
    "Turkey": ["turkey", "Meleagris gallopavo"],
    # Shorebirds
    "Sanderling": ["sanderling", "Calidris alba"],
}

# Mammalian species
MAMMAL_SPECIES = {
    "Human": ["human", "Homo sapiens", "patient", "farm worker"],
    "Cattle": ["cattle", "dairy cattle", "cow", "bovine", "Bos taurus"],
    "Domestic Cat": ["cat", "feline", "Felis catus", "domestic cat"],
    "Red Fox": ["red fox", "fox", "Vulpes vulpes"],
    "Harbor Seal": ["harbor seal", "Phoca vitulina"],
    "Grey Seal": ["grey seal", "gray seal", "Halichoerus grypus"],
    "Elephant Seal": ["elephant seal", "Mirounga"],
    "Sea Lion": ["sea lion", "Otaria", "Zalophus"],
    "Fur Seal": ["fur seal", "Callorhinus", "Arctocephalus"],
    "Caspian Seal": ["caspian seal", "Pusa caspica"],
    "Mink": ["mink", "Neovison vison"],
    "Swine": ["swine", "pig", "porcine", "Sus scrofa"],
}

# Effect keywords
EFFECTS = {
    "mortality": ["mortality", "death", "die-off", "mass death", "fatal", "lethal", "died"],
    "morbidity": ["morbidity", "illness", "sick", "clinical signs", "symptoms"],
    "neurological": ["neurological", "neurotropic", "encephalitis", "brain", "CNS", "ataxia"],
    "respiratory": ["respiratory", "pneumonia", "lung", "pulmonary"],
    "transmission": ["transmission", "spread", "spillover", "cross-species"],
    "mammal_adaptation": ["mammalian adaptation", "mammal-to-mammal", "PB2 mutation"],
    "population_decline": ["population decline", "breeding failure", "colony collapse"],
    "recovery": ["recovery", "immunity", "seroprevalence", "antibodies"],
}


def extract_mentions(text: str, patterns: dict) -> dict[str, int]:
    """Extract mentions of patterns in text."""
    mentions = {}
    text_lower = text.lower()

    for name, aliases in patterns.items():
        count = 0
        for alias in aliases:
            # Case-insensitive search for most, case-sensitive for abbreviations
            if alias.isupper() or len(alias) <= 4:
                count += len(re.findall(r'\b' + re.escape(alias) + r'\b', text))
            else:
                count += len(re.findall(r'\b' + re.escape(alias.lower()) + r'\b', text_lower))
        if count > 0:
            mentions[name] = count

    return mentions


def analyze_paper(md_path: Path) -> dict:
    """Analyze a single paper markdown file."""
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    paper_id = md_path.stem

    # Extract mentions
    genes = extract_mentions(text, GENES)
    avian = extract_mentions(text, AVIAN_SPECIES)
    mammals = extract_mentions(text, MAMMAL_SPECIES)
    effects = extract_mentions(text, EFFECTS)

    return {
        "paper_id": paper_id,
        "char_count": len(text),
        "genes_found": list(genes.keys()),
        "genes_counts": genes,
        "avian_species": list(avian.keys()),
        "avian_counts": avian,
        "mammal_species": list(mammals.keys()),
        "mammal_counts": mammals,
        "effects": list(effects.keys()),
        "effects_counts": effects,
        "has_genomics": len(genes) > 0,
        "has_species_data": len(avian) > 0 or len(mammals) > 0,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load paper metadata
    with open(PAPERS_JSON) as f:
        papers_meta = {p["id"]: p for p in json.load(f).get("papers", [])}

    # Analyze all markdown files
    md_files = sorted(MD_DIR.glob("*.md"))
    print(f"Analyzing {len(md_files)} markdown files...\n")

    results = []
    gene_totals = Counter()
    avian_totals = Counter()
    mammal_totals = Counter()
    effect_totals = Counter()

    for md_path in md_files:
        analysis = analyze_paper(md_path)
        paper_id = analysis["paper_id"]

        # Add metadata
        meta = papers_meta.get(paper_id, papers_meta.get(paper_id.replace("_", ""), {}))
        analysis["title"] = meta.get("title", "")
        analysis["category"] = meta.get("category", "")
        analysis["year"] = meta.get("year")

        results.append(analysis)

        # Aggregate counts
        gene_totals.update(analysis["genes_counts"])
        avian_totals.update(analysis["avian_counts"])
        mammal_totals.update(analysis["mammal_counts"])
        effect_totals.update(analysis["effects_counts"])

    # Create main analysis DataFrame
    df_records = []
    for r in results:
        df_records.append({
            "paper_id": r["paper_id"],
            "title": r["title"],
            "category": r["category"],
            "year": r["year"],
            "char_count": r["char_count"],
            "genes": ",".join(r["genes_found"]),
            "avian_species": ",".join(r["avian_species"]),
            "mammal_species": ",".join(r["mammal_species"]),
            "effects": ",".join(r["effects"]),
            "gene_count": len(r["genes_found"]),
            "species_count": len(r["avian_species"]) + len(r["mammal_species"]),
            "has_genomics": r["has_genomics"],
        })

    df = pl.DataFrame(df_records)
    df.write_parquet(OUTPUT_DIR / "paper_analysis.parquet")

    # Create gene summary
    gene_df = pl.DataFrame([
        {"gene": k, "total_mentions": v}
        for k, v in gene_totals.most_common()
    ])
    gene_df.write_parquet(OUTPUT_DIR / "gene_mentions.parquet")

    # Create species summary
    species_records = []
    for name, count in avian_totals.most_common():
        species_records.append({"species": name, "type": "avian", "mentions": count})
    for name, count in mammal_totals.most_common():
        species_records.append({"species": name, "type": "mammal", "mentions": count})
    species_df = pl.DataFrame(species_records)
    species_df.write_parquet(OUTPUT_DIR / "species_mentions.parquet")

    # Create effects summary
    effects_df = pl.DataFrame([
        {"effect": k, "mentions": v}
        for k, v in effect_totals.most_common()
    ])
    effects_df.write_parquet(OUTPUT_DIR / "effects_mentions.parquet")

    # Print summary
    print("=" * 60)
    print("PAPER ANALYSIS SUMMARY")
    print("=" * 60)

    print(f"\nTotal papers analyzed: {len(results)}")
    print(f"Papers with genomics content: {sum(1 for r in results if r['has_genomics'])}")
    print(f"Papers with species data: {sum(1 for r in results if r['has_species_data'])}")

    print("\n" + "=" * 60)
    print("TOP GENES MENTIONED")
    print("=" * 60)
    for gene, count in gene_totals.most_common(20):
        print(f"  {gene:15} {count:5} mentions")

    print("\n" + "=" * 60)
    print("TOP AVIAN SPECIES")
    print("=" * 60)
    for species, count in avian_totals.most_common(15):
        print(f"  {species:20} {count:5} mentions")

    print("\n" + "=" * 60)
    print("TOP MAMMAL SPECIES")
    print("=" * 60)
    for species, count in mammal_totals.most_common(10):
        print(f"  {species:20} {count:5} mentions")

    print("\n" + "=" * 60)
    print("EFFECTS DOCUMENTED")
    print("=" * 60)
    for effect, count in effect_totals.most_common():
        print(f"  {effect:20} {count:5} mentions")

    print("\n" + "=" * 60)
    print("PAPERS WITH MOST GENE CONTENT")
    print("=" * 60)
    genomics_papers = sorted(results, key=lambda x: len(x["genes_found"]), reverse=True)
    for p in genomics_papers[:10]:
        if p["genes_found"]:
            print(f"\n  {p['paper_id']}")
            print(f"    Genes: {', '.join(p['genes_found'][:8])}")

    # Save full JSON for detailed analysis
    with open(OUTPUT_DIR / "paper_analysis.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
