#!/usr/bin/env python3
"""Automatic EMPRES-i downloader (no more manual browser exports).

FAO's public cloud function serves the same rows as the browser export:

  https://europe-west1-fao-empresi.cloudfunctions.net/getLatestEventsByDate
      ?animal_type=all&diagnosis_status=all&disease=avian_influenza
      &start_date=YYYY-MM-DD&end_date=YYYY-MM-DD

It returns CSV with snake_case headers — same fields as the manual export,
which is capped at 15,000 rows per click. This script:

  1. reads the last download date from _download_state.json
  2. fetches month-sized chunks since then (well under any cap)
  3. merges with the previous Latest_Reported_Events_*.csv snapshot,
     deduplicating by Event ID (events are re-reported)
  4. writes a new dated snapshot in the EXACT manual-export schema —
     scripts/ingest_detections.py's load_empresi_latest() reads the
     last file sorted, so the snapshot must always be self-contained
  5. updates _download_state.json

Run:  pixi run python scripts/fetch_empresi.py [--start-date YYYY-MM-DD]
                                     [--end-date YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import time
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "raw" / "external" / "empresi-latest"
STATE = DIR / "_download_state.json"
URL = "https://europe-west1-fao-empresi.cloudfunctions.net/getLatestEventsByDate"
UA = "Roost/avian-HPAI-atlas (research website data pipeline)"

# cloud-function snake_case → manual-export Title Case
HEADER_MAP = {
    "id_event": "Event ID",
    "disease": "Disease",
    "serotype": "Serotype",
    "latitude": "latitude",
    "longitude": "longitude",
    "locality": "Locality",
    "country": "Country",
    "region": "Region",
    "observation_date": "observation date",
    "report_date": "report date",
    "species": "Species",
    "diagnosis_source": "Diagnosis Source",
    "humans_affected": "Humans Affected",
    "humans_deaths": "Human Deaths",
    "diagnosis_status": "Diagnosis Status",
}
CHUNK_ROWS_WARN = 9000   # approaching the manual export's 15k cap


def fetch_chunk(start: str, end: str) -> list[dict]:
    q = urllib.parse.urlencode({
        "animal_type": "all", "diagnosis_status": "all",
        "disease": "avian_influenza",
        "start_date": start, "end_date": end,
    })
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"{URL}?{q}",
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                text = r.read().decode("utf-8", errors="replace")
            rows = list(csv.DictReader(io.StringIO(text)))
            unknown = set(rows[0].keys()) - set(HEADER_MAP) if rows else set()
            if unknown:
                print(f"  WARN unknown API columns: {sorted(unknown)}",
                      file=sys.stderr)
            return rows
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"  attempt {attempt + 1} failed ({e}); retry in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"EMPRES-i API unreachable for {start}..{end}")


def month_chunks(start: date, end: date):
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=8)).replace(day=1) - timedelta(days=1)
        yield cur.isoformat(), min(nxt, end).isoformat()
        cur = min(nxt, end) + timedelta(days=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-date", help="override the last-download state")
    ap.add_argument("--end-date", help="default: today (UTC)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    end = date.fromisoformat(args.end_date) if args.end_date else \
        datetime.now(timezone.utc).date()
    if args.start_date:
        start = date.fromisoformat(args.start_date)
    elif state.get("downloaded"):
        start = date.fromisoformat(state["downloaded"])
    else:
        print("no prior download state — pass --start-date for a backfill",
              file=sys.stderr)
        return 1
    print(f"fetching EMPRES-i avian_influenza events "
          f"{start} → {end}", file=sys.stderr)

    # previous snapshot (pipeline reads the LAST file sorted)
    prior = sorted(DIR.glob("Latest_Reported_Events_*.csv"))
    seen: set[str] = set()
    merged: list[dict] = []
    if prior:
        with prior[-1].open() as f:
            for row in csv.DictReader(f):
                eid = (row.get("Event ID") or "").strip()
                if eid and eid not in seen:
                    seen.add(eid)
                    merged.append(row)
        print(f"  base snapshot {prior[-1].name}: {len(merged)} events",
              file=sys.stderr)

    total_new = 0
    for cs, ce in month_chunks(start, end):
        rows = fetch_chunk(cs, ce)
        new_rows = []
        for r in rows:
            out = {HEADER_MAP.get(k, k): v for k, v in r.items()}
            eid = (out.get("Event ID") or "").strip()
            if eid and eid in seen:
                continue
            if eid:
                seen.add(eid)
            new_rows.append(out)
        merged.extend(new_rows)
        total_new += len(new_rows)
        print(f"  {cs}..{ce}: {len(rows)} events, {len(new_rows)} new",
              file=sys.stderr)
        if len(rows) >= CHUNK_ROWS_WARN:
            print(f"  WARN chunk near cap ({len(rows)} rows) — verify "
                  f"completeness", file=sys.stderr)
        time.sleep(1.0)   # politeness between chunks

    print(f"total new events: {total_new}; snapshot size {len(merged)}",
          file=sys.stderr)
    if args.dry_run:
        return 0

    out_name = f"Latest_Reported_Events_{end.isoformat()}.csv"
    out_path = DIR / out_name
    fieldnames = list(HEADER_MAP.values())
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged)

    report_dates = [r.get("report date") for r in merged if r.get("report date")]
    STATE.write_text(json.dumps({
        "source": "empresi_latest",
        "downloader": "automatic — FAO cloud function "
                      "getLatestEventsByDate (scripts/fetch_empresi.py)",
        "downloaded": end.isoformat(),
        "file": out_name,
        "coverage": f"report dates {min(report_dates)} to "
                    f"{max(report_dates)}, {len(merged)} events "
                    f"(merged snapshot, deduped by Event ID)",
        "events_added": total_new,
        "note": "the manual export procedure (README) remains a fallback",
    }, indent=2))
    print(f"wrote {out_name} ({len(merged)} events) + updated state",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
