#!/usr/bin/env python3
"""fetch_species_wikipedia.py — English Wikipedia summaries for every index
species (2026-11).

For each species in species_index.json, fetch the REST summary
(en.wikipedia.org/api/rest_v1/page/summary/<sci>) — follows synonym
redirects, returns the intro extract ("The brambling is a small passerine
bird... It has also been called..."), a one-line description and the
canonical article URL. Powers the Bird of the Day overview + Wikipedia
link-out; available for species-page overviews later.

Master: data/aves_wikipedia.json  {sci: {d, e, u} | {missing: true}}
Web twin: web/public/data/aves_wikipedia.json (same content)

Resume-safe: species already in the master (including `missing`
sentinels) are skipped; checkpoint written every 250 species. Polite:
identifying User-Agent + 60 ms delay (~15 req/s → ~13 min for 11k).

Rerun after taxonomy refreshes (new species enter the index).

Usage: pixi run python scripts/fetch_species_wikipedia.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "web" / "public" / "data" / "species_index.json"
MASTER = ROOT / "data" / "aves_wikipedia.json"
TWIN = ROOT / "web" / "public" / "data" / "aves_wikipedia.json"
API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
UA = ("Roost-avian-influenza-resource/1.0 (research; "
      "https://josephguhlin.com/Roost; joseph@josephguhlin.com)")


def fetch_one(sci: str) -> dict:
    url = API + urllib.parse.quote(sci.replace(" ", "_"))
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode())
    if d.get("type") != "standard" or not d.get("extract"):
        return {"missing": True}
    page = (d.get("content_urls", {}).get("desktop", {}) or {}).get("page")
    return {"d": d.get("description") or "", "e": d["extract"], "u": page or ""}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    species = [e["sci"] for e in json.loads(INDEX.read_text()) if e.get("sci")]
    doc = json.loads(MASTER.read_text()) if MASTER.exists() else {}

    todo = [s for s in species if s not in doc]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(species)} index species | {len(species) - len(todo)} already "
          f"fetched | {len(todo)} to go")

    n_ok = n_missing = 0
    for i, sci in enumerate(todo, 1):
        try:
            rec = fetch_one(sci)
        except Exception as e:
            print(f"  {sci}: {type(e).__name__} — will retry on next run")
            time.sleep(1)
            continue
        doc[sci] = rec
        if rec.get("missing"):
            n_missing += 1
        else:
            n_ok += 1
        if i % 250 == 0:
            MASTER.write_text(json.dumps(doc, ensure_ascii=False))
            print(f"  [{i}/{len(todo)}] ok={n_ok} missing={n_missing}")
        time.sleep(0.06)

    MASTER.write_text(json.dumps(doc, ensure_ascii=False))
    TWIN.write_text(json.dumps(doc, ensure_ascii=False))
    have = sum(1 for v in doc.values() if not v.get("missing"))
    print(f"done: {have} summaries, {n_missing} missing sentinels this run, "
          f"{len(doc)} total entries → {MASTER.name} + web twin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
