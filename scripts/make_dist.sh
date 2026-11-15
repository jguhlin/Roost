#!/usr/bin/env bash
# make_dist.sh — build a self-contained distribution folder for remote hosting.
#
# Usage:
#   scripts/make_dist.sh                 # lean build (~150 MB): full site,
#                                        #   no genome FASTAs (IGV viewer off)
#   scripts/make_dist.sh --with-genomes  # + staged genomes (~4.3 GB): enables
#                                        #   the igv.js "genome context" views
#                                        #   (Phase 5: 2bit + gff only — the
#                                        #   plain/bgzip FASTAs are never
#                                        #   staged; was ~17 GB)
#
# Output: web/dist/ — upload its CONTENTS to any static host (S3, Netlify,
# nginx…). The app uses hash routing (#/home), so no server rewrite rules
# are needed. Host at the domain root, or rebuild with a subpath base:
#   npx vite build --base=/my/subpath/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/web"

WITH_GENOMES=0
[ "${1:-}" = "--with-genomes" ] && WITH_GENOMES=1

echo "==> cleaning web/dist"
rm -rf dist

# The staged genome files in public/data/genomes are symlinks into the local
# genome store (4.3 GB dereferenced: genome.2bit + annotation.gff.bgz[.tbi]).
# Default build excludes them; the
# dev server is unaffected (they are restored afterwards either way).
STAGING=".genomes-staging"
if [ -e public/data/genomes ]; then
  echo "==> temporarily hiding genome symlinks from the copy step"
  rm -rf "$STAGING"
  mv public/data/genomes "$STAGING"
fi
restore_genomes() {
  if [ -d "$STAGING" ]; then
    mv "$STAGING" public/data/genomes
    # Safety net: drop dangling links (data-side files pruned since the
    # last staging) — they would crash the next bare `vite build`.
    find public/data/genomes -xtype l -delete
    find public/data/genomes -mindepth 1 -type d -empty -delete
    echo "==> genome symlinks restored to public/data/genomes"
  fi
}
trap restore_genomes EXIT

echo "==> vite build"
npm run build

# maplibre v6 resolves its worker at runtime as ./maplibre-gl-worker.mjs
# relative to the bundle chunk (dynamic URL from import.meta.url) — invisible
# to the bundler, so it is never emitted. Ship worker + shared chunk manually.
cp node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs dist/assets/
cp node_modules/maplibre-gl/dist/maplibre-gl-shared.mjs dist/assets/

# public/wasm/ holds a 78 MB molecule-viewer bundle nothing in src/ imports
# (the viewer uses the 3Dmol CDN) — skip it in the distribution.
if [ -d dist/wasm ]; then
  echo "==> dropping unused wasm bundle (78 MB)"
  rm -rf dist/wasm
fi

if [ "$WITH_GENOMES" = 1 ]; then
  echo "==> copying genomes (.2bit reference — ~4.2 GB instead of 17 GB)"
  mkdir -p dist/data/genomes
  # Copy from the real store, not the staging dir — the staging symlinks are
  # relative and only resolve from public/data/genomes/<acc>/.
  # Only what the browser needs: 2bit reference sequence, bgzipped
  # annotation + tabix index. Plain and bgzipped FASTAs stay behind.
  # (Run scripts/genes/genomes_to_2bit.sh first if genome.2bit is missing.)
  rsync -a \
    --include='*/' \
    --include='genome.2bit' \
    --include='annotation.gff.bgz' --include='annotation.gff.bgz.tbi' \
    --exclude='*' "$ROOT/data/genomes/" dist/data/genomes/
  # rsync's --include='*/' leaves empty dir skeletons (blastdb, diamond_db…)
  find dist/data/genomes -mindepth 2 -type d -empty -delete
fi

echo
echo "==> dist ready: $(du -sh dist | cut -f1)"
echo "    index: dist/index.html"
if [ "$WITH_GENOMES" = 0 ]; then
  echo "    note: genome .2bit references not included — the igv.js 'Genome context' viewer will show its 'must be staged' notice; rerun with --with-genomes to embed them"
fi
