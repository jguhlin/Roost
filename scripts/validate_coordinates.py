#!/usr/bin/env python3
"""
Coordinate validation for Roost detection data.

Validates:
- Coordinate ranges (-90 to 90 lat, -180 to 180 lon)
- Suspicious zero coordinates
- Coordinate precision

Usage:
    python scripts/validate_coordinates.py
"""

import json
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")


def validate_coordinates(df: pl.DataFrame) -> dict:
    """
    Validate coordinates in detection data.

    Returns validation report dict.
    """
    total = len(df)

    # Records with coordinates
    with_coords = df.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )
    coords_count = len(with_coords)

    report = {
        "total_records": total,
        "with_coordinates": coords_count,
        "coordinate_coverage_pct": round(100 * coords_count / total, 1) if total > 0 else 0,
        "issues": [],
    }

    if coords_count == 0:
        return report

    # Range validation
    invalid_lat = with_coords.filter(
        (pl.col("latitude") < -90) | (pl.col("latitude") > 90)
    ).height
    invalid_lon = with_coords.filter(
        (pl.col("longitude") < -180) | (pl.col("longitude") > 180)
    ).height

    if invalid_lat > 0:
        report["issues"].append(f"Invalid latitude values: {invalid_lat}")
    if invalid_lon > 0:
        report["issues"].append(f"Invalid longitude values: {invalid_lon}")

    report["invalid_latitude"] = invalid_lat
    report["invalid_longitude"] = invalid_lon

    # Zero coordinates (suspicious - often indicates missing data)
    zero_coords = with_coords.filter(
        (pl.col("latitude") == 0) & (pl.col("longitude") == 0)
    ).height
    if zero_coords > 0:
        report["issues"].append(f"Zero coordinates (0, 0): {zero_coords}")
    report["zero_coordinates"] = zero_coords

    # Coordinate ranges
    report["latitude_range"] = {
        "min": round(float(with_coords["latitude"].min()), 4),
        "max": round(float(with_coords["latitude"].max()), 4),
    }
    report["longitude_range"] = {
        "min": round(float(with_coords["longitude"].min()), 4),
        "max": round(float(with_coords["longitude"].max()), 4),
    }

    # By source
    source_stats = (
        df
        .group_by("source")
        .agg([
            pl.len().alias("total"),
            (pl.col("latitude").is_not_null() & pl.col("longitude").is_not_null()).sum().alias("with_coords"),
        ])
        .with_columns(
            (100 * pl.col("with_coords") / pl.col("total")).round(1).alias("pct")
        )
        .sort("total", descending=True)
    )
    report["by_source"] = [
        {
            "source": row["source"],
            "total": row["total"],
            "with_coordinates": row["with_coords"],
            "coverage_pct": row["pct"],
        }
        for row in source_stats.iter_rows(named=True)
    ]

    # Validation status
    report["valid"] = len(report["issues"]) == 0

    return report


def main():
    print("=" * 60)
    print("COORDINATE VALIDATION")
    print("=" * 60)

    # Load detections
    detections_file = DATA_DIR / "detections_merged.parquet"
    if not detections_file.exists():
        print("No detections file found.")
        return

    df = pl.read_parquet(detections_file)
    print(f"\nLoaded {len(df):,} detection records")

    # Validate
    report = validate_coordinates(df)

    # Print results
    print(f"\nCoordinate Coverage:")
    print(f"  Records with coordinates: {report['with_coordinates']:,} / {report['total_records']:,}")
    print(f"  Coverage: {report['coordinate_coverage_pct']:.1f}%")

    if report['with_coordinates'] > 0:
        print(f"\nCoordinate Ranges:")
        print(f"  Latitude:  {report['latitude_range']['min']:.2f} to {report['latitude_range']['max']:.2f}")
        print(f"  Longitude: {report['longitude_range']['min']:.2f} to {report['longitude_range']['max']:.2f}")

    print(f"\nValidation Issues:")
    if report["issues"]:
        for issue in report["issues"]:
            print(f"  - {issue}")
    else:
        print("  None - all coordinates valid")

    print(f"\nBy Source:")
    for src in report["by_source"]:
        print(f"  {src['source']:20s} {src['with_coordinates']:5,} / {src['total']:5,} ({src['coverage_pct']:.0f}%)")

    # Save report
    report_file = DATA_DIR / "coordinate_validation.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved report to {report_file}")

    if report["valid"]:
        print("\n✓ All coordinates valid")
    else:
        print(f"\n✗ Found {len(report['issues'])} validation issues")


if __name__ == "__main__":
    main()
