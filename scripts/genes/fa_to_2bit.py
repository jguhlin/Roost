#!/usr/bin/env python3
"""
fa_to_2bit.py — convert FASTA to UCSC .2bit format (big-endian).

as UCSC writes them). 4 bases/byte packing (~4:1 compression) with N-run
blocks; fully random access, consumed by igv.js via range requests
(reference.twoBitURL). Soft-masking (lowercase) is dropped — these are
unmasked assemblies.

Format (all multi-byte integers BIG-ENDIAN), per UCSC spec:
  header:  magic 0x1A412743 | version=0 | sequenceCount | reserved=0
  index:   [nameLen u8 | name bytes] × N            (names sorted)
  sizes:   dnaSize u32 × N
  offsets: record offset u32 × N
  record:  dnaSize u32 | nBlockCount u32 | nStarts u32[] | nSizes u32[]
           | maskBlockCount u32 =0 | reserved u32 =0 | packedDNA

Usage:
    python scripts/genes/fa_to_2bit.py genome.fna genome.2bit [--verify]
"""
import argparse
import struct
import sys

MAGIC = 0x1A412743
# UCSC 2bit base encoding: 0=T, 1=C, 2=A, 3=G (NOT alphabetical)
BASE_CODES = {'T': 0, 'C': 1, 'A': 2, 'G': 3}
BYTE_OF = {}
for b1 in 'TCAG':
    for b2 in 'TCAG':
        for b3 in 'TCAG':
            for b4 in 'TCAG':
                BYTE_OF[b1 + b2 + b3 + b4] = (BASE_CODES[b1] << 6) | (BASE_CODES[b2] << 4) | (BASE_CODES[b3] << 2) | BASE_CODES[b4]


def read_fasta_sequences(path):
    """yield (name, sequence-uppercase-chunks list) per record, streaming"""
    name, chunks = None, []
    with open(path, 'rb') as f:
        for line in f:
            if line.startswith(b'>'):
                if name is not None:
                    yield name, chunks
                name = line[1:].split()[0].decode()
                chunks = []
            else:
                chunks.append(line.strip())
    if name is not None:
        yield name, chunks


def build_record(dna_chunks):
    """returns (record_bytes_without_size, dnaSize, nBlocks) for one sequence"""
    n_starts, n_sizes = [], []
    in_n, n_start, n_len = False, 0, 0
    packed = bytearray()
    quad = []
    dna_size = 0
    N_BYTE = BYTE_OF['TTTT']  # placeholder; N runs are tracked separately but
    # interior single-Ns inside packed regions still need an encoding — 2bit
    # requires Ns to be in nBlocks, so packed regions are ACGT-only. We pack
    # garbage for N positions (use 'T') — nBlocks overrides them on read.

    def flush_quad():
        packed.append(BYTE_OF[''.join(quad)])
        quad.clear()

    for chunk in dna_chunks:
        for ch in chunk.decode('ascii', 'ignore').upper():
            dna_size += 1
            if ch in BASE_CODES:  # ACGT
                if in_n:
                    n_starts.append(n_start); n_sizes.append(n_len); in_n = False
                quad.append(ch)
                if len(quad) == 4:
                    flush_quad()
            else:  # N or IUPAC ambiguity -> N
                if not in_n:
                    in_n, n_start, n_len = True, dna_size - 1, 1
                else:
                    n_len += 1
                quad.append('T')  # filler; real bases come from nBlocks
                if len(quad) == 4:
                    flush_quad()
    if in_n:
        n_starts.append(n_start); n_sizes.append(n_len)
    if quad:
        while len(quad) < 4:
            quad.append('T')  # tail padding
        flush_quad()

    header = struct.pack('<II', dna_size, len(n_starts))
    header += struct.pack(f'<{len(n_starts)}I', *n_starts) if n_starts else b''
    header += struct.pack(f'<{len(n_sizes)}I', *n_sizes) if n_sizes else b''
    header += struct.pack('<II', 0, 0)  # maskBlockCount=0, reserved=0
    return header + bytes(packed), dna_size


def convert(fasta_path, out_path):
    seqs = []  # (name, record_bytes, dnaSize)
    for name, chunks in read_fasta_sequences(fasta_path):
        rec, size = build_record(chunks)
        seqs.append((name, rec, size))
    seqs.sort(key=lambda s: s[0])

    n = len(seqs)
    # index layout (per actual UCSC files + igv/py2bit readers):
    #   header 16 bytes, then per sequence: [namelen u8][name][offset u32].
    # dnaSize lives at the start of each record, not in the index.
    offsets = []
    off = 16 + sum(1 + len(nm.encode()) + 4 for nm, _, _ in seqs)
    for _, rec, _ in seqs:
        offsets.append(off)
        off += len(rec)

    with open(out_path, 'wb') as f:
        f.write(struct.pack('<III', MAGIC, 0, n))
        f.write(struct.pack('<I', 0))  # reserved
        for (name, _, _), o in zip(seqs, offsets):
            nb = name.encode()
            f.write(bytes([len(nb)])); f.write(nb)
            f.write(struct.pack('<I', o))
        for _, rec, _ in seqs:
            f.write(rec)
    return n, off


def verify(fasta_path, two_bit_path):
    """spot-check: first 1000 bases + last 100 of first & biggest sequence"""
    import subprocess
    def faidx(name, start, end):
        out = subprocess.run(['samtools', 'faidx', fasta_path, f'{name}:{start}-{end}'],
                             capture_output=True, text=True).stdout
        return ''.join(out.split('\n')[1:]).upper()

    class TB:
        def __init__(self, path):
            self.f = open(path, 'rb')
            assert struct.unpack('<I', self.f.read(4))[0] == MAGIC
            _version = struct.unpack('<I', self.f.read(4))[0]
            cnt = struct.unpack('<I', self.f.read(4))[0]
            self.f.read(4)  # reserved
            idx, offs = [], []
            for _ in range(cnt):
                l = self.f.read(1)[0]
                idx.append(self.f.read(l).decode())
                offs.append(struct.unpack('<I', self.f.read(4))[0])
            sizes = {}
            for nm, o in zip(idx, offs):
                self.f.seek(o)
                sizes[nm] = struct.unpack('<I', self.f.read(4))[0]
            self.meta = {nm: (sizes[nm], o) for nm, o in zip(idx, offs)}

        def seq(self, name, start, end):
            size, off = self.meta[name]
            start = max(0, start)
            f = self.f
            f.seek(off)
            dna_size = struct.unpack('<I', f.read(4))[0]
            nblk = struct.unpack('<I', f.read(4))[0]
            nstarts = struct.unpack(f'<{nblk}I', f.read(4 * nblk)) if nblk else ()
            nsizes = struct.unpack(f'<{nblk}I', f.read(4 * nblk)) if nblk else ()
            f.read(8)  # mask count + reserved
            data_start = f.tell()
            out = []
            for p in range(start, min(end, dna_size)):
                # N?
                is_n = False
                for st, ln in zip(nstarts, nsizes):
                    if st <= p < st + ln:
                        is_n = True
                        break
                if is_n:
                    out.append('N')
                    continue
                byte = None
                f.seek(data_start + p // 4)
                byte = f.read(1)[0]
                code = (byte >> (2 * (3 - (p % 4)))) & 3
                out.append('TCAG'[code])
            return ''.join(out)

    tb = TB(two_bit_path)
    first = min(tb.meta, key=lambda n: tb.meta[n][1])
    biggest = max(tb.meta, key=lambda n: tb.meta[n][0])
    ok = True
    for name, s, e in [(first, 0, 1000), (first, max(0, tb.meta[first][0] - 100), tb.meta[first][0]),
                       (biggest, 1000, 2000)]:
        a, b = faidx(name, s + 1, e), tb.seq(name, s, e)
        if a != b:
            ok = False
            print(f'  MISMATCH {name}:{s}-{e}\n    faidx: {a[:60]}\n    2bit : {b[:60]}')
        else:
            print(f'  ok {name}:{s + 1}-{e} ({len(a)} bases match)')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fasta')
    ap.add_argument('out')
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    n, size = convert(args.fasta, args.out)
    print(f'{args.out}: {n} sequences, {size / 1e6:.1f} MB')
    if args.verify:
        print('verifying…')
        sys.exit(0 if verify(args.fasta, args.out) else 1)


if __name__ == '__main__':
    main()
