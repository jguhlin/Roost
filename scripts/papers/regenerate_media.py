#!/usr/bin/env python3
"""Regenerate the research-media pipeline — one safe, resumable command.

  pixi run python scripts/papers/regenerate_media.py [--steps a,b,c] [--force]

Steps (default: all):
  proposals  execute figure_proposals from briefings (deterministic)
  videos     make_explainer for every briefing (stale-checked; --force rebuilds)
  layers     refresh derived layers: links, gap ledger, bridges,
             synthesis (LLM), briefings index, aggregation, credits rollup

Each item is isolated: one failure never stops the run; the final report
lists ok / skipped / failed per step. Exit 1 only if a step had failures.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
REPORT: dict[str, list[str]] = {}


def run(label: str, argv: list[str], cwd: Path = ROOT, env: dict | None = None) -> bool:
    t0 = time.time()
    e = {**os.environ, **(env or {})}
    r = subprocess.run(argv, cwd=cwd, env=e, capture_output=True, text=True)
    dt = time.time() - t0
    tail = (r.stdout.strip().splitlines() or [""])[-1][:110]
    err = (r.stderr.strip().splitlines() or [""])[-1][:110] if r.returncode else ""
    ok = r.returncode == 0
    REPORT.setdefault(label, []).append(
        f"{'ok  ' if ok else 'FAIL'} {dt:6.1f}s  {tail or err}")
    if not ok:
        REPORT[label].append(f"     stderr: {err}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="proposals,videos,layers",
                    help="comma list: proposals,videos,layers")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]

    env_llm = {"LLM_MAX_TOKENS": "8192"}
    fails = 0

    if "proposals" in steps:
        print("== proposals ==")
        run("proposals", [PY, "scripts/papers/execute_figure_proposals.py"])

    if "videos" in steps:
        print("== videos ==")
        cmd = [PY, "scripts/figures/make_explainer.py", "--all"]
        if args.force:
            cmd.append("--force")
        env = {
            "FFX264": os.environ.get(
                "FFX264",
                "/mnt/data/*/.julia/artifacts/"
                "587de110e5f58fd435dc35b294df31bb7a75f692/lib"),
            "PATH": os.environ.get("PATH", ""),
        }
        # Resolve the glob (depot mount is machine-local; username-free).
        import glob as _g
        _hits = _g.glob(env["FFX264"])
        if _hits:
            env["FFX264"] = _hits[0]
        env["LIBRARY_PATH"] = f"{env['FFX264']}:{os.environ.get('LIBRARY_PATH', '')}"
        env["LD_LIBRARY_PATH"] = f"{env['FFX264']}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        run("videos", cmd, env=env)

    if "layers" in steps:
        print("== layers ==")
        run("layers:links", [PY, "scripts/papers/link_contradictions_briefings.py"])
        run("layers:ledger", [PY, "scripts/papers/gap_ledger.py"])
        run("layers:bridges", [PY, "scripts/papers/data_lit_bridges.py"])
        run("layers:synthesis", [PY, "scripts/papers/synthesize_briefings.py"],
            env=env_llm)
        # index newest-first (same logic as research_agent, standalone)
        idx = []
        d = ROOT / "web/public/data/research_briefings"
        for f in sorted(d.glob("*.json")):
            if f.name == "index.json":
                continue
            b = json.loads(f.read_text(encoding="utf-8"))
            idx.append({"slug": b.get("slug", f.stem), "title": b.get("title", f.stem),
                        "summary": b.get("summary", ""), "generated": b.get("generated", ""),
                        "gap_report": bool(b.get("_gap_report")),
                        "hypotheses": b.get("hypotheses", []),
                        "research_plan": b.get("research_plan", [])})
        idx.sort(key=lambda e: e.get("generated", ""), reverse=True)
        (d / "index.json").write_text(json.dumps(idx, indent=1))
        REPORT.setdefault("layers:index", []).append(f"ok          {len(idx)} briefings indexed")
        run("layers:aggregation", [PY, "scripts/papers/build_aggregation.py"])
        run("layers:credits", [PY, "scripts/figures/build_attribution.py", "--rollup"])

    print("\n" + "=" * 72)
    print("REPORT")
    print("=" * 72)
    for label, lines in REPORT.items():
        print(f"[{label}]")
        for line in lines:
            print("  " + line)
            if line.startswith("FAIL"):
                fails += 1
    print(f"\n{'FAILURES: ' + str(fails) if fails else 'ALL STEPS OK'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
