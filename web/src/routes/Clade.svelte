<script>
  import { trackEvent } from '../lib/analytics.js';
  import { t } from '../lib/stores/i18n.svelte.js';
  /**
   * CladeView — clade-specific gene absence/presence patterns.
   * Route: #/clade
   *
   * A heatmap of gene × taxonomic order showing the fraction of
   * genome-searched species in each order with each gene (FULL).
   * Highlights genes lost in entire clades while present elsewhere.
   *
   * Data: precomputed clade_matrix.json (built by
   * scripts/genes/build_clade_matrix.py using the FULL aves taxonomy,
   * not just detected species — includes kiwis, parrots, petrels etc).
   * No DuckDB needed — the JSON loads in <100ms.
   *
   * URL state: ?gene=SYM, ?order=XXX, ?losses=1, ?sort=, ?col=, ?dir=, ?q=
   */
  import { onMount } from 'svelte';
  import { navigate, getRoute, updateParams, subscribe as routerSubscribe } from '../lib/stores/router.js';

  let loading = $state(true);
  let error = $state(null);

  // Data (from precomputed JSON)
  let data = $state(null);       // {orders, genes, totalSearched, totalExcluded}
  let selectedGene = $state(null);
  let selectedOrder = $state(null);
  let selectedCell = $state(null);
  // analytics: gene × order cell drill-downs
  $effect(() => { if (selectedGene && selectedOrder) trackEvent('Clade', 'cell', `${selectedGene} | ${selectedOrder}`); });
  let geneDetail = $state(null);  // species detail (loaded lazily from DuckDB)
  let filterLosses = $state(false);
  let filterPanel = $state(false);   // core gene panel (critical/high importance)
  let searchText = $state('');
  let sortMode = $state('losses');
  let sortColumn = $state(null);
  let sortDir = $state('desc');
  let urlSyncReady = $state(false);

  const applyParams = (p = {}) => {
    selectedGene = p.gene || null;
    selectedOrder = p.order || null;
    filterLosses = p.losses === '1';
    filterPanel = p.panel === '1';
    const sm = ['losses', 'alpha', 'conservation', 'papers', 'column'].includes(p.sort) ? p.sort : 'losses';
    sortMode = sm;
    if (p.col && sm === 'column') {
      sortColumn = p.col;
      sortDir = p.dir === 'asc' ? 'asc' : 'desc';
    }
    searchText = p.q || '';
  };

  const applyRoute = (route) => {
    if (route.page !== 'clade' || !urlSyncReady) return;
    applyParams(route.params || {});
  };

  $effect(() => {
    void selectedGene; void selectedOrder; void filterLosses; void filterPanel; void sortMode;
    void searchText; void sortColumn; void sortDir;
    if (loading || !urlSyncReady) return;
    updateParams({
      gene: selectedGene || null,
      order: selectedOrder || null,
      losses: filterLosses ? '1' : null,
      panel: filterPanel ? '1' : null,
      sort: sortMode !== 'losses' ? sortMode : null,
      col: sortMode === 'column' ? sortColumn : null,
      dir: sortMode === 'column' ? sortDir : null,
      q: searchText || null,
    });
  });

  onMount(async () => {
    applyParams(getRoute()?.params || {});
    const cleanup = routerSubscribe(applyRoute);
    try {
      const r = await fetch('data/clade_matrix.json');
      if (!r.ok) throw new Error(`Failed to load clade matrix (${r.status})`);
      data = await r.json();
      loading = false;
      urlSyncReady = true;
    } catch (e) {
      error = e.message;
      loading = false;
    }
    return cleanup;
  });

  let orders = $derived(data?.orders || []);
  let filteredMatrix = $derived.by(() => {
    let rows = data?.genes || [];
    if (filterLosses) rows = rows.filter(r => r.nLosses > 0);
    if (filterPanel) rows = rows.filter(r => r.importance === 'critical' || r.importance === 'high');
    if (searchText) {
      const q = searchText.toLowerCase();
      rows = rows.filter(r => r.gene.toLowerCase().includes(q));
    }
    if (sortMode === 'column' && sortColumn) {
      const col = sortColumn;
      const dir = sortDir === 'desc' ? 1 : -1; // desc = most absent first
      rows = [...rows].sort((a, b) => {
        const av = a.orders[col] ?? 1;
        const bv = b.orders[col] ?? 1;
        return (av - bv) * dir || a.gene.localeCompare(b.gene);
      });
    } else {
      switch (sortMode) {
        case 'alpha': rows = [...rows].sort((a, b) => a.gene.localeCompare(b.gene)); break;
        case 'conservation': rows = [...rows].sort((a, b) => b.conservation - a.conservation); break;
        case 'papers': rows = [...rows.filter(r => !r.family)].sort((a, b) => (b.papers || 0) - (a.papers || 0) || a.gene.localeCompare(b.gene)); break;
        default: rows = [...rows].sort((a, b) => b.nLosses - a.nLosses || a.gene.localeCompare(b.gene));
      }
    }
    return rows;
  });

  let lossCount = $derived((data?.genes || []).filter(r => r.nLosses > 0).length);

  function cellColor(pct) {
    if (pct === undefined) return '#f1f5f9';
    if (pct >= 0.9) return '#16a34a';
    if (pct >= 0.7) return '#4ade80';
    if (pct >= 0.5) return '#a3e635';
    if (pct >= 0.3) return '#fbbf24';
    if (pct >= 0.1) return '#fb923c';
    return '#ef4444';
  }

  async function selectCell(gene, order) {
    selectedCell = { gene, order };
    selectedGene = gene;
    selectedOrder = order;
    geneDetail = null;
    try {
      const { db, dbStore } = await import('../lib/stores/db.js');
      await dbStore.loadGenePresence();
      const rows = await db.query(`
        SELECT gp.species, gp.status, gp.conf
        FROM gene_presence gp
        WHERE gp.gene = '${gene.replace(/'/g, "''")}'
        ORDER BY gp.species
      `);
      // Filter to just this order's species (using the species names from our data)
      const orderSp = new Set();
      // We need species → order mapping; use DuckDB
      await dbStore.loadSpecies();
      const spRows = await db.query(`SELECT scientific_name FROM species WHERE "order" = '${order.replace(/'/g, "''")}'`);
      for (const s of spRows) orderSp.add(s.scientific_name);
      geneDetail = rows.filter(r => orderSp.has(r.species));
    } catch { geneDetail = []; }
  }

  function shortOrder(name) {
    return name.replace('iformes', '').replace('imorphae', '');
  }
</script>

<svelte:head><title>{t('clade.page.title') || 'Clade-Specific Gene Patterns'} — Roost</title></svelte:head>

<div class="space-y-4">
  <div class="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('clade.page.title') || 'Clade-Specific Gene Patterns'}</h1>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        {#if loading}Loading…{:else if data}
          {filteredMatrix.length} {t('clade.genes.orders') || 'genes ×'} {orders.length} {t('clade.orders.word') || 'orders'} — {lossCount} {t('clade.absence.desc') || 'genes show clade-specific absence'}{filterPanel ? ` · ${t('clade.core.panel')}` : ''}
          <span class="text-xs text-gray-500 dark:text-gray-400 ml-1">({data.totalSearched} {t('clade.searched.species') || 'genome-searched species'}; {data.totalExcluded} {t('clade.mammals.excluded') || 'mammals excluded'})</span>
        {/if}
      </p>
    </div>
    <div class="flex flex-wrap gap-2 items-center">
      <input type="text" bind:value={searchText} placeholder={t('search.placeholder.genes.short') || 'Search genes…'}
        class="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white" />
      <select bind:value={sortMode} aria-label={t('routes.clade.sort.most.clade.losses')} class="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
        <option value="losses">{t('routes.clade.sort.most.clade.losses') || 'Sort: most clade losses'}</option>
        <option value="papers">{t('clade.sort.papers') || 'Sort: most researched (papers)'}</option>
        <option value="alpha">{t('clade.sort.alpha') || 'Sort: alphabetical'}</option>
        <option value="conservation">{t('clade.sort.conserved') || 'Sort: most conserved'}</option>
      </select>
      <button class="px-3 py-2 text-sm rounded-lg font-medium {filterPanel
        ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'}"
        title={t('clade.panel.tip') || 'Restrict to the curated core gene panel (critical + high importance genes)'}
        onclick={() => filterPanel = !filterPanel}>{filterPanel ? '✓ ' : ''}{t('clade.core.panel') || 'Core gene panel'}</button>
      <button class="px-3 py-2 text-sm rounded-lg font-medium {filterLosses
        ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'}"
        onclick={() => filterLosses = !filterLosses}>{filterLosses ? '✓ ' : ''}{t('clade.only.losses') || 'Only clade losses'}</button>
    </div>
  </div>

  {#if error}
    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-300">
      {error} — run <code>pixi run build-clade-matrix</code> to regenerate.
    </div>
  {:else if loading}
    <div class="flex items-center justify-center py-16">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  {:else}
    <!-- id used by the axe gate to include-scope the scan on this route
         (the 28k-node matrix below is exclusion-scoped data) -->
    <div id="clade-controls" class="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
      <span class="font-medium">{t('clade.presence.label') || 'Presence:'}</span>
      {#each [['#ef4444', '0-10%'], ['#fb923c', '10-30%'], ['#fbbf24', '30-50%'], ['#a3e635', '50-70%'], ['#4ade80', '70-90%'], ['#16a34a', '90-100%']] as [color, label]}
        <span class="inline-flex items-center gap-1"><span class="w-3 h-3 rounded-sm" style="background:{color}"></span>{label}</span>
      {/each}
      <span class="ml-4 italic">{t('clade.sort.hint') || 'Click a column header to sort · click a cell for species detail · a "clade loss"'} {t('clade.sort.hint.tail') || '= ≤10% present in an order while ≥30% overall'}</span>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded-xl shadow overflow-x-auto">
      <!-- id used by the axe gate to scope-scan around this ~28k-node matrix -->
      <table id="clade-matrix" class="text-xs" style="min-width: 100%;">
        <thead>
          <tr class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <th class="text-left py-2 px-3 font-medium text-gray-600 dark:text-gray-300 sticky left-0 bg-gray-50 dark:bg-gray-800 z-10">{t('genes.word') || 'Gene'}</th>
            <th class="py-2 px-1 font-medium text-gray-500 dark:text-gray-400 text-center" title={t('routes.clade.orders.where.this.gene') || 'Orders where this gene is lost'}>{t('clade.losses.col') || 'Losses'}</th>
            {#each orders as ord (ord.name)}
              <th class="py-2 px-1 font-medium cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20
                           {selectedOrder === ord.name || sortColumn === ord.name ? 'bg-blue-100 dark:bg-blue-900/40' : ''}"
                  title={`${ord.name} (${t('clade.n_searched_species', {n: ord.nSpecies})})`}
                  onclick={() => {
                    if (sortColumn === ord.name) {
                      if (sortDir === 'desc') { sortDir = 'asc'; }
                      else { sortColumn = null; sortMode = 'losses'; sortDir = 'desc'; }
                    } else {
                      sortColumn = ord.name; sortMode = 'column'; sortDir = 'desc';
                    }
                    selectedOrder = selectedOrder === ord.name ? null : ord.name;
                  }}>
                <div class="transform -rotate-45 origin-bottom-left whitespace-nowrap text-[10px] h-16 flex items-end">
                  <span class="origin-bottom-left translate-y-2">{shortOrder(ord.name)}</span>
                  {#if sortColumn === ord.name}<span class="ml-0.5 text-blue-600 dark:text-blue-400">{sortDir === 'desc' ? '▼' : '▲'}</span>{/if}
                </div>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          {#each filteredMatrix as row (row.gene)}
            <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/30 cursor-pointer {selectedGene === row.gene ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
                onclick={() => selectedGene = selectedGene === row.gene ? null : row.gene}>
              <td class="py-1.5 px-3 font-mono font-medium text-gray-900 dark:text-white sticky left-0 {selectedGene === row.gene ? 'bg-blue-50 dark:bg-gray-800' : 'bg-white dark:bg-gray-800'} z-10">{row.gene}</td>
              <td class="py-1.5 px-1 text-center">
                {#if row.nLosses > 0}
                  <span class="px-1.5 py-0.5 rounded-full text-[10px] font-semibold {row.nLosses >= 5 ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-300' : row.nLosses >= 2 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">{row.nLosses}</span>
                {:else}<span class="text-gray-300">—</span>{/if}
              </td>
              {#each orders as ord (ord.name)}
                {@const pct = row.orders[ord.name]}
                <td class="py-1.5 px-0.5 text-center" onclick={(e) => { e.stopPropagation(); selectCell(row.gene, ord.name); }}>
                  <div class="w-full h-6 rounded-sm mx-auto transition-transform hover:scale-110"
                       style="background: {cellColor(pct)}; {selectedGene === row.gene && selectedOrder === ord.name ? 'outline: 2px solid #2563eb; outline-offset: 1px;' : ''}"
                       title="{row.gene} in {ord.name}: {pct !== undefined ? Math.round(pct * 100) + '%' : (t('clade.no.data') || 'no data')}"></div>
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if selectedCell && geneDetail}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
        <div class="flex items-start justify-between gap-3 mb-3">
          <div>
            <h3 class="font-semibold text-gray-900 dark:text-white"><span class="font-mono">{selectedCell.gene}</span> in {selectedCell.order}</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {geneDetail.filter(d => d.status === 'FULL').length} of {geneDetail.length} species have this gene
            </p>
          </div>
          <button class="text-gray-500 dark:text-gray-400 hover:text-gray-600" onclick={() => { selectedCell = null; geneDetail = null; selectedGene = null; selectedOrder = null; }}>✕</button>
        </div>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
          {#each geneDetail as sp}
            {@const nfHi = sp.status === 'NOT_FOUND' && sp.conf === 'high'}
            <a href="#/species-full/{encodeURIComponent(sp.species)}"
               title={nfHi ? t('phylo.legend.nf.hi.tip') : (sp.status === 'NOT_FOUND' ? t('phylo.legend.nf.lo.tip') : '')}
               class="flex items-center gap-2 text-xs px-2 py-1.5 rounded {sp.status === 'FULL' ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : sp.status === 'FRAGMENT' ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800' : nfHi ? 'bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-700' : 'bg-red-50 dark:bg-red-900/20 border border-dashed border-red-300 dark:border-red-700'}">
              <span class="w-4 text-center">{sp.status === 'FULL' ? '✓' : sp.status === 'FRAGMENT' ? '~' : nfHi ? '✗' : '✗?'}</span>
              <span class="italic flex-1 truncate">{sp.species}</span>
            </a>
          {/each}
        </div>
        <div class="mt-3 flex gap-2">
          <a href="#/genes/{encodeURIComponent(selectedCell.gene)}" class="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700">View {selectedCell.gene} gene page →</a>
          <a href="#/phylogeny?gene={encodeURIComponent(selectedCell.gene)}" class="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700">{t('routes.clade.view.on.phylogeny') || 'View on phylogeny →'}</a>
        </div>
      </div>
    {/if}

    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
      <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">Methodology</h3>
      <div class="text-sm text-gray-600 dark:text-gray-300 space-y-2">
        <p>{t('routes.clade.each.cell.shows.the') || 'Each cell shows the'}<strong>{t('routes.clade.percentage.of.genome.searched') || 'percentage of genome-searched species'}</strong> {t('clade.protein.match') || "in that order with a full-length BLAST match to the gene's reference protein. On"}ly species with sequenced genomes are counted — the denominator is searched species, not all species in the order.</p>
        <p>A <strong>clade-specific loss</strong> {t('clade.widespread.badge') || '(flagged with a badge) means the gene is present in ≥30% of all searched species'} but absent in ≥90% of one order — evidence of lineage-specific gene loss rather than general non-conservation.</p>
        <p>Taxonomy from the full NCBI Aves taxonomy ({data?.totalSearched || '…'} searched species across {orders.length} orders), not just HPAI-detected species. {data?.totalExcluded || '…'} searched species (mammals, unmatched names) are excluded.</p>
        <p class="text-xs text-gray-500 dark:text-gray-400 italic">{t('clade.caveats') || 'Caveats: BLAST-based calls, not confirmed losses. Scaffold-level genomes may mis'}s genes. Orders with 3-5 species are less reliable than large ones. Annotation gaps in reference proteins can masquerade as losses.</p>
      </div>
    </div>
  {/if}
</div>
