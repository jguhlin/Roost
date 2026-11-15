#!/usr/bin/env python3
"""Refinement sweep: re-localize ALL existing UI strings per locale.

Runs each locale's full key set through the upgraded native-localizer
prompt (anti-calque, counting nouns, academic register) in batches.
Only overwrites when the model returns a value for a known key; keys are
validated against the current file so nothing can be dropped or renamed.
Before/after diffs are logged to i18n_refinement_log.json for review.

Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python \
    scripts/papers/i18n_refine.py [--langs ko,zh,hi,ja,fr,es] [--limit N]
"""
import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "web/public/data/i18n"
BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")
LANG_NAMES = {"zh": "Simplified Chinese", "hi": "Hindi", "ja": "Japanese",
              "fr": "French", "ko": "Korean", "es": "Spanish"}

CONTEXT = """
PRODUCT: Roost — a scientific dashboard on highly pathogenic avian influenza
(HPAI/H5N1) in birds and mammal spillover hosts: detection records, host
species, genomes, gene presence/absence, literature synthesis. AUDIENCE:
virologists, ecologists, genomicists, surveillance officials. TONE: formal
academic/technical UI — concise labels, complete sentences in descriptions.
Stat labels are COUNT LABELS (a number follows), so use counting nouns.
USAGE by key prefix: nav.* = 1-2 word navigation; stats.* = KPI count
labels; home.* = landing cards; <page>.* = titles/sections/tooltips.
Follow docs/I18N_GLOSSARY.md terminology for your language (key rules
inlined below):
ko: genome=유전체; Detections=검출 건수; affected species=감염 종; most
affected=최다 감염 종; mammals=포유류 (+n종); Map=분포 지도; host=숙주;
reservoir=저장 숙주; spillover=종간 감염.
ja: 検出数/感染種/宿主/保有宿主/遺伝子の有無.
zh: 检测数/感染物种/宿主/储存宿主/跨物种传播/基因存在缺失.
fr: détections/espèces infectées/hôte/réservoir/transmission inter-espèces.
es: detecciones/especies infectadas/hospedador/reservorio/transmisión entre
especies.
Keep BLAST/HPAI/H5N1/IUCN untranslated. Preserve {placeholders} exactly.
"""

SYSTEM = (
    CONTEXT + " You are a native scientific-UI localizer producing a professional "
    "translation of a research dashboard. Re-localize each English source "
    "string so it reads naturally and natively — NOT as literal translation. "
    "Rules: avoid calques; use counting nouns for stat labels (Korean: "
    "검출 건수 not bare 검출); prefer standard academic terminology over "
    "loanwords (Korean: 유전체 not 게놈; map=분포 지도); keep proper nouns "
    "(BLAST, H5N1, HPAI) as-is; preserve {placeholders} and HTML exactly; "
    "keep translations concise (UI labels). If the existing translation is "
    "already natural, return it unchanged. Return ONLY a JSON object "
    "mapping key -> improved translation. No reasoning, no commentary."
)


def llm(prompt):
    body = json.dumps({"model": MODEL, "temperature": 0.1, "max_tokens": 6144,
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
        return json.loads(raw[s:e + 1]) if 0 <= s < e else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="ko,zh,hi,ja,fr,es")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    en = json.loads((I18N / "en_i18n.json").read_text()) if (I18N / "en_i18n.json").exists() else {}
    if not en:  # fall back to keys from ko file structure
        en = {k: "" for k in json.loads((I18N / "ko_i18n.json").read_text())}
    log = {}
    for lang in args.langs.split(","):
        path = I18N / f"{lang}_i18n.json"
        cur = json.loads(path.read_text())
        keys = sorted(cur.keys())
        if args.limit:
            keys = keys[:args.limit]
        changed = 0
        log[lang] = []
        for i in range(0, len(keys), 60):
            batch = keys[i:i + 60]
            payload = {k: {"source": en.get(k) or cur[k], "current": cur[k]} for k in batch}
            prompt = (f"Target language: {LANG_NAMES.get(lang, lang)}.\n"
                      f"Existing translations (English source or current value):\n"
                      + json.dumps(payload, ensure_ascii=False)
                      + "\nReturn the improved JSON object for these keys.")
            try:
                out = parse_obj(llm(prompt))
            except Exception as e:
                print(f"  {lang} batch {i//60}: error {str(e)[:60]}")
                time.sleep(2)
                continue
            for k, v in out.items():
                v = str(v)
                if k in cur and v and v != cur[k] and ("{n}" in cur[k]) == ("{n}" in v):
                    log[lang].append({"key": k, "before": cur[k], "after": v})
                    cur[k] = v
                    changed += 1
            path.write_text(json.dumps(cur, ensure_ascii=False, indent=1))
            print(f"  {lang}: {min(i+60, len(keys))}/{len(keys)} (+{changed} refined)", flush=True)
        print(f"{lang}: {changed} strings refined of {len(keys)}")
    (I18N / "i18n_refinement_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=1))
    print("diff log -> web/public/data/i18n/i18n_refinement_log.json")


if __name__ == "__main__":
    main()
