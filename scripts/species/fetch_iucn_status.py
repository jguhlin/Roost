#!/usr/bin/env python3
"""Fetch IUCN Red List conservation status for all catalogue species.

Source: Wikidata property P141 (IUCN conservation status), which mirrors the
IUCN Red List and is openly queryable via SPARQL — the official IUCN API
requires a token and GBIF's iucnRedListCategory field is no longer populated.
Names from web/public/data/species_index.json are matched against P225
(taxon name) in one batched VALUES query per chunk.

Preferred statement wins when a species carries several P141 values (historic
assessments): preferred rank first, then most recent point-in-time (P585),
then the most severe category.

Output: web/public/data/species/iucn_status.json
  { "status": { "Gallus gallus": "LC", ... },
    "meta": { source, n_species, n_matched, generated } }

Run:  pixi run python scripts/species/fetch_iucn_status.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIES_INDEX = ROOT / "web" / "public" / "data" / "species_index.json"
OUT = ROOT / "web" / "public" / "data" / "species" / "iucn_status.json"

SPARQL = "https://query.wikidata.org/sparql"
CHUNK = 120          # names per query (VALUES list)
PAUSE_S = 1.0        # politeness between chunks
UA = "Roost/avian-HPAI-atlas (research website data pipeline)"

# Wikidata IUCN category items -> IUCN code (labels used as fallback)
Q_TO_CODE = {
    "Q211005": "LC",  # least concern
    "Q11394": "NT",   # near threatened
    "Q278113": "VU",  # vulnerable
    "Q219127": "EN",  # endangered
    "Q219172": "CR",  # critically endangered
    "Q237350": "EX",  # extinct
    "Q239509": "EW",  # extinct in the wild
    "Q3244985": "DD",  # data deficient
    "Q1068438": "NT",  # lower risk / conservation dependent (legacy)
}
LABEL_PATTERNS = [  # checked in order; first match wins
    ("critically endangered", "CR"),
    ("extinct in the wild", "EW"),
    ("least concern", "LC"),
    ("near threatened", "NT"),
    ("vulnerable", "VU"),
    ("endangered", "EN"),
    ("extinct", "EX"),
    ("data deficient", "DD"),
]
SEVERITY = {"EX": 90, "EW": 85, "CR": 80, "EN": 70, "VU": 60, "NT": 50,
            "LC": 10, "DD": 0}


def qid(uri: str) -> str:
    return uri.rstrip("/").rsplit("/", 1)[-1]


def code_of(uri: str, label: str) -> str | None:
    q = qid(uri)
    if q in Q_TO_CODE:
        return Q_TO_CODE[q]
    low = label.lower()
    for pat, code in LABEL_PATTERNS:
        if pat in low:
            return code
    return None


def run_sparql(names: list[str]) -> list[dict]:
    values = " ".join(f'"{n}"' for n in names)
    query = f"""SELECT ?name ?status ?statusLabel ?rank ?date WHERE {{
  VALUES ?name {{ {values} }}
  ?item wdt:P225 ?name ; p:P141 ?st .
  ?st ps:P141 ?status .
  OPTIONAL {{ ?st wikibase:rank ?rank }}
  OPTIONAL {{ ?st pq:P585 ?date }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                SPARQL, data=body,
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            return data["results"]["bindings"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            wait = 5 * (attempt + 1)
            print(f"  attempt {attempt + 1} failed ({e}); retry in {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("SPARQL endpoint unreachable after 3 attempts")


def pick(statements: list[dict]) -> str | None:
    """Best statement: preferred rank, then latest date, then most severe."""
    def key(s):
        rank = {"http://wikiba.se/ontology#PreferredRank": 2,
                "http://wikiba.se/ontology#NormalRank": 1}.get(s.get("rank", ""), 0)
        d = s.get("date", "")
        return (rank, d, SEVERITY.get(s["code"], 0))
    cand = [s for s in statements if s["code"]]
    if not cand:
        return None
    return max(cand, key=key)["code"]


def main() -> int:
    index = json.loads(SPECIES_INDEX.read_text())
    names = sorted({s["sci"] for s in index if s.get("sci")})
    print(f"species: {len(names)}", file=sys.stderr)

    by_species: dict[str, list[dict]] = {}
    for i in range(0, len(names), CHUNK):
        chunk = names[i:i + CHUNK]
        for b in run_sparql(chunk):
            name = b["name"]["value"]
            code = code_of(b["status"]["value"], b.get("statusLabel", {}).get("value", ""))
            if code:
                by_species.setdefault(name, []).append({
                    "code": code,
                    "rank": b.get("rank", {}).get("value", ""),
                    "date": b.get("date", {}).get("value", ""),
                })
        print(f"  {min(i + CHUNK, len(names))}/{len(names)} queried "
              f"({len(by_species)} matched so far)", file=sys.stderr)
        if i + CHUNK < len(names):
            time.sleep(PAUSE_S)

    status = {name: pick(stmts) for name, stmts in by_species.items()}
    status = {k: v for k, v in status.items() if v}

    # second pass: still-unmatched names usually point at synonym items
    # (genus splits: "Astur gentilis" exists as an item but the IUCN status
    # sits on the accepted/synonym sibling). Hop one P1420 synonym step —
    # keep chunks tiny; the property path is expensive for WDQS.
    unmatched = [n for n in names if n not in status]
    if unmatched:
        print(f"  synonym-hop pass for {len(unmatched)} unmatched", file=sys.stderr)
        for i in range(0, len(unmatched), 25):
            values = " ".join(f'"{n}"' for n in unmatched[i:i + 25])
            query = f"""SELECT ?name ?status ?statusLabel WHERE {{
  VALUES ?name {{ {values} }}
  ?mine wdt:P225 ?name .
  {{ ?mine wdt:P1420 ?other . ?other wdt:P141 ?status . }}
  UNION
  {{ ?other wdt:P1420 ?mine . ?other wdt:P141 ?status . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}"""
            for attempt in range(3):
                try:
                    body = urllib.parse.urlencode(
                        {"query": query, "format": "json"}).encode()
                    req = urllib.request.Request(
                        SPARQL, data=body,
                        headers={"User-Agent": UA,
                                 "Accept": "application/sparql-results+json"})
                    with urllib.request.urlopen(req, timeout=90) as r:
                        data = json.load(r)
                    break
                except (urllib.error.URLError, TimeoutError,
                        json.JSONDecodeError) as e:
                    wait = 10 * (attempt + 1)
                    print(f"  synonym-hop attempt {attempt + 1} failed ({e}); "
                          f"retry in {wait}s", file=sys.stderr)
                    time.sleep(wait)
            else:
                continue
            for b in data["results"]["bindings"]:
                code = code_of(b["status"]["value"],
                               b.get("statusLabel", {}).get("value", ""))
                if code:
                    by_species.setdefault(b["name"]["value"], []).append(
                        {"code": code, "rank": "", "date": ""})
            if i + 25 < len(unmatched):
                time.sleep(PAUSE_S)
        for n in unmatched:
            code = pick(by_species.get(n, []))
            if code:
                status[n] = code
    out = {
        "status": status,
        "meta": {
            "source": "Wikidata P141 (IUCN Red List category mirror)",
            "sparql": SPARQL,
            "n_species": len(names),
            "n_matched": len(status),
            "generated": datetime.fromtimestamp(
                time.time(), tz=timezone.utc).isoformat(timespec="seconds"),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out))
    from collections import Counter
    dist = Counter(status.values())
    unmatched = [n for n in names if n not in status]
    print(f"wrote {OUT.name}: {len(status)}/{len(names)} matched", file=sys.stderr)
    print(f"  distribution: {dict(sorted(dist.items()))}", file=sys.stderr)
    print(f"  unmatched examples: {unmatched[:8]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
