#!/usr/bin/env python3
"""Build gene data with paper citations and importance scores for web display."""

import json
import re
from collections import defaultdict
from pathlib import Path

# Shared counting patterns — the analysis tier and the fallback tier MUST
# count the same spellings or analyzed/fallback papers aren't comparable.
from analyze_paper import GENE_PATTERNS

PROJECT_ROOT = Path(__file__).parent.parent.parent
MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
OUTPUT_PATH = PROJECT_ROOT / "web" / "public" / "data" / "genes.json"
ANALYSIS_DIR = PROJECT_ROOT / "data" / "papers" / "analyses"

# Gene definitions with detailed info
GENES = {
    "ANP32A": {
        "symbol": "ANP32A",
        "name": "Acidic Nuclear Phosphoprotein 32A",
        "aliases": ["ANP32A", "ANP32-A", "pp32", "LANP"],
        "category": "Host Factor",
        "tier": 1,
        "description": "Essential host factor required for influenza virus polymerase activity. Contains a 33-amino-acid insertion in birds that supports avian influenza replication.",
        "function": "Required for influenza virus RNA synthesis. The avian-specific 33-amino-acid insertion in ANP32A enables efficient viral polymerase activity. Mammalian ANP32A lacks this insertion, creating the primary species barrier.",
        "species_difference": "Birds have a 33-amino-acid insertion (residues 149-182) absent in mammals. This insertion is critical for supporting avian influenza polymerase.",
        "key_finding": "Single knockout insufficient for resistance; viruses rapidly evolve escape mutations (PA-349K/PB2-M631L). Triple knockout of ANP32A/B/E required for robust resistance.",
        "keywords": ["ANP32A", "ANP32-A", "acidic nuclear phosphoprotein 32A", "species barrier"],
    },
    "ANP32B": {
        "symbol": "ANP32B",
        "name": "Acidic Nuclear Phosphoprotein 32B",
        "aliases": ["ANP32B", "ANP32-B", "APRIL"],
        "category": "Host Factor",
        "tier": 1,
        "description": "Paralog of ANP32A that can support influenza polymerase in mammals. Provides redundancy in mammalian cells.",
        "function": "Can substitute for ANP32A in supporting influenza polymerase, particularly in mammalian cells where both ANP32A and ANP32B are utilized.",
        "species_difference": "Both ANP32A and ANP32B support infection in humans, but only ANP32A performs this role in chickens.",
        "key_finding": "Double knockout of ANP32A and ANP32B almost completely eliminates polymerase activity in human cells.",
        "keywords": ["ANP32B", "ANP32-B"],
    },
    "ANP32E": {
        "symbol": "ANP32E",
        "name": "Acidic Nuclear Phosphoprotein 32E",
        "aliases": ["ANP32E", "ANP32-E", "CPD1"],
        "category": "Host Factor",
        "tier": 2,
        "description": "Third ANP32 family member with emerging role in influenza replication.",
        "function": "Can support influenza polymerase activity. Required for complete resistance when combined with ANP32A/B knockout.",
        "species_difference": "Less characterized than ANP32A/B but involved in viral adaptation.",
        "key_finding": "Triple knockout (ANP32A/B/E) required for complete resistance to influenza infection.",
        "keywords": ["ANP32E", "ANP32-E"],
    },
    "DDX58": {
        "symbol": "DDX58",
        "name": "RIG-I (Retinoic Acid Inducible Gene I)",
        "aliases": ["RIG-I", "DDX58", "RIG-1", "retinoic acid-inducible gene I"],
        "category": "Pattern Recognition",
        "tier": 1,
        "description": "Cytoplasmic RNA helicase that senses viral RNA. Primary detector of influenza virus in mammals and ducks.",
        "function": "Recognizes 5'-triphosphate viral RNA and triggers innate immune response through MAVS signaling.",
        "species_difference": "ABSENT IN CHICKENS. The DDX58 gene encoding RIG-I is missing from the chicken genome. Ducks and most other birds retain RIG-I.",
        "key_finding": "Absence of RIG-I in chickens is a key factor explaining their high susceptibility to influenza compared to ducks.",
        "keywords": ["RIG-I", "DDX58", "RIG-1", "retinoic acid-inducible gene I"],
    },
    "IFIH1": {
        "symbol": "IFIH1",
        "name": "MDA5 (Melanoma Differentiation-Associated Gene 5)",
        "aliases": ["MDA5", "IFIH1", "melanoma differentiation-associated gene 5"],
        "category": "Pattern Recognition",
        "tier": 1,
        "description": "RNA helicase that detects cytoplasmic double-stranded RNA. Partially compensates for RIG-I absence in chickens.",
        "function": "Senses long dsRNA and triggers type I interferon response. In chickens, MDA5 is the primary viral RNA sensor due to RIG-I absence.",
        "species_difference": "In chickens, MDA5 must compensate for the absence of RIG-I, but this compensation is incomplete.",
        "key_finding": "Chicken MDA5 (ChMda5) regulates IFN-β in the absence of RIG-I functionality.",
        "keywords": ["MDA5", "IFIH1", "melanoma differentiation-associated gene 5"],
    },
    "MX1": {
        "symbol": "MX1",
        "name": "MX Dynamin Like GTPase 1",
        "aliases": ["MX1", "Mx1", "MxA", "myxovirus resistance 1"],
        "category": "Antiviral Response",
        "tier": 1,
        "description": "Key interferon-induced antiviral protein. Human MxA strongly inhibits influenza; chicken Mx is non-functional.",
        "function": "Directly inhibits influenza virus replication by blocking viral mRNA synthesis and interfering with viral ribonucleoprotein complex.",
        "species_difference": "Human MxA strongly inhibits influenza, while chicken Mx shows minimal antiviral activity. The Mx 2032 G/A polymorphism has been studied but shows inconsistent protective effects.",
        "key_finding": "Species-specific differences in MX1 antiviral potency dramatically affect disease outcomes.",
        "keywords": ["MX1", "Mx1", "MxA", "myxovirus resistance 1"],
    },
    "IFIT5": {
        "symbol": "IFIT5",
        "name": "Interferon Induced Protein With Tetratricopeptide Repeats 5",
        "aliases": ["IFIT5", "ISG58"],
        "category": "ISG",
        "tier": 1,
        "description": "Interferon-stimulated gene with antiviral activity. KEY RESISTANCE MARKER distinguishing resistant from susceptible bird species.",
        "function": "Binds viral RNA and inhibits translation. Strongly upregulated in HPAI-resistant species (cranes, pigeons) but NOT in susceptible species (chickens, raptors).",
        "species_difference": "STRONGLY UPREGULATED IN RESISTANT SPECIES: 45-57x in cranes, 54x in pigeons. NOT upregulated in chickens (3.6x) or most raptors.",
        "key_finding": "IFIT5 is proposed as a genetic marker for HPAI resistance. Transgenic chickens expressing IFIT5 show improved survival.",
        "keywords": ["IFIT5", "ISG58"],
    },
    "TRIM25": {
        "symbol": "TRIM25",
        "name": "Tripartite Motif Containing 25",
        "aliases": ["TRIM25"],
        "category": "ISG",
        "tier": 2,
        "description": "E3 ubiquitin ligase essential for RIG-I activation.",
        "function": "Activates RIG-I through K63-linked ubiquitination. Essential for RIG-I signaling pathway.",
        "species_difference": "Targeted by influenza NS1 protein to evade innate immunity.",
        "key_finding": "TRIM25 promotes antiviral innate immune response through the TRIM25-IRF7 pathway.",
        "keywords": ["TRIM25"],
    },
    "TRIM32": {
        "symbol": "TRIM32",
        "name": "Tripartite Motif Containing 32",
        "aliases": ["TRIM32"],
        "category": "ISG",
        "tier": 3,
        "description": "E3 ubiquitin ligase involved in antiviral signaling in ducks.",
        "function": "Functions in IFN-β signaling against influenza infection in ducks.",
        "species_difference": "Duck TRIM32 has been characterized for its role in innate immunity.",
        "key_finding": "Duck TRIM32 functions in IFN-β signaling against influenza A virus infection.",
        "keywords": ["TRIM32"],
    },
    "PB2": {
        "symbol": "PB2",
        "name": "Polymerase Basic Protein 2",
        "aliases": ["PB2", "polymerase basic 2"],
        "category": "Viral Protein",
        "tier": 1,
        "description": "Influenza virus polymerase subunit. Key determinant of host range and mammalian adaptation.",
        "function": "Essential component of viral RNA polymerase. Interacts with host ANP32 proteins. Mutations enable mammalian adaptation.",
        "species_difference": "Avian viruses require specific PB2 mutations (E627K, D701N) to efficiently replicate in mammals.",
        "key_finding": "PB2 mutations E627K, D701N, M631L, and T271A are associated with mammalian adaptation. M631L specifically associated with cattle adaptation.",
        "keywords": ["PB2", "polymerase basic 2"],
    },
    "IRF7": {
        "symbol": "IRF7",
        "name": "Interferon Regulatory Factor 7",
        "aliases": ["IRF7", "interferon regulatory factor 7"],
        "category": "Signal Transduction",
        "tier": 2,
        "description": "Master regulator of type I interferon response.",
        "function": "Transcription factor that activates interferon gene expression in response to viral infection.",
        "species_difference": "Important component of innate immune signaling in birds.",
        "key_finding": "TRIM25-IRF7 pathway important for antiviral innate immune response.",
        "keywords": ["IRF7", "interferon regulatory factor 7"],
    },
    "sialic_acid": {
        "symbol": "SA",
        "name": "Sialic Acid Receptors",
        "aliases": ["sialic acid", "Sia", "α2,3", "α2,6", "alpha-2,3", "alpha-2,6"],
        "category": "Receptor",
        "tier": 1,
        "description": "Cell surface glycans that serve as receptors for influenza virus attachment.",
        "function": "Influenza HA binds sialic acids to enter cells. α2,3-linked sialic acids preferred by avian viruses; α2,6-linked by human viruses.",
        "species_difference": "Birds primarily have α2,3-linked sialic acids in respiratory tract; humans have α2,6-linked. Receptor distribution affects tropism.",
        "key_finding": "Bovine H5N1 viruses bind poorly to human-type receptors, reducing pandemic risk. Receptor binding changes are monitored for adaptation.",
        "keywords": ["sialic acid", "Sia", "α2,3", "α2,6", "alpha-2,3", "alpha-2,6", "receptor"],
    },
    "OAS": {
        "symbol": "OAS",
        "name": "Oligoadenylate Synthase",
        "aliases": ["OAS", "OAS1", "2'-5'-oligoadenylate synthase"],
        "category": "ISG",
        "tier": 1,
        "description": "Interferon-induced antiviral enzyme that synthesizes 2'-5' oligoadenylates to activate RNase L.",
        "function": "Synthesizes 2'-5' oligoadenylates which activate RNase L to degrade viral RNA. Key antiviral effector.",
        "species_difference": "STRONGLY UPREGULATED IN HPAI-RESISTANT BIRDS (cranes, pigeons) but NOT in susceptible species (chickens, raptors).",
        "key_finding": "OAS expression was significantly upregulated at 6h and 12h post-infection in HPAI-resistant bird species. Proposed as genetic marker for HPAI resistance.",
        "keywords": ["OAS", "OAS1", "oligoadenylate synthase", "2'-5'-oligoadenylate"],
    },
    "MAVS": {
        "symbol": "MAVS",
        "name": "Mitochondrial Antiviral Signaling Protein",
        "aliases": ["MAVS", "IPS-1", "VISA", "Cardif"],
        "category": "Signal Transduction",
        "tier": 1,
        "description": "Mitochondrial adaptor protein essential for RIG-I and MDA5 signaling.",
        "function": "Transmits signal from RIG-I/MDA5 to activate IRF3/IRF7 and NF-κB, inducing interferon production.",
        "species_difference": "Influenza NS1 and PB1-F2 proteins target MAVS to evade innate immunity.",
        "key_finding": "RIG-I binds MAVS at the mitochondrial membrane, triggering the signaling cascade that activates IRF3, IRF7, and NF-κB.",
        "keywords": ["MAVS", "IPS-1", "mitochondrial antiviral signaling"],
    },
    "IRF3": {
        "symbol": "IRF3",
        "name": "Interferon Regulatory Factor 3",
        "aliases": ["IRF3", "interferon regulatory factor 3"],
        "category": "Signal Transduction",
        "tier": 2,
        "description": "Transcription factor activated by viral infection to induce type I interferon.",
        "function": "Phosphorylated upon viral detection, translocates to nucleus to activate IFN-α/β gene expression.",
        "species_difference": "Works with IRF7 to amplify interferon response. Targeted by viral evasion mechanisms.",
        "key_finding": "IRF3 and IRF7 are both triggered by the MAVS signaling cascade, resulting in type-I IFN production.",
        "keywords": ["IRF3", "interferon regulatory factor 3"],
    },
    "HERC3": {
        "symbol": "HERC3",
        "name": "HECT and RLD Domain Containing E3 Ubiquitin Protein Ligase 3",
        "aliases": ["HERC3"],
        "category": "ISG",
        "tier": 2,
        "description": "E3 ubiquitin ligase potentially involved in antiviral response.",
        "function": "Member of HERC family of E3 ligases. May regulate protein degradation during viral infection.",
        "species_difference": "Upregulated in HPAI-resistant bird species (cranes, pigeons) but less consistently than OAS/IFIT5.",
        "key_finding": "HERC3 was upregulated in HPAI-resistant birds but with lower ratios than OAS and IFIT5.",
        "keywords": ["HERC3"],
    },
    "RSAD2": {
        "symbol": "RSAD2",
        "name": "Viperin (Radical S-Adenosyl Methionine Domain Containing 2)",
        "aliases": ["RSAD2", "viperin", "cig5"],
        "category": "ISG",
        "tier": 2,
        "description": "Interferon-induced antiviral protein with broad-spectrum activity.",
        "function": "Inhibits viral replication by disrupting lipid rafts and viral budding. Interferes with viral RNA synthesis.",
        "species_difference": "Expression elevated in infected cells; may contribute to resistance phenotypes.",
        "key_finding": "Expression of RSAD2/viperin was elevated in cells from various bird species after infection.",
        "keywords": ["RSAD2", "viperin"],
    },
    "NS1": {
        "symbol": "NS1",
        "name": "Non-Structural Protein 1",
        "aliases": ["NS1", "non-structural protein 1"],
        "category": "Viral Protein",
        "tier": 1,
        "description": "Influenza virus protein that suppresses host innate immune response.",
        "function": "Inhibits RIG-I activation, blocks TRIM25 ubiquitination, suppresses interferon production. Major virulence factor.",
        "species_difference": "Effectiveness of NS1 immune evasion varies by host species and viral strain.",
        "key_finding": "NS1 inhibits TRIM25-mediated RIG-I activation and interferes with MAVS signaling to evade innate immunity.",
        "keywords": ["NS1", "non-structural protein 1"],
    },
}


def load_analyses() -> dict:
    """Load pre-computed paper analyses with importance scores."""
    analyses = {}
    if not ANALYSIS_DIR.exists():
        return analyses

    for path in ANALYSIS_DIR.glob("*.json"):
        try:
            with open(path) as f:
                analysis = json.load(f)
            analyses[analysis["paper_id"]] = analysis
        except Exception:
            pass
    return analyses


def find_gene_papers(gene_info: dict, papers_meta: dict, md_dir: Path, analyses: dict = None, dict_key: str = None) -> list:
    """Find papers mentioning a gene and extract relevant passages with importance scores."""
    papers_found = []
    keywords = gene_info.get("keywords", [gene_info["symbol"]])
    gene_symbol = gene_info["symbol"]
    # Pattern resolution order: symbol, then the GENES dict key (some records
    # carry display symbols that differ from their analysis key — e.g.
    # "sialic_acid"/dict key resolves the patterns, symbol is "SA").
    pattern_candidates = [gene_symbol, dict_key,
                          (dict_key or gene_symbol).replace("_", " "),
                          gene_symbol.replace("_", " ")]
    pattern_key = next((c for c in pattern_candidates if c in GENE_PATTERNS), None)
    # analysis files key their `genes` dict by the GENE_PATTERNS key
    fallback_patterns = GENE_PATTERNS.get(pattern_key, []) if pattern_key else []
    combined_pattern = None  # compiled per gene on first use (fallback tier)
    kw_by_lower = {}

    for md_path in md_dir.glob("*.md"):
        paper_id = md_path.stem

        # Check if we have pre-computed analysis with importance scores
        if analyses and paper_id in analyses:
            analysis = analyses[paper_id]
            gene_genes = analysis.get("genes", {})
            gene_data = gene_genes.get(gene_symbol)
            if not gene_data and pattern_key:
                gene_data = gene_genes.get(pattern_key)

            if gene_data:
                # Use pre-computed importance score
                meta = papers_meta.get(paper_id, papers_meta.get(paper_id.replace("_", ""), {}))

                # Get passage from analysis or fallback
                passages = gene_data.get("passages", [])
                passage = passages[0] if passages else ""
                if isinstance(passage, dict):
                    passage = passage.get("passage", "")

                papers_found.append({
                    "paper_id": paper_id,
                    "title": meta.get("title", ""),
                    "authors": meta.get("authors", ""),
                    "year": meta.get("year"),
                    "journal": meta.get("journal", ""),
                    "doi": meta.get("doi"),
                    "url": meta.get("url", ""),
                    "category": meta.get("category", ""),
                    "mentions": gene_data.get("mentions", 0),
                    "importance_score": gene_data.get("importance_score", 0.0),
                    "evidence_type": gene_data.get("evidence_type", "unknown"),
                    "confidence": gene_data.get("confidence", "low"),
                    "passage": passage[:300] if passage else "",
                })
                continue

        # Fallback: search markdown directly. No patterns for this gene
        # (empty alternation would zero-width-match every character and
        # report the file's byte count as mentions) — skip instead.
        if not fallback_patterns:
            continue
        text = md_path.read_text(encoding="utf-8", errors="ignore")

        # Same pattern set as the analysis path (see note above). Single
        # combined pass, case-insensitive.
        if combined_pattern is None:
            combined_pattern = re.compile(
                "|".join(f"(?:{p})" for p in fallback_patterns), re.IGNORECASE)
        mention_counts = {}
        for m in combined_pattern.finditer(text):
            k = m.group(0).lower()
            mention_counts[k] = mention_counts.get(k, 0) + 1
        mentions = sum(mention_counts.values())

        if mentions > 0:
            # Get paper metadata
            meta = papers_meta.get(paper_id, papers_meta.get(paper_id.replace("_", ""), {}))

            # Extract a relevant passage (first sentence mentioning the gene)
            passage = ""
            for kw in keywords:
                pattern = r'[^.]*\b' + re.escape(kw) + r'\b[^.]*\.'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    passage = match.group(0).strip()[:300]
                    break

            papers_found.append({
                "paper_id": paper_id,
                "title": meta.get("title", ""),
                "authors": meta.get("authors", ""),
                "year": meta.get("year"),
                "journal": meta.get("journal", ""),
                "doi": meta.get("doi"),
                "url": meta.get("url", ""),
                "category": meta.get("category", ""),
                "mentions": mentions,
                "importance_score": 0.5,  # Default score for non-analyzed papers
                "evidence_type": "unknown",
                "confidence": "low",
                "passage": passage,
            })

    # Sort by importance score, then by mentions
    papers_found.sort(key=lambda x: (-x.get("importance_score", 0), -x["mentions"], -int(x.get("year") or 0)))
    # No cap: the full paper list ships; the gene page paginates client-side
    # (paper_count/total_mentions must reflect the whole corpus, not a slice).
    return papers_found


def main():
    # Load paper metadata
    with open(PAPERS_JSON) as f:
        papers_data = json.load(f)
    papers_meta = {p["id"]: p for p in papers_data.get("papers", [])}

    # Load pre-computed analyses
    analyses = load_analyses()

    print(f"Loaded {len(papers_meta)} papers metadata")
    print(f"Loaded {len(analyses)} pre-computed analyses")
    print(f"Processing {len(GENES)} genes...\n")

    genes_output = []

    for symbol, gene_info in GENES.items():
        print(f"Processing {symbol}...")

        # Find citing papers with importance scores
        papers = find_gene_papers(gene_info, papers_meta, MD_DIR, analyses, dict_key=symbol)

        # Calculate average importance score
        importance_scores = [p.get("importance_score", 0) for p in papers if p.get("importance_score")]
        avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0.0

        gene_record = {
            "symbol": gene_info["symbol"],
            "name": gene_info["name"],
            "aliases": gene_info.get("aliases", []),
            "category": gene_info["category"],
            "tier": gene_info["tier"],
            "description": gene_info["description"],
            "function": gene_info["function"],
            "species_difference": gene_info.get("species_difference", ""),
            "key_finding": gene_info.get("key_finding", ""),
            "papers": papers,
            "paper_count": len(papers),
            "total_mentions": sum(p["mentions"] for p in papers),
            "avg_importance_score": round(avg_importance, 2),
        }

        genes_output.append(gene_record)
        print(f"  Found {len(papers)} papers, {gene_record['total_mentions']} mentions, avg importance: {avg_importance:.2f}")

    # Sort by tier, then by average importance, then by total mentions
    genes_output.sort(key=lambda x: (x["tier"], -x.get("avg_importance_score", 0), -x["total_mentions"]))

    # Save output
    from datetime import datetime
    output = {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "total_genes": len(genes_output),
        "genes": genes_output,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {OUTPUT_PATH}")

    # Summary
    print("\n=== Gene Summary ===")
    print(f"{'Gene':<12} {'Tier':<5} {'Papers':<8} {'Mentions':<10} {'Avg Importance':<15}")
    print("-" * 50)
    for g in genes_output:
        print(f"{g['symbol']:<12} {g['tier']:<5} {g['paper_count']:<8} {g['total_mentions']:<10} {g.get('avg_importance_score', 0):<15.2f}")


if __name__ == "__main__":
    main()
