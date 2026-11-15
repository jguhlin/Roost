#!/usr/bin/env python3
"""
Scope tagging (D55): classify every paper's research scope so downstream
consumers can weight relevance without excluding anything.

Scopes:
  avian          — bird hosts (our core)
  avian-epi      — bird outbreak/spread/surveillance
  human          — human immunology/infection/clinical
  mammalian      — cattle/cats/foxes/marine mammals etc.
  vaccination    — vaccine studies (any host)
  viral-biology  — viral genetics/evolution per se
  methods        — assays/models/protocols
  mixed          — genuinely multiple

Derivation is deterministic from species_focus + title keywords (from the
D54 metadata pass) — no LLM needed. Scope is a *relevance hint*, never an
exclusion filter: human papers still feed text-scan evidence, cross-taxon
synthesis, and gene discovery.

Usage: pixi run python scripts/papers/tag_scope.py
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"

BIRD_WORDS = re.compile(r"\b(bird|avian|poultry|chicken|duck|goose|turkey|waterfowl|raptor|"
                        r"gull|tern|pelican|cormorant|swan|falcon|eagle|owl|parrot|psittac|"
                        r"passerine|songbird|shorebird|seabird|wild ?fowl|galliform|anseriform|"
                        r"strigops|apteryx|kiwi|kakapo|takahe|kea)\w*", re.I)
MAMMAL_WORDS = re.compile(r"\b(human|patient|clinical|cattle|bovine|cow|dairy|cat|feline|"
                          r"dog|canine|fox|feline|mink|mustelid|sea lion|seal|dolphin|whale|"
                          r"mouse|murine|swine|porcine|pig|ferret|macaque|primate|horse|equine)\w*", re.I)
EPI_WORDS = re.compile(r"\b(outbreak|spread|transmission|surveillance|epidemiol|incidence|"
                       r"mortality event|migration network|phylogeograph|geographic|"
                       r"panzootic|spillover)\w*", re.I)
VAX_WORDS = re.compile(r"\bvaccin\w+|\bimmunization\b", re.I)
VIRAL_WORDS = re.compile(r"\b(viral (genetic|evolution|mutation|reassortment|polymerase)|"
                         r"genome evolution|antigenic)\w*", re.I)
METHOD_WORDS = re.compile(r"\b(assay|protocol|method for|novel method|in silico pipeline)\w*", re.I)


def classify(p: dict) -> str:
    title = p.get("title") or ""
    species = " ".join(p.get("species_focus") or [])
    blob = f"{title} {species}"
    birds = bool(BIRD_WORDS.search(blob))
    mammals = bool(MAMMAL_WORDS.search(blob))
    epi = bool(EPI_WORDS.search(title))
    vax = bool(VAX_WORDS.search(blob))

    # species_focus (from LLM metadata pass) is most reliable
    sf = (p.get("species_focus") or [])
    sf_text = " ".join(sf).lower()
    sf_bird = bool(re.search(r"chicken|duck|poultry|avian|bird|turkey|gallus|anas|kiwi|kakapo|parrot|tern|gull|eagle|falcon", sf_text, re.I))
    sf_mammal = bool(re.search(r"human|patient|cattle|bovine|cat|dog|fox|mink|mouse|murine|swine|pig|ferret|macaque|sea lion|seal|dolphin", sf_text, re.I))

    if vax:
        return "vaccination"
    if sf_bird and epi:
        return "avian-epi"
    if sf_bird and not sf_mammal:
        return "avian"
    if sf_mammal and not sf_bird:
        if re.search(r"human|patient|clinical", sf_text, re.I) and not re.search(r"cattle|cat|dog|fox|mink|mouse|swine|ferret", sf_text, re.I):
            return "human"
        return "mammalian"
    if birds and not mammals:
        return "avian" if not epi else "avian-epi"
    if mammals and not birds:
        return "human" if re.search(r"human|patient|clinical", blob) else "mammalian"
    if epi:
        return "avian-epi" if birds else "epidemiology"
    if VIRAL_WORDS.search(title):
        return "viral-biology"
    if METHOD_WORDS.search(title):
        return "methods"
    return "avian" if birds else "mixed"


def main():
    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]
    n = 0
    for p in papers:
        if not p.get("scope"):
            p["scope"] = classify(p)
            n += 1
    PAPERS_JSON.write_text(json.dumps(data, indent=1))
    dist = Counter(p.get("scope") for p in papers)
    print(f"tagged {n}; distribution:")
    for scope, count in dist.most_common():
        print(f"  {scope:12s} {count}")


if __name__ == "__main__":
    main()
