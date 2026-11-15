<script>
  import { trackEvent } from '../lib/analytics.js';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { navigate, getRoute, updateParams, subscribe as routerSubscribe } from '../lib/stores/router.js';
  import PhyloTree from '../lib/components/phylogeny/PhyloTree.svelte';
  import PhyloControls from '../lib/components/phylogeny/PhyloControls.svelte';
  import PhyloLegend from '../lib/components/phylogeny/PhyloLegend.svelte';
  import SpeciesDetail from '../lib/components/species/SpeciesDetail.svelte';
  import { db } from '../lib/stores/db.js';

  // State
  let colorMode = $state('detected');
  let searchQuery = $state('');
  let searchResults = $state(null);
  let selectedSpeciesId = $state(null);
  let treeComponent = $state(null);
  let filterGenome = $state(false);
  let filterDetected = $state(false);

  // --- Gene overlay (#/phylogeny?gene=SYM from the gene page) ---
  let overlayGene = $state(null);        // symbol or null
  // analytics: which genes people trace across the tree
  $effect(() => { if (overlayGene) trackEvent('Phylogeny', 'view', overlayGene); });
  let geneStatuses = $state(null);        // {Tree_Name: FULL|FRAGMENT|NOT_FOUND}
  let geneOverlayCounts = $state(null);   // {full, fragment, not_found, mapped}
  let filterGeneCalls = $state(false);    // default ON for the overlay action
  let geneLoading = $state(false);
  let overlaySeq = 0;                     // race guard for fast gene switches

  // --- URL state (#/phylogeny?gene=DDX58&color=susceptibility&calls=0&
  //     genome=1&detected=1&q=…) — shareable, reproducible views. URL is
  //     the source of truth on load/SPA-nav; state flows back via $effect.
  const COLOR_MODES = ['detected', 'detections', 'susceptibility', 'genome'];
  let urlSyncReady = $state(false);

  onMount(() => {
    urlSyncReady = true;
    applyRoute(getRoute());
    return routerSubscribe(applyRoute);
  });

  function applyRoute(route) {
    if (route?.page !== 'phylogeny' || !urlSyncReady) return;
    const p = route.params || {};
    const nextGene = p.gene ? String(p.gene).toUpperCase() : null;
    const nextColor = COLOR_MODES.includes(p.color)
      ? p.color : (nextGene ? 'gene' : 'detected');
    const nextCalls = nextGene ? p.calls !== '0' : false;
    const nextGenome = p.genome === '1';
    const nextDetected = p.detected === '1';
    const nextQ = p.q || '';
    if (nextGene === overlayGene && nextColor === colorMode
        && nextCalls === filterGeneCalls && nextGenome === filterGenome
        && nextDetected === filterDetected && nextQ === searchQuery) return;
    if (nextGene !== overlayGene) {
      if (nextGene) startGeneOverlay(nextGene);
      else clearGeneOverlay();
    }
    colorMode = nextColor;
    filterGeneCalls = nextCalls;
    filterGenome = nextGenome;
    filterDetected = nextDetected;
    searchQuery = nextQ;
  }

  // state → URL (echo-guarded by applyRoute's no-op comparison)
  $effect(() => {
    void overlayGene; void colorMode; void filterGeneCalls;
    void filterGenome; void filterDetected; void searchQuery;
    if (!urlSyncReady) return;
    updateParams({
      gene: overlayGene || null,
      color: (colorMode !== 'detected' && colorMode !== 'gene') ? colorMode : null,
      calls: overlayGene && !filterGeneCalls ? '0' : null,
      genome: filterGenome ? '1' : null,
      detected: filterDetected ? '1' : null,
      q: searchQuery || null,
    });
  });

  async function startGeneOverlay(symbol) {
    const seq = ++overlaySeq;
    overlayGene = symbol;
    colorMode = 'gene';
    filterGeneCalls = true;   // default: only species with a call for this gene
    geneLoading = true;
    try {
      // One gene's calls from the DuckDB parquet matrix — a few hundred
      // rows, not a 13 MB catalogue fetch (Phase 2 Step 3)
      const calls = await db.getPresenceCallsForGene(symbol);
      if (seq !== overlaySeq) return;   // a newer gene took over
      const statuses = {};
      let full = 0, frag = 0, nf = 0, nfHi = 0;
      for (const c of calls || []) {
        const key = c.species.replace(/[\s]+/g, '_');
        let st = c.status;
        // absence-confidence split: a non-detection on a well-searched
        // genome (control-gene recovery ≥90%) is strong evidence of
        // absence; anything else stays visually distinct so low-
        // confidence non-detections are never read as established losses.
        if (st === 'NOT_FOUND' && c.conf === 'high') { st = 'NOT_FOUND_HI'; nfHi++; }
        statuses[key] = st;
        if (c.status === 'FULL') full++;
        else if (c.status === 'FRAGMENT') frag++;
        else if (c.status === 'NOT_FOUND') nf++;
      }
      geneStatuses = statuses;
      geneOverlayCounts = { full, fragment: frag, not_found: nf, not_found_hi: nfHi, mapped: full + frag + nf };
    } catch {
      if (seq === overlaySeq) geneStatuses = {};
    }
    if (seq === overlaySeq) geneLoading = false;
  }

  function clearGeneOverlay() {
    overlayGene = null;
    geneStatuses = null;
    geneOverlayCounts = null;
    filterGeneCalls = false;
    colorMode = 'detected';
  }

  // Handle search
  function handleSearch(event) {
    searchQuery = event.detail.query;
  }

  // Handle color mode change
  function handleColorModeChange(event) {
    colorMode = event.detail.mode;
  }

  // Handle genome filter toggle
  function handleFilterGenomeChange(event) {
    filterGenome = event.detail.enabled;
  }

  function handleFilterDetectedChange(event) {
    filterDetected = event.detail.enabled;
  }

  // Handle species selection from tree
  function handleSpeciesSelect(event) {
    const { taxonId, scientificName } = event.detail;
    selectedSpeciesId = taxonId || scientificName;
  }

  // Handle search results
  function handleSearchResults(event) {
    searchResults = event.detail;
  }

  // Tree control handlers
  function handleZoomIn() {
    treeComponent?.zoomIn();
  }

  function handleZoomOut() {
    treeComponent?.zoomOut();
  }

  function handleResetView() {
    treeComponent?.resetView();
  }

  function handleCollapseAll() {
    treeComponent?.collapseAll();
  }

  function handleExpandAll() {
    treeComponent?.expandAll();
  }

  function handleExport() {
    const newick = treeComponent?.exportNewick();
    if (newick) {
      // Create download
      const blob = new Blob([newick], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'roost_phylogeny.tre';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  }

  function closeSpeciesDetail() {
    selectedSpeciesId = null;
  }
</script>

<svelte:head><title>{t('routes_Phylogeny.phylogeny') || 'Phylogeny'} — Roost</title></svelte:head>

<div class="space-y-6">
  <!-- Mobile notice (these graphs need desktop viewport) -->
  <div class="lg:hidden bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm text-amber-700 dark:text-amber-300">
    {t('phylogeny.mobile.notice.pre')}
    <a href="#/species" class="underline">{t('phylogeny_page.species.explorer')}</a> {t('phylogeny.mobile.notice.and')}
    <a href="#/papers" class="underline">{t('phylogeny_page.papers')}</a> {t('phylogeny.mobile.notice.post')}
  </div>
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('routes_Phylogeny.phylogeny')}</h1>
    <p class="text-gray-600 dark:text-gray-300 mt-1">
      {t('phylogeny.subtitle') || 'Interactive phylogenetic tree of bird species with H5N1 detection data'}
    </p>
  </div>

  <!-- Gene overlay banner + legend -->
  {#if overlayGene}
    <div class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="flex items-center gap-2 flex-wrap">
          <span class="px-2 py-0.5 text-xs font-bold rounded bg-emerald-600 text-white">{t('phylo.gene.overlay') || 'GENE OVERLAY'}</span>
          <span class="font-mono font-semibold text-gray-900 dark:text-white">{overlayGene}</span>
          {#if geneLoading}<span class="text-xs text-gray-500 dark:text-gray-400">{t('phylogeny_page.loading.presence.calls')}</span>
          {:else if geneOverlayCounts}
            <span class="text-xs text-gray-600 dark:text-gray-300">
              {geneOverlayCounts.full} {t('presence.full.word') || 'present'} · {geneOverlayCounts.fragment} {t('presence.fragment.word') || 'fragment'} · {geneOverlayCounts.not_found} {t('presence.absent.word') || 'absent'}
              ({geneOverlayCounts.not_found_hi} {t('phylo.absent.highconf')})
              · {geneOverlayCounts.mapped} {t('phylo.species.with.calls') || 'species with calls'}
            </span>
          {/if}
        </div>
        <div class="flex items-center gap-3 mt-2">
          <label class="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300 cursor-pointer">
            <input type="checkbox" bind:checked={filterGeneCalls} />
            {t('phylo.only.species.with') || 'Only species with'} {overlayGene} {t('phylo.calls') || 'calls'}
          </label>
          <span class="text-xs text-gray-500 dark:text-gray-400">{t('routes.phylogeny.uncheck.to.place.the') || '← uncheck to place the gene in full clade context'}</span>
        </div>
      </div>
      <button
        class="px-3 py-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 rounded-lg hover:bg-emerald-100 dark:hover:bg-emerald-900/40"
        onclick={() => clearGeneOverlay()}>
        ✕ {t('phylo.clear.overlay') || 'Clear overlay'}
      </button>
    </div>
    <div class="flex flex-wrap gap-3 text-xs text-gray-600 dark:text-gray-300">
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm" style="background:#16a34a"></span> {t('presence.full') || 'Present'}</span>
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm" style="background:#f59e0b"></span>{t('routes.phylogeny.fragment.partial.pseudogene') || 'Fragment (partial / pseudogene?)'}</span>
      <span class="flex items-center gap-1.5" title={t('phylo.legend.nf.hi.tip')}><span class="w-3 h-3 rounded-sm" style="background:#b91c1c"></span> {t('phylo.legend.nf.hi')}</span>
      <span class="flex items-center gap-1.5" title={t('phylo.legend.nf.lo.tip')}><span class="w-3 h-3 rounded-sm" style="background:#fca5a5"></span> {t('phylo.legend.nf.lo')}</span>
      <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm" style="background:#d1d5db"></span> {t('phylo.not.searched') || 'Not searched'}</span>
    </div>
  {/if}

  <!-- Main content -->
  <div class="flex flex-col lg:flex-row gap-6">
    <!-- Sidebar -->
    <div class="lg:w-72 flex-shrink-0 space-y-4">
      <PhyloControls
        {colorMode}
        {searchResults}
        {filterGenome}
        {filterDetected}
        on:search={handleSearch}
        on:colorModeChange={handleColorModeChange}
        on:filterGenomeChange={handleFilterGenomeChange}
        on:filterDetectedChange={handleFilterDetectedChange}
        on:zoomIn={handleZoomIn}
        on:zoomOut={handleZoomOut}
        on:resetView={handleResetView}
        on:collapseAll={handleCollapseAll}
        on:expandAll={handleExpandAll}
        on:export={handleExport}
      />
      <PhyloLegend {colorMode} />

      <!-- Data source info -->
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('phylogeny_page.data.source')}</h3>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          {t('phylo.data.source.desc') || 'Tree based on avian phylogeny with species from our detection database. Colors reflect detection counts and metadata from aggregated surveillance data.'}
        </p>
        <a
          href="https://birdtree.org/"
          target="_blank"
          rel="noopener noreferrer"
          class="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-2 inline-block"
        >
          {t('phylo.learn.more') || 'Learn more at'} BirdTree.org →
        </a>
      </div>
    </div>

    <!-- Tree container -->
    <div class="flex-1 min-h-[600px] lg:min-h-[700px]">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow h-full">
        <PhyloTree
          bind:this={treeComponent}
          {colorMode}
          {searchQuery}
          {filterGenome}
          {filterDetected}
          {geneStatuses}
          {filterGeneCalls}
          on:speciesSelect={handleSpeciesSelect}
          on:searchResults={handleSearchResults}
        />
      </div>
    </div>
  </div>

  <!-- Instructions -->
  <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
    <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('phylogeny_page.how.to.use')}</h3>
    <div class="grid md:grid-cols-3 gap-4 text-sm text-gray-600 dark:text-gray-400">
      <div class="flex items-start gap-2">
        <span class="text-blue-600 dark:text-blue-400">1.</span>
        <span><strong>{t('routes_Phylogeny.search')}</strong>{t('routes.phylogeny.for.species.by.common') || 'for species by common or scientific name to highlight them on the tree.'}</span>
      </div>
      <div class="flex items-start gap-2">
        <span class="text-blue-600 dark:text-blue-400">2.</span>
        <span><strong>{t('phylogeny_page.change.colors')}</strong>{t('routes.phylogeny.to.visualize.detection.counts') || 'to visualize detection counts, susceptibility, or genome availability.'}</span>
      </div>
      <div class="flex items-start gap-2">
        <span class="text-blue-600 dark:text-blue-400">3.</span>
        <span><strong>{t('phylogeny_page.click.species')}</strong>{t('routes.phylogeny.to.view.detailed.detection') || 'to view detailed detection history, genome info, and external links.'}</span>
      </div>
    </div>
  </div>
</div>

<!-- Species detail modal -->
{#if selectedSpeciesId}
  <SpeciesDetail speciesId={selectedSpeciesId} onclose={closeSpeciesDetail} />
{/if}
