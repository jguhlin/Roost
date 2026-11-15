<script>
  import { t, sn } from '../../../lib/stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import searchStore from '../../stores/search.js';
  import { trackEvent } from '../../analytics.js';
  import { navigate } from '../../stores/router.js';
  import { getIUCNInfo } from '../../utils/format.js';
  import { phylopicIndex, phylopicPath } from '../../utils/phylopic.js';

  // Props
  let { placeholder = 'Search species, genes, locations...', compact = false } = $props();

  // Local state
  let query = $state('');
  let results = $state([]);
  let loading = $state(false);
  let open = $state(false);
  let selectedIndex = $state(-1);
  let silhouettes = $state(null);
  $effect(() => { phylopicIndex().then(i => silhouettes = i); });
  let inputRef = $state(null);

  // Subscribe to search store
  onMount(() => {
    const unsubscribe = searchStore.subscribe(state => {
      results = state.results;
      loading = state.loading;
    });

    // Preload species index
    searchStore.preload();

    // Keyboard shortcut: Cmd/Ctrl + K to focus search
    const handleKeydown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef?.focus();
        open = true;
      }
      if (e.key === 'Escape' && open) {
        close();
      }
    };
    window.addEventListener('keydown', handleKeydown);

    return () => {
      unsubscribe();
      window.removeEventListener('keydown', handleKeydown);
    };
  });

  function handleInput(e) {
    query = e.target.value;
    selectedIndex = -1;
    searchStore.setQuery(query);
    if (query.length >= 2) {
      open = true;
    }
  }

  function handleFocus() {
    if (query.length >= 2 || results.length > 0) {
      open = true;
    }
  }

  function close() {
    open = false;
    selectedIndex = -1;
  }

  function selectResult(result) {
    // analytics: search → pick ("Strigops habroptila ← kakapo") — the
    // intent-to-destination signal, entity and term in one event name
    const q = (searchStore.state?.query || '').trim();
    const entity = result.type === 'gene' ? result.symbol
      : result.type === 'mutation' ? result.canonical
      : result.scientific_name || result.name || '?';
    trackEvent('Search', 'click', q ? `${entity} ← ${q}` : entity);
    searchStore.selectResult(result);
    query = '';
    close();
    // Route by result type
    if (result.type === 'gene') {
      navigate('genes', result.symbol);
    } else if (result.type === 'mutation') {
      navigate('mutations', result.canonical);
    } else {
      // null-id species (mammals, unresolved) navigate by scientific name —
      // the detection modal cannot resolve them, so wiki/presence species
      // go straight to the full page (gene panel + wiki content)
      if (!result.id && result.scientific_name) {
        navigate('species-full', result.scientific_name);
      } else {
        navigate('species', result.id || result.scientific_name);
      }
    }
  }

  function handleKeydown(e) {
    if (!open) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
        break;
      case 'ArrowUp':
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          selectResult(results[selectedIndex]);
        } else if (query.length >= 2) {
          // Navigate to search results page
          navigate('species', null, { q: query });
          close();
        }
        break;
      case 'Escape':
        close();
        break;
    }
  }

  // Click outside to close
  function handleClickOutside(e) {
    if (!e.target.closest('.search-container')) {
      close();
    }
  }
</script>

<svelte:window onclick={handleClickOutside} />

<div class="search-container relative {compact ? 'w-64' : 'w-full max-w-xl'}">
  <div class="relative">
    <!-- Search icon -->
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>

    <input
      bind:this={inputRef}
      type="text"
      value={query}
      oninput={handleInput}
      onfocus={handleFocus}
      onkeydown={handleKeydown}
      {placeholder}
      class="w-full pl-10 pr-12 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent {compact ? 'text-sm py-1.5' : ''}"
    />

    <!-- Keyboard shortcut hint -->
    {#if !compact && !query}
      <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
        <kbd class="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded border border-gray-300 dark:border-gray-600">⌘K</kbd>
      </span>
    {/if}

    <!-- Loading spinner -->
    {#if loading}
      <svg class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    {/if}
  </div>

  <!-- Results dropdown -->
  {#if open && (results.length > 0 || query.length >= 2)}
    <div class="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden z-50 max-h-96 overflow-y-auto">
      {#if results.length === 0}
        <div class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
          {t('search.no.results') || 'No results found for'} "{query}"
        </div>
      {:else}
        <ul class="divide-y divide-gray-100 dark:divide-gray-700">
          {#each results as result, i}
            <li>
              <button
                class="w-full px-4 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:bg-gray-50 dark:focus:bg-gray-700 {selectedIndex === i ? 'bg-blue-50 dark:bg-blue-900/30' : ''}"
                onclick={() => selectResult(result)}
                onmouseenter={() => selectedIndex = i}
              >
                {#if result.type === 'gene'}
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">{t('lib_components_common_SearchBar.gene')}</span>
                      <span class="text-sm font-mono font-semibold text-gray-900 dark:text-white">{result.symbol}</span>
                      <span class="text-xs text-gray-500 dark:text-gray-400">{result.sublabel}</span>
                    </div>
                    <span class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                      {result.paper_count} {result.paper_count !== 1 ? (t('common.papers.plural') || 'papers') : (t('common.paper.singular') || 'paper')}
                    </span>
                  </div>
                {:else if result.type === 'mutation'}
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">{t('lib_components_common_SearchBar.mutation')}</span>
                      <span class="text-sm font-mono font-semibold text-gray-900 dark:text-white">{result.canonical}</span>
                    </div>
                    <span class="text-xs text-gray-500 dark:text-gray-400">{result.sublabel}</span>
                  </div>
                {:else}
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      {#if phylopicPath(result.scientific_name, silhouettes)}
                        <img src={phylopicPath(result.scientific_name, silhouettes)} alt="" class="h-5 w-5 object-contain flex-shrink-0 dark:invert" />
                      {/if}
                      <div class="flex items-baseline gap-2 min-w-0">
                        <span class="text-sm font-medium text-gray-900 dark:text-white italic truncate">
                          {result.scientific_name}
                        </span>
                        {#if result.common_name}
                          <span class="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {sn(result.scientific_name, result.common_name)}
                          </span>
                        {/if}
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      {#if result.iucn}
                        {@const iucnInfo = getIUCNInfo(result.iucn)}
                        <span class="text-xs px-1.5 py-0.5 rounded font-bold {iucnInfo.bg} {iucnInfo.text}" title={t('iucn.' + (result.iucn || 'DD')) || iucnInfo.name}>
                          {result.iucn}
                        </span>
                      {/if}
                      {#if result.vaccination_target}
                        <span class="text-xs px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300" title={t('common.searchbar.vaccination.target') || 'Vaccination target species'}>
                          Vacc
                        </span>
                      {/if}
                      {#if result.detections > 0}
                        <span class="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
                          {result.detections.toLocaleString()} {result.detections !== 1 ? (t('common.detections.plural') || 'detections') : (t('common.detection.singular') || 'detection')}
                        </span>
                      {/if}
                    </div>
                  </div>
                  {#if result.order || result.family}
                    <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {[result.order, result.family].filter(Boolean).join(' › ')}
                    </div>
                  {/if}
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      {/if}

      <!-- Search all hint -->
      {#if query.length >= 2}
        <div class="px-4 py-2 border-t border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button
            class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            onclick={() => { navigate('species', null, { q: query }); close(); }}
          >
            Search all species for "{query}" →
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>
