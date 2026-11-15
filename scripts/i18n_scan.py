#!/usr/bin/env python3
"""Systematic hardcoded-English detector for Svelte templates.

Scans every .svelte file, walking line by line, tracking whether we're inside
a <script> block (skip — JS logic, not display text), and finding:
  1. Text nodes: English text between > and < that isn't inside {t(...)}
  2. Quoted attributes: English in attr="..." that isn't attr={t(...)}
  3. Mixed template text: English words adjacent to {expressions} that aren't
     part of a t() call

Positive detection heuristics:
  - Text contains ≥2 common English words (the, and, for, with, etc.)
  - OR text starts with a capital letter and has ≥4 words
  - AND is not: a URL, a CSS class, a number, a single technical term

Usage: pixi run python scripts/i18n_scan.py [--fix] [--verbose]
  --fix: generate a patch file with suggested t() wiring
  --verbose: show all matches including borderline cases
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"

# English indicator words (high confidence)
EN_WORDS = re.compile(
    r'\b(?:the|and|for|with|from|this|that|not|all|can|will|has|have|been|'
    r'are|was|were|its|their|when|where|which|click|search|filter|show|hide|'
    r'load|loading|error|failed|no\s|none|empty|try|adjust|select|enter|'
    r'view|open|close|download|upload|export|import|copy|paste|remove|add|'
    r'clear|reset|apply|cancel|save|delete|edit|create|new|old|total|more|'
    r'less|over|under|between|within|across|about|into|onto|upon|each|'
    r'every|some|any|both|few|many|most|other|another|same|different|'
    r'only|also|just|still|even|ever|never|always|often|sometimes|'
    r'detection|species|genome|gene|paper|mutation|country|data|'
    r'research|study|analysis|result|finding|evidence|literature|'
    r'first|last|next|previous|page|list|table|chart|map|graph)\b', re.I)

# Things that look English but aren't translatable
SKIP_PATTERNS = [
    re.compile(r'^(?:https?://|mailto:|tel:|#|/\|\.|\.\.|~)'),
    re.compile(r'^(?:GCA_|GCF_|ENSG|ENS|LOC\d|NM_|NP_|XP_)'),
    re.compile(r'^(?:DNA|RNA|BLAST|API|JSON|CSV|TSV|HTML|CSS|SVG|WASM|HTTP|FTP|URL|DOI|PMID|ORCID)$'),
    re.compile(r'^(?:true|false|null|undefined|NaN|Infinity)$'),
    re.compile(r'^[\d\s\-+.,%()×–—·]+$', ),  # numbers/punctuation only
    re.compile(r'^(?:H\d+N\d+|H\d+|N\d+|clade\s+[\d.]+|EA/AM|LPAI|HPAI)$'),
    re.compile(r'^(?:svg|path|circle|rect|line|polyline|polygon|g|defs|use|text|tspan)$', re.I),
]

# Attribute names that commonly contain translatable text
TRANSLATABLE_ATTRS = {'placeholder', 'title', 'aria-label', 'alt', 'label', 'aria-description'}


def is_english(text):
    """Check if text looks like displayable English."""
    text = text.strip()
    if len(text) < 4:
        return False
    for pat in SKIP_PATTERNS:
        if pat.match(text):
            return False
    words = EN_WORDS.findall(text)
    n_words = len(text.split())
    return (len(words) >= 1 and n_words >= 2) or (n_words >= 4 and text[0].isupper())


def in_t_call(line, col):
    """Check if position col on line is inside a {t(...)} or {tc(...)} expression."""
    # look backwards for opening { that isn't closed before col
    depth = 0
    for i in range(col - 1, -1, -1):
        ch = line[i]
        if ch == '}':
            depth += 1
        elif ch == '{':
            if depth == 0:
                # check what follows this {
                after = line[i:i+5]
                if 't(' in after or 'tc(' in after or 'sn(' in after or 'pt(' in after or 'ptopic(' in after:
                    return True
                # || fallback pattern inside the expression is also translated
                if '||' in line[i:col]:
                    return True
                return False
            depth -= 1
    return False


def in_t_call_at(text, col):
    """True if offset col sits inside a {t(...)} / {tc(...)} / {… || fallback} expression."""
    depth = 0
    for i in range(col - 1, max(0, col - 2000), -1):
        ch = text[i]
        if ch == '}':
            depth += 1
        elif ch == '{':
            if depth == 0:
                after = text[i:i+8]
                if 't(' in after or 'tc(' in after or 'sn(' in after or 'pt(' in after or 'ptopic(' in after:
                    return True
                # || fallback pattern inside the expression is also translated
                if '||' in text[i:col]:
                    return True
                return False
            depth -= 1
    return False


def scan_file(path):
    """Scan a single .svelte file for hardcoded English."""
    findings = []
    content = open(path).read()

    # Blank out script/style blocks and comments, preserving line count so
    # offsets still map to line numbers.
    tpl = content
    for pattern in (r'<script\b.*?</script>', r'<style\b.*?</style>', r'<!--.*?-->'):
        for m in list(re.finditer(pattern, tpl, re.DOTALL)):
            start, end = m.span()
            tpl = tpl[:start] + '\n' * tpl[start:end].count('\n') + tpl[end:]

    def lineno_of(offset):
        return tpl.count('\n', 0, offset) + 1

    # 1. Text nodes: >English text< — DOTALL so text on its own line between
    #    tags (multi-line nodes) is caught, not just same-line >text<.
    for m in re.finditer(r'>([^<>{}]+)<', tpl, re.DOTALL):
        text = ' '.join(m.group(1).split())
        if is_english(text) and not in_t_call_at(tpl, m.start(1)):
            findings.append((lineno_of(m.start(1)), 'text', text[:80], m.start(1)))

    seen = {(f[0], f[2]) for f in findings}
    for lineno, line in enumerate(tpl.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue

        # 2. Quoted attributes with English
        for m in re.finditer(r'(\w+)="([^"]{4,})"', line):
            attr, val = m.group(1), m.group(2)
            if attr in TRANSLATABLE_ATTRS and is_english(val):
                # skip if value already contains a t() call or || fallback (wired)
                if '{t(' in val or '||' in val or "{t('" in val:
                    continue
                # check if preceded by ={t( (already translated)
                if not re.search(r'=\s*$', line[:m.start(2)]):
                    key = (lineno, f'attr:{attr}')
                    if (lineno, val[:80]) not in seen:
                        findings.append((lineno, f'attr:{attr}', val[:80], m.start(2)))

        # 3. Text adjacent to expressions (mixed content)
        # >English {expr} more English<
        for m in re.finditer(r'>\s*([A-Z][a-z]+(?:\s+[a-z]+){1,})\s*\{', line):
            text = m.group(1).strip()
            if is_english(text) and not in_t_call_at(tpl, m.start(1)):
                findings.append((lineno, 'mixed', text[:60] + ' {…', m.start(1)))

        # 4. Text after expression closing (mixed content)
        for m in re.finditer(r'\}\s*([a-z][a-z]+(?:\s+[a-z]+){1,})\s*<', line):
            text = m.group(1).strip()
            if is_english(text) and not in_t_call_at(tpl, m.start(1)):
                findings.append((lineno, 'post-expr', '{…} ' + text[:60], m.start(1)))

    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--fix', action='store_true', help='output suggested keys')
    args = ap.parse_args()

    all_findings = defaultdict(list)
    for root, dirs, files in os.walk(WEB):
        dirs[:] = [d for d in dirs if d not in {'node_modules', '__pycache__'}]
        for f in sorted(files):
            if not f.endswith('.svelte'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, WEB)
            findings = scan_file(path)
            if findings:
                all_findings[rel] = findings

    total = sum(len(v) for v in all_findings.values())
    print(f"Hardcoded English strings found: {total} across {len(all_findings)} files\n")

    for f in sorted(all_findings, key=lambda k: -len(all_findings[k])):
        items = all_findings[f]
        print(f"  {f} ({len(items)}):")
        for lineno, kind, text, col in items[:6]:
            print(f"    L{lineno:4d} [{kind:9s}] {text}")
        if len(items) > 6:
            print(f"    ... +{len(items) - 6} more")
        print()

    if args.fix:
        print("\nSuggested t() keys (for wiring):")
        for f in sorted(all_findings):
            for lineno, kind, text, _ in all_findings[f]:
                # generate a key name from the text
                words = re.findall(r'[a-z]+', text.lower())[:4]
                key = '.'.join(words) if words else f'misc.{lineno}'
                print(f"  {f}:{lineno} → t('{key}')  // {text[:50]}")


if __name__ == '__main__':
    main()
