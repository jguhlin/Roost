#!/usr/bin/env python3
"""LLM endpoint health check — run before any LLM pass.

Verifies: endpoint up, model responds, and crucially whether the server is
in REASONING mode (content empty, text in reasoning_content) — the normal
config since the 2026-10-07 server restart. Scripts with the reasoning
fallback handle it; ones without must be patched before running.

Exit 0 = healthy (either mode, reported); exit 1 = unusable.
Usage: LLM_BASE_URL=http://localhost:8005/v1 pixi run python scripts/papers/llm_health.py
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("LLM_BASE_URL", "http://localhost:8005/v1")
MODEL = os.environ.get("LLM_MODEL", "muse-glimmer-30b")


def main():
    try:
        with urllib.request.urlopen(f"{BASE}/models", timeout=10) as r:
            models = [m["id"] for m in json.loads(r.read())["data"]]
        if MODEL not in models:
            print(f"✗ model {MODEL} not served (have: {models})"); return 1
    except Exception as e:
        print(f"✗ endpoint down: {e}"); return 1
    body = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": 3072,
                       "messages": [{"role": "user", "content":
                        'Reply with exactly this JSON and nothing else: {"ok": true}'}]}).encode()
    try:
        req = urllib.request.Request(f"{BASE}/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            msg = json.loads(r.read())["choices"][0]["message"]
    except Exception as e:
        print(f"✗ completion failed: {e}"); return 1
    content = (msg.get("content") or "").strip()
    reasoning = (msg.get("reasoning_content") or "").strip()
    if content:
        print(f"✓ endpoint healthy — plain mode ({len(content)} chars)")
        return 0
    if reasoning:
        print(f"⚠ endpoint healthy — REASONING mode (content empty; "
              f"reasoning_content has {len(reasoning)} chars). "
              f"Scripts WITHOUT the reasoning fallback will see empty responses "
              f"and fail silently (641/641 backfill failures, 2026-10-07).")
        return 0
    print("✗ both content and reasoning_content empty — unusable response")
    return 1


if __name__ == "__main__":
    sys.exit(main())
