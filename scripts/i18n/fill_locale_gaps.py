#!/usr/bin/env python3
"""Fill locale gaps for en-dict UI keys (standing "next translation batch").

The shipped web/public/data/i18n/{lang}_i18n.json files lag manually-added
en-dict keys (a11y.*, mermaid.*, spread.* …) — t() falls back to English in
the meantime. This script finds en-dict keys missing from each locale,
batch-translates them via the local LLM with a strict accept filter
(doctrine: reject token leakage / English echo / placeholder drift),
writes back, and is fully resume-safe (incremental per locale).

Usage:
  LLM_BASE_URL=http://localhost:8005/v1 \
    pixi run python scripts/i18n/fill_locale_gaps.py [--workers 16]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"
EN_DICT = ROOT / "web" / "src" / "lib" / "stores" / "i18n.svelte.js"

LOCALES = ["zh", "hi", "ja", "es", "ko", "fr"]
LANG_NAMES = {
    "zh": "Simplified Chinese (中文)",
    "hi": "Hindi (हिन्दी)",
    "ja": "Japanese (日本語)",
    "es": "Spanish (Español)",
    "ko": "Korean (한국어)",
    "fr": "French (Français)",
}


def load_en_dict() -> dict[str, str]:
    src = EN_DICT.read_text()
    out: dict[str, str] = {}
    # one key per line: 'key': 'value' | 'key': "value" | 'key': `tpl`
    # (keys may contain hyphens: genes.category.host-factor, verdict.context-dependent)
    pat = re.compile(r"^\s*'([a-z0-9_.-]+)':\s*('([^']*)'|\"([^\"]*)\"|`([^`]*)`)", re.M)
    for m in pat.finditer(src):
        key = m.group(1)
        val = next(g for g in m.groups()[2:] if g is not None)
        out[key] = val
    return out


def acceptable(key: str, en: str, val: str) -> bool:
    """Doctrine accept-filter: no token leakage, no English echo (cognates
    allowed via rough similarity), no {placeholder} drift."""
    if not val or not isinstance(val, str):
        return False
    if "<|" in val or "assistant" in val.lower()[:40] or "```" in val:
        return False
    if val.strip() == en.strip():
        # exact English echo — reject UNLESS single-word: single words are
        # overwhelmingly cognates (es "experimental", fr "Provenance") which
        # the integrity suite's cognate allowlist accepts
        return len(en.strip().split()) == 1
    en_ph = sorted(re.findall(r"\{[a-z]\}", en))
    val_ph = sorted(re.findall(r"\{[a-z]\}", val))
    if en_ph != val_ph:
        return False
    return True


def translate_batch(lang: str, batch: dict[str, str], url: str, model: str) -> dict:
    prompt = f"""Translate each English value to {LANG_NAMES[lang]}.
Keep scientific terms (H5N1, DNA, gene symbols like DDX58, clades like 2.3.4.4b) in English.
Keep {n_placeholder_note()} EXACTLY as-is (do not translate inside braces).
UI labels — translate naturally and concisely.

Reply ONLY with a JSON object with the SAME keys but translated values:
{{"key": "translated", ...}}

Input:
{json.dumps(batch, ensure_ascii=False, indent=1)}"""
    try:
        r = httpx.post(
            f"{url.rstrip('/')}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a professional translator. Reply ONLY with the JSON object."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 8000,
                "temperature": 0.1,
            },
            timeout=300,
        )
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            rc = msg["reasoning_content"].strip()
            m = re.search(r"\{.*\}", rc, re.DOTALL)
            if m:
                text = m.group(0)
        if text:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
    except Exception as e:
        print(f"  batch error: {e}", file=sys.stderr)
    return {}


def n_placeholder_note():
    return "placeholders like {n} or {m} or {s}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--batch-size", type=int, default=25)
    ap.add_argument("--layer", choices=["inline", "en_i18n"], default="inline",
                    help="inline = en dict in i18n.svelte.js (default); en_i18n = legacy "
                         "auto-extracted key space in web/public/data/i18n/en_i18n.json")
    args = ap.parse_args()

    en = load_en_dict()
    if args.layer == "en_i18n":
        ext = json.loads((I18N_DIR / "en_i18n.json").read_text())
        # do not duplicate keys the inline dict already covers (t() prefers them)
        for k, v in ext.items():
            if k not in en and isinstance(v, str):
                en[k] = v
    print(f"en dict: {len(en)} keys")

    jobs = []
    for lang in LOCALES:
        f = I18N_DIR / f"{lang}_i18n.json"
        loc = json.loads(f.read_text()) if f.exists() else {}
        missing = {k: v for k, v in en.items() if k not in loc}
        print(f"{lang}: {len(missing)} missing of {len(en)}")
        for i in range(0, len(missing), args.batch_size):
            jobs.append((lang, dict(list(missing.items())[i:i + args.batch_size])))

    if not jobs:
        print("all locales complete")
        return

    def work(job):
        lang, batch = job
        got = translate_batch(lang, batch, args.url, args.model)
        kept = {k: v for k, v in got.items()
                if k in batch and acceptable(k, batch[k], v)}
        return lang, kept, len(batch)

    results: dict[str, list] = {l: [] for l in LOCALES}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for lang, kept, size in ex.map(work, jobs):
            results[lang].append(kept)
            if kept:
                print(f"  {lang}: {len(kept)}/{size} accepted")

    for lang in LOCALES:
        f = I18N_DIR / f"{lang}_i18n.json"
        loc = json.loads(f.read_text()) if f.exists() else {}
        added = 0
        for kept in results[lang]:
            for k, v in kept.items():
                if k not in loc:
                    loc[k] = v
                    added += 1
        f.write_text(json.dumps(loc, ensure_ascii=False, indent=1))
        print(f"{lang}: +{added} → {f.name} ({len(loc)} keys)")


if __name__ == "__main__":
    main()
