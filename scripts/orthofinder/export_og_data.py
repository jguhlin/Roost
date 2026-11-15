#!/usr/bin/env python3
"""Export per-orthogroup web payloads for panel-mapped OGs.

For each OG in web/public/data/gene_orthogroups.json (primary OGs of panel genes):
  - web/public/data/orthogroups/{OG}.json
      members (species of_id, accession, NCBI product, tree/MSA leaf key),
      per-species copy-count vector (aligned to species_map.json of_id order),
      resolved-gene-tree Newick, summary stats.
  - web/public/data/orthogroups/{OG}.fa.zst
      MSA, all-gap columns dropped, <=150 representative species
      (RefSeq proteins preferred; chicken & mallard always kept),
      zstd -19 (no --long; browser fzstd-compatible).

Run:  pixi run python scripts/orthofinder/export_og_data.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OF_RUN = ROOT / "orthofinder" / "orthofinder_aves463_root16_20260928"
RESULTS = OF_RUN / "Results_Aves463_Root16"
MAP_JSON = ROOT / "web" / "public" / "data" / "gene_orthogroups.json"
SPECIES_JSON = ROOT / "web" / "public" / "data" / "orthofinder" / "species_map.json"
OUT_DIR = ROOT / "web" / "public" / "data" / "orthogroups"

CHICKEN_OF_ID = 186
MALLARD_OF_ID = 19
MAX_TAXA = 150
MAX_DECOMPRESSED = 2_000_000  # bytes of FASTA before we shed more species


def leaf_key(label: str, acc: str) -> str:
    sci, asm = label.split("__")
    return f"{sci}__{asm.replace('.', '_')}_{acc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--of-run", type=Path, default=OF_RUN)
    ap.add_argument("--limit", type=int, default=None, help="export only first N OGs")
    args = ap.parse_args()
    t0 = time.time()

    run, results = args.of_run, args.of_run / "Results_Aves463_Root16"

    gene_map = json.loads(MAP_JSON.read_text())
    wanted: set[str] = set(gene_map["og_to_genes"])
    if args.limit:
        wanted = set(sorted(wanted)[: args.limit])
    print(f"OGs to export: {len(wanted)}", file=sys.stderr)

    # species: of_id -> label, ordered list
    smap = json.loads(SPECIES_JSON.read_text())
    smap.sort(key=lambda r: r["of_id"])
    of_ids = [r["of_id"] for r in smap]
    label = {r["of_id"]: r["label"] for r in smap}
    pos = {oid: i for i, oid in enumerate(of_ids)}

    # ---- membership rows ----------------------------------------------------
    label_to_ofid: dict[str, int] = {r["label"]: r["of_id"] for r in smap}
    members: dict[str, list[tuple[int, str]]] = defaultdict(list)  # og -> (of_id, acc)
    with open(results / "Orthogroups" / "Orthogroups.tsv") as f:
        header = f.readline().rstrip("\n").split("\t")[1:]
        for row in f:
            og = row.split("\t", 1)[0]
            if og not in wanted:
                continue
            parts = row.rstrip("\n").split("\t")
            for i, cell in enumerate(parts[1:]):
                if cell:
                    ofid = label_to_ofid[header[i]]
                    for a in cell.split(","):
                        members[og].append((ofid, a.strip()))
    print(f"[1] membership: {sum(len(v) for v in members.values())} proteins "
          f"({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- products for member accessions --------------------------------------
    need_acc = {a for lst in members.values() for _, a in lst}
    product: dict[str, str] = {}
    with open(run / "Identifiers" / "SequenceIDs.txt") as f:
        for line in f:
            iid, rest = line.split(": ", 1)
            acc = rest.split(" ")[0]
            if acc in need_acc:
                desc = rest[len(acc):].strip().rstrip("\n")
                if " [" in desc:  # strip trailing "[Species]"
                    desc = desc.rsplit(" [", 1)[0]
                product[acc] = desc
    print(f"[2] products: {len(product)} accessions ({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- copy counts ----------------------------------------------------------
    counts: dict[str, list[int]] = {}
    with open(results / "Orthogroups" / "Orthogroups.GeneCount.tsv") as f:
        hdr = f.readline().rstrip("\n").split("\t")
        gc_label_to_idx = {lab: i for i, lab in enumerate(hdr[1:])}
        for row in f:
            og = row.split("\t", 1)[0]
            if og not in wanted:
                continue
            parts = row.rstrip("\n").split("\t")
            vec = [0] * len(of_ids)
            for lab, i in gc_label_to_idx.items():
                if lab not in label_to_ofid:  # trailing 'Total' column
                    continue
                if i < len(parts) - 1 and parts[i + 1].strip():
                    vec[pos[label_to_ofid[lab]]] = int(parts[i + 1])
            counts[og] = vec
    print(f"[3] counts: {len(counts)} OG rows ({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- trees ------------------------------------------------------------------
    trees: dict[str, str] = {}
    with open(results / "Resolved_Gene_Trees" / "Resolved_Gene_Trees.txt") as f:
        for line in f:
            og = line.split(":", 1)[0]
            if og in wanted:
                trees[og] = line.rstrip("\n").split(": ", 1)[1].rstrip(";") + ";"
    print(f"[4] trees: {len(trees)} ({time.time()-t0:.0f}s)", file=sys.stderr)

    # ---- per-OG export ------------------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_msa = 0
    msa_bytes = 0
    biggest = ("", 0)
    for og in sorted(wanted):
        mem = members.get(og, [])
        vec = counts.get(og, [0] * len(of_ids))
        present = sum(1 for v in vec if v > 0)
        max_copies = max(vec) if vec else 0
        total_copies = sum(vec)

        payload = {
            "og": og,
            "genes": gene_map["og_to_genes"].get(og, []),
            "n_species": len(of_ids),
            "n_species_present": present,
            "n_proteins": total_copies,
            "max_copies": max_copies,
            "single_copy": present > 1 and max_copies == 1,
            "counts": vec,
            "has_tree": og in trees,
            "has_msa": False,
            "members": [
                {"s": ofid, "a": acc,
                 "p": product.get(acc, ""),
                 "m": leaf_key(label[ofid], acc)}
                for ofid, acc in mem
            ],
        }
        if og in trees:
            payload["tree"] = trees[og]

        # ---- MSA ----
        msa_path = results / "MultipleSequenceAlignments" / f"{og}.fa"
        if msa_path.exists():
            # choose representative accessions: RefSeq preferred, <=MAX_TAXA species
            by_species: dict[int, list[str]] = defaultdict(list)
            for ofid, a in mem:
                by_species[ofid].append(a)
            chosen: dict[int, str] = {}
            for ofid, accs in by_species.items():
                chosen[ofid] = sorted(accs, key=lambda a: 0 if a.startswith(("NP_", "XP_")) else 1)[0]
            sp = sorted(chosen)
            if len(sp) > MAX_TAXA:
                keep = {CHICKEN_OF_ID, MALLARD_OF_ID} & set(sp)
                rest = [s for s in sp if s not in keep]
                step = (len(rest) + 1) / (MAX_TAXA - len(keep) + 1)
                sp = sorted(keep | {rest[min(int(i * step), len(rest) - 1)]
                                    for i in range(MAX_TAXA - len(keep))})
            wanted_keys = {leaf_key(label[s], chosen[s]) for s in sp}
            seqs: dict[str, str] = {}
            cur = None
            with open(msa_path) as f:
                for line in f:
                    if line.startswith(">"):
                        cur = line[1:].strip()
                        seqs[cur] = "" if cur in wanted_keys else None
                    elif cur is not None and seqs.get(cur) is not None:
                        seqs[cur] += line.strip()
            seqs = {k: v for k, v in seqs.items() if v is not None}
            if seqs:
                # shed species if FASTA too large, then drop all-gap columns
                def fasta_len(d):
                    return sum(len(k) + len(v) + 3 for k, v in d.items())
                while fasta_len(seqs) > MAX_DECOMPRESSED and len(seqs) > 60:
                    for k in sorted(seqs)[int(len(seqs) * 0.7):]:
                        seqs.pop(k, None)
                keys = list(seqs)
                if keys:
                    drop_cols = set()
                    for c in range(len(seqs[keys[0]])):
                        if all(s[c] in "-.Xx" for s in seqs.values()):
                            drop_cols.add(c)
                    if drop_cols:
                        for k in keys:
                            seqs[k] = "".join(ch for i, ch in enumerate(seqs[k]) if i not in drop_cols)
                    out_fa = OUT_DIR / f"{og}.fa"
                    with open(out_fa, "w") as f:
                        for k in keys:
                            f.write(f">{k}\n{seqs[k]}\n")
                    subprocess.run(["zstd", "-19", "-q", "-f", str(out_fa),
                                    "-o", str(OUT_DIR / f"{og}.fa.zst")], check=True)
                    out_fa.unlink()
                    n_msa += 1
                    zb = (OUT_DIR / f"{og}.fa.zst").stat().st_size
                    msa_bytes += zb
                    if zb > biggest[1]:
                        biggest = (og, zb)
                    payload["has_msa"] = True

        (OUT_DIR / f"{og}.json").write_text(json.dumps(payload, ensure_ascii=False))

    print(f"[5] exported {len(wanted)} OG JSONs, {n_msa} MSAs "
          f"({msa_bytes/1e6:.1f} MB zst total, biggest {biggest[0]} {biggest[1]/1e3:.0f} KB) "
          f"({time.time()-t0:.0f}s)", file=sys.stderr)

    # slim summary for the gene page (avoids fetching member-heavy OG JSONs)
    summary = {}
    for path in sorted(OUT_DIR.glob("OG*.json")):
        d = json.loads(path.read_text())
        summary[d["og"]] = {
            "n_species_present": d["n_species_present"],
            "n_proteins": d["n_proteins"],
            "max_copies": d["max_copies"],
            "single_copy": d["single_copy"],
            "has_tree": d["has_tree"],
            "has_msa": d["has_msa"],
        }
    (OUT_DIR / "og_summary.json").write_text(json.dumps(summary, ensure_ascii=False))
    print(f"[6] wrote og_summary.json ({len(summary)} entries)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
