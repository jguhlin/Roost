<script>
  import { t } from '../lib/stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { db, dbStore } from '../lib/stores/db.js';
  import { navigate, getRoute, updateParams, subscribe as routerSubscribe } from '../lib/stores/router.js';
  import { formatNumber, formatN50, getAssemblyLevelInfo } from '../lib/utils/format.js';
  import { ncbi } from '../lib/utils/urls.js';

  // State
  let species = $state([]);
  let loading = $state(true);
  let activeTab = $state('detected');
  let assemblyFilter = $state('');
  let annotationFilter = $state('');
  let orderFilter = $state('');
  let searchText = $state('');
  let taxaFilter = $state('all'); // 'all' | 'aves' | 'mammals'
  let orders = $state([]);

  // --- URL state (#/genomes?tab=undetected&assembly=Chromosome&annotated=yes&
  //     order=Anseriformes) — shareable views, same pattern as the other
  //     browsers. Absent param = its default; values are whitelisted/escaped
  //     because they are interpolated into SQL.
  let urlSyncReady = $state(false);

  const applyParams = (p = {}) => {
    activeTab = p.tab === 'undetected' ? 'undetected' : 'detected';
    assemblyFilter = ['Chromosome', 'Scaffold', 'Contig', 'Complete Genome'].includes(p.assembly) ? p.assembly : '';
    annotationFilter = ['yes', 'no'].includes(p.annotated) ? p.annotated : '';
    orderFilter = (p.order || '').replace(/'/g, "''");
    searchText = p.q || '';
    taxaFilter = ['all', 'aves', 'mammals'].includes(p.taxa) ? p.taxa : 'all';
  };

  const applyRoute = route => {
    if (route.page === 'genomes' && urlSyncReady) applyParams(route.params || {});
  };

  let summary = $state(null); // catalog-wide counts
  let breakdown = $state(null); // detailed dimensions
  let showBreakdown = $state(false);

  onMount(async () => {
    applyParams(getRoute()?.params || {});
    await loadData();
    try {
      const r = await db.query(`
        SELECT count(*) AS total,
               count(*) FILTER (WHERE is_aves) AS avian,
               count(*) FILTER (WHERE NOT is_aves) AS mammal,
               count(DISTINCT organism_name) AS species,
               count(*) FILTER (WHERE assembly_level = 'Chromosome') AS chromosome,
               count(*) FILTER (WHERE assembly_level = 'Scaffold') AS scaffold,
               count(*) FILTER (WHERE assembly_level = 'Contig') AS contig,
               count(*) FILTER (WHERE assembly_level = 'Complete Genome') AS complete,
               count(*) FILTER (WHERE annotation_status IS NOT NULL) AS annotated,
               count(*) FILTER (WHERE accession LIKE 'GCF%') AS refseq,
               count(*) FILTER (WHERE accession LIKE 'GCA%') AS genbank
        FROM genomes`);
      summary = r[0];
      // normalize BigInt for JSON-safe use — BEFORE any await, or the
      // reactive render sees raw BigInts and throws on arithmetic
      for (const k of Object.keys(summary)) summary[k] = Number(summary[k]);

      // Cross-cutting details: RefSeq↔GenBank mirrors, multi-assembly
      // species, and detected-species overlap — each needs its own GROUP BY
      const [mirrors, multi, detected] = await Promise.all([
        db.query(`
          WITH bases AS (
            SELECT regexp_replace(regexp_replace(accession, '^GC[FA]_', ''), '\\.\\d+$', '') AS base,
                   accession LIKE 'GCF%' AS is_refseq
            FROM genomes)
          SELECT count(*) AS n FROM (
            SELECT base FROM bases
            GROUP BY base
            HAVING count(*) FILTER (WHERE is_refseq) > 0
               AND count(*) FILTER (WHERE NOT is_refseq) > 0)`),
        db.query(`
          SELECT count(*) FILTER (WHERE n > 1) AS multi_species,
                 max(n) AS max_per_species
          FROM (SELECT organism_name, count(*) AS n FROM genomes GROUP BY organism_name)`),
        db.query(`
          SELECT count(*) AS n FROM (
            SELECT DISTINCT g.organism_name
            FROM genomes g
            JOIN species s ON s.scientific_name = g.organism_name
            WHERE s.detection_records > 0)`),
      ]);
      breakdown = {
        mirrorPairs: Number(mirrors[0]?.n || 0),
        multiSpecies: Number(multi[0]?.multi_species || 0),
        maxPerSpecies: Number(multi[0]?.max_per_species || 0),
        detectedSpecies: Number(detected[0]?.n || 0),
      };
    } catch { /* counts are cosmetic */ }
    return routerSubscribe(applyRoute);
  });

  async function loadData() {
    loading = true;
    try {
      await dbStore.loadSpecies();
      await dbStore.loadGenomes();

      // Unique orders: detected species + the genome catalog's own taxonomy
      const orderResults = await db.query(`
        SELECT DISTINCT tax_order as ord FROM genomes
        WHERE tax_order IS NOT NULL AND tax_order != ''
        ORDER BY tax_order
      `);
      orders = orderResults.map(r => r.ord);

      await loadSpecies();
    } catch (e) {
      console.error('Failed to load genomes:', e);
    } finally {
      loading = false;
      urlSyncReady = true;
    }
  }

  async function loadSpecies() {
    // The undetected tab lists species that have genomes in the assembly
    // catalog but NO entry in the detected-species table (species.parquet
    // only covers HPAI-detected species). Anti-join against genomes.
    if (activeTab === 'undetected') {
      let where = ['g.assembly_level IS NOT NULL'];
      if (assemblyFilter) where.push(`g.assembly_level = '${assemblyFilter}'`);
      if (annotationFilter === 'yes') where.push('g.annotation_status IS NOT NULL');
      else if (annotationFilter === 'no') where.push('g.annotation_status IS NULL');
      if (orderFilter) where.push(`g.tax_order = '${orderFilter}'`);
      if (taxaFilter === 'aves') where.push('g.is_aves = true');
      else if (taxaFilter === 'mammals') where.push('(g.is_aves = false OR g.is_aves IS NULL)');
      if (searchText) {
        const q = searchText.replace(/'/g, "''").toLowerCase();
        where.push(`(lower(g.organism_name) LIKE '%${q}%' OR lower(coalesce(g.organism_common_name, '')) LIKE '%${q}%')`);
      }
      let sql = `SELECT g.organism_name as scientific_name,
                        g.organism_common_name as primary_common_name,
                        g.tax_order as "order", g.is_aves,
                        g.assembly_level, g.scaffold_n50, g.contig_n50,
                        g.total_length, g.annotation_status as has_annotation,
                        g.is_representative, g.accession as genome_accession,
                        CAST(0 AS BIGINT) as detection_records, CAST(0 AS BIGINT) as detection_count
                 FROM genomes g
                 ANTI JOIN species s ON s.scientific_name = g.organism_name
                 WHERE ${where.join(' AND ')}
                 QUALIFY row_number() OVER (PARTITION BY g.organism_name ORDER BY g.scaffold_n50 DESC NULLS LAST) = 1
                 ORDER BY g.scaffold_n50 DESC NULLS LAST LIMIT 100`;
      species = await db.query(sql);
      return;
    }

    let sql = 'SELECT * FROM species WHERE genome_accession IS NOT NULL AND detection_records > 0';

    // Assembly level filter
    if (assemblyFilter) {
      sql += ` AND assembly_level = '${assemblyFilter}'`;
    }

    // Annotation filter
    if (annotationFilter === 'yes') {
      sql += ' AND has_annotation = true';
    } else if (annotationFilter === 'no') {
      sql += ' AND (has_annotation = false OR has_annotation IS NULL)';
    }

    // Order filter (value escaped at applyParams; belt-and-braces here)
    if (orderFilter) {
      sql += ` AND "order" = '${orderFilter.replace(/'/g, "''")}'`;
    }

    // Taxa filter (detected tab: mammals have no order, filter on genome table join)
    if (taxaFilter !== 'all') {
      // species table has no is_aves; join genomes for the flag
      sql += taxaFilter === 'aves'
        ? ` AND scientific_name IN (SELECT organism_name FROM genomes WHERE is_aves)`
        : ` AND scientific_name IN (SELECT organism_name FROM genomes WHERE NOT is_aves)`;
    }

    // Text search (scientific + common name)
    if (searchText) {
      const q = searchText.replace(/'/g, "''").toLowerCase();
      sql += ` AND (lower(scientific_name) LIKE '%${q}%' OR lower(coalesce(common_name, '')) LIKE '%${q}%')`;
    }

    // Sort
    sql += ' ORDER BY detection_records DESC NULLS LAST, scaffold_n50 DESC NULLS LAST LIMIT 100';

    species = await db.query(sql);
  }

  // React to filter changes — reload + keep the URL shareable
  // (orderFilter is included; it was silently missing from the URL before)
  $effect(() => {
    void activeTab; void assemblyFilter; void annotationFilter; void orderFilter;
    void searchText; void taxaFilter;
    if (loading || !urlSyncReady) return;
    // Debounce text search so typing doesn't re-query per keystroke
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      loadSpecies();
      updateParams({
        tab: activeTab !== 'detected' ? activeTab : null,
        assembly: assemblyFilter || null,
        annotated: annotationFilter || null,
        order: orderFilter || null,
        q: searchText || null,
        taxa: taxaFilter !== 'all' ? taxaFilter : null,
      });
    }, 300);
  });
  let searchTimer;

  function clearFilters() {
    assemblyFilter = '';
    annotationFilter = '';
    orderFilter = '';
    searchText = '';
    taxaFilter = 'all';
  }

  const tabs = [
    { id: 'detected', label: 'Detected + Genome', description: 'Species with both HPAI detections and genome assemblies' },
    { id: 'undetected', label: 'Genome Only', description: 'Species with genomes but no confirmed cases' }
  ];
</script>

<svelte:head><title>{t('genomes_page.genome.browser') || 'Genome browser'} — Roost</title></svelte:head>

<div class="space-y-6">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('genomes_page.genome.browser')}</h1>
    <p class="text-gray-600 dark:text-gray-300 mt-1">
      {t('genomes.subtitle') || 'Find species for comparative genomics analysis'}
    </p>
    {#if summary}
      {@const pct = (n) => Math.round(100 * n / summary.total) + '%'}
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mt-3">
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2">
          <div class="text-lg font-semibold text-gray-900 dark:text-white leading-tight">{summary.species.toLocaleString()}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{t('genomes_page.species.with.assemblies')}</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2" title="{t('genomes.ncbi.title') || 'NCBI catalog entries — many species have multiple submissions (breeds, versions)'}; some are RefSeq↔GenBank mirrors of the same assembly">
          <div class="text-lg font-semibold text-gray-900 dark:text-white leading-tight">{summary.total.toLocaleString()}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{t('genomes_page.total.assemblies')}</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2">
          <div class="text-lg font-semibold text-gray-900 dark:text-white leading-tight">{summary.avian.toLocaleString()} <span class="text-sm font-normal text-gray-500 dark:text-gray-400">/</span> {summary.mammal.toLocaleString()}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{t('genomes_page.avian.mammal.assemblies')}</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2">
          <div class="text-lg font-semibold text-gray-900 dark:text-white leading-tight">{(summary.chromosome + summary.complete).toLocaleString()} <span class="text-sm font-normal text-gray-500 dark:text-gray-400">{pct(summary.chromosome + summary.complete)}</span></div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{t('genomes_page.chromosomelevel')}</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2">
          <div class="text-lg font-semibold text-gray-900 dark:text-white leading-tight">{summary.annotated.toLocaleString()} <span class="text-sm font-normal text-gray-500 dark:text-gray-400">{pct(summary.annotated)}</span></div>
          <div class="text-xs text-gray-500 dark:text-gray-400">{t('genomes_page.annotated')}</div>
        </div>
      </div>
      <button
        class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
        onclick={() => showBreakdown = !showBreakdown}>
        {showBreakdown ? '▾' : '▸'} {t('genomes.catalog.breakdown') || 'Catalog breakdown'}
      </button>
      {#if showBreakdown && summary && breakdown}
        {@const pct = (n) => (100 * n / summary.total).toFixed(1) + '%'}
        <div class="mt-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-sm divide-y divide-gray-100 dark:divide-gray-700">
          <div class="pb-2">
            <div class="font-medium text-gray-900 dark:text-white mb-1">{t('genomes.by_assembly_level')} <span class="font-normal text-gray-500 dark:text-gray-400 text-xs">({t('genomes.partitions_n', {n: summary.total.toLocaleString()})})</span></div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-x-4 text-gray-600 dark:text-gray-300">
              <span>{t('genomes.opt.chromosome')}: <strong>{summary.chromosome.toLocaleString()}</strong> ({pct(summary.chromosome)})</span>
              <span>{t('genomes.opt.scaffold')}: <strong>{summary.scaffold.toLocaleString()}</strong> ({pct(summary.scaffold)})</span>
              <span>{t('genomes.opt.contig')}: <strong>{summary.contig.toLocaleString()}</strong> ({pct(summary.contig)})</span>
              <span>{t('genomes.opt.complete')}: <strong>{summary.complete.toLocaleString()}</strong> ({pct(summary.complete)})</span>
            </div>
          </div>
          <div class="py-2">
            <div class="font-medium text-gray-900 dark:text-white mb-1">{t('genomes.by_accession')} <span class="font-normal text-gray-500 dark:text-gray-400 text-xs">({t('genomes.partitions_catalog')})</span></div>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 text-gray-600 dark:text-gray-300">
              <span>RefSeq (GCF_): <strong>{summary.refseq.toLocaleString()}</strong> ({pct(summary.refseq)})</span>
              <span>GenBank (GCA_): <strong>{summary.genbank.toLocaleString()}</strong> ({pct(summary.genbank)})</span>
              <span class="text-gray-500 dark:text-gray-400">{t('genomes.of_which')} <strong>{breakdown.mirrorPairs.toLocaleString()}</strong>{t('routes.genomes.pairs.are.the.same') || 'pairs are the same underlying assembly submitted under both accessions'}</span>
            </div>
          </div>
          <div class="py-2">
            <div class="font-medium text-gray-900 dark:text-white mb-1">{t('genomes.by_annotation')} <span class="font-normal text-gray-500 dark:text-gray-400 text-xs">({t('genomes.partitions_catalog')})</span></div>
            <div class="grid grid-cols-2 gap-x-4 text-gray-600 dark:text-gray-300">
              <span>{t('genomes.annotated')}: <strong>{summary.annotated.toLocaleString()}</strong> ({pct(summary.annotated)})</span>
              <span>{t('genomes.no_annotation')}: <strong>{(summary.total - summary.annotated).toLocaleString()}</strong> ({pct(summary.total - summary.annotated)})</span>
            </div>
          </div>
          <div class="pt-2">
            <div class="font-medium text-gray-900 dark:text-white mb-1">{t('genomes.per_species_depth')} <span class="font-normal text-gray-500 dark:text-gray-400 text-xs">({t('genomes.why_species_to_assemblies', {a: summary.total.toLocaleString(), s: summary.species.toLocaleString()})})</span></div>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-4 text-gray-600 dark:text-gray-300">
              <span>{t('routes.genomes.species.with.single.assembly') || 'Species with a single assembly:'}<strong>{(summary.species - breakdown.multiSpecies).toLocaleString()}</strong></span>
              <span>{t('routes.genomes.species.with.multiple') || 'Species with multiple:'}<strong>{breakdown.multiSpecies.toLocaleString()}</strong> (up to {breakdown.maxPerSpecies} for one species)</span>
              <span>{t('routes.genomes.species.also.hpai.detected') || 'Species also HPAI-detected:'}<strong>{breakdown.detectedSpecies.toLocaleString()}</strong> of {summary.species.toLocaleString()}</span>
            </div>
          </div>
        </div>
      {/if}
    {/if}
  </div>

  <!-- Tabs -->
  <div class="flex border-b border-gray-200 dark:border-gray-700">
    {#each tabs as tab}
      <button
        onclick={() => activeTab = tab.id}
        class="px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors {activeTab === tab.id ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
      >
        {t('genomes.tab.label.' + tab.id) || tab.label}
      </button>
    {/each}
  </div>

  <!-- Tab description -->
  <p class="text-sm text-gray-500 dark:text-gray-400">
    {t('genomes.tab.' + activeTab) || tabs.find(x => x.id === activeTab)?.description}
  </p>

  <!-- Filters -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
    <div class="flex flex-wrap gap-4 items-center">
      <!-- Assembly level -->
      <!-- Text search -->
      <div>
        <input
          type="text"
          bind:value={searchText}
          placeholder={t('search.placeholder.species') || 'Search species…'}
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 w-52"
        />
      </div>

      <!-- Assembly level -->
      <!-- Taxa: all / birds / mammals -->
      <div class="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600" role="group" aria-label={t('tip.genomes.taxa') || 'Taxa filter'}>
        <button class="px-3 py-2 text-sm font-medium {taxaFilter === 'all' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}"
                onclick={() => taxaFilter = 'all'}>{t('genomes_page.all')}</button>
        <button class="px-3 py-2 text-sm font-medium border-l border-gray-300 dark:border-gray-600 {taxaFilter === 'aves' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}"
                onclick={() => taxaFilter = 'aves'}>{t('genomes_page.birds')}</button>
        <button class="px-3 py-2 text-sm font-medium border-l border-gray-300 dark:border-gray-600 {taxaFilter === 'mammals' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}"
                onclick={() => taxaFilter = 'mammals'} title="Mammalian spillover hosts">{t('genomes_page.mammals')}</button>
      </div>

      <!-- Assembly level -->
      <div>
        <select
          bind:value={assemblyFilter}
          aria-label={t('genomes_page.all.assembly.levels')}
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{t('genomes_page.all.assembly.levels')}</option>
          <option value="Chromosome">{t('genomes.opt.chromosome') || 'Chromosome'}</option>
          <option value="Scaffold">{t('genomes_page.scaffolded')}</option>
          <option value="Contig">{t('genomes_page.contigs')}</option>
          <option value="Complete Genome">{t('genomes_page.complete')}</option>
        </select>
      </div>

      <!-- Annotation -->
      <div>
        <select
          bind:value={annotationFilter}
          aria-label={t('genomes_page.all.annotation.status')}
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{t('genomes_page.all.annotation.status')}</option>
          <option value="yes">{t('routes_Genomes.annotated')}</option>
          <option value="no">{t('genomes_page.not.annotated')}</option>
        </select>
      </div>

      <!-- Order -->
      <div>
        <select
          bind:value={orderFilter}
          aria-label={t('genomes_page.all.orders')}
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{t('genomes_page.all.orders')}</option>
          {#each orders as order}
            <option value={order}>{order}</option>
          {/each}
        </select>
      </div>

      {#if assemblyFilter || annotationFilter || orderFilter || searchText || taxaFilter !== 'all'}
        <button
          onclick={clearFilters}
          class="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
        >
          {t('genomes.clear_filters')}
        </button>
      {/if}
    </div>
  </div>

  <!-- Results -->
  {#if loading}
    <div class="grid gap-4">
      {#each [1,2,3,4,5] as _}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 animate-pulse">
          <div class="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-2"></div>
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
        </div>
      {/each}
    </div>
  {:else if species.length === 0}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
      <svg class="w-12 h-12 mx-auto text-gray-500 dark:text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">{t('genomes_page.no.genomes.found')}</h3>
      <p class="text-gray-500 dark:text-gray-400 mb-4">
        {#if activeTab === 'detected' && taxaFilter === 'mammals'}
          Mammalian detections appear on the Map and in the Spread model, but species
          profiles currently cover birds only. Mammal assemblies are on the
          <button class="text-blue-600 dark:text-blue-400 hover:underline" onclick={() => { activeTab = 'undetected'; taxaFilter = 'mammals'; }}>{t('genomes_page.genome.only.tab')}</button>.
        {:else}
          Try adjusting your filters
        {/if}
      </p>
      <button
        onclick={clearFilters}
        class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        {t('genomes.clear_all_filters')}
      </button>
    </div>
  {:else}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <th class="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesFullPage.species')}</th>
            <th class="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesDetail.detections')}</th>
            <th class="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">{t('routes_Genomes.assembly')}</th>
            <th class="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">{t('routes_Genomes.level')}</th>
            <th class="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">N50</th>
            <th class="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesDetail.annotation')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          {#each species as sp}
            {@const levelInfo = getAssemblyLevelInfo(sp.assembly_level)}
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <td class="py-3 px-4">
                <button
                  onclick={() => navigate('species', sp.taxon_id || sp.scientific_name)}
                  class="text-left hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-400"
                >
                  <span class="font-medium text-gray-900 dark:text-white italic">{sp.scientific_name}</span>
                  {#if sp.is_aves === false}
                    <span class="ml-1.5 px-1.5 py-0.5 text-[10px] rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 font-medium" title={t('routes.genomes.mammal.potential.hpai.spillover') || 'Mammal — potential HPAI spillover host'}>{t('genomes_page.mammal')}</span>
                  {/if}
                  {#if sp.common_name || sp.primary_common_name}
                    <span class="text-gray-500 dark:text-gray-400 block text-xs">{sp.common_name || sp.primary_common_name}</span>
                  {/if}
                </button>
              </td>
              <td class="py-3 px-4">
                {#if sp.detection_records > 0}
                  <span class="px-2 py-0.5 text-xs rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300" title={t('species.card.detections.tip')}>
                    {formatNumber(sp.detection_records)}
                  </span>
                {:else}
                  <span class="text-gray-500 dark:text-gray-400">—</span>
                {/if}
              </td>
              <td class="py-3 px-4">
                <a
                  href={ncbi.assembly(sp.genome_accession)}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-600 dark:text-blue-400 hover:underline font-mono text-xs"
                >
                  {sp.genome_accession}
                </a>
              </td>
              <td class="py-3 px-4">
                <span class="px-2 py-0.5 text-xs rounded {levelInfo.color === 'green' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : levelInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
                  {levelInfo.label}
                </span>
              </td>
              <td class="py-3 px-4 font-mono text-xs text-gray-600 dark:text-gray-300">
                {formatN50(sp.scaffold_n50)}
              </td>
              <td class="py-3 px-4">
                {#if sp.has_annotation}
                  <span class="text-green-700 dark:text-green-400">{t('routes_Genomes.yes')}</span>
                {:else}
                  <span class="text-gray-500 dark:text-gray-400">{t('common.no')}</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if species.length >= 100}
      <p class="text-center text-sm text-gray-500 dark:text-gray-400">
        {t('genomes.showing.first') || 'Showing first 100 results. Use filters to narrow down.'}
      </p>
    {/if}
  {/if}
</div>
