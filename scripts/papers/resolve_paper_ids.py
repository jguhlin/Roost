#!/usr/bin/env python3
"""Deterministic paper-ID fuzzy matching for adjudication output.

The adjudicator sometimes mangles paper IDs (truncation, title-fragment,
year appended). This resolves mangled IDs back to real ones using
progressively looser matching:
  1. exact match
  2. prefix match (first 15+ chars)
  3. substring match (either direction)
  4. title-token overlap
Unresolvable IDs return None (the export drops them).

Standalone module — imported by export_contradictions.py.
"""
from __future__ import annotations

import re
import unicodedata


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).lower().strip()
    return re.sub(r"[^a-z0-9]", "", s)


def build_index(valid_ids: list[str], titles: dict[str, str]):
    """Pre-build lookup structures."""
    by_norm = {_norm(pid): pid for pid in valid_ids}
    by_prefix = {}
    for pid in valid_ids:
        n = _norm(pid)
        for L in range(min(len(n), 25), 9, -1):
            by_prefix.setdefault(n[:L], []).append(pid)
    by_title_token = {}
    for pid, title in titles.items():
        tokens = [t for t in re.sub(r"[^a-z0-9 ]", " ", title.lower()).split()
                  if len(t) > 3]
        for t in tokens[:8]:
            by_title_token.setdefault(t, set()).add(pid)
    return by_norm, by_prefix, by_title_token


def resolve_id(raw: str, valid_ids: list[str], titles: dict[str, str],
               by_norm=None, by_prefix=None, by_title_token=None) -> str | None:
    """Try to resolve a possibly-mangled paper ID to a real one."""
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()

    # exact
    if raw in set(valid_ids):
        return raw

    # normalised exact
    if by_norm is None:
        by_norm = {_norm(pid): pid for pid in valid_ids}
    n = _norm(raw)
    if n in by_norm:
        return by_norm[n]

    # strip trailing junk: "[id year study_type]" or "[id None review]"
    stripped = re.sub(r"\s+\d{4}\s+\w.*$", "", raw).strip("[] ")
    if stripped != raw:
        if stripped in set(valid_ids):
            return stripped
        sn = _norm(stripped)
        if sn in by_norm:
            return by_norm[sn]

    # prefix match (normalised, ≥10 chars)
    if by_prefix is None:
        by_prefix = {}
        for pid in valid_ids:
            pn = _norm(pid)
            for L in range(min(len(pn), 25), 9, -1):
                by_prefix.setdefault(pn[:L], []).append(pid)
    if len(n) >= 10:
        for L in range(min(len(n), 25), 9, -1):
            if n[:L] in by_prefix:
                cands = by_prefix[n[:L]]
                if len(cands) == 1:
                    return cands[0]

    # substring: raw norm contained in a real ID's norm (or vice versa)
    for pid in valid_ids:
        pn = _norm(pid)
        if len(n) >= 8 and (n in pn or pn in n):
            return pid

    # title-token overlap (for "Characterization of oseltamivir..." style)
    if by_title_token is None:
        by_title_token = {}
        for pid, title in titles.items():
            tokens = [t for t in
                      re.sub(r"[^a-z0-9 ]", " ", title.lower()).split()
                      if len(t) > 3]
            for t in tokens[:8]:
                by_title_token.setdefault(t, set()).add(pid)
    raw_tokens = [t for t in
                  re.sub(r"[^a-z0-9 ]", " ", raw.lower()).split()
                  if len(t) > 3]
    if raw_tokens:
        overlap = None
        for t in raw_tokens[:6]:
            if t in by_title_token:
                s = by_title_token[t]
                overlap = s if overlap is None else (overlap & s)
                if overlap and len(overlap) == 1:
                    return next(iter(overlap))
        if overlap and len(overlap) <= 2:
            return next(iter(overlap))

    return None


def resolve_contradictions(x: list[dict], valid_ids: list[str],
                           titles: dict[str, str]) -> tuple[list[dict], dict]:
    """Resolve paper_a/paper_b in a list of contradiction dicts.
    Returns (resolved, stats)."""
    by_norm, by_prefix, by_title = build_index(valid_ids, titles)
    vid = set(valid_ids)
    stats = {"exact": 0, "fuzzy": 0, "unresolved_a": 0, "unresolved_b": 0,
             "self_pair_dropped": 0}
    out = []
    for r in x:
        ra = resolve_id(r.get("paper_a", ""), valid_ids, titles,
                        by_norm, by_prefix, by_title)
        rb = resolve_id(r.get("paper_b", ""), valid_ids, titles,
                        by_norm, by_prefix, by_title)
        if ra in vid:
            stats["exact" if r.get("paper_a") in vid else "fuzzy"] += 1
        elif r.get("paper_a"):
            stats["unresolved_a"] += 1
        if rb in vid:
            pass  # counted with a
        elif r.get("paper_b"):
            stats["unresolved_b"] += 1
        if ra and rb and ra == rb:
            stats["self_pair_dropped"] += 1
            continue
        if ra and rb:
            r = {**r, "paper_a": ra, "paper_b": rb}
            out.append(r)
        # else: dropped (unresolved)
    return out, stats
