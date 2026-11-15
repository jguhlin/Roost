#!/usr/bin/env bash
# genomes_to_2bit.sh — convert all staged genome FASTAs to UCSC .2bit.
#
# .2bit packs 4 bases/byte (~4:1) with N-run blocks and is natively
# random-accessible — igv.js reads it via range requests (reference.twoBitURL),
# so the genome browser still fetches only the viewed region. The genome
# browser prefers genome.2bit when present (see GenomeBrowser.svelte).
#
# Creates data/genomes/<assembly>/genome.2bit and symlinks it into
# web/public/data/genomes/ for the dev server. Idempotent.
#
# KEEP_GENOMES-aware: if only genome.fna.zst exists (archived genome),
# decompresses on demand, converts, then re-removes the plain FASTA —
# the zst archive is the storage format, the 2bit the served format.
#
# Optional args: specific accessions, e.g.
#   scripts/genes/genomes_to_2bit.sh GCA_003342965.1 GCA_013398075.1
# (default: all genome dirs)
#
# Validate one file any time with:
#   python scripts/genes/fa_to_2bit.py genome.fna genome.2bit.check --verify
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GENOMES="$ROOT/data/genomes"
PARALLEL="${T2B_PARALLEL:-3}"
ZSTD="$(command -v zstd || echo "$ROOT/.pixi/envs/default/bin/zstd")"

convert_one() {
  d="$1"; acc="$(basename "$d")"
  decompressed=0
  if [ -s "$d/genome.2bit" ]; then
    echo "· $acc: already converted, skipping"
  elif [ -e "$d/genome.fna" ]; then
    echo "· $acc: converting…"
    python3 "$ROOT/scripts/genes/fa_to_2bit.py" "$d/genome.fna" "$d/genome.2bit"
  elif [ -e "$d/genome.fna.zst" ]; then
    echo "· $acc: no plain FASTA — decompressing genome.fna.zst on demand"
    "$ZSTD" -d -q "$d/genome.fna.zst" -o "$d/genome.fna"
    decompressed=1
    echo "· $acc: converting…"
    python3 "$ROOT/scripts/genes/fa_to_2bit.py" "$d/genome.fna" "$d/genome.2bit" \
      || { rm -f "$d/genome.fna"; echo "! $acc: conversion failed" >&2; return 0; }
  else
    echo "· $acc: no FASTA (plain or archived), skipping" >&2
  fi
  if [ "$decompressed" = 1 ]; then
    rm -f "$d/genome.fna"  # zst archive remains; plain FASTA never stays
  fi
  pub="$ROOT/web/public/data/genomes/$acc"
  if [ -s "$d/genome.2bit" ]; then
    mkdir -p "$pub"
    # ln -sfn: idempotent — relinks stale links instead of erroring
    ln -sfn "../../../../../data/genomes/$acc/genome.2bit" "$pub/genome.2bit"
  elif [ -L "$pub/genome.2bit" ] && [ ! -e "$pub/genome.2bit" ]; then
    # data-side 2bit was pruned — drop the dangling public link
    # (dangling symlinks crash `vite build`'s public-dir copy step)
    rm "$pub/genome.2bit"
  fi
}
export -f convert_one
export ROOT GENOMES ZSTD

if [ "$#" -gt 0 ]; then
  # targeted re-run: explicit accession list
  printf '%s\n' "$@" | xargs -I{} -P "$PARALLEL" bash -c 'convert_one "$GENOMES/$1"' _ {}
else
  find "$GENOMES" -mindepth 1 -maxdepth 1 -type d | sort \
    | xargs -I{} -P "$PARALLEL" bash -c 'convert_one "$@"' _ {}
fi

echo "done."
