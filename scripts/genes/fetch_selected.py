#!/usr/bin/env python3
"""Bounded fetch driver (D74): download ONLY the selected accessions.

Reuses fetch_genomes.fetch_genome (same download/caching semantics) without
pulling all pending manifest entries; merges statuses back into the manifest
the same way fetch_genomes.main does.
Usage: pixi run python scripts/genes/fetch_selected.py --accessions-file FILE
"""
import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "fetch_genomes", ROOT / "scripts" / "genes" / "fetch_genomes.py")
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

ap = argparse.ArgumentParser()
ap.add_argument("--accessions-file", required=True)
args = ap.parse_args()

accs = set(json.loads(Path(args.accessions_file).read_text()))
manifest_path = ROOT / "data" / "genomes" / "genomes.json"
manifest = json.loads(manifest_path.read_text())
entries = [g for g in manifest["genomes"] if g["accession"] in accs]
print(f"[fetch-selected] {len(entries)} of {len(accs)} accessions in manifest")

records = {}
for i, entry in enumerate(entries):
    rec = fg.fetch_genome(entry)
    records[entry["accession"]] = rec
    print(f"  [{i+1}/{len(entries)}] {entry['accession']} "
          f"{entry.get('common', ''):20} {rec['status']:16} "
          f"{rec.get('size_mb', 0)} MB", flush=True)

existing = {g["accession"]: g for g in json.loads(manifest_path.read_text())["genomes"]}
for acc, rec in records.items():
    existing[acc] = {**existing.get(acc, {}), **rec}
manifest_path.write_text(json.dumps({
    "set": manifest.get("set", "all"),
    "generated": date.today().isoformat(),
    "genomes": list(existing.values())}, indent=1))

ok = sum(1 for r in records.values() if r["status"] in ("ok", "cached"))
print(f"[fetch-selected] {ok}/{len(entries)} ready; manifest updated")
sys.exit(0 if ok == len(entries) else 1)
