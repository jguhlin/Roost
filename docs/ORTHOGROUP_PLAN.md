# OrthoGroup Integration Plan

**Status:** Approved for implementation (2026-09-28). Scope decisions locked in §4.
**Source:** `orthofinder/orthofinder_aves463_root16_20260928/` — 15 GB, extracted and verified.

## 1. What we have

Reviewed, corrected-root OrthoFinder 3.1.5 run over **463 avian proteomes**
(6,824,866 proteins → 40,494 orthogroups, 98.9% assigned), accepted 2026-09-28.

| Asset | Location | Size | Contents |
|---|---|---|---|
| Orthogroup membership | `Results_Aves463_Root16/Orthogroups/Orthogroups.tsv` | 94 MB | OG → protein accessions per species |
| **Presence/count matrix** | `Orthogroups/Orthogroups.GeneCount.tsv` | 37 MB | 40,494 OGs × 463 species copy counts |
| MSAs | `MultipleSequenceAlignments/*.fa` | 7.4 GB | 35,831 aligned FASTA |
| Gene trees | `Resolved_Gene_Trees/Resolved_Gene_Trees.txt` | 449 MB | 31,257 Newick (`OGid: tree;` per line) |
| Species tree | `Species_Tree/SpeciesTree_rooted*.txt` | 27 KB | Rooted, node-labelled Newick |
| Protein metadata | `Identifiers/SequenceIDs.txt` | 6.8 M lines | internal ID → accession + NCBI product text |
| Species registry | `Identifiers/SpeciesIDs.txt` | 463 | `Species__GCA/GCF_accession` |
| Protein→gene maps | `Identifiers/protein_to_gene/*.tsv` | 463 files | accession → assembly-local gene ID (chicken map carries symbols) |
| Provenance | `Provenance/`, `ORTHOFINDER.md`, `MANIFEST_core.json` | — | Full methods, logs, per-file SHA256 |

Pairwise orthologues: separate optional companion archive, **not downloaded** (§4.5).

### Verification already performed

- Integrity: zstd test + 4 random SHA256 spot-checks vs `MANIFEST_core.json` — pass.
- Join viability: `SequenceIDs.txt` product text → OG via one scan of `Orthogroups.tsv`.
  Demo: **DDX58/RIG-I → OG0011985** — 328 proteins / 328 species, all in exactly one OG.
- Biology check: RIG-I present 335/463, **absent from all Galliformes** (reproduces the
  documented galliform RIG-I loss), present in Anseriformes. ANP32A → OG0004189
  (448/463 species).
- Species join: **463/463** OF species match `data/species_table.parquet` by scientific
  name; 246 also match the 719-species web index.
- Compression: zstd-19 on aligned FASTA is highly effective — RIG-I MSA 332 KB → 32 KB
  (9.7%), ANP32A 256 KB → 16 KB (6.1%), a 360 MB giant family → 0.9 MB (0.25%).

### Gotchas (enforce in code)

- MSA/tree labels sanitize `.` → `_` in accessions; match the known species prefix,
  don't split at every underscore.
- Never join OG numeric IDs with older exports.
- Protein accessions alone are not globally unique — always species-qualify.
- 31,257 trees < 40,494 OGs: some OGs lack trees/MSAs; UI degrades gracefully.
- `protein_to_gene` maps include discarded isoforms; restrict via SequenceIDs.

## 2. Architecture

```
scripts/orthofinder/                # Phase A (offline build)
  build_species_map.py              # OF label ↔ taxon_id ↔ site species
  map_panel_to_og.py                # 992 panel genes → OG(s), curated + generic regex
  export_og_data.py                 # per-OG payload JSON + zstd MSA + Newick
  export_og_matrix.py               # full 40,494 × 463 parquet for DuckDB

data/orthofinder/                   # intermediates (not in git)
  species_map.parquet
  gene_to_og.tsv                    # full mapping incl. review rows

web/public/data/
  gene_orthogroups.json             # gene → OG(s) + confidence (web-facing)
  orthofinder/species_map.json
  og_matrix.parquet                 # full count matrix
  orthogroups/
    OGxxxxxxxx.json                 # members, counts, stats, tree newick
    OGxxxxxxxx.fa.zst               # trimmed MSA, zstd-19, lazy-fetched
```

## 3. Phase A — build pipeline

### A1. Species map
Join the 463 `SpeciesIDs.txt` labels to `species_table.parquet` (scientific name;
463/463 verified). Carry taxon_id, assembly accession, order/family.
Outputs: `data/orthofinder/species_map.parquet` + `web/public/data/orthofinder/species_map.json`.

### A2. Panel → orthogroup mapping (`map_panel_to_og.py`)
Panel scope: **all 992 genes** of `host_panel_v2.json` (18 Tier-1, 534 Tier-2, 440 Tier-3).

Method per gene:
1. **Curated patterns** for all 18 Tier-1 genes (hand-written, family-discriminating;
   e.g. ANP32A = `leucine-rich nuclear phosphoprotein 32 family member A\b`,
   DDX58 = `RIG-I\b`, IFITM1 vs IFITM3 distinguished by trailing digit).
2. **Generic patterns** for Tier-2/3: `\bSYMBOL\b`, full gene name, aliases.
3. Match against product text in `SequenceIDs.txt` (all 463 species; chicken is
   species 186, mallard 19 — genes absent in chicken still anchor elsewhere).
4. Map hit accessions → OG (single scan of `Orthogroups.tsv`); vote.
5. Confidence:
   - **high** — ≥75% of matched proteins in one OG, ≥10 species matched
   - **medium** — 50–75% in one OG, or fewer species
   - **review** — split across OGs (paralog families: IFITM, OAS, MHC, TLR) or weak
     matches → manual override table `CURATED_OVERRIDES` in the script
6. Outputs:
   - `data/orthofinder/gene_to_og.tsv` — every gene incl. review rows + stats
   - `web/public/data/gene_orthogroups.json` — trimmed web payload

Chicken symbol cross-check: for genes with `chicken_gene_id`, verify the mapped OG
contains a chicken protein whose `protein_to_gene/GCF_016699485.2.tsv` symbol matches;
record `chicken_symbol_check` (agree/disagree/no-chicken).

### A3. Per-OG web payloads (`export_og_data.py`)
For the union of mapped OGs (high + medium + overridden-review; est. 900–1,300):

`OGxxxxxxxx.json`:
- members: species, protein accession, product text, NCBI Protein URL
- per-species copy counts (presence vector, 463 slots)
- stats: n species, coverage %, single-copy flag, max copies, has-tree, has-msa
- resolved gene tree Newick (if present; median 10 KB, max 478 KB — include as-is)

`OGxxxxxxxx.fa.zst` — MSA, **zstd level 19**:
- drop all-gap columns
- cap taxa (representative sampling, ≤ 150 species) and hard cap ~2 MB decompressed
  for giant families
- served static, **decompressed client-side** (fzstd, ~10 KB gzipped lib)
- estimated total for panel OGs: **15–30 MB compressed** (verified ratios 6–10%)

### A4. Full matrix (`export_og_matrix.py`)
`GeneCount.tsv` → `web/public/data/og_matrix.parquet` (long or wide; DuckDB-friendly,
~5–15 MB) for the download center and any-OG exploration.

### A5. Provenance & methods
- Register run in `provenance.json` (source hashes from `MANIFEST_core.json`, software,
  dates, caveats).
- Methods page section from `ORTHOFINDER.md`.

## 4. Locked decisions

1. **Scope: panel genes only.** All 992 panel genes map to OGs; only their OGs get
   full payloads (MSA/tree/members). Full 35,831-OG export is a possible later phase
   (the matrix parquet still covers everything).
2. **MSAs are zstd-compressed** (`.fa.zst`, level 19) and decompressed in-browser.
   No plain-FASTA duplication on the server.
3. **BLAST-based presence stays visible.** Gene pages show both: BLAST presence
   (255 assemblies, E-levels) and orthogroup presence (463 species, copy counts),
   clearly labeled by method. Neither silently supersedes the other.
4. **Viewers:** gene tree = Phylocanvas GL (reuse from Phylogeny page); MSA = minimal
   custom canvas component (theme-consistent, no dependency; horizontal scroll,
   species-prefixed labels, conservation shading optional). Iterate later if needed.
5. **Orthologues companion: skip** for now; revisit if pairwise orthologue views wanted.

## 5. Phase B — web

1. **Gene page orthology section** (GeneFullPage): OG chip(s) + confidence, presence
   bar (n/463), copy-number distribution, link to `#/orthogroups/:og`. BLAST presence
   retained alongside.
2. **Orthogroup route** `#/orthogroups/:og`:
   - header: OG id, size, coverage, single-copy status, mapped panel gene(s)
   - presence grid: 463 species ordered by species tree, cell = copy count
   - gene tree: Phylocanvas GL from embedded Newick
   - MSA: lazy-fetch `.fa.zst` → fzstd → canvas viewer
   - member table: species, accession, product, NCBI Protein link
   - graceful "no tree / no MSA exported" states
3. **Species pages:** "OrthoFinder" badge for the 463 (link to their OG stats).
4. **Downloads:** og_matrix.parquet, panel OG bundle, mapping table, provenance.
5. **Methods:** OrthoFinder run description + caveats (orthology ≠ phenotype approval).

## 6. Acceptance criteria

- A2: all 18 Tier-1 genes map with `high` confidence or a documented override;
  review list exported for human curation.
- A3: every exported OG JSON validates (species count = 463 slots; members' accessions
  ⊆ Orthogroups.tsv row); every `.fa.zst` decompresses cleanly (fzstd-compatible
  frame — no `--long` window).
- Web: `npm run build` passes; OG route renders for OG0011985 with tree + MSA;
  gene page shows orthology section; BLAST presence still visible.
- Provenance recorded before any web data ships.

## 7. UI copy caveats (from bundle README)

Orthology resource, not conservation/phenotype approval. Partial proteins, fast-tree
uncertainty, root-dependent memberships are accepted limitations. Alignment trimming
can remove columns. Gene IDs in `protein_to_gene` are assembly-local.
