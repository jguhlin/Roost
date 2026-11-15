#!/usr/bin/env python3
"""ANP32 species-barrier comparison: the 33-aa insert across birds + mammals.

Avian ANP32A (and paralog ANP32B) carry a ~33-residue insert between the
LRR and LCAR domains (partial exon-5 duplication; Long et al. 2016, Nature)
that supports the avian influenza polymerase. Mammalian ANP32 proteins lack
it — the core species-barrier determinant.

Method:
  1. For each paralog, NW-align one clean insert-carrying bird protein
     (waterfowl by preference, else the modal-length species) to the human
     reference. Internal reference-gap runs separated by <6 residues are
     merged — the insert is an acidic duplication that the aligner often
     splits. This yields the insert site in human coordinates.
  2. Every species' protein is then scored by anchoring two conserved
     18-aa windows flanking the site (<=2 mismatches) and measuring the
     span between them; a global-NW merged-gap fallback covers divergent
     sequences.
  birds    — OrthoFinder OG MSAs (ungapped; one entry per species)
  mammals  — HPAI-confirmed mammals with genomes; ANP32A/B/E proteins via
             the NCBI `datasets` CLI (--include protein), cached slim
  refs     — UniProt human ANP32A/B/E (canonical, no insert)

Output: web/public/data/anp32/comparison.json
Run:  pixi run python scripts/genes/export_anp32_comparison.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OF_RESULTS = ROOT / "orthofinder" / "orthofinder_aves463_root16_20260928" / "Results_Aves463_Root16"
SPECIES_MAP = ROOT / "web" / "public" / "data" / "orthofinder" / "species_map.json"
MAMMALS = ROOT / "web" / "public" / "data" / "detected_mammals.json"
CACHE = ROOT / "data" / "anp32" / "cache"
OUT = ROOT / "web" / "public" / "data" / "anp32" / "comparison.json"

OGS = {"A": "OG0004189", "B": "OG0003684", "E": "OG0006217"}
UNIPROT = {"A": "P39687", "B": "Q92688", "E": "Q9BTT0"}  # human, no insert
UA = "Roost/avian-HPAI-atlas (research website data pipeline)"
MERGE_DIST = 6      # gap runs this close are one insert (acidic dup splits)
MIN_INSERT = 8       # report span-excess at/above this length
FLANK = 18           # anchor window length
GAP_L = 12           # distance from site to left-anchor end / right-anchor start
GAP_R = 15
HUMAN_SPAN = GAP_L + GAP_R   # measured span on the no-insert reference


# ---------------------------------------------------------------- utils ----
def fetch_uniprot(acc: str) -> str:
    cache = CACHE / f"uniprot_{acc}.fa"
    if cache.exists():
        return cache.read_text()
    url = f"https://rest.uniprot.org/uniprotkb/{acc}.fasta"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                txt = r.read().decode()
            CACHE.mkdir(parents=True, exist_ok=True)
            cache.write_text(txt)
            return txt
        except Exception as e:
            print(f"  uniprot {acc} attempt {attempt+1}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"UniProt {acc} unreachable")


def parse_fasta(txt: str) -> list[tuple[str, str]]:
    out, name, buf = [], None, []
    for line in txt.splitlines():
        if line.startswith(">"):
            if name:
                out.append((name, "".join(buf)))
            name, buf = line[1:], []
        else:
            buf.append(line.strip().upper())
    if name:
        out.append((name, "".join(buf)))
    return out


# ------------------------------------------------------------ alignment ----
def nw_align(a: str, b: str) -> tuple[str, str]:
    """Global Needleman-Wunsch (match +3 / mismatch -2 / gap -12)."""
    n, m = len(a), len(b)
    GAP = -12
    score = [[0] * (m + 1) for _ in range(n + 1)]
    ptr = [[0] * (m + 1) for _ in range(n + 1)]  # 0 diag, 1 up, 2 left
    for i in range(1, n + 1):
        score[i][0] = i * GAP
        ptr[i][0] = 1
    for j in range(1, m + 1):
        score[0][j] = j * GAP
        ptr[0][j] = 2
    for i in range(1, n + 1):
        ai = a[i - 1]
        row, prow = score[i], score[i - 1]
        p_row = ptr[i]
        for j in range(1, m + 1):
            d = prow[j - 1] + (3 if ai == b[j - 1] else -2)
            u = prow[j] + GAP
            l = row[j - 1] + GAP
            best, p = d, 0
            if u > best:
                best, p = u, 1
            if l > best:
                best, p = l, 2
            row[j] = best
            p_row[j] = p
    aa, bb = [], []
    i, j = n, m
    while i > 0 or j > 0:
        p = ptr[i][j] if i > 0 and j > 0 else (1 if i > 0 else 2)
        if p == 0:
            aa.append(a[i - 1]); bb.append(b[j - 1]); i -= 1; j -= 1
        elif p == 1:
            aa.append(a[i - 1]); bb.append("-"); i -= 1
        else:
            aa.append("-"); bb.append(b[j - 1]); j -= 1
    return "".join(reversed(aa)), "".join(reversed(bb))


def merged_gap_runs(qa: str, ra: str, min_run: int = 8) -> list[dict]:
    """Runs of query residues aligned to reference gaps; runs closer than
    MERGE_DIST joined. Internal only (not at sequence termini)."""
    runs, cur_len, cur_start = [], 0, 0
    qpos = 0
    starts = []
    for k in range(len(qa) + 1):
        ch_q = qa[k] if k < len(qa) else "$"
        ch_r = ra[k] if k < len(ra) else "$"
        is_gap = k < len(qa) and ch_r == "-"
        if is_gap:
            if cur_len == 0:
                cur_start = qpos
            cur_len += 1
        else:
            if cur_len >= min_run:
                runs.append({"start": cur_start, "len": cur_len})
            cur_len = 0
        if k < len(qa) and ch_q != "-":
            qpos += 1
    # merge close runs
    merged = []
    for r in runs:
        if merged and r["start"] - (merged[-1]["start"] + merged[-1]["len"]) <= MERGE_DIST:
            prev_end = merged[-1]["start"] + merged[-1]["len"]
            merged[-1]["len"] = r["start"] + r["len"] - merged[-1]["start"]
        else:
            merged.append(dict(r))
    q_total = len(qa.replace("-", ""))
    # drop terminal artifacts
    return [r for r in merged
            if r["start"] >= 5 and r["start"] + r["len"] <= q_total - 5]


def derive_site(ref: str, carrier: str) -> dict:
    """Align an insert-carrying sequence to the reference; return the
    insert (merged) and the reference index just after it."""
    qa, ra = nw_align(carrier, ref)
    runs = merged_gap_runs(qa, ra)
    if not runs:
        return {}
    ins = max(runs, key=lambda r: r["len"])
    if ins["len"] < MIN_INSERT:
        return {}
    # reference coordinate right after the insert: count ref residues
    # up to the alignment column where the insert ends
    qpos = 0
    ref_after = None
    end_q = ins["start"] + ins["len"]
    for k in range(len(qa)):
        if qa[k] != "-":
            if qpos == end_q:
                ref_after = len(ra[:k].replace("-", ""))
                break
            qpos += 1
    if ref_after is None:
        ref_after = len(ref)
    return {"insert_start": ins["start"] + 1, "insert_len": ins["len"],
            "insert_seq": carrier[ins["start"]:ins["start"] + ins["len"]],
            "site": ref_after}


def anchor_find(seq: str, anchor: str, max_mm: int = 2) -> int | None:
    """First index of anchor in seq allowing <=max_mm mismatches."""
    n, m = len(seq), len(anchor)
    if m == 0 or n < m:
        return None
    for i in range(n - m + 1):
        mm = 0
        for k in range(m):
            if seq[i + k] != anchor[k]:
                mm += 1
                if mm > max_mm:
                    break
        if mm <= max_mm:
            return i
    return None


def _windows(ref: str, site: int) -> tuple[str, str, str]:
    """Left anchor, right anchor (distal — past the acidic duplication) and
    the reference middle they bracket."""
    a2 = max(FLANK + 1, site - GAP_L)
    a1 = max(0, a2 - FLANK)
    b1 = min(len(ref) - FLANK - 1, site + GAP_R)
    b2 = min(len(ref), b1 + FLANK)
    return ref[a1:a2], ref[b1:b2], ref[a2:b1]


def span_for(seq: str, ref: str, site: int) -> int | None:
    """Residues between the two anchor matches in seq (None if not found)."""
    L, R, _mid = _windows(ref, site)
    ia = anchor_find(seq, L)
    if ia is None:
        return None
    ib = anchor_find(seq[ia + len(L):], R, max_mm=3)
    if ib is None:
        return None
    return ib


def pick_site(ref: str, samples: list[str]) -> int:
    """Scan candidate junction sites; pick the one where bird spans exceed
    the no-insert reference span by the most (the insert)."""
    import statistics
    best = (0, len(ref) // 2)
    for site in range(80, len(ref) - 60, 5):
        spans = [span_for(s, ref, site) for s in samples]
        spans = [s for s in spans if s is not None]
        if len(spans) < len(samples) * 0.6:
            continue          # anchors not conserved at this site
        excess = statistics.median(spans) - HUMAN_SPAN
        if excess > best[0]:
            best = (excess, site)
    return best[1]


def detect_insert(seq: str, ref: str, site: int) -> dict:
    """Insert = span excess over the no-insert reference span; sequence
    extracted by removing the conserved middle from the span."""
    L, R, mid = _windows(ref, site)
    ia = anchor_find(seq, L)
    if ia is not None:
        ib = anchor_find(seq[ia + len(L):], R, max_mm=3)
        if ib is not None:
            span = seq[ia + len(L): ia + len(L) + ib]
            excess = len(span) - HUMAN_SPAN
            # exact insert residues: drop the conserved middle copy
            ins = span
            if len(mid) >= 12:
                p = anchor_find(span, mid, max_mm=3)
                if p is not None:
                    ins = span[:p] + span[p + len(mid):]
            present = excess >= MIN_INSERT and len(ins) >= MIN_INSERT
            return {"len": len(seq),
                    "insert_len": len(ins) if present else max(0, excess),
                    "insert_start": ia + len(L) + 1,
                    "insert_seq": ins if present else ""}
    # NW fallback for divergent sequences
    qa, ra = nw_align(seq, ref)
    runs = merged_gap_runs(qa, ra)
    if runs:
        ins = max(runs, key=lambda r: r["len"])
        if ins["len"] >= MIN_INSERT:
            return {"len": len(seq), "insert_len": ins["len"],
                    "insert_start": ins["start"] + 1,
                    "insert_seq": seq[ins["start"]:ins["start"] + ins["len"]]}
    return {"len": len(seq), "insert_len": 0, "insert_start": None,
            "insert_seq": ""}


# -------------------------------------------------------------- mammals ----
def mammal_anp32(acc: str) -> dict:
    cache = CACHE / f"{acc}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        zpath = td / "p.zip"
        for attempt in range(3):
            r = subprocess.run(
                ["pixi", "run", "datasets", "download", "genome", "accession", acc,
                 "--include", "protein", "--filename", str(zpath)],
                capture_output=True, text=True, timeout=900)
            if r.returncode == 0 and zpath.exists():
                break
            print(f"  {acc} attempt {attempt+1}: {(r.stderr or '')[-120:]}",
                  file=sys.stderr)
            time.sleep(10 * (attempt + 1))
        else:
            return {}
        found: dict[str, str] = {}
        # datasets protein FASTA headers carry descriptions, not [gene=]
        # attributes: "acidic leucine-rich nuclear phosphoprotein 32 family
        # member A isoform X1 [Felis catus]" — match on both when present
        NAME_PAT = {
            "A": re.compile(r"phosphoprotein\s*32\s*(?:family\s*)?member\s+A\b|\bpp32\b|\bLANP\b", re.I),
            "B": re.compile(r"phosphoprotein\s*32\s*(?:family\s*)?member\s+B\b|PHAP-?II", re.I),
            "E": re.compile(r"phosphoprotein\s*32\s*(?:family\s*)?member\s+E\b", re.I),
        }
        GENE_PAT = {"A": {"ANP32A"}, "B": {"ANP32B", "ANP32B1", "PP32R1"}, "E": {"ANP32E"}}
        with zipfile.ZipFile(zpath) as z:
            for member in z.namelist():
                if not member.endswith(".faa"):
                    continue
                with z.open(member) as f:
                    txt = f.read().decode()
                for head, seq in parse_fasta(txt):
                    if len(seq) < 120 or len(seq) > 500:
                        continue
                    g = re.search(r"\[gene=([^\]]+)\]", head)
                    gene = (g.group(1).upper() if g else "")
                    par = next((p for p, names in GENE_PAT.items()
                                if gene in names), None)
                    if par is None:
                        par = next((p for p, pat in NAME_PAT.items()
                                    if pat.search(head)), None)
                    if par is None:
                        continue
                    # keep the isoform closest to the human reference length
                    # (avoids odd X-isoforms with retained tails)
                    if par not in found or abs(len(seq) - 249) < abs(len(found[par]) - 249):
                        found[par] = seq
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(found))
    return found


# ----------------------------------------------------------------- main ----
def main() -> int:
    smap = json.loads(SPECIES_MAP.read_text())
    smap_by_binomial = {s["label"].split("__")[0]: s for s in smap}

    refs = {}
    for par, acc in UNIPROT.items():
        seq = parse_fasta(fetch_uniprot(acc))[0][1]
        refs[par] = {"uniprot": acc, "label": f"Human ANP32{par}",
                     "seq": seq, "len": len(seq), "insert_len": 0}

    species: dict[str, dict] = {}

    for par, og in OGS.items():
        msa_path = OF_RESULTS / "MultipleSequenceAlignments" / f"{og}.fa"
        if not msa_path.exists():
            print(f"  WARN {og} MSA missing", file=sys.stderr)
            continue
        recs = parse_fasta(msa_path.read_text())
        # one entry per species binomial: keep the longest protein
        by_species: dict[str, str] = {}
        for head, seq in recs:
            key = head.split("__")[0]
            ung = seq.replace("-", "")
            if key not in by_species or len(ung) > len(by_species[key]):
                by_species[key] = ung
        full_lens = [len(s) for s in by_species.values() if len(s) >= 200]
        modal_len = Counter(full_lens).most_common(1)[0][0] if full_lens else 250

        # data-driven junction site: the site where bird spans exceed the
        # no-insert reference span by the most
        import random
        sample_keys = random.Random(42).sample(sorted(by_species),
                                                min(30, len(by_species)))
        site = pick_site(refs[par]["seq"],
                         [by_species[k] for k in sample_keys
                          if len(by_species[k]) >= 200] or list(by_species.values())[:30])
        refs[par]["site"] = site

        frag_thresh = 0.7 * modal_len
        for key, ung in by_species.items():
            meta = smap_by_binomial.get(key)
            sci = meta["sci"] if meta else key.replace("_", " ")
            entry = species.setdefault(sci, {
                "com": meta["com"] if meta else sci,
                "order": meta.get("order") if meta else None,
                "group": "Aves"})
            entry[par] = detect_insert(ung, refs[par]["seq"], site)
            if len(ung) < frag_thresh:
                entry[par]["frag"] = True

    # ---- mammals with confirmed HPAI ----
    mammals = [m for m in json.loads(MAMMALS.read_text()) if m.get("genome_acc")]
    print(f"mammals with genomes: {len(mammals)}", file=sys.stderr)
    for i, m in enumerate(mammals):
        sci = m["sci"]
        prots = mammal_anp32(m["genome_acc"])
        entry = species.setdefault(sci, {"com": m.get("com") or sci,
                                         "order": "Mammalia", "group": "Mammalia",
                                         "det": m.get("det") or 0})
        entry["group"] = "Mammalia"
        entry["det"] = m.get("det") or 0
        for par, seq in prots.items():
            entry[par] = detect_insert(seq, refs[par]["seq"], refs[par].get("site", 0))
        if (i + 1) % 10 == 0 or i == len(mammals) - 1:
            print(f"  [{i+1}/{len(mammals)}] mammals done", file=sys.stderr)

    stats = {}
    for par in "ABE":
        aves = [v[par]["insert_len"] for v in species.values()
                if v.get("group") == "Aves" and par in v]
        mam = [v[par]["insert_len"] for v in species.values()
               if v.get("group") == "Mammalia" and par in v]
        stats[par] = {"aves_hist": dict(sorted(Counter(aves).items())),
                      "mammal_hist": dict(sorted(Counter(mam).items())),
                      "aves_n": len(aves), "mammal_n": len(mam)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "meta": {
            "generated": datetime.fromtimestamp(time.time(), tz=timezone.utc)
                           .isoformat(timespec="seconds"),
            "method": ("insert = span between conserved flanking windows of the "
                       "human ANP32 references (site derived by NW to an avian "
                       "carrier; acidic-duplication gap runs merged); birds from "
                       "OrthoFinder OG MSAs, mammals via NCBI datasets protein "
                       "FASTAs (HPAI-confirmed species only)"),
        },
        "references": {p: {k: v for k, v in r.items()
                           if k not in ("seq",)} for p, r in refs.items()},
        "stats": stats,
        "species": species,
    }))
    print(f"wrote {OUT.name}: {len(species)} species "
          f"({stats['A']['aves_n']} birds + {stats['A']['mammal_n']} mammals on ANP32A)",
          file=sys.stderr)
    for par in "ABE":
        s = stats[par]
        print(f"  ANP32{par}: aves {s['aves_hist']} | mammals {s['mammal_hist']}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
