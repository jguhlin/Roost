#!/usr/bin/env python3
"""
Roost data refresh — one command for the periodic update cycle.

Runs the full pipeline: fetch latest detection data from all auto sources,
refresh ArcGIS dashboards, re-ingest + deduplicate + harmonize, rebuild
profiles and susceptibility scores, export web data, rebuild wiki pages,
and rebuild + test the web app. Prints a before/after summary and logs to
data/refresh_logs/.

Usage:
    pixi run refresh                # full cycle incl. web build + tests
    pixi run refresh --skip-web     # data pipeline only
    pixi run refresh --skip-tests   # build but don't run Playwright
    pixi run refresh --papers       # also refresh paper corpus (slow, LLM)

Automation roadmap (not yet done — see ROADMAP.md "Automation" section):
  - cron/systemd timer or GitHub Actions schedule (weekly)
  - data freshness alerts (fail if newest record older than N days)
  - incremental fetch (skip unchanged sources via ETag/Last-Modified)
  - GISAID/Dryad manual-source reminders
  - auto-commit of data/ exports + deploy hook
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIR = PROJECT_ROOT / "web"
STATS = WEB_DIR / "public" / "data" / "stats.json"
LOG_DIR = PROJECT_ROOT / "data" / "refresh_logs"


def _exe(name, *fallbacks):
    """Resolve an executable even when PATH is minimal (e.g. systemd unit)."""
    found = shutil.which(name)
    if found:
        return found
    for f in fallbacks:
        if Path(f).exists():
            return f
    return name  # let subprocess raise its usual, clear FileNotFoundError


_HOME = Path.home()
# Bare names fail under systemd (no ~/.pixi/bin on PATH) — resolve explicitly.
PIXI = _exe("pixi", str(_HOME / ".pixi/bin/pixi"))
UV = _exe("uv", str(_HOME / ".pixi/bin/uv"))
NPM = _exe("npm", str(_HOME / ".volta/bin/npm"), "/usr/bin/npm")
NPX = _exe("npx", str(_HOME / ".volta/bin/npx"), "/usr/bin/npx")

# Sources safe to fetch automatically (no registration/login)
AUTO_SOURCES = [
    "aphis", "aphis_mammals", "aphis_flocks", "canada_cwhc", "europe_outbreaks",
    "uk_defra_2024", "uk_defra_2025", "uk_defra_2026",
    "acap_hpai", "owid_h5n1_human", "oafd", "empresi_linked",
    "ireland_dafm", "sa_ocims_strandings", "fao_ssa_hpai",
]

STEPS = [
    # (label, command, cwd)
    ("arcgis-refresh", [PIXI, "run", "refresh-arcgis"], PROJECT_ROOT),
    ("fetch-sources", [PIXI, "run", "fetch", *AUTO_SOURCES], PROJECT_ROOT),
    ("wahis-harvest", [PIXI, "run", "python", "scripts/fetch_wahis_events.py"], PROJECT_ROOT),
    ("wahis-supplement", [PIXI, "run", "python", "scripts/add_wahis_detections.py"], PROJECT_ROOT),
    ("whispers-harvest", [PIXI, "run", "python", "scripts/fetch_whispers_events.py"], PROJECT_ROOT),
    ("empresi-harvest", [PIXI, "run", "python", "scripts/fetch_empresi.py"], PROJECT_ROOT),
    ("fao-supplement", [PIXI, "run", "python", "scripts/add_fao_detections.py"], PROJECT_ROOT),
    ("ingest", [PIXI, "run", "ingest-detections"], PROJECT_ROOT),
    ("deduplicate", [PIXI, "run", "deduplicate"], PROJECT_ROOT),
    ("harmonize", [PIXI, "run", "harmonize-species"], PROJECT_ROOT),
    ("first-records", [PIXI, "run", "python", "scripts/species_first_records.py"], PROJECT_ROOT),
    # data activity: detection deltas + detection-triggered mammal genomes +
    # periodic avian NCBI check. BEFORE web-export (mutates data/genomes.parquet)
    ("data-activity", [PIXI, "run", "python", "scripts/data_activity.py"], PROJECT_ROOT),
    ("profiles", [PIXI, "run", "build-profiles"], PROJECT_ROOT),
    ("susceptibility", [PIXI, "run", "susceptibility"], PROJECT_ROOT),
    ("phylogeny", [PIXI, "run", "fetch-phylogeny"], PROJECT_ROOT),
    ("web-export", [PIXI, "run", "python", "scripts/export_web_data.py"], PROJECT_ROOT),
    # NOTE: export_geojson reads web/public/data/detections.parquet, so it
    # must run AFTER web-export (was previously reversed — stale aggregates)
    ("geojson", [PIXI, "run", "export-geojson"], PROJECT_ROOT),
    ("gene-data", [PIXI, "run", "python", "scripts/papers/build_gene_data.py"], PROJECT_ROOT),
    ("wiki-pages", [PIXI, "run", "python", "scripts/papers/build_wiki_pages.py"], PROJECT_ROOT),
    # second data-activity pass: papers/connections diffs need the rebuilt
    # papers.json / gene_relationships.json (idempotent upserts)
    ("data-activity-papers", [PIXI, "run", "python", "scripts/data_activity.py", "--papers-only"], PROJECT_ROOT),
]


def read_stats():
    try:
        with open(STATS) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def run(cmd, cwd, log):
    log.write(f"\n$ {' '.join(cmd)}  (cwd={cwd})\n")
    log.flush()
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    log.write(result.stdout)
    log.flush()
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Roost periodic refresh")
    parser.add_argument("--skip-web", action="store_true",
                        help="skip web build + tests (data pipeline only)")
    parser.add_argument("--skip-tests", action="store_true",
                        help="build web but skip Playwright tests")
    parser.add_argument("--papers", action="store_true",
                        help="also run the paper pipeline (search, download, LLM analysis)")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"refresh_{datetime.now():%Y%m%d_%H%M}.log"
    before = read_stats()

    print(f"Roost refresh — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"Log: {log_path}\n")

    steps = list(STEPS)
    if args.papers:
        steps.insert(1, ("papers-search",
                         [PIXI, "run", "python", "scripts/papers/search_papers.py"],
                         PROJECT_ROOT))

    failed = []
    with open(log_path, "w") as log:
        for label, cmd, cwd in steps:
            print(f"  [{label}] {' '.join(cmd[:3])}...")
            ok = run(cmd, cwd, log)
            if not ok:
                print(f"  [{label}] FAILED — see log, continuing with remaining steps")
                failed.append(label)

        if not args.skip_web:
            print("  [web-build] npm run build")
            ok = run([NPM, "run", "build"], WEB_DIR, log)
            if not ok:
                failed.append("web-build")

            if not args.skip_tests:
                print("  [web-test] playwright")
                ok = run([NPX, "playwright", "test"], WEB_DIR, log)
                if not ok:
                    failed.append("web-test")

        print("  [freshness] freshness check")
        ok = run([PIXI, "run", "freshness", "--warn-only"], PROJECT_ROOT, log)
        if not ok:
            failed.append("freshness")

        print("  [integrity] integrity check")
        ok = run([PIXI, "run", "integrity"], PROJECT_ROOT, log)
        if not ok:
            failed.append("integrity")

        # Bluesky bot: QUEUE-ONLY under automation (user 2026-11-09: not
        # ready for autonomous posting). Composes + stages to
        # state/queue.jsonl for human review; publish is manual:
        #   uv run bot.py --post-queue [--multilang]
        bot = PROJECT_ROOT / "bsky-bot" / "bot.py"
        if bot.exists():
            print("  [bsky-bot] bluesky post → QUEUE (manual review)")
            ok = run([UV, "run", "bot.py", "--queue"],
                     PROJECT_ROOT / "bsky-bot", log)
            if not ok:
                failed.append("bsky-bot")
        else:
            print("  [bsky-bot] skipped (private bot repo not present)")

    after = read_stats()

    print("\n" + "=" * 60)
    print("REFRESH SUMMARY")
    print("=" * 60)
    keys = ["detections", "species", "countries", "georeferenced",
            "genomes", "chromosome_level_genomes"]
    for k in keys:
        b, a = before.get(k), after.get(k)
        delta = "" if b in (None, a) else f"  ({a - b:+d})"
        print(f"  {k:26s} {b!s:>8} → {a!s:>8}{delta}")
    print(f"  {'generated':26s} {after.get('generated', '?')}")

    if failed:
        print(f"\n⚠ Failed steps: {', '.join(failed)} — inspect {log_path}")
        sys.exit(1)
    print(f"\n✓ All steps completed. Log: {log_path}")


if __name__ == "__main__":
    main()
