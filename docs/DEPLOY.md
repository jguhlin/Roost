# DEPLOY — shipping a Roost distribution to the live host

Live site: **https://josephguhlin.com/Roost/** (hash-routed SPA — no server
rewrite rules needed; upload the dist CONTENTS to the docroot).

Host: **`$ROOST_DEPLOY_HOST`** (machine-local env var, never committed),
docroot `public_html/Roost/`.
SSH key auth (BatchMode) — the key is unlocked per-session by the operator;
nobody else ever gets the passphrase.

## One-command deploy

```bash
scripts/deploy_dist.sh            # build (lean) + upload + unzip + verify
scripts/deploy_dist.sh --no-build # deploy an existing web/dist
scripts/deploy_dist.sh --with-genomes  # + genome .2bit views (~4.5 GB zip)
```

## The procedure, step by step (what the script does)

### 0. Preconditions
- Clean working tree state for `web/public/data` (artifacts fresh:
  `pixi run export-web` run after any pipeline stage; by-the-numbers green)
- `ROOST_DEPLOY_HOST` exported (see below) and SSH key unlocked
  (test: `ssh -o BatchMode=yes "$ROOST_DEPLOY_HOST" echo ok`)

### 1. Build the distribution
```bash
scripts/make_dist.sh              # → web/dist/ (lean ~470 MB unpacked)
```
Genome-symlink handling, maplibre worker copy, wasm-bundle skip are all in
the script. `--with-genomes` embeds the IGV 2bit views.

### 2. Package
```bash
cd web/dist && zip -qr ../roost-beta-dist-$(date +%Y%m%d).zip . -x ".*" && cd ..
# → web/roost-beta-dist-YYYYMMDD.zip (~134 MB lean)
```
Spot-verify BEFORE upload (bad builds are cheap to catch here):
```bash
unzip -p web/roost-beta-dist-*.zip data/stats.json   # fresh numbers?
unzip -l web/roost-beta-dist-*.zip | tail -1         # ~28k files
```

### 3. Upload
```bash
sftp -o BatchMode=yes -b - "$ROOST_DEPLOY_HOST" << EOF
put web/roost-beta-dist-YYYYMMDD.zip public_html/Roost/
EOF
```

### 4. Unzip IN PLACE (atomic-ish overlay)
```bash
ssh -o BatchMode=yes "$ROOST_DEPLOY_HOST" \
  "cd public_html/Roost && unzip -o roost-beta-dist-YYYYMMDD.zip && rm roost-beta-dist-YYYYMMDD.zip"
```
`-o` overwrites without prompting. index.html flips to the new build on
overwrite; hashed assets are additive (old ones linger — see cleanup).

### 5. Verify the live site
```bash
curl -s https://josephguhlin.com/Roost/ | head -c 200        # new index.html
curl -s https://josephguhlin.com/Roost/data/stats.json        # fresh generated stamp
curl -sI https://josephguhlin.com/Roost/data/bird_of_the_day.json  # 200
```
Then click around in a real browser (home Bird of the Day, a species page,
the map).

## Maintenance notes

- **Stale hashed assets accumulate**: every deploy adds `assets/*.js|css`
  with new content hashes; old ones are never referenced again. Occasional
  cleanup on the host:
  ```bash
  ssh "$ROOST_DEPLOY_HOST" "cd public_html/Roost/assets && \
    ls | grep -E '\.(js|css)' | wc -l"   # count; prune old when large
  ```
- **Rollback**: re-run steps 3–4 with the PREVIOUS zip (keep the last few
  `roost-beta-dist-*.zip` files locally; the zip is the rollback artifact).
  Data-level rollback = rebuild dist from earlier artifacts + redeploy.
- **Genome-enabled deploys** (~4.5 GB): same flow; the upload window is much
  longer — run inside `tmux`/background so a dropped shell doesn't kill sftp.
- **Naming**: `roost-beta-dist-YYYYMMDD.zip` (drop `-beta` when the site
  graduates; keep the date-stamped scheme — it IS the rollback history).
