#!/usr/bin/env python3
"""
Add mammal genome data for H5N1-affected species.

Downloads genome metadata from NCBI for key mammal species affected by H5N1
and adds them to the genomes.parquet file.
"""

import json
import subprocess
from pathlib import Path
import polars as pl

ROOST_DIR = Path(__file__).parent.parent
DATA_DIR = ROOST_DIR / "data"
WEB_DATA_DIR = ROOST_DIR / "web" / "public" / "data"

# H5N1-affected mammals to add
H5N1_MAMMALS = [
    "Mirounga leonina",       # Southern elephant seal
    "Halichoerus grypus",     # Gray seal
    "Phoca vitulina",         # Harbor seal
    "Zalophus californianus", # California sea lion
    "Arctocephalus gazella",  # Antarctic fur seal
    "Arctocephalus forsteri", # Long-nosed fur seal (already have but verify)
    "Leptonychotes weddellii", # Weddell seal
    "Callorhinus ursinus",    # Northern fur seal
    "Eumetopias jubatus",     # Steller sea lion
]

def get_genome_from_ncbi(species_name: str) -> dict | None:
    """Query NCBI datasets for genome info."""
    try:
        result = subprocess.run(
            ["pixi", "run", "datasets", "summary", "genome", "taxon", species_name, "--as-json-lines"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            data = json.loads(line)
            reports = data.get('reports', [])
            if not reports:
                continue

            # Find best assembly (prefer RefSeq + Chromosome)
            best = None
            best_score = -1
            for r in reports:
                acc = r.get('accession', '')
                level = r.get('assembly_info', {}).get('assembly_level', '')

                # Score: RefSeq=10, Chromosome=5, Scaffold=2, Contig=1
                score = 0
                if acc.startswith('GCF_'):
                    score += 10
                if level == 'Chromosome':
                    score += 5
                elif level == 'Scaffold':
                    score += 2
                elif level == 'Contig':
                    score += 1

                if score > best_score:
                    best_score = score
                    best = r

            if best:
                org = best.get('organism', {})
                asm = best.get('assembly_info', {})
                stats = best.get('assembly_stats', {})
                return {
                    'accession': best.get('accession'),
                    'organism_name': org.get('organism_name'),
                    'organism_common_name': org.get('common_name'),
                    'taxon_id': org.get('tax_id'),
                    'assembly_level': asm.get('assembly_level'),
                    'contig_n50': stats.get('contig_n50'),
                    'scaffold_n50': stats.get('scaffold_n50'),
                    'total_length': stats.get('total_sequence_length'),
                    'annotation_status': 'Full annotation' if best.get('annotation_info') else None,
                    'is_representative': asm.get('refseq_category') == 'representative genome',
                }
    except Exception as e:
        print(f"  Error querying {species_name}: {e}")
    return None


def main():
    print("=" * 60)
    print("ADD MAMMAL GENOMES")
    print("=" * 60)

    # Load existing genomes
    genome_file = DATA_DIR / "genomes.parquet"
    if genome_file.exists():
        genomes_df = pl.read_parquet(genome_file)
        existing = set(genomes_df['organism_name'].to_list())
        print(f"\nExisting genomes: {len(genomes_df)}")
    else:
        genomes_df = None
        existing = set()

    # Query NCBI for each mammal
    new_genomes = []
    for species in H5N1_MAMMALS:
        if species in existing:
            print(f"\n{species}: already in database")
            continue

        print(f"\n{species}: querying NCBI...")
        genome = get_genome_from_ncbi(species)
        if genome:
            print(f"  Found: {genome['accession']} ({genome['assembly_level']})")
            new_genomes.append(genome)
        else:
            print(f"  No genome found")

    if not new_genomes:
        print("\nNo new genomes to add")
        return

    # Create DataFrame for new genomes
    new_df = pl.DataFrame(new_genomes)

    # Merge with existing
    if genomes_df is not None:
        # Ensure schema compatibility
        for col in genomes_df.columns:
            if col not in new_df.columns:
                new_df = new_df.with_columns(pl.lit(None).alias(col))
        new_df = new_df.select(genomes_df.columns)
        merged_df = pl.concat([genomes_df, new_df])
    else:
        merged_df = new_df

    # Save
    merged_df.write_parquet(genome_file)
    print(f"\nSaved {len(merged_df)} genomes to {genome_file}")

    # Copy to web
    web_genome_file = WEB_DATA_DIR / "genomes.parquet"
    merged_df.write_parquet(web_genome_file)

    print(f"\nAdded {len(new_genomes)} mammal genomes:")
    for g in new_genomes:
        print(f"  {g['organism_name']}: {g['accession']}")


if __name__ == "__main__":
    main()
