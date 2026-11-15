#!/usr/bin/env python3
"""
Full i18n translation (D68b): translate all extracted strings to zh/hi/ja.
Reads extraction.json, batches to LLM, outputs complete translation files.

Usage: pixi run python scripts/i18n_translate.py [--workers 64]
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"
# Pipeline working files live in data/ (not shipped on the website);
# only runtime-fetched files stay in web/public/data/i18n/.
WORKSPACE_DIR = ROOT / "data" / "i18n_workspace"
EXTRACTION = I18N_DIR / "extraction.json"
LOCALES = ["zh", "hi", "ja", "es", "ko"]
LANG_NAMES = {"zh": "Simplified Chinese (中文)", "hi": "Hindi (हिन्दी)", "ja": "Japanese (日本語)", "es": "Spanish (Español)", "ko": "Korean (한국어)"}


def translate_batch(batch, target_lang, url, model):
    """Translate a batch of key→english pairs."""
    input_map = {k: v for k, (v, _) in batch.items()}
    prompt = f"""Translate each English value to {LANG_NAMES[target_lang]}.
Keep scientific terms (H5N1, DNA, gene names like DDX58) in English.
Keep abbreviations as-is. Translate naturally.

Reply ONLY with a JSON object with the SAME keys but translated values:
{{"key": "translated", ...}}

Input:
{json.dumps(input_map, ensure_ascii=False, indent=1)}"""

    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional translator. Reply ONLY with the JSON object."},
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
        print(f"    batch error: {e}")
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=64)
    args = ap.parse_args()

    extraction = json.loads(EXTRACTION.read_text())
    items = {k: (v["english"], v) for k, v in extraction.items()}
    print(f"{len(items)} strings to translate × {len(LOCALES)} languages")

    # Incremental: seed from any existing {lang}_full.json so reruns only
    # fill gaps (batch failures never lose previous coverage)
    translations = {}
    for lang in LOCALES:
        f = WORKSPACE_DIR / f"{lang}_full.json"
        if f.exists():
            try:
                translations[lang] = {k: v for k, v in
                                      json.loads(f.read_text()).items()
                                      if k in items}
            except Exception:
                translations[lang] = {}
        else:
            translations[lang] = {}

    # Split into batches of 25 for LLM — only keys still missing per language
    keys = list(items.keys())

    def work(args_tuple):
        lang, batch_idx, batch = args_tuple
        result = translate_batch(batch, lang, args.url, args.model)
        return lang, batch_idx, result

    jobs = []
    for lang in LOCALES:
        missing_keys = [k for k in keys if k not in translations[lang]]
        for i in range(0, len(missing_keys), 25):
            chunk = missing_keys[i:i+25]
            jobs.append((lang, i,
                         {k: items[k] for k in chunk}))
    if not jobs:
        print("all strings already translated")
        return
    with ThreadPoolExecutor(max_workers=min(args.workers, len(jobs))) as ex:
        for lang, idx, result in ex.map(work, jobs):
            translations[lang].update(result)
            total = sum(len(t) for t in translations.values())
            if total % 100 < len(LOCALES):
                print(f"  progress: {total} translations total")

    # Save
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    for lang in LOCALES:
        out = WORKSPACE_DIR / f"{lang}_full.json"
        out.write_text(json.dumps(translations[lang], indent=1, ensure_ascii=False))
        n = len(translations[lang])
        pct = 100 * n // len(items)
        print(f"  {lang}: {n}/{len(items)} ({pct}%) → {out.name}")

        # Sample
        for key in list(translations[lang])[:3]:
            print(f"    {key}: {translations[lang][key][:50]}")


if __name__ == "__main__":
    main()
