<script>
  import { t } from '../lib/stores/i18n.svelte.js';
  /**
   * Glossary — abbreviations & terms from Avian Immunology (2022, 3rd ed.).
   * Route: #/glossary — live search, gene-link detection for abbreviations
   * that match panel symbols.
   */
  import { onMount } from 'svelte';
  import { getRoute, updateParams, subscribe as routerSubscribe } from '../lib/stores/router.js';
  import OnDeviceExplain from '../lib/components/common/OnDeviceExplain.svelte';

  let data = $state(null);
  let query = $state('');
  const PAGE_SIZE = 60;
  let page = $state(1);

  // --- URL state: ?q= (term search) + ?p= (page) — same contract as the
  //     other pages
  let urlSyncReady = $state(false);

  const applyParams = (p = {}) => {
    const next = p.q || '';
    if (next !== query) { query = next; }
    const nextP = Math.max(1, parseInt(p.p, 10) || 1);
    if (nextP !== page) page = nextP;
  };

  onMount(async () => {
    applyParams(getRoute()?.params || {});
    urlSyncReady = true;
    const cleanupRoute = routerSubscribe(route => {
      if (route.page === 'glossary' && urlSyncReady) applyParams(route.params || {});
    });
    try {
      const r = await fetch('data/glossary.json');
      data = await r.json();
    } catch { /* empty state */ }
    return cleanupRoute;
  });

  // state → URL (echo-guarded by applyParams)
  $effect(() => {
    void query; void page;
    if (!urlSyncReady) return;
    updateParams({ q: query || null, p: page > 1 ? String(page) : null });
  });

  let filtered = $derived.by(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    if (!q) return data.entries;
    return data.entries.filter(e =>
      e.abbr.toLowerCase().includes(q) || e.def.toLowerCase().includes(q)
    );
  });

  // searching jumps back to page 1 (only on actual query CHANGES — a
  // mount-time run must not stomp a deep-linked ?p=)
  let _lastQuery = null;
  $effect(() => {
    const q = query;
    if (_lastQuery !== null && q !== _lastQuery) page = 1;
    _lastQuery = q;
  });

  let totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)));
  let clampedPage = $derived(Math.min(page, totalPages));
  let paged = $derived(filtered.slice((clampedPage - 1) * PAGE_SIZE, clampedPage * PAGE_SIZE));
</script>

<svelte:head><title>{t('lib_components_common_Footer.glossary') || 'Glossary'} — Roost</title></svelte:head>

<div class="max-w-4xl mx-auto space-y-6">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{t('lib_components_common_Footer.glossary')}</h1>
    <p class="text-gray-600 dark:text-gray-300">
      {data ? `${data.count} ` + (t('glossary.count') || 'abbreviations and terms') : 'loading…'} from
      <em>{t('glossary_page.avian.immunology')}</em> {t('glossary.edition.note')}
    </p>
  </div>

  <input
    type="text"
    bind:value={query}
    placeholder={t('search.placeholder.glossary') || 'Search abbreviations and terms… (e.g. AID, MHC, TLR)'}
    class="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
  />

  {#if data}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow divide-y divide-gray-100 dark:divide-gray-700">
      {#each paged as e (e.abbr + '::' + e.def)}
        <div class="px-4 py-2.5">
          <div class="flex items-baseline gap-4">
            <span class="font-mono font-semibold text-blue-700 dark:text-blue-300 min-w-[90px]">{e.abbr}</span>
            <span class="text-sm text-gray-700 dark:text-gray-300">{e.def}</span>
            <OnDeviceExplain abbr={e.abbr} definition={e.def} />
          </div>
        </div>
      {/each}
      {#if filtered.length === 0}
        <div class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">{t('glossary_page.no.matches')}</div>
      {/if}
    </div>

    {#if totalPages > 1}
      <nav class="flex items-center justify-center gap-2 flex-wrap" aria-label={t('glossary.pagination_aria')}>
        <button class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={clampedPage === 1} onclick={() => (page = clampedPage - 1)}>{t('glossary.prev')}</button>
        {#each Array.from({ length: totalPages }, (_, i) => i + 1) as p (p)}
          {#if p === 1 || p === totalPages || Math.abs(p - clampedPage) <= 1}
            <button class="min-w-[36px] px-2 py-1.5 text-sm rounded-lg font-medium {p === clampedPage
              ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
              aria-current={p === clampedPage ? 'page' : undefined}
              onclick={() => (page = p)}>{p}</button>
          {:else if Math.abs(p - clampedPage) === 2}
            <span class="text-gray-400 px-1">…</span>
          {/if}
        {/each}
        <button class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={clampedPage === totalPages} onclick={() => (page = clampedPage + 1)}>{t('glossary.next')}</button>
        <span class="text-xs text-gray-500 dark:text-gray-400 ml-2">{t('glossary.page_of', { p: clampedPage, n: totalPages, total: filtered.length })}</span>
      </nav>
    {/if}
  {/if}
</div>
