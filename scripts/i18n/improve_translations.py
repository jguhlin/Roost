#!/usr/bin/env python3
"""Context-aware translation improvement pass.

The gap-filler translates bare key→value pairs; without UI context the
model can't always pick the right register or technical sense. This pass
groups keys by PREFIX FAMILY (which maps to a page/section), sends each
group with:
  - where the strings render (curated context per family)
  - the English source
  - the CURRENT translation
and asks for improved translations (accuracy, naturalness, technical
correctness for an avian-influenza research/conservation site).

Only rewrites values that change; strict accept filter (token leakage /
echo / placeholder drift). Resume-safe ledger per locale.

Usage:
  LLM_BASE_URL=http://localhost:8005/v1 \
    pixi run python scripts/i18n/improve_translations.py [--locale es] [--workers 8]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
I18N_DIR = ROOT / "web" / "public" / "data" / "i18n"
EN_DICT = ROOT / "web" / "src" / "lib" / "stores" / "i18n.svelte.js"
LEDGER = ROOT / "data" / "i18n_workspace" / "improve_ledger.jsonl"

LOCALES = ["zh", "hi", "ja", "es", "ko", "fr"]
LANG_NAMES = {
    "zh": "Simplified Chinese (中文)", "hi": "Hindi (हिन्दी)",
    "ja": "Japanese (日本語)", "es": "Spanish (Español)",
    "ko": "Korean (한국어)", "fr": "French (Français)",
}

# prefix family -> UI context for the translator
FAMILY_CONTEXT = {
    "spread.": "Spread-model pages: epidemiological layers, era timeline, "
               "host-competence matrix, corpus synthesis (findings callouts, "
               "introduction events, mammal chains). Scientific register.",
    "susceptibility.": "Species-susceptibility scoring pages: two-axis "
                       "(infection permissiveness vs disease severity) "
                       "methodology and per-species breakdowns.",
    "region.risk.": "Regional-risk page: per-country virus presence, "
                    "watchlists of at-risk species — aimed at conservation "
                    "officers; plain, operational language.",
    "vaccines.": "Vaccine-model pages: platforms, campaign history, outcome "
                 "ledger, protection gaps. Mixed technical/field register.",
    "a11y.": "Screen-reader announcements and accessibility labels — concise, "
             "no jargon, numbers must read naturally when spoken.",
    "model.spread.": "Spread-model graph page: stage/edge evidence counts "
                     "and parameter chips.",
    "units.": "Unit abbreviations (days, months, km/day) — use the "
              "locale's standard scientific unit notation.",
    # --- families added by the 2026-10-30 wiring + data-layer passes ---
    "anp32.": "ANP32 species-barrier page: protein-structure comparisons "
               "of the 33-aa avian insert, per-species insert-length table, "
               "parity cards. Molecular-biology register.",
    "numbers.": "By-the-numbers page: deterministic artifact statistics and "
                "a consistency-check table (check / expected / right / "
                "sources / status columns). 'Right' means the correct "
                "expected value; 'Check' is a verification test name.",
    "model.cyto.": "Interactive pathway-graph controls and legend: layout "
                   "buttons (Pathway/Organic = graph layout modes), node "
                   "labels toggle, presence status chips (present/fragment/"
                   "not found), edge types. 'Center' and 'Fit' are verbs "
                   "(center the view on a gene, fit graph to canvas).",
    "model.": "Infection-response model page: species differences, gene "
              "badges ('{n} papers' = study count), phenotype labels "
              "(Tolerant/Highly susceptible), literature-evidence panels.",
    "genomes.": "Genome-catalog page: assembly levels (Chromosome/Scaffold/"
                "Contig), annotation status, per-species depth. "
                "'Complete genome' is an assembly-level category.",
    "methods.": "Methods/provenance page: pipeline descriptions (gene "
                "presence, paper processing, surveillance aggregation, "
                "text mining, orthology). Technical documentation register.",
    "orthogroups.": "Orthology browser: OrthoFinder run stats, copy-number "
                    "grids, gene trees. Confidence tiers (high/medium/review).",
    "contradictions.": "Literature-contradictions page: adjudicated claim "
                       "clusters. Verdict chips (real = genuine conflict; "
                       "context = context-dependent; apparent = spurious/"
                       "resolved), reason labels (temporal, methodological, "
                       "data age…). Epidemiological register.",
    "history.": "Data-history timeline: KPI labels and chart captions.",
    "mutations.": "Mutation-tracking page: effect sentences, paper counts.",
    "landscape.": "Research-landscape page: briefing/gap/video cards, "
                  "filter chips (Synthesis/Gaps/Conflicts/Open — 'Open' "
                  "means open research questions).",
    "synteny.": "Micro-synteny explorer: conserved gene blocks, strand "
                "markers, legend.",
    "footer.": "Site footer: sustainability statement mentioning locally "
               "hosted LLMs and University of Otago energy commitments.",
}


def family_for(key: str) -> str:
    for prefix in FAMILY_CONTEXT:
        if key.startswith(prefix):
            return prefix
    # longest matching dot-prefix otherwise
    parts = key.split(".")
    for i in range(len(parts) - 1, 0, -1):
        p = ".".join(parts[:i]) + "."
        if p in FAMILY_CONTEXT:
            return p
    return "common UI chrome (navigation, tables, buttons)"


def load_en_dict() -> dict[str, str]:
    src = EN_DICT.read_text()
    out = {}
    pat = re.compile(
        r"^\s*'([a-z0-9_.]+)':\s*('([^']*)'|\"([^\"]*)\"|`([^`]*)`)", re.M)
    for m in pat.finditer(src):
        out[m.group(1)] = next(g for g in m.groups()[2:] if g is not None)
    return out


def acceptable(key, en, val):
    if not val or not isinstance(val, str):
        return False
    if "<|" in val or "```" in val:
        return False
    if val.strip() == en.strip() and len(en.split()) > 1:
        return False  # multi-word exact echo is suspect; single words OK
    if sorted(re.findall(r"\{[a-z]\}", en)) != sorted(
            re.findall(r"\{[a-z]\}", val)):
        return False
    return True


def improve_prompt(lang, family, pairs):
    ctx = FAMILY_CONTEXT.get(family, family)
    payload = json.dumps(
        {k: {"en": v["en"], "current": v["current"]}
         for k, v in pairs.items()}, ensure_ascii=False, indent=1)
    return f"""You are reviewing UI translations for {LANG_NAMES[lang]} on a
scientific web site about avian influenza (H5N1) spread, host susceptibility,
and vaccination — used by researchers AND conservation officers.

SECTION CONTEXT: these strings render in — {ctx}

For each key: improve the {LANG_NAMES[lang]} translation for accuracy,
naturalness, and the correct technical sense in this context. Keep
scientific terms (H5N1, clade 2.3.4.4b, R0, gene symbols, DIVA) in Latin
script. Keep placeholders like {{n}} exactly. If the current translation
is already correct, return it unchanged. Reply ONLY with JSON:
{{"<key>": "<improved translation>", ...}}

Items:
{payload}"""


async def improve_family(client, sem, lang, family, pairs, chunk=25):
    """Large families are chunked — single-shot JSON replies truncate."""
    keys = list(pairs)
    merged = {}
    for i in range(0, len(keys), chunk):
        sub = {k: pairs[k] for k in keys[i:i + chunk]}
        got = await _improve_chunk(client, sem, lang, family, sub)
        if got:
            merged.update(got)
    return family, merged


async def _improve_chunk(client, sem, lang, family, pairs):
    async with sem:
        try:
            r = await client.post(
                f"{os.environ.get('LLM_BASE_URL', 'http://localhost:8005/v1').rstrip('/')}/chat/completions",
                json={"model": os.environ.get("LLM_MODEL", "muse-glimmer-30b"),
                      "messages": [
                          {"role": "system",
                           "content": "You are a professional translator. Reply ONLY with the JSON object."},
                          {"role": "user",
                           "content": improve_prompt(lang, family, pairs)}],
                      "max_tokens": 8000, "temperature": 0.1},
                timeout=600)
            msg = r.json()["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text and msg.get("reasoning_content"):
                m = re.search(r"\{.*\}", msg["reasoning_content"], re.DOTALL)
                if m:
                    text = m.group(0)
            if not text:
                return family, {}
            m = re.search(r"\{.*\}", text, re.DOTALL)
            return json.loads(m.group(0)) if m else {}
        except Exception as e:
            print(f"  {lang}/{family}: chunk error {str(e)[:80]}",
                  file=sys.stderr)
            return {}


async def run(locales, workers):
    en = load_en_dict()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                d = json.loads(line)
                done.add((d["locale"], d["family"], d["hash"]))
            except Exception:
                pass

    sem = asyncio.Semaphore(workers)
    async with httpx.AsyncClient(timeout=600.0) as client:
        for lang in locales:
            f = I18N_DIR / f"{lang}_i18n.json"
            loc = json.loads(f.read_text())
            families = defaultdict(dict)
            for k, cur in loc.items():
                if k not in en:
                    continue
                families[family_for(k)][k] = {"en": en[k], "current": cur}
            tasks = []
            task_keys = {}
            for fam, pairs in families.items():
                h = str(len(pairs))
                if (lang, fam, h) in done:
                    continue
                tasks.append(improve_family(client, sem, lang, fam, pairs))
                task_keys[(lang, fam)] = (fam, h, list(pairs))
            if not tasks:
                print(f"{lang}: families already improved")
                continue
            changed = 0
            for fut in asyncio.as_completed(tasks):
                fam, got = await fut
                meta = task_keys.get((lang, fam))
                if not meta:
                    continue
                _, h, keys = meta
                for k in keys:
                    v = got.get(k)
                    if v is not None and acceptable(k, en[k], v) \
                            and v != loc.get(k):
                        loc[k] = v
                        changed += 1
                with LEDGER.open("a") as lf:
                    lf.write(json.dumps({"locale": lang, "family": fam,
                                         "hash": h,
                                         "accepted": changed}) + "\n")
            f.write_text(json.dumps(loc, ensure_ascii=False, indent=1))
            print(f"{lang}: reviewed {len(task_keys)} families, "
                  f"{changed} translations improved → {f.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locale", action="append")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    locales = args.locale or LOCALES
    asyncio.run(run(locales, args.workers))


if __name__ == "__main__":
    main()
