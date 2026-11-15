#!/usr/bin/env python3
"""
Susceptibility scoring for Roost — LEGACY v1 (severity-weighted composite).

**Axis note (2026-11-10):** this model scores DISEASE OUTCOME (mortality-
weighted × RIG-I status), not infection permissiveness. A reservoir species
(mallard: infected constantly, rarely diseased) reads "highly_tolerant"
HERE while being highly permissive in reality. The current, authoritative
two-axis model is scripts/model/build_susceptibility.py (permissiveness ×
severity, #/susceptibility pages). This v1 parquet still backs the species
grid chips, Compare, SpreadCyto and host_competence joins — every UI that
shows it must label it "legacy model" (susc.legacy.* keys) and link to the
two-axis view. Do NOT interpret its classes as infection susceptibility.

Builds composite susceptibility scores combining:
1. Mortality rate (from phenotype data)
2. RIG-I pathway status (from taxonomic inference)
3. Genome quality (affects confidence)
4. Sample size (affects confidence)

RIG-I (DDX58) Status by Order:
- Galliformes (chickens, turkeys, quail): ABSENT - highly susceptible
- Anseriformes (ducks, geese, swans): PRESENT - generally tolerant
- Most other orders: PRESENT

This explains the key species difference: waterfowl are reservoirs
because they have RIG-I for viral sensing, while gallinaceous birds
lack this sensor and are more susceptible.

Usage:
    python scripts/build_susceptibility_scores.py
"""

import json
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")

# =============================================================================
# RIG-I PATHWAY STATUS BY ORDER
# =============================================================================

# Based on Barber et al. 2010, Magor et al. 2013, and comparative genomics
# DDX58 (RIG-I) and RNF135 (RIPLET) presence/absence
RIGI_STATUS = {
    # ABSENT - Lost RIG-I pathway
    "Galliformes": {
        "rigi_present": False,
        "riplet_present": False,
        "notes": "Lost RIG-I and RIPLET. Rely on MDA5 only.",
        "susceptibility_modifier": 1.5,  # Increases susceptibility
    },

    # PRESENT - Have RIG-I pathway (most birds)
    "Anseriformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Primary reservoir species.",
        "susceptibility_modifier": 0.7,  # Decreases susceptibility
    },
    "Charadriiformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Shorebirds and gulls.",
        "susceptibility_modifier": 0.8,
    },
    "Passeriformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Songbirds.",
        "susceptibility_modifier": 0.9,
    },
    "Accipitriformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Raptors - high mortality despite RIG-I.",
        "susceptibility_modifier": 1.0,  # No modifier - other factors dominate
    },
    "Strigiformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Owls - high mortality despite RIG-I.",
        "susceptibility_modifier": 1.0,
    },
    "Falconiformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Falcons.",
        "susceptibility_modifier": 1.0,
    },
    "Pelecaniformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Pelicans, herons.",
        "susceptibility_modifier": 0.9,
    },
    "Suliformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Cormorants, boobies.",
        "susceptibility_modifier": 0.9,
    },
    "Columbiformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Pigeons, doves.",
        "susceptibility_modifier": 0.8,
    },
    "Gruiformes": {
        "rigi_present": True,
        "riplet_present": True,
        "notes": "Full RIG-I pathway. Cranes, rails.",
        "susceptibility_modifier": 0.9,
    },
}

# Default for orders not explicitly listed
DEFAULT_RIGI_STATUS = {
    "rigi_present": True,  # Most birds have RIG-I
    "riplet_present": True,
    "notes": "Assumed present (most birds retain RIG-I).",
    "susceptibility_modifier": 1.0,
}


def get_rigi_status(order: str) -> dict:
    """Get RIG-I pathway status for an order."""
    return RIGI_STATUS.get(order, DEFAULT_RIGI_STATUS)


# =============================================================================
# SUSCEPTIBILITY SCORING
# =============================================================================

def calculate_susceptibility_score(
    mortality_rate: float,
    rigi_modifier: float,
    sample_size: int,
    has_genome: bool,
    has_annotation: bool,
) -> tuple[float, float]:
    """
    Calculate susceptibility score and confidence.

    Score: 0-100 (higher = more susceptible)
    Confidence: 0-1 (higher = more certain)

    Scoring formula:
    - Base score from mortality rate (0-100)
    - Adjusted by RIG-I pathway modifier
    - Capped at 0-100

    Confidence factors:
    - Sample size (n >= 100: high, n >= 30: medium, else low)
    - Genome availability
    - Annotation status
    """
    # Base score from mortality (0-100 scale)
    base_score = mortality_rate * 100

    # Apply RIG-I modifier
    adjusted_score = base_score * rigi_modifier

    # Cap at 0-100
    final_score = max(0, min(100, adjusted_score))

    # Calculate confidence
    # Sample size factor (0-0.5)
    if sample_size >= 100:
        size_conf = 0.5
    elif sample_size >= 30:
        size_conf = 0.35
    elif sample_size >= 10:
        size_conf = 0.2
    else:
        size_conf = 0.1

    # Genome factor (0-0.3)
    genome_conf = 0.2 if has_genome else 0
    if has_annotation:
        genome_conf = 0.3

    # Multi-source bonus (0-0.2) - handled externally
    # For now, base confidence on size + genome
    confidence = size_conf + genome_conf

    return round(final_score, 1), round(confidence, 2)


def classify_susceptibility(score: float) -> str:
    """Classify susceptibility based on score."""
    if score >= 90:
        return "highly_susceptible"
    elif score >= 70:
        return "susceptible"
    elif score >= 40:
        return "intermediate"
    elif score >= 15:
        return "tolerant"
    else:
        return "highly_tolerant"


def build_susceptibility_table() -> pl.DataFrame:
    """
    Build susceptibility scores for all species with detection data.
    """
    # Load required data
    print("Loading data...")

    profiles_file = DATA_DIR / "species_profiles.parquet"
    if not profiles_file.exists():
        raise FileNotFoundError("Run build-profiles first")

    profiles = pl.read_parquet(profiles_file)
    print(f"  Species profiles: {len(profiles):,}")

    phenotype_file = DATA_DIR / "phenotype_table.parquet"
    phenotype = pl.DataFrame()
    if phenotype_file.exists():
        phenotype = pl.read_parquet(phenotype_file)
        print(f"  Phenotype data: {len(phenotype):,} species")

    # Filter to species with detection data
    detected = profiles.filter(pl.col("has_detections"))
    print(f"  Species with detections: {len(detected):,}")

    # Build susceptibility scores
    print("\nCalculating susceptibility scores...")

    results = []
    for row in detected.iter_rows(named=True):
        taxon_id = row["taxon_id"]
        order = row.get("order", "")

        # Get RIG-I status for this order
        rigi_status = get_rigi_status(order)
        rigi_modifier = rigi_status["susceptibility_modifier"]
        has_rigi = rigi_status["rigi_present"]

        # Get mortality rate from phenotype if available
        mortality_rate = row.get("mortality_rate")
        if mortality_rate is None:
            # No phenotype data - use detection count as proxy
            # High detection with no mortality info = likely tolerant reservoir
            mortality_rate = 0.5  # Assume intermediate

        # Sample size
        sample_size = row.get("detection_count", 0) or 0

        # Genome info
        has_genome = row.get("has_genome", False)
        has_annotation = row.get("has_annotation", False)

        # Calculate score and confidence
        score, confidence = calculate_susceptibility_score(
            mortality_rate=mortality_rate,
            rigi_modifier=rigi_modifier,
            sample_size=sample_size,
            has_genome=has_genome,
            has_annotation=has_annotation,
        )

        # Multi-source bonus for confidence
        source_count = row.get("source_count", 1) or 1
        if source_count >= 2:
            confidence = min(1.0, confidence + 0.1)

        # Classify
        classification = classify_susceptibility(score)

        results.append({
            "taxon_id": taxon_id,
            "scientific_name": row["scientific_name"],
            "common_name": row.get("common_name"),
            "order": order,
            "family": row.get("family"),
            # Scores
            "susceptibility_score": score,
            "susceptibility_class": classification,
            "confidence": confidence,
            # Components
            "mortality_rate": round(mortality_rate, 3) if mortality_rate else None,
            "has_rigi": has_rigi,
            "rigi_modifier": rigi_modifier,
            # Data quality
            "detection_count": sample_size,
            "source_count": source_count,
            "has_genome": has_genome,
            "has_annotation": has_annotation,
            # Phenotype class (if available)
            "phenotype_class": row.get("phenotype_class"),
        })

    df = pl.DataFrame(results)

    # Sort by susceptibility score (most susceptible first)
    df = df.sort("susceptibility_score", descending=True)

    return df


def validate_scores(df: pl.DataFrame):
    """
    Validate susceptibility scores against known biology.

    Expected patterns:
    - Galliformes should be highly susceptible (no RIG-I)
    - Anseriformes should be more tolerant (have RIG-I, reservoirs)
    - Raptors/owls often highly susceptible despite RIG-I (other factors)
    """
    print("\n" + "=" * 60)
    print("VALIDATION: Known Susceptibility Patterns")
    print("=" * 60)

    # Galliformes (should be susceptible)
    galliforms = df.filter(pl.col("order") == "Galliformes")
    if len(galliforms) > 0:
        avg_score = galliforms["susceptibility_score"].mean()
        print(f"\nGalliformes (no RIG-I, expected susceptible):")
        print(f"  Species: {len(galliforms)}")
        print(f"  Avg susceptibility score: {avg_score:.1f}")
        for row in galliforms.head(5).iter_rows(named=True):
            print(f"    {row['scientific_name']}: {row['susceptibility_score']:.0f} ({row['susceptibility_class']})")

    # Anseriformes (should be more tolerant)
    anseriforms = df.filter(pl.col("order") == "Anseriformes")
    if len(anseriforms) > 0:
        avg_score = anseriforms["susceptibility_score"].mean()
        tolerant = anseriforms.filter(
            pl.col("susceptibility_class").is_in(["tolerant", "highly_tolerant"])
        ).height
        print(f"\nAnseriformes (have RIG-I, expected more tolerant):")
        print(f"  Species: {len(anseriforms)}")
        print(f"  Avg susceptibility score: {avg_score:.1f}")
        print(f"  Tolerant/highly tolerant: {tolerant} ({100*tolerant/len(anseriforms):.0f}%)")

    # High-confidence predictions
    high_conf = df.filter(pl.col("confidence") >= 0.5)
    print(f"\nHigh-confidence predictions (conf >= 0.5): {len(high_conf)}")

    # Score distribution
    print("\nScore distribution:")
    for cls in ["highly_susceptible", "susceptible", "intermediate", "tolerant", "highly_tolerant"]:
        count = df.filter(pl.col("susceptibility_class") == cls).height
        print(f"  {cls:20s}: {count:3d} species")


def main():
    print("=" * 60)
    print("BUILDING SUSCEPTIBILITY SCORES")
    print("=" * 60)

    df = build_susceptibility_table()

    print(f"\nGenerated scores for {len(df):,} species")

    # Summary statistics
    print("\nSummary:")
    avg_score = df["susceptibility_score"].mean()
    high_conf_count = df.filter(pl.col("confidence") >= 0.5).height
    with_rigi = df.filter(pl.col("has_rigi")).height
    print(f"  Average susceptibility score: {avg_score:.1f}")
    print(f"  High-confidence predictions: {high_conf_count}")
    print(f"  Species with RIG-I: {with_rigi} / {len(df)}")

    # Top most susceptible
    print("\nTop 10 most susceptible species:")
    for row in df.head(10).iter_rows(named=True):
        rigi = "+" if row["has_rigi"] else "-"
        conf = "H" if row["confidence"] >= 0.5 else ("M" if row["confidence"] >= 0.3 else "L")
        print(f"  {row['scientific_name']:30s} {row['susceptibility_score']:5.1f}  RIG-I:{rigi}  conf:{conf}  n={row['detection_count']}")

    # Top most tolerant
    print("\nTop 10 most tolerant species:")
    tolerant = df.sort("susceptibility_score").head(10)
    for row in tolerant.iter_rows(named=True):
        rigi = "+" if row["has_rigi"] else "-"
        conf = "H" if row["confidence"] >= 0.5 else ("M" if row["confidence"] >= 0.3 else "L")
        print(f"  {row['scientific_name']:30s} {row['susceptibility_score']:5.1f}  RIG-I:{rigi}  conf:{conf}  n={row['detection_count']}")

    # Validate
    validate_scores(df)

    # Save outputs
    print("\n" + "=" * 60)
    print("SAVING OUTPUTS")
    print("=" * 60)

    df.write_parquet(DATA_DIR / "susceptibility_scores.parquet")
    print(f"  susceptibility_scores.parquet ({len(df)} species)")

    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# df.write_csv(DATA_DIR / "susceptibility_scores.tsv", separator="\t")
    print(f"  susceptibility_scores.tsv")

    # High-confidence subset
    high_conf = df.filter(pl.col("confidence") >= 0.5)
    if len(high_conf) > 0:
        # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# high_conf.write_csv(DATA_DIR / "susceptibility_scores_highconf.tsv", separator="\t")
        print(f"  susceptibility_scores_highconf.tsv ({len(high_conf)} species)")

    # JSON summary
    summary = {
        "generated": str(date.today()),
        "total_species": len(df),
        "high_confidence_count": high_conf_count,
        "avg_susceptibility_score": round(avg_score, 1),
        "species_with_rigi": with_rigi,
        "species_without_rigi": len(df) - with_rigi,
        "by_class": df.group_by("susceptibility_class").len().to_dicts(),
        "by_order": df.group_by("order").agg([
            pl.len().alias("count"),
            pl.col("susceptibility_score").mean().round(1).alias("avg_score"),
            pl.col("has_rigi").first().alias("has_rigi"),
        ]).sort("count", descending=True).to_dicts(),
        "methodology": {
            "components": ["mortality_rate", "rigi_pathway_status", "genome_quality", "sample_size"],
            "rigi_source": "Taxonomic inference (Barber et al. 2010, Magor et al. 2013)",
            "mortality_source": "HPAI detection sampling method (morbidity/mortality vs live)",
        },
    }

    with open(DATA_DIR / "susceptibility_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  susceptibility_summary.json")


if __name__ == "__main__":
    main()
