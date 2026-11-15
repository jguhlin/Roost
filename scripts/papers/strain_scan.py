#!/usr/bin/env python3
"""
Strain dimension (D89): strain x species x gene interactions.

Scans the corpus for strain/genotype/clade tokens (known registry + novel
detection), indexes them per paper, and cross-tabulates with the mining
evidence (windows, candidates) so strain-resolved relationships and
species-specific virulence switches become visible:

  data/papers/connections/strain_index.json — paper x strain registry
  data/papers/connections/strain_species_gene.json — the triples:
    strain → species → genes co-mentioned in windows + lethality language

Known registry: clades (2.3.4.4b, 2.3.4.4h, 2.3.2.1a…), NA-genotypes
(D1.1, D1.2, D1.3, B3.13, B3.6, B3.2, B3.5, A3, G5, A1a…), subtypes
(H5N1, H5N2, H5N6, H5N8, H5N5), signature mutations (PB2-627K/E, 701N).
Novel detection: "genotype <TOKEN>" / "clade <TOKEN>" tokens not in the
registry are recorded to the strain discovery list for review.

Usage: pixi run python scripts/papers/strain_scan.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
MD_DIR = ROOT / "docs" / "papers_md"
MANIFEST = ROOT / "data" / "papers" / "corpus_manifest.json"
WINDOWS = ROOT / "data" / "papers" / "connections" / "windows.jsonl"
PAPERS = ROOT / "web" / "public" / "data" / "papers.json"
OUT_DIR = ROOT / "data" / "papers" / "connections"
OUT_INDEX = OUT_DIR / "strain_index.json"
OUT_TRIPLES = OUT_DIR / "strain_species_gene.json"

# deterministic registry
REGISTRY = {
    "clade.2.3.4.4b": r"2\.3\.4\.4b",
    "clade.2.3.4.4h": r"2\.3\.4\.4h",
    "clade.2.3.4.4": r"2\.3\.4\.4(?!b|h)",
    "clade.2.3.2.1": r"2\.3\.2\.1[a-z]?",
    "clade.7": r"\bclade 7\b",
    "genotype.D1.1": r"\bD1\.1\b",
    "genotype.D1.2": r"\bD1\.2\b",
    "genotype.D1.3": r"\bD1\.3\b",
    "genotype.B3.13": r"\bB3\.13\b",
    "genotype.B3.6": r"\bB3\.6\b",
    "genotype.B3.2": r"\bB3\.2\b",
    "genotype.B3.5": r"\bB3\.5\b",
    "genotype.A3": r"\bgenotype A3\b",
    "genotype.G5": r"\bgenotype G5\b|\bG5\b(?= genotype| reassortant)",
    "genotype.A1a": r"\bA1a\b",
    "subtype.H5N1": r"\bH5N1\b",
    "subtype.H5N2": r"\bH5N2\b",
    "subtype.H5N5": r"\bH5N5\b",
    "subtype.H5N6": r"\bH5N6\b",
    "subtype.H5N8": r"\bH5N8\b",
    "mutation.PB2-627K": r"627K|E627K",
    "mutation.PB2-627E": r"627E",
    "mutation.PB2-701N": r"701N|D701N",
    "mutation.PB2-631L": r"631L|M631L",
}
LETHALITY = re.compile(
    r"lethal|lethality|highly pathogenic|mortalit|death rate|survival|"
    r"virulen|attenuat|pathogenicity|systemic infection|fatal", re.IGNORECASE)
SPECIES = re.compile(
    r"chicken|duck|mallard|turkey|quail|geese|goose|swan|pheasant|pigeon|"
    r"cattle|bovine|dairy|human|mice|mouse|ferret|mink|cat\b|dog|seal|"
    r"swine|pig\b|fox|raptor|eagle|gull|tern|gannet|cormorant|pelican|"
    r"penguin|albatross", re.IGNORECASE)
NOVEL_GENO = re.compile(r"(?:genotype|clade)\s+([A-Z]{1,2}[0-9](?:\.[0-9])?)",
                        re.IGNORECASE)


def species_set(text):
    return {m.group(0).lower() for m in SPECIES.finditer(text)}


def main():
    manifest = json.loads(MANIFEST.read_text())
    ready = [r["paper_id"] for r in manifest["papers"] if r["status"] == "ready"]

    index = {}
    novel_counter = Counter()
    for pid in ready:
        p = MD_DIR / f"{pid}.md"
        if not p.exists():
            continue
        text = p.read_text(errors="replace").lower()
        found = [name for name, pat in REGISTRY.items()
                 if re.search(pat, text, re.IGNORECASE)]
        for m in NOVEL_GENO.finditer(text):
            token = f"novel.{m.group(1).upper()}"
            if token.replace("novel.", "") not in \
                    {n.split(".")[-1] for n in found}:
                novel_counter[f"{m.group(1).upper()}"] += 1
        if found:
            index[pid] = found

    # triples: strain x species x gene from mined windows
    windows = []
    if WINDOWS.exists():
        for line in WINDOWS.read_text().splitlines():
            try:
                windows.append(json.loads(line))
            except Exception:
                pass
    triples = defaultdict(lambda: defaultdict(lambda: Counter()))
    for w in windows:
        pid = w["paper_id"]
        strains = index.get(pid, [])
        if not strains:
            continue
        text = None
        # read the window text once
        md = MD_DIR / f"{pid}.md"
        if not md.exists():
            continue
        # cheap: use co_genes directly + paper-level species from title/abstract
        genes = set(w.get("co_genes") or []) | {w["gene"]}
        species = species_set(w.get("co_species_hint", "") or "")
        if not species:
            continue
        for strain in strains:
            for sp in species:
                for g in genes:
                    triples[strain][sp][g] += 1

    # paper-level species (title) as fallback hint source
    papers = json.loads(PAPERS.read_text())["papers"]
    title_species = {p["id"]: species_set(p.get("title", "")) for p in papers}
    for w in windows:
        pid = w["paper_id"]
        if pid in title_species and title_species[pid] and pid in index:
            genes = set(w.get("co_genes") or []) | {w["gene"]}
            for strain in index[pid]:
                for sp in title_species[pid]:
                    for g in genes:
                        triples[strain][sp][g] += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    strain_counts = Counter(s for strains in index.values() for s in strains)
    OUT_INDEX.write_text(json.dumps({
        "_doc": "papers x strain registry (deterministic scan, D89)",
        "papers_with_strains": len(index),
        "strain_counts": dict(strain_counts.most_common()),
        "novel_genotype_tokens": dict(novel_counter.most_common(20)),
    }, indent=1, ensure_ascii=False))

    OUT_TRIPLES.write_text(json.dumps({
        "_doc": ("strain x species x gene co-mention triples from mined "
                 "windows (D89). Counts are co-occurrence signals for "
                 "review, not published claims."),
        "triples": {s: {sp: dict(genes.most_common(20))
                        for sp, genes in sps.items()}
                    for s, sps in triples.items()},
    }, indent=1, ensure_ascii=False))

    print(f"strain index: {len(index)} papers with strains | "
          f"top: {strain_counts.most_common(6)}")
    print(f"novel genotype tokens (unregistered): "
          f"{novel_counter.most_common(5)}")
    print(f"strain x species x gene triples: "
          f"{sum(len(genes) for sps in triples.values() for genes in sps.values())} "
          f"gene entries across {len(triples)} strains → "
          f"{OUT_TRIPLES.name}")


if __name__ == "__main__":
    main()
