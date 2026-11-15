# Gene Presence Pipeline — Decision & Build Log

Running log of decisions made while implementing `PLAN_GENE_PRESENCE.md`.
Each entry: date, decision, rationale, consequence. The plan doc is the
contract; this is the lab notebook.

---

## 2026-08-30 — Session 1: scaffold + validation milestone

**Scope this session:** Steps 1–2 (panel v2, references), Step 5 core (BLAST
layer + evidence ladder), Step 6 (searchability), validation controls on
chicken + duck + zebra finch. T1-wide acquisition and web integration follow.

### D1 — Open decisions settled with defaults (from plan §8)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| (a) BLAST thresholds | blastn: e≤1e-20, id≥80%, cov≥60% · tblastn: e≤1e-10, id≥40%, cov≥50% · FRAGMENT: cov 20–60% | plan defaults; tune against controls before wider rollout |
| (b) Control-gene panel | curated ~14 single-copy housekeeping genes (ACTB, GAPDH, RPL-family…) via chicken CDS | BUSCO lineage download is heavier; housekeeping set is transparent, fast, and we can reuse the same blast plumbing. Revisit if searchability scores look off |
| (c) Disk budget | 802 GB free; T1 genome-only ≈ 50–100 GB, blast DBs add ~same | fits; annotated-only genomes for T1, contig-level genomes get genome-only |
| (d) Avimm tier-2 | deferred; T1 = curated 19 + wiki host genes (~40) | validate the ladder first; Avimm scales later, protein-only |

### D2 — Panel v2 content
- Tier 1 = existing curated 19-gene panel + wiki host genes with ≥2 papers,
  merged on canonical symbol (shared alias namespace from `species_aliases`
  pattern). Each entry carries `paralog_family` + `discriminator` flag for
  ANP32 / IFITM / MX / OAS / TLR families (discriminator *regions* not yet
  chosen — v1 uses full-CDS with family-aware interpretation).

### D3 — Pseudogene ORF-check: deferred
Status vocabulary includes `PSEUDOGENIZED`, but v1 does not implement ORF
integrity checks (frameshift detection needs alignments in coordinates).
Fragments below coverage get `FRAGMENT`; pseudogene discrimination is a v2
task. Recorded so nobody mistakes v1 fragments for clean absences.

### D4 — Evidence store format
New calls appended to `data/genes/gene_presence_v2.parquet`, keyed
(panel_version, taxon_id, gene_symbol). Existing 3,636 API calls remain in the
old store; merged at view time with `method` distinguishing layers.

### Validation gates (from plan §5, must pass)
- DDX58/RIG-I: chicken → SEARCHED_NOT_FOUND with high searchability
  (high-confidence absence); duck → found.
- ANP32A: found in both chicken + duck.
- Control genes: near-complete recovery in chromosome-level assemblies.

### D5 — Legacy reference sequences were mislabeled (blocking discovery)
The old `data/genes/sequences/*.fasta` accessions are WRONG: `ANP32A_chicken.fasta`
holds HSF1, `ANP32B` holds NMUR1, old panel gene ID 395532 is COL1A1, not
ANP32A. **All v1 blast plans built on those files would have been garbage.**
Rebuild: `build_references.py` resolves every gene via `datasets summary gene
symbol X --taxon Gallus gallus` with strict symbol/alternate-name verification,
downloads NCBI gene packages, keeps the longest transcript, records sha256+
accession provenance. Correct anchors: ANP32A=415562, ANP32B=420087,
ANP32E=426109. Old sequences dir kept but quarantined from the pipeline.

### D6 — datasets zip extraction bug (fixed)
`--include genome` packages can contain `cds_from_genomic.fna`; the first
extractor matched `endswith("genomic.fna")` and zebra finch silently got the
CDS file (108 MB) instead of the genome. Fixed: exact `genome.fna` match,
fallback = largest .fna. Always verify downloaded genome size (~1 Gb for
birds) — `size_mb` now recorded in the manifest.

### D7 — DDX58 reference handling (the known-loss control, live)
Chicken DDX58 symbol search returns nothing — **consistent with the known
RIG-I loss** (first gate passing, at the reference layer). Duck resolves as
symbol RIGI. Gap: `build_references.py` anchors the duck ortholog download on
the chicken gene ID, which doesn't exist for DDX58 → no duck reference fetched.
Patch queued: duck-first resolution (chicken miss → search duck, download via
the duck gene ID, flag gene `chicken_absent_expected`).

### D9 — Controls directory bug (fixed; cost one wasted run)
`build_references.py` wrote all 12 control references into `controls/` itself
instead of `controls/{SYMBOL}/` — files clobbered each other and the blast
layer's searchability loop found zero control queries (s=0.00 on chicken while
panel genes hit at 99-100% — the tell). Fixed path join; controls rebuilt 12/12
into per-symbol dirs. **Lesson: a searchability of exactly 0 with healthy
panel hits means the controls are broken, not the genome.**

### D8 — Family-level wiki symbols correctly unresolvable
MHC, NFKB, OAS, TLR, ANP32 (family-level names) return no single-gene match —
correct behavior. Member-level genes (OASL, TLR3/7/21, ANP32A/B/E, IFITM)
carry searchable references; family entries become web-layer roll-ups.

---

### V0 VALIDATION RESULTS (2026-08-30) — ALL GATES PASS

**184 calls** (46 genes × 4 validation genomes), evidence ladder live:

| Gate | Result |
|------|--------|
| **DDX58/RIG-I × chicken** | `NOT_FOUND`, confidence **high** (s=1.00) — the known RIG-I loss, independently rediscovered by the pipeline |
| **DDX58/RIG-I × duck** | `FULL` (blastn 82% id, 86% cov via duck anchor) |
| DDX58 × zebra finch | `FULL` — passerine RIG-I present (correct) |
| DDX58 × turkey | `NOT_FOUND` — **matches literature** (RIG-I loss extends beyond chicken in galliforms) |
| ANP32A × chicken | `FULL` 99.3% id |

Status distribution: 157 FULL · 13 FRAGMENT · 14 NOT_FOUND.
Searchability: chicken 1.00 · turkey 0.92 · duck 0.75 · zebra finch 0.67.

**Observation for T1:** searchability drops with chicken-reference divergence
(zebra finch 0.67 via chicken controls) — at scale, controls should include
taxon-diverse references or relax thresholds with phylogenetic distance, else
absences on distant lineages get over-downgraded. Logged as a T1 task.

### D10 — Blast loop skipped duck-only genes (fixed)
The first full run silently skipped DDX58/RNF135 (loop required chicken refs),
so "ALL GATES PASS" ran with only the ANP32A gate — misleading. Fixed: duck
references alone are sufficient to query; gates now include explicit
`call EXISTS` assertions so a missing gate fails the run, not skips it.
**Rule: a green validation report must enumerate which gates ran.**

### D11 — Web integration plan (user direction, 2026-08-30)
End state for the site: a **matrix view of all genes × all species** (the
presence calls), where every cell is clickable and every gene row links to the
gene page. Gene pages already have: NCBI Gene / UniProt / PDB links (curated +
wiki), research literature, mutations, species studied. **To add:** reference
sequence display (serve the `references_v2` transcripts/proteins we now hold —
FASTA viewer with download), and presence-across-species strip fed by
`gene_presence_v2`. Presence matrix display conventions (from the ladder):
green=annotated(E5) · blue=found(E4) · amber=fragment(E3) · gray-striped=
absent-lowconf(E2) · white=not searched. Sequences carry accessions so every
displayed sequence links back to NCBI.

### D12 — Avimm unreachable; UniProt GO backbone chosen instead (2026-08-31)
Avimm (avimm.ab.mpg.de) times out from this network; the Bhogal 2020 paper has
no PMC/BMC-accessible supplement. Replacement backbone: **UniProt REST** —
`(organism_id:9031) AND go:0002376` (immune system process) → 2,518 proteins →
**567 unique NCBI-ID'd genes** with symbols/synonyms/protein names/accessions
(saved: `data/genes/avimm_uniprot_backbone.json`). Panel v3 = **596 genes**
(18 curated + 32 wiki + 546 GO backbone after dedup/LOC-filter). GO:0002376
chosen over GO:0006955 (immune response) as the broader parent; tier-3 chicken
gene IDs come from UniProt xrefs (trusted), unlike legacy curated IDs.

### D13 — ID-poisoning regression near-miss (caught by validation habit)
Panel v3's first build carried the WRONG legacy gene IDs (D5 poison) via the
curated-file merge, and the reference builder's `known_gene_id` short-circuit
faithfully downloaded COL1A1 as "ANP32A" again. Fix: panel builder nulls ALL
legacy IDs (resolve every tier-1/2 by symbol; only UniProt backbone IDs
trusted). Lesson folded into D5: **trust hierarchy for gene IDs =
symbol-resolution > UniProt xref > never the legacy curated file.**

### D14 — ImmunomeDB vintage caveat + external-resource TODOs (2026-08-31)
ImmunomeDB (gitlab.com/rcmueller/immunomedb) is frozen ~2020: annotations are
GeneWise projections onto the **B10K phase-1 (363 genome) assemblies**, which
modern chromosome/T2T assemblies supersede. Usage rule: ImmunomeDB calls are a
**breadth layer** (annotation-level evidence with Shift/MidStop pseudogene
flags for 363 species), never overriding our own blast layer on current
assemblies. Where both exist, ours wins; where only ImmunomeDB exists, its
calls carry a `source_vintage: 2020-B10K1` caveat.

**TODO (later phases, user-directed):**
- [ ] **eggNOG** — orthology/functional annotation for all panel genes+proteins
      (eggNOG-mapper runs offline; gives OGs, GO, COGs → better paralog-family
      resolution than our hand lists)
- [ ] **InterProScan** — domain/motif scanning across all reference + found
      proteins (identifies truncations, domain losses in fragments — feeds the
      pseudogene/FRAGMENT discrimination deferred in D3)

### D15 — ImmunomeDB integration design (2026-08-31)
Downloaded the full dataset (363 GFFs + FASTAs, 0 failures). Structure per
species: GeneWise-projected immune genes onto B10K-v1 assemblies, keyed by
`Source=ENSGALP*/ENSTGUP*` (chicken/finch Ensembl protein probes) with
`Shift`/`MidStop` flags — the latter directly supplies pseudogene evidence
that D3 deferred. FASTA headers are coordinate-only (no gene names), so
probe→symbol goes via **UniProt ID mapping** (`Ensembl_Protein` → UniProtKB →
gene_primary; Ensembl REST was down + a mirror had an expired cert — noted).
Integration (`immunomedb_integration.py`): presence calls at
`method=annotation, source_vintage=2020-B10K1` — per D14 they never override
our blast layer on modern assemblies; MidStop/Shift>0 → PSEUDOGENIZED.

### D16 — ImmunomeDB presence layer results (2026-08-31)
107,486 annotation calls: 520 gene symbols × 363 species, 8,910 PSEUDOGENIZED
(via Shift/MidStop flags). 266 genes present in ≥300 species (core immunome),
186 in <50 (lineage-specific losses or probe failures).

**DDX58/RIG-I is entirely absent from ImmunomeDB** — including duck (which has
308 other immune calls). Their probes are chicken+zebra-finch Ensembl
proteins; chicken lost RIG-I and the finch probe evidently didn't survive the
UniProt symbol mapping (777 probes unmapped, mostly LOC-style). The D14 rule
proves itself on day one: **ImmunomeDB is breadth-only; our blast layer is the
authority.** Anything absent from ImmunomeDB is a gap in *their* probe set,
not evidence of gene loss.

Merge note: many ImmunomeDB symbols are 2020-era LOC placeholders
(LOC100222345 etc.) — merge only named symbols into the panel; LOC entries
stay in the calls store keyed by probe ID for provenance.

### D17 — Reconfirmation policy for vintage layers (user direction, 2026-08-31)
B10K-v1 assemblies have been superseded for many of the 363 species
(chromosome-level and T2T replacements since 2020). Policy:
1. ImmunomeDB calls are **leads, not findings** — display only with the
   vintage badge until reconfirmed.
2. Reconfirmation = our blast layer on the species' **current** RefSeq/Ensembl
   assembly. A reconfirmed call upgrades to the blast layer's status; a
   contradicted call (present-then, absent-now or vice versa) keeps both
   records with the disagreement visible — assembly improvement can genuinely
   resolve OR dissolve a projection (GeneWise on contigs was optimistic).
3. **T1/T2 genome selection implication**: species with ImmunomeDB calls get
   a priority bump when choosing which modern assemblies to fetch, so the
   vintage layer gets reconfirmed systematically rather than incidentally.
   Priority = detected-species ∩ ImmunomeDB species first (double value).

### D18 — Batch tblastn scaling (fixed with two-stage smart mode)
Full-panel batch tblastn (617 proteins × 1 Gb genome) exceeded a 1-hour
subprocess timeout — 6-frame genome translation dominates cost. Fix: **two
stage** — (1) batch blastn (dc-megablast, fast) for ALL genes; (2) chunked
tblastn **only for genes blastn didn't call FULL** (subset FASTA, 6 chunks,
per-call runtime bounded). On validation genomes this cuts tblastn work
80–100%: turkey needed zero tblastn, duck one gene. Per-call blast timeout
also raised 3600→7200s as belt-and-braces.

### V1 FULL-PANEL VALIDATION (2026-08-31) — ALL GATES PASS

**2,368 calls** = 592 genes × 4 validation genomes, all six gates enumerated
and green (RIG-I chicken absent high-conf / duck present, ANP32A control).

| Genome | FULL | FRAGMENT | NOT_FOUND | tblastn needed |
|--------|------|----------|-----------|----------------|
| chicken (s=1.00) | 589 | 0 | 3 | 4 genes |
| turkey (s=0.92) | 583 | 5 | 4 | 22 genes |
| Pekin duck T2T (s=0.75) | 512 | 46 | 34 | 307 genes |
| zebra finch (s=0.67) | 436 | 96 | 60 | 413 genes |

The gradient is exactly the design's prediction: blastn handles close
lineages (galliforms), tblastn carries the divergent ones, and NOT_FOUND
concentrates where searchability is lowest — with confidence grades that say
so. Chicken's 3 NOT_FOUND at s=1.00 are high-confidence absences (real gene
losses to investigate, e.g. alongside DDX58).

### D19 — Switch tblastn → DIAMOND (user direction, 2026-08-31)
BLAST's tblastn (protein vs 6-frame-translated genome) was the bottleneck
(D18: 1hr timeout on 617 proteins × 1Gb). **DIAMOND 2.2.5** (bioconda)
replaces it: translate genome to 6-frame protein FASTA → `diamond makedb` →
`diamond blastp --ultra-sensitive`. Advantages:
- **500–2000× faster** (batch of 617 proteins vs 1Gb genome: minutes, not hours)
- **`--ultra-sensitive`** mode catches more divergent homologs than tblastn
  default — critical for chicken-probe → 90MY-divergent NZ species
- Sensitivity ladder: fast → mid-sensitive → sensitive → more-sensitive →
  very-sensitive → ultra-sensitive. We use ultra-sensitive (cross-species is
  the whole point; speed gain more than covers the sensitivity cost).
- blastn (dc-megablast, nucleotide) retained for Stage 1 close-species calls
  — DIAMOND doesn't replace nucleotide searches.

### V2 FULL 15-GENOME RUN + NZ RIG-I DISCOVERY (2026-08-31)

**8,880 calls**, all gates pass. DIAMOND --very-sensitive + getorf ORF DBs.

| Genome | FULL | FRAG | NF | searchability |
|--------|------|------|----|----|
| chicken | 588 | 1 | 3 | 1.00 |
| turkey | 574 | 10 | 8 | 0.92 |
| Pekin duck | 321 | 144 | 127 | 0.75 |
| kākāpō | 261 | 178 | 153 | 0.67 |
| takahē | 248 | 179 | 165 | 0.67 |
| hoiho | 267 | 174 | 151 | 0.75 |
| NI brown kiwi | 254 | 185 | 153 | 0.75 |
| kea | 197 | 200 | 195 | 0.67 |
| kākāriki | 186 | 224 | 182 | 0.50 |
| weka | 199 | 209 | 184 | 0.67 |
| hihi | 192 | 211 | 189 | 0.67 |

### 🔬 RIG-I (DDX58) across all 15 species — headline finding:

| Species | Status | Confidence |
|---------|--------|------------|
| chicken | NOT_FOUND | **high** (known loss ✓) |
| turkey | NOT_FOUND | **high** (galliform loss ✓) |
| duck | **FULL** | known presence ✓ |
| zebra finch | **FULL** | known presence ✓ |
| **kākāpō** | NOT_FOUND | low (scaffold assembly) |
| **takahē** | NOT_FOUND | low |
| **all 4 kiwi** | NOT_FOUND | low–medium |
| **kea** | NOT_FOUND | low |
| **kākāriki** | NOT_FOUND | low |
| **weka** | NOT_FOUND | low |
| **hihi** | NOT_FOUND | low |
| **hoiho** | **FRAGMENT** | partial/pseudogene? |
| **NI brown kiwi** | **FRAGMENT** | partial/pseudogene? |

**Implication: RIG-I may be absent across NZ native birds** — parallel to the
galliform loss. If confirmed (chromosome-level assemblies needed), this is a
conservation-critical finding: NZ birds may be intrinsically more susceptible
to H5N1 (as chickens are), compounding island-population vulnerability.

**Caveats:** NZ genomes are scaffold-level (s=0.5–0.75), so absences carry
low confidence. The two FRAGMENTs (hoiho, NI brown kiwi) need follow-up —
they could be pseudogenized remnants or assembly artifacts.

### D20 — CRITICAL CORRECTION: RIG-I "absence" in NZ birds was a threshold artifact

The V2 finding that RIG-I is absent across NZ native birds was **wrong**. The
raw blastn evidence shows RIG-I IS present in every NZ species tested:

| Species | blastn id% | cov% | e-value | V2 call | Correct call |
|---------|-----------|------|---------|---------|--------------|
| kākāpō | 79.0 | 93 | 8.5e-131 | NOT_FOUND | **FULL** |
| kākāriki | 78.5 | 93 | 7.6e-125 | NOT_FOUND | **FULL** |
| weka | 75.8 | 97 | 2.1e-100 | NOT_FOUND | **FULL** |
| takahē | 75.6 | 94 | 1.0e-98 | NOT_FOUND | **FULL** |
| hihi | 77.3 | 85 | 8.7e-105 | NOT_FOUND | **FULL** |
| hoiho | 81.1 | 58 | 1.8e-146 | FRAGMENT | **FULL** (borderline) |
| kea | 75.7 | 28 | 3.8e-103 | NOT_FOUND | FRAGMENT |
| kiwi (4 spp) | 79-80 | 46 | ~e-107-110 | NOT_FOUND/FRAG | FRAGMENT |

**Root cause:** The 80% blastn identity threshold was calibrated for
chicken→other-bird comparisons. DDX58 has no chicken reference (chicken lost
the gene) — the duck reference is used instead. Duck→parrot/paleognath
comparisons naturally produce 75-80% identity. Every NZ species fell just
below the cutoff.

**Secondary issue:** DIAMOND/getorf coverage is meaningless for multi-exon
genes. getorf splits at stop codons (intron boundaries), producing one ORF per
exon. A 933-aa protein fragments into 5+ short ORFs, none exceeding ~11%
coverage.

**Fix:** (1) Add a high-significance override: blastn e-value < 1e-50 AND
coverage ≥ 80% → FULL regardless of identity; (2) for DIAMOND, sum coverage
across multiple ORF hits to the same genomic region; (3) log reference-species
divergence per call so future thresholds are distance-aware.

**True RIG-I losses remain:** chicken and turkey only (both high-confidence,
protein-level noise matches at ~30% identity). NZ birds all have RIG-I.

### D21 — Kākāpō/kiwi DDX58 follow-up: gene IS present, NCBI-annotated

**NCBI annotation confirms RIG-I (DDX58) in NZ species:**
| Species | NCBI RIGI | Location | Assembly level |
|---------|-----------|----------|----------------|
| kākāpō | ✓ RIGI | chrZ:42,075,405-42,097,978 | chromosome |
| NI brown kiwi | ✓ RIGI | chrZ:8,366,388-8,384,537 | chromosome |
| rowi | ✓ RIGI | Unplaced scaffold | scaffold |
| kea | ✓ RIGI | Unplaced scaffold | scaffold |
| duck | ✓ RIGI | chrZ:69,790,656-69,812,251 | complete |
| zebra finch | ✓ RIGI | chrZ:39,576,059-39,600,141 | chromosome |
| takahē | ✗ not annotated | — | chromosome (but unannotated) |
| hoiho | ✗ not annotated | — | scaffold |
| kākāriki | ✗ not annotated | — | scaffold |
| weka | ✗ not annotated | — | scaffold |
| hihi | ✗ not annotated | — | scaffold |
| GS/LS kiwi | ✗ not annotated | — | scaffold (no annotation) |

**Key finding: RIG-I is Z-linked in birds.** In all chromosome-level genomes
with annotation, DDX58 maps to chromosome Z (sex chromosome: males ZZ,
females ZW). This means RIG-I hemizygosity in female birds (single Z copy)
could affect antiviral immunity — a potential sex-biased susceptibility factor.

**Pipeline lesson:** our blast layer should check NCBI annotation FIRST
(E5 = proof positive), then blast only for unannotated genes/genomes. The
current pipeline goes straight to blast, missing free annotation evidence.
This mirrors D7's reference-resolution lesson: check the easiest source first.

**Threshold redesign needed (user direction):** the 80% identity cutoff is a
single-species calibration that fails for cross-lineage comparisons. See D22.

### D22 — Threshold redesign: evidence integration, not fixed cutoffs

**Problem:** Fixed identity thresholds (80% blastn, 40% tblastn) fail across
the divergence range of birds (~60-120 MY). A duck-reference search against
kākāpō produces 75-80% identity at full length — a real ortholog that falls
just below the cutoff. Coverage thresholds fail for multi-exon genes with
getorf (exon fragments).

**New approach — layered evidence with adaptive significance:**

**Layer 0 — NCBI annotation check (E5):**
Query `datasets summary gene taxon {species}` per genome before blasting.
If the gene is annotated → E5 ANNOTATED, highest confidence, done.
This is free (API) and authoritative. Currently missing from the pipeline.

**Layer 1 — blastn with e-value significance (distance-free):**
Primary criterion: e-value (distance-independent measure of surprise).
- FULL: e-value < 1e-50 AND summed coverage across all HSPs ≥ 60%
- FRAGMENT: e-value < 1e-50 AND summed coverage 20-60%
- Identity is REPORTED but not a gate — real orthologs at 70% identity
  have e-values < 1e-50 by definition of alignment length

**Summed coverage:** Instead of best-single-HSP coverage (qcovhsp), sum
non-overlapping aligned bases across all HSPs on the same chromosome.
This handles multi-exon genes where the query aligns to exon after exon.

**Layer 2 — DIAMOND protein search with ORF-fragment reassembly:**
For genes without blastn evidence:
- Run DIAMOND --very-sensitive
- Group hits by chromosome/scaffold
- Sum coverage across hits in the same genomic region
- FULL if summed protein coverage ≥ 40% + e-value < 1e-20

**Layer 3 — absence confidence (unchanged from D1):**
Searchability × assembly level → high/medium/low confidence absence.

**Reference divergence tracking:** Each call records the reference species
used + estimated divergence (from phylogeny or observed identity). This
enables future distance-aware threshold refinement without re-running.

### D23 — Comparative analysis expansion (user direction, 2026-08-31)
Beyond presence/absence: extract sequences, build MSAs, cluster, tree.
The RIG-I finding is a perfect example — knowing it's Z-linked and present in
NZ birds is step 1; step 2 is whether the NZ RIG-I protein has the same
domains, same conservation pattern, or shows signs of degradation (pseudogene
trajectory). The threshold redesign (D22) needs real sequences to calibrate
against. MAFFT + FastTree + MCL added to the plan (Phase G).

### V3 — FULL COMPARATIVE LAYER (2026-08-31)

**575 MAFFT alignments + 561 FastTree phylogenetic trees** across 592 genes
× 15 species (batch DIAMOND extraction: 15 calls for all genomes = minutes
vs 8+ hours per-gene; D18 lesson applied again).

Outputs:
- `data/genes/sequences_v2/{GENE}.faa` — 592 multi-species protein FASTAs
- `data/genes/alignments/{GENE}.aln.faa` — 575 MAFFT alignments
- `data/genes/alignments/{GENE}_identity.tsv` — pairwise identity matrices
- `data/genes/trees/{GENE}.nwk` — 561 FastTree Newick trees

Limitation: DIAMOND-extracted sequences are single-ORF fragments for
multi-exon genes (getorf limitation, D22). NCBI-annotated species have
full-length proteins. ORF stitching is the next quality improvement.

### D24 — ORF stitching + MCL + web integration plan (2026-08-31)

**ORF stitching approach:** Rather than complex exon assembly, improve the
DIAMOND extraction by:
1. Running with `-k 10` (multiple ORF hits per query)
2. Grouping hits by contig (ORF IDs embed the contig name)
3. Reporting the total query coverage across all ORFs on the same contig
4. Using the longest single ORF as the representative protein
5. Flagging `multi_exon=True` when total coverage > 1.5× single-ORF coverage

This gives honest coverage numbers and identifies multi-exon genes for
future splice-aware extraction. NCBI-annotated species already have
full-length proteins (E5 path).

**MCL clustering:** All-vs-all DIAMOND across all ~9,000 proteins (~592 genes
× 15 species), then MCL at inflation 1.4 (moderate) and 2.0 (tight).
Identifies ortholog groups, paralogs, and potential annotation errors.

**Web:** Fill the species modal Gene Panel tab with the presence matrix +
add tree links to gene pages. Export web-friendly JSON.

### V4 — COMPARATIVE LAYER COMPLETE (2026-09-01)

**MCL Clustering:**
- 8,270 proteins, 130,417 edges, 787 clusters (inflation 1.4)
- 690 clean ortholog groups · 78 mixed · 19 superclusters
- DDX58: 12 species, clean ortholog cluster (chicken + turkey absent ✓)
- JAK family correctly splits into paralog sub-clusters
- 146 single-species clusters = species-specific duplications

**ORF Stitching:**
- Multi-ORF coverage tracking: groups DIAMOND hits by contig, sums qcov
- `multi_exon` flag when summed coverage > 1.5× best single ORF
- DDX58 re-extracted: 13 sequences, tree rebuilt

**Web:**
- Species modal Gene Panel tab LIVE: 592 genes for chicken
- Color-coded grid (green/amber/red) for 16 key immune genes
- Critical absence badges (⚠ DDX58 for chicken)
- All 13 Playwright tests pass

**Next: T2 genome expansion + full re-extraction with stitching + tree viewer on gene pages**

### D25 — Species index redesign: taxonomy-driven (user direction, 2026-09-01)
The species list should cover ALL birds (~11,284 Aves from taxonomy) + any
mammals/species with H5N1 detections or research mentions. Detection data,
genomes, and papers are LAYERS on species pages, not gates for inclusion.

Architecture:
- species_index.json = full Aves taxonomy + mammals from detections
  (det count = 0 for undetected species — they're still searchable)
- species_wiki_supplement.json = paper-referenced species not in taxonomy
- Each entry carries data-availability flags: det, has_genome, has_papers

### D26 — Gene Panel UX fixes + species full pages (user direction, 2026-09-01)
Issues raised:
- 592 genes searched but only 16 shown in the grid — misleading
- Mx1 shows red (absent) but no "critical" label — confusing importance vs status
- Species modal too cramped for 592 genes — needs a full page

Fixes:
1. Expand export to include ALL genes with importance tiers
2. Gene Panel tab shows key genes + "view all N →" link to full page
3. Species full page (#/species/{id}/full or equivalent) with:
   - Complete gene panel (searchable, filterable)
   - Detection timeline, genome info, research
   - Proper importance vs status visual separation

### D27 — Null-id species navigation + index hygiene (2026-09-01)
**Bug**: search results for species with `id: null` (mammals, unresolved)
navigated to `#/species` with no id → modal never opened (Homo sapiens case).
**Fix**: SearchBar falls back to scientific name → modal resolves via
getSpeciesByName / getSpeciesFromIndex.

**Bug**: build_species_index mislabeled 129 unmatched birds as Mammalia
(taxonomic splits: old Anas → Mareca/Spatula; common names in sci fields).
**Fix**: resolution ladder — exact sci match → common-name match →
unique genus-swap (same epithet) → unresolved (no fake classification).
36 species synonym-merged into taxonomy entries with combined det counts;
91 unresolved kept searchable; 0 fake mammals.

**Bug**: RangeError "Invalid time value" — 938 detection dates in non-ISO
formats (ISO week dates `2026-W13-1` unparseable by JS Date).
**Fix**: defensive formatDate/formatDateLong/formatRelativeTime with
ISO-week parser; invalid → '—' instead of throwing.

### D28 — Gene identity/labeling config + zero-literature caution (2026-09-01)
**Problem**: 592-gene panel had alias duplicates (MDA5/IFIH1, GBP/GBP1, JAK/JAK2,
IFNA/IFNA1, IL-1BETA/IL1B — 75 redundant calls) and importance-labeled genes
with zero corpus references (IFITM3, OASL, STAT1, STAT2) promising more than
the data backs.

**Config-driven identity** (data/genes/gene_config.json — ever-growing, no code
edits needed):
- aliases: alias → canonical; export merges with best-evidence-wins
  (status rank × evidence level). 587 canonical genes from 592.
- importance_overrides: 28 "hidden gems" upgraded standard → high
  (STING1/STING, TLR15 bird-specific, MYD88, TICAM1/TRIF, EIF2AK2/PKR,
  TYK2, JAK2, IRF1/8, SYK, TRAF3/6, MHC cluster B2M/BLB1/2, TAP1/2,
  RAG1, AICDA, CASP3/6, RIPK2, NOD1, TIRAP, UNC93B1, PRKCD, TLR4/5)
  → 47 key genes total (3 critical + 44 high)
- display_names: TLR15 name corrected (panel had "Toll-like receptor 2" —
  wrong); PKR, TRIF, STING aliases added
- 27 LOC* genes flagged unannotated_locus (excluded from literature asks)

**Zero-literature caution** (UI): gene pages without corpus papers now show
"Not yet covered by our paper corpus" + explicit disclaimer that importance
labels reflect panel curation, not corpus claims. Presence matrix (genome
evidence) remains — it IS data-backed.

**Growth path**: add papers → build_wiki_pages.py → re-export → literature
sections fill automatically; importance moves from config to corpus-backed.

### D29 — Credits page + PhyloPic silhouettes (2026-09-01)
**Credits** (#/credits, footer-linked): data sources (WAHIS, WHISPers, FAO,
OCIMS, ImmunomeDB, NZ MPI, WHA, NCBI, UniProt, Clements, IUCN, GBIF, PDB,
papers corpus), software stack (DIAMOND, BLAST+, MAFFT, FastTree, MCL,
DuckDB, Svelte, MapLibre/deck.gl, Playwright, pixi), and per-contributor
PhyloPic attributions.

**PhyloPic** (scripts/fetch_phylopic.py):
- Species silhouettes downloaded locally (web/public/images/phylopic/) —
  site never hits their API at runtime (user requirement)
- ~540 species: all detected + gene-presence + supplement mammals
- Two-step API: name search → node w/ primaryImage; genus fallback
- 0.35s politeness delay; incremental attribution persistence (resume-safe)
- UI: SpeciesCard (40px), modal header (64px), full page (80px);
  dark:invert for dark mode; attribution on Credits page
- raster ≥256px preferred, 192px thumbnail fallback

**Fix**: SpeciesFullPage detections query → store method (loads table
first; kills noisy Catalog Error on cold load).

### D30 — Species page UX: genome detail, tab persistence, two-view panel (2026-09-01)
- **Detections empty state**: "No HPAI detections recorded" + surveillance-
  coverage caveat instead of blank table
- **Genome tab**: total length, contig N50, scaffold N50, annotation status
  (Yes/No + label), NCBI representative flag. Kākāpō "not annotated" bug was
  a duplicate `has_annotation` key in _indexToSpecies (last-wins) — fixed
- **Tab persistence**: ?tab=genes in URL survives back-navigation
- **Two-view gene panel**: Compact (bird's-eye strip: 8 headline genes with
  function snippets + all-critical-present/missing verdict) and Detailed
  list (table: gene | function | status | evidence level | role | impact
  if lost for absences)
- **Gene functions**: curated one-liners for 47 key genes (gene_config
  functions) + UniProt fetcher for 546 GO-backbone genes
  (fetch_uniprot_functions.py → gene_functions.json, resume-safe)
- **Impact if lost**: curated statements on gene pages + detailed rows,
  labeled "curated · not from paper corpus"
- formatN50 gained Gb tier; stray 'b' suffix removed

### D31 — Method provenance badges (2026-09-01)
User ask: show WHERE each call comes from — annotation vs our search —
and how reliable it is. Especially: annotated genome + gene missing from
annotation + recovered by DIAMOND search.

Badges in detailed view (methodInfo()):
- 🏷️ annotated (E5, blue): "Listed in this genome's NCBI annotation — gold standard"
- ✨ search-found (E4, violet): genome-annotated → "annotation gap recovered
  by our DIAMOND search"; unannotated → "found by DIAMOND search"
- ≈ fragment (E3, amber): partial match — pseudogene/assembly gap/divergent
- ∅ no match (E2, gray): annotated genome → high-confidence absence;
  unannotated → weaker evidence

Bird's-eye adds: "✨ N genes missing from this genome's annotation but
recovered by our search" + "see how we know" → detailed view filtered.
Compact grid: ✨ marker on E4 cards, tooltips carry method + function.

Distribution (15 genomes): E5=3341, E4=3557, E3=1169, E2=738.
Recovered-on-annotated: turkey 156, duck 125, rowi 101, NI kiwi 100,
kākāpō 98, chicken 77, finch 71 — even RefSeq annotations miss
70-150 immune genes per genome.

### D32 — Wiki family-alias layer + honest bird's-eye verdict (2026-09-01)
**Alias layer** (gene_config wiki_aliases): corpus family symbols attribute to
canonical panel genes, tagged `via_alias` so provenance stays visible.
Mappings: IFITM→IFITM3, MDA5→IFIH1, ANP32→ANP32A, IFNA→IFNA1, RIG-I→DDX58.
Result: IFITM3 0→3 papers, IFNA1 +12, ANP32A +2. Conservative by design —
ambiguous families (OAS, TLR, JAK, GBP) unmapped.

**Bird's-eye verdict fix**: "All critical present" under a strip showing 2 ✗
was technically true (critical tier) but visually contradictory. Verdict now
computed from the VISIBLE strip: missing critical (red) / critical present but
high missing (amber, names the genes) / all present (green).

### D33 — Evidence drawers: "judge it yourself" HSP viewers (2026-09-01)
New: scripts/genes/export_evidence.py — re-runs batch DIAMOND (same params
as extract_batch) and persists HSP-level evidence per gene × species:
  data/genes/evidence/{GENE}.json + web/public/data/evidence/ (592 files)
Per record: contig, HSP coords (qstart/qend/sstart/send/slen), pident,
evalue, qcov per HSP, summed coverage, multi-exon flag, threshold verdict,
no_hit records for absences (search scope stated).

Viewer: EvidenceDrawer.svelte on gene pages — 👁 button per species row in
the presence matrix →
  - HSP map (SVG): query track + subject ORF track, blocks colored by
    identity (red→green heat scale), connecting lines, tooltips
  - HSP table: per-HSP coordinates, %id, e-value, coverage
  - Threshold box: D20 math applied to this cluster
  - Absences: explicit "searched, nothing passed" + scope

One caveat: evidence re-run uses duck-first references only, so coverage
numbers can differ slightly from the original per-species-reference calls —
the status badge shows the original call; the drawer shows this HSP set.

### D34 — Embedded genome browser (igv.js) — no custom WASM needed (2026-09-01)
User asked for near-full genome browser for evidence judgment; considered
building Rust/WASM — NOT needed. igv.js (Broad, embeddable, ~2MB lazy-loaded)
serves the reference FASTA via HTTP range requests against a .fai index —
viewers fetch only the viewed region.

Data plumbing:
- scripts/genes/prepare_igv.py: per genome — re-run getorf (deterministic
  ordinals recover ORF→genomic coords from deflines `[start - end] strand`),
  pure-python faidx, symlink genome.fna+fai into web/public/data/genomes/.
  Kākāpō: 6.7M ORF coords; NC_044302.2_118841 → chrZ:42,095,975-42,096,385 (+)
- export_evidence.py: HSP protein coords → genomic (orf_start + (sstart-1)*3,
  strand-aware); stores assembly accession per record

Viewer: GenomeBrowser.svelte — igv.createBrowser with indexed FASTA +
identity-colored HSP annotation track (inline features), auto-located to the
evidence locus ±30%. EvidenceDrawer: "🧬 Genome context" toggle.

### D35 — Nucleotide exon tracks + NCBI GFF overlay in igv (2026-09-01)
Motivated by user doubt on kākāpō DDX58 (protein-ORF view showed ~50%).
Definitive check: divergent blastn (-task blastn -dust no) of duck DDX58
mRNA vs kākāpō genome = 18 exons, 96.9% mRNA coverage, best e=8.5e-131
across chrZ:42,077,279-42,096,628. Gene is real; protein-ORF coverage
undersells split genes structurally (6-frame ORFs cannot splice).

New layers:
- export_evidence.py: batched per-genome blastn (all reference mRNAs,
  one call/genome) → exon_hsps per record with genomic coords, exon_count,
  exon_best_e. Bug fixes en route: blastn needs -outfmt as ONE arg
  (DIAMOND-style tokens → USAGE error) and -out (not -o).
- fetch_gffs.py: NCBI GFF3 per accession (datasets API → FTP), sort
  (tabix needs position-sorted; NCBI GFFs are not), bgzip+tabix, staged
  for range requests. Stdin-consumption bug fixed (two decompressions).
- GenomeBrowser: three tracks — NCBI annotation (gff3+tabix), mRNA exon
  HSPs (nucleotide evidence), protein HSPs (identity-colored)
- Drawer: exon summary line + caveat when protein coverage <70% w/ exons

**Finding**: kākāpō GFF annotates gene-DDX58 at chrZ:42,075,405-42,097,978
— exactly our locus. The E4_unannotated_found label is WRONG for this call:
the L0 annotation integration missed RefSeq AR101. Layer-0 re-validation
bug to fix (affects other E4s on annotated genomes).

### D36 — Intake protocols codified (2026-09-01)
docs/INTAKE.md now defines operating protocols: paper (two-pass system —
fast regex pass + mandatory full LLM verified pass, honest provenance
stamps after the D32 false-verification incident), detection/case
(refresh pipeline + new-source adapter pattern), news (drop folder
standards; news never = wiki evidence alone; suspected-vs-confirmed
preserved), genome (ordered chain incl. IGV assets), gene panel
(config-driven), and quarterly hygiene checklist. README links it first.

### D37 — Full verified paper digest complete + discovery report (2026-09-01)
130 new papers through the FULL 7-step verified LLM pipeline (resume-safe
across two timeouts; 271 verified + 1 partial of 272 total markdowns).
Wiki rebuilt: 254 genes (>=2 papers or curated), 213 species.

**Discovery report ("mentioned but never searched")**: 162 host genes with
corpus evidence but NOT in the 592-panel. Top candidates: TNF (27pp),
NFKBIA/NFKB (27pp), IFITM family members (IFITM2 13pp), ISG15 (22pp),
IFNB1 (12pp), PKR alias, NLRP3 (11pp), IFIT1 (10pp), CXCL10, SOCS1,
OAS1, STING alias, HERC5, IFIT2/3, IL-8/IL-17, ACE2. Several are aliases
of existing panel genes (PKR→EIF2AK2, STING→STING1, OAS1 near OASL,
IFITM2/3 near IFITM3) — need wiki_alias entries rather than new panel
genes. True novel adds: TNF, NFKBIA, ISG15, SOCS1, CXCL10, IFIT1/2/3,
HERC5, NLRP3 (11pp — was only in config as high-importance, now has
corpus backing!), IL-8, IL-17, ACE2.

### D38 — OASL alias bug fixed (2026-09-01)
User chased fimmu-09-01398.pdf (412 OASL mentions) → found it correctly
duplicate-skipped but MIS-matched to duck_genome2013 (same CAU authors).
Real duplicate target: input_2024_8 ("The two faces of OASL" review), fully
analysed in the digest.

Root cause of "OASL has no literature": build_wiki_pages GENE_ALIASES
mapped oasl→OAS family — all OASL evidence diverted to the OAS entry
(the "OAS 29 papers" anomaly in D37's discovery report). Fixed: OASL is
its own symbol with species-variant aliases (hOASL/mOASL1/2/dOASL/…).
Result: OASL 13 papers (10 central); OAS family honestly 5 papers.
STAT1/STAT2 also gained papers in the digest; missing-list now 14.

Intake lesson: _already_matched/ PDFs deserve periodic spot-checks —
content matching can mis-target (right skip, wrong reason).

### D39 — Text-mention evidence tier + JAK family aliases (2026-09-01)
User flagged: PB2/JAK1 paper (input_2024_90, 204 JAK1/2 mentions) discusses
JAK2 but extraction captured only JAK1 (title bias). Fix: generic text-scan
tier in build_wiki_pages — panel symbols regex-counted in every paper
markdown (≥3 mentions, not already extracted) get honest "discussed in text"
evidence, labelled via=text_scan, weaker than studied-tier. Plus JAK1/2/3
canonical entries and a raw gene_evidence_counts.json sidecar (independent
of the ≥2-paper wiki threshold) powering coverage reports.

Coverage: 82 → 142/587 panel genes with any corpus evidence
(129 studied-tier + alias + 13 text-only). JAK2 credited (1 paper).
Importance-labeled zero-evidence list: 15 → 9
(AICDA, BLB1, CASP3, CASP6, IRF8, NOD1, RAG1, RIPK2, SYK).

### D40 — LLM gene-extraction prompt rebuilt for recall (2026-09-01)
Old prompt suppressed peripheral genes ("not just mentioned in passing")
— root of the JAK2 miss. New: three explicit importance tiers, instruction
to include siblings discussed alongside central genes, full panel-symbol
checklist injected into the prompt (lazy-loaded, ~560 symbols), free-form
discovery preserved ("novel discoveries welcome"), primer-table exclusion
kept. Applies to future full passes; text-scan covers existing corpus.

### D42 — Combinatorial insight synthesis engine (2026-09-01)
scripts/papers/synthesize.py: random/same_gene/cross_taxa/contrast pairing
of corpus papers → LLM synthesis judgment. Anti-hallucination architecture:
- every paper card carries journal + year + type; explicit TEMPORAL CONTEXT
  block (lineage eras, 2024 cattle spillover, preprint caveats)
- output REQUIRES grounding_quotes: verbatim per-paper substrings
- MECHANICAL verification: string-containment check — fabricated quotes
  structurally cannot pass (no LLM trust in the gate)
- lifecycle: unverified_hypothesis → human triage (DIGEST.md); never
  auto-published to wiki
- --url/--model/--temperature flags for server swaps

Status: gemma4-31b declines all synthesis under the strict regime (0/18
clean NO_INSIGHTs across strategies) — awaiting the faster sglang server
with a stronger model; tooling ready.

### D43 — Author network + muse-glimmer synthesis live (2026-09-01)
**LLM**: aoraki44 sglang server (muse-glimmer-30b, 131k ctx) via SSH tunnel
→ localhost:8005. INTAKE.md notes the tunnel-drop reminder protocol.
Quirks handled: prompt-echo without system role; verdicts at END of
monologue content (tail-parsing); JSON truncated at low max_tokens
(raised to 3000); placeholder-quote fabrication caught by the
mechanical grounding gate. Synthesis now producing grounded insights
(2-3 per dozen combos) with --workers parallelism.

**Author network** (build_author_network.py): 128 authors, 260 papers,
140 co-authorship edges, 10 clusters. data/papers/author_network.json
(full graph: author↔paper bipartite + weighted co-author edges +
per-author gene portfolio/species/journals/years) + author_network.md
digest (prolific authors, strongest collaborations, research clusters,
gene specialists). Internal graph-DB asset; "et al" artifacts filtered.

### D44 — Avian H5N1 response model v0.1 (2026-09-01)
docs/MODEL_AVIAN_H5N1_RESPONSE.md — the synthesis capstone: 6-stage
species-agnostic avian model (sensing → signalling → effectors → viral
antagonism → cell death → adaptive), mermaid-drawable, every gene node
badged with live corpus-evidence counts (from gene_evidence_counts.json),
species-split table (RIG-I/MDA5/OAS3 across 15 genomes), and a two-tier
gap registry: G1-G8 lit-search targets (BST2, CASP3/6, MHC genes, RAG1,
sialic genetics, Z-linkage, IFITM family, TLR15) vs T1-T5 true gaps
(NZ species immunity, avian STING, inflammasome, mucosal IgA,
temperature-dependence). Update protocol defined (badge refresh on every
wiki rebuild; gap closure notation; version discipline).

### D45 — Model page: the researcher-facing model surface (2026-09-01)
#/model (header "Model") — the avian H5N1 response model as an interactive
research artifact:
- overview mermaid (lineage losses red, antagonism dashed)
- 6 stage node tables: every gene links to its gene page; live evidence
  badges from gene_evidence_counts.json (copied to web/public)
- gap registry panel: G1-G8 lit-search / T1-T5 true-gap, each linking
  to the relevant gene page
- disagreements panel: contradiction/temporal insights from the synthesis
  engine (2 seeded), with paper links; contradiction mining strategy added
  to synthesize.py (same-gene pairs, conflict-hunting prompt)

Verified: stages render, mermaid draws, DDX58 shows "56 papers" badge,
gene links resolve to pages with evidence, gaps and disagreement panels
live. 13/13 tests.

### D46 — Model v0.2: config-driven, expanded stages, mining orchestrator (2026-09-01)
Model moved to data/model/avian_h5n1_model.json (stages 0-7 incl. Entry,
Host-Range bridge; 3 cross-cutting axes: Z-linkage sex, 41°C temperature,
species outcome taxonomy; 13-item gap registry). /model page now renders
from config: live sensor matrix (15 genomes × 8 genes, clickable species
with silhouettes), per-stage evidence coverage bars, axes cards, gaps,
disagreements. mine_model_nodes.py compiled dry packs for all 54 nodes
(34 well-studied / 5 single / 3 mentions / 12 gap). LLM pack-filling
queued for later. 13/13 tests.

### D47 — Mega pipeline complete: 616 verified papers (2026-09-01)
315 PDFs → fast pass (313 ok, 2 stragglers, 5 dups deleted) → FULL verified
digest on muse-glimmer-30b @ c56 → finishing chain. Totals:
- 616/622 papers verified (6 partial), 622 markdowns
- wiki genes 254 → 328; species 213 → (see wiki_species)
- panel evidence coverage: 82 → 157/587 any-tier (140 studied) — nearly doubled
- importance-labeled zero-evidence: 9 → 6 (CASP3, CASP6, IRF8, NOD1, RAG1,
  RIPK2) — SYK/BLB1/TAP2/AICDA/TIRAP/UNC93B1 gained corpus backing
- discovery list: 207 host genes outside panel with evidence (top: TNF 29pp,
  NFKB 27, IFITM-family, ISG15 22, IFIT1/2, CXCL10, SOCS1, ACE2, Caspase-1)
- gene model badges refresh queued; contradiction batch + node packs next
13/13 tests.

### D49 — Copyright posture codified (2026-09-01)
Books (Avian Immunology 3rd ed.) are CITED, never REPUBLISHED: chapter
markdowns stay internal (docs/papers_md) for LLM mining only; the site
publishes citations, extracted findings with attribution, and grounded
passages from open papers. Credits page cites the book (Schat, Kaspers &
Kaiser, Academic Press 2022). Verified: no chapter text in any served
data file.

### D50 — Paper asset registry (2026-09-01)
Internal inventory (data/papers/paper_registry.json — excluded from web
exports per user directive): canonical PDF path+md5-12, markdown, dedup
sources, corrections, news clips, orphan flags. 635 papers, zero orphans.
Rebuild protocol in INTAKE.md.

### D51 — Dedup matcher false-positive fixed (2026-09-01)
Batch 5 wrongly deleted 28 book chapters as "duplicates": a Kazakhstan paper
(input_2024_404) with an ALL-CYRILLIC title normalized to an EMPTY string,
and Python's `'' in text` is True — so its title-contains match hit every
document. Three fixes: (1) empty-title_norm guard, (2) book chapters skip
content-matching entirely (filename-only — new by construction), (3)
doc_type plumbed through match calls. Verified: chapter → None, re-upload →
correct match. Chapters restaged from the zip; retry running.
Also: python -u/stdbuf for unbuffered fast-pass logs.

### D52 — Foreign-language + thesis corpus policy (2026-09-01)
Corpus survey: 1 Cyrillic paper (Kazakhstan HPAI monitoring — title
translated to English, original preserved in title_original), 1 tagged
thesis, 1 Russian-journal paper with transliterated citation. Policy
(INTAKE): theses valued for deep-background mining; foreign-language
docs flow the full pipeline; non-Latin titles get English title +
title_original; Cyrillic empty-normalisation documented as the D51 root
cause (guard is permanent).

### D53 — Thesis census corrected: 12 total (2026-09-01)
User challenged the "4 theses" count; page-count scan (35+pp) found 9 more
hiding behind markers deeper than the 4000-char scan window: 374pp
metabolic-reprogramming PhD, 316pp host-antiviral-proteins PhD, 214pp
"DISSERTATION FOR THE DEGREE OF…", 147pp host-pathogen systems, 104pp
chicken TLR3 characterization, 97pp Palestine Polytechnic masters, 92pp
West Chester, 79pp + 71pp University of Copenhagen (the "foreign"
theses — Danish institutions, English text). All tagged. Also flagged 2
identical 496pp full-book copies (input_2024_165/_135) as superseded by
the chapter set. Lesson: structural detection (page count) beats
text-window matching for doc typing.

### D54 — LLM metadata enrichment pass (2026-09-01)
enrich_metadata.py: per-paper {language (ISO 639-1), doc_type
(peer-reviewed|preprint|thesis|book-chapter|review|report|correction),
species_focus} → papers.json. Hybrid: deterministic first (markdown
doc-type markers, bioRxiv/medRxiv venue → preprint, script-ratio language),
LLM for the rest (muse-glimmer, c32, ~1 call/paper). Deterministic types
never overridden. Batch 6 chain (1061 PDFs, mass-dedup expected) ends with
the enrichment pass before web build. Feeds: synthesis temporal/venue
weighting, papers filters, model species views.

### D55 — Scope tagging: nothing excluded, everything weighted (2026-09-01)
tag_scope.py — deterministic scope per paper from species_focus + title:
avian | avian-epi | human | mammalian | vaccination | viral-biology |
methods | mixed. Human/epi papers STAY fully mined (summaries, text-scan
gene credit, cross-taxon synthesis fuel, discovery for genes lacking
avian data) — scope is a relevance hint for downstream weighting/display,
never an exclusion filter. Run after enrich_metadata (needs species_focus).

### D56 — Decision pipeline formalized (2026-09-01)
docs/DECISION_PIPELINE.md: the intake-to-destination architecture drawn
as one system (typing → matching → two-pass extraction → D54 metadata →
D55 scope → D56 policy routing). Most of it was already built piecewise;
now explicit, with invariants (scope never excludes; deterministic before
LLM; deletions logged; provenance visible) and three remaining wires:
avian/mammalian badge split, scope-carrying evidence rows, consumers
reading pipeline_policy.json programmatically.

### D57 — Two-model architecture: infection + spread (2026-09-02)
Infection model R1 launched (node packs + contradiction mining).
Spread model v0.1 built: 9 stages (reservoir → amplification → bridge →
flyways → seasonality → environmental → anthropogenic → spillover chains
→ NZ/Australasia risk) with inter-stage connections. spread_evidence.jsonl
extraction running (LLM per-paper: flyways, species roles, spread
mechanisms, geography, seasonality, key finding from 102+ epi-scoped
papers). Both models render from data/model/*.json configs → /model page
(needs spread tab). Gene panel unchanged at 587 — 98 discovery candidates
(≥3 papers) awaiting panel-growth decision.

### D58 — Model v0.4: functional motifs, cytokine storm, furin, R2 launched (2026-09-02)
User-directed upgrades:
- **ANP32A 33-aa insertion checked**: kākāpō CONFIRMED to have the full avian
  insertion (susceptible to avian polymerase). Kiwi/rowi partial (248aa).
  8 NZ species too short to assess (fragments only). MX1 too fragmented.
- **Cytokine Storm stage (2.5)** inserted after Signaling: TNF, IL6, IL1B,
  NLRP3, CASP1, SOCS1, IL10 — the tolerance-vs-lethality dividing line
- **Stage 0 expanded**: FURIN (HPAI systemic spread determinant),
  B4GALNT2, ST3GAL4 (sialic acid genetics)
- **Viral antagonism expanded**: PB1-F2 (apoptosis in immune cells),
  PA-X (host shutoff), full NS1/PB2 counter-attack arsenal
- **Adaptive immunity**: IgY, Bursa of Fabricius, mucosal IgA context added
- **Functional motifs section** in model JSON: ANP32A 33-aa status per
  species, MX1 aa631 (needs full-length), extensible for more motifs
- R2 model thinking round launched (node packs + spread evidence → LLM
  structural proposals)
Model now 9 stages, v0.4. 13/13 tests.

### D59 — Conservation risk assessment documented (2026-09-02)
docs/CONSERVATION_RISK_ASSESSMENT.md: the operational companion to the
model. Sections: confirmed findings (ANP32A per-species, RIG-I/MDA5,
combined kākāpō risk picture), data gaps (full-length extraction needs,
MX1 aa631 blocker), model gaps (lit-search targets ranked), panel growth
candidates (98 genes, top 6 recommended), infrastructure needs (exon
stitching, motif checking, clade tagging), literature search priority
queue (7 searches ranked by NZ conservation impact). Linked from INTAKE.

### D60 — Models v0.5/v0.2 applied from R2 proposals (2026-09-02)
INFECTION MODEL v0.5:
- Stage 0 pruned: FURIN (strong, 6pp) + ST6GAL1 (description corrected:
  α2,6-sialyltransferase, MODULATES tropism) retained; B4GALNT2, GALE,
  CMAH, ST3GAL4 moved to hypothesized pool (zero evidence)
- Stage 2.5 Cytokine Storm strengthened: TNF 29pp, IL6 45pp, IL1B 32pp
  (strong coverage confirmed by R2)
- Stage 1 annotated: description reflects pipeline genomic data (RIG-I
  absence, Z-linkage, OASL mimicry) not solely paper-extracted text —
  node-pack excerpts are narrower than the model's evidence base

SPREAD MODEL v0.2:
- Bridge hosts: synanthropic/urban layer + domestic duck farm interface added
- Spillover: marine mammal bridge (fur seal A3) + mammalian amplification
  hotspots (cattle B3.13/D1.1) added
- NZ risk: six specific evidence gaps documented (migratory connectivity,
  farm interface, water persistence, marine mammal susceptibility,
  genotype arrival risk, livestock pathways)
- 3 new connections: environmental→reservoir circular, anthropogenic→routes
  bidirectional, amplification→spillover marine
13/13 tests.

### D61 — i18n, header cleanup, title, overnight LLM launched (2026-09-02)
UI: page title "Roost — Avian Influenza Host Genomics Resource"; Downloads +
Resources removed from header nav (footer only); Viral Counter-Attack →
Viral Antagonism; language switcher (EN/ZH/HI/JA) in header, i18n store
with translations for nav/model/common keys, localStorage persistence.
Overnight LLM: 300-combo synthesis batch (5 strategies × 60 pairs,
workers 32) + model node deep-mining (54 nodes × top-5 papers) +
context mining for 9 lit-search target genes. Will notify.

### D66 — Topic normalization + generation; metadata quality sweep (2026-09-02)
Topic merge rules (fix_topics.py TOPIC_MERGE): Duck→Ducks, Chicken→Chickens,
Turkey→Turkeys, PB2 Mutation→PB2 Mutations, Seabird→Seabirds, Raptor→Raptors,
Mammal→Mammals, Vaccine→Vaccination, Wild Bird→Wild Birds, Marine Mammal→
Marine Mammals. 500 papers received deterministic topics from species_focus +
category + title/summary keyword matching (species, genes, regions, scope).
225 distinct topics; 632/632 papers have topics (100%).

Broader metadata quality: removed 19 error/junk pages (Taylor & Francis
"problem providing content" ×14, "No item found", journal index pages);
stripped HTML from 13+ summaries; fixed array-fragment summaries (343 → 3
via abstract extraction + LLM); corrected categories via rules + LLM;
merged singular/plural topics; fixed reference-list-as-title, TOC-as-title,
dot-leader titles, cookie-banner titles. Final: 632 papers, 99.8% with real
titles, 99.8% categorized, 100% with topics, 95%+ with readable summaries.

## D72 — DOI discovery + metadata backfill + BibTeX (2026-09-03)

- **find_dois.py**: 202 papers lacked DOIs → Crossref bibliographic search
  (title + first author) with normalized-title scoring ≥0.97 + PMID-exact path.
  55 resolved (4 PMID + 51 strong). The one 0.954 match (gannet→H7N3) correctly
  rejected by the author-corroboration rule. DOI coverage 430→485 (76%).
- **backfill_doi_meta.py**: Crossref works/{doi} → structured `authors_list`
  (family/given, full roster), year (243→530, 84%), journal (131→469, 74%).
  Display strings capped at 3 + "et al."; full lists kept in data for the
  author network. Merge-write only, {papers:[...]} invariant verified.
- **Author network rebuilt**: 5,560 authors, 14,144 edges (was 127 authors).
  Consortium papers (100+ authors) capped at first 10 + last 2 by position —
  standard bibliometric cut, prevents n(n-1)/2 edge explosion (was 1.64M).
- **bibtex.py**: 632 entries in data/papers/roost.bib, full author lists,
  @article/@phdthesis/@techreport/@incollection by doc_type.
- Papers.svelte: fmtAuthors() — ≤3 + et al. display everywhere.

**D72 final pass (thesis/DataCite round):** theses included in search; DataCite
API added (ProQuest/university repos/OSF/Zenodo — Crossref's blind spot).
Type-filter applied: Dataset/Software/Image and supplementary-file titles
("Additional file…", "Data from:…") rejected — 6 false matches caught.
+5 DOIs (1 EFSA report, 4 DataCite exact-title). Final: 490/632 (77.5%),
year 531 (84%), journal 470 (74%), authors_list 447. Remaining 142 are
reports/bulletins/regional items legitimately without DOIs.

## D73 — Gene absence-phenotype mining (2026-09-03)

`scripts/papers/mine_absence_phenotypes.py` — extracts loss-of-function
evidence from paper text: knockout/knockdown/siRNA/CRISPR/natural-absence/
LOF-mutation/antagonist-blocked → phenotype + host class (avian/mammalian)
+ VERBATIM quote. Grounding gate: quote must be substring of the markdown
(smart-quote/punctuation-tolerant fallback); un-verifiable records dropped.

- Purpose: replace the gene catalogue's speculative `impact_if_absent`
  (21 genes, uncited) with literature-grounded, cited evidence — especially
  avian-vs-mammalian contrasts
- Output: data/papers/gene_absence_phenotypes.jsonl (per paper) →
  --aggregate builds gene_absence_summary.json (per gene: avian/mammalian
  records with paper citations)
- Test: trim25_irf72026 → 4 grounded records (duck TRIM25 siRNA → enhanced
  TMUV/NDRV/VSV replication; domain mutants lost suppression; IRF7 K46R;
  mammalian ΔRING contrast)
- muse-glimmer quirk: reasons verbosely before emitting JSON — extractor
  takes the LAST complete JSON array; max_tokens 8000; "JSON array as the
  FINAL thing" instruction
- Feeds: gene pages (impact-if-absent with citations), conservation risk
  assessment, model verification evidence pool

Part of the full-re-run campaign: summary rebuild → gene claims →
conclusions → absence phenotypes → model verification.

## D74 — Campaign architecture + intake round (2026-09-03)

**campaign.py** (scripts/papers/): full-re-run orchestrator, all phases
resume-safe, all outputs grounded+cited. Smoke-tested per phase:
- [B] summaries: 2 sentences + main_conclusion, numbers required, no generic
  openers; summary_v2 marker; checkpoint saves every 25
- [C1] gene claims: iterative exclusion loop (user pattern) — round1 "one gene",
  roundN "excluding [list]", stop on false/cap-15; symbols verified vs panel+
  aliases; quotes grounding-gated. Test: TRIM25 paper → 12 tiered genes
- [C2] conclusions: same loop, cap-8
- [D] model verify: per paper × 9+9 stages; verdicts agrees/disagrees/changes/
  adds/not_relevant; ungrounded quotes auto-demoted to not_relevant; export
  tallies for manual model review (v0.6)
- [export] conclusions_list → papers.json; impact_if_absent_lit → gene catalogue;
  gene_lit_claims.json counts; wiki rebuild

**Intake round:** 9 PDFs → 3 new papers (6 deduped correctly). Auto-generated
IDs were garbage ("read_2025") — fixed to proper IDs from markdown content
(chicken_ifitm_ndv2025, ifitm3_nedd4_sva_thesis2024, pasquesi_endogenous2022),
titles extracted, DOIs set from header lines. 632→635 papers.
process_with_llm.py now env-overridable LLM_URL/LLM_MODEL (strong model default
when set). convert_analyses.py step confirmed as the papers.json registration
point. NOTE: fast-pass LLM ID generation unreliable — flag for prompt fix.

## D75 — Species-aware model view + absence corpus (2026-09-03)

**Absence corpus (complete for current corpus):** the campaign smoke test's
subprocess ran mine_absence_phenotypes.py over all papers — 609 mined, 95
papers with LOF evidence, 280 grounded records, 156 genes (ANP32A avian=5/
mammalian=4, IFITM3 mammalian=18, DDX58 4/2, MX1 5/3). Spot-check quote
verification 100%. Served as web/public/data/gene_absence_summary.json.

**Model page species context (user decisions D74 q5-9):**
- Species selector (15 sequenced species, restricted per decision)
- Chips re-style per presence: red "absent", amber dashed "fragment",
  green tint present (RIG-I→DDX58 etc. alias handling)
- Click gene → evidence drawer: literature absence records filtered by
  species class (avian evidence only for birds; mammalian branch ready),
  exact-species first (blue tag "this species"), then same-order keyword
  match ("· same order"), then "reported in [host]" — every record cited
  [paper_id, year] with quote
- Curated impact_if_absent shown BELOW literature ONLY when ≥1 lit record
  exists, labeled "Curated hypothesis (not species-specific)"; hidden
  entirely without backing
- Verified: chicken → RIG-I absent (red), kākāpō → fragments, drawer opens,
  13/13 tests, zero errors

Campaign additions: explicit viral gene list in verification (PB2/HA/NS1/
PA-X/... never dropped); discovery bucket (gene_discovery.jsonl per
occurrence → gene_discovery.json ranked, ≥3 papers = candidate class).

## D76 — Campaign iterate loop + full launch (2026-09-03)

**Single-paper iterate (user protocol: run 1 → examine → fix → rerun → go):**
- Test paper chicken_ifitm_ndv2025. Summary/conclusions/absence excellent
  first pass. Gene claims BUG: known_genes() read cfg["genes"] but
  gene_config.json is {aliases, importance_overrides, display_names,
  wiki_aliases} — panel never loaded, only viral list verified → IFITMs
  bounced to discovery. FIX: known_genes now = gene_catalogue keys (587)
  + config aliases + wiki_aliases + viral list + model aliases = 654
  symbols. Rerun → 8 claims (IFITM1/3 central, IFNL3, NDV W/F/NP/V,
  STAT1) — correct.
- scope=None on the 3 intake papers blocked verify → tag_scope.py rerun.
- Verify verdicts apt: entry adds (IFITM entry restriction), effectors
  agrees, celldeath adds.

**Full campaign launched** (ba641ecab): summaries (632) → gene claims
(~632 × exclusion loop) → conclusions → absence (no-op, done) → model
verify (~633) → export (papers.json, gene catalogue, discovery bucket,
absence summary, wiki rebuild) → build + tests. Resume-safe throughout.

## D77 — Model v0.6 / v0.3 applied (2026-09-04)

Approved from MODEL_V06_DRAFT.md. Edits grounded in the verification campaign
(569 papers, 1,592 verdicts; quotes in model_verdicts.jsonl):

**Spread v0.2 → v0.3:**
- reservoir desc rewritten: "dying reservoir" — 2.3.4.4b lethality in ducks/
  geese with ongoing transmission; no single clear reservoir species; poultry
  amplification (5 disagrees + 21 changes)
- timing desc rewritten: seasonality dissolved, year-round circulation,
  breeding-colony and spring peaks, rainfall-driven in Africa (24 changes)
- diverges[] added: reservoir pathology, bridge-host identity, flyway limits

**Infection v0.5 → v0.6:**
- cytokine_storm: wild-bird caveat appended (peracute necrosis w/o infiltrates
  in kittiwakes, "counter to the paradigm" attenuation, cytokines→resistance)
- celldeath: duck tolerance "partial and eroding" (2.3.4.4b lethal, H5N6
  increasing pathogenicity)
- diverges[] added: storm-vs-peracute mechanism, RIG-I-chicken flag
  (annotation-bleed interpretation, not a gene change)

**Frontend:** diverges render in both tabs with linkified [paper_id]
citations (splitCitations helper); spread-stage translation prefix bug fixed
(model.inf. → model.spread. — was shadowing with infection translations).
Verified: all stage rewrites + 5 diverges entries render, citations navigate,
13/13 tests.

Not yet applied: the 373 "adds" verdicts — separate enrichment pass later.

## D78 — Post-campaign cleanup round (2026-09-04)

**1. Adds enrichment (373 "adds" clustered → additions ledgers):**
- infection v0.6 +8 additions: dairy-cattle emergence, mammalian-adaptation
  markers in wild-bird isolates, new mammalian host records, IFITM entry
  block, Galectin-3 co-factor, neuroinvasion mechanism, STING-GSDMD axis,
  adaptive serology
- spread v0.3 +4 additions: specific bridge hosts, mammalian bridges
  (swine/dairy), REVERSE spillover (mammal→bird via scavenging), Antarctic
  establishment
- Rendered as "What the literature adds" panels on both Model tabs, all
  citations linkified

**2. Markdown re-fetch:** 23 papers without markdowns → EuropePMC OA fetch
recovered 4 (pb2_anp32_taylor2026 59KB, hokkaido 56KB, france_seabirds 50KB,
xie2023 81KB); 19 remain closed-access/not-in-PMC (drop PDFs to backfill).
4-paper campaign catchup running (bg b69fe1e3e).

**3. Phase-2 translations:** translate_papers.py updated (conclusions field
+ --refresh-papers flag); 635 papers × 4 langs re-translation running
(bg b9854a842) — v2 summaries invalidated old translations.

**4. Panel growth round:** 9 discovery-bucket genes added to host_panel_v2
(596→605): ISG15 TNF IFNB1 NLRP3 CXCL10 IL8 NFKBIA SOCS1 CASP1 JAK1 (JAK1
was already present — 9 added). All tier-2, category-tagged, sources
discovery_bucket_v1. References → DIAMOND presence → export running
(bg b253e2c9e).

## D79 — Panel-growth incident + recovery (2026-09-04)

**Incident:** blast_presence.py --genes (9-gene subset run) produced 0 calls
(reference resolution had failed for 8/9 new genes — only TNF resolved), then
REWROTE gene_presence_v2.jsonl with the empty result. export_presence followed,
publishing an empty gene_presence.json (0 genes × 0 species).

**Root causes (2):**
1. blast_presence.py always rewrote the full jsonl from the current run's
   calls — subset runs replaced 8,880 calls with the subset's output
2. Validation gates hard-failed on out-of-scope genes (DDX58 gates fail on any
   --genes run that excludes DDX58) — and were ignored downstream anyway

**Recovery:** gene_presence_v2.parquet (Aug 31, 8,880 raw rows) → jsonl
reconstructed → export re-run → 587 genes × 15 species restored, kākāpō
DDX58 FULL/E4 verified. Evidence store (592 files) untouched throughout.

**Hardening (applied):**
- subset runs MERGE into existing calls (drop only in-scope (species,gene)
  pairs, append new), never replace
- empty-write guard: 0 calls → abort before touching the jsonl
- gates are scope-aware on --genes runs
- LESSON: blast_presence --genes previously implied "recompute the panel
  subset and REPLACE" — semantics now merge. Parquet mirror saved the day;
  keep it fresh after every run (it is).

Reference failures for ISG15/IFNB1/NLRP3/CXCL10/IL8/NFKBIA/SOCS1/CASP1 under
investigation (chicken symbol resolution retry running).

## D80 — Panel growth round complete (2026-09-04)

**10 genes attempted, 8 added with presence calls (587→593 catalogue,
8895 served calls), 2 real findings:**

1. **TNF/ISG15/CXCL10 have NO annotated ortholog in ANY bird genome checked**
   (Gallus, Anas, Taeniopygia, Meleagris — NCBI gene db). Canonical TNF-α
   does not exist in birds; **TNFSF15 (TL1A) is the functional analog** —
   added to the panel (alias TNF), FULL/E5 in all 15 genomes including
   kākāpō. ISG15/CXCL10: absent from avian annotations entirely — the 37+36
   discovery-bucket papers measuring them are mammalian-system studies.
   These stay OUT of the panel (nothing avian to search); documented here
   and in panel notes.
2. **Alias resolution worked as designed**: IFNB1→IFNB (chicken symbol),
   CASP1 resolved twice (CASP1 + PCASP1 paracaspase — both real genes).

**New panel members with 15-genome presence:** IFNB, NLRP3, IL8, NFKBIA,
SOCS1, CASP1, PCASP1, TNFSF15, JAK1 (straggler — was in panel, never called).
Kākāpō: TNFSF15/NLRP3/IL8/NFKBIA/SOCS1/IFNB FULL, CASP1 FRAGMENT.
The cytokine-storm and inflammasome model stages now have genomic presence
grounding across all NZ species.

Runs went through the D79 merge path: zero data loss (8955→8970 verified).

## D81 — Orphan markdown intake (2026-09-04)

**Shadow corpus discovered:** 52 markdowns in docs/papers_md never registered
into papers.json (fast-pass registration gap — same failure as the read_*
three). 1 was an attached correction (correctly skipped), 51 registered via
register_orphans.py: title from first heading/header lines, DOI regex,
journal/year from citation lines. Titles cleaned of markdown artifacts;
bulk_title_fix.py (LLM) repairs weak ones; find_dois + backfill fill metadata.

Full chain: register → DOI → metadata → title fix → scope → campaign phases
(summaries/gene claims/conclusions/verify/absence) → export → author network
→ BibTeX → wiki → stats → build+test. Corpus 635 → ~686.

## D82 — Dedup over-matching bug + LLM outage (2026-09-04)

**Bug:** match_pdf_to_paper's title-keyword rule (first 3 words >4 chars,
all-in-filename) matched generic-titled papers to nearly every incoming HPAI
PDF. input_2024_358 ("Highly Pathogenic Avian Influenza", 4 words) ate **33
PDFs historically**. Same vector via markdown-head title substring.

**Fix:** specificity guard — title-keyword and md-content matching now
require ≥5-word titles not in the generic blocklist, 4+ matched keywords,
≥45-char normalized title for content matches. Generic-titled papers match
by exact paper-id/DOI only.

**Recovery (no LLM needed):** 5 DOI-named false dupes re-fetched via
EuropePMC full text (isme_hpai_2025, scirep_h5n1_2021, scirep_h5n1_2025,
commbio_h5n1_2026, sciadv_aea2068 — 99/38/88/44/59 KB) → 692 papers.
3 need operator re-drop: "pathogenesis 2022 North American…" (no DOI
found), Vega-Macaya Transboundary 2026 (10.1155/tbed/1266281, closed OA),
document.pdf (unidentifiable).

**Compounding outage:** LLM tunnel dropped mid-chain (connection refused on
:8005). Blocked: 54 summary catch-ups (52 orphans + 2), 14 title fixes,
campaign phases for the 5 recovered papers. The 47-PDF batch itself was
consumed while the matcher bug was live — mostly genuine dupes (specific-
title matches verified) + the 8 false ones handled above.

**When tunnel returns:** campaign.py summaries (54 pending) → genes/verify/
absence for 5 recovered → bulk_title_fix → translations incremental →
export + rebuilds.

## D84 — Full-panel stage assignment + model updates (2026-09-04)

**15th disagreement folded in:** scirep_h5n1_2025 (spatial-risk study) —
model selection did NOT retain gull/shorebird (Charadriiformes) abundance
as H5 outbreak predictors; bridge diverges entry extended with the quote.

**Recoveries:** vega_macaya_2026 recovered from PMC HTML (81KB, Wiley 403'd
automation; PMC mirror worked) → corpus 695, campaign queued. pathogenesis-
2022 (Avian Pathology 10.1080/03079457.2023.2196258) needs manual PDF
re-drop — T&F blocks all automated access.

**OAS finding (user Q):** OAS1/OAS2/OAS3 exist in NO bird genome (kākāpō,
duck, chicken all absent at NCBI; human has all 3). The OAS expansion is
mammalian-only — mirrors the TNF story. Birds: single OAS + OASL + RNASEL.
Kākāpō OASL found by our search layer despite NCBI symbol gap.

**Stage assignment (scripts/genes/assign_stages.py):** keyword rules over
UniProt function/protein-name text assigned 269 panel genes to model stages;
claims-LLM +21; 303 remain unassigned (evidence-poor backbone genes —
Avidin, hemoglobin subunits). Output: gene_stage_assignment.json (served).

**ModelCyto full-panel toggle:** 541 non-model genes render as hidden dots
in their stage containers; toggle shows all 609 genes. 303 unassigned go in
an "Uncharacterized" container — the evidence gap is now visible on the
graph itself. Deterministic before LLM throughout.

### D67 — MHC-B genes completed in model + catalogue aliases (2026-09-15)
USER FINDING: "MHC genes missing from the model pathway" — two causes fixed.
(1) The adaptive stage lacked the best-evidenced MHC gene (BF2, 19pp — B21
haplotype protection) plus TAPBP/CD74; BNK/B-Lec (MHC-B-encoded NK pair,
incl. Blec2 — corpus input_2024_158 warns Blec nomenclature is contradictory:
"Blec2" in some nomenclature is structurally unlike Blec1/3, pair often
written Blec2/Blec1) added with it. Model adaptive now: B2M, BF2, BLB1/2,
CD74, TAP1/2, TAPBP, BNK, BLEC, RAG1, AICDA, SYK, IRF8 (14 genes).
(2) Birds use B-locus names (BF/BLB/DMB/BG/BNK/B-Lec), never HLA/"MHC"
symbols — invisible to search. Added `catalogue_aliases` section to
gene_config.json (B-F, B-LB, tapasin, MHC class I heavy chain…), wired into
export_presence.py gene catalogue (display+search only; presence-merge
`aliases` untouched by design). Curated functions for 8 null-function MHC
genes (BF1/BF2/TAPBP/CD74/DMB2/CIITA/BNK/BLEC) — keyword stage assignment
now deterministic for them.
Also: stale v0.1 badges fixed in MODEL doc Stage 6 (BLB1/TAP2 "zero corpus
papers" was pre-D47; now 10/17pp), G3 gap sharpened to cross-species
associations, nomenclature note added to stage desc.
Pipeline: export_presence.py → assign_stages.py (keyword) → model JSON synced
to web/public. 81/81 tests.

### D68 — Vaccine model pillar: page + queue-based mining infra (2026-09-15)
Third model pillar (infection | spread | VACCINE — "how we intervene", unit =
vaccine × species × experiment; 570/1206 corpus papers mention vaccination).
Not a gene-model stage: own 9-stage pipeline (platforms, antigen, delivery,
adjuvant, response, protection, DIVA, deployment, escape) with GENE BRIDGE
links both ways (BF2/BLB2/CD74/RAG1/AICDA/TLR21/TLR3/DDX58/IFNB1/IRF8 —
adjuvant = chosen sensor, sensor = gene).
Literature LLM is DOWN: build_vaccine_model.py ships the skeleton with
DETERMINISTIC keyword-tier evidence (🟡, whole-corpus rg per stage: 467
candidate papers, top m2e_nanovaccines 356 hits). mine_vaccines.py is the
resumable LLM pass for when it returns: queue rebuilt from fresh corpus scan
each run (new papers auto-enter), claims jsonl = mined-state ledger,
new-only default, --all/--redo/--papers/--dry; proposer+skeptic double-
confirm; output merges → stages rebadge 🟡→🟢. 6 gaps registered (V1 NZ
taonga program, V2 transmission-block efficacy, V3 avian imprinting, V4
MHC×response beyond chicken, V5 mRNA poultry economics, V6 oral-bait).
Web: #/vaccines (Vaccines.svelte — pipeline mermaid, stage cards with
candidate counts + top-paper links + gene chips, gene-bridge panel, mining
queue panel, gaps), nav entry, i18n key, Model-page tab cross-link.
Design doc: docs/MODEL_VACCINES.md. 81/81 tests.

### D69 — Vaccine model: species readiness, tracker, spread links (2026-09-15)
(1) SPECIES VACCINE-RESPONSE CAPACITY (deterministic, genome-tier):
build_vaccine_readiness.py scores 4 immune modules a vaccine needs
(MHC-II helper, MHC-I/CD8, CpG/TLR21, RNA/LAIV innate priming) from the
presence matrix — 208 species (161 avian: 50 strong / 72 capable / 33
reduced / 6 concern). Sanity checks pass: chicken & turkey missing DDX58
(Galliformes RIG-I loss), mallard complete, kākāpō 0.85 strong (CpG arm
intact, MHC-I/CD8 reduced: BF2 fragment + TAPBP/DMB2 missing → planner
callout on the page). Honest caveats shipped: mammals flagged
(B-locus nomenclature uninterpretable — is_aves join from genomes.parquet),
absences may reflect genome quality not true loss. Tier upgrades to
'calibrated' when mining lands (user opted: scores now, calibration later).
(2) DEVELOPMENT TRACKER: 15 curated entries (licensed+deployed inactivated
programs China/Egypt/Indonesia/Vietnam/Mexico, HVT-H5 vectors incl.
Vectormune/Vaxxitek, Mexico H7N3 DIVA precedent, France duck campaign
2023 (corpus: france_duck_vaccination2025), condor + king-penguin wildlife
programs, US cattle conditional-license landscape, mRNA/DNA/M2e-nano/LAIV
candidates) — every entry corpus-anchored (paper links); web_verified flags
on entries needing live checks (search API keys unset — /web-tools needed;
WOAH global-strategy page fetched directly as first web source).
(3) SPREAD INTEGRATION: spread_integration block — R_eff ≈ R₀×(1−eff×coverage)
on amplification, DIVA/trade on anthropogenic, spillover reduction, NZ
pre-emptive taonga programs; numbers pending V2 transmission-block mining.
Web: readiness table (bands, module columns, kākāpō planner callout,
species links), tracker table, spread cards on #/vaccines. 81/81 tests.

### D70 — Vaccine mining prompts hardened + triage pass; nav rename (2026-09-15)
PROMPT REFINEMENT (mine_vaccines.py; schema in build_vaccine_model.LLM_PLAN,
single source — mine imports it):
- New pass 1 TRIAGE (--triage, 1 cheap call/paper): primary / vaccine-relevant
  / mention-only / not-vaccine → skips mention-only before expensive calls,
  primaries mine first; ledger data/papers/vaccine_triage.jsonl; --tier filter.
- PROPOSER hard rules against classic failure modes: never compute/convert
  ("8/10" stays "8/10", units as printed); groups never merge (vaccinated vs
  control arm-swaps are the worst error class); every number quote-anchored
  (≤8 verbatim quotes); one record per vaccine×species×experiment (multi-arm
  → multiple records); nulls/negative results are results; genes_mentioned
  carry context enum (adjuvant_target/response_marker/haplotype_effect/
  correlate_of_protection/vector_component); challenge clade only if stated.
- Schema expanded 26→~46 fields with 5 controlled vocabularies (platform ×12,
  delivery_route, transmission_assessed incl. inferred_from_shedding,
  diva, gene context); timing fields (age at vaccination, days last-dose→
  challenge) for waning analysis.
- SKEPTIC verdict modes: ok / unverified (plausible, not quote-anchored →
  human review, verified:null) / contradicted (drop from 🟢); explicitly
  audits arm-swaps, unit mismatch, impossible ranges, species-of-quotes.
- Nav label 'Vaccines' → 'Vaccine' (i18n en; fallback covers locales).
Verified: both scripts parse; --triage --dry lists 467; 81/81 tests.

### D71 — Vaccine page sourcing audit: every claim cited (2026-09-15)
USER GOAL: "everything said on the website is backed by news/journal/other."
Implemented as a gate, not a hope:
- CLAIMS registry in build_vaccine_model.py: 23 load-bearing factual claims
  across the 9 stages, each with an rg probe → resolved to corpus papers at
  build time (backed_by + backing_count in the shipped JSON); stage cards now
  render "Key claims · cited" with paper links. Unsourced claims would render
  amber ⚠ and fail the audit.
- audit_vaccine_claims.py (exit-1 gate, CI-able; report
  data/model/vaccine_claims_audit.md): checks (1) every claim ≥1 corpus paper,
  (2) every tracker corpus id resolves to a real markdown file + no-source
  entries carry web_verified:false, (3) gene-bridge genes exist in catalogue,
  (4) readiness shipped with all 3 anchor species.
- Audit caught 3 real issues on first run: IFNB1 not in catalogue (→ IFNB,
  fixed), a too-narrow probe (corpus says 'vaccination programme' — British
  spelling; probe widened), and resolve_claims regex-vs-literal bug (probes
  are regex; scan_stage escapes keywords — split code paths).
- One unsourced number corrected from the corpus itself: 'in ovo ~20 billion
  doses/yr' → 'mass application vaccinates ≈24 billion chickens annually'
  (practical_aspects_poultry_2022 §18.3.1).
RESULT: AUDIT PASS — 23/23 claims corpus-backed (71pp–2pp), 15/15 tracker
entries sourced-or-flagged, 10/10 gene-bridge genes in catalogue, readiness
anchors verified. 81/81 tests.

### D72 — Species-vaccine-response source plan; SearXNG live (2026-09-15)
SearXNG web tools confirmed working (search API configured). Source audit for
readiness scores: (a) ImmunomeDB already local — 363 B10K species × 520
immune genes BUT zero B-locus genes (no BF/BLB/TAP/B2M; only IFIH1/TLR4 of
module genes) → cannot score MHC modules; useful for cross-validation +
immune-backbone scoring for +317 species not yet in readiness. (b) IPD-MHC
verified: bird coverage = Gallus only (BirdBase retired) → chicken B-locus
allele reference for haplotype modeling, not cross-species. (c) The real
species-breadth lever = running existing blast_presence.py on more B10K/NCBI
assemblies. (d) 7 papers queued to papers_need_download.csv (was 26): kākāpō
MHC-II β loci (Immunogenetics 2013 — direct planner upgrade), chicken
antibody-response genetics 2024, divergent vaccine-Ab selection lines 2019,
duck-vs-chicken response reviews ×4. Source plan table added to
MODEL_VACCINES.md. 81/81 tests.

### D73 — ImmunomeDB joined into readiness: 525 species (2026-09-15)
build_vaccine_readiness.py now joins the local ImmunomeDB snapshot (363 B10K
species × 520 immune genes, ANNOTATED/PSEUDOGENIZED): 46 overlapping species
gain a backbone cross-validation column; 317 B10K species enter the readiness
table as backbone-only records (ANNOTATED/panel; MHC modules honestly null —
ImmunomeDB carries no B-locus genes; caveat text + vintage 2020-B10K1 shown
per row). Ready table: new Backbone column, '—' module cells for
backbone-only rows, band chips exclude n/a; ImmunomeDB provenance block in
the JSON (vintage, panel size, overlap/backbone-only counts). Sorted:
presence-scored first, then backbone-only by backbone. Kākāpō anchor
unchanged. Also removed a stale duplicate write_text block from D69 edit.
81/81 tests; dist rebuilt.

### D74 — Readiness IFNB ghost-gene bug fixed; BLAST module run launched (2026-09-15)
BUG (caught pre-run while checking BLAST references): readiness MODULES listed
IFNB1 but the presence matrix symbol is IFNB — the gene had zero rows, was
silently scored 0.0, deflating rna_laiv for EVERY species by 1/7. Fixed
(IFNB1→IFNB) + hardening: build_vaccine_readiness now EXITS if any module
gene has no presence rows (ghost-gene class fails loudly forever). Corrected
scores: mallard 0.96→1.00 (perfect), chicken 0.93→0.96, kākāpō 0.85→0.89
(rna_laiv actually 1.0); avian bands 50/72/33/6 → 59/73/26/3.
BLAST MODULE RUN (in flight): manifest audit showed all on-disk genomes
already scored; new scoring requires downloads. Targeted the upgrade mission:
10 chromosome-level pending genomes whose species are ImmunomeDB
backbone-only (→ full module scores): budgerigar (parrot — kākāpō-relevant),
great tit, house sparrow, collared flycatcher, red-throated loon, whooping
crane, lesser rhea (paleognath), hoatzin, great cormorant, red-crested
turaco. New fetch_selected.py driver (reuses fetch_genome semantics, bounded
accession list) → blast_presence --genes <21 module genes> → export →
assign_stages → readiness → claims audit → pytest, chained in background.
81/81 tests at launch.

### D74 (result) — BLAST module run complete: 10 species upgraded (2026-09-15)
All stages green (exit 0): 10/10 genomes fetched (7 were already cached on
disk — downloads had happened, scoring never ran), 21 module genes BLASTed
per genome (searchability-gated, absence-confidence graded, full provenance
in gene_presence_v2), export + stages + readiness + claims audit PASS +
81/81 tests. Readiness: 317 → 307 backbone-only; 56 cross-validated;
avian bands now 67 strong / 75 capable / 26 reduced / 3 concern.
Highlights: whooping crane + great cormorant 1.00 (perfect, all 21 intact);
red-throated loon 0.975; budgerigar (parrot, kākāpō-relevant) 0.79 capable —
MHC-I/CD8 arm only 0.30 (TAP1/TAP2/TAPBP not found; tblastn homology at
58.9/58.8% id just under thresholds — lineage signal vs annotation quality,
honest caveat applies, cf. kākāpō's own mhc1=0.70); paleognath rhea 0.83.
Dist rebuilt; verified live (#/vaccines readiness table).

### D75 — Full upgrade batch launched: 36 genomes (2026-09-15)
User directive: expand module scoring to all upgradeable genomes. Selected
ALL remaining pending ∩ ImmunomeDB-backbone-only species: 36 (34
chromosome-level), incl. NZ rifleman (Acanthisitta chloris) and kagu
(Rhynochetos jubatus — NZ), Seychelles magpie-robin, crested ibis, canary,
starling, paleognaths (Eudromia), and broad passerine/neoavian coverage.
Same chain as D74 (fetch_selected → blast 21 module genes → export →
stages → readiness → audit → tests → dist), now with && fail-fast.
Expected end state: ~307 backbone-only → ~271; fully-scored species 218→254.

### D75 (result) — 36-genome upgrade complete: 254 species fully scored (2026-09-15)
All stages green under bash wrapper (fish had eaten the first launch — bash
syntax in fish shell; relanched via script, set -euo pipefail). Readiness:
backbone-only 307 → 271; fully scored 218 → 254; avian bands 90 strong /
88 capable / 26 reduced / 3 concern; median overall 0.812. Audit PASS,
81/81 tests, dist rebuilt.
Watchlist results:
- Kagu (NZ) 0.889 strong — MIRROR of kākāpō (0.889, TAPBP missing, mhc1
  0.70): two NZ endemics with the same module signature.
- Rifleman (NZ) 0.829 capable — DMB2/IFNB/TAP2/TAPBP gaps.
- Lovebird (2nd parrot) 0.914 strong, mhc1 0.80 — DOES NOT replicate
  budgerigar's 0.30 TAP-depletion → budgerigar result is likely
  assembly/annotation quality, NOT a parrot-lineage signal. Correction
  noted against D74's speculation.
- Crested ibis 0.982 (near-perfect); Seychelles magpie-robin 0.757 (most
  reduced — island endemic); tinamou (paleognath) DDX58 missing (novel
  if real — assembly caveat applies).
Remaining 271 backbone-only species have NO available assembly — they
upgrade only as new genomes publish (B10K/NCBI watch).

### D75 erratum — kagu geography (2026-09-15)
D75 (result) mislabeled the kagu (Rhynochetos jubatus) as NZ. It is endemic
to NEW CALEDONIA — sole living member of Rhynochetidae (Eurypygiformes,
sister to the sunbittern), flightless, endangered (~1k birds). The
kākāpō-mirror observation therefore becomes MORE interesting, not less:
kākāpō (NZ, Psittaciformes) and kagu (New Caledonia, Eurypygiformes) are
deeply diverged lineages on different landmasses — identical module
signatures (0.889, TAPBP missing, mhc1 0.70) = convergent pattern in two
unrelated flightless island endemics, OR a shared annotation-quality
artifact (kagu ImmunomeDB backbone 0.517 — older B10K1 annotation).
Flagged for the mining pass: check TAPBP assemblies for both.
Also: the apparent corpus kagu hits were 'Sakaguchi' substring false
positives — the kagu has NO HPAI literature (consistent with no New
Caledonia detections). Pure genome-tier species: readiness is the only
evidence layer it has.
