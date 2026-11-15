#!/usr/bin/env python3
"""
Export data for the Roost web application.

Copies and optimizes data files from data/ to web/public/data/:
- Parquet files (detections, species, genomes, gene presence, susceptibility)
- GeoJSON layers for mapping
- Search index for species lookup
- Stats JSON for homepage
- Provenance and schema documentation

Usage:
    python scripts/export_web_data.py
"""

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path
import polars as pl

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
WEB_DATA_DIR = ROOT_DIR / "web" / "public" / "data"


def export_parquet_files():
    """Copy main parquet files for DuckDB-WASM."""
    print("\n=== Exporting Parquet files ===")

    files_to_copy = [
        ("detections_merged.parquet", "detections.parquet"),
        ("species_profiles_detected.parquet", "species.parquet"),
        ("genomes.parquet", "genomes.parquet"),
        ("susceptibility_scores.parquet", "susceptibility.parquet"),
    ]

    for src_name, dst_name in files_to_copy:
        src = DATA_DIR / src_name
        dst = WEB_DATA_DIR / dst_name

        if src.exists():
            if src_name == "detections_merged.parquet":
                # Phase 0.5 (SPREAD_MODEL): derive a canonical date column.
                # date_detected ships mixed ISO (all sources but aphis_us)
                # and US M/D/YYYY (aphis_us only) — split verified by source.
                df = pl.read_parquet(src)
                d = pl.col("date_detected")
                df = df.with_columns(
                    # ISO week dates (uk_defra, gisaid_avilist: '2026-W15-1')
                    pl.when(d.str.contains(r"^\d{4}-W"))
                      .then(d.str.to_date("%G-W%V-%u", strict=False))
                      # plain ISO dates
                      .when(d.str.contains(r"^\d{4}-"))
                      .then(d.str.slice(0, 10).str.to_date("%Y-%m-%d", strict=False))
                      # US M/D/YYYY (aphis_us)
                      .otherwise(d.str.to_date("%m/%d/%Y", strict=False))
                      .alias("date_iso"))
                bad = df.filter(
                    pl.col("date_detected").is_not_null() & pl.col("date_iso").is_null()).height
                if bad:
                    print(f"  NOTE: {bad} dated records have no point date (year-ranges/invalid ISO weeks) — date_iso null")
                df.write_parquet(dst)
                size_kb = dst.stat().st_size / 1024
                print(f"  Normalized {src_name} -> {dst_name} (+date_iso, {size_kb:.1f} KB)")

                # Geocode coordinate-less US rows (state-area scatter).
                # Integrated here so it can never be lost by ordering.
                sys.path.insert(0, str(Path(__file__).parent))
                from geocode_detections import apply_geocoding
                df = apply_geocoding(df)
                df.write_parquet(dst)
                geo_count = df.filter(pl.col("latitude").is_not_null()).height
                print(f"  Geocoded: {geo_count}/{df.height} ({geo_count / df.height:.1%})")
            elif src_name == "genomes.parquet":
                # Join Aves taxonomy onto the assembly catalog so the web
                # Genomes page can group by order. LEFT JOIN: mammals
                # (mink, foxes, cats — real HPAI spillover hosts) stay
                # visible with tax_order NULL and is_aves false.
                df = pl.read_parquet(src)
                tax_file = DATA_DIR / "aves_taxonomy.tsv"
                if tax_file.exists():
                    tax = pl.read_csv(tax_file, separator="\t").select([
                        "scientific_name", "order", "family"
                    ]).rename({
                        "scientific_name": "organism_name",
                        "order": "tax_order",
                        "family": "tax_family",
                    })
                    df = df.join(tax, on="organism_name", how="left").with_columns(
                        pl.col("tax_order").is_not_null().alias("is_aves"))
                    n_aves = df.filter(pl.col("is_aves")).height
                    print(f"  Taxonomy join: {n_aves} avian + "
                          f"{df.height - n_aves} other organisms (spillover "
                          f"hosts kept, tax_order NULL)")
                df.write_parquet(dst)
                size_kb = dst.stat().st_size / 1024
                print(f"  Enriched {src_name} -> {dst_name} (+tax_order, "
                      f"+is_aves, {size_kb:.1f} KB)")
            elif src_name == "susceptibility_scores.parquet":
                # Phase 3: ship only the susceptibility-specific facts;
                # the 12 columns shared with species.parquet (names,
                # taxonomy, detection/mortality/phenotype, genome flags)
                # are joined at runtime instead of duplicated.
                keep = [c for c in [
                    "scientific_name", "susceptibility_score",
                    "susceptibility_class", "confidence", "has_rigi",
                    "rigi_modifier",
                ] if c in pl.read_parquet_schema(src).names()]
                pl.read_parquet(src).select(keep).write_parquet(dst)
                size_kb = dst.stat().st_size / 1024
                print(f"  Slimmed {src_name} -> {dst_name} ({size_kb:.1f} KB, "
                      f"{len(keep)} columns)")
            else:
                shutil.copy2(src, dst)
                size_kb = dst.stat().st_size / 1024
                print(f"  Copied {src_name} -> {dst_name} ({size_kb:.1f} KB)")
        else:
            print(f"  WARNING: {src_name} not found")


def export_curated_overlays():
    """Curated overlays shipped verbatim (canonical: data/manual/)."""
    print("\n=== Exporting curated overlays ===")
    for name in ("spread_events.json", "species_overlay.json", "spread_mutations.json", "flyways.json", "spread_regions.json"):
        src = DATA_DIR / "manual" / name
        if src.exists():
            shutil.copy2(src, WEB_DATA_DIR / name)
            print(f"  Copied manual/{name} -> web/public/data/{name}")


def export_geojson_files():
    """Copy GeoJSON files for MapLibre."""
    print("\n=== Exporting GeoJSON files ===")

    geojson_dir = DATA_DIR / "geojson"
    dst_dir = WEB_DATA_DIR / "geojson"
    dst_dir.mkdir(exist_ok=True)

    if not geojson_dir.exists():
        print("  WARNING: geojson directory not found")
        return

    for src in geojson_dir.glob("*.geojson"):
        dst = dst_dir / src.name
        shutil.copy2(src, dst)
        size_kb = dst.stat().st_size / 1024
        print(f"  Copied {src.name} ({size_kb:.1f} KB)")


# Fields carried across re-exports from an existing index record (curated
# enrichment: IUCN, range, conservation, vaccination targeting…). Anything
# not listed here is rebuilt from the parquet on every export.
ENRICH_FIELDS = [
    "com", "ord", "fam", "iucn", "trend", "endemic", "range", "population",
    "notes", "maori_name", "conservation", "vaccination_target", "countries",
]


def _load_index_records(path):
    """Load a previous index/enhanced file as {scientific_name: record}."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            records = json.load(f)
        return {r.get("sci", ""): r for r in records if r.get("sci")}
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: could not read {path.name}: {e}")
        return {}


def _load_overlay():
    """Curated species overlay (data/manual/species_overlay.json, git-tracked).

    Returns {scientific_name: (entry, is_mammal)} flattened from the
    mammals / manual_detections / species_of_concern lists. This file
    is the single home for hand-curated species metadata; the scripts that
    used to edit species_index.json in place (add_mammal_species.py,
    add_nz_species.py) now upsert here instead.
    """
    path = DATA_DIR / "manual" / "species_overlay.json"
    if not path.exists():
        print(f"  WARNING: {path} not found (curated overlay skipped)")
        return {}
    try:
        with open(path) as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: could not read species_overlay.json: {e}")
        return {}
    flat = {}
    for key, is_mammal in (("mammals", True), ("manual_detections", False),
                           ("species_of_concern", False)):
        for entry in raw.get(key, []):
            sci = entry.get("scientific_name")
            if sci:
                flat[sci] = (entry, is_mammal)
    return flat


# Overlay-entry fields mapped into index records (curated context only —
# never detection counts or taxonomy, which come from the live sources).
_OVERLAY_FIELDS = [
    "iucn", "trend", "endemic", "range", "population", "notes",
    "conservation", "vaccination_target", "maori_name", "case", "countries",
]

# Overlay-entry field → index field renames
_OVERLAY_RENAMES = {
    "conservation_status": "conservation",
    "population_estimate": "population",
}

# species.parquet genome columns → compact index keys (replaces the old
# add_detections.merge_genome_data second-writer pass)
_GENOME_KEYS = [
    ("genome_accession", "genome_acc"), ("assembly_level", "genome_level"),
    ("scaffold_n50", "genome_n50"), ("has_annotation", "genome_annot"),
]


def generate_search_index():
    """Generate species search index — the site's ONLY writer of it.

    Sources, merged in one deterministic pass:
      1. species_profiles_detected.parquet  — birds: core fields + genome info
      2. detected_mammals.json               — mammals: fresh counts + genomes
      3. data/manual/species_overlay.json    — curated context (IUCN, NZ,
         maori, high-risk mammals), also appends species absent from 1-2
      4. existing index (+ legacy enhanced)   — merge-preserve so a re-export
         never silently wipes enrichment (Phase 1 regression fix)
    """
    print("\n=== Generating search index ===")

    species_file = DATA_DIR / "species_profiles_detected.parquet"
    if not species_file.exists():
        print("  WARNING: species_profiles_detected.parquet not found")
        return

    df = pl.read_parquet(species_file)

    existing = _load_index_records(WEB_DATA_DIR / "species_index.json")
    enhanced = _load_index_records(WEB_DATA_DIR / "species_index_enhanced.json")
    overlay = _load_overlay()

    def overlay_context(sci):
        """(fields dict, entry) from the curated overlay for a species."""
        entry, _ = overlay.get(sci, ({}, False))
        fields = {}
        for f in _OVERLAY_FIELDS:
            if entry.get(f) not in (None, ""):
                fields[f] = entry[f]
        for src, dst in _OVERLAY_RENAMES.items():
            if entry.get(src) not in (None, ""):
                fields.setdefault(dst, entry[src])
        return fields, entry

    def merge_enrichment(record, sci):
        """Fill curated fields. Overlay-managed species (species_of_concern,
        manual_detections) take PRECEDENCE for overlay fields — the overlay
        is the authoritative curated source (kākāpō population update
        2026-11). Otherwise: existing index → legacy enhanced → overlay."""
        carried = False
        ov, _ = overlay_context(sci)
        is_overlay_managed = bool(ov)
        for field in ENRICH_FIELDS + _OVERLAY_FIELDS:
            if is_overlay_managed and field in _OVERLAY_FIELDS and ov.get(field):
                record[field] = ov[field]  # overlay wins for its own fields
                carried = True
                continue
            if record.get(field):
                continue
            val = existing.get(sci, {}).get(field) or enhanced.get(sci, {}).get(field)
            if val in (None, ""):
                val = ov.get(field)
            if val not in (None, ""):
                record[field] = val
                carried = True
        return carried

    search_records = []
    n_enriched = 0
    seen = set()

    # --- 1. Birds from the profiles parquet (core + genome info) ---
    for row in df.iter_rows(named=True):
        sci = row.get("scientific_name", "")
        record = {
            "id": row.get("taxon_id") or sci,
            "sci": sci,
            "com": row.get("common_name", ""),
            "ord": row.get("order") or row.get("order_name", "") or "",
            "fam": row.get("family") or row.get("family_name", "") or "",
            "det": row.get("detection_records", row.get("detection_count", 0)),
        }
        for src_key, dst_key in _GENOME_KEYS:
            v = row.get(src_key)
            if v not in (None, ""):
                record[dst_key] = v
        if merge_enrichment(record, sci):
            n_enriched += 1
        search_records.append(record)
        seen.add(sci)

    # --- 2. Mammals from detected_mammals.json (fresh counts, ord=Mammalia
    # per the D113 class-filter convention; real family via overlay) ---
    n_mammals = 0
    mammals_file = WEB_DATA_DIR / "detected_mammals.json"
    mammals = []
    if mammals_file.exists():
        try:
            with open(mammals_file) as f:
                mammals = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARNING: could not read detected_mammals.json: {e}")
    for m in mammals:
        sci = m.get("sci", "")
        if not sci or sci in seen:
            continue
        seen.add(sci)
        record = {
            "id": m.get("id") or sci,
            "sci": sci,
            "com": m.get("com") or sci,
            "ord": m.get("ord") or "Mammalia",
            "fam": m.get("fam", ""),
            "det": m.get("det", 0),
            "class": "Mammalia",
        }
        if m.get("genome_acc"):
            record["genome_acc"] = m["genome_acc"]
            record["genome_level"] = m.get("genome_level", "")
        if merge_enrichment(record, sci):
            n_enriched += 1
        ov, entry = overlay_context(sci)
        if entry.get("family") and not record["fam"]:
            record["fam"] = entry["family"]
        # detected_mammals.json often carries sci==com; prefer a curated
        # common name when it adds information.
        if entry.get("common_name") and record["com"] == sci:
            record["com"] = entry["common_name"]
        search_records.append(record)
        n_mammals += 1

    # --- 3. Overlay-only species: high-risk mammals with no detections,
    # manual-case species / species of concern not present in the parquet
    # sources ---
    n_overlay_only = 0
    for sci, (entry, is_mammal) in overlay.items():
        if sci in seen:
            continue
        seen.add(sci)
        record = {
            "id": entry.get("taxon_id") or sci,
            "sci": sci,
            "com": entry.get("common_name") or sci,
            "ord": "Mammalia" if is_mammal else (entry.get("order", "")),
            "fam": entry.get("family", ""),
            "det": entry.get("detections", 0),
        }
        if is_mammal:
            record["class"] = "Mammalia"
        if entry.get("genome_accession"):
            record["genome_acc"] = entry["genome_accession"]
        if merge_enrichment(record, sci):
            n_enriched += 1
        search_records.append(record)
        n_overlay_only += 1
        if is_mammal:
            n_mammals += 1

    # --- 4. Full Aves taxonomy tail: every bird species on Earth is
    # searchable even with zero detections/genomes/research (Methods
    # promise; the hihi question 2026-11). Minimal records — the genome
    # backfill below enriches any that DO have catalogue assemblies. ---
    n_tax_only = 0
    _common_names = {}
    _cn_file = DATA_DIR / "aves_common_names.json"
    if _cn_file.exists():
        # Wikidata vernacular mirror (scripts/fetch_common_names.py) — fills
        # the ~70% of the NCBI Aves taxonomy that ships without common names.
        _common_names = json.loads(_cn_file.read_text())
    tax_file = DATA_DIR / "aves_taxonomy.tsv"
    if tax_file.exists():
        with open(tax_file) as f:
            _hdr = f.readline().rstrip("\n").split("\t")
            ix = {k: _hdr.index(k) for k in
                  ("taxon_id", "scientific_name", "common_name",
                   "rank", "order", "family")}
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) < len(_hdr):
                    continue
                if p[ix["rank"]] != "species":
                    continue
                sci = p[ix["scientific_name"]]
                if not sci or sci in seen:
                    continue
                seen.add(sci)
                search_records.append({
                    "id": p[ix["taxon_id"]] or sci,
                    "sci": sci,
                    "com": p[ix["common_name"]] or _common_names.get(sci, ""),
                    "ord": p[ix["order"]] or "",
                    "fam": p[ix["family"]] or "",
                    "det": 0,
                })
                n_tax_only += 1

    # Sort by detection count descending
    search_records.sort(key=lambda x: x.get("det", 0), reverse=True)

    # Genome backfill for records without one (overlay-only / no-detection
    # species MUST show their genomics — kākāpō fix): best catalogue
    # assembly, preferring accessions that actually have presence calls
    _gp = pl.read_parquet(DATA_DIR / "genes" / "gene_presence_v2.parquet")
    _searched = {r["assembly_accession"] for r in _gp.iter_rows(named=True)}
    _gcat = pl.read_parquet(DATA_DIR / "genomes.parquet")
    _lvl = {"Chromosome": 3, "Scaffold": 2, "Contig": 1}
    _gcat = _gcat.with_columns(pl.col("assembly_level").replace_strict(_lvl, default=0).alias("_l"))
    _best = {}
    for r in _gcat.sort(["scientific_name" if "scientific_name" in _gcat.columns else "organism_name", "_l"],
                        descending=[False, True]).iter_rows(named=True):
        sci = r.get("scientific_name") or r.get("organism_name")
        acc = r["accession"]
        prev = _best.get(sci)
        if prev is None or (acc in _searched) > (prev[0] in _searched) or \
           ((acc in _searched) == (prev[0] in _searched) and r["_l"] > prev[2]):
            _best[sci] = (acc, r["assembly_level"], r["_l"], r.get("organism_common_name"))
    n_backfilled = 0
    n_named = 0
    for rec in search_records:
        b = _best.get(rec["sci"])
        if b and not rec.get("genome_acc"):
            rec["genome_acc"] = b[0]
            rec["genome_level"] = b[1]
            rec["has_genome"] = True
            n_backfilled += 1
        # common-name backfill: catalogue carries IOC-ish names the raw
        # NCBI taxonomy lacks (taxonomy tail is ~70% unnamed)
        if b and b[3] and not rec.get("com"):
            rec["com"] = b[3]
            n_named += 1
    print(f"  genome backfill: {n_backfilled} records gained catalogue assemblies; "
          f"{n_named} gained common names")

    # Fresh breakdown of DETECTED species (det>0) — written every export so
    # the Home stats can never go stale (D107 follow-up; single writer here)
    supp_mammal_names = set()
    supp_tsv = DATA_DIR / "taxonomy_supplement.tsv"
    if supp_tsv.exists():
        supp_mammal_names = set(
            pl.read_csv(supp_tsv, separator="\t",
                        schema_overrides={"taxon_id": pl.Int64})
              .filter(pl.col("class") == "Mammalia")["scientific_name"].to_list()
        )
    det_recs = [r for r in search_records if r.get("det", 0) > 0]
    n_mam = sum(1 for r in det_recs
                if r.get("class") == "Mammalia" or r["sci"] in supp_mammal_names)
    breakdown = {
        "birds": len(det_recs) - n_mam,
        "mammals": n_mam,
        "unresolved": 0,
        "detected_total": len(det_recs),
        "index_total": len(search_records),
        "mammal_rows": sum(r["det"] for r in det_recs
                            if r.get("class") == "Mammalia" or r["sci"] in supp_mammal_names),
    }
    (DATA_DIR / "species_breakdown.json").write_text(json.dumps(breakdown, indent=2))
    print(f"  species_breakdown.json: {breakdown['birds']} birds + "
          f"{breakdown['mammals']} mammals = {breakdown['detected_total']} detected")

    output = WEB_DATA_DIR / "species_index.json"
    with open(output, "w") as f:
        json.dump(search_records, f, separators=(",", ":"), ensure_ascii=False)

    size_kb = output.stat().st_size / 1024
    print(f"  Generated species_index.json ({len(search_records)} species "
          f"[{n_mammals} mammals, +{n_overlay_only} overlay-only, "
          f"+{n_tax_only} taxonomy-only], "
          f"{n_enriched} with curated enrichment, {size_kb:.1f} KB)")


def generate_stats():
    """Generate summary statistics for the homepage."""
    print("\n=== Generating stats ===")

    stats = {
        "generated": datetime.now().isoformat(),
    }

    # Detection stats — read from the WEB copy (includes geocoding)
    det_file = WEB_DATA_DIR / "detections.parquet"
    if not det_file.exists():
        det_file = DATA_DIR / "detections_merged.parquet"
    if det_file.exists():
        df = pl.read_parquet(det_file)
        stats["detections"] = len(df)
        # 'Global' is not a country (literature records without attribution)
        stats["countries"] = df.filter(pl.col("country") != "Global")["country"].n_unique()

        # Date range
        if "date" in df.columns:
            dates = df["date"].drop_nulls()
            if len(dates) > 0:
                stats["date_min"] = str(dates.min())
                stats["date_max"] = str(dates.max())

        # Records with coordinates
        if "latitude" in df.columns:
            with_coords = df.filter(
                pl.col("latitude").is_not_null() &
                pl.col("longitude").is_not_null()
            ).height
            stats["georeferenced"] = with_coords

    # Species stats — with the mammal breakdown (D107): the aves-built
    # table counts birds only; detections also carry mammals
    species_file = DATA_DIR / "species_profiles_detected.parquet"
    if species_file.exists():
        df = pl.read_parquet(species_file)
        stats["species"] = len(df)
        try:
            import json as _json
            bd = _json.loads((DATA_DIR / "species_breakdown.json").read_text())
            stats["species_birds"] = bd.get("birds", len(df))
            stats["species_mammals"] = bd.get("mammals", 0)
        except (OSError, ValueError):
            pass

        # Top orders
        if "order_name" in df.columns:
            top_orders = (
                df.group_by("order_name")
                .agg(pl.len().alias("count"))
                .sort("count", descending=True)
                .head(5)
                .to_dicts()
            )
            stats["top_orders"] = top_orders

    # Searchable species = the freshly generated index (birds + mammals +
    # curated overlay-only species — D-phase3). generate_search_index runs
    # before this in main(), so the file reflects the current export.
    index_file = WEB_DATA_DIR / "species_index.json"
    if index_file.exists():
        try:
            with open(index_file) as f:
                stats["searchable_species"] = len(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass

    # Genome stats
    genome_file = DATA_DIR / "genomes.parquet"
    if genome_file.exists():
        df = pl.read_parquet(genome_file)
        stats["genomes"] = len(df)
        if "assembly_level" in df.columns:
            chromosome_level = df.filter(pl.col("assembly_level") == "Chromosome").height
            stats["chromosome_level_genomes"] = chromosome_level

    # Paper stats (D78: live numbers for Methods/Home)
    papers_file = WEB_DATA_DIR / "papers.json"
    if papers_file.exists():
        with open(papers_file) as f:
            stats["papers"] = len(json.load(f)["papers"])

    # Gene presence stats (Phase 2: catalogue JSON + parquet are the sources)
    cat_file = WEB_DATA_DIR / "gene_catalogue.json"
    if cat_file.exists():
        with open(cat_file) as f:
            gp = json.load(f)
        stats["panel_genes"] = len(gp.get("gene_catalogue", {}))
        stats["presence_species"] = gp.get("total_species", 0)
        stats["presence_calls"] = gp.get("total_gene_calls", 0)

    # Orthogroup stats (OrthoFinder integration; live from exported files)
    og_map_file = WEB_DATA_DIR / "gene_orthogroups.json"
    if og_map_file.exists():
        with open(og_map_file) as f:
            ogm = json.load(f)
        stats["panel_genes_mapped"] = len(ogm.get("genes", {}))
    og_matrix_file = WEB_DATA_DIR / "og_matrix.parquet"
    if og_matrix_file.exists():
        try:
            import pyarrow.parquet as pq
            import pyarrow.compute as pc
            col = pq.read_table(og_matrix_file, columns=["og"]).column("og")
            stats["orthogroups"] = pc.count_distinct(col).as_py()
        except Exception:
            pass
    smap_file = WEB_DATA_DIR / "orthofinder" / "species_map.json"
    if smap_file.exists():
        with open(smap_file) as f:
            stats["og_species"] = len(json.load(f))

    # Synteny explorer blocks
    blocks_file = WEB_DATA_DIR / "synteny" / "blocks.json"
    if blocks_file.exists():
        try:
            with open(blocks_file) as f:
                stats["synteny_blocks"] = len(json.load(f)["blocks"])
        except Exception:
            pass
    # IUCN conservation status (Wikidata P141)
    iucn_file = WEB_DATA_DIR / "species" / "iucn_status.json"
    if iucn_file.exists():
        try:
            with open(iucn_file) as f:
                stats["iucn_species"] = len(json.load(f)["status"])
        except Exception:
            pass
    # ANP32 species-barrier comparison
    anp32_file = WEB_DATA_DIR / "anp32" / "comparison.json"
    if anp32_file.exists():
        try:
            with open(anp32_file) as f:
                stats["anp32_species"] = len(json.load(f)["species"])
        except Exception:
            pass
    # Static BLAST reference set
    blast_file = WEB_DATA_DIR / "blast" / "panel_refs.json"
    if blast_file.exists():
        try:
            with open(blast_file) as f:
                stats["blast_sequences"] = len(json.load(f)["entries"])
        except Exception:
            pass

    # Source count from provenance
    prov_file = DATA_DIR / "detections_provenance.json"
    if prov_file.exists():
        with open(prov_file) as f:
            prov = json.load(f)
        # Top-level keys are source IDs
        stats["sources"] = len(prov)

    # Uncertain (genus-level) records — counted, never forced to species
    # (2026-11-07, the curlew lesson)
    try:
        detq = pl.read_parquet(WEB_DATA_DIR / "detections.parquet",
                               columns=["genus"])
        g = detq.filter(pl.col("genus").is_not_null())["genus"].value_counts()
        stats["uncertain_records"] = int(detq.filter(pl.col("genus").is_not_null()).height)
        stats["uncertain_genera"] = int(g.height)
    except Exception:
        pass

    output = WEB_DATA_DIR / "stats.json"
    with open(output, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"  Generated stats.json")
    for key, value in stats.items():
        if not isinstance(value, list):
            print(f"    {key}: {value}")


def generate_provenance():
    """Generate unified provenance documentation."""
    print("\n=== Generating provenance ===")

    provenance = {
        "generated": datetime.now().isoformat(),
        "sources": [],
        "files": {},
    }

    # Load detection provenance if available
    prov_file = DATA_DIR / "detections_provenance.json"
    if prov_file.exists():
        with open(prov_file) as f:
            det_prov = json.load(f)
            for source_id, source_data in det_prov.items():
                provenance["sources"].append({
                    "id": source_id,
                    "name": source_data.get("name", source_id),
                    "url": source_data.get("url", ""),
                    "license": source_data.get("license", "Unknown"),
                    "records": source_data.get("records", 0),
                })

    # Document exported files
    file_docs = {
        "detections.parquet": {
            "description": "All HPAI wild bird detection records",
            "schema": "detections",
            "source": "detections_merged.parquet",
        },
        "species.parquet": {
            "description": "Species profiles with detection counts, genome info, susceptibility",
            "schema": "species",
            "source": "species_profiles_detected.parquet",
        },
        "genomes.parquet": {
            "description": "NCBI genome assembly metadata for avian species",
            "schema": "genomes",
            "source": "genomes.parquet",
        },
        "susceptibility.parquet": {
            "description": "HPAI susceptibility scores and classifications",
            "schema": "susceptibility",
            "source": "susceptibility_scores.parquet",
        },
        "gene_presence.parquet": {
            "description": "Gene presence matrix (long format: species x gene calls)",
            "schema": "gene_presence",
            "source": "scripts/genes/export_presence.py (from data/genes/gene_presence_v2.jsonl)",
        },
        "gene_orthogroups.json": {
            "description": "Panel gene -> orthogroup mapping with confidence tiers",
            "schema": "gene_orthogroups",
            "source": "scripts/orthofinder/map_panel_to_og.py",
        },
        "og_matrix.parquet": {
            "description": "OrthoGroup x species copy-count matrix (dense long format)",
            "schema": "og_matrix",
            "source": "scripts/orthofinder/export_og_matrix.py",
        },
        "orthofinder/species_map.json": {
            "description": "463 OrthoFinder species -> site taxonomy map",
            "schema": "orthofinder_species",
            "source": "scripts/orthofinder/build_species_map.py",
        },
    }

    for filename, doc in file_docs.items():
        filepath = WEB_DATA_DIR / filename
        if filepath.exists():
            doc["size_bytes"] = filepath.stat().st_size
            doc["exists"] = True
        else:
            doc["exists"] = False
        provenance["files"][filename] = doc

    # OrthoFinder run provenance
    of_root = ROOT_DIR / "orthofinder" / "orthofinder_aves463_root16_20260928"
    of_manifest = of_root / "MANIFEST_core.json"
    if of_manifest.exists():
        import hashlib
        manifest_sha = hashlib.sha256(of_manifest.read_bytes()).hexdigest()
        gene_map_path = WEB_DATA_DIR / "gene_orthogroups.json"
        og_payloads = WEB_DATA_DIR / "orthogroups"
        n_og_payloads = len(list(og_payloads.glob("OG*.json"))) if og_payloads.exists() else 0
        provenance["orthofinder"] = {
            "run": "orthofinder_aves463_root16_20260928",
            "software": "OrthoFinder 3.1.5 (reviewed, corrected-root export)",
            "species": 463,
            "proteins": 6824866,
            "orthogroups": 40494,
            "accepted": "2026-09-28",
            "manifest_sha256": manifest_sha,
            "pipeline": [
                "scripts/orthofinder/build_species_map.py",
                "scripts/orthofinder/map_panel_to_og.py",
                "scripts/orthofinder/export_og_data.py",
                "scripts/orthofinder/export_og_matrix.py",
            ],
            "og_payloads_exported": n_og_payloads,
            "notes": ("Orthology resource, not conservation/phenotype approval. "
                      "Partial proteins, fast-tree uncertainty, root-dependent "
                      "memberships are accepted limitations."),
        }

    output = WEB_DATA_DIR / "provenance.json"
    with open(output, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"  Generated provenance.json ({len(provenance['sources'])} sources)")


def generate_genes_json():
    """Generate gene panel definitions for the Genes page."""
    print("\n=== Generating genes.json ===")

    # Gene panel - 19 genes organized by tier/category
    genes = [
        {
            "symbol": "MX1",
            "name": "MX Dynamin Like GTPase 1",
            "category": "Antiviral Response",
            "tier": 1,
            "description": "Key interferon-induced antiviral protein",
            "function": "Directly inhibits influenza virus replication",
        },
        {
            "symbol": "DDX58",
            "name": "RIG-I (Retinoic Acid Inducible Gene I)",
            "category": "Pattern Recognition",
            "tier": 1,
            "description": "Cytoplasmic RNA helicase that senses viral RNA",
            "function": "Recognizes 5'-triphosphate viral RNA",
        },
        {
            "symbol": "IFIH1",
            "name": "MDA5",
            "category": "Pattern Recognition",
            "tier": 1,
            "description": "RNA helicase that detects cytoplasmic dsRNA",
            "function": "Senses long dsRNA and triggers IFN response",
        },
        {
            "symbol": "EIF2AK2",
            "name": "PKR (Protein Kinase R)",
            "category": "Antiviral Response",
            "tier": 1,
            "description": "Interferon-induced protein kinase",
            "function": "Phosphorylates eIF2α to inhibit viral protein synthesis",
        },
        {
            "symbol": "ANP32A",
            "name": "Acidic Nuclear Phosphoprotein 32A",
            "category": "Host Factor",
            "tier": 1,
            "description": "Nuclear protein affecting viral polymerase",
            "function": "Required for influenza polymerase function",
        },
        {
            "symbol": "ANP32B",
            "name": "Acidic Nuclear Phosphoprotein 32B",
            "category": "Host Factor",
            "tier": 1,
            "description": "Paralog of ANP32A",
            "function": "May compensate for ANP32A in some species",
        },
        {
            "symbol": "ANP32E",
            "name": "Acidic Nuclear Phosphoprotein 32E",
            "category": "Host Factor",
            "tier": 2,
            "description": "Third ANP32 family member",
            "function": "Role in supporting influenza polymerase",
        },
        {
            "symbol": "IFNA",
            "name": "Interferon Alpha",
            "category": "Interferon System",
            "tier": 2,
            "description": "Type I interferon cytokine",
            "function": "Activates antiviral state",
        },
        {
            "symbol": "IFNB1",
            "name": "Interferon Beta 1",
            "category": "Interferon System",
            "tier": 2,
            "description": "Type I interferon cytokine",
            "function": "Induces antiviral gene expression",
        },
        {
            "symbol": "IFNG",
            "name": "Interferon Gamma",
            "category": "Interferon System",
            "tier": 2,
            "description": "Type II interferon cytokine",
            "function": "Activates macrophages",
        },
        {
            "symbol": "OAS1",
            "name": "2'-5'-Oligoadenylate Synthetase 1",
            "category": "ISG",
            "tier": 2,
            "description": "Interferon-induced enzyme",
            "function": "Activates RNase L",
        },
        {
            "symbol": "OASL",
            "name": "2'-5'-Oligoadenylate Synthetase Like",
            "category": "ISG",
            "tier": 2,
            "description": "OAS family member",
            "function": "Enhances RIG-I signaling",
        },
        {
            "symbol": "RSAD2",
            "name": "Viperin",
            "category": "ISG",
            "tier": 2,
            "description": "Radical SAM enzyme",
            "function": "Inhibits viral budding",
        },
        {
            "symbol": "ISG15",
            "name": "Interferon-Stimulated Gene 15",
            "category": "ISG",
            "tier": 2,
            "description": "Ubiquitin-like modifier",
            "function": "Conjugates to viral proteins",
        },
        {
            "symbol": "TLR3",
            "name": "Toll-Like Receptor 3",
            "category": "Pattern Recognition",
            "tier": 2,
            "description": "Endosomal receptor for dsRNA",
            "function": "Recognizes viral dsRNA",
        },
        {
            "symbol": "TLR7",
            "name": "Toll-Like Receptor 7",
            "category": "Pattern Recognition",
            "tier": 2,
            "description": "Endosomal receptor for ssRNA",
            "function": "Recognizes viral ssRNA",
        },
        {
            "symbol": "TRIM25",
            "name": "Tripartite Motif Containing 25",
            "category": "ISG",
            "tier": 2,
            "description": "E3 ubiquitin ligase",
            "function": "Activates RIG-I through ubiquitination",
        },
        {
            "symbol": "MAVS",
            "name": "Mitochondrial Antiviral Signaling Protein",
            "category": "Signal Transduction",
            "tier": 2,
            "description": "Adaptor protein for RIG-I and MDA5",
            "function": "Transmits signal to activate IFN response",
        },
        {
            "symbol": "IFIT5",
            "name": "IFN-Induced Protein with TPR 5",
            "category": "ISG",
            "tier": 3,
            "description": "Interferon-stimulated gene product",
            "function": "May bind viral RNA",
        },
    ]

    output = WEB_DATA_DIR / "genes.json"

    # Do not clobber the rich gene panel built by scripts/papers/build_gene_data.py
    # (which adds aliases, paper citations, passages, and importance scores).
    if output.exists():
        try:
            with open(output) as f:
                existing = json.load(f)
            if isinstance(existing, dict) and "genes" in existing and \
                    any("papers" in g for g in existing["genes"]):
                print(f"  Kept existing rich genes.json ({len(existing['genes'])} genes, "
                      f"built by build_gene_data.py)")
                return
        except (json.JSONDecodeError, OSError):
            pass

    with open(output, "w") as f:
        json.dump(genes, f, indent=2)

    print(f"  Generated fallback genes.json ({len(genes)} genes)")


def main():
    """Export all web data."""
    print("Roost Web Data Export")
    print("=" * 40)

    # Create output directory
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {WEB_DATA_DIR}")

    # Export each type
    export_parquet_files()
    export_curated_overlays()
    export_geojson_files()
    generate_search_index()
    generate_stats()
    generate_provenance()
    generate_genes_json()

    # Bird of the Day roster — reads the freshly exported parquet + index
    # (must run AFTER export_parquet_files/generate_search_index)
    sys.path.insert(0, str(Path(__file__).parent / "genes"))
    import build_bird_of_the_day  # noqa: E402
    if build_bird_of_the_day.main() != 0:
        raise SystemExit("bird_of_the_day export failed")

    print("\n" + "=" * 40)
    print("Export complete!")

    # Summary
    total_size = sum(f.stat().st_size for f in WEB_DATA_DIR.rglob("*") if f.is_file())
    print(f"Total size: {total_size / 1024:.1f} KB ({total_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
