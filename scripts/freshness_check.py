#!/usr/bin/env python3
"""
Data freshness alerts for Roost.

A fetch can "succeed" while the data behind it has quietly gone stale (API
schema changes, dashboards stop updating, silent zero-record responses).
This check measures the actual content: the newest record date per source in
the merged detections table, plus the last successful fetch time per
registered source.

Checks:
  1. Content freshness — newest parseable date per `source` in
     data/detections_merged.parquet vs a per-source max age (days).
  2. Pipeline freshness — last successful fetch in data/.fetch_state.json
     vs 2× each source's declared update frequency.

Static/archived sources (threshold None) are reported but never flagged.

Usage:
    pixi run freshness               # exit 1 if anything is STALE
    pixi run freshness --warn-only   # report, always exit 0
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path("data")
MERGED = DATA_DIR / "detections_merged.parquet"
FETCH_STATE = DATA_DIR / ".fetch_state.json"

# Max age (days) of the newest record per merged-data source.
# None = static/archived dataset, content age is expected.
CONTENT_THRESHOLDS = {
    # APHIS wild-bird confirmations lag collection by ~2-4 weeks
    "aphis_us": ("APHIS US wild birds", 28),
    "aphis_mammals": ("APHIS US mammals", 35),        # weekly page updates; mammal confirmations lag lab turnaround
    "aphis_flocks": ("APHIS US flocks", 28),          # weekly dashboard; premises confirmations are prompt
    "uk_defra": ("UK DEFRA/APHA", 14),                # weekly reports
    "canada_cwhc": ("Canada CWHC", 120),              # dashboard lags by months (verified: newest 2026-03)
    "fao": ("FAO situation updates", 45),             # key matched case-insensitively below
    "wahis": ("WOAH WAHIS events", 60),              # newest event START lags reporting by weeks–months; harvest freshness tracked separately
    "whispers": ("USGS WHISPers events", 150),        # US mortality events; AI diagnosis appears months after the event (pending → confirmed lag)
    "sdm_hpai": ("Europe/SDM outbreaks", None),       # community archive; newest 2024-04, verify cadence
    "empresi_linked": ("EMPRES-i (archived 2012-21)", None),
    "italy_wild": ("Italy wild birds (archived)", None),
    "iceland_usgs": ("Iceland USGS (study)", None),
    "oafd_us_2022": ("OAFD 2022 (archived)", None),
}

# Multiplier on declared update frequency for fetch-pipeline staleness
FREQUENCY_MAX_AGE_DAYS = {
    "realtime": 3,
    "daily": 3,
    "weekly": 14,
    "monthly": 62,
    "quarterly": 186,
}


def parse_date(s):
    """Best-effort date parse for the mixed formats in the merged table."""
    if not s:
        return None
    s = str(s).strip()

    # ISO: 2026-08-27 (possibly with time)
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None

    # ISO week: 2026-W34-1
    m = re.match(r"^(\d{4})-W(\d{1,2})-", s)
    if m:
        try:
            year, week = int(m.group(1)), int(m.group(2))
            return date.fromisocalendar(year, week, 1)
        except ValueError:
            return None

    # Slash dates: 8/27/2026 (US M/D/Y) or 27/8/2026 (D/M/Y)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 and b <= 12:      # day first
            a, b = b, a
        try:
            return date(y, a, b) if a <= 12 else None
        except ValueError:
            return None

    return None


def content_freshness():
    """Newest record date per source in the merged detections table."""
    try:
        import polars as pl
        df = pl.read_parquet(MERGED)
    except Exception as e:
        print(f"  (cannot read {MERGED}: {e})")
        return [], []

    today = date.today()
    rows, stale = [], []

    for src in sorted(df["source"].unique().to_list()):
        label, threshold = CONTENT_THRESHOLDS.get(src.lower(), CONTENT_THRESHOLDS.get(src, (src, None)))
        dates = [parse_date(v) for v in
                 df.filter(pl.col("source") == src)["date_detected"].to_list()]
        dates = [d for d in dates if d]
        if not dates:
            rows.append((src, label, "no parseable dates", "-", threshold, "NO DATA"))
            continue
        newest = max(dates)
        age = (today - newest).days
        if threshold is None:
            status = "static"
        elif age <= threshold:
            status = "OK"
        else:
            status = "STALE"
            stale.append(src)
        rows.append((src, label, newest.isoformat(), f"{age}d", threshold, status))

    # Sources expected in content but absent from the merged table
    present = {s.lower() for s in df["source"].unique().to_list()}
    missing = [s for s in CONTENT_THRESHOLDS if s.lower() not in present]
    return rows, stale + [f"{m} (missing)" for m in missing]


def pipeline_freshness():
    """Last successful fetch per registered source vs update frequency."""
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from sources import SOURCES  # noqa: E402
    except ImportError:
        return [], []

    if not FETCH_STATE.exists():
        return [], []
    state = json.loads(FETCH_STATE.read_text())
    today = datetime.now()
    rows, stale = [], []

    for sid, src in sorted(SOURCES.items()):
        freq = src.update_frequency.value
        max_age = FREQUENCY_MAX_AGE_DAYS.get(freq)
        if max_age is None:      # static sources: no pipeline expectation
            continue
        if src.requires_auth:    # manual login sources are expected to lag
            continue
        s = state.get(sid)
        if not s or not s.get("success"):
            rows.append((sid, sid, "never succeeded", "-", max_age, "NO DATA"))
            continue
        try:
            last = datetime.fromisoformat(s["last_fetch"])
        except (ValueError, KeyError):
            continue
        age = (today - last).days
        status = "OK" if age <= max_age else "STALE"
        if status == "STALE":
            stale.append(sid)
        rows.append((sid, sid, last.strftime("%Y-%m-%d"), f"{age}d", max_age, status))

    return rows, stale


def main():
    parser = argparse.ArgumentParser(description="Roost data freshness check")
    parser.add_argument("--warn-only", action="store_true",
                        help="report without exiting non-zero on stale sources")
    args = parser.parse_args()

    print("=" * 72)
    print("FRESHNESS CHECK")
    print(f"Today: {date.today().isoformat()}")
    print("=" * 72)

    all_stale = []

    print("\nContent: newest record per source (detections_merged.parquet)")
    print("-" * 72)
    print(f"{'source':<16} {'newest':<12} {'age':<7} {'max':<6} status")
    rows, stale = content_freshness()
    all_stale += stale
    for src, label, newest, age, threshold, status in rows:
        if status == "static":
            continue  # keep the table focused on live sources
        print(f"{src:<16} {newest:<12} {age:<7} {str(threshold):<6} {status}")

    print("\nPipeline: last successful fetch vs update frequency")
    print("-" * 72)
    print(f"{'source':<20} {'last fetch':<12} {'age':<7} {'max':<6} status")
    rows, stale = pipeline_freshness()
    all_stale += stale
    for src, label, last, age, threshold, status in rows:
        print(f"{src:<20} {last:<12} {age:<7} {str(threshold):<6} {status}")

    print("-" * 72)
    if all_stale:
        print(f"⚠ STALE: {', '.join(sorted(set(s.split(' (')[0] for s in all_stale)))}")
        if not args.warn_only:
            sys.exit(1)
    else:
        print("✓ All live sources are fresh")


if __name__ == "__main__":
    main()
