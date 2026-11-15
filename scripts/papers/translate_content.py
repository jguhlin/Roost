#!/usr/bin/env python3
"""Content-layer translation: model stages, node notes, gene functions, methods.

Extracts all translatable content from data files, compares against existing
translations per locale, and translates what's missing with full context.

Content sources:
  - data/model/avian_h5n1_model.json (infection stages, node notes)
  - data/model/h5n1_spread_model.json (spread stages, additions)
  - data/model/h5n1_vaccine_model.json (vaccine pipeline stages)
  - data/genes/gene_functions.json (per-gene function descriptions)
  - data/model/ methods text (if present)

Output: web/public/data/i18n/{lang}_content.json (or {lang}.json for ko/es
which use a single file).

Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python \
    scripts/papers/translate_content.py [--dry-run] [--limit N]
"""
import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "web/public/data/i18n"
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")

GLOSSARY = """Product: Roost — scientific resource on avian influenza (HPAI/H5N1)
host genomics for researchers. Content includes infection model stages,
immune gene functions, spread ecology, and vaccine pipeline descriptions.
Korean: genome=유전체, host=숙주, IFN=인터페론, spillover=종간 감염.
Chinese: genome=基因组, host=宿主, IFN=干扰素, spillover=跨物种传播.
Translate as a native immunologist/virologist would write it. Formal register.
Gene symbols (DDX58, ANP32A, MX1) and species names stay in Latin/English.
Clade designations (2.3.4.4b) and HA/NA subtypes stay as-is."""

SYSTEM = ("You are a bilingual scientific content translator specializing in "
          "avian immunology and virology. " + GLOSSARY +
          " Return ONLY a JSON object mapping key to translated string. "
          "No reasoning, no commentary.")


def llm(prompt, max_tokens=6144):
    body = json.dumps({"model": MODEL, "temperature": 0.1,
                       "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        msg = json.loads(r.read())["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    if not text:
        rc = (msg.get("reasoning_content") or "").strip()
        s, e = rc.find("{"), rc.rfind("}")
        text = rc[s:e + 1] if 0 <= s < e else ""
    return text


def parse_obj(raw):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("{"), raw.rfind("}")
        try:
            return json.loads(raw[s:e + 1]) if 0 <= s < e else {}
        except:
            return {}


def extract_content():
    """Extract all translatable content with contextual keys."""
    items = {}  # key -> {"en": ..., "context": ...}

    # 1. Infection model
    m1 = json.loads((ROOT / "data/model/avian_h5n1_model.json").read_text())
    for i, stage in enumerate(m1.get("stages", [])):
        sname = stage.get("name", stage.get("stage", f"stage_{i}"))
        sid = stage.get("id", f"inf_stage_{i}")
        items[f"model.inf.stage.{sid}.name"] = {
            "en": sname, "context": f"Infection model stage {i+1}"}
        if stage.get("description"):
            items[f"model.inf.stage.{sid}.desc"] = {
                "en": stage["description"][:400],
                "context": f"Description of infection model stage: {sname}"}
        for el in stage.get("elements", []):
            if isinstance(el, dict):
                sym = el.get("gene") or el.get("symbol") or el.get("node", "")
                if not sym:
                    continue
                if el.get("note") or el.get("description"):
                    items[f"model.inf.{sym}.note"] = {
                        "en": (el.get("note") or el.get("description", ""))[:400],
                        "context": f"Node note for {sym} in stage {sname}"}

    # 2. Spread model
    m2 = json.loads((ROOT / "data/model/h5n1_spread_model.json").read_text())
    for i, stage in enumerate(m2.get("stages", [])):
        sname = stage.get("name", stage.get("stage", ""))
        sid = stage.get("id", f"spread_stage_{i}")
        items[f"model.spread.stage.{sid}.name"] = {
            "en": sname, "context": f"Spread model stage"}
        if stage.get("description"):
            items[f"model.spread.stage.{sid}.desc"] = {
                "en": stage["description"][:400],
                "context": f"Description of spread model stage: {sname}"}
    for a in m2.get("additions", []):
        topic = a.get("topic", a.get("id", ""))
        if a.get("description"):
            items[f"model.spread.addition.{topic}.desc"] = {
                "en": a["description"][:400],
                "context": f"New evidence addition: {topic}"}

    # 3. Vaccine model
    m3 = json.loads((ROOT / "data/model/h5n1_vaccine_model.json").read_text())
    for i, stage in enumerate(m3.get("stages", [])):
        sname = stage.get("name", stage.get("stage", ""))
        sid = stage.get("id", f"vac_stage_{i}")
        items[f"model.vac.stage.{sid}.name"] = {
            "en": sname, "context": "Vaccine pipeline stage"}

    # 4. Gene functions
    gf = json.loads((ROOT / "data/genes/gene_functions.json").read_text())
    for sym, desc in gf.items():
        if isinstance(desc, str) and len(desc) > 20:
            items[f"gene.function.{sym}"] = {
                "en": desc[:500], "context": f"Function of {sym} (immune/host gene)"}

    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    content = extract_content()
    print(f"translatable content items: {len(content)}")

    lang_names = {"zh": "Simplified Chinese", "ko": "Korean", "ja": "Japanese",
                  "fr": "French", "es": "Spanish", "hi": "Hindi"}

    for lang in ["zh", "ko", "ja", "fr", "es", "hi"]:
        # load existing translations (both content and general files)
        existing = {}
        for suffix in ["_content.json", ".json"]:
            p = I18N / f"{lang}{suffix}"
            if p.exists():
                existing.update(json.loads(p.read_text()))

        # find what's missing or might be stale (content changed since translation)
        todo = {k: v for k, v in content.items()
                if k not in existing or not existing.get(k)}
        if args.limit:
            todo = dict(list(todo.items())[:args.limit])
        if not todo:
            print(f"\n{lang}: complete ({len(existing)} translations)")
            continue

        print(f"\n{lang}: {len(todo)} items to translate")

        # translate in batches of 10
        output_file = I18N / f"{lang}_content.json"
        if lang in ("ko", "es"):  # these use a single file
            output_file = I18N / f"{lang}.json"
        current = json.loads(output_file.read_text()) if output_file.exists() else {}

        items_list = list(todo.items())
        for i in range(0, len(items_list), 10):
            batch = dict(items_list[i:i + 10])
            prompt_parts = []
            for key, info in batch.items():
                prompt_parts.append(f"KEY: {key}\nCONTEXT: {info['context']}\n"
                                    f"ENGLISH: {info['en']}")
            prompt = (f"Target language: {lang_names[lang]}.\n\n"
                      + "\n---\n".join(prompt_parts)
                      + "\n\nReturn a JSON object: {key: translation}")
            try:
                result = parse_obj(llm(prompt))
            except Exception as e:
                print(f"  batch {i // 10 + 1}: error {str(e)[:60]}")
                time.sleep(1)
                continue
            for key, translated in result.items():
                if key in batch and translated:
                    current[key] = translated
            output_file.write_text(json.dumps(current, ensure_ascii=False, indent=1))
            done = min(i + 10, len(items_list))
            print(f"  {done}/{len(items_list)} translated", flush=True)

        print(f"{lang}: {len(current)} total content translations")


if __name__ == "__main__":
    main()
