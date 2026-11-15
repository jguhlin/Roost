#!/usr/bin/env python3
"""Bird of the Day — homepage engagement card (2026-11).

Emits web/public/data/bird_of_the_day.json: a FLAT candidate list of every
species with a sequenced genome + searched gene panel, each carrying the
per-gene status of the 18 tier-1 core-panel genes (host_panel_v2.json).
The FRONTEND picks deterministically: candidates[floor(UTCms/86400000) %
len] — same bird for every browser on the same day, cycling through all
candidates and looping. Dataset updates (new genomes/panels) change the
list length and shift the cycle; that is accepted (user decision 2026-11).

Status codes (one char per gene, aligned with genes[] order):
  P = FULL (present) · F = FRAGMENT · A = NOT_FOUND (absent) · ? = no call

Each candidate also carries up to 3 vernacular names (English first, then
non-English alternates from species_names.json) for the card's small-print
line — sci-name echoes are skipped (79 species have no real common name).

Deterministic gates (fail loudly, never ship a broken card):
  - every tier-1 symbol must exist in gene_presence.parquet
  - every candidate must have a species_index entry (id for deep-linking)
  - BIRDS ONLY: candidates restricted to species in aves_taxonomy.tsv —
    the panel also searched mammal genomes, and a mammal on the "Bird of
    the Day" card is a bug, not a curation choice (user 2026-11)

Rerun after panel/presence rebuilds and species-index exports — wired into
export_web_data.py so every web export refreshes it.

Usage: pixi run python scripts/genes/build_bird_of_the_day.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data" / "genes" / "host_panel_v2.json"
AVES_TAXONOMY = ROOT / "data" / "aves_taxonomy.tsv"
PRESENCE = ROOT / "web" / "public" / "data" / "gene_presence.parquet"
SPECIES_INDEX = ROOT / "web" / "public" / "data" / "species_index.json"
SPECIES_NAMES = ROOT / "web" / "public" / "data" / "species_names.json"
OUT = ROOT / "web" / "public" / "data" / "bird_of_the_day.json"

STATUS_CODE = {"FULL": "P", "FRAGMENT": "F", "NOT_FOUND": "A"}


def main() -> int:
    panel = json.loads(PANEL.read_text())
    t1 = [g for g in panel["genes"] if g.get("tier") == 1]
    t1.sort(key=lambda g: (g.get("category", ""), g["symbol"]))
    symbols = [g["symbol"] for g in t1]
    if len(symbols) != 18:
        print(f"FAIL: expected 18 tier-1 genes, panel has {len(symbols)}")
        return 1

    wiki_master = {}
    try:
        wiki_master = json.loads((ROOT / "data" / "aves_wikipedia.json").read_text())
    except (OSError, json.JSONDecodeError):
        pass

    t = pq.read_table(PRESENCE)
    sub = t.filter(pc.is_in(t.column("gene"), value_set=pa.array(symbols)))
    found = set(pc.unique(sub.column("gene")).to_pylist())
    missing = [s for s in symbols if s not in found]
    if missing:
        print(f"FAIL: tier-1 genes absent from gene_presence.parquet: {missing}")
        return 1

    status_by_species: dict[str, dict[str, str]] = defaultdict(dict)
    species_col = sub.column("species").to_pylist()
    gene_col = sub.column("gene").to_pylist()
    status_col = sub.column("status").to_pylist()
    for sp, gn, st in zip(species_col, gene_col, status_col):
        status_by_species[sp][gn] = STATUS_CODE.get(st, "?")

    index = {e["sci"]: e for e in json.loads(SPECIES_INDEX.read_text())}
    try:
        vernacular = json.loads(SPECIES_NAMES.read_text())
    except FileNotFoundError:
        vernacular = {}

    def names_for(sci: str, index_com: str) -> dict[str, str]:
        """Vernaculars by language code (en first, then available UI
        locales). Sci-name echoes are skipped (not real common names). The
        card renders locale-matching name + English, so an English page
        never shows a foreign name."""
        com = (vernacular.get(sci) or {}).get("com") or {}
        out: dict[str, str] = {}
        if index_com and index_com.lower() != sci.lower():
            out["en"] = index_com
        for lang in ("en", "ja", "fr", "es", "zh", "ko", "hi"):
            v = com.get(lang)
            if v and v.lower() != sci.lower() and v not in out.values():
                out.setdefault(lang, v)
        return out

    # birds only — aves_taxonomy.tsv is the authoritative species-rank list
    birds = set()
    with AVES_TAXONOMY.open() as f:
        header = f.readline().rstrip("\n").split("\t")
        sci_col = header.index("scientific_name")
        rank_col = header.index("rank")
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) > rank_col and cols[rank_col] == "species":
                birds.add(cols[sci_col])

    candidates = []
    skipped = []
    mammals = []
    for sci in sorted(status_by_species):
        entry = index.get(sci)
        if entry is None or entry.get("id") is None:
            skipped.append(sci)
            continue
        if sci not in birds:
            mammals.append(sci)
            continue
        codes = "".join(status_by_species[sci].get(s, "?") for s in symbols)
        if "?" in codes:
            skipped.append(f"{sci} (incomplete panel)")
            continue
        # Wikipedia intro + article URL (structured summaries fetch)
        wiki_out = None
        wr2 = (wiki_master or {}).get(sci)
        if wr2 and not wr2.get("missing") and wr2.get("e"):
            sents = re.split(r"(?<=[.!?])\s+", wr2["e"].strip())
            wiki_out = {"e": " ".join(sents[:2])[:400], "u": wr2.get("u") or ""}

        candidates.append({
            "i": str(entry["id"]),
            "sci": sci,
            "nm": names_for(sci, entry.get("com") or ""),
            "st": codes,
            "w": wiki_out,
        })

    if skipped:
        print(f"note: {len(skipped)} presence species without index entry skipped: "
              f"{skipped[:3]}")
    if mammals:
        print(f"note: {len(mammals)} non-avian species excluded (Bird of the Day "
              f"is birds only): {mammals[:3]}")
    if len(candidates) < 100:
        print(f"FAIL: only {len(candidates)} candidates — something is wrong upstream")
        return 1

    doc = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "genes": [{"s": g["symbol"], "n": g.get("name", ""), "c": g.get("category", "")}
                  for g in t1],
        "candidates": candidates,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    kb = OUT.stat().st_size / 1024
    n_full = sum(1 for c in candidates if "?" not in c["st"])
    print(f"bird_of_the_day.json: {len(candidates)} candidates × {len(symbols)} genes "
          f"({kb:.0f} KB, {n_full} with complete calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
