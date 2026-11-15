#!/usr/bin/env python3
"""
Generate species-level data sheets for Roost.

Creates comprehensive per-species reports combining:
- Taxonomy and identification
- Detection history (counts, locations, dates)
- Susceptibility assessment
- Genomic data availability
- Geographic distribution

Output: data/species_sheets/ (one JSON per species)
        data/species_sheets_summary.tsv (overview table)

Usage:
    python scripts/generate_species_sheets.py
    python scripts/generate_species_sheets.py --species "Anas platyrhynchos"
    python scripts/generate_species_sheets.py --min-detections 10
"""

import json
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")
OUTPUT_DIR = DATA_DIR / "species_sheets"


def load_all_data() -> dict:
    """Load all required data sources."""
    data = {}

    # Species profiles (required)
    profiles_file = DATA_DIR / "species_profiles.parquet"
    if not profiles_file.exists():
        raise FileNotFoundError("Run build-profiles first")
    data["profiles"] = pl.read_parquet(profiles_file)

    # Susceptibility scores
    susc_file = DATA_DIR / "susceptibility_scores.parquet"
    if susc_file.exists():
        data["susceptibility"] = pl.read_parquet(susc_file)
    else:
        data["susceptibility"] = pl.DataFrame()

    # Detections
    det_file = DATA_DIR / "detections_merged.parquet"
    if det_file.exists():
        data["detections"] = pl.read_parquet(det_file)
    else:
        data["detections"] = pl.DataFrame()

    # Phenotype
    pheno_file = DATA_DIR / "phenotype_table.parquet"
    if pheno_file.exists():
        data["phenotype"] = pl.read_parquet(pheno_file)
    else:
        data["phenotype"] = pl.DataFrame()

    return data


def get_detection_summary(detections: pl.DataFrame, scientific_name: str) -> dict:
    """Get detection summary for a species."""
    species_det = detections.filter(pl.col("scientific_name") == scientific_name)

    if len(species_det) == 0:
        return {}

    # Extract year from date
    if "date_detected" in species_det.columns:
        species_det = species_det.with_columns([
            pl.col("date_detected").str.slice(0, 4).cast(pl.Int32, strict=False).alias("year")
        ])

    # Basic counts
    total = len(species_det)
    georeferenced = species_det.filter(
        pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()
    ).height

    # Country distribution
    countries = species_det.filter(pl.col("country").is_not_null()).group_by("country").len()
    country_dist = {row["country"]: row["len"] for row in countries.iter_rows(named=True)}

    # Year distribution
    year_dist = {}
    if "year" in species_det.columns:
        years = species_det.filter(pl.col("year").is_not_null()).group_by("year").len()
        year_dist = {int(row["year"]): row["len"] for row in years.iter_rows(named=True)}

    # Source distribution
    sources = species_det.filter(pl.col("source").is_not_null()).group_by("source").len()
    source_dist = {row["source"]: row["len"] for row in sources.iter_rows(named=True)}

    # Geographic bounds
    geo_bounds = None
    if georeferenced > 0:
        geo_subset = species_det.filter(
            pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()
        )
        geo_bounds = {
            "lat_min": float(geo_subset["latitude"].min()),
            "lat_max": float(geo_subset["latitude"].max()),
            "lon_min": float(geo_subset["longitude"].min()),
            "lon_max": float(geo_subset["longitude"].max()),
        }

    return {
        "total_detections": total,
        "georeferenced_detections": georeferenced,
        "georeferenced_pct": round(100 * georeferenced / total, 1) if total > 0 else 0,
        "countries": country_dist,
        "country_count": len(country_dist),
        "years": year_dist,
        "year_range": [min(year_dist.keys()), max(year_dist.keys())] if year_dist else None,
        "sources": source_dist,
        "source_count": len(source_dist),
        "geographic_bounds": geo_bounds,
    }


def generate_species_sheet(
    scientific_name: str,
    data: dict,
) -> dict:
    """Generate comprehensive data sheet for a single species."""

    # Get profile
    profile = data["profiles"].filter(pl.col("scientific_name") == scientific_name)
    if len(profile) == 0:
        return None

    profile = profile.row(0, named=True)

    sheet = {
        "scientific_name": scientific_name,
        "generated": str(date.today()),
    }

    # === Taxonomy ===
    sheet["taxonomy"] = {
        "taxon_id": profile.get("taxon_id"),
        "common_name": profile.get("common_name"),
        "order": profile.get("order"),
        "family": profile.get("family"),
    }

    # === Data Availability ===
    sheet["data_availability"] = {
        "has_detections": profile.get("has_detections", False),
        "has_genome": profile.get("has_genome", False),
        "has_annotation": profile.get("has_annotation", False),
        "has_phenotype": profile.get("has_phenotype", False),
        "data_completeness": profile.get("data_completeness"),
    }

    # === Genomic Data ===
    if profile.get("has_genome"):
        sheet["genomics"] = {
            "assembly_accession": profile.get("assembly_accession"),
            "assembly_level": profile.get("assembly_level"),
            "genome_size_mb": profile.get("genome_size_mb"),
            "scaffold_n50": profile.get("scaffold_n50"),
            "gc_percent": profile.get("gc_percent"),
            "has_annotation": profile.get("has_annotation"),
        }

    # === Susceptibility ===
    if len(data["susceptibility"]) > 0:
        susc = data["susceptibility"].filter(pl.col("scientific_name") == scientific_name)
        if len(susc) > 0:
            susc_row = susc.row(0, named=True)
            sheet["susceptibility"] = {
                "score": susc_row.get("susceptibility_score"),
                "class": susc_row.get("susceptibility_class"),
                "confidence": susc_row.get("confidence"),
                "has_rigi": susc_row.get("has_rigi"),
                "rigi_modifier": susc_row.get("rigi_modifier"),
                "mortality_rate": susc_row.get("mortality_rate"),
            }

    # === Detection History ===
    if len(data["detections"]) > 0:
        det_summary = get_detection_summary(data["detections"], scientific_name)
        if det_summary:
            sheet["detections"] = det_summary

    # === Phenotype ===
    if len(data["phenotype"]) > 0:
        pheno = data["phenotype"].filter(pl.col("scientific_name") == scientific_name)
        if len(pheno) > 0:
            pheno_row = pheno.row(0, named=True)
            sheet["phenotype"] = {
                "mortality_rate": pheno_row.get("mortality_rate"),
                "sample_size": pheno_row.get("sample_size"),
                "phenotype_class": pheno_row.get("phenotype_class"),
            }

    return sheet


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate species data sheets")
    parser.add_argument("--species", help="Generate for specific species only")
    parser.add_argument("--min-detections", type=int, default=0,
                        help="Minimum detection count to include")
    parser.add_argument("--top", type=int, help="Generate for top N species by detections")
    args = parser.parse_args()

    print("=" * 60)
    print("GENERATING SPECIES DATA SHEETS")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    data = load_all_data()
    print(f"  Profiles: {len(data['profiles']):,}")
    print(f"  Susceptibility: {len(data['susceptibility']):,}")
    print(f"  Detections: {len(data['detections']):,}")
    print(f"  Phenotype: {len(data['phenotype']):,}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Determine which species to process
    if args.species:
        species_list = [args.species]
    else:
        # Get species with detections
        detected = data["profiles"].filter(pl.col("has_detections"))

        if args.min_detections > 0:
            detected = detected.filter(
                pl.col("detection_count") >= args.min_detections
            )

        # Sort by detection count
        detected = detected.sort("detection_count", descending=True)

        if args.top:
            detected = detected.head(args.top)

        species_list = detected["scientific_name"].to_list()

    print(f"\nGenerating sheets for {len(species_list)} species...")

    # Generate sheets
    sheets = []
    summary_rows = []

    for i, species in enumerate(species_list):
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(species_list)}...")

        sheet = generate_species_sheet(species, data)
        if sheet is None:
            continue

        sheets.append(sheet)

        # Write individual JSON
        safe_name = species.replace(" ", "_").replace("/", "_")
        with open(OUTPUT_DIR / f"{safe_name}.json", "w") as f:
            json.dump(sheet, f, indent=2, default=str)

        # Build summary row
        summary_rows.append({
            "scientific_name": species,
            "common_name": sheet["taxonomy"].get("common_name"),
            "order": sheet["taxonomy"].get("order"),
            "family": sheet["taxonomy"].get("family"),
            "detection_count": sheet.get("detections", {}).get("total_detections", 0),
            "country_count": sheet.get("detections", {}).get("country_count", 0),
            "susceptibility_score": sheet.get("susceptibility", {}).get("score"),
            "susceptibility_class": sheet.get("susceptibility", {}).get("class"),
            "has_genome": sheet["data_availability"]["has_genome"],
            "data_completeness": sheet["data_availability"]["data_completeness"],
        })

    print(f"  Generated {len(sheets)} sheets")

    # Write summary table
    if summary_rows:
        summary_df = pl.DataFrame(summary_rows)
        summary_df = summary_df.sort("detection_count", descending=True)
        summary_df.write_csv(DATA_DIR / "species_sheets_summary.tsv", separator="\t")
        print(f"\nSummary: species_sheets_summary.tsv")

    # Write combined JSON
    combined = {
        "generated": str(date.today()),
        "total_species": len(sheets),
        "species": sheets,
    }
    with open(OUTPUT_DIR / "_all_species.json", "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"Combined: species_sheets/_all_species.json")

    # Statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Species sheets generated: {len(sheets)}")
    print(f"Output directory: {OUTPUT_DIR}")

    if summary_rows:
        with_susc = sum(1 for r in summary_rows if r["susceptibility_score"] is not None)
        with_genome = sum(1 for r in summary_rows if r["has_genome"])
        print(f"  With susceptibility scores: {with_susc}")
        print(f"  With genome data: {with_genome}")


if __name__ == "__main__":
    main()
