#!/usr/bin/env python3
"""
Scrape Australian H5N1 bird flu data from agriculture.gov.au

This script uses Playwright to extract the "Events by species" table from:
https://www.agriculture.gov.au/campaigns/birdflu/latest-data

Usage:
    # Install playwright browsers first:
    playwright install chromium

    # Run the scraper:
    python scripts/scrape_aus_data.py

    # Output to specific file:
    python scripts/scrape_aus_data.py --output data/sources/aus_events.json

    # Just print the data (don't save):
    python scripts/scrape_aus_data.py --dry-run
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    exit(1)

# Realistic browser headers to avoid bot detection
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
AUS_URL = "https://www.agriculture.gov.au/campaigns/birdflu/latest-data"
AUS_STATE_FILE = DATA_DIR / "sources" / ".aus_scraper_state.json"

# Species name mapping (common name -> scientific name)
# Add mappings as we encounter new species
SPECIES_MAP = {
    "greater crested tern": "Thalasseus bergii",
    "crested tern": "Thalasseus bergii",
    "silver gull": "Chroicocephalus novaehollandiae",
    "australian pelican": "Pelecanus conspicillatus",
    "pacific gull": "Larus pacificus",
    "kelp gull": "Larus dominicanus",
    "australasian gannet": "Morus serrator",
    "black swan": "Cygnus atratus",
    "little penguin": "Eudyptula minor",
    "fairy penguin": "Eudyptula minor",
    "australian fur seal": "Arctocephalus pusillus",
    "long-nosed fur seal": "Arctocephalus forsteri",
    "new zealand fur seal": "Arctocephalus forsteri",
    "wedge-tailed shearwater": "Ardenna pacifica",
    "short-tailed shearwater": "Ardenna tenuirostris",
    "flesh-footed shearwater": "Ardenna carneipes",
    "cape barren goose": "Cereopsis novaehollandiae",
    "masked booby": "Sula dactylatra",
    "brown booby": "Sula leucogaster",
    "red-tailed tropicbird": "Phaethon rubricauda",
    "sooty tern": "Onychoprion fuscatus",
    "noddy": "Anous stolidus",  # Common noddy
    "brown noddy": "Anous stolidus",
    "black noddy": "Anous minutus",
    "white tern": "Gygis alba",
    "common tern": "Sterna hirundo",
    "caspian tern": "Hydroprogne caspia",
}


def load_scraper_state() -> dict:
    """Load the last scraper state for delta detection."""
    if AUS_STATE_FILE.exists():
        with open(AUS_STATE_FILE) as f:
            return json.load(f)
    return {"last_total_events": 0, "last_scraped_count": 0, "last_scrape_date": None}


def save_scraper_state(total_events: int, scraped_count: int):
    """Save the current scraper state."""
    state = {
        "last_total_events": total_events,
        "last_scraped_count": scraped_count,
        "last_scrape_date": datetime.now(timezone.utc).isoformat(),
    }
    AUS_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUS_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved state: {total_events} total events, {scraped_count} scraped")


def normalize_species_name(name: str) -> tuple[str, str | None]:
    """Convert common name to scientific name if known."""
    if not name:
        return name, None

    lower = name.lower().strip()

    # Check our mapping
    if lower in SPECIES_MAP:
        return name, SPECIES_MAP[lower]

    # Try partial matches
    for common, scientific in SPECIES_MAP.items():
        if common in lower or lower in common:
            return name, scientific

    return name, None


def scrape_aus_events(headless: bool = True, browser_type: str = "chromium") -> dict:
    """Scrape the Events by species table from agriculture.gov.au"""

    result = {
        "metadata": {
            "source_url": AUS_URL,
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "region": "Australia",
        },
        "events_by_species": [],
        "events_by_state": [],
        "total_events": None,
        "raw_tables": {},
    }

    browsers_to_try = [browser_type]
    if browser_type == "chromium":
        browsers_to_try.append("firefox")

    with sync_playwright() as p:
        page = None
        browser = None

        for browser_name in browsers_to_try:
            print(f"Launching {browser_name} (headless={headless})...")

            try:
                if browser_name == "firefox":
                    browser = p.firefox.launch(headless=headless)
                else:
                    browser = p.chromium.launch(headless=headless)

                # Create context with realistic browser settings
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1920, "height": 1080},
                    locale="en-AU",
                )
                page = context.new_page()

                # Intercept network requests to find JSON data endpoints
                json_responses = []

                def handle_response(response):
                    url = response.url
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type or url.endswith(".json"):
                        try:
                            if response.status == 200:
                                body = response.text()
                                if len(body) > 100:  # Ignore tiny responses
                                    json_responses.append({
                                        "url": url[:200],
                                        "size": len(body),
                                        "body": body[:5000] if len(body) < 50000 else body[:5000] + "...(truncated)"
                                    })
                                    print(f"    [JSON] {url[:80]}... ({len(body)} bytes)")
                        except:
                            pass

                page.on("response", handle_response)

                print(f"Navigating to {AUS_URL}...")
                page.goto(AUS_URL, timeout=90000, wait_until="domcontentloaded")
                print("Page loaded successfully!")

                # Store JSON responses for analysis
                result["json_endpoints"] = json_responses
                break  # Success, exit the browser loop

            except Exception as e:
                print(f"Navigation error with {browser_name}: {e}")
                if browser:
                    browser.close()
                    browser = None
                if browser_name == browsers_to_try[-1]:
                    raise  # Last browser failed, re-raise
                print(f"Trying next browser...")
                continue

        if not page:
            raise RuntimeError("Failed to load page with any browser")

        # Wait for dynamic content to load
        print("Waiting for page content...")
        page.wait_for_timeout(2000)

        # Scroll down to trigger lazy loading
        print("Scrolling to load dynamic content...")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)

        # Try to wait for tables to appear
        try:
            page.wait_for_selector("table", timeout=10000)
            print("Tables detected!")
        except:
            print("No tables found after waiting, checking for data elements...")

        # Find all tables on the page
        tables = page.query_selector_all("table")
        print(f"Found {len(tables)} tables on page")

        # If no tables, try to find data in other formats (divs, lists, etc.)
        if not tables:
            # Look for species data in any format
            print("Looking for alternative data formats...")

            # Try to find summary stats
            event_count_el = page.query_selector("text=/\\d+\\s*positive\\s*events?/i")
            if event_count_el:
                text = event_count_el.inner_text()
                print(f"Found event count text: {text}")
                # Extract the number
                match = re.search(r'(\d+)\s*positive\s*events?', text, re.IGNORECASE)
                if match:
                    result["total_events"] = int(match.group(1))

            # Look for Power BI embed or iframe
            power_bi = page.query_selector("iframe[src*='powerbi'], iframe[src*='app.powerbi']")
            if power_bi:
                print("Found Power BI embed - data is in embedded dashboard")
                result["metadata"]["note"] = "Data displayed via Power BI embed"

            # Look for any data containers
            data_sections = page.query_selector_all("[class*='data'], [class*='table'], [class*='species'], [class*='event']")
            print(f"Found {len(data_sections)} potential data sections")

            # Try to extract text data from the page for state breakdown
            # The page shows state counts like "18 in Western Australia (WA)"
            page_text = page.inner_text("body")

            # Extract state counts from text
            state_patterns = [
                (r'(\d+)\s*in\s*Western\s*Australia\s*\(WA\)', 'WA'),
                (r'(\d+)\s*in\s*South\s*Australia\s*\(SA\)', 'SA'),
                (r'(\d+)\s*in\s*New\s*South\s*Wales\s*\(NSW\)', 'NSW'),
                (r'(\d+)\s*in\s*Queensland\s*\(QLD\)', 'QLD'),
                (r'(\d+)\s*in\s*Victoria\s*\(VIC\)', 'VIC'),
                (r'(\d+)\s*in\s*Tasmania\s*\(TAS\)', 'TAS'),
            ]
            for pattern, state in state_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    count = int(match.group(1))
                    result["events_by_state"].append({"state": state, "event_count": count})
                    print(f"  Found state: {state} = {count} events")

            # Check for Power BI / Fabric iframes
            iframes = page.query_selector_all("iframe")
            print(f"Found {len(iframes)} iframes")
            for i, iframe in enumerate(iframes):
                src = iframe.get_attribute("src") or ""
                title = iframe.get_attribute("title") or ""
                print(f"  iframe {i}: title='{title}'")

                if "fabric.microsoft.com" in src or "powerbi" in src.lower():
                    result["metadata"]["powerbi_embed"] = True
                    print(f"    -> Fabric/Power BI embed detected")

                    # Try to access the iframe content
                    try:
                        frame = iframe.content_frame()
                        if frame:
                            print(f"    -> Accessing iframe content...")
                            frame.wait_for_load_state("domcontentloaded", timeout=10000)

                            # Look for table data inside the embed
                            tables = frame.query_selector_all("table, [role='grid'], [role='table'], .tableEx")
                            print(f"    -> Found {len(tables)} table-like elements in iframe")

                            # Look for any visible text data
                            rows = frame.query_selector_all("[role='row'], tr, .row")
                            print(f"    -> Found {len(rows)} row elements")

                            # Try to get all text content
                            if "Events by species" in title or "Image 3" in title:
                                # This is the events table - scroll to get ALL data
                                print(f"    -> Scrolling to load all table data...")
                                all_record_ids = set()
                                all_events = []
                                no_new_data_count = 0
                                target_count = result.get("total_events", 500)  # Use known total as target

                                # Scroll through the table - keep going until we have all events
                                for scroll_attempt in range(200):  # Up to 200 scroll attempts for large tables
                                    text_content = frame.inner_text("body")
                                    lines = [l.strip().replace('\xa0', ' ') for l in text_content.split('\n') if l.strip()]

                                    # Parse events from current view
                                    current_row = []
                                    for line in lines:
                                        if line == "Select Row":
                                            if len(current_row) >= 6:
                                                record_id = current_row[6] if len(current_row) > 6 else f"row_{len(all_events)}"
                                                if record_id not in all_record_ids:
                                                    all_record_ids.add(record_id)
                                                    event = {
                                                        "date": current_row[0],
                                                        "state": current_row[1],
                                                        "lga": current_row[2],
                                                        "locality": current_row[3],
                                                        "common_name": current_row[4],
                                                        "scientific_name": normalize_species_name(current_row[4])[1] or current_row[5],
                                                        "record_id": record_id,
                                                        "event_id": current_row[7] if len(current_row) > 7 else "",
                                                    }
                                                    all_events.append(event)
                                            current_row = []
                                        elif line not in ["Show keyboard shortcuts", "Show screen reader tips",
                                                           "Skip to main content", "Power BI Report",
                                                           "Scroll up", "Scroll down", "Scroll left", "Scroll right",
                                                           "Row Selection", "Date sampled", "Jurisdiction",
                                                           "Local government area", "Locality", "Common name",
                                                           "Scientific name", "record_id", "event_id"] and \
                                             not line.startswith("Data updated") and not line.startswith("Published"):
                                            current_row.append(line)

                                    prev_count = len(all_record_ids)

                                    # Multiple scroll strategies to ensure we get all data
                                    try:
                                        # Strategy 1: Scroll the grid/table element
                                        frame.evaluate("""
                                            const grid = document.querySelector('[role=grid], [role=table], .tableEx, .bodyCells');
                                            if (grid) {
                                                grid.scrollTop += 500;
                                            }
                                        """)
                                        frame.wait_for_timeout(400)

                                        # Strategy 2: Scroll scrollable containers
                                        frame.evaluate("""
                                            const containers = document.querySelectorAll('[style*="overflow"], .scroll-wrapper, .pivotTable');
                                            containers.forEach(c => c.scrollTop += 500);
                                        """)
                                        frame.wait_for_timeout(300)

                                        # Strategy 3: Use keyboard to scroll
                                        frame.keyboard.press("PageDown")
                                        frame.wait_for_timeout(300)

                                    except Exception as e:
                                        pass

                                    # Check if we got new data
                                    if len(all_record_ids) == prev_count:
                                        no_new_data_count += 1
                                    else:
                                        no_new_data_count = 0

                                    # Progress update every 10 scrolls
                                    if scroll_attempt % 10 == 0:
                                        print(f"      Scroll {scroll_attempt + 1}: {len(all_events)}/{target_count} events")

                                    # Stop conditions
                                    if len(all_events) >= target_count:
                                        print(f"      Reached target count!")
                                        break
                                    if no_new_data_count >= 15:  # No new data for 15 consecutive scrolls
                                        print(f"      No new data after {no_new_data_count} scrolls")
                                        break

                                result["events_by_species"] = all_events
                                print(f"    -> Parsed {len(all_events)} events from table (target: {target_count})")
                    except Exception as e:
                        print(f"    -> Could not access iframe content: {e}")

            # Try to find downloadable data links
            download_links = page.query_selector_all("a[href*='download'], a[href*='.csv'], a[href*='.xlsx'], a[href*='.json']")
            if download_links:
                print(f"Found {len(download_links)} potential download links")
                for link in download_links:
                    href = link.get_attribute("href")
                    text = link.inner_text()
                    print(f"  Download: {text} -> {href}")

        # Look for the Events by species table
        for i, table in enumerate(tables):
            # Get table caption or preceding heading
            caption = table.query_selector("caption")
            caption_text = caption.inner_text() if caption else ""

            # Try to get preceding heading
            heading = ""
            try:
                # Look for h2/h3 before table
                prev = table.evaluate("el => el.previousElementSibling?.textContent")
                if prev:
                    heading = prev.strip()
            except:
                pass

            print(f"\nTable {i+1}: caption='{caption_text}', heading='{heading}'")

            # Extract headers
            headers = []
            header_row = table.query_selector("thead tr, tr:first-child")
            if header_row:
                header_cells = header_row.query_selector_all("th, td")
                headers = [cell.inner_text().strip() for cell in header_cells]
            print(f"  Headers: {headers}")

            # Extract rows
            rows = []
            body_rows = table.query_selector_all("tbody tr, tr:not(:first-child)")
            for row in body_rows:
                cells = row.query_selector_all("td")
                if cells:
                    row_data = [cell.inner_text().strip() for cell in cells]
                    if any(row_data):  # Skip empty rows
                        rows.append(row_data)

            print(f"  Rows: {len(rows)}")

            # Store raw table data
            table_key = caption_text or heading or f"table_{i+1}"
            result["raw_tables"][table_key] = {
                "headers": headers,
                "rows": rows
            }

            # Parse Events by species table
            if "species" in caption_text.lower() or "species" in heading.lower():
                print("  -> This appears to be the Events by species table!")
                for row in rows:
                    if len(row) >= 2:
                        species_raw = row[0]
                        event_count = row[1] if len(row) > 1 else ""

                        # Try to parse count
                        try:
                            count = int(re.sub(r'[^\d]', '', event_count))
                        except:
                            count = None

                        common_name, scientific_name = normalize_species_name(species_raw)

                        event = {
                            "species_raw": species_raw,
                            "common_name": common_name,
                            "scientific_name": scientific_name,
                            "event_count": count,
                        }

                        # Add state if present
                        if len(row) > 2:
                            event["state"] = row[2]

                        result["events_by_species"].append(event)

            # Parse Events by state table
            elif "state" in caption_text.lower() or "state" in heading.lower():
                print("  -> This appears to be the Events by state table!")
                for row in rows:
                    if len(row) >= 2:
                        state = row[0]
                        count_str = row[1]
                        try:
                            count = int(re.sub(r'[^\d]', '', count_str))
                        except:
                            count = None

                        result["events_by_state"].append({
                            "state": state,
                            "event_count": count
                        })

        # Try to find total events count from page text
        try:
            page_text = page.inner_text("body")
            total_match = re.search(r'(\d+)\s*(?:confirmed\s*)?events?', page_text, re.IGNORECASE)
            if total_match:
                result["total_events"] = int(total_match.group(1))
        except:
            pass

        # Take a screenshot for debugging
        screenshot_path = DATA_DIR / "aus_scrape_debug.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"\nSaved debug screenshot to {screenshot_path}")

        browser.close()

    # Calculate totals
    if result["events_by_species"]:
        # Count individual events (each record is one event)
        result["metadata"]["species_events_total"] = len(result["events_by_species"])

    if result["events_by_state"]:
        state_total = sum(e["event_count"] or 0 for e in result["events_by_state"])
        result["metadata"]["state_events_total"] = state_total

    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape Australian H5N1 data")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--dry-run", action="store_true", help="Print data without saving")
    parser.add_argument("--show-browser", action="store_true", help="Show browser window")
    parser.add_argument("--check", action="store_true", help="Just check for new events (don't scrape all)")
    args = parser.parse_args()

    print("=" * 60)
    print("AUSTRALIAN H5N1 DATA SCRAPER")
    print("=" * 60)

    # Load previous state for delta detection
    prev_state = load_scraper_state()
    print(f"\nPrevious state: {prev_state['last_total_events']} total events, "
          f"{prev_state['last_scraped_count']} scraped")
    if prev_state['last_scrape_date']:
        print(f"Last scrape: {prev_state['last_scrape_date']}")

    # Scrape data
    data = scrape_aus_events(headless=not args.show_browser)

    # Check for new events
    current_total = data.get("total_events", 0)
    new_events = current_total - prev_state["last_total_events"]
    if new_events > 0:
        print(f"\n*** {new_events} NEW EVENTS DETECTED! ***")
    elif new_events == 0:
        print(f"\nNo new events since last scrape.")
    else:
        print(f"\nEvent count changed: {prev_state['last_total_events']} -> {current_total}")

    if args.check:
        print("\n[Check mode - not scraping full data]")
        return

    # Print summary
    print("\n" + "=" * 60)
    print("SCRAPE RESULTS")
    print("=" * 60)
    print(f"\nTotal events: {data.get('total_events', 'Unknown')}")
    print(f"Species entries: {len(data['events_by_species'])}")
    print(f"State entries: {len(data['events_by_state'])}")

    if data["events_by_species"]:
        print("\nEvents by species (sample):")
        for e in data["events_by_species"][:10]:
            sci = e.get("scientific_name") or "?"
            date = e.get("date", "")
            state = e.get("state", "")
            locality = e.get("locality", "")
            common = e.get("common_name", e.get("species_raw", "?"))
            print(f"  - {date} | {state} | {locality} | {common} ({sci})")
        if len(data["events_by_species"]) > 10:
            print(f"  ... and {len(data['events_by_species']) - 10} more")

    if data["events_by_state"]:
        print("\nEvents by state:")
        for e in data["events_by_state"]:
            print(f"  - {e['state']}: {e['event_count']} events")

    # Save output
    if not args.dry_run:
        output_path = Path(args.output) if args.output else DATA_DIR / "sources" / "aus_scraped_events.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved to {output_path}")

        # Save state for delta detection
        save_scraper_state(
            total_events=data.get("total_events", 0),
            scraped_count=len(data.get("events_by_species", []))
        )
    else:
        print("\n[Dry run - not saving]")
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
