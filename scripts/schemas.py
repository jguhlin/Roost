#!/usr/bin/env python3
"""
Canonical data schemas for Roost.

Defines the standard column names and types for each data category.
All ingestion scripts should normalize to these schemas.

Usage:
    from schemas import DetectionSchema, normalize_detection

    df = normalize_detection(raw_df, source="aphis")
"""

import polars as pl
from dataclasses import dataclass, field
from typing import Optional
from datetime import date


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

@dataclass
class DetectionSchema:
    """
    Canonical schema for HPAI detection records.

    This is the target schema for all detection sources.
    """
    # Core fields (required)
    source: str                    # Source identifier (e.g., "aphis", "ireland_dafm")
    date: date                     # Detection/collection date
    country: str                   # ISO country code or name

    # Species (at least one required)
    scientific_name: Optional[str] = None   # Binomial name
    common_name: Optional[str] = None       # Common name
    taxon_id: Optional[int] = None          # NCBI taxon ID

    # Location (optional)
    state_province: Optional[str] = None    # State/province/region
    county: Optional[str] = None            # County/district
    locality: Optional[str] = None          # Specific location name
    latitude: Optional[float] = None        # WGS84
    longitude: Optional[float] = None       # WGS84

    # Detection details
    strain: Optional[str] = None            # e.g., "H5N1", "H5"
    subtype: Optional[str] = None           # e.g., "2.3.4.4b"
    pathogenicity: Optional[str] = None     # "HP" or "LP"

    # Sampling
    sampling_type: Optional[str] = None     # "mortality", "harvest", "live", "unknown"
    n_individuals: int = 1                  # Number of birds

    # Metadata
    record_id: Optional[str] = None         # Source-specific ID


# Column definitions for Polars
DETECTION_COLUMNS = {
    "source": pl.Utf8,
    "date": pl.Date,
    "country": pl.Utf8,
    "scientific_name": pl.Utf8,
    "common_name": pl.Utf8,
    "taxon_id": pl.Int64,
    "state_province": pl.Utf8,
    "county": pl.Utf8,
    "locality": pl.Utf8,
    "latitude": pl.Float64,
    "longitude": pl.Float64,
    "strain": pl.Utf8,
    "subtype": pl.Utf8,
    "pathogenicity": pl.Utf8,
    "sampling_type": pl.Utf8,
    "n_individuals": pl.Int32,
    "record_id": pl.Utf8,
}


@dataclass
class TrackingSchema:
    """
    Canonical schema for GPS tracking records.
    """
    source: str                    # Source identifier
    timestamp: str                 # ISO timestamp
    latitude: float                # WGS84
    longitude: float               # WGS84

    # Individual
    individual_id: str             # Tag/transmitter ID
    scientific_name: Optional[str] = None
    common_name: Optional[str] = None

    # Status
    life_state: Optional[str] = None       # "alive", "dead", "unknown"
    behavior: Optional[str] = None         # "migration", "local", "nesting", etc.
    cause_of_death: Optional[str] = None   # If dead: "hpai", "other", "unknown"

    # Metadata
    sensor_type: Optional[str] = None      # "gps", "argos", etc.


TRACKING_COLUMNS = {
    "source": pl.Utf8,
    "timestamp": pl.Datetime,
    "latitude": pl.Float64,
    "longitude": pl.Float64,
    "individual_id": pl.Utf8,
    "scientific_name": pl.Utf8,
    "common_name": pl.Utf8,
    "life_state": pl.Utf8,
    "behavior": pl.Utf8,
    "cause_of_death": pl.Utf8,
    "sensor_type": pl.Utf8,
}


@dataclass
class GenomeSchema:
    """
    Canonical schema for genome assembly records.
    """
    accession: str                 # Assembly accession (e.g., GCF_...)
    taxon_id: int                  # NCBI taxon ID
    scientific_name: str           # Species binomial

    # Assembly quality
    assembly_level: str            # "Chromosome", "Scaffold", "Contig"
    scaffold_n50: Optional[int] = None
    total_length: Optional[int] = None

    # Annotation
    has_annotation: bool = False
    gene_count: Optional[int] = None

    # Metadata
    submitter: Optional[str] = None
    release_date: Optional[date] = None
    is_representative: bool = False


GENOME_COLUMNS = {
    "accession": pl.Utf8,
    "taxon_id": pl.Int64,
    "scientific_name": pl.Utf8,
    "assembly_level": pl.Utf8,
    "scaffold_n50": pl.Int64,
    "total_length": pl.Int64,
    "has_annotation": pl.Boolean,
    "gene_count": pl.Int32,
    "submitter": pl.Utf8,
    "release_date": pl.Date,
    "is_representative": pl.Boolean,
}


# =============================================================================
# NORMALIZATION FUNCTIONS
# =============================================================================

# Field mappings from source columns to canonical columns
SOURCE_FIELD_MAPS = {
    "aphis": {
        "Bird Species": "common_name",
        "State": "state_province",
        "County": "county",
        "Collection Date": "date",
        "HPAI Strain": "strain",
        "Sampling Method": "sampling_type",
    },
    "ireland_dafm": {
        "Species": "scientific_name",
        "County": "county",
        "DateConfirmed": "date",
        "Subtype": "strain",
        "latitude": "latitude",
        "longitude": "longitude",
    },
    "canada_cwhc": {
        "Species": "scientific_name",
        "Province": "state_province",
        "Date_Collected": "date",
        "Y_Latitude": "latitude",
        "X_Longitude": "longitude",
    },
    "europe_outbreaks": {
        "Confirmed Date": "date",
        "Country": "country",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "HPAI Strain": "strain",
        "Classification": "sampling_type",
    },
    "acap_hpai": {
        "Species": "scientific_name",
        "EnglishName": "common_name",
        "Date": "date",
        "Region": "country",
        "Location1": "state_province",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "Subtype": "strain",
        "Individuals": "n_individuals",
    },
    "uk_defra": {
        "Species": "common_name",
        "Latin.Latin Name": "scientific_name",
        "County": "county",
        "Country": "country",
        "District": "state_province",
        "Week (Year)": "date",
        "Virus Isolated": "strain",
        "Total (Positive)": "n_individuals",
    },
}

# Sampling type normalization
SAMPLING_TYPE_MAP = {
    # APHIS
    "morbidity/mortality": "mortality",
    "hunter harvest": "harvest",
    "live bird": "live",
    "hunter-harvested": "harvest",
    "live-wild": "live",
    # OAFD
    "mortality": "mortality",
    "harvest": "harvest",
    "live": "live",
    # Default
    "unknown": "unknown",
    "": "unknown",
}


def normalize_sampling_type(value: str) -> str:
    """Normalize sampling type to canonical values."""
    if value is None:
        return "unknown"
    return SAMPLING_TYPE_MAP.get(value.lower().strip(), "unknown")


def ensure_columns(df: pl.DataFrame, columns: dict[str, pl.DataType]) -> pl.DataFrame:
    """
    Ensure a DataFrame has all required columns with correct types.

    Missing columns are added as null. Extra columns are kept.
    """
    for col, dtype in columns.items():
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col))

    return df


def normalize_detection(
    df: pl.DataFrame,
    source: str,
    country: str = "Unknown",
) -> pl.DataFrame:
    """
    Normalize a detection DataFrame to canonical schema.

    Args:
        df: Raw DataFrame from source
        source: Source identifier
        country: Default country if not in data

    Returns:
        DataFrame with canonical schema
    """
    # Get field mapping for this source
    field_map = SOURCE_FIELD_MAPS.get(source, {})

    # Rename columns
    rename_map = {k: v for k, v in field_map.items() if k in df.columns}
    if rename_map:
        df = df.rename(rename_map)

    # Add source and country
    df = df.with_columns([
        pl.lit(source).alias("source"),
    ])

    if "country" not in df.columns:
        df = df.with_columns(pl.lit(country).alias("country"))

    # Normalize sampling type if present
    if "sampling_type" in df.columns:
        df = df.with_columns(
            pl.col("sampling_type").map_elements(
                normalize_sampling_type, return_dtype=pl.Utf8
            ).alias("sampling_type")
        )

    # Ensure all columns exist
    df = ensure_columns(df, DETECTION_COLUMNS)

    # Select only canonical columns (preserving order)
    canonical_cols = list(DETECTION_COLUMNS.keys())
    extra_cols = [c for c in df.columns if c not in canonical_cols]

    return df.select(canonical_cols + extra_cols)


def validate_detection(df: pl.DataFrame) -> list[str]:
    """
    Validate a detection DataFrame against schema requirements.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Check required columns exist
    required = ["source", "date", "country"]
    for col in required:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    # Check at least one species identifier
    species_cols = ["scientific_name", "common_name", "taxon_id"]
    if not any(col in df.columns for col in species_cols):
        errors.append("At least one species identifier required")

    # Check for null values in required fields
    if "source" in df.columns and df["source"].null_count() > 0:
        errors.append("Null values in 'source' column")

    # Check coordinate validity
    if "latitude" in df.columns:
        invalid_lat = df.filter(
            (pl.col("latitude").is_not_null()) &
            ((pl.col("latitude") < -90) | (pl.col("latitude") > 90))
        ).height
        if invalid_lat > 0:
            errors.append(f"Invalid latitude values: {invalid_lat} records")

    if "longitude" in df.columns:
        invalid_lon = df.filter(
            (pl.col("longitude").is_not_null()) &
            ((pl.col("longitude") < -180) | (pl.col("longitude") > 180))
        ).height
        if invalid_lon > 0:
            errors.append(f"Invalid longitude values: {invalid_lon} records")

    return errors


# =============================================================================
# SUMMARY FUNCTIONS
# =============================================================================

def detection_summary(df: pl.DataFrame) -> dict:
    """Generate summary statistics for a detection DataFrame."""
    summary = {
        "total_records": len(df),
        "sources": df["source"].unique().to_list() if "source" in df.columns else [],
    }

    if "scientific_name" in df.columns:
        summary["species_count"] = df["scientific_name"].n_unique()

    if "country" in df.columns:
        summary["countries"] = df["country"].unique().to_list()

    if "date" in df.columns:
        dates = df["date"].drop_nulls()
        if len(dates) > 0:
            summary["date_range"] = {
                "min": str(dates.min()),
                "max": str(dates.max()),
            }

    if "latitude" in df.columns and "longitude" in df.columns:
        with_coords = df.filter(
            pl.col("latitude").is_not_null() &
            pl.col("longitude").is_not_null()
        ).height
        summary["records_with_coordinates"] = with_coords

    if "sampling_type" in df.columns:
        summary["sampling_types"] = (
            df.group_by("sampling_type")
            .agg(pl.len().alias("count"))
            .sort("count", descending=True)
            .to_dicts()
        )

    return summary


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Roost Data Schemas")
    print("=" * 40)

    print("\nDetection Schema:")
    for col, dtype in DETECTION_COLUMNS.items():
        print(f"  {col}: {dtype}")

    print("\nTracking Schema:")
    for col, dtype in TRACKING_COLUMNS.items():
        print(f"  {col}: {dtype}")

    print("\nGenome Schema:")
    for col, dtype in GENOME_COLUMNS.items():
        print(f"  {col}: {dtype}")

    print(f"\nSource field mappings: {len(SOURCE_FIELD_MAPS)} sources")
