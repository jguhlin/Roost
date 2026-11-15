#!/usr/bin/env python3
"""Shared region normalization: free-text region/country names -> the
spread-era 8-bucket scheme. Used by the synthesis route×establishment
join and the vaccine-campaigns builder."""
from __future__ import annotations

NAME_LOOKUP = {
    "china": "east_southeast_asia", "vietnam": "east_southeast_asia",
    "viet nam": "east_southeast_asia", "indonesia": "east_southeast_asia",
    "korea": "east_southeast_asia", "japan": "east_southeast_asia",
    "hong kong": "east_southeast_asia", "taiwan": "east_southeast_asia",
    "myanmar": "east_southeast_asia", "thailand": "east_southeast_asia",
    "cambodia": "east_southeast_asia", "laos": "east_southeast_asia",
    "philippines": "east_southeast_asia", "malaysia": "east_southeast_asia",
    "bangladesh": "west_central_asia_mena", "india": "west_central_asia_mena",
    "pakistan": "west_central_asia_mena", "israel": "west_central_asia_mena",
    "egypt": "africa", "nigeria": "africa", "africa": "africa",
    "morocco": "africa", "tunisia": "africa", "senegal": "africa",
    "ghana": "africa", "sudan": "africa", "kenya": "africa",
    "france": "europe", "netherlands": "europe", "europe": "europe",
    "european": "europe", "italy": "europe", "germany": "europe",
    "spain": "europe", "uk": "europe", "united kingdom": "europe",
    "britain": "europe", "russia": "europe", "ukraine": "europe",
    "poland": "europe", "romania": "europe", "bulgaria": "europe",
    "germany": "europe", "sweden": "europe", "norway": "europe",
    "finland": "europe", "denmark": "europe", "turkey": "west_central_asia_mena",
    "iran": "west_central_asia_mena", "iraq": "west_central_asia_mena",
    "kazakhstan": "west_central_asia_mena", "georgia": "west_central_asia_mena",
    "azerbaijan": "west_central_asia_mena", "central asia": "west_central_asia_mena",
    "middle east": "west_central_asia_mena", "mena": "west_central_asia_mena",
    "usa": "north_america", "united states": "north_america",
    "us ": "north_america", "north america": "north_america",
    "canada": "north_america", "mexico": "north_america",
    "alaska": "north_america", "greenland": "north_america",
    "brazil": "south_america", "peru": "south_america",
    "south america": "south_america", "argentina": "south_america",
    "chile": "south_america", "ecuador": "south_america",
    "colombia": "south_america", "bolivia": "south_america",
    "uruguay": "south_america", "venezuela": "south_america",
    "new zealand": "oceania", "australia": "oceania", "oceania": "oceania",
    "pacific": "oceania", "antarctica": "antarctica_subantarctic",
    "subantarctic": "antarctica_subantarctic",
    "eurasia": "europe", "asia": "east_southeast_asia",
    "europe/africa": "europe",
}


def region_bucket(region_text: str | None) -> str | None:
    """Free-text region -> era bucket, or None when unmappable."""
    t = (region_text or "").lower()
    if not t:
        return None
    for name, bucket in NAME_LOOKUP.items():
        if name in t:
            return bucket
    return None
