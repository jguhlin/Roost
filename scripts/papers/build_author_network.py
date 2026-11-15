#!/usr/bin/env python3
"""
Author network (D43): co-authorship graph over the corpus.

Nodes: authors (normalised "Last FI" form) and papers.
Edges: author→paper (author_of), author→author (co_author, weighted by
shared papers). Author metadata: paper count, journals, year range, and
the GENE PORTFOLIO each author has studied (from verified analyses).

Outputs:
  data/papers/author_network.json  — full graph (internal graph-DB asset)
  data/papers/author_network.md    — human digest (hubs, clusters, portfolios)

Usage: pixi run python scripts/papers/build_author_network.py
"""

import json
import re
from collections import defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PAPERS_JSON = ROOT / "web" / "public" / "data" / "papers.json"
LLM_DIR = ROOT / "data" / "papers" / "llm_analyses"
OUT_JSON = ROOT / "data" / "papers" / "author_network.json"
OUT_MD = ROOT / "data" / "papers" / "author_network.md"

SPLIT_RE = re.compile(r"[,;]| and |&")


def norm_name(raw: str) -> str:
    name = re.sub(r"\s+", " ", raw).strip(" .;")
    name = re.sub(r"\s+et\.?\s+al\.?$", "", name, flags=re.IGNORECASE).strip(" .;")
    return name


def parse_authors(field) -> list:
    if not field:
        return []
    if isinstance(field, list):
        parts = field
    else:
        parts = SPLIT_RE.split(str(field))
    out = []
    for p in parts:
        n = norm_name(p)
        if n and len(n) > 2 and not re.fullmatch(r"[\d\-]+", n) \
                and not re.fullmatch(r"et\.? al\.?", n, re.IGNORECASE):
            out.append(n)
    return out


def main():
    papers = json.loads(PAPERS_JSON.read_text())["papers"]

    author_papers = defaultdict(set)     # author → {pid}
    author_meta = defaultdict(lambda: {"journals": set(), "years": [],
                                       "genes": set(), "species": set()})
    paper_nodes = []

    for p in papers:
        pid = p["id"]
        # Prefer structured authors_list (D72) or authors_full (2026-10-05
        # backfill) — full roster, no "et al." truncation
        structured = p.get("authors_list") or p.get("authors_full")
        if structured:
            authors = []
            for a in structured:
                fam = (a.get("family") or "").strip()
                giv = (a.get("given") or "").strip()
                if fam:
                    initials = "".join(f"{part[0].upper()}." for part in giv.replace("-", " ").split() if part)
                    authors.append(norm_name(f"{fam} {initials}".strip()))
            authors = [a for a in authors if a and len(a) > 2]
        else:
            authors = parse_authors(p.get("authors"))
        paper_nodes.append({
            "id": pid, "title": (p.get("title") or "")[:100],
            "year": p.get("year"), "journal": p.get("journal") or "",
            "authors": authors,
        })
        for a in authors:
            author_papers[a].add(pid)
            m = author_meta[a]
            if p.get("journal"):
                m["journals"].add(p["journal"])
            if p.get("year"):
                m["years"].append(p["year"])

        # gene/species portfolio from the verified analysis
        ap = LLM_DIR / f"{pid}.json"
        if ap.exists():
            try:
                d = json.loads(ap.read_text())
                st = d.get("steps", {})
                genes = [g.get("name") for g in
                         st.get("genes", {}).get("extracted", {}).get("genes", [])]
                species = [s.get("name") for s in
                           st.get("species", {}).get("extracted", {}).get("species", [])]
                for a in authors:
                    for g in genes:
                        base = re.sub(r"\s*\([^)]*\)", "", g or "").upper().strip()
                        if base and len(base) <= 12:
                            author_meta[a]["genes"].add(base)
                    for s in species:
                        author_meta[a]["species"].add(s[:40])
            except Exception:
                pass

    # co-author edges — cap per paper by position (first 10 + last 2) so
    # consortium papers (100+ authors) don't explode n(n-1)/2 edges
    co_author = defaultdict(int)  # (a, b) sorted → count
    for pn in paper_nodes:
        all_authors = list(dict.fromkeys(pn["authors"]))
        if len(all_authors) > 12:
            significant = all_authors[:10] + all_authors[-2:]
        else:
            significant = all_authors
        for a, b in combinations(sorted(set(significant)), 2):
            co_author[(a, b)] += 1

    # collaboration adjacency
    collab = defaultdict(list)
    for (a, b), w in co_author.items():
        collab[a].append({"with": b, "papers": w})
        collab[b].append({"with": a, "papers": w})

    author_nodes = []
    for a, pids in sorted(author_papers.items(), key=lambda kv: -len(kv[1])):
        m = author_meta[a]
        years = [y for y in m["years"] if y]
        author_nodes.append({
            "name": a,
            "papers": len(pids),
            "paper_ids": sorted(pids),
            "journals": sorted(m["journals"]),
            "year_range": (lambda ys: [min(ys), max(ys)] if ys else None)([int(y) for y in years if str(y).strip()[:4].isdigit()]),
            "gene_portfolio": sorted(m["genes"])[:25],
            "species_studied": sorted(m["species"])[:15],
            "collaborators": sorted(collab.get(a, []), key=lambda c: -c["papers"])[:30],
        })

    graph = {
        "generated": date.today().isoformat(),
        "counts": {
            "authors": len(author_nodes),
            "papers": len(paper_nodes),
            "co_author_edges": len(co_author),
        },
        "authors": author_nodes,
        "papers": paper_nodes,
        "co_author_edges": [
            {"a": a, "b": b, "papers": w}
            for (a, b), w in sorted(co_author.items(), key=lambda kv: -kv[1])
        ],
    }
    OUT_JSON.write_text(json.dumps(graph, indent=1))

    # digest
    with open(OUT_MD, "w") as f:
        f.write(f"# Author network — {len(author_nodes)} authors, "
                f"{len(paper_nodes)} papers, {len(co_author)} co-authorship edges\n\n")
        f.write("## Most prolific authors\n\n| Author | Papers | Years | Top genes |\n|---|---|---|---|\n")
        for a in author_nodes[:20]:
            yr = f"{a['year_range'][0]}–{a['year_range'][1]}" if a["year_range"] else "—"
            f.write(f"| {a['name']} | {a['papers']} | {yr} | "
                    f"{', '.join(a['gene_portfolio'][:5]) or '—'} |\n")

        f.write("\n## Strongest collaborations\n\n| Pair | Shared papers |\n|---|---|\n")
        for e in graph["co_author_edges"][:15]:
            f.write(f"| {e['a']} × {e['b']} | {e['papers']} |\n")

        # connected components = research clusters
        parent = {}
        def find(x):
            while parent.get(x, x) != x:
                x = parent[x]
            return x
        def union(x, y):
            parent.setdefault(x, x); parent.setdefault(y, y)
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
        for e in graph["co_author_edges"]:
            union(e["a"], e["b"])
        clusters = defaultdict(list)
        for a in author_nodes:
            clusters[find(a["name"])].append(a["name"])
        clusters = sorted(clusters.values(), key=len, reverse=True)
        f.write(f"\n## Research clusters (co-authorship components): {len(clusters)}\n\n")
        for i, c in enumerate(clusters[:12], 1):
            f.write(f"{i}. **{len(c)} authors**: {', '.join(sorted(c)[:10])}"
                    f"{'…' if len(c) > 10 else ''}\n")

        # gene specialists
        f.write("\n## Gene specialists (who studies what)\n\n")
        by_gene = defaultdict(list)
        for a in author_nodes:
            for g in a["gene_portfolio"]:
                by_gene[g].append(a["name"])
        for g in ["DDX58", "IFIH1", "ANP32A", "OASL", "MX1", "IFITM3", "STAT1", "PB2"]:
            who = sorted(by_gene.get(g, []))[:6]
            if who:
                f.write(f"- **{g}**: {', '.join(who)}\n")

    print(f"Authors: {len(author_nodes)} · papers: {len(paper_nodes)} · "
          f"co-author edges: {len(co_author)} · clusters: {len(clusters)}")
    print(f"→ {OUT_JSON}\n→ {OUT_MD}")


if __name__ == "__main__":
    main()
