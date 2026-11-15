#!/usr/bin/env python3
"""
Build the WOAH WAHIS supplement from harvested event details.

Reads data/raw/external/wahis/details_compact.jsonl (one compact event per
line, built by scripts/fetch_wahis_events.py) and writes
data/manual/wahis_detections.json — one record per (event × species total).

Species mapping: taxonomy common-name match (normalized) + alias table;
unmapped species are kept with species_raw only (the harmonizer may still
map them; unmapped ones don't block the rest).

Usage:
    pixi run python scripts/fetch_wahis_events.py      # harvest first
    pixi run python scripts/add_wahis_detections.py
"""

import json
import re
import unicodedata
from pathlib import Path

import polars as pl
import sys

ROOST_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOST_DIR))
from scripts.species_aliases import BIRD_ALIASES, MAMMAL_ALIASES, EXTRA_SKIP_PATTERNS  # noqa: E402
DATA_DIR = ROOST_DIR / "data"
DETAILS_FILE = DATA_DIR / "raw" / "external" / "wahis" / "details_compact.jsonl"
TAXONOMY = DATA_DIR / "aves_taxonomy.tsv"
OUT_PATH = DATA_DIR / "manual" / "wahis_detections.json"

SOURCE_TAG = "WAHIS"

SKIP_SPECIES_PATTERNS = [
    r"^birds?$", r"unidentified", r"unknown", r"\(mixed\)", r"^aves$",
    r"^poultry$", r"^domestic birds", r"^wild birds", r"^other bird",
    r"^wildlife", r"^bovine",
] + EXTRA_SKIP_PATTERNS

# Common-name variants seen in WAHIS that miss the taxonomy common-name match
SPECIES_ALIASES = {
    "common crane": "Grus grus",
    "glossy ibis": "Plegadis falcinellus",
    "grey plover": "Pluvialis squatarola",
    "black-bellied plover": "Pluvialis squatarola",
    "whimbrel": "Numenius phaeopus",
    "black scoter": "Melanitta americana",
    "western cattle egret": "Bubulcus ibis",
    "cattle egret": "Bubulcus ibis",
    "brazilian teal": "Amazonetta brasiliensis",
    "grey goshawk": "Accipiter novaehollandiae",
    "western kingbird": "Tyrannus verticalis",
    "lincoln's sparrow": "Melospiza lincolnii",
    "eurasian buzzard (common buzzard)": "Buteo buteo",
    "common buzzard": "Buteo buteo",
    "western screech owl": "Megascops kennicottii",
    "horned screamer": "Anhima cornuta",
    "comb duck": "Sarkidiornis sylvicola",
    "white-faced whistling duck": "Dendrocygna viduata",
    "black-billed magpie": "Pica hudsonia",
    "dark-eyed junco": "Junco hyemalis",
    "turkey vulture": "Cathartes aura",
    "black vulture": "Coragyps atratus",
    "yellow-headed caracara": "Milvago chimachima",
    "southern lapwing": "Vanellus chilensis",
    "wattled jacana": "Jacana jacana",
    "snowy-crowned tern": "Sterna trudeaui",
    "bare-faced ibis": "Phimosus infuscatus",
    # WAHIS harvest wave 2
    "greylag goose": "Anser anser",
    "whooper swan": "Cygnus cygnus",
    "greater white-fronted goose": "Anser albifrons",
    "bean goose": "Anser fabalis",
    "common pheasant": "Phasianus colchicus",
    "common coot": "Fulica atra",
    "rock pigeon": "Columba livia",
    "rock dove": "Columba livia",
    "common magpie": "Pica pica",
    "peregrine falcon": "Falco peregrinus",
    "barn owl": "Tyto alba",
}


def normalize(name: str) -> str:
    """lowercase, strip accents, hyphens→spaces, collapse whitespace."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().replace("’", "'").replace("-", " ")
    # drop parenthetical aliases: "Barn Owl (Common Barn-Owl)" → "barn owl"
    name = re.sub(r"\s*\([^)]*\)", "", name)
    return re.sub(r"\s+", " ", name).strip()


def build_lookup() -> dict:
    t = pl.read_csv(TAXONOMY, separator="\t")
    lookup = {}
    for sci, com in zip(t["scientific_name"].to_list(), t["common_name"].to_list()):
        lookup[normalize(sci)] = sci
        if com:
            lookup.setdefault(normalize(com), sci)
    # shared alias tables (scripts/species_aliases.py) win over partial matches
    for alias, sci in {**BIRD_ALIASES, **MAMMAL_ALIASES, **SPECIES_ALIASES}.items():
        lookup[normalize(alias)] = sci
    return lookup


def is_generic(name: str) -> bool:
    if re.search(r"unidentified|\(mixed\)", name, re.I):
        return True
    n = normalize(name)
    return any(re.search(p, n) for p in SKIP_SPECIES_PATTERNS)


def strain_for(detail: dict) -> str:
    sub = detail.get("subType")
    if sub:
        return str(sub)
    disease = (detail.get("disease") or "").lower()
    if "bovine" in disease:
        return "H5N1"  # bovine clade events are H5N1 (2025-)
    return "HPAI"


def main():
    if not DETAILS_FILE.exists():
        raise SystemExit(f"No details file: {DETAILS_FILE}\nRun: pixi run python scripts/fetch_wahis_events.py")

    lookup = build_lookup()
    # dedupe by eventId (append-mode store), keeping the last occurrence
    by_id = {}
    for l in DETAILS_FILE.read_text().splitlines():
        if l.strip():
            try:
                d = json.loads(l)
                by_id[d["eventId"]] = d
            except json.JSONDecodeError:
                continue
    details = list(by_id.values())

    records = []
    unmapped = {}
    for d in details:
        iso = d.get("country_iso")
        date = d.get("startedOn") or d.get("confirmOn")
        if not iso or not date:
            continue
        for tot in d.get("totals", []):
            name = (tot.get("speciesName") or "").strip()
            if not name or is_generic(name):
                continue
            sci = lookup.get(normalize(name))
            if not sci:
                unmapped[name] = unmapped.get(name, 0) + 1
            cases = tot.get("cases")
            deaths = tot.get("deaths")
            records.append({
                "species_raw": name,
                "scientific_name_parsed": sci,
                "date_detected": date,
                "country": iso,
                "state": None,
                "county": None,
                "strain": strain_for(d),
                "sampling_method_raw": (
                    f"WOAH WAHIS event {d['eventId']} "
                    f"({d.get('reason') or 'event'}; {d.get('outbreaks_count') or 0} outbreaks; "
                    f"wild={tot.get('isWild')}; cases={cases}, deaths={deaths})"
                ),
                "sampling_type": "confirmed event",
                "source_file": f"wahis_event_{d['eventId']}.json",
                "detection_count": cases or deaths or 1,
                "latitude": d.get("latitude"),
                "longitude": d.get("longitude"),
            })

    mapped = sum(1 for r in records if r["scientific_name_parsed"])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "source": SOURCE_TAG,
        "description": "WOAH WAHIS immediate notifications & follow-ups — avian influenza events",
        "records": records,
    }, indent=1))

    countries = len({r["country"] for r in records})
    print(f"Wrote {len(records)} {SOURCE_TAG} records "
          f"({len(details)} events, {countries} countries) → {OUT_PATH}")
    print(f"  species mapped: {mapped}/{len(records)} ({100*mapped//max(1,len(records))}%)")
    if unmapped:
        top = sorted(unmapped.items(), key=lambda x: -x[1])[:12]
        print(f"  top unmapped species: {[n for n, _ in top]}")
    print("\nNext: pixi run ingest-detections && pixi run deduplicate")


if __name__ == "__main__":
    main()
