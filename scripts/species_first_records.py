#!/usr/bin/env python3
"""
Species first records — a registry of when each species was first registered
in Roost's detection data.

Ornithology convention: a "first record" is the first documented detection of
a species. This registry tracks two distinct dates per species:

  registered_on     the pipeline date when the species first appeared in the
                    harmonized detection table (i.e. when Roost learned of it)
  first_detection   the earliest detection DATE in the data (often historical,
                    e.g. a 2005 SDM record ingested in 2026)

Append-only semantics: registered_on is written once and never changes.
Record counts / countries / first_detection refresh on every run (they
describe the data, not the registration event).

Outputs:
  data/species_first_records.json           canonical registry
  web/public/data/species_first_records.json  web export (same content)

Usage:
  python scripts/species_first_records.py                     # normal run
  python scripts/species_first_records.py --seed-baseline \
      data/backups/detections_merged_backup_2026-09-11.parquet \
      --seed-date 2026-09-11                                  # first-time seed
"""

import argparse
import json
import re
from datetime import date
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WEB_DATA = PROJECT_ROOT / "web" / "public" / "data"
REGISTRY_PATH = DATA_DIR / "species_first_records.json"
WEB_EXPORT_PATH = WEB_DATA / "species_first_records.json"

# Baseline name variants that the species harmonizer later consolidated into
# canonical binomials. A species reachable only via one of these variants was
# in the database before — registering it "today" would be misleading.
CONSOLIDATED_ALIASES = {
    "American Widgeon": "Mareca americana",
    "Cackling Geese": "Branta hutchinsii",
    "Glaucous-Winged Gull": "Larus glaucescens",
    "Great-horned Owl": "Bubo virginianus",
    "Green Winged Teal": "Anas carolinensis",
    "Green-Winged Teal": "Anas carolinensis",
    "Long-Eared Owl": "Asio otus",
    "Raven": "Corvus corax",
    "Red-Breasted Merganser": "Mergus serrator",
    "Whistling Swan (Tundra Swan)": "Cygnus columbianus",
}

# Valid binomial/trinomial shape (loose; membership in species_table is the
# real gate — this just keeps error messages meaningful).
BINOMIAL = re.compile(r"^[A-Z][a-z]+ [a-z][a-z-]+(?: [a-z-]+)?$")


def add_date_iso(df: pl.DataFrame) -> pl.DataFrame:
    """Derive date_iso exactly like export_web_data.py (ISO-week/ISO/US)."""
    d = pl.col("date_detected")
    return df.with_columns(
        pl.when(d.str.contains(r"^\d{4}-W"))
          .then(d.str.to_date("%G-W%V-%u", strict=False))
          .when(d.str.contains(r"^\d{4}-"))
          .then(d.str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False))
          .otherwise(d.str.to_date("%m/%d/%Y", strict=False))
          .alias("date_iso")
    )


def current_species() -> pl.DataFrame:
    """Valid species with detection stats from the canonical parquet.

    Gate: a real NCBI taxon_id + strict binomial name (canonicalization
    guarantees this shape). This covers mammals, which the aves-derived
    species_table lacks — that table only enriches common names."""
    det = pl.read_parquet(DATA_DIR / "detections_merged.parquet")
    det = add_date_iso(det)

    sp = pl.read_parquet(DATA_DIR / "species_table.parquet").select(
        ["taxon_id", "common_name"]
    ).filter(pl.col("taxon_id").is_not_null())

    det = det.filter(
        pl.col("taxon_id").is_not_null()
        & pl.col("scientific_name").str.contains(r"^[A-Z][a-z]+ [a-z][a-z-]+$")
    )

    df = (
        det.join(sp, on="taxon_id", how="left")
        .group_by("taxon_id", "scientific_name")
        .agg(
            pl.col("common_name").drop_nulls().mode().first().alias("common_name"),
            pl.col("date_iso").min().alias("first_detection"),
            pl.col("date_iso").max().alias("last_detection"),
            pl.len().alias("records"),
            pl.col("country").drop_nulls().unique().alias("countries"),
            pl.col("source").mode().first().alias("top_source"),
        )
        .sort("scientific_name")
    )

    # Mammals et al.: fall back to NCBI vernacular names (names.dmp)
    missing = df.filter(pl.col("common_name").is_null())["taxon_id"].to_list()
    if missing:
        want = {str(t) for t in missing}
        ncbi = {}
        names_dmp = DATA_DIR / "taxonomy" / "names.dmp"
        if names_dmp.exists():
            for line in names_dmp.read_text(errors="ignore").splitlines():
                parts = line.split("\t|\t")
                if len(parts) >= 4 and parts[0] in want:
                    if parts[3].strip("|\t ") in ("genbank common name", "common name"):
                        ncbi.setdefault(parts[0], parts[1].strip())
        if ncbi:
            df = df.with_columns(
                pl.col("common_name").fill_null(
                    pl.col("taxon_id").cast(pl.String).replace_strict(ncbi, default=None)
                )
            )
    return df


def main():
    parser = argparse.ArgumentParser(description="Species first-records registry")
    parser.add_argument("--seed-baseline", type=Path, default=None,
                        help="prior detections parquet; its species are registered on --seed-date")
    parser.add_argument("--seed-date", type=str, default=None,
                        help="registration date for baseline species (YYYY-MM-DD)")
    args = parser.parse_args()

    today = date.today().isoformat()
    if args.seed_date:
        date.fromisoformat(args.seed_date)  # validate

    cur = current_species()
    print(f"Current valid detected species (rank=species, taxonomy-mapped): {len(cur)}")

    # ---- baseline names for seeding -------------------------------------
    baseline_names = set()
    if args.seed_baseline:
        base = pl.read_parquet(args.seed_baseline)
        baseline_names = set(
            base["scientific_name"].drop_nulls().unique().to_list()
        )
        # lift consolidated variants to their canonical binomial
        for variant, canonical in CONSOLIDATED_ALIASES.items():
            if variant in baseline_names:
                baseline_names.discard(variant)
                baseline_names.add(canonical)
        print(f"Baseline species names (incl. consolidated aliases): {len(baseline_names)}")

    # ---- merge with existing registry ------------------------------------
    registry = {"registrations": []}
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text())
    known = {r["scientific_name"]: r for r in registry["registrations"]}

    rows = cur.iter_rows(named=True)
    entries, new_today = [], []
    for r in rows:
        name = r["scientific_name"]
        if not BINOMIAL.match(name):
            continue  # safety net; the taxonomy join should already exclude junk
        first_det = r["first_detection"].isoformat() if r["first_detection"] else None
        last_det = r["last_detection"].isoformat() if r["last_detection"] else None
        if name in known:
            e = known[name]
            e.update(  # data stats refresh; registration date immutable
                common_name=r["common_name"], first_detection=first_det,
                last_detection=last_det, records=r["records"],
                countries=sorted(r["countries"]), top_source=r["top_source"],
            )
            entries.append(e)
            continue
        if args.seed_baseline and name in baseline_names:
            reg_date = args.seed_date or today
            via = None
        else:
            reg_date = today
            via = r["top_source"]
            new_today.append((name, r["common_name"], reg_date, first_det, r["records"]))
        entries.append({
            "scientific_name": name,
            "common_name": r["common_name"],
            "taxon_id": r["taxon_id"],
            "registered_on": reg_date,
            "first_detection": first_det,
            "last_detection": last_det,
            "records": r["records"],
            "countries": sorted(r["countries"]),
            "top_source": r["top_source"],
            "registered_via": via,
        })

    entries.sort(key=lambda e: (e["registered_on"], e["scientific_name"]), reverse=True)

    doc = {
        "description": ("Species first records: when each species first entered "
                        "Roost's harmonized detection table. registered_on = pipeline "
                        "date of first appearance; first_detection = earliest detection "
                        "date in the data (may predate registration)."),
        "schema_version": 1,
        "generated": date.today().isoformat(),
        "total_registered": len(entries),
        "registrations": entries,
    }
    if not args.seed_baseline and registry.get("seed_notes"):
        doc["seed_notes"] = registry["seed_notes"]  # preserve provenance
    if args.seed_baseline:
        dropped = sorted(
            n for n in baseline_names
            if n not in {e["scientific_name"] for e in entries}
        )
        doc["seed_notes"] = {
            "baseline": str(args.seed_baseline),
            "baseline_species_without_current_records": dropped,
        }
        if dropped:
            print(f"  NOTE: {len(dropped)} baseline names have no current records: "
                  f"{dropped[:10]}{'…' if len(dropped) > 10 else ''}")

    REGISTRY_PATH.write_text(json.dumps(doc, indent=2))
    WEB_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEB_EXPORT_PATH.write_text(json.dumps(doc, separators=(",", ":")))

    print(f"Registry: {len(entries)} species → {REGISTRY_PATH}")
    print(f"Web export → {WEB_EXPORT_PATH}")
    if new_today:
        print(f"\nNewly registered today ({len(new_today)}):")
        for name, common, reg, first, n in sorted(new_today, key=lambda x: x[0]):
            print(f"  {name:34s} {str(common or '')[:22]:22s} first={first or '?':12s} {n:>5} recs")


if __name__ == "__main__":
    main()
