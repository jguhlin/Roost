#!/usr/bin/env python3
"""
Per-paper analysis with incremental updates and importance scoring.
Stores analysis results per paper so we don't have to reanalyze everything.
Includes section-weighted importance scoring for genes.
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import hashlib

PROJECT_ROOT = Path(__file__).parent.parent.parent
MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
ANALYSIS_DIR = PROJECT_ROOT / "data" / "papers" / "analyses"
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"

# Ensure analysis directory exists
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# Section weights for importance scoring
SECTION_WEIGHTS = {
    "abstract": 0.9,
    "introduction": 0.4,
    "methods": 0.5,
    "results": 1.0,
    "discussion": 1.0,
    "conclusions": 1.0,
    "supplementary": 0.3,
    "references": 0.0,
    "acknowledgments": 0.0,
    "unknown": 0.5,
}

# Section detection patterns
SECTION_PATTERNS = {
    "abstract": [r"(?:^|\n)#+?\s*abstract\b", r"(?:^|\n)abstract\b"],
    "introduction": [r"(?:^|\n)#+?\s*introduction\b", r"(?:^|\n)\d+\.?\s*introduction\b"],
    "methods": [r"(?:^|\n)#+?\s*methods?\b", r"(?:^|\n)#+?\s*materials?\s+and\s+methods?\b"],
    "results": [r"(?:^|\n)#+?\s*results?\b"],
    "discussion": [r"(?:^|\n)#+?\s*discussion\b"],
    "conclusions": [r"(?:^|\n)#+?\s*conclusions?\b"],
    "references": [r"(?:^|\n)#+?\s*references\b"],
    "supplementary": [r"(?:^|\n)#+?\s*supplement", r"(?:^|\n)#+?\s*supporting\s+information"],
    "acknowledgments": [r"(?:^|\n)#+?\s*acknowledg"],
}

# Gene patterns for extraction
GENE_PATTERNS = {
    "ANP32A": [r"\bANP32A\b", r"\bANP32-A\b", r"\bacidic nuclear phosphoprotein 32A\b"],
    "ANP32B": [r"\bANP32B\b", r"\bANP32-B\b"],
    "ANP32E": [r"\bANP32E\b", r"\bANP32-E\b"],
    "DDX58": [r"\bRIG-I\b", r"\bDDX58\b", r"\bretinoic acid.inducible gene I\b"],
    "IFIH1": [r"\bMDA5\b", r"\bIFIH1\b", r"\bmelanoma differentiation.associated gene 5\b"],
    "MX1": [r"\bMX1\b", r"\bMx1\b", r"\bMxA\b", r"\bmyxovirus resistance\b"],
    "IFIT5": [r"\bIFIT5\b", r"\bISG58\b"],
    "TRIM25": [r"\bTRIM25\b"],
    "TRIM32": [r"\bTRIM32\b"],
    "IRF7": [r"\bIRF7\b", r"\binterferon regulatory factor 7\b"],
    "IRF3": [r"\bIRF3\b", r"\binterferon regulatory factor 3\b"],
    "OAS": [r"\bOAS\b", r"\bOAS1\b", r"\boligoadenylate synthase\b"],
    "MAVS": [r"\bMAVS\b", r"\bIPS-1\b", r"\bmitochondrial antiviral signaling\b"],
    "HERC3": [r"\bHERC3\b"],
    "RSAD2": [r"\bRSAD2\b", r"\bviperin\b"],
    "NS1": [r"\bNS1\b(?! [a-z])"],  # Avoid NS1 followed by lowercase
    "PB2": [r"\bPB2\b", r"\bpolymerase basic 2\b"],
    "PB1": [r"\bPB1\b", r"\bpolymerase basic 1\b"],
    "PA": [r"\bPA\b(?! [a-z])"],  # Avoid PA followed by lowercase (like "PA based")
    "NP": [r"\bNP\b", r"\bnucleoprotein\b"],
    "HA": [r"\bHA\b", r"\bhemagglutinin\b"],
    "NA": [r"\bNA\b", r"\bneuraminidase\b"],
    "IFN-alpha": [r"\bIFN-α\b", r"\bIFN-alpha\b", r"\binterferon alpha\b"],
    "IFN-beta": [r"\bIFN-β\b", r"\bIFN-beta\b", r"\binterferon beta\b"],
    "sialic acid": [r"\bsialic acid\b", r"\bα2,3\b", r"\bα2,6\b", r"\balpha-2,3\b", r"\balpha-2,6\b"],
}

# Species patterns
AVIAN_SPECIES = {
    "Chicken": [r"\bchicken\b", r"\bchickens\b", r"\bgallus\b"],
    "Duck": [r"\bduck\b", r"\bducks\b", r"\banas\b"],
    "Turkey": [r"\bturkey\b", r"\bturkeys\b"],
    "Mallard": [r"\bmallard\b", r"\bmallards\b"],
    "Northern Gannet": [r"\bgannet\b", r"\bgannets\b", r"\bmorus bassanus\b"],
    "Great Skua": [r"\bskua\b", r"\bskuas\b", r"\bstercorarius\b"],
    "Sandwich Tern": [r"\bsandwich tern\b", r"\bthalasseus sandvicensis\b"],
    "Bald Eagle": [r"\bbald eagle\b", r"\bhaliaeetus leucocephalus\b"],
    "American Crow": [r"\bcrow\b", r"\bcrows\b", r"\bcorvus\b"],
    "Common Murre": [r"\bmurre\b", r"\bguillemot\b"],
    "Whooper Swan": [r"\bwhooper swan\b", r"\bcygnus cygnus\b"],
    "Mute Swan": [r"\bmute swan\b", r"\bcygnus olor\b"],
    # Penguins
    "King Penguin": [r"\bking penguin\b", r"\baptenodytes patagonicus\b"],
    "Emperor Penguin": [r"\bemperor penguin\b", r"\baptenodytes forsteri\b"],
    "Gentoo Penguin": [r"\bgentoo penguin\b", r"\bpygoscelis papua\b"],
    "Adelie Penguin": [r"\badelie penguin\b", r"\badélie penguin\b", r"\bpygoscelis adeliae\b"],
    "African Penguin": [r"\bafrican penguin\b", r"\bspheniscus demersus\b"],
    "Humboldt Penguin": [r"\bhumboldt penguin\b", r"\bspheniscus humboldti\b"],
    "Chinstrap Penguin": [r"\bchinstrap penguin\b", r"\bpygoscelis antarcticus\b"],
    "Rockhopper Penguin": [r"\brockhopper penguin\b", r"\beudyptes\b"],
    # Parrots
    "Parrot": [r"\bparrot\b", r"\bparrots\b", r"\bpsittaciform\b"],
    "Kakapo": [r"\bkakapo\b", r"\bstrigops habroptila\b"],
    # Cranes (HPAI-resistant)
    "Japanese Crane": [r"\bjapanese crane\b", r"\bred-crowned crane\b", r"\bgrus japonensis\b"],
    "Hooded Crane": [r"\bhooded crane\b", r"\bgrus monacha\b"],
    "White-necked Crane": [r"\bwhite-necked crane\b", r"\bgrus vipio\b"],
    # Other resistant species
    "Rock Pigeon": [r"\brock pigeon\b", r"\bcolumba livia\b", r"\bpigeon\b"],
    # Raptors (susceptible)
    "Golden Eagle": [r"\bgolden eagle\b", r"\baquila chrysaetos\b"],
    "Peregrine Falcon": [r"\bperegrine falcon\b", r"\bfalco peregrinus\b"],
}

MAMMAL_SPECIES = {
    "Cattle": [r"\bcattle\b", r"\bcow\b", r"\bcows\b", r"\bdairy\b", r"\bbovine\b"],
    "Human": [r"\bhuman\b", r"\bhumans\b", r"\bpatient\b", r"\bpatients\b"],
    "Domestic Cat": [r"\bcat\b", r"\bcats\b", r"\bfeline\b"],
    "Swine": [r"\bswine\b", r"\bpig\b", r"\bpigs\b", r"\bporcine\b"],
    "Red Fox": [r"\bfox\b", r"\bfoxes\b", r"\bvulpes\b"],
    "Elephant Seal": [r"\belephant seal\b", r"\bmirounga\b"],
    "Fur Seal": [r"\bfur seal\b", r"\barctocephalus\b"],
    "Sea Lion": [r"\bsea lion\b", r"\botaria\b"],
    "Mink": [r"\bmink\b", r"\bneovison\b"],
}

# Key mutation patterns
MUTATIONS = {
    "PB2-E627K": [r"\bE627K\b", r"\b627K\b"],
    "PB2-D701N": [r"\bD701N\b", r"\b701N\b"],
    "PB2-M631L": [r"\bM631L\b", r"\b631L\b"],
    "PB2-T271A": [r"\bT271A\b", r"\b271A\b"],
}

# Effect patterns
EFFECTS = {
    "transmission": [r"\btransmission\b", r"\bspread\b", r"\bspillover\b"],
    "mortality": [r"\bmortality\b", r"\bdeath\b", r"\bdie-off\b"],
    "respiratory": [r"\brespiratory\b", r"\bpneumonia\b", r"\blung\b"],
    "neurological": [r"\bneurological\b", r"\bneurotropic\b", r"\bbrain\b", r"\bencephalitis\b"],
    "recovery": [r"\brecovery\b", r"\bsurviv\b"],
    "adaptation": [r"\badaptation\b", r"\badapt\b", r"\bmammalian adaptation\b"],
}

# Gene tier assignments
GENE_TIERS = {
    "ANP32A": 1, "ANP32B": 1, "ANP32E": 2,
    "DDX58": 1, "IFIH1": 1, "MX1": 1, "IFIT5": 1, "OAS": 1,
    "MAVS": 1, "IRF7": 2, "IRF3": 2,
    "PB2": 1, "PB1": 2, "PA": 2, "NP": 2, "NS1": 1, "HA": 1, "NA": 1,
    "TRIM25": 2, "TRIM32": 3, "RSAD2": 2, "HERC3": 2,
    "sialic acid": 1, "IFN-alpha": 2, "IFN-beta": 2,
}


def detect_sections(text: str) -> dict:
    """Detect major sections and their positions in the text."""
    sections = {}
    text_lower = text.lower()

    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                sections[section] = {
                    "start": match.start(),
                    "weight": SECTION_WEIGHTS.get(section, 0.5),
                }
                break

    # Calculate end positions
    sorted_sections = sorted(sections.items(), key=lambda x: x[1]["start"])
    for i, (name, data) in enumerate(sorted_sections):
        if i + 1 < len(sorted_sections):
            data["end"] = sorted_sections[i + 1][1]["start"]
        else:
            data["end"] = len(text)

    return sections


def get_section_for_position(pos: int, sections: dict) -> str:
    """Get the section name for a given text position."""
    for name, data in sections.items():
        if data["start"] <= pos < data.get("end", float("inf")):
            return name
    return "unknown"


def calculate_importance_score(section_mentions: dict, total_mentions: int) -> float:
    """Calculate weighted importance score based on section mentions."""
    if total_mentions == 0:
        return 0.0

    weighted_sum = 0.0
    for section, count in section_mentions.items():
        weight = SECTION_WEIGHTS.get(section, 0.5)
        weighted_sum += min(count, 10) * weight  # Cap at 10 per section

    max_possible = total_mentions * 1.0  # Max weight is 1.0
    return round(min(weighted_sum / max_possible, 1.0), 2)


def assign_evidence_type(section_mentions: dict) -> str:
    """Assign evidence type based on where gene is mentioned."""
    primary_sections = {"results", "discussion", "conclusions", "abstract"}
    if any(section_mentions.get(s, 0) > 0 for s in primary_sections):
        return "primary"
    if any(section_mentions.get(s, 0) > 0 for s in {"methods", "introduction"}):
        return "supporting"
    return "supplementary"


def assign_confidence(importance_score: float, total_mentions: int, section_mentions: dict) -> str:
    """Assign confidence level for gene finding."""
    has_results = section_mentions.get("results", 0) > 0
    if importance_score >= 0.7 and has_results and total_mentions >= 5:
        return "high"
    elif importance_score >= 0.4 or total_mentions >= 3:
        return "medium"
    return "low"


def file_hash(path: Path) -> str:
    """Get MD5 hash of file contents."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def count_patterns(text: str, patterns: list) -> int:
    """Count total matches for a list of patterns."""
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


def extract_key_passages(text: str, patterns: list, max_passages: int = 3) -> list:
    """Extract sentences containing pattern matches."""
    passages = []
    for pattern in patterns:
        for match in re.finditer(r'[^.]*' + pattern + r'[^.]*\.', text, re.IGNORECASE):
            passage = match.group(0).strip()
            if 50 < len(passage) < 500 and passage not in passages:
                passages.append(passage)
                if len(passages) >= max_passages:
                    return passages
    return passages


def analyze_paper(md_path: Path, paper_meta: dict) -> dict:
    """Analyze a single paper and return structured results with importance scoring."""
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    text_lower = text.lower()

    # Detect sections for importance scoring
    sections = detect_sections(text)

    # Gene analysis with importance scoring
    genes = {}
    for gene, patterns in GENE_PATTERNS.items():
        section_mentions = defaultdict(int)
        total_mentions = 0

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                total_mentions += 1
                section = get_section_for_position(match.start(), sections)
                section_mentions[section] += 1

        if total_mentions > 0:
            section_mentions = dict(section_mentions)
            importance_score = calculate_importance_score(section_mentions, total_mentions)
            evidence_type = assign_evidence_type(section_mentions)
            confidence = assign_confidence(importance_score, total_mentions, section_mentions)

            genes[gene] = {
                "mentions": total_mentions,
                "importance_score": importance_score,
                "evidence_type": evidence_type,
                "confidence": confidence,
                "tier": GENE_TIERS.get(gene, 3),
                "section_mentions": section_mentions,
                "passages": extract_key_passages(text, patterns, 2)
            }

    # Species analysis
    avian_species = {}
    for species, patterns in AVIAN_SPECIES.items():
        count = count_patterns(text_lower, patterns)
        if count > 0:
            avian_species[species] = count

    mammal_species = {}
    for species, patterns in MAMMAL_SPECIES.items():
        count = count_patterns(text_lower, patterns)
        if count > 0:
            mammal_species[species] = count

    # Mutation analysis
    mutations = {}
    for mutation, patterns in MUTATIONS.items():
        count = count_patterns(text, patterns)
        if count > 0:
            mutations[mutation] = {
                "mentions": count,
                "passages": extract_key_passages(text, patterns, 2)
            }

    # Effects analysis
    effects = {}
    for effect, patterns in EFFECTS.items():
        count = count_patterns(text_lower, patterns)
        if count > 0:
            effects[effect] = count

    # Extract conclusions/key findings (look for specific sections)
    key_findings = []
    conclusion_patterns = [
        r'(?:conclusion|conclusions|summary|in summary)[:\s]*([^.]+\.(?:[^.]+\.)?)',
        r'(?:we found|we show|we demonstrate|our results)[^.]+\.',
        r'(?:these findings|this study|our data|these data)[^.]+\.',
    ]
    for pattern in conclusion_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches[:2]:
            if 50 < len(match) < 500:
                key_findings.append(match.strip())

    # Classify paper focus
    focus_areas = []
    if sum(avian_species.values()) > 10:
        focus_areas.append("avian")
    if sum(mammal_species.values()) > 10:
        focus_areas.append("mammalian")
    if genes.get("ANP32A", {}).get("mentions", 0) > 5 or genes.get("PB2", {}).get("mentions", 0) > 10:
        focus_areas.append("host_genomics")
    if mutations:
        focus_areas.append("viral_mutations")
    if effects.get("transmission", 0) > 5:
        focus_areas.append("transmission")

    return {
        "paper_id": md_path.stem,
        "file_hash": file_hash(md_path),
        "analyzed_at": datetime.now().isoformat(),
        "metadata": {
            "title": paper_meta.get("title", ""),
            "authors": paper_meta.get("authors", ""),
            "year": paper_meta.get("year"),
            "journal": paper_meta.get("journal", ""),
            "category": paper_meta.get("category", ""),
        },
        "sections": {k: {"start": v["start"], "end": v.get("end", 0), "weight": v["weight"]}
                     for k, v in sections.items()},
        "genes": genes,
        "avian_species": avian_species,
        "mammal_species": mammal_species,
        "mutations": mutations,
        "effects": effects,
        "focus_areas": focus_areas,
        "key_findings": key_findings[:5],
        "word_count": len(text.split()),
        "has_genomics_content": bool(genes),
        "has_species_data": bool(avian_species or mammal_species),
    }


def load_paper_meta() -> dict:
    """Load paper metadata from papers.json."""
    with open(PAPERS_JSON) as f:
        data = json.load(f)
    return {p["id"]: p for p in data.get("papers", [])}


def get_existing_analyses() -> dict:
    """Load existing analyses from disk."""
    analyses = {}
    for path in ANALYSIS_DIR.glob("*.json"):
        with open(path) as f:
            analysis = json.load(f)
            analyses[analysis["paper_id"]] = {
                "file_hash": analysis.get("file_hash"),
                "path": path,
            }
    return analyses


def analyze_all(force: bool = False) -> dict:
    """Analyze all papers, skipping those already analyzed (unless changed)."""
    paper_meta = load_paper_meta()
    existing = get_existing_analyses()

    results = {
        "analyzed": [],
        "skipped": [],
        "errors": [],
    }

    for md_path in sorted(MD_DIR.glob("*.md")):
        paper_id = md_path.stem
        current_hash = file_hash(md_path)

        # Check if already analyzed and unchanged
        if not force and paper_id in existing:
            if existing[paper_id]["file_hash"] == current_hash:
                results["skipped"].append(paper_id)
                continue

        # Analyze paper
        try:
            meta = paper_meta.get(paper_id, {})
            analysis = analyze_paper(md_path, meta)

            # Save analysis
            output_path = ANALYSIS_DIR / f"{paper_id}.json"
            with open(output_path, "w") as f:
                json.dump(analysis, f, indent=2)

            results["analyzed"].append(paper_id)
            print(f"Analyzed: {paper_id}")

            # Print summary
            genes = [g for g, d in analysis["genes"].items() if d["mentions"] >= 2]
            if genes:
                print(f"  Genes: {', '.join(genes[:8])}")
            if analysis["mutations"]:
                print(f"  Mutations: {', '.join(analysis['mutations'].keys())}")
            if analysis["key_findings"]:
                print(f"  Key finding: {analysis['key_findings'][0][:100]}...")

        except Exception as e:
            results["errors"].append({"paper_id": paper_id, "error": str(e)})
            print(f"Error analyzing {paper_id}: {e}")

    return results


def aggregate_analyses() -> dict:
    """Aggregate all per-paper analyses into summary data."""
    all_genes = defaultdict(lambda: {"mentions": 0, "papers": []})
    all_species = defaultdict(lambda: {"mentions": 0, "type": None})
    all_mutations = defaultdict(lambda: {"mentions": 0, "papers": []})

    for path in ANALYSIS_DIR.glob("*.json"):
        with open(path) as f:
            analysis = json.load(f)
            paper_id = analysis["paper_id"]

            # Aggregate genes
            for gene, data in analysis.get("genes", {}).items():
                all_genes[gene]["mentions"] += data["mentions"]
                all_genes[gene]["papers"].append(paper_id)

            # Aggregate species
            for species, count in analysis.get("avian_species", {}).items():
                all_species[species]["mentions"] += count
                all_species[species]["type"] = "avian"

            for species, count in analysis.get("mammal_species", {}).items():
                all_species[species]["mentions"] += count
                all_species[species]["type"] = "mammal"

            # Aggregate mutations
            for mutation, data in analysis.get("mutations", {}).items():
                all_mutations[mutation]["mentions"] += data["mentions"]
                all_mutations[mutation]["papers"].append(paper_id)

    return {
        "genes": dict(all_genes),
        "species": dict(all_species),
        "mutations": dict(all_mutations),
        "total_papers": len(list(ANALYSIS_DIR.glob("*.json"))),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze papers incrementally")
    parser.add_argument("--force", action="store_true", help="Re-analyze all papers")
    parser.add_argument("--aggregate", action="store_true", help="Only aggregate existing analyses")
    args = parser.parse_args()

    if args.aggregate:
        print("Aggregating existing analyses...")
        summary = aggregate_analyses()
        print(f"\nTotal papers analyzed: {summary['total_papers']}")
        print(f"Genes found: {len(summary['genes'])}")
        print(f"Species mentioned: {len(summary['species'])}")
        print(f"Mutations tracked: {len(summary['mutations'])}")
        return

    print("Analyzing papers (incremental)...")
    results = analyze_all(force=args.force)

    print(f"\n=== Summary ===")
    print(f"Analyzed: {len(results['analyzed'])}")
    print(f"Skipped (unchanged): {len(results['skipped'])}")
    print(f"Errors: {len(results['errors'])}")

    # Aggregate results
    print("\nAggregating results...")
    summary = aggregate_analyses()

    # Save aggregate summary
    summary_path = PROJECT_ROOT / "data" / "papers" / "analysis_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
