#!/usr/bin/env python3
"""Process PDFs with LLM-enhanced analysis.

Typed intake (INTAKE.md §1): papers, corrections, theses, news clips,
AND (D119) supplemental data files (.xlsx/.xls/.csv) staged for later
species-model expansion, plus a _deferred/ overflow pile with a full intake
ledger so nothing that misses the neat piles is ever silently dropped.
"""

import json
import re
import shutil
from datetime import date
import sys
from pathlib import Path

import os
import httpx
import pymupdf4llm

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "pdfs_to_process"
OUTPUT_PDF_DIR = PROJECT_ROOT / "docs" / "papers_pdfs"
OUTPUT_MD_DIR = PROJECT_ROOT / "docs" / "papers_md"
PAPERS_JSON = PROJECT_ROOT / "web" / "public" / "data" / "papers.json"
ANALYSIS_DIR = PROJECT_ROOT / "data" / "papers" / "analyses"
INTERNAL_DIR = PROJECT_ROOT / "data" / "papers" / "internal"

import os

LLM_URL = os.environ.get("LLM_URL", "http://localhost:8001/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4-31b")
MAX_TOKENS = 8192  # D120: muse-glimmer reasons before answering — small
                   # budgets truncate the thinking and the answer never lands
                   # (the 21-empty-summaries + 87-deferred lesson)

# Ensure directories exist
for d in [OUTPUT_PDF_DIR, OUTPUT_MD_DIR, ANALYSIS_DIR, INTERNAL_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_papers_db():
    """Load papers database."""
    if not PAPERS_JSON.exists():
        return {}
    with open(PAPERS_JSON) as f:
        data = json.load(f)
    return {p["id"]: p for p in data.get("papers", [])}


def normalize(s: str) -> str:
    """Normalize string for matching."""
    return re.sub(r'[^a-z0-9]', '', s.lower())


def match_pdf_to_paper(pdf_name: str, papers: dict, md_text: str = "", doc_type: str = "paper") -> tuple[str, dict] | None:
    """Try to match PDF filename to a paper ID.
    Book chapters are new by construction — filename matching only,
    no content matching (a Cyrillic-title bug once matched everything).
    D82: generic umbrella titles ("Highly Pathogenic Avian Influenza") must
    never keyword-match — they ate 33 PDFs via first-3-words substring."""
    GENERIC_TITLES = {
        "highly pathogenic avian influenza", "avian influenza",
        "influenza a virus", "h5n1", "hpai", "avian flu",
        "wild birds", "poultry",
    }
    pdf_norm = normalize(pdf_name)
    md_lower = (md_text.lower() if md_text else "") if doc_type == "paper" else ""

    def title_is_specific(title: str) -> bool:
        if len(title.split()) < 5:
            return False
        if normalize(title) in GENERIC_TITLES:
            return False
        return True

    for pid, paper in papers.items():
        # Check paper ID in filename
        if pid.lower().replace("_", "") in pdf_name.lower().replace("_", ""):
            return pid, paper

        # Check DOI suffix in filename
        doi = paper.get("doi") or ""
        if doi:
            doi_suffix = doi.split("/")[-1].lower().replace(".", "")
            if doi_suffix and doi_suffix in pdf_norm:
                return pid, paper

            # Also check if DOI appears in the markdown content — HEAD ONLY
            # (first 3000 chars): a paper's own DOI prints in the header/
            # footnote; reference-list DOIs at the tail made 8 citing papers
            # falsely match one heavily-cited corpus paper (D120).
            if md_lower and doi.lower() in md_lower[:3000]:
                return pid, paper

        # Title keywords — ONLY specific titles (D82 guard). Require 4+ words
        # from a 5+ word title; generic titles fall through to exact-DOI only.
        title = paper.get("title", "")
        if title_is_specific(title):
            title_words = [w for w in normalize(title).split() if len(w) > 4][:4]
            if len(title_words) >= 4 and all(w in pdf_norm for w in title_words):
                return pid, paper

            # Title in markdown head — same specificity guard
            if md_lower and len(title) > 30:
                title_norm = normalize(title)[:60]
                if len(title_norm) >= 45 and title_norm in normalize(md_lower[:3000]):
                    return pid, paper

    return None


def call_llm(prompt: str, max_tokens: int = MAX_TOKENS) -> str:
    """Call the LLM and return the response content ('' on failure —
    callers must treat '' as LLM-down, never mint data from it)."""
    try:
        response = httpx.post(
            LLM_URL,
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        if not content:
            # Try reasoning_content if content is empty
            content = data["choices"][0]["message"].get("reasoning_content", "")
        return content.strip()
    except Exception as e:
        print(f"  LLM error: {e}")
        return ""


def generate_paper_id(md_text: str, pdf_name: str) -> str:
    """Use LLM to suggest a paper ID based on content.
    D120: NO fallback paths — junk IDs (word_year scrapes, filename stems
    like 1_s2_0_s0032579125000136) are worse than deferring the file.
    Returns a validated author_topic_year id, or None (caller defers)."""
    # Extract first ~2000 chars for context
    sample = md_text[:2000]

    prompt = f"""Read this paper excerpt and give me a short ID for it.

{sample}

The ID should be: firstauthor_topic_year (like: smith_gannet2024)

Your answer (just the ID):"""

    response = call_llm(prompt, max_tokens=4096)
    if not response:
        print("  WARNING: LLM unavailable — refusing to mint a fallback paper "
              "ID (D120); deferring file to _deferred/")
        return None

    # author[_topic-segments]_year — hyphens inside segments are legit
    # (mhc-b-haplotypes) and sanitized to the corpus underscore convention
    id_match = re.findall(r'\b([a-z0-9]+(?:[-_][a-z0-9]+)*_\d{4})\b', response.lower())
    if id_match:
        # reasoning text may discuss candidates — the FINAL answer trails
        # the thinking, so take the last plausible id (D120)
        paper_id = id_match[-1].replace("-", "_")[:30]
        if len(paper_id) >= 8:
            return paper_id
        print(f"  WARNING: LLM-proposed ID too short to trust ({paper_id!r}) — "
              "deferring rather than minting a weak ID (D120)")
        return None

    print(f"  WARNING: LLM ID response unusable ({response[:60]!r}) — no clean "
          "author_topic_year pattern; deferring rather than minting a junk "
          "fallback ID (D120)")
    return None


def generate_summary(md_text: str, paper_meta: dict) -> dict:
    """Use LLM to generate structured summary of the paper."""
    # Get abstract or first section
    abstract_match = re.search(r'(?:abstract|summary)\s*\n(.*?)(?:\n#|\n\n\n)', md_text, re.IGNORECASE | re.DOTALL)
    abstract = abstract_match.group(1)[:1500] if abstract_match else md_text[:1500]

    prompt = f"""Analyze this HPAI/avian influenza research paper and provide a structured summary.

Title: {paper_meta.get('title', 'Unknown')}
Journal: {paper_meta.get('journal', 'Unknown')}

Abstract/Content:
{abstract}

Provide your response in this exact JSON format:
{{
    "one_liner": "Single sentence summary of the main finding (max 150 chars)",
    "key_finding": "The most important result or conclusion",
    "species_studied": ["list", "of", "species"],
    "genes_discussed": ["list", "of", "genes"],
    "study_type": "experimental/surveillance/genomic/review/other",
    "relevance_score": 1-5 (5=highly relevant to HPAI research)
}}

Reply with ONLY the JSON, no other text."""

    response = call_llm(prompt, max_tokens=8192)

    # Try to parse JSON from response
    try:
        # Find JSON in response
        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    return {
        "one_liner": "",
        "key_finding": "",
        "species_studied": [],
        "genes_discussed": [],
        "study_type": "unknown",
        "relevance_score": 0,
    }


def detect_doc_type(pdf_name: str, md_text: str = "") -> str:
    """Classify non-standard intake: correction/erratum, thesis, news.
    Returns 'paper' | 'correction' | 'thesis' | 'news'."""
    name_l = pdf_name.lower()
    if name_l.startswith("book_"):
        return "book_chapter"
    if re.search(r"correction|erratum|retract|editorial expression", name_l):
        return "correction"
    if re.search(r"dissertation|_phd_|thesis", name_l):
        return "thesis"
    head = md_text[:3000].lower()
    if re.search(r"correction|erratum", head[:600]) and len(md_text) < 12000:
        return "correction"
    if re.search(r"a dissertation|submitted in partial fulfillment|doctor of philosophy", head):
        return "thesis"
    # news: short, outlet-ish, no references section
    if (len(md_text) < 15000
            and "references" not in head
            and re.search(r"reuters|associated press|promed|cidrap|outbreak news|"
                          r"news report|staff writer|correspondent", head)):
        return "news"
    return "paper"


def handle_correction(pdf_path: Path, md_text: str, paper_id: str) -> bool:
    """Corrections attach to the parent paper — never analysed standalone,
    never deleted (unlike plain duplicates)."""
    note = re.sub(r"\s+", " ", md_text.strip())[:600]
    corrections_file = PROJECT_ROOT / "data" / "papers" / "corrections.json"
    corrections = json.loads(corrections_file.read_text()) if corrections_file.exists() else {}
    corrections[paper_id] = {
        "source_pdf": pdf_path.name,
        "note": note,
        "attached": date.today().isoformat(),
    }
    corrections_file.write_text(json.dumps(corrections, indent=1))
    # keep the correction markdown for search
    (OUTPUT_MD_DIR / f"{paper_id}_correction.md").write_text(md_text)
    archived = PROJECT_ROOT / "data" / "papers" / "correction_pdfs"
    archived.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, archived / pdf_path.name)
    pdf_path.unlink()
    print(f"  CORRECTION attached to {paper_id} (archived, noted)")
    return False


def handle_news(pdf_path: Path, md_text: str) -> bool:
    """News routes to docs/news_md per INTAKE §3 — never the paper pipeline."""
    news_dir = PROJECT_ROOT / "docs" / "news_md"
    news_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", pdf_path.stem.lower())[:60].strip("-")
    out = news_dir / f"{date.today().isoformat()}_{slug}.md"
    header = (f"<!-- news clip: {pdf_path.name} — intake {date.today()} -->\n"
              f"<!-- NOT paper-corpus evidence; see INTAKE.md §3 -->\n\n")
    out.write_text(header + md_text)
    pdf_path.unlink()
    print(f"  NEWS clip filed → {out.name}")
    return False


SUPPLEMENT_DIR = PROJECT_ROOT / "data" / "supplements"
INTAKE_LEDGER = PROJECT_ROOT / "data" / "papers" / "intake_ledger.jsonl"
DEFERRED_DIR = INPUT_DIR / "_deferred"


def ledger_write(filename: str, route: str, *, paper_id=None, doc_type=None,
                 classifier=None, reason=None, **extra):
    """D119: every intake disposition lands here — the reconsider-later
    instrument. route: paper|correction|thesis|news|supplement|deferred|duplicate."""
    INTAKE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": date.today().isoformat(), "file": filename, "route": route,
           "paper_id": paper_id, "doc_type": doc_type,
           "classifier": classifier, "reason": reason, **extra}
    with open(INTAKE_LEDGER, "a") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# brv70173-sup-0002-datas1.xlsx → manuscript code 'brv70173'
SUPP_CODE_RES = [
    re.compile(r"^([a-z0-9]{3,12})-sup-", re.I),
    re.compile(r"^(.+?)[-_](?:supplement|supp)\b", re.I),
]


def supplement_code(path: Path):
    for rx in SUPP_CODE_RES:
        m = rx.match(path.name.lower())
        if m:
            return m.group(1)
    return None


def find_supplement_parent(code, papers_db: dict):
    """Associate with the parent paper: sibling PDF in this batch sharing
    the code, a registry id prefix, or an archived papers_pdf stem.
    Returns (paper_id | None, how)."""
    if not code:
        return None, "no-code"
    sibling = next((p for p in INPUT_DIR.glob("*.pdf")
                    if p.stem.lower().startswith(code.lower())), None)
    if sibling:
        m = match_pdf_to_paper(sibling.stem, papers_db, "")
        if m:
            return m[0], f"sibling-pdf:{sibling.name}"
    hits = [pid for pid in papers_db if pid.lower().startswith(code.lower())]
    if len(hits) == 1:
        return hits[0], "registry-prefix"
    for pdf in OUTPUT_PDF_DIR.glob(f"{code}*.pdf"):
        return pdf.stem, "archive-stem"
    return None, "pending"


def _sanitize_rows(df, n_rows=4, n_cols=12):
    rows = []
    for row in df.head(n_rows).iter_rows(named=True):
        rows.append({k: (str(v)[:40] if v is not None else None)
                     for k, v in list(row.items())[:n_cols]})
    return rows


def preview_workbook(path: Path) -> list:
    """Per-sheet structural preview via fastexcel/polars (csv included)."""
    if path.suffix.lower() == ".csv":
        import polars as pl
        dfs = [(path.stem, pl.read_csv(path, infer_schema_length=100))]
    else:
        from fastexcel import read_excel
        wb = read_excel(path)
        dfs = [(name, wb.load_sheet(name).to_polars()) for name in wb.sheet_names]
    return [{"sheet": name, "n_rows": df.height, "n_cols": df.width,
             "columns": [str(c) for c in df.columns[:20]],
             "sample_rows": _sanitize_rows(df)} for name, df in dfs]


# heuristic fallback (no LLM): judge by column names
COL_RES = {
    "species": re.compile(r"species|taxon|\bbird\b|host[_ ]name|latin|scientific|common name", re.I),
    "date": re.compile(r"\bdate\b|\byear\b|\bmonth\b|semester|_dt$|detected", re.I),
    "location": re.compile(r"countr|region|province|state|admin|localit|latitude|longitud|\blat\b|\blon\b", re.I),
    "event": re.compile(r"event|outbreak|\bcase\b|mortal|detection|epizo|epidem", re.I),
}


def heuristic_classify(sheets: list) -> dict:
    cols = [c for s in sheets for c in s["columns"]]
    blob = " ".join(cols)
    has = {k: bool(rx.search(blob)) for k, rx in COL_RES.items()}

    def col_for(k):
        for c in cols:
            if COL_RES[k].search(c):
                return c
        return None

    if has["species"] and has["date"] and (has["location"] or has["event"]):
        cc = "species_sightings"
    elif has["event"] and has["location"]:
        cc = "detection_surveillance"
    elif has["species"]:
        cc = "species_metadata"
    else:
        cc = "other_data"
    return {"content_class": cc,
            "join_keys": {k: col_for(k) for k in ("species", "date", "location")},
            "ingest_candidate": ("detections" if cc in ("species_sightings",
                                                          "detection_surveillance") else None),
            "why": "column-name heuristic", "classifier": "heuristic"}


SUPP_CLASS_SYS = """You classify supplemental data files attached to avian-influenza research.
Given per-sheet structure (names, columns, sample rows), reply ONLY as JSON:
{"content_class": "species_sightings"|"detection_surveillance"|"mortality_events"|"phylogeny_diversity"|"genomic_metadata"|"lab_experiment"|"metadata_only"|"mixed"|"other_data",
 "join_keys": {"species": <column name or null>, "date": <column or null>, "location": <column or null>},
 "ingest_candidate": "detections"|"wahis"|null,
 "why": "<25 words"}
ingest_candidate names which Roost pipeline this could feed (detections
ingest, WAHIS events); null when it is analysis-only data. Judge strictly
from the columns and sample rows shown; never speculate beyond them."""


def llm_classify_supplement(sheets: list):
    payload = json.dumps(sheets, ensure_ascii=False)[:6000]
    try:
        raw = call_llm(SUPP_CLASS_SYS + "\n\nSHEETS:\n" + payload, max_tokens=4096)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        d = json.loads(m.group(0)) if m else None
        if d and "content_class" in d:
            d["classifier"] = "llm"
            return d
    except Exception:
        pass
    return None  # heuristic fallback in caller


def handle_supplement(path: Path, papers_db: dict, dry: bool = False) -> bool:
    """D119: stage a supplemental data file for later species-model expansion.
    Nothing auto-joins; the ledger + classification keep it reconsiderable."""
    print(f"\n{'='*60}\nSupplement: {path.name}\n{'='*60}")
    try:
        sheets = preview_workbook(path)
    except Exception as e:
        print(f"  ERROR parsing: {e} — deferring")
        return defer_file(path, reason=f"supplement_parse_error: {str(e)[:120]}", dry=dry)
    code = supplement_code(path)
    parent, how = find_supplement_parent(code, papers_db)
    cls = llm_classify_supplement(sheets) or heuristic_classify(sheets)
    print(f"  {len(sheets)} sheet(s), {sum(s['n_rows'] for s in sheets):,} rows total"
          f" | class={cls['content_class']} ({cls['classifier']})"
          f" | parent={parent or 'PENDING'} ({how})")
    if dry:
        print("  dry — staged nothing")
        return True
    stage = SUPPLEMENT_DIR / (code or path.stem)
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, stage / path.name)
    (stage / "preview.json").write_text(json.dumps(sheets, ensure_ascii=False, indent=1))
    cls.update({"file": path.name, "manuscript_code": code,
                "parent_paper": parent, "parent_association": how,
                "ts": date.today().isoformat()})
    (stage / "classify.json").write_text(json.dumps(cls, ensure_ascii=False, indent=1))
    ledger_write(path.name, "supplement", doc_type=cls["content_class"],
                 classifier=cls["classifier"], reason=cls.get("why"),
                 parent_paper=parent, manuscript_code=code,
                 ingest_candidate=cls.get("ingest_candidate"))
    path.unlink()
    print(f"  Staged → {stage}")
    return True


ODD_DOC_SYS = """You triage odd intake documents for an avian-influenza corpus.
Given the text excerpt, reply ONLY as JSON:
{"kind": "paper_like"|"supplement"|"poster"|"presentation"|"map_or_figure"|"form_or_datasheet"|"other",
 "why": "<15 words"}
paper_like = a research article/thesis/report with prose and citations. When
in doubt, paper_like — diverting a real paper to the deferred pile is worse
than processing an odd document as a paper."""


def classify_odd_doc(md_text: str):
    try:
        raw = call_llm(ODD_DOC_SYS + "\n\nEXCERPT:\n" + md_text[:4000], max_tokens=2048)
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        d = json.loads(m.group(0)) if m else None
        if d and d.get("kind"):
            return d
    except Exception:
        pass
    return None


def defer_file(path: Path, reason: str, dry: bool = False, odd: dict = None) -> bool:
    """Move a file to the _deferred pile + ledger it — the reconsider path."""
    if dry:
        print(f"  dry — would defer {path.name}: {reason}")
        return True
    DEFERRED_DIR.mkdir(parents=True, exist_ok=True)
    dest = DEFERRED_DIR / path.name
    shutil.copy2(path, dest)
    path.unlink()
    ledger_write(path.name, "deferred", doc_type=(odd or {}).get("kind"),
                 classifier=("llm" if odd else None), reason=reason)
    print(f"  DEFERRED → {dest} ({reason})")
    return True


def archive_duplicate(pdf_path: Path):
    """D120: duplicates are ARCHIVED to _already_matched/, never deleted —
    INTAKE §1 promised this; the code had drifted to unlink, which made a
    false content-match unrecoverable."""
    dest_dir = INPUT_DIR / "_already_matched"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pdf_path), dest_dir / pdf_path.name)


def process_single_pdf(pdf_path: Path, papers_db: dict, force: bool = False) -> bool:
    """Process a single PDF through the full pipeline."""
    pdf_name = pdf_path.stem
    print(f"\n{'='*60}")
    print(f"Processing: {pdf_name}")
    print(f"{'='*60}")

    # Step 1: Try to match to existing paper (filename only first)
    match = match_pdf_to_paper(pdf_name, papers_db, "", "book_chapter" if pdf_name.lower().startswith("book_") else "paper")

    if match:
        paper_id, paper_meta = match
        print(f"  Matched to: {paper_id}")

        # Check if already processed
        dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
        dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"
        if dest_pdf.exists() and dest_md.exists() and not force:
            dedup_log = PROJECT_ROOT / "data" / "papers" / "dedup_log.txt"
            with open(dedup_log, "a") as df:
                df.write(f"{pdf_path.name}\t→ {paper_id} (filename)\n")
            print(f"  SKIP duplicate of {paper_id} — archived (filename match)")
            ledger_write(pdf_path.name, "duplicate", paper_id=paper_id,
                         reason="filename match")
            archive_duplicate(pdf_path)
            return False
    else:
        paper_id = None
        paper_meta = {}

    # Step 2: Convert PDF to markdown
    print(f"  Converting to markdown...")
    try:
        md_text = pymupdf4llm.to_markdown(str(pdf_path))
        print(f"    → {len(md_text):,} chars")
    except Exception as e:
        print(f"  ERROR converting PDF: {e}")
        return defer_file(pdf_path, reason=f"conversion_error: {str(e)[:120]}")

    # Step 2b: odd-document triage (D119) — matchless, very short text gets
    # one cheap classification call; non-paper-like docs go to _deferred
    # with their classification ledgered, never silently dropped.
    if not paper_id and len(md_text) < 2500:
        odd = classify_odd_doc(md_text)
        if odd and odd.get("kind") not in ("paper_like", None):
            return defer_file(pdf_path, reason=f"odd-doc: {odd['kind']}", odd=odd)

    # Step 3: If no filename match, try matching with content (DOI/title)
    # (corrections/theses/news handled by type detection first)
    doc_type = detect_doc_type(pdf_name)
    if not paper_id:
        doc_type = detect_doc_type(pdf_name, md_text)
        if doc_type == "news":
            return handle_news(pdf_path, md_text)
    else:
        doc_type = detect_doc_type(pdf_name, md_text)
    if doc_type == "correction":
        # attach to matched paper; if none, try content match
        if not paper_id:
            m = match_pdf_to_paper(pdf_name, papers_db, md_text)
            if m:
                paper_id, paper_meta = m
        if paper_id:
            return handle_correction(pdf_path, md_text, paper_id)
        # unmatched correction: file as its own doc (rare)
        print("  unmatched correction — processing as standalone")
    if not paper_id:
        match = match_pdf_to_paper(pdf_name, papers_db, md_text)
        if match:
            paper_id, paper_meta = match
            # Check if already processed — skip AND remove the duplicate
            # (keep no extra copies; the canonical analysis lives under the
            # matched paper ID — see INTAKE.md §1 dedup policy)
            dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
            dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"
            if dest_pdf.exists() and dest_md.exists() and not force:
                dedup_log = PROJECT_ROOT / "data" / "papers" / "dedup_log.txt"
                with open(dedup_log, "a") as df:
                    df.write(f"{pdf_path.name}\t→ {paper_id}\n")
                print(f"  SKIP duplicate of {paper_id} — archived (content match; logged to dedup_log.txt)")
                ledger_write(pdf_path.name, "duplicate", paper_id=paper_id,
                             reason="content match")
                archive_duplicate(pdf_path)
                return False
        else:
            print(f"  No match found - will generate ID from content")

    # Step 4: If still no match, use LLM to generate paper ID
    if not paper_id:
        print(f"  Generating paper ID with LLM...")
        new_id = generate_paper_id(md_text, pdf_name)
        if new_id is None:
            return defer_file(pdf_path, "WARNING: id-generation-unreliable — "
                              "no junk fallback IDs (D120); re-run intake")
        paper_id = new_id
        print(f"    → {paper_id}")

        # Check again if this ID exists
        dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
        dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"
        if dest_pdf.exists():
            # Add suffix to make unique
            i = 2
            while (OUTPUT_PDF_DIR / f"{paper_id}_{i}.pdf").exists():
                i += 1
            paper_id = f"{paper_id}_{i}"
            dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
            dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"

    # Step 5: Save markdown
    dest_md = OUTPUT_MD_DIR / f"{paper_id}.md"
    if doc_type == "thesis":
        md_text = (f"<!-- doc-type: thesis — not peer-reviewed; weight accordingly -->\n\n" + md_text)
    elif doc_type == "book_chapter":
        md_text = ("<!-- doc-type: book-chapter — Avian Immunology (2022, 3rd ed.); "
                   "authoritative reference; cite as book chapter -->\n\n" + md_text)
    dest_md.write_text(md_text)
    print(f"  Saved markdown: {dest_md.name}")

    # Step 6: Move PDF
    dest_pdf = OUTPUT_PDF_DIR / f"{paper_id}.pdf"
    shutil.copy2(pdf_path, dest_pdf)
    print(f"  Copied PDF: {dest_pdf.name}")

    # Step 7: Generate LLM summary
    print(f"  Generating LLM summary...")
    summary = generate_summary(md_text, paper_meta)
    if summary.get("one_liner"):
        print(f"    → {summary['one_liner'][:80]}...")

    # Step 8: Run entity extraction (import the function)
    print(f"  Running entity extraction...")
    try:
        # Import here to avoid circular imports
        skill_scripts = PROJECT_ROOT / ".claude" / "skills" / "analyze-paper" / "scripts"
        sys.path.insert(0, str(skill_scripts))
        from analyze_single import analyze_paper

        public_analysis, internal_analysis = analyze_paper(dest_md, paper_meta)

        # Add LLM summary to internal analysis
        internal_analysis["llm_summary"] = summary
        if summary.get("one_liner"):
            internal_analysis["knowledge_summary"]["one_liner"] = summary["one_liner"]

        # Save analyses
        with open(ANALYSIS_DIR / f"{paper_id}.json", "w") as f:
            json.dump(public_analysis, f, indent=2)

        with open(INTERNAL_DIR / f"{paper_id}.json", "w") as f:
            json.dump(internal_analysis, f, indent=2)

        print(f"  Analysis saved")
        print(f"    Genes: {len(public_analysis['genes'])}")
        print(f"    Species: {len(public_analysis['species_detections'])}")

    except Exception as e:
        print(f"  ERROR in analysis: {e}")

    # Step 9: Remove from input directory
    pdf_path.unlink()
    print(f"  Removed from pdfs_to_process")
    ledger_write(pdf_path.name, "paper", paper_id=paper_id, doc_type=doc_type,
                 classifier="fast-pass")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-process existing")
    parser.add_argument("--limit", type=int, help="Process only N papers")
    parser.add_argument("--dry", action="store_true",
                        help="classify/preview supplements only — move nothing, write no ledger")
    parser.add_argument("--ledger-report", action="store_true",
                        help="summarize the intake ledger and exit")
    parser.add_argument("pdf", nargs="?", help="Specific PDF to process")
    args = parser.parse_args()

    # D120: line-buffer stdout — a piped run must show progress as it
    # happens, not post-mortem after a buffer's worth of silent work.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    if args.ledger_report:
        if not INTAKE_LEDGER.exists():
            print("no intake ledger yet")
            return
        from collections import Counter
        recs = [json.loads(l) for l in INTAKE_LEDGER.read_text().splitlines() if l.strip()]
        print(f"{len(recs)} intake records: "
              f"{dict(Counter(r['route'] for r in recs))}")
        for r in recs:
            if r["route"] in ("deferred", "supplement"):
                print(f"  [{r['route']:10}] {r['file']} — {r.get('doc_type')} "
                      f"(parent={r.get('parent_paper')}, {r.get('reason')})")
        return

    papers_db = load_papers_db()
    print(f"Loaded {len(papers_db)} papers from database")

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            pdf_path = INPUT_DIR / args.pdf
        if pdf_path.exists():
            process_single_pdf(pdf_path, papers_db, args.force)
        else:
            print(f"PDF not found: {args.pdf}")
    else:
        pdfs = sorted(INPUT_DIR.glob("*.pdf"))
        supps = sorted(list(INPUT_DIR.glob("*.xlsx")) + list(INPUT_DIR.glob("*.xls"))
                       + list(INPUT_DIR.glob("*.csv")))
        print(f"Found {len(pdfs)} PDFs + {len(supps)} supplemental data files")

        if args.limit:
            pdfs = pdfs[:args.limit]

        processed = 0
        for supp in supps:
            if handle_supplement(supp, papers_db, dry=bool(getattr(args, 'dry', False))):
                processed += 1
        if getattr(args, 'dry', False):
            print("\ndry — PDF pipeline skipped (classification preview only)")
            return
        for pdf_path in pdfs:
            if process_single_pdf(pdf_path, papers_db, args.force):
                processed += 1

        print(f"\n{'='*60}")
        print(f"DONE: Processed {processed} papers")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
