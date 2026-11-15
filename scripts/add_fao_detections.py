#!/usr/bin/env python3
"""
Build FAO HPAI supplements from FAO situation-update pages.

Covers BOTH pages (same table schema):
  - Global AIV with zoonotic potential  (fao_global_aiv source)
  - Sub-Saharan Africa HPAI             (fao_ssa_hpai source)

Parses each fetched HTML snapshot into per-(country × species) records and
writes data/manual/fao_detections.json — loaded as a first-class source by
ingest_detections.py, so records survive pipeline rebuilds.

Usage:
    pixi run fetch fao_global_aiv fao_ssa_hpai
    pixi run python scripts/add_fao_detections.py
"""

import html as html_mod
import json
import re
import sys
from pathlib import Path

ROOST_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOST_DIR))
from scripts.species_aliases import BIRD_ALIASES, MAMMAL_ALIASES  # noqa: E402

DATA_DIR = ROOST_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "external"
OUT_PATH = DATA_DIR / "manual" / "fao_detections.json"

SOURCE_TAG = "FAO"

PAGES = [
    ("fao-ssa/sub_saharan_africa_hpai.html", "FAO Sub-Saharan Africa HPAI",
     "sub_saharan_africa_hpai.html"),
    ("fao-ssa/global_aiv_with_zoonotic_potential.html",
     "FAO Global AIV with Zoonotic Potential", "global_aiv_with_zoonotic_potential.html"),
]

COUNTRY_ISO = {
    "united states of america": "USA", "australia": "AUS", "austria": "AUT",
    "belgium": "BEL", "canada": "CAN", "chile": "CHL", "colombia": "COL",
    "denmark": "DNK", "germany": "DEU", "indonesia": "IDN", "namibia": "NAM",
    "nepal": "NPL", "netherlands": "NLD", "netherlands (kingdom of the)": "NLD",
    "new zealand": "NZL", "nigeria": "NGA", "norway": "NOR", "peru": "PER",
    "the philippines": "PHL", "philippines": "PHL", "poland": "POL",
    "portugal": "PRT", "south africa": "ZAF", "togo": "TGO", "viet nam": "VNM",
    "vietnam": "VNM", "mexico": "MEX", "honduras": "HND",
    "cote d`ivoire": "CIV", "cote d'ivoire": "CIV", "senegal": "SEN",
}

SPECIES_MAP = {
    # Sub-Saharan Africa page
    "african (jackass) penguin": "Spheniscus demersus",
    "black sparrowhawk": "Accipiter melanoleucus",
    "brown skua": "Stercorarius lonnbergi",
    "cape cormorant": "Phalacrocorax capensis",
    "common tern": "Sterna hirundo",
    "crowned cormorant": "Microcarbo coronatus",
    "egyptian goose": "Alopochen aegyptiaca",
    "grey-headed gull": "Chroicocephalus cirrocephalus",
    "grey heron": "Ardea cinerea",
    "hartlaub's gull": "Chroicocephalus hartlaubii",
    "kelp gull": "Larus dominicanus",
    "litle stint": "Calidris minuta",
    "little stint": "Calidris minuta",
    "reed cormorant": "Microcarbo africanus",
    "sacred ibis": "Threskiornis aethiopicus",
    "swift tern": "Thalasseus bergii",
    "white-backed vulture": "Gyps africanus",
    "white-breasted cormorant": "Phalacrocorax carbo",
    # Global page
    "american crow": "Corvus brachyrhynchos",
    "common raven": "Corvus corax",
    "herring gull": "Larus argentatus",
    "southern giant petrel": "Macronectes giganteus",
    "common barn-owl": "Tyto alba",
    "canada goose": "Branta canadensis",
    "short-eared owl": "Asio flammeus",
    "barnacle goose": "Branta leucopsis",
    "eurasian oystercatcher": "Haematopus ostralegus",
    "brent goose": "Branta bernicla",
    "black-faced ibis": "Theristicus melanopis",
    "indian pond-heron": "Ardeola grayii",
    "black-headed gull": "Chroicocephalus ridibundus",
    "eurasian spoonbill": "Platalea leucorodia",
    "common eider": "Somateria mollissima",
    "white stork": "Ciconia ciconia",
    "andean teal": "Anas andium",
    "great black-backed gull": "Larus marinus",
    "plain chachalaca": "Ortalis vetula",
    "black vulture": "Coragyps atratus",
    "muscovy duck": "Cairina moschata",
    "swamp harrier hawk": "Circus approximans",
    "swamp harrier": "Circus approximans",
    # global page, wave 2
    "common buzzard": "Buteo buteo",
    "mallard": "Anas platyrhynchos",
    "greylag goose": "Anser anser",
    "mute swan": "Cygnus olor",
    "lesser black-backed gull": "Larus fuscus",
    "common shelduck": "Tadorna tadorna",
    "great white pelican": "Pelecanus onocrotalus",
    "mandarin duck": "Aix galericulata",
    "kalij pheasant": "Lophura leucomelanos",
    "northern bald ibis": "Geronticus eremita",
    "northern gannet": "Morus bassanus",
    "ring-billed gull": "Larus delawarensis",
    "purple swamphen": "Porphyrio porphyrio",
    "peacock": "Pavo cristatus",
    # domestic
    "chicken": "Gallus gallus",
    "turkey": "Meleagris gallopavo",
}

SKIP_SPECIES = {
    "poultry", "goose", "duck", "domestic non-poultry birds", "non-poultry birds",
    "laridae", "ardeidae", "anatidae", "ciconiidae", "unknown", "birds",
    "fighting cock", "backyard poultry", "cattle",
}


def clean_country(cell: str):
    """('Namibia (Karas)' → ('Namibia', 'Karas'); 'United States of America 7' → (…, None))."""
    cell = re.sub(r"\s+\d+$", "", cell.strip())
    m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", cell)
    if m and not re.match(r"^[A-Z][a-z]+ [a-z-]+$", m.group(2)):  # parens = admin regions, not binomial
        return m.group(1).strip(), m.group(2).strip()
    return cell.strip(), None


def parse_date(cell: str):
    """Mixed D/M and M/D with typo tolerance ('07/072026')."""
    cell = cell.strip()
    # repair missing space: 07/072026 → 07/07/2026
    m = re.match(r"^(\d{1,2})/(\d{2})(\d{4})$", cell)
    if m:
        cell = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", cell)
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if a > 12 and b <= 12:   # must be M/D
        a, b = b, a
    # FAO default is D/M
    try:
        from datetime import date
        return date(y, b, a).isoformat()
    except ValueError:
        try:
            return date(y, a, b).isoformat()
        except ValueError:
            return None


def parse_total_events(cell: str) -> int:
    """'1703 (incl. W1661 M42)' → 1703; '17 (in W)' → 17."""
    m = re.match(r"^(\d+)", cell.strip().replace(",", ""))
    return int(m.group(1)) if m else 1


def parse_species(cell: str):
    out = []
    for chunk in re.split(r"[;,]", cell):
        sp = chunk.strip().lower().rstrip(".,;").lstrip("-")
        sp = re.sub(r"\s*note:.*$", "", sp).strip()
        if sp and sp not in SKIP_SPECIES and len(sp) > 2:
            out.append(sp)
    return out


def parse_table(html: str):
    tbl = re.search(r"<table.*?</table>", html, re.S)
    if not tbl:
        return []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbl.group(0), re.S)

    out = []
    for row in rows[1:]:
        cells = []
        for raw in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S):
            text = html_mod.unescape(re.sub(r"<[^>]+>", " ", raw))
            cells.append(re.sub(r"\s+", " ", text).strip())
        cells = [c for c in cells if c]
        if len(cells) < 4:
            continue

        # Optional leading virus cell (rowspan): H5 / H5N1 / H5N5 / H7N3 / HxNx
        strain = None
        if re.match(r"^[hH]\d?N?\d*[xX]?$", cells[0]):
            strain = cells[0].upper()
            cells = cells[1:]
        if len(cells) < 4:
            continue
        country_cell, date_cell, _new_cell, total_cell = cells[0], cells[1], cells[2], cells[3]
        species_cell = cells[4] if len(cells) > 4 else ""

        date_iso = parse_date(date_cell)
        if not date_iso:
            continue
        country, regions = clean_country(country_cell)
        out.append((country, strain or "H5N1",
                    date_iso, parse_total_events(total_cell),
                    parse_species(species_cell), regions))
    return out


def main():
    # shared alias tables supplement the page-specific map
    combined_species_map = {**BIRD_ALIASES, **MAMMAL_ALIASES, **SPECIES_MAP}
    all_records = []
    for rel_path, label, source_file in PAGES:
        html_path = RAW_DIR / rel_path
        if not html_path.exists():
            print(f"  (skipping {label}: {html_path} not found — run fetch first)")
            continue
        rows = parse_table(html_path.read_text(encoding="utf-8", errors="ignore"))
        page_records = 0
        skipped = set()
        for country, strain, date_iso, total_events, species, regions in rows:
            iso = COUNTRY_ISO.get(country.lower())
            if not iso:
                skipped.add(country)
                continue
            for sp in species:
                sci = combined_species_map.get(sp)
                if not sci:
                    skipped.add(sp)
                    continue
                all_records.append({
                    "species_raw": sp,
                    "scientific_name_parsed": sci,
                    "date_detected": date_iso,
                    "country": iso,
                    "state": regions or None,
                    "county": None,
                    "strain": strain,
                    "sampling_method_raw": f"{label} (country total: {total_events} events)",
                    "sampling_type": "confirmed event",
                    "source_file": source_file,
                    "detection_count": 1,
                    "latitude": None,
                    "longitude": None,
                })
                page_records += 1
        print(f"{label}: {len(rows)} country rows → {page_records} records")
        if skipped:
            print(f"  unmapped: {sorted(skipped)[:12]}")

    if not all_records:
        raise SystemExit("No records parsed from any FAO page")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "source": SOURCE_TAG,
        "description": "FAO HPAI situation updates (Global AIV + Sub-Saharan Africa)",
        "records": all_records,
    }, indent=1))

    countries = sorted({r["country"] for r in all_records})
    print(f"\nWrote {len(all_records)} {SOURCE_TAG} records "
          f"({len(countries)} countries) → {OUT_PATH}")
    print(f"countries: {', '.join(countries)}")
    print("\nNext: pixi run ingest-detections && pixi run deduplicate")


if __name__ == "__main__":
    main()
