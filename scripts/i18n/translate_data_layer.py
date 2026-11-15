#!/usr/bin/env python3
"""Data-layer translation (2026-10-30): translate corpus-adjacent English that
renders on data-heavy pages into the papers/{lang}.json maps and
{lang}_content.json content layer.

Sources (all finite, hashed or keyed):
  1. mutation effect sentences  → papers/{lang}.json findings  (eh = md5[:12])
  2. wiki-gene role sentences   → papers/{lang}.json roles     (fh = md5[:12])
  3. paper topic vocabulary     → papers/{lang}.json topics
  4. avian-model stage text     → {lang}_content.json model.stage.{id}.{title,desc,note}
  5. vaccine-model stage text   → {lang}_content.json vaccine.stage.{id}.{title,desc}

Doctrine accept-filter (same as fill_locale_gaps): no token leakage, no
English echo (cognates allowed), no {placeholder} drift. Resume-safe: existing
keys are never re-translated. JSON-map outputs merge in place.

Usage:
  LLM_BASE_URL=http://localhost:8005/v1 pixi run python scripts/i18n/translate_data_layer.py [--workers 8] [--batch 20]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web" / "public" / "data"
I18N = WEB / "i18n"

LOCALES = ["zh", "hi", "ja", "es", "ko", "fr"]
LANG_NAMES = {
    "zh": "Simplified Chinese (中文)",
    "hi": "Hindi (हिन्दी)",
    "ja": "Japanese (日本語)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "ko": "Korean (한국어)",
}


def h12(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def collect_jobs() -> dict[str, dict[str, str]]:
    """Return {target_map: {key: english}} for every untranslated entry.

    target_map naming: 'papers:<lang>:<section>' or 'content:<lang>'.
    """
    jobs: dict[str, dict[str, str]] = {}
    muts = json.loads((WEB / "wiki_mutations.json").read_text())["mutations"]
    effects: dict[str, str] = {}
    for e in muts.values():
        if not isinstance(e, dict):
            continue
        for p in e.get("papers", []):
            if isinstance(p, dict) and p.get("effect"):
                eh = p.get("eh") or h12(p["effect"])
                effects.setdefault(eh, p["effect"])

    wg = json.loads((WEB / "wiki_genes.json").read_text())
    roles: dict[str, str] = {}
    for g in wg["genes"].values():
        if isinstance(g, dict):
            for r in g.get("roles") or []:
                if isinstance(r, dict) and r.get("role"):
                    roles.setdefault(r.get("fh") or h12(r["role"]), r["role"])

    papers = json.loads((WEB / "papers.json").read_text())
    papers = papers["papers"] if isinstance(papers, dict) and "papers" in papers else papers
    topics: dict[str, str] = {}
    for p in papers:
        for tp in p.get("topics") or []:
            topics.setdefault(tp, tp)

    model_stages: dict[str, str] = {}
    am = json.loads((WEB / "avian_h5n1_model.json").read_text())
    for s in am["stages"]:
        for field in ("title", "desc", "note"):
            if s.get(field):
                model_stages[f"model.stage.{s['id']}.{field}"] = s[field]

    vax_stages: dict[str, str] = {}
    vm = json.loads((WEB / "h5n1_vaccine_model.json").read_text())
    for s in vm["stages"]:
        for field in ("title", "desc"):
            if s.get(field):
                vax_stages[f"vaccine.stage.{s['id']}.{field}"] = s[field]

    contradictions: dict[str, str] = {}
    cx = json.loads((WEB / "papers" / "contradictions.json").read_text())
    for x in cx.get("contradictions", []):
        for field, key in (("topic", "th"), ("what", "wh"), ("explanation", "ex")):
            if x.get(field):
                contradictions.setdefault(x.get(key) or h12(x[field]), x[field])

    briefings: dict[str, str] = {}
    try:
        bidx = json.loads((WEB / "research_briefings" / "index.json").read_text())
        for b in bidx:
            for field, key in (("title", "th"), ("summary", "sh")):
                if b.get(field):
                    briefings.setdefault(b.get(key) or h12(b[field]), b[field])
    except FileNotFoundError:
        pass

    vax_claims: dict[str, str] = {}
    vmj = json.loads((WEB / "h5n1_vaccine_model.json").read_text())
    for s in vmj.get("stages", []):
        for c in (s.get("claims_resolved") or []):
            if c.get("claim"):
                vax_claims.setdefault(c.get("ch") or h12(c["claim"]), c["claim"])

    mechanism_effects: dict[str, str] = {}
    pe = json.loads((WEB / "pathway_edges.json").read_text())
    for e in pe.get("edges", []):
        if e.get("effect"):
            mechanism_effects.setdefault(e.get("eh") or h12(e["effect"]), e["effect"])
    for gf in (WEB / "gene_evidence").glob("*.json"):
        try:
            gd = json.loads(gf.read_text())
        except json.JSONDecodeError:
            continue
        for m in gd.get("mechanisms") or []:
            if m.get("effect"):
                mechanism_effects.setdefault(m.get("eh") or h12(m["effect"]), m["effect"])

    for lang in LOCALES:
        papers_map = json.loads((I18N / "papers" / f"{lang}.json").read_text())
        for section, source in (("findings", effects), ("roles", roles), ("topics", topics), ("findings", contradictions), ("findings", briefings), ("findings", vax_claims), ("findings", mechanism_effects)):
            have = papers_map.get(section) or {}
            todo = {k: v for k, v in source.items() if not have.get(k)}
            if todo:
                tgt = f"papers:{lang}:{section}"
                jobs[tgt] = {**jobs.get(tgt, {}), **todo}
        content_map = json.loads((I18N / f"{lang}_content.json").read_text())
        for source in (model_stages, vax_stages):
            todo = {k: v for k, v in source.items() if not content_map.get(k)}
            if todo:
                jobs[f"content:{lang}"] = {**jobs.get(f"content:{lang}", {}), **todo}
    return jobs


PLACEHOLDER = re.compile(r"\{[a-z0-9_]+\}")


def acceptable(en: str, val: str) -> bool:
    if not val or not isinstance(val, str):
        return False
    if "<|" in val or "assistant" in val.lower()[:40] or "```" in val:
        return False
    if val.strip() == en.strip():
        return False
    # placeholder drift
    if sorted(PLACEHOLDER.findall(en)) != sorted(PLACEHOLDER.findall(val)):
        return False
    # rough cognate allow: ≥55% shared ascii-lowercased tokens is fine only
    # when the value contains non-ascii (a real translation) — pure-ascii
    # echo-ish outputs are rejected unless clearly shorter/different words
    if val.isascii() and lang_is_cjk_like(en, val) is False:
        # allow ascii for hi/zh-less locales only if it differs meaningfully
        if len(set(val.lower().split()) & set(en.lower().split())) > max(1, 0.8 * len(en.split())):
            return False
    return True


def lang_is_cjk_like(en: str, val: str) -> bool:  # placeholder, never True here
    return False


def translate_batch(batch: dict[str, str], lang: str, url: str, model: str) -> dict[str, str]:
    prompt = f"""Translate each English value to {LANG_NAMES[lang]}.

Rules:
- Keep gene symbols (DDX58, IFIH1, MX1, PB2, HA, NS1…), virus nomenclature (H5N1, HPAI, clade 2.3.4.4b), abbreviations (IFN, MHC, DNA, RNA, BLAST) and Latin species names verbatim
- Translate the MEANING, not word-for-word; keep scientific register
- Keep values roughly similar in length to the original
- Preserve any {{placeholder}} tokens exactly

Reply ONLY with a JSON object with the SAME keys and translated values."""
    numbered = json.dumps(batch, ensure_ascii=False)
    r = httpx.post(
        f"{url}/chat/completions",
        json={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You are a precise scientific translator. Output valid JSON only."},
                {"role": "user", "content": prompt + "\n\n" + numbered},
            ],
        },
        timeout=300,
    )
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    text = msg.get("content") or ""
    if not text and msg.get("reasoning_content"):
        rc = msg["reasoning_content"].strip()
        m = re.search(r"\{.*\}", rc, re.S)
        if m:
            text = m.group(0)
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return {k: v for k, v in out.items() if isinstance(v, str)} if isinstance(out, dict) else {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1"))
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()

    jobs = collect_jobs()
    if not jobs:
        print("nothing to do — all sources translated")
        return
    total = sum(len(v) for v in jobs.values())
    print(f"{total} strings across {len(jobs)} targets")
    for tgt, todo in sorted(jobs.items()):
        print(f"  {tgt}: {len(todo)}")

    work = []
    for tgt, todo in jobs.items():
        items = list(todo.items())
        for i in range(0, len(items), args.batch):
            work.append((tgt, dict(items[i : i + args.batch])))

    def run(item):
        tgt, batch = item
        lang = tgt.split(":")[1]
        try:
            out = translate_batch(batch, lang, args.url, args.model)
        except Exception as e:
            return tgt, {}, f"request failed: {type(e).__name__}: {e}"
        accepted = {}
        for k, en in batch.items():
            v = out.get(k, "")
            if acceptable(en, v):
                accepted[k] = v
        return tgt, accepted, None

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (tgt, accepted, err) in enumerate(ex.map(run, work), 1):
            results.setdefault(tgt, {}).update(accepted)
            if i % 10 == 0:
                print(f"  [{i}/{len(work)} batches]")

    # merge + write (papers maps and content layers)
    for tgt, merged in results.items():
        if not merged:
            continue
        parts = tgt.split(":")
        kind, lang = parts[0], parts[1]
        section = parts[2] if len(parts) > 2 else None
        if kind == "papers":
            p = I18N / "papers" / f"{lang}.json"
            d = json.loads(p.read_text())
            d.setdefault(section, {}).update(merged)
            p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        else:
            p = I18N / f"{lang}_content.json"
            d = json.loads(p.read_text())
            d.update(merged)
            p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        print(f"  {tgt}: +{len(merged)} accepted")


if __name__ == "__main__":
    main()
