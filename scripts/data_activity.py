#!/usr/bin/env python3
"""Data activity log — an event registry for changes in Roost's DATA.

Not a product changelog: every event describes the data itself.

  detections_added   N new detection records vs the previous run (by source)
  species_registered N species entered the first-records registry today
  genome_added       a genome assembly entered the catalog
                      trigger: 'detection'  — mammal detected → genome fetched
                      trigger: 'periodic'   — avian NCBI freshness check
  genome_updated     a better assembly replaced an older one (periodic)

Outputs:
  data/data_activity.json             human-readable event log (append-mostly)
  web/public/data/data_activity.json  compact copy for the website
  data/data_activity_snapshot.json    previous-run counters (delta base)

Idempotency: summary events are one-per-date (upserted on rerun);
genome events are deduped by accession. The log never records UI changes.
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import polars as pl

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "model"))
from iso3_names import ISO3_NAMES  # noqa: E402
DATA_DIR = ROOT / "data"
TAX_DIR = DATA_DIR / "taxonomy"
DETECTIONS = DATA_DIR / "detections_merged.parquet"
GENOMES = DATA_DIR / "genomes.parquet"
FIRST_RECORDS = DATA_DIR / "species_first_records.json"
ACTIVITY = DATA_DIR / "data_activity.json"
SNAPSHOT = DATA_DIR / "data_activity_snapshot.json"
IDS_SNAPSHOT = DATA_DIR / "data_activity_ids.parquet"  # record_id set (v2: exact row diffs)
PAPER_IDS_SNAPSHOT = DATA_DIR / "data_activity_paper_ids.json"
CONN_KEYS_SNAPSHOT = DATA_DIR / "data_activity_connection_keys.json"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
RELATIONSHIPS_JSON = ROOT / "web" / "public" / "data" / "gene_relationships.json"
WEB_EXPORT = ROOT / "web" / "public" / "data" / "data_activity.json"

# more distinct species than this in one delta → too many to fit in the feed
SPECIES_DETAIL_MAX = 10

TODAY = date.today().isoformat()


# ---------------------------------------------------------------- taxonomy
class Lineage:
    """Resolve class/order from the local NCBI taxdump (nodes.dmp/names.dmp)."""

    def __init__(self):
        self.parent, self.rank = {}, {}
        self.names = {}
        for line in (TAX_DIR / "nodes.dmp").read_text(errors="ignore").splitlines():
            p = line.split("\t|\t")
            if len(p) >= 3:
                self.parent[p[0]] = p[1]
                self.rank[p[0]] = p[2].rstrip("\t|")
        for line in (TAX_DIR / "names.dmp").read_text(errors="ignore").splitlines():
            p = line.split("\t|\t")
            if len(p) >= 4 and p[3].strip("\t| ") == "scientific name":
                self.names[p[0]] = p[1]
        self._cache = {}

    def ranked(self, taxon_id: int, want_rank: str) -> str | None:
        tid = str(taxon_id)
        key = (tid, want_rank)
        if key in self._cache:
            return self._cache[key]
        seen, cur = set(), tid
        out = None
        while cur and cur not in seen and cur in self.rank:
            seen.add(cur)
            if self.rank[cur] == want_rank:
                out = self.names.get(cur)
                break
            cur = self.parent.get(cur)
        self._cache[key] = out
        return out

    def klass(self, taxon_id: int) -> str | None:
        return self.ranked(taxon_id, "class")

    def order(self, taxon_id: int) -> str | None:
        return self.ranked(taxon_id, "order")

    def is_aves(self, taxon_id: int) -> bool:
        return self.klass(taxon_id) == "Aves"


# ------------------------------------------------------------------- NCBI
def ncbi_best_assembly(scientific_name: str) -> dict | None:
    """Best NCBI assembly for a species (RefSeq > chromosome > scaffold).

    Returns None both when NCBI has no assembly for the taxon (common for
    data-poor species — the avian gap is real) and on query failure; stderr
    is surfaced so the two are distinguishable in logs.
    """
    import shutil
    exe = shutil.which("datasets") or "datasets"  # direct binary; avoid nested pixi
    try:
        result = subprocess.run(
            [exe, "summary", "genome", "taxon", scientific_name, "--as-json-lines"],
            capture_output=True, text=True, timeout=45,
        )
        if result.returncode != 0:
            msg = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "rc!=0"
            print(f"      NCBI: {msg}", flush=True)
            return None
        best, best_score = None, -1
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            for r in data.get("reports", []):
                acc = r.get("accession", "")
                level = r.get("assembly_info", {}).get("assembly_level", "")
                score = 10 if acc.startswith("GCF_") else 0
                score += {"Chromosome": 5, "Scaffold": 2, "Contig": 1}.get(level, 0)
                if score > best_score:
                    best_score, best = score, r
        if best is None:
            return None
        org, asm, stats = (best.get("organism", {}),
                           best.get("assembly_info", {}),
                           best.get("assembly_stats", {}))
        return {
            "accession": best.get("accession"),
            "organism_name": org.get("organism_name") or scientific_name,
            "organism_common_name": org.get("common_name"),
            "taxon_id": org.get("tax_id"),
            "assembly_level": asm.get("assembly_level"),
            "contig_n50": stats.get("contig_n50"),
            "scaffold_n50": stats.get("scaffold_n50"),
            "total_length": stats.get("total_sequence_length"),
            "annotation_status": "Full annotation" if best.get("annotation_info") else None,
            "is_representative": asm.get("refseq_category") == "representative genome",
        }
    except Exception as e:
        print(f"    NCBI query failed for {scientific_name}: {e}")
        return None


# -------------------------------------------------------------- summaries
def upsert_event(events: list, today_event: dict) -> list:
    """Summary events are one-per-date: replace same-day same-kind."""
    kept = [e for e in events
            if not (e.get("date") == today_event["date"]
                    and e.get("kind") == today_event["kind"])]
    kept.append(today_event)
    return kept


def summarize_detections(prev_ids, prev_total=None) -> tuple[dict, dict | None]:
    """Exact row-level diff vs the previous record_id set.

    Returns (counts, detections_added event or None). The event carries the
    species breakdown when the delta spans ≤ SPECIES_DETAIL_MAX distinct
    species (bigger refreshes show count + sources only — too many to fit).

    NOTE: record_ids are NOT stable across merges (source:rownum style
    shifts when sources re-harvest), so `count` is row-churn, not news.
    `net` (total_after − prev_total) is the honest number — consumers
    (bsky bot) display `net` when present (2026-11-06: churn read 23,100
    on a +24 day).
    """
    det = pl.read_parquet(DETECTIONS)
    total = det.height
    by_source = dict(Counter(det["source"].drop_nulls().to_list()))
    counts = {"total": total, "by_source": by_source}
    if prev_ids is None:
        return counts, None
    new = det.filter(~pl.col("record_id").is_in(list(prev_ids)))
    if new.height <= 0:
        return counts, None
    src_delta = dict(Counter(new["source"].drop_nulls().to_list()))
    src_delta = dict(sorted(src_delta.items(), key=lambda kv: -kv[1]))
    event = {
        "date": TODAY, "kind": "detections_added", "count": new.height,
        "total_after": total, "by_source": src_delta,
    }
    if prev_total is not None:
        event["net"] = total - prev_total
    species = Counter(new["scientific_name"].drop_nulls().to_list())
    # "unidentified" rows (null species) get an explicit chip so an event
    # can't read as only-geese when most of it is unspecified
    unnamed = new.height - new["scientific_name"].drop_nulls().len()
    if unnamed > 0:
        species["Unidentified (no species reported)"] = unnamed
    if 0 < len(species) <= SPECIES_DETAIL_MAX:
        # common names from the first-records registry
        common = {}
        if FIRST_RECORDS.exists():
            for r in json.loads(FIRST_RECORDS.read_text())["registrations"]:
                common[r["scientific_name"]] = r.get("common_name")
        event["species"] = [
            {"name": n, "n": c} for n, c in
            sorted(species.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        event["detail"] = [
            {
                "sci": r["scientific_name"],
                "com": common.get(r["scientific_name"]),
                "state": r.get("state"), "county": r.get("county"),
                "country": r.get("country"),
                "date": str(r.get("date_detected") or "")[:10].lstrip("0")
                        if r.get("date_detected") else None,
                "source": r.get("source"),
            }
            for r in new.sort("scientific_name").iter_rows(named=True)
        ][:20]
    return counts, event


def summarize_registrations(events: list, lin: Lineage) -> None:
    if not FIRST_RECORDS.exists():
        return
    reg = json.loads(FIRST_RECORDS.read_text())
    fresh = [r for r in reg["registrations"] if r["registered_on"] == TODAY]
    if not fresh:
        return
    aves = sum(1 for r in fresh
               if r.get("taxon_id") and lin.is_aves(r["taxon_id"]))
    mammals = sum(1 for r in fresh
                  if r.get("taxon_id") and lin.klass(r["taxon_id"]) == "Mammalia")
    upsert = {
        "date": TODAY, "kind": "species_registered",
        "count": len(fresh), "aves": aves, "mammals": mammals,
        "examples": [{"sci": r["scientific_name"],
                       "com": r.get("common_name") or "",
                       "first": r.get("first_detection") or "",
                       "country": (ISO3_NAMES.get((r.get("countries") or [None])[0], "")
                                    if r.get("countries") else ""),
                       "records": r.get("records", 0)}
                      for r in
                      sorted(fresh, key=lambda r: -r.get("records", 0))[:5]],
    }
    events.extend(upsert_event(events, upsert))


def summarize_papers(events) -> None:
    """papers_added event: diff papers.json ids vs snapshot, with highlights."""
    if not PAPERS_JSON.exists():
        return
    doc = json.loads(PAPERS_JSON.read_text())
    papers = doc if isinstance(doc, list) else doc.get("papers", [])
    ids = {p.get("id") for p in papers}
    prev = set(json.loads(PAPER_IDS_SNAPSHOT.read_text())) \
        if PAPER_IDS_SNAPSHOT.exists() else None
    if prev is not None:
        fresh = [p for p in papers if p.get("id") not in prev and p.get("id")]
        if fresh:
            fresh.sort(key=lambda p: -(int(p.get("year") or 0)))
            # stamp the event with the batch's own 'added' date (falls back
            # to TODAY) — the papers-only pass can run past midnight, which
            # previously stamped the event a day later than the papers
            added_dates = sorted(p.get("added") for p in fresh if p.get("added"))
            ev_date = added_dates[-1] if added_dates else TODAY
            upsert = {
                "date": ev_date, "kind": "papers_added", "count": len(fresh),
                "paper_ids": [p["id"] for p in fresh],
                "highlights": [
                    {"id": p["id"], "title": (p.get("title") or "")[:90],
                     "year": p.get("year")}
                    for p in fresh[:3]
                ],
            }
            events.extend(upsert_event(events, upsert))
    PAPER_IDS_SNAPSHOT.write_text(json.dumps(sorted(i for i in ids if i)))


def summarize_connections(events) -> None:
    """connection_added events: new gene-gene edges, each referencing its
    evidence paper — the bot's headline material."""
    if not RELATIONSHIPS_JSON.exists():
        return
    edges = json.loads(RELATIONSHIPS_JSON.read_text()).get("edges", [])
    keys = {f"{e.get('from')}|{e.get('to')}|{e.get('mechanism')}" for e in edges}
    prev = set(json.loads(CONN_KEYS_SNAPSHOT.read_text())) \
        if CONN_KEYS_SNAPSHOT.exists() else None
    if prev is not None:
        papers_by_id = {}
        if PAPERS_JSON.exists():
            doc = json.loads(PAPERS_JSON.read_text())
            for p in (doc if isinstance(doc, list) else doc.get("papers", [])):
                papers_by_id[p.get("id")] = p
        fresh = [e for e in edges
                 if f"{e.get('from')}|{e.get('to')}|{e.get('mechanism')}" not in prev]
        for e in fresh[:10]:
            ev = (e.get("evidence") or [{}])[0]
            pid = ev.get("paper_id")
            paper = papers_by_id.get(pid, {})
            events.append({
                "date": TODAY, "kind": "connection_added",
                "from": e.get("from"), "to": e.get("to"),
                "label": e.get("label") or e.get("mechanism"),
                "edge_source": e.get("source"),
                "paper_id": pid,
                "paper_title": (paper.get("title") or "")[:90] or None,
                "paper_year": paper.get("year"),
                "quote": (ev.get("quote") or "")[:140] or None,
            })
        if len(fresh) > 10:
            events.append({"date": TODAY, "kind": "connections_note",
                           "count": len(fresh) - 10, "note": "more not listed"})
    CONN_KEYS_SNAPSHOT.write_text(json.dumps(sorted(keys)))


# ------------------------------------------------------------ genome sync
GENOME_COLS = ["accession", "organism_name", "organism_common_name", "taxon_id",
               "assembly_level", "contig_n50", "scaffold_n50", "total_length",
               "annotation_status", "is_representative"]


def genome_sync(events, lin: Lineage, aves_limit: int) -> int:
    if not GENOMES.exists() or not FIRST_RECORDS.exists():
        return 0
    genomes = pl.read_parquet(GENOMES)
    covered = set(genomes["taxon_id"].drop_nulls().to_list())
    have_acc = set(genomes["accession"].to_list())

    reg = json.loads(FIRST_RECORDS.read_text())["registrations"]
    # newest registrations first: today's mammals before older gaps
    reg.sort(key=lambda r: r["registered_on"], reverse=True)

    mammal_queue = [r for r in reg
                    if r.get("taxon_id") and lin.klass(r["taxon_id"]) == "Mammalia"
                    and r["taxon_id"] not in covered]
    aves_queue = [r for r in reg
                  if r.get("taxon_id") and lin.is_aves(r["taxon_id"])
                  and r["taxon_id"] not in covered]
    print(f"Genome gaps: {len(mammal_queue)} mammals (trigger: detection), "
          f"{len(aves_queue)} birds (trigger: periodic, limit {aves_limit})")

    new_rows, added_m, added_a, queries = [], 0, 0, 0
    for r in mammal_queue:  # mammals are never limited
        name = r["scientific_name"]
        print(f"  [detection] {name} ...", flush=True)
        g = ncbi_best_assembly(name)
        queries += 1
        if g and g["accession"] not in have_acc:
            new_rows.append(g); have_acc.add(g["accession"]); added_m += 1
    for r in aves_queue[:aves_limit]:
        name = r["scientific_name"]
        print(f"  [periodic ] {name} ...", flush=True)
        g = ncbi_best_assembly(name)
        queries += 1
        if g and g["accession"] not in have_acc:
            new_rows.append(g); have_acc.add(g["accession"]); added_a += 1

    for g in new_rows:
        tax = int(g["taxon_id"]) if g["taxon_id"] is not None else None
        is_aves = tax is not None and lin.is_aves(tax)
        trigger = "detection" if not is_aves else "periodic"
        events.append({
            "date": TODAY, "kind": "genome_added",
            "taxon_id": tax, "scientific_name": g["organism_name"],
            "common_name": g["organism_common_name"],
            "accession": g["accession"], "assembly_level": g["assembly_level"],
            "trigger": trigger, "is_aves": is_aves,
        })

    if new_rows:
        add = pl.DataFrame(new_rows)
        for col in GENOME_COLS:
            if col not in add.columns:
                add = add.with_columns(pl.lit(None).alias(col))
        add = add.select(GENOME_COLS)
        pl.concat([genomes, add], how="diagonal").write_parquet(GENOMES)

    print(f"  → {added_m} mammal genomes (detection), "
          f"{added_a} avian genomes (periodic), {queries} NCBI queries")
    return len(new_rows)


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Data activity log")
    ap.add_argument("--seed-previous", type=Path, default=None,
                    help="older detections parquet; first event records the real delta")
    ap.add_argument("--skip-genomes", action="store_true")
    ap.add_argument("--aves-limit", type=int, default=250,
                    help="max avian NCBI queries per run (weekly timer walks the rest)")
    ap.add_argument("--papers-only", action="store_true",
                    help="only diff papers.json / gene_relationships.json "
                         "(second invocation, after the papers pipeline)")
    args = ap.parse_args()

    lin = Lineage()
    doc = json.loads(ACTIVITY.read_text()) if ACTIVITY.exists() else {"events": []}
    events = doc.get("events", [])

    if args.papers_only:
        summarize_papers(events)
        summarize_connections(events)
        events = _finalize(doc, events)
        feed = Counter(e["kind"] for e in events if e["date"] == TODAY)
        print(f"Papers/connections pass: {len(events)} events "
              f"({dict(feed)} today) → {ACTIVITY}")
        return 0

    # ---- delta base: record_id set (v2) → exact row attribution --------
    prev_ids = None
    prev_total = None
    if SNAPSHOT.exists():
        try:
            prev_total = json.loads(SNAPSHOT.read_text()).get("total")
        except (json.JSONDecodeError, OSError):
            prev_total = None
    if IDS_SNAPSHOT.exists():
        prev_ids = set(pl.read_parquet(IDS_SNAPSHOT)["record_id"].to_list())
    elif args.seed_previous:
        prev_ids = set(pl.read_parquet(args.seed_previous,
                                       columns=["record_id"])["record_id"].to_list())
        base_total = len(prev_ids)
        # baseline informational event so the log has a beginning
        events = upsert_event(events, {
            "date": args.seed_previous.stem.split("backup_")[-1], "kind": "baseline",
            "detections": base_total, "note": "merged table, pre-canonicalization",
        })

    counts, det_event = summarize_detections(prev_ids, prev_total)
    if det_event:
        events = upsert_event(events, det_event)
    summarize_registrations(events, lin)
    if not args.skip_genomes:
        genome_sync(events, lin, aves_limit=args.aves_limit)

    # one summary event per genome batch too (feed-friendly)
    today_ga = [e for e in events
                if e["date"] == TODAY and e["kind"] == "genome_added"]
    by_trigger = Counter(e["trigger"] for e in today_ga)
    if any(by_trigger.values()):
        events = upsert_event(events, {
            "date": TODAY, "kind": "genomes_added",
            "mammal_detection": by_trigger.get("detection", 0),
            "avian_periodic": by_trigger.get("periodic", 0),
        })

    events = _finalize(doc, events)
    if counts:
        SNAPSHOT.write_text(json.dumps(counts))
    # id snapshot: current rows are next run's diff base
    pl.read_parquet(DETECTIONS, columns=["record_id"]).write_parquet(IDS_SNAPSHOT)

    feed = Counter(e["kind"] for e in events if e["date"] == TODAY)
    print(f"\nActivity log: {len(events)} events → {ACTIVITY}")
    print(f"Today: {dict(feed)}")
    return 0


def _dedupe(events):
    """Sort newest-first, drop exact-duplicate events (idempotent reruns)."""
    events = sorted(events, key=lambda e: (e["date"], e.get("kind", "")), reverse=True)
    seen, uniq = set(), []
    for e in events:
        key = json.dumps(e, sort_keys=True)
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


def _finalize(doc, events):
    """Sort, dedupe, and write both registry copies."""
    events = _dedupe(events)
    doc = {
        "description": ("Data activity: changes in Roost's data itself — "
                        "detections added, species registered, genomes added "
                        "(trigger: detection or periodic NCBI check), papers "
                        "added, and gene connections with their evidence papers. "
                        "Not a product changelog."),
        "schema_version": 2,
        "generated": TODAY,
        "events": events,
    }
    ACTIVITY.write_text(json.dumps(doc, indent=2))
    WEB_EXPORT.parent.mkdir(parents=True, exist_ok=True)
    WEB_EXPORT.write_text(json.dumps(doc, separators=(",", ":")))
    return events


if __name__ == "__main__":
    sys.exit(main())
