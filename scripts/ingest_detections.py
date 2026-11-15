#!/usr/bin/env python3
"""
Ingest avian influenza detection data from multiple sources.

Sources:
- APHIS US wild birds (2023-present)
- OAFD US wild birds (2022)
- Italy wild birds (future)
- Additional sources as available

Each record includes full provenance:
- source: Which database/file
- source_url: Where to get updates
- date_range: Coverage period
- sampling_method: How bird was found (key for phenotype)
"""

import polars as pl
import re
from pathlib import Path
from datetime import datetime
import json

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
EXTERNAL_DIR = RAW_DIR / "external"


# Source metadata for provenance tracking
SOURCES = {
    "aphis_us": {
        "name": "APHIS US Wild Bird HPAI Detections",
        "url": "https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv",
        "description": "USDA APHIS wild bird surveillance data",
        "country": "USA",
        "update_frequency": "Weekly during outbreaks",
    },
    "oafd_us_2022": {
        "name": "Open Avian Flu Dataset - US Wild Birds 2022",
        "url": "https://zenodo.org/records/8246456",
        "description": "Historical US wild bird data from early outbreak",
        "country": "USA",
        "update_frequency": "Static (historical)",
    },
    "italy_wild": {
        "name": "Italy HPAI Wild Bird Detections",
        "url": "https://zenodo.org/records/8246456",
        "description": "Italian wild bird surveillance via OAFD",
        "country": "Italy",
        "update_frequency": "Static (historical)",
    },
    "gisaid_avilist": {
        "name": "GISAID Global Wild Bird AIV Hosts",
        "url": "https://zenodo.org/records/15970977",
        "doi": "10.5281/zenodo.15970977",
        "description": "Taxonomically harmonized dataset of 394 wild bird AIV hosts from GISAID (1973-2023)",
        "country": "Global",
        "update_frequency": "Static (2023 snapshot)",
        "has_phenotype": False,  # Detection only, no mortality data
    },
    "usgs_alaska": {
        "name": "USGS Izembek NWR Alaska IAV Surveillance",
        "url": "https://doi.org/10.5066/F7JD4W2W",
        "description": "Waterfowl IAV sampling at Izembek NWR, Alaska (2011-2024)",
        "country": "USA",
        "update_frequency": "Annual updates",
        "has_phenotype": False,  # Detection only (lab positives)
    },
    "empresi_linked": {
        "name": "EMPRES-i Linked Epidemiological and Genomic Data",
        "url": "https://doi.org/10.57745/JNA7N9",
        "doi": "10.57745/JNA7N9",
        "description": "FAO EMPRES-i AI events linked with GISAID sequences (2012-2021)",
        "country": "Global",
        "update_frequency": "Static (2012-2021)",
        "has_phenotype": False,
    },
    "sdm_hpai": {
        "name": "SDM HPAI Wild Bird Detections (FAO/WOAH compiled)",
        "url": "https://github.com/sarahhayes/avian_flu_sdm",
        "description": "HPAI positive wild bird detections compiled from FAO EMPRES-i and WOAH WAHIS (2005-2024)",
        "country": "Global (47 countries)",
        "update_frequency": "Research dataset",
        "has_phenotype": False,
    },
    "canada_cwhc": {
        "name": "Canada CWHC HPAI Wildlife Dashboard",
        "url": "https://cfia-ncr.maps.arcgis.com/apps/dashboards/89c779e98cdf492c899df23e1c38fdbc",
        "description": "Canadian Wildlife Health Cooperative HPAI detections in wild birds",
        "country": "Canada",
        "update_frequency": "Weekly updates",
        "has_phenotype": False,
    },
    "vs_surveillance": {
        "name": "VS Wild Bird Surveillance H5 Positives",
        "url": "https://services7.arcgis.com/2C1NQ7u6M6SXoa8p/arcgis/rest/services/VS_Avian_Influenza_Wild_Bird_Surveillance_Dashboard_data_view_feature_layer_/FeatureServer/0",
        "description": "USDA Veterinary Services wild bird AIV surveillance - H5 positive samples with geographic data",
        "country": "USA",
        "update_frequency": "Ongoing surveillance",
        "has_phenotype": False,
    },
    "iceland_usgs": {
        "name": "USGS Iceland AIV Surveillance (2010-2018)",
        "url": "https://doi.org/10.5066/P9ZJKQHU",
        "description": "Wild bird AIV surveillance in Iceland (Dusek et al.), 381 positives across 20+ species",
        "country": "Iceland",
        "update_frequency": "Static (2010-2018)",
        "has_phenotype": False,
    },
    "ireland_occurrence": {
        "name": "Ireland Wild Bird Species Occurrence (with H5 targeting)",
        "url": "https://data.gov.ie/dataset/h5n1-wild-bird-species",
        "description": "Wild bird occurrence data for Ireland with H5 HPAI target species indicators",
        "country": "Ireland",
        "update_frequency": "Research dataset",
        "has_phenotype": False,
        "is_occurrence_data": True,  # Not detection data
    },
    "github_usa": {
        "name": "GitHub fbranda USA HPAI Wild Birds",
        "url": "https://github.com/fbranda/avian-flu",
        "description": "Comprehensive USA HPAI wild bird detections from GitHub repository",
        "country": "USA",
        "update_frequency": "Community maintained",
        "has_phenotype": False,
    },
    "github_italy": {
        "name": "GitHub fbranda Italy HPAI Wild Birds",
        "url": "https://github.com/fbranda/avian-flu",
        "description": "Italy HPAI wild bird detections from GitHub repository",
        "country": "Italy",
        "update_frequency": "Community maintained",
        "has_phenotype": False,
    },
    "uk_defra": {
        "name": "UK DEFRA/APHA Wild Bird AI Findings",
        "url": "https://www.gov.uk/government/publications/avian-influenza-in-wild-birds",
        "description": "UK APHA wild bird avian influenza surveillance data (2024-2026)",
        "country": "UK",
        "update_frequency": "Weekly updates",
        "has_phenotype": False,
    },
    "aphis_mammals": {
        "name": "APHIS US HPAI Detections in Mammals",
        "url": "https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza/hpai-detections/mammals",
        "description": "USDA APHIS confirmed HPAI detections in wild and captive mammals (2022-present), one record per animal",
        "country": "USA",
        "update_frequency": "Weekly updates",
        "has_phenotype": True,  # clinical cases (found sick/dead)
    },
    "aphis_flocks": {
        "name": "APHIS US Commercial & Backyard Flock Detections",
        "url": "https://www.aphis.usda.gov/livestock-poultry-disease/avian/avian-influenza/hpai-detections/commercial-backyard-flocks",
        "description": "Confirmed HPAI detections on US poultry premises (2022-present) with birds affected; exported from the APHIS Tableau dashboard (ExportToCsv sheet)",
        "country": "USA",
        "update_frequency": "Weekly updates",
        "has_phenotype": True,  # premises-level mortality/culling counts
    },
}


def load_aphis_us() -> pl.DataFrame:
    """Load APHIS US wild bird data with provenance."""
    file_path = RAW_DIR / "aphis_wild_birds.csv"
    if not file_path.exists():
        print(f"  APHIS file not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Normalize columns
    df = df.with_columns([
        pl.col("Bird Species").alias("species_raw"),
        pl.col("State").alias("state"),
        pl.col("County").alias("county"),
        pl.col("Date Detected").alias("date_detected"),
        pl.col("HPAI Strain").alias("strain"),
        pl.col("Sampling Method").str.to_lowercase().alias("sampling_method_raw"),
    ])

    # Classify sampling method
    df = df.with_columns([
        pl.when(pl.col("sampling_method_raw").str.contains("morbidity|mortality"))
          .then(pl.lit("mortality"))
          .when(pl.col("sampling_method_raw").str.contains("live"))
          .then(pl.lit("live"))
          .when(pl.col("sampling_method_raw").str.contains("harvest"))
          .then(pl.lit("harvest"))
          .otherwise(pl.lit("other"))
          .alias("sampling_type")
    ])

    # Add provenance
    df = df.with_columns([
        pl.lit("aphis_us").alias("source"),
        pl.lit("USA").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
    ])

    return df.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file"
    ])


def load_oafd_us_2022() -> pl.DataFrame:
    """Load OAFD US 2022 wild bird data with provenance."""
    file_path = EXTERNAL_DIR / "avian-flu-main" / "Americas" / "USA" / "hpai-wild-birds.csv"
    if not file_path.exists():
        print(f"  OAFD US file not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Normalize columns
    df = df.with_columns([
        pl.col("Type of Wild Bird").alias("species_raw"),
        pl.col("State").alias("state"),
        pl.col("County").alias("county"),
        pl.col("Date Detected").alias("date_detected"),
        pl.col("HPAI Strain").alias("strain"),
        pl.col("Sampling Source").str.to_lowercase().alias("sampling_method_raw"),
    ])

    # Classify sampling method
    df = df.with_columns([
        pl.when(pl.col("sampling_method_raw").str.contains("mortality"))
          .then(pl.lit("mortality"))
          .when(pl.col("sampling_method_raw").str.contains("live"))
          .then(pl.lit("live"))
          .when(pl.col("sampling_method_raw").str.contains("harvest"))
          .then(pl.lit("harvest"))
          .otherwise(pl.lit("other"))
          .alias("sampling_type")
    ])

    # Add provenance
    df = df.with_columns([
        pl.lit("oafd_us_2022").alias("source"),
        pl.lit("USA").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
    ])

    return df.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file"
    ])


def load_italy_wild() -> pl.DataFrame:
    """Load Italy wild bird data with provenance."""
    italy_dir = EXTERNAL_DIR / "avian-flu-main" / "Europe" / "Italy" / "HPAI"

    dfs = []
    for season_dir in italy_dir.iterdir():
        if season_dir.is_dir():
            wild_file = season_dir / f"hpai-wild-birds-{season_dir.name}.csv"
            if wild_file.exists():
                df = pl.read_csv(wild_file)
                df = df.with_columns([
                    pl.col("Species").alias("species_raw"),
                    pl.lit("").alias("state"),  # Italy uses Region
                    pl.col("Province").alias("county"),
                    pl.col("Confirmation date").alias("date_detected"),
                    pl.col("HPAI strain").alias("strain"),
                    pl.lit("unknown").alias("sampling_method_raw"),
                    pl.lit("unknown").alias("sampling_type"),  # Italy data doesn't have this
                    pl.lit("italy_wild").alias("source"),
                    pl.lit("Italy").alias("country"),
                    pl.lit(str(wild_file)).alias("source_file"),
                ])
                dfs.append(df.select([
                    "species_raw", "state", "county", "date_detected", "strain",
                    "sampling_method_raw", "sampling_type", "source", "country", "source_file"
                ]))

    if dfs:
        return pl.concat(dfs)
    return pl.DataFrame()


def load_gisaid_avilist() -> pl.DataFrame:
    """Load GISAID Avilist global wild bird hosts (detection only, no phenotype)."""
    file_path = EXTERNAL_DIR / "zenodo-avilist" / "species_list.csv"
    if not file_path.exists():
        print(f"  GISAID Avilist not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Parse scientific name from Order-Family-Genus-Species column
    df = df.with_columns([
        pl.col("Order-Family-Genus-Species").str.split("-").list.get(3).alias("scientific_name_parsed"),
        pl.col("English_name_AviList").alias("species_raw"),
        pl.lit("").alias("state"),
        pl.lit("").alias("county"),
        pl.lit("1973-2023").alias("date_detected"),  # Date range, not specific date
        pl.lit("various").alias("strain"),
        pl.lit("virus_isolation").alias("sampling_method_raw"),
        pl.lit("unknown").alias("sampling_type"),  # No mortality data
        pl.lit("gisaid_avilist").alias("source"),
        pl.lit("Global").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
        pl.col("Isolate_Count_Sum").alias("detection_count"),
    ])

    # Expand each species row by its isolate count for consistent aggregation
    # Actually, keep as single row per species with count - we'll handle differently
    return df.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed", "detection_count"
    ])


def load_usgs_alaska() -> pl.DataFrame:
    """Load USGS Izembek Alaska IAV surveillance data (positives only)."""
    samp_path = EXTERNAL_DIR / "usgs-izembek" / "sampling.csv"
    tax_path = EXTERNAL_DIR / "usgs-izembek" / "taxonomy.csv"

    if not samp_path.exists():
        print(f"  USGS Alaska sampling not found: {samp_path}")
        return pl.DataFrame()

    # Load with lossy encoding for any bad chars
    try:
        samples = pl.read_csv(samp_path, encoding="utf8-lossy", truncate_ragged_lines=True)
        taxonomy = pl.read_csv(tax_path, encoding="utf8-lossy")
    except Exception as e:
        print(f"  USGS Alaska: Error reading CSV - {e}")
        return pl.DataFrame()

    # Filter to HPAI positives only (or all IAV positives)
    positives = samples.filter(
        (pl.col("confirmed_HP_IAV_positive") == "Y") |
        (pl.col("Virus_isolation_positive") == "Y")
    )

    if len(positives) == 0:
        print("  USGS Alaska: No positive samples found")
        return pl.DataFrame()

    # Join with taxonomy to get species names
    positives = positives.join(
        taxonomy.select(["Species_Code", "Species", "Common_name"]),
        on="Species_Code",
        how="left"
    )

    # Normalize columns
    positives = positives.with_columns([
        pl.col("Common_name").alias("species_raw"),
        pl.lit("Alaska").alias("state"),
        pl.lit("Izembek NWR").alias("county"),
        pl.col("Sample_Collection_Date").alias("date_detected"),
        pl.col("AIV_HA_and_NA_subtypes").fill_null("unknown").alias("strain"),
        pl.lit("live_capture").alias("sampling_method_raw"),
        pl.lit("live").alias("sampling_type"),  # All live birds sampled
        pl.lit("usgs_alaska").alias("source"),
        pl.lit("USA").alias("country"),
        pl.lit(str(samp_path)).alias("source_file"),
        pl.col("Species").alias("scientific_name_parsed"),
    ])

    return positives.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed"
    ])


def _parse_empres_species(sp: str):
    """Parse an EMPRES-i Species cell into [(common, scientific), …].

    Formats seen in the wild:
      'Wild - Greylag Goose:Anser anser(Anatidae)'   colon form
      'Wild - Pacific loon (Gavia pacifica)'          trailing-paren form
      'Wild - Cormorant'                              common only
      'Wild - A:Sci(Fam) | Wild - B:Sci(Fam)'         multi-species event
    """
    out = []
    for part in sp.split("|"):
        part = part.strip()
        if part.lower().startswith("wild"):
            part = part.split("-", 1)[1].strip() if "-" in part else part
        if not part:
            continue
        common, sci = part, ""
        if ":" in part:
            head, tail = part.split(":", 1)
            common, sci = head.strip(), tail.split("(")[0].strip()
        else:
            m = re.search(r"\(([^)]*\s[^)]*)\)\s*$", part)  # 2+ words in parens
            if m:
                common = part[:m.start()].strip()
                sci = m.group(1).strip()
        if sci:
            words = sci.split()
            sci = " ".join([words[0].capitalize()] + [w.lower() for w in words[1:]])
        if common:
            out.append((common, sci))
    return out


def load_empresi_latest() -> pl.DataFrame:
    """Load EMPRES-i Latest Reported Events CSV (manual export, 15k row cap).

    Wild-bird events only (mirrors load_empresi_linked's scope). Species
    strings look like 'Wild - Greylag Goose:Anser anser(Anatidae)'.
    """
    d = EXTERNAL_DIR / "empresi-latest"
    if not d.exists():
        return pl.DataFrame()
    csvs = sorted(d.glob("Latest_Reported_Events_*.csv"))
    if not csvs:
        return pl.DataFrame()
    f = csvs[-1]
    try:
        raw = pl.read_csv(f)
    except Exception as e:
        print(f"    WARNING: empresi_latest read failed: {e}")
        return pl.DataFrame()

    records = []
    for row in raw.iter_rows(named=True):
        sp = (row.get("Species") or "").strip()
        if not sp.lower().startswith("wild"):
            continue  # domestic mammals/poultry out of scope for this source
        lat = row.get("latitude")
        lon = row.get("longitude")
        for common, sci in _parse_empres_species(sp):
            records.append({
                "species_raw": common,
                "scientific_name_parsed": sci or None,
                "state": "",
                "county": "",
                "date_detected": (row.get("observation date") or "").strip(),
                "strain": str(row.get("Serotype") or "").strip(),
                "sampling_method_raw": "surveillance",
                "sampling_type": "unknown",
                "source": "empresi_latest",
                "country": (row.get("Country") or "").strip(),
                "source_file": f.name,
                "record_ref": str(row.get("Event ID") or ""),
                "latitude": float(lat) if lat not in (None, "") else None,
                "longitude": float(lon) if lon not in (None, "") else None,
                "detection_count": 1,
            })
    if not records:
        return pl.DataFrame()
    return pl.DataFrame(records).with_columns([
        pl.col("latitude").cast(pl.Float64),
        pl.col("longitude").cast(pl.Float64),
        pl.col("detection_count").cast(pl.Int64),
    ])


def load_empresi_linked() -> pl.DataFrame:
    """Load EMPRES-i linked epidemiological data (wild birds only)."""
    import json as json_lib

    file_path = EXTERNAL_DIR / "empresi-linked" / "doc_events_empres-i_strategy=1-to-1.csv"
    if not file_path.exists():
        print(f"  EMPRES-i linked data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path, separator=";")

    # Parse host JSON to extract wild bird species
    domestic_ids = {9031, 9005, 8996}  # chicken, turkey, guinea fowl

    records = []
    for row in df.iter_rows(named=True):
        try:
            hosts = json_lib.loads(row['host'].replace("'", '"'))
            for h in hosts:
                # Skip non-birds and domestic poultry
                if h.get('id') in domestic_ids:
                    continue
                hier = h.get('hierarchy', [])
                if 'aves' not in [x.lower() for x in hier]:
                    continue
                # Get species-level name
                if len(hier) >= 2:
                    last = hier[-1]
                    if ' ' in last:
                        parts = last.split()
                        sci_name = parts[0].capitalize() + ' ' + ' '.join(p.lower() for p in parts[1:])
                        records.append({
                            'species_raw': h.get('common_name', ''),
                            'state': '',
                            'county': row.get('loc_name', ''),
                            'date_detected': row.get('published_at', ''),
                            'strain': str(row.get('disease', '')),
                            'sampling_method_raw': 'surveillance',
                            'sampling_type': 'unknown',
                            'source': 'empresi_linked',
                            'country': row.get('loc_country_code', 'Unknown'),
                            'source_file': str(file_path),
                            'scientific_name_parsed': sci_name,
                            'detection_count': 1,
                        })
        except:
            continue

    if not records:
        print("  EMPRES-i: No wild bird records found")
        return pl.DataFrame()

    return pl.DataFrame(records)


def load_sdm_hpai() -> pl.DataFrame:
    """
    Load SDM HPAI wild bird detections with WGS84 coordinates.

    This dataset contains HPAI positive detections from 47 countries (2005-2024).
    Species are in various formats that need parsing.
    Coordinates converted from LAEA Europe (EPSG:3035) to WGS84.
    """
    import re

    # Use WGS84-converted file if available
    file_path = EXTERNAL_DIR / "github-avianflu" / "hpai-pos-birds-sdm-wgs84.csv"
    if not file_path.exists():
        file_path = EXTERNAL_DIR / "github-avianflu" / "hpai-pos-birds-sdm.csv"
    if not file_path.exists():
        print(f"  SDM HPAI data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Parse scientific names from various formats
    def parse_species(s: str) -> tuple[str, str | None]:
        """
        Parse species string to extract raw name and scientific name.

        Formats handled:
        - "Mute Swan:cygnus Olor(Anatidae)" -> ("Mute Swan", "Cygnus olor")
        - "Accipiter gentilis" -> ("Accipiter gentilis", "Accipiter gentilis")
        - "Arctic Tern (Sterna Paradisea)" -> ("Arctic Tern", "Sterna paradisea")
        """
        s = str(s).strip()
        sci_name = None
        raw_name = s

        # Format: "Common Name:genus Species(Family)"
        if ':' in s:
            parts = s.split(':')
            raw_name = parts[0].strip()
            if len(parts) > 1:
                sci_part = parts[1].split('(')[0].strip()
                words = sci_part.split()
                if len(words) >= 2:
                    sci_name = f"{words[0].title()} {' '.join(w.lower() for w in words[1:])}"
        # Format: "Common Name (Genus Species)"
        elif '(' in s and ')' in s:
            match = re.search(r'\(([^)]+)\)', s)
            if match:
                inner = match.group(1).strip()
                words = inner.split()
                if len(words) >= 2 and words[0][0].isupper():
                    sci_name = f"{words[0].title()} {' '.join(w.lower() for w in words[1:])}"
                    raw_name = s.split('(')[0].strip()
        # Format: "Genus species" (already scientific)
        else:
            words = s.split()
            if len(words) >= 2:
                # Check if first word looks like a genus (capitalized, Latin-looking)
                if words[0][0].isupper() and words[0].isalpha() and len(words[0]) > 2:
                    # Skip family/order names ending in -idae, -iformes
                    if not any(words[0].lower().endswith(x) for x in ('idae', 'iformes', 'inae')):
                        sci_name = f"{words[0].title()} {words[1].lower()}"

        return (raw_name, sci_name)

    # Process each record
    records = []
    for row in df.iter_rows(named=True):
        raw_name, sci_name = parse_species(row['Species'])

        # Skip unidentified/incognita entries
        if any(x in raw_name.lower() for x in ['incognita', 'unidentified', 'unspecified']):
            continue

        # Get coordinates (from WGS84-converted file)
        lat = row.get('latitude')
        lon = row.get('longitude')

        records.append({
            'species_raw': raw_name,
            'state': '',
            'county': '',
            'date_detected': row.get('observation.date', ''),
            'strain': row.get('serotype_HN', row.get('Serotype', 'HPAI')),
            'sampling_method_raw': row.get('source', 'surveillance'),
            'sampling_type': 'unknown',  # SDM doesn't have mortality data
            'source': 'sdm_hpai',
            'country': row.get('Country', 'Unknown'),
            'source_file': str(file_path),
            'scientific_name_parsed': sci_name,
            'detection_count': 1,
            'latitude': lat,
            'longitude': lon,
        })

    if not records:
        print("  SDM HPAI: No valid records found")
        return pl.DataFrame()

    result = pl.DataFrame(records)
    print(f"    Parsed {len(result):,} records, {result['scientific_name_parsed'].drop_nulls().n_unique()} species with scientific names")

    return result


def load_canada_cwhc() -> pl.DataFrame:
    """
    Load Canada CWHC HPAI wild bird detections from ArcGIS export.

    This dataset contains confirmed HPAI detections from the Canadian Wildlife
    Health Cooperative dashboard.
    """
    file_path = EXTERNAL_DIR / "arcgis-hpai" / "Canada_HPAI_HighPath_Birds.csv"
    if not file_path.exists():
        print(f"  Canada CWHC data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Common name to scientific name mapping for Canadian species
    # (will be refined by taxonomy lookup)
    canada_species_map = {
        "Canada Goose": "Branta canadensis",
        "Canada goose": "Branta canadensis",
        "Cackling Goose": "Branta hutchinsii",
        "Mallard": "Anas platyrhynchos",
        "American Crow": "Corvus brachyrhynchos",
        "Bald Eagle": "Haliaeetus leucocephalus",
        "Great Horned Owl": "Bubo virginianus",
        "Snow Goose": "Anser caerulescens",
        "American Wigeon": "Mareca americana",
        "Trumpeter Swan": "Cygnus buccinator",
        "Red-tailed Hawk": "Buteo jamaicensis",
        "Red-Tailed Hawk": "Buteo jamaicensis",
        "Peregrine Falcon": "Falco peregrinus",
        "Cooper's Hawk": "Accipiter cooperii",
        "Glaucous-winged Gull": "Larus glaucescens",
        "Barred Owl": "Strix varia",
        "Great Blue Heron": "Ardea herodias",
        "White-Winged Scoter": "Melanitta deglandi",
        "Northern Harrier": "Circus hudsonius",
        "Common Raven": "Corvus corax",
        "Ring-billed Gull": "Larus delawarensis",
        "Double-crested Cormorant": "Nannopterum auritum",
        "Green-winged Teal": "Anas crecca",
        "Northern Pintail": "Anas acuta",
        "Herring Gull": "Larus argentatus",
    }

    # Convert timestamp if present
    df = df.with_columns([
        pl.col("Species").alias("species_raw"),
        pl.lit("").alias("state"),  # Canada uses province but not in this data
        pl.lit("").alias("county"),
        # Date_Found is epoch timestamp
        pl.when(pl.col("Date_Found").is_not_null())
          .then(pl.col("Date_Found").cast(pl.Int64) // 1000)
          .otherwise(pl.lit(None))
          .alias("date_epoch"),
        pl.lit("HPAI").alias("strain"),
        pl.col("Sample_Type").alias("sampling_method_raw"),
        pl.lit("unknown").alias("sampling_type"),  # No mortality distinction
        pl.lit("canada_cwhc").alias("source"),
        pl.lit("Canada").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
    ])

    # Map species names
    df = df.with_columns([
        pl.col("species_raw").replace(canada_species_map).alias("scientific_name_parsed"),
    ])

    # Convert epoch to date string
    df = df.with_columns([
        pl.when(pl.col("date_epoch").is_not_null())
          .then(pl.from_epoch("date_epoch", time_unit="s").dt.strftime("%Y-%m-%d"))
          .otherwise(pl.lit(""))
          .alias("date_detected")
    ])

    # Add latitude/longitude from Y_Latitude, X_Longitude
    if "Y_Latitude" in df.columns and "X_Longitude" in df.columns:
        df = df.with_columns([
            pl.col("Y_Latitude").alias("latitude"),
            pl.col("X_Longitude").alias("longitude"),
        ])
    else:
        df = df.with_columns([
            pl.lit(None).cast(pl.Float64).alias("latitude"),
            pl.lit(None).cast(pl.Float64).alias("longitude"),
        ])

    result = df.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed", "latitude", "longitude"
    ]).with_columns([
        pl.lit(1).cast(pl.Int64).alias("detection_count")
    ])

    # Count mapped species
    mapped = result.filter(pl.col("scientific_name_parsed") != pl.col("species_raw"))
    coords_count = result.filter(pl.col("latitude").is_not_null()).height
    print(f"    {len(result)} records, {mapped['scientific_name_parsed'].n_unique()} species pre-mapped, {coords_count} with coords")

    return result


def load_vs_surveillance() -> pl.DataFrame:
    """
    Load VS Wild Bird Surveillance H5 positive data.

    This dataset contains surveillance samples with H5 detection status and
    geographic information (state, county, watershed). It does not include
    species-level identification but provides valuable geographic coverage data.

    Note: This data is complementary - it confirms H5 presence in regions
    but doesn't add new species to our detection list.
    """
    file_path = EXTERNAL_DIR / "arcgis-hpai" / "VS_Wild_Bird_H5_Positive.csv"

    # Fall back to full surveillance file if H5-filtered not available
    if not file_path.exists():
        file_path = EXTERNAL_DIR / "arcgis-hpai" / "VS_Wild_Bird_Surveillance_full.csv"
        if not file_path.exists():
            print(f"  VS Surveillance data not found")
            return pl.DataFrame()

    df = pl.read_csv(file_path)

    # Filter for H5 detected if using full file
    if "Final_H5" in df.columns:
        df = df.filter(pl.col("Final_H5") == "Detected")

    if len(df) == 0:
        print("  No H5 positive samples found")
        return pl.DataFrame()

    # Filter for High Path only
    if "Final_Pathogenicity" in df.columns:
        hp_df = df.filter(pl.col("Final_Pathogenicity") == "High Path AI")
        if len(hp_df) > 0:
            df = hp_df
            print(f"    Filtered to {len(df)} High Path samples")

    # This data doesn't have species - it's surveillance-level
    # We'll record it as "Wild bird (unspecified)" for geographic tracking
    df = df.with_columns([
        pl.lit("Wild bird (unspecified)").alias("species_raw"),
        pl.col("State").alias("state"),
        pl.col("County").alias("county"),
        # Date_Collected is epoch timestamp
        pl.when(pl.col("Date_Collected").is_not_null())
          .then(pl.col("Date_Collected").cast(pl.Int64) // 1000)
          .otherwise(pl.lit(None))
          .alias("date_epoch"),
        pl.lit("H5").alias("strain"),
        pl.lit("surveillance").alias("sampling_method_raw"),
        pl.lit("unknown").alias("sampling_type"),
        pl.lit("vs_surveillance").alias("source"),
        pl.lit("USA").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
        pl.lit(None).cast(pl.Utf8).alias("scientific_name_parsed"),
    ])

    # Convert epoch to date string
    df = df.with_columns([
        pl.when(pl.col("date_epoch").is_not_null())
          .then(pl.from_epoch("date_epoch", time_unit="s").dt.strftime("%Y-%m-%d"))
          .otherwise(pl.lit(""))
          .alias("date_detected")
    ])

    result = df.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed"
    ]).with_columns([
        pl.lit(1).cast(pl.Int64).alias("detection_count")
    ])

    # Summary by state
    states = result.group_by("state").len().sort("len", descending=True)
    top_states = states.head(5)["state"].to_list()
    print(f"    {len(result)} H5+ samples across {states.height} states")
    print(f"    Top states: {', '.join(top_states)}")

    return result


def load_iceland_usgs() -> pl.DataFrame:
    """
    Load USGS Iceland AIV surveillance data (2010-2018).

    This dataset contains 6,635 samples from wild birds in Iceland,
    with 381 positives across 20+ species.
    """
    file_path = EXTERNAL_DIR / "usgs-datasets" / "data" / "raw" / "external" / "usgs-datasets" / "iceland_Dusek_data release list.csv"
    if not file_path.exists():
        print(f"  Iceland USGS data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path, encoding="utf8-lossy")

    # Filter to positive results only
    positives = df.filter(pl.col("Result") == "P")

    if len(positives) == 0:
        print("  Iceland USGS: No positive samples found")
        return pl.DataFrame()

    # Normalize columns
    positives = positives.with_columns([
        pl.col("Species").alias("species_raw"),
        pl.col("Region").alias("state"),
        pl.col("Location").alias("county"),
        pl.col("Date Collected").alias("date_detected"),
        pl.col("Final HA Result").fill_null("AIV+").alias("strain"),
        pl.lit("live_capture").alias("sampling_method_raw"),
        pl.lit("live").alias("sampling_type"),
        pl.lit("iceland_usgs").alias("source"),
        pl.lit("Iceland").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
        pl.col("Scientific Name").alias("scientific_name_parsed"),
    ])

    result = positives.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed"
    ]).with_columns([
        pl.lit(1).cast(pl.Int64).alias("detection_count")
    ])

    # Summary
    species_count = result["scientific_name_parsed"].n_unique()
    print(f"    {len(result)} positive samples, {species_count} species")

    return result


def load_ireland_occurrence() -> pl.DataFrame:
    """
    Load Ireland wild bird occurrence data with H5 targeting indicators.

    This is occurrence data (bird sightings) not detection data.
    Species with target_H5_HPAI=1 are target species for H5N1 surveillance.
    Useful for identifying species present in Ireland that may be susceptible.
    """
    file_path = EXTERNAL_DIR / "usgs-datasets" / "data" / "raw" / "external" / "ireland-gov" / "h5n1_wild_bird_species.csv"
    if not file_path.exists():
        print(f"  Ireland occurrence data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path, encoding="utf8-lossy")

    # Extract unique species that are H5 targets
    h5_targets = df.filter(pl.col("target_H5_HPAI") == 1)

    if len(h5_targets) == 0:
        print("  Ireland: No H5 target species found")
        return pl.DataFrame()

    # Get unique species
    species_df = h5_targets.group_by(["Scientific_Name", "Common_Name"]).agg([
        pl.col("Latitude").mean().alias("avg_lat"),
        pl.col("Longitude").mean().alias("avg_lon"),
        pl.len().alias("occurrence_count"),
    ])

    # Create pseudo-detection records for target species
    result = species_df.with_columns([
        pl.col("Common_Name").alias("species_raw"),
        pl.lit("").alias("state"),
        pl.lit("").alias("county"),
        pl.lit("2014-2020").alias("date_detected"),  # Date range in dataset
        pl.lit("H5_target").alias("strain"),
        pl.lit("occurrence_record").alias("sampling_method_raw"),
        pl.lit("unknown").alias("sampling_type"),
        pl.lit("ireland_occurrence").alias("source"),
        pl.lit("Ireland").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
        pl.col("Scientific_Name").alias("scientific_name_parsed"),
        pl.col("occurrence_count").alias("detection_count"),
    ]).select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed", "detection_count"
    ])

    # Summary
    total_species = df["Scientific_Name"].n_unique()
    target_species = len(result)
    print(f"    {target_species} H5 target species out of {total_species} total species")

    return result


def load_github_usa() -> pl.DataFrame:
    """
    Load USA HPAI wild bird data from GitHub fbranda repository.

    This is a comprehensive dataset maintained by the community.
    """
    file_path = EXTERNAL_DIR / "github-avian-flu" / "hpai-wild-birds-usa.csv"
    if not file_path.exists():
        print(f"  GitHub USA data not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path, encoding="utf8-lossy")

    # Normalize columns - same format as OAFD
    df = df.with_columns([
        pl.col("Type of Wild Bird").alias("species_raw"),
        pl.col("State").alias("state"),
        pl.col("County").alias("county"),
        pl.col("Date Detected").alias("date_detected"),
        pl.col("HPAI Strain").alias("strain"),
        pl.col("Sampling Source").str.to_lowercase().alias("sampling_method_raw"),
    ])

    # Classify sampling method
    df = df.with_columns([
        pl.when(pl.col("sampling_method_raw").str.contains("mortality|morbidity"))
          .then(pl.lit("mortality"))
          .when(pl.col("sampling_method_raw").str.contains("live"))
          .then(pl.lit("live"))
          .when(pl.col("sampling_method_raw").str.contains("harvest|nwdp"))
          .then(pl.lit("harvest"))
          .otherwise(pl.lit("other"))
          .alias("sampling_type")
    ])

    # Add provenance
    result = df.with_columns([
        pl.lit("github_usa").alias("source"),
        pl.lit("USA").alias("country"),
        pl.lit(str(file_path)).alias("source_file"),
        pl.lit(None).cast(pl.Utf8).alias("scientific_name_parsed"),
        pl.lit(1).cast(pl.Int64).alias("detection_count"),
    ]).select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed", "detection_count"
    ])

    # Summary
    species_count = result["species_raw"].n_unique()
    print(f"    {len(result)} records, {species_count} species")

    return result


def load_github_italy() -> pl.DataFrame:
    """
    Load Italy HPAI wild bird data from GitHub fbranda repository.

    Combines 2021-22 and 2022-23 seasons.
    """
    base_dir = EXTERNAL_DIR / "github-avian-flu"
    files = [
        base_dir / "hpai-wild-birds-italy-2122.csv",
        base_dir / "hpai-wild-birds-italy-2223.csv",
    ]

    dfs = []
    for file_path in files:
        if not file_path.exists():
            continue

        df = pl.read_csv(file_path, encoding="utf8-lossy")

        # Italy format: n, ID ADIS, Region, ..., Species, HPAI strain, Confirmation date
        df = df.with_columns([
            pl.col("Species").alias("species_raw"),
            pl.col("Region").alias("state"),
            pl.col("Province").alias("county"),
            pl.col("Confirmation date").alias("date_detected"),
            pl.col("HPAI strain").alias("strain"),
            pl.lit("surveillance").alias("sampling_method_raw"),
            pl.lit("unknown").alias("sampling_type"),
            pl.lit("github_italy").alias("source"),
            pl.lit("Italy").alias("country"),
            pl.lit(str(file_path)).alias("source_file"),
        ])

        # Parse scientific name from species string like "Mallard duck (Anas platyrhynchos)"
        df = df.with_columns([
            pl.col("species_raw").map_elements(
                lambda s: extract_scientific_name(str(s)) if s else None,
                return_dtype=pl.Utf8
            ).alias("scientific_name_parsed"),
            pl.col("No. animals").cast(pl.Int64).fill_null(1).alias("detection_count"),
        ])

        # Add coordinates if present
        if "Latitude" in df.columns and "Longitude" in df.columns:
            df = df.with_columns([
                pl.col("Latitude").cast(pl.Float64).alias("latitude"),
                pl.col("Longitude").cast(pl.Float64).alias("longitude"),
            ])
        else:
            df = df.with_columns([
                pl.lit(None).cast(pl.Float64).alias("latitude"),
                pl.lit(None).cast(pl.Float64).alias("longitude"),
            ])

        dfs.append(df.select([
            "species_raw", "state", "county", "date_detected", "strain",
            "sampling_method_raw", "sampling_type", "source", "country", "source_file",
            "scientific_name_parsed", "detection_count", "latitude", "longitude"
        ]))

    if not dfs:
        print("  GitHub Italy data not found")
        return pl.DataFrame()

    result = pl.concat(dfs)

    # Summary
    species_count = result["scientific_name_parsed"].drop_nulls().n_unique()
    print(f"    {len(result)} records, {species_count} species with scientific names")

    return result


def _read_defra_table(file_path) -> pl.DataFrame:
    """Read a DEFRA wild-birds file as xlsx or CSV.

    DEFRA's publishing service sometimes serves CSV bytes under the .xlsx
    asset URL (the 2026 file does), which breaks calamine's zip reader.
    Sniff the magic bytes instead of trusting the extension.
    """
    with open(file_path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"PK":  # xlsx is a zip archive
        return pl.read_excel(file_path)
    return pl.read_csv(file_path)


def load_uk_defra() -> pl.DataFrame:
    """
    Load UK DEFRA/APHA wild bird avian influenza data (2024-2026).

    Combines Excel files from multiple years. The 2026 file has clean headers,
    while 2024/2025 have header rows that need skipping.
    """
    uk_dir = EXTERNAL_DIR / "uk-defra"
    if not uk_dir.exists():
        print(f"  UK DEFRA directory not found: {uk_dir}")
        return pl.DataFrame()

    dfs = []

    # Column mapping for different file formats
    # 2026 has clean headers, 2024/2025 have title row + header row
    for year in [2024, 2025, 2026]:
        file_path = uk_dir / f"uk_wild_birds_{year}.xlsx"
        if not file_path.exists():
            continue

        try:
            if year == 2026:
                # 2026 has clean headers (may be CSV-served-as-xlsx)
                df = _read_defra_table(file_path)
                # Map columns
                col_map = {
                    "Week (Year)": "week",
                    "District": "district",
                    "County": "county",
                    "Country": "region",
                    "Species": "species_raw",
                    "Latin.Latin Name": "scientific_name_parsed",
                    "Virus Isolated": "strain",
                    "Total (Positive)": "n_birds",
                }
            else:
                # 2024/2025 have title row + description row before headers
                # Skip first 2 rows, use row 3 (index 2) as header
                df = _read_defra_table(file_path)

                # Get headers from row 2 (0-indexed row 1)
                header_row = df.row(1)  # "Week", "District", "County", etc.
                # Create new column names
                new_cols = [str(h) if h else f"col_{i}" for i, h in enumerate(header_row)]

                # Skip first 2 rows (title + header) and rename
                df = df.slice(2)  # Start from row 3
                df.columns = new_cols

                # Map columns for 2024/2025 format (column names vary slightly)
                col_map = {
                    "Week": "week",
                    "District": "district",
                    "County": "county",
                    "Species (Positive)": "species_raw",
                    "Species": "species_raw",  # 2025 variant
                    "Species (Latin)": "scientific_name_parsed",
                    "Pathotype": "strain",
                    "Total": "n_birds",
                    "Total (Positive)": "n_birds",  # 2025 variant
                }

            # Rename columns that exist
            rename_map = {k: v for k, v in col_map.items() if k in df.columns}
            if rename_map:
                df = df.rename(rename_map)

            # Skip rows with null species or placeholder rows ("no positive",
            # DEFRA 2026 also emits all-"Not applicable" summary rows)
            if "species_raw" in df.columns:
                df = df.filter(
                    pl.col("species_raw").is_not_null() &
                    ~pl.col("species_raw").str.to_lowercase().str.contains("no positive") &
                    ~pl.col("species_raw").str.to_lowercase().str.contains("not applicable")
                )
                # Clean species name - remove count suffix like "(1)", "(2)"
                df = df.with_columns([
                    pl.col("species_raw").str.replace(r"\s*\(\d+\)\s*$", "").alias("species_raw")
                ])

            # Add year and source columns
            df = df.with_columns([
                pl.lit(year).alias("year"),
                pl.lit("uk_defra").alias("source"),
                pl.lit("UK").alias("country"),
                pl.lit(str(file_path)).alias("source_file"),
                pl.lit("surveillance").alias("sampling_method_raw"),
                pl.lit("mortality").alias("sampling_type"),  # UK data is from dead bird reports
            ])

            # Parse week to approximate date
            if "week" in df.columns:
                # Week format: "1 (2026)" or just "1"
                df = df.with_columns([
                    pl.col("week").cast(pl.Utf8).str.extract(r"(\d+)", group_index=1)
                    .cast(pl.Int32).fill_null(1).alias("week_num")
                ])
                # Approximate date as start of that week
                df = df.with_columns([
                    pl.concat_str([
                        pl.lit(str(year)),
                        pl.lit("-W"),
                        pl.col("week_num").cast(pl.Utf8).str.pad_start(2, "0"),
                        pl.lit("-1")
                    ]).alias("date_detected")
                ])
            else:
                df = df.with_columns([
                    pl.lit(f"{year}-01-01").alias("date_detected")
                ])

            # Add region as state if available
            if "region" in df.columns:
                df = df.with_columns(pl.col("region").alias("state"))
            elif "district" in df.columns:
                df = df.with_columns(pl.col("district").alias("state"))
            else:
                df = df.with_columns(pl.lit("").alias("state"))

            # Ensure n_birds is numeric (handle both string and int types)
            if "n_birds" in df.columns:
                df = df.with_columns([
                    pl.col("n_birds").cast(pl.Utf8).str.extract(r"(\d+)", group_index=1)
                    .cast(pl.Int64).fill_null(1).alias("detection_count")
                ])
            else:
                df = df.with_columns(pl.lit(1).cast(pl.Int64).alias("detection_count"))

            # Drop the n_birds column to avoid type conflicts
            if "n_birds" in df.columns:
                df = df.drop("n_birds")

            # Ensure county exists
            if "county" not in df.columns:
                df = df.with_columns(pl.lit("").alias("county"))

            # Ensure strain exists
            if "strain" not in df.columns:
                df = df.with_columns(pl.lit("HPAI").alias("strain"))

            dfs.append(df)
            print(f"    {year}: {len(df)} records")

        except Exception as e:
            print(f"    {year}: Error loading - {e}")
            continue

    if not dfs:
        print("  UK DEFRA: No data files loaded")
        return pl.DataFrame()

    result = pl.concat(dfs, how="diagonal")

    # Ensure all required columns exist
    required_cols = [
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed", "detection_count"
    ]
    for col in required_cols:
        if col not in result.columns:
            result = result.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

    result = result.select(required_cols)

    # Summary
    total_records = len(result)
    species_count = result["species_raw"].n_unique()
    sci_count = result["scientific_name_parsed"].drop_nulls().n_unique()
    print(f"    Total: {total_records} records, {species_count} species ({sci_count} with scientific names)")

    return result


# ---------------------------------------------------------------------------
# APHIS mammals + commercial/backyard flocks
# ---------------------------------------------------------------------------

# Domestic species inferred from the flock "Production" label. Premises with
# mixed/unspecified birds (backyard flocks, live bird markets, gamebirds,
# "WOAH Poultry"/"WOAH Non-Poultry") are left unmapped: species_raw keeps the
# production label for provenance.
PRODUCTION_TO_SPECIES = {
    # chickens
    "commercial broiler production": "Gallus gallus",
    "commercial broiler breeder": "Gallus gallus",
    "commercial broiler breeder pullets": "Gallus gallus",
    "primary broiler breeder pedigree farm": "Gallus gallus",
    "commercial table egg layer": "Gallus gallus",
    "commercial table egg pullets": "Gallus gallus",
    "commercial table egg breeder": "Gallus gallus",
    "commercial breeder operation": "Gallus gallus",
    # turkeys
    "commercial turkey meat bird": "Meleagris gallopavo",
    "commercial turkey breeder hens": "Meleagris gallopavo",
    "commercial turkey breeder toms": "Meleagris gallopavo",
    "commercial turkey breeder replacement hens": "Meleagris gallopavo",
    "commercial turkey poult supplier": "Meleagris gallopavo",
    # ducks (US duck industry is overwhelmingly Pekin = domestic mallard)
    "commercial duck meat bird": "Anas platyrhynchos",
    "commercial duck breeder": "Anas platyrhynchos",
}


def load_aphis_mammals() -> pl.DataFrame:
    """
    Load APHIS US mammal HPAI detections (one row per animal).

    Species names may carry a "(captive)" suffix, which we move into the
    sampling method (captive vs wild) and map the base name via the shared
    MAMMAL_ALIASES table. Each record is one animal (detection_count=1).
    """
    import re as _re
    from species_aliases import MAMMAL_ALIASES

    file_path = EXTERNAL_DIR / "aphis" / "hpai-mammals.csv"
    if not file_path.exists():
        print(f"  APHIS mammals file not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    def base_name(name: str) -> str:
        return _re.sub(r"\s*\([^)]*\)", "", str(name)).strip()

    records = []
    for row in df.iter_rows(named=True):
        raw = str(row.get("Species") or "").strip()
        if not raw:
            continue
        captive = "(captive)" in raw.lower()
        base = base_name(raw)
        sci = MAMMAL_ALIASES.get(base.lower())
        records.append({
            "species_raw": base,
            "state": row.get("State") or "",
            "county": row.get("County") or "",
            "date_detected": row.get("Date Detected") or "",
            "date_collected": row.get("Date Collected") or "",
            "strain": row.get("HPAI Strain") or "HPAI",
            "sampling_method_raw": ("captive mammal (clinical case)" if captive
                                     else "wild mammal found sick/dead"),
            "sampling_type": "mortality",
            "source": "aphis_mammals",
            "country": "USA",
            "source_file": str(file_path),
            "scientific_name_parsed": sci,
            "detection_count": 1,
            # Event identity (finalized after aggregation): keeps distinct
            # events (specimens collected on different days, captive vs wild)
            # from collapsing during deduplication
            "record_ref": "",
        })

    if not records:
        print("  APHIS mammals: no records")
        return pl.DataFrame()

    result = pl.DataFrame(records)

    # The CSV repeats identical rows once per animal (e.g. three mink from the
    # same farm share one row triplet). Collapse them into event records with
    # detection_count = number of animals so deduplication cannot swallow
    # animals, while "numbers affected" still sums correctly.
    result = (
        result.group_by([
            "species_raw", "state", "county", "date_detected", "date_collected",
            "strain", "sampling_method_raw", "scientific_name_parsed",
        ])
        .agg(pl.col("detection_count").sum().alias("detection_count"))
        .with_columns([
            pl.lit("mortality").alias("sampling_type"),
            pl.lit("aphis_mammals").alias("source"),
            pl.lit("USA").alias("country"),
            pl.lit(str(file_path)).alias("source_file"),
            # One reference per aggregated event, covering every grouping
            # column — rows that survived aggregation necessarily differ in
            # at least one of them, so references (and dedup keys) are unique
            pl.concat_str([
                pl.lit("aphis-mammal:"),
                pl.col("species_raw").fill_null(""),
                pl.lit("|"),
                pl.col("county").fill_null(""),
                pl.lit("|"),
                pl.col("date_collected").fill_null(""),
                pl.lit("|"),
                pl.col("date_detected").fill_null(""),
                pl.lit("|"),
                pl.col("strain").fill_null(""),
                pl.lit("|"),
                pl.col("sampling_method_raw").fill_null(""),
            ]).alias("record_ref"),
        ])
        .drop("date_collected")
    )

    total_animals = result["detection_count"].sum()
    mapped = result.filter(pl.col("scientific_name_parsed").is_not_null())
    print(f"    {total_animals:,} animals in {len(result):,} event records, "
          f"{mapped['scientific_name_parsed'].n_unique()} species mapped "
          f"({100 * mapped['detection_count'].sum() / total_animals:.0f}% of animals)")
    return result


def load_aphis_flocks() -> pl.DataFrame:
    """
    Load APHIS commercial/backyard flock detections (premises-level).

    detection_count carries the number of birds affected on the premises
    (the headerless final column of the Tableau export), so downstream species
    aggregation sums true animal counts. A full-fidelity side table with the
    original columns is written to data/aphis_flocks.parquet.
    """
    file_path = EXTERNAL_DIR / "aphis" / "hpai-commercial-backyard-flocks.csv"
    if not file_path.exists():
        print(f"  APHIS flocks file not found: {file_path}")
        return pl.DataFrame()

    df = pl.read_csv(file_path)

    # "NA" / "Active" / a release date
    def control_status(v):
        s = str(v or "").strip()
        if not s or s.lower() in ("na", "n/a"):
            return "NA"
        if s.lower() == "active":
            return "Active"
        return "Released"

    records = []
    for row in df.iter_rows(named=True):
        production = str(row.get("Production") or "").strip()
        birds_raw = str(row.get("Birds Affected") or "0").replace(",", "")
        birds = int(birds_raw) if birds_raw.isdigit() else 0
        records.append({
            "species_raw": production or "Poultry (unspecified)",
            "state": row.get("State") or "",
            "county": row.get("County Name") or "",
            "date_detected": row.get("Confirmed Diagnosis") or "",
            "strain": "HPAI",
            "sampling_method_raw": "premises confirmation (commercial/backyard flock)",
            "sampling_type": "farm",
            "source": "aphis_flocks",
            "country": "USA",
            "source_file": str(file_path),
            "scientific_name_parsed": PRODUCTION_TO_SPECIES.get(production.lower()),
            "detection_count": birds if birds > 0 else 1,
            # Premises identity: keeps distinct flocks (same county/day/species)
            # from collapsing during deduplication
            "record_ref": row.get("Special ID") or "",
            # full-fidelity fields for the side table
            "special_id": row.get("Special ID") or "",
            "control_area_status": control_status(row.get("Control Area Released")),
            "control_area_released": str(row.get("Control Area Released") or ""),
            "birds_affected": birds,
        })

    if not records:
        print("  APHIS flocks: no records")
        return pl.DataFrame()

    detail = pl.DataFrame(records)
    detail.write_parquet(DATA_DIR / "aphis_flocks.parquet")

    result = detail.select([
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "scientific_name_parsed", "detection_count", "record_ref",
    ])

    total_birds = detail["birds_affected"].sum()
    mapped = detail.filter(pl.col("scientific_name_parsed").is_not_null())
    print(f"    {len(result):,} premises, {total_birds:,} birds affected; "
          f"{mapped.height:,} premises mapped to domestic species "
          f"({mapped['birds_affected'].sum():,} birds)")
    return result


def load_species_mapping() -> pl.DataFrame:
    """Load species name to taxon_id mapping."""
    mapping_file = DATA_DIR / "aphis_species_mapping.tsv"
    if mapping_file.exists():
        return pl.read_csv(mapping_file, separator="\t")
    return pl.DataFrame()


def load_taxonomy() -> pl.DataFrame:
    """Load taxonomy table for scientific name lookups."""
    taxonomy_file = DATA_DIR / "aves_taxonomy.tsv"
    if taxonomy_file.exists():
        return pl.read_csv(taxonomy_file, separator="\t")
    return pl.DataFrame()


def extract_scientific_name(raw_name: str) -> str | None:
    """Extract scientific name from raw species string."""
    import re
    # Try to extract from parentheses: "Common name (Genus species)"
    match = re.search(r'\(([A-Z][a-z]+ [a-z]+)\)', raw_name)
    if match:
        return match.group(1)
    return None


def harmonize_species_names(df: pl.DataFrame) -> pl.DataFrame:
    """
    Harmonize species names across sources.
    Returns dataframe with added scientific_name and taxon_id columns.

    Strategy:
    1. Try APHIS mapping (for US common names)
    2. Try extracting scientific name from parentheses (for European data)
    3. Look up taxon_id from taxonomy table
    """
    mapping = load_species_mapping()
    taxonomy = load_taxonomy()

    # First, try APHIS mapping
    if len(mapping) > 0:
        df = df.join(
            mapping.select(["aphis_name", "scientific_name", "taxon_id"]),
            left_on="species_raw",
            right_on="aphis_name",
            how="left"
        )
    else:
        df = df.with_columns([
            pl.lit(None).cast(pl.Utf8).alias("scientific_name"),
            pl.lit(None).cast(pl.Int64).alias("taxon_id"),
        ])

    # For unmapped records, try multiple fallbacks:
    # 1. Use scientific_name_parsed if available (from GISAID/USGS)
    # 2. Extract from parentheses in raw string
    # BUT: an "Unspecified …" raw label NEVER gets a binomial — even when
    # the source's own Latin column carries one (DEFRA 'Unspecified
    # Guillemot' ships 'Cepphus grylle'); genus-only strings likewise
    # (they used to resolve to an arbitrary species — 2026-11-06 fix)
    _unidentified = pl.col("species_raw").str.to_lowercase().str.contains(
        "unidentified|unknown|unspecified|undetermined|not specified")
    _genus_only = pl.col("scientific_name_parsed").str.split(" ").list.len() == 1
    df = df.with_columns([
        pl.when(pl.col("scientific_name").is_not_null())
          .then(pl.col("scientific_name"))
          .when(_unidentified | _genus_only.fill_null(True))
          .then(None)
          .when(pl.col("scientific_name_parsed").is_not_null())
          .then(pl.col("scientific_name_parsed"))
          .when(pl.col("species_raw").is_not_null())
          .then(pl.col("species_raw").map_elements(extract_scientific_name, return_dtype=pl.Utf8))
          .otherwise(None)
          .alias("scientific_name")
    ])

    # For records with scientific_name but no taxon_id, look up in taxonomy
    if len(taxonomy) > 0:
        # Create lookup for scientific names
        sci_to_taxon = taxonomy.select(["scientific_name", "taxon_id"]).unique()

        df = df.join(
            sci_to_taxon.rename({"taxon_id": "taxon_id_lookup"}),
            on="scientific_name",
            how="left"
        ).with_columns([
            pl.when(pl.col("taxon_id").is_null())
              .then(pl.col("taxon_id_lookup"))
              .otherwise(pl.col("taxon_id"))
              .alias("taxon_id")
        ]).drop("taxon_id_lookup")

    return df


def load_manual_supplements() -> pl.DataFrame:
    """
    Load curated manual supplements from data/manual/*.json.

    Each file: {"source": "<tag>", "records": [...]}. Records carry
    scientific_name_parsed so the harmonizer can map them exactly.
    These are first-class pipeline inputs — unlike the legacy add_* scripts
    that wrote into detections_merged.parquet and were wiped on rebuild.
    """
    manual_dir = DATA_DIR / "manual"
    if not manual_dir.exists():
        return pl.DataFrame()

    frames = []
    for jf in sorted(manual_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text())
        except json.JSONDecodeError as e:
            print(f"    WARNING: invalid JSON in {jf.name}: {e}")
            continue
        recs = data.get("records", [])
        if not recs:
            continue
        df = pl.DataFrame(recs)
        # Ensure required columns exist
        for col in ["state", "county", "strain", "sampling_method_raw",
                    "sampling_type", "source_file", "detection_count",
                    "latitude", "longitude"]:
            if col not in df.columns:
                df = df.with_columns(pl.lit(None).alias(col))
        df = df.with_columns(pl.lit(data.get("source", jf.stem)).alias("source"))
        frames.append(df)
        print(f"    {jf.name}: {len(df)} records (source={data.get('source', jf.stem)})")

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal_relaxed")


def harmonize_countries(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize the country column to ISO 3166-1 alpha-3 codes.

    Sources mix conventions (APHIS 'USA', sdm_hpai full names, uk_defra 'UK').
    The site groups/filters by ISO code, so mixed values split countries
    (e.g. Canada data was invisible under 'Canada' vs 'CAN').
    """
    name_to_iso = {
        "canada": "CAN", "uk": "GBR", "united kingdom": "GBR",
        "great britain": "GBR", "england": "GBR", "scotland": "GBR",
        "wales": "GBR", "northern ireland": "GBR",
        "united states of america": "USA", "united states": "USA", "usa": "USA",
        "italy": "ITA", "isle of man": "IMN", "moldova  republic of": "MDA",
        "moldova": "MDA", "slovakia": "SVK", "north macedonia": "MKD",
        "netherlands": "NLD", "finland": "FIN", "portugal": "PRT",
        "israel": "ISR", "denmark": "DNK", "hungary": "HUN", "austria": "AUT",
        "latvia": "LVA", "cyprus": "CYP", "czech republic": "CZE", "czechia": "CZE",
        "montenegro": "MNE", "france": "FRA", "spain": "ESP", "germany": "DEU",
        "luxembourg": "LUX", "norway": "NOR", "slovenia": "SVN",
        "svalbard and jan mayen islands": "SJM", "croatia": "HRV", "guernsey": "GGY",
        "jersey": "JEY", "belgium": "BEL", "estonia": "EST", "sweden": "SWE",
        "russia": "RUS", "russian federation": "RUS", "switzerland": "CHE",
        "faroe islands": "FRO", "lithuania": "LTU", "iceland": "ISL",
        "georgia": "GEO",
        "turkey": "TUR", "turkiye": "TUR", "bulgaria": "BGR", "poland": "POL",
        "bosnia and herzegovina": "BIH", "ireland": "IRL", "albania": "ALB",
        "romania": "ROU", "serbia": "SRB", "tunisia": "TUN", "greece": "GRC",
        "ukraine": "UKR", "viet nam": "VNM", "south korea": "KOR",
        "north korea": "PRK", "iran": "IRN", "iraq": "IRQ", "japan": "JPN",
        "china": "CHN", "taiwan": "TWN", "hong kong": "HKG",
        "new zealand": "NZL", "australia": "AUS", "south africa": "ZAF",
        "cote d'ivoire": "CIV", "cote d'ivoire": "CIV",
        "the netherlands": "NLD", "czech rep.": "CZE",
        # UN full-name forms (EMPRES-i/WAHLIS/WHO style) → ISO3
        "argentina": "ARG", "bangladesh": "BGD", "brazil": "BRA",
        "cambodia": "KHM", "chile": "CHL", "costa rica": "CRI",
        "ecuador": "ECU", "guatemala": "GTM", "honduras": "HND",
        "india": "IND", "kazakhstan": "KAZ", "mexico": "MEX",
        "mongolia": "MNG", "namibia": "NAM", "nepal": "NPL",
        "peru": "PER", "philippines": "PHL", "uruguay": "URY",
        "panama": "PAN", "gabon": "GAB", "ghana": "GHA",
        "cayman islands": "CYM", "greenland": "GRL", "antarctica": "ATA",
        "china, hong kong special administrative region": "HKG",
        "hong kong sar": "HKG",
        "falkland islands (malvinas)": "FLK",
        "heard island and mcdonald islands": "HMD",
        "iran (islamic republic of)": "IRN",
        "madeira islands": "PRT",
        "moldova, republic of": "MDA", "republic of moldova": "MDA",
        "netherlands (kingdom of the)": "NLD",
        "republic of korea": "KOR", "korea, republic of": "KOR",
        "saint helena": "SHN",
        "south georgia and the south sandwich islands": "SGS",
        "kuril islands": "RUS",
        "taiwan (province of china)": "TWN",
        "taiwan, province of china": "TWN",
        "the united kingdom of great britain and northern ireland": "GBR",
        "united kingdom of great britain and northern ireland": "GBR",
        # 'Global' events (WAHIS multi-country) carry no single country
        "global": None,
    }
    df = df.with_columns(
        pl.col("country").map_elements(
            lambda c: name_to_iso.get(str(c).strip().lower(), c),
            return_dtype=pl.Utf8,
        ).alias("country")
    )
    fixed = sum(1 for k, v in name_to_iso.items() if v)
    return df


def merge_all_sources() -> pl.DataFrame:
    """
    Merge detection data from all available sources.
    Returns unified dataframe with provenance.
    """
    print("Loading detection data from all sources...")

    sources_loaded = []

    # Load APHIS US
    print("  Loading APHIS US...")
    aphis = load_aphis_us()
    if len(aphis) > 0:
        print(f"    {len(aphis):,} records")
        sources_loaded.append(("aphis_us", aphis))

    # Load OAFD US 2022
    print("  Loading OAFD US 2022...")
    oafd = load_oafd_us_2022()
    if len(oafd) > 0:
        print(f"    {len(oafd):,} records")
        sources_loaded.append(("oafd_us_2022", oafd))

    # Load Italy
    print("  Loading Italy wild birds...")
    italy = load_italy_wild()
    if len(italy) > 0:
        print(f"    {len(italy):,} records")
        sources_loaded.append(("italy_wild", italy))

    # Load GISAID Avilist (global species list)
    print("  Loading GISAID Avilist (global)...")
    avilist = load_gisaid_avilist()
    if len(avilist) > 0:
        print(f"    {len(avilist)} species ({avilist['detection_count'].sum():,} isolates)")
        sources_loaded.append(("gisaid_avilist", avilist))

    # Load USGS Alaska
    print("  Loading USGS Alaska...")
    usgs = load_usgs_alaska()
    if len(usgs) > 0:
        print(f"    {len(usgs):,} positive samples")
        sources_loaded.append(("usgs_alaska", usgs))

    # Load EMPRES-i linked data
    print("  Loading EMPRES-i linked (global)...")
    empresi = load_empresi_linked()
    if len(empresi) > 0:
        print(f"    {len(empresi):,} wild bird events")
        sources_loaded.append(("empresi_linked", empresi))

    empresi_latest = load_empresi_latest()
    if len(empresi_latest) > 0:
        print(f"    {len(empresi_latest):,} latest reported events")
        sources_loaded.append(("empresi_latest", empresi_latest))

    # Load SDM HPAI data (FAO/WOAH compiled)
    print("  Loading SDM HPAI (FAO/WOAH global)...")
    sdm = load_sdm_hpai()
    if len(sdm) > 0:
        sources_loaded.append(("sdm_hpai", sdm))

    # Load Canada CWHC data
    print("  Loading Canada CWHC...")
    canada = load_canada_cwhc()
    if len(canada) > 0:
        sources_loaded.append(("canada_cwhc", canada))

    # Load VS Surveillance H5+ data (geographic coverage, no species)
    print("  Loading VS Surveillance H5+...")
    vs = load_vs_surveillance()
    if len(vs) > 0:
        sources_loaded.append(("vs_surveillance", vs))

    # Load Iceland USGS data
    print("  Loading Iceland USGS (2010-2018)...")
    iceland = load_iceland_usgs()
    if len(iceland) > 0:
        sources_loaded.append(("iceland_usgs", iceland))

    # Load Ireland occurrence data (H5 target species)
    print("  Loading Ireland H5 target species...")
    ireland = load_ireland_occurrence()
    if len(ireland) > 0:
        sources_loaded.append(("ireland_occurrence", ireland))

    # Load GitHub USA data (comprehensive)
    print("  Loading GitHub USA HPAI...")
    github_usa = load_github_usa()
    if len(github_usa) > 0:
        sources_loaded.append(("github_usa", github_usa))

    # Load GitHub Italy data
    print("  Loading GitHub Italy HPAI...")
    github_italy = load_github_italy()
    if len(github_italy) > 0:
        sources_loaded.append(("github_italy", github_italy))

    # Load UK DEFRA data
    print("  Loading UK DEFRA/APHA (2024-2026)...")
    uk_defra = load_uk_defra()
    if len(uk_defra) > 0:
        sources_loaded.append(("uk_defra", uk_defra))

    # Load APHIS mammal detections (one record per animal)
    print("  Loading APHIS mammals (2022-present)...")
    aphis_mammals = load_aphis_mammals()
    if len(aphis_mammals) > 0:
        sources_loaded.append(("aphis_mammals", aphis_mammals))

    # Load APHIS commercial/backyard flock detections (premises-level + birds affected)
    print("  Loading APHIS commercial/backyard flocks (2022-present)...")
    aphis_flocks = load_aphis_flocks()
    if len(aphis_flocks) > 0:
        sources_loaded.append(("aphis_flocks", aphis_flocks))

    # Load manual supplements (curated additions: NZ, AUS, FAO SSA, …)
    print("  Loading manual supplements (data/manual/)...")
    supplements = load_manual_supplements()
    if len(supplements) > 0:
        print(f"    {len(supplements):,} records")
        sources_loaded.append(("manual_supplements", supplements))

    if not sources_loaded:
        print("  No data sources found!")
        return pl.DataFrame()

    # Normalize columns across sources before merging
    # Some sources have extra columns (scientific_name_parsed, detection_count)
    base_cols = [
        "species_raw", "state", "county", "date_detected", "strain",
        "sampling_method_raw", "sampling_type", "source", "country", "source_file",
        "record_ref",
    ]

    normalized_dfs = []
    for name, df in sources_loaded:
        # Pad any missing base columns so a partial source schema can't
        # crash the merge (unfinished-source WIP did exactly this before).
        pad_text = {
            "species_raw": "", "state": "", "county": "", "strain": "",
            "sampling_method_raw": "", "sampling_type": "", "source": "",
            "country": "", "source_file": "",
        }
        pads = [pl.lit(v).cast(pl.Utf8).alias(c)
                for c, v in pad_text.items() if c not in df.columns]
        if "date_detected" not in df.columns:
            pads.append(pl.lit(None).cast(pl.Utf8).alias("date_detected"))
        if pads:
            df = df.with_columns(pads)
        # Add latitude/longitude if not present
        if "latitude" not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("latitude"))
        if "longitude" not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("longitude"))
        # Add scientific_name_parsed if not present
        if "scientific_name_parsed" not in df.columns:
            df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias("scientific_name_parsed"))
        # Add record_ref if not present (stable per-record reference, e.g. APHIS
        # flock Special IDs — protects distinct premises from dedup collapse)
        if "record_ref" not in df.columns:
            df = df.with_columns(pl.lit("").cast(pl.Utf8).alias("record_ref"))
        # Add detection_count if not present (default to 1 per record)
        if "detection_count" not in df.columns:
            df = df.with_columns(pl.lit(1).cast(pl.Int64).alias("detection_count"))
        else:
            # Ensure consistent type
            df = df.with_columns(pl.col("detection_count").cast(pl.Int64))

        normalized_dfs.append(df.select(base_cols + ["scientific_name_parsed", "detection_count", "latitude", "longitude"]))

    # Merge all
    all_data = pl.concat(normalized_dfs)
    print(f"\n  Total records: {len(all_data):,}")

    # Date sanity: a date that doesn't start with a digit is not a date
    # (guards against shifted-field scrape rows, e.g. DAFF 'SA')
    all_data = all_data.with_columns(
        pl.when(pl.col("date_detected").str.strip_chars().str.contains(r"^\d"))
          .then(pl.col("date_detected"))
          .otherwise(None)
          .alias("date_detected")
    )

    # Harmonize species names
    print("  Harmonizing species names...")
    all_data = harmonize_species_names(all_data)

    # Uncertainty policy: genus-level home + hard guard (2026-11-07)
    all_data = apply_uncertainty_policy(all_data)

    # Normalize country codes to ISO3 (Canada/UK/Europe were split across conventions)
    print("  Harmonizing country codes...")
    all_data = harmonize_countries(all_data)

    # Stable content-derived record id — the dedup tracker and the
    # data-activity diff (History page) key on this, so it must NOT be a
    # row position: any upstream change used to shift every id and produce
    # phantom "new record" churn (or mask genuine additions).
    all_data = all_data.with_columns(
        pl.concat_str([
            pl.col("source").fill_null(""),
            pl.col("record_ref").cast(pl.Utf8).fill_null(""),
            pl.col("scientific_name").fill_null(""),
            pl.col("country").fill_null(""),
            pl.col("date_detected").fill_null(""),
        ], separator="|").hash().cast(pl.Utf8).str.slice(0, 18)
        .alias("record_id")
    )
    # collisions within identical content rows still need distinct ids
    all_data = all_data.with_row_index("_rid")
    all_data = all_data.with_columns(
        (pl.col("record_id") + ":" + pl.col("_rid").cast(pl.Utf8)).alias("record_id")
    ).drop("_rid")

    return all_data


def apply_uncertainty_policy(df: pl.DataFrame) -> pl.DataFrame:
    """Genus-level home + HARD GUARD for uncertain records (2026-11-07).

    Genus extraction: genus-only Latin ('Numenius') or the genus behind an
    Unspecified-style raw label lands in the `genus` column — counted at
    genus level, never forced to a species.

    Guard: raises SystemExit if any uncertain row carries a binomial or a
    single-word scientific name survives — the curlew lesson (phantom
    species announced publicly, 2026-11-06) must never recur silently.
    """
    _GENUS_RE = __import__("re").compile(r"^[A-Z][a-z]{2,}$")
    _NOT_GENUS = ("idae", "iformes", "inae")

    def _looks_genus(tok):
        return (tok is not None and _GENUS_RE.match(tok)
                and not tok.lower().endswith(_NOT_GENUS))

    df = df.with_columns(
        pl.when(pl.col("scientific_name").is_not_null())
          .then(None)  # species resolved — genus field stays empty
          .otherwise(pl.coalesce(
            pl.when(pl.col("scientific_name_parsed").is_not_null()
                    & (pl.col("scientific_name_parsed").str.strip_chars()
                       .str.split(" ").list.len() == 1))
              .then(pl.col("scientific_name_parsed").str.strip_chars())
              .map_elements(lambda t: t if _looks_genus(t) else None,
                            return_dtype=pl.Utf8),
            pl.when(pl.col("species_raw").str.to_lowercase()
                      .str.contains("unspecified|undetermined|not specified")
                    & pl.col("scientific_name_parsed").is_not_null())
              .then(pl.col("scientific_name_parsed").str.strip_chars()
                     .str.split(" ").list.first())
              .map_elements(lambda t: t if _looks_genus(t) else None,
                            return_dtype=pl.Utf8),
        )).alias("genus")
    )
    # species-level uncertainty = prefix words on the BARE label; a
    # parenthetical qualifier ('Blackbird (unidentified)' = individual not
    # confirmable, species unambiguous) does not make the record uncertain
    _unid = (pl.col("species_raw").str.replace_all(r"\s*\([^)]*\)\s*", " ")
             .str.to_lowercase().str.contains(
                 "unidentified|unknown|unspecified|undetermined|not specified"))
    bad_unid = df.filter(_unid & pl.col("scientific_name").is_not_null()
                         & pl.col("scientific_name").str.contains(" "))
    bad_single = df.filter(pl.col("scientific_name").is_not_null()
                           & (pl.col("scientific_name").str.strip_chars()
                              .str.split(" ").list.len() == 1))
    if bad_unid.height or bad_single.height:
        raise SystemExit(
            f"INGEST GUARD FAILED: {bad_unid.height} uncertain rows carry a "
            f"binomial (e.g. {bad_unid['species_raw'].unique().to_list()[:3]}); "
            f"{bad_single.height} single-word scientific names survived "
            f"(e.g. {bad_single['scientific_name'].unique().to_list()[:3]}). "
            "Fix the resolver — never ship phantom species.")
    n_genus = df.filter(pl.col("genus").is_not_null()).height
    if n_genus:
        print(f"  genus-level uncertain records: {n_genus} "
              f"({df.filter(pl.col('genus').is_not_null())['genus'].n_unique()} genera)")
    return df


def compute_source_summary(df: pl.DataFrame) -> dict:
    """Compute summary statistics by source."""
    summary = {}

    for source in df["source"].unique().to_list():
        source_df = df.filter(pl.col("source") == source)
        summary[source] = {
            "records": len(source_df),
            "species": source_df["species_raw"].n_unique(),
            "mapped_species": source_df.filter(pl.col("taxon_id").is_not_null())["taxon_id"].n_unique(),
            "date_range": {
                "min": source_df["date_detected"].min(),
                "max": source_df["date_detected"].max(),
            },
            "sampling_types": source_df.group_by("sampling_type").len().to_dicts(),
            "metadata": SOURCES.get(source, {}),
        }

    return summary


def save_merged_data(df: pl.DataFrame, output_dir: Path = DATA_DIR):
    """Save merged detection data with provenance."""
    output_dir.mkdir(exist_ok=True)

    # Save full dataset
    df.write_parquet(output_dir / "detections_merged.parquet")
    # Phase 6 (DATA_MATURATION): TSV mirrors retired — regenerate on demand with
# df.write_csv('<name>.tsv', separator='\t'); the parquet is canonical.
# df.write_csv(output_dir / "detections_merged.tsv", separator="\t")

    # Compute and save summary
    summary = compute_source_summary(df)
    summary["_metadata"] = {
        "generated": datetime.now().isoformat(),
        "total_records": len(df),
        "total_species_raw": df["species_raw"].n_unique(),
        "total_species_mapped": df.filter(pl.col("taxon_id").is_not_null())["taxon_id"].n_unique(),
        "sources": list(df["source"].unique().to_list()),
    }

    with open(output_dir / "detections_provenance.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\nSaved to {output_dir}/:")
    print(f"  - detections_merged.parquet ({len(df):,} records)")
    print(f"  - detections_merged.tsv")
    print(f"  - detections_provenance.json")


def main():
    print("=" * 60)
    print("MERGING DETECTION DATA FROM MULTIPLE SOURCES")
    print("=" * 60)

    # Merge all sources
    merged = merge_all_sources()

    if len(merged) == 0:
        print("No data to merge!")
        return

    # Summary by source
    print("\n" + "=" * 60)
    print("SOURCE SUMMARY")
    print("=" * 60)

    for source in merged["source"].unique().to_list():
        source_df = merged.filter(pl.col("source") == source)
        meta = SOURCES.get(source, {})
        print(f"\n{meta.get('name', source)}:")
        print(f"  Records: {len(source_df):,}")
        print(f"  Species: {source_df['species_raw'].n_unique()}")
        print(f"  Mapped to NCBI: {source_df.filter(pl.col('taxon_id').is_not_null())['taxon_id'].n_unique()}")
        print(f"  Date range: {source_df['date_detected'].min()} - {source_df['date_detected'].max()}")

        # Sampling type breakdown
        sampling = source_df.group_by("sampling_type").len().sort("len", descending=True)
        print("  Sampling types:")
        for row in sampling.iter_rows(named=True):
            print(f"    {row['sampling_type']:12s} {row['len']:,}")

    # Overall summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    print(f"Total records: {len(merged):,}")
    print(f"Total species (raw names): {merged['species_raw'].n_unique()}")
    print(f"Total species (mapped to NCBI): {merged.filter(pl.col('taxon_id').is_not_null())['taxon_id'].n_unique()}")
    print(f"Countries: {merged['country'].unique().to_list()}")

    # Sampling type summary
    print("\nSampling type breakdown (all sources):")
    sampling_all = merged.group_by("sampling_type").len().sort("len", descending=True)
    for row in sampling_all.iter_rows(named=True):
        pct = 100 * row["len"] / len(merged)
        print(f"  {row['sampling_type']:12s} {row['len']:6,} ({pct:5.1f}%)")

    # Save
    save_merged_data(merged)


if __name__ == "__main__":
    main()
