#!/usr/bin/env python3
"""
i18n wiring (D68c): replace hardcoded strings in .svelte files with t() calls.

Reads extraction.json for string locations, applies replacements.
Adds import statements where needed.

Usage:
  pixi run python scripts/i18n_wire.py --plan   # show what would change
  pixi run python scripts/i18n_wire.py --apply  # actually edit files
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "web" / "src"
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"
EXTRACTION = I18N_DIR / "extraction.json"


def esc(s):
    """Escape for use in regex."""
    return re.escape(s)


def wire_file(filepath, extractions, translations, apply=False):
    """Wire t() calls into a single file."""
    text = filepath.read_text()
    original = text
    changes = []

    # Group by type for targeted replacement
    for item in extractions:
        key = None
        # Find the key for this English string
        for k, v in translations.get("key_map", {}).items():
            if v == item["english"]:
                key = k
                break
        if not key:
            continue

        old = item["english"]
        typ = item["type"]

        if typ == "text":
            # Replace >Text< with >{t('key')}<
            pattern = f">{re.escape(old)}<"
            replacement = f">{{t('{key}')}}<"
            if pattern in text:
                text = text.replace(pattern, replacement, 1)
                changes.append(f"  text: {old[:40]!r} → t('{key}')")

        elif typ == "placeholder":
            pattern = f'placeholder="{re.escape(old)}"'
            replacement = f"placeholder={{t('{key}')}}"
            if pattern in text:
                text = text.replace(pattern, replacement, 1)
                changes.append(f"  placeholder: {old[:40]!r} → t('{key}')")

        elif typ == "title":
            pattern = f'title="{re.escape(old)}"'
            replacement = f"title={{t('{key}')}}"
            if pattern in text:
                text = text.replace(pattern, replacement, 1)
                changes.append(f"  title: {old[:40]!r} → t('{key}')")

    # Add import if we made changes and it's not there
    if changes and "from '../lib/stores/i18n.svelte.js'" not in text and \
       "from '../../lib/stores/i18n.svelte.js'" not in text and \
       "from '../../stores/i18n.svelte.js'" not in text:
        # Determine relative path depth
        rel = filepath.relative_to(SRC)
        depth = len(rel.parts) - 1
        prefix = "../" * depth
        import_line = f"  import {{ t }} from '{prefix}lib/stores/i18n.svelte.js';\n"

        # Insert after the first import or after <script>
        if "<script>\n" in text:
            text = text.replace("<script>\n", f"<script>\n{import_line}", 1)
        elif "import " in text:
            # Find last import line and add after it
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("import "):
                    last_import = i
            lines.insert(last_import + 1, import_line.strip())
            text = "\n".join(lines)
        changes.append(f"  + import {{ t }} from i18n")

    if changes:
        if apply:
            filepath.write_text(text)
            print(f"\n{filepath.relative_to(SRC)}: {len(changes)} changes applied")
        else:
            print(f"\n{filepath.relative_to(SRC)}: {len(changes)} changes planned")
        for c in changes:
            print(c)

    return len(changes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    extraction = json.loads(EXTRACTION.read_text())

    # Build key→english map from extraction
    key_map = {k: v["english"] for k, v in extraction.items()}

    # Load translations (any language, use the key map)
    translations = {"key_map": key_map}

    # Group extractions by file
    by_file = {}
    for key, item in extraction.items():
        by_file.setdefault(item["file"], []).append({**item, "key": key})

    total = 0
    for rel_path, items in sorted(by_file.items()):
        filepath = SRC / rel_path
        if not filepath.exists():
            continue
        n = wire_file(filepath, items, translations, apply=args.apply)
        total += n

    mode = "applied" if args.apply else "planned"
    print(f"\n{'='*50}")
    print(f"Total: {total} changes {mode} across {len(by_file)} files")
    if args.plan:
        print("Run with --apply to make changes")


if __name__ == "__main__":
    main()
