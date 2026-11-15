#!/usr/bin/env bash
# One-off: clone the reference/vendor repos for the figure system.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/vendor" 2>/dev/null || { echo "no vendor/ dir"; exit 1; }
repos=(
  pkt-lab/svg-diagram
  jgraph/drawio-mcp
  enesgul23/scientific-figure-skills
  SAADAT-Abu/Morphly
  duerrsimon/bioicons
  resolvetosavelives/healthicons
  dwzhu-pku/PaperBanana
  stuinfla/paperbanana
  llmsresearch/paperbanana
  ResearAI/AutoFigure-Edit
)
for r in "${repos[@]}"; do
  name="$(basename "$r")"
  if [ -d "$name/.git" ]; then echo "SKIP $name"; continue; fi
  if git clone --depth 1 "https://github.com/$r" "$name" >/dev/null 2>&1; then
    echo "OK   $name"
  else
    echo "FAIL $name"
  fi
done
du -sh */ 2>/dev/null | sort -h | tail -12
