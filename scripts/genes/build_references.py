#!/usr/bin/env python3
"""
Build verified multi-species reference sequences for the gene-presence panel.

For each panel gene + each control gene:
  1. Resolve the chicken (Gallus gallus) gene ID by symbol — STRICTLY verified
     (returned symbol must match query or list it as an alternate name).
  2. Resolve the duck (Anas platyrhynchos) ortholog — by duck symbol search,
     falling back to the chicken ID's ortholog set.
  3. Download NCBI gene data packages (transcripts rna.fna + protein.faa).
  4. Keep the longest transcript as the primary reference; record full
     provenance (IDs, accessions, sha256, date) in a manifest.

This REPLACES the old data/genes/sequences/ fastas, whose accessions were
mislabeled (e.g. 'ANP32A_chicken.fasta' was HSF1; gene ID 395532 in the old
panel is COL1A1). See docs/GENE_PRESENCE_LOG.md D5.

Usage: pixi run python scripts/genes/build_references.py [--limit N]
"""

import argparse
import hashlib
import json
import subprocess
import time
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GENE_DIR = ROOT / "data" / "genes"
PANEL = GENE_DIR / "host_panel_v2.json"
OUT_DIR = GENE_DIR / "references_v2"
MANIFEST = OUT_DIR / "manifest.json"

CHICKEN = "Gallus gallus"
DUCK = "Anas platyrhynchos"

# Single-copy housekeeping controls for the searchability score (plan §D2/D)
CONTROL_GENES = [
    "ACTB", "GAPDH", "RPL5", "RPL8", "RPLP0", "HPRT1",
    "TBP", "TFRC", "YWHAZ", "SDHA", "UBC", "B2M",
]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kw)


def datasets(*args):
    """Run pixi datasets CLI, return stdout."""
    r = run(["pixi", "run", "datasets", *args])
    if r.returncode != 0:
        raise RuntimeError(f"datasets {' '.join(args[:4])}… failed: {r.stderr[:200]}")
    return r.stdout


def resolve_symbol(symbol: str, taxon: str):
    """Resolve a gene symbol to (gene_id, matched_symbol, description)."""
    out = datasets("summary", "gene", "symbol", symbol, "--taxon", taxon)
    d = json.loads(out)
    for r in d.get("reports", []):
        g = r["gene"]
        syms = {g.get("symbol", "").upper(), symbol.upper()} | {
            a.upper() for a in g.get("alternate_names", [])
        }
        if symbol.upper() in syms:
            return g["gene_id"], g.get("symbol"), g.get("description", "")
    return None, None, None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def download_gene(gene_id: str, dest: Path, ortholog: str | None = None) -> dict | None:
    """Download a gene package (optionally ortholog-filtered) and extract seqs."""
    args = ["download", "gene", "gene-id", gene_id, "--filename", str(dest)]
    if ortholog:
        args += ["--ortholog", ortholog]
    datasets(*args)
    if not dest.exists():
        return None
    files = {}
    with zipfile.ZipFile(dest) as z:
        for name in z.namelist():
            base = name.rsplit("/", 1)[-1]
            if base in ("rna.fna", "protein.faa", "data_report.jsonl"):
                files[base] = z.read(name).decode("utf-8", errors="ignore")
    if not files:
        return None
    return {
        "rna": files.get("rna.fna", ""),
        "protein": files.get("protein.faa", ""),
        "report": files.get("data_report.jsonl", ""),
        "zip_sha": sha256(dest),
    }


def longest_seq(fasta: str) -> tuple[str, int] | None:
    """Return (header, length) of the longest sequence in a FASTA string."""
    best, best_len, cur, cur_len = None, -1, None, 0
    for line in fasta.splitlines():
        if line.startswith(">"):
            if cur and cur_len > best_len:
                best, best_len = cur, cur_len
            cur, cur_len = line[1:], 0
        else:
            cur_len += len(line.strip())
    if cur and cur_len > best_len:
        best, best_len = cur, cur_len
    return (best, best_len) if best else None


def write_fasta(path: Path, header: str, fasta: str):
    """Write just the longest record to path."""
    lines = []
    take = False
    for line in fasta.splitlines():
        if line.startswith(">"):
            take = line[1:] == header
            if take:
                lines.append(f">{line[1:]}")
        elif take:
            lines.append(line.strip())
    path.write_text("\n".join(lines) + "\n")


def build_gene_entry(symbol: str, is_control: bool = False, tier: int | None = None,
                     known_gene_id: str | None = None, want_duck: bool = True):
    entry = {
        "symbol": symbol,
        "is_control": is_control,
        "tier": tier,
        "chicken_gene_id": None,
        "duck_gene_id": None,
        "chicken": None,
        "duck": None,
        "status": "ok",
        "note": None,
    }

    # chicken (known ID short-circuits symbol resolution — backbone entries)
    cid = known_gene_id
    csym, cdesc = symbol, ""
    if not cid:
        try:
            cid, csym, cdesc = resolve_symbol(symbol, CHICKEN)
            time.sleep(0.4)
        except Exception as e:
            entry["status"] = "error"
            entry["note"] = f"chicken resolve: {e}"
            return entry
    if not cid:
        # Duck-first fallback (D7): genes absent from chicken's annotation
        # (DDX58/RIG-I is the canonical case). Resolve in duck and use the
        # duck gene ID as the anchor; blast still runs against every genome.
        try:
            did, dsym, ddesc = resolve_symbol(symbol, DUCK)
            time.sleep(0.4)
        except Exception:
            did = None
        if did:
            entry["duck_gene_id"] = did
            gene_dir = OUT_DIR / "controls" / symbol if is_control else OUT_DIR / symbol
            gene_dir.mkdir(parents=True, exist_ok=True)
            try:
                pkg = download_gene(did, gene_dir / "_duck.zip")
                time.sleep(0.4)
                if pkg and pkg["rna"]:
                    hdr, ln = longest_seq(pkg["rna"])
                    write_fasta(gene_dir / "duck_rna.fna", hdr, pkg["rna"])
                    phdr, pln = (longest_seq(pkg["protein"]) or (None, 0))
                    if phdr:
                        write_fasta(gene_dir / "duck_protein.faa", phdr, pkg["protein"])
                    entry["duck"] = {
                        "resolved_symbol": dsym, "description": ddesc,
                        "rna_header": hdr, "rna_len": ln,
                        "protein_len": pln or None, "zip_sha": pkg["zip_sha"],
                    }
                    entry["status"] = "chicken_absent_duck_reference"
                    return entry
            except Exception as e:
                entry["note"] = f"duck-first download: {e}"
        entry["status"] = "chicken_symbol_not_found"
        return entry
    entry["chicken_gene_id"] = cid

    # duck (skip for controls and tier-3 backbone genes — chicken refs only)
    did = None
    if not is_control and want_duck:
        try:
            did, _, _ = resolve_symbol(symbol, DUCK)
            time.sleep(0.4)
        except Exception:
            did = None
    entry["duck_gene_id"] = did

    gene_dir = OUT_DIR / "controls" / symbol if is_control else OUT_DIR / symbol
    gene_dir.mkdir(parents=True, exist_ok=True)

    # chicken sequences
    try:
        pkg = download_gene(cid, gene_dir / "_chicken.zip")
        time.sleep(0.4)
        if pkg and pkg["rna"]:
            hdr, ln = longest_seq(pkg["rna"])
            write_fasta(gene_dir / "chicken_rna.fna", hdr, pkg["rna"])
            phdr, pln = (longest_seq(pkg["protein"]) or (None, 0))
            if phdr:
                write_fasta(gene_dir / "chicken_protein.faa", phdr, pkg["protein"])
            entry["chicken"] = {
                "resolved_symbol": csym, "description": cdesc,
                "rna_header": hdr, "rna_len": ln,
                "protein_len": pln or None, "zip_sha": pkg["zip_sha"],
            }
    except Exception as e:
        entry["status"] = "error"
        entry["note"] = f"chicken download: {e}"
        return entry

    # duck sequences via ortholog set (works even when duck symbol differs)
    if not is_control and want_duck:
        try:
            pkg = download_gene(cid, gene_dir / "_duck.zip", ortholog=DUCK)
            time.sleep(0.4)
            if pkg and pkg["rna"]:
                hdr, ln = longest_seq(pkg["rna"])
                write_fasta(gene_dir / "duck_rna.fna", hdr, pkg["rna"])
                phdr, pln = (longest_seq(pkg["protein"]) or (None, 0))
                if phdr:
                    write_fasta(gene_dir / "duck_protein.faa", phdr, pkg["protein"])
                # actual duck gene id from report
                for line in pkg["report"].splitlines():
                    if line.strip():
                        g = json.loads(line).get("gene", {})
                        entry["duck_gene_id"] = entry["duck_gene_id"] or g.get("gene_id")
                        break
                entry["duck"] = {
                    "rna_header": hdr, "rna_len": ln,
                    "protein_len": pln or None, "zip_sha": pkg["zip_sha"],
                }
        except Exception as e:
            entry["note"] = (entry["note"] or "") + f" | duck download: {e}"

    return entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="limit genes (testing)")
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--only", default=None,
                        help="comma-separated symbols: build only these genes")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = json.loads(PANEL.read_text())
    manifest_path = OUT_DIR / "_downloads"
    manifest_path.mkdir(exist_ok=True)

    if not args.controls_only:
        genes = panel["genes"]
        if args.only:
            only = {s.strip().upper() for s in args.only.split(",") if s.strip()}
            genes = [g for g in genes if g["symbol"].upper() in only]
            print(f"--only: {len(genes)} panel genes match {len(only)} requested symbols")
            # skip genes already resolved with sequences (idempotent re-runs)
            if (OUT_DIR / "panel_references.json").exists():
                prev = {e["symbol"].upper(): e for e in json.loads(
                    (OUT_DIR / "panel_references.json").read_text())["genes"]}
                keep, skipped = [], 0
                for g in genes:
                    e = prev.get(g["symbol"].upper())
                    if e and (e.get("chicken") or e.get("duck")):
                        skipped += 1
                        continue
                    keep.append(g)
                print(f"  skipping {skipped} genes with existing references")
                genes = keep
        if args.limit:
            genes = genes[:args.limit]
        entries = []
        print(f"Building references for {len(genes)} panel genes…")
        for i, g in enumerate(genes):
            e = build_gene_entry(
                g["symbol"], tier=g["tier"],
                known_gene_id=(str(g["chicken_gene_id"]) if g.get("chicken_gene_id") else None),
                want_duck=(g["tier"] or 3) <= 2,
            )
            entries.append(e)
            flag = "✓" if e["status"] == "ok" and e["chicken"] else e["status"]
            print(f"  [{i+1}/{len(genes)}] {g['symbol']:10s} chicken={e['chicken_gene_id']} "
                  f"duck={e['duck_gene_id']} {flag}", flush=True)

        # merge with the existing manifest so --only subset runs never shrink
        # the panel (blast_presence reads the full gene list from it); entries
        # skipped as already-resolved are carried over unchanged.
        manifest_path_json = OUT_DIR / "panel_references.json"
        if manifest_path_json.exists():
            prev = json.loads(manifest_path_json.read_text())
            built = {e["symbol"].upper(): e for e in entries}
            merged = [built.get(e["symbol"].upper(), e) for e in prev["genes"]]
            for sym, e in built.items():
                if sym not in {e2["symbol"].upper() for e2 in prev["genes"]}:
                    merged.append(e)
            entries = merged
        out = {
            "panel_version": panel["panel_version"],
            "generated": date.today().isoformat(),
            "genes": entries,
        }
        (OUT_DIR / "panel_references.json").write_text(json.dumps(out, indent=1))
        ok = sum(1 for e in entries if e["chicken"])
        print(f"\npanel references: {ok}/{len(entries)} with chicken seqs → panel_references.json")

    print("\nBuilding control-gene references…")
    controls = []
    for i, sym in enumerate(CONTROL_GENES):
        e = build_gene_entry(sym, is_control=True)
        controls.append(e)
        print(f"  [{i+1}/{len(CONTROL_GENES)}] {sym:8s} chicken={e['chicken_gene_id']} "
              f"{'✓' if e['chicken'] else e['status']}", flush=True)
    (OUT_DIR / "control_references.json").write_text(json.dumps({
        "generated": date.today().isoformat(), "genes": controls,
    }, indent=1))
    ok = sum(1 for e in controls if e["chicken"])
    print(f"controls: {ok}/{len(controls)}")


if __name__ == "__main__":
    main()
