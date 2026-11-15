#!/usr/bin/env python3
"""Corpus preflight (D75) — make every registered paper text-minable.

Guarantees:
  1. Attempt lawful open-access recovery (PMC / EuropePMC / Unpaywall) for
     registered papers lacking a PDF and Markdown.
  2. Convert every locally held PDF to non-empty Markdown WITHOUT overwriting
     good existing extractions (an existing Markdown >= TOO_SHORT_CHARS is
     never touched; a too-short one is only replaced by a LONGER reconvert).
  3. Emit data/papers/corpus_manifest.json with one of four statuses per paper:
       ready              — Markdown >= TOO_SHORT_CHARS
       missing_source     — no lawfully obtainable open-access copy (explicit
                            exclusion record; NEVER negative evidence)
       conversion_failed  — PDF held but Markdown conversion errored/empty
       too_short          — Markdown exists but below the mining threshold

Usage:
  pixi run python scripts/papers/corpus_preflight.py             # full (network)
  pixi run python scripts/papers/corpus_preflight.py --no-network  # local only
  pixi run python scripts/papers/corpus_preflight.py --check     # verify vs manifest
  pixi run python scripts/papers/corpus_preflight.py --paper ID  # single paper
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
PDF_DIR = ROOT / "docs" / "papers_pdfs"
MD_DIR = ROOT / "docs" / "papers_md"
MANIFEST = ROOT / "data" / "papers" / "corpus_manifest.json"

TOO_SHORT_CHARS = 2000
MIN_PDF_BYTES = 10_000

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ---------------------------------------------------------------- helpers


def load_papers():
    return json.loads(PAPERS_JSON.read_text())["papers"]


def md_path(pid):
    return MD_DIR / f"{pid}.md"


def pdf_path(pid):
    return PDF_DIR / f"{pid}.pdf"


def md_len(pid):
    p = md_path(pid)
    return len(p.read_text(errors="replace").strip()) if p.exists() else 0


JUNK_MARKERS = (
    "JavaScript is disabled in your browser",
    "Please enable JavaScript",
    "Are you a robot",
    "Access Denied",
    "Request unsuccessful. Incapsula",
)


def convert_pdf_to_md(pid):
    """PDF → Markdown via pymupdf4llm. Returns (text|None, junk|bool);
    junk=True means the PDF is a bot-block page, not the paper."""
    import pymupdf4llm
    try:
        text = pymupdf4llm.to_markdown(str(pdf_path(pid)))
    except Exception:
        return None, False
    text = (text or "").strip() or None
    if text and any(m in text[:800] for m in JUNK_MARKERS):
        return None, True
    return text, False


# ---------------------------------------------------------------- recovery

PMC_URL_RE = re.compile(r"PMC(\d+)", re.IGNORECASE)
PMID_URL_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/", re.IGNORECASE)


def _client():
    return httpx.Client(follow_redirects=True, timeout=60,
                        headers={"User-Agent": UA})


# ---- JATS (PMC article XML) → Markdown -------------------------------

def _el_text(el):
    """All descendant text of an element, whitespace-normalised."""
    parts = [t for t in el.itertext() if t and t.strip()]
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _walk_container(el, out, depth=0):
    """Recursively render <p>, lists, figures, tables into markdown lines."""
    import xml.etree.ElementTree as ET
    tag = el.tag.split("}")[-1]
    if tag == "p":
        txt = _el_text(el)
        if txt:
            out.append(txt)
            out.append("")
        return
    if tag == "title":
        return  # handled by parent section
    if tag in ("fig", "table-wrap"):
        cap = el.find(".//caption")
        label = el.find(".//label")
        txt = _el_text(cap if cap is not None else el)
        if txt:
            prefix = _el_text(label) if label is not None else ("Figure" if tag == "fig" else "Table")
            out.append(f"*{prefix}: {txt}*")
            out.append("")
        return
    if tag in ("list", "def-list"):
        for li in el:
            litag = li.tag.split("}")[-1]
            if litag in ("list-item", "def-item"):
                body_txt = []
                for sub in li:
                    subtag = sub.tag.split("}")[-1]
                    if subtag in ("p",):
                        t = _el_text(sub)
                        if t:
                            body_txt.append(t)
                    elif subtag in ("term", "def"):
                        t = _el_text(sub)
                        if t:
                            body_txt.append(t)
                if body_txt:
                    out.append("- " + " ".join(body_txt))
        out.append("")
        return
    if tag == "ref":
        return  # reference lists are noise for mining
    for child in el:
        if isinstance(child.tag, str):
            _walk_container(child, out, depth + 1)


def jats_to_markdown(xml_text):
    """EuropePMC fullTextXML (JATS) → plain Markdown for text mining."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    out = []
    title = root.find(".//article-title")
    if title is not None and _el_text(title):
        out.append("# " + _el_text(title))
        out.append("")
    abstract = root.find(".//abstract")
    if abstract is not None:
        out.append("## Abstract")
        out.append("")
        _walk_container(abstract, out)
    body = root.find(".//body")
    if body is None:
        text = "\n".join(out).strip()
        return text or None

    def walk_section(sec, depth=2):
        t = sec.find("title")
        if t is not None and _el_text(t):
            out.append("#" * min(depth, 6) + " " + _el_text(t))
            out.append("")
        for child in sec:
            ctag = child.tag.split("}")[-1]
            if ctag == "sec":
                walk_section(child, depth + 1)
            elif isinstance(child.tag, str) and ctag != "title":
                _walk_container(child, out)

    for child in body:
        ctag = child.tag.split("}")[-1]
        if ctag == "sec":
            walk_section(child)
        elif isinstance(child.tag, str):
            _walk_container(child, out)
    text = "\n".join(out).strip()
    return text or None


def fetch_pmc_pdf(client, pmcid, out):
    """Download the PDF for a PMC article (open-access subset only).
    NOTE: pmc.ncbi.nlm.nih.gov now gates /pdf/ behind a proof-of-work
    challenge, so this route mostly fails; kept for already-issued links."""
    page_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/"
    try:
        html = client.get(page_url).text
    except Exception:
        return False
    href = None
    for pat in (r'href="(pdf/[^"]+\.pdf)"',
                r'href="(https://cdn\.ncbi[^"]+\.pdf)"',
                r'href="(/articles/PMC\d+/pdf/[^"]+)"'):
        m = re.search(pat, html)
        if m:
            href = m.group(1)
            if href.startswith("/"):
                href = "https://pmc.ncbi.nlm.nih.gov" + href
            elif not href.startswith("http"):
                href = page_url.rstrip("/") + "/" + href
            break
    if not href:
        return False
    try:
        r = client.get(href)
        if r.status_code == 200 and r.content[:4] == b"%PDF" \
                and len(r.content) >= MIN_PDF_BYTES:
            out.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


def fetch_epmc_xml_md(client, pmcid):
    """EuropePMC fullTextXML (lawful OA channel) → Markdown text or None."""
    try:
        r = client.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/"
                       f"PMC{pmcid}/fullTextXML")
        if r.status_code == 200 and "<body" in r.text:
            return jats_to_markdown(r.text)
    except Exception:
        pass
    return None


def idconv(client, ident):
    """DOI or PMID → PMCID via NCBI ID converter."""
    try:
        r = client.get("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/",
                       params={"ids": ident, "format": "json", "tool": "roost"})
        records = r.json().get("records", [])
        if records and records[0].get("pmcid"):
            return re.sub(r"^\D+", "", records[0]["pmcid"])
    except Exception:
        pass
    return None


def europepmc_oa(client, doi):
    """EuropePMC → (pmcid|None, oa_pdf_url|None) for a DOI."""
    try:
        r = client.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": f'DOI:"{doi}"', "format": "json",
                    "resultType": "core", "pageSize": "1"})
        results = r.json().get("resultList", {}).get("result", [])
        if not results:
            return None, None
        res = results[0]
        pmcid = re.sub(r"^\D+", "", res["pmcid"]) if res.get("pmcid") else None
        pdf_url = None
        if res.get("isOpenAccess") == "Y" or res.get("inPMC") == "Y":
            for link in res.get("fullTextUrlList", {}).get(
                    "fullTextUrl", []):
                if link.get("availability") in ("Open access", "Free") and \
                        (link.get("documentStyle") == "pdf" or
                         ".pdf" in link.get("url", "")):
                    pdf_url = link["url"]
                    break
        return pmcid, pdf_url
    except Exception:
        return None, None


def unpaywall_oa(client, doi):
    """Unpaywall → best OA PDF URL (needs ROOST_UNPAYWALL_EMAIL)."""
    import os
    email = os.environ.get("ROOST_UNPAYWALL_EMAIL")
    if not email:
        return None
    try:
        r = client.get(f"https://api.unpaywall.org/v2/{doi}",
                       params={"email": email})
        if r.status_code != 200:
            return None
        loc = r.json().get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url")
    except Exception:
        return None


def recover(client, paper):
    """Try every lawful OA route for one paper.
    Returns (via-tag, md_text_or_None). md_text set when recovered as
    full-text XML (no PDF involved)."""
    pid, doi, url = paper["id"], paper.get("doi"), paper.get("url") or ""

    def pmcid_md(pmcid):
        md = fetch_epmc_xml_md(client, pmcid)
        if md:
            return md, False
        # XML unavailable → try the legacy PDF route too
        if fetch_pmc_pdf(client, pmcid, pdf_path(pid)):
            return convert_pdf_to_md(pid)
        return None, False

    # 1. explicit PMC URL on the record
    m = PMC_URL_RE.search(url)
    if m:
        md, _ = pmcid_md(m.group(1))
        if md:
            return "epmc_xml_pmc_url", md
        time.sleep(0.4)
    # 2. PubMed URL → PMID → idconv → PMC
    m = PMID_URL_RE.search(url)
    if m:
        pmcid = idconv(client, m.group(1))
        if pmcid:
            md, _ = pmcid_md(pmcid)
            if md:
                return "epmc_xml_pubmed_idconv", md
        time.sleep(0.4)
    # 3. DOI → EuropePMC (direct XML or OA PDF)
    if doi:
        pmcid, pdf_url = europepmc_oa(client, doi)
        if pmcid:
            md, _ = pmcid_md(pmcid)
            if md:
                return "epmc_xml_doi", md
            time.sleep(0.4)
        if pdf_url:
            try:
                r = client.get(pdf_url)
                if r.status_code == 200 and r.content[:4] == b"%PDF" \
                        and len(r.content) >= MIN_PDF_BYTES:
                    pdf_path(pid).write_bytes(r.content)
                    return "europepmc_pdf", convert_pdf_to_md(pid)[0]
            except Exception:
                pass
        time.sleep(0.4)
        # 4. DOI → Unpaywall (optional; needs ROOST_UNPAYWALL_EMAIL)
        upw = unpaywall_oa(client, doi)
        if upw:
            try:
                r = client.get(upw)
                if r.status_code == 200 and r.content[:4] == b"%PDF" \
                        and len(r.content) >= MIN_PDF_BYTES:
                    pdf_path(pid).write_bytes(r.content)
                    return "unpaywall", convert_pdf_to_md(pid)[0]
            except Exception:
                pass
    return None, None


# ---------------------------------------------------------------- statuses


def classify(pid, allow_reconvert):
    """Compute status for one paper; may write/replace Markdown.

    Returns (status, info-dict). An existing good extraction is never
    overwritten: we only convert when Markdown is absent or too short,
    and only replace a too-short one with a LONGER fresh conversion.
    Junk PDFs (bot-block pages) are removed and reported missing_source.
    """
    info = {"paper_id": pid}
    n = md_len(pid)
    has_pdf = pdf_path(pid).exists()

    if n >= TOO_SHORT_CHARS:
        return "ready", info

    if has_pdf and allow_reconvert:
        fresh, junk = convert_pdf_to_md(pid)
        if junk:
            # bot-block capture, not a real source — remove the junk pdf and
            # any junk-derived markdown; record explicit exclusion
            pdf_path(pid).unlink(missing_ok=True)
            md_path(pid).unlink(missing_ok=True)
            info["reason"] = "held pdf is a bot-block page, not the paper"
            info["removed_junk_pdf"] = True
            return "missing_source", info
        if fresh is not None and len(fresh) > max(n, TOO_SHORT_CHARS):
            md_path(pid).write_text(fresh, encoding="utf-8")
            info["reconverted"] = True
            return "ready", info
        if fresh is not None:
            # fresh conversion no better — keep whichever is longer
            if len(fresh) > n:
                md_path(pid).write_text(fresh, encoding="utf-8")
            return ("too_short" if max(n, len(fresh)) > 0
                    else "conversion_failed"), info
        if n == 0:
            info["reason"] = "pdf→md conversion failed or empty"
            return "conversion_failed", info
        return "too_short", info

    if n > 0:
        return "too_short", info
    return "missing_source", info


def run(network=True, only=None, recover_missing=True):
    papers = load_papers()
    if only:
        papers = [p for p in papers if p["id"] == only]
        if not papers:
            sys.exit(f"no such paper: {only}")

    MD_DIR.mkdir(exist_ok=True)
    entries = {}

    # provenance from a previous manifest survives reruns (D75): a
    # missing_source reason recorded once must not vanish on a local pass
    prior = {}
    if MANIFEST.exists():
        try:
            for r in json.loads(MANIFEST.read_text())["papers"]:
                prior[r["paper_id"]] = r
        except Exception:
            pass

    # ---- pass 1: classify from local state (no writes for good mds)
    need_recovery = []
    for p in papers:
        pid = p["id"]
        status, info = classify(pid, allow_reconvert=True)
        if status == "missing_source" and network and recover_missing:
            need_recovery.append(p)          # decided after local pass
        else:
            if status == "missing_source" and "reason" not in info:
                info["reason"] = "no local pdf or markdown"
            if status == "conversion_failed" and "reason" not in info:
                info["reason"] = "pdf→md conversion failed or empty"
            prev = prior.get(pid) or {}
            if prev.get("status") == status:
                for k in ("reason", "recovered_via", "removed_junk_pdf"):
                    if prev.get(k) is not None and k not in info:
                        info[k] = prev[k]
        entries[pid] = (status, info)

    # ---- pass 2: lawful OA recovery for the missing
    if need_recovery:
        print(f"[preflight] attempting OA recovery for {len(need_recovery)} papers")
        with _client() as client:
            for p in need_recovery:
                pid = p["id"]
                via, md = recover(client, p)
                time.sleep(0.6)
                if via:
                    if md and len(md) >= TOO_SHORT_CHARS:
                        md_path(pid).write_text(md, encoding="utf-8")
                        entries[pid] = ("ready", {"paper_id": pid,
                                                  "recovered_via": via})
                        print(f"  recovered {pid} via {via} "
                              f"({len(md):,} chars)")
                        continue
                    if md:
                        md_path(pid).write_text(md, encoding="utf-8")
                        entries[pid] = ("too_short", {"paper_id": pid,
                                                      "recovered_via": via})
                        print(f"  recovered {pid} via {via} but too short")
                        continue
                    pdf_path(pid).unlink(missing_ok=True)
                    entries[pid] = ("conversion_failed",
                                    {"paper_id": pid, "recovered_via": via,
                                     "reason": "recovered pdf failed to "
                                               "convert"})
                    print(f"  {pid}: recovered pdf failed conversion")
                    continue
                entries[pid] = ("missing_source",
                                {"paper_id": pid,
                                 "reason": missing_reason(p)})
                print(f"  no OA copy: {pid} ({entries[pid][1]['reason']})")

    # ---- merge provenance for statuses unchanged from prior manifest
    for pid, (status, info) in entries.items():
        prev = prior.get(pid) or {}
        if prev.get("status") == status:
            for k in ("reason", "recovered_via", "removed_junk_pdf"):
                if prev.get(k) is not None and k not in info:
                    info[k] = prev[k]

    manifest = build_manifest(entries)
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    report(manifest)
    return manifest


def missing_reason(p):
    if not p.get("doi") and not p.get("url"):
        return "no doi or url on record"
    url = p.get("url") or ""
    if PMC_URL_RE.search(url):
        return ("in PMC but full text not served via EuropePMC and "
                "PDF download is challenge-gated")
    if p.get("doi"):
        return "no open-access copy found via PMC/EuropePMC/Unpaywall"
    if url.startswith("http"):
        return "url is not an open-access pdf source (html/news/report page)"
    return "no open-access copy found"


def build_manifest(entries):
    counts = {"ready": 0, "missing_source": 0,
              "conversion_failed": 0, "too_short": 0}
    rows = []
    for pid in sorted(entries):
        status, info = entries[pid]
        counts[status] += 1
        info = dict(info)
        info["status"] = status
        info["md"] = md_path(pid).exists()
        info["md_chars"] = md_len(pid)
        info["pdf"] = pdf_path(pid).exists()
        rows.append(info)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "thresholds": {"too_short_chars": TOO_SHORT_CHARS},
        "counts": counts,
        "papers": rows,
    }


def report(m):
    c = m["counts"]
    total = sum(c.values())
    print(f"\n[preflight] manifest → {MANIFEST.relative_to(ROOT)}")
    print(f"  ready              {c['ready']:>4}")
    print(f"  missing_source     {c['missing_source']:>4}")
    print(f"  conversion_failed  {c['conversion_failed']:>4}")
    print(f"  too_short          {c['too_short']:>4}")
    print(f"  total              {total:>4}")


# ---------------------------------------------------------------- --check


def check():
    """Validate the manifest against current files. Exit 1 on drift.
    Usable by CI/tests without network."""
    if not MANIFEST.exists():
        sys.exit("corpus_preflight: no manifest — run corpus_preflight.py first")
    m = json.loads(MANIFEST.read_text())
    papers = {p["id"] for p in load_papers()}
    manifest_ids = {r["paper_id"] for r in m["papers"]}
    problems = []
    if papers - manifest_ids:
        problems.append(f"papers missing from manifest: "
                        f"{sorted(papers - manifest_ids)[:5]}")
    if manifest_ids - papers:
        problems.append(f"manifest rows for unregistered papers: "
                        f"{sorted(manifest_ids - papers)[:5]}")
    for r in m["papers"]:
        pid = r["paper_id"]
        n = md_len(pid)
        if r["status"] == "ready" and n < TOO_SHORT_CHARS:
            problems.append(f"{pid}: ready but md is {n} chars")
        if r["status"] == "too_short" and n >= TOO_SHORT_CHARS:
            problems.append(f"{pid}: too_short but md has {n} chars")
        if r["status"] == "missing_source" and n >= TOO_SHORT_CHARS:
            problems.append(f"{pid}: missing_source but md exists ({n} chars)")
        if r["status"] in ("ready", "too_short") and n == 0:
            problems.append(f"{pid}: {r['status']} but no markdown file")
    if problems:
        print("corpus_preflight --check FAILED:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"corpus_preflight --check OK "
          f"({len(m['papers'])} papers, {m['counts']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-network", action="store_true",
                    help="local pass only: convert held PDFs, no recovery")
    ap.add_argument("--check", action="store_true",
                    help="verify manifest matches disk; no network, no writes")
    ap.add_argument("--paper", help="single paper id")
    args = ap.parse_args()
    if args.check:
        check()
    else:
        run(network=not args.no_network, only=args.paper)


if __name__ == "__main__":
    main()
