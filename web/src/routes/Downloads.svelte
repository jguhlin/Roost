<script>
  import { t } from '../lib/stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { formatBytes } from '../lib/utils/format.js';
  import SourceBadge from '../lib/components/common/SourceBadge.svelte';

  // Available downloads. Sizes and record counts are NEVER hardcoded:
  //  - size comes from a live HEAD request (exact, on any static host)
  //  - records comes from stats.json (regenerated on every data export)
  const baseDownloads = [
    {
      name: 'genes.parquet',
      description: 'Gene panel — one row per gene (curated + literature corpus + genome-annotation): symbol, name, category, host/viral kind, evidence scope, tier, corpus paper count, aliases, and per-gene presence counts. (Parquet opens in DuckDB, pandas/polars, R arrow, and Excel via the Parquet import.)',
      url: 'data/genes.parquet',
      format: 'Parquet',
    },
    {
      name: 'detections.parquet',
      description: 'All HPAI detection records (birds + mammals) with normalized fields',
      format: 'Parquet',
      url: 'data/detections.parquet',
      schema: 'detections',
      recordsFrom: (s) => s.detections,
    },
    {
      name: 'species.parquet',
      description: 'Species profiles with detection counts, genome info, and mortality phenotype',
      format: 'Parquet',
      url: 'data/species.parquet',
      schema: 'species',
      recordsFrom: (s) => s.species,
    },
    {
      name: 'detections.geojson',
      description: 'Georeferenced detection points for mapping',
      format: 'GeoJSON',
      url: 'data/geojson/detections.geojson',
      recordsFrom: (s) => s.georeferenced,
    },
    {
      name: 'detections_by_country.geojson',
      description: 'Detection counts aggregated by country',
      format: 'GeoJSON',
      url: 'data/geojson/detections_by_country.geojson',
    },
    {
      name: 'detections_by_species.geojson',
      description: 'Detection counts aggregated by species',
      format: 'GeoJSON',
      url: 'data/geojson/detections_by_species.geojson',
    },
    {
      name: 'hotspots.geojson',
      description: 'High-density detection clusters (1.0° grid)',
      format: 'GeoJSON',
      url: 'data/geojson/hotspots.geojson',
    },
    {
      name: 'species_index.json',
      description: 'Compact species list for search/autocomplete (birds + mammals)',
      format: 'JSON',
      url: 'data/species_index.json',
      recordsFrom: (s) => s.searchable_species,
    },
    {
      name: 'stats.json',
      description: 'Aggregate statistics for homepage display',
      format: 'JSON',
      url: 'data/stats.json'
    },
    {
      name: 'og_matrix.parquet',
      description: 'Orthogroup × species copy-number matrix from the OrthoFinder 463-bird run (root-corrected): dense long format (og, of_id, copies) covering all 40,494 orthogroups × 463 species. Query with DuckDB/pandas; join of_id via the species map below.',
      format: 'Parquet',
      url: 'data/og_matrix.parquet',
      recordsFrom: (s) => s.orthogroups,
    },
    {
      name: 'orthofinder_gene_to_og.tsv',
      description: 'Panel-gene → orthogroup mapping: symbol, tier, category, hit counts, primary orthogroup + vote fraction, top orthogroups, confidence tier, and chicken cross-check (799 mapped genes → 720 orthogroups).',
      format: 'TSV',
      url: 'data/orthofinder_gene_to_og.tsv',
      recordsFrom: (s) => s.panel_genes_mapped,
    },
    {
      name: 'orthofinder_species_map.json',
      description: 'Species map for the OrthoFinder run: of_id (0–462) → scientific name, assembly accession, leaf label, plus the root-corrected species tree ordering.',
      format: 'JSON',
      url: 'data/orthofinder/species_map.json',
      recordsFrom: (s) => s.og_species,
    },
    {
      name: 'synteny_blocks.json',
      description: 'Conserved micro-synteny blocks (recurring co-located core gene-sets) with per-species tracks from annotation coordinates; curated blocks additionally carry current-annotation flanking genes (flanks.json).',
      format: 'JSON',
      url: 'data/synteny/blocks.json',
      recordsFrom: (s) => s.synteny_blocks,
    },
    {
      name: 'iucn_status.json',
      description: 'IUCN Red List category per species (LC/NT/VU/EN/CR/EW/EX/DD) from Wikidata P141.',
      // counts injected from stats.json — never hardcoded prose
      descParams: (s) => ({ a: s.iucn_species, b: s.species }),
      format: 'JSON',
      url: 'data/species/iucn_status.json',
      recordsFrom: (s) => s.iucn_species,
    },
    {
      name: 'anp32_comparison.json',
      description: 'ANP32 species-barrier comparison: the avian 33-aa insert measured from protein sequences across 447 birds and every HPAI-confirmed mammal with a genome (per-paralog lengths, sequences, junction sites).',
      format: 'JSON',
      url: 'data/anp32/comparison.json',
      recordsFrom: (s) => s.anp32_species,
    },
    {
      name: 'panel_refs.json (BLAST db)',
      description: 'Static-BLAST reference proteins: 799 genes × key species (chicken, mallard, turkey, zebra finch, quail, swan goose, eagle, kiwi). Searchable in-browser at #/blast (WASM blastp, no upload).',
      format: 'JSON',
      url: 'data/blast/panel_refs.json',
      recordsFrom: (s) => s.blast_sequences,
    },
  ];

  let downloads = $state(baseDownloads);
  let statsData = $state(null);

  onMount(async () => {
    // Record counts from stats.json (regenerated on every export)
    let stats = {};
    try {
      const r = await fetch('data/stats.json');
      if (r.ok) stats = await r.json();
    } catch { /* sizes/records simply stay hidden */ }
    downloads = baseDownloads.map((d) => ({
      ...d,
      records: d.recordsFrom ? d.recordsFrom(stats) : d.records,
    }));
    statsData = stats;
    // Exact sizes from live HEAD requests — always current, any host
    await Promise.all(downloads.map(async (d, i) => {
      try {
        const r = await fetch(d.url, { method: 'HEAD' });
        const len = Number(r.headers.get('content-length'));
        if (len > 0) downloads[i] = { ...downloads[i], size: len };
      } catch { /* keep no size */ }
    }));
  });

  // Data sources with attribution
  const sources = [
    { id: 'aphis', name: 'USDA APHIS', description: 'US wild bird surveillance', license: 'Public Domain', url: 'https://www.aphis.usda.gov/aphis/ourfocus/animalhealth/animal-disease-information/avian/avian-influenza/2022-hpai' },
    { id: 'canada_cwhc', name: 'Canada CWHC', description: 'Canadian Wildlife Health Cooperative', license: 'Open Government License', url: 'https://www.cwhc-rcsf.ca/' },
    { id: 'uk_defra', name: 'UK DEFRA/APHA', description: 'UK animal health surveillance', license: 'Open Government License', url: 'https://www.gov.uk/government/collections/avian-influenza-bird-flu' },
    { id: 'ireland_dafm', name: 'Ireland DAFM', description: 'Department of Agriculture, Food and the Marine', license: 'Public Sector Information', url: 'https://www.gov.ie/en/publication/e5a5b-avian-influenza/' },
    { id: 'acap_hpai', name: 'ACAP HPAI Database', description: 'Agreement on Conservation of Albatrosses and Petrels', license: 'CC BY', url: 'https://www.acap.aq/' },
    { id: 'empresi', name: 'FAO EMPRES-i', description: 'Emergency Prevention System', license: 'FAO Open Data', url: 'https://empres-i.fao.org/' }
  ];

  // Example queries (titles translated; code stays in its language)
  const examples = [
    {
      title: t('downloads.ex.python'),
      language: 'python',
      code: `import pandas as pd

# Load detections
df = pd.read_parquet('detections.parquet')
print(f"Total detections: {len(df)}")

# Filter to recent US detections
us_2024 = df[(df['country'] == 'United States') & (df['date'] >= '2024-01-01')]`
    },
    {
      title: t('downloads.ex.duckdb'),
      language: 'sql',
      code: `-- Top species by detection count
SELECT scientific_name, COUNT(*) as n
FROM 'detections.parquet'
GROUP BY scientific_name
ORDER BY n DESC
LIMIT 10;

-- Detections by country and year
SELECT country, EXTRACT(YEAR FROM date) as year, COUNT(*) as n
FROM 'detections.parquet'
GROUP BY country, year
ORDER BY year DESC, n DESC;`
    },
    {
      title: t('downloads.ex.r'),
      language: 'r',
      code: `library(arrow)
library(dplyr)

# Species profiles + susceptibility scores (join on scientific_name;
# susceptibility.parquet ships score/class columns only — Phase 3)
species <- read_parquet("species.parquet")
susc <- read_parquet("susceptibility.parquet")

high_risk <- species %>%
  inner_join(susc, by = "scientific_name") %>%
  filter(!is.na(genome_accession), susceptibility_class %in% c("High", "highly_susceptible"))`
    }
  ];
</script>

<svelte:head><title>{t('routes_Downloads.downloads') || 'Downloads'} — Roost</title></svelte:head>

<div class="space-y-8">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{t('routes_Downloads.downloads')}</h1>
    <p class="text-gray-600 dark:text-gray-300">
      {t('downloads.subtitle') || 'Bulk data exports with full provenance documentation. All files are regenerated from primary sources.'}
    </p>
  </div>

  <!-- Download files -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{t('downloads.available.files')}</h2>
    </div>
    <div class="divide-y divide-gray-100 dark:divide-gray-700">
      {#each downloads as file}
        <div class="px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-3">
              <span class="font-mono text-sm font-medium text-gray-900 dark:text-white">{file.name}</span>
              <span class="px-2 py-0.5 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                {file.format}
              </span>
              {#if file.records}
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {t('downloads.records.count', { n: file.records.toLocaleString() })}
                </span>
              {/if}
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{t('downloads.desc.' + file.name, file.descParams && statsData ? file.descParams(statsData) : undefined)}</p>
          </div>
          <div class="flex items-center gap-4 ml-4">
            <span class="text-sm text-gray-500 dark:text-gray-400">{formatBytes(file.size)}</span>
            <a
              href={file.url}
              download
              class="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              {t('downloads.download')}
            </a>
          </div>
        </div>
      {/each}
    </div>
  </div>

  <!-- Code Examples -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{t('downloads.example.usage')}</h2>
    </div>
    <div class="divide-y divide-gray-100 dark:divide-gray-700">
      {#each examples as example}
        <div class="px-6 py-4">
          <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-2">{example.title}</h3>
          <pre class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm"><code>{example.code}</code></pre>
        </div>
      {/each}
    </div>
  </div>

  <!-- Data Sources -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{t('downloads.data.sources.attribution')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('downloads.cite.orig') || 'Data is aggregated from multiple public surveillance databases. Please cite original sources when using this data.'}
      </p>
    </div>
    <div class="divide-y divide-gray-100 dark:divide-gray-700">
      {#each sources as source}
        <div class="px-6 py-4 flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3">
              <SourceBadge source={source.id} />
              <span class="text-sm text-gray-700 dark:text-gray-300">{t('downloads.tool.' + source.name) || source.description}</span>
            </div>
            <div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {t('downloads.license.label', { license: source.license })}
            </div>
          </div>
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            class="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
          >
            {t('downloads.source.link')}
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      {/each}
    </div>
  </div>

  <!-- Citation -->
  <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
    <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">{t('downloads.how.to.cite')}</h3>
    <p class="text-sm text-gray-600 dark:text-gray-300 font-mono bg-white dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700">
      Roost: Avian Influenza Host Genomics Resource. [Dataset]. Retrieved from https://josephguhlin.com/Roost/. Accessed {new Date().toISOString().split('T')[0]}.
    </p>
    <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
      {t('downloads.cite.primary') || 'Please also cite the primary data sources as listed above.'}
    </p>
  </div>
</div>
