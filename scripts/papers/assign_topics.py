#!/usr/bin/env python3
"""
Topic assignment + strain tagging + LLM provenance (D90).

1. Strain topics: deterministic from strain_index.json (already scanned).
2. Vaccine topics: deterministic scan for vaccine-related language.
3. LLM topic extraction: for papers with no/sparse topics, ask muse-glimmer
   to assign topics from a controlled vocabulary + title.
4. LLM provenance: every LLM-driven extraction records model, date,
   prompt_version, and affected papers to data/papers/llm_provenance.json.

Usage:
  pixi run python scripts/papers/assign_topics.py            # deterministic only
  pixi run python scripts/papers/assign_topics.py --llm      # + Muse pass
  pixi run python scripts/papers/assign_topics.py --check    # coverage report
"""

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
STRAIN_INDEX = ROOT / "data" / "papers" / "connections" / "strain_index.json"
MD_DIR = ROOT / "docs" / "papers_md"
PROVENANCE = ROOT / "data" / "papers" / "llm_provenance.json"

DEFAULT_URL = "http://localhost:8005/v1"
DEFAULT_MODEL = "muse-glimmer-30b"

PROMPT_VERSION = "topics-v2"

# Controlled topic vocabulary (superset — LLM picks from this + may add new)
TOPIC_VOCAB = [
    "Pathogenesis", "Innate Immunity", "Adaptive Immunity", "Vaccines",
    "Vaccination", "Antivirals", "Epidemiology", "Surveillance",
    "Host Genomics", "Cross-Species", "Mammalian Spillover", "Wild Birds",  # NB: 'Cross-Species Transmission' merges into 'Cross-Species' (D109)
    "Poultry", "Chickens", "Ducks", "Turkeys", "Waterfowl", "Raptors",
    "Seabirds", "Passerines", "Cattle", "Cats", "Dogs", "Humans", "Swine",
    "Marine Mammals", "Mink", "Evolution", "Reassortment", "Genomics",
    "Molecular", "Receptor Binding", "PB2", "Polymerase", "HA", "NA",
    "NS1", "Replication", "Transmission", "Milk", "Mammary Gland",
    "Public Health", "Pandemic Preparedness", "One Health", "Biosecurity",
    "Outbreak", "Modeling", "Diagnostics", "Serology", "Review",
    "Ecology", "Migration", "Phylogenetics", "Phylodynamics",
    "Species Barrier", "Tropism", "Apoptosis", "Inflammasome",
    "Interferon", "Gene Expression", "Transcriptomics", "Proteomics",
    "Vaccine Development", "Vaccine Strategy", "Cross-Reactive Immunity",
    "Pre-existing Immunity", "Risk Assessment", "Zoonosis",
    "Clade 2.3.4.4b", "Clade 2.3.4.4h", "Clade 2.3.2.1",
    "Genotype D1.1", "Genotype D1.2", "Genotype D1.3",
    "Genotype B3.13", "Genotype B3.6", "Genotype B3.2", "Genotype G5",
    "H5N1", "H5N2", "H5N5", "H5N6", "H5N8",
]

VACCINE_RE = re.compile(
    r"vaccin|immuniz|antigen.*deliver|mRNA.*vaccine|ChAdOx|adeno.*vector|"
    r"inactivated.*virus.*vaccine|live.*attenuated|subunit.*vaccine|"
    r"nanobody|antibody.*therapy|monoclonal", re.IGNORECASE)

STRAIN_TOPIC_MAP = {
    "clade.2.3.4.4b": "Clade 2.3.4.4b",
    "clade.2.3.4.4h": "Clade 2.3.4.4h",
    "clade.2.3.4.4": "Clade 2.3.4.4",
    "clade.2.3.2.1": "Clade 2.3.2.1",
    "genotype.D1.1": "Genotype D1.1",
    "genotype.D1.2": "Genotype D1.2",
    "genotype.D1.3": "Genotype D1.3",
    "genotype.B3.13": "Genotype B3.13",
    "genotype.B3.6": "Genotype B3.6",
    "genotype.B3.2": "Genotype B3.2",
    "genotype.G5": "Genotype G5",
    "subtype.H5N1": "H5N1",
    "subtype.H5N2": "H5N2",
    "subtype.H5N5": "H5N5",
    "subtype.H5N6": "H5N6",
    "subtype.H5N8": "H5N8",
}

# Subtype tags: only tag non-H5N1 subtypes (H5N1 is the default, skip it)
NON_DEFAULT_STRAINS = {k: v for k, v in STRAIN_TOPIC_MAP.items()
                       if v != "H5N1"}


def load_provenance():
    if PROVENANCE.exists():
        try:
            return json.loads(PROVENANCE.read_text())
        except Exception:
            pass
    return {"calls": []}


def record_provenance(task, model, prompt_version, papers_affected,
                      notes=""):
    prov = load_provenance()
    prov["calls"].append({
        "task": task,
        "model": model,
        "prompt_version": prompt_version,
        "papers": papers_affected[:20] if isinstance(papers_affected, list)
        else papers_affected,
        "total_papers": len(papers_affected) if isinstance(papers_affected, list)
        else papers_affected,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "notes": notes,
    })
    PROVENANCE.write_text(json.dumps(prov, indent=1, ensure_ascii=False))


def deterministic_pass(papers):
    """Strain topics from strain index + vaccine detection from title/md."""
    strain_map = {}
    if STRAIN_INDEX.exists():
        # strain_index has {paper_id: [strain_keys]}
        idx = json.loads(STRAIN_INDEX.read_text())
        # The index is a summary; re-derive per-paper from the raw scan
        pass  # handled below via direct text scan

    md_texts = {}
    updated = 0
    vax_added = 0
    strain_added = 0

    for p in papers:
        pid = p["id"]
        topics = set(p.get("topics") or [])
        orig_count = len(topics)

        # --- vaccine detection (title + first 2k of md) ---
        title = (p.get("title") or "") + " " + (p.get("summary") or "")
        if VACCINE_RE.search(title):
            topics.add("Vaccines")
        md = MD_DIR / f"{pid}.md"
        if md.exists() and "Vaccines" not in topics:
            head = md.read_text(errors="replace")[:2000]
            if VACCINE_RE.search(head):
                topics.add("Vaccines")

        # --- strain topics (from text scan) ---
        scan_text = title
        if md.exists():
            scan_text += " " + md.read_text(errors="replace")[:5000]
        for key, topic in NON_DEFAULT_STRAINS.items():
            # convert key like "clade.2.3.4.4b" to regex pattern
            pat = key.replace("genotype.", r"\b").replace(
                "clade.", "clade ").replace("subtype.", "")
            pat = re.escape(pat).replace(r"\ ", " ")
            # simpler: just search for the human-readable form
            if topic.lower() in scan_text.lower():
                topics.add(topic)

        if len(topics) > orig_count:
            p["topics"] = sorted(topics)
            updated += 1
            if "Vaccines" in topics and "Vaccines" not in (p.get("topics") or []):
                vax_added += 1
            strain_added += sum(1 for t in topics if t.startswith(
                ("Clade", "Genotype", "H5N")))

    return updated, vax_added, strain_added


TOPIC_PROMPT = f"""You assign research-paper topics for an avian-influenza database.

Given a paper's title, assign 3–8 topics from this vocabulary (use exact spellings):
{json.dumps(TOPIC_VOCAB[:60])}

Also add strain/genotype topics if the title names one (e.g. "Clade 2.3.4.4b", "Genotype D1.1", "H5N6").

Rules:
- Only use topics that the title clearly supports
- Include at least one host-species topic (Chickens, Ducks, Cattle, Humans, Wild Birds, etc.) if identifiable
- Include at least one research-type topic (Pathogenesis, Epidemiology, Vaccines, Review, etc.)
- "Vaccines" applies to any vaccine/immunization/antibody-therapy paper

Return ONLY JSON: {{"topics": ["Topic1", "Topic2", ...]}}"""


def llm_topic_pass(papers, url, model, workers):
    """Fill topics for papers with 0 or 1 topics via muse-glimmer."""
    todo = [p for p in papers if len(p.get("topics") or []) <= 1]
    print(f"  papers needing LLM topics: {len(todo)}")
    if not todo:
        return 0

    def work(p):
        title = p.get("title") or ""
        try:
            r = httpx.post(f"{url.rstrip('/')}/chat/completions", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": TOPIC_PROMPT},
                    {"role": "user", "content": f"TITLE: {title}"},
                ],
                "max_tokens": 32000, "temperature": 0.1,
            }, timeout=900)
            msg = r.json()["choices"][0]["message"]
            text = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            # extract JSON object
            m = re.search(r'\{[^{}]*"topics"[^{}]*\}', text, re.DOTALL)
            if m:
                d = json.loads(m.group(0))
                return p["id"], [t for t in d.get("topics", [])
                                 if isinstance(t, str) and len(t) > 1][:8]
        except Exception as e:
            print(f"    {p['id'][:30]}: {str(e)[:60]}")
        return p["id"], None

    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work, p) for p in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            pid, topics = fut.result()
            if topics:
                results[pid] = topics
            if i % 50 == 0:
                print(f"    [{i}/{len(todo)}]")

    by_id = {p["id"]: p for p in papers}
    n = 0
    for pid, topics in results.items():
        if pid in by_id:
            existing = set(by_id[pid].get("topics") or [])
            by_id[pid]["topics"] = sorted(existing | set(topics))
            n += 1

    if n:
        record_provenance("topic_extraction", model, PROMPT_VERSION,
                          sorted(results.keys()),
                          f"Assigned topics to {n} papers via LLM")
    return n


def check_coverage(papers):
    no_topics = sum(1 for p in papers if not p.get("topics"))
    sparse = sum(1 for p in papers if len(p.get("topics") or []) <= 1)
    vax = sum(1 for p in papers if "Vaccines" in (p.get("topics") or []))
    strains = sum(1 for p in papers if any(
        t.startswith(("Clade", "Genotype")) or t in ("H5N2", "H5N5", "H5N6", "H5N8")
        for t in p.get("topics", [])))
    topic_counts = Counter(t for p in papers for t in p.get("topics", []))
    print(f"papers: {len(papers)} | no topics: {no_topics} | sparse (≤1): {sparse}")
    print(f"vaccine-tagged: {vax} | strain-tagged: {strains}")
    print(f"distinct topics: {len(topic_counts)}")
    print(f"top 20: {topic_counts.most_common(20)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true",
                    help="run Muse topic extraction for sparse papers")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = json.loads(PAPERS_JSON.read_text())
    papers = data["papers"]

    if args.check:
        check_coverage(papers)
        return

    print("=== deterministic pass (vaccine + strains) ===")
    updated, vax, strains = deterministic_pass(papers)
    print(f"  updated {updated} papers | +vaccine tags: {vax} | "
          f"+strain tags: {strains}")
    record_provenance("topic_deterministic", "regex", "det-v1", updated,
                      f"vaccine + strain tags: +{vax} vax, +{strains} strain")

    if args.llm:
        print("=== LLM topic extraction ===")
        n = llm_topic_pass(papers, args.url, args.model, args.workers)
        print(f"  LLM assigned topics to {n} papers")

    PAPERS_JSON.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print("=== final coverage ===")
    check_coverage(papers)
    print(f"→ {PAPERS_JSON.name} saved")


if __name__ == "__main__":
    main()
