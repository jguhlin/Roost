"""Appeal-layer tests (D80): two-prompt investigation of muse rejections.

Stage 1 (investigator) may only overturn with a verbatim quote from the
candidate's passage; stage 2 (skeptic) must re-confirm from the single
quoted sentence. Only double-confirmed overturns publish as approvals.
"""

import json

import pytest

from conftest import load_module


@pytest.fixture()
def conn():
    return load_module("papers/connections.py", "connections_appeal_test")


PASSAGE = ("We investigated host factors required for avian influenza "
           "polymerase activity. Human ANP32A binds FluPol 627E, and "
           "co-immunoprecipitation demonstrated that ANP32A interacts "
           "directly with PB2. Controls showed no binding to NP.")


def _cand(cid, quote="Human ANP32A binds FluPol 627E"):
    return {
        "candidate_id": cid, "window_id": "w" + cid, "gene": "ANP32A",
        "paper_id": "p_one", "from": "ANP32A", "to": "PB2",
        "mechanism": "binding", "quote": quote,
        "context": {"proposed_stage": "early", "location": "",
                    "species": "human", "phenotype": "",
                    "evidence_type": "experimental",
                    "reported_timepoints": ""},
        "status": "pending",
    }


def _env(conn, tmp_path, monkeypatch, cands, decisions):
    papers = tmp_path / "papers.json"
    papers.write_text(json.dumps({"papers": [
        {"id": "p_one", "title": "One", "year": 2024, "journal": "J",
         "doi": "d", "url": ""},
    ]}))
    cpath = tmp_path / "candidates.jsonl"
    conn.append_jsonl(cpath, cands)
    dpath = tmp_path / "decisions.json"
    dpath.write_text(json.dumps(decisions))
    windows = tmp_path / "windows.jsonl"
    conn.append_jsonl(windows, [
        {"window_id": "w" + c["candidate_id"], "gene": c["gene"],
         "paper_id": c["paper_id"], "via": [], "para": [0, 1],
         "char_len": len(PASSAGE), "co_genes": [], "co_viral": [],
         "eligible": True}
        for c in cands
    ])
    md = tmp_path / "p_one.md"
    md.write_text(PASSAGE + "\n\n" + PASSAGE)
    appeals = tmp_path / "appeals.jsonl"
    adone = tmp_path / "appeals_done.jsonl"
    monkeypatch.setattr(conn, "PAPERS_JSON", papers)
    monkeypatch.setattr(conn, "CANDIDATES_PATH", cpath)
    monkeypatch.setattr(conn, "REVIEW_PATH", dpath)
    monkeypatch.setattr(conn, "WINDOWS_PATH", windows)
    monkeypatch.setattr(conn, "MD_DIR", tmp_path)
    monkeypatch.setattr(conn, "APPEALS_PATH", appeals)
    monkeypatch.setattr(conn, "APPEALS_DONE_PATH", adone)
    return dpath, appeals, adone


def _reject_note(cid):
    return {cid: {"status": "rejected", "reviewer": "muse",
                  "model": "muse-glimmer-30b", "decided": "t",
                  "note": "quote reports FluPol, not PB2"}}


def _dispatch_chat(conn, stage1_reply, stage2_reply):
    def fake_chat(system, user, *a, **k):
        if "re-examine REJECTED" in system:
            return stage1_reply
        return stage2_reply
    return fake_chat


def test_double_confirmed_overturn_approves(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, appeals, _ = _env(conn, tmp_path, monkeypatch, cands,
                          _reject_note("c1"))
    stage1 = json.dumps({"candidate_verdicts": [{
        "candidate_id": "c1", "verdict": "overturn",
        "reason": "co-IP shows direct interaction",
        "quote": "co-immunoprecipitation demonstrated that ANP32A "
                 "interacts directly with PB2",
    }]})
    stage2 = json.dumps({"verdict": "confirm",
                         "reason": "explicit direct interaction",
                         "quote": "co-immunoprecipitation demonstrated that "
                                  "ANP32A interacts directly with PB2"})
    monkeypatch.setattr(conn, "muse_chat",
                        _dispatch_chat(conn, stage1, stage2))
    conn.run_review_appeal("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["status"] == "approved"
    assert dec["c1"]["reviewer"] == "muse-appeal"
    assert "skeptic confirmed" in dec["c1"]["note"]
    audit = [json.loads(l) for l in appeals.read_text().splitlines()]
    assert audit[0]["stage2"]["verdict"] == "confirm"


def test_skeptic_deny_keeps_rejection(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, appeals, _ = _env(conn, tmp_path, monkeypatch, cands,
                          _reject_note("c1"))
    stage1 = json.dumps({"candidate_verdicts": [{
        "candidate_id": "c1", "verdict": "overturn",
        "reason": "passage states interaction",
        "quote": "co-immunoprecipitation demonstrated that ANP32A "
                 "interacts directly with PB2",
    }]})
    stage2 = json.dumps({"verdict": "deny", "reason": "not explicit",
                         "quote": ""})
    monkeypatch.setattr(conn, "muse_chat",
                        _dispatch_chat(conn, stage1, stage2))
    conn.run_review_appeal("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["status"] == "rejected"      # unchanged
    assert dec["c1"]["reviewer"] == "muse"
    audit = [json.loads(l) for l in appeals.read_text().splitlines()]
    assert audit[0]["stage1"]["verdict"] == "overturn"
    assert audit[0]["stage2"]["verdict"] == "deny"


def test_overturn_quote_must_come_from_passage(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, _, _adone = _env(conn, tmp_path, monkeypatch, cands, _reject_note("c1"))
    stage1 = json.dumps({"candidate_verdicts": [{
        "candidate_id": "c1", "verdict": "overturn",
        "reason": "invented",
        "quote": "ANP32A physically binds the PB2 subunit with high affinity",
    }]})  # NOT in the passage → must downgrade to uncertain
    monkeypatch.setattr(conn, "muse_chat",
                        _dispatch_chat(conn, stage1, "{}"))
    conn.run_review_appeal("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["status"] == "rejected"      # no appeal applied


def test_skeptic_confirm_requires_quotable_sentence(conn, tmp_path,
                                                    monkeypatch):
    cands = [_cand("c1")]
    dpath, _, _adone = _env(conn, tmp_path, monkeypatch, cands, _reject_note("c1"))
    q = "co-immunoprecipitation demonstrated that ANP32A interacts directly with PB2"
    stage1 = json.dumps({"candidate_verdicts": [{
        "candidate_id": "c1", "verdict": "overturn",
        "reason": "passage states it", "quote": q}]})
    stage2 = json.dumps({"verdict": "confirm", "reason": "yes",
                         "quote": "some sentence that is not the quoted one"})
    monkeypatch.setattr(conn, "muse_chat",
                        _dispatch_chat(conn, stage1, stage2))
    conn.run_review_appeal("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["status"] == "rejected"      # skeptic could not quote → deny


def test_human_rejections_never_enter_appeal(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, _, _adone = _env(conn, tmp_path, monkeypatch, cands,
                    {"c1": {"status": "rejected", "reviewer": "human",
                            "decided": "t", "note": ""}})
    called = {"n": 0}
    monkeypatch.setattr(conn, "muse_chat",
                        lambda *a, **k: called.__setitem__(
                            "n", called["n"] + 1) or "{}")
    conn.run_review_appeal("http://x/v1", "muse-glimmer-30b", workers=1)
    dec = json.loads(dpath.read_text())
    assert dec["c1"]["reviewer"] == "human"
    assert called["n"] == 0


def test_resume_skips_done_batches(conn, tmp_path, monkeypatch):
    cands = [_cand("c1")]
    dpath, _, adone = _env(conn, tmp_path, monkeypatch, cands,
                        _reject_note("c1"))
    conn.append_jsonl(adone, [{"batch": "c1", "ts": "t"}])
    called = {"n": 0}
    monkeypatch.setattr(conn, "muse_chat",
                        lambda *a, **k: called.__setitem__(
                            "n", called["n"] + 1) or "{}")
    conn.run_review_appeal("http://x/v1", "muse-glimmer-30b", workers=1)
    assert called["n"] == 0
