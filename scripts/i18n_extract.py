#!/usr/bin/env python3
"""
Full i18n extraction (D68): scan all .svelte files, extract every hardcoded
UI string, generate keys, output a replacement plan.

Extracts: text nodes, placeholder/title/aria-label attributes, section headers.
Ignores: expressions, scientific terms, dynamic content.

Usage: pixi run python scripts/i18n_extract.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "web" / "src"
OUT = ROOT / "web" / "public" / "data" / "i18n" / "extraction.json"

# Skip these (research content, not UI chrome)
SKIP_PATTERNS = [
    re.compile(r"^[A-Z]{2,}[0-9]*$"),  # gene symbols, codes
    re.compile(r"^[\d\s\-+/·|,.:;%()#✓~✗●◐○∅📖🧬🌍🪺🦠🛡️📡🔴📍🫧🔵🟣🟠🦆🐔☠️💥]+$"),  # symbols/numbers only
    re.compile(r"^https?://"),  # URLs
    re.compile(r"^#[/#]"),  # hash routes
    re.compile(r"^(E\d|GCF_|GCA_|NC_|XM_|XP_|NP_)"),  # accessions
    re.compile(r"^(px-|py-|bg-|text-|border-|rounded|flex|grid|space-|w-|h-|font|dark:|hover:|md:|lg:|sm:)"),  # CSS classes
]


def extract_from_svelte(filepath):
    """Extract translatable strings from a Svelte file."""
    text = filepath.read_text(errors="ignore")
    strings = []

    # 1. Text content in elements (between > and <, not expressions)
    # Match text that's plainly between tags
    for m in re.finditer(r">([^<>{}]+)<", text):
        s = m.group(1).strip()
        if is_translatable(s):
            strings.append(("text", s, m.start(1)))

    # 2. Placeholder attributes
    for m in re.finditer(r'placeholder="([^"]+)"', text):
        s = m.group(1).strip()
        if is_translatable(s):
            strings.append(("placeholder", s, m.start(1)))

    # 3. Title attributes (tooltips)
    for m in re.finditer(r'title="([^"]+)"', text):
        s = m.group(1).strip()
        if is_translatable(s) and len(s) > 10:
            strings.append(("title", s, m.start(1)))

    # 4. aria-label
    for m in re.finditer(r'aria-label="([^"]+)"', text):
        s = m.group(1).strip()
        if is_translatable(s):
            strings.append(("aria", s, m.start(1)))

    # Deduplicate, preserving order
    seen = set()
    unique = []
    for typ, s, pos in strings:
        key = f"{typ}:{s}"
        if key not in seen:
            seen.add(key)
            unique.append((typ, s, pos))

    return unique


def is_translatable(s):
    """Check if a string should be translated."""
    if not s or len(s.strip()) < 3:
        return False
    # Skip pure symbols, numbers, CSS, URLs, accessions
    for pat in SKIP_PATTERNS:
        if pat.match(s):
            return False
    # Must contain at least one word character
    if not re.search(r"[a-zA-Z]{3,}", s):
        return False
    # Skip expressions, interpolations
    if "{" in s or "}" in s:
        return False
    # Skip very long strings (probably content, not UI)
    if len(s) > 300:
        return False
    return True


def make_key(s, file_stem):
    """Generate a sensible i18n key from a string."""
    # Try to create a semantic key
    words = re.sub(r"[^a-z0-9\s]", "", s.lower()).split()
    if not words:
        return None
    # Use first 3-4 meaningful words
    key_words = [w for w in words if len(w) > 2][:4]
    if not key_words:
        return None
    key = ".".join(key_words)
    return f"{file_stem}.{key}"


def main():
    files = sorted(SRC.rglob("*.svelte"))
    all_strings = {}  # key → {english, file, type, position}

    for f in files:
        rel = f.relative_to(SRC)
        stem = str(rel).replace("/", "_").replace(".svelte", "")
        extracted = extract_from_svelte(f)
        for typ, s, pos in extracted:
            key = make_key(s, stem)
            if not key:
                continue
            # Handle duplicate keys (same text in different files)
            base_key = key
            n = 1
            while key in all_strings and all_strings[key]["english"] != s:
                n += 1
                key = f"{base_key}_{n}"
            if key not in all_strings:
                all_strings[key] = {
                    "english": s,
                    "file": str(rel),
                    "type": typ,
                    "position": pos,
                }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(all_strings, indent=1, ensure_ascii=False))

    print(f"Scanned {len(files)} .svelte files")
    print(f"Extracted {len(all_strings)} unique translatable strings")

    # By file
    by_file = {}
    for v in all_strings.values():
        by_file.setdefault(v["file"], []).append(v)
    print("\nBy file (top 15):")
    for f, items in sorted(by_file.items(), key=lambda kv: -len(kv[1]))[:15]:
        print(f"  {len(items):3d}  {f}")

    # By type
    from collections import Counter
    types = Counter(v["type"] for v in all_strings.values())
    print(f"\nBy type: {dict(types)}")


if __name__ == "__main__":
    main()
