#!/usr/bin/env python3
"""
Harvest WOAH WAHIS avian influenza events via the public API.

Two phases:
  1. Event list  (httpx): POST /api/v1/pi/event/filtered-list with the three
     avian-influenza disease IDs, paginated. No auth needed.
  2. Event detail (Playwright in-page fetch): GET
     /api/v1/pi/review/event/{eventId}/all-information — this route only
     returns data from a real browser context, so a headless Chromium page
     is opened once and fetch() runs inside it.

Output (data/raw/external/wahis/):
  events.json          — full event list (reportId, eventId, country, …)
  details_compact.jsonl — one compact detail per line: event header,
                          species totals (cases/deaths, wild flag),
                          outbreak location summary
  .state.json          — eventId → reportId last harvested (incremental:
                          refetch when reportId changes)

Usage:
    pixi run python scripts/fetch_wahis_events.py [--full] [--limit N]
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

OUT_DIR = Path("data/raw/external/wahis")
STATE_FILE = OUT_DIR / ".state.json"
EVENTS_FILE = OUT_DIR / "events.json"
DETAILS_FILE = OUT_DIR / "details_compact.jsonl"

BASE = "https://wahis.woah.org"
LIST_URL = f"{BASE}/api/v1/pi/event/filtered-list?language=en"
DETAIL_URL = f"{BASE}/api/v1/pi/review/event/{{event_id}}/all-information?language=en"

# Avian influenza disease IDs (from /api/v1/pi/disease/first-level-filters)
HPAI_DISEASE_IDS = [
    668,  # High pathogenicity avian influenza viruses (poultry)
    671,  # Influenza A viruses of high pathogenicity (non-poultry incl. wild birds)
    922,  # Avian influenza A viruses of high pathogenicity (bovines) (2025-)
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": BASE,
    "Referer": f"{BASE}/",
}


def fetch_event_list() -> list[dict]:
    """Phase 1: all AI events via the public filtered-list endpoint."""
    events = []
    page = 0
    with httpx.Client(timeout=120, headers=HEADERS) as client:
        while True:
            payload = {
                "eventIds": [], "reportIds": [], "countries": [],
                "firstDiseases": HPAI_DISEASE_IDS, "secondDiseases": [],
                "typeStatuses": [], "reasons": [], "eventStatuses": [],
                "reportTypes": [], "reportStatuses": [], "eventStartDate": None,
                "submissionDate": None, "animalTypes": [],
                "sortColumn": "submissionDate", "sortOrder": "desc",
                "pageSize": 500, "pageNumber": page,
            }
            resp = None
            for attempt in range(3):  # WAHIS occasionally 504s; retry
                try:
                    resp = client.post(LIST_URL, json=payload)
                    resp.raise_for_status()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code >= 500 and attempt < 2:
                        print(f"  list page {page}: {e.response.status_code}, retrying ({attempt+1}/2)...", flush=True)
                        time.sleep(3 * (attempt + 1))
                    else:
                        raise
            if resp is None:
                raise RuntimeError("unreachable")
            data = resp.json()
            batch = data.get("list", [])
            events.extend(batch)
            total = data.get("totalSize", 0)
            print(f"  list page {page}: +{len(batch)} (total {len(events)}/{total})")
            if len(events) >= total or not batch:
                break
            page += 1
            time.sleep(0.3)
    return events


def compact_detail(detail: dict) -> dict:
    """Reduce an all-information payload to what we need for ingestion."""
    ev = detail.get("event", {})
    report = detail.get("report", {})
    outbreaks = detail.get("outbreaks", []) or []
    coords = [(o.get("latitude"), o.get("longitude")) for o in outbreaks
              if isinstance(o.get("latitude"), (int, float))
              and isinstance(o.get("longitude"), (int, float))]
    return {
        "eventId": ev.get("eventId"),
        "reportId": report.get("reportId"),
        "country": (ev.get("country") or {}).get("name"),
        "country_iso": (ev.get("country") or {}).get("isoCode"),
        "disease": (ev.get("disease") or {}).get("name"),
        "subType": (ev.get("subType") or {}).get("diseaseType") or (ev.get("subType") or {}).get("subType"),
        "startedOn": (ev.get("startedOn") or "")[:10] or None,
        "confirmOn": (ev.get("confirmOn") or "")[:10] or None,
        "endedOn": (ev.get("endedOn") or "")[:10] or None,
        "eventStatus": ((ev.get("eventStatus") or {}).get("translation")),
        "reason": ((ev.get("reason") or {}).get("translation")),
        "outbreaks_count": len(outbreaks),
        "latitude": round(sum(c[0] for c in coords) / len(coords), 4) if coords else None,
        "longitude": round(sum(c[1] for c in coords) / len(coords), 4) if coords else None,
        "totals": [
            {
                "speciesName": t.get("speciesName"),
                "isWild": t.get("isWild"),
                "cases": t.get("cases"),
                "deaths": t.get("deaths"),
                "killed": t.get("killed"),
                "slaughtered": t.get("slaughtered"),
            }
            for t in (detail.get("quantitativeData", {}) or {}).get("totals", [])
            if t.get("speciesName")
        ],
    }


def fetch_details(todo: list[dict], batch_size: int = 20) -> tuple[list[dict], list[int]]:
    """Phase 2: fetch all-information inside a browser page context.

    Concurrent (Promise.all) fetches per batch; each batch is checkpointed
    immediately to DETAILS_FILE (append) and .state.json, so a timeout or
    crash loses at most one batch.
    """
    from playwright.sync_api import sync_playwright

    fetched, failed = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto(f"{BASE}/#/event-management", wait_until="domcontentloaded",
                  timeout=60000)
        page.wait_for_timeout(3000)

        for i in range(0, len(todo), batch_size):
            batch = todo[i:i + batch_size]
            specs = [{"eventId": e["eventId"], "url": DETAIL_URL.format(event_id=e["eventId"])}
                     for e in batch]
            try:
                results = page.evaluate(
                    """
                    async (specs) => {
                      const one = async (s) => {
                        try {
                          const r = await fetch(s.url, {
                            headers: {"Accept": "application/json", "type": "TOKEN", "env": "DEV"},
                            credentials: "include"
                          });
                          const text = await r.text();
                          return {eventId: s.eventId, status: r.status, body: text};
                        } catch (e) {
                          return {eventId: s.eventId, status: 0, body: String(e)};
                        }
                      };
                      return await Promise.all(specs.map(one));
                    }
                    """,
                    specs)
            except Exception as e:  # page crashed mid-batch
                print(f"\n  batch error at {i}: {e}", flush=True)
                continue

            batch_ok = []
            for res in results:
                if res["status"] == 200 and res["body"]:
                    try:
                        detail = json.loads(res["body"])
                        batch_ok.append(compact_detail(detail))
                    except json.JSONDecodeError:
                        failed.append(res["eventId"])
                else:
                    failed.append(res["eventId"])

            # checkpoint immediately
            if batch_ok:
                with open(DETAILS_FILE, "a") as f:
                    for d in batch_ok:
                        f.write(json.dumps(d) + "\n")
                fetched.extend(batch_ok)

            done = min(i + batch_size, len(todo))
            print(f"  details: {done}/{len(todo)} (failed: {len(failed)})", flush=True)
            time.sleep(0.2)

        browser.close()
    return fetched, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="refetch details even if reportId unchanged")
    parser.add_argument("--limit", type=int, default=None,
                        help="limit number of detail fetches (testing)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Phase 1: event list")
    events = fetch_event_list()
    EVENTS_FILE.write_text(json.dumps({
        "fetched_at": datetime.now().isoformat(),
        "total": len(events),
        "events": events,
    }, indent=1))
    print(f"  saved {len(events)} events → {EVENTS_FILE}")

    # incremental: refetch events whose reportId changed; also skip anything
    # already present in the JSONL store (survives crashed runs)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    known = state.get("events", {})
    stored_ids = set()
    if DETAILS_FILE.exists():
        for line in DETAILS_FILE.read_text().splitlines():
            if line.strip():
                try:
                    stored_ids.add(json.loads(line)["eventId"])
                except json.JSONDecodeError:
                    continue
    todo = [e for e in events
            if e["eventId"] not in stored_ids
            and (args.full or known.get(str(e["eventId"])) != e["reportId"])]
    if args.limit:
        todo = todo[:args.limit]
    print(f"Phase 2: event details ({len(todo)} to fetch of {len(events)}; "
          f"{len(stored_ids)} already stored)", flush=True)

    if todo:
        fetched, failed = fetch_details(todo)

        # update state for successfully fetched events
        for e in events:
            if any(d["eventId"] == e["eventId"] for d in fetched):
                known[str(e["eventId"])] = e["reportId"]
        state = {"updated": datetime.now().isoformat(), "events": known}
        STATE_FILE.write_text(json.dumps(state, indent=1))
        print(f"  fetched {len(fetched)}, failed {len(failed)}: {failed[:10]}", flush=True)
    else:
        print("  all details current", flush=True)

    print(f"  compact store: {DETAILS_FILE} "
          f"({len(DETAILS_FILE.read_text().splitlines()) if DETAILS_FILE.exists() else 0} events)")

    # Record fetch state for freshness monitoring (same format as fetch.py)
    state_path = Path("data/.fetch_state.json")
    try:
        fs = json.loads(state_path.read_text()) if state_path.exists() else {}
        fs["woah_wahis"] = {
            "last_fetch": datetime.now().isoformat(),
            "records": len(events),
            "success": True,
        }
        state_path.write_text(json.dumps(fs, indent=2, default=str))
    except OSError:
        pass


if __name__ == "__main__":
    main()
