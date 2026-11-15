#!/usr/bin/env python3
"""Geocode coordinate-less detections via county/state centroids (W1).

Strategy (provenance ladder: MODELED):
  1. County centroids — derived from georeferenced detections in the same
     (state, county). If 5+ georeferenced detections exist in a county,
     their mean lat/lon is that county's centroid.
  2. State centroids — US Census state centroids (public data, inlined).
     Applied when no county-level match exists.

The result adds latitude/longitude to previously coordinate-less rows,
with a geocode_method column for provenance ('county_centroid',
'state_centroid', or null for already-georeferenced rows).

Usage: pixi run python scripts/geocode_detections.py
"""

import polars as pl
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEB = ROOT / "web" / "public" / "data"

# US state centroids (Census Bureau, public domain)
STATE_CENTROIDS = {
    "Alabama": (32.806671, -86.791130), "Alaska": (61.370716, -152.404419),
    "Arizona": (33.729759, -111.431221), "Arkansas": (34.969704, -92.373123),
    "California": (36.116203, -119.681564), "Colorado": (39.059811, -105.311104),
    "Connecticut": (41.597782, -72.755371), "Delaware": (39.318523, -75.507141),
    "Florida": (27.766279, -81.686783), "Georgia": (33.040619, -83.643074),
    "Hawaii": (21.094318, -77.134934), "Idaho": (44.240459, -114.478828),
    "Illinois": (40.349457, -88.986137), "Indiana": (39.849426, -86.258278),
    "Iowa": (42.011539, -93.210526), "Kansas": (38.526600, -96.726486),
    "Kentucky": (37.668140, -84.670067), "Louisiana": (31.169546, -91.867805),
    "Maine": (44.693947, -69.381927), "Maryland": (39.063946, -76.802101),
    "Massachusetts": (42.230171, -71.530106), "Michigan": (43.326618, -84.536095),
    "Minnesota": (45.694454, -93.900192), "Mississippi": (32.741646, -89.678696),
    "Missouri": (38.456085, -92.288368), "Montana": (46.921925, -110.454353),
    "Nebraska": (41.125370, -98.268082), "Nevada": (38.313515, -117.055374),
    "New Hampshire": (43.680553, -71.581182), "New Jersey": (40.298904, -74.521011),
    "New Mexico": (34.840515, -106.248482), "New York": (42.165726, -74.948051),
    "North Carolina": (35.630066, -79.806419), "North Dakota": (47.528912, -99.784012),
    "Ohio": (40.388783, -82.764915), "Oklahoma": (35.565342, -97.528407),
    "Oregon": (43.933184, -120.558298), "Pennsylvania": (40.590752, -77.209755),
    "Rhode Island": (41.680893, -71.511780), "South Carolina": (33.856892, -80.945007),
    "South Dakota": (44.444328, -100.226327), "Tennessee": (35.747845, -86.692345),
    "Texas": (31.054487, -97.563461), "Utah": (40.150032, -111.862434),
    "Vermont": (44.045876, -72.710686), "Virginia": (37.769337, -78.169968),
    "Washington": (47.400902, -121.490494), "West Virginia": (38.640935, -80.622766),
    "Wisconsin": (44.268543, -89.616508), "Wyoming": (42.755966, -107.302490),
    "District of Columbia": (38.9072, -77.0369),
}


def apply_geocoding(df: pl.DataFrame) -> pl.DataFrame:
    """Apply state-area-scatter geocoding to coordinate-less US rows.
    Returns a new DataFrame with latitude/longitude/geocode_method filled in."""
    import hashlib
    
    STATE_BBOX = {
        'Alabama': (30.2, -88.5, 35.0, -84.9), 'Alaska': (55.0, -168.0, 71.4, -130.0),
        'Arizona': (31.3, -115.0, 37.0, -108.0), 'Arkansas': (33.0, -94.6, 36.5, -89.6),
        'California': (32.5, -124.4, 42.0, -114.1), 'Colorado': (37.0, -109.1, 41.0, -102.0),
        'Connecticut': (40.9, -73.7, 42.1, -71.8), 'Delaware': (38.4, -75.8, 39.8, -74.9),
        'Florida': (24.5, -87.6, 31.0, -80.0), 'Georgia': (30.4, -85.6, 35.0, -80.8),
        'Hawaii': (18.9, -160.3, 22.2, -154.8), 'Idaho': (42.0, -117.2, 49.0, -111.0),
        'Illinois': (36.9, -91.5, 42.5, -87.0), 'Indiana': (37.8, -88.1, 41.8, -84.8),
        'Iowa': (40.4, -96.6, 43.5, -90.1), 'Kansas': (37.0, -102.0, 40.0, -94.6),
        'Kentucky': (36.5, -89.5, 39.1, -82.0), 'Louisiana': (29.0, -94.0, 33.0, -89.0),
        'Maine': (43.0, -71.1, 47.5, -66.9), 'Maryland': (37.9, -79.5, 39.7, -75.0),
        'Massachusetts': (41.2, -73.5, 43.0, -69.9), 'Michigan': (41.7, -90.4, 48.3, -82.1),
        'Minnesota': (43.5, -97.2, 49.4, -89.5), 'Mississippi': (30.2, -91.7, 35.0, -88.1),
        'Missouri': (36.0, -95.8, 40.6, -88.1), 'Montana': (44.4, -116.0, 49.0, -103.0),
        'Nebraska': (40.0, -104.1, 43.0, -95.3), 'Nevada': (35.0, -120.0, 42.0, -114.0),
        'New Hampshire': (42.7, -72.6, 45.3, -70.6), 'New Jersey': (38.9, -75.6, 41.4, -73.9),
        'New Mexico': (31.3, -109.1, 37.0, -103.0), 'New York': (40.5, -79.8, 45.0, -71.9),
        'North Carolina': (33.8, -84.3, 36.6, -75.5), 'North Dakota': (45.9, -104.1, 49.0, -96.6),
        'Ohio': (38.4, -84.8, 42.0, -80.5), 'Oklahoma': (33.6, -103.0, 37.0, -94.4),
        'Oregon': (42.0, -124.6, 46.3, -116.5), 'Pennsylvania': (39.7, -80.6, 42.3, -74.7),
        'Rhode Island': (41.1, -71.9, 42.0, -71.1), 'South Carolina': (32.0, -83.4, 35.2, -78.5),
        'South Dakota': (42.5, -104.1, 46.0, -96.4), 'Tennessee': (35.0, -90.3, 36.7, -81.6),
        'Texas': (25.8, -106.6, 36.5, -93.5), 'Utah': (37.0, -114.1, 42.0, -109.0),
        'Vermont': (42.7, -73.4, 45.0, -71.5), 'Virginia': (36.5, -83.7, 39.5, -75.2),
        'Washington': (45.5, -124.8, 49.0, -116.9), 'West Virginia': (37.2, -82.6, 40.6, -77.7),
        'Wisconsin': (42.5, -92.9, 47.0, -86.8), 'Wyoming': (41.0, -111.1, 45.0, -104.0),
        'District of Columbia': (38.8, -77.1, 39.0, -76.9),
    }

    no_geo = df.filter(pl.col("latitude").is_null())
    if no_geo.height == 0:
        return df

    scatter = {}
    for state, bbox in STATE_BBOX.items():
        lat_min, lon_min, lat_max, lon_max = bbox
        m = 0.1
        counties = (no_geo.filter(pl.col("state") == state)
                    .select("county").unique()["county"].to_list())
        for county in counties:
            h = hashlib.md5(f"{state}|{county}".encode()).hexdigest()
            fx = int(h[0:4], 16) / 65535
            fy = int(h[4:8], 16) / 65535
            lat = round(lat_min + (lat_max - lat_min) * (m + fy * (1 - 2*m)), 4)
            lon = round(lon_min + (lon_max - lon_min) * (m + fx * (1 - 2*m)), 4)
            scatter[(state, county)] = (lat, lon)

    if not scatter:
        return df

    keys = list(scatter.keys())
    lookup = pl.DataFrame({
        "state": [k[0] for k in keys],
        "county": [k[1] for k in keys],
        "scat_lat": [scatter[k][0] for k in keys],
        "scat_lon": [scatter[k][1] for k in keys],
    })
    df = df.join(lookup, on=["state", "county"], how="left")
    df = df.with_columns([
        pl.when(pl.col("latitude").is_null() & pl.col("scat_lat").is_not_null())
          .then(pl.col("scat_lat")).otherwise(pl.col("latitude")).alias("latitude"),
        pl.when(pl.col("longitude").is_null() & pl.col("scat_lon").is_not_null())
          .then(pl.col("scat_lon")).otherwise(pl.col("longitude")).alias("longitude"),
        pl.when(pl.col("latitude").is_null() & pl.col("scat_lat").is_not_null())
          .then(pl.lit("state_area_scatter"))
          .otherwise(pl.col("geocode_method") if "geocode_method" in df.columns else pl.lit(None, dtype=pl.Utf8))
          .alias("geocode_method"),
    ]).drop(["scat_lat", "scat_lon"])
    return df


def main():
    df = pl.read_parquet(WEB / "detections.parquet")
    total = df.height
    already = df.filter(pl.col("latitude").is_not_null()).height
    no_geo = df.filter(pl.col("latitude").is_null())
    print(f"Total: {total} | already georeferenced: {already} | coordinate-less: {no_geo.height}")

    # 1. Build county centroids from our own georeferenced data
    geo = df.filter(pl.col("latitude").is_not_null() & pl.col("county").is_not_null() & (pl.col("county") != ""))
    county_centroids = (
        geo.group_by(["state", "county"])
        .agg(
            pl.col("latitude").mean().alias("clat"),
            pl.col("longitude").mean().alias("clon"),
            pl.len().alias("n"),
        )
        .filter(pl.col("n") >= 3)  # need 3+ for a reliable centroid
    )
    print(f"County centroids from own data: {county_centroids.height} counties")

    # Join county centroids to coordinate-less rows
    no_geo_with_county = no_geo.filter(pl.col("county").is_not_null() & (pl.col("county") != ""))
    county_matched = no_geo_with_county.join(
        county_centroids.select(["state", "county", "clat", "clon"]),
        on=["state", "county"], how="inner",
    )
    print(f"  matched to county centroids: {county_matched.height} rows")

    # 2. State centroid fallback
    state_lookup = pl.DataFrame({
        "state": list(STATE_CENTROIDS.keys()),
        "slat": [v[0] for v in STATE_CENTROIDS.values()],
        "slon": [v[1] for v in STATE_CENTROIDS.values()],
    })
    state_matched = no_geo.join(state_lookup, on="state", how="inner")
    # Exclude rows already matched at county level
    county_keys = set(zip(county_matched["state"], county_matched["county"]))
    state_only = state_matched.filter(
        ~pl.struct(["state", "county"]).map_elements(
            lambda x: (x["state"], x["county"] if x["county"] else "") in county_keys,
            return_dtype=pl.Boolean,
        )
    ) if county_keys else state_matched
    print(f"  matched to state centroids: {state_only.height} rows")

    # Apply the geocoding
    # County-level (higher precision)
    df = df.with_columns([
        pl.when(
            pl.col("latitude").is_null()
            & pl.col("county").is_not_null() & (pl.col("county") != "")
        )
        .then(
            # join county centroid — we need to look up each row
            pl.col("county").map_elements(lambda c: c, return_dtype=pl.Utf8)
        )
        .otherwise(pl.col("latitude")).alias("latitude"),
    ])

    # Simpler: build a full-row update using joins
    # Reset and do it properly
    df = pl.read_parquet(WEB / "detections.parquet")

    # Apply county centroids
    county_updates = (
        df.filter(pl.col("latitude").is_null())
        .join(county_centroids.select(["state", "county", "clat", "clon"]),
              on=["state", "county"], how="inner")
        .with_columns([
            pl.col("clat").alias("latitude"),
            pl.col("clon").alias("longitude"),
            pl.lit("county_centroid").alias("geocode_method"),
        ])
        .drop(["clat", "clon"])
    )

    # Apply state centroids (for rows not county-matched)
    county_keys_set = set(zip(
        county_updates["state"].to_list(),
        county_updates["county"].to_list(),
    )) if county_updates.height > 0 else set()

    remaining = df.filter(pl.col("latitude").is_null()).join(
        county_centroids.select(["state", "county"]), on=["state", "county"], how="anti",
    ) if county_centroids.height > 0 else df.filter(pl.col("latitude").is_null())

    state_updates = (
        remaining.join(state_lookup, on="state", how="inner")
        .with_columns([
            pl.col("slat").alias("latitude"),
            pl.col("slon").alias("longitude"),
            pl.lit("state_centroid").alias("geocode_method"),
        ])
        .drop(["slat", "slon"])
    )

    # Combine: original geo'd rows + county geocoded + state geocoded + still-geocoded-less
    geocoded = df.filter(pl.col("latitude").is_not_null()).with_columns(
        pl.lit(None, dtype=pl.Utf8).alias("geocode_method"))

    still_missing = df.filter(pl.col("latitude").is_null()).join(
        county_centroids.select(["state", "county"]), on=["state", "county"], how="anti",
    ).join(state_lookup.select(["state"]), on="state", how="anti") \
     if county_centroids.height > 0 else df.filter(pl.col("latitude").is_null()).join(
         state_lookup.select(["state"]), on="state", how="anti")

    if still_missing.height > 0:
        still_missing = still_missing.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("geocode_method"))

    # Align schemas before concat
    cols = geocoded.columns
    for part in [county_updates, state_updates, still_missing]:
        if part.height > 0:
            for c in cols:
                if c not in part.columns:
                    part = part.with_columns(pl.lit(None).alias(c))
            # ensure column order
            part = part.select(cols)
            geocoded = pl.concat([geocoded, part], how="vertical")

    geocoded = geocoded.sort("record_id") if "record_id" in geocoded.columns else geocoded

    now_geo = geocoded.filter(pl.col("latitude").is_not_null()).height
    print(f"\nResult: {now_geo}/{total} georeferenced ({now_geo/total:.1%})")
    print(f"  county centroids: {county_updates.height} rows")
    print(f"  state centroids: {state_updates.height} rows")
    print(f"  still missing: {still_missing.height} rows")
    by_method = geocoded.group_by("geocode_method").len().sort("len", descending=True)
    print(by_method.to_dicts())

    geocoded.write_parquet(WEB / "detections.parquet")
    print(f"\nWrote {WEB / 'detections.parquet'}")


if __name__ == "__main__":
    main()
