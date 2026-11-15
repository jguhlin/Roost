#!/usr/bin/env python3
"""
Full LLM translation pass (D67): translate ALL UI strings, model descriptions,
methods text, and page content into zh, hi, ja. Outputs complete translation
files for each locale.

Usage: pixi run python scripts/translate_all.py [--workers 64]
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
WEB = ROOT / "web" / "public" / "data"
I18N = ROOT / "web" / "src" / "lib" / "stores" / "i18n.svelte.js"

LOCALES = ["zh", "hi", "ja"]
LANG_NAMES = {"zh": "Simplified Chinese (中文)", "hi": "Hindi (हिन्दी)", "ja": "Japanese (日本語)"}


def call_llm(prompt, url, model, max_tokens=4000):
    try:
        r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional scientific/technical translator. Reply ONLY with a valid JSON object mapping English keys to translations. No other text."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens, "temperature": 0.1,
        }, timeout=300)
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
        print(f"    LLM error: {e}")
    return {}


def collect_strings():
    """Collect ALL strings that need translation."""
    strings = {}

    # 1. i18n keys (from the English translations)
    # Parse the i18n.svelte.js to extract en translations
    src = I18N.read_text()
    en_match = re.search(r"en:\s*\{(.*?)\n\s*\},", src, re.DOTALL)
    if en_match:
        for m in re.finditer(r"'([^']+)':\s*'([^']+)'", en_match.group(1)):
            key, val = m.group(1), m.group(2)
            strings[f"i18n.{key}"] = val

    # 2. Model stage descriptions
    inf = json.loads((ROOT / "data/model/avian_h5n1_model.json").read_text())
    for stage in inf.get("stages", []):
        strings[f"model.inf.{stage['id']}.title"] = stage["title"]
        strings[f"model.inf.{stage['id']}.desc"] = stage["desc"]
    for axis in inf.get("axes", []):
        strings[f"model.inf.axis.{axis['id']}.title"] = axis["title"]
        strings[f"model.inf.axis.{axis['id']}.desc"] = axis["desc"]

    # 3. Spread model
    spread = json.loads((ROOT / "data/model/h5n1_spread_model.json").read_text())
    for stage in spread.get("stages", []):
        strings[f"model.spread.{stage['id']}.title"] = stage["title"]
        strings[f"model.spread.{stage['id']}.desc"] = stage["desc"]

    # 4. Methods page descriptions (from the Svelte source)
    methods_src = (ROOT / "web/src/routes/Methods.svelte").read_text()
    for m in re.finditer(r'<p class="text-sm[^"]*text-gray[^"]*[^>]*>\s*(?:\{#if[^}]+\})?\s*([^<]{40,300})', methods_src):
        text = m.group(1).strip()
        if not text.startswith("{") and not text.startswith("@"):
            key = f"methods.{len(strings):03d}"
            strings[key] = text

    # 5. Common UI strings from various pages
    extras = {
        "common.search_species": "Search species…",
        "common.search_genes": "Search genes…",
        "common.search_papers": "Search papers…",
        "common.detected_only": "Detected only",
        "common.all_species": "All species",
        "common.gene_panel": "Gene Panel",
        "common.full_page": "Full page",
        "common.view_all": "View all genes",
        "common.critical": "critical",
        "common.high": "high",
        "common.present": "Present",
        "common.fragment": "Fragment",
        "common.not_found": "Not found",
        "common.annotated": "Annotated",
        "common.search_found": "Search-found",
        "common.loading_dots": "loading…",
        "common.no_results": "No results",
        "common.clear_all": "clear all",
        "common.showing": "Showing",
        "common.of_total": "of",
        "common.total": "total",
        "common.infection_model": "Infection Model",
        "common.spread_model": "Spread Model",
        "common.gap_registry": "Gap Registry",
        "common.disagreements": "Where the literature disagrees",
        "common.sensor_matrix": "Sensor Matrix",
        "common.evidence": "Evidence",
        "common.critical_absences": "Critical gene absences",
        "common.no_detections": "No HPAI detections recorded",
        "common.no_genome": "No genome available",
        "common.birdseye": "Bird's-eye view",
        "common.detailed_list": "Detailed list",
        "common.compact": "Compact",
        "common.genome_context": "Genome context",
        "common.inspect_evidence": "Inspect the raw evidence",
        "common.threshold_applied": "Thresholds applied",
        "common.where_literature_disagrees": "Where the literature disagrees",
        "common.not_yet_covered": "Not yet covered by our paper corpus",
        "common.gap_registry_desc": "Lit-search targets vs true gaps",
        "common.evidence_ladder": "Evidence ladder",
    }
    strings.update(extras)

    return strings


def translate_batch(strings, target_lang, url, model):
    """Translate a batch of strings to target language."""
    # Limit batch size to stay in context
    items = list(strings.items())
    batches = [items[i:i+30] for i in range(0, len(items), 30)]
    results = {}

    for batch in batches:
        input_json = json.dumps({k: v for k, v in batch}, ensure_ascii=False, indent=1)
        prompt = f"""Translate each English value to {LANG_NAMES[target_lang]}.
Keep scientific gene names (DDX58, IFIH1, MX1, etc.) in English.
Keep abbreviations like H5N1, HPAI, IFN, MHC as-is.
Translate naturally, not word-for-word.

Reply ONLY with a JSON object with the SAME keys but translated values:
{{"key": "translated value", ...}}

Input:
{input_json}"""

        got = call_llm(prompt, url, model)
        if got:
            results.update(got)

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8005/v1")
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=64)
    args = ap.parse_args()

    # Collect all strings
    strings = collect_strings()
    print(f"Collected {len(strings)} strings to translate")

    # Translate to each language in parallel
    def work(lang):
        return lang, translate_batch(strings, lang, args.url, args.model)

    translations = {}
    with ThreadPoolExecutor(max_workers=len(LOCALES)) as ex:
        for lang, result in ex.map(work, LOCALES):
            translations[lang] = result
            n = len(result)
            print(f"  {lang}: {n}/{len(strings)} translated ({100*n//len(strings)}%)")

    # Save translation files
    out_dir = ROOT / "web" / "public" / "data" / "i18n"
    out_dir.mkdir(parents=True, exist_ok=True)

    for lang, result in translations.items():
        # Split into i18n keys vs content translations
        i18n_keys = {}
        content_keys = {}
        for key, val in result.items():
            if key.startswith("i18n."):
                i18n_keys[key[5:]] = val  # strip "i18n." prefix
            else:
                content_keys[key] = val

        # Save content translations
        content_file = out_dir / f"{lang}.json"
        content_file.write_text(json.dumps(content_keys, indent=1, ensure_ascii=False))

        # Save i18n translations for the store
        i18n_file = out_dir / f"{lang}_i18n.json"
        i18n_file.write_text(json.dumps(i18n_keys, indent=1, ensure_ascii=False))

        print(f"  → {content_file} ({len(content_keys)} content keys)")
        print(f"  → {i18n_file} ({len(i18n_keys)} i18n keys)")

    print("\nDone. Translation files in web/public/data/i18n/")


if __name__ == "__main__":
    main()
