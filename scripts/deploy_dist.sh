#!/usr/bin/env bash
# deploy_dist.sh — build, upload, and unzip a Roost distribution in place.
# See docs/DEPLOY.md for the full procedure and maintenance notes.
#
# Usage:
#   scripts/deploy_dist.sh [--no-build] [--with-genomes]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Deploy target is machine-local config, never committed.
# Set ROOST_DEPLOY_HOST (e.g. in ~/.bashrc or a direnv) before deploying.
HOST="${ROOST_DEPLOY_HOST:-}"
REMOTE_DIR="public_html/Roost"
STAMP="$(date +%Y%m%d)"
ZIP="$ROOT/web/roost-beta-dist-$STAMP.zip"

NO_BUILD=0
GENOMES=""
for arg in "$@"; do
  case "$arg" in
    --no-build) NO_BUILD=1 ;;
    --with-genomes) GENOMES="--with-genomes" ;;
  esac
done

echo "==> preflight: ssh key + host"
if [[ -z "$HOST" ]]; then
  echo "FAIL: ROOST_DEPLOY_HOST is not set (user@host for the deploy server)." >&2
  echo "       Export it locally, e.g. in ~/.bashrc — never commit the value." >&2
  exit 1
fi
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "echo ok" >/dev/null

if [ "$NO_BUILD" = 0 ]; then
  echo "==> building distribution$GENOMES"
  bash "$ROOT/scripts/make_dist.sh" $GENOMES
fi

if [ ! -d "$ROOT/web/dist" ] || [ ! -f "$ROOT/web/dist/index.html" ]; then
  echo "FAIL: web/dist missing — run without --no-build" >&2
  exit 1
fi

if [ "$NO_BUILD" = 0 ] || [ ! -f "$ZIP" ]; then
  echo "==> packaging $ZIP"
  (cd "$ROOT/web/dist" && zip -qr "$ZIP" . -x ".*")
fi

echo "==> verifying package"
unzip -p "$ZIP" data/stats.json | head -c 200; echo

echo "==> uploading ($(du -h "$ZIP" | cut -f1))"
sftp -o BatchMode=yes -b - "$HOST" <<EOF
put "$ZIP" "$REMOTE_DIR/$(basename "$ZIP")"
EOF

echo "==> unzipping in place"
ssh -o BatchMode=yes "$HOST" "cd $REMOTE_DIR && unzip -o $(basename "$ZIP") && rm $(basename "$ZIP")"

echo "==> live verification"
sleep 2
curl -sf "https://josephguhlin.com/Roost/data/stats.json" | head -c 200; echo
echo
echo "deployed: https://josephguhlin.com/Roost/  ($STAMP)"
