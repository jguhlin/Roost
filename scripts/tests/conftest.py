"""Shared fixtures for Roost scripts tests.

Loads sibling scripts by file path (they are not an installable package).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"


def load_module(relpath, name):
    path = SCRIPTS / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def repo_root():
    return ROOT


@pytest.fixture(scope="session")
def preflight():
    return load_module("papers/corpus_preflight.py", "corpus_preflight")
