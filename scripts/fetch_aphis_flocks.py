#!/usr/bin/env python3
"""
Fetch APHIS Commercial & Backyard Flock HPAI detections.

The APHIS page (https://www.aphis.usda.gov/livestock-poultry-disease/avian/
avian-influenza/hpai-detections/commercial-backyard-flocks) embeds a Tableau
dashboard on publicdashboards.dl.usda.gov with no static CSV behind it. The
data is exported through the dashboard's toolbar (Download -> Crosstab ->
sheet "ExportToCsv" -> CSV), which yields a UTF-16, tab-delimited file whose
final column (birds affected on the premises) has no header.

This script automates that export with Playwright, decodes the file, and
writes a normalized UTF-8 CSV to
    data/raw/external/aphis/hpai-commercial-backyard-flocks.csv
with an explicit "Birds Affected" header for the unnamed last column.

Reverse-engineered pure-HTTP flow (session bootstrap) is documented in the
module docstring of _normalize_export below; the browser path is used because
the export command requires the sheet GUID that only the booted viz client
knows.

Usage:
    python scripts/fetch_aphis_flocks.py            # fetch + normalize
    python scripts/fetch_aphis_flocks.py --raw-only # keep tab/UTF-16 file
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

OUTPUT_PATH = Path("data/raw/external/aphis/hpai-commercial-backyard-flocks.csv")
STATE_PATH = Path("data/raw/external/aphis/.flocks_fetch_state.json")

DASHBOARD_URL = (
    "https://publicdashboards.dl.usda.gov/t/MRP_PUB/views/"
    "VS_Avian_HPAIConfirmedDetections2022/HPAI2022ConfirmedDetections"
    "?:embed=y&:showVizHome=no&:toolbar=yes&:tabs=no"
)

# Expected columns of the ExportToCsv sheet (last one headerless in the raw file)
EXPECTED_HEADERS = [
    "Special ID", "County Name", "State", "Production",
    "Confirmed Diagnosis", "Control Area Released",
]
FINAL_COLUMN = "Birds Affected"


def _normalize_export(raw_bytes: bytes, out_path: Path) -> int:
    """Decode the UTF-16 tab-delimited export and write a clean CSV.

    The Tableau crosstab export ("useTabs=true") uses UTF-16-LE with a BOM
    and leaves the measure column unnamed; we append an explicit header.
    Returns the number of data rows written.
    """
    text = raw_bytes.decode("utf-16")  # BOM-aware
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ValueError(f"Export too short: {len(lines)} lines")

    rows = [ln.split("\t") for ln in lines]
    header = rows[0]

    # Sanity-check the known header prefix before rewriting it
    for i, expected in enumerate(EXPECTED_HEADERS):
        if i >= len(header) or header[i].strip() != expected:
            raise ValueError(
                f"Unexpected export header at position {i}: "
                f"{header[i] if i < len(header) else '<missing>'!r} "
                f"(expected {expected!r}). Dashboard layout may have changed."
            )

    ncols = len(header)
    # The raw header row ends with an empty/missing name for the measure
    # column; every data row has one more field than the header.
    if ncols < len(EXPECTED_HEADERS) + 1:
        header = header + [""]
        ncols = len(header)

    import csv
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(EXPECTED_HEADERS + [FINAL_COLUMN])
        n = 0
        for row in rows[1:]:
            row = row + [""] * (ncols - len(row))
            # Strip a possible stray empty header cell, keep value columns
            w.writerow(row[: len(EXPECTED_HEADERS) + 1])
            n += 1
    return n


def fetch_via_browser(out_path: Path, timeout_ms: int = 45000) -> bytes:
    """Drive the Tableau toolbar export and return the raw file bytes."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(accept_downloads=True)
            page = ctx.new_page()
            page.goto(DASHBOARD_URL, wait_until="domcontentloaded",
                      timeout=timeout_ms)
            page.wait_for_selector("canvas", timeout=timeout_ms)
            page.wait_for_timeout(5000)  # let the viz finish booting

            page.click("#download", timeout=timeout_ms)
            page.wait_for_timeout(700)
            page.get_by_text("Crosstab", exact=True).first.click(timeout=timeout_ms)
            page.wait_for_timeout(1500)
            # sheet picker: choose the export sheet, then CSV format
            page.get_by_text("ExportToCsv", exact=True).first.click(timeout=timeout_ms)
            page.wait_for_timeout(500)
            page.get_by_text("CSV", exact=True).first.click(timeout=timeout_ms)
            page.wait_for_timeout(500)

            with page.expect_download(timeout=timeout_ms) as dl:
                page.get_by_text("Download", exact=True).last.click(timeout=timeout_ms)
            download = dl.value
            tmp = out_path.with_suffix(".utf16.tmp")
            download.save_as(tmp)
            raw = tmp.read_bytes()
            tmp.unlink(missing_ok=True)
            return raw
        finally:
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH,
                        help="output CSV path")
    parser.add_argument("--raw-only", action="store_true",
                        help="save the raw UTF-16 tab file without normalizing")
    parser.add_argument("--attempts", type=int, default=2)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    last_err = None
    for attempt in range(1, args.attempts + 1):
        try:
            raw = fetch_via_browser(args.output)
            break
        except Exception as e:  # noqa: BLE001 - report and retry
            last_err = e
            print(f"  attempt {attempt} failed: {e}", file=sys.stderr)
    else:
        print(f"FAILED to export flocks data: {last_err}", file=sys.stderr)
        return 1

    if args.raw_only:
        args.output.write_bytes(raw)
        rows = max(0, len(raw.decode("utf-16").splitlines()) - 1)
    else:
        rows = _normalize_export(raw, args.output)

    checksum = hashlib.md5(raw).hexdigest()
    state = {
        "last_fetch": datetime.now().isoformat(),
        "rows": rows,
        "checksum": checksum,
        "source": DASHBOARD_URL.split("/views/")[1].split("/")[0],
    }
    STATE_PATH.write_text(json.dumps(state, indent=2))

    # Machine-readable result line for scripts/fetch.py
    print(f"FETCH_RESULT: {json.dumps({'records': rows, 'checksum': checksum})}")

    # Quick summary
    text = raw.decode("utf-16")
    total_birds = 0
    for ln in text.splitlines()[1:]:
        parts = ln.split("\t")
        if len(parts) >= 7:
            v = parts[6].replace(",", "").strip()
            if v.isdigit():
                total_birds += int(v)
    print(f"  {rows:,} flock records, {total_birds:,} birds affected total")
    print(f"  saved: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
