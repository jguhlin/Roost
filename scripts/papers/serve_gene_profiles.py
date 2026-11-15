#!/usr/bin/env python3
"""Copy gene profiles from data/ to web/public/data/ with translation hashes."""
import hashlib, json, shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
src = ROOT / "data/papers/gene_profiles"
dst = ROOT / "web/public/data/gene_profiles"
dst.mkdir(exist_ok=True)

def h12(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

n = 0
for f in src.glob("*.json"):
    if f.parent != src:
        continue
    try:
        profile = json.loads(f.read_text())
    except Exception:
        shutil.copy2(f, dst / f.name)
        n += 1
        continue
    # add hash fields for translation lookup
    hashes = {}
    for field in ("overview", "function", "species_differences",
                  "clinical_relevance", "cross_study_patterns"):
        v = profile.get(field)
        if v and len(v) > 10:
            hashes[field] = h12(v)
    profile["_h"] = hashes
    for kf in profile.get("key_findings", []):
        v = kf.get("text")
        if v and len(v) > 10:
            kf["_h"] = h12(v)
    (dst / f.name).write_text(json.dumps(profile, indent=1, ensure_ascii=False))
    n += 1
print(f"served {n} gene profiles → {dst.relative_to(ROOT)}")
