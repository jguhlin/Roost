#!/usr/bin/env bash
# Mirror Togo Picture Gallery (DBCLS) and Servier Medical Art.
#
# Togo:   https://dbarchive.biosciencedbc.jp/data/togo-pic/image/
#         (svg_format.zip is gone; the directory listing serves files directly)
#         License: © DBCLS TogoTV, CC BY 4.0 — attribution required.
# Servier: https://smart.servier.com/wp-content/uploads/ServierMedicalArt-all-kits.zip
#         License: CC BY 4.0 — attribution required ("Image(s) provided by
#         Servier Medical Art, https://smart.servier.com, CC BY 4.0").
#
# Outputs: assets/togo/*.svg + assets/togo/manifest.json
#          assets/servier/**/SVG/**/*.svg + assets/servier/manifest.json
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"
mkdir -p assets/togo assets/servier download_tmp

# ---------------- Togo Picture Gallery ----------------
TOGO_URL="https://dbarchive.biosciencedbc.jp/data/togo-pic/image/"
if [ ! -f assets/togo/manifest.json ]; then
  echo "== Togo: listing $TOGO_URL"
  curl -s "$TOGO_URL" \
    | grep -o 'href="[^"]*\.svg"' | sed 's/href="//;s/"//' \
    | grep -v '^?' > download_tmp/togo_svgs.txt
  echo "   $(wc -l < download_tmp/togo_svgs.txt) SVG files"
  while read -r f; do
    out="assets/togo/$f"
    [ -s "$out" ] && continue
    curl -sf --retry 3 -o "$out" "$TOGO_URL/$f"
    sleep 0.15
  done < download_tmp/togo_svgs.txt
fi

# ---------------- Servier Medical Art ----------------
SERVIER_ZIP="https://smart.servier.com/wp-content/uploads/ServierMedicalArt-all-kits.zip"
SERVIER_MARKER="assets/servier/.slides_converted"
if [ ! -f "$SERVIER_MARKER" ]; then
  echo "== Servier: downloading all-kits zip (~165 MB)"
  curl -sfL --retry 3 -C - -o download_tmp/ServierMedicalArt-all-kits.zip "$SERVIER_ZIP"
  echo "   extracting SVG subset (nested: 49 kits as PPTX)"
  # The all-kits zip contains one .pptx per category; each PPTX is itself a
  # zip whose ppt/media/*.svg are the vector sources (PNGs are fallbacks).
  python3 - <<'PY'
import io, os, re, zipfile
z = zipfile.ZipFile("download_tmp/ServierMedicalArt-all-kits.zip")
n_svg = 0
for kit in z.namelist():
    if not kit.lower().endswith(".pptx"):
        continue
    cat = re.sub(r"^SMART-", "", os.path.splitext(kit)[0])
    cat = re.sub(r"[^a-z0-9-]+", "-", cat.lower()).strip("-")
    inner = zipfile.ZipFile(io.BytesIO(z.read(kit)))
    outdir = os.path.join("assets", "servier", cat)
    os.makedirs(outdir, exist_ok=True)
    for m in inner.namelist():
        if m.lower().endswith(".svg"):
            with open(os.path.join(outdir, os.path.basename(m)), "wb") as f:
                f.write(inner.read(m))
            n_svg += 1
print(f"   {n_svg} SVGs extracted from 49 kits")
PY
  # Most kit art is native PowerPoint shapes, one illustration per slide.
  # Convert those too: PPTX -> PDF (LibreOffice) -> per-page SVG (pdftocairo).
  python3 - <<'PY'
import io, os, re, zipfile
z = zipfile.ZipFile("download_tmp/ServierMedicalArt-all-kits.zip")
kits = [k for k in z.namelist() if k.lower().endswith(".pptx")]
for k in kits:
    cat = re.sub(r"^SMART-", "", os.path.splitext(k)[0])
    cat = re.sub(r"[^a-z0-9-]+", "-", cat.lower()).strip("-")
    open(f"download_tmp/{os.path.basename(k)}", "wb").write(z.read(k))
print(f"   {len(kits)} kits staged for slide conversion")
PY
  mkdir -p download_tmp/servier_pdf
  for pptx in download_tmp/*.pptx; do
    base="$(basename "$pptx" .pptx)"
    cat="$(echo "${base#SMART-}" | tr 'A-Z_' 'a-z-' | sed 's/[^a-z0-9-]*//g; s/^-\+//; s/-\+$//')"
    [ -d "assets/servier/$cat" ] || { echo "   ?? no dir for $cat ($base)"; continue; }
    timeout 300 soffice --headless -env:UserInstallation=file:///tmp/lo_servier \
      --convert-to pdf --outdir download_tmp/servier_pdf "$pptx" >/dev/null 2>&1
    pdf="download_tmp/servier_pdf/$base.pdf"
    [ -s "$pdf" ] || { echo "   !! pdf failed: $base"; continue; }
    n=$(pdfinfo "$pdf" | awk '/^Pages:/{print $2}')
    for p in $(seq 1 "$n"); do
      out="assets/servier/$cat/$cat-$(printf %02d "$p").svg"
      pdftocairo -svg -f "$p" -l "$p" "$pdf" "$out" 2>/dev/null
    done
    echo "   $cat: $n slides"
  done
  # drop blank/cover pages (no vector content)
  python3 - <<'PY'
import glob, os
removed = 0
for f in glob.glob("assets/servier/*/*-*.svg"):
    try:
        s = open(f, encoding="utf-8", errors="ignore").read()
    except OSError:
        continue
    if "<path" not in s and "<image" not in s and len(s) < 6000:
        os.remove(f); removed += 1
print(f"   removed {removed} blank/cover pages")
PY
  touch "$SERVIER_MARKER"
fi

echo "== building manifests"
python3 scripts/figures/build_togo_servier_manifest.py

echo "== done"
du -sh assets/togo assets/servier 2>/dev/null || true
