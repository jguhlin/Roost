# Papers Search and Update Scripts

Scripts for finding and adding new H5N1/avian influenza research papers to the Roost database.

## Quick Start

```bash
# Run the full update workflow
./scripts/papers/update_papers.sh

# Or run individual steps:
python3 scripts/papers/search_papers.py --days 30
python3 scripts/papers/merge_papers.py --review
```

## Scripts

### `search_papers.py`

Searches PubMed, PMC, and bioRxiv for new papers matching H5N1 research queries.

```bash
# Search all sources, last 30 days
python3 scripts/papers/search_papers.py

# Search specific source
python3 scripts/papers/search_papers.py --source pubmed --days 60

# Search specific category
python3 scripts/papers/search_papers.py --category host_genomics
```

**Options:**
- `--source`: `pubmed`, `pmc`, `biorxiv`, or `all` (default)
- `--days`: Number of days to search back (default: 30)
- `--category`: Query category - `core`, `host_genomics`, `species`, `evolution`, or `all`

**Output:** Creates `scripts/papers/new_papers.json` with found papers.

### `auto_merge_review.py` (D87)

LLM-gated merge review for candidate batches (snowball/search output).
Each candidate answers explicit confirmation questions via muse-glimmer
(Q1 relevance — with a verbatim title-quote the program verifies, Q2 source
type — research/preprint/review/report only, Q3 scope), duplicates are
removed deterministically (title-similarity >= 0.8, first-seen wins), and
only accepted papers reach `merge_papers.py --all`. Rejections are logged to
`auto_merge_rejected.json` with reasons. Resume-safe via `auto_merge_log.json`.

```bash
pixi run python scripts/papers/auto_merge_review.py            # dry run
pixi run python scripts/papers/auto_merge_review.py --apply    # merge accepted
```

### `clade_discovery.py` (D91)

Continuously detects and classifies genotype/clade/subtype designations.
Broad scan → persistent registry → Muse LLM verification → alerts.
Wired into `campaign.py connections` phase.

```bash
pixi run python scripts/papers/clade_discovery.py            # scan only
pixi run python scripts/papers/clade_discovery.py --llm      # + verify novel
pixi run python scripts/papers/clade_discovery.py --check    # registry report
```

### `merge_papers.py`

Reviews and merges new papers into the main database.

```bash
# Show list of new papers
python3 scripts/papers/merge_papers.py

# Interactive review (approve/skip each paper)
python3 scripts/papers/merge_papers.py --review

# Add all new papers without review
python3 scripts/papers/merge_papers.py --all

# Add specific papers by index
python3 scripts/papers/merge_papers.py --ids 0,2,5

# Dry run (show what would be added)
python3 scripts/papers/merge_papers.py --all --dry-run
```

**Features:**
- Automatic ID generation
- Category assignment
- Topic extraction
- Species link generation
- Archives processed papers

### `update_papers.sh`

Convenience wrapper that runs search and shows next steps.

```bash
# Search last 30 days (default)
./scripts/papers/update_papers.sh

# Search last 60 days
./scripts/papers/update_papers.sh 60
```

## Search Categories

The search uses multiple query categories:

| Category | Focus |
|----------|-------|
| `core` | General H5N1/HPAI wild bird papers |
| `host_genomics` | ANP32, Mx, IFITM, RIG-I, MDA5, susceptibility |
| `species` | Waterfowl, raptors, seabirds, corvids, mammals |
| `evolution` | Reassortment, PB2 mutations, receptor binding |

## Duplicate Detection

Papers are checked for duplicates against the existing database using:
1. DOI matching
2. URL matching
3. Normalized title matching (case-insensitive, punctuation-removed)

## File Structure

```
scripts/papers/
├── README.md              # This file
├── search_papers.py       # Search script
├── merge_papers.py        # Merge script
├── update_papers.sh       # Convenience wrapper
├── new_papers.json        # Latest search results (temporary)
├── search_log.json        # Search history log
└── archive/               # Archived search results
    └── new_papers_YYYYMMDD_HHMMSS.json
```

## Data Files

| File | Location | Description |
|------|----------|-------------|
| `papers.json` | `web/public/data/` | Main papers database |
| `mammals.json` | `web/public/data/` | Mammal species data |
| `species_index.json` | `web/public/data/` | Bird species index |

## Workflow

1. **Search**: Run `search_papers.py` to find new papers
2. **Review**: Use `merge_papers.py --review` to approve papers
3. **Enhance**: Manually add summaries and "cited for" text
4. **Links**: Species links are auto-generated during merge

## Manual Paper Addition

To manually add a paper, edit `web/public/data/papers.json`:

```json
{
  "id": "authorYYYY_topic",
  "title": "Full paper title",
  "authors": "Author A, Author B, et al.",
  "journal": "Journal Name",
  "year": 2024,
  "doi": "10.1234/example",
  "url": "https://...",
  "topics": ["H5N1", "Wild Birds", "Topic"],
  "category": "Wild Birds",
  "summary": "Brief summary of key findings...",
  "cited_for": "What we cite this paper for"
}
```

Then run `python3 scripts/add_species_links.py` to update species links.

## API Rate Limits

- PubMed/PMC: 3 requests/second (script includes delays)
- bioRxiv: No documented limit (script includes delays)

## Troubleshooting

**No results found:**
- Try increasing `--days` parameter
- Check internet connection
- Verify NCBI API is accessible

**Duplicate not detected:**
- Titles may differ between preprint and publication
- DOIs may be missing
- Manually check and skip during review
