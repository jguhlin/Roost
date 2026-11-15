#!/usr/bin/env python3
"""Fetch English common names for taxonomy-tail species from Wikidata.

The NCBI Aves taxonomy ships ~70% of species without vernacular names, and
the genome catalogue only covers its own subset — 6k+ searchable species
would otherwise show a bare scientific name in the dropdown and on pages.
Wikidata taxon items carry the English vernacular as their label
(the same channel fetch_iucn_status.py mirrors for Red List status).

Writes data/aves_common_names.json (git-tracked source artifact,
{scientific_name: common_name}) and patches the CURRENT
web/public/data/species_index.json in place so names go live immediately;
export_web_data.py merges the artifact on every future rebuild.

Usage: pixi run python scripts/fetch_common_names.py [--workers 1] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "aves_common_names.json"
INDEX = ROOT / "web" / "public" / "data" / "species_index.json"

SPARQL = "https://query.wikidata.org/sparql"
UA = "Roost-avian-influenza-resource/1.0 (research; contact via GitHub)"

QUERY = """SELECT ?name ?label WHERE {{
  VALUES ?name {{ {names} }}
  ?taxon wdt:P225 ?name.
  ?taxon rdfs:label ?label.
  FILTER(LANG(?label) = "en")
}}"""


def fetch_batch(names: list[str]) -> dict[str, str]:
    values = " ".join(f'"{n}"' for n in names)
    q = QUERY.format(names=values)
    url = SPARQL + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "Accept": "application/sparql-results+json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    out = {}
    for row in data["results"]["bindings"]:
        sci = row["name"]["value"]
        label = row["label"]["value"].strip()
        # skip disambiguation junk and Q-id fallbacks
        if not label or label.startswith("Q") or "(" in label:
            continue
        # first binding wins (deterministic order from WDQS)
        out.setdefault(sci, label[:60])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=250)
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between SPARQL batches")
    ap.add_argument("--limit", type=int, default=0, help="only first N (debug)")
    args = ap.parse_args()

    index = json.loads(INDEX.read_text())
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    unnamed = [s["sci"] for s in index if not s.get("com")]
    todo = sorted(set(unnamed) - set(existing))
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(unnamed)} unnamed in index; {len(existing)} already fetched; {len(todo)} to query")

    merged = dict(existing)
    got = 0
    for i in range(0, len(todo), args.batch):
        chunk = todo[i : i + args.batch]
        try:
            got_batch = fetch_batch(chunk)
        except Exception as e:
            print(f"  batch {i // args.batch + 1}: FAILED {type(e).__name__}: {e} — retrying once")
            time.sleep(10)
            try:
                got_batch = fetch_batch(chunk)
            except Exception as e2:
                print(f"  batch {i // args.batch + 1}: failed twice ({e2}) — skipping")
                continue
        merged.update(got_batch)
        got += len(got_batch)
        print(f"  [{min(i + args.batch, len(todo))}/{len(todo)}] +{len(got_batch)} names")
        OUT.write_text(json.dumps(merged, indent=1, ensure_ascii=False))  # checkpoint each batch
        time.sleep(args.pause)

    # lowercase-first style to match existing index conventions (chicken, kākāpō)
    merged = {k: (v[0].lower() + v[1:] if v else v) for k, v in merged.items()}
    OUT.write_text(json.dumps(merged, indent=1, ensure_ascii=False))

    # patch the live index
    n_patched = 0
    for s in index:
        if not s.get("com") and merged.get(s["sci"]):
            s["com"] = merged[s["sci"]]
            n_patched += 1
    INDEX.write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False))
    print(f"names fetched: +{got} (artifact total {len(merged)}); index patched: {n_patched}")


if __name__ == "__main__":
    main()
