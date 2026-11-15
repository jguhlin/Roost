#!/usr/bin/env bash
# Mirror all open scientific asset libraries into assets/ using the Morphly fetchers.
# Bounded: resume/re-run safe. Disk-light: SVG only.
# Manual downloads NOT handled here (registration/download UI):
#   Togo   → assets/togo/       (svg_format.zip from dbarchive.biosciencedbc.jp)
#   Servier→ assets/servier/    (pack zip from smart.servier.com)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRAPER="$ROOT/vendor/Morphly/scraper"
OUT="$ROOT/assets"
PY="${PYTHON:-python3}"

[ -d "$SCRAPER" ] || { echo "vendor/Morphly missing — git clone SAADAT-Abu/Morphly first"; exit 1; }
mkdir -p "$OUT"

run() { # name, cmd...
  local name="$1"; shift
  echo "=== $name ==="
  "$@" 2>&1 | tail -4
}

# One tarball download, quick
run reactome    "$PY" "$SCRAPER/reactome_fetcher.py"    --out "$OUT/reactome"
run healthicons "$PY" "$SCRAPER/healthicons_fetcher.py" --out "$OUT/healthicons"
# Site crawls, slower
run bioicons    "$PY" "$SCRAPER/bioicons_fetcher.py"    --out "$OUT/bioicons"
run phylopic    "$PY" "$SCRAPER/phylopic_fetcher.py"    --out "$OUT/phylopic" --limit "${PHYLOPIC_LIMIT:-2500}"
# Bounded ranges; increase --end later to extend
run nih-bioart  "$PY" "$SCRAPER/bioart_scraper.py"      --start 1 --end "${BIOART_END:-600}" --out "$OUT/nih-bioart"
run scidraw     "$PY" "$SCRAPER/scidraw_fetcher.py"     --out "$OUT/scidraw"

echo "=== rebuilding index ==="
"$PY" "$ROOT/scripts/figures/build_asset_index.py"
"$PY" "$ROOT/scripts/figures/build_attribution.py" --rollup
echo "DONE mirror_assets"
