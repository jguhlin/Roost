#!/usr/bin/env python3
"""Paper database — turn the paper corpus into a queryable trait-mining base.

One ripgrep pass over docs/papers_md (1,083 papers, ~67 MB) matches the whole
gene panel (811 catalogue symbols + curated protein-name aliases, e.g.
RIG-I→DDX58) and stores, per paper:

  genes           canonical symbols mentioned (list)
  gene_hits       JSON {gene: {n, snippets[]}} — ±300-char windows around
                  matches, capped, ready for LLM processing WITHOUT feeding
                  in the whole paper
  strains         JSON {value: {n, snippet}} — clades (2.3.4.4b…) and
                  subtypes (H5N1…) for detection-strain evaluation
  authors         split into a list
  paper_type      scientific_published | scientific_preprint | thesis |
                  media | government | other (deterministic heuristics)
  language_guess  en | latin-non-en | cjk | unknown (script/stopword heuristic)
  species         from the existing LLM analyses where available

Outputs (internal): data/papers/paper_db.parquet + paper_db_meta.json
Exclusions documented in meta: ≤2-char FP-prone symbols (C, II, HA, NA, NP…)
are not grepped — see meta.no_grep_symbols.

Run:  pixi run python scripts/papers/build_paper_db.py [--rg PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
MD_DIR = ROOT / "docs" / "papers_md"
INDEX = ROOT / "data" / "papers" / "papers_index.parquet"
CATALOGUE = ROOT / "web" / "public" / "data" / "gene_catalogue.json"
ANALYSES = ROOT / "data" / "papers" / "analyses"
OUT = ROOT / "data" / "papers" / "paper_db.parquet"
OUT_META = ROOT / "data" / "papers" / "paper_db_meta.json"

SNIPPETS_PER_GENE = None      # UNCAPPED — every matched paragraph is kept
SNIPPET_CHARS = 4000          # guard only for pathological lines (tables);
                              # normal prose paragraphs pass through whole
SNIPPETS_PER_STRAIN = 2

# curated protein-name aliases for the key immune genes (symbol variants
# plus the names papers actually use); catalogue aliases are merged on top
CURATED_ALIASES = {
    "DDX58": ["RIG-I", "RIG‐I", "RIG‑I", "RIG‑1", "RIG like", "retinoic acid-inducible gene I"],
    "IFIH1": ["MDA5", "melanoma differentiation-associated protein 5"],
    "DHX58": ["LGP2", "LGP-2"],
    "MAVS": ["IPS-1", "Cardif", "VISA", "mitochondrial antiviral signaling"],
    "EIF2AK2": ["PKR", "protein kinase R"],
    "OAS1": ["2-5A synthetase", "OAS-1"],
    "OASL": ["OAS-like", "OASL1"],
    "RNASEL": ["RNase L", "RNase-L"],
    "MB21D1": ["cGAS", "cGAS–STING"],
    "TMEM173": ["STING", "MITA", "ERIS"],
    "TLR3": ["Toll-like receptor 3"],
    "TLR7": ["Toll-like receptor 7"],
    "TLR8": ["Toll-like receptor 8"],
    "TLR9": ["Toll-like receptor 9"],
    "IRF3": ["interferon regulatory factor 3"],
    "IRF7": ["interferon regulatory factor 7"],
    "STAT1": ["signal transducer and activator of transcription 1"],
    "IFITM1": ["IFITM"],
    "IFITM3": ["IFITM"],
    "MX1": ["MxA", "Mx1", "Myxovirus resistance"],
    "IFNA": ["type I interferon", "IFN-α", "IFN-alpha"],
    "IFNB": ["IFN-β", "IFN-beta", "interferon-beta"],
    "ANP32A": ["pp32", "LANP", "acidic leucine-rich nuclear phosphoprotein 32A"],
    "ANP32B": ["APRIL", "PHAPII"],
    "CDKN1A": ["p21"],
    "TP53": ["p53"],
    "NLRX1": ["NLRX-1"],
    "ZBP1": ["DAI", "DLM-1"],
    "CASP1": ["caspase-1", "ICE"],
    "IL1B": ["IL-1β", "IL-1beta", "interleukin-1beta", "interleukin-1 beta"],
    "IL6": ["IL-6", "interleukin-6"],
    "TNF": ["TNF-α", "TNF-alpha", "tumor necrosis factor-alpha"],
}

# symbols too short/ambiguous to grep without drowning in false positives
NO_GREP = {"C", "II", "HA", "NA", "NP", "PA", "M1", "NS", "BF", "BG", "M2"}

# Title-case variants that collide with English/product usage (e.g. QIAamp
# "Mini Kit") — mouse-style capitalize() is otherwise legitimate (Kit the
# mouse gene loses some recall; acceptable vs hundreds of kit-product hits)
EXCLUDE_TITLE = {"Kit", "Jun", "Max", "Cat", "Bad", "Bid", "Sea", "Era", "Tan"}

STRAIN_PATTERNS = [
    re.compile(r"\b2\.3\.\d+\.\d+[a-z]?\b"),        # clades incl. 2.3.4.4b
    re.compile(r"\b[Hh]\d[Nn]\d\b"),                 # subtypes H5N1, h7n9 …
    re.compile(r"\b(HPAI|LPAI|H5Nx|H5Nx)\b"),
]


def normalize(s: str) -> str:
    return unicodedata.normalize("NFKD", s).replace("‐", "-").replace("‑", "-")


def build_pattern_map():
    gc = json.loads(CATALOGUE.read_text())["gene_catalogue"]
    variant_to_canon: dict[str, str] = {}
    patterns: list[str] = []
    no_grep = sorted(NO_GREP & set(gc))
    for sym, meta in gc.items():
        variants = {sym} - (NO_GREP if sym in NO_GREP else set())
        if sym not in NO_GREP and sym.isupper() and len(sym) > 2 \
                and sym.capitalize() not in EXCLUDE_TITLE:
            variants.add(sym.capitalize())      # mouse/rat style Ddx58, Ifih1
        for a in list(meta.get("aliases", [])) + CURATED_ALIASES.get(sym, []):
            a = normalize(a).strip()
            if a and len(a) >= 3:
                variants.add(a)
        for v in variants:
            v = re.escape(normalize(v))
            patterns.append(v)
            variant_to_canon[normalize(v).lower()] = sym
    return patterns, variant_to_canon, no_grep


def paper_type(row) -> str:
    j = (row.get("journal") or "").lower()
    u = (row.get("url") or "").lower()
    t = (row.get("title") or "").lower()
    src = row.get("source_type") or ""
    if any(k in j or k in u for k in
           ["biorxiv", "medrxiv", "arxiv", "preprint", "researchsquare",
            "ssrn", "chemrxiv", "preprints.org"]):
        return "scientific_preprint"
    if any(k in t or k in j or k in u for k in
           ["dissertation", "thesis", "proquest"]):
        return "thesis"
    if any(k in u or k in j for k in
           ["usda", "aphis", "defra", "fao.org", "who.int", "woah", "oie.int",
            "efsa", "ecdc", "gov.", "gov/", "ministry", "department of ",
            "government"]) and src not in ("cdc_eid",):
        return "government"
    if any(k in u or k in j for k in
           ["reuters", "bbc", "news", "guardian", "nytimes", "cidrap",
            "statnews", "outbreak newstoday", "promed", "magazine"]):
        return "media"
    if row.get("doi") or (row.get("journal") and len(row["journal"]) > 3):
        return "scientific_published"
    return "other"


def language_guess(text: str) -> str:
    sample = text[:4000]
    if not sample.strip():
        return "unknown"
    cjk = sum(1 for c in sample if "\u4e00" <= c <= "\u9fff" or
              "\u3040" <= c <= "\u30ff" or "\uac00" <= c <= "\ud7af")
    if cjk > len(sample) * 0.2:
        return "cjk"
    latin = sum(1 for c in sample if c.isalpha())
    if latin < len(sample) * 0.3:
        return "unknown"
    en_markers = sum(sample.lower().count(w) for w in
                     (" the ", " and ", " of ", " in ", " with ", " were "))
    return "en" if en_markers >= 4 else "latin-non-en"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rg", default=shutil.which("rg") or "rg")
    args = ap.parse_args()

    patterns, v2c, no_grep = build_pattern_map()
    print(f"patterns: {len(patterns)} variants → {len(set(v2c.values()))} genes; "
          f"not grepped: {no_grep}", file=sys.stderr)

    # ---- one ripgrep pass over the whole corpus ----
    pat = "\\b(?:" + "|".join(patterns) + ")\\b"
    combined = re.compile(pat)
    r = subprocess.run(
        [args.rg, "--vimgrep", "--case-sensitive", "--no-messages",
         "-e", pat, str(MD_DIR)],
        capture_output=True, text=True, timeout=1800)
    hits: dict[str, dict[str, dict]] = {}   # file -> gene -> {n, lines:set()}
    v2c_norm = {normalize(k).lower(): v for k, v in v2c.items()}
    for line in r.stdout.splitlines():
        try:
            fname, lineno, _col, text = line.split(":", 3)
            lineno = int(lineno)
        except ValueError:
            continue
        for m in combined.findall(normalize(text)):
            canon = v2c_norm.get(m.lower())
            if not canon:
                continue
            d = hits.setdefault(fname, {}).setdefault(canon, {"n": 0, "lines": set()})
            d["n"] += 1
            d["lines"].add((lineno, text.strip()))

    print(f"papers with gene hits: {len(hits)}", file=sys.stderr)

    # ---- strain pass (separate, cheap) ----
    strain_hits: dict[str, dict[str, dict]] = {}
    for f in sorted(MD_DIR.glob("*.md")):
        try:
            text = normalize(f.read_text(errors="replace"))
        except Exception:
            continue
        found: dict[str, dict] = {}
        for pat_re in STRAIN_PATTERNS:
            for m in pat_re.finditer(text):
                val = m.group(0).upper()
                d = found.setdefault(val, {"n": 0, "snippet": ""})
                d["n"] += 1
                if not d["snippet"]:
                    s = max(0, m.start() - 140)
                    d["snippet"] = re.sub(r"\s+", " ", text[s:m.end() + 140]).strip()
        if found:
            strain_hits[f.stem] = dict(sorted(found.items(),
                                              key=lambda kv: -kv[1]["n"])[:20])

    # ---- assemble ----
    idx = pl.read_parquet(INDEX)
    idx_by = {r["id"]: r for r in idx.iter_rows(named=True)}
    rows = []
    for f in sorted(MD_DIR.glob("*.md")):
        pid = f.stem
        row = idx_by.get(pid, {})
        text = ""
        try:
            text = f.read_text(errors="replace")
        except Exception:
            pass
        gh = hits.get(str(f), {})
        gene_hits = {}
        for gene, d in gh.items():
            snippets = []
            for lineno, ltext in sorted(d["lines"]):   # every match, uncapped
                snippets.append(re.sub(r"\s+", " ", ltext)[:SNIPPET_CHARS])
            gene_hits[gene] = {"n": d["n"], "snippets": snippets}
        # analyses species
        species = []
        an = ANALYSES / f"{pid}.json"
        if an.exists():
            try:
                a = json.loads(an.read_text())
                species = sorted({s.get("scientific_name") or s.get("name", "")
                                  for s in a.get("species_detections", [])
                                  if s.get("scientific_name") or s.get("name")})
            except Exception:
                pass
        authors_raw = row.get("authors") or ""
        authors = [a.strip().rstrip(",") for a in re.split(r",|\band\b", authors_raw)
                   if a.strip() and a.strip().lower() != "et al."]
        rows.append({
            "id": pid,
            "title": row.get("title") or "",
            "authors": authors,
            "journal": row.get("journal") or "",
            "year": row.get("year"),
            "doi": row.get("doi"),
            "url": row.get("url") or "",
            "paper_type": paper_type(row),
            "category": row.get("category") or "",
            "topics": row.get("topics") or "",
            "summary": row.get("summary") or "",
            "language_guess": language_guess(text),
            "n_genes": len(gene_hits),
            "genes": sorted(gene_hits),
            "gene_hits": json.dumps(gene_hits),
            "strains": json.dumps(strain_hits.get(pid, {})),
            "species": species,
            "analysis_available": an.exists(),
            "chars": len(text),
        })

    df = pl.DataFrame(rows)
    df.write_parquet(OUT)
    OUT_META.write_text(json.dumps({
        "generated": datetime.fromtimestamp(
            __import__("time").time(), tz=timezone.utc).isoformat(timespec="seconds"),
        "n_papers": df.height,
        "papers_with_genes": df.filter(pl.col("n_genes") > 0).height,
        "papers_with_strains": df.filter(pl.col("strains") != "{}").height,
        "no_grep_symbols": no_grep,
        "paper_type_counts": {t: c for t, c in df["paper_type"].value_counts()
                              .rows()},
        "language_counts": {t: c for t, c in df["language_guess"].value_counts()
                            .rows()},
        "snippets_per_gene": "UNCAPPED (every matched paragraph kept; "
                            "individual lines truncated only at 4000 chars "
                            "for table dumps)",
        "note": "gene_hits/strains are JSON columns; snippets are the FULL "
                "matched paragraph lines (uncapped; truncated only at 4000 "
                "chars for table dumps) for LLM processing",
    }, indent=2, default=str))
    print(f"wrote {OUT.name}: {df.height} papers", file=sys.stderr)
    print(f"  with genes: {df.filter(pl.col('n_genes') > 0).height} | "
          f"with strains: {df.filter(pl.col('strains') != '{}').height}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
