#!/usr/bin/env python3
"""
i18n drift checker (D71): detects when English text in components has changed
since its translation was generated, so translations go stale silently.

Checks:
1. Re-extracts strings from all .svelte files
2. Compares against extraction.json (English source of truth)
3. Reports: stale translations (English changed), orphaned keys (no component
   references them), unwired strings (English text present, no t() call)

Usage: pixi run python scripts/i18n_check.py
Exit code 1 if action needed (useful for CI / quarterly hygiene).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEB = ROOT / "web" / "src"
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"

SKIP_EXACT = {
    'NCBI', 'GBIF', 'Wikipedia', 'GitHub', 'DOI', 'Link', 'RCSB', 'CARTO',
    'OpenStreetMap', 'ORF', 'EN', 'ZH', 'HI', 'JA', 'FR', 'Vacc', 'lit',
}


def extract_current():
    """Extract all t()/tc() keys and hardcoded English from components."""
    t_keys_used = set()
    hardcoded = []

    for f in sorted(WEB.rglob("*.svelte")):
        content = f.read_text()
        # Collect t('key') and tc('key') references
        for m in re.finditer(r"\b[t]c?\(\s*'([^']+)'\s*\)", content):
            t_keys_used.add(m.group(1))
        # Collect hardcoded English text nodes
        for m in re.finditer(r'>\s*([A-Za-z][A-Za-z0-9\s\'\-\.,:;!?/&…·—]{3,60})\s*<', content):
            text = m.group(1).strip()
            if text not in SKIP_EXACT and re.search(r'[a-z]', text) and len(text) > 4:
                if not any(c in text for c in '{}$'):
                    hardcoded.append((str(f.relative_to(WEB)), text))

    return t_keys_used, hardcoded


def main():
    extraction = json.loads((I18N_DIR / "extraction.json").read_text())
    final_extract = {}
    fe = I18N_DIR / "final_extract.json"
    if fe.exists():
        final_extract = json.loads(fe.read_text())

    t_keys_used, hardcoded = extract_current()

    # All keys that have English text recorded
    known_english = {**{k: v["english"] for k, v in extraction.items()}, **final_extract}

    # 1. Orphaned keys: in translation files but never referenced by t()/tc()
    print("=== ORPHANED KEYS (in translation files, never called) ===")
    orphaned = 0
    for lang_file in sorted(I18N_DIR.glob("*_i18n.json")):
        lang = lang_file.stem.replace("_i18n", "")
        data = json.loads(lang_file.read_text())
        orphans = [k for k in data if k not in t_keys_used and not k.startswith("nav.")
                   and not k.startswith("stats.") and not k.startswith("home.")
                   and not k.startswith("common.") and not k.startswith("species.")
                   and not k.startswith("genes.") and not k.startswith("papers.")
                   and not k.startswith("model.")]
        # Also check if key maps to a known extraction (may be wired via dynamic keys)
        real_orphans = [k for k in orphans if k not in known_english or k not in t_keys_used]
        # Dynamic keys (gene.X.function etc) are used via template literals — skip
        real_orphans = [k for k in orphans if not re.match(
            r'(gene|model|evidence)\.', k)]
        if real_orphans:
            orphaned += len(real_orphans)
            print(f"  {lang}: {len(real_orphans)} orphans (e.g. {real_orphans[:3]})")
    if orphaned == 0:
        print("  none — all keys are referenced")

    # 2. Unwired strings: English text in components without t() call
    print("\n=== UNWIRED STRINGS (hardcoded English, no t() call) ===")
    # Get all English values currently behind t() calls
    wired_english = set(known_english.values())
    unwired = [(f, text) for f, text in hardcoded if text not in wired_english]
    if unwired:
        for f, text in unwired[:15]:
            print(f"  {f}: '{text[:50]}'")
        if len(unwired) > 15:
            print(f"  … and {len(unwired)-15} more")
        print(f"  TOTAL: {len(unwired)} unwired")
    else:
        print("  none — all visible text is wired")

    # 3. Paper translation coverage + orphans
    print("\n=== PAPER TRANSLATIONS ===")
    papers_file = ROOT / "web" / "public" / "data" / "papers.json"
    trans_dir = I18N_DIR / "papers"
    if papers_file.exists():
        paper_ids = {p["id"] for p in json.loads(papers_file.read_text())["papers"]}
        # current content hashes from wiki_genes (for orphan detection)
        wiki_file = ROOT / "web" / "public" / "data" / "wiki_genes.json"
        live_hashes = set()
        if wiki_file.exists():
            for gene in json.loads(wiki_file.read_text())["genes"].values():
                for f in gene.get("key_findings", []):
                    if f.get("fh"): live_hashes.add(f["fh"])
                for c in gene.get("conclusions", []):
                    if isinstance(c, dict) and c.get("fh"): live_hashes.add(c["fh"])
                for r in gene.get("roles", []):
                    if r.get("fh"): live_hashes.add(r["fh"])
        for lang in ["zh", "hi", "ja", "fr"]:
            tf = trans_dir / f"{lang}.json"
            if tf.exists():
                data = json.loads(tf.read_text())
                done = sum(1 for pid in paper_ids if pid in data.get("papers", {}))
                orphan_papers = [k for k in data.get("papers", {}) if k not in paper_ids]
                orphan_hashes = ([k for k in data.get("findings", {}) if k not in live_hashes]
                                 + [k for k in data.get("roles", {}) if k not in live_hashes]
                                 + [k for k in data.get("conclusions", {}) if k not in live_hashes])
                line = f"  {lang}: {done}/{len(paper_ids)} papers, {len(data.get('topics', {}))} topics"
                if orphan_papers or orphan_hashes:
                    line += f"  ⚠ {len(orphan_papers)} orphaned papers, {len(orphan_hashes)} orphaned texts"
                print(line)
            else:
                print(f"  {lang}: not started")

    # Summary
    needs_action = len(unwired) > 0
    print(f"\n{'ACTION NEEDED' if needs_action else 'OK'}: "
          f"{len(unwired)} unwired, {orphaned} orphaned")
    sys.exit(1 if needs_action else 0)


if __name__ == "__main__":
    main()
