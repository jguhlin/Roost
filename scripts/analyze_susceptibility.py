#!/usr/bin/env python3
"""
Extended susceptibility analysis for Roost.

Expands on basic susceptibility scores with:
1. Family-level patterns
2. Taxonomic risk profiles
3. Ecological guild analysis (waterfowl, raptors, shorebirds, etc.)
4. Detection trends over time
5. Geographic hotspots
6. Cross-species comparisons

Usage:
    python scripts/analyze_susceptibility.py
"""

import json
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")

# =============================================================================
# ECOLOGICAL GUILDS
# =============================================================================

# Map families to ecological guilds for higher-level analysis
FAMILY_TO_GUILD = {
    # Waterfowl (reservoir species)
    "Anatidae": "Waterfowl",

    # Raptors
    "Accipitridae": "Raptor",
    "Falconidae": "Raptor",
    "Pandionidae": "Raptor",
    "Cathartidae": "Vulture",

    # Owls
    "Strigidae": "Owl",
    "Tytonidae": "Owl",

    # Shorebirds
    "Scolopacidae": "Shorebird",
    "Charadriidae": "Shorebird",
    "Recurvirostridae": "Shorebird",
    "Haematopodidae": "Shorebird",

    # Gulls and terns
    "Laridae": "Gull/Tern",
    "Sternidae": "Gull/Tern",

    # Seabirds
    "Alcidae": "Seabird",
    "Procellariidae": "Seabird",
    "Sulidae": "Seabird",
    "Phalacrocoracidae": "Cormorant",
    "Fregatidae": "Seabird",

    # Wading birds
    "Ardeidae": "Heron/Egret",
    "Threskiornithidae": "Ibis/Spoonbill",
    "Ciconiidae": "Stork",

    # Pelicans
    "Pelecanidae": "Pelican",

    # Cranes and rails
    "Gruidae": "Crane",
    "Rallidae": "Rail",

    # Gamebirds
    "Phasianidae": "Gamebird",
    "Odontophoridae": "Gamebird",
    "Meleagrididae": "Gamebird",
    "Numididae": "Gamebird",

    # Pigeons
    "Columbidae": "Pigeon/Dove",

    # Corvids
    "Corvidae": "Corvid",

    # Other passerines
    "Sturnidae": "Passerine",
    "Icteridae": "Passerine",
    "Fringillidae": "Passerine",
    "Passeridae": "Passerine",
    "Turdidae": "Passerine",
}


def get_guild(family: str) -> str:
    """Get ecological guild for a family."""
    return FAMILY_TO_GUILD.get(family, "Other")


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_by_family(scores: pl.DataFrame) -> pl.DataFrame:
    """Analyze susceptibility patterns by family."""
    family_stats = (
        scores
        .group_by(["order", "family"])
        .agg([
            pl.len().alias("species_count"),
            pl.col("detection_count").sum().alias("total_detections"),
            pl.col("susceptibility_score").mean().round(1).alias("avg_score"),
            pl.col("susceptibility_score").std().round(1).alias("score_std"),
            pl.col("susceptibility_score").min().alias("min_score"),
            pl.col("susceptibility_score").max().alias("max_score"),
            pl.col("mortality_rate").mean().round(3).alias("avg_mortality"),
            pl.col("has_rigi").first().alias("has_rigi"),
            (pl.col("confidence") >= 0.5).sum().alias("high_conf_count"),
        ])
        .sort("total_detections", descending=True)
    )

    return family_stats


def analyze_by_guild(scores: pl.DataFrame) -> pl.DataFrame:
    """Analyze susceptibility patterns by ecological guild."""
    # Add guild column
    scores_with_guild = scores.with_columns(
        pl.col("family").map_elements(get_guild, return_dtype=pl.Utf8).alias("guild")
    )

    guild_stats = (
        scores_with_guild
        .group_by("guild")
        .agg([
            pl.len().alias("species_count"),
            pl.col("detection_count").sum().alias("total_detections"),
            pl.col("susceptibility_score").mean().round(1).alias("avg_score"),
            pl.col("susceptibility_score").std().round(1).alias("score_std"),
            pl.col("mortality_rate").mean().round(3).alias("avg_mortality"),
            pl.col("has_rigi").mean().round(2).alias("pct_with_rigi"),
            # Classification distribution
            (pl.col("susceptibility_class") == "highly_susceptible").sum().alias("n_highly_susceptible"),
            (pl.col("susceptibility_class") == "tolerant").sum().alias("n_tolerant"),
            (pl.col("susceptibility_class") == "highly_tolerant").sum().alias("n_highly_tolerant"),
        ])
        .with_columns(
            ((pl.col("n_tolerant") + pl.col("n_highly_tolerant")) / pl.col("species_count") * 100)
            .round(1).alias("pct_tolerant")
        )
        .sort("total_detections", descending=True)
    )

    return guild_stats, scores_with_guild


def analyze_temporal_trends(detections: pl.DataFrame) -> pl.DataFrame:
    """Analyze detection trends over time."""
    # Parse dates and extract year-month
    temporal = (
        detections
        .filter(pl.col("date_detected").is_not_null())
        .with_columns([
            # Try to parse various date formats
            pl.when(pl.col("date_detected").str.contains(r"^\d{4}-\d{2}-\d{2}"))
              .then(pl.col("date_detected").str.slice(0, 7))  # YYYY-MM
              .when(pl.col("date_detected").str.contains(r"^\d{1,2}/\d{1,2}/\d{4}"))
              .then(
                  pl.col("date_detected").str.extract(r"(\d{4})$", 1) + "-" +
                  pl.col("date_detected").str.extract(r"^(\d{1,2})/", 1).str.zfill(2)
              )
              .otherwise(pl.lit(None))
              .alias("year_month")
        ])
        .filter(pl.col("year_month").is_not_null())
    )

    monthly_counts = (
        temporal
        .group_by("year_month")
        .agg([
            pl.len().alias("detection_count"),
            pl.col("source").n_unique().alias("source_count"),
        ])
        .sort("year_month")
    )

    return monthly_counts


def analyze_geographic_hotspots(detections: pl.DataFrame) -> pl.DataFrame:
    """Identify geographic hotspots of detections."""
    # By country
    country_stats = (
        detections
        .group_by("country")
        .agg([
            pl.len().alias("detection_count"),
            pl.col("taxon_id").drop_nulls().n_unique().alias("species_count"),
            pl.col("source").n_unique().alias("source_count"),
        ])
        .sort("detection_count", descending=True)
    )

    return country_stats


def analyze_geographic_by_state(detections: pl.DataFrame) -> pl.DataFrame:
    """Analyze US detections by state."""
    us_detections = detections.filter(pl.col("country") == "USA")

    if len(us_detections) == 0:
        return pl.DataFrame()

    state_stats = (
        us_detections
        .group_by("state")
        .agg([
            pl.len().alias("detection_count"),
            pl.col("taxon_id").drop_nulls().n_unique().alias("species_count"),
        ])
        .sort("detection_count", descending=True)
    )

    return state_stats


def identify_high_risk_families(family_stats: pl.DataFrame) -> pl.DataFrame:
    """Identify families with highest susceptibility risk."""
    # High risk = high avg score + sufficient data
    high_risk = (
        family_stats
        .filter(pl.col("species_count") >= 3)  # At least 3 species
        .filter(pl.col("total_detections") >= 50)  # At least 50 detections
        .filter(pl.col("avg_score") >= 70)  # High susceptibility
        .sort("avg_score", descending=True)
    )

    return high_risk


def identify_reservoir_candidates(scores: pl.DataFrame) -> pl.DataFrame:
    """Identify potential reservoir species (tolerant + high detection)."""
    reservoirs = (
        scores
        .filter(pl.col("susceptibility_class").is_in(["tolerant", "highly_tolerant"]))
        .filter(pl.col("detection_count") >= 20)
        .filter(pl.col("confidence") >= 0.3)
        .sort("detection_count", descending=True)
    )

    return reservoirs


def generate_summary_tables(
    scores: pl.DataFrame,
    family_stats: pl.DataFrame,
    guild_stats: pl.DataFrame,
) -> dict:
    """Generate publication-ready summary tables."""

    tables = {}

    # Table 1: Overall susceptibility distribution
    tables["susceptibility_distribution"] = (
        scores
        .group_by("susceptibility_class")
        .agg([
            pl.len().alias("species_count"),
            pl.col("detection_count").sum().alias("total_detections"),
            pl.col("susceptibility_score").mean().round(1).alias("avg_score"),
        ])
        .sort("avg_score", descending=True)
    )

    # Table 2: Top 20 most susceptible species
    tables["most_susceptible"] = (
        scores
        .filter(pl.col("confidence") >= 0.3)
        .sort("susceptibility_score", descending=True)
        .head(20)
        .select([
            "scientific_name", "common_name", "order", "family",
            "susceptibility_score", "mortality_rate", "has_rigi",
            "detection_count", "confidence"
        ])
    )

    # Table 3: Top 20 most tolerant species
    tables["most_tolerant"] = (
        scores
        .filter(pl.col("confidence") >= 0.3)
        .sort("susceptibility_score")
        .head(20)
        .select([
            "scientific_name", "common_name", "order", "family",
            "susceptibility_score", "mortality_rate", "has_rigi",
            "detection_count", "confidence"
        ])
    )

    # Table 4: Guild summary
    tables["guild_summary"] = guild_stats.select([
        "guild", "species_count", "total_detections",
        "avg_score", "avg_mortality", "pct_tolerant"
    ])

    # Table 5: Family risk ranking
    tables["family_risk"] = (
        family_stats
        .filter(pl.col("total_detections") >= 20)
        .select([
            "order", "family", "species_count", "total_detections",
            "avg_score", "avg_mortality", "has_rigi"
        ])
        .head(20)
    )

    return tables


def main():
    print("=" * 60)
    print("EXTENDED SUSCEPTIBILITY ANALYSIS")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    scores = pl.read_parquet(DATA_DIR / "susceptibility_scores.parquet")
    print(f"  Susceptibility scores: {len(scores)} species")

    detections = pl.read_parquet(DATA_DIR / "detections_merged.parquet")
    print(f"  Detection records: {len(detections):,}")

    # Family-level analysis
    print("\n" + "=" * 60)
    print("FAMILY-LEVEL PATTERNS")
    print("=" * 60)

    family_stats = analyze_by_family(scores)
    print(f"\nFamilies with detections: {len(family_stats)}")

    print("\nTop 15 families by detection count:")
    for row in family_stats.head(15).iter_rows(named=True):
        rigi = "+" if row["has_rigi"] else "-"
        print(f"  {row['family']:25s} {row['total_detections']:5,} det  {row['species_count']:2} spp  "
              f"score: {row['avg_score']:5.1f}±{row['score_std'] or 0:.1f}  RIG-I:{rigi}")

    # High-risk families
    high_risk = identify_high_risk_families(family_stats)
    if len(high_risk) > 0:
        print(f"\nHigh-risk families (score ≥ 70, n ≥ 50):")
        for row in high_risk.iter_rows(named=True):
            rigi = "+" if row["has_rigi"] else "-"
            print(f"  {row['family']:25s} score: {row['avg_score']:.0f}  RIG-I:{rigi}  "
                  f"({row['species_count']} spp, {row['total_detections']} det)")

    # Guild-level analysis
    print("\n" + "=" * 60)
    print("ECOLOGICAL GUILD PATTERNS")
    print("=" * 60)

    guild_stats, scores_with_guild = analyze_by_guild(scores)

    print("\nSusceptibility by ecological guild:")
    print(f"{'Guild':<20} {'Species':>8} {'Detections':>10} {'Avg Score':>10} {'% Tolerant':>12}")
    print("-" * 65)
    for row in guild_stats.iter_rows(named=True):
        guild = row['guild'] or 'Unknown'
        print(f"{guild:<20} {row['species_count']:>8} {row['total_detections']:>10,} "
              f"{row['avg_score']:>10.1f} {row['pct_tolerant']:>11.1f}%")

    # Reservoir candidates
    print("\n" + "=" * 60)
    print("POTENTIAL RESERVOIR SPECIES")
    print("=" * 60)

    reservoirs = identify_reservoir_candidates(scores)
    print(f"\nTolerant species with high detection rates ({len(reservoirs)} candidates):")
    for row in reservoirs.head(15).iter_rows(named=True):
        print(f"  {row['scientific_name']:30s} score: {row['susceptibility_score']:4.1f}  "
              f"n={row['detection_count']:,}  mort: {row['mortality_rate']*100:.1f}%")

    # Geographic patterns
    print("\n" + "=" * 60)
    print("GEOGRAPHIC PATTERNS")
    print("=" * 60)

    country_stats = analyze_geographic_hotspots(detections)
    print("\nDetections by country:")
    for row in country_stats.head(10).iter_rows(named=True):
        print(f"  {row['country']:20s} {row['detection_count']:6,} det  {row['species_count']:3} species")

    state_stats = analyze_geographic_by_state(detections)
    if len(state_stats) > 0:
        print("\nUS detections by state (top 15):")
        for row in state_stats.head(15).iter_rows(named=True):
            state = row['state'] or 'Unknown'
            print(f"  {state:20s} {row['detection_count']:5,} det  {row['species_count']:3} species")

    # Temporal patterns
    print("\n" + "=" * 60)
    print("TEMPORAL PATTERNS")
    print("=" * 60)

    monthly = analyze_temporal_trends(detections)
    if len(monthly) > 0:
        print(f"\nDetection timeline ({len(monthly)} months with data):")
        # Show recent months
        recent = monthly.tail(12)
        for row in recent.iter_rows(named=True):
            bar = "█" * min(50, row['detection_count'] // 20)
            print(f"  {row['year_month']}  {row['detection_count']:5,}  {bar}")

    # Generate summary tables
    print("\n" + "=" * 60)
    print("GENERATING SUMMARY TABLES")
    print("=" * 60)

    tables = generate_summary_tables(scores, family_stats, guild_stats)

    # Save outputs
    output_dir = DATA_DIR / "analysis"
    output_dir.mkdir(exist_ok=True)

    for name, table in tables.items():
        table.write_csv(output_dir / f"{name}.tsv", separator="\t")
        print(f"  {name}.tsv ({len(table)} rows)")

    # Save guild-annotated scores
    scores_with_guild.write_parquet(DATA_DIR / "susceptibility_scores_annotated.parquet")
    print(f"  susceptibility_scores_annotated.parquet")

    # Save family stats
    family_stats.write_csv(output_dir / "family_susceptibility.tsv", separator="\t")
    print(f"  family_susceptibility.tsv")

    # Save guild stats
    guild_stats.write_csv(output_dir / "guild_susceptibility.tsv", separator="\t")
    print(f"  guild_susceptibility.tsv")

    # Save geographic stats
    country_stats.write_csv(output_dir / "country_detections.tsv", separator="\t")
    if len(state_stats) > 0:
        state_stats.write_csv(output_dir / "us_state_detections.tsv", separator="\t")

    # Summary JSON
    summary = {
        "generated": str(date.today()),
        "total_species_scored": len(scores),
        "families_analyzed": len(family_stats),
        "guilds_analyzed": len(guild_stats),
        "high_risk_families": high_risk.to_dicts() if len(high_risk) > 0 else [],
        "reservoir_candidates": reservoirs.head(10).to_dicts(),
        "guild_summary": guild_stats.to_dicts(),
        "top_countries": country_stats.head(10).to_dicts(),
    }

    with open(output_dir / "analysis_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  analysis_summary.json")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nOutputs saved to {output_dir}/")


if __name__ == "__main__":
    main()
