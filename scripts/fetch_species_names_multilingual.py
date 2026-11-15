#!/usr/bin/env python3
"""Fetch multilingual vernacular names (zh/hi/ja/es/ko/fr + en gap-fill)
for ALL searchable species from Wikidata.

Same channel as fetch_common_names.py (taxon item labels are the vernacular
names), extended to every UI locale. Factual data — no LLM involvement.

Writes:
  data/aves_names_multilingual.json   {sci: {lang: name}}  (checkpoint per batch)
  web/public/data/species_names.json  merged (existing LLM-reviewed entries
                                      WIN; Wikidata fills gaps + the
                                      taxonomy tail)

Usage: pixi run python scripts/fetch_species_names_multilingual.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "data" / "aves_names_multilingual.json"
INDEX = ROOT / "web" / "public" / "data" / "species_index.json"
NAMES = ROOT / "web" / "public" / "data" / "species_names.json"

SPARQL = "https://query.wikidata.org/sparql"
UA = "Roost-avian-influenza-resource/1.0 (research; contact via GitHub)"
LANGS = ("en", "zh", "hi", "ja", "es", "ko", "fr")

QUERY = """SELECT ?name ?label ?lang WHERE {{
  VALUES ?name {{ {names} }}
  ?taxon wdt:P225 ?name.
  ?taxon rdfs:label ?label.
  FILTER(LANG(?label) IN ({langs}))
  BIND(LANG(?label) AS ?lang)
}}"""


def fetch_batch(names: list[str]) -> dict[str, dict[str, str]]:
    values = " ".join(f'"{n}"' for n in names)
    q = QUERY.format(names=values, langs=", ".join(f'"{l}"' for l in LANGS))
    url = SPARQL + "?" + urllib.parse.urlencode({"query": q, "format": "json"})
    req = urllib.request.Request(url, headers={
        "Accept": "application/sparql-results+json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    out: dict[str, dict[str, str]] = {}
    for row in data["results"]["bindings"]:
        sci = row["name"]["value"]
        lang = row["lang"]["value"]
        label = row["label"]["value"].strip()
        if not label or label.startswith("Q") or "(" in label:
            continue
        # Wikidata labels for obscure taxa are often just the scientific
        # name repeated — not a vernacular; drop those.
        if label.lower() == sci.lower():
            continue
        if lang == "zh-hant" or lang == "zh-cn":  # normalize to zh
            lang = "zh"
        if lang not in LANGS:
            continue
        out.setdefault(sci, {}).setdefault(lang, label[:80])
    return out


def norm(lang: str, v: str) -> str:
    # lowercase-first for Latin-script locales, matching index style
    if lang in ("en", "es", "fr", "hi") and v and v[0].isupper():
        return v[0].lower() + v[1:]
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    index = json.loads(INDEX.read_text())
    art = json.loads(ART.read_text()) if ART.exists() else {}
    todo = sorted(set(s["sci"] for s in index if s.get("sci")) - set(art))
    if args.limit:
        todo = todo[: args.limit]
    print(f"index species: {len(index)}; artifact: {len(art)}; to query: {len(todo)}")

    for i in range(0, len(todo), args.batch):
        chunk = todo[i : i + args.batch]
        try:
            got = fetch_batch(chunk)
        except Exception as e:
            print(f"  batch {i // args.batch + 1}: {type(e).__name__}: {e} — retry once")
            time.sleep(10)
            try:
                got = fetch_batch(chunk)
            except Exception as e2:
                print(f"  batch {i // args.batch + 1}: failed twice ({e2}) — skip")
                continue
        # ensure every queried species has an entry (even empty → not re-queried)
        for sci in chunk:
            art.setdefault(sci, {})
        for sci, langs in got.items():
            for l, v in langs.items():
                art[sci][l] = norm(l, v)
        ART.write_text(json.dumps(art, indent=1, ensure_ascii=False))
        n_langs = sum(len(v) for v in got.values())
        print(f"  [{min(i + args.batch, len(todo))}/{len(todo)}] +{len(got)} species, +{n_langs} names")

    # merge into the live species_names.json (existing entries WIN)
    names = json.loads(NAMES.read_text())
    n_filled = 0
    for sci, langs in art.items():
        entry = names.setdefault(sci, {"com": {}, "aliases": []})
        com = entry.setdefault("com", {})
        for l, v in langs.items():
            if not com.get(l):
                com[l] = v
                n_filled += 1
    NAMES.write_text(json.dumps(names, indent=1, ensure_ascii=False))

    # report coverage
    by_lang = {l: 0 for l in LANGS}
    for v in names.values():
        for l in by_lang:
            if (v.get("com") or {}).get(l):
                by_lang[l] += 1
    print(f"merged {n_filled} names into species_names.json ({len(names)} species)")
    print("per-language coverage:", by_lang)


if __name__ == "__main__":
    main()
