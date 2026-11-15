#!/usr/bin/env python3
"""
Harvest USGS WHISPers avian influenza events and build a supplement.

WHISPers (Wildlife Health Information Sharing Partnership) is the USGS
mortality-event reporting system: confirmed-lab-diagnosis events with
species (incl. latin names + TSN), affected counts, dates, county/state.

API (public, JSON): https://whispers.usgs.gov/api/eventsummaries/?diagnosis={id}
HPAI diagnosis IDs (from /api/diagnoses/):
  22=HPAI (NOS), 660=H5N1, 661=H5N2, 662=H5N8, 685=H5, 692=H7N3

Output: data/manual/whispers_detections.json (source=WHISPERS) — loaded by
ingest_detections.py as a manual supplement.

Usage: pixi run python scripts/fetch_whispers_events.py
"""

import json
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOST_DIR = Path(__file__).parent.parent
OUT_PATH = ROOST_DIR / "data" / "manual" / "whispers_detections.json"
STATE_PATH = ROOST_DIR / "data" / "raw" / "external" / "whispers" / ".state.json"

BASE = "https://whispers.usgs.gov/api/eventsummaries/"

AI_DIAGNOSES = {
    22: "HPAI",
    660: "H5N1",
    661: "H5N2",
    662: "H5N8",
    685: "H5",
    692: "H7N3",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Roost/0.1"}


def fetch_events(client: httpx.Client) -> dict[int, dict]:
    """All AI events keyed by id (first diagnosis wins for strain)."""
    by_id: dict[int, dict] = {}
    for did, strain in AI_DIAGNOSES.items():
        url = BASE
        params = {"format": "json", "limit": 100, "diagnosis": did}
        pages = 0
        while url:
            for attempt in range(3):
                try:
                    r = client.get(url, params=params)
                    r.raise_for_status()
                    data = r.json()
                    break
                except (httpx.HTTPError, ValueError) as e:
                    if attempt == 2:
                        raise
                    print(f"  retry after error: {e}", flush=True)
                    time.sleep(2 * (attempt + 1))
            for ev in data.get("results", []):
                eid = ev["id"]
                if eid not in by_id:
                    ev["_strain"] = strain
                    by_id[eid] = ev
            pages += 1
            url = data.get("next")
            params = None
            time.sleep(0.15)
        print(f"  diagnosis {did} ({strain}): {pages} page(s), cumulative {len(by_id)} events", flush=True)
    return by_id


def build_records(events: dict[int, dict]) -> list[dict]:
    records = []
    for eid, ev in sorted(events.items()):
        start = (ev.get("start_date") or "")[:10] or None
        if not start:
            continue
        admin1 = ev.get("administrativelevelones") or []
        admin2 = ev.get("administrativeleveltwos") or []
        state = admin1[0]["name"] if admin1 else None
        county = admin2[0]["name"] if admin2 else None
        affected = ev.get("affected_count")
        for sp in ev.get("species") or []:
            genus = (sp.get("genus_name") or "").strip()
            latin = (sp.get("species_latin_name") or "").strip()
            sci = f"{genus} {latin}" if genus and latin and latin not in ("sp.",) else None
            name = sp.get("name") or ""
            if not name and not sci:
                continue
            records.append({
                "species_raw": name or sci,
                "scientific_name_parsed": sci,
                "date_detected": start,
                "country": "USA",
                "state": state,
                "county": county,
                "strain": ev["_strain"],
                "sampling_method_raw": f"WHISPers event {eid} (lab-confirmed mortality event)",
                "sampling_type": "mortality",
                "source_file": f"whispers_event_{eid}",
                "detection_count": affected or 1,
                "latitude": None,
                "longitude": None,
            })
    return records


def main():
    with httpx.Client(timeout=60, headers=HEADERS, follow_redirects=True) as client:
        events = fetch_events(client)
    records = build_records(events)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "source": "WHISPERS",
        "description": "USGS WHISPers lab-confirmed HPAI wildlife mortality events (US)",
        "records": records,
    }, indent=1))

    mapped = sum(1 for r in records if r["scientific_name_parsed"])
    states = len({r["state"] for r in records if r["state"]})
    print(f"\nWrote {len(records)} WHISPERS records "
          f"({len(events)} events, {states} states) → {OUT_PATH}")
    print(f"  species with scientific names: {mapped}/{len(records)}")

    # fetch state for freshness monitoring
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({
        "updated": datetime.now().isoformat(), "events": len(events),
    }, indent=1))
    state_path = ROOST_DIR / "data" / ".fetch_state.json"
    try:
        fs = json.loads(state_path.read_text()) if state_path.exists() else {}
        fs["usgs_whispers"] = {
            "last_fetch": datetime.now().isoformat(),
            "records": len(records),
            "success": True,
        }
        state_path.write_text(json.dumps(fs, indent=2, default=str))
    except OSError:
        pass


if __name__ == "__main__":
    main()
