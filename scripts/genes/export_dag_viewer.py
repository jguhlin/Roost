#!/usr/bin/env python3
"""Export share-safe DAG envelopes for the website's verso DAG viewer embeds.

Reads the committed verso pipeline packages and writes static graph-only
documents to web/public/data/:

  dag_gene_panel_intake.json    — the §12 panel-finding method
  dag_gene_panel_presence.json  — the 15..N species presence search

Sanitisation: command templates, params, scripts, and resources are stripped
(they contain absolute host paths and inline code — not for the public site);
only the scientific structure survives — nodes with labels/descriptions,
ports, expected outputs (deliverable roles), and edges. Node positions are
computed as a left-to-right layered layout (packages store 0,0 placeholders).
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web" / "public" / "data"
PKGS = {
    "dag_gene_panel_intake.json": ROOT / "verso_workspace" / "gene_panel_intake.biopipe.json",
    "dag_gene_panel_presence.json": ROOT / "verso_workspace" / "presence" / "gene_panel_presence.biopipe.json",
}

KEEP_NODE_FIELDS = ("id", "label", "description", "tool", "node_type",
                    "input_ports", "output_ports", "expected_outputs", "format")


def layered_positions(dag: dict) -> dict[str, dict]:
    """DEPRECATED as shipped layout: the 300×160 grid overlaps the viewer's
    ~480×200 rendered nodes (user report 2026-11: stacked/overlapping
    workflow diagrams). Positions are no longer written — the verso viewer
    runs its own automatic layout when nodes carry no coordinates.
    Kept for reference/debugging only."""
    nodes, edges = dag["nodes"], dag["edges"]
    indeg = {nid: 0 for nid in nodes}
    out = defaultdict(list)
    for e in edges:
        out[e["source"]].append(e["target"])
        indeg[e["target"]] += 1
    col = {nid: 0 for nid in nodes}
    frontier = sorted(n for nid, d in indeg.items() if d == 0 for n in [nid])
    queue = list(frontier)
    while queue:
        nid = queue.pop(0)
        for t in out[nid]:
            col[t] = max(col[t], col[nid] + 1)
            indeg[t] -= 1
            if indeg[t] == 0:
                queue.append(t)
    by_col = defaultdict(list)
    for nid, c in col.items():
        by_col[c].append(nid)
    pos = {}
    for c, nids in by_col.items():
        for i, nid in enumerate(sorted(nids)):
            pos[nid] = {"x": c * 300.0, "y": i * 160.0}
    return pos


def export(pkg_path: Path, out_path: Path, title: str, subtitle: str) -> None:
    pkg = json.loads(pkg_path.read_text())
    dag = pkg["definition"]["dag"]
    _ = layered_positions  # deprecated (see docstring); kept importable
    nodes = []
    for nid, n in dag["nodes"].items():
        node = {k: n.get(k) for k in KEEP_NODE_FIELDS if n.get(k) not in (None, [], "")}
        node["id"] = nid
        if "expected_outputs" in node:
            node["expected_outputs"] = [
                {k: o.get(k) for k in ("port", "role") if o.get(k) is not None}
                for o in node["expected_outputs"]
            ]
        # NOTE: no "position" — the viewer auto-layouts unpositioned nodes
        nodes.append(node)
    edges = [{"source": e["source"], "target": e["target"],
              "source_port": e.get("source_port"), "target_port": e.get("target_port")}
             for e in dag["edges"]]
    completion = dag.get("completion") or {}
    doc = {
        "title": title,
        "subtitle": subtitle,
        "dag": {
            "name": dag.get("name"),
            "description": dag.get("description"),
            "nodes": nodes,
            "edges": edges,
            "completion": {
                "objective": completion.get("objective"),
                "deliverables": [
                    {"id": d.get("id"), "label": d.get("label"),
                     "node_id": d.get("node_id"), "port_id": d.get("port_id")}
                    for d in completion.get("deliverables", [])
                ],
            },
        },
    }
    out_path.write_text(json.dumps(doc, indent=1))
    print(f"{out_path.name}: {len(nodes)} nodes / {len(edges)} edges")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    export(
        PKGS["dag_gene_panel_intake.json"],
        OUT / "dag_gene_panel_intake.json",
        "Gene panel intake — collision-first discovery",
        "docs/GENE_PANEL.md §12: literature-discovered genes are normalised, "
        "noise-filtered, and resolved against the panel, existing searches, "
        "and annotation before any genome search is queued.",
    )
    export(
        PKGS["dag_gene_panel_presence.json"],
        OUT / "dag_gene_panel_presence.json",
        "Gene panel presence search",
        "Coverage-aware genome search: targets are genes lacking calls on any "
        "manifest genome; references resolve via NCBI; batch BLAST/DIAMOND "
        "assigns FULL/FRAGMENT/NOT_FOUND with searchability; export is gated "
        "on complete species and target coverage.",
    )


if __name__ == "__main__":
    main()
