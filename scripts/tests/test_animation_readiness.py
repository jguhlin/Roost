#!/usr/bin/env python3
"""Targeted validation tests for the animation-readiness corrections (2026-11-10).

Guards the specific scientific/data-consistency fixes made for the Roost
animation project. These are deliberately narrow: each test pins one
corrected fact or one canonical definition documented in
docs/animation/scientific_readiness_report.md.

Run: pixi run python -m pytest scripts/tests/test_animation_readiness.py -v
     (or plain `python scripts/tests/test_animation_readiness.py`)
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import polars as pl  # noqa: E402

# ---------------------------------------------------------------- helpers


def load_json(p):
    return json.loads((ROOT / p).read_text())


def read_parquet(p):
    return pl.read_parquet(ROOT / p)


RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, "PASS", ""))
        print(f"  PASS  {name}")
    except AssertionError as e:
        RESULTS.append((name, "FAIL", str(e)[:200]))
        print(f"  FAIL  {name}: {e}")
    except Exception as e:  # noqa: BLE001
        RESULTS.append((name, "ERROR", f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


# ---------------------------------------------------- 1. Barber 2010 record

BARBER = {
    "title": "Association of RIG-I with innate immunity of ducks to influenza",
    "doi": "10.1073/pnas.1001755107",
    "journal": "Proc Natl Acad Sci U S A",
    "pmid": 20308570,
}


def t_barber_record():
    md = load_json("data/papers/records/barber2010.json")["metadata"]
    assert md["title"] == BARBER["title"], md["title"]
    assert md["doi"] == BARBER["doi"], md["doi"]
    assert md["journal"] == BARBER["journal"], md["journal"]
    # the unsupported 'pseudogene' CLAIM must be gone (the correction note
    # itself may legitimately mention the removed wording)
    assert "carry a non-functional" not in md["summary"].lower(), "pseudogene claim still presented as fact"
    assert "_meta_correction" in md, "correction provenance note missing"
    assert "may be absent" in md["summary"], "summary must match the paper's wording"


def t_barber_web_twin():
    papers = load_json("web/public/data/papers.json")["papers"]
    p = next(x for x in papers if x["id"] == "barber2010")
    assert p["doi"] == BARBER["doi"], p["doi"]
    assert p["title"] == BARBER["title"], p["title"]
    assert "carry a non-functional" not in p["summary"].lower()


# --------------------------------------- 2. detection counts (records vs animals)

def t_detection_records_column():
    df = read_parquet("data/species_profiles_detected.parquet")
    assert "detection_records" in df.columns, "detection_records missing"
    ch = df.filter(pl.col("scientific_name") == "Gallus gallus")
    assert ch.height == 1
    rec = int(ch["detection_records"][0])
    aff = int(ch["detection_count"][0])
    # chicken: ~314 surveillance records vs ~182M animals affected
    assert 250 <= rec <= 400, f"chicken detection_records={rec} (expected record count)"
    assert aff > 1_000_000, f"chicken detection_count={aff} (animals affected should be huge)"


def t_species_index_det_sane():
    idx = load_json("web/public/data/species_index.json")
    det_max = max((int(r.get("det") or 0)) for r in idx)
    # surveillance records are bounded by total rows in detections_merged (~45k)
    assert det_max < 5_000, f"species_index det max={det_max} — flock-size sum leaked again"
    ch = next(r for r in idx if r["sci"] == "Gallus gallus")
    assert 250 <= int(ch["det"]) <= 400, f"chicken det={ch['det']}"


def t_detection_count_consumers_use_records():
    # every artifact that surfaces "detections" must carry record counts,
    # not animals-affected sums
    phy = load_json("web/public/data/phylogeny.json")["metadata"]
    mx = max((v.get("detection_count") or 0) for v in phy.values())
    assert mx < 5_000, f"phylogeny metadata detection_count max={mx} (flock sizes)"
    assert phy["Gallus_gallus"]["detection_count"] == 314
    assert phy["Anas_platyrhynchos"]["detection_count"] == 1838
    br = load_json("web/public/data/data_lit_bridges.json")["species"]["data_no_literature"]
    assert br and "det_records" in br[0], "bridges must use det_records"
    assert all(float(r["det_records"]) < 5_000 for r in br)


def t_host_competence_synced_with_detections():
    det = read_parquet("web/public/data/detections.parquet")
    hc = load_json("web/public/data/host_competence.json")
    by = {s["species"]: s for s in hc["species"]}
    for sci in ("Anas platyrhynchos", "Gallus gallus"):
        # host_competence counts DATED records only (builder filters
        # date_iso not null) — raw parquet may hold a few undated rows on
        # top; both definitions are documented in the readiness report.
        n_dated = det.filter((pl.col("scientific_name") == sci)
                             & pl.col("date_iso").is_not_null()).height
        n_hc = (by[sci].get("detections") or {}).get("count")
        assert n_hc == n_dated, (
            f"{sci}: host_competence={n_hc} vs dated detections.parquet={n_dated} (stale artifact)")


# --------------------------------------------- 3. kākāpō spelling unification

def t_kakapo_resolvable_everywhere():
    sus = load_json("web/public/data/species_susceptibility.json")["species"]
    keys = {s["species"].lower() for s in sus}
    assert "strigops habroptila" in keys, (
        "susceptibility v2 not keyed by canonical spelling; "
        f"found: {[k for k in keys if 'strigops' in k]}")
    e = next(s for s in sus if s["species"].lower() == "strigops habroptila")
    assert e["class"] == "unevaluated", e["class"]
    # index + tree both use habroptila
    idx = load_json("web/public/data/species_index.json")
    assert any(r["sci"] == "Strigops habroptila" for r in idx)
    nw = load_json("web/public/data/phylogeny.json")["newick"]
    assert "Strigops_habroptila" in nw, "kākāpō missing from BirdTree newick (spelling drift)"


# ------------------------------------------- 4. presence counts & units canonical

def t_presence_counts_definitions():
    raw = read_parquet("data/genes/gene_presence_v2.parquet")
    btn = load_json("web/public/data/by_the_numbers.json")
    cat = load_json("web/public/data/gene_catalogue.json")
    web = read_parquet("web/public/data/gene_presence.parquet")
    # by_the_numbers counts raw gene×assembly rows
    assert btn["genomics"]["presence_calls"] == raw.height, (
        f"by_the_numbers {btn['genomics']['presence_calls']} != raw {raw.height}")
    # web twin: best call per (species, gene). The catalogue header counts
    # canonical_by_key BEFORE the D111 subspecies→binomial rollup, so it is
    # ≥ the shipped parquet rows; species universes must match exactly.
    assert cat["total_gene_calls"] >= web.height, (
        f"catalogue {cat['total_gene_calls']} < web parquet {web.height}")
    assert cat["total_species"] == web["species"].n_unique(), (
        f"catalogue species {cat['total_species']} != parquet "
        f"{web['species'].n_unique()}")


def t_web_presence_carries_confidence():
    web = read_parquet("web/public/data/gene_presence.parquet")
    assert "conf" in web.columns and "searchability" in web.columns, web.columns
    nf = web.filter(pl.col("status") == "NOT_FOUND")
    vals = set(nf["conf"].drop_nulls().to_list())
    assert vals <= {"high", "medium", "low"}, vals


# ------------------------------------- 5. genomic interpretation guards (DDX58/IFITM3)

GALLIFORM_FAMILIES = {"Phasianidae", "Odontophoridae", "Numididae", "Cracidae", "Megapodiidae"}


def _species_families():
    sm = read_parquet("data/orthofinder/species_map.parquet")
    return dict(zip(sm["sci_name"].to_list(), sm["family"].to_list()))


def t_ddx58_high_confidence_absences_are_gamebirds():
    df = read_parquet("data/genes/gene_presence_v2.parquet")
    nf = df.filter(
        (pl.col("gene_symbol") == "DDX58")
        & (pl.col("status_level") == "E2_searched_not_found")
        & (pl.col("absence_confidence") == "high"))
    spp = nf["species"].unique().to_list()
    assert len(spp) >= 30, f"only {len(spp)} high-confidence DDX58 absences"
    fam = _species_families()
    non_gamebird = [s for s in spp if fam.get(s) not in GALLIFORM_FAMILIES]
    # species outside the OrthoFinder set can't be family-checked; only
    # flag ones we CAN resolve
    resolvable_offenders = [s for s in non_gamebird if s in fam]
    assert not resolvable_offenders, f"non-gamebird hi-conf DDX58 absences: {resolvable_offenders}"


def t_ddx58_basal_galliforms_retain():
    df = read_parquet("data/genes/gene_presence_v2.parquet")
    order = {"E5_annotated": 4, "E4_unannotated_found": 3, "E3_fragment": 2, "E2_searched_not_found": 1}
    for sci, expected_min in (("Penelope pileata", 3), ("Alectura lathami", 3)):
        sub = df.filter((pl.col("gene_symbol") == "DDX58") & (pl.col("species") == sci))
        assert sub.height >= 1, f"{sci} missing from presence data"
        best = max(order[s] for s in sub["status_level"].to_list())
        assert best >= expected_min, f"{sci} DDX58 degraded: {sub['status_level'].to_list()}"


def t_ifitm3_zero_high_confidence_absences():
    df = read_parquet("data/genes/gene_presence_v2.parquet")
    nf_hi = df.filter(
        (pl.col("gene_symbol") == "IFITM3")
        & (pl.col("status_level") == "E2_searched_not_found")
        & (pl.col("absence_confidence") == "high"))
    assert nf_hi.height == 0, (
        f"{nf_hi.height} high-confidence IFITM3 absences appeared — "
        "low-confidence non-detections must never be presented as established losses")


# ------------------------------------------------- 6. ANP32A denominators

def t_anp32a_denominators():
    d = load_json("web/public/data/anp32/comparison.json")
    PALAEO = {"Struthioniformes", "Rheiformes", "Casuariiformes", "Apterygiformes", "Tinamiformes"}
    comp, pal, pal_zero, neo, neo33, neo0, neo_other = 0, 0, 0, 0, 0, 0, 0
    for k, v in d["species"].items():
        A = v.get("A") or {}
        if not A or v.get("group") != "Aves" or A.get("frag"):
            continue
        comp += 1
        il = A.get("insert_len") or 0
        if v.get("order") in PALAEO:
            pal += 1
            pal_zero += (il == 0)
        else:
            neo += 1
            neo33 += (il == 33)
            neo0 += (il == 0)
            neo_other += (il not in (0, 33))
    assert comp == pal + neo, "palaeognath set must be disjoint + exhaustive"
    assert pal == 12 and pal_zero == 12, f"palaeognaths={pal}, zero-insert={pal_zero}"
    # the canonical caption numbers
    assert neo33 == 316 and neo0 == 18 and neo_other == 41, (
        f"neognaths 33/0/other = {neo33}/{neo0}/{neo_other}")
    assert comp == 387, f"complete sequences drifted: {comp}"


# --------------------------------------- 7. UI: susceptibility-axis + confidence labels

def t_i18n_axis_keys_present():
    src = (ROOT / "web/src/lib/stores/i18n.svelte.js").read_text()
    for key in ("susc.legacy.tip", "susc.legacy.short", "species.card.detections.tip",
                "phylo.legend.nf.hi", "phylo.legend.nf.lo", "phylo.absent.highconf"):
        assert f"'{key}':" in src, f"i18n key {key} missing from en dict"


def t_phylogeny_confidence_split():
    src = (ROOT / "web/src/lib/components/phylogeny/PhyloTree.svelte").read_text()
    assert "NOT_FOUND_HI" in src and "#fca5a5" in src, "confidence colour split missing"
    ph = (ROOT / "web/src/routes/Phylogeny.svelte").read_text()
    assert "NOT_FOUND_HI" in ph and "not_found_hi" in ph


def t_susceptibility_vocabularies_distinct_axes():
    v1 = read_parquet("web/public/data/susceptibility.parquet")
    v2 = load_json("web/public/data/species_susceptibility.json")
    assert "methodology" in v2 and "permissiveness" in str(v2["methodology"]).lower()
    # the two artifacts must disagree on mallard BY DESIGN (severity vs
    # permissiveness axes) — pin the disagreement so nobody "fixes" one
    # onto the other
    m1 = v1.filter(pl.col("scientific_name") == "Anas platyrhynchos")
    m2 = next(s for s in v2["species"] if s["species"] == "Anas platyrhynchos")
    assert m1["susceptibility_class"][0] == "highly_tolerant"
    assert m2["class"] == "highly_susceptible" and m2["severity"] is not None
    # v2 must label its score as permissiveness (not tolerance of infection)
    assert m2["permissiveness"] >= 75


# ------------------------------------------------ 8. animation exports integrity

def t_animation_exports():
    A = ROOT / "docs/animation"
    for f in ("journey1_species.json", "journey2_literature.json", "journey3_ddx58.json"):
        d = load_json(f"docs/animation/{f}")
        assert isinstance(d, dict) and d
    j1 = load_json("docs/animation/journey1_species.json")
    assert "Anas platyrhynchos" in j1 and "Strigops habroptila" in j1
    assert j1["Strigops habroptila"]["detections"]["n"] == 0
    assert j1["Strigops habroptila"]["susceptibility_v2"]["class"] == "unevaluated"
    j3 = load_json("docs/animation/journey3_ddx58.json")
    assert j3["literature"]["key_reference"]["doi"] == BARBER["doi"], (
        "journey3 still cites the dead Barber DOI")
    rows = list(csv.DictReader(open(A / "ddx58_calls_galloanserae.csv")))
    assert len(rows) == 24
    nf = [r for r in rows if r["ddx58_status"] == "NOT_FOUND"]
    assert all(r["family"] in GALLIFORM_FAMILIES for r in nf)
    anp = list(csv.DictReader(open(A / "anp32a_insert_palaeognaths.csv")))
    assert len(anp) == 387
    pal = [r for r in anp if r["palaeognath"] == "True"]
    assert len(pal) == 12 and all(r["anp32a_insert_len"] == "0" for r in pal)
    for f, n_tips in (("subtree_rigI_galloanserae.newick", 24),
                      ("subtree_palaeognaths.newick", 15)):
        s = (A / f).read_text().strip()
        assert s.endswith(";")
        depth = 0
        for ch in s:
            depth += (ch == "(") - (ch == ")")
            assert depth >= 0
        assert depth == 0
        tips = set(re.findall(r"([A-Za-z_]+):[0-9]", s))
        assert len(tips) == n_tips, f"{f}: {len(tips)} tips != {n_tips}"


# ------------------------------------------------------------------ runner

def main():
    tests = [
        ("barber2010 record corrected", t_barber_record),
        ("barber2010 web twin corrected", t_barber_web_twin),
        ("detection_records column (records vs animals)", t_detection_records_column),
        ("species_index det sane (no flock sizes)", t_species_index_det_sane),
        ("detection-count consumers use records (tree/bridges)", t_detection_count_consumers_use_records),
        ("host_competence synced with detections", t_host_competence_synced_with_detections),
        ("kākāpō spelling resolvable everywhere", t_kakapo_resolvable_everywhere),
        ("presence counts: canonical units", t_presence_counts_definitions),
        ("web presence carries confidence ladder", t_web_presence_carries_confidence),
        ("DDX58 hi-conf absences are gamebirds", t_ddx58_high_confidence_absences_are_gamebirds),
        ("DDX58 basal galliforms retain gene", t_ddx58_basal_galliforms_retain),
        ("IFITM3 zero high-confidence absences", t_ifitm3_zero_high_confidence_absences),
        ("ANP32A denominators (387 = 12 palaeo + 375 neo)", t_anp32a_denominators),
        ("i18n axis/confidence keys present", t_i18n_axis_keys_present),
        ("phylogeny confidence colour split", t_phylogeny_confidence_split),
        ("susceptibility axes distinct by design", t_susceptibility_vocabularies_distinct_axes),
        ("animation exports integrity", t_animation_exports),
    ]
    print("=" * 72)
    print("Roost animation-readiness validation")
    print("=" * 72)
    for name, fn in tests:
        check(name, fn)
    failed = [r for r in RESULTS if r[1] != "PASS"]
    print("-" * 72)
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    if failed:
        print("FAILED:")
        for name, status, msg in failed:
            print(f"  [{status}] {name}: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
