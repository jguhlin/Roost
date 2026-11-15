<script>
  import { onMount } from 'svelte';
  import { doi } from '../lib/utils/urls.js';
  import { navigate, subscribe as routerSubscribe, getRoute, updateParams } from '../lib/stores/router.js';
  import { trackSearch, trackEvent } from '../lib/analytics.js';
  import SpeciesDetail from '../lib/components/species/SpeciesDetail.svelte';
  import { t, pt, ptopic } from '../lib/stores/i18n.svelte.js';
  import { announce } from '../lib/stores/a11y.svelte.js';
  import { formatNumber } from '../lib/utils/format.js';

  let papers = $state([]);
  let categories = $state([]);
  let speciesIndex = $state({}); // Map scientific name -> common name
  let mammalsIndex = $state({}); // Map scientific name -> common name
  let loading = $state(true);
  let addedFilter = $state(null);   // ?added=YYYY-MM-DD — batch view (History link)
  let error = $state(null);

  // Species detail modal
  let selectedSpecies = $state(null);

  // Focused paper via route id (#/papers/{paper_id}) — deep links from citation chips
  let focusPaperId = $state(null);
  // analytics: which papers people open (route-driven, fires on change)
  $effect(() => { if (focusPaperId) trackEvent('Paper', 'view', focusPaperId); });
  let focusPaper = $derived(focusPaperId ? papers.find(p => p.id === focusPaperId) : null);

  // Per-paper DEG summaries (lazy — only fetched when a paper is focused)
  let degSummaries = $state(null);
  let focusDeg = $derived(degSummaries && focusPaperId ? degSummaries[focusPaperId] : null);
  $effect(() => {
    if (focusPaperId && !degSummaries) {
      fetch('data/paper_deg_summaries.json')
        .then(r => r.ok ? r.json() : { papers: {} })
        .then(d => { degSummaries = d.papers || {}; })
        .catch(() => { degSummaries = {}; });
    }
  });

  // --- URL state: ?q= (search), ?f= (facet chips, 'type:value|type:value'),
  //     ?p= (page) — shareable alongside #/papers/{id} focus links.
  // Absent param = its default; chips round-trip through a compact string
  // because the router params are a flat string map.
  let urlSyncReady = $state(false);
  let syncedKey = '';   // filter state as last restored from / written to the URL

  const chipsToParam = (chips) => chips.length
    ? chips.map(f => `${f.type}:${f.value}`).join('|') : null;
  const paramToChips = (raw) => {
    if (!raw) return [];
    return String(raw).split('|').map(part => {
      const i = part.indexOf(':');
      if (i < 1) return null;
      const type = part.slice(0, i);
      if (!['category', 'topic', 'year', 'species'].includes(type)) return null;
      return { type, value: part.slice(i + 1) };
    }).filter(Boolean);
  };
  const chipsKey = (chips) => chipsToParam(chips) || '';

  const applyParams = (p = {}) => {
    const nextQ = p.q || '';
    const nextChips = paramToChips(p.f);
    const nextP = Math.max(1, parseInt(p.p, 10) || 1);
    const nextAdded = /^\d{4}-\d{2}-\d{2}$/.test(p.added || '') ? p.added : null;
    if (nextQ === searchQuery && chipsKey(nextChips) === chipsKey(activeFilters) && nextP === page && nextAdded === addedFilter) return;
    if (nextQ !== searchQuery) searchQuery = nextQ;
    if (chipsKey(nextChips) !== chipsKey(activeFilters)) activeFilters = nextChips;
    if (nextP !== page) page = nextP;
    if (nextAdded !== addedFilter) addedFilter = nextAdded;
    // mark this state as URL-derived so the pagination-reset effect
    // doesn't fire for restores (a fresh [] alone would trigger it)
    syncedKey = nextQ + '|' + chipsKey(nextChips);
  };

  const applyRoute = route => {
    focusPaperId = route.page === 'papers' ? route.id : null;
    if (route.page === 'papers' && urlSyncReady) applyParams(route.params || {});
  };

  onMount(() => {
    applyParams(getRoute()?.params || {});
    applyRoute(getRoute());
    return routerSubscribe(applyRoute);
  });

  onMount(async () => {
    try {
      // Load papers, species index, mammals + species-mentions index
      const [papersRes, speciesRes, mammalsRes, speciesMentionsRes] = await Promise.all([
        fetch('data/papers.json'),
        fetch('data/species_index.json'),
        fetch('data/mammals.json').catch(() => ({ ok: false })),
        fetch('data/paper_species_mentions.json').then((r) => r.ok ? r.json() : {}).catch(() => ({}))
      ]);
      paperSpeciesMentions = await speciesMentionsRes;

      if (!papersRes.ok) throw new Error('Failed to load papers');
      const papersData = await papersRes.json();
      papers = papersData.papers || [];
      categories = [...new Set([
        ...(papersData.categories || []),
        ...papers.map(p => p.category).filter(Boolean),
      ])].sort();
      if (papers.some(p => !p.category)) categories.push('Uncategorized');

      // Build species lookup
      if (speciesRes.ok) {
        const speciesData = await speciesRes.json();
        for (const sp of speciesData) {
          speciesIndex[sp.sci] = sp.com || sp.sci;
        }
      }

      // Build mammals lookup
      if (mammalsRes.ok) {
        const mammalsData = await mammalsRes.json();
        for (const sp of mammalsData.species || []) {
          mammalsIndex[sp.sci] = sp.common || sp.sci;
        }
      }

      loading = false;
      urlSyncReady = true;
    } catch (e) {
      error = e.message;
      loading = false;
    }
  });

  // Display rule: ≤3 authors shown, then 'et al.' Full list in authors_list (network).
  function fmtAuthors(a) {
    if (!a) return '';
    const parts = a.split(', ').filter(x => x && !/^et\.? al\.?$/i.test(x.trim()));
    if (parts.length <= 3) return parts.join(', ');
    return parts.slice(0, 3).join(', ') + ', et al.';
  }

  function openSpeciesDetail(scientificName) {
    selectedSpecies = scientificName;
  }

  function closeSpeciesDetail() {
    selectedSpecies = null;
  }

  // Get display name for a species
  function getSpeciesName(sci) {
    return speciesIndex[sci] || mammalsIndex[sci] || sci.replace(/_/g, ' ');
  }

  // Check if it's a bird species
  function isBird(sci) {
    return sci in speciesIndex;
  }

  // Unique topics from all papers, with paper counts (D109)
  let topicCounts = $derived.by(() => {
    const c = new Map();
    for (const p of papers) for (const t of (p.topics || [])) c.set(t, (c.get(t) || 0) + 1);
    return c;
  });
  let allTopics = $derived([...topicCounts.keys()].sort());
  let categoryCounts = $derived.by(() => {
    const c = new Map();
    for (const p of papers) {
      const k = p.category || 'Uncategorized';
      c.set(k, (c.get(k) || 0) + 1);
    }
    return c;
  });

  let topicFilter = $state('');
  let categoryFilter = $state('');
  let yearFilter = $state('');

  // Tag-chip filter model (D44): a set of active {type, value} chips.
  // Semantics: OR within a dimension, AND across dimensions (faceted search).
  let activeFilters = $state([]);

  function addFilter(type, value) {
    if (value === '' || value == null) return;
    if (!activeFilters.some(f => f.type === type && String(f.value) === String(value))) {
      activeFilters = [...activeFilters, { type, value }];
    }
  }
  function removeFilter(i) {
    activeFilters = activeFilters.filter((_, idx) => idx !== i);
  }
  function clearFilters() {
    activeFilters = [];
  }

  function matchesChips(p) {
    const byType = {};
    for (const f of activeFilters) {
      (byType[f.type] = byType[f.type] || []).push(String(f.value));
    }
    for (const [type, vals] of Object.entries(byType)) {
      if (type === 'category') {
        if (!vals.includes(p.category || 'Uncategorized')) return false;
      } else if (type === 'topic') {
        const pts = (p.topics || []).map(String);
        if (!vals.some(v => pts.includes(v))) return false;
      } else if (type === 'year') {
        if (!vals.includes(String(p.year))) return false;
      } else if (type === 'species') {
        const all = [
          ...((p.species_links?.avian) || []),
          ...((p.species_links?.mammal) || []),
        ].map(String);
        if (!vals.some(v => all.includes(v))) return false;
      }
    }
    return true;
  }
  let searchQuery = $state('');
  let paperSpeciesMentions = $state({});  // paper_id -> [{sci, com}] (typed claims)
  let showSummaries = $state(true);
  let page = $state(1);
  const PAGE_SIZE = 25;

  function goTo(n) {
    page = Math.min(Math.max(1, n), totalPages);  // URL sync via the effect below
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Any INTERACTIVE filter change returns to page 1 — but URL restores
  // (deep links / SPA nav) keep their ?p=N because applyParams marks the
  // state as URL-derived via syncedKey.
  $effect(() => {
    void activeFilters; void searchQuery;
    if (loading) return;
    if (searchQuery + '|' + chipsKey(activeFilters) === syncedKey) return;
    page = 1;
  });

  // state → URL (echo-guarded by applyParams' comparison)
  $effect(() => {
    void searchQuery; void activeFilters; void page; void addedFilter;
    if (loading || !urlSyncReady) return;
    updateParams({
      q: searchQuery || null,
      f: chipsToParam(activeFilters),
      p: page > 1 ? String(page) : null,
      added: addedFilter || null,
    });
    syncedKey = searchQuery + '|' + chipsKey(activeFilters);
  });
  // a11y: announce the filtered result count to screen readers when it settles
  let lastAnnouncedPapers = $state(-1);
  $effect(() => {
    const n = filteredPapers.length;
    if (n > 0 && n !== lastAnnouncedPapers) {
      lastAnnouncedPapers = n;
      announce(t('a11y.announce.papers.results', { n }));
    }
  });
  let totalPages = $derived(Math.max(1, Math.ceil(filteredPapers.length / PAGE_SIZE)));
  let pagedPapers = $derived(filteredPapers.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE));
  // windowed page buttons: 1 … p-1 p p+1 … last
  let pageWindow = $derived.by(() => {
    const out = [];
    const add = (n) => { if (n >= 1 && n <= totalPages && !out.includes(n)) out.push(n); };
    add(1); add(2);
    for (let n = page - 2; n <= page + 2; n++) add(n);
    add(totalPages - 1); add(totalPages);
    out.sort((a, b) => a - b);
    // insert ellipsis markers
    const disp = [];
    let prev = 0;
    for (const n of out) {
      if (n - prev > 1) disp.push('…');
      disp.push(n);
      prev = n;
    }
    return disp;
  });

  // analytics: paper searches with result counts (no-op in dev)
  let _paperSearchTimer = null;
  $effect(() => {
    void searchQuery;
    if (_paperSearchTimer) clearTimeout(_paperSearchTimer);
    if (searchQuery.trim().length < 2) return;
    const q = searchQuery.trim();
    _paperSearchTimer = setTimeout(() => trackSearch('papers', q, filteredPapers.length), 600);
  });

  let filteredPapers = $derived(papers.filter(p => {
    if (addedFilter) {
      // event stamps and paper 'added' stamps can differ by a day across
      // midnight (UTC vs intake time) — accept a ±1 day window
      const addedTs = Date.parse(addedFilter);
      const pd = Date.parse(p.added || '');
      if (isNaN(pd) || Math.abs(pd - addedTs) > 36 * 3600 * 1000) return false;
    }
    if (!matchesChips(p)) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      // registry-minimal entries (register_orphans) may lack authors/journal
      // — guard every field or one thin record kills the whole filter (D124)
      if (!(p.title || '').toLowerCase().includes(q) &&
          !(p.authors || '').toLowerCase().includes(q) &&
          !(p.journal || '').toLowerCase().includes(q) &&
          !((p.summary || '').toLowerCase()).includes(q)) {
        // species-aware pass: match the query against species named in this
        // paper's typed claims (scientific or common name)
        const mentions = paperSpeciesMentions[p.id] || [];
        const hit = mentions.some(m =>
          m.sci?.toLowerCase().includes(q) || m.com?.toLowerCase().includes(q));
        if (!hit) return false;
      }
    }
    return true;
  }));

  const years = $derived([...new Set(papers.map(p => p.year))].sort((a, b) => b - a));

  // Group by category for display
  let papersByCategory = $derived.by(() => {
    const grouped = {};
    for (const paper of filteredPapers) {
      const cat = paper.category || 'Uncategorized';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(paper);
    }
    return grouped;
  });
</script>

<svelte:head><title>{t('papers.title') || 'Papers'} — Roost</title></svelte:head>

<div class="space-y-6">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('papers.title')}</h1>
    <p class="text-gray-600 dark:text-gray-300 mt-1">
      {t('papers.subtitle') || 'Key literature for avian influenza host genomics and cross-species transmission research'}
    </p>
    {#if !loading && papers.length > 0}
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {formatNumber(papers.length)} {t('papers.count') || 'papers in collection'}
      </p>
    {/if}
  </div>

  {#if loading}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
      <p class="text-gray-500 dark:text-gray-400">{t('papers_page.loading.papers')}</p>
    </div>
  {:else if error}
    <div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-6 border border-red-200 dark:border-red-800">
      <p class="text-red-700 dark:text-red-300">Error loading papers: {error}</p>
    </div>
  {:else}
    <!-- Focused paper (deep link #/papers/{id}) -->
    {#if focusPaper}
      <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg shadow p-6 border border-blue-200 dark:border-blue-800 space-y-3">
        <button
          onclick={() => navigate('papers')}
          class="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
        >
          {t('papers.back.all')}
        </button>
        <h2 class="text-xl font-bold text-gray-900 dark:text-white">{pt(focusPaper.id, 'title') || focusPaper.title}{#if pt(focusPaper.id, 'title') && pt(focusPaper.id, 'title') !== focusPaper.title}<span class="block text-base italic font-normal text-gray-500 dark:text-gray-400">{focusPaper.title}</span>{/if}</h2>
        <p class="text-sm text-gray-600 dark:text-gray-300">
          {fmtAuthors(focusPaper.authors)}{focusPaper.year ? ` (${focusPaper.year})` : ''}
          {#if focusPaper.journal}<span class="italic"> · {focusPaper.journal}</span>{/if}
        </p>
        <div class="flex flex-wrap gap-1.5">
          {#each focusPaper.topics || [] as topic}
            <span class="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">{ptopic(topic)}</span>
          {/each}
        </div>
        {#if focusPaper.summary}
          <p class="text-sm text-gray-600 dark:text-gray-400">{focusPaper.summary}</p>
        {/if}
        {#if focusPaper.cited_for}
          <p class="text-sm text-gray-500 dark:text-gray-400">
            <span class="font-medium">{t('papers_page.cited.for')}</span> {focusPaper.cited_for}
          </p>
        {/if}
        {#if focusDeg && (focusDeg.count_findings?.length || focusDeg.top_genes?.length)}
          <div class="border-t border-blue-200 dark:border-blue-800 pt-3 space-y-2" data-testid="paper-deg-summary">
            <h2 class="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">{t('papers_page.differential.expression')}</h2>
            {#each focusDeg.count_findings as c}
              <div class="flex items-start gap-2 text-sm">
                <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">{c.value}</span>
                <span class="text-gray-600 dark:text-gray-400">{c.finding}{#if c.context}<span class="text-gray-500 dark:text-gray-400"> ({c.context})</span>{/if}</span>
              </div>
            {/each}
            {#if focusDeg.top_genes?.length}
              <div class="flex flex-wrap gap-1.5 pt-1">
                {#each focusDeg.top_genes as g}
                  <a href="#/genes/{g.symbol}" title={g.role}
                    class="px-2 py-0.5 text-xs rounded-full {g.importance === 'central' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 font-medium' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'} hover:underline">
                    {g.symbol}
                  </a>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
        <div class="flex flex-wrap gap-2 pt-1">
          {#if focusPaper.doi}
            <a href={doi(focusPaper.doi)} target="_blank" rel="noopener noreferrer"
              class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">DOI: {focusPaper.doi}</a>
          {:else if focusPaper.url}
            <a href={focusPaper.url} target="_blank" rel="noopener noreferrer"
              class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">{t('papers_page.publisher.page')}</a>
          {/if}
          {#each (focusPaper.species_links?.avian || []) as sci}
            <button
              onclick={() => { addFilter('species', sci); focusPaperId = null; }}
              title={t('routes.papers.filter.papers.by.sci', { sci })}
              class="px-3 py-1.5 text-sm bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 rounded hover:bg-sky-200"
            >🪶 {getSpeciesName(sci)}</button>
          {/each}
          {#each (focusPaper.species_links?.mammal || []) as sci}
            <button
              onclick={() => { addFilter('species', sci); focusPaperId = null; }}
              title={t('routes.papers.filter.papers.by.sci', { sci })}
              class="px-3 py-1.5 text-sm bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded hover:bg-orange-200"
            >🐁 {getSpeciesName(sci)}</button>
          {/each}
        </div>
      </div>
    {:else}
    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex-1 min-w-[200px]">
          <input
            type="text"
            bind:value={searchQuery}
            placeholder={t('search.placeholder.papers') || 'Search papers...'}
            class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <select
            value=""
            onchange={(e) => { addFilter('category', e.target.value); e.target.value = ''; }}
            aria-label={t('papers.filter.category')}
            class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-[calc(100vw-6rem)] min-w-0"
          >
            <option value="">{t('papers.filter.category') || '+ Category…'}</option>
            {#each categories as cat}
              <option value={cat}>{ptopic(cat)} ({categoryCounts.get(cat) || 0})</option>
            {/each}
          </select>
        </div>

        <div>
          <select
            value=""
            onchange={(e) => { addFilter('topic', e.target.value); e.target.value = ''; }}
            aria-label={t('papers.filter.topic')}
            class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-[calc(100vw-6rem)] min-w-0"
          >
            <option value="">{t('papers.filter.topic') || '+ Topic…'}</option>
            {#each allTopics as topic}
              <option value={topic}>{ptopic(topic)} ({topicCounts.get(topic)})</option>
            {/each}
          </select>
        </div>

        <div>
          <select
            value=""
            onchange={(e) => { addFilter('year', e.target.value); e.target.value = ''; }}
            aria-label={t('papers.filter.year')}
            class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-[calc(100vw-6rem)] min-w-0"
          >
            <option value="">{t('papers.filter.year') || '+ Year…'}</option>
            {#each years as year}
              <option value={year}>{year}</option>
            {/each}
          </select>
        </div>

        <label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
          <input
            type="checkbox"
            bind:checked={showSummaries}
            class="rounded border-gray-300 dark:border-gray-600"
          />
          {t('papers.show.summaries') || 'Show summaries'}
        </label>

        {#if topicFilter || yearFilter || searchQuery || categoryFilter}
          <button
            onclick={() => { topicFilter = ''; yearFilter = ''; searchQuery = ''; categoryFilter = ''; }}
            class="text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            {t('papers.clear.filters')}
          </button>
        {/if}
      </div>

      <!-- Active filter chips -->
      {#if activeFilters.length > 0}
        <div class="flex flex-wrap items-center gap-2 mt-3">
          {#each activeFilters as f, i}
            <button
              class="group inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium
                {f.type === 'category' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                  : f.type === 'topic' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                  : 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'}
                hover:opacity-80 transition-opacity"
              title={t('tip.papers.remove.filter') || 'Remove filter'}
              onclick={() => removeFilter(i)}
            >
              <span class="text-[10px] uppercase opacity-60">{f.type}</span>
              {f.value}
              <span class="ml-0.5 opacity-50 group-hover:opacity-100">✕</span>
            </button>
          {/each}
          <button
            class="text-xs text-gray-500 dark:text-gray-400 hover:text-red-600 ml-1"
            onclick={clearFilters}
          >
            clear all
          </button>
        </div>
      {/if}

      {#if addedFilter}
        <div class="mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 px-4 py-2.5">
          <span class="text-sm text-blue-800 dark:text-blue-200">📚 Papers added on {addedFilter} — showing this batch ({filteredPapers.length})</span>
          <button
            class="ml-auto text-xs px-2.5 py-1 rounded-full bg-blue-600 text-white hover:bg-blue-700"
            onclick={() => (addedFilter = null)}
          >{t('papers_page.view.all.papers')}</button>
        </div>
      {/if}

      <div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
        {t('papers.showing') || 'Showing'} {formatNumber((page - 1) * PAGE_SIZE + 1)}–{formatNumber(Math.min(page * PAGE_SIZE, filteredPapers.length))} {t('papers.of') || 'of'} {formatNumber(filteredPapers.length)} {t('papers.papers') || 'papers'} ({t('papers.of.total') || 'of'} {formatNumber(papers.length)} {t('papers.total') || 'total'})
      </div>
    </div>

    <!-- Papers list -->
    <div class="space-y-4">
      <!-- sr-only section heading: paper-card h3s need an h2 level above -->
      <h2 class="sr-only">{t('papers.results.heading') || 'Paper results'}</h2>
      {#each pagedPapers as paper}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <button
                  class="px-2 py-0.5 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  title={t('tip.papers.category') || 'Filter by this category'}
                  onclick={() => addFilter('category', paper.category || 'Uncategorized')}
                >
                  {paper.category || 'Uncategorized'}
                </button>
                <button
                  class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  title={t('tip.papers.year') || 'Filter by this year'}
                  onclick={() => addFilter('year', paper.year)}
                >
                  {paper.year ?? '—'}
                </button>
                {#each (paper.topics || []).slice(0, 4) as topic}
                  <button
                    class="px-2 py-0.5 text-xs rounded bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/50"
                    title={t('tip.papers.topic') || 'Filter by this topic'}
                    onclick={() => addFilter('topic', topic)}
                  >
                    {ptopic(topic)}
                  </button>
                {/each}
              </div>

              <h3 class="font-medium text-gray-900 dark:text-white">
                {#if paper.doi}
                  <a
                    href={doi(paper.doi)}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-400"
                  >
                    {pt(paper.id, 'title') || paper.title_en || paper.title}
                  </a>
                {:else if paper.url}
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-400"
                  >
                    {pt(paper.id, 'title') || paper.title_en || paper.title}
                  </a>
                {:else}
                  {pt(paper.id, 'title') || paper.title_en || paper.title}
                {/if}
                {#if (pt(paper.id, 'title') || paper.title_en) && (pt(paper.id, 'title') || paper.title_en) !== paper.title}<span class="block text-sm italic text-gray-500 dark:text-gray-400 mt-0.5">{paper.title}</span>{/if}
              </h3>
              <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
                {fmtAuthors(paper.authors)}
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                {paper.journal}
              </p>

              {#if showSummaries && paper.summary}
                <p class="text-sm text-gray-700 dark:text-gray-200 mt-3 bg-gray-50 dark:bg-gray-700/50 p-3 rounded-md">
                  {pt(paper.id, 'summary') || paper.summary}
                </p>
              {/if}

              <div class="flex flex-wrap gap-2 mt-3">
                {#each paper.topics as topic}
                  <button
                    onclick={() => topicFilter = topic}
                    class="px-2 py-0.5 text-xs rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50"
                  >
                    {ptopic(topic)}
                  </button>
                {/each}
              </div>

              <!-- Species Links -->
              {#if paper.species_links && (paper.species_links.avian?.length > 0 || paper.species_links.mammal?.length > 0)}
                <div class="flex flex-wrap gap-2 mt-2">
                  <span class="text-xs text-gray-500 dark:text-gray-400">{t('routes_Papers.species')}</span>
                  {#each paper.species_links.avian || [] as sci}
                    <button
                      onclick={() => addFilter('species', sci)}
                      class="px-2 py-0.5 text-xs rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50"
                      title={t('papers.filter.species', { sci })}
                    >
                      {getSpeciesName(sci)}
                    </button>
                  {/each}
                  {#each paper.species_links.mammal || [] as sci}
                    <button
                      onclick={() => addFilter('species', sci)}
                      class="px-2 py-0.5 text-xs rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-900/50"
                      title={t('papers.filter.species', { sci })}
                    >
                      {getSpeciesName(sci)}
                    </button>
                  {/each}
                </div>
              {/if}

              {#if paper.cited_for}
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  <span class="font-medium">{t('papers_page.cited.for')}</span> {pt(paper.id, 'cited_for') || paper.cited_for}
                </p>
              {/if}
            </div>

            <div class="flex flex-col gap-2">
              {#if paper.doi}
                <a
                  href={doi(paper.doi)}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex-shrink-0 px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 flex items-center gap-2"
                >
                  DOI
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              {:else if paper.url}
                <a
                  href={paper.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex-shrink-0 px-4 py-2 bg-gray-600 text-white text-sm rounded-md hover:bg-gray-700 flex items-center gap-2"
                >
                  Link
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              {/if}
            </div>
          </div>
        </div>
      {:else}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
          <p class="text-gray-500 dark:text-gray-400">{t('papers_page.no.papers.found.matching')}</p>
        </div>
      {/each}
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="flex flex-wrap items-center justify-center gap-1.5 mt-6">
        <button
          class="px-3 py-1.5 rounded-lg text-sm bg-white dark:bg-gray-800 shadow {page === 1 ? 'text-gray-500 dark:text-gray-400' : 'text-gray-700 dark:text-gray-200 hover:shadow-md'}"
          disabled={page === 1}
          onclick={() => goTo(page - 1)}
        >
          ←
        </button>
        {#each pageWindow as pn}
          {#if pn === '…'}
            <span class="px-2 text-gray-500 dark:text-gray-400">…</span>
          {:else}
            <button
              class="min-w-[36px] px-2 py-1.5 rounded-lg text-sm {pn === page
                ? 'bg-blue-600 text-white shadow'
                : 'bg-white dark:bg-gray-800 shadow text-gray-700 dark:text-gray-200 hover:shadow-md'}"
              onclick={() => goTo(pn)}
            >
              {pn}
            </button>
          {/if}
        {/each}
        <button
          class="px-3 py-1.5 rounded-lg text-sm bg-white dark:bg-gray-800 shadow {page === totalPages ? 'text-gray-500 dark:text-gray-400' : 'text-gray-700 dark:text-gray-200 hover:shadow-md'}"
          disabled={page === totalPages}
          onclick={() => goTo(page + 1)}
        >
          →
        </button>
        <span class="text-sm text-gray-500 dark:text-gray-400 ml-2">
          {t('common.page') || 'page'} {page} / {totalPages}
        </span>
      </div>
    {/if}

    <!-- Note about curation -->
    <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-100 dark:border-blue-800">
      <h3 class="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">{t('papers_page.about.this.collection')}</h3>
      <p class="text-sm text-blue-800 dark:text-blue-200">
        {t('papers.curated.desc') || 'This is a curated selection of key papers relevant to avian influenza host genomics, cross-species transmission,'}
        {t('papers.curated.desc2') || 'and pandemic preparedness. Papers are summarized for quick reference with proper citations maintained.'}
        {t('papers.curated.use') || 'For comprehensive literature searches, use'}
        <a href="https://pubmed.ncbi.nlm.nih.gov/?term=H5N1+avian+influenza" target="_blank" rel="noopener noreferrer" class="underline">{t('routes_Papers.pubmed')}</a>
        or
        <a href="https://scholar.google.com/scholar?q=H5N1+avian+influenza+host+genomics" target="_blank" rel="noopener noreferrer" class="underline">{t('papers_page.google.scholar')}</a>.
      </p>
    </div>
  {/if}
  {/if}
</div>

<!-- Species Detail Modal -->
{#if selectedSpecies}
  <SpeciesDetail speciesId={selectedSpecies} onclose={closeSpeciesDetail} />
{/if}
