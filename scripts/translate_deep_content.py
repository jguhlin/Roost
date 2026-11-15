#!/usr/bin/env python3
"""
Deep content translation (D69): translate gene functions, model descriptions,
evidence labels, species labels into all languages including French.

Usage: pixi run python scripts/translate_deep_content.py [--workers 64]
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"
# Input lives in the interior workspace (data/), never shipped; translated
# {lang}_content.json output stays in I18N_DIR (fetched at runtime).
CONTENT = ROOT / "data" / "i18n_workspace" / "content_extract.json"

LOCALES = ["zh", "hi", "ja", "fr", "es", "ko"]
LANG_NAMES = {
    "zh": "Simplified Chinese (中文)",
    "hi": "Hindi (हिन्दी)",
    "ja": "Japanese (日本語)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",   # added 2026-10-30: KeyError on es/ko aborted
    "ko": "Korean (한국어)",      # the run before es/ko content files were written
}


def translate_batch(batch, target_lang, url, model):
    input_map = dict(batch)
    prompt = f"""Translate each English value to {LANG_NAMES[target_lang]}.

Rules:
- Keep gene symbols (DDX58, IFIH1, MX1, etc.) in English
- Keep scientific abbreviations (H5N1, HPAI, IFN, MHC, DNA, RNA, BLAST, DIAMOND) as-is
- Translate the MEANING, not word-for-word
- Keep translations concise (similar length to original)

Reply ONLY with a JSON object with the SAME keys but translated values.

Input:
{json.dumps(input_map, ensure_ascii=False, indent=1)}"""

    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional scientific translator. Reply ONLY with the JSON object."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4000, "temperature": 0.1,
        }, timeout=300)
        msg = r.json()["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text and msg.get("reasoning_content"):
            rc = msg["reasoning_content"].strip()
            m = re.search(r'\{.*\}', rc, re.DOTALL)
            if m:
                text = m.group(0)
        if text:
            m = re.search(r'\{.*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
    except Exception as e:
        print(f"    batch error: {str(e)[:60]}")
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--locales", default=None, help="comma-separated subset of locales (default: all)")
    args = ap.parse_args()
    locales = [l.strip() for l in args.locales.split(",")] if args.locales else LOCALES

    content = json.loads(CONTENT.read_text())
    items = list(content.items())
    print(f"{len(items)} strings × {len(LOCALES)} languages = {len(items) * len(LOCALES)} translations")

    # Split into batches of 20
    batches = [(items[i:i+20]) for i in range(0, len(items), 20)]

    # Generate jobs
    jobs = [(lang, i, batch) for lang in locales for i, batch in enumerate(batches)]

    def work(job):
        lang, idx, batch = job
        batch_dict = {k: v for k, v in batch}
        result = translate_batch(batch_dict, lang, args.url, args.model)
        return lang, idx, result

    translations = {lang: {} for lang in locales}
    with ThreadPoolExecutor(max_workers=min(args.workers, len(jobs))) as ex:
        for i, (lang, idx, result) in enumerate(ex.map(work, jobs), 1):
            translations[lang].update(result)
            if i % 20 == 0 or i == len(jobs):
                total = sum(len(t) for t in translations.values())
                print(f"  [{i}/{len(jobs)} batches] {total} translations done")

    # Save
    for lang in locales:
        out = I18N_DIR / f"{lang}_content.json"
        out.write_text(json.dumps(translations[lang], indent=1, ensure_ascii=False))
        n = len(translations[lang])
        pct = 100 * n // len(items)
        print(f"  {lang}: {n}/{len(items)} ({pct}%)")

        # Sample
        for key in ['gene.DDX58.function', 'evidence.status.full', 'model.spread.reservoir.desc']:
            if key in translations[lang]:
                print(f"    {key}: {translations[lang][key][:60]}")


if __name__ == "__main__":
    main()
