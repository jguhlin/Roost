#!/usr/bin/env python3
"""Render a figure source → preview PNG (and exports).

  figures/src/<fig>.svg   → rsvg-convert → figures/preview/<fig>.png
                            --export also writes figures/export/<fig>.{svg,pdf,png}
  figures/src/<fig>.drawio→ draw.io Desktop CLI if installed (else instructions)
  figures/src/<fig>.py    → executed (the script itself writes its outputs)

The editable source stays authoritative; everything here is derived output.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "figures" / "src"
PREVIEW = ROOT / "figures" / "preview"
EXPORT = ROOT / "figures" / "export"
PREVIEW_WIDTH = 1600
EXPORT_WIDTH = 2400


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def render_svg(path: Path, fig: str, export: bool) -> int:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    png = PREVIEW / f"{fig}.png"
    r = run(["rsvg-convert", "-w", str(PREVIEW_WIDTH), "-o", str(png), str(path)])
    if r.returncode != 0:
        print(f"rsvg-convert failed:\n{r.stderr}", file=sys.stderr)
        return 1
    print(f"preview → {png.relative_to(ROOT)}")
    if export:
        EXPORT.mkdir(parents=True, exist_ok=True)
        svg_out = EXPORT / f"{fig}.svg"
        shutil.copy2(path, svg_out)
        pdf_out = EXPORT / f"{fig}.pdf"
        r = run(["rsvg-convert", "-f", "pdf", "-o", str(pdf_out), str(path)])
        if r.returncode != 0:
            print(f"warning: PDF export failed: {r.stderr.strip()}", file=sys.stderr)
        png_out = EXPORT / f"{fig}.png"
        r = run(["rsvg-convert", "-w", str(EXPORT_WIDTH), "-o", str(png_out), str(path)])
        if r.returncode != 0:
            print(f"warning: export PNG failed: {r.stderr.strip()}", file=sys.stderr)
        print(f"export  → {EXPORT.relative_to(ROOT)}/{fig}.{{svg,pdf,png}}")
    return 0


def render_drawio(path: Path, fig: str, export: bool) -> int:
    cli = shutil.which("drawio")
    if not cli:
        for cand in ("/usr/bin/drawio", "/opt/drawio/drawio",
                     str(Path.home() / "Applications/draw.io.app/Contents/MacOS/drawio")):
            if Path(cand).exists():
                cli = cand
                break
    if not cli:
        print("draw.io Desktop CLI not found. Install draw.io Desktop, then re-run.\n"
              "The .drawio source is still valid and editable at:\n"
              f"  {path.relative_to(ROOT)}", file=sys.stderr)
        return 2
    PREVIEW.mkdir(parents=True, exist_ok=True)
    png = PREVIEW / f"{fig}.png"
    r = run([cli, "-x", "-f", "png", "-o", str(png), str(path)])
    if r.returncode != 0:
        print(f"drawio export failed:\n{r.stderr}", file=sys.stderr)
        return 1
    print(f"preview → {png.relative_to(ROOT)}")
    if export:
        EXPORT.mkdir(parents=True, exist_ok=True)
        for fmt in ("svg", "pdf"):
            out = EXPORT / f"{fig}.{fmt}"
            r = run([cli, "-x", "-f", fmt, "--embed-diagram", "-o", str(out), str(path)])
            if r.returncode != 0:
                print(f"warning: {fmt} export failed: {r.stderr.strip()}", file=sys.stderr)
        print(f"export  → {EXPORT.relative_to(ROOT)}/{fig}.{{svg,pdf,png}}")
    return 0


def render_py(path: Path, fig: str, export: bool) -> int:
    print(f"running {path.relative_to(ROOT)} (plotting code is the source of truth)")
    r = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, cwd=str(ROOT))
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 1
    have = [p.name for p in EXPORT.glob(f"{fig}.*")] if EXPORT.exists() else []
    print(f"outputs present in export/: {', '.join(have) or '(script writes its own)'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="figures/src/<fig>.svg|.drawio|.py")
    ap.add_argument("--export", action="store_true",
                    help="also write submission exports (svg/pdf/png)")
    args = ap.parse_args()

    path = Path(args.source)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"no such source: {path}")
    fig = path.stem

    if path.suffix == ".svg":
        return render_svg(path, fig, args.export)
    if path.suffix == ".drawio" or path.suffix == ".xml":
        return render_drawio(path, fig, args.export)
    if path.suffix == ".py":
        return render_py(path, fig, args.export)
    raise SystemExit(f"unknown source type: {path.suffix}")


if __name__ == "__main__":
    sys.exit(main())
