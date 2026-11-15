#!/usr/bin/env bash
# bgzip_genomes.sh — bgzip-compress the staged genome FASTAs in place.
#
# BGZF (bgzip) keeps the file randomly accessible through a .gzi block
# index, which igv.js consumes via reference.compressedIndexURL — so the
# genome browser still fetches only the viewed region instead of streaming
# the whole 1+ GB file. Typical FASTA ratio ≈ 3:1.
#
# For each data/genomes/<assembly>/genome.fna this creates:
#   genome.fna.gz        (bgzf; ~1/3 the size)
#   genome.fna.gz.gzi    (block index for random access)
# and keeps genome.fna and genome.fna.fai untouched (fai offsets are in
# uncompressed coordinates — igv combines it with the gzi).
#
# Idempotent: skips assemblies already compressed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GENOMES="$ROOT/data/genomes"

THREADS="${BGZIP_THREADS:-4}"
PARALLEL="${BGZIP_PARALLEL:-2}"

compress_one() {
  local d="$1"
  local acc
  acc="$(basename "$d")"
  if [ -s "$d/genome.fna.gz" ] && [ -s "$d/genome.fna.gz.gzi" ]; then
    echo "· $acc: already compressed, skipping"
    return 0
  fi
  if [ ! -e "$d/genome.fna" ]; then
    echo "! $acc: no genome.fna, skipping" >&2
    return 0
  fi
  echo "· $acc: compressing…"
  bgzip -@ "$THREADS" -i -k -c "$d/genome.fna" > "$d/genome.fna.gz"
  echo "  $(basename "$(readlink -f "$d/genome.fna")"): $(du -hL "$d/genome.fna" | cut -f1) -> $(du -h "$d/genome.fna.gz" | cut -f1)"
  # Phase 5 (DATA_MATURATION): no website staging for the bgzf fasta —
  # nothing on the site fetches genome.fna.gz (the browser uses genome.2bit).
  # The interior copy stays as a pipeline artifact.
}
export -f compress_one
export THREADS

find "$GENOMES" -mindepth 1 -maxdepth 1 -type d | sort \
  | xargs -I{} -P "$PARALLEL" bash -c 'compress_one "$@"' _ {}

echo "done."
