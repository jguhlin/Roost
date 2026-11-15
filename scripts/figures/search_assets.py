#!/usr/bin/env python3
"""Search the local scientific asset index (assets/manifest.sqlite, FTS5).

Returns compact JSON (title, source, path, license, attribution, score) so a
coding agent can pick assets without loading SVG content into context.

  python3 scripts/figures/search_assets.py --query "bird chromosome" \
      --license-priority permissive --limit 12

  python3 scripts/figures/search_assets.py \
      --import assets/reactome/cell/chromosome-1.svg --figure fig-methods
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "assets" / "manifest.sqlite"

FTS_FIELDS = "title, description, keywords, scientific_name, category"
# license preference: lower = better (permissive first)
PRIORITY = {"public_domain": 0, "permissive": 1, "cc_by": 2, "other": 3}
LICENSE_CLASS_SQL = (
    "CASE WHEN public_domain=1 THEN 0 "
    "WHEN public_domain=0 AND share_alike=0 AND commercial_ok=1 "
    "     AND (license LIKE '%CC BY%' OR license LIKE '%cc by%') THEN 2 "
    "WHEN share_alike=0 AND commercial_ok=1 AND license != '' THEN 1 "
    "ELSE 3 END"
)


SPECIES_ALIAS_MAP = None


def _load_species_aliases():
    """Lazy-load the corpus species alias map (common name → scientific)."""
    global SPECIES_ALIAS_MAP
    if SPECIES_ALIAS_MAP is None:
        SPECIES_ALIAS_MAP = {}
        p = ROOT / "data" / "papers" / "species_alias_map.json"
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                for k, v in raw.items():
                    if isinstance(v, dict) and v.get("canonical"):
                        SPECIES_ALIAS_MAP[k.lower().replace("-", " ")] = v["canonical"].lower()
            except (json.JSONDecodeError, OSError):
                pass
    return SPECIES_ALIAS_MAP


def fts_expr(query: str) -> str:
    terms = [t for t in re.split(r"[^A-Za-z0-9]+", query.lower()) if len(t) >= 2]
    if not terms:
        raise SystemExit("query has no usable terms")
    # common-name → scientific-name expansion via the corpus alias map:
    # "bar-headed goose" also matches phylopic's "Anser indicus" title
    aliases = _load_species_aliases()
    extra: list[str] = []
    for i in range(len(terms)):
        for j in range(i + 1, min(i + 4, len(terms)) + 1):
            phrase = " ".join(terms[i:j])
            sci = aliases.get(phrase)
            if sci:
                extra += [w for w in sci.split() if w not in terms and len(w) >= 3]
    terms += extra
    if extra:
        # alias terms are OR-alternates to the original phrase, not required
        core = [t for t in terms if t not in extra]
        alt = " OR ".join(f'"{t}"*' for t in extra)
        return "(" + " AND ".join(f'"{t}"*' for t in core) + ") OR (" + alt + ")"
    return " AND ".join(f'"{t}"*' for t in terms)


def search(args: argparse.Namespace) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    sql = (
        f"SELECT a.*, bm25(asset_fts) AS rank, {LICENSE_CLASS_SQL} AS lic_class "
        f"FROM asset_fts JOIN assets a ON a.id = asset_fts.rowid "
        f"WHERE asset_fts MATCH ? "
    )
    params: list = [fts_expr(args.query)]
    conds = []
    if args.sources:
        conds.append(f"source IN ({','.join('?' * len(args.sources))})")
        params.extend(args.sources)
    if args.require_commercial_ok:
        conds.append("commercial_ok = 1")
    if args.no_share_alike:
        conds.append("share_alike = 0")
    if conds:
        sql += " AND " + " AND ".join(conds)
    order = ", lic_class ASC" if args.license_priority else ""
    sql += f" ORDER BY rank ASC{order} LIMIT ?"
    params.append(args.limit)
    rows = [dict(r) for r in con.execute(sql, params).fetchall()]
    con.close()
    out = []
    for r in rows:
        out.append({
            "title": r["title"],
            "source": r["source"],
            "category": r["category"],
            "path": r["file_path"],
            "license": r["license"] or "unknown",
            "requires_attribution": bool(r["requires_attribution"]),
            "share_alike": bool(r["share_alike"]),
            "commercial_ok": bool(r["commercial_ok"]),
            "attribution": (r["attribution"] or "")[:160],
            "score": round(1.0 / (1.0 + abs(r["rank"])), 3),
        })
    return out


def import_asset(path: str, figure: str) -> dict:
    """Copy an asset SVG into figures/src/assets/<figure>/ and record provenance."""
    src = (ROOT / path).resolve()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM assets WHERE file_path = ?", (str(src.relative_to(ROOT)),)).fetchone()
    con.close()
    if row is None:
        raise SystemExit(f"asset not in index: {path}")
    dest_dir = ROOT / "figures" / "src" / "assets" / figure
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    record = {
        "asset_id": row["source_id"],
        "title": row["title"],
        "source": row["source"],
        "source_url": row["source_url"],
        "original_path": row["file_path"],
        "imported_path": str(dest.relative_to(ROOT)),
        "author": row["author"],
        "license": row["license"],
        "license_url": row["license_url"],
        "attribution": row["attribution"] or row["citation"],
        "requires_attribution": bool(row["requires_attribution"]),
        "share_alike": bool(row["share_alike"]),
        "commercial_ok": bool(row["commercial_ok"]),
        "modified": False,
    }
    manifest_path = ROOT / "figures" / "manifests" / f"{figure}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            manifest = {}
    assets = manifest.setdefault("assets", [])
    if not any(a.get("imported_path") == record["imported_path"] for a in assets):
        assets.append(record)
    manifest["figure"] = manifest.get("figure", figure)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", help="keyword query, e.g. 'bird chromosome sequencing'")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--license-priority", action="store_true",
                    help="order results CC0/PD → permissive → CC BY")
    ap.add_argument("--source", dest="sources", action="append",
                    help="restrict to source (repeatable: bioicons, reactome, …)")
    ap.add_argument("--require-commercial-ok", action="store_true")
    ap.add_argument("--no-share-alike", action="store_true", dest="no_share_alike",
                    default=True)
    ap.add_argument("--import", dest="import_path", metavar="PATH",
                    help="import an indexed asset into a figure workspace")
    ap.add_argument("--figure", help="figure name for --import")
    args = ap.parse_args()

    if not DB.exists():
        raise SystemExit("assets/manifest.sqlite missing — run scripts/figures/build_asset_index.py")
    if args.import_path:
        if not args.figure:
            raise SystemExit("--import requires --figure NAME")
        import_asset(args.import_path, args.figure)
        return 0
    if not args.query:
        ap.error("--query is required unless --import is used")
    results = search(args)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
