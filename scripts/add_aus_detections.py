#!/usr/bin/env python3
"""
Add Australian H5N1 detections to the database and GeoJSON.

Uses scraped data from agriculture.gov.au with geocoded coordinates.
"""

import json
from datetime import datetime
from pathlib import Path

import polars as pl

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"

# Australian locality coordinates (approximate)
# Format: "Locality, STATE": (lat, lon)
AUS_LOCALITIES = {
    # Victoria - Major coastal locations
    "Portland, VIC": (-38.3333, 141.6000),
    "Nelson, VIC": (-38.0500, 141.0000),
    "Nelson Estuary, VIC": (-38.0500, 141.0167),
    "Port Campbell, VIC": (-38.6167, 143.0167),
    "Port Fairy, VIC": (-38.3833, 142.2333),
    "Warrnambool, VIC": (-38.3833, 142.4833),
    "Warnambool, VIC": (-38.3833, 142.4833),  # Alternate spelling
    "Apollo Bay, VIC": (-38.7500, 143.6667),
    "Apollo Bay Harbour, VIC": (-38.7583, 143.6700),
    "Lorne, VIC": (-38.5333, 143.9833),
    "Torquay, VIC": (-38.3333, 144.3167),
    "Sorrento, VIC": (-38.3397, 144.7411),
    "Blairgowrie, VIC": (-38.3575, 144.7767),
    "Rosebud, VIC": (-38.3500, 144.9000),
    "Dromana Beach, VIC": (-38.3333, 144.9667),
    "McCrae Beach, VIC": (-38.3500, 144.9333),
    "Mt Eliza, VIC": (-38.1833, 145.0833),
    "Frankston, VIC": (-38.1500, 145.1167),
    "Summerlands, VIC": (-38.5167, 145.2333),
    "Phillip Island, VIC": (-38.4833, 145.2333),
    "Newhaven, VIC": (-38.5167, 145.3500),
    "Corinella, VIC": (-38.4636, 145.4489),
    "Coronet Bay, VIC": (-38.4833, 145.4500),
    "Cape Patterson, VIC": (-38.6667, 145.6333),
    "Point Lonsdale, VIC": (-38.2833, 144.6167),
    "St Leonards Beach, VIC": (-38.1667, 144.7167),
    "Swan Bay, VIC": (-38.2333, 144.6833),
    "Werribee, VIC": (-37.9000, 144.6667),
    "Wantirna South, VIC": (-37.8667, 145.2333),
    "Wheelers Hill, VIC": (-37.9000, 145.1833),
    "Oak Park, VIC": (-37.7167, 144.9167),
    "Doncaster East, VIC": (-37.7833, 145.1500),
    "Christmas Hills, VIC": (-37.6500, 145.3167),
    "Bacchus Marsh, VIC": (-37.6667, 144.4333),
    "Kyneton, VIC": (-37.2500, 144.4500),
    "Peterborough, VIC": (-38.6167, 142.8667),
    "Princetown, VIC": (-38.6833, 143.1500),
    "Lakes Entrance, VIC": (-37.8833, 148.0000),
    "Bumberrah, VIC": (-37.8500, 147.6000),
    "Hamilton, VIC": (-37.7333, 142.0167),
    "Hawkesdale, VIC": (-38.1167, 142.3500),
    "Allansford, VIC": (-38.3833, 142.6000),
    "Tyrendarra, VIC": (-38.2167, 141.8000),
    "Logans Beach, VIC": (-38.4167, 142.5167),
    "Yambuk, VIC": (-38.3000, 142.0500),
    "Killarney Beach, VIC": (-38.3833, 142.2333),
    "Sandy Point WP, VIC": (-38.8333, 146.1167),
    "Clyde, VIC": (-38.1333, 145.3333),
    "St Andrews Beach, VIC": (-38.4333, 144.8000),
    "Sugarloaf, VIC": (-37.6833, 145.2333),
    "Red Cliffs, VIC": (-34.3000, 142.1833),
    # Tasmania
    "Scottsdale, TAS": (-41.1500, 147.5167),
    "Lulworth, TAS": (-41.0667, 146.7833),
    "King Island, TAS": (-39.8833, 143.8833),
    "Currie, TAS": (-39.9333, 143.8500),
    "Rocky Cape, TAS": (-40.9000, 145.5167),
    "Burnie, TAS": (-41.0500, 145.9000),
    "Sulphur Creek, TAS": (-41.1000, 145.9500),
    "Burgess Cove, TAS": (-41.0500, 147.0000),
    # New South Wales
    "Merimbula, NSW": (-36.8833, 149.9000),
    "Narooma, NSW": (-36.2167, 150.0667),
    "Eden, NSW": (-37.0667, 149.9000),
    "Hawks Nest, NSW": (-32.6667, 152.1667),
    "Coomealla, NSW": (-34.0667, 142.0500),
    # Queensland
    "Castaways Beach, QLD": (-26.4333, 153.0833),
    "Moreton Island, QLD": (-27.1500, 153.4000),
    # South Australia - Major locations
    "Port MacDonnell, SA": (-38.0500, 140.7000),
    "Carpenter Rocks, SA": (-37.9500, 140.4167),
    "Beachport, SA": (-37.4833, 140.0167),
    "Robe, SA": (-37.1667, 139.7500),
    "North Page, SA": (-35.7833, 137.0167),
    "Point Turton, SA": (-34.9333, 137.3000),
    "Pelican Point, SA": (-34.8167, 138.4833),
    "Middleton, SA": (-35.5167, 138.7000),
    "Southend, SA": (-37.5500, 140.1333),
    "Clayton Bay, SA": (-35.5000, 138.9167),
    "Goolwa Channel, SA": (-35.5000, 138.7833),
    "Milang, SA": (-35.4000, 138.9833),
    "D'Estrees Bay, SA": (-35.9667, 137.5333),
    "Christies Beach, SA": (-35.1333, 138.5000),
    "Normanville, SA": (-35.4500, 138.3167),
    "Arno Bay, SA": (-33.9167, 136.5833),
    "Avenue Range, SA": (-37.1333, 140.2833),
    "West Range, SA": (-37.0500, 140.2000),
    "Novar Gardens, SA": (-34.9667, 138.5333),
    "Mylor, SA": (-35.0500, 138.7667),
    "Marino, SA": (-35.0500, 138.5167),
    "West Beach, SA": (-34.9500, 138.5167),
    "Rapid Bay, SA": (-35.5167, 138.1833),
    "Tanunda, SA": (-34.5167, 138.9667),
    "Lucky Bay, SA": (-34.0167, 135.8167),
    "Tarpeena, SA": (-37.5833, 140.2833),
    "Emu Bay, SA": (-35.7833, 137.5000),
    "Flagstaff Hill, SA": (-35.0500, 138.5833),
    "McLaren Vale, SA": (-35.2167, 138.5500),
    "Victor Harbor, SA": (-35.5500, 138.6167),
    "Penola, SA": (-37.3833, 140.8333),
    "Cape Jervis, SA": (-35.6000, 138.1000),
    "Cape Douglas, SA": (-37.9667, 140.6333),
    "Brown Beach, SA": (-35.5833, 138.5833),
    "Kohinoor, SA": (-37.0333, 140.2667),
    "Cape Jaffa, SA": (-36.9500, 139.6833),
    "O'Sullivan Beach, SA": (-35.1167, 138.4833),
    "Padthaway, SA": (-36.6167, 140.5000),
    "North Haven, SA": (-34.7833, 138.4833),
    # Western Australia
    "Mullaloo, WA": (-31.7667, 115.7333),
    "Esperance, WA": (-33.8667, 121.9000),
    "Seabird, WA": (-31.2833, 115.6333),
    "Northampton, WA": (-28.3500, 114.6333),
    "Denmark, WA": (-34.9500, 117.3500),
    "Lancelin, WA": (-31.0167, 115.3333),
    "Roses Beach, WA": (-33.5500, 115.1000),
    "Quindalup, WA": (-33.6500, 115.1000),
}

# State centroids as fallback
STATE_CENTROIDS = {
    "VIC": (-37.0, 144.0),
    "TAS": (-42.0, 147.0),
    "NSW": (-32.0, 147.0),
    "QLD": (-22.0, 145.0),
    "SA": (-30.0, 135.0),
    "WA": (-25.0, 122.0),
    "NT": (-20.0, 133.0),
    "ACT": (-35.3, 149.1),
}


def get_coordinates(locality: str, state: str) -> tuple[float, float]:
    """Get coordinates for a locality, with fallback to state centroid."""
    key = f"{locality}, {state}"
    if key in AUS_LOCALITIES:
        return AUS_LOCALITIES[key]

    # Try with variations
    for stored_key, coords in AUS_LOCALITIES.items():
        if locality.lower() in stored_key.lower():
            return coords

    # Fallback to state centroid
    if state in STATE_CENTROIDS:
        print(f"  Using state centroid for: {key}")
        return STATE_CENTROIDS[state]

    return (-25.0, 134.0)  # Australia center


def main():
    print("=" * 60)
    print("ADD AUSTRALIAN DETECTIONS")
    print("=" * 60)

    # Load scraped data
    scraped_file = DATA_DIR / "sources" / "aus_scraped_events.json"
    if not scraped_file.exists():
        print(f"Error: {scraped_file} not found. Run scraper first.")
        return

    with open(scraped_file) as f:
        scraped = json.load(f)

    events = scraped.get("events_by_species", [])
    print(f"\nLoaded {len(events)} events from scraper")

    if not events:
        print("No events to add")
        return

    # Filter out malformed entries (where locality contains species names)
    species_keywords = ["Tern", "Gull", "Penguin", "Petrel", "Seal", "Gannet", "Booby", "Shearwater"]
    valid_events = []
    skipped = 0
    for e in events:
        loc = e.get("locality", "")
        if any(kw in loc for kw in species_keywords):
            skipped += 1
            continue
        valid_events.append(e)

    print(f"Valid events: {len(valid_events)}, skipped {skipped} malformed entries")
    events = valid_events

    # Load existing detections
    parquet_file = DATA_DIR / "detections_merged.parquet"
    if parquet_file.exists():
        existing_df = pl.read_parquet(parquet_file)
        max_id = existing_df["record_id"].max()
        if max_id is None:
            max_id = 0
        print(f"Existing detections: {len(existing_df)}, max_id: {max_id}")
    else:
        existing_df = None
        max_id = 0

    # Create detection records
    new_records = []
    for i, e in enumerate(events):
        # Parse date
        date_str = e.get("date", "")
        try:
            # Format: DD/MM/YYYY
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            date_iso = date_obj.strftime("%Y-%m-%d")
        except:
            date_iso = date_str

        # Get coordinates
        lat, lon = get_coordinates(e.get("locality", ""), e.get("state", ""))

        record = {
            "record_id": max_id + i + 1,
            "scientific_name": e.get("scientific_name", ""),
            "species_raw": e.get("common_name", ""),
            "date_detected": date_iso,
            "country": "AUS",
            "state": e.get("state", ""),
            "county": e.get("locality", ""),
            "latitude": lat,
            "longitude": lon,
            "source": "DAFF",
        }
        new_records.append(record)
        print(f"  {date_iso} | {e.get('state')} | {e.get('locality')} | {e.get('common_name')}")

    # Create DataFrame
    new_df = pl.DataFrame(new_records)

    # Merge with existing
    if existing_df is not None:
        # Ensure schema compatibility - match types
        for col in existing_df.columns:
            if col not in new_df.columns:
                new_df = new_df.with_columns(pl.lit(None).alias(col))
            elif col in new_df.columns:
                # Cast to match existing dtype
                new_df = new_df.with_columns(
                    pl.col(col).cast(existing_df[col].dtype)
                )

        # Select same columns as existing
        new_df = new_df.select(existing_df.columns)
        merged_df = pl.concat([existing_df, new_df])
    else:
        merged_df = new_df

    # Save parquet
    merged_df.write_parquet(parquet_file)
    print(f"\nSaved {len(merged_df)} detections to {parquet_file}")

    # Copy to web
    web_parquet = WEB_DATA_DIR / "detections.parquet"
    merged_df.write_parquet(web_parquet)

    # Update GeoJSON
    geojson_file = WEB_DATA_DIR / "geojson" / "detections.geojson"
    if geojson_file.exists():
        with open(geojson_file) as f:
            geojson = json.load(f)
    else:
        geojson = {"type": "FeatureCollection", "features": []}

    # Add new features
    for rec in new_records:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [rec["longitude"], rec["latitude"]]
            },
            "properties": {
                "species": rec["scientific_name"],
                "common_name": rec["species_raw"],
                "date": rec["date_detected"],
                "country": rec["country"],
                "state": rec["state"],
                "locality": rec["county"],
                "source": rec["source"],
            }
        }
        geojson["features"].append(feature)

    with open(geojson_file, "w") as f:
        json.dump(geojson, f)
    print(f"Updated {geojson_file} ({len(geojson['features'])} features)")

    # Also save to dist if exists
    dist_geojson = ROOST_DIR / "web" / "dist" / "data" / "geojson" / "detections.geojson"
    if dist_geojson.parent.exists():
        with open(dist_geojson, "w") as f:
            json.dump(geojson, f)
        print(f"Updated {dist_geojson}")

    print(f"\n{'=' * 60}")
    print(f"Done! Added {len(new_records)} Australian detections")


if __name__ == "__main__":
    main()
