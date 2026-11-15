#!/usr/bin/env python3
"""Pre-build static HTML species pages for SEO + link previews.

Generates one crawlable HTML page per species at /species/{slug}.html with:
- Per-species <title> ("Cape cormorant and bird flu — Roost")
- Meta description from the insights summary
- OpenGraph tags (og:title, og:description, og:url, og:type)
- Twitter card tags
- Static facts-at-a-glance content (crawlable text)
- Canonical link to the SPA page (#/species-full/{sci})
- noscript redirect for humans who land here

Also generates sitemap.xml and robots.txt.

DESIGNED TO RE-RUN: only regenerates pages whose underlying artifact has
changed (hash comparison), cleans up stale pages for species no longer
in the index. Call after build_species_insights.py — it's part of the
export chain (pixi task: build-species-seo).

Usage: pixi run python scripts/build_species_seo.py [--force] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "public" / "data"
INSIGHTS = WEB / "species_insights"
OUT_DIR = ROOT / "web" / "public" / "species"
SITEMAP = ROOT / "web" / "public" / "sitemap.xml"
ROBOTS = ROOT / "web" / "public" / "robots.txt"

BASE_URL = "https://josephguhlin.com/Roost"
SITE_NAME = "Roost — Avian Influenza Host Genomics Resource"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">{noindex}
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="/Roost/seo.css">
<!-- OpenGraph -->
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{site_name}">
<!-- Twitter -->
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<script>location.replace('{spa_url}');</script>
</head>
<body>
<noscript>
<p><a href="{spa_url}">View the interactive page for {common_name} on Roost</a></p>
</noscript>
<main>
<h1>{common_name} <em>({sci_name})</em></h1>
{summary_html}
{facts_html}
{groups_html}
<p><a href="{spa_url}" class="cta">View the full interactive page →</a></p>
<p class="credit">Source: <a href="{base_url}">{site_name}</a>. Accessed {date}.</p>
</main>
</body>
</html>"""


def slugify(sci: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sci.lower()).strip("-")


def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_page(entry: dict, insight: dict | None) -> str:
    sci = entry["sci"]
    common = entry.get("com") or sci
    slug = slugify(sci)

    # Title and description
    if insight and insight.get("summary"):
        summary = insight["summary"]
        # First 1-2 sentences (≤160 chars for meta description)
        sentences = re.split(r"(?<=[.!?])\s+", summary)
        desc = sentences[0]
        if len(desc) < 100 and len(sentences) > 1:
            desc += " " + sentences[1]
        description = desc[:157] + "…" if len(desc) > 160 else desc
        title = f"{common} and bird flu — {SITE_NAME.split(' — ')[0]}"
        og_title = f"{common} ({sci}) — Roost"
    else:
        description = f"Gene panel, detection records, and HPAI susceptibility for {common} ({sci}) on Roost."
        title = f"{common} ({sci}) — Roost"
        og_title = title

    canonical = f"{BASE_URL}/species/{slug}.html"
    spa_url = f"{BASE_URL}/#/species-full/{sci.replace(' ', '%20')}"

    # Summary paragraph
    if insight and insight.get("summary"):
        summary_html = f'<p class="summary">{esc(insight["summary"])}</p>'
    else:
        summary_html = ""

    # Facts table
    facts_rows = []
    dh = insight.get("detection_history") if insight else None
    if dh:
        facts_rows.append(f"<tr><td>Surveillance reports</td><td>{dh['n']}</td></tr>")
        facts_rows.append(f"<tr><td>Countries</td><td>{dh['countries']}</td></tr>")
        facts_rows.append(f"<tr><td>First detected</td><td>{dh.get('first', '—')}</td></tr>")
        facts_rows.append(f"<tr><td>Most recent</td><td>{dh.get('last', '—')}</td></tr>")
    elif insight:
        facts_rows.append(f"<tr><td>HPAI detections</td><td>None recorded</td></tr>")
        if insight.get("has_genome"):
            facts_rows.append(f"<tr><td>Genome</td><td>Available (gene panel searchable)</td></tr>")
        else:
            facts_rows.append(f"<tr><td>Genome</td><td>Not sequenced</td></tr>")

    if insight and insight.get("facts", {}).get("n_detected_relatives"):
        n = insight["facts"]["n_detected_relatives"]
        order = insight["facts"].get("order", "")
        facts_rows.append(f"<tr><td>Detected {order} relatives</td><td>{n} species</td></tr>")

    facts_html = ""
    if facts_rows:
        facts_html = '<table class="facts"><tbody>' + "".join(facts_rows) + "</tbody></table>"

    # Gene groups summary
    groups_html = ""
    if insight and insight.get("groups"):
        parts = []
        for g in insight["groups"]:
            present = sum(1 for x in g["genes"] if x["status"] == "FULL")
            total = len(g["genes"])
            parts.append(f"<li>{g['label']}: {present}/{total} present</li>")
        groups_html = '<ul class="groups">' + "".join(parts) + "</ul>"

    return TEMPLATE.format(
        title=esc(title),
        description=esc(description),
        noindex="\n<meta name=\"robots\" content=\"noindex\">" if not (insight and insight.get("summary")) else "",
        canonical=canonical,
        og_title=esc(og_title),
        site_name=SITE_NAME,
        spa_url=spa_url,
        common_name=esc(common),
        sci_name=esc(sci),
        summary_html=summary_html,
        facts_html=facts_html,
        groups_html=groups_html,
        base_url=BASE_URL,
        date=time.strftime("%Y-%m-%d"),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerate all pages")
    ap.add_argument("--limit", type=int, default=0, help="only first N (debug)")
    args = ap.parse_args()

    idx = json.loads((WEB / "species_index.json").read_text())
    insights_idx = json.loads((INSIGHTS / "index.json").read_text())

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Hash file for change detection
    hash_file = OUT_DIR / ".build-hashes.json"
    old_hashes = json.loads(hash_file.read_text()) if hash_file.exists() else {}

    n_new = n_same = n_stale = 0
    urls = []
    today = time.strftime("%Y-%m-%d")

    for entry in idx:
        sci = entry.get("sci", "")
        if not sci:
            continue
        slug = slugify(sci)
        taxon_id = str(entry.get("id") or slug)

        # Load insight by taxon_id (the artifacts are keyed by taxon_id)
        insight_data = None
        insight_path = INSIGHTS / f"{taxon_id}.json"
        if insight_path.exists():
            insight_data = json.loads(insight_path.read_text())

        html = build_page(entry, insight_data)
        h = hashlib.md5(html.encode()).hexdigest()

        # Only species with insight summaries go in the sitemap (the rest
        # are noindex stubs — including them would signal thin content)
        if insight_data and insight_data.get("summary"):
            urls.append(f"{BASE_URL}/species/{slug}.html")

        out_path = OUT_DIR / f"{slug}.html"
        if not args.force and old_hashes.get(slug) == h:
            n_same += 1
            continue

        out_path.write_text(html)
        old_hashes[slug] = h
        n_new += 1

        if args.limit and n_new >= args.limit:
            break

    # Clean up stale pages (species no longer in the index)
    valid_slugs = {slugify(e["sci"]) for e in idx if e.get("sci")}
    for f in OUT_DIR.glob("*.html"):
        if f.stem not in valid_slugs:
            f.unlink()
            old_hashes.pop(f.stem, None)
            n_stale += 1

    # Save hashes
    hash_file.write_text(json.dumps(old_hashes))

    # Sitemap
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # Static pages first
    for path in ["/", "/#press", "/#numbers", "/#contradictions", "/#methods"]:
        loc = BASE_URL + ("/" if path == "/" else path)
        sitemap += f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq></url>\n"
    # Species pages
    for u in urls:
        sitemap += f"  <url><loc>{u}</loc><changefreq>monthly</changefreq></url>\n"
    sitemap += "</urlset>\n"
    SITEMAP.write_text(sitemap)

    # robots.txt
    ROBOTS.write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n"
    )

    print(f"SEO pages: {n_new} written, {n_same} unchanged, {n_stale} stale removed")
    print(f"Sitemap: {len(urls)} species URLs + 5 static pages")
    print(f"Output: {OUT_DIR} ({OUT_DIR.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
