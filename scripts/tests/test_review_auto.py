"""Muse auto-review tests (D79).

The reviewer must: require verbatim citations for every decision (anything
unquotable from the supplied evidence downgrades to uncertain), leave human
decisions untouched, tag its provenance, and stay resume-safe.
"""

import json

import pytest

from conftest import load_module


@pytest.fixture()
def conn():
    return load_module("papers/connections.py", "connections_test")


def _cand(cid, frm="DDX58", to="MAVS", mech="activation",
          quote="RIG-I signalling activates MAVS within hours",
          paper="p_one"):
    return {
        "candidate_id": cid, "window_id": "w" + cid, "gene": frm,
        "paper_id": paper, "from": frm, "to": to, "mechanism": mech,
        "quote": quote,
        "context": {"proposed_stage": "early", "location": "",
                    "species": "chicken", "phenotype": "",
                    "evidence_type": "experimental",
                    "reported_timepoints": "12 hpi"},
        "status": "pending",
    }


def test_extract_json_object_balanced_and_string_safe(conn):
    assert conn.extract_json_object(None) is None
    assert conn.extract_json_object("no braces") is None
    obj = conn.extract_json_object('noise {"a": {"b": 1}, "c": "x}y"} tail')
    assert obj == {"a": {"b": 1}, "c": "x}y"}
    # braces inside strings must not break balance
    assert conn.extract_json_object('{"q": "curly } braces {"}') == \
        {"q": "curly } braces {"}
    # truncated object → None (quarantine path)
    assert conn.extract_json_object('{"verdict": "appr') is None
    # last complete object wins
    both = '{"v": 1} middle {"v": 2}'
    assert conn.extract_json_object(both)["v"] == 2


def _env(conn, tmp_path, monkeypatch, cands, decisions=None):
    papers = tmp_path / "papers.json"
    papers.write_text(json.dumps({"papers": [
        {"id": "p_one", "title": "One", "year": 2024, "journal": "J",
         "doi": "d", "url": ""},
    ]}))
    cpath = tmp_path / "candidates.jsonl"
    conn.append_jsonl(cpath, cands)
    dpath = tmp_path / "decisions.json"
    dpath.write_text(json.dumps(decisions or {}))
    adone = tmp_path / "auto_done.jsonl"
    monkeypatch.setattr(conn, "PAPERS_JSON", papers)
    monkeypatch.setattr(conn, "CANDIDATES_PATH", cpath)
    monkeypatch.setattr(conn, "REVIEW_PATH", dpath)
    monkeypatch.setattr(conn, "AUTO_DONE_PATH", adone)
    return dpath, adone


def test_unquotable_justification_downgrades_to_uncertain(conn, tmp_path,
                                                           monkeypatch):
    """Approve whose 'quote' is NOT in the evidence pack → no decision."""
    cands = [_cand("c1")]
    dpath, adone = _env(conn, tmp_path, monkeypatch, cands)
    reply = json.dumps({
        "verdict": "approve", "reason": "looks right",
        "quote": "MAVS is activated by RIG-I downstream of detection",
        "candidate_verdicts": [{
            "candidate_id": "c1", "verdict": "approve",
            "reason": "looks right",
            "quote": "MAVS is activated by RIG-I downstream of detection",
        }],
    })
    monkeypatch.setattr(conn, "muse_chat", lambda *a, **k: reply)
    conn.run_review_auto("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec == {}, "unquotable justification must not decide anything"
    # the group is still marked processed (no infinite retry)
    assert adone.exists()


def test_quoted_verdicts_recorded_with_provenance(conn, tmp_path,
                                                  monkeypatch):
    cands = [_cand("c1"), _cand("c2", quote="RIG-I activates MAVS in duck cells")]
    dpath, adone = _env(conn, tmp_path, monkeypatch, cands)
    reply = json.dumps({
        "verdict": "approve", "reason": "explicit mechanism, right direction",
        "quote": "RIG-I signalling activates MAVS within hours",
        "candidate_verdicts": [
            {"candidate_id": "c1", "verdict": "approve",
             "reason": "explicit activation statement",
             "quote": "RIG-I signalling activates MAVS within hours"},
            {"candidate_id": "c2", "verdict": "reject",
             "reason": "co-expression only",
             "quote": "RIG-I activates MAVS in duck cells"},
        ],
    })
    monkeypatch.setattr(conn, "muse_chat", lambda *a, **k: reply)
    conn.run_review_auto("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["status"] == "approved"
    assert dec["c1"]["reviewer"] == "muse"
    assert dec["c1"]["model"] == "muse-glimmer-30b"
    assert "explicit activation" in dec["c1"]["note"]
    assert dec["c2"]["status"] == "rejected"


def test_human_decisions_are_final(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, _ = _env(conn, tmp_path, monkeypatch, cands,
                    {"c1": {"status": "rejected", "reviewer": "human",
                            "decided": "t", "note": ""}})
    called = {"n": 0}

    def fake_chat(*a, **k):
        called["n"] += 1
        return "{}"

    monkeypatch.setattr(conn, "muse_chat", fake_chat)
    conn.run_review_auto("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["reviewer"] == "human"   # untouched
    assert called["n"] == 0                   # group skipped entirely


def test_resume_set_skips_done_groups(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, adone = _env(conn, tmp_path, monkeypatch, cands)
    conn.append_jsonl(adone, [{"group": ["DDX58", "MAVS", "activation"],
                               "ts": "t"}])
    called = {"n": 0}
    monkeypatch.setattr(conn, "muse_chat",
                        lambda *a, **k: called.__setitem__("n",
                                                           called["n"] + 1) or "{}")
    conn.run_review_auto("http://x/v1", "muse-glimmer-30b", workers=1)
    assert called["n"] == 0
    print(conn.run_review_auto.__doc__)


def test_muse_decisions_rerun_only_when_pending(conn, tmp_path, monkeypatch):
    """A second auto pass must not re-decide muse-decided candidates
    (reset via `review reset` to redo)."""
    cands = [_cand("c1")]
    dpath, _ = _env(conn, tmp_path, monkeypatch, cands)
    reply = json.dumps({
        "verdict": "approve", "reason": "explicit",
        "quote": "RIG-I signalling activates MAVS within hours",
        "candidate_verdicts": [
            {"candidate_id": "c1", "verdict": "approve", "reason": "explicit",
             "quote": "RIG-I signalling activates MAVS within hours"}]})
    monkeypatch.setattr(conn, "muse_chat", lambda *a, **k: reply)
    conn.run_review_auto("http://x/v1", "muse-glimmer-30b", workers=1)
    assert json.loads(dpath.read_text())["c1"]["status"] == "approved"
    # second pass: groups all have muse decisions → nothing todo
    conn.run_review_auto("http://x/v1", "muse-glimmer-30b", workers=1)
    assert json.loads(dpath.read_text())["c1"]["status"] == "approved"
