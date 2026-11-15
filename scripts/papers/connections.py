#!/usr/bin/env python3
"""Connection miner (D76) — search + Muse classification layers.

`search`   boundary-aware `rg --json` corpus scan → per-gene status + windows
`classify` Muse pass over eligible windows → pending candidates (review-gated)
`status`   human summary of the search layer

Storage (all under data/papers/connections/):
  search_status.json   per-gene hit/no_hit/unsearchable record
  windows.jsonl        deduped gene-paper evidence windows
  window_verdicts.jsonl  one Muse verdict per processed window (resume set)
  candidates.jsonl     validated relationship candidates (status: pending)
  quarantine.jsonl      malformed/ungrounded responses (never evidence)

Resume safety: classify skips window_ids already in window_verdicts.jsonl;
a dropped Muse tunnel aborts cleanly — every future finding stays pending.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

# canonical gene-symbol resolution (shared map; see build_gene_registry)
_AM = json.loads((Path(__file__).resolve().parents[2] / "data" / "papers" / "gene_alias_map.json").read_text())
_AL, _SYN = _AM.get("aliases", {}), _AM.get("synonyms", {})


def resolve_gene(t):
    t = str(t).strip()
    for probe in (t, t.upper(), t.lower()):
        h = _AL.get(probe)
        if h is not None:
            return None if h == "NOT_A_GENE" else _SYN.get(h, h)
    return _SYN.get(t.upper(), t.upper())
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

ROOT = Path(__file__).parent.parent.parent

# LLM provenance (D90): every extraction pass records model/prompt/date
sys_path = str(ROOT / "scripts" / "papers")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)
try:
    from llm_provenance import track as _llm_track
except ImportError:
    _llm_track = lambda *a, **k: None
MD_DIR = ROOT / "docs" / "papers_md"
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
GENE_CONFIG = ROOT / "data" / "genes" / "gene_config.json"
GENE_PRESENCE = ROOT / "web" / "public" / "data" / "gene_catalogue.json"
MANIFEST = ROOT / "data" / "papers" / "corpus_manifest.json"
OUT_DIR = ROOT / "data" / "papers" / "connections"
STATUS_PATH = OUT_DIR / "search_status.json"
WINDOWS_PATH = OUT_DIR / "windows.jsonl"
VERDICTS_PATH = OUT_DIR / "window_verdicts.jsonl"
CANDIDATES_PATH = OUT_DIR / "candidates.jsonl"
QUARANTINE_PATH = OUT_DIR / "quarantine.jsonl"

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

VIRAL_PROTEINS = {
    "PB2", "PB1", "PB1-F2", "PA", "PA-X", "HA", "HA1", "HA2", "NP",
    "NA", "NA1", "NA2", "M1", "M2", "M42", "NS1", "NS2", "NS3", "HE",
}

# identifiers that collide with ubiquitous non-gene tokens in this corpus
# ("NA" in "not applicable", "M1/M2" macrophages, "PA"/"NP" abbreviations).
# They stay UNSEARCHABLE unless explicitly re-enabled here after review.
EXPLICIT_UNSAFE = {"NA", "M1", "M2", "PA", "NP", "HA", "M", "II", "C"}

MIN_ALNUM = 3  # shortest searchable identifier length (alnum chars)

# fallback when no system dictionary is available (subset observed in the
# corpus vocabulary; extend as collisions surface in review)
FALLBACK_ENGLISH_WORDS = {
    "ace", "ada", "bash", "fer", "ide", "kit", "oas", "sting",
}


def english_word_identifiers(keys):
    """Keys that are also common English words → exact-case-only matches."""
    words = None
    for path in ("/usr/share/dict/words", "/usr/share/dict/american-english"):
        try:
            words = {w.strip().lower() for w in open(path, errors="ignore")}
            break
        except OSError:
            continue
    if words is None:
        words = FALLBACK_ENGLISH_WORDS
    out = set()
    for key in keys:
        if alnum_len(key) >= 3 and key.lower() in words:
            out.add(key)
    return out


def alnum_norm(ident):
    return re.sub(r"[^A-Z0-9]", "", ident.upper())


# ============================================================ identifier index

def alnum_len(ident):
    return len(re.sub(r"[^A-Za-z0-9]", "", ident))


def build_identifier_index():
    """All searchable identifiers for the corpus scan.

    Returns (searchable, viral_searchable, unsafe_records, catalogue) where
      searchable: {IDENT_UPPER: {canonical, kind}} for host genes
      viral_searchable: {IDENT_UPPER: {...}} viral protein endpoints
      unsafe_records: [{ident, reason, owners}] — owners empty for viral-only
    kind ∈ canonical | catalogue_alias | merge_alias | family | viral.
    An identifier mapping to more than one canonical gene is ambiguous →
    unsearchable. Short identifiers (< MIN_ALNUM alnum chars) are unsearchable.
    """
    cat = json.loads(GENE_PRESENCE.read_text())["gene_catalogue"]
    cfg = json.loads(GENE_CONFIG.read_text())

    # identifier → set of canonical owners
    owners = defaultdict(set)
    kinds = {}

    def add(ident, canonical, kind):
        if not ident:
            return
        key = ident.upper()
        owners[key].add(canonical)
        # most specific kind wins if an identifier is registered twice
        priority = {"canonical": 0, "catalogue_alias": 1,
                    "merge_alias": 2, "family": 3}
        if key not in kinds or priority[kind] < priority[kinds[key]]:
            kinds[key] = kind

    for gene, meta in cat.items():
        add(gene, gene, "canonical")
        for a in meta.get("aliases") or []:
            add(a, gene, "catalogue_alias")
    for a, t in cfg.get("aliases", {}).items():
        if a != "_doc":
            add(a, t, "merge_alias")
    for fam, t in cfg.get("wiki_aliases", {}).items():
        if fam != "_doc":
            add(fam, t, "family")

    # collapse alnum-equal canonical duplicates (e.g. catalogue carrying both
    # "IL18" and "IL-18"): keep the dash-free HUGO-style symbol canonical,
    # the variant becomes an alias. One gene, one owner — duplicate catalogue
    # entries must not fork the miner (or the cards).
    by_alnum = defaultdict(set)
    for key, canon_set in owners.items():
        for c in canon_set:
            by_alnum[alnum_norm(c)].add(c)
    collapsed = {}                     # variant canonical → kept canonical
    for variants in by_alnum.values():
        if len(variants) > 1:
            keep = sorted(variants, key=lambda c: ("-" in c, c))[0]
            for v in variants:
                if v != keep:
                    collapsed[v] = keep
    for key in list(owners):
        owners[key] = {collapsed.get(c, c) for c in owners[key]}

    searchable = {}
    unsafe_records = []
    for key, canon_set in owners.items():
        if key in EXPLICIT_UNSAFE or alnum_len(key) < MIN_ALNUM:
            unsafe_records.append({
                "ident": key,
                "reason": "identifier too short or collision-prone",
                "owners": sorted(canon_set)})
        elif len(canon_set) > 1:
            unsafe_records.append({
                "ident": key,
                "reason": f"ambiguous: maps to {', '.join(sorted(canon_set))}",
                "owners": sorted(canon_set)})
        elif key in VIRAL_PROTEINS:
            unsafe_records.append({
                "ident": key,
                "reason": "host identifier collides with viral protein",
                "owners": sorted(canon_set)})
        else:
            searchable[key] = {"canonical": next(iter(canon_set)),
                               "kind": kinds[key]}

    # viral proteins as endpoints for co-occurrence (not panel genes)
    viral_searchable = {}
    for vp in VIRAL_PROTEINS:
        if alnum_len(vp) < MIN_ALNUM or vp in owners:
            continue  # NA, M1, M2, PA, NP, HA unsafe; host-owned tokens skip
        viral_searchable[vp] = {"canonical": vp, "kind": "viral"}

    return searchable, viral_searchable, unsafe_records, cat


# ============================================================ paragraphs

def split_paragraphs(text):
    """Markdown → [(para_text, start_line_0, end_line_0_exclusive)]."""
    paras = []
    cur, start = [], 0
    for i, line in enumerate(text.splitlines()):
        if line.strip():
            cur.append(line)
        else:
            if cur:
                paras.append(("\n".join(cur), start, i))
            cur, start = [], i + 1
    if cur:
        paras.append(("\n".join(cur), start, len(text.splitlines())))
    return paras


# ============================================================ rg scan

def rg_pattern(searchable, viral_searchable):
    idents = sorted(set(searchable) | set(viral_searchable),
                    key=lambda s: (-len(s), s))  # longest-first alternation
    return r"\b(?:" + "|".join(re.escape(i) for i in idents) + r")\b"


def rg_scan(pattern, files):
    """One rg run → {file_stem: {line_no_0: [MATCHED_TEXT_UPPER, ...]}}."""
    hits = defaultdict(lambda: defaultdict(list))
    if not files:
        return hits
    proc = subprocess.run(
        ["rg", "--json", "-i", "-o", "--no-heading", "-e", pattern]
        + [str(f) for f in files],
        capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "match":
            continue
        data = event["data"]
        path = data["path"]["text"]
        line_no = data["line_number"] - 1  # 0-based
        matched = data["submatches"][0]["match"]["text"]  # original case
        hits[Path(path).stem].setdefault(line_no, []).append(matched)
    return hits


# ============================================================ windows

def window_id(gene, paper_id, p0, p1, text):
    norm = re.sub(r"\s+", " ", text.strip())[:160]
    raw = f"{gene}|{paper_id}|{p0}|{p1}|{norm}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def merge_ranges(ranges):
    """Merge overlapping/adjacent paragraph ranges."""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [list(ranges[0])]
    for p0, p1 in ranges[1:]:
        if p0 <= merged[-1][1]:  # overlap (windows already include context)
            merged[-1][1] = max(merged[-1][1], p1)
        else:
            merged.append([p0, p1])
    return [tuple(r) for r in merged]


def co_occurrences(text, regex, searchable, viral_searchable, case_sensitive):
    genes, viral = set(), set()
    for m in regex.finditer(text):
        token = m.group(0)
        key = token.upper()
        if key in case_sensitive and token != key:
            continue
        if key in searchable:
            genes.add(searchable[key]["canonical"])
        elif key in viral_searchable:
            viral.add(key)
    return sorted(genes), sorted(viral)


# ============================================================ search phase

def ready_papers():
    manifest = json.loads(MANIFEST.read_text())
    return [r["paper_id"] for r in manifest["papers"] if r["status"] == "ready"]


def load_paragraphs(paper_ids):
    paras = {}
    for pid in paper_ids:
        p = MD_DIR / f"{pid}.md"
        if p.exists():
            paras[pid] = split_paragraphs(p.read_text(errors="replace"))
    return paras


def run_search(only_gene=None):
    t0 = time.time()
    searchable, viral_searchable, unsafe_records, cat = build_identifier_index()
    print(f"[search] identifiers: {len(searchable)} searchable host, "
          f"{len(viral_searchable)} viral, {len(unsafe_records)} unsafe")

    pattern = rg_pattern(searchable, viral_searchable)
    paper_ids = ready_papers()
    files = [MD_DIR / f"{pid}.md" for pid in paper_ids]
    print(f"[search] rg over {len(files)} ready papers "
          f"(manifest-gated; missing ≠ negative evidence)")
    hits = rg_scan(pattern, files)
    n_hits = sum(len(ls) for f in hits.values() for ls in f.values())
    print(f"[search] rg matched {n_hits} lines in "
          f"{len(hits)} papers ({time.time() - t0:.1f}s)")

    paragraphs = load_paragraphs(sorted(hits.keys()))
    regex = re.compile(pattern, re.IGNORECASE)

    # ---- case-collision policy: identifiers that are common English words
    # (KIT, STING, ACE...) are attributed ONLY on exact-case matches, so
    # "test kit"/"Kit fox" never ground a gene window. Mixed-case biology
    # spellings (mTOR, cGAS, Bcl-2) stay case-insensitive.
    case_sensitive = english_word_identifiers(set(searchable)
                                              | set(viral_searchable))
    if case_sensitive:
        print(f"[search] case-sensitive (English-word collision): "
              f"{sorted(case_sensitive)}")

    # ---- attribute hits → (gene, paper) paragraph ranges
    gene_paper_paras = defaultdict(set)   # (gene, pid) → {para_idx}
    gene_vias = defaultdict(set)          # (gene, pid) → {ident}
    for pid, line_hits in hits.items():
        paras = paragraphs.get(pid)
        if not paras:
            continue
        # line → paragraph index map
        line2para = {}
        for idx, (_, s, e) in enumerate(paras):
            for ln in range(s, e):
                line2para[ln] = idx
        for line_no, tokens in line_hits.items():
            para_idx = line2para.get(line_no)
            if para_idx is None:
                continue
            for token in tokens:
                key = token.upper()
                if key in case_sensitive and token != key:
                    continue  # lowercase/titlecase mention of a word-collision symbol
                src = searchable.get(key)
                if src:
                    k = (src["canonical"], pid)
                    gene_paper_paras[k].add(para_idx)
                    gene_vias[k].add((key, src["kind"]))

    # ---- expand to windows (paragraph ±1), dedupe, co-occurring endpoints
    windows = []
    for (gene, pid), para_idxs in sorted(gene_paper_paras.items()):
        ranges = merge_ranges(
            [(max(0, i - 1), min(len(paragraphs[pid]), i + 2))
             for i in para_idxs])
        for p0, p1 in ranges:
            text = "\n\n".join(paragraphs[pid][i][0] for i in range(p0, p1))
            co_genes, co_viral = co_occurrences(
                text, regex, searchable, viral_searchable, case_sensitive)
            co_genes = [g for g in co_genes if g != gene]
            vias = sorted(gene_vias[(gene, pid)])
            windows.append({
                "window_id": window_id(gene, pid, p0, p1, text),
                "gene": gene,
                "paper_id": pid,
                "via": [{"ident": i, "kind": k} for i, k in vias],
                "para": [p0, p1],
                "char_len": len(text),
                "co_genes": co_genes[:16],
                "co_viral": co_viral[:8],
                "eligible": bool(co_genes or co_viral),
            })

    # ---- status for EVERY gene (hit / no_hit / unsearchable)
    genes_with_windows = {w["gene"] for w in windows}
    unsafe_by_ident = {r["ident"]: r["reason"] for r in unsafe_records}
    unsafe_for_gene = defaultdict(list)
    viral_unsearchable = []
    for rec_ in unsafe_records:
        if rec_["owners"]:
            for owner in rec_["owners"]:
                if owner in cat:
                    unsafe_for_gene[owner].append(
                        {"ident": rec_["ident"], "reason": rec_["reason"]})
        else:
            viral_unsearchable.append({"ident": rec_["ident"],
                                       "reason": rec_["reason"]})

    status = {}
    for gene in sorted(cat):
        ids = identifier_list(searchable, gene)
        unsafe_entries = [
            {"ident": e["ident"], "reason": e["reason"]}
            for e in sorted(unsafe_for_gene.get(gene, []),
                            key=lambda e: e["ident"])
            if e["ident"] != gene.upper()
        ]
        rec = {
            "gene": gene,
            "identifiers": ids,
            "n_windows": sum(1 for w in windows if w["gene"] == gene),
            "n_papers": len({w["paper_id"] for w in windows
                             if w["gene"] == gene}),
        }
        if gene in genes_with_windows:
            rec["status"] = "hit"
        elif not ids:
            # no searchable identifier left → unsearchable, never no_hit
            rec["status"] = "unsearchable"
        else:
            rec["status"] = "no_hit"
        if unsafe_entries and rec["status"] != "unsearchable":
            rec["partial_unsafe"] = unsafe_entries
        if rec["status"] == "unsearchable":
            rec["unsafe"] = unsafe_entries or [{
                "ident": gene, "reason": "no searchable identifiers"}]
        status[gene] = rec

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    counts = defaultdict(int)
    for rec in status.values():
        counts[rec["status"]] += 1
    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "counts": dict(counts),
        "papers_searched": len(files),
        "genes": status,
        "viral_unsearchable": sorted(viral_unsearchable,
                                      key=lambda r: r["ident"]),
    }
    STATUS_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    with WINDOWS_PATH.open("w") as f:
        for w in windows:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")

    print(f"[search] genes: " + ", ".join(f"{k}={v}" for k, v
                                          in sorted(counts.items())))
    print(f"[search] windows: {len(windows)} "
          f"({sum(1 for w in windows if w['eligible'])} eligible) → "
          f"{WINDOWS_PATH.relative_to(ROOT)}")
    print(f"[search] status  → {STATUS_PATH.relative_to(ROOT)}")
    return out


def identifier_list(searchable, gene):
    return sorted(i for i, s in searchable.items()
                  if s["canonical"] == gene)


# ============================================================ classify

MECHANISMS = {"activation", "inhibition", "binding", "cleavage_trafficking",
              "viral_dependency"}
STAGES = {"early", "middle", "late", "unclear"}

SYSTEM_PROMPT = """You extract gene-relationship evidence from avian influenza research passages.

For each numbered passage window you judge the FOCUS GENE against the other
known genes / viral proteins present:

- "no_relation": the passage does not state a specific relationship involving
  the focus gene.
- "mechanistic": the passage states an explicit mechanism: activation or
  induction, inhibition or suppression, physical binding, cleavage or
  trafficking, or a viral dependency/support (virus needs or antagonizes the
  host factor). Co-expression alone, shared pathway membership, phenotype
  association, and general discussion are NOT mechanistic.
- "contextual": the passage gives functional context about the focus gene
  (role, location, species, phenotype, timing) without a mechanistic link to
  another listed endpoint.

Mechanistic types (exactly one): activation | inhibition | binding |
cleavage_trafficking | viral_dependency.

Return ONLY a JSON array with EXACTLY one object per window, in order:
[{"window": 1, "verdict": "no_relation"},
 {"window": 2, "verdict": "mechanistic",
  "from": "SYMBOL-that-acts", "to": "SYMBOL-acted-on", "mechanism": "activation",
  "quote": "one verbatim sentence from the window",
  "context": {"stage": "early|middle|late|unclear",
              "location": "cellular location or empty",
              "species": "experimental species or empty",
              "phenotype": "observed phenotype or empty",
              "evidence_type": "experimental|observational|review|computational",
              "timepoints": "verbatim reported infection timepoints, e.g. '12 hpi', or empty"}},
 {"window": 3, "verdict": "contextual",
  "context": {"stage": "...", "location": "...", "species": "...",
              "phenotype": "...", "evidence_type": "...", "timepoints": "..."}}]

Rules:
- from/to symbols must appear in the window and be from the listed endpoints
  (focus gene, other known genes, viral proteins). For binding use
  from = focus gene. For viral dependency use from = viral protein.
- stage is the CONCEPTUAL phase of the infection course (early/middle/late/
  unclear) — NEVER copy hours-post-infection into it; report those verbatim
  in context.timepoints.
- The quote must be copied verbatim from the window text and span at most
  ~35 words (a single sentence or clause).
- No text outside the JSON array."""


def muse_chat(system, user, url, model, max_tokens=32000, temperature=0.1):
    """Single Muse call; tolerates reasoning-content-only responses."""
    r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user +
             "\n\n(Reply with ONLY the JSON array. No text after it.)"},
        ],
        "max_tokens": max_tokens, "temperature": temperature,
    }, timeout=900)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    content = (msg.get("content") or "").strip()
    if not content and msg.get("reasoning_content"):
        content = msg["reasoning_content"].strip()
    return content


def extract_json_array(text):
    """Last complete, balanced, parseable JSON array in the text (greedy
    regexes either swallow separators between arrays or stop at the first
    object; a bracket scanner gets this right)."""
    if not text:
        return None
    best = None
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        val = json.loads(text[start:i + 1])
                        if isinstance(val, list):
                            best = val
                    except Exception:
                        pass
                    start = None
    return best


def extract_json_object(text):
    """Last complete, balanced, parseable JSON object in the text."""
    if not text:
        return None
    best = None
    depth = 0
    start = None
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        val = json.loads(text[start:i + 1])
                        if isinstance(val, dict):
                            best = val
                    except Exception:
                        pass
                    start = None
    return best


def load_windows(gene=None):
    if not WINDOWS_PATH.exists():
        sys.exit("no windows.jsonl — run `connections.py search` first")
    out = []
    for line in WINDOWS_PATH.read_text().splitlines():
        w = json.loads(line)
        if not w.get("eligible"):
            continue
        if gene and w["gene"] != gene:
            continue
        out.append(w)
    return out


def window_text(w):
    """Re-read the window paragraphs from disk (text is not stored in the
    window record — windows.jsonl stays lean; the paper md is the source)."""
    md = MD_DIR / f"{w['paper_id']}.md"
    paras = split_paragraphs(md.read_text(errors="replace"))
    p0, p1 = w["para"]
    return "\n\n".join(paras[i][0] for i in range(p0, p1))


def chunk_windows(gene_windows, max_windows=4, max_chars=14000):
    """Pack a gene's windows into Muse-sized chunks."""
    chunks, cur, cur_chars = [], [], 0
    for w in gene_windows:
        text = window_text(w)
        if cur and (len(cur) >= max_windows or cur_chars + len(text) > max_chars):
            chunks.append(cur)
            cur, cur_chars = [], 0
        cur.append((w, text))
        cur_chars += len(text)
    if cur:
        chunks.append(cur)
    return chunks


def build_user_prompt(gene, chunk):
    parts = [f"FOCUS GENE: {gene}"]
    endpoints = set()
    for w, _ in chunk:
        endpoints.update(w.get("co_genes", []))
        endpoints.update(w.get("co_viral", []))
    parts.append("OTHER KNOWN ENDPOINTS IN THESE PASSAGES: "
                 + ", ".join(sorted(endpoints)))
    for i, (w, text) in enumerate(chunk, 1):
        if len(text) > 4000:
            text = text[:4000] + " …[truncated]"
        parts.append(f"[WINDOW {i}] (paper {w['paper_id']})\n{text}")
    return "\n\n".join(parts)


# ---- grounding validation ---------------------------------------------

_DASH_QUOTES = {"\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
                "\u201c": '"', "\u201d": '"', "\u2212": "-"}


def build_endpoint_index():
    """Alias-aware endpoint tools for grounding.

    Returns (canonical_of, aliases_of, case_sensitive):
      canonical_of: any identifier (RIG-I, MDA5, IL-18 …) → canonical symbol
      aliases_of:   canonical → identifiers that may appear in text
      case_sensitive: identifiers needing exact-case matches (KIT, STING…)
    """
    searchable, viral_searchable, unsafe_records, cat = build_identifier_index()
    canonical_of = {}
    aliases_of = defaultdict(set)
    for ident, src in searchable.items():
        canonical_of[ident] = src["canonical"]
        aliases_of[src["canonical"]].add(ident)
    for vp, src in viral_searchable.items():
        canonical_of[vp] = vp
        aliases_of[vp].add(vp)
    case_sensitive = english_word_identifiers(set(searchable)
                                              | set(viral_searchable))
    return dict(canonical_of), {k: sorted(v) for k, v in aliases_of.items()}, \
        case_sensitive


def _norm(s):
    for k, v in _DASH_QUOTES.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip().lower()


def _mention_check(symbol, text_norm, aliases_of, case_sensitive):
    """Boundary-aware presence of ANY spelling of the canonical symbol."""
    for ident in aliases_of.get(symbol, [symbol]):
        strict = ident in case_sensitive
        for form in ([ident] if strict else [ident, ident.lower(),
                                            ident.capitalize()]):
            pat = (r"(?:^|[^A-Za-z0-9])" + re.escape(form)
                   + r"(?:[^A-Za-z0-9]|$)")
            if re.search(pat, text_norm):
                return True
    return False


def validate_candidate(entry, w, text, endpoint_index):
    """Returns (candidate-dict | None, failure-reason | None)."""
    canonical_of, aliases_of, case_sensitive = endpoint_index
    if entry.get("verdict") != "mechanistic":
        return None, None
    frm_raw = str(entry.get("from") or "").upper().strip()
    to_raw = str(entry.get("to") or "").upper().strip()
    # alias spellings (RIG-I, MDA5, IL-18) normalise to canonical endpoints
    frm = canonical_of.get(frm_raw, frm_raw)
    to = canonical_of.get(to_raw, to_raw)
    mech = str(entry.get("mechanism") or "").lower().strip()
    quote = re.sub(r"\s+", " ", str(entry.get("quote") or "")).strip()

    if mech not in MECHANISMS:
        return None, f"invalid mechanism {mech!r}"
    if frm not in aliases_of:
        return None, f"unknown endpoint {frm_raw!r}"
    if to not in aliases_of:
        return None, f"unknown endpoint {to_raw!r}"
    if frm == to:
        return None, "self-edge"
    gene = w["gene"]
    if gene not in (frm, to):
        return None, "focus gene is not an endpoint"

    text_norm = _norm(text)
    if not _mention_check(frm, text_norm, aliases_of, case_sensitive) \
            or not _mention_check(to, text_norm, aliases_of, case_sensitive):
        return None, "endpoint not mentioned in supplied context"
    if len(quote) < 15 or _norm(quote) not in text_norm:
        return None, "quote not found verbatim in window"

    ctx = entry.get("context") or {}
    stage = str(ctx.get("stage") or "").lower().strip()
    if stage not in STAGES:
        stage = "unclear"
    candidate = {
        "candidate_id": hashlib.sha1(
            f"{gene}|{w['paper_id']}|{w['window_id']}|{frm}|{to}|{mech}"
            .encode()).hexdigest()[:12],
        "window_id": w["window_id"],
        "gene": gene,
        "paper_id": w["paper_id"],
        "from": frm,
        "to": to,
        "mechanism": mech,
        "quote": quote[:600],
        "context": {
            "proposed_stage": stage,
            "location": str(ctx.get("location") or "").strip()[:200],
            "species": str(ctx.get("species") or "").strip()[:120],
            "phenotype": str(ctx.get("phenotype") or "").strip()[:300],
            "evidence_type": str(ctx.get("evidence_type") or "").strip()[:60],
            "reported_timepoints": str(ctx.get("timepoints") or "").strip()[:200],
        },
        "status": "pending",
    }
    return candidate, None


def verdicts_done():
    done = set()
    if VERDICTS_PATH.exists():
        for line in VERDICTS_PATH.read_text().splitlines():
            try:
                done.add(json.loads(line)["window_id"])
            except Exception:
                pass
    return done


def append_jsonl(path, records):
    with path.open("a") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


DISCOVERY_PATH = ROOT / "data" / "papers" / "gene_discovery.jsonl"


def log_counterpart_discovery(paper_id, symbol):
    """Non-panel gene proposed as a connection endpoint → the existing
    discovery queue (never a graph node; a large pattern across papers may
    earn panel candidacy through the normal review path)."""
    sym = symbol.strip().upper()
    if not sym or len(sym) > 12 or not re.fullmatch(r"[A-Z0-9][A-Z0-9./-]*", sym):
        return
    with DISCOVERY_PATH.open("a") as f:
        f.write(json.dumps({
            "paper_id": paper_id, "gene": sym,
            "role": "proposed connection counterpart (not in panel)",
        }, ensure_ascii=False) + "\n")


def run_classify(url, model, workers, gene=None, limit_windows=0):
    t0 = time.time()
    endpoint_index = build_endpoint_index()
    canonical_of, aliases_of, _ = endpoint_index

    windows = load_windows(gene)
    done = verdicts_done()
    todo = [w for w in windows if w["window_id"] not in done]
    if limit_windows:
        todo = todo[:limit_windows]
    print(f"[classify] eligible windows: {len(windows)} done: {len(done)} "
          f"todo: {len(todo)}")
    if not todo:
        print("[classify] nothing to do")
        return

    # group by gene → chunks (no per-paper cap: every window is processed)
    by_gene = defaultdict(list)
    for w in todo:
        by_gene[w["gene"]].append(w)
    jobs = []
    for g, ws in sorted(by_gene.items()):
        for chunk in chunk_windows(ws):
            jobs.append((g, chunk))
    print(f"[classify] muse calls: {len(jobs)} "
          f"(avg {sum(len(c) for _, c in jobs) / len(jobs):.1f} windows/call)")

    stats = defaultdict(int)
    tunnel_down = []
    lock_write = []  # collected under threads, appended by main thread

    def work(job):
        g, chunk = job
        prompt = build_user_prompt(g, chunk)
        try:
            content = muse_chat(SYSTEM_PROMPT, prompt, url, model)
        except Exception as e:  # tunnel drop / timeout → surface as abort
            return {"kind": "tunnel", "err": str(e)[:120], "gene": g}
        parsed = extract_json_array(content)
        if parsed is None:
            # invalid JSON → one retry (plan), then quarantine
            try:
                content = muse_chat(SYSTEM_PROMPT +
                                    "\nYour previous reply was not valid "
                                    "JSON. Output ONLY the JSON array.",
                                    prompt, url, model)
                parsed = extract_json_array(content)
            except Exception as e:
                return {"kind": "tunnel", "err": str(e)[:120], "gene": g}
        results = []
        # match entries by reported window number when present, else position
        by_no = {}
        for e in parsed or []:
            if isinstance(e, dict):
                no = e.get("window")
                if isinstance(no, int) and 1 <= no <= len(chunk):
                    by_no[no] = e
        for i, (w, text) in enumerate(chunk, 1):
            entry = by_no.get(i)
            if entry is None and parsed and i <= len(parsed) \
                    and isinstance(parsed[i - 1], dict) \
                    and "window" not in parsed[i - 1]:
                entry = parsed[i - 1]
            if entry is None:
                results.append((w, {
                    "window_id": w["window_id"], "gene": g,
                    "paper_id": w["paper_id"], "verdict": "quarantined",
                    "reason": "missing or non-object entry in response"},
                    None, {"window_id": w["window_id"], "gene": g,
                           "paper_id": w["paper_id"],
                           "reason": "malformed response",
                           "raw": (content or "")[:500]}))
                continue
            verdict = str(entry.get("verdict") or "").lower().strip()
            if verdict not in ("no_relation", "mechanistic", "contextual"):
                verdict = "quarantined"
            cand, failure = None, None
            if verdict == "mechanistic":
                cand, failure = validate_candidate(
                    entry, w, text, endpoint_index)
                if failure:
                    verdict = "quarantined"
                    # non-panel counterpart proposals feed the discovery queue
                    if failure.startswith("unknown endpoint"):
                        m = re.search(r"'([^']+)'", failure)
                        if m:
                            log_counterpart_discovery(w["paper_id"], m.group(1))
            rec = {"window_id": w["window_id"], "gene": g,
                   "paper_id": w["paper_id"], "verdict": verdict}
            if verdict == "contextual":
                ctx = entry.get("context") or {}
                rec["context"] = {
                    "proposed_stage": str(ctx.get("stage") or "").lower()
                    .strip()[:20],
                    "location": str(ctx.get("location") or "").strip()[:200],
                    "species": str(ctx.get("species") or "").strip()[:120],
                    "phenotype": str(ctx.get("phenotype") or "").strip()[:300],
                    "evidence_type": str(ctx.get("evidence_type") or "")
                    .strip()[:60],
                    "reported_timepoints": str(ctx.get("timepoints") or "")
                    .strip()[:200],
                }
            quar = None
            if verdict == "quarantined":
                quar = {"window_id": w["window_id"], "gene": g,
                        "paper_id": w["paper_id"],
                        "reason": failure or f"verdict {verdict!r}",
                        "raw": json.dumps(entry)[:500]}
            results.append((w, rec, cand, quar))
        return {"kind": "ok", "results": results, "gene": g}

    out_verdicts, out_cands, out_quar = [], [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(work, job): job for job in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            if res["kind"] == "tunnel":
                tunnel_down.append(res)
                continue
            for w, rec, cand, quar in res["results"]:
                stats[rec["verdict"]] += 1
                out_verdicts.append(rec)
                if cand:
                    out_cands.append(cand)
                if quar:
                    out_quar.append(quar)
            if i % 20 == 0 or i == len(jobs):
                append_jsonl(VERDICTS_PATH, out_verdicts)
                append_jsonl(CANDIDATES_PATH, out_cands)
                append_jsonl(QUARANTINE_PATH, out_quar)
                out_verdicts, out_cands, out_quar = [], [], []
                print(f"  [{i}/{len(jobs)}] "
                      + " ".join(f"{k}={v}" for k, v in
                                  sorted(stats.items())))

    if out_verdicts:
        append_jsonl(VERDICTS_PATH, out_verdicts)
        append_jsonl(CANDIDATES_PATH, out_cands)
        append_jsonl(QUARANTINE_PATH, out_quar)

    print(f"[classify] done in {time.time() - t0:.0f}s: "
          + " ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    _llm_track("connections_classify", model, "classify-v2",
               sum(stats.values()),
               notes=f"windows classified: {dict(stats)}")
    if tunnel_down:
        print(f"[classify] MUSE TUNNEL ERRORS on {len(tunnel_down)} calls "
              f"(e.g. {tunnel_down[0]['err']}) — rerun to resume; "
              "all findings remain pending review")
        sys.exit(2)


# ============================================================ review

REVIEW_PATH = OUT_DIR / "review_decisions.json"
REPORT_PATH = OUT_DIR / "review_report.md"

# Legacy-curated edges mirrored from web/src/routes/ModelCyto.svelte
# (SIGNAL_EDGES / INHIBIT_EDGES / INTERACTIONS). They seed the published
# relationship file (source: curated) and flag report rows matching an
# already-curated connection. Tuples: (from, to, mechanism, label).
LEGACY_EDGES = [
    ("DDX58", "MAVS", "activation", "activates"),
    ("IFIH1", "MAVS", "activation", "activates"),
    ("TLR3", "TICAM1", "activation", "activates"),
    ("TLR7", "MYD88", "activation", "activates"),
    ("TLR21", "MYD88", "activation", "activates"),
    ("TLR4", "MYD88", "activation", "activates"),
    ("MAVS", "IRF3", "activation", "activates"),
    ("MAVS", "IRF7", "activation", "activates"),
    ("MYD88", "IRF7", "activation", "activates"),
    ("TICAM1", "IRF3", "activation", "activates"),
    ("IRF3", "IFNB1", "activation", "activates"),
    ("IRF7", "IFNA1", "activation", "activates"),
    ("IFNB1", "JAK2", "activation", "activates"),
    ("IFNA1", "JAK2", "activation", "activates"),
    ("JAK2", "STAT1", "activation", "activates"),
    ("JAK2", "STAT2", "activation", "activates"),
    ("STAT1", "MX1", "activation", "activates"),
    ("STAT1", "IFITM3", "activation", "activates"),
    ("STAT1", "OASL", "activation", "activates"),
    ("STAT1", "EIF2AK2", "activation", "activates"),
    ("STAT1", "BST2", "activation", "activates"),
    ("STAT1", "RSAD2", "activation", "activates"),
    ("STAT1", "ISG15", "activation", "activates"),
    ("IRF1", "IFNB1", "activation", "activates"),
    ("NLRP3", "CASP1", "activation", "activates"),
    ("CASP1", "IL1B", "activation", "activates"),
    ("TRIM25", "DDX58", "activation", "activates"),
    ("UNC93B1", "TLR3", "cleavage_trafficking", "traffics"),
    ("UNC93B1", "TLR7", "cleavage_trafficking", "traffics"),
    ("UNC93B1", "TLR21", "cleavage_trafficking", "traffics"),
    ("STING1", "IRF3", "activation", "activates"),
    ("TLR4", "TICAM1", "activation", "uses adaptor"),
    ("NOD1", "RIPK2", "activation", "signals through"),
    ("TAP1", "B2M", "binding", "supports MHC-I"),
    ("TAP2", "B2M", "binding", "supports MHC-I"),
    ("HERC5", "ISG15", "binding", "conjugates"),
    ("MYD88", "TNF", "activation", "induces"),
    ("MYD88", "IL6", "activation", "induces"),
    ("RIPK2", "IL6", "activation", "induces"),
    ("STAT1", "TAP1", "activation", "induces"),
    ("STAT1", "B2M", "activation", "induces"),
    ("TLR4", "NLRP3", "activation", "primes"),
    ("SOCS1", "JAK2", "inhibition", "inhibits"),
    ("IL10", "IL6", "inhibition", "inhibits"),
    ("NS1", "IRF3", "inhibition", "inhibits"),
    ("PB2", "ANP32A", "viral_dependency", "polymerase support"),
    ("NS1", "IFNB1", "inhibition", "antagonizes IFN"),
    ("PA-X", "IFNB1", "inhibition", "suppresses IFN"),
    ("PB1-F2", "NLRP3", "activation", "activates inflammasome"),
    ("HA", "ST6GAL1", "binding", "α2,6 receptor binding"),
    ("FURIN", "HA", "cleavage_trafficking", "cleaves HA"),
    ("PB2", "JAK2", "inhibition", "antagonizes signaling"),
]

MECH_LABEL = {
    "activation": "activates",
    "inhibition": "inhibits",
    "binding": "binds",
    "cleavage_trafficking": "cleaves / traffics",
    "viral_dependency": "viral dependency",
}


def load_candidates():
    """Dedupe by candidate_id (append-only file, last write wins)."""
    if not CANDIDATES_PATH.exists():
        return []
    by_id = {}
    for line in CANDIDATES_PATH.read_text().splitlines():
        try:
            c = json.loads(line)
            by_id[c["candidate_id"]] = c
        except Exception:
            continue
    return list(by_id.values())


def load_decisions():
    if REVIEW_PATH.exists():
        try:
            return json.loads(REVIEW_PATH.read_text())
        except Exception:
            pass
    return {}


def save_decisions(dec):
    REVIEW_PATH.write_text(json.dumps(dec, indent=1, ensure_ascii=False))


def effective_status(cand, decisions):
    d = decisions.get(cand["candidate_id"])
    return d["status"] if d else "pending"


def legacy_match(frm, to, mech):
    """Exact pair+mechanism, or same pair any mechanism (weaker match)."""
    strong = any(f == frm and t == to and m == mech
                 for f, t, m, _ in LEGACY_EDGES)
    weak = any((f == frm and t == to) or (f == to and t == frm)
               for f, t, _, _ in LEGACY_EDGES)
    return "exact" if strong else ("pair" if weak else None)


def papers_meta():
    papers = json.loads(PAPERS_JSON.read_text())["papers"]
    return {p["id"]: p for p in papers}


def rel_key(c):
    return f"{c['from']} → {c['to']} ({c['mechanism']})"


def run_review_list(status="pending", gene=None, limit=40):
    cands = load_candidates()
    decisions = load_decisions()
    rows = [c for c in cands
            if (status == "all" or effective_status(c, decisions) == status)
            and (not gene or gene in (c["gene"], c["from"], c["to"]))]
    papers = papers_meta()
    print(f"{len(rows)} candidate(s) with effective status "
          f"'{status}'" + (f" for {gene}" if gene else ""))
    for c in rows[:limit]:
        p = papers.get(c["paper_id"], {})
        d = decisions.get(c["candidate_id"], {})
        who = (d.get("reviewer") or "-")[:6]
        print(f"  {c['candidate_id']}  [{effective_status(c, decisions):>8}]"
              f"[{who:>6}] "
              f"{c['from']} → {c['to']} ({c['mechanism']})  "
              f"· {p.get('year', '?')} {(p.get('journal') or '')[:28]}")
        print(f"      “{c['quote'][:100]}”")
    if len(rows) > limit:
        print(f"  … and {len(rows) - limit} more (use --limit)")


def run_review_decide(ids, action, note=None):
    cands = {c["candidate_id"] for c in load_candidates()}
    decisions = load_decisions()
    unknown = [i for i in ids if i not in cands]
    if unknown:
        sys.exit(f"unknown candidate id(s): {', '.join(unknown)} — "
                 "see `review list`")
    status = {"approve": "approved", "reject": "rejected"}.get(action, action)
    for i in ids:
        if action == "reset":
            decisions.pop(i, None)
        else:
            decisions[i] = {"status": status,
                            "decided": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "note": note or ""}
    save_decisions(decisions)
    print(f"{status}: {len(ids)} candidate(s) → "
          f"{REVIEW_PATH.relative_to(ROOT)}")


def run_review_stats():
    cands = load_candidates()
    decisions = load_decisions()
    stats = defaultdict(int)
    by_reviewer = defaultdict(int)
    for c in cands:
        s = effective_status(c, decisions)
        stats[s] += 1
        d = decisions.get(c["candidate_id"])
        if d and s != "pending":
            by_reviewer[d.get("reviewer") or "?"] += 1
    print("candidates:", dict(stats) or "none yet")
    if by_reviewer:
        print("decided by:", dict(by_reviewer))
    if CANDIDATES_PATH.exists():
        print(f"quarantined windows: "
              f"{sum(1 for _ in QUARANTINE_PATH.open())}")


# ---- export (publish gate) ---------------------------------------------

PUBLISHED_PATH = ROOT / "web" / "public" / "data" / "gene_relationships.json"
COUNTS_INTERNAL = ROOT / "data" / "papers" / "gene_evidence_counts.json"
COUNTS_PUBLIC = ROOT / "web" / "public" / "data" / "gene_evidence_counts.json"
GENE_OVERRIDES_PATH = OUT_DIR / "gene_overrides.json"
PUBLIC_QUOTE_CHARS = 300   # public exposure = short reviewed claims only

# Documented phase→stage mapping for reviewed stage proposals (conservative;
# only ever classifies genes that remain unclassified by every other source).
PHASE_STAGE = {"early": "sensing", "middle": "signaling", "late": "celldeath"}

# Free-text location → curated annotation vocabulary (geneGraphAnnotations)
LOC_MAP = [
    ("nucleus", ("nucleus", "nuclear")),
    ("mitochondria", ("mitochondr",)),
    ("endosome", ("endosome", "endosomal", "endocyt")),
    ("cytosol", ("cytosol", "cytoplasm")),
    ("surface", ("membrane", "cell surface", "plasma membrane", "surface")),
    ("secreted", ("secreted", "extracellular")),
    ("viral", ("virion", "viral replication", "viral rna")),
]


def map_locations(text):
    t = (text or "").lower()
    return [loc for loc, tokens in LOC_MAP if any(k in t for k in tokens)]


def run_export():
    """Publish approved relationships + legacy curated edges.

    Pending and rejected candidates NEVER reach this file. Quotes are capped
    at PUBLIC_QUOTE_CHARS — full evidence Markdown stays internal.
    Also emits reviewed stage proposals (for still-unclassified panel genes),
    a location overlay merged with curated annotations downstream, and
    reviewed connection counts merged into the evidence-count sidecar."""
    cands = load_candidates()
    decisions = load_decisions()
    papers = papers_meta()
    gp = json.loads(GENE_PRESENCE.read_text())
    panel = set(gp["gene_catalogue"])

    edges = {}

    def edge_for(frm, to, mech, source="reviewed"):
        key = (frm, to, mech)
        if key not in edges:
            edges[key] = {"from": frm, "to": to, "mechanism": mech,
                          "label": MECH_LABEL.get(mech, mech),
                          "source": source, "evidence": []}
        return edges[key]

    for frm, to, mech, label in LEGACY_EDGES:
        e = edge_for(frm, to, mech, source="curated")
        e["label"] = label

    n_ev = 0
    stage_votes = defaultdict(lambda: defaultdict(set))   # gene → stage → papers
    loc_overlay = defaultdict(set)
    for c in cands:
        if effective_status(c, decisions) != "approved":
            continue
        p = papers.get(c["paper_id"], {})
        ctx = c.get("context", {})
        e = edge_for(c["from"], c["to"], c["mechanism"])
        e["source"] = ("curated+reviewed" if e["source"] == "curated"
                        else "reviewed")
        import hashlib as _hl
        e["evidence"].append({
            "paper_id": c["paper_id"],
            "quote_h": _hl.md5(c["quote"].encode("utf-8")).hexdigest()[:12],
            "year": p.get("year"),
            "journal": (p.get("journal") or "")[:80],
            "quote": c["quote"][:PUBLIC_QUOTE_CHARS],
            "species": ctx.get("species", ""),
            "stage": ctx.get("proposed_stage", ""),
            "location": ctx.get("location", "")[:120],
            "strain": ctx.get("strain", "")[:120],
            "timepoints": ctx.get("reported_timepoints", ""),
            "evidence_type": ctx.get("evidence_type", ""),
        })
        n_ev += 1
        # reviewed context: stage proposals + location overlay (panel genes;
        # never overrides — downstream merge only fills unclassified genes)
        for sym in (c["from"], c["to"]):
            if sym not in panel:
                continue
            stage = ctx.get("proposed_stage") or ""
            if stage in PHASE_STAGE:
                stage_votes[sym][stage].add(c["paper_id"])
            for loc in map_locations(ctx.get("location")):
                loc_overlay[sym].add(loc)

    stage_proposals = {}
    for gene, votes in stage_votes.items():
        best = sorted(votes.items(),
                      key=lambda kv: (-len(kv[1]), kv[0]))[0]
        stage_proposals[gene] = {
            "proposed": best[0],
            "papers": len(best[1]),
            "stage": PHASE_STAGE[best[0]],
            "note": "phase-level proposal; classify-only (never overrides)"
        }
    location_overlay = {g: sorted(v) for g, v in sorted(loc_overlay.items())}

    edge_list = sorted(edges.values(),
                       key=lambda e: (e["from"], e["to"], e["mechanism"]))
    out = {
        "version": 1,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "_doc": ("Mechanistic relationships: legacy-curated edges plus "
                 "review-approved mined candidates. Pending/rejected "
                 "candidates never publish; quotes are trimmed."),
        "counts": {
            "edges": len(edge_list),
            "curated_only": sum(1 for e in edge_list
                                if e["source"] == "curated"),
            "with_reviewed_evidence": sum(1 for e in edge_list
                                           if e["evidence"]),
            "evidence": n_ev,
        },
        "stage_proposals": stage_proposals,
        "location_overlay": location_overlay,
        "edges": edge_list,
    }
    PUBLISHED_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"[export] {PUBLISHED_PATH.name}: {out['counts']}")

    # ---- reviewed connection counts → evidence-count sidecar (D78 item 25).
    # Merged non-destructively into the internal file and the served copy
    # (the served copy had no refresh path at all until now).
    conn_by_gene = defaultdict(lambda: {"connections": 0, "evidence": 0})
    for e in edge_list:
        if not e["evidence"]:
            continue
        for raw_sym in (e["from"], e["to"]):
            sym = resolve_gene(raw_sym) or raw_sym  # legacy edge symbols -> canonical
            c = conn_by_gene[sym]
            c["connections"] += 1
            c["evidence"] += len(e["evidence"])
    base = None
    for path in (COUNTS_INTERNAL, COUNTS_PUBLIC):
        if path.exists():
            try:
                base = json.loads(path.read_text())
                break
            except Exception:
                pass
    base = base or {}
    for sym, rec in base.items():
        rec.pop("reviewed_connections", None)
        rec.pop("reviewed_evidence", None)
    for sym, c in conn_by_gene.items():
        base.setdefault(sym, {})
        base[sym]["reviewed_connections"] = c["connections"]
        base[sym]["reviewed_evidence"] = c["evidence"]
    COUNTS_INTERNAL.write_text(json.dumps(base, indent=1))
    COUNTS_PUBLIC.write_text(json.dumps(base, indent=1))

    def _rel(p):
        try:
            return p.relative_to(ROOT)
        except ValueError:
            return p

    print(f"[export] reviewed counts → {_rel(COUNTS_INTERNAL)} + "
          f"{_rel(COUNTS_PUBLIC)} "
          f"({len(conn_by_gene)} genes with reviewed connections)")
    return out


# ---- report ------------------------------------------------------------

def run_report():
    """Internal review report — full Markdown stays internal (plan).
    Grouped by proposed relationship with independent-paper support and
    existing curated-edge matches."""
    cands = load_candidates()
    decisions = load_decisions()
    papers = papers_meta()
    if not cands:
        print("no candidates yet — run classify first")
        return

    groups = defaultdict(list)
    for c in cands:
        groups[(c["from"], c["to"], c["mechanism"])].append(c)

    status_order = {"approved": 0, "pending": 1, "rejected": 2}
    lines = [
        "# Connection mining — review report",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} · INTERNAL ONLY — "
        "full quotes/Markdown never leave this file.",
        "",
        f"- candidates: {len(cands)} "
        f"(approved {sum(1 for c in cands if effective_status(c, decisions) == 'approved')}, "
        f"pending {sum(1 for c in cands if effective_status(c, decisions) == 'pending')}, "
        f"rejected {sum(1 for c in cands if effective_status(c, decisions) == 'rejected')})",
        f"- proposed relationships: {len(groups)}",
        f"- relationships with ≥2 independent papers: "
        f"{sum(1 for g in groups.values() if len({c['paper_id'] for c in g}) >= 2)}",
        "",
        "Decide via `connections.py review approve|reject <id>` or by editing "
        "`review_decisions.json`. Pending and rejected candidates never "
        "reach published data.",
        "",
        "---",
        "",
    ]

    for (frm, to, mech), group in sorted(
            groups.items(),
            key=lambda kv: (-len({c["paper_id"] for c in kv[1]}), kv[0])):
        n_papers = len({c["paper_id"] for c in group})
        lm = legacy_match(frm, to, mech)
        tag = {"exact": " · MATCHES curated edge (same mechanism)",
               "pair": " · overlaps curated pair (different mechanism)"}.get(lm, "")
        lines.append(f"## {frm} → {to} — {mech}")
        lines.append("")
        lines.append(f"*{n_papers} independent paper(s) · "
                     f"{len(group)} candidate(s){tag}*")
        lines.append("")
        for c in sorted(group, key=lambda c: (status_order.get(
                effective_status(c, decisions), 3), c["paper_id"])):
            p = papers.get(c["paper_id"], {})
            ctx = c.get("context", {})
            ctx_bits = [b for b in (
                f"stage: {ctx.get('proposed_stage')}" if ctx.get("proposed_stage") and ctx["proposed_stage"] != "unclear" else "",
                f"sp: {ctx.get('species')}" if ctx.get("species") else "",
                f"loc: {ctx.get('location')}" if ctx.get("location") else "",
                f"tp: {ctx.get('reported_timepoints')}" if ctx.get("reported_timepoints") else "",
                f"ev: {ctx.get('evidence_type')}" if ctx.get("evidence_type") else "",
            ) if b]
            lines.append(f"- `[{effective_status(c, decisions)}]` "
                         f"`{c['candidate_id']}` "
                         f"**{p.get('year', '?')} · {(p.get('title') or c['paper_id'])[:90]}**")
            lines.append(f"  > {c['quote'][:220]}")
            if ctx_bits:
                lines.append(f"  · {' · '.join(ctx_bits)}")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"report → {REPORT_PATH.relative_to(ROOT)} "
          f"({len(cands)} candidates, {len(groups)} relationships)")


# ---- automated first-pass review (muse-glimmer, D79) --------------------

AUTO_DONE_PATH = OUT_DIR / "auto_review_done.jsonl"
APPEALS_PATH = OUT_DIR / "appeals.jsonl"
APPEALS_DONE_PATH = OUT_DIR / "appeals_done.jsonl"

# Nomenclature equivalences the appeal judge MAY use when deciding whether a
# passage supports a claim (never to alter quotes):
EQUIVALENCES = """- RIG-I = DDX58; MDA5 = IFIH1; LGP2 = DHX58; PKR = EIF2AK2;
  iNOS = NOS2; STING = STING1; Mx = MX1 family.
- "FluPol" / "viral polymerase" / "polymerase complex" = the PB2+PB1+PA
  complex. A statement about the polymerase supports a PB2 (or PB1/PA) claim
  ONLY when the passage ties the interaction to that subunit (e.g. residue
  627 or 701N of PB2, PB2 mutations, PB2-containing subcomplex).
- "interacts with / associates with / complex with" CAN state physical
  binding when the passage describes direct molecular interaction; a purely
  genetic or co-expression association does NOT.
- A quote naming only an alias (RIG-I for DDX58) still supports the claim for
  the canonical symbol."""

INVESTIGATOR_PROMPT = """You re-examine REJECTED gene-relationship candidates with MORE context than the first reviewer had: the claim, the recorded rejection reason, and the FULL source passage the evidence came from.

Decide for each candidate:
- "overturn": the passage explicitly states the claimed mechanistic relationship (type AND direction), possibly in a different sentence than the original quote or under a standard alias.
- "uphold": the passage does not explicitly state it (mentions both genes, co-expression, wrong direction, different pair, or speculation).
- "uncertain": cannot tell from the passage.

Nomenclature equivalences you MAY use when judging (never to alter quotes):
{nomenclature}

ANTI-HALLUCINATION RULES (absolute):
- Judge ONLY from the supplied passage. Never use outside knowledge to overturn.
- Every verdict MUST carry a "quote" copied VERBATIM from that candidate's passage (copy-paste; do not paraphrase, fix typos, or merge sentences). If you cannot find one, the verdict must be "uphold" or "uncertain" with an empty quote.
- Overturning requires the quoted sentence itself to state the mechanism and direction.

Return ONLY JSON:
{{"candidate_verdicts": [{{"candidate_id": "...", "verdict": "overturn|uphold|uncertain", "reason": "one sentence", "quote": "verbatim from that passage, or empty"}}]}}
One entry per supplied candidate, same order.""".format(nomenclature=EQUIVALENCES)

SKEPTIC_PROMPT = """You are the final check on a proposed OVERTURN of a rejected gene-relationship candidate. An appeal reviewer found a sentence it claims explicitly states the relationship.

Given the claim and that single quoted sentence, decide:
- "confirm": the sentence EXPLICITLY states this mechanistic relationship with this direction (aliases per the equivalence list are acceptable).
- "deny": the sentence alone does not state it.

Nomenclature equivalences you MAY use (never to alter the quote):
{nomenclature}

ANTI-HALLUCINATION RULES: judge ONLY the supplied sentence; no outside knowledge; copy your "quote" VERBATIM from the supplied sentence (or empty).

Return ONLY JSON:
{{"verdict": "confirm|deny", "reason": "one sentence", "quote": "verbatim or empty"}}""".format(nomenclature=EQUIVALENCES)


def _windows_by_id():
    if not WINDOWS_PATH.exists():
        return {}
    out = {}
    for line in WINDOWS_PATH.read_text().splitlines():
        try:
            w = json.loads(line)
            out[w["window_id"]] = w
        except Exception:
            pass
    return out


def _passage_for(cand, windows):
    """Full source passage for a candidate, original quote guaranteed inside."""
    w = windows.get(cand.get("window_id"))
    if not w:
        return cand.get("quote", "")
    try:
        text = window_text(w)
    except Exception:
        return cand.get("quote", "")
    if _norm(cand.get("quote", "")) not in _norm(text):
        # window text drifted (should not happen) — fall back to quote + head
        return cand.get("quote", "") + "\n[passage unavailable]"
    if len(text) > 3000:
        q = cand.get("quote", "")
        pos = _norm(text).find(_norm(q)) if q else -1
        start = max(0, min(pos - 1200, len(text) - 3000))
        text = text[start:start + 3000]
    return text


def run_review_appeal(url, model, workers=8, limit_batches=0,
                       temperature=0.1):
    """Second-pass investigation of muse-rejected candidates.

    Stage 1 (investigator): full passage + rejection reason + equivalences
    → overturn proposals with verbatim passage quotes.
    Stage 2 (skeptic): each overturn re-checked against its single quoted
    sentence; only double-confirmed overturns become approvals
    (reviewer: muse-appeal). Human decisions are never touched."""
    cands = load_candidates()
    decisions = load_decisions()
    windows = _windows_by_id()

    rejected = [c for c in cands
                if decisions.get(c["candidate_id"], {}).get("status")
                == "rejected"
                and decisions[c["candidate_id"]].get("reviewer") == "muse"]
    groups = defaultdict(list)
    for c in rejected:
        groups[(c["from"], c["to"], c["mechanism"])].append(c)

    done = set()
    if APPEALS_DONE_PATH.exists():
        for line in APPEALS_DONE_PATH.read_text().splitlines():
            try:
                done.add(json.loads(line)["batch"])
            except Exception:
                pass

    batches = []
    for key, group in sorted(groups.items()):
        for i in range(0, len(group), 4):
            chunk = group[i:i + 4]
            bkey = ",".join(sorted(c["candidate_id"] for c in chunk))
            if bkey in done:
                continue
            batches.append((key, chunk, bkey))
    if limit_batches:
        batches = batches[:limit_batches]
    print(f"[appeal] muse-rejected candidates: {len(rejected)} in "
          f"{len(groups)} relationships → {len(batches)} batches to investigate")
    if not batches:
        print("[appeal] nothing to do")
        return

    def build_payload(chunk):
        parts = []
        for c in chunk:
            d = decisions[c["candidate_id"]]
            parts.append(
                f"[CANDIDATE] id={c['candidate_id']}\n"
                f"claim: {c['from']} --{c['mechanism']}--> {c['to']}\n"
                f"recorded rejection reason: {d.get('note', '')[:250]}\n"
                f"source passage (verbatim from the paper):\n"
                f"{_passage_for(c, windows)}")
        return "\n\n".join(parts)

    def work(batch):
        key, chunk, bkey = batch
        payload = (f"RELATIONSHIP UNDER RE-EXAMINATION: "
                   f"{key[0]} --{key[2]}--> {key[1]}\n\n"
                   + build_payload(chunk))
        try:
            content = muse_chat(INVESTIGATOR_PROMPT, payload, url, model,
                                temperature=temperature)
        except Exception as e:
            return {"kind": "tunnel", "err": str(e)[:120], "bkey": bkey}
        parsed = extract_json_object(content)
        if parsed is None:
            try:
                content = muse_chat(INVESTIGATOR_PROMPT +
                                    "\nYour previous reply was not valid "
                                    "JSON. Output ONLY the JSON object.",
                                    payload, url, model,
                                    temperature=temperature)
                parsed = extract_json_object(content)
            except Exception as e:
                return {"kind": "tunnel", "err": str(e)[:120], "bkey": bkey}
        by_id = {c["candidate_id"]: c for c in chunk}
        passages = {c["candidate_id"]: _norm(_passage_for(c, windows))
                    for c in chunk}
        stage1 = {}
        for cv in (parsed or {}).get("candidate_verdicts") or []:
            if not isinstance(cv, dict):
                continue
            cid = str(cv.get("candidate_id") or "")
            v = str(cv.get("verdict") or "").lower().strip()
            if cid not in by_id or v not in ("overturn", "uphold", "uncertain"):
                continue
            q = re.sub(r"\s+", " ", str(cv.get("quote") or "")).strip()
            if v == "overturn" and (len(q) < 12
                    or _norm(q) not in passages[cid]):
                v = "uncertain"       # unquotable overturn → no appeal
                q = ""
            stage1[cid] = {"verdict": v,
                           "reason": str(cv.get("reason") or "")[:300],
                           "quote": q[:PUBLIC_QUOTE_CHARS]}
        return {"kind": "ok", "bkey": bkey, "stage1": stage1,
                "chunk": [{"candidate_id": c["candidate_id"],
                           "claim": f"{c['from']} --{c['mechanism']}--> {c['to']}",
                           "quote": stage1.get(c["candidate_id"], {}).get("quote", "")}
                          for c in chunk]}

    results = []
    tunnel = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, b): b for b in batches}
        for i, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            results.append(res)
            if res["kind"] == "tunnel":
                tunnel.append(res)
            if i % 20 == 0 or i == len(batches):
                print(f"  stage1 [{i}/{len(batches)}]")

    # ---- stage 2: skeptic double-check on every overturn
    overturns = []
    for res in results:
        if res["kind"] != "ok":
            continue
        for item in res["chunk"]:
            s1 = res["stage1"].get(item["candidate_id"], {})
            if s1.get("verdict") == "overturn":
                overturns.append((item, s1))
    print(f"[appeal] stage1 overturn proposals: {len(overturns)} "
          "→ skeptic double-check")

    def skeptic(item, s1):
        payload = (f"CLAIM: {item['claim']}\n"
                   f"QUOTED SENTENCE: {s1['quote']}")
        try:
            content = muse_chat(SKEPTIC_PROMPT, payload, url, model,
                                temperature=temperature)
        except Exception as e:
            return {"cid": item["candidate_id"], "verdict": "uncertain",
                    "reason": f"skeptic tunnel error: {str(e)[:80]}",
                    "quote": ""}
        parsed = extract_json_object(content)
        if not isinstance(parsed, dict) \
                or str(parsed.get("verdict") or "").lower() not in \
                ("confirm", "deny"):
            return {"cid": item["candidate_id"], "verdict": "uncertain",
                    "reason": "malformed skeptic response", "quote": ""}
        v = parsed["verdict"].lower()
        q = re.sub(r"\s+", " ", str(parsed.get("quote") or "")).strip()
        if v == "confirm" and (len(q) < 12
                               or _norm(q) not in _norm(s1["quote"])):
            v = "deny"   # skeptic could not quote the sentence → deny
        return {"cid": item["candidate_id"], "verdict": v,
                "reason": str(parsed.get("reason") or "")[:300],
                "quote": q[:PUBLIC_QUOTE_CHARS]}

    skeptic_results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(skeptic, item, s1) for item, s1 in overturns]
        for i, fut in enumerate(as_completed(futs), 1):
            skeptic_results.append(fut.result())
            if i % 20 == 0 or i == len(overturns):
                print(f"  stage2 [{i}/{len(overturns)}]")
    skeptic_by_cid = {r["cid"]: r for r in skeptic_results}

    # ---- apply: only double-confirmed overturns become approvals
    n_over = 0
    audit = []
    for res in results:
        if res["kind"] != "ok":
            continue
        for item in res["chunk"]:
            cid = item["candidate_id"]
            s1 = res["stage1"].get(cid, {})
            s2 = skeptic_by_cid.get(cid, {})
            audit.append({
                "candidate_id": cid, "claim": item["claim"],
                "stage1": s1,
                "stage2": s2 or None,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            if s1.get("verdict") == "overturn" \
                    and s2.get("verdict") == "confirm":
                decisions[cid] = {
                    "status": "approved",
                    "reviewer": "muse-appeal",
                    "model": model,
                    "decided": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "note": (
                        f"appeal overturned rejection: {s1.get('reason', '')} "
                        f"| skeptic confirmed: {s2.get('reason', '')} "
                        f"| quote: {s1.get('quote', '')[:120]}"),
                }
                n_over += 1
        append_jsonl(APPEALS_DONE_PATH, [{"batch": res["bkey"],
                                         "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}])
    if audit:
        append_jsonl(APPEALS_PATH, audit)
    if n_over:
        save_decisions(decisions)
    counts = defaultdict(int)
    for a in audit:
        counts[a["stage1"].get("verdict") or "?"] += 1
    print(f"[appeal] stage1: " + " ".join(f"{k}={v}" for k, v in
                                          sorted(counts.items()))
          + f" | double-confirmed overturns applied: {n_over}")
    _llm_track("review_appeal", model, "appeal-v2",
               len(audit),
               notes=f"stage1: {dict(counts)} | overturns: {n_over}")
    if tunnel:
        print(f"[appeal] MUSE TUNNEL ERRORS on {len(tunnel)} batches "
              f"(e.g. {tunnel[0]['err']}) — rerun to resume")
        sys.exit(2)

REVIEWER_PROMPT = """You are a cautious literature reviewer for an avian-influenza gene-relationship database. You are given ONE proposed relationship and its evidence extracts. The quotes have already been verified as verbatim sentences from the named papers — treat them as the complete universe of evidence.

Decide whether this relationship should be PUBLISHED as a mechanistic graph edge.

VERDICTS:
- "approve": the quotes explicitly state this mechanistic relationship with this direction.
- "reject": the evidence is not an explicit mechanism of the claimed type/direction — co-expression, shared pathway membership, phenotype association, background mention, or a different direction/pair than claimed.
- "uncertain": you cannot tell from the supplied evidence alone.

Mechanistic types eligible for edges: activation/induction, inhibition/suppression, physical binding, cleavage/trafficking, viral dependency/support.

ANTI-HALLUCINATION RULES (absolute):
- Base every judgment ONLY on the supplied evidence. Never draw on outside knowledge to approve something the quotes do not state.
- Never invent papers, genes, quotes or mechanisms.
- Every verdict MUST include a "quote" copied VERBATIM from the supplied evidence (copy-paste, do not paraphrase or fix typos). If you cannot find a quotable sentence supporting your verdict, the verdict must be "uncertain" with an empty quote.
- If the evidence is from a review or a general statement rather than an experimental finding, still judge it — but say so in the reason.

Return ONLY JSON:
{"verdict": "approve|reject|uncertain",
 "reason": "one sentence",
 "quote": "verbatim sentence from the evidence, or empty",
 "candidate_verdicts": [{"candidate_id": "...", "verdict": "approve|reject|uncertain", "reason": "one sentence", "quote": "verbatim or empty"}]}
One candidate_verdicts entry per supplied candidate, same order."""


def _review_groups(cands, decisions, only_with_decisions=False):
    """Group pending-or-reviewable candidates by relationship."""
    groups = defaultdict(list)
    for c in cands:
        d = decisions.get(c["candidate_id"])
        if d and d.get("reviewer") == "human":
            continue                     # human decisions are final
        if d and d.get("reviewer") == "muse" and not only_with_decisions:
            continue                     # already auto-reviewed
        groups[(c["from"], c["to"], c["mechanism"])].append(c)
    return groups


def build_review_payload(group):
    papers = papers_meta()
    lines = []
    for i, c in enumerate(group, 1):
        p = papers.get(c["paper_id"], {})
        ctx = c.get("context", {})
        meta = []
        if p.get("year"):
            meta.append(str(p["year"]))
        if p.get("journal"):
            meta.append(p["journal"][:60])
        meta.append(p.get("doi") or c["paper_id"])
        bits = "; ".join(b for b in (
            f"species: {ctx.get('species')}" if ctx.get("species") else "",
            f"evidence_type: {ctx.get('evidence_type')}" if ctx.get("evidence_type") else "",
            f"timepoints: {ctx.get('reported_timepoints')}" if ctx.get("reported_timepoints") else "",
        ) if b)
        lines.append(
            f"[CANDIDATE {i}] id={c['candidate_id']} paper=({', '.join(meta)})"
            + (f" ({bits})" if bits else "")
            + f"\nclaim: {c['from']} --{c['mechanism']}--> {c['to']}\nquote: {c['quote']}")
    return "\n\n".join(lines)


def _verdict_ok(v):
    return v in ("approve", "reject", "uncertain")


def run_review_auto(url, model, workers=8, limit_groups=0, temperature=0.1):
    """First-pass review by muse-glimmer. Records decisions tagged
    reviewer='muse' (human decisions always win; `review reset` can undo).
    Resume-safe; tunnel drop exits 2 without partial writes."""
    cands = load_candidates()
    decisions = load_decisions()
    groups = _review_groups(cands, decisions)
    keys = sorted(groups)
    if limit_groups:
        keys = keys[:limit_groups]
    done = set()
    if AUTO_DONE_PATH.exists():
        for line in AUTO_DONE_PATH.read_text().splitlines():
            try:
                done.add(tuple(json.loads(line)["group"]))
            except Exception:
                pass
    todo = [k for k in keys if k not in done]
    print(f"[review-auto] groups: {len(groups)} done: {len(done & set(groups))} "
          f"todo: {len(todo)}")
    if not todo:
        print("[review-auto] nothing to do")
        return

    def work(key):
        group = groups[key]
        payload = (f"PROPOSED RELATIONSHIP: {key[0]} --{key[2]}--> {key[1]}\n\n"
                   + build_review_payload(group))
        try:
            content = muse_chat(REVIEWER_PROMPT, payload, url, model,
                                temperature=temperature)
        except Exception as e:
            return {"kind": "tunnel", "err": str(e)[:120], "key": key}
        parsed = extract_json_object(content)
        if parsed is None:
            try:
                content = muse_chat(
                    REVIEWER_PROMPT + "\nYour previous reply was not valid "
                    "JSON. Output ONLY the JSON object.", payload, url, model,
                    temperature=temperature)
                parsed = extract_json_object(content)
            except Exception as e:
                return {"kind": "tunnel", "err": str(e)[:120], "key": key}
        if not isinstance(parsed, dict) or not _verdict_ok(parsed.get("verdict")):
            return {"kind": "skip", "key": key,
                    "reason": "malformed reviewer response"}

        # anti-hallucination enforcement: every quoted justification must be a
        # verbatim substring of the supplied evidence pack
        allowed_quotes = _norm(build_review_payload(group))
        by_id = {c["candidate_id"]: c for c in group}
        verdicts = {}
        for cv in parsed.get("candidate_verdicts") or []:
            if not isinstance(cv, dict):
                continue
            cid = str(cv.get("candidate_id") or "")
            v = str(cv.get("verdict") or "").lower().strip()
            if cid not in by_id or not _verdict_ok(v):
                continue
            q = re.sub(r"\s+", " ", str(cv.get("quote") or "")).strip()
            if v in ("approve", "reject") and (len(q) < 12
                    or _norm(q) not in allowed_quotes):
                v = "uncertain"          # unquotable justification → no decision
                q = ""
            verdicts[cid] = {"verdict": v,
                             "reason": str(cv.get("reason") or "")[:300],
                             "quote": q[:PUBLIC_QUOTE_CHARS]}
        # relationship-level fallback for groups whose per-candidate list is
        # missing/incomplete: apply the group verdict only where quotable
        if not verdicts:
            q = re.sub(r"\s+", " ", str(parsed.get("quote") or "")).strip()
            v = parsed["verdict"]
            if v in ("approve", "reject") and (len(q) < 12
                    or _norm(q) not in allowed_quotes):
                v = "uncertain"
                q = ""
            verdicts = {c["candidate_id"]: {"verdict": v,
                                             "reason": str(parsed.get("reason") or "")[:300],
                                             "quote": q[:PUBLIC_QUOTE_CHARS]}
                        for c in group}
        return {"kind": "ok", "key": key, "verdicts": verdicts}

    stats = defaultdict(int)
    tunnel = []
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, k): k for k in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            res = fut.result()
            results.append(res)
            if res["kind"] == "tunnel":
                tunnel.append(res)
            if i % 20 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] "
                      + " ".join(f"{k}={v}" for k, v in
                                  sorted(stats.items())))

    # single-writer application of decisions (main thread)
    n_dec = 0
    for res in results:
        if res["kind"] != "ok":
            continue
        for cid, v in res["verdicts"].items():
            if v["verdict"] == "uncertain":
                stats["uncertain"] += 1
                continue
            decisions[cid] = {
                "status": "approved" if v["verdict"] == "approve"
                else "rejected",
                "reviewer": "muse",
                "model": model,
                "decided": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "note": (v["reason"] +
                         (f" | quote: {v['quote'][:120]}" if v["quote"]
                          else "")).strip(),
            }
            stats[v["verdict"]] += 1
            n_dec += 1
        append_jsonl(AUTO_DONE_PATH,
                     [{"group": list(res["key"]),
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}])
    if n_dec:
        save_decisions(decisions)
    print(f"[review-auto] decisions written: {n_dec} "
          + " ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    _llm_track("review_auto", model, "reviewer-v2",
               n_dec, notes=f"decisions: {dict(stats)}")
    if tunnel:
        print(f"[review-auto] MUSE TUNNEL ERRORS on {len(tunnel)} groups "
              f"(e.g. {tunnel[0]['err']}) — rerun to resume")
        sys.exit(2)


# ---- coverage report (acceptance, D78 item 32) --------------------------

COVERAGE_PATH = OUT_DIR / "coverage_report.md"


def run_coverage():
    """Acceptance artifact: mining-status record + coverage report separating
    hits, no hits, unsafe/unsearchable identifiers, candidate relationships
    and contextual-only findings. INTERNAL (quotes stay out of this file)."""
    st = json.loads(STATUS_PATH.read_text())
    genes = st["genes"]
    verdicts = defaultdict(int)
    verdicts_by_gene = defaultdict(lambda: defaultdict(int))
    for line in VERDICTS_PATH.read_text().splitlines():
        v = json.loads(line)
        verdicts[v["verdict"]] += 1
        verdicts_by_gene[v["gene"]][v["verdict"]] += 1
    cands = load_candidates()
    decisions = load_decisions()
    cand_by_status = defaultdict(int)
    for c in cands:
        cand_by_status[effective_status(c, decisions)] += 1
    rels = defaultdict(set)   # (from,to,mech) → papers
    for c in cands:
        rels[(c["from"], c["to"], c["mechanism"])].add(c["paper_id"])

    hits = [g for g, r in genes.items() if r["status"] == "hit"]
    nohits = [g for g, r in genes.items() if r["status"] == "no_hit"]
    unsafe = [g for g, r in genes.items() if r["status"] == "unsearchable"]
    contextual_only = [g for g in genes
                       if verdicts_by_gene[g].get("mechanistic", 0) == 0
                       and verdicts_by_gene[g].get("contextual", 0) > 0]
    with_candidates = {c["gene"] for c in cands}

    lines = [
        "# Connection-mining coverage report",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} · INTERNAL ONLY",
        "",
        "## Mining status (every registered panel gene)",
        "",
        f"- **hit**: {len(hits)} genes — identifier matched in corpus Markdown",
        f"- **no_hit**: {len(nohits)} genes — searchable identifiers, no corpus "
        "match (never negative evidence)",
        f"- **unsearchable**: {len(unsafe)} genes — "
        "collision-prone/short identifiers recorded, not searched blindly",
        f"- total records: {len(genes)} (deduplicated panel; the original 593 "
        "included one duplicate spelling, IL-18/IL18)",
        "",
        "Unsearchable identifiers: "
        + ", ".join(sorted(g for g in unsafe))
        + "; viral tokens unsearched: "
        + ", ".join(sorted(v["ident"] for v in st.get("viral_unsearchable", [])))
        + ".",
        "",
        "## Window verdicts (Muse pass over all eligible windows)",
        "",
        f"- eligible windows processed: {sum(verdicts.values())} "
        "(every distinct gene-paper window; no top-paper truncation)",
        f"- mechanistic candidates: {verdicts.get('mechanistic', 0)} → "
        f"{len(cands)} grounded candidates "
        f"({dict(cand_by_status)}; pending/rejected never publish)",
        f"- contextual-only findings: {verdicts.get('contextual', 0)} windows "
        f"({len(contextual_only)} genes with contextual but no mechanistic)",
        f"- no_relation: {verdicts.get('no_relation', 0)}",
        f"- quarantined (malformed/ungrounded, never evidence): "
        f"{verdicts.get('quarantined', 0)}",
        "",
        "## Candidate relationships",
        "",
        f"- distinct proposed relationships: {len(rels)}",
        f"- relationships with ≥2 independent papers: "
        f"{sum(1 for p in rels.values() if len(p) >= 2)}",
        f"- genes with ≥1 candidate: {len(with_candidates)}",
        "",
        "| relationship | independent papers |",
        "|---|---|",
    ]
    for (frm, to, mech), papers in sorted(
            rels.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:60]:
        lines.append(f"| {frm} → {to} ({mech}) | {len(papers)} |")
    if len(rels) > 60:
        lines.append(f"| … {len(rels) - 60} more | |")
    lines += [
        "",
        "## Exposure boundary",
        "",
        "Full Markdown, window text and full quotes stay internal "
        "(docs/papers_md, data/papers/connections). Only short reviewed "
        "claims (≤300 chars) and citations are exposed publicly via "
        "gene_relationships.json — and only after approval.",
        "",
        "Generated by `connections.py coverage`.",
    ]
    COVERAGE_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"coverage → {COVERAGE_PATH.relative_to(ROOT)} "
          f"(hit={len(hits)} no_hit={len(nohits)} unsearchable={len(unsafe)} "
          f"candidates={len(cands)} contextual_windows="
          f"{verdicts.get('contextual', 0)})")


def print_status():
    if not STATUS_PATH.exists():
        sys.exit("no search_status.json — run `connections.py search` first")
    s = json.loads(STATUS_PATH.read_text())
    genes = s["genes"]
    print(f"generated {s['generated']}  papers searched: "
          f"{s['papers_searched']}")
    print("counts:", s["counts"])
    print("\nunsearchable genes:")
    for g, rec in genes.items():
        if rec["status"] == "unsearchable":
            why = "; ".join(e["reason"] for e in rec.get("unsafe", [])[:2])
            print(f"  {g:10s} {why[:80]}")
    hit_genes = [g for g, r in genes.items() if r["status"] == "hit"]
    top = sorted(hit_genes, key=lambda g: -genes[g]["n_windows"])[:12]
    print("\ntop genes by windows:")
    for g in top:
        print(f"  {g:10s} {genes[g]['n_windows']:>4} windows / "
              f"{genes[g]['n_papers']:>3} papers")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "classify", "status",
                                    "report", "review", "export", "coverage"])
    ap.add_argument("--gene", help="restrict to one gene (diagnostics)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit-windows", type=int, default=0,
                    help="classify only the first N pending windows")
    ap.add_argument("--status", default="pending",
                    choices=["pending", "approved", "rejected", "all"])
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--note", default=None,
                    help="optional note recorded with a review decision")
    ap.add_argument("--limit-groups", type=int, default=0,
                    help="review auto: only the first N relationship groups")
    ap.add_argument("--temperature", type=float, default=0.1,
                    help="review auto sampling temperature (keep low)")
    args, rest = ap.parse_known_args()

    if args.cmd == "search":
        run_search(only_gene=args.gene)
    elif args.cmd == "classify":
        run_classify(args.url, args.model, args.workers, args.gene,
                     args.limit_windows)
    elif args.cmd == "report":
        run_report()
    elif args.cmd == "export":
        run_export()
    elif args.cmd == "coverage":
        run_coverage()
    elif args.cmd == "review":
        if not rest:
            run_review_stats()
        else:
            action, ids = rest[0], rest[1:]
            if action == "list":
                run_review_list(args.status, args.gene, args.limit)
            elif action in ("approve", "reject", "reset"):
                if not ids:
                    sys.exit(f"review {action}: give one or more candidate ids")
                run_review_decide(ids, action, args.note)
            elif action == "auto":
                run_review_auto(args.url, args.model, args.workers,
                                args.limit_groups, args.temperature)
            elif action == "appeal":
                run_review_appeal(args.url, args.model, args.workers,
                                  args.limit_groups, args.temperature)
            else:
                sys.exit(f"unknown review action {action!r} "
                         "(list|approve|reject|reset|auto|appeal)")
    else:
        print_status()


if __name__ == "__main__":
    main()
