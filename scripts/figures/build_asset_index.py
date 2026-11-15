#!/usr/bin/env python3
"""Build assets/manifest.sqlite (FTS5) from per-library manifest.json files.

Reads every assets/<lib>/manifest.json written by the Morphly fetchers
(vendor/Morphly/scraper) plus the Togo CSV if present, normalises entries
into a single SQLite index with a full-text-search table.

Re-run any time: the database is rebuilt from scratch (cheap, deterministic).
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
DB = ASSETS / "manifest.sqlite"

SCHEMA = """
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS asset_fts;
CREATE TABLE assets (
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,
  source_id TEXT,
  title TEXT NOT NULL,
  scientific_name TEXT DEFAULT '',
  description TEXT DEFAULT '',
  keywords TEXT DEFAULT '',
  category TEXT DEFAULT '',
  file_path TEXT NOT NULL,
  source_url TEXT DEFAULT '',
  license TEXT DEFAULT '',
  license_url TEXT DEFAULT '',
  author TEXT DEFAULT '',
  attribution TEXT DEFAULT '',
  requires_attribution INTEGER DEFAULT 0,
  share_alike INTEGER DEFAULT 0,
  public_domain INTEGER DEFAULT 0,
  commercial_ok INTEGER DEFAULT 1,
  collection TEXT DEFAULT '',
  citation TEXT DEFAULT ''
);
CREATE INDEX idx_assets_source ON assets(source);
CREATE VIRTUAL TABLE asset_fts USING fts5(
  title, description, keywords, scientific_name, category,
  content='assets', content_rowid='id', tokenize='porter unicode61'
);
"""

PD_PAT = re.compile(r"\b(cc0|public domain|pdm|cc-0)\b", re.I)
NC_PAT = re.compile(r"\b(nc|non[- ]?commercial)\b", re.I)
SA_PAT = re.compile(r"\b(by-?sa|share[- ]?alike)\b", re.I)
PERMISSIVE_PAT = re.compile(r"\b(cc0|public domain|mit|bsd|apache|pdm)\b", re.I)


def license_flags(license_label: str, share_alike: bool) -> tuple[bool, bool, bool, bool]:
    """→ (public_domain, share_alike, non_commercial, commercial_ok)."""
    label = license_label or ""
    pd = bool(PD_PAT.search(label))
    sa = share_alike or bool(SA_PAT.search(label))
    nc = bool(NC_PAT.search(label))
    commercial_ok = not sa and not nc
    return pd, sa, nc, commercial_ok


def norm_entry(e: dict, lib: str, lib_dir: Path) -> dict | None:
    files = []
    for group in e.get("local_files") or []:
        for fmt, rel in (group.get("files") or {}).items():
            if fmt.upper() == "SVG" and rel:
                files.append(rel)
    if not files:
        return None
    rel = files[0]
    path = lib_dir / rel
    if not path.exists():  # tolerate both lib-relative and repo-root-relative
        alt = ROOT / rel
        if alt.exists():
            path = alt
        else:
            return None
    lic = e.get("license", "")
    sa = bool(e.get("share_alike"))
    pd, sa, nc, ok = license_flags(lic, sa)
    kw = e.get("keywords") or []
    if isinstance(kw, str):
        kw = kw.split()
    return {
        "source": e.get("source") or lib,
        "source_id": e.get("id", ""),
        "title": e.get("title") or "Untitled",
        "scientific_name": e.get("scientific_name", "") or "",
        "description": e.get("description", "") or "",
        "keywords": " ".join(str(k) for k in kw),
        "category": e.get("category", "") or "",
        "file_path": str(path.relative_to(ROOT)),
        "source_url": e.get("source_page", "") or "",
        "license": lic,
        "license_url": e.get("license_url", "") or "",
        "author": e.get("creator", "") or "",
        "attribution": e.get("citation", "") or "",
        "requires_attribution": int(bool(e.get("requires_attribution"))),
        "share_alike": int(sa),
        "public_domain": int(pd),
        "commercial_ok": int(ok),
        "collection": e.get("collection", "") or "",
        "citation": e.get("citation", "") or "",
    }


def load_togo(togo_dir: Path) -> list[dict]:
    """Togo Picture Gallery: manual zip + CSV (see docs/FIGURE_AGENT.md §9.4)."""
    rows: list[dict] = []
    csvs = list(togo_dir.rglob("*.csv"))
    if not csvs:
        return rows
    svg_root = togo_dir
    for cand in (togo_dir / "svg_format", togo_dir / "svg", togo_dir):
        if cand.is_dir():
            svg_root = cand
    with open(csvs[0], encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            pid = (row.get("Picture ID") or row.get("picture_id") or "").strip()
            if not pid:
                continue
            matches = list(svg_root.rglob(f"*{pid}*.svg")) or list(svg_root.rglob(f"*{pid}*.SVG"))
            if not matches:
                continue
            title = row.get("Title (en)") or row.get("Title (jp)") or pid
            rows.append({
                "source": "togo",
                "source_id": f"togo:{pid}",
                "title": title,
                "scientific_name": row.get("Scientific Name", "") or "",
                "description": "",
                "keywords": row.get("Tags", "") or "",
                "category": "Life science",
                "file_path": str(matches[0].relative_to(ROOT)),
                "source_url": "https://dbarchive.biosciencedbc.jp/data/togo-pic/",
                "license": "CC BY 4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "author": "DBCLS TogoTV",
                "attribution": "© 2016 DBCLS TogoTV / CC-BY-4.0",
                "requires_attribution": 1,
                "share_alike": 0,
                "public_domain": 0,
                "commercial_ok": 1,
                "collection": "Togo Picture Gallery",
                "citation": "© 2016 DBCLS TogoTV / CC-BY-4.0 "
                            "(https://dbarchive.biosciencedbc.jp/en/togo-pic/lic.html)",
            })
    return rows


def main() -> int:
    if not ASSETS.is_dir():
        print("no assets/ directory — run scripts/figures/mirror_assets.sh first", file=sys.stderr)
        return 1
    entries: list[dict] = []
    for lib_dir in sorted(p for p in ASSETS.iterdir() if p.is_dir()):
        manifest = lib_dir / "manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for e in data:
                n = norm_entry(e, lib_dir.name, lib_dir)
                if n:
                    entries.append(n)
        elif lib_dir.name == "togo":
            entries.extend(load_togo(lib_dir))
    if not entries:
        print("no manifest entries found — nothing to index", file=sys.stderr)
        return 1

    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    cols = [k for k in entries[0]]
    con.executemany(
        f"INSERT INTO assets ({','.join(cols)}) VALUES ({','.join(':' + c for c in cols)})",
        entries,
    )
    con.execute(
        "INSERT INTO asset_fts(rowid, title, description, keywords, scientific_name, category) "
        "SELECT id, title, description, keywords, scientific_name, category FROM assets"
    )
    con.commit()

    by_source: dict[str, int] = {}
    by_license: dict[str, int] = {}
    for e in entries:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
        by_license[e["license"] or "unknown"] = by_license.get(e["license"] or "unknown", 0) + 1
    print(f"indexed {len(entries)} assets → {DB.relative_to(ROOT)}")
    for s, n in sorted(by_source.items()):
        print(f"  {n:>6}  {s}")
    print("licenses:")
    for l, n in sorted(by_license.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>6}  {l}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
