"""Tests for the per-paper DEG summary builder.

build_deg_summaries.py moves the DEG story (counts, top expressed genes) to
the PAPER level: count findings must be quantified infection-category
statements; criteria/threshold findings (FDR cut-offs) are excluded; gene
chips must be real symbols (no antibodies, no parentheticals, no comma lists).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "papers"))

from build_deg_summaries import (  # noqa: E402
    CRITERIA_RE,
    DEG_RE,
    EXPR_ROLE_RE,
)


class TestDegDetection:
    def test_deg_finding_matched(self):
        assert DEG_RE.search("Differentially expressed genes (DEGs) in DK/49-infected ducks")
        assert DEG_RE.search("Total number of DEGs identified")

    def test_non_deg_finding_not_matched(self):
        assert not DEG_RE.search("Mortality reached 85% in chickens")


class TestCriteriaExclusion:
    def test_identification_criteria(self):
        assert CRITERIA_RE.search("DEG identification criteria")

    def test_selection_criteria(self):
        assert CRITERIA_RE.search("DEG selection criteria were applied")

    def test_cutoff(self):
        assert CRITERIA_RE.search("used a cut-off of 0.05")

    def test_normal_finding_not_excluded(self):
        assert not CRITERIA_RE.search("DEGs in DK/49-infected ducks vs control (Day 2)")


class TestExpressionRoles:
    def test_upregulated(self):
        assert EXPR_ROLE_RE.search("Upregulated by H1N1 infection; enhances chemotaxis")

    def test_elevated(self):
        assert EXPR_ROLE_RE.search("An RNA helicase with significantly elevated expression")

    def test_resistant_line(self):
        assert EXPR_ROLE_RE.search("higher in resistant chickens")

    def test_structural_role_not_matched(self):
        assert not EXPR_ROLE_RE.search("Encodes the viral RNA polymerase subunit")
