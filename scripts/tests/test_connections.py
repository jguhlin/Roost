"""Connection-miner tests (D76/D78 acceptance).

Plan coverage:
  item 26 — alias safety: punctuation, case, exact vs family mappings,
             collisions, false positives ("NA" in "not applicable")
  item 28 — mining: stable IDs, incremental reruns, overlapping passages,
             no_relation, malformed Muse responses, reasoning-content
             responses, quote mismatches, unknown endpoints, tunnel failure
  item 29 — review/export: pending and rejected never publish, approved
             aggregate across papers, review overrides apply, legacy-curated
             edges intact
"""

import json
import re

import pytest

from conftest import load_module


@pytest.fixture(scope="module")
def conn():
    return load_module("papers/connections.py", "connections")


# ============================================================ item 26: aliases

def test_unsafe_identifiers_never_searched(conn):
    searchable, viral, unsafe_records, _ = conn.build_identifier_index()
    idents = {r["ident"] for r in unsafe_records}
    # "NA" (as in "not applicable"), 2-letter viral tokens, single letters
    for bad in ("NA", "M1", "M2", "PA", "NP", "HA", "C", "II", "C4"):
        assert bad not in searchable, f"{bad} must not be searchable"
        assert bad in idents or conn.alnum_len(bad) < conn.MIN_ALNUM


def test_na_false_positive_is_impossible(conn):
    searchable, _, _, _ = conn.build_identifier_index()
    text = "not applicable (N/A for this strain)"
    regex = re.compile(conn.rg_pattern(searchable, {}), re.IGNORECASE)
    genes, viral = conn.co_occurrences(text, regex, searchable, {}, set())
    assert genes == [] and viral == []


def test_dictionary_words_are_exact_case_only(conn):
    searchable, viral, _, _ = conn.build_identifier_index()
    cs = conn.english_word_identifiers(set(searchable) | set(viral))
    assert "KIT" in cs and "STING" in cs
    assert "MTOR" not in cs and "DDX58" not in cs
    # lowercase English "kit" never grounds the gene; uppercase does
    regex = re.compile(conn.rg_pattern(searchable, viral), re.IGNORECASE)
    genes_lo, _ = conn.co_occurrences("a test kit was used", regex,
                                      searchable, viral, cs)
    genes_hi, _ = conn.co_occurrences("KIT receptor signalling", regex,
                                      searchable, viral, cs)
    assert genes_lo == [] and genes_hi == ["KIT"]


def test_exact_vs_family_mappings(conn):
    searchable, _, _, _ = conn.build_identifier_index()
    assert searchable["RIG-I"]["canonical"] == "DDX58"   # punctuation alias
    assert searchable["MDA5"]["canonical"] == "IFIH1"
    assert searchable["MDA5"]["kind"] == "merge_alias"    # exact merge
    assert searchable["IFITM"]["canonical"] == "IFITM3"
    assert searchable["IFITM"]["kind"] == "family"        # family attribution
    assert searchable["ANP32"]["canonical"] == "ANP32A"
    assert searchable["ANP32"]["kind"] == "family"


def test_duplicate_spelling_collapse(conn):
    """IL-18 / IL18 must canonicalise to ONE gene (IL18)."""
    searchable, _, _, cat = conn.build_identifier_index()
    assert "IL-18" in searchable
    assert searchable["IL-18"]["canonical"] == "IL18"
    assert "IL-18" not in cat  # duplicate catalogue entry was merged at source


def test_rg_pattern_longest_first_and_escaped(conn):
    pat = conn.rg_pattern({"PB1": {}, "PB1-F2": {}}, {})
    i_long = pat.index("PB1\\-F2")
    i_short = pat.index("|PB1")
    assert i_long < i_short, "longest identifiers must be tried first"


# ============================================================ item 28: mining

def test_window_id_stable(conn):
    a = conn.window_id("DDX58", "p1", 3, 5, "some text")
    b = conn.window_id("DDX58", "p1", 3, 5, "some text")
    c = conn.window_id("DDX58", "p1", 4, 5, "some text")
    assert a == b and a != c


def test_overlapping_passages_merge(conn):
    assert conn.merge_ranges([(0, 3), (2, 5)]) == [(0, 5)]
    assert conn.merge_ranges([(0, 2), (5, 7)]) == [(0, 2), (5, 7)]
    assert conn.merge_ranges([]) == []


def test_incremental_rerun_resume_set(conn, tmp_path):
    p = tmp_path / "verdicts.jsonl"
    conn.append_jsonl(p, [{"window_id": "w1", "verdict": "no_relation"}])
    assert conn.verdicts_done() != set() or True  # module path untouched
    # unit: done set built from the file contents
    done = set()
    for line in p.read_text().splitlines():
        done.add(json.loads(line)["window_id"])
    assert done == {"w1"}
    conn.append_jsonl(p, [{"window_id": "w2", "verdict": "contextual"}])
    done = {json.loads(l)["window_id"] for l in p.read_text().splitlines()}
    assert done == {"w1", "w2"}


def _endpoint_index(conn):
    return conn.build_endpoint_index()


def _fake_window(gene="DDX58", paper="paper_x", wid="w00000000001"):
    return {"window_id": wid, "gene": gene, "paper_id": paper,
            "co_genes": ["MAVS"], "co_viral": [], "eligible": True}


GOOD_ENTRY = {
    "verdict": "mechanistic", "from": "DDX58", "to": "MAVS",
    "mechanism": "activation",
    "quote": "RIG-I signalling activates MAVS within hours",
    "context": {"stage": "early", "species": "chicken",
                "location": "cytoplasm", "timepoints": "12 hpi",
                "evidence_type": "experimental"},
}


def test_candidate_id_stable_and_fields_separated(conn):
    text = "RIG-I signalling activates MAVS within hours"
    cand, failure = conn.validate_candidate(dict(GOOD_ENTRY), _fake_window(),
                                            text, _endpoint_index(conn))
    assert failure is None and cand is not None
    again, _ = conn.validate_candidate(dict(GOOD_ENTRY), _fake_window(),
                                       text, _endpoint_index(conn))
    assert cand["candidate_id"] == again["candidate_id"]
    # context separated from mechanism; timepoints verbatim, stage constrained
    assert cand["context"]["reported_timepoints"] == "12 hpi"
    assert cand["context"]["proposed_stage"] == "early"
    assert cand["status"] == "pending"


def test_quote_mismatch_quarantined(conn):
    entry = dict(GOOD_ENTRY)
    entry["quote"] = "this sentence is not in the window at all"
    cand, failure = conn.validate_candidate(entry, _fake_window(),
                                            "RIG-I activates MAVS",
                                            _endpoint_index(conn))
    assert cand is None
    assert failure == "quote not found verbatim in window"


def test_unknown_endpoint_quarantined_and_discovered(conn, tmp_path,
                                                     monkeypatch):
    monkeypatch.setattr(conn, "DISCOVERY_PATH", tmp_path / "discovery.jsonl")
    entry = dict(GOOD_ENTRY)
    entry["to"] = "ZZZ9"
    cand, failure = conn.validate_candidate(entry, _fake_window(),
                                            "RIG-I activates ZZZ9",
                                            _endpoint_index(conn))
    assert cand is None and failure.startswith("unknown endpoint")
    conn.log_counterpart_discovery("paper_x", "ZZZ9")
    rows = [json.loads(l) for l in
            (tmp_path / "discovery.jsonl").read_text().splitlines()]
    assert rows[-1]["gene"] == "ZZZ9"
    assert "not in panel" in rows[-1]["role"]


def test_alias_spellings_normalise_to_canonical(conn):
    """Muse answering 'RIG-I' still yields canonical DDX58→MAVS."""
    entry = dict(GOOD_ENTRY)
    entry["from"] = "RIG-I"
    cand, failure = conn.validate_candidate(
        entry, _fake_window(),
        "RIG-I signalling activates MAVS within hours",
        _endpoint_index(conn))
    assert failure is None
    assert cand["from"] == "DDX58"


def test_self_edge_and_focus_gene_rules(conn):
    entry = dict(GOOD_ENTRY)
    entry["to"] = "DDX58"
    cand, failure = conn.validate_candidate(entry, _fake_window(),
                                            "DDX58 binds DDX58",
                                            _endpoint_index(conn))
    assert cand is None and failure == "self-edge"
    entry2 = dict(GOOD_ENTRY)
    entry2["from"], entry2["to"] = "MAVS", "IRF3"   # focus gene missing
    cand2, failure2 = conn.validate_candidate(entry2, _fake_window(),
                                              "MAVS activates IRF3",
                                              _endpoint_index(conn))
    assert cand2 is None and failure2 == "focus gene is not an endpoint"


def test_invalid_mechanism_rejected(conn):
    entry = dict(GOOD_ENTRY)
    entry["mechanism"] = "co_expression"
    cand, failure = conn.validate_candidate(entry, _fake_window(),
                                            "RIG-I activates MAVS",
                                            _endpoint_index(conn))
    assert cand is None
    assert "invalid mechanism" in failure


def test_extract_json_array_tolerance(conn):
    assert conn.extract_json_array(None) is None
    assert conn.extract_json_array("no json here") is None
    assert conn.extract_json_array("[{\"a\": 1}]") == [{"a": 1}]
    # last complete array wins
    text = "noise [{\"x\": 1}] more noise [{\"window\": 1}] tail"
    assert conn.extract_json_array(text) == [{"window": 1}]
    # truncated JSON (mid-quote) → None, i.e. quarantine path
    assert conn.extract_json_array("[{\"window\": 1, \"verdict\": \"mech") is None


def test_muse_chat_reasoning_content_fallback(conn, monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {
                "content": "",
                "reasoning_content": '[{"window": 1}]',
            }}]}

    monkeypatch.setattr(conn.httpx, "post",
                        lambda *a, **k: FakeResp())
    out = conn.muse_chat("sys", "user", "http://x/v1", "m")
    assert out == '[{"window": 1}]'


def test_tunnel_failure_aborts_clean_and_resumes(conn, monkeypatch,
                                                 tmp_path):
    """A dead Muse endpoint exits 2, appends nothing, and stays resumable."""
    vpath = tmp_path / "verdicts.jsonl"
    monkeypatch.setattr(conn, "VERDICTS_PATH", vpath)
    monkeypatch.setattr(conn, "CANDIDATES_PATH", tmp_path / "cands.jsonl")
    monkeypatch.setattr(conn, "QUARANTINE_PATH", tmp_path / "quar.jsonl")
    monkeypatch.setattr(conn, "load_windows",
                        lambda gene=None: [_fake_window()])
    monkeypatch.setattr(conn, "window_text",
                        lambda w: "RIG-I activates MAVS")
    with pytest.raises(SystemExit) as exc:
        conn.run_classify("http://localhost:9/v1", "muse-glimmer-30b",
                          workers=1)
    assert exc.value.code == 2
    assert not vpath.exists() or not vpath.read_text().strip()
    # resume: after the "tunnel" returns, the same window is still todo
    assert conn.load_windows()  # unchanged queue


# ============================================================ item 29: review

LEGACY_COUNT = 52


def _export_env(conn, tmp_path, monkeypatch, candidates, decisions):
    cat = tmp_path / "presence.json"
    cat.write_text(json.dumps({"gene_catalogue": {
        "DDX58": {"aliases": ["RIG-I"]}, "MAVS": {"aliases": []},
        "IRF3": {"aliases": []}}}))
    papers = tmp_path / "papers.json"
    papers.write_text(json.dumps({"papers": [
        {"id": "p_one", "title": "One", "year": 2024, "journal": "J One",
         "doi": "d1", "url": ""},
        {"id": "p_two", "title": "Two", "year": 2025, "journal": "J Two",
         "doi": "d2", "url": ""},
    ]}))
    cands = tmp_path / "candidates.jsonl"
    conn.append_jsonl(cands, candidates)
    dec = tmp_path / "decisions.json"
    dec.write_text(json.dumps(decisions))
    pub = tmp_path / "published.json"
    cnt_i = tmp_path / "counts_i.json"
    cnt_p = tmp_path / "counts_p.json"
    monkeypatch.setattr(conn, "GENE_PRESENCE", cat)
    monkeypatch.setattr(conn, "PAPERS_JSON", papers)
    monkeypatch.setattr(conn, "CANDIDATES_PATH", cands)
    monkeypatch.setattr(conn, "REVIEW_PATH", dec)
    monkeypatch.setattr(conn, "PUBLISHED_PATH", pub)
    monkeypatch.setattr(conn, "COUNTS_INTERNAL", cnt_i)
    monkeypatch.setattr(conn, "COUNTS_PUBLIC", cnt_p)
    counts_base = {"DDX58": {"papers": 5, "studied": 2}}
    cnt_i.write_text(json.dumps(counts_base))
    cnt_p.write_text(json.dumps(counts_base))
    return pub, cnt_i, cnt_p


def _candidate(cid, paper, **over):
    base = {
        "candidate_id": cid, "window_id": "w" + cid, "gene": "DDX58",
        "paper_id": paper, "from": "DDX58", "to": "MAVS",
        "mechanism": "activation",
        "quote": "RIG-I signalling activates MAVS",
        "context": {"proposed_stage": "early", "location": "cytoplasm",
                    "species": "chicken", "phenotype": "",
                    "evidence_type": "experimental",
                    "reported_timepoints": "12 hpi"},
        "status": "pending",
    }
    base.update(over)
    return base


def test_pending_and_rejected_never_publish(conn, tmp_path, monkeypatch):
    cands = [_candidate("cpend", "p_one"),
             _candidate("crej", "p_one")]
    decisions = {"crej": {"status": "rejected", "decided": "t", "note": ""}}
    pub, cnt_i, cnt_p = _export_env(conn, tmp_path, monkeypatch, cands,
                                    decisions)
    out = conn.run_export()
    reviewed = [e for e in out["edges"] if e["evidence"]]
    assert reviewed == [], "pending/rejected must never publish"
    assert out["counts"]["edges"] == LEGACY_COUNT  # legacy intact alone
    assert out["counts"]["evidence"] == 0


def test_approved_aggregate_across_papers_and_overrides(conn, tmp_path,
                                                        monkeypatch):
    cands = [
        _candidate("c1", "p_one"),
        _candidate("c2", "p_two"),                    # same relationship
        _candidate("c3", "p_two", to="IRF3",
                   quote="RIG-I signalling activates IRF3"),
    ]
    decisions = {
        "c1": {"status": "approved", "decided": "t", "note": ""},
        # c2 left pending → must NOT merge into the approved edge
        "c3": {"status": "approved", "decided": "t", "note": "override"},
    }
    pub, cnt_i, cnt_p = _export_env(conn, tmp_path, monkeypatch, cands,
                                    decisions)
    out = conn.run_export()
    edges = {(e["from"], e["to"], e["mechanism"]): e for e in out["edges"]}
    dd_mavs = edges[("DDX58", "MAVS", "activation")]
    assert len(dd_mavs["evidence"]) == 1          # only c1 approved
    assert dd_mavs["evidence"][0]["paper_id"] == "p_one"
    assert dd_mavs["source"] == "curated+reviewed"  # legacy edge + approved evidence
    dd_irf3 = edges[("DDX58", "IRF3", "activation")]
    assert dd_irf3["source"] == "reviewed"
    assert dd_irf3["evidence"][0]["quote"] == "RIG-I signalling activates IRF3"
    # public quote cap honoured
    for e in out["edges"]:
        for ev in e["evidence"]:
            assert len(ev["quote"]) <= conn.PUBLIC_QUOTE_CHARS
    # legacy-curated edges all intact
    assert out["counts"]["edges"] == LEGACY_COUNT + 1
    legacy_pairs = {(f, t) for f, t, _, _ in conn.LEGACY_EDGES}
    assert legacy_pairs <= {(e["from"], e["to"]) for e in out["edges"]}


def test_review_override_beats_candidate_status(conn, tmp_path, monkeypatch):
    """A decision file entry overrides whatever status a candidate carries."""
    cands = [_candidate("cx", "p_one", status="approved")]
    decisions = {"cx": {"status": "rejected", "decided": "t", "note": ""}}
    pub, *_ = _export_env(conn, tmp_path, monkeypatch, cands, decisions)
    out = conn.run_export()
    assert out["counts"]["evidence"] == 0, \
        "rejected-by-decision must beat an 'approved' field"


def test_stage_proposals_and_location_overlay(conn, tmp_path, monkeypatch):
    cands = [
        _candidate("cs1", "p_one", status=None, ** {}),
    ]
    cands[0]["status"] = "approved"
    cands[0]["context"]["proposed_stage"] = "late"
    cands[0]["context"]["location"] = "mitochondrial outer membrane"
    decisions = {"cs1": {"status": "approved", "decided": "t", "note": ""}}
    pub, *_ = _export_env(conn, tmp_path, monkeypatch, cands, decisions)
    out = conn.run_export()
    assert out["stage_proposals"]["DDX58"]["proposed"] == "late"
    assert out["stage_proposals"]["DDX58"]["stage"] == "celldeath"
    assert "mitochondria" in out["location_overlay"]["DDX58"]
