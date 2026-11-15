#!/usr/bin/env python3
"""Generate localized species names + aliases for all index species.

Output: web/public/data/species_names.json
  {sci: {"com": {"en": "...", "ko": "...", ...},
         "aliases": ["...", ...]}}

Sources:
  - English common names: species_index.json
  - Aliases: detection species_raw values (what surveillance sources call them)
  - Localized names: LLM (scientific name + English common name → 6 languages)

The site loads this once and uses it for:
  - Localized common name display (next to scientific name)
  - Search matching (any language's name finds the species)
  - Alias resolution (common search terms map to the right species)

Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python \
    scripts/papers/build_species_names.py [--dry-run]
"""
import argparse
import json
import os
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
OUT = WEB / "public" / "data" / "species_names.json"
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
LANGS = ["ko", "zh", "hi", "ja", "fr", "es"]

PROMPT = """For each bird/mammal species, provide the common name in each language.
Use the standard/well-known name a local birdwatcher or researcher would use.
For species without an established common name in a language, use an empty string "".
Return ONLY a JSON array: [{"sci": "...", "ko": "...", "zh": "...", "hi": "...",
"ja": "...", "fr": "...", "es": "..."}]
No reasoning, no commentary."""


def llm(prompt, max_tokens=8192):
    body = json.dumps({"model": MODEL, "temperature": 0.1,
                       "max_tokens": max_tokens,
                       "messages": [{"role": "system",
                                     "content": "You are a multilingual ornithology reference. "
                                                 "Translate species common names accurately. Strict JSON."},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    if not text:
        rc = (msg.get("reasoning_content") or "").strip()
        s, e = rc.find("["), rc.rfind("]")
        text = rc[s:e + 1] if 0 <= s < e else ""
    return text


def parse_arr(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("["), raw.rfind("]")
        return json.loads(raw[s:e + 1]) if 0 <= s < e else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # 1. English common names from the index
    idx = json.loads((WEB / "public/data/species_index.json").read_text())
    en_names = {r["sci"]: r.get("com", "") for r in idx}

    # 2. Aliases from detection species_raw
    d = pl.read_parquet(ROOT / "data/detections_merged.parquet").filter(
        pl.col("scientific_name").is_not_null() & pl.col("species_raw").is_not_null())
    alias_map = defaultdict(set)
    for r in d.select(["scientific_name", "species_raw"]).unique().iter_rows(named=True):
        raw = r["species_raw"].strip()
        sci = r["scientific_name"]
        if raw and raw != sci and len(raw) > 2:
            alias_map[sci].add(raw)

    # 3. Build the base table
    species = sorted(en_names.keys())
    table = {}
    for sci in species:
        table[sci] = {
            "com": {"en": en_names[sci]},
            "aliases": sorted(alias_map.get(sci, set()))[:8],
        }

    print(f"species: {len(species)} | with aliases: {sum(1 for v in table.values() if v['aliases'])}")

    # 4. LLM translation in batches of 25
    if not args.dry_run:
        translated = {}
        for i in range(0, len(species), 25):
            batch = species[i:i + 25]
            entries = [{"sci": s, "en": en_names.get(s, "")} for s in batch]
            try:
                results = parse_arr(llm(PROMPT + "\n\n" + json.dumps(entries, ensure_ascii=False)))
                for r in results:
                    if r.get("sci"):
                        translated[r["sci"]] = {lang: r.get(lang, "") for lang in LANGS}
                print(f"  {min(i + 25, len(species))}/{len(species)} "
                      f"({len(translated)} translated)", flush=True)
            except Exception as e:
                print(f"  batch {i // 25}: error {str(e)[:60]}")
            time.sleep(0.5)

        for sci, names in translated.items():
            if sci in table:
                table[sci]["com"].update(names)

    # 5. Write
    if args.dry_run:
        for sci in list(table)[:3]:
            print(f"  {sci}: {table[sci]}")
        return

    OUT.write_text(json.dumps(table, ensure_ascii=False, indent=1))
    n_named = sum(1 for v in table.values() if any(v["com"].get(l) for l in LANGS))
    print(f"species_names.json: {len(table)} species, {n_named} with translations")


if __name__ == "__main__":
    main()
