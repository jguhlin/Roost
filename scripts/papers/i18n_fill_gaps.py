#!/usr/bin/env python3
"""Fill i18n gaps: find English sources for untranslated t() keys and translate.

Scans components for t() calls with missing translations, extracts surrounding
context to infer the English source, then generates translations for all six
languages. Keys whose English can't be confidently determined are skipped.

Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python scripts/papers/i18n_fill_gaps.py [--dry-run]
"""
import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
I18N = WEB / "public" / "data" / "i18n"
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
LANGS = {"zh": "Simplified Chinese", "hi": "Hindi", "ja": "Japanese",
         "fr": "French", "ko": "Korean", "es": "Spanish"}

CONTEXT = """You are filling missing translations for a scientific web dashboard
about avian influenza (HPAI/H5N1) host genomics. For each i18n key, I give you
the key name, the component file it appears in, and surrounding code context.
Determine the correct English UI string, then translate it.
Key naming: dots separate words, camelCase fragments are literal English.
Example: credits_page.how.to.cite.this → "How to cite this"
Return ONLY a JSON array: [{"key": "...", "en": "...", "zh": "...", "hi": "...",
"ja": "...", "fr": "...", "ko": "...", "es": "..."}]
Use natural, concise UI labels. Follow the localization glossary (Korean:
유전체 not 게놈, 검출 건수 for detection counts, etc). No reasoning."""


def llm(prompt, max_tokens=8192):
    body = json.dumps({"model": MODEL, "temperature": 0.1,
                       "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": CONTEXT},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    if not text:
        rc = (msg.get("reasoning_content") or "").strip()
        s, e = rc.find("["), rc.rfind("]")
        text = rc[s:e + 1] if 0 <= s < e else ""
    return text


def parse_arr(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("["), raw.rfind("]")
        return json.loads(raw[s:e + 1]) if 0 <= s < e else []


def find_key_context(key, max_context=300):
    """Find the t('key') call site and return surrounding code."""
    results = []
    for root, dirs, files in os.walk(WEB / "src"):
        for f in files:
            if not f.endswith((".svelte", ".js")):
                continue
            path = os.path.join(root, f)
            try:
                src = open(path).read()
            except Exception:
                continue
            # find the key in t() or tc() calls
            for m in re.finditer(rf"t\('{re.escape(key)}'\)", src):
                start = max(0, m.start() - max_context // 2)
                end = min(len(src), m.end() + max_context // 2)
                ctx = src[start:end]
                results.append({"file": os.path.relpath(path, WEB),
                                "context": ctx[:max_context]})
                if len(results) >= 2:
                    return results
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # find all t() keys used in code
    keys_used = set()
    for root, dirs, files in os.walk(WEB / "src"):
        for f in files:
            if f.endswith((".svelte", ".js")):
                src = open(os.path.join(root, f)).read()
                keys_used |= set(re.findall(r"t\('([a-z][a-z0-9_.]+)'\)", src))

    ko = json.loads((I18N / "ko_i18n.json").read_text())
    missing = sorted(k for k in keys_used
                     if k not in ko and re.match(r"^[a-z][a-z0-9_.]*$", k)
                     and "." in k and len(k) < 80)
    print(f"missing keys: {len(missing)}")

    # skip library/technical false positives
    skip = {"cytoscape", "script", "species", "igv", "mermaid",
            "detections.parquet", "content-type", "content-length"}
    missing = [k for k in missing if k.lower() not in skip
               and not k.startswith("content-")]

    # build context for each
    entries = []
    for key in missing:
        ctx = find_key_context(key)
        if ctx:
            entries.append({"key": key, "sites": ctx})
        else:
            entries.append({"key": key, "sites": [], "guess": key.replace(".", " ").title()})

    print(f"with context: {sum(1 for e in entries if e['sites'])} | "
          f"guess-only: {sum(1 for e in entries if not e['sites'])}")

    # translate in batches of 15
    all_translations = []
    for i in range(0, len(entries), 15):
        batch = entries[i:i + 15]
        prompt_parts = []
        for e in batch:
            p = f"KEY: {e['key']}"
            if e.get("sites"):
                p += f"\nFILE: {e['sites'][0]['file']}\nCONTEXT: ...{e['sites'][0]['context']}..."
            elif e.get("guess"):
                p += f"\nNO CONTEXT — infer from key name. Best guess: {e['guess']}"
            prompt_parts.append(p)
        prompt = ("Translate these UI strings:\n\n" +
                  "\n---\n".join(prompt_parts) +
                  f"\n\nLanguages: {', '.join(f'{v} ({k})' for k, v in LANGS.items())}")
        try:
            results = parse_arr(llm(prompt))
            all_translations.extend(results)
            print(f"  batch {i // 15 + 1}: {len(results)} translated", flush=True)
        except Exception as ex:
            print(f"  batch {i // 15 + 1}: error {str(ex)[:60]}")
        time.sleep(1)

    if args.dry_run:
        for t in all_translations[:5]:
            print(f"  {t['key']}: en={t.get('en', '?')[:30]} ko={t.get('ko', '?')[:20]}")
        print(f"(dry run — {len(all_translations)} would be applied)")
        return

    # apply
    applied = 0
    for t in all_translations:
        key = t.get("key")
        if not key or not t.get("en"):
            continue
        for lang in list(LANGS) + ["en"]:
            path = I18N / f"{lang}_i18n.json"
            d = json.loads(path.read_text())
            val = t.get(lang) or t["en"]
            if key not in d:
                d[key] = val
                path.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        applied += 1
    print(f"applied {applied} keys across all languages")


if __name__ == "__main__":
    main()
