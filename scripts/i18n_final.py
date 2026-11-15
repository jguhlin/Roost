#!/usr/bin/env python3
"""
Final i18n pass (D70): extract remaining hardcoded strings, translate, wire.
More careful than the regex codemod: exact-match replacement with verification.

Usage: pixi run python scripts/i18n_final.py [--dry-run] [--translate] [--wire]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
WEB = ROOT / "web" / "src"
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"

# Strings that should NOT be translated (proper nouns, technical terms, link text)
SKIP_EXACT = {
    'NCBI', 'GBIF', 'Wikipedia', 'GitHub', 'DOI', 'Link', 'RCSB', 'CARTO',
    'OpenStreetMap', 'ORF', 'EN', 'ZH', 'HI', 'JA', 'FR',
    'NCBI Gene', 'NCBI Taxonomy', 'View on RCSB',
    'Ball & Stick', 'Vacc', 'lit',
}

# Skip patterns (technical, code fragments)
SKIP_PATTERNS = [
    re.compile(r'^[A-Z]{2,}[0-9]*$'),  # acronyms
    re.compile(r'^(DNA|RNA|cDNA|mRNA|HSP|ORF)$', re.I),
    re.compile(r'^\d'),  # starts with number
    re.compile(r'(?:aa|bp|kb|Mb)$'),  # measurements
]

# High-priority files with their semantic key prefixes
TARGET_FILES = {
    'lib/components/species/SpeciesDetail.svelte': 'species_detail',
    'lib/components/species/SpeciesFullPage.svelte': 'species_full',
    'lib/components/genes/EvidenceDrawer.svelte': 'evidence',
    'lib/components/genes/GeneFullPage.svelte': 'gene_full',
    'routes/Genomes.svelte': 'genomes_page',
    'routes/Species.svelte': 'species_page',
    'routes/Genes.svelte': 'genes_page',
    'routes/Mutations.svelte': 'mutations_page',
    'lib/components/phylogeny/PhyloControls.svelte': 'phylo',
    'routes/Home.svelte': 'home',
    'routes/Downloads.svelte': 'downloads',
    'lib/components/common/Footer.svelte': 'footer',
    'routes/Map.svelte': 'map_page',
    'lib/components/phylogeny/PhyloTree.svelte': 'phylotree',
    'routes/Credits.svelte': 'credits_page',
    'lib/components/genes/MutationFullPage.svelte': 'mutation_full',
    'routes/Phylogeny.svelte': 'phylogeny_page',
    'routes/Resources.svelte': 'resources_page',
    'lib/components/genes/MolecularViewer.svelte': 'molviewer',
    'routes/Methods.svelte': 'methods_page',
    'lib/components/phylogeny/PhyloLegend.svelte': 'phylolegend',
    'lib/components/species/SpeciesCard.svelte': 'species_card',
    'routes/Glossary.svelte': 'glossary_page',
    'routes/Papers.svelte': 'papers_page',
}


def is_translatable(text):
    text = text.strip()
    if not text or len(text) < 3:
        return False
    if text in SKIP_EXACT:
        return False
    if any(p.search(text) for p in SKIP_PATTERNS):
        return False
    if not re.search(r'[a-z]', text):  # all caps single words
        return False
    # Skip if contains code-like patterns
    if any(c in text for c in ['{', '}', '$', '=>', '&&', '||', '(']) and not re.match(r'^[A-Z][a-z].*\(', text):
        if '(' in text and ')' not in text:
            return False
    return True


def extract_strings():
    """Extract remaining hardcoded strings from target files."""
    results = {}  # key → english
    for rel_path, prefix in TARGET_FILES.items():
        f = WEB / rel_path
        if not f.exists():
            continue
        content = f.read_text()
        # Text nodes: >text<
        for m in re.finditer(r'>\s*([A-Za-z][^<>{}\n]{2,80})\s*<', content):
            text = m.group(1).strip()
            if is_translatable(text):
                # Generate key from text
                words = re.sub(r'[^a-z0-9\s]', '', text.lower()).split()[:4]
                key = f"{prefix}.{'.'.join(words)}"
                if key not in results and text not in results.values():
                    results[key] = text
    return results


def translate_strings(strings, lang):
    """Translate using LLM."""
    # localization-quality context (2026-10-07, native-speaker review of ko):
    # translate as a native academic/scientific-localizer, NOT literally
    STYLE = (
        "You are a native scientific-UI localizer. Translate as a professional "
        "translation of a research dashboard would read — natural, concise, "
        "register-appropriate. AVOID literal calques. Use counting nouns for "
        "stat labels (e.g. Korean detection count = 검출 건수, not bare 검출). "
        "Prefer academic terminology over loanwords where standard "
        "(Korean: genome=유전체, not 게놈; map=분포 지도). Keep proper nouns "
        "(BLAST, H5N1) as-is. Preserve {placeholders} exactly."
    )
    import httpx
    LANG_NAMES = {
        "zh": "Simplified Chinese", "hi": "Hindi", "ja": "Japanese", "fr": "French", "ko": "Korean", "es": "Spanish",
    }
    items = list(strings.items())
    translations = {}
    for i in range(0, len(items), 25):
        batch = dict(items[i:i+25])
        prompt = f"""Translate each English UI string to {LANG_NAMES[lang]}.
These are interface labels for a scientific website about avian influenza.
Keep technical terms (HPAI, H5N1, DNA, genome, NCBI) as-is.

Reply ONLY with JSON: {{"key": "translation", ...}}

{json.dumps(batch, ensure_ascii=False, indent=1)}"""
        try:
            r = httpx.post("http://localhost:8005/v1/chat/completions", json={
                "model": "muse-glimmer-30b",
                "messages": [
                    {"role": "system", "content": "You are a UI translator. Reply ONLY with the JSON object."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 4000, "temperature": 0.1,
            }, timeout=300)
            msg = r.json()["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text and msg.get("reasoning_content"):
                m2 = re.search(r'\{.*\}', msg["reasoning_content"], re.DOTALL)
                if m2: text = m2.group(0)
            if text:
                m2 = re.search(r'\{.*\}', text, re.DOTALL)
                if m2:
                    translations.update(json.loads(m2.group(0)))
        except Exception as e:
            print(f"  batch {i//25} error: {str(e)[:50]}")
    return translations


def wire_strings(strings):
    """Wire t() calls into source files with exact-match verification."""
    changes = {}
    for rel_path, prefix in TARGET_FILES.items():
        f = WEB / rel_path
        if not f.exists():
            continue
        content = f.read_text()
        original = content

        for key, english in strings.items():
            if not key.startswith(prefix + '.'):
                continue
            # Exact replacement: >text< → >{t('key')}<
            old = f'>{english}<'
            new = f">{{t('{key}')}}<"
            if old in content:
                content = content.replace(old, new)

        if content != original:
            # Add import if needed
            if "from '../../stores/i18n.svelte.js'" not in content and \
               "from '../../../lib/stores/i18n.svelte.js'" not in content and \
               "from '../lib/stores/i18n.svelte.js'" not in content:
                # Determine relative path
                depth = len(Path(rel_path).parts) - 1
                rel = '../' * depth + 'lib/stores/i18n.svelte.js'
                # Insert after first import
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('import'):
                        lines.insert(i + 1, f"import {{ t }} from '{rel}';")
                        break
                content = '\n'.join(lines)

            f.write_text(content)
            n = sum(1 for key, eng in strings.items()
                    if key.startswith(prefix + '.') and f"{{t('{key}')}}" in content)
            changes[rel_path] = n

    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='Just extract and count')
    ap.add_argument('--translate', action='store_true', help='Translate missing strings')
    ap.add_argument('--wire', action='store_true', help='Wire t() calls')
    args = ap.parse_args()

    strings = extract_strings()
    print(f"Extracted {len(strings)} translatable strings")

    if args.dry_run:
        for key, text in sorted(strings.items()):
            print(f"  {key}: {text[:60]}")
        return

    # Save extraction
    (I18N_DIR / "final_extract.json").write_text(
        json.dumps(strings, indent=1, ensure_ascii=False))
    print(f"Saved to final_extract.json")

    if args.translate:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = dict(zip(["zh", "hi", "ja", "fr", "ko", "es"],
                              ex.map(lambda l: translate_strings(strings, l), ["zh", "hi", "ja", "fr", "ko", "es"])))
        for lang, translations in results.items():
            f = I18N_DIR / f"{lang}_i18n.json"
            existing = json.loads(f.read_text())
            existing.update(translations)
            f.write_text(json.dumps(existing, indent=1, ensure_ascii=False))
            print(f"  {lang}: +{len(translations)} (total {len(existing)})")

    if args.wire:
        changes = wire_strings(strings)
        print(f"\nWired {sum(changes.values())} strings across {len(changes)} files:")
        for f, n in sorted(changes.items(), key=lambda x: -x[1]):
            print(f"  {f}: {n}")


if __name__ == '__main__':
    main()
