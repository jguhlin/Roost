#!/usr/bin/env python3
"""Discover best-available NCBI assemblies for corpus species without genomes.

For each avian wiki species (>=2 corpus papers) lacking a genome in
data/genomes/genomes.json, resolve its scientific name and pick the best
assembly: RefSeq > Chromosome > Scaffold level, newest release.

Writes data/genomes/candidate_species.json (sorted by corpus paper_count) —
NOT the manifest; review then extend genomes.json via extend_genomes.py.

Usage: pixi run python scripts/genes/discover_assemblies.py
"""

import json
import subprocess
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENOME_DIR = ROOT / "data" / "genomes"
MANIFEST = GENOME_DIR / "genomes.json"
CANDIDATES = GENOME_DIR / "candidate_species.json"

# common-name fixes for species whose wiki scientific_name is missing/generic
NAME_FIXES = {
    "goose": "Anser cygnoidus domesticus",
    "domestic goose": "Anser anser domesticus",
    "Domestic goose": "Anser anser domesticus",
    "Domestic duck": "Anas platyrhynchos domesticus",
    "domestic duck": "Anas platyrhynchos domesticus",
    "quail": "Coturnix japonica",
    "whooper swan": "Cygnus cygnus",
    "Swan": "Cygnus olor",
    "swan": "Cygnus olor",
    "Common Eider": "Somateria mollissima",
    "pigeon": "Columba livia",
    "Mute swan": "Cygnus olor",
    "Black-headed gull": "Chroicocephalus ridibundus",
}

# skip: domestic variants whose assemblies duplicate the wild species we
# already have or will fetch
SKIP_SCI = {
    "Anas platyrhynchos domesticus",  # same species as Pekin duck (have)
    "Gallus gallus domesticus",       # chicken (have)
}


def datasets_summary(taxon: str) -> list[dict]:
    r = subprocess.run(
        ["pixi", "run", "datasets", "summary", "genome", "taxon", taxon,
         "--as-json-lines"],
        capture_output=True, text=True, timeout=180,
    )
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def best_assembly(records: list[dict]) -> dict | None:
    best, best_score = None, None
    for d in records:
        ai = d.get("assembly_info", {})
        acc = d.get("accession", "")
        if not acc:
            continue
        level = ai.get("assembly_level", "")
        rec = {
            "accession": acc,
            "assembly_level": level,
            "refseq": acc.startswith("GCF"),
            "release_date": (ai.get("release_date") or "")[:10],
            "size_mb": round(ai.get("total_sequence_length", 0) / 1e6),
            "annotated": bool(d.get("annotation_info", {}).get("release_name")),
            "organism": (ai.get("biosample") or {}).get("organism", {}).get("organism_name", "")
                        or d.get("organism", {}).get("organism_name", ""),
        }
        score = (
            rec["refseq"], level == "Chromosome", level == "Scaffold",
            rec["annotated"], rec["release_date"],
        )
        if best_score is None or score > best_score:
            best, best_score = rec, score
    return best


def main() -> None:
    wiki = json.loads((ROOT / "web" / "public" / "data" / "wiki_species.json").read_text())["species"]
    manifest = json.loads(MANIFEST.read_text())["genomes"]
    have_sci = {g["species"] for g in manifest}
    have_acc = {g["accession"] for g in manifest}

    # avian, >=2 papers, not already covered
    seen_sci: set[str] = set()
    todo = []
    for s, v in sorted(wiki.items(), key=lambda kv: -(kv[1].get("paper_count") or 0)):
        if v.get("avian") is not True or (v.get("paper_count") or 0) < 2:
            continue
        sci = v.get("scientific_name") or NAME_FIXES.get(s) or ""
        if not sci or sci in seen_sci or sci in have_sci or sci in SKIP_SCI:
            continue
        seen_sci.add(sci)
        todo.append({"common": s, "scientific_name": sci,
                     "paper_count": v.get("paper_count", 0)})

    print(f"species to query: {len(todo)}")
    results = []
    for i, t in enumerate(todo):
        recs = datasets_summary(t["scientific_name"])
        best = best_assembly(recs)
        if best and best["accession"] not in have_acc:
            best.update({"common": t["common"], "papers": t["paper_count"]})
            results.append(best)
            flag = "chr" if best["assembly_level"] == "Chromosome" else best["assembly_level"][:4]
            print(f"  [{i+1}/{len(todo)}] {t['scientific_name'][:34]:36s} "
                  f"{best['accession']:16s} {flag:5s} {best['size_mb']:6d} MB "
                  f"({t['paper_count']} papers)", flush=True)
        else:
            print(f"  [{i+1}/{len(todo)}] {t['scientific_name'][:34]:36s} "
                  f"{'— no assembly / dup' if best else '— none'}", flush=True)
        time.sleep(0.6)
        # checkpoint so a late failure never loses the sweep
        if (i + 1) % 10 == 0:
            CANDIDATES.write_text(json.dumps(
                {"generated": date.today().isoformat(), "partial": True,
                 "candidates": sorted(results, key=lambda r: (-r["papers"], not r["refseq"]))},
                indent=1))

    results.sort(key=lambda r: (-r["papers"], not r["refseq"]))
    CANDIDATES.write_text(json.dumps(
        {"generated": date.today().isoformat(),
         "candidates": results}, indent=1))
    chrom = sum(1 for r in results if r["assembly_level"] == "Chromosome")
    print(f"\n{len(results)} candidate assemblies ({chrom} chromosome-level) "
          f"→ {CANDIDATES.name}")
    print(f"estimated download: {sum(r['size_mb'] for r in results)/1000:.0f} GB")


if __name__ == "__main__":
    main()
