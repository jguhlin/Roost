#!/usr/bin/env python3
"""
Fetch avian influenza detection data from external databases.

Sources:
- Canada CWHC Dashboard (ArcGIS)
- WAHIS (WOAH)
- FAO EMPRES-i

Usage:
    python scripts/fetch_external_data.py [source]

    source: canada, wahis, all (default: all)
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Try httpx first (lighter weight), fall back to requests
try:
    import httpx
    USE_HTTPX = True
except ImportError:
    import requests
    USE_HTTPX = False

DATA_DIR = Path("data/raw/external")


async def fetch_canada_arcgis():
    """
    Fetch Canada CWHC wild bird HPAI data via ArcGIS Feature Service API.

    The dashboard uses an ArcGIS feature layer that we can query directly.
    """
    print("\n" + "=" * 60)
    print("FETCHING CANADA CWHC DATA")
    print("=" * 60)

    # ArcGIS Feature Service endpoint (discovered from dashboard network requests)
    # This is the standard pattern for CFIA ArcGIS services
    base_url = "https://services5.arcgis.com/NEbzsWa1jRxC6hAm/arcgis/rest/services"

    # Try common layer names for HPAI wildlife data
    possible_services = [
        "HPAI_Wildlife_Cases/FeatureServer/0",
        "Avian_Influenza_Wildlife/FeatureServer/0",
        "Wildlife_HPAI/FeatureServer/0",
        "CFIA_HPAI_Wildlife/FeatureServer/0",
    ]

    output_dir = DATA_DIR / "canada-cwhc"
    output_dir.mkdir(parents=True, exist_ok=True)

    # First, let's try to discover the correct service
    print("  Attempting to discover ArcGIS feature service...")

    # Try a direct query approach - the dashboard HTML might reveal the service URL
    dashboard_url = "https://cfia-ncr.maps.arcgis.com/apps/dashboards/89c779e98cdf492c899df23e1c38fdbc"

    if USE_HTTPX:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get the dashboard config
            try:
                # ArcGIS dashboards often have a config endpoint
                config_url = f"https://cfia-ncr.maps.arcgis.com/sharing/rest/content/items/89c779e98cdf492c899df23e1c38fdbc/data?f=json"
                resp = await client.get(config_url)
                if resp.status_code == 200:
                    config = resp.json()
                    print(f"  Found dashboard config")

                    # Extract data source URLs from config
                    config_str = json.dumps(config)

                    # Look for feature service URLs in the config
                    import re
                    urls = re.findall(r'https://[^"]+FeatureServer/\d+', config_str)
                    if urls:
                        print(f"  Found {len(urls)} feature service URLs")
                        for url in set(urls):
                            print(f"    {url}")

                        # Try to query each feature service
                        for service_url in set(urls):
                            try:
                                query_url = f"{service_url}/query"
                                params = {
                                    "where": "1=1",
                                    "outFields": "*",
                                    "f": "geojson",
                                    "resultRecordCount": 10000
                                }
                                resp = await client.get(query_url, params=params)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    if "features" in data and len(data["features"]) > 0:
                                        # Check if this looks like wildlife HPAI data
                                        sample = data["features"][0].get("properties", {})
                                        if any(k.lower() in str(sample.keys()).lower() for k in ["species", "bird", "common_name"]):
                                            print(f"  SUCCESS: Found wildlife data with {len(data['features'])} records")

                                            # Save the data
                                            output_file = output_dir / "canada_wildlife_hpai.geojson"
                                            with open(output_file, "w") as f:
                                                json.dump(data, f)
                                            print(f"  Saved to {output_file}")

                                            # Also save as CSV
                                            import csv
                                            csv_file = output_dir / "canada_wildlife_hpai.csv"
                                            if data["features"]:
                                                fieldnames = list(data["features"][0].get("properties", {}).keys())
                                                with open(csv_file, "w", newline="") as f:
                                                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                                                    writer.writeheader()
                                                    for feat in data["features"]:
                                                        writer.writerow(feat.get("properties", {}))
                                                print(f"  Saved CSV to {csv_file}")

                                            return True
                            except Exception as e:
                                print(f"    Error querying {service_url}: {e}")
                                continue

                    # Save config for manual inspection
                    with open(output_dir / "dashboard_config.json", "w") as f:
                        json.dump(config, f, indent=2)
                    print(f"  Saved dashboard config for inspection")

            except Exception as e:
                print(f"  Error fetching dashboard config: {e}")

    print("  Could not automatically extract data. Manual download may be required.")
    print("  Dashboard URL: https://cfia-ncr.maps.arcgis.com/apps/dashboards/89c779e98cdf492c899df23e1c38fdbc")
    return False


async def fetch_wahis_data():
    """
    Fetch WAHIS avian influenza outbreak data.

    WAHIS provides disease event notifications via their public API.
    """
    print("\n" + "=" * 60)
    print("FETCHING WAHIS (WOAH) DATA")
    print("=" * 60)

    output_dir = DATA_DIR / "wahis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # WAHIS API endpoints
    # The public dashboard uses these endpoints
    base_url = "https://wahis.woah.org/api/v1"

    if USE_HTTPX:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Try to get avian influenza events
                # Disease ID 1 = Highly pathogenic avian influenza
                events_url = f"{base_url}/pi/getEventList"

                # The API requires specific headers
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                # Query parameters for HPAI in wild birds
                payload = {
                    "diseaseIdList": [1],  # HPAI
                    "reportTypeList": ["IN", "FU"],  # Immediate notifications and follow-ups
                    "animalTypeList": ["wild"],
                    "pageNumber": 1,
                    "pageSize": 1000,
                }

                print("  Querying WAHIS API for HPAI events...")
                resp = await client.post(events_url, json=payload, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    if "eventList" in data:
                        events = data["eventList"]
                        print(f"  Found {len(events)} events")

                        # Save raw data
                        output_file = output_dir / "wahis_hpai_events.json"
                        with open(output_file, "w") as f:
                            json.dump(data, f, indent=2)
                        print(f"  Saved to {output_file}")
                        return True
                    else:
                        print(f"  Unexpected response format: {list(data.keys())}")
                else:
                    print(f"  API returned status {resp.status_code}")
                    print(f"  Response: {resp.text[:500]}")

                # Try alternative public endpoint
                print("  Trying alternative WAHIS dashboard endpoint...")
                dashboard_url = "https://wahis.woah.org/api/v1/pi/dashboard/hpai"
                resp = await client.get(dashboard_url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    output_file = output_dir / "wahis_hpai_dashboard.json"
                    with open(output_file, "w") as f:
                        json.dump(data, f, indent=2)
                    print(f"  Saved dashboard data to {output_file}")
                    return True

            except Exception as e:
                print(f"  Error: {e}")

    print("  WAHIS API access may require browser automation.")
    print("  Web interface: https://wahis.woah.org/#/dashboards/qd-dashboard")
    return False


async def fetch_with_playwright():
    """
    Use Playwright to scrape data from dashboards that don't have direct API access.
    """
    print("\n" + "=" * 60)
    print("ATTEMPTING PLAYWRIGHT BROWSER AUTOMATION")
    print("=" * 60)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("  Playwright not available. Install with: pixi add playwright")
        return False

    output_dir = DATA_DIR / "canada-cwhc"
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        print("  Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Intercept network requests to find the data endpoint
        data_urls = []

        async def handle_response(response):
            url = response.url
            if "FeatureServer" in url or "query" in url:
                if response.status == 200:
                    try:
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type:
                            data_urls.append(url)
                    except:
                        pass

        page.on("response", handle_response)

        print("  Loading Canada CWHC dashboard...")
        try:
            await page.goto(
                "https://cfia-ncr.maps.arcgis.com/apps/dashboards/89c779e98cdf492c899df23e1c38fdbc",
                wait_until="networkidle",
                timeout=60000
            )
            print("  Dashboard loaded, waiting for data...")
            await asyncio.sleep(5)  # Wait for data to load

            print(f"  Captured {len(data_urls)} potential data URLs")
            for url in data_urls[:10]:
                print(f"    {url[:100]}...")

            # Save discovered URLs
            with open(output_dir / "discovered_urls.json", "w") as f:
                json.dump(data_urls, f, indent=2)

            # Try to fetch data from discovered URLs
            for url in data_urls:
                if "query" in url and "FeatureServer" in url:
                    print(f"  Attempting to fetch: {url[:80]}...")
                    try:
                        resp = await page.request.get(url)
                        if resp.status == 200:
                            data = await resp.json()
                            if "features" in data:
                                print(f"    Found {len(data['features'])} features!")

                                # Check if it's wildlife data
                                if data["features"]:
                                    sample = data["features"][0].get("properties", data["features"][0].get("attributes", {}))
                                    if sample:
                                        print(f"    Fields: {list(sample.keys())[:10]}")

                                        # Save if it looks like wildlife data
                                        output_file = output_dir / "canada_hpai_data.json"
                                        with open(output_file, "w") as f:
                                            json.dump(data, f, indent=2)
                                        print(f"    Saved to {output_file}")

                                        await browser.close()
                                        return True
                    except Exception as e:
                        print(f"    Error: {e}")
                        continue

        except Exception as e:
            print(f"  Error loading dashboard: {e}")

        await browser.close()

    return False


async def main():
    """Main entry point."""
    source = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("=" * 60)
    print("EXTERNAL DATA FETCHER")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {}

    if source in ["canada", "all"]:
        results["canada_api"] = await fetch_canada_arcgis()
        if not results["canada_api"]:
            results["canada_playwright"] = await fetch_with_playwright()

    if source in ["wahis", "all"]:
        results["wahis"] = await fetch_wahis_data()


    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results.items():
        status = "SUCCESS" if success else "NEEDS MANUAL"
        print(f"  {name}: {status}")

    return any(results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
