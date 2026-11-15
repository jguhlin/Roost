#!/usr/bin/env python3
"""Layer C — host competence matrix (SPREAD_MODEL.md Phase 7).

Per-species aggregation of everything the corpus says about a host's role
in H5N1 spread, with explicit provenance per block:

  PAPER_EXTRACTED  paper_species_traits.parquet — LLM-extracted,
                   quote-grounded, verify-verdicted rows (778 rows /
                   168 species). Statistics use confirmed +
                   paraphrased-supported rows only; unsupported/
                   contradicted rows are counted and reported, never used.
  MODELED          susceptibility.parquet — composite susceptibility
                   scores (mortality + RIG-I inference + genome quality).
  MEASURED         detections — surveillance stamps per species.

Output: data/model/host_competence.json
        (+ twin web/public/data/host_competence.json)
Rerun after trait extraction passes, susceptibility rebuilds, or
detections rebuilds.

Usage: pixi run python scripts/model/build_host_competence.py
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
TRAITS = ROOT / "data" / "papers" / "paper_species_traits.parquet"
SUSCEPT = ROOT / "web" / "public" / "data" / "susceptibility.parquet"
SPECIES = ROOT / "web" / "public" / "data" / "species.parquet"
DET = ROOT / "web" / "public" / "data" / "detections.parquet"
OUT = ROOT / "data" / "model" / "host_competence.json"
OUT_WEB = ROOT / "web" / "public" / "data" / "host_competence.json"

USABLE = ["confirmed", "paraphrased-supported"]  # verify verdicts usable in stats
MAX_QUOTES = 2  # evidence sample per species


def median(xs: list[float]) -> float | None:
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    m = n // 2
    return xs[m] if n % 2 else (xs[m - 1] + xs[m]) / 2


SPREAD = ROOT / "data" / "papers" / "paper_spread.parquet"


# Curated synonyms: common/domestic labels the taxonomy resolver can't
# reach. Scientific names here don't need to exist in species.parquet —
# they create competence entries on their own (taxonomy lookups tolerate
# the miss). Group labels ("wild birds", "waterfowl", "ducks" as a class)
# are deliberately NOT mapped.
SYNONYMS = {
    "dairy cattle": "Bos taurus", "dairy cow": "Bos taurus",
    "cow": "Bos taurus", "cattle": "Bos taurus",
    "domestic cattle": "Bos taurus",
    "domestic duck": "Anas platyrhynchos",
    "cat": "Felis catus", "domestic cat": "Felis catus",
    "red fox": "Vulpes vulpes", "fox": "Vulpes vulpes",
    "hen": "Gallus gallus", "chicken": "Gallus gallus",
    "domestic chicken": "Gallus gallus",
    "pig": "Sus scrofa", "swine": "Sus scrofa", "domestic pig": "Sus scrofa",
    "dairy worker": "Homo sapiens", "human": "Homo sapiens",
    "dog": "Canis lupus familiaris", "domestic dog": "Canis lupus familiaris",
    "mink": "Neogale vison", "american mink": "Neogale vison",
    "domestic goose": "Anser anser",
    "domestic turkey": "Meleagris gallopavo", "turkey": "Meleagris gallopavo",
    "south american sea lion": "Otaria flavescens",
    "elephant seal": "Mirounga leonina", "harbor seal": "Phoca vitulina",
    "horse": "Equus caballus", "raccoon dog": "Nyctereutes procyonoides",
    "domestic pigeon": "Columba livia", "pigeon": "Columba livia",
    "mute swan": "Cygnus olor", "whooper swan": "Cygnus cygnus",
}


def _norm_name(s: str) -> str:
    s = (s or "").strip().lower()
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]  # crude plural fold: chickens -> chicken
    return s


_GENOTYPE = re.compile(r"\b([BD]1\.1|[BD]3\.\d+)\b")
_CLADE = re.compile(r"2\.3\.\d+(?:\.\d+)?")


def _norm_clade(s: str) -> str:
    """Collapse clade+genotype variants: '2.3.4.4b genotype B3.13' ->
    '2.3.4.4b/B3.13'; bare genotype -> itself; junk -> stripped."""
    s = s or ""
    g = _GENOTYPE.search(s)
    c = _CLADE.search(s)
    if c and g:
        return f"{c.group(0)}b/{g.group(1)}"
    if g:
        return g.group(1)
    if c:
        return f"{c.group(0)}b"
    return s.strip()


def merge_llm_roles(species_out: list[dict]) -> tuple[int, int, int]:
    """Merge llm_extract_spread host_roles items into competence entries.

    Species strings from the LLM are common names ("dairy cows",
    "mallards"), scientific names, or unresolvable group labels ("wild
    birds"). Resolve via species.parquet common/scientific names; group
    labels are skipped and counted. Returns (merged, unresolved, new).
    """
    import polars as pl

    if not SPREAD.exists():
        return 0, 0, 0
    tax = pl.read_parquet(SPECIES).select(
        "scientific_name", "common_name").drop_nulls(subset=["scientific_name"])
    resolver: dict[str, str] = {}
    for r in tax.iter_rows(named=True):
        resolver[_norm_name(r["scientific_name"])] = r["scientific_name"]
        if r.get("common_name"):
            resolver.setdefault(_norm_name(r["common_name"]),
                                r["scientific_name"])

    hr = pl.read_parquet(SPREAD).filter(pl.col("section") == "host_roles")
    agg: dict[str, dict] = {}
    unresolved = 0
    for r in hr.iter_rows(named=True):
        it = json.loads(r["payload"])
        raw = (it.get("species") or "").strip()
        sci = (resolver.get(_norm_name(raw))
               or SYNONYMS.get(_norm_name(raw)))
        if not sci:
            unresolved += 1
            continue
        a = agg.setdefault(sci, {"roles": {}, "clades": set(),
                                 "papers": set(), "grounded": 0, "items": 0})
        a["items"] += 1
        a["papers"].add(r["paper_id"])
        if r.get("quote_in_text"):
            a["grounded"] += 1
        for role in it.get("roles") or []:
            a["roles"][role] = a["roles"].get(role, 0) + 1
        if it.get("clade"):
            a["clades"].add(_norm_clade(it["clade"]))

    by_species = {e["species"]: e for e in species_out}
    new = 0
    for sci, a in sorted(agg.items()):
        entry = by_species.get(sci)
        if entry is None:
            entry = {"species": sci, "papers": {"count": 0},
                     "records": {"total": 0, "by_kind": {}},
                     "mortality_pct": None, "mortality_by_clade": None,
                     "shedding_days": None}
            species_out.append(entry)
            by_species[sci] = entry
            new += 1
        entry["llm_roles"] = {
            "roles": {k: v for k, v in sorted(a["roles"].items(),
                                              key=lambda kv: -kv[1])},
            "clades": sorted(a["clades"]),
            "papers": len(a["papers"]),
            "grounded": a["grounded"], "items": a["items"],
        }
    species_out.sort(key=lambda e: (-e["papers"]["count"], e["species"]))
    return len(agg), unresolved, new


def main() -> None:
    t = pl.read_parquet(TRAITS).filter(pl.col("species_norm").is_not_null())
    sus = pl.read_parquet(SUSCEPT)
    det = (pl.read_parquet(DET)
           .filter(pl.col("date_iso").is_not_null()
                   & pl.col("scientific_name").is_not_null()))
    det_by_species = det.group_by("scientific_name").agg(
        pl.len().alias("n"), pl.col("date_iso").min().alias("first"))
    sus_by_species = {r["scientific_name"]: r
                      for r in sus.iter_rows(named=True)}

    species_out = []
    for (sp,) in t.select("species_norm").unique().iter_rows():
        grp = t.filter(pl.col("species_norm") == sp)
        rows = list(grp.iter_rows(named=True))
        usable = [r for r in rows if r["verify_verdict"] in USABLE]
        excluded = len(rows) - len(usable)

        kinds: dict[str, int] = {}
        for r in rows:
            k = r["kind"] or "unknown"
            kinds[k] = kinds.get(k, 0) + 1

        mort = []
        for r in usable:
            nt, nd = r["n_total"], r["n_dead"]
            if nt and nd is not None and nt > 0 and nd <= nt:
                mort.append(round(100.0 * nd / nt, 1))
        # per-clade competence (the comparability axis researchers ask for)
        by_clade: dict[str, list[float]] = {}
        for r in usable:
            nt, nd, cl = r["n_total"], r["n_dead"], (r["clade"] or "").strip()
            if cl and nt and nd is not None and nt > 0 and nd <= nt:
                by_clade.setdefault(cl, []).append(round(100.0 * nd / nt, 1))
        clade_mort = {cl: {"median": median(vs), "studies": len(vs)}
                      for cl, vs in sorted(by_clade.items())} or None
        shedding = sorted({r["shedding_days"] for r in usable
                           if r["shedding_days"] is not None})
        clades = sorted({r["clade"].strip() for r in usable
                         if r["clade"] and r["clade"].strip()})
        papers = sorted({r["paper_id"] for r in rows})
        quotes = [r["verify_quote"] for r in
                  sorted((r for r in usable if r.get("quote_in_text")
                          and r.get("verify_quote")),
                         key=lambda r: -(r["n_total"] or 0))][:MAX_QUOTES]

        entry = {
            "species": sp,
            "papers": {"count": len(papers), "ids": papers},
            "records": {"total": len(rows), "by_kind": kinds,
                        "excluded_unverified": excluded},
            "mortality_pct": ({
                "median": median(mort), "min": min(mort), "max": max(mort),
                "studies": len(mort)} if mort else None),
            "mortality_by_clade": clade_mort,
            "shedding_days": ({"values": shedding, "studies":
                               len({r["paper_id"] for r in usable
                                    if r["shedding_days"] is not None})}
                              if shedding else None),
            "clades": clades,
            "evidence_quotes": quotes,
            "provenance": "PAPER_EXTRACTED (quote-grounded, verify-verdicted)",
        }

        s = sus_by_species.get(sp)
        if s:
            entry["susceptibility"] = {
                "score": s["susceptibility_score"],
                "class": s["susceptibility_class"],
                "confidence": s["confidence"],
                "has_rigi": s["has_rigi"],
                "provenance": "MODELED (composite)",
            }
        d = det_by_species.filter(pl.col("scientific_name") == sp) if sp else det_by_species.head(0)
        if d.height:
            r0 = d.row(0, named=True)
            entry["detections"] = {
                "count": r0["n"], "first": str(r0["first"]),
                "provenance": "MEASURED (surveillance)",
            }
        species_out.append(entry)

    species_out.sort(key=lambda e: (-e["papers"]["count"], e["species"]))

    # ---- LLM host_roles merge (v2 extraction; roles are the one thing
    # deterministic data can't supply) ----
    roles_merged, roles_unresolved, roles_new_species = merge_llm_roles(
        species_out)

    # ---- coverage-gap matrix: species x evidence-type, holes lit up ----
    # (the researcher's "what should we study next" grid)
    taxonomy = (pl.read_parquet(SPECIES)
                .select("scientific_name", "genus", "family", "order"))
    tax = {r["scientific_name"]: r for r in taxonomy.iter_rows(named=True)}
    sus_species = {s for s in sus_by_species if s}
    evidence_types = ["mortality", "shedding", "field_outbreak",
                      "experimental", "surveillance", "serology",
                      "susceptibility", "detections", "llm_roles"]
    entries_by_species = {e["species"]: e for e in species_out}
    gap_rows = []
    for sp in sorted(set(entries_by_species) | sus_species):
        e = entries_by_species.get(sp)
        kinds = (e or {}).get("records", {}).get("by_kind", {})
        ev = {
            "mortality": bool(e and e["mortality_pct"]),
            "shedding": bool(e and e["shedding_days"]),
            "field_outbreak": kinds.get("field_outbreak", 0) > 0,
            "experimental": kinds.get("experimental_challenge", 0) > 0,
            "surveillance": kinds.get("surveillance", 0) > 0,
            "serology": kinds.get("serology", 0) > 0,
            "susceptibility": sp in sus_species,
            "detections": bool(e and e.get("detections")),
            "llm_roles": bool(e and e.get("llm_roles")),
        }
        gap_rows.append({"species": sp, "evidence": ev,
                         "holes": sum(1 for v in ev.values() if not v)})

    # ---- taxonomic proxy rollup for data-poor species ----
    # (the conservationist's answer for "my species has zero direct data")
    thin = [e["species"] for e in species_out if e["papers"]["count"] < 2]
    rich = {e["species"]: e for e in species_out if e["papers"]["count"] >= 2}
    proxies = []
    for sp in thin:
        t = tax.get(sp)
        if not t:
            continue
        for level in ("genus", "family", "order"):
            mates = [r for r, rt in ((r, tax.get(r)) for r in rich)
                     if rt and rt[level] and rt[level] == t[level]]
            if mates:
                m_vals = [v for m in mates
                          for v in ([rich[m]["mortality_pct"]["median"]]
                                    if rich[m]["mortality_pct"] else [])]
                proxies.append({
                    "species": sp, "level": level,
                    "donors": sorted(mates),
                    "mortality_median": median(m_vals),
                    "donor_papers": sum(rich[m]["papers"]["count"]
                                        for m in mates),
                })
                break

    n_mort = sum(1 for e in species_out if e["mortality_pct"])
    n_shed = sum(1 for e in species_out if e["shedding_days"])
    n_sus = sum(1 for e in species_out if e.get("susceptibility"))
    n_det = sum(1 for e in species_out if e.get("detections"))

    doc = {
        "version": 1,
        "generated": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "traits": str(TRAITS.relative_to(ROOT)),
            "susceptibility": str(SUSCEPT.relative_to(ROOT)),
            "detections": str(DET.relative_to(ROOT)),
        },
        "provenance_ladder": {
            "PAPER_EXTRACTED": "LLM extraction, quote-grounded, "
                               "verify-verdicted; stats from usable rows only",
            "MODELED": "composite score (mortality + RIG-I inference)",
            "MEASURED": "surveillance records",
        },
        "species": species_out,
        "llm_roles_merge": {
            "species_with_roles": roles_merged,
            "new_species_added": roles_new_species,
            "unresolved_labels": roles_unresolved,
            "provenance": "PAPER_EXTRACTED (llm_extract_spread host_roles, "
                          "quote-grounded)",
        },
        "coverage": {
            "evidence_types": evidence_types,
            "gap_matrix": gap_rows,
            "no_direct_data": sorted(sus_species - set(entries_by_species)),
            "note": "holes = evidence types with no data; the grid is the "
                    "research-gap view",
        },
        "proxies": {
            "for_thin_species": proxies,
            "note": "nearest taxonomic relatives with >= 2 evidence papers "
                    "(genus -> family -> order fallback); marked proxy, "
                    "never presented as direct evidence",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    OUT_WEB.write_text(json.dumps(doc, ensure_ascii=False, indent=1))

    print(f"{len(species_out)} species: mortality {n_mort}, shedding "
          f"{n_shed}, susceptibility {n_sus}, detections {n_det}")
    print(f"llm_roles merged: {roles_merged} species "
          f"({roles_new_species} new, {roles_unresolved} unresolved labels)")
    clade_strat = sum(1 for e in species_out if e["mortality_by_clade"])
    print(f"per-clade mortality: {clade_strat} species stratified; "
          f"gap matrix: {len(gap_rows)} species x {len(evidence_types)} "
          f"evidence types; proxies: {len(proxies)} thin species rolled "
          f"up to relatives")
    for e in species_out[:12]:
        m, s = e["mortality_pct"], e["shedding_days"]
        mort_s = f"{m['median']:.0f}%({m['studies']})" if m else "—"
        shed_s = str(s["values"]) if s else "—"
        print(f"  {e['species']:<28} papers={e['papers']['count']:>2} "
              f"kinds={e['records']['by_kind']} mort={mort_s} "
              f"shed={shed_s}")
    print(f"\n→ {OUT.relative_to(ROOT)}\n→ {OUT_WEB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
