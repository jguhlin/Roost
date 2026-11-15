"""Contextual stage-placement tests (D82).

contextual_pass fills ONLY genes with no assignment (source 'none');
model/keyword/claims/override decisions are untouchable.
"""

import json

import pytest

from conftest import load_module


@pytest.fixture()
def assign():
    return load_module("genes/assign_stages.py", "assign_stages_test")


def test_contextual_pass_fills_only_unassigned(assign, tmp_path, monkeypatch):
    path = tmp_path / "contextual_stages.json"
    path.write_text(json.dumps({
        "GENEA": {"stage": "sensing", "note": "n", "quote": "q",
                  "papers": ["p1"]},
        "GENEB": {"stage": "effectors", "note": "n", "quote": "q",
                  "papers": ["p1"]},
        "GENEC": {"stage": "signaling", "note": "n", "quote": "q",
                  "papers": ["p1"]},
        "GENED": {"stage": "not-a-stage", "note": "n", "quote": "q",
                  "papers": ["p1"]},
    }))
    monkeypatch.setattr(assign, "ROOT", tmp_path)
    # recreate the expected relative path under the fake ROOT
    sub = tmp_path / "data" / "papers" / "connections"
    sub.mkdir(parents=True)
    (sub / "contextual_stages.json").write_text(path.read_text())

    assignment = {
        "GENEA": {"stage": None, "source": "none"},          # fillable
        "GENEB": {"stage": "adaptive", "source": "model"},   # untouchable
        "GENEC": {"stage": "sensing", "source": "keyword"},  # untouchable
        "GENED": {"stage": None, "source": "none"},          # invalid stage id
    }
    n = assign.contextual_pass(assignment)
    assert n == 1
    assert assignment["GENEA"] == {
        "stage": "sensing", "source": "contextual", "note": "n"}
    assert assignment["GENEB"]["source"] == "model"
    assert assignment["GENEC"]["source"] == "keyword"
    assert assignment["GENED"]["source"] == "none"


def test_contextual_pass_no_file(assign, tmp_path, monkeypatch):
    monkeypatch.setattr(assign, "ROOT", tmp_path)
    assert assign.contextual_pass({}) == 0
