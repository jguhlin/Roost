#!/usr/bin/env python3
"""Process NEW papers: pdfs_to_process/*.pdf → registered papers + extractions.

Pipeline per PDF (deterministic — LLM enrichment happens later):
  1. convert to markdown (pymupdf4llm) into docs/papers_md/<id>.md,
     archive the PDF into docs/papers_pdfs/
  2. metadata: DOI found in text → Crossref (cached); fallback heuristics
  3. register in web/public/data/papers.json (History's papers_added event
     follows automatically via data_activity.py --papers-only)
  4. extractions into data/papers/paper_extras.parquet (keyed by paper id,
     joined with paper_db later):
       study_type       multi-label list, primary first, 'other' fallback
       mutations        [{mutation, gene, snippet}] (e.g. PB2 E627K)
       sample_sizes     [{n, snippet}]
       geography        {countries: [], snippets: []} hashmap
       social_snippet   ≤300-char Bluesky-ready post: author et al. + year +
                        title + original-publication link
       effect_direction SCHEMA ONLY (list of {exposure, outcome, direction,
                        evidence}) — filled by the LLM pass
  5. junk (non-science PDFs) → pdfs_to_process/_deferred + intake ledger
  6. optional social queue: data/papers/social_queue.jsonl

Run:  pixi run python scripts/papers/process_new_papers.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "papers"))
from build_paper_db import (  # noqa: E402
    build_pattern_map, paper_type, language_guess, normalize,
)

INPUT_DIR = ROOT / "pdfs_to_process"
MD_DIR = ROOT / "docs" / "papers_md"
PDF_DIR = ROOT / "docs" / "papers_pdfs"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
LEDGER = ROOT / "data" / "papers" / "intake_ledger.jsonl"
EXTRAS = ROOT / "data" / "papers" / "paper_extras.parquet"
SOCIAL_QUEUE = ROOT / "data" / "papers" / "social_queue.jsonl"
DOI_CACHE = ROOT / "data" / "papers" / "doi_meta_cache.json"
DEFERRED = INPUT_DIR / "_deferred"
TODAY_ISO = date.today().isoformat()

COUNTRY_LIST = """Afghanistan,Albania,Algeria,Angola,Argentina,Armenia,Australia,Austria,Azerbaijan,Bangladesh,Belarus,Belgium,Belize,Benin,Bhutan,Bolivia,Bosnia,Botswana,Brazil,Brunei,Bulgaria,Burkina,Burundi,Cambodia,Cameroon,Canada,Chad,Chile,China,Colombia,Congo,Costa Rica,Croatia,Cuba,Cyprus,Czechia,Denmark,Djibouti,Ecuador,Egypt,El Salvador,Eritria,Estonia,Ethiopia,Fiji,Finland,France,Gabon,Gambia,Georgia,Germany,Ghana,Greece,Guatemala,Guinea,Guyana,Haiti,Honduras,Hungary,Iceland,India,Indonesia,Iran,Iraq,Ireland,Israel,Italy,Jamaica,Japan,Jordan,Kazakhstan,Kenya,Kiribati,Korea,Kuwait,Kyrgyzstan,Laos,Latvia,Lebanon,Lesotho,Liberia,Libya,Lithuania,Luxembourg,Macedonia,Madagascar,Malawi,Malaysia,Mali,Mauritania,Mexico,Moldova,Mongolia,Montenegro,Morocco,Mozambique,Myanmar,Namibia,Nepal,Netherlands,New Zealand,Nicaragua,Niger,Nigeria,Norway,Oman,Pakistan,Panama,Papua New Guinea,Paraguay,Peru,Philippines,Poland,Portugal,Qatar,Romania,Russia,Rwanda,Saudi Arabia,Senegal,Serbia,Sierra Leone,Singapore,Slovakia,Slovenia,Somalia,South Africa,Spain,Sri Lanka,Sudan,Sweden,Switzerland,Syria,Taiwan,Tajikistan,Tanzania,Thailand,Togo,Trinidad,Tunisia,Turkey,Turkmenistan,Uganda,Ukraine,United Arab Emirates,United Kingdom,United States,Uruguay,Uzbekistan,Venezuela,Vietnam,Yemen,Zambia,Zimbabwe""".split(",")

STUDY_TYPES = [
    ("experimental_challenge", 4, r"inoculat|challenge (study|experiment)|experimental infection|intranasal|intratracheal|infected experimentally|pathogenicity experiment"),
    ("field_outbreak", 4, r"outbreak|mass mortality|die-?off|field investigation|found dead|mortality event"),
    ("serology", 3, r"seroprevalen|antibod(y|ies)|serolog|ELISA|hemagglutination inhibition"),
    ("surveillance", 3, r"surveillance|monitoring program|active sampling"),
    ("review", 3, r"systematic review|meta-?analysis|we review|review of the literature"),
    ("genomics", 2, r"genome|sequencing|phylogen|transmission dynamics|evolutionary"),
    ("vaccine", 2, r"vaccin"),
    ("risk_model", 2, r"model(l)?ing|risk assessment|projection"),
]

MUT_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z]{1,7}\s+[-–]?\s*)?([A-Z])\d{2,4}[A-Z])\b")
N_RE = re.compile(r"\b[nN]\s*=\s*(\d{1,6})\b")
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>)\]]{5,80})\b")


def ledger(file_name: str, route: str, doc_type: str, reason: str, **kw):
    with LEDGER.open("a") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).date().isoformat(),
                            "file": file_name, "route": route,
                            "doc_type": doc_type, "classifier": "process_new_papers",
                            "reason": reason, **kw}) + "\n")


def crossref(doi: str) -> dict | None:
    cache = json.loads(DOI_CACHE.read_text()) if DOI_CACHE.exists() else {}
    if doi in cache:
        return cache[doi]
    try:
        import httpx
        r = httpx.get(f"https://api.crossref.org/works/{doi}", timeout=30,
                      headers={"User-Agent": "Roost/avian-HPAI-atlas/1.0"})
        if r.status_code == 200:
            m = r.json().get("message", {})
            out = {
                "title": (m.get("title") or [""])[0],
                "journal": (m.get("container-title") or [""])[0],
                "year": None,
                "authors": ", ".join(
                    f"{a.get('family', '')} {a.get('given', '')[:1]}".strip() + "."
                    for a in m.get("author", [])[:8]),
                "url": f"https://doi.org/{doi}",
            }
            # Prefer the year the paper actually became available: some
            # publishers assign future issue dates (e.g. online Sept 2026 →
            # "published-print Jan 2027") — never record a future year.
            import datetime as _dt
            now_year = _dt.date.today().year
            year = None
            for k in ("published-print", "published-online", "issued", "created"):
                dp = (m.get(k) or {}).get("date-parts", [[]])[0]
                if dp and len(dp) >= 1:
                    try:
                        y = int(dp[0])
                    except (TypeError, ValueError):
                        continue
                    if y <= now_year:
                        year = y
                        break
                    if year is None:
                        year = y   # future date — keep as fallback only
            out["year"] = year
            cache[doi] = out
            DOI_CACHE.write_text(json.dumps(cache, indent=1))
            return out
    except Exception as e:
        print(f"    crossref failed: {e}", file=sys.stderr)
    return None


def first_page(pdf: Path) -> str:
    import pymupdf
    with pymupdf.open(pdf) as doc:
        return "\n".join(page.get_text() for page in doc[:2])


def to_markdown(pdf: Path) -> str:
    import pymupdf4llm
    return pymupdf4llm.to_markdown(str(pdf))


def classify_junk(text: str, fname: str, title: str = "") -> str | None:
    # permanent rejection list (data/papers/rejected_titles.json): papers
    # purged from the corpus that keep arriving in upload batches
    try:
        for r in json.loads((ROOT / "data/papers/rejected_titles.json").read_text()):
            if r["title_contains"].lower() in (title or "").lower():
                return f"rejected list: {r.get('reason', 'previously purged')}"
    except Exception:
        pass
    if len(text.strip()) < 1500:
        return "too short / not a full document"
    fl = fname.lower()
    junk_kw = ["rain streak", "optimal transport", "image de", "deep learning vision",
               "ip_disclosure", "ip agreement", "ip_disc", "_ip_", "confidentiality",
               "nondisclosure", "non-disclosure", "material transfer", "trf_eoi",
               "how-to", "expression_of_interest"]
    if any(k in fl for k in junk_kw):
        return "non-topic document (IP/legal/admin)"
    return None


def garbage_title(title: str) -> bool:
    """Titles like '7.-1' or '3.2' extracted from junk PDFs — not papers."""
    t = (title or "").strip()
    if len(t) < 6:
        return True
    letters = sum(c.isalpha() for c in t)
    if letters < max(4, len(t) // 3):          # mostly digits/punctuation
        return True
    if not re.search(r"[a-zA-Z]{3,}", t):      # no real word at all
        return True
    return False


def classify_offtopic(title: str, text: str) -> str | None:
    """Real paper, wrong field — Roost is an avian-influenza corpus."""
    blob = f"{title} {text[:6000]}".lower()
    topic_kw = ("influenza", "avian", "bird", "poultry", "wildfowl", "waterfowl",
                "h5n1", "h5n", "h7n", "h9n", "aiv", "duck", "goose", "swan",
                "penguin", "seal", "mink", "zoonos", "one health", "virus")
    hits = sum(1 for k in topic_kw if k in blob)
    if hits < 2 and "influenza" not in blob and "bird" not in blob:
        return "off-topic (no avian-influenza/virus signal in title+abstract)"
    return None


def study_types(text: str) -> list[str]:
    scores = []
    for name, weight, pat in STUDY_TYPES:
        n = len(re.findall(pat, text, flags=re.I))
        if n:
            scores.append((n * weight, name))
    scores.sort(reverse=True)
    out = [name for _, name in scores]
    return out or ["other"]


def mine_mutations(text: str) -> list[dict]:
    out, seen = [], set()
    for m in MUT_RE.finditer(text):
        mut = m.group(1).replace(" ", "")
        if mut in seen or len(mut) > 12:
            continue
        # require a gene-like context in the preceding 60 chars
        ctx = text[max(0, m.start() - 60):m.start()]
        g = re.search(r"\b([A-Z][A-Za-z0-9]{1,7})\b\s*$", ctx)
        seen.add(mut)
        s = max(0, m.start() - 120)
        out.append({"mutation": mut, "gene": g.group(1) if g else None,
                    "snippet": re.sub(r"\s+", " ", text[s:m.end() + 80])[:260]})
        if len(out) >= 60:
            break
    return out


def mine_sample_sizes(text: str) -> list[dict]:
    out, seen = [], set()
    for m in N_RE.finditer(text):
        n = int(m.group(1))
        if n < 3 or n > 500000 or n in seen:
            continue
        seen.add(n)
        s = max(0, m.start() - 100)
        out.append({"n": n, "snippet": re.sub(r"\s+", " ", text[s:m.end() + 60])[:240]})
        if len(out) >= 25:
            break
    return out


def mine_geography(text: str) -> dict:
    found = {}
    for c in COUNTRY_LIST:
        n = len(re.findall(rf"\b{re.escape(c)}\b", text))
        if n:
            found[c] = n
    top = sorted(found, key=lambda c: -found[c])[:15]
    snippets = []
    for c in top[:5]:
        m = re.search(rf"\b{re.escape(c)}\b", text)
        if m:
            s = max(0, m.start() - 100)
            snippets.append({"country": c,
                             "snippet": re.sub(r"\s+", " ", text[s:m.end() + 120])[:240]})
    return {"countries": [{"name": c, "mentions": found[c]} for c in top],
            "snippets": snippets}


def social_snippet(meta: dict) -> str:
    first = (meta.get("authors") or "Unknown").split(",")[0].strip()
    surname = first.split()[0] if first.split() else "Unknown"
    year = meta.get("year") or ""
    title = (meta.get("title") or "").rstrip(".")
    link = meta.get("doi") and f"https://doi.org/{meta['doi']}" or meta.get("url") or ""
    s = f"🧵 {surname} et al. ({year}): {title}. {link}"
    if len(s) > 297:
        s = s[:294] + "..."
    return s


def slug_id(meta: dict) -> str:
    surname = (meta.get("authors") or "anon").split(",")[0].split()[0].lower()
    surname = re.sub(r"[^a-z]", "", surname)
    words = re.sub(r"[^a-z0-9 ]", "", (meta.get("title") or "paper").lower()).split()
    stop = {"the", "a", "of", "and", "in", "for", "with", "to", "on", "from", "avian",
            "influenza", "virus", "viruses"}
    key = next((w for w in words if w not in stop and len(w) > 3), words[0] if words else "study")
    year = meta.get("year") or "nd"
    return f"{surname}_{key}_{year}".replace("__", "_")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    print(f"PDFs in {INPUT_DIR.name}: {len(pdfs)}", file=sys.stderr)
    if not pdfs:
        return 0

    papers_doc = json.loads(PAPERS_JSON.read_text())
    papers = papers_doc["papers"]
    existing_ids = {p["id"] for p in papers}
    existing_titles = {normalize(p.get("title", ""))[:60] for p in papers}

    patterns, v2c, _ = build_pattern_map()
    import subprocess
    new_rows = []

    for pdf in pdfs:
        print(f"\n== {pdf.name}", file=sys.stderr)
        try:
            head = first_page(pdf)
        except Exception as e:
            ledger(pdf.name, "deferred", "unreadable", f"pdf open failed: {e}")
            if not args.dry_run:
                DEFERRED.mkdir(exist_ok=True)
                shutil.copy2(pdf, DEFERRED / pdf.name)
            continue
        _probe_t = (crossref(DOI_RE.search(head).group(1).rstrip(".")) or {}).get("title", "") if DOI_RE.search(head) else ""
        junk = classify_junk(head, pdf.name, _probe_t)
        if junk:
            print(f"  DEFER: {junk}", file=sys.stderr)
            ledger(pdf.name, "deferred", "other", junk)
            if not args.dry_run:
                DEFERRED.mkdir(exist_ok=True)
                shutil.copy2(pdf, DEFERRED / pdf.name)
            continue
        # metadata-derived title sanity (2026-10-05): junk PDFs yield
        # garbage titles like '7.-1' — never register those
        _probe_doi = DOI_RE.search(head) or DOI_RE.search(pdf.stem.replace("-", " "))
        _probe_title = ""
        if _probe_doi:
            _cr = crossref(_probe_doi.group(1).rstrip("."))
            _probe_title = (_cr or {}).get("title", "")
        if garbage_title(_probe_title):
            print("  DEFER: garbage/no title (not a paper)", file=sys.stderr)
            ledger(pdf.name, "deferred", "other", "garbage title")
            if not args.dry_run:
                DEFERRED.mkdir(exist_ok=True)
                shutil.copy2(pdf, DEFERRED / pdf.name)
            continue

        # metadata
        meta = {}
        doi_m = DOI_RE.search(head) or DOI_RE.search(pdf.stem.replace("-", " "))
        if doi_m:
            meta["doi"] = doi_m.group(1).rstrip(".")
            cr = crossref(meta["doi"])
            if cr:
                meta.update({k: v for k, v in cr.items() if v})
        meta.setdefault("title", pdf.stem.replace("_", " ")[:120])
        # dedupe against existing papers by normalized title prefix
        if normalize(meta["title"])[:60] in existing_titles:
            print(f"  SKIP: already registered ({meta['title'][:50]}…)", file=sys.stderr)
            ledger(pdf.name, "already_registered", "paper", "title match",
                   title=meta["title"])
            if not args.dry_run:
                shutil.copy2(pdf, PDF_DIR / pdf.name)
            continue

        md = to_markdown(pdf) if not args.dry_run else head
        # gates: off-topic science, and metadata quality
        off = classify_offtopic(meta.get("title", ""), head)
        if off:
            print(f"  DEFER: {off}", file=sys.stderr)
            ledger(pdf.name, "deferred", "paper_offtopic", off,
                   title=meta.get("title", "")[:80])
            if not args.dry_run:
                DEFERRED.mkdir(exist_ok=True)
                shutil.copy2(pdf, DEFERRED / pdf.name)
            continue
        if not meta.get("doi") and (not meta.get("authors") or \
                meta.get("title", "") == pdf.stem.replace("_", " ")[:120]):
            print("  DEFER: no DOI and weak metadata — needs manual review",
                  file=sys.stderr)
            ledger(pdf.name, "deferred", "paper_metadata", "no DOI; title/authors unresolved",
                   title=meta.get("title", "")[:80])
            if not args.dry_run:
                DEFERRED.mkdir(exist_ok=True)
                shutil.copy2(pdf, DEFERRED / pdf.name)
            continue
        pid = slug_id(meta)
        while pid in existing_ids:
            pid += "x"
        # database-level constraint: the generated ID must be URL-safe and
        # not collide with any existing paper (including orphans in extras)
        if not re.match(r"^[a-z0-9][a-z0-9_-]*$", pid):
            print(f"  WARN generated ID '{pid}' contains unusual characters — "
                  "sanitising", file=sys.stderr)
            pid = re.sub(r"[^a-z0-9_-]", "", pid) or f"paper_{len(existing_ids)}"
        existing_ids.add(pid)
        existing_titles.add(normalize(meta["title"])[:60])

        st = study_types(md or head)
        muts = mine_mutations(md or head)
        ns = mine_sample_sizes(md or head)
        geo = mine_geography(md or head)
        snippet = social_snippet(meta)
        ptype = paper_type({"journal": meta.get("journal", ""),
                            "url": meta.get("url", ""),
                            "title": meta.get("title", ""),
                            "source_type": "", "doi": meta.get("doi")})
        print(f"  → {pid} [{ptype}] {st[:2]} genes/muts/n = …", file=sys.stderr)

        if args.dry_run:
            print(f"     title: {meta['title'][:70]}", file=sys.stderr)
            print(f"     authors: {(meta.get('authors') or '?')[:60]}", file=sys.stderr)
            print(f"     social: {snippet[:90]}", file=sys.stderr)
            continue

        # write outputs
        (MD_DIR / f"{pid}.md").write_text(md)
        shutil.copy2(pdf, PDF_DIR / f"{pid}.pdf")
        papers.append({
            "id": pid,
            "title": meta.get("title", ""),
            "authors": meta.get("authors", ""),
            "journal": meta.get("journal", ""),
            "year": meta.get("year"),
            "doi": meta.get("doi"),
            "url": meta.get("url") or "", "added": TODAY_ISO,
            "category": "Avian Influenza",
            "topics": st[:3],
            "summary": "",
            "cited_for": "",
            "pdf_status": "downloaded",
        })
        ledger(pdf.name, "paper", "paper", "new paper registered",
               paper_id=pid, title=meta.get("title", "")[:80])
        with SOCIAL_QUEUE.open("a") as f:
            f.write(json.dumps({"paper_id": pid, "snippet": snippet,
                                "posted": False,
                                "generated": datetime.now(timezone.utc)
                                   .isoformat(timespec="seconds")}) + "\n")
        new_rows.append({
            "id": pid, "title": meta.get("title", ""),
            "authors": [a.strip() for a in re.split(r",|\band\b", meta.get("authors") or "") if a.strip() and a.strip().lower() != "et al."],
            "journal": meta.get("journal", ""), "year": meta.get("year"),
            "doi": meta.get("doi"), "url": meta.get("url") or "",
            "paper_type": ptype,
            "category": "Avian Influenza", "topics": ",".join(st[:3]),
            "summary": "", "language_guess": language_guess(md or head),
            "study_type": st,
            "mutations": json.dumps(muts), "n_mutations": len(muts),
            "sample_sizes": json.dumps(ns),
            "geography": json.dumps(geo),
            "social_snippet": snippet,
            "effect_direction": "[]",   # schema: [{exposure, outcome, direction, evidence}] — LLM pass
            "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

    if args.dry_run:
        print(f"\ndry run complete — {len(pdfs)} PDFs examined", file=sys.stderr)
        return 0

    if new_rows:
        papers_doc["papers"] = papers
        PAPERS_JSON.write_text(json.dumps(papers_doc, indent=1))
        extras = pl.DataFrame(new_rows)
        # dtype normalization: the corpus stores `year` as Utf8 (intakes
        # pre-normalization) — cast new rows to match or diagonal concat
        # dies (2026-11-06 crash at exactly this line)
        for col in ("year",):
            if col in extras.columns and extras.schema[col] != pl.Utf8:
                extras = extras.with_columns(pl.col(col).cast(pl.Utf8))
        if EXTRAS.exists():
            old = pl.read_parquet(EXTRAS)
            old = old.filter(~pl.col("id").is_in(extras["id"].to_list()))
            extras = pl.concat([old, extras], how="diagonal")
        extras.write_parquet(EXTRAS)
        print(f"\nregistered {len(new_rows)} new papers; extras table "
              f"{extras.height} rows; social queue updated", file=sys.stderr)
        print("next: data_activity.py --papers-only → History; "
              "build_paper_index.py → index", file=sys.stderr)
    else:
        print("\nno new papers registered (all deferred/duplicates)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
