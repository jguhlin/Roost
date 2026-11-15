#!/usr/bin/env python3
"""
verify_2bit.py — structural check of genome.2bit files against their sources.

For each requested assembly dir, parses the .2bit index (magic, sequence
count, names, dnaSize sum) and compares against the FASTA on disk
(genome.fna) or its KEEP_GENOMES archive (genome.fna.zst, streamed via
zstdcat — never decompressed to disk).

Catches: truncated writes, wrong-endian/garbled records, half-converted
files, and mismatched source pairs. Spot-decoding of bases is covered by
fa_to_2bit.py --verify when samtools is available; this script is the
samtools-free integrity gate.

Usage:
  python scripts/genes/verify_2bit.py [ACC ...]   # default: every genome.2bit
Exit 0 iff every checked file passes.
"""
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GENOMES = ROOT / "data" / "genomes"
MAGIC = 0x1A412743
ZSTD = ROOT / ".pixi" / "envs" / "default" / "bin" / "zstdcat"


def read_2bit_index(path: Path):
    """Return (seq_names, dna_sizes) from the .2bit header+index+records."""
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError(f"truncated header ({len(data)} bytes)")
    magic, _version, count = struct.unpack_from("<III", data, 0)
    if magic != MAGIC:
        raise ValueError(f"bad magic 0x{magic:08X} (expected 0x{MAGIC:08X})")
    pos = 16
    names, offsets = [], []
    for _ in range(count):
        nlen = data[pos]
        pos += 1
        names.append(data[pos:pos + nlen].decode())
        pos += nlen
        offsets.append(struct.unpack_from("<I", data, pos)[0])
        pos += 4
    sizes = []
    for off in offsets:
        if off + 4 > len(data):
            raise ValueError("record offset past EOF")
        sizes.append(struct.unpack_from("<I", data, off)[0])
    return names, sizes


def fasta_stats(acc_dir: Path):
    """Stream the FASTA (plain or zst) → (n_records, total_bases, first_name, last_name)."""
    fna = acc_dir / "genome.fna"
    if fna.exists():
        proc = subprocess.Popen(["cat", str(fna)], stdout=subprocess.PIPE)
    elif (acc_dir / "genome.fna.zst").exists():
        proc = subprocess.Popen([str(ZSTD), "-dc", str(acc_dir / "genome.fna.zst")],
                                stdout=subprocess.PIPE)
    else:
        raise FileNotFoundError("neither genome.fna nor genome.fna.zst")
    n = total = 0
    first = last = None
    assert proc.stdout is not None
    for line in proc.stdout:
        if line.startswith(b">"):
            n += 1
            name = line[1:].split()[0].decode()
            if first is None:
                first = name
            last = name
        else:
            total += len(line.strip())
    proc.stdout.close()
    if proc.wait() != 0:
        raise RuntimeError("FASTA stream failed")
    return n, total, first, last


def check_acc(acc: str) -> bool:
    acc_dir = GENOMES / acc
    tb = acc_dir / "genome.2bit"
    if not tb.exists():
        print(f"✗ {acc}: no genome.2bit")
        return False
    try:
        names, sizes = read_2bit_index(tb)
        fa_n, fa_total, fa_first, fa_last = fasta_stats(acc_dir)
    except Exception as e:
        print(f"✗ {acc}: {e}")
        return False
    ok = True
    if len(names) != fa_n:
        print(f"✗ {acc}: sequence count {len(names)} != FASTA {fa_n}")
        ok = False
    if sum(sizes) != fa_total:
        print(f"✗ {acc}: dnaSize sum {sum(sizes):,} != FASTA {fa_total:,}")
        ok = False
    # sequence identity is order-independent (2bit sorts names); check membership
    if set(names) != {fa_first, fa_last} and fa_first not in names:
        print(f"✗ {acc}: first FASTA seq {fa_first!r} missing from 2bit")
        ok = False
    if fa_last not in names:
        print(f"✗ {acc}: last FASTA seq {fa_last!r} missing from 2bit")
        ok = False
    if ok:
        print(f"✓ {acc}: {len(names):,} seqs, {sum(sizes):,} bases, "
              f"{tb.stat().st_size / 1e6:.0f} MB")
    return ok


def main():
    accs = sys.argv[1:]
    if not accs:
        accs = sorted(d.parent.name for d in GENOMES.glob("*/genome.2bit"))
    if not accs:
        print("no genome.2bit files found")
        return 1
    results = [check_acc(a) for a in accs]
    n_ok = sum(results)
    print(f"\n{n_ok}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
