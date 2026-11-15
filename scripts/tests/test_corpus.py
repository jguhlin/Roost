"""Corpus preflight tests (D75 acceptance).

Plan requirements:
  - valid Markdown for every locally held PDF
  - an explicit exclusion record for every unavailable registered source
  - good existing extractions are never overwritten
"""

import json
import subprocess
import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent.parent


def load_papers():
    return json.loads(
        (ROOT / "web" / "public" / "data" / "papers.json").read_text())["papers"]


def load_manifest():
    return json.loads(
        (ROOT / "data" / "papers" / "corpus_manifest.json").read_text())


VALID = {"ready", "missing_source", "conversion_failed", "too_short"}


def test_manifest_exists_and_covers_every_registered_paper():
    m = load_manifest()
    papers = load_papers()
    rows = {r["paper_id"]: r for r in m["papers"]}
    assert len(rows) == len(papers), (
        f"manifest has {len(rows)} rows for {len(papers)} registered papers")
    for p in papers:
        assert p["id"] in rows
        assert rows[p["id"]]["status"] in VALID


def test_every_locally_held_pdf_has_valid_markdown():
    """Every PDF held for a registered paper must have non-empty Markdown."""
    pdfs = list((ROOT / "docs" / "papers_pdfs").glob("*.pdf"))
    ids = {p["id"] for p in load_papers()}
    md_dir = ROOT / "docs" / "papers_md"
    checked = 0
    for pdf in pdfs:
        if pdf.stem not in ids:
            continue  # unregistered stray — out of scope here
        md = md_dir / f"{pdf.stem}.md"
        assert md.exists(), f"{pdf.stem}: PDF held but no Markdown extracted"
        text = md.read_text(errors="replace").strip()
        assert len(text) > 0, f"{pdf.stem}: Markdown extraction is empty"
        checked += 1
    assert checked > 600, "expected the full corpus of held PDFs to be checked"


def test_explicit_exclusion_record_for_unavailable_sources():
    """Every non-ready registered paper must carry an explicit reason/state."""
    m = load_manifest()
    ids = {p["id"] for p in load_papers()}
    non_ready = [r for r in m["papers"] if r["status"] != "ready"]
    assert non_ready, "expected at least some unavailable sources"
    for r in non_ready:
        assert r["paper_id"] in ids
        # missing_source and conversion_failed need a human-readable reason
        if r["status"] in ("missing_source", "conversion_failed"):
            assert r.get("reason"), f"{r['paper_id']}: no exclusion reason"


def test_statuses_match_disk_state():
    m = load_manifest()
    md_dir = ROOT / "docs" / "papers_md"
    thr = m["thresholds"]["too_short_chars"]
    for r in m["papers"]:
        md = md_dir / f"{r['paper_id']}.md"
        n = len(md.read_text(errors="replace").strip()) if md.exists() else 0
        if r["status"] == "ready":
            assert n >= thr, f"{r['paper_id']}: ready but {n} chars"
        elif r["status"] == "too_short":
            assert 0 < n < thr, f"{r['paper_id']}: too_short but {n} chars"
        elif r["status"] == "missing_source":
            assert n == 0 or r.get("removed_junk_pdf"), (
                f"{r['paper_id']}: missing_source but md has {n} chars")


def test_check_mode_passes_from_clean_shell():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "papers" / "corpus_preflight.py"),
         "--check"],
        cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------------------- unit level


def test_jats_to_markdown_extracts_body(preflight):
    xml = """<?xml version="1.0"?>
    <article><front><article-meta>
      <article-title>A study of DDX58 in ducks</article-title>
      <abstract><p>RIG-I senses influenza.</p></abstract>
    </article-meta></front>
    <body><sec><title>Results</title>
      <p>DDX58 knockdown increased viral titers.</p>
      <fig><label>Figure 1</label><caption>Viral titers rose.</caption></fig>
    </sec></body></article>"""
    md = preflight.jats_to_markdown(xml)
    assert md is not None
    assert "# A study of DDX58 in ducks" in md
    assert "## Abstract" in md
    assert "RIG-I senses influenza." in md
    assert "## Results" in md
    assert "DDX58 knockdown increased viral titers." in md
    assert "*Figure 1: Viral titers rose.*" in md


def test_jats_to_markdown_front_matter_only(preflight):
    xml = ('<?xml version="1.0"?><article><front>'
           '<article-title>Front only</article-title></front></article>')
    md = preflight.jats_to_markdown(xml)
    assert md and "Front only" in md and len(md) < 100


def test_classify_never_overwrites_good_extraction(preflight, tmp_path,
                                                   monkeypatch):
    md_dir = tmp_path / "md"
    pdf_dir = tmp_path / "pdf"
    md_dir.mkdir()
    pdf_dir.mkdir()
    monkeypatch.setattr(preflight, "MD_DIR", md_dir)
    monkeypatch.setattr(preflight, "PDF_DIR", pdf_dir)

    good = "x" * (preflight.TOO_SHORT_CHARS + 50)
    (md_dir / "p1.md").write_text(good)
    (pdf_dir / "p1.pdf").write_bytes(b"%PDF- would-be-fresh-conversion")

    converted = {"n": 0}

    def fake_convert(pid):
        converted["n"] += 1
        return "y" * (preflight.TOO_SHORT_CHARS + 5), False

    monkeypatch.setattr(preflight, "convert_pdf_to_md", fake_convert)
    status, _ = preflight.classify("p1", allow_reconvert=True)
    assert status == "ready"
    assert converted["n"] == 0, "good extraction must not be reconverted"
    assert (md_dir / "p1.md").read_text() == good


def test_classify_replaces_too_short_only_with_longer(preflight, tmp_path,
                                                      monkeypatch):
    md_dir = tmp_path / "md"
    pdf_dir = tmp_path / "pdf"
    md_dir.mkdir()
    pdf_dir.mkdir()
    monkeypatch.setattr(preflight, "MD_DIR", md_dir)
    monkeypatch.setattr(preflight, "PDF_DIR", pdf_dir)

    (md_dir / "p2.md").write_text("short")       # 5 chars
    (pdf_dir / "p2.pdf").write_bytes(b"%PDF-")

    # fresh conversion longer than threshold → replaces, ready
    monkeypatch.setattr(preflight, "convert_pdf_to_md",
                        lambda pid: ("z" * (preflight.TOO_SHORT_CHARS + 10), False))
    status, _ = preflight.classify("p2", allow_reconvert=True)
    assert status == "ready"
    assert len((md_dir / "p2.md").read_text()) == preflight.TOO_SHORT_CHARS + 10

    # fresh conversion still short → keeps longer, reports too_short
    (md_dir / "p3.md").write_text("12345678")
    (pdf_dir / "p3.pdf").write_bytes(b"%PDF-")
    monkeypatch.setattr(preflight, "convert_pdf_to_md",
                        lambda pid: ("1" * 10, False))
    status, _ = preflight.classify("p3", allow_reconvert=True)
    assert status == "too_short"
    assert (md_dir / "p3.md").read_text() == "1" * 10  # longer kept


def test_classify_junk_pdf_becomes_missing_source(preflight, tmp_path,
                                                  monkeypatch):
    md_dir = tmp_path / "md"
    pdf_dir = tmp_path / "pdf"
    md_dir.mkdir()
    pdf_dir.mkdir()
    monkeypatch.setattr(preflight, "MD_DIR", md_dir)
    monkeypatch.setattr(preflight, "PDF_DIR", pdf_dir)

    (md_dir / "p4.md").write_text("JavaScript is disabled in your browser.")
    (pdf_dir / "p4.pdf").write_bytes(b"%PDF-")
    monkeypatch.setattr(
        preflight, "convert_pdf_to_md",
        lambda pid: ("JavaScript is disabled in your browser. Please "
                     "enable JavaScript.", True))
    status, info = preflight.classify("p4", allow_reconvert=True)
    assert status == "missing_source"
    assert info["removed_junk_pdf"]
    assert not (pdf_dir / "p4.pdf").exists()
    assert not (md_dir / "p4.md").exists()
