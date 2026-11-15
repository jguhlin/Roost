"""Species-resolution guards (2026-11-07, the curlew lesson).

A genus-only or Unspecified-style record must NEVER carry a binomial
scientific_name. These tests pin the resolver + the ingest guard against
the real shapes that shipped phantom species (Numenius→americanus etc.).
"""
import sys
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "papers"))

from harmonize_species import (  # noqa: E402
    build_name_index, harmonize_species_name, is_unidentified, load_taxonomy,
)


def _index():
    return build_name_index(load_taxonomy())


# --- is_unidentified: the uncertain-label vocabulary -----------------------
@pytest.mark.parametrize("label", [
    "Unspecified Curlew", "unspecified buzzard", "Undetermined Gull",
    "Not specified swan", "unknown raptor", "Unidentified Bird",
])
def test_uncertain_labels_are_unidentified(label):
    assert is_unidentified(label)


@pytest.mark.parametrize("label", [
    "Curlew", "long-billed curlew", "Numenius arquata", "Black Swan",
])
def test_specific_labels_are_not_unidentified(label):
    assert not is_unidentified(label)


# --- the resolver: genus-only Latin never yields a species -----------------
def test_genus_only_latin_resolves_to_nothing():
    idx = _index()
    for genus in ["Numenius", "Buteo", "Cygnus", "Anser", "Corvus",
                  "Columba", "Cepphus", "Fulmarus"]:
        assert harmonize_species_name(genus, idx) is None, genus


def test_unspecified_raw_never_resolves():
    idx = _index()
    for raw in ["Unspecified Curlew", "Unspecified Buzzard",
                "Unspecified Swan", "Unspecified Goose"]:
        assert harmonize_species_name(raw, idx) is None, raw


def test_real_species_still_resolve():
    idx = _index()
    assert harmonize_species_name("Numenius arquata", idx) is not None
    assert harmonize_species_name("Cygnus atratus", idx) is not None
    assert harmonize_species_name("Curlew", idx) is not None  # common map


# --- the ingest hard guard -------------------------------------------------
def _frame(rows):
    return pl.DataFrame(rows, schema={
        "species_raw": pl.Utf8, "scientific_name": pl.Utf8,
        "scientific_name_parsed": pl.Utf8}, strict=False)


def test_guard_passes_clean_rows(capsys):
    from ingest_detections import apply_uncertainty_policy
    df = apply_uncertainty_policy(_frame([
        {"species_raw": "Curlew", "scientific_name": "Numenius arquata",
         "scientific_name_parsed": "Numenius arquata"},
        {"species_raw": "Unspecified Curlew", "scientific_name": None,
         "scientific_name_parsed": "Numenius"},
    ]))
    # genus home populated for the uncertain row
    assert df.filter(pl.col("species_raw") == "Unspecified Curlew")["genus"][0] == "Numenius"
    assert df.filter(pl.col("species_raw") == "Curlew")["genus"][0] is None


def test_guard_fails_on_unspecified_with_binomial():
    from ingest_detections import apply_uncertainty_policy
    with pytest.raises(SystemExit, match="INGEST GUARD FAILED"):
        apply_uncertainty_policy(_frame([
            {"species_raw": "Unspecified Curlew",
             "scientific_name": "Numenius americanus",
             "scientific_name_parsed": "Numenius"},
        ]))


def test_guard_fails_on_single_word_scientific_name():
    from ingest_detections import apply_uncertainty_policy
    with pytest.raises(SystemExit, match="INGEST GUARD FAILED"):
        apply_uncertainty_policy(_frame([
            {"species_raw": "Unspecified Buzzard",
             "scientific_name": "Buteo",
             "scientific_name_parsed": "Buteo"},
        ]))


def test_guard_genus_from_binomial_behind_unspecified():
    """DEFRA ships 'Unspecified Guillemot' + full Latin 'Cepphus grylle' —
    species nulled (guard), genus preserved (home)."""
    from ingest_detections import apply_uncertainty_policy
    df = apply_uncertainty_policy(_frame([
        {"species_raw": "Unspecified Guillemot", "scientific_name": None,
         "scientific_name_parsed": "Cepphus grylle"},
    ]))
    assert df["genus"][0] == "Cepphus"


def test_genus_never_set_for_resolved_species_with_blob_parsed():
    """EMPRES-i parsed strings are family-order hyphen blobs
    ('Laridae-charadriiformes') — not genera. Species resolves from the
    parenthetical; genus must stay null."""
    from ingest_detections import apply_uncertainty_policy
    df = apply_uncertainty_policy(_frame([
        {"species_raw": "Black-legged Kittiwake (Rissa tridactyla)",
         "scientific_name": "Rissa tridactyla",
         "scientific_name_parsed": "Laridae-charadriiformes"},
    ]))
    assert df["genus"][0] is None
    assert df["scientific_name"][0] == "Rissa tridactyla"
