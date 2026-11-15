#!/usr/bin/env python3
"""
Download the ImmunomeDB dataset (363 B10K species, frozen ~2020).

Grabs from gitlab.com/rcmueller/immunomedb (branch: master):
  - setup/data/Sample_sheet_363genomes_short_name.txt  (species code → name)
  - setup/data/b10k_annotation/*_immune.gff.gz          (immune gene GFFs)
  - setup/data/b10k_assembly/*_immune.fa.gz             (immune gene sequences)
  - setup/sql/*.sql, setup/py/*                         (schema + parsers)

See GENE_PRESENCE_LOG.md D14 for the vintage caveat.

Usage: pixi run python scripts/genes/fetch_immunomedb.py [--gffs-only]
"""

import argparse
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
OUT = ROOT / "data" / "genes" / "immunomedb"
PID = "rcmueller%2Fimmunomedb"
REF = "master"


def download(client, path: str, dest: Path) -> bool:
    url = (f"https://gitlab.com/api/v4/projects/{PID}/repository/files/"
           f"{path.replace('/', '%2F')}/raw?ref={REF}")
    r = client.get(url)
    if r.status_code != 200:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gffs-only", action="store_true",
                        help="skip the .fa.gz sequence files")
    args = parser.parse_args()

    species = []
    with httpx.Client(timeout=120, headers={"User-Agent": "Roost/0.1"},
                      follow_redirects=True) as client:
        # file list (paginated)
        items, page = [], 1
        while True:
            r = client.get(f"https://gitlab.com/api/v4/projects/{PID}/repository/tree",
                           params={"recursive": "true", "per_page": 100, "page": page})
            batch = r.json()
            if not batch:
                break
            items.extend(i["path"] for i in batch)
            page += 1
        print(f"{len(items)} files in repo")

        # small essentials
        for path in ["setup/data/Sample_sheet_363genomes_short_name.txt",
                     "setup/HOWTO.txt",
                     "setup/sql/create_tables.sql",
                     "setup/sql/insert_basedata.sql",
                     "setup/py/databases.py"]:
            ok = download(client, path, OUT / path.replace("setup/", ""))
            print(f"  {'✓' if ok else '✗'} {path}")

        gffs = [p for p in items if p.endswith("_immune.gff.gz")]
        fas = [p for p in items if p.endswith("_immune.fa.gz")]
        print(f"downloading {len(gffs)} GFFs" +
              (f" + {len(fas)} FASTAs" if not args.gffs_only else ""))

        done = fail = 0
        todo = gffs + ([] if args.gffs_only else fas)
        for i, path in enumerate(todo):
            dest = OUT / path.replace("setup/data/", "")
            if dest.exists() and dest.stat().st_size > 0:
                done += 1
                continue
            if download(client, path, dest):
                done += 1
            else:
                fail += 1
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(todo)} (failures: {fail})", flush=True)
            time.sleep(0.15)  # be polite to gitlab

    print(f"\ndone: {done}, failed: {fail} → {OUT}")


if __name__ == "__main__":
    main()
