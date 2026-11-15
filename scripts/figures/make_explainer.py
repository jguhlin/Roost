#!/usr/bin/env python3
"""Generate an educational explainer video from a research briefing.

  pixi run python scripts/figures/make_explainer.py --slug NAME [--skip-build]

Deterministic briefing→video codegen (MEDIA_PLAN: lecture format is the
default video form for briefings):
  - title beat (briefing title + question)
  - one numbered section per briefing section: heading + body sentences as
    progressive lines (~4.2 s apart, wrapped at ~88 chars)
  - final section: unresolved questions
  - ambient bed (CC0-by-construction), section progress dots, citations kept

Emits figures/video/<slug>-explainer/ (a fframes crate), builds + renders it,
and publishes the video to the briefing's page.
"""
from __future__ import annotations

import argparse
import glob as _glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _ffx264() -> str:
    """libx264 shared-lib dir required by the prebuilt ffmpeg-sys.

    FFX264 env var wins; otherwise search known Julia depots (username-free).
    """
    if os.environ.get("FFX264"):
        return os.environ["FFX264"]
    h = "587de110e5f58fd435dc35b294df31bb7a75f692"
    for base in (Path.home() / ".julia", Path("/mnt/data/*/.julia")):
        hits = _glob.glob(str(base / "artifacts" / h / "lib"))
        if hits:
            return hits[0]
    raise SystemExit("FFX264 not set and libx264 Julia artifact not found — "
                     "export FFX264=/path/to/libx264/lib")

ROOT = Path(__file__).resolve().parents[2]
BRIEF = ROOT / "web" / "public" / "data" / "research_briefings"
VIDS = ROOT / "figures" / "video"
TEMPLATE = VIDS / "anp32a-barrier"
UNIT = 1080.0 / 1080.0
INK = "#0f172a"
X0 = 150.0
LINE_H = 96.0
LINE_T = 4.2
WRAP = 88
ACCENTS = [("#1d4ed8", "#eff6ff"), ("#166534", "#f0fdf4"),
           ("#92400e", "#fffbeb"), ("#1d4ed8", "#eff6ff"),
           ("#475569", "#f1f5f9")]


def slugify(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:44]


def esc(s: str) -> str:
    s = "".join(ch for ch in s if ord(ch) >= 32)  # drop control chars
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def wrap_sentence(s: str) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > WRAP and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def sentences(body: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", body.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


def build_slides(b: dict) -> list[dict]:
    """(label, title, lines, accent) — title slide + sections + unresolved."""
    slides = []
    q = b.get("question", "")
    qlines = wrap_sentence(q)[:3]
    slides.append({"label": "", "title": b.get("title", b["slug"])[:96],
                   "lines": qlines, "accent": ACCENTS[0], "is_title": True})
    META = re.compile(r"search(es( performed| conducted| history)?| history| coverage)?"
                      r"|evidence (retrieved|found)|relevance assessment"
                      r"|limitations( of| and)?|agent process", re.I)
    for i, sec in enumerate(b.get("sections", [])[:6]):
        if META.search(sec.get("heading", "")):
            continue  # process-meta sections make poor lecture content
        body_sents = sentences(sec.get("body", ""))
        lines: list[str] = []
        for s_ in body_sents[:5]:
            lines.extend(wrap_sentence(s_)[:2])  # ≤2 rows per sentence
        if not lines:
            continue
        slides.append({"label": f"{len(slides)} / n", "title": sec.get("heading", "")[:70],
                       "lines": lines[:7], "accent": ACCENTS[(len(slides)) % len(ACCENTS)],
                       "is_title": False})
    unres = b.get("unresolved") or []
    if unres:
        lines = []
        for u in unres[:4]:
            lines.extend(wrap_sentence(u)[:2])
        if lines:
            slides.append({"label": f"{len(slides)} / n", "title": "What remains open",
                           "lines": lines[:6], "accent": ACCENTS[4], "is_title": False})
    # fix labels now the count is known
    n = len(slides)
    for i, s in enumerate(slides):
        s["label"] = "" if s["is_title"] else f"{i} / {n - 1}"
    return slides


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--slug")
    g.add_argument("--all", action="store_true",
                   help="every briefing (skips stale-checked ones unless --force)")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="rebuild even if the published video is newer than the briefing")
    args = ap.parse_args()

    if args.all:
        import subprocess as _sp
        fails = []
        for bf in sorted(BRIEF.glob("*.json")):
            if bf.name == "index.json":
                continue
            slug = bf.stem
            # movie-usefulness policy (MEDIA_PLAN): full briefings only, with
            # enough substantive (non-meta) content to carry a walkthrough
            try:
                bb = json.loads(bf.read_text())
            except json.JSONDecodeError:
                continue
            if bb.get("_gap_report"):
                print(f"[skip gap-report] {slug[:56]}")
                continue
            META = re.compile(r"search(es( performed| conducted| history)?| history| coverage)?"
                              r"|evidence (retrieved|found)|relevance assessment"
                              r"|limitations( of| and)?|agent process", re.I)
            substantive = [x for x in bb.get("sections", [])
                           if not META.search(x.get("heading", ""))]
            if len(substantive) < 3:
                print(f"[skip thin] {slug[:56]} ({len(substantive)} substantive sections)")
                continue
            cmd = [sys.executable, __file__, "--slug", slug]
            if args.force:
                cmd.append("--force")
            r = _sp.run(cmd, capture_output=True, text=True)
            status = "ok" if r.returncode == 0 else "FAIL"
            if r.returncode != 0:
                fails.append(slug)
                print(f"[{status}] {slug}: {r.stderr.strip().splitlines()[-1][:100] if r.stderr.strip() else ''}")
            else:
                tail = (r.stdout.strip().splitlines() or [""])[-1][:90]
                print(f"[ok] {slug[:52]}: {tail}")
        print(f"all-mode: {len(list(BRIEF.glob('*.json'))) - 1 - len(fails)} ok, {len(fails)} failed")
        return 1 if fails else 0

    bp = BRIEF / f"{args.slug}.json"
    if not bp.exists():
        print(f"no briefing: {bp}", file=sys.stderr)
        return 1
    b = json.loads(bp.read_text())

    # stale check: skip if the published video is newer than the briefing
    if not args.force:
        try:
            idx = json.loads((ROOT / "web/public/figures/index.json").read_text())
            vids = {v["file"]: v.get("published", "")
                    for v in idx.get("videos", [])}
            import re as _re
            cratename = f"{slugify(args.slug)}-explainer"
            vidfile = f"{cratename}.mp4"
            pub = vids.get(vidfile, "")
            brief_gen = b.get("generated", "")
            if pub and brief_gen and pub >= brief_gen:
                print(f"skip (current): {vidfile} published {pub[:19]} >= briefing {brief_gen[:19]}")
                return 0
        except (json.JSONDecodeError, OSError):
            pass
    proj_name = f"{slugify(args.slug)}-explainer"
    proj = VIDS / proj_name

    # scaffold
    if not proj.exists():
        proj.mkdir(parents=True)
        (proj / "src").mkdir()
        shutil.copy2(TEMPLATE / "Cargo.lock", proj / "Cargo.lock")
        shutil.copytree(TEMPLATE / "media", proj / "media")
        ct = (TEMPLATE / "Cargo.toml").read_text()
        ct = ct.replace('name = "anp32a-barrier"', f'name = "{proj_name}"')
        ct = ct.replace('name = "anp32a_barrier"', f'name = "{proj_name.replace("-", "_")}"')
        (proj / "Cargo.toml").write_text(ct)
        main_rs = (TEMPLATE / "src" / "main.rs").read_text()
        main_rs = main_rs.replace("anp32a_barrier::", f'{proj_name.replace("-", "_")}::')
        main_rs = main_rs.replace("Anp32aMedia", "ExplainerMedia").replace("Anp32aVideo", "ExplainerVideo")
        (proj / "src" / "main.rs").write_text(main_rs)

    slides = build_slides(b)
    n = len(slides)
    t = 0.5
    starts = []
    for s in slides:
        starts.append(t)
        if s["is_title"]:
            t += 3.0 + len(s["lines"]) * LINE_T
        else:
            t += 1.6 + len(s["lines"]) * LINE_T + 1.4
    total = round(t + 1.5, 1)

    lines_of_code = []
    lines_of_code.append(f"//! Educational explainer (auto-generated from briefing {args.slug}).")
    lines_of_code.append("//! Generated by scripts/figures/make_explainer.py — edit the briefing,")
    lines_of_code.append("//! not this file; regenerate with make_explainer.py --slug.")
    lines_of_code.append("use fframes::{")
    lines_of_code.append("    AudioMap, AudioTimestamp::*, AudioTrack, Color, Duration, FFramesContext,")
    lines_of_code.append("    Frame, Svgr, Video, include_media_dir,")
    lines_of_code.append("};")
    lines_of_code.append("")
    lines_of_code.append('include_media_dir!(pub struct ExplainerMedia, "media");')
    lines_of_code.append("")
    lines_of_code.append("pub const WIDTH: usize = 1920;")
    lines_of_code.append("pub const HEIGHT: usize = 1080;")
    lines_of_code.append("const UNIT: f32 = HEIGHT as f32 / 1080.0;")
    lines_of_code.append('const FONT: &str = "DM Sans";')
    lines_of_code.append("const W: u16 = 500;")
    lines_of_code.append('const INK: &str = "#0f172a";')
    lines_of_code.append('const FAINT: &str = "#94a3b8";')
    lines_of_code.append("const STARTS: &[f32] = &[")
    for st in starts:
        lines_of_code.append(f"    {st:.1},")
    lines_of_code.append("];")
    lines_of_code.append(f"const TOTAL: f32 = {total};")
    lines_of_code.append("")
    lines_of_code.append("pub struct ExplainerVideo<'a> { pub media: &'a ExplainerMedia }")
    lines_of_code.append("")
    lines_of_code.append("impl std::fmt::Debug for ExplainerVideo<'_> {")
    lines_of_code.append("    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {")
    lines_of_code.append('        f.debug_struct("ExplainerVideo").finish()')
    lines_of_code.append("    }")
    lines_of_code.append("}")
    lines_of_code.append("")
    lines_of_code.append("impl Video for ExplainerVideo<'_> {")
    lines_of_code.append("    const FPS: usize = 30;")
    lines_of_code.append("    const WIDTH: usize = WIDTH;")
    lines_of_code.append("    const HEIGHT: usize = HEIGHT;")
    lines_of_code.append("    const BACKGROUND_COLOR: Color = Color::WHITE;")
    lines_of_code.append("    fn duration(&self) -> Duration<'_> { Duration::Seconds(TOTAL) }")
    lines_of_code.append("    fn audio(&self) -> AudioMap<'_> {")
    lines_of_code.append("        AudioMap::from([AudioTrack::new(\"ambient-pad.wav\", Second(0.)..Eof)")
    lines_of_code.append("            .gain_db(-20.).fade_in(2.).fade_out(2.)])")
    lines_of_code.append("    }")
    lines_of_code.append("    fn render_frame<'a>(&'a self, mut frame: Frame, ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {")
    lines_of_code.append("        let _ = &ctx;")
    lines_of_code.append("        let t = frame.seconds() as f32;")
    lines_of_code.append("        let f = |from: f32, dur: f32| if t < from { 0.0 } else { ((t - from) / dur).min(1.0) };")
    lines_of_code.append("        let line = |i: usize, j: usize| f(STARTS[i] + 0.8 + j as f32 * 4.2, 0.7);")

    # per-slide <g> blocks
    svg_elements: list[str] = []
    dots = []
    for i, s in enumerate(slides):
        start = starts[i]
        end = starts[i + 1] if i + 1 < len(slides) else total
        accent, bg = s["accent"]
        vis = (f"(if t < {start} {{ 0.0 }} else if {end} - t < 0.7 {{ (({end} - t) / 0.7).max(0.0) }}"
               f" else {{ f({start}, 0.7) }})")
        g = [f'<g opacity={{{vis}}}>']
        if not s["is_title"]:
            tw = max(560.0, 15.5 * len(s["title"]) + 140.0)
            g.append(f'<rect x={{x0}} y={{148. * UNIT}} width={{{
                tw:.1f} * UNIT}} height={{92. * UNIT}} rx={{14. * UNIT}} fill="{bg}"/>')
            head = esc(f'{s["label"]}  ·  {s["title"]}')
            g.append(f'<text x={{x0 + 30. * UNIT}} y={{208. * UNIT}} font-family={{FONT}} '
                     f'font-size={{38. * UNIT}} font-weight={{700}} fill="{accent}">'
                     f'"{head}"</text>')
        else:
            g.append(f'<text x={{x0}} y={{200. * UNIT}} font-family={{FONT}} '
                     f'font-size={{46. * UNIT}} font-weight={{700}} fill="{accent}">'
                     f'"{esc(s["title"])}"</text>')
        y = 330.0
        for j, ln in enumerate(s["lines"]):
            fs = 34.0 if s["is_title"] else 29.0
            fill = INK if not s["is_title"] else "#334155"
            g.append(f'<text x={{x0}} y={{{y:.1f} * UNIT}} font-family={{FONT}} '
                     f'font-size={{{fs} * UNIT}} font-weight={{W}} fill="{fill}" '
                     f'opacity={{line({i}, {j})}}>"• {esc(ln)}"</text>')
            y += LINE_H
        g.append("</g>")
        svg_elements.append("\n                ".join(g))
        dots.append((i, accent))

    lines_of_code.append("        let cx = WIDTH as f32 / 2.0;")
    lines_of_code.append("        let x0 = 150.0 * UNIT;")
    lines_of_code.append("        fframes::svgr!(")
    lines_of_code.append('            <svg xmlns="http://www.w3.org/2000/svg" viewBox={format!("0 0 {WIDTH} {HEIGHT}")} width={WIDTH} height={HEIGHT}>')
    lines_of_code.append('                <rect width={WIDTH} height={HEIGHT} fill="#f8fafc"/>')
    for el in svg_elements:
        lines_of_code.append("                " + el)
    # progress dots
    spread = 46.0
    off = -(len(dots) - 1) / 2.0 * spread
    for i, accent in dots:
        pos = f"(cx + {off + i * spread:.1f} * UNIT)"
        cond = f"if t >= STARTS[{i}] {{ \"{accent}\" }} else {{ \"#cbd5e1\" }}"
        lines_of_code.append('                <circle cx={' + pos + '} cy={HEIGHT as f32 - 56. * UNIT} r={9. * UNIT} fill={' + cond + '}/>')
    lines_of_code.append('                <text x={52. * UNIT} y={HEIGHT as f32 - 22. * UNIT} font-family={FONT} font-size={19. * UNIT} font-weight={W} fill={FAINT}>')
    lines_of_code.append(f'                    "Roost · educational explainer · briefing: {esc(args.slug)[:80]}"')
    lines_of_code.append("                </text>")
    lines_of_code.append("            </svg>")
    lines_of_code.append("        )")
    lines_of_code.append("    }")
    lines_of_code.append("}")

    (proj / "src" / "lib.rs").write_text("\n".join(lines_of_code) + "\n")
    print(f"generated {proj / 'src/lib.rs'} — {n} slides, {total}s")

    if args.skip_build:
        return 0

    env = {
        **os.environ,
        "FFX264": _ffx264(),
    }
    env["LIBRARY_PATH"] = f"{env['FFX264']}:{env.get('LIBRARY_PATH', '')}"
    env["LD_LIBRARY_PATH"] = f"{env['FFX264']}:{env.get('LD_LIBRARY_PATH', '')}"
    r = subprocess.run(["cargo", "build", "--release"], cwd=proj, env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], file=sys.stderr)
        return 1
    r = subprocess.run(["cargo", "run", "--release", "--", "render"], cwd=proj,
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:], file=sys.stderr)
        return 1
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "rendered")

    # frame verification: probe slide midpoints; fail on blank beats
    import subprocess as _sp2
    from PIL import Image as _Img
    import numpy as _np
    bad = []
    for st in starts:
        probe = max(st + 2.0, 0.5)
        _sp2.run(["ffmpeg", "-y", "-v", "error", "-ss", str(probe),
                  "-i", str(proj / "out.mp4"), "-frames:v", "1", "/tmp/_probe.png"],
                 capture_output=True)
        try:
            im = _np.asarray(_Img.open("/tmp/_probe.png").convert("L"))
            if (im < 200).mean() < 0.001:
                bad.append(probe)
        except Exception:
            bad.append(probe)
    if bad:
        print(f"frame verification FAILED — blank beats at {bad}", file=sys.stderr)
        return 1
    print(f"frame verification: {len(starts)} beats OK")

    out = proj / "out.mp4"
    vid = ROOT / "figures" / "export" / f"{proj_name}.mp4"
    shutil.copy2(out, vid)
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/figures/publish_figure.py"),
         "--video", str(vid), "--page", args.slug,
         "--caption",
         f"Educational explainer ({int(total // 60)} min {int(total % 60)} s): "
         f"the briefing's sections as a narrated-style walkthrough with on-screen "
         f"citations. Auto-generated from the briefing by make_explainer.py."],
        capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
