#!/usr/bin/env python3
"""
Data source registry for Roost.

This module defines all data sources with metadata, schemas, and access methods.
It serves as the single source of truth for what data exists and how to get it.

Usage:
    from sources import SOURCES, get_source, SourceType

    # Get a source definition
    source = get_source("aphis")

    # List all sources by type
    detection_sources = [s for s in SOURCES.values() if s.type == SourceType.DETECTION]
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class SourceType(Enum):
    """Categories of data sources."""
    DETECTION = "detection"          # HPAI detection records
    TRACKING = "tracking"            # GPS/movement data
    GENOMICS = "genomics"            # Genome assemblies, sequences
    SURVEILLANCE = "surveillance"    # Screening/sampling results
    TAXONOMY = "taxonomy"            # Species classification
    VIRAL = "viral"                  # Viral sequences
    REFERENCE = "reference"          # External reference (linked, not downloaded)


class AccessMethod(Enum):
    """How to access the data."""
    DIRECT_DOWNLOAD = "direct"       # Simple URL download
    ARCGIS = "arcgis"                # ArcGIS Feature Service API
    API = "api"                      # REST API
    SCRAPE = "scrape"                # Browser automation required
    MANUAL = "manual"                # Manual download (registration, etc.)
    NCBI = "ncbi"                    # NCBI datasets/E-utilities


class UpdateFrequency(Enum):
    """How often the source is updated."""
    REALTIME = "realtime"            # Continuous updates
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    STATIC = "static"                # One-time dataset


@dataclass
class DataSource:
    """Definition of a data source."""
    id: str                                    # Unique identifier
    name: str                                  # Human-readable name
    type: SourceType                           # Category
    access: AccessMethod                       # How to get it
    url: str                                   # Primary URL
    description: str                           # What this data contains

    # Optional metadata
    update_frequency: UpdateFrequency = UpdateFrequency.STATIC
    requires_auth: bool = False                # Needs registration/login
    redistributable: bool = True               # Can we redistribute?
    has_coordinates: bool = False              # Contains lat/long
    output_dir: str = ""                       # Subdirectory in data/raw/external/
    output_file: str = ""                      # Primary output filename

    # Schema info
    key_fields: list[str] = field(default_factory=list)  # Important columns
    species_field: str = ""                    # Column with species name
    date_field: str = ""                       # Column with date
    lat_field: str = ""                        # Latitude column
    lon_field: str = ""                        # Longitude column

    # ArcGIS-specific
    arcgis_filter: str = "1=1"                 # WHERE clause for ArcGIS

    # API-specific
    api_params: dict = field(default_factory=dict)

    # Notes
    notes: str = ""

    def local_path(self, base_dir: Path = Path("data/raw/external")) -> Path:
        """Get the local file path for this source."""
        if self.output_dir:
            return base_dir / self.output_dir / self.output_file
        return base_dir / self.output_file


# =============================================================================
# SOURCE REGISTRY
# =============================================================================

SOURCES: dict[str, DataSource] = {}


def register(source: DataSource) -> DataSource:
    """Register a data source."""
    SOURCES[source.id] = source
    return source


def get_source(source_id: str) -> DataSource:
    """Get a source by ID."""
    if source_id not in SOURCES:
        raise KeyError(f"Unknown source: {source_id}. Available: {list(SOURCES.keys())}")
    return SOURCES[source_id]


# =============================================================================
# DETECTION SOURCES
# =============================================================================

register(DataSource(
    id="aphis",
    name="USDA APHIS Wild Bird Detections",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv",
    description="US wild bird HPAI detections. Primary US source, high quality.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=False,
    output_dir="aphis",
    output_file="hpai-wild-birds.csv",
    species_field="Bird Species",
    date_field="Collection Date",
    key_fields=["State", "County", "Bird Species", "HPAI Strain", "Sampling Method"],
))

register(DataSource(
    id="aphis_mammals",
    name="USDA APHIS HPAI Detections in Mammals",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://www.aphis.usda.gov/sites/default/files/hpai-mammals.csv",
    description=("US HPAI detections in mammals (2022-present), one row per animal. "
                 "Published behind the mammals Drupal page as its CSV export."),
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=False,
    output_dir="aphis",
    output_file="hpai-mammals.csv",
    species_field="Species",
    date_field="Date Detected",
    key_fields=["State", "County", "Species", "HPAI Strain", "Date Detected"],
    notes="Wild + captive mammals; '(captive)' suffix marks captive animals.",
))

register(DataSource(
    id="aphis_flocks",
    name="USDA APHIS Commercial & Backyard Flock Detections",
    type=SourceType.DETECTION,
    access=AccessMethod.SCRAPE,
    url="https://publicdashboards.dl.usda.gov/t/MRP_PUB/views/VS_Avian_HPAIConfirmedDetections2022/HPAI2022ConfirmedDetections",
    description=("Confirmed HPAI detections in US commercial/backyard flocks "
                 "(premises-level, with birds affected). Served via a Tableau "
                 "dashboard; exported through the hidden 'ExportToCsv' sheet. "
                 "Raw export is UTF-16 tab-delimited with a headerless final "
                 "column (birds affected)."),
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=False,
    output_dir="aphis",
    output_file="hpai-commercial-backyard-flocks.csv",
    date_field="Confirmed Diagnosis",
    key_fields=["State", "County Name", "Production", "Confirmed Diagnosis",
                "Control Area Released", "Birds Affected"],
    notes="Fetched by scripts/fetch_aphis_flocks.py (Playwright; no static CSV exists).",
    api_params={"scraper": "scripts/fetch_aphis_flocks.py"},
))

register(DataSource(
    id="ireland_dafm",
    name="Ireland DAFM Wild Bird AI Surveillance (Historical)",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://assets.gov.ie/98696/58589762-e8f9-4bb0-9d39-09570efbad62.xls",
    description="Ireland wild bird AI surveillance 1980-2020. Species targeted for H5N1 monitoring.",
    update_frequency=UpdateFrequency.STATIC,
    has_coordinates=False,
    output_dir="ireland-dafm",
    output_file="wild_bird_surveillance.xls",
    species_field="Species",
    key_fields=["Species", "County"],
    notes="Historical surveillance data. ArcGIS dashboard endpoint deprecated.",
))

register(DataSource(
    id="canada_cwhc",
    name="Canada CWHC HPAI Wildlife Dashboard",
    type=SourceType.DETECTION,
    access=AccessMethod.ARCGIS,
    url="https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/hpai_dashboard/FeatureServer/0",
    description="Canadian wild bird HPAI detections with coordinates.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=True,
    output_dir="canada-cwhc",
    output_file="hpai_wildlife.csv",
    arcgis_filter="Species_Group='Bird' AND HPAI='High Path'",
    species_field="Species",
    date_field="Date_Collected",
    lat_field="Y_Latitude",
    lon_field="X_Longitude",
    key_fields=["Species", "Province", "Date_Collected"],
    api_params={"oid_field": "ObjectId", "date_field": "Date_Found"},  # service-side names for incremental fetch
))

register(DataSource(
    id="vs_surveillance",
    name="VS Wild Bird Surveillance",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.ARCGIS,
    url="https://services7.arcgis.com/2C1NQ7u6M6SXoa8p/arcgis/rest/services/VS_Avian_Influenza_Wild_Bird_Surveillance_Dashboard_data_view_feature_layer_/FeatureServer/0",
    description="USDA Veterinary Services wild bird surveillance data.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=False,
    output_dir="arcgis-hpai",
    output_file="VS_Wild_Bird_Surveillance.csv",
    species_field="Species",
    key_fields=["State", "Species", "Final_H5"],
    api_params={"oid_field": "OBJECTID", "date_field": "Date_Collected"},  # service-side names for incremental fetch
))

register(DataSource(
    id="oafd",
    name="Open Avian Flu Dataset",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://zenodo.org/api/records/8246456/files/avian-flu-main.zip/content",
    description="Curated multi-country HPAI data from Zenodo. Includes US, Italy, UK.",
    update_frequency=UpdateFrequency.MONTHLY,
    redistributable=True,
    output_dir="avian-flu-main",
    output_file="avian-flu-main.zip",
    notes="Unzip after download. Contains subdirectories by country.",
))

register(DataSource(
    id="europe_outbreaks",
    name="European HPAI Outbreaks (fbranda)",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://raw.githubusercontent.com/fbranda/avian-flu/main/Europe/europe-outbreaks.csv",
    description="European HPAI outbreaks 2016-2021 with coordinates. Wild birds, farms, backyard.",
    has_coordinates=True,
    output_dir="github-avianflu",
    output_file="europe-outbreaks.csv",
    date_field="Confirmed Date",
    lat_field="Latitude",
    lon_field="Longitude",
    key_fields=["Country", "HPAI Strain", "Classification"],
    notes="Classification: Wild birds, Farm, Backyard, Captive birds.",
))

register(DataSource(
    id="acap_hpai",
    name="ACAP HPAI Seabird Database",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://zenodo.org/api/records/20248627/files/AcapHpai20260516_events.tsv/content",
    description="Confirmed HPAI H5N1 in seabirds (albatrosses, petrels) with coordinates.",
    has_coordinates=True,
    redistributable=True,
    output_dir="zenodo-acap-hpai",
    output_file="events.tsv",
    species_field="Species",
    date_field="Date",
    lat_field="Latitude",
    lon_field="Longitude",
    key_fields=["Species", "Region", "Subtype", "Category"],
))

register(DataSource(
    id="empresi_linked",
    name="EMPRES-i Linked Dataset",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://entrepot.recherche.data.gouv.fr/api/access/datafile/431355",
    description="FAO EMPRES-i events linked to viral sequences (2012-2021). ZIP archive.",
    output_dir="empresi-linked",
    output_file="result_files.zip",
    species_field="species_name",
    key_fields=["country", "species_name", "disease", "serotype"],
    notes="DOI: 10.57745/JNA7N9. Unzip to get doc_events_empres-i_strategy=1-to-1.csv",
))

register(DataSource(
    id="empresi_latest",
    name="FAO EMPRES-i Latest Reported Events",
    type=SourceType.DETECTION,
    access=AccessMethod.MANUAL,
    url="https://empres-i.apps.fao.org/",
    description="Latest reported HPAI events, all hosts. Automatic: FAO cloud function getLatestEventsByDate (scripts/fetch_empresi.py; wired into refresh_all). Manual browser export is the fallback — see data/raw/external/empresi-latest/README.md.",
    update_frequency=UpdateFrequency.WEEKLY,
    output_dir="empresi-latest",
    output_file="Latest_Reported_Events_2026-09-10.csv",
    species_field="Species",
    key_fields=["Country", "Species", "observation date", "Serotype"],
    notes="Baseline download 2026-09-10; future exports should query from that date. Wild rows carry embedded scientific names.",
))

# =============================================================================
# PHENOTYPE SOURCES (survival, susceptibility, resilience)
# =============================================================================
register(DataSource(
    id="fws_condor_hpai",
    name="FWS California Condor HPAI Updates 2023",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.MANUAL,
    url="https://www.fws.gov/program/california-condor-recovery/southwest-california-condor-flock-hpai-information-updates-2023",
    description="Field survival and mortality data for the Southwest California condor flock during the 2023 HPAI outbreak. Mortality counts, survivor tracking, vaccination response.",
    output_dir="phenotype/fws-condor",
    output_file="page.html",
    notes="D117 phenotype source — survival/mortality for Gymnogyps californianus.",
))

register(DataSource(
    id="antarctica_heard_hpai",
    name="Australian Antarctic Division Heard Island H5N1 Outbreak",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.MANUAL,
    url="https://www.antarctica.gov.au/news/2026/scientists-determine-extent-of-h5-avian-influenza-bird-flu-outbreak-at-heard-island-and-mcdonald-islands/",
    description="Mortality estimates and species affected from the H5N1 outbreak at Heard Island and McDonald Islands (subantarctic).",
    output_dir="phenotype/antarctica-heard",
    output_file="page.html",
    notes="D117 phenotype source — field mortality for subantarctic seabirds.",
))

register(DataSource(
    id="cdc_eid_07_0740",
    name="CDC EID: Experimental Infection of Swans and Geese with H5N1",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.MANUAL,
    url="https://wwwnc.cdc.gov/eid/article/14/1/07-0740-t1",
    description="Experimental challenge data: survival fractions for swans and geese inoculated with HPAI H5N1. Peer-reviewed.",
    output_dir="phenotype/cdc-eid",
    output_file="table.html",
    notes="D117 phenotype source — experimental survival for Anatidae (whooper swan, mute swan, greylag goose, Canada goose, mallard).",
))

# =============================================================================
# TRACKING SOURCES (Core = infected/mortality)
# =============================================================================

register(DataSource(
    id="dryad_rlha",
    name="Dryad Rough-legged Hawk HPAI Mortality",
    type=SourceType.TRACKING,
    access=AccessMethod.MANUAL,
    url="https://datadryad.org/dataset/doi:10.5061/dryad.n2z34tn92",
    description="71 GPS-tracked hawks, 29 deaths, 11 confirmed HPAI. High value.",
    requires_auth=True,
    has_coordinates=True,
    notes="Requires free Dryad account. ~40MB. Contact: npaprocki@usgs.gov",
))

register(DataSource(
    id="movebank_griffon",
    name="Movebank Griffon Vulture H5N1 (France 2022)",
    type=SourceType.TRACKING,
    access=AccessMethod.MANUAL,
    url="https://movebank.org",
    description="31 vultures tracked during France 2022 H5N1 outbreak.",
    requires_auth=True,
    has_coordinates=True,
    notes="Studies: 'Eurasian Griffon vulture in France (Grands Causses 2018)'. Request permission.",
))

# =============================================================================
# GENOMICS SOURCES
# =============================================================================

register(DataSource(
    id="ncbi_genomes",
    name="NCBI Aves Genomes",
    type=SourceType.GENOMICS,
    access=AccessMethod.NCBI,
    url="https://www.ncbi.nlm.nih.gov/datasets/",
    description="Avian genome assemblies from NCBI. 2,847 genomes, 786 species.",
    update_frequency=UpdateFrequency.WEEKLY,
    output_dir="ncbi-genomes",
    output_file="avian_genomes.zip",
    notes="Use: datasets download genome taxon 'Aves' --dehydrated",
))

register(DataSource(
    id="ncbi_taxonomy",
    name="NCBI Taxonomy",
    type=SourceType.TAXONOMY,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz",
    description="Full NCBI taxonomy dump. 40K+ Aves taxa.",
    update_frequency=UpdateFrequency.STATIC,  # dump changes rarely; no daily expectation
    output_file="taxdump.tar.gz",
))

# =============================================================================
# SURVEILLANCE SOURCES
# =============================================================================

register(DataSource(
    id="izembek",
    name="USGS Izembek Alaska Surveillance",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://www.sciencebase.gov/catalog/item/5ac7b5b7e4b0e2c2dd1108c1",
    description="AIV screening from Izembek NWR, Alaska (2011-2024). 13K samples.",
    output_dir="usgs-izembek",
    output_file="sampling.csv",
    species_field="Species_Code",
    date_field="Sample_Collection_Date",
    notes="DOI: 10.5066/F7JD4W2W. 480 AIV+ samples (low-path).",
))

# =============================================================================
# REFERENCE SOURCES (Linked, not downloaded)
# =============================================================================

register(DataSource(
    id="gbif",
    name="GBIF Bird Occurrences",
    type=SourceType.REFERENCE,
    access=AccessMethod.API,
    url="https://gbif.org",
    description="3.1B occurrence records. Use for species distribution context.",
    notes="Aves taxonKey = 212. API: gbif.org/developer/occurrence",
))

register(DataSource(
    id="ebird",
    name="eBird Observations",
    type=SourceType.REFERENCE,
    access=AccessMethod.API,
    url="https://ebird.org",
    description="500M+ bird observations. Occurrence, phenology, trends.",
    requires_auth=True,
    notes="Free API key required: ebird.org/api/keygen",
))

register(DataSource(
    id="movebank",
    name="Movebank Animal Tracking",
    type=SourceType.REFERENCE,
    access=AccessMethod.API,
    url="https://movebank.org",
    description="7,500+ tracking studies. Migration patterns, flyways.",
    notes="API: movebank.org/movebank/service/direct-read",
))

register(DataSource(
    id="gisaid",
    name="GISAID Avian Influenza",
    type=SourceType.VIRAL,
    access=AccessMethod.MANUAL,
    url="https://gisaid.org",
    description="23K+ viral isolates with host metadata. Primary sequence source.",
    requires_auth=True,
    redistributable=False,
    notes="Requires institutional email and Data Access Agreement.",
))

register(DataSource(
    id="owid_h5n1_human",
    name="Our World in Data H5N1 Human Cases",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://ourworldindata.org/grapher/h5n1-flu-reported-cases.csv",
    description="WHO H5N1 human cases since 1997. Zoonotic transmission tracking.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=False,
    redistributable=True,
    output_dir="owid",
    output_file="h5n1_human_cases.csv",
    date_field="Month",
    key_fields=["Entity", "Month", "Human cases with highly pathogenic avian influenza A/H5N1 (monthly)"],
    notes="Source: WHO Global Influenza Programme via CDC.",
))

register(DataSource(
    id="uk_defra_2026",
    name="UK DEFRA/APHA Wild Bird AI Findings 2026",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://assets.publishing.service.gov.uk/media/6a82c5ac3be22055c1aaa395/Avian_influenza_in_wild_birds_for_week_33_2026.xlsx",
    description="UK APHA wild bird avian influenza findings 2026. Updated weekly.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=True,
    output_dir="uk-defra",
    output_file="uk_wild_birds_2026.xlsx",
    species_field="Species",
    date_field="Date Found",
    key_fields=["Species", "Region", "County", "Subtype"],
    notes="URL changes weekly - check gov.uk/government/publications/avian-influenza-in-wild-birds for latest.",
))

register(DataSource(
    id="uk_defra_2025",
    name="UK DEFRA/APHA Wild Bird AI Findings 2025",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://assets.publishing.service.gov.uk/media/695d199c34c664251c38a109/Avian_Influenza_in_wild_birds_findings_2025_.xlsx",
    description="UK APHA wild bird avian influenza findings 2025. Full year cumulative.",
    update_frequency=UpdateFrequency.STATIC,
    has_coordinates=True,
    output_dir="uk-defra",
    output_file="uk_wild_birds_2025.xlsx",
    species_field="Species",
    date_field="Date Found",
    key_fields=["Species", "Region", "County", "Subtype"],
))

register(DataSource(
    id="uk_defra_2024",
    name="UK DEFRA/APHA Wild Bird AI Findings 2024",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://assets.publishing.service.gov.uk/media/67727b88743b5171e596ac6d/Avian_Influenza_in_wild_birds_findings_2024_-_Week_52.xlsx",
    description="UK APHA wild bird avian influenza findings 2024. Full year.",
    update_frequency=UpdateFrequency.STATIC,
    has_coordinates=True,
    output_dir="uk-defra",
    output_file="uk_wild_birds_2024.xlsx",
    species_field="Species",
    date_field="Date Found",
    key_fields=["Species", "Region", "County", "Subtype"],
))


# =============================================================================
# SOUTH AFRICA & FAO AFRICA (2026-08 additions)
# =============================================================================

register(DataSource(
    id="usgs_whispers",
    name="USGS WHISPers AI Mortality Events",
    type=SourceType.DETECTION,
    access=AccessMethod.API,
    url="https://whispers.usgs.gov/",
    description="Lab-confirmed HPAI wildlife mortality events from the USGS Wildlife "
                "Health Information Sharing Partnership: 842 events with species "
                "(latin names), affected counts, dates, county/state.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=False,
    output_dir="whispers",
    output_file="whispers_detections.json",
    key_fields=["id", "start_date", "affected_count", "species"],
    notes="Fetched+supplement built by scripts/fetch_whispers_events.py "
          "(public DRF JSON API, ?diagnosis=ID filter; HPAI IDs 22/660/661/662/685/692).",
))

register(DataSource(
    id="sa_ocims_strandings",
    name="South Africa OCIMS Seabird AI Response (Strandings)",
    type=SourceType.SURVEILLANCE,
    access=AccessMethod.ARCGIS,
    url="https://services6.arcgis.com/FGcnAbfUGHEZZ7XP/arcgis/rest/services/AffectedBirds20260821/FeatureServer/2",
    description="Seabird stranding/response records from the DEA/OCIMS avian influenza "
                "reporting system (Cape cormorant crisis 2021 onwards). Reported strandings, "
                "not per-record lab confirmation.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=True,
    output_dir="sa-ocims",
    output_file="affected_birds_strandings.csv",
    arcgis_filter="1=1",
    species_field="species_type",
    date_field="strandings_date",
    lat_field="bird_lat",
    lon_field="bird_long",
    key_fields=["strandings_date", "species_type", "animal_cond", "Prov"],
    api_params={"oid_field": "objectid", "date_field": "strandings_date"},  # service-side names for incremental fetch
    notes="Feeds the DEA 'Seabird Response' dashboard; ~1.9k records, actively updated. "
          "Companion Locality layer: portal.environment.gov.za/server/rest/services/OC/AI_Response/MapServer",
))

register(DataSource(
    id="woah_wahis",
    name="WOAH WAHIS Avian Influenza Events",
    type=SourceType.DETECTION,
    access=AccessMethod.API,
    url="https://wahis.woah.org/#/event-management",
    description="Official WOAH immediate notifications and follow-up reports for "
                "avian influenza (HPAI poultry, HPAI non-poultry incl. wild birds, "
                "bovine HPAI): ~2k events with per-species case/death totals, "
                "outbreak coordinates, lab results.",
    update_frequency=UpdateFrequency.WEEKLY,
    has_coordinates=True,
    output_dir="wahis",
    output_file="events.json",
    key_fields=["eventId", "country", "disease", "subType", "startedOn"],
    notes="Fetched by scripts/fetch_wahis_events.py (public /api/v1/pi endpoints; "
          "detail route needs a browser context). Supplement built by "
          "scripts/add_wahis_detections.py. Disease IDs: 668 poultry, 671 non-poultry/wild, 922 bovine.",
))

register(DataSource(
    id="fao_global_aiv",
    name="FAO Global AIV with Zoonotic Potential",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://www.fao.org/animal-health/situation-updates/global-aiv-with-zoonotic-potential",
    description="FAO global avian influenza situation update — country table with "
                "last-outbreak dates, event totals (W/wildlife, M/mammal breakdowns), "
                "and species affected. Covers all regions incl. South America, Asia, Europe.",
    update_frequency=UpdateFrequency.MONTHLY,
    has_coordinates=False,
    output_dir="fao-ssa",
    output_file="global_aiv_with_zoonotic_potential.html",
    notes="Parsed by scripts/add_fao_detections.py together with the SSA page. "
          "Independent validation: matches NZ DOC cases (2 events, same species).",
))

register(DataSource(
    id="fao_ssa_hpai",
    name="FAO Sub-Saharan Africa HPAI Situation Update",
    type=SourceType.DETECTION,
    access=AccessMethod.DIRECT_DOWNLOAD,
    url="https://www.fao.org/animal-health/situation-updates/sub-saharan-africa-hpai/en",
    description="FAO situation-update table of confirmed HPAI events in sub-Saharan Africa "
                "(country, admin regions, last event date, event counts, species affected). "
                "Parsed by scripts/add_fao_ssa_detections.py.",
    update_frequency=UpdateFrequency.MONTHLY,
    has_coordinates=False,
    output_dir="fao-ssa",
    output_file="sub_saharan_africa_hpai.html",
    notes="HTML table; small but the only per-species confirmed-event layer for Africa. "
          "Companion: WOAH RR-Africa immediate notifications index (parseable disease|date|country list)",
))


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def list_sources(
    source_type: Optional[SourceType] = None,
    downloadable_only: bool = False
) -> list[DataSource]:
    """List sources, optionally filtered."""
    sources = list(SOURCES.values())

    if source_type:
        sources = [s for s in sources if s.type == source_type]

    if downloadable_only:
        sources = [s for s in sources if s.access != AccessMethod.MANUAL
                   and s.type != SourceType.REFERENCE]

    return sources


def sources_summary() -> str:
    """Generate a summary of all sources."""
    lines = ["# Data Sources Summary", ""]

    by_type: dict[SourceType, list[DataSource]] = {}
    for s in SOURCES.values():
        by_type.setdefault(s.type, []).append(s)

    for stype in SourceType:
        sources = by_type.get(stype, [])
        if sources:
            lines.append(f"## {stype.value.title()} ({len(sources)} sources)")
            for s in sources:
                auth = " [AUTH]" if s.requires_auth else ""
                coords = " [GPS]" if s.has_coordinates else ""
                lines.append(f"- **{s.id}**: {s.name}{auth}{coords}")
            lines.append("")

    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for s in SOURCES.values():
                print(f"{s.id}: {s.name} ({s.type.value})")
        elif cmd == "summary":
            print(sources_summary())
        elif cmd in SOURCES:
            s = SOURCES[cmd]
            print(f"ID: {s.id}")
            print(f"Name: {s.name}")
            print(f"Type: {s.type.value}")
            print(f"Access: {s.access.value}")
            print(f"URL: {s.url}")
            print(f"Coordinates: {s.has_coordinates}")
            print(f"Auth Required: {s.requires_auth}")
            if s.notes:
                print(f"Notes: {s.notes}")
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python sources.py [list|summary|<source_id>]")
    else:
        print(f"Registered {len(SOURCES)} data sources")
        print("Run: python sources.py list")
