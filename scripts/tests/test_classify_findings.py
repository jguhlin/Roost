"""Tests for key-finding categorisation and garbage filtering.

Covers scripts/papers/classify_findings.py:
- methods/QC findings (alignment rate, reads per sample, QC thresholds)
  classify as "methods"
- infection findings (mortality, shedding, fold change, DEG counts)
  classify as "infection"
- table-dump gene roles and truncated fragment findings are garbage
- real findings are NOT flagged as garbage
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "papers"))

from classify_findings import (  # noqa: E402
    classify,
    is_garbage_finding,
    is_garbage_role,
)


class TestMethodsClassification:
    def test_alignment_rate(self):
        assert classify("Average alignment rate of RNA-seq reads to the duck genome") == "methods"

    def test_reads_per_sample(self):
        assert classify("Paired-end reads per sample range") == "methods"

    def test_qc_bound(self):
        assert classify("Cell-level QC n_genes lower bound for Control/H5N1") == "methods"

    def test_mapping_rate_via_context(self):
        assert classify("Depth achieved", context="mapping rate 92%") == "methods"

    def test_star_aligner(self):
        assert classify("the STAR aligner was used with default settings") == "methods"


class TestInfectionClassification:
    def test_mortality(self):
        assert classify("Mortality reached 85% in infected chickens") == "infection"

    def test_shedding(self):
        assert classify("Viral shedding detected for 10 days post infection") == "infection"

    def test_fold_change(self):
        assert classify("log2 fold change of IFIT5 was 4.2 at 24h post infection") == "infection"

    def test_deg_count(self):
        assert classify("484 genes were differentially expressed") == "infection"

    def test_transmission(self):
        assert classify("Transmission rate between cage mates was 33%") == "infection"


class TestGarbageRoles:
    def test_bold_soup(self):
        role = "**ISG12-2** **JUN** **IRF7** **IRG1** **ISG12-2** H9N2 log2 fold change"
        assert is_garbage_role(role)

    def test_gene_list_dump(self):
        role = ("3L2 CXCLi1 CXCR1 CXCR4 CXCLi1 EGR1 FKBP5 GBP GCH1 IFIT5 IFITM1 "
                "IFITM3 IFITM5 CXCR1 CXCR4 GBP GCH1 H3N1 log2 fold c")
        assert is_garbage_role(role)

    def test_number_grid(self):
        assert is_garbage_role("LIPI LITAF LYG2 LYZ 8 6 4 2 0 -2 -4 -6")

    def test_real_role_ok(self):
        assert not is_garbage_role("Encodes interferon-induced RNA sensor upregulated after H5N1 infection")

    def test_empty_role_ok(self):
        assert not is_garbage_role("")


class TestGarbageFindings:
    def test_truncated_fragment(self):
        assert is_garbage_finding("s** Our study highlights the complex interplay")

    def test_bold_soup(self):
        assert is_garbage_finding("**A** **B** **C** **D** **E** results shown")

    def test_number_grid(self):
        assert is_garbage_finding("values plotted 8 6 4 2 0 across groups")

    def test_real_finding_ok(self):
        assert not is_garbage_finding("Mortality was 60% in the H5N1 group versus 0% in controls")
