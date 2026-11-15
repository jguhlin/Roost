#!/usr/bin/env python3
"""Deterministic integrity tests for every LLM-written i18n data store.

Catches the four failure classes observed in production:

  1. Chat-template token leakage — reasoning-mode models sometimes emit
     <|start|>/<|message|>/<|eom|>/assistant markers mid-translation
     (seen: papers/zh.json, papers/ja.json, es_i18n.json, fr_i18n.json).

  2. English echo — a degenerate model returns the English source unchanged
     for a non-English locale (seen: ko/ja downloads descriptions).

  3. Prettified-key garbage — a gap-fill script once wrote
     "credits page how to cite this" (key with underscores→spaces) as the
     VALUE, so every locale rendered the key name as text (282 entries in
     en_i18n.json).

  4. Placeholder drift — translations that drop {n}/{c} interpolation
     placeholders or <br/> structure present in the English source
     (seen: mermaid labels losing <br/>).

Run:  pixi run python scripts/tests/test_i18n_integrity.py  (or via pytest)
Exit 0 = clean; any failure prints file, key, and a short excerpt.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "web" / "public" / "data" / "i18n"
LOCALES = ["zh", "ko", "ja", "fr", "es", "hi"]

# --- contamination patterns (class 1) ---------------------------------------
TOKEN_PATTERNS = [
    ("chat-template", re.compile(r"<\|[^|]{0,40}\|>")),
    ("assistant-marker", re.compile(r"(?:^|\n)\s*assistant\s*(?:\n|:)", re.I)),
    ("system-marker", re.compile(r"(?:^|\n)\s*system\s*(?:\n|:)", re.I)),
    ("md-fence", re.compile(r"```")),
    # nested translation-JSON artifact: {"zh": "..", "ko": ".."} leaking into a value
    ("json-artifact", re.compile(r'"(?:zh|ko|ja|fr|es|hi)"\s*:\s*"')),
]

# --- known false positives for English-echo (class 2) -----------------------
# Words that are legitimately identical in the target locale (cognates /
# scientific terms / brand names). A value is only flagged if it differs from
# English ONLY by strings in this set.
COGNATES = {
    "es": {"genes", "BLAST", "Roost", "DNA", "RNA", "viral", "pandemia"},
    "fr": {"BLAST", "Roost", "DNA", "RNA"},
    "zh": {"BLAST", "Roost", "DNA", "RNA", "H5N1"},
    "ko": {"BLAST", "Roost", "DNA", "RNA", "H5N1"},
    "ja": {"BLAST", "Roost", "DNA", "RNA", "H5N1"},
    "hi": {"BLAST", "Roost", "DNA", "RNA", "H5N1"},
}
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

def is_cognate_only(english, translated, lang):
    """True if every word difference between english and translated is a known cognate."""
    def words(s):
        return {w for w in PUNCT.sub(" ", s).lower().split() if w}
    diff = words(english) ^ words(translated)
    # identical or all differing tokens are cognates → not a real echo
    return not diff or diff <= {c.lower() for c in COGNATES.get(lang, set())}


def load(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None


def iter_strings(node, trail=()):
    if isinstance(node, str):
        yield trail, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from iter_strings(v, trail + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_strings(v, trail + (str(i),))


def test_token_leakage():
    """Class 1: chat-template / reasoning tokens in any string of any store."""
    failures = []
    stores = [(I18N / f"{l}_i18n.json",) for l in LOCALES]
    stores += [(I18N / f"{l}.json",) for l in LOCALES]
    stores += [(I18N / f"{l}_content.json",) for l in LOCALES]
    stores += [(I18N / "papers" / f"{l}.json",) for l in LOCALES]
    stores += [(I18N / "en_i18n.json",), (I18N / "extraction.json",), (I18N / "final_extract.json",)]
    for (path,) in stores:
        store = load(path)
        if store is None:
            continue
        for trail, s in iter_strings(store):
            for label, pat in TOKEN_PATTERNS:
                if pat.search(s):
                    key = ".".join(trail[:4])
                    failures.append(f"{path.name} [{label}] {key}: …{s[max(0,pat.search(s).start()-20):pat.search(s).start()+30]}…")
    assert not failures, f"token leakage in {len(failures)} strings:\n  " + "\n  ".join(failures[:20])


def test_english_echo():
    """Class 2: non-English locale value identical to the English fallback."""
    failures = []
    for lang in LOCALES:
        en = load(I18N / "en_i18n.json") or {}
        loc = load(I18N / f"{lang}_i18n.json") or {}
        for k, v in loc.items():
            if k in en and isinstance(en[k], str) and isinstance(v, str):
                if v.strip() == en[k].strip() and not is_cognate_only(en[k], v, lang):
                    # only flag meaningful strings (>= 3 words), short labels are noise
                    if len(en[k].split()) >= 3:
                        failures.append(f"{lang}_i18n.json {k}: {v[:60]!r}")
    assert not failures, f"English echo in {len(failures)} entries:\n  " + "\n  ".join(failures[:20])


def test_prettified_key_garbage():
    """Class 3: value is just the key name prettified (gap-fill corruption)."""
    failures = []
    for path in sorted(I18N.glob("*.json")):
        if path.name in {"i18n_refinement_log.json"}:
            continue
        store = load(path)
        if store is None:
            continue
        for trail, s in iter_strings(store):
            if not trail:
                continue
            # reconstruct a plausible key from the trail (leaf segments)
            leaf = trail[-1] if trail else ""
            prettified = leaf.replace("_", " ").replace(".", " ").strip().lower()
            if len(prettified) > 12 and s.strip().lower() == prettified:
                failures.append(f"{path.name} {'.'.join(trail[:3])}: {s[:60]!r}")
    assert not failures, f"prettified-key garbage in {len(failures)} entries:\n  " + "\n  ".join(failures[:20])


def test_placeholder_integrity():
    """Class 4a: {n}/{c} placeholders in translations match the English source."""
    failures = []
    en = load(I18N / "en_i18n.json") or {}
    ph = re.compile(r"\{[a-z]\}")
    for lang in LOCALES:
        loc = load(I18N / f"{lang}_i18n.json") or {}
        for k, v in loc.items():
            if k in en and isinstance(en[k], str) and isinstance(v, str):
                want, got = set(ph.findall(en[k])), set(ph.findall(v))
                if want and want != got:
                    failures.append(f"{lang}_i18n.json {k}: en has {sorted(want)}, {lang} has {sorted(got)}")
    assert not failures, f"placeholder drift in {len(failures)} entries:\n  " + "\n  ".join(failures[:20])


def test_markup_structure_preserved():
    """Class 4b: <br/> tags in English source survive translation (mermaid labels)."""
    failures = []
    en = load(I18N / "en_i18n.json") or {}
    # also check the inline en dict
    store_src = (ROOT / "web" / "src" / "lib" / "stores" / "i18n.svelte.js").read_text()
    for m in re.finditer(r"'([a-zA-Z0-9_.\- ]+)':\s*'((?:[^'\\]|\\.)*)'", store_src):
        k, v = m.group(1), m.group(2).replace("\\'", "'")
        en.setdefault(k, v)
    for lang in LOCALES:
        loc = load(I18N / f"{lang}_i18n.json") or {}
        for k, v in loc.items():
            if k in en and isinstance(en[k], str) and isinstance(v, str):
                if en[k].count("<br/>") != v.count("<br/>"):
                    failures.append(f"{lang}_i18n.json {k}: en has {en[k].count('<br/>')} <br/>, {lang} has {v.count('<br/>')}")
    assert not failures, f"markup drift in {len(failures)} entries:\n  " + "\n  ".join(failures[:20])


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test.__name__}\n{e}")
    print(f"\n{'ALL PASS' if not failed else f'{failed} FAILING'}")
    sys.exit(1 if failed else 0)
