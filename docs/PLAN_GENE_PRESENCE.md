# Plan: Host Gene Presence Pipeline (Phase 3 Rebuild)

**Goal:** For every host-relevant gene, determine its presence status in every
available avian genome — with an honest evidence ladder that distinguishes
*proof positive* (annotation), *strong suggestion* (sequence found, unannotated),
*fragment* (partial sequence), and *absence with quantified doubt* (absence is
never proof of loss — assembly gaps, GC-biased regions, and microchromosome
dropout all conspire to hide genes).

**Status: DESIGN — no code yet. This document is the contract.**

---

## 1. What exists today (audit)

| Asset | State | Gap |
|-------|-------|-----|
| `scripts/detect_gene_presence.py` | 3,636 calls, 202 species; methods: NCBI ortholog API, gene DB, annotation symbol match; provenance schema (`GenePresenceCall`) | No sequence search (BLAST marked "future"); API rate limits; annotation-symbol matching only works for annotated genomes; "Absent" calls lack doubt quantification |
| `data/genes/sequences/` | Chicken CDS FASTAs for the 19-gene core panel | Single reference species (chicken); no protein sequences; no duck/outgroup anchors |
| `data/genes/gene_panel.json` | 19 genes, tiered | vs Avimm's ~1,170 chicken immune genes — the "all host relevant genes" ask |
| `docs/GENE_PANEL.md` | Panel design principles | No blast/absence-confidence methodology |
| Species modal "Gene Panel" tab | Placeholder "coming soon" | Awaiting real matrix |

**Key insight from the audit:** the current pipeline's "Absent" (1,618 calls)
mixes *searched-and-not-found* with *couldn't-search* (no annotation to match
against). The rebuild must separate these, and add the sequence-search layer
that converts many "Absent" calls into "Unannotated-found" (blast hit) or
absence-with-confidence.

---

## 2. Phase A — The gene list ("all host relevant genes")

Union, deduplicate, and tier — not a flat list:

| Source | ~Count | Role |
|--------|--------|------|
| Curated panel (existing) | 19 | Tier 1 — causal challenge-experiment evidence |
| Wiki corpus genes (57 canonical, 42 host-kind) | 42 | Tier 1–2 — every one carries paper citations; includes literature-only genes (BTN3A3, KPNA…) |
| Avian Immunome Database (Avimm) | ~1,170 | Tier 2–3 backbone — chicken immune genes w/ synonyms |
| NCBI Gene / Ensembl chicken GO immune terms | ~1,500 | Cross-check + catch Avimm misses |
| OMIA / literature resistance alleles (Mx1 S631N, MHC-B haplotypes) | handful | Variant-level (later phase) |

**Deduplication is the hard part** (immune families: IFITM cluster, OASL/OAS1,
MX1/MX2, TLR family, MHC). Rules:
1. Canonical symbol = NCBI Gene symbol for *Gallus gallus*; alias table carries
   Ensembl IDs, old symbols, Avimm names, and our wiki aliases (the shared
   `species_aliases`-style approach, one alias namespace per gene).
2. **Paralog families get family-aware handling**: each family member gets a
   *discriminator region* (most diverged 200–300 bp of CDS, or unique exon)
   flagged for blast discrimination; family-level presence is reported
   alongside member-level calls with lower confidence.
3. Each gene record: symbol, synonyms, NCBI/Ensembl gene IDs (chicken), CDS +
   protein accession refs, expected copy number (single/family), tier.

**Output:** `data/genes/host_panel_v2.json` (versioned — results are keyed to
panel version so re-runs are attributable).

---

## 3. Phase B — Reference sequences

Per gene, **multi-species reference set** (not chicken-only):

- **Anchor species**: chicken (annotation gold standard), duck *Anas
  platyrhynchos* (divergent anseriform; RIG-I positive where chicken is the
  known-loss control), zebra finch (passerine outgroup).
- Sequence types: CDS (blastn for close comparisons) **and protein (tblastn —
  the cross-species workhorse, tolerant of 20–30% divergence)**.
- Provenance per sequence: accession, database, retrieval date, checksum.
- **Pseudogene test**: store the intact-ORF coordinates so a hit can be checked
  for frameshifts/premature stops (→ `PSEUDOGENIZED` status, distinct from
  absent).

Decision (to settle before coding): CDS from NCBI Orthologs API where possible
(we already have the API plumbing), falling back to Ensembl BioMart/REST, then
manual curation for the stubborn cases (MHC-B especially).

---

## 4. Phase C — Target genome selection

We hold 3,851 assemblies / 1,979 species. Not all deserve full search on day
one; explicit tiers:

- **T1 validation set** (~150): detected species (our 525 detected ∩ genome
  available — compute exactly in code) with best-quality assembly per species,
  spanning orders. Must include: chicken, duck, turkey, zebra finch (controls).
- **T2**: remaining detected species with any assembly.
- **T3**: phylogenetic-coverage sample of undetected species (context for
  "is this gene universally avian or is its loss recent?").
- Per genome record: accession, assembly level (chromosome/scaffold/contig),
  contig/scaffold N50, annotation status/release, GC%, estimated completeness
  (BUSCO if available; else derive a searchability proxy — see Phase D).

**Genome acquisition**: NCBI Datasets API (`datasets download genome
accession … --include genome,gff,rna,protein`) — we already have the CLI and a
dehydrated avian download from Phase 0. Disk budget: ~1–2 GB per annotated
genome; genome-only ~300 MB → T1 ≈ 150–300 GB worst case; dehydrated rehydration
+ streaming blast can cut this if disk binds.

---

## 5. Phase D — The evidence ladder (the heart)

Every (gene × genome) cell gets exactly one status, with **confidence = an
explicit function of assembly searchability**:

| Level | Status | Meaning | How determined |
|-------|--------|---------|----------------|
| E0 | `NO_GENOME` | Species has no assembly | — |
| E1 | `NOT_SEARCHED` | Assembly exists, pipeline hasn't run | — |
| E2 | `SEARCHED_NOT_FOUND` | No annotation match, no blast hit | absence claim — see confidence below |
| E3 | `FRAGMENT` | Blast hit below coverage threshold (e.g. <50% CDS, or tblastn <X% protein) | partial sequence: assembly edge OR real pseudogene OR family cross-hit |
| E4 | `UNANNOTATED_FOUND` | No annotation, but blastn/tblastn full-length hit (≥ thresholds) | **the pipeline's key deliverable** — converts "Absent"→present |
| E5 | `ANNOTATED` | Symbol/synonym/ID match in GFF + protein FASTA corroborates | proof positive |
| — | `PSEUDOGENIZED` | hit present but ORF disrupted (frameshift/stop) | blast + ORF check |
| — | `PARALOG_AMBIGUOUS` | hit(s) present but discriminator region can't separate family members | family-level call only |

**Thresholds (initial proposal, tune on T1):**
- blastn: e-value ≤ 1e-20, identity ≥ 80%, coverage ≥ 60% of CDS (close species)
- tblastn: e-value ≤ 1e-10, identity ≥ 40%, coverage ≥ 50% of protein
  (cross-species; immune genes are conserved enough)
- FRAGMENT: same e-value/identity but coverage 20–60%.

**Absence confidence (the "missing is not proof" machinery):**
For every `SEARCHED_NOT_FOUND`, compute a **detectability prior** for that
(genome, genomic-context) pair:
1. **Assembly level prior**: chromosome > scaffold > contig (lookup table from
   empirical validation).
2. **Searchability control**: blast a panel of ~50 single-copy conserved
   control genes (BUSCO-like avian set) against the same assembly. Fraction
   recovered = assembly searchability s ∈ [0,1]. If s < 0.9, every absence call
   on that genome is downgraded to `NOT_FOUND_LOWCONF`.
3. **Gene difficulty prior**: genes in GC-rich/repetitive contexts (e.g. known
   MHC region, IFITM cluster) get an a-priori "hard-to-assemble" flag; absence
   in scaffold-level assemblies of such genes is never reported as loss.
4. Absence is finally reported as: `absent (confidence high|medium|low)` +
   machine-readable components (s, assembly level, gene difficulty, method
   coverage).

**Known-loss validation controls (must pass before any results ship):**
- DDX58/RIG-I: absent in chicken (chromosome-level, BUSCO-complete → high-conf
  true loss), present in duck.
- ANP32A avian 33-aa insertion: present in birds, absent in mammal outgroups.
- IFITM family: multi-copy in ducks vs fewer in chicken — tests paralog handling.
- Any pipeline output contradicting these is a bug, not a finding.

---

## 6. Phase E — Compute design

- **Tools**: NCBI BLAST+ (bioconda, already in our channel); `blastn -task
  dc-megablast` for CDS, `tblastn` for proteins; makeblastdb per genome (cached,
  keyed by assembly accession + checksum).
- **Orchestration**: extend the existing provenance-first Python pipeline;
  genome-at-a-time jobs (checkpoint per genome, resumable — same pattern as the
  WAHIS harvester); GNU parallel or pixi tasks for concurrency; results
  appended to a calls store keyed (panel_version, assembly, gene).
- **Scale estimate**: T1 = 150 genomes × (19 tier-1 genes × 2 sequence types)
  ≈ 5,700 searches — hours on one box. Full panel (say 300 genes incl. Avimm
  tier-2) × 150 genomes ≈ 90k searches — days; plan a nightly batch.
- **Caching + idempotence**: blast DBs kept under `data/genomes/{accession}/`;
  results parquet partitioned by assembly; a changed panel version only
  re-runs new/changed genes.

---

## 7. Phase F — Outputs & integration

1. `data/genes/gene_presence_calls.parquet` — extended schema: existing
   `GenePresenceCall` fields + `status_level` (E0–E5), `absence_confidence`,
   `searchability`, `blast_stats` (bitscore, evalue, pident, coverage),
   `panel_version`.
2. Presence matrix (species × gene) with evidence-tiered display: green
   (annotated) / blue (unannotated-found) / amber (fragment) / gray-striped
   (absent-lowconf) / white (not searched).
3. Web: fill the species-modal **Gene Panel tab** with this matrix (evidence
   badges, click-through to blast alignment stats); gene full pages gain a
   "Presence across birds" strip (X of Y searched genomes annotated/found/
   absent-lowconf).
4. Analysis hooks: join to susceptibility scores — the original hypothesis
   (gene content predicts outcome) becomes directly testable.

---

## 8. Rollout order

| Step | Deliverable | Est. |
|------|-------------|------|
| 1 | `host_panel_v2.json` (list + aliases + discriminators) | small |
| 2 | Multi-species reference sequences w/ provenance | small |
| 3 | T1 genome acquisition + searchability controls | medium |
| 4 | Annotation-match layer rebuild (reuse NCBI API code) | small |
| 5 | BLAST layer + evidence ladder + validation controls pass | **core** |
| 6 | Absence-confidence machinery | core |
| 7 | Web integration (Gene Panel tab) | small |
| 8 | Scale to T2/T3 + Avimm tier-2 panel | background batches |

Steps 1–4 are low-risk reuse; 5–6 are the novel engineering; the design above
is the contract for both. **Open decisions to settle before coding:**
(a) exact blast thresholds (tune on T1 controls), (b) control-gene panel source
(BUSCO Aves vs curated 50), (c) disk budget for genome caching, (d) whether
Tier-2 Avimm genes search protein-only (cheaper, sufficient for presence).

---

## Phase G — Sequence Collection & Comparative Analysis

**Goal:** For every gene found (E4/E5), extract its actual sequence, translate
if needed, build MSAs, cluster into ortholog groups, and generate phylogenetic
trees. This transforms presence/absence into evolutionary insight.

### G1. Sequence Extraction

**From NCBI annotation (E5):**
- Fetch protein FASTA via `datasets download gene gene-id {id}`
- Direct, clean, full-length
- Accession-linked provenance

**From blastn hits (E4):**
- Extract the aligned genomic region ± flank (500 bp each side)
- Use the aligned blocks as exon coordinates
- Splice together exons → CDS candidate
- Translate with standard code, check for stops

**From DIAMOND ORF hits (E4):**
- Extract the matching ORF sequences directly
- These are already protein
- May be fragmented across exons → reassemble by genomic proximity

### G2. Protein Compilation Per Gene

For each panel gene, compile a FASTA of all species' protein sequences:
- Reference species (chicken, duck, finch) protein from our verified references
- E5 species: NCBI-annotated protein
- E4 species: extracted/translated protein
- Tag each with species, method, confidence

Output: `data/genes/sequences/{GENE}.faa` (one multi-species FASTA per gene)

### G3. Multiple Sequence Alignment

- **Tool:** MAFFT (accurate, handles divergent sequences)
- Per gene: align all species' proteins
- Output: `data/genes/alignments/{GENE}.aln.faa`
- Compute identity matrix, conservation scores per position
- Identify species-specific indels, premature stops, domain losses

### G4. Ortholog Clustering

- **Tool:** MCL (Markov Cluster Algorithm) on all-vs-all similarity
- Input: BLASTP/DIAMOND all-vs-all across all extracted proteins
- Cluster at multiple inflation parameters (1.2, 2.0, 4.0)
- Output: `data/genes/clusters/{GENE}_clusters.tsv`
- Identify: single-copy orthologs, recent duplications, paralogs

### G5. Phylogenetic Trees

- **Tool:** FastTree (fast, good for 50-500 sequences) or IQ-TREE (accurate)
- Per gene tree from the MSA
- Compare gene tree vs species tree (from BirdTree)
- Identify: gene duplications, losses, HGT, unusual rates

### G6. Cluster Graphs & Visualization

- Per gene: network graph of species connections weighted by identity
- Cross-gene: pan-immunome graph showing gene family expansions/contractions
- Interactive tree + alignment viewer on the website

### Dependencies to add:
```
mafft >= 7.5          # MSAs
fasttree >= 2.1       # phylogenetics
mcl                   # clustering  
iqtree >= 2.2         # alternative phylogenetics (more accurate)
```

### Implementation order:
1. Sequence extraction (from all evidence types)
2. Per-gene FASTA compilation
3. MAFFT alignment + conservation scoring
4. FastTree gene trees
5. MCL clustering
6. Web visualization (tree viewer + alignment viewer)
