#!/usr/bin/env python3
"""
annotate_overlaps.py — cross-reference evidence HSP loci with the staged
NCBI gene annotation for each genome.

For every (gene, species) record in web/public/data/evidence/*.json that has
genomic HSPs, find annotated genes overlapping the HSP cluster and record
them under `annotation_hits`:

    "annotation_hits": [
      {
        "gene": "IRF7", "biotype": "protein_coding",
        "gene_id": "gene-IRF7", "gstart": 15442326, "gend": 15445784,
        "overlap_bp": 2933,
        "transcripts": [
          {"acc": "NM_205372.2",
           "product": "interferon regulatory factor 7",
           "cds_products": ["interferon regulatory factor 3"]}
        ]
      }
    ]

This answers "is the hit really an unannotated gene, or does it fall inside
an existing NCBI annotation (possibly under a different name)?" — e.g.
chicken IFITM3 sits on LOC770612 ("IFITM1-like" gene name, IFITM3 CDS
product), and the chicken "IRF3" search hits the annotated IRF7 locus.

Idempotent: rewrites a file only when its annotation_hits change.
Requires the genome to be staged (annotation.gff.bgz present) — records for
unstaged genomes are left untouched.

Usage:
    python scripts/genes/annotate_overlaps.py [--report] [--quiet]
        --report   print name-mismatch cases (queried symbol vs annotation)
"""

import argparse
import glob
import gzip
import json
import os
import re
import sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVIDENCE_DIR = os.path.join(ROOT, 'web', 'public', 'data', 'evidence')
GENOMES_DIR = os.path.join(ROOT, 'web', 'public', 'data', 'genomes')

MAX_HITS = 3          # annotation genes kept per record
MIN_OVERLAP_BP = 20   # ignore trivial edge brushes


def parse_attrs(field):
    attrs = {}
    for kv in field.split(';'):
        if '=' in kv:
            k, v = kv.split('=', 1)
            attrs[unquote(k.strip())] = unquote(v.strip())
    return attrs


class Annotation:
    """gene-level view of one NCBI genome annotation (GFF3)."""

    def __init__(self, gff_path):
        # contig -> [(start, end, gene_name, biotype, gene_id)]
        self.genes = {}
        # gene_id -> [{acc, product}] transcript stubs (filled from mRNA lines)
        self.transcripts = {}
        # rna_id -> gene_id
        self.rna_parent = {}
        # rna_id -> set(cds products)
        self.cds_products = {}

        opener = gzip.open if gff_path.endswith('.gz') or gff_path.endswith('.bgz') else open
        with opener(gff_path, 'rt') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                p = line.rstrip('\n').split('\t')
                if len(p) < 9:
                    continue
                contig, ftype, start, end = p[0], p[2], int(p[3]), int(p[4])
                attrs = parse_attrs(p[8])

                if ftype == 'gene':
                    name = attrs.get('gene') or attrs.get('Name') or attrs.get('ID', '')
                    self.genes.setdefault(contig, []).append(
                        (start, end, name, attrs.get('gene_biotype', ''), attrs.get('ID', ''))
                    )
                elif ftype in ('mRNA', 'transcript'):
                    gid = attrs.get('Parent', '')
                    acc = attrs.get('transcript_id') or attrs.get('ID', '').replace('rna-', '')
                    self.rna_parent[attrs.get('ID', '')] = gid
                    if gid:
                        self.transcripts.setdefault(gid, []).append(
                            {'acc': acc, 'product': attrs.get('product', ''), 'rna_id': attrs.get('ID', '')}
                        )
                elif ftype == 'CDS':
                    rid = attrs.get('Parent', '')
                    prod = attrs.get('product', '')
                    if rid and prod:
                        self.cds_products.setdefault(rid, set()).add(prod)

        for lst in self.genes.values():
            lst.sort()

    def overlapping(self, contig, intervals):
        """genes overlapping any (start, end) interval; returns annotation_hits dicts."""
        hits = {}
        for (gstart, gend, name, biotype, gid) in self.genes.get(contig, []):
            ov = 0
            for (s, e) in intervals:
                ov += max(0, min(e, gend) - max(s, gstart))
            if ov >= MIN_OVERLAP_BP:
                txs = []
                for tx in self.transcripts.get(gid, [])[:3]:
                    txs.append({
                        'acc': tx['acc'],
                        'product': tx['product'],
                        'cds_products': sorted(self.cds_products.get(tx['rna_id'], []))[:3],
                    })
                hits[gid] = {
                    'gene': name, 'biotype': biotype, 'gene_id': gid,
                    'gstart': gstart, 'gend': gend, 'overlap_bp': ov,
                    'transcripts': txs,
                }
        return sorted(hits.values(), key=lambda h: -h['overlap_bp'])[:MAX_HITS]


def record_intervals(rec):
    """(contig, [(start, end)]) for the verdict cluster: exon HSPs + protein HSPs."""
    spans = {}
    for h in (rec.get('exon_hsps') or []) + (rec.get('hsps') or []):
        if h.get('gstart') is not None:
            spans.setdefault(h.get('contig') or rec.get('contig'), []).append((h['gstart'], h['gend']))
    return spans.items()


def hit_text(hit):
    """all searchable text for a hit, for the name-match report"""
    parts = [hit.get('gene', '')]
    for tx in hit.get('transcripts', []):
        parts.append(tx.get('product', ''))
        parts.extend(tx.get('cds_products', []))
    return ' '.join(parts).lower()


def norm_symbol(sym):
    return re.sub(r'[^a-z0-9]', '', sym.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true', help='print queried-symbol vs annotation mismatches')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(EVIDENCE_DIR, '*.json')))
    docs = {}          # path -> parsed json (records mutated in place)
    by_assembly = {}   # assembly -> [(path, gene, species_key, record)]
    for path in files:
        try:
            d = json.load(open(path))
        except Exception as e:
            print(f'  ! skipping {os.path.basename(path)}: {e}', file=sys.stderr)
            continue
        docs[path] = d
        gene = d.get('gene')
        for sp, rec in (d.get('species') or {}).items():
            if rec.get('assembly') and (rec.get('hsps') or rec.get('exon_hsps')):
                by_assembly.setdefault(rec['assembly'], []).append((path, gene, sp, rec))

    total_updated, total_records, total_hits = 0, 0, 0
    changed = set()    # paths with mutated records
    mismatch_cases = []

    for assembly in sorted(by_assembly):
        gff = os.path.join(GENOMES_DIR, assembly, 'annotation.gff.bgz')
        if not os.path.exists(gff):
            if not args.quiet:
                print(f'– {assembly}: no staged annotation, skipping {len(by_assembly[assembly])} records')
            continue
        if not args.quiet:
            print(f'· {assembly}: loading annotation…')
        ann = Annotation(gff)

        for (path, gene, sp, rec) in by_assembly[assembly]:
            total_records += 1
            new_hits = []
            for contig, intervals in record_intervals(rec):
                new_hits.extend(ann.overlapping(contig, intervals))
            new_hits = sorted(new_hits, key=lambda h: -h['overlap_bp'])[:MAX_HITS]
            if rec.get('annotation_hits') != new_hits:
                rec['annotation_hits'] = new_hits
                changed.add(path)
            if new_hits:
                total_hits += 1
                top = new_hits[0]
                text = hit_text(top)
                sym = norm_symbol(gene)
                if sym and sym not in re.sub(r'[^a-z0-9]', '', text):
                    mismatch_cases.append((gene, sp, top.get('gene'), (top.get('transcripts') or [{}])[0].get('product')))

    for path in changed:
        json.dump(docs[path], open(path, 'w'), separators=(',', ':'))
        total_updated += 1

    print(f'\n{total_records} genomic records scanned · {total_hits} overlap an annotation · {total_updated} files updated')

    if args.report:
        print(f'\n--- queried symbol not found in top annotation name/product ({len(mismatch_cases)}) ---')
        for gene, sp, ann_gene, product in mismatch_cases[:200]:
            print(f'  {gene:12s} × {sp:28s} -> annotated as {ann_gene} ({product})')


if __name__ == '__main__':
    main()
