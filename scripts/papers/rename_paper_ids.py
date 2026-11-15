#!/usr/bin/env python3
"""
Paper ID renaming (D92): replace meaningless IDs (input_2024_154, paper_2024,
read_2024_3, unknown*) with meaningful slugs derived from the paper's title.

Convention: {topic_words}_{year} — lowercase, underscores, max 40 chars.
Examples:
  input_2024_476 "Computational Structural Analysis Predicts..." → computational_host_range_2024
  paper_2024 "Spatiotemporal Dynamics of HPAI..." → spatiotemporal_hpai_2024

The script:
  1. Generates new IDs from titles
  2. Checks for collisions (appends _v2, _v3 if needed)
  3. Writes a mapping file (old_id → new_id)
  4. Optionally applies the rename across ALL referencing files

Usage:
  pixi run python scripts/papers/rename_paper_ids.py --dry-run   # show mapping
  pixi run python scripts/papers/rename_paper_ids.py --apply     # do the rename
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
MD_DIR = ROOT / "docs" / "papers_md"
MAPPING_PATH = ROOT / "data" / "papers" / "id_rename_map.json"

BAD_PATTERN = re.compile(
    r'^(input_\d|paper_\d|read_\d|unknown\d|_dup_)', re.IGNORECASE)

# Files that contain paper_id references (path relative to ROOT, format)
REFERENCING_FILES = [
    # (path, jsonl or json, field_path)
    ("data/papers/gene_claims.jsonl", "jsonl", "paper_id"),
    ("data/papers/paper_conclusions.jsonl", "jsonl", "paper_id"),
    ("data/papers/gene_absence_phenotypes.jsonl", "jsonl", "paper_id"),
    ("data/papers/model_verdicts.jsonl", "jsonl", "paper_id"),
    ("data/papers/gene_discovery.jsonl", "jsonl", "paper_id"),
    ("data/papers/connections/windows.jsonl", "jsonl", "paper_id"),
    ("data/papers/connections/window_verdicts.jsonl", "jsonl", "paper_id"),
    ("data/papers/connections/candidates.jsonl", "jsonl", "paper_id"),
    ("data/papers/connections/quarantine.jsonl", "jsonl", "paper_id"),
    ("data/papers/connections/appeals.jsonl", "jsonl", None),
    ("data/papers/corpus_manifest.json", "json", None),
    ("data/papers/paper_registry.json", "json", None),
    ("web/public/data/wiki_genes.json", "json", None),
    ("web/public/data/gene_discovery.json", "json", None),
]

STOP_WORDS = {
    'the', 'a', 'an', 'of', 'in', 'and', 'or', 'to', 'for', 'with', 'on',
    'at', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
    'during', 'between', 'among', 'through', 'into', 'over', 'after',
    'before', 'under', 'above', 'below', 'up', 'down', 'out', 'off',
    'that', 'this', 'these', 'those', 'it', 'its', 'their', 'his', 'her',
    'which', 'what', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
    'can', 'could', 'should', 'would', 'may', 'might', 'must', 'shall',
    'will', 'do', 'does', 'did', 'has', 'have', 'had', 'not', 'no', 'nor',
    'but', 'if', 'then', 'else', 'so', 'than', 'too', 'very', 'just',
    'about', 'against', 'between', 'through', 'during', 'before', 'after',
    'and', 'but', 'for', 'nor', 'or', 'so', 'yet', 'both', 'either',
    'neither', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
    'only', 'own', 'same', 's', 't', 'don', 'now', 'also', 'may',
    'highly', 'pathogenic', 'avian', 'influenza', 'virus', 'h5n1',
}


def slug_from_title(title, year, max_len=36):
    """Generate a meaningful slug from a paper's title."""
    if not title:
        return f"untitled_{year}"
    # Remove markdown, parentheses content, special chars
    t = re.sub(r'\*\*|\*|__|\[|\]|\(|\)', ' ', title)
    t = re.sub(r'[^\w\s]', ' ', t)
    words = t.lower().split()
    # Remove stop words and H5N1-ubiquitous terms (they don't differentiate)
    key_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    if not key_words:
        key_words = [w for w in words if len(w) > 2][:3]
    # Take the first 3-4 most distinctive words
    slug_words = key_words[:4]
    slug = '_'.join(slug_words)
    if len(slug) > max_len:
        slug = '_'.join(slug_words[:3])[:max_len]
    # Clean up
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    slug = re.sub(r'_+', '_', slug).strip('_')
    if not slug:
        slug = 'study'
    return f"{slug}_{year}"


def build_mapping(papers):
    """Build old→new mapping for all bad-ID papers."""
    existing = {p['id'] for p in papers}
    mapping = {}
    for p in papers:
        if not BAD_PATTERN.match(p['id']):
            continue
        year = p.get('year') or '2024'
        new_id = slug_from_title(p.get('title', ''), year)
        # Collision check
        base = new_id
        counter = 2
        while new_id in existing and new_id != p['id']:
            suffix = f"_v{counter}"
            trim_len = 40 - len(suffix)
            new_id = base[:trim_len] + suffix
            counter += 1
        existing.add(new_id)
        mapping[p['id']] = new_id
    return mapping


def rename_in_json(obj, mapping):
    """Recursively rename paper_id values in a JSON structure."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            val = obj[key]
            if key == 'paper_id' and val in mapping:
                obj[key] = mapping[val]
            elif isinstance(val, str) and val in mapping and \
                    key in ('id', 'paper_id', 'pid'):
                obj[key] = mapping[val]
            else:
                rename_in_json(val, mapping)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, str) and item in mapping:
                obj[i] = mapping[item]
            else:
                rename_in_json(item, mapping)
    # For appeals.jsonl which has nested paper references
    if isinstance(obj, dict) and 'window_id' in obj:
        pass  # window_ids don't contain paper_ids directly


def apply_rename(mapping):
    """Apply the rename across papers.json, markdown files, and all referencing files."""
    # 1. papers.json
    data = json.loads(PAPERS_JSON.read_text())
    for p in data['papers']:
        if p['id'] in mapping:
            p['id'] = mapping[p['id']]
    PAPERS_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"  papers.json: {len(mapping)} IDs renamed")

    # 2. markdown files
    renamed_md = 0
    for old_id, new_id in mapping.items():
        old_md = MD_DIR / f"{old_id}.md"
        new_md = MD_DIR / f"{new_id}.md"
        if old_md.exists():
            if new_md.exists():
                print(f"  WARNING: {new_md.name} already exists, skipping")
            else:
                old_md.rename(new_md)
                renamed_md += 1
    print(f"  markdown files: {renamed_md} renamed")

    # Also rename PDFs if they exist
    pdf_dir = ROOT / "docs" / "papers_pdfs"
    renamed_pdf = 0
    for old_id, new_id in mapping.items():
        old_pdf = pdf_dir / f"{old_id}.pdf"
        new_pdf = pdf_dir / f"{new_id}.pdf"
        if old_pdf.exists() and not new_pdf.exists():
            old_pdf.rename(new_pdf)
            renamed_pdf += 1
    if renamed_pdf:
        print(f"  PDF files: {renamed_pdf} renamed")

    # 3. All referencing data files
    for path_str, fmt, _ in REFERENCING_FILES:
        path = ROOT / path_str
        if not path.exists():
            continue
        n_changed = 0
        if fmt == "jsonl":
            lines = []
            for line in path.read_text().splitlines():
                try:
                    rec = json.loads(line)
                    before = json.dumps(rec)
                    rename_in_json(rec, mapping)
                    after = json.dumps(rec)
                    if before != after:
                        n_changed += 1
                    lines.append(json.dumps(rec, ensure_ascii=False))
                except Exception:
                    lines.append(line)
            path.write_text('\n'.join(lines) + '\n')
        else:
            data = json.loads(path.read_text())
            before = json.dumps(data)
            rename_in_json(data, mapping)
            after = json.dumps(data)
            if before != after:
                n_changed = 1
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        if n_changed:
            print(f"  {path_str}: {n_changed} records updated")

    # 4. Review decisions (keys are candidate_ids, not paper_ids — but
    # candidate_ids contain window_ids which don't reference paper IDs directly)
    # 5. Strain index (keys are paper_ids)
    strain_path = ROOT / "data/papers/connections/strain_index.json"
    if strain_path.exists():
        # strain_index doesn't have per-paper keys in the current version
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    papers = json.loads(PAPERS_JSON.read_text())['papers']
    bad = [p for p in papers if BAD_PATTERN.match(p['id'])]
    print(f"papers with bad IDs: {len(bad)} of {len(papers)}")

    mapping = build_mapping(papers)
    print(f"mapping generated: {len(mapping)} renames")

    if args.dry_run:
        print("\nsample mappings:")
        for old, new in sorted(mapping.items())[:20]:
            title = next((p.get('title', '?')[:50] for p in papers
                          if p['id'] == old), '?')
            print(f"  {old:30s} → {new:40s} | {title}")
        return

    if args.apply:
        # backup
        backup = PAPERS_JSON.with_suffix('.json.bak')
        shutil.copy2(PAPERS_JSON, backup)
        print(f"backup: {backup.name}")

        MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
        MAPPING_PATH.write_text(json.dumps(mapping, indent=1))
        print(f"mapping saved: {MAPPING_PATH}")

        apply_rename(mapping)
        print(f"\ndone: {len(mapping)} paper IDs renamed across all files")


if __name__ == "__main__":
    main()
