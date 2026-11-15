<script>
  import { onMount } from 'svelte';
  import { db, dbStore } from '../lib/stores/db.js';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { announce } from '../lib/stores/a11y.svelte.js';
  import { subscribe as routerSubscribe, updateParams, getRoute } from '../lib/stores/router.js';
  import { formatNumber } from '../lib/utils/format.js';
  import SpeciesCard from '../lib/components/species/SpeciesCard.svelte';

  // State
  let species = $state([]);

  // a11y: announce the visible result count to screen readers when it settles
  // (loads and filter changes — polite live region, see lib/stores/a11y)
  let lastAnnouncedCount = $state(-1);
  $effect(() => {
    const n = species.length;
    if (n > 0 && n !== lastAnnouncedCount) {
      lastAnnouncedCount = n;
      announce(t('a11y.announce.species.results', { n }));
    }
  });
  let loading = $state(true);
  let searchQuery = $state('');
  let orderFilter = $state('');
  let sortBy = $state('detections');
  let orders = $state([]);
  let totalDetected = $state(0);
  let totalAll = $state(0);   // all searchable species (taxonomy)
  // IUCN status map (sci -> code) from data/species/iucn_status.json
  let iucnMap = $state(null);
  // conservation filter: threatened = VU/EN/CR/EW/EX
  let threatOnly = $state(false);
  const THREAT_CODES = new Set(['VU', 'EN', 'CR', 'EW', 'EX']);
  const passThreat = (list) => (threatOnly
    ? list.filter(s => THREAT_CODES.has(iucnMap?.get(s.scientific_name) || s.iucn))
    : list);
  let showAll = $state(false); // false = detected only (default)
  let classFilter = $state(''); // '' | Aves | Mammalia (D113)
  let loadSeq = 0;   // guards against out-of-order async loads (fast typing)
  let loadError = $state(null);

  // Get initial query from URL — shareable/reproducible views (D113+):
  // q, class (Aves|Mammalia), order, sort (detections|name|susceptibility),
  // all=1 (full taxonomy toggle). The URL is the source of truth on load;
  // afterwards state → URL via $effect, and SPA navigations back via
  // routerSubscribe → applyRoute (state matches → no-op, so no loops).
  let urlSyncReady = $state(false);

  onMount(() => {
    const p = getRoute()?.params || {};
    searchQuery = p.q || '';
    orderFilter = p.order || '';
    sortBy = ['name', 'susceptibility'].includes(p.sort) ? p.sort : 'detections';
    classFilter = ['Aves', 'Mammalia'].includes(p.class) ? p.class : '';
    showAll = p.all === '1';
    threatOnly = p.threat === '1';

    loadData();
    return routerSubscribe(applyRoute);
  });

  function applyRoute(route) {
    if (route?.page !== 'species' || !urlSyncReady) return;
    const p = route.params || {};
    const nextQ = p.q || '';
    const nextOrder = p.order || '';
    const nextSort = ['name', 'susceptibility'].includes(p.sort) ? p.sort : 'detections';
    const nextClass = ['Aves', 'Mammalia'].includes(p.class) ? p.class : '';
    const nextAll = p.all === '1';
    if (nextQ === searchQuery && nextOrder === orderFilter && nextSort === sortBy
        && nextClass === classFilter && nextAll === showAll) return;
    searchQuery = nextQ;
    orderFilter = nextOrder;
    sortBy = nextSort;
    classFilter = nextClass;
    showAll = nextAll;
  }

  async function loadData() {
    loading = true;
    try {
      await dbStore.loadSpecies();

      // Get unique orders
      const orderResults = await db.query(`
        SELECT DISTINCT "order" as ord FROM species
        WHERE "order" IS NOT NULL AND "order" != ''
        ORDER BY "order"
      `);
      orders = orderResults.map(r => r.ord);

      // Get total count of detected species (parquet) and all (index)
      const countResult = await db.queryScalar('SELECT COUNT(*) FROM species');
      totalDetected = countResult;
      try {
        const r = await fetch('data/species_index.json');
        totalAll = (await r.json()).length;
      } catch { totalAll = countResult; }
      try {
        const r = await fetch('data/species/iucn_status.json');
        if (r.ok) {
          const d = await r.json();
          iucnMap = new Map(Object.entries(d.status || {}));
        }
      } catch { /* badges stay hidden */ }
    } catch (e) {
      console.error('Failed to load species:', e);
      loadError = 'Failed to load species data. Check your connection and try refreshing.';
    } finally {
      loading = false;
      urlSyncReady = true;   // triggers the reactive loader below
    }
  }

  async function loadSpecies() {
    const seq = ++loadSeq;  // stale responses (older seq) are dropped

    // When searching, search everything (taxonomy + supplement) — search
    // should find any species regardless of detection status
    if (searchQuery && searchQuery.length >= 2) {
      let results = await db.searchSpeciesAll(searchQuery, 100);

      // Apply class filter (Aves | Mammalia) — parquet rows are birds by
      // construction; index/supplement rows carry ord='Mammalia' or the
      // mammal flag (mapped through in _indexToSpecies)
      if (classFilter) {
        results = results.filter(s =>
          (s.mammal || s.order === 'Mammalia') ? classFilter === 'Mammalia'
                                               : classFilter === 'Aves');
      }

      // Apply order filter if set
      if (orderFilter) {
        results = results.filter(s => s.order === orderFilter);
      }

      // Apply sorting
      switch (sortBy) {
        case 'name':
          results.sort((a, b) => (a.scientific_name || '').localeCompare(b.scientific_name || ''));
          break;
        case 'susceptibility':
          results.sort((a, b) => (b.susceptibility_score || 0) - (a.susceptibility_score || 0));
          break;
        default:
          // Already sorted by detection_count
          break;
      }

      species = passThreat(results.map(r => ({ ...r, iucn: iucnMap?.get(r.scientific_name) || r.iucn || null })));
      return;
    }

    if (seq !== loadSeq) return;
    // No search query — show detected species by default; "all" toggle
    // pulls the full taxonomy list from the index
    if (!showAll && !classFilter) {
      // Detected species joined with susceptibility (Phase 3: the slim
      // susceptibility table carries score/class only; shared columns
      // come from species). This also fixes the sort-by-susceptibility
      // path, which previously referenced a column the species table
      // never had (Binder Error → empty grid).
      await dbStore.loadSusceptibility();
      // detection_records = surveillance record count (the honest "detections"
      // metric); raw detection_count in the parquet sums animals affected
      // (flock sizes reach millions for poultry) and must not back the badge.
      let sql = `SELECT s.*, su.susceptibility_score, su.susceptibility_class, su.has_rigi,
                        s.detection_records
                 FROM species s
                 LEFT JOIN susceptibility su ON s.scientific_name = su.scientific_name
                 WHERE s.detection_records > 0`;
      if (orderFilter) sql += ` AND s."order" = '${orderFilter}'`;
      switch (sortBy) {
        case 'name': sql += ' ORDER BY s.scientific_name ASC'; break;
        case 'susceptibility': sql += ' ORDER BY su.susceptibility_score DESC NULLS LAST'; break;
        default: sql += ' ORDER BY s.detection_records DESC NULLS LAST';
      }
      sql += ' LIMIT 100';
      const rows = await db.query(sql);
      if (seq !== loadSeq) return;
      species = passThreat(rows.map(r => ({
        ...r,
        detection_count: Number(r.detection_records ?? r.detection_count ?? 0),
        iucn: iucnMap?.get(r.scientific_name) || null
      })));
      return;
    }

    if (!showAll && classFilter === 'Mammalia') {
      // mammals aren't in the aves parquet — detected_mammals.json is the
      // authoritative list (built from detections + genome manifest)
      try {
        const r = await fetch('data/detected_mammals.json');
        const mams = await r.json();
        let rows = mams.map(s => ({
          taxon_id: null, scientific_name: s.sci, common_name: s.com,
          order: 'Mammalia', family: null,
          detection_count: s.det || 0,
          country_count: s.countries || 0,
          has_genome: !!s.genome_acc,
          assembly_level: s.genome_level || (s.genome_acc ? 'Assembly' : null),
          genome_accession: s.genome_acc || null,
          has_presence: !!s.genome_searched,
          iucn: iucnMap?.get(s.sci) || null
        }));
        // Sort select applies here too (susceptibility has no mammal
        // scores yet — falls back to detections)
        if (sortBy === 'name') {
          rows.sort((a, b) => a.scientific_name.localeCompare(b.scientific_name));
        } else {
          rows.sort((a, b) => (Number(b.detection_count) || 0) - (Number(a.detection_count) || 0));
        }
        if (seq !== loadSeq) return;
        species = passThreat(rows);
      } catch { if (seq === loadSeq) species = []; }
      return;
    }

    // showAll — load the merged index + supplement (D113: includes
    // mammals and literature-only species; carries genome badges)
    try {
      const [r, sup] = await Promise.all([
        fetch('data/species_index.json'),
        fetch('data/species_wiki_supplement.json').catch(() => null)
      ]);
      let idx = await r.json();
      if (sup && sup.ok) {
        const supplement = await sup.json();
        const have = new Set(idx.map(s => (s.sci || '').toLowerCase()));
        for (const s of supplement) {
          if (!have.has((s.sci || '').toLowerCase())) { idx.push(s); have.add((s.sci || '').toLowerCase()); }
        }
      }
      if (classFilter) idx = idx.filter(s => (s.ord || (s.mammal ? 'Mammalia' : 'Aves')) === classFilter);
      if (orderFilter) idx = idx.filter(s => s.ord === orderFilter);
      totalAll = idx.length;
      // Sort select applies in the full-taxonomy view too; susceptibility
      // scores join from the slim table (no scores for mammals yet)
      if (sortBy === 'name') {
        idx.sort((a, b) => (a.sci || '').localeCompare(b.sci || ''));
      } else if (sortBy === 'susceptibility') {
        let score = null;
        try {
          await dbStore.loadSusceptibility();
          const su = await db.query('SELECT scientific_name, susceptibility_score FROM susceptibility');
          score = new Map(su.map(r => [r.scientific_name, Number(r.susceptibility_score)]));
        } catch { /* keep detection sort */ }
        idx.sort((a, b) =>
          ((score ? (score.get(b.sci) ?? -1) : (b.det || 0)) - (score ? (score.get(a.sci) ?? -1) : (a.det || 0)))
          || (b.det || 0) - (a.det || 0));
      } else {
        idx.sort((a, b) => (b.det || 0) - (a.det || 0) || (a.sci || '').localeCompare(b.sci || ''));
      }
      if (seq !== loadSeq) return;
      species = passThreat(idx.slice(0, 200).map(s => ({
        taxon_id: s.id,
        scientific_name: s.sci,
        common_name: s.com,
        order: s.ord || (s.mammal ? 'Mammalia' : 'Aves'),
        family: s.fam,
        detection_count: s.det || 0,
        has_genome: s.has_genome || s.genome_species || false,
        assembly_level: s.genome_level || (s.genome_acc ? 'Chromosome' : null),
        genome_accession: s.genome_acc || null,
        has_presence: s.has_presence || s.genome_species || false,
        iucn: iucnMap?.get(s.sci) || null
      })));
    } catch (e) {
      console.error('Failed to load full index:', e);
      if (seq === loadSeq) species = [];
    }
  }

  // React to filter changes — reload + keep the URL shareable.
  // NOTE: classFilter/showAll MUST be read here; before this fix the
  // Birds/Mammals/All buttons never re-ran the loader (dead UI — only the
  // header caption changed).
  $effect(() => {
    void searchQuery; void orderFilter; void sortBy; void classFilter; void showAll; void threatOnly;
    if (loading || !urlSyncReady) return;
    loadSpecies();
    updateParams({
      q: searchQuery || null,
      order: orderFilter || null,
      sort: sortBy !== 'detections' ? sortBy : null,
      class: classFilter || null,
      all: showAll ? '1' : null,
      threat: threatOnly ? '1' : null,
    });
  });

  function handleSearch(e) {
    searchQuery = e.target.value;
  }

  function clearFilters() {
    searchQuery = '';
    orderFilter = '';
    sortBy = 'detections';
    classFilter = '';
    showAll = false;
    threatOnly = false;
  }
</script>

<svelte:head><title>{t('species.title') || 'Species'} — Roost</title></svelte:head>

<div class="space-y-6">
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('species.title')}</h1>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        <a href="#/compare" class="text-blue-600 dark:text-blue-400 hover:underline font-medium"
           title={t('routes.species.side.by.side.comparison') || 'Side-by-side comparison of 2–5 species: detections, genome quality, gene panel'}>{'⚖ ' + (t('compare.side.by.side') || 'Compare species side-by-side') + ' →'}</a>
      </p>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        {#if classFilter === 'Mammalia'}
          {formatNumber(species.length)} {t('species.mammals.detected') || 'mammals with HPAI detections'}
        {:else if classFilter === 'Aves'}
          {showAll ? `${formatNumber(totalAll)} ${t('species.bird.all') || 'bird species'}` : `${formatNumber(totalDetected)} ${t('species.birds.detected') || 'birds with HPAI detections'}`}
        {:else if showAll}
          {formatNumber(totalAll)} {t('species.full.taxonomy') || 'species — full taxonomy (birds + mammals)'}
        {:else}
          {formatNumber(totalDetected)} {t('species.with.hpai') || 'with HPAI detections'} · {formatNumber(totalAll)} {t('species.searchable') || 'searchable'}
        {/if}
      </p>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
    <div class="flex flex-wrap gap-4 items-center">
      <!-- Class filter (D113) -->
      <div class="flex gap-1.5">
        {#each [['', t('common.all') || 'All'], ['Aves', '🐦 ' + (t('species.birds') || 'Birds')], ['Mammalia', '🐾 ' + (t('species.mammals') || 'Mammals')]] as [val, label]}
          <button
            onclick={() => classFilter = val}
            class="px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors {classFilter === val
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
          >{label}</button>
        {/each}
      </div>

      <!-- Conservation filter (IUCN) -->
      <button
        onclick={() => threatOnly = !threatOnly}
        title={t('species.threat.filter') || 'Show only species assessed as threatened (VU, EN, CR, EW, EX) by the IUCN Red List (via Wikidata P141)'}
        class="px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors {threatOnly
          ? 'bg-red-600 text-white'
          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
      >{'⚠ ' + (t('species.threatened') || 'Threatened')}</button>

      <!-- Search -->
      <div class="flex-1 min-w-[200px]">
        <input
          type="text"
          value={searchQuery}
          oninput={handleSearch}
          placeholder={t('search.placeholder.name') || 'Search by name...'}
          class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <!-- Order filter -->
      <div>
        <select
          bind:value={orderFilter}
          aria-label={t('species_page.all.orders')}
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{t('species_page.all.orders')}</option>
          {#each orders as order}
            <option value={order}>{order}</option>
          {/each}
        </select>
      </div>

      <!-- Sort -->
      <div>
        <select
          bind:value={sortBy}
          aria-label={t('species_page.sort.by')}
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="detections">{t('species_page.most.detections')}</option>
          <option value="name">{t('species_page.name.az')}</option>
          <option value="susceptibility">{t('lib_components_species_SpeciesDetail.susceptibility')}</option>
        </select>
      </div>

      <!-- Detected-only / show-all toggle -->
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-2 rounded-lg text-sm font-medium transition-colors {!showAll
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'}"
          onclick={() => { showAll = false; }}
        >
          {t('species.detected.only') || 'Detected only'}
        </button>
        <button
          class="px-3 py-2 rounded-lg text-sm font-medium transition-colors {showAll
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'}"
          onclick={() => { showAll = true; }}
        >
          {t('species.all.species') || 'All species'}
        </button>
      </div>

      <!-- Clear button -->
      {#if searchQuery || orderFilter || sortBy !== 'detections' || classFilter || showAll}
        <button
          onclick={clearFilters}
          class="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
        >
          {t('species.clear.filters')}
        </button>
      {/if}
    </div>
  </div>

  <!-- Error state (network failure, not "no results") -->
  {#if loadError}
    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
      <p class="text-red-700 dark:text-red-300 font-medium">{loadError}</p>
      <button class="mt-3 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              onclick={() => { loadError = null; loadData(); }}>{t('species_page.retry')}</button>
    </div>
  {:else if loading}
    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each [1,2,3,4,5,6] as _}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 animate-pulse">
          <div class="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-3"></div>
          <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
        </div>
      {/each}
    </div>
  {:else if species.length === 0}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
      <svg class="w-12 h-12 mx-auto text-gray-500 dark:text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">{t('species_page.no.species.found')}</h3>
      <p class="text-gray-500 dark:text-gray-400 mb-4">
        {t('species.try.adjusting') || 'Try adjusting your search or filters'}
      </p>
      <button
        onclick={clearFilters}
        class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
      >
        {t('species.clear.filters') || 'Clear all filters'}
      </button>
    </div>
  {:else}
    <!-- sr-only section heading: gives the card h3s a valid hierarchy
         (h1 → h2 section → h3 card titles) without visual change -->
    <h2 class="sr-only">{t('species.results.heading') || 'Species results'}</h2>
    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each species as sp (sp.scientific_name)}
        <SpeciesCard species={sp} />
      {/each}
    </div>

    {#if species.length >= 100}
      <p class="text-center text-sm text-gray-500 dark:text-gray-400">
        {t('species.showing.first') || 'Showing first 100 results. Use filters to narrow down.'}
      </p>
    {/if}
  {/if}
</div>
