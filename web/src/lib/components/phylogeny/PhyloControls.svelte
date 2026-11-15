<script>
  import { createEventDispatcher } from 'svelte';
import { t } from '../../stores/i18n.svelte.js';

  export let colorMode = 'detections';
  export let searchResults = null;
  export let filterGenome = false;
  export let filterDetected = false;

  const dispatch = createEventDispatcher();

  const colorModes = [
    { value: 'detected', label: 'Detected', icon: 'check' },
    { value: 'detections', label: 'Detection Count', icon: 'activity' },
    { value: 'susceptibility', label: 'Susceptibility', icon: 'alert' },
    { value: 'genome', label: 'Genome Available', icon: 'dna' },
  ];

  function handleFilterGenomeToggle() {
    dispatch('filterGenomeChange', { enabled: !filterGenome });
  }

  function handleFilterDetectedToggle() {
    dispatch('filterDetectedChange', { enabled: !filterDetected });
  }

  let searchInput = '';
  let searchTimeout;

  function handleSearchInput(e) {
    const value = e.target.value;
    searchInput = value;

    // Debounce search
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      dispatch('search', { query: value });
    }, 300);
  }

  function clearSearch() {
    searchInput = '';
    dispatch('search', { query: '' });
  }

  function handleColorModeChange(mode) {
    dispatch('colorModeChange', { mode });
  }

  function handleZoomIn() {
    dispatch('zoomIn');
  }

  function handleZoomOut() {
    dispatch('zoomOut');
  }

  function handleResetView() {
    dispatch('resetView');
  }

  function handleCollapseAll() {
    dispatch('collapseAll');
  }

  function handleExpandAll() {
    dispatch('expandAll');
  }

  function handleExport() {
    dispatch('export');
  }
</script>

<div class="phylo-controls bg-white dark:bg-gray-800 rounded-lg shadow p-4 space-y-4">
  <!-- Search -->
  <div>
    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
      {t('phylo.search.species') || 'Search Species'}
    </span>
    <div class="relative">
      <input
        type="text"
        value={searchInput}
        oninput={handleSearchInput}
        placeholder={t('search.placeholder.name') || 'Search by name...'}
        class="w-full pl-9 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-md
               bg-white dark:bg-gray-700 text-gray-900 dark:text-white
               placeholder-gray-400 dark:placeholder-gray-500
               focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      />
      <svg class="absolute left-3 top-2.5 h-4 w-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
      {#if searchInput}
        <button
          onclick={clearSearch}
          class="absolute right-2 top-2.5 text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          aria-label={t('tip.phylo.clear') || 'Clear search'}
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      {/if}
    </div>
    {#if searchResults}
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        {#if searchResults.matches.length > 0}
          {t('phylo.found.species') || 'Found'} {searchResults.matches.length} {t('common.species.word') || 'species'}
        {:else if searchResults.query}
          {t('phylo.no.species.found') || 'No species found'}
        {/if}
      </p>
    {/if}
  </div>

  <!-- Color Mode -->
  <div>
    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
      {t('phylo.branch.coloring') || 'Branch Coloring'}
    </span>
    <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
      {t('phylo.controls.gradient') || 'Colors branches from tips to root'}
    </p>
    <div class="flex flex-wrap gap-2">
      {#each colorModes as mode}
        <button
          onclick={() => handleColorModeChange(mode.value)}
          class="px-3 py-1.5 text-sm rounded-full transition-colors
                 {colorMode === mode.value
                   ? 'bg-blue-600 text-white'
                   : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
        >
          {t('phylo.mode.' + mode.value) || mode.label}
        </button>
      {/each}
    </div>
  </div>

  <!-- Filters -->
  <div>
    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
      {t('common.filters') || 'Filters'}
    </span>
    <label class="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={filterGenome}
        onchange={handleFilterGenomeToggle}
        class="w-4 h-4 text-blue-600 dark:text-blue-400 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
      />
      <span class="text-sm text-gray-700 dark:text-gray-300">
        {t('phylo.controls.genomeonly') || 'Only species with genome'}
      </span>
    </label>
    <label class="flex items-center gap-2 cursor-pointer mt-1">
      <input
        type="checkbox"
        checked={filterDetected}
        onchange={handleFilterDetectedToggle}
        class="w-4 h-4 text-red-600 dark:text-red-400 bg-gray-100 border-gray-300 rounded focus:ring-red-500 dark:bg-gray-700 dark:border-gray-600"
      />
      <span class="text-sm text-gray-700 dark:text-gray-300">
        {t('phylo.only.h5n1.detected') || 'Only H5N1-detected species'}
      </span>
    </label>
  </div>

  <!-- Zoom Controls -->
  <div>
    <span class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
      {t('phylo.view.controls') || 'View Controls'}
    </span>
    <div class="flex flex-wrap gap-2">
      <button
        onclick={handleZoomIn}
        class="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
        title={t('phylo.zoom.in') || 'Zoom In'}
      >
        <svg class="w-4 h-4 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
        </svg>
      </button>
      <button
        onclick={handleZoomOut}
        class="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
        title={t('phylo.zoom.out') || 'Zoom Out'}
      >
        <svg class="w-4 h-4 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
        </svg>
      </button>
      <button
        onclick={handleResetView}
        class="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
        title={t('tip.phylo.fit') || 'Fit to View'}
      >
        <svg class="w-4 h-4 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
        </svg>
      </button>
      <div class="w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>
      <button
        onclick={handleCollapseAll}
        class="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
        title={t('tip.phylo.collapse') || 'Collapse All'}
      >
        <svg class="w-4 h-4 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
        </svg>
      </button>
      <button
        onclick={handleExpandAll}
        class="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
        title={t('tip.phylo.expand') || 'Expand All'}
      >
        <svg class="w-4 h-4 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>
  </div>

  <!-- Export -->
  <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
    <button
      onclick={handleExport}
      class="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm
             bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300
             rounded hover:bg-gray-200 dark:hover:bg-gray-600"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      {t('phylo.export.newick') || 'Export Newick'}
    </button>
  </div>
</div>
