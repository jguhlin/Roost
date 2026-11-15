#!/usr/bin/env python3
"""
Fetch UniProt function descriptions for the GO-backbone panel genes.

Reads uniprot accessions from host_panel_v2.json, queries UniProt's REST
API (batch, 500 accessions per request, no key needed), and writes
data/genes/gene_functions.json: {symbol: "function text"}.

Resume-safe: existing entries are kept; only new accessions fetched.

Usage: pixi run python scripts/genes/fetch_uniprot_functions.py
"""

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PANEL = ROOT / "data" / "genes" / "host_panel_v2.json"
OUT = ROOT / "data" / "genes" / "gene_functions.json"

API = "https://rest.uniprot.org/uniprotkb/search"
BATCH = 20   # accessions per query (URL length limit)
SLEEP = 0.6  # politeness between requests


def main():
    panel = json.load(open(PANEL))
    genes = panel["genes"] if isinstance(panel, dict) else panel

    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [g for g in genes if g.get("uniprot") and g["symbol"] not in existing]
    print(f"Panel genes with UniProt accessions: {sum(1 for g in genes if g.get('uniprot'))}")
    print(f"Already have functions: {len(existing)}, to fetch: {len(todo)}")
    if not todo:
        print("Nothing to do.")
        return

    results = dict(existing)
    fetched = 0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        accs = " OR ".join(f"accession:{g['uniprot']}" for g in chunk)
        url = f"{API}?query={urllib.parse.quote(accs)}&fields=accession,cc_function&format=json&size={BATCH}"
        req = urllib.request.Request(url, headers={"User-Agent": "Roost/0.1 (research portal)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"  batch {i // BATCH}: failed: {e} — retrying once")
            time.sleep(5)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
            except Exception as e2:
                print(f"  batch {i // BATCH}: skipped ({e2})")
                continue

        acc_to_fn = {}
        for entry in data.get("results", []):
            acc = entry.get("primaryAccession")
            comments = entry.get("comments") or []
            texts = []
            for c in comments:
                if c.get("commentType") == "FUNCTION":
                    for t in c.get("texts", []):
                        texts.append(t.get("value", ""))
            if acc and texts:
                acc_to_fn[acc] = " ".join(texts)

        for g in chunk:
            fn = acc_to_fn.get(g["uniprot"])
            if fn:
                results[g["symbol"]] = fn
                fetched += 1
        # persist incrementally
        OUT.write_text(json.dumps(results, indent=1))
        if (i // BATCH) % 5 == 0:
            print(f"  chunk {i // BATCH + 1}/{(len(todo) + BATCH - 1) // BATCH}: +{fetched} functions (total {len(results)})")
        time.sleep(SLEEP)

    OUT.write_text(json.dumps(results, indent=1))
    print(f"\nDone: {fetched} new, {len(results)} total → {OUT}")


if __name__ == "__main__":
    main()
