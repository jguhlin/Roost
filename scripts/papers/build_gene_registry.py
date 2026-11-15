#!/usr/bin/env python3
"""Build the gene registry: every gene/concept ever implicated in the corpus.

One JSONL entry per canonical symbol (aliases + synonyms resolved via
data/papers/gene_alias_map.json), including singletons, with paper-level
linkage, species, claim tiers, and the surface forms that resolve to it.

Host-gene buckets (the two headline numbers people ask about):
  - REGISTRY TOTAL  — every host locus tracked, from literature OR the
    comparative-genomics panel (wiki corpus, UniProt/GO immune backbone)
  - STUDIED (n_studied >= 1) — at least one paper where the gene is a
    study subject; the strict "what has actually been studied" number
  The gap between them is intentional and meaningful:
  - claims/discovery-linked only — extracted into typed claims or the
    discovery log but never a study subject (mentioned as context)
  - panel-only — zero literature; searched across genomes precisely
    because nobody has studied them (the site's "genome-annotation"
    toggle is this bucket's catalogue sidecar)
  - text-only — >=3 raw text mentions, never extracted
Semantics are re-emitted each run into gene_registry.meta.json next to
the jsonl, with live bucket counts, so docs can never drift from data.

Kinds: host_gene, viral_gene, viral_subtype, mutation, mhc_allele, mirna,
       circ_rna, concept, other.

Usage: pixi run python scripts/papers/build_gene_registry.py
Output: data/papers/gene_registry.jsonl (+ .meta.json sidecar)
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
PAPERS = ROOT / "data" / "papers"
GENES = ROOT / "data" / "genes"

am = json.loads((PAPERS / "gene_alias_map.json").read_text())
AL, SYN = am.get("aliases", {}), am.get("synonyms", {})
gec = json.loads((PAPERS / "gene_evidence_counts.json").read_text())
panel = json.loads((GENES / "host_panel_v2.json").read_text())["genes"]
panel_syms = {g["symbol"] for g in panel}
tier_by_sym = {g["symbol"]: g["tier"] for g in panel}
wg = json.loads((ROOT / "web/public/data/wiki_genes.json").read_text())["genes"]
viral = {g for g, v in wg.items() if v.get("kind") == "viral"}
bb = json.loads((GENES / "avimm_uniprot_backbone.json").read_text())
uniprot_syms = {v["symbol"] for v in bb["genes"].values() if v.get("symbol")}


def resolve(t):
    t = str(t).strip()
    if not (1 < len(t) < 40):
        return None
    for probe in (t, t.upper(), t.lower()):
        h = AL.get(probe)
        if h is not None:
            return None if h == "NOT_A_GENE" else SYN.get(h, h)
    return SYN.get(t.upper(), t.upper())


def J(x):
    try:
        return json.loads(x) if isinstance(x, str) else (x or [])
    except Exception:
        return []


papers_by_gene = defaultdict(set)
species_by_gene = defaultdict(set)
mech_papers = defaultdict(set)

# corpus membership (D-45 purge hygiene): claim tables can carry orphaned
# paper ids (purged scraping artifacts, pre-rename ids); registry linkage
# must only cite papers that exist
_corpus_ids = set(pl.read_parquet(PAPERS / "papers_index.parquet")["id"].to_list())
_rename = json.loads((PAPERS / "id_rename_map.json").read_text()) \
    if (PAPERS / "id_rename_map.json").exists() else {}
_corpus_ids |= {v for v in _rename.values() if v in _corpus_ids}  # valid targets only

def canon_pid(pid):
    """paper id -> corpus id, or None if orphaned"""
    if pid in _corpus_ids:
        return pid
    r = _rename.get(pid)
    return r if r in _corpus_ids else None

# evidence classes (derived from typed-claim text/scope; taxonomy documented
# in gene_registry.meta.json bucket/evidence definitions)
import re as _re
_PERT = _re.compile(r'\b(knockout|knock-out|CRISPR|siRNA|shRNA|knockdown|overexpression|over-expression|edited|deletion mutant|rescue experiment)\b', _re.I)
_RECEP = _re.compile(r'\b(receptor binding|sialic acid receptor|alpha 2,3|2,6-linked)\b', _re.I)
_PATHO = _re.compile(r'\b(patholog|lesion|mortality|virulence|clinical signs|tissue tropism)\b', _re.I)
_SEQV = _re.compile(r'\b(mutation|variant|substitution|polymorphism|SNP|amino acid change)\b', _re.I)
_IMM = _re.compile(r'\b(interferon|cytokine|interleukin|immune response|ISG|antiviral)\b', _re.I)
evidence_classes = defaultdict(set)

for r in pl.read_parquet(PAPERS / "typed_claims.parquet").iter_rows(named=True):
    pid = canon_pid(r["paper_id"])
    if not pid:
        continue
    gs = {resolve(g) for g in J(r["genes"])} - {None}
    for g in gs:
        papers_by_gene[g].add(pid)
        species_by_gene[g].update(
            s for s in J(r["species"]) if isinstance(s, str) and " " in s)
    if gs:
        t = r["text"] or ""
        scope = r["scope"] or ""
        c = set()
        if _PERT.search(t): c.add("perturbation")
        if _RECEP.search(t): c.add("receptor_interaction")
        if _PATHO.search(t): c.add("pathology")
        if _SEQV.search(t): c.add("sequence_variation")
        if _IMM.search(t): c.add("immune_response")
        if "in vitro" in scope or "in silico" in scope: c.add("in_vitro_in_silico")
        for g in gs:
            evidence_classes[g] |= (c or {"mention_only"})
for r in pl.read_parquet(PAPERS / "paper_mechanisms.parquet").iter_rows(named=True):
    pid = canon_pid(r["paper_id"])
    if not pid:
        continue
    for a in J(r["actors"]) + J(r["targets"]):
        s = resolve(a)
        if s:
            mech_papers[s].add(pid)
for g, ps in mech_papers.items():
    papers_by_gene[g] |= ps
for line in (PAPERS / "gene_discovery.jsonl").read_text().splitlines():
    d = json.loads(line)
    pid = canon_pid(d["paper_id"])
    if not pid:
        continue
    s = resolve(d["gene"])
    if s:
        papers_by_gene[s].add(pid)
for line in (PAPERS / "gene_claims.jsonl").read_text().splitlines():
    d = json.loads(line)
    pid = canon_pid(d["paper_id"])
    if not pid:
        continue
    for rec in d.get("records", []):
        s = resolve(rec["gene"])
        if s:
            papers_by_gene[s].add(pid)

tiers = defaultdict(Counter)
for line in (PAPERS / "gene_claims.jsonl").read_text().splitlines():
    if not canon_pid(json.loads(line)["paper_id"]):
        continue
    for r in json.loads(line).get("records", []):
        s = resolve(r["gene"])
        if s:
            tiers[s][r.get("tier", "?")] += 1

surf_by_canon = defaultdict(list)
for k, v in {**AL, **SYN}.items():
    c = SYN.get(v, v)
    if c and v != "NOT_A_GENE" and k != c and len(k) < 25:
        surf_by_canon[c].append(k)

# fold panel symbols through the same resolution (panel carries legacy
# synonyms like CXCL8/IL8, PKR/EIF2AK2 and non-gene concepts like
# '28S rRNA' — folded or dropped here; panel cleanup tracked in AGENTS.md)
tier_by_folded = {}
folded_panel = set()
for g in panel:
    r = resolve(g["symbol"])
    if r and r != "NOT_A_GENE":
        folded_panel.add(r)
        tier_by_folded.setdefault(r, []).append(g["tier"])
panel_tier = {sym: min(ts) for sym, ts in tier_by_folded.items()}

curated_syms = set()
_curated_path = ROOT / "web" / "public" / "data" / "genes.json"
if _curated_path.exists():
    for _g in json.loads(_curated_path.read_text()).get("genes", []):
        curated_syms.add(_g["symbol"])

universe = set(gec) | folded_panel | set(papers_by_gene) | set(tiers) | curated_syms
# ghost filter: symbols that are synonyms of another entry and carry no
# linkage of their own are stale keys (old edge/panel vocabulary)
universe = {s for s in universe
           if not (SYN.get(s, s) != s and SYN.get(s) in universe
                   and not papers_by_gene.get(s) and not tiers.get(s))}
MUT = re.compile(r"^(HA|NA|NP|PB2|PB1|PA|NS1|M1|ANP32A|ANP32B|ANP32E)-[A-Z]?\d+[A-Z]$")
ALLELE = re.compile(r"^(BF2|BLB|BL2|BLA|B)\*|^B(2|4B|12|13|15|19|21)$|^AMME", re.I)
ACC = re.compile(r"^[A-Z]{2}\d{5,}\.\d+$")


def kind(sym):
    if sym in curated_syms and sym not in gec and sym not in folded_panel:
        return "concept"  # curated concepts like SA (sialic-acid receptors)
    if MUT.match(sym):
        return "mutation"
    if ALLELE.match(sym):
        return "mhc_allele"
    if sym in viral:
        return "viral_gene"
    if re.match(r"^(hsa-)?(gga-)?miR-?|^MIR\d", sym, re.I):
        return "mirna"
    if sym.startswith("circ"):
        return "circ_rna"
    if re.match(r"^(H\d+N\d+|H\d+|N\d+)$", sym):
        return "viral_subtype"
    if sym in folded_panel or sym in gec or sym in uniprot_syms:
        return "host_gene"
    if re.match(r"^[A-Z][A-Z0-9]{1,9}$", sym) and papers_by_gene.get(sym):
        return "host_gene"
    if " " in sym or ACC.match(sym):
        return "concept"
    return "other"


out = PAPERS / "gene_registry.jsonl"
n, kinds = 0, Counter()
with open(out, "w") as f:
    for sym in sorted(universe):
        rec = gec.get(sym, {}) if isinstance(gec.get(sym), dict) else {}
        t = tiers.get(sym, {})
        e = {
            "symbol": sym, "kind": kind(sym),
            "panel_tier": panel_tier.get(sym) or tier_by_sym.get(sym),
            "claim_tier": ("central" if t.get("central")
                           else "supporting" if t.get("supporting") else None),
            "n_papers": rec.get("papers", 0) or len(papers_by_gene.get(sym, ())),
            "n_studied": rec.get("studied", 0),
            "n_mechanism_papers": len(mech_papers.get(sym, ())),
            "n_species": len(species_by_gene.get(sym, ())),
            "species": sorted(species_by_gene.get(sym, ()))[:20],
            "paper_ids": sorted(papers_by_gene.get(sym, ())),
            "claim_records": sum(t.values()),
            "known_as": sorted(set(surf_by_canon.get(sym, [])))[:12],
            "evidence_classes": sorted(evidence_classes.get(sym, set()))
        }
        f.write(json.dumps(e) + "\n")
        n += 1
        kinds[e["kind"]] += 1
print(f"gene_registry.jsonl: {n} entries")
print("kinds:", dict(kinds.most_common()))

# sidecar: bucket semantics + live counts (regenerated every run so the
# headline numbers people quote can never drift from the data)
host_entries = [e for e in (json.loads(l) for l in out.read_text().splitlines())
                if e["kind"] == "host_gene"]
buckets = Counter()
for e in host_entries:
    if e["n_studied"] >= 1:
        buckets["studied"] += 1
    elif e["paper_ids"]:
        buckets["claims_discovery_linked_only"] += 1
    elif e["n_papers"] > 0:
        buckets["text_only_mentions"] += 1
    elif e["panel_tier"]:
        buckets["panel_only_no_literature"] += 1
    else:
        buckets["registry_residue"] += 1
meta = {
    "generated": __import__("datetime").date.today().isoformat(),
    "file": "gene_registry.jsonl",
    "host_gene_total": len(host_entries),
    "evidence_class_counts": {
        c: sum(1 for e in host_entries if c in e["evidence_classes"])
        for c in ["perturbation", "immune_response", "in_vitro_in_silico",
                  "sequence_variation", "pathology", "receptor_interaction",
                  "mention_only"]
    },
    "evidence_class_definitions": {
        "perturbation": "claim text mentions knockout/CRISPR/siRNA/overexpression-class experiments",
        "immune_response": "claim text mentions interferon/cytokine/interleukin/ISG/antiviral response",
        "in_vitro_in_silico": "claim scoped in vitro or in silico",
        "sequence_variation": "claim text mentions mutations/variants/polymorphisms",
        "pathology": "claim text mentions pathology/lesions/mortality/virulence",
        "receptor_interaction": "claim text mentions receptor binding / sialic acid specificity",
        "mention_only": "typed claim exists but no derived class matched",
        "mechanistic": "registry field n_mechanism_papers > 0 (actor->target mechanisms)",
    },
    "buckets": dict(buckets),
    "bucket_definitions": {
        "studied": ">=1 paper where the gene is a study subject "
                   "(gene_evidence_counts.studied >= 1) — the strict "
                   "'what has actually been studied' number",
        "claims_discovery_linked_only": "extracted into typed claims or the "
        "discovery log (paper-level linkage exists) but never a study subject",
        "text_only_mentions": ">=3 raw text mentions, never extracted as "
        "studied or claimed",
        "panel_only_no_literature": "zero literature; member of the host "
        "panel (curated + UniProt/GO immune backbone) searched across "
        "genomes — candidates awaiting their first paper",
        "registry_residue": "tracked via alias map / backbone with no "
        "evidence of any kind",
    },
    "non_host_kinds": {k: v for k, v in kinds.most_common() if k != "host_gene"},
}
(PAPERS / "gene_registry.meta.json").write_text(json.dumps(meta, indent=1))
print("sidecar: gene_registry.meta.json")

# web-served per-gene host-species map ("Detected host species" chips on
# gene pages; species named in typed claims about the gene)
ghs = {e["symbol"]: {"n_species": e["n_species"], "species": e["species"]}
       for e in host_entries if e["n_species"] > 0}
_ghs_out = ROOT / "web" / "public" / "data" / "gene_host_species.json"
_ghs_out.write_text(json.dumps(ghs))
print(f"gene_host_species.json: {len(ghs)} genes")
