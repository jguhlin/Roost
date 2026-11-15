#!/usr/bin/env python3
"""Cross-link adjudicated contradictions ↔ research briefings (deterministic).

A contradiction links to a briefing when the briefing cites one of the
contradiction's two papers ([paper_id] markers in sections/hypotheses/
key_contradictions) or lists it in key_contradictions.papers.

Output: web/public/data/contradiction_briefing_links.json
  {"meta": {...}, "by_contradiction": {cluster: [slugs]},
   "by_briefing": {slug: [{cluster, topic, verdict}]}}
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRIEF_DIR = ROOT / "web" / "public" / "data" / "research_briefings"
CONTRA = ROOT / "web" / "public" / "data" / "papers" / "contradictions.json"
OUT = ROOT / "web" / "public" / "data" / "contradiction_briefing_links.json"

CITE = re.compile(r"\[([a-z0-9_\-\.]+)\]")


def briefing_citations(b: dict) -> set[str]:
    """All [paper_id] markers in a briefing's text fields."""
    cites: set[str] = set()
    for sec in b.get("sections") or []:
        cites.update(CITE.findall(sec.get("body", "")))
    for h in b.get("hypotheses") or []:
        for f in (h.get("evidence_for") or []) + (h.get("evidence_against") or []):
            cites.update(CITE.findall(str(f)))
    for kc in b.get("key_contradictions") or []:
        cites.update(kc.get("papers") or [])
    return cites


def main() -> int:
    if not CONTRA.exists():
        print("contradictions.json missing — run export_contradictions.py first",
              file=sys.stderr)
        return 1
    contra = json.loads(CONTRA.read_text(encoding="utf-8"))

    briefings = []
    for f in sorted(BRIEF_DIR.glob("*.json")):
        if f.name == "index.json":
            continue
        b = json.loads(f.read_text(encoding="utf-8"))
        b["_cites"] = briefing_citations(b)
        briefings.append(b)

    # contradiction cluster -> papers
    clus_papers: dict[str, set[str]] = {}
    clus_meta: dict[str, dict] = {}
    for c in contra.get("contradictions", []):
        cl = c.get("cluster", "")
        papers = {c["a"]["id"], c["b"]["id"]}
        clus_papers[cl] = clus_papers.get(cl, set()) | papers
        clus_meta.setdefault(cl, {"topic": c.get("topic", ""),
                                  "verdict": c.get("verdict", "")})

    by_contra: dict[str, list[str]] = defaultdict(list)
    by_brief: dict[str, list[dict]] = defaultdict(list)
    n_links = 0
    for b in briefings:
        for cl, papers in clus_papers.items():
            if b["_cites"] & papers:
                by_contra[cl].append(b["slug"])
                by_brief[b["slug"]].append(
                    {"cluster": cl, "topic": clus_meta[cl]["topic"],
                     "verdict": clus_meta[cl]["verdict"]})
                n_links += 1

    for d in (by_contra, by_brief):
        for k in d:
            d[k] = sorted(set(d[k])) if k in by_contra else sorted(
                d[k], key=lambda x: x["cluster"])

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "n_contradictions_with_briefings": len(by_contra),
            "n_briefings_with_contradictions": len(by_brief),
            "n_links": n_links,
            "method": "shared paper citations between briefing text and "
                      "contradiction paper pairs",
        },
        "by_contradiction": by_contra,
        "by_briefing": by_brief,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"links → {OUT.relative_to(ROOT)} "
          f"({n_links} links, {len(by_brief)} briefings, {len(by_contra)} clusters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
