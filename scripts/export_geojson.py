#!/usr/bin/env python3
"""
GeoJSON export for Roost.

Exports georeferenced detection data with susceptibility scores
for visualization in GIS tools, web maps, or Kepler.gl.

Output layers:
1. detections.geojson - Individual detection points
2. detections_by_species.geojson - Aggregated by species (centroid)
3. detections_by_country.geojson - Aggregated by country
4. hotspots.geojson - High-density detection clusters

Usage:
    python scripts/export_geojson.py
    python scripts/export_geojson.py --year 2024
    python scripts/export_geojson.py --species "Anas platyrhynchos"
"""

import json
from datetime import date
from pathlib import Path

import polars as pl

DATA_DIR = Path("data")
WEB_DATA_DIR = Path("web/public/data")
OUTPUT_DIR = DATA_DIR / "geojson"


def load_data() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Load detection and susceptibility data."""
    # Read from the shipped detections (includes geocoded coordinates from
    # the geocoding pipeline — state_area_scatter for coordinate-less US rows)
    detections = pl.read_parquet(WEB_DATA_DIR / "detections.parquet")

    susceptibility_file = DATA_DIR / "susceptibility_scores.parquet"
    if susceptibility_file.exists():
        susceptibility = pl.read_parquet(susceptibility_file)
    else:
        susceptibility = pl.DataFrame()

    return detections, susceptibility


def to_geojson_point(lon: float, lat: float, properties: dict) -> dict:
    """Create a GeoJSON Point feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": properties
    }


def to_geojson_collection(features: list) -> dict:
    """Create a GeoJSON FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": features
    }


def export_detections(
    detections: pl.DataFrame,
    susceptibility: pl.DataFrame,
    year: int | None = None,
    species: str | None = None,
) -> dict:
    """
    Export individual detection points as GeoJSON.

    Args:
        detections: Detection DataFrame
        susceptibility: Susceptibility scores DataFrame
        year: Filter to specific year (optional)
        species: Filter to specific species (optional)

    Returns:
        GeoJSON FeatureCollection
    """
    # Filter to georeferenced records
    geo = detections.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )

    # Extract year from date if available
    if "date_detected" in geo.columns:
        geo = geo.with_columns([
            pl.col("date_detected").str.slice(0, 4).cast(pl.Int32, strict=False).alias("year")
        ])

    # Apply filters
    if year and "year" in geo.columns:
        geo = geo.filter(pl.col("year") == year)
    if species:
        geo = geo.filter(pl.col("scientific_name") == species)

    # Join with susceptibility scores
    if len(susceptibility) > 0:
        geo = geo.join(
            susceptibility.select([
                "scientific_name",
                "common_name",
                "susceptibility_score",
                "susceptibility_class",
                "confidence",
                "has_rigi",
            ]),
            on="scientific_name",
            how="left"
        )

    # Build features
    features = []
    for row in geo.iter_rows(named=True):
        properties = {
            "scientific_name": row.get("scientific_name"),
            "common_name": row.get("common_name"),
            "date": str(row.get("date_detected")) if row.get("date_detected") else None,
            "year": row.get("year"),
            "country": row.get("country"),
            "state": row.get("state"),
            "source": row.get("source"),
            "strain": row.get("strain"),
            "sampling_method": row.get("sampling_method_raw"),
        }

        # Add susceptibility if available
        if "susceptibility_score" in row:
            properties["susceptibility_score"] = row.get("susceptibility_score")
            properties["susceptibility_class"] = row.get("susceptibility_class")
            properties["confidence"] = row.get("confidence")
            properties["has_rigi"] = row.get("has_rigi")

        # Clean None values
        properties = {k: v for k, v in properties.items() if v is not None}

        features.append(to_geojson_point(
            row["longitude"],
            row["latitude"],
            properties
        ))

    return to_geojson_collection(features)


def export_by_species(
    detections: pl.DataFrame,
    susceptibility: pl.DataFrame,
) -> dict:
    """
    Export species-level aggregates (centroid of detections).
    """
    # Filter to georeferenced
    geo = detections.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )

    # Aggregate by species
    species_agg = geo.group_by("scientific_name").agg([
        pl.col("latitude").mean().alias("centroid_lat"),
        pl.col("longitude").mean().alias("centroid_lon"),
        pl.col("latitude").min().alias("lat_min"),
        pl.col("latitude").max().alias("lat_max"),
        pl.col("longitude").min().alias("lon_min"),
        pl.col("longitude").max().alias("lon_max"),
        pl.len().alias("detection_count"),
        pl.col("country").n_unique().alias("country_count"),
    ])

    # Join susceptibility
    if len(susceptibility) > 0:
        species_agg = species_agg.join(
            susceptibility.select([
                "scientific_name",
                "common_name",
                "susceptibility_score",
                "susceptibility_class",
                "confidence",
                "has_rigi",
                "order",
                "family",
            ]),
            on="scientific_name",
            how="left"
        )

    # Build features
    features = []
    for row in species_agg.iter_rows(named=True):
        properties = {
            "scientific_name": row["scientific_name"],
            "detection_count": row["detection_count"],
            "country_count": row["country_count"],
            "lat_range": [row["lat_min"], row["lat_max"]],
            "lon_range": [row["lon_min"], row["lon_max"]],
        }

        # Add taxonomy and susceptibility
        for field in ["common_name", "order", "family", "susceptibility_score", "susceptibility_class", "confidence", "has_rigi"]:
            if field in row and row[field] is not None:
                properties[field] = row[field]

        features.append(to_geojson_point(
            row["centroid_lon"],
            row["centroid_lat"],
            properties
        ))

    return to_geojson_collection(features)


# Static ISO3 centroids (D108): countries with detections but no
# georeferenced rows still deserve a map feature at their centroid
ISO3_CENTROIDS = {
    "ALA": (20.0, 60.2), "ARE": (24.0, 54.0), "CIV": (7.5, -5.5),
    "IDN": (-2.5, 118.0), "MMR": (21.0, 96.0), "PSE": (31.9, 35.2),
    "TGO": (8.6, 1.0), "THA": (15.0, 101.0),
    # Not in Natural Earth 110m (tiny/remote territories with detections)
    "HMD": (-53.1, 73.8), "SGS": (-54.5, -37.0), "SHN": (-15.9, -5.7),
    "IOT": (-7.3, 72.4), "SVJ": (78.8, 17.2), "BVT": (-54.4, 3.4),
}


def _load_ne_iso3_centroids() -> dict:
    """Derive ISO3 → centroid from the Natural Earth 110m shapes so every
    country with detections gets a map feature even without georeferenced
    points (mean of vertices — fine at 110m zoom for centroid markers)."""
    import json as _json

    def walk(coords, lats, lons):
        if isinstance(coords[0], (int, float)):
            lons.append(coords[0]); lats.append(coords[1])
        else:
            for c in coords:
                walk(c, lats, lons)

    out = {}
    path = DATA_DIR / "geojson" / "ne_110m_countries.geojson"
    if not path.exists():
        return out
    try:
        gj = _json.loads(path.read_text())
    except (_json.JSONDecodeError, OSError):
        return out
    for f in gj.get("features", []):
        iso3 = (f.get("properties") or {}).get("ISO_A3_EH") \
            or (f.get("properties") or {}).get("ISO_A3")
        if not iso3 or iso3 == "-99":
            continue
        geom = f.get("geometry") or {}
        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        lats, lons = [], []
        walk(geom["coordinates"], lats, lons)
        if lats:
            out[iso3] = (sum(lats) / len(lats), sum(lons) / len(lons))
    return out


# Complete centroid map: manual entries win, NE-derived fills the rest
ISO3_CENTROIDS = {**_load_ne_iso3_centroids(), **ISO3_CENTROIDS}


def export_by_country(detections: pl.DataFrame) -> dict:
    """
    Export country-level aggregates.

    Note: Uses centroid approximation. For proper country polygons,
    join with a country boundaries dataset.
    """
    with_country = detections.filter(pl.col("country").is_not_null() & (pl.col("country") != "Global"))

    # Filter to georeferenced with country
    geo = with_country.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )

    # Aggregate by country
    country_agg = geo.group_by("country").agg([
        pl.col("latitude").mean().alias("centroid_lat"),
        pl.col("longitude").mean().alias("centroid_lon"),
        pl.len().alias("detection_count"),
        pl.col("scientific_name").n_unique().alias("species_count"),
    ])

    # Countries with detections but zero georeferenced rows: add features
    # at their static centroid so the map count matches the data
    geo_countries = set(country_agg["country"].to_list())
    all_counts = with_country.group_by("country").agg([
        pl.len().alias("detection_count"),
        pl.col("scientific_name").n_unique().alias("species_count"),
    ])
    extra_rows = []
    for row in all_counts.iter_rows(named=True):
        c = row["country"]
        if c not in geo_countries and c in ISO3_CENTROIDS:
            lat, lon = ISO3_CENTROIDS[c]
            extra_rows.append({"country": c, "centroid_lat": lat, "centroid_lon": lon,
                               "detection_count": row["detection_count"],
                               "species_count": row["species_count"]})
    if extra_rows:
        extra = pl.DataFrame(extra_rows, schema={
            "country": pl.String, "centroid_lat": pl.Float64, "centroid_lon": pl.Float64,
            "detection_count": pl.UInt32, "species_count": pl.UInt32})
        country_agg = pl.concat([country_agg, extra], how="diagonal")

    features = []
    for row in country_agg.iter_rows(named=True):
        features.append(to_geojson_point(
            row["centroid_lon"],
            row["centroid_lat"],
            {
                "country": row["country"],
                "detection_count": row["detection_count"],
                "species_count": row["species_count"],
            }
        ))

    return to_geojson_collection(features)


def export_hotspots(
    detections: pl.DataFrame,
    grid_size: float = 1.0,  # Degrees
    min_detections: int = 10,
) -> dict:
    """
    Export detection hotspots using grid-based clustering.

    Args:
        detections: Detection DataFrame
        grid_size: Grid cell size in degrees
        min_detections: Minimum detections to be considered a hotspot
    """
    # Filter to georeferenced
    geo = detections.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    )

    # Create grid cells
    geo = geo.with_columns([
        (pl.col("latitude") / grid_size).floor().alias("lat_cell"),
        (pl.col("longitude") / grid_size).floor().alias("lon_cell"),
    ])

    # Aggregate by grid cell
    hotspots = geo.group_by(["lat_cell", "lon_cell"]).agg([
        pl.col("latitude").mean().alias("centroid_lat"),
        pl.col("longitude").mean().alias("centroid_lon"),
        pl.len().alias("detection_count"),
        pl.col("scientific_name").n_unique().alias("species_count"),
        pl.col("country").first(),
    ]).filter(pl.col("detection_count") >= min_detections)

    # Calculate intensity (normalize to 0-1)
    max_count = hotspots["detection_count"].max()
    if max_count and max_count > 0:
        hotspots = hotspots.with_columns([
            (pl.col("detection_count") / max_count).alias("intensity")
        ])
    else:
        hotspots = hotspots.with_columns([
            pl.lit(0.0).alias("intensity")
        ])

    features = []
    for row in hotspots.iter_rows(named=True):
        features.append(to_geojson_point(
            row["centroid_lon"],
            row["centroid_lat"],
            {
                "detection_count": row["detection_count"],
                "species_count": row["species_count"],
                "country": row.get("country"),
                "intensity": round(row["intensity"], 3),
                "grid_lat": row["lat_cell"] * grid_size,
                "grid_lon": row["lon_cell"] * grid_size,
            }
        ))

    return to_geojson_collection(features)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export GeoJSON layers")
    parser.add_argument("--year", type=int, help="Filter to specific year")
    parser.add_argument("--species", help="Filter to specific species")
    parser.add_argument("--grid-size", type=float, default=1.0, help="Hotspot grid size (degrees)")
    args = parser.parse_args()

    print("=" * 60)
    print("EXPORTING GEOJSON LAYERS")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    detections, susceptibility = load_data()

    geo_count = detections.filter(
        pl.col("latitude").is_not_null() &
        pl.col("longitude").is_not_null()
    ).height
    print(f"  Detections: {len(detections):,} total, {geo_count:,} georeferenced")
    print(f"  Susceptibility scores: {len(susceptibility):,} species")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Export layers
    print("\nExporting layers...")

    # 1. Individual detections
    print("  detections.geojson...")
    det_geojson = export_detections(detections, susceptibility, args.year, args.species)
    with open(OUTPUT_DIR / "detections.geojson", "w") as f:
        json.dump(det_geojson, f)
    print(f"    {len(det_geojson['features']):,} features")

    # 2. By species
    print("  detections_by_species.geojson...")
    species_geojson = export_by_species(detections, susceptibility)
    with open(OUTPUT_DIR / "detections_by_species.geojson", "w") as f:
        json.dump(species_geojson, f)
    print(f"    {len(species_geojson['features']):,} features")

    # 3. By country
    print("  detections_by_country.geojson...")
    country_geojson = export_by_country(detections)
    with open(OUTPUT_DIR / "detections_by_country.geojson", "w") as f:
        json.dump(country_geojson, f)
    print(f"    {len(country_geojson['features']):,} features")

    # 4. Hotspots
    print("  hotspots.geojson...")
    hotspot_geojson = export_hotspots(detections, grid_size=args.grid_size)
    with open(OUTPUT_DIR / "hotspots.geojson", "w") as f:
        json.dump(hotspot_geojson, f)
    print(f"    {len(hotspot_geojson['features']):,} features")

    # Summary
    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nLayers exported:")
    print(f"  detections.geojson          - {len(det_geojson['features']):,} detection points")
    print(f"  detections_by_species.geojson - {len(species_geojson['features']):,} species centroids")
    print(f"  detections_by_country.geojson - {len(country_geojson['features']):,} country aggregates")
    print(f"  hotspots.geojson             - {len(hotspot_geojson['features']):,} hotspot cells")

    print("\nVisualization options:")
    print("  - kepler.gl: Drag and drop GeoJSON files")
    print("  - QGIS: Open as vector layers")
    print("  - Mapbox/Leaflet: Load as GeoJSON sources")

    # Write metadata
    metadata = {
        "generated": str(date.today()),
        "total_detections": len(detections),
        "georeferenced_detections": geo_count,
        "layers": {
            "detections": len(det_geojson["features"]),
            "by_species": len(species_geojson["features"]),
            "by_country": len(country_geojson["features"]),
            "hotspots": len(hotspot_geojson["features"]),
        },
        "filters": {
            "year": args.year,
            "species": args.species,
        },
        "hotspot_grid_size_degrees": args.grid_size,
    }
    with open(OUTPUT_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    main()
