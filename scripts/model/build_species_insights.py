#!/usr/bin/env python3
"""Species insights — plain-language, evidence-backed gene panel narratives.

"What can we learn about this bird's response to influenza, and where
should we investigate next?" (user design brief 2026-11):

1. FUNCTIONAL GROUPING — genes grouped by biological job (Detect / Alert /
   Defend / Virus uses), from the model's stage assignment + catalogue
   categories.
2. CONFIDENCE-AWARE — every gene call carries its evidence level (E5
   annotated … E2 absent-with-uncertainty); absences on low-quality
   assemblies keep their uncertainty.
3. RELATIVES INFERENCE — species without genomes get estimated panels from
   their closest searched relatives (same genus → family → order,
   majority-vote per gene), labelled as estimates.
4. LLM NARRATIVE — a local-LLM pass turns the deterministic record into
   short plain-language summaries (species page card) + a longer overview,
   a susceptibility discussion (NO hard scores in prose) and a vaccine
   paragraph. Every input the LLM sees is evidence-derived; outputs are
   doctrine-filtered (echo/leak/placeholder).
5. CAVEATS — explicit, always rendered (no-genome inference, assembly
   quality, untested functions).

Deterministic records are built for ALL index species; LLM narratives are
generated incrementally (resume-safe per-species JSON ledger) — pages
degrade gracefully to the deterministic panel until a narrative lands.

Usage:
  pixi run python scripts/model/build_species_insights.py [--deterministic-only]
  LLM_BASE_URL=... pixi run python scripts/model/build_species_insights.py [--limit N] [--species "Gallus gallus"]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
WEB = ROOT / "web" / "public" / "data"
OUT_LEDGER = DATA / "model" / "species_insights"          # interior cache
OUT_WEB = WEB / "species_insights"                        # shipped artifacts

LOCALES = []  # narratives are en-only for now (hash-stable); translation later

# ---------------------------------------------------------------- grouping
STAGE_GROUPS = {
    "entry": None,               # virus entry factors — folded into "virus uses"
    "sensing": "detect",
    "signaling": "alert",
    "cytokine_storm": "alert",
    "effectors": "defend",
    "adaptive": "defend",
    "dependency": "virus_uses",
    "celldeath": "alert",
    "hostrange": "virus_uses",
}
CATEGORY_GROUPS = {
    "Pattern Recognition": "detect", "Sensor": "detect",
    "Immune Response": "alert", "Immune (GO:0002376)": "alert",
    "Antiviral Response": "defend", "ISG": "defend", "Effector": "defend",
    "Dependency": "virus_uses", "Host Factor": "virus_uses",
}
GROUP_LABELS = {
    "detect": "Detecting the virus",
    "alert": "Raising the alarm",
    "defend": "Restricting infection",
    "virus_uses": "Machinery the virus uses",
}
GROUP_ORDER = ["detect", "alert", "defend", "virus_uses"]

STATUS_WORDS = {
    ("FULL", "E5"): "found — listed in this genome's own annotation (strongest evidence)",
    ("FULL", "E4"): "found — convincing sequence match where no annotation exists",
    ("FULL", None): "found",
    ("FRAGMENT", None): "partial match only — possibly a pseudogene, assembly gap, or a genuinely divergent gene; treat with caution",
    ("NOT_FOUND", None): "not found by search — absence on a well-assembled genome is meaningful, but assembly quality can masquerade as loss",
}


def h12(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def load_inputs():
    idx = json.loads((WEB / "species_index.json").read_text())
    presence = pl.read_parquet(DATA / "genes" / "gene_presence_v2.parquet")
    tax = {}
    with open(DATA / "aves_taxonomy.tsv") as f:
        hdr = f.readline().rstrip("\n").split("\t")
        ix = {k: hdr.index(k) for k in ("scientific_name", "genus", "family", "order")}
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < len(hdr):
                continue
            tax[p[ix["scientific_name"]]] = {
                "genus": p[ix["genus"]], "family": p[ix["family"]], "order": p[ix["order"]]
            }
    catalogue = json.loads((WEB / "gene_catalogue.json").read_text())["gene_catalogue"]
    stage = {g: v["stage"] for g, v in
             json.loads((WEB / "gene_stage_assignment.json").read_text()).items()}
    susc = {e["species"]: e for e in
            json.loads((WEB / "species_susceptibility.json").read_text())["species"]}
    vax = json.loads((WEB / "vaccine_readiness.json").read_text())["species"]
    wiki = json.loads((WEB / "wiki_genes.json").read_text())["genes"]
    research = {}
    wiki_index = {}
    overlay = {}
    try:
        wp = json.loads((ROOT / "data" / "aves_wikipedia.json").read_text())
        wiki_index = {k: v for k, v in wp.items()}
    except (OSError, json.JSONDecodeError):
        pass
    try:
        ov = json.loads((ROOT / "data" / "manual" / "species_overlay.json").read_text())
        for e in (ov if isinstance(ov, list) else ov.get("species", ov.get("species_of_concern", [])) or []):
            if e.get("scientific_name"):
                overlay[e["scientific_name"]] = e
    except (OSError, json.JSONDecodeError):
        pass
    try:
        for e in json.loads((WEB / "wiki_species.json").read_text())["species"].values():
            research[e.get("scientific_name")] = e
    except FileNotFoundError:
        pass
    return idx, presence, tax, catalogue, stage, susc, vax, wiki, research, wiki_index, overlay


def group_of(symbol: str, catalogue: dict, stage: dict) -> str | None:
    st = stage.get(symbol)
    if st and st in STAGE_GROUPS:
        g = STAGE_GROUPS[st]
        if g:
            return g
    cat = (catalogue.get(symbol) or {}).get("category")
    return CATEGORY_GROUPS.get(cat)


def core_panel(catalogue: dict, model_stages_path: Path) -> list[str]:
    """Readable panel = curated importance genes UNION the infection-model's
    stage genes (~136) — not every stage-assigned gene (816, unreadable)."""
    panel = {g for g, e in catalogue.items()
             if e.get("importance") in ("critical", "high")}
    am = json.loads(model_stages_path.read_text())
    for s in am.get("stages", []):
        for x in s.get("genes", []):
            if isinstance(x, str):
                panel.add(x)
            elif isinstance(x, list) and x and isinstance(x[0], str):
                panel.add(x[0])
    panel &= set(catalogue.keys())
    return sorted(panel)


def find_relatives(sci: str, tax: dict, searched: set[str]) -> list[str]:
    """Closest searched species: same genus, then family, then order."""
    t = tax.get(sci)
    if not t:
        return []
    for rank in ("genus", "family", "order"):
        hits = sorted(s for s in searched if s != sci and tax.get(s, {}).get(rank) == t[rank])
        if hits:
            return hits[:8]
    return []


def detected_relatives(sci: str, tax: dict, detected: set[str], limit: int = 6) -> list[dict]:
    """Same-order species WITH HPAI detections — the kākāpō story: no
    detections itself, but 19 parrot species have records."""
    t = tax.get(sci)
    if not t:
        return []
    rels = []
    for rank in ("genus", "family", "order"):
        for s in sorted(detected):
            if s == sci:
                continue
            st = tax.get(s, {})
            if st.get(rank) == t[rank]:
                rels.append({"sci": s, "rank": rank})
        if rels:
            return rels[:limit]
    return rels[:limit]


def deterministic_record(sci, entry, presence_by_sp, tax, catalogue, stage, susc, vax, wiki, panel, detected_set=None, research=None, wiki_index=None, overlay=None):
    searched = set(presence_by_sp.keys())
    has_genome = sci in searched
    own = presence_by_sp.get(sci, {})
    basis = "genome" if has_genome else "relatives"
    relatives = [] if has_genome else find_relatives(sci, tax, searched)
    rel_calls = [presence_by_sp[r] for r in relatives]

    gene_entries = []
    for sym in panel:
        if has_genome:
            call = own.get(sym)
            if not call:
                continue
            status = call.get("search_status")
            level = call.get("status_level")
            origin = "called"
            if status == "NOT_FOUND" and call.get("absence_confidence"):
                level = call.get("absence_confidence")
        else:
            votes = Counter((rc.get(sym) or {}).get("search_status") for rc in rel_calls if rc.get(sym))
            if not votes:
                continue
            status = votes.most_common(1)[0][0]
            n_with = len(votes)
            agree = votes[status]
            level = None
            origin = f"estimated from {len(relatives)} related species ({agree}/{n_with} agree)"

        cat = catalogue.get(sym, {})
        gene_entries.append({
            "symbol": sym,
            "group": group_of(sym, catalogue, stage),
            "status": status,
            "level": level,
            "importance": cat.get("importance") or "standard",
            "origin": origin,
        })

    groups = []
    for gk in GROUP_ORDER:
        genes = [e for e in gene_entries if e["group"] == gk]
        if genes:
            groups.append({
                "key": gk,
                "label": GROUP_LABELS[gk],
                "genes": sorted(genes, key=lambda e: -e.get("papers", 0)),
            })

    s = susc.get(sci)
    v = vax.get(sci)

    # Detection history summary (for the "No detections" / "Detected..." section)
    det_count = entry.get("det", 0) or 0
    det_history = None
    if det_count > 0:
        try:
            _d = pl.read_parquet(DATA / "detections_merged.parquet")
            _g = _d.filter(pl.col("scientific_name") == sci)
            if _g.height:
                # Row count = number of detection RECORDS (the detection_count
                # column aggregates flock/event sizes — summing it gives millions)
                _dates = _g.filter(pl.col("date_detected").is_not_null())
                det_history = {
                    "first": str(_dates["date_detected"].min())[:10] if _dates.height else None,
                    "last": str(_dates["date_detected"].max())[:10] if _dates.height else None,
                    "n": _g.height,
                    "countries": _g["country"].n_unique(),
                }
        except Exception:
            pass

    # Facts at a glance (deterministic — the reporter's numbers box)
    det_rels = detected_relatives(sci, tax, detected_set or set()) if det_count == 0 else []
    w = wiki.get("", {})  # placeholder — evidence level computed from wiki_species
    evidence_level = "not_studied"
    if det_count > 0:
        evidence_level = "detected"
    if has_genome:
        evidence_level = "detected_and_sequenced" if det_count > 0 else "sequenced_only"
    elif relatives:
        evidence_level = "relatives_studied" if any(r in detected_set or set() for r in relatives) else "relatives_sequenced"

    caveats = []
    if not has_genome:
        if relatives:
            caveats.append(
                f"No genome is available for this species — gene panel estimated from its "
                f"closest sequenced relatives ({', '.join(relatives[:3])}"
                + (f" and {len(relatives)-3} more" if len(relatives) > 3 else "") + ").")
        else:
            caveats.append("No genome and no sequenced close relatives — no gene panel can be estimated.")
    else:
        caveats.append("Gene calls come from annotation and sequence search; fragments and "
                       "absences can reflect assembly quality, not true biology.")
    if s and s.get("confidence", 1) < 0.5:
        caveats.append("Susceptibility assessment rests on thin evidence — treat as provisional.")

    # Research evidence (wiki corpus): top 3 by status weight — only
    # species with curated evidence get a `research` key at all; the
    # prompt says to SKIP research entirely when it's absent.
    research_out = None
    rw = (research or {}).get(sci)
    if rw and rw.get("evidence"):
        rank = {"confirmed": 0, "infected": 0, "susceptible": 1,
                "resistant": 1, "sampled": 2, "unknown": 3}
        ev = sorted(rw["evidence"], key=lambda e: rank.get(e.get("status"), 4))[:3]
        research_out = [{"title": e.get("title"), "year": e.get("year"),
                         "status": e.get("status"),
                         "finding": (e.get("finding") or "")[:220]}
                        for e in ev]

    # Wikipedia intro (first ~2 sentences) — context for the intro sentence
    # in the summary's OWN words; never quoted verbatim
    wiki_intro = None
    wr = (wiki_index or {}).get(sci)
    if wr and not wr.get("missing") and wr.get("e"):
        sents = re.split(r"(?<=[.!?])\s+", wr["e"].strip())
        wiki_intro = " ".join(sents[:3])[:600]

    # Overlay conservation facts (species of concern / mammals): status,
    # population estimate, range countries
    ov = (overlay or {}).get(sci) or {}
    conservation = None
    if ov.get("conservation_status") or ov.get("population_estimate"):
        conservation = {
            "status": ov.get("conservation_status"),
            "population": ov.get("population_estimate"),
            "countries": (ov.get("countries") or [])[:4],
        }

    return {
        "sci": sci,
        "common": entry.get("com") or None,
        "taxon_id": entry.get("id"),
        "has_genome": has_genome,
        "basis": basis,
        "relatives": relatives[:5],
        "detections": det_history["n"] if det_history else det_count,
        "detection_history": det_history,
        "facts": {
            "evidence_level": evidence_level,
            "detected_relatives": det_rels,
            "n_detected_relatives": len(det_rels),
            "order": tax.get(sci, {}).get("order"),
            "iucn": entry.get("iucn") or (s or {}).get("class") if s else entry.get("iucn"),
            "citation": (
                f"Roost: Avian Influenza Host Genomics Resource (2026). "
                f"{sci}. https://josephguhlin.com/Roost/#/species-full/{sci.replace(' ', '%20')}. "
                f"Accessed {time.strftime('%Y-%m-%d')}."
            ),
        },
        "groups": groups,
        "research": research_out,
        "wikipedia": wiki_intro,
        "conservation": conservation,
        "susceptibility": ({k: s.get(k) for k in
                            ("permissiveness", "severity", "class", "outcome", "confidence",
                             "severity_basis", "severity_studies")} if s else None),
        "vaccine": ({k: v.get(k) for k in ("overall", "band", "anchor")} if v else None),
        "caveats": caveats,
        "generated": time.strftime("%Y-%m-%d"),
    }


PROMPT = """You write plain-language summaries of a bird species' gene panel for a
conservation/research audience. You get a deterministic JSON record from the
Roost resource: gene calls grouped by function (each with status/level/origin),
detection history, susceptibility evidence, vaccine readiness and explicit caveats.

Write, as JSON:
{{"summary": "5-6 sentences (up to 7 when research is rich) written for someone deciding whether to dig deeper. Fixed order: (0) INTRODUCTION — open with ONE OR TWO sentences introducing the species itself, in your OWN words from the `wikipedia` and `conservation` context: what kind of bird it is, where it lives (say 'endemic to X' when its range is a single country), conservation status and population ONLY when a `conservation` object is present in the record — if it is absent, do NOT mention any IUCN or conservation status at all, never infer or invent one — and at most one distinctive trait. The intro must be substantive: name the kind of bird AND its range, habitat or a distinctive trait drawn from the `wikipedia` context — never a vacuous opener like 'is a species of bird'. Never copy Wikipedia's phrasing. (1) FIELD STATUS — the detection facts: 'Recorded in N HPAI detections across K countries (first YEAR)' or 'One historical detection' or 'No HPAI detections on record.' (2) RISK PICTURE — one to two sentences: the susceptibility verdict in plain words (e.g. 'evidence points to high susceptibility with severe outcomes' / 'susceptibility remains unevaluated'), then what the gene panel actually shows with a little texture — walk the functional groups briefly (detection / alarm / defence) and lead with whatever is DISTINCTIVE for THIS species (an unusual absence, a complete toolkit, fragments where relatives have full calls), keeping the assembly-quality uncertainty where the record carries it; if the panel is estimated from relatives, say so. VARY the phrasing across records — never reuse identical sentence shapes. (3) RESEARCH — ONLY if the `research` list exists: one clause on the most pertinent finding, experimental results first ('experimental infection caused fatal disease' beats any gene inference). If there is NO research key in the record, the summary must contain NO sentence or clause about research — never write 'no research is available' or 'there is no experimental research'; just finish after the risk picture. Drop 'across K countries' when K is 1; say 'first recorded YEAR' when the count is 1.",
 "overview": "1-2 short paragraphs: walk the functional groups in plain terms — 'the virus-detection toolkit is complete' or 'several defence genes are missing'. Name specific genes only when they're critical markers (RIG-I, MX1, IFITM3). Interpret absences WITH their uncertainty. Mention what relatives' experiments showed where studied_in is populated.",
 "susceptibility": "2-4 sentences in plain language discussing how susceptible/severe the evidence suggests this species is — describe, don't score. Mention evidence thinness honestly.",
 "vaccines": "1-2 sentences on what its immune-gene panel suggests about vaccination prospects (vaccine readiness band if present), with appropriate hedging."}}

Rules:
- EVERY claim must trace to the record; do not invent findings, numbers or species
- NEVER end the summary with a standalone sentence restating the panel basis ('The panel is based on the species genome.') — basis appears as an adjective ('genome-based panel') or the relatives caveat only
- WRITE FOR A GENERALIST: 'the virus-detection genes are all present' not 'DDX58, IFIH1, TLR3, TLR7 are present'
- Genes stay as symbols ONLY when they're the point (e.g. 'missing RIG-I, the primary detector'). HARD LIMIT: at most FIVE gene symbols in the entire summary — count them before answering; if a sixth is tempting, describe it in words instead ('several alarm-signal genes are fragmentary', 'the MHC antigen-presentation pathway is patchy')
- Absences: always keep the uncertainty wording from the record
- If basis is "relatives", the summary must SAY the panel is estimated from relatives
- NEVER open the summary with a formulaic 'X has a genome-based immune panel'
  sentence — lead with what stands out; the panel basis is shown separately
- If detection_history is null and detections is 0, the summary should mention no HPAI detections have been recorded
- If detection_history is present, the summary may reference when it was first detected or how many countries
- Keep the caveat register: provisional, estimated, not-yet-tested
- Reply ONLY with the JSON object"""


def llm_narrative(record: dict, url: str, model: str) -> dict | None:
    body = json.dumps({
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You are a careful scientific writer. Output valid JSON only."},
            {"role": "user", "content": PROMPT + "\n\nRECORD:\n" + json.dumps(record, ensure_ascii=False)},
        ],
    }).encode()
    req = urllib.request.Request(f"{url.rstrip('/')}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        msg = json.load(r)["choices"][0]["message"]
    text = msg.get("content") or ""
    if not text and msg.get("reasoning_content"):
        m = re.search(r"\{.*\}", msg["reasoning_content"], re.S)
        if m:
            text = m.group(0)
    m = re.search(r"\{.*\}", text.strip(), re.S)
    if not m:
        return None
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    keep = {}
    for k in ("summary", "overview", "susceptibility", "vaccines"):
        v = out.get(k)
        if isinstance(v, str) and 30 < len(v) < 3000 and "<|" not in v and "```" not in v:
            keep[k] = v.strip()
    if "summary" in keep:
        keep["summary"] = strip_formulaic_opener(keep["summary"])
    return keep if len(keep) >= 2 else None


def slugify(sci: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sci.lower()).strip("-")


# Bare formulaic opener, cut per user decision 2026-11. Only matches when
# the sentence ENDS at the formula — qualified forms ("...panel that looks
# patchy") carry real content and must survive.
_OPENER_RE = re.compile(
    r"^The [^,.]{3,60}? has a genome-based (?:immune (?:gene )?panel"
    r"|panel for influenza-response genes)(?P<tail>\.|, and )", re.I)


def strip_formulaic_opener(s: str) -> str:
    if not s:
        return s
    m = _OPENER_RE.match(s)
    if not m:
        return s
    if m.group("tail") == ", and ":
        rest = s[m.end():]      # qualified: keep the clause after ', and '
    else:
        rest = s[m.end():].lstrip()  # bare formula: drop the whole sentence
    if not rest:
        return s  # never strip a summary to empty
    return rest[0].upper() + rest[1:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1"))
    ap.add_argument("--model", default="muse-glimmer-30b")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--species", default=None,
                    help="single species or comma-separated list (debug/targeted)")
    ap.add_argument("--regenerate", action="store_true",
                    help="re-run the LLM even when the ledger has a narrative "
                         "(backs up the ledger to a timestamped dir first)")
    ap.add_argument("--deterministic-only", action="store_true")
    ap.add_argument("--strip-openers", action="store_true",
                    help="one-off: strip formulaic openers from the narrative "
                         "ledger in place (no LLM); then run --deterministic-only "
                         "to rebuild the web artifacts")
    args = ap.parse_args()

    if args.strip_openers:
        changed = 0
        for f in sorted(OUT_LEDGER.glob("*.json")):
            d = json.loads(f.read_text())
            s = d.get("summary")
            if not s:
                continue
            clean = strip_formulaic_opener(s)
            if clean != s:
                d["summary"] = clean
                f.write_text(json.dumps(d, ensure_ascii=False, indent=1))
                changed += 1
        print(f"strip-openers: {changed} ledger summaries cleaned")
        return

    if args.regenerate and not args.species:
        # full re-run: back up the whole ledger first (single-species debug
        # runs skip the copy — they'd make a backup per call)
        backup = OUT_LEDGER.parent / (
            OUT_LEDGER.name + "_backup_" + time.strftime("%Y%m%d_%H%M%S"))
        shutil.copytree(OUT_LEDGER, backup)
        print(f"--regenerate: ledger backed up to {backup}")

    idx, presence, tax, catalogue, stage, susc, vax, wiki, research, wiki_index, overlay = load_inputs()
    presence_by_sp = defaultdict(dict)
    for r in presence.iter_rows(named=True):
        presence_by_sp[r["species"]][r["gene_symbol"]] = r
    panel = core_panel(catalogue, WEB / "avian_h5n1_model.json")
    detected_set = {e["sci"] for e in idx if (e.get("det", 0) or 0) > 0}
    print(f"core panel: {len(panel)} genes | searched: {len(presence_by_sp)} | detected: {len(detected_set)}")

    OUT_LEDGER.mkdir(parents=True, exist_ok=True)
    OUT_WEB.mkdir(parents=True, exist_ok=True)

    # Priority: detected + susceptibility-known species first, then genomes,
    # then everything else (relatives-inferred) — the LLM ledger is resumable.
    # Build artifacts ONLY for species with real signal (genome-searched,
    # detected, or susceptibility/vaccine-known) — the deep taxonomy tail
    # has nothing evidence-based to say, and 11k artifacts would bloat the
    # shipped dist. The panel simply doesn't render for the rest.
    def in_scope(e):
        sci = e.get("sci", "")
        return (sci in presence_by_sp or (e.get("det", 0) or 0) > 0
                or sci in susc or sci in vax)

    def priority(e):
        det = e.get("det", 0) or 0
        sci = e.get("sci", "")
        has_g = sci in presence_by_sp
        known = sci in susc or sci in vax
        return (0 if (det and (has_g or known)) else 1 if known or has_g else 2, -det)

    species_list = sorted([e for e in idx if in_scope(e)], key=priority)
    if args.species:
        want = {s.strip().lower() for s in args.species.split(",")}
        species_list = [e for e in idx if e["sci"].lower() in want]
        print(f"targeted: {len(species_list)} of {len(want)} requested species")
    if args.limit:
        species_list = species_list[: args.limit]

    manifest = {}
    n_llm = 0
    for i, entry in enumerate(species_list, 1):
        sci = entry.get("sci", "")
        if not sci:
            continue
        slug = str(entry.get("id") or slugify(sci))
        rec = deterministic_record(sci, entry, presence_by_sp, tax, catalogue,
                                   stage, susc, vax, wiki, panel, detected_set,
                                   research=research, wiki_index=wiki_index, overlay=overlay)
        # LLM narrative (resume: skip when the ledger already has one)
        if not args.deterministic_only:
            cache = OUT_LEDGER / f"{slug}.json"
            if not cache.exists() or args.regenerate:
                try:
                    narr = llm_narrative(rec, args.url, args.model)
                except Exception as e:
                    print(f"  [{i}/{len(species_list)}] {sci}: LLM {type(e).__name__} — deferred")
                    narr = None
                    time.sleep(2)
                if narr:
                    cache.write_text(json.dumps(narr, ensure_ascii=False, indent=1))
                    n_llm += 1
                    time.sleep(0.4)
        # merge from cache ALWAYS — the ledger is the durable narrative store;
        # artifacts rebuild around it (--deterministic-only still gets narratives)
        cache = OUT_LEDGER / f"{slug}.json"
        if cache.exists():
            narr = json.loads(cache.read_text())
            # rename LLM 'susceptibility' → 'susceptibility_narrative' so it
            # doesn't clobber the deterministic scores object of the same name
            if "susceptibility" in narr:
                narr["susceptibility_narrative"] = narr.pop("susceptibility")
            if narr.get("summary"):
                narr["summary"] = strip_formulaic_opener(narr["summary"])
            rec.update(narr)
        (OUT_WEB / f"{slug}.json").write_text(
            json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
        manifest[slug] = {"sci": sci, "has_genome": rec["has_genome"],
                          "narrative": bool(rec.get("summary"))}
        if i % 50 == 0:
            print(f"  [{i}/{len(species_list)}] llm this run: {n_llm}")
            (OUT_WEB / "index.json").write_text(json.dumps(
                {"generated": time.strftime("%Y-%m-%d"), "species": manifest},
                ensure_ascii=False))

    (OUT_WEB / "index.json").write_text(json.dumps(
        {"generated": time.strftime("%Y-%m-%d"), "species": manifest},
        ensure_ascii=False))
    n_narr = sum(1 for v in manifest.values() if v["narrative"])
    print(f"done: {len(manifest)} species artifacts, {n_narr} with narratives "
          f"({n_llm} new this run)")


if __name__ == "__main__":
    main()
