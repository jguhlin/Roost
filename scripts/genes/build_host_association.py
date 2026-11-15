#!/usr/bin/env python3
"""
Host-association layer (D84): per-gene host-class annotations derived
deterministically from existing evidence — wiki host flags, species-studied
lists, mined connection evidence species, and avian genome presence.

Classes per gene:
  aves      — evidence only in birds
  mammalia  — evidence only in mammals (incl. mammalian cell lines)
  both      — evidence in birds AND mammals
  other     — evidence only in other taxa / unclassifiable hosts
  none      — no host evidence in the corpus (never negative evidence)

Output: web/public/data/gene_host_association.json
  {GENE: {"class", "papers": {aves, mammalia, other}, "species": [...],
          "sources": [...]}}
Viral proteins keep class "viral" (they are not host genes).

Usage: pixi run python scripts/genes/build_host_association.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
WIKI = ROOT / "web" / "public" / "data" / "wiki_genes.json"
REL = ROOT / "web" / "public" / "data" / "gene_relationships.json"
PRESENCE = ROOT / "web" / "public" / "data" / "gene_catalogue.json"
CLAIMS = ROOT / "data" / "papers" / "gene_claims.jsonl"
OUT = ROOT / "web" / "public" / "data" / "gene_host_association.json"

VIRAL = {"PB2", "PB1", "PB1-F2", "PA", "PA-X", "HA", "HA1", "HA2", "NP",
         "NA", "M1", "M2", "M42", "NS1", "NS2", "NS3", "HE", "NS", "M"}

AVES = re.compile(
    r"chicken|gallus|duck|mallard|anas|turkey|meleagris|quail|goose|geese|"
    r"swan|teal|pheasant|partridge|grouse|pigeon|dove|falcon|eagle|raptor|"
    r"owl|hawk|crane|stork|heron|gull|tern|penguin|albatross|petrel|"
    r"shearwater|cormorant|gannet|booby|frigate|pelican|cormorant|kākāpō|"
    r"kakapo|kiwi|kea|takahē|takahe|weka|finch|sparrow|passerine|perch bird|"
    r"crow|raven|magpie|jay|starling|myna|parrot|psittacine|avian|bird|"
    r"poultry|waterfowl|shorebird|seabird|wader|struthio|ostrich|emu|cassowary",
    re.IGNORECASE)
MAMMALIA = re.compile(
    r"human|mouse|mice|murine|mus musculus|rat|hamster|ferret|mink|cat|feline|"
    r"dog|canine|fox|wolf|raccoon|skunk|bear|tiger|lion|seal|sea lion|fur seal|"
    r"otter|dolphin|porpoise|whale|pig|swine|porcine|boar|cattle|bovine|cow|"
    r"bison|buffalo|goat|sheep|ovine|deer|elk|moose|camel|alpaca|llama|horse|"
    r"equine|elephant|bat|shrew|hedgehog|squirrel|marmot|primate|macaque|"
    r"hek293|a549|hela|mdck|vero|293t|cellosaurus|mammal|mammalian|bovine",
    re.IGNORECASE)


def classify(text):
    """text → {'aves','mammalia','other'} bit set."""
    if not text:
        return set()
    hits = set()
    if AVES.search(text):
        hits.add("aves")
    if MAMMALIA.search(text):
        hits.add("mammalia")
    # mammalian cell lines without other mammal signal → mammalia
    if hits:
        return hits
    if re.search(r"cell|line|in vitro| vero", text, re.IGNORECASE):
        return {"other"}
    if text.strip():
        return {"other"}
    return set()


def canonical_map():
    """alias spellings -> canonical panel symbol (gene_config aliases +
    wiki_aliases): RIGI/RIG-I -> DDX58, so duplicate wiki spellings fold."""
    cfg = json.loads((ROOT / "data" / "genes" / "gene_config.json").read_text())
    m = {}
    for a, tgt in cfg.get("aliases", {}).items():
        if a != "_doc":
            m[a.upper()] = tgt
    for a, tgt in cfg.get("wiki_aliases", {}).items():
        if a != "_doc":
            m[a.upper()] = tgt
    return m


def main():
    canon = canonical_map()
    fold = lambda s: canon.get(str(s).upper(), s)
    wiki_raw = json.loads(WIKI.read_text())["genes"] if WIKI.exists() else {}
    wiki = {}
    for sym, g in wiki_raw.items():
        wiki.setdefault(fold(sym), g)
    presence = json.loads(PRESENCE.read_text())["gene_catalogue"]

    # gene → {class: paper_count}, gene → species set, gene → source tags
    cls_papers = defaultdict(Counter)
    species = defaultdict(set)
    sources = defaultdict(set)

    # 1. wiki host flags (paper-granular)
    for sym, g in wiki.items():
        if g.get("kind") == "viral" or sym in ("NS", "M"):
            continue
        if g.get("avian_papers"):
            cls_papers[sym]["aves"] += g["avian_papers"]
            sources[sym].add("wiki")
        if g.get("mammalian_papers"):
            cls_papers[sym]["mammalia"] += g["mammalian_papers"]
            sources[sym].add("wiki")
        for s in g.get("species_studied", []):
            name = s.get("name") if isinstance(s, dict) else str(s)
            if name:
                species[sym].add(name)

    # 2. species_studied classification (each species counts once per gene)
    for sym, sps in species.items():
        for name in sps:
            for c in classify(name):
                cls_papers[sym][c] += 1

    # 3. mined evidence species strings (per evidence record)
    if REL.exists():
        for e in json.loads(REL.read_text()).get("edges", []):
            for ev in e.get("evidence", []):
                sp = ev.get("species") or ""
                hits = classify(sp)
                if not hits:
                    continue
                for sym0 in (e["from"], e["to"]):
                    sym = fold(sym0)
                    if sym in VIRAL:
                        continue
                    for c in hits:
                        cls_papers[sym][c] += 1
                    sources[sym].add("mined")
                    if sp:
                        species[sym].add(sp)

    # 4. gene-claims roles sometimes name hosts ("in chickens, ...")
    if CLAIMS.exists():
        for line in CLAIMS.read_text().splitlines():
            try:
                rec = json.loads(line)
            except Exception:
                continue
            for r in rec.get("records", []):
                sym = fold(str(r.get("gene", "")).upper())
                if sym in VIRAL or sym not in presence:
                    continue
                hits = classify(r.get("role", ""))
                if hits:
                    sources[sym].add("claims")
                    for c in hits:
                        cls_papers[sym][c] += 1

    out = {}
    for sym0 in sorted(set(presence) | set(wiki) | set(cls_papers)):
        sym = fold(sym0)
        if sym in out:
            continue
        if sym in VIRAL or sym in ("NS", "M") or \
                wiki.get(sym, {}).get("kind") == "viral":
            continue
        counts = cls_papers.get(sym, Counter())
        classes = {c for c in ("aves", "mammalia", "other") if counts.get(c)}
        if "aves" in classes and "mammalia" in classes:
            klass = "both"
        elif "aves" in classes:
            klass = "aves"
        elif "mammalia" in classes:
            klass = "mammalia"
        elif "other" in classes:
            klass = "other"
        else:
            klass = "none"
        rec = {
            "class": klass,
            "papers": {c: counts.get(c, 0)
                       for c in ("aves", "mammalia", "other")},
            "species": sorted(species.get(sym, []))[:12],
        }
        if sources.get(sym):
            rec["sources"] = sorted(sources[sym])
        out[sym] = rec

    # viral proteins + wiki viral-kind entries: class viral
    viral_syms = VIRAL | {s for s, g in wiki.items()
                          if g.get("kind") == "viral"}
    for sym in sorted(viral_syms):
        out[sym] = {"class": "viral", "papers": {}, "species": []}

    tally = Counter(v["class"] for v in out.values())
    OUT.write_text(json.dumps({
        "_doc": ("Deterministic host-class associations per gene: aves / "
                 "mammalia / both / other / none (no corpus host evidence — "
                 "never negative evidence) / viral. Derived from wiki host "
                 "flags, species-studied lists, mined evidence species, and "
                 "gene-claims roles."),
        "counts": dict(tally),
        "genes": out,
    }, indent=1, ensure_ascii=False))
    print(f"→ {OUT.relative_to(ROOT)} ({len(out)} genes)")
    print("  classes:", dict(tally))


if __name__ == "__main__":
    main()
