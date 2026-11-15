<script>
  /**
   * Species comparison tool (FUTURE_TODO #5) — side-by-side view of 2–5
   * species: overview metrics (detections, genome, susceptibility, IUCN,
   * OrthoFinder), the host-panel gene presence matrix, and CSV export.
   *
   * Selection is URL-synced (#/compare?s=A|B|C) so comparisons are
   * shareable. Data: DuckDB tables (species, genomes, susceptibility,
   * gene_presence) plus iucn_status.json and orthofinder species_og_stats.
   */
  import { onMount } from 'svelte';
  import { trackEvent } from '../lib/analytics.js';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { dbStore, db } from '../lib/stores/db.js';
  import { navigate, updateParams, subscribe as routerSubscribe, getRoute } from '../lib/stores/router.js';
  import { formatNumber, formatN50, getIUCNInfo } from '../lib/utils/format.js';
  import { normalizeText } from '../lib/stores/search.js';

  const MAX = 5;

  let selected = $state([]);        // sci names
  let search = $state('');
  let candidates = $state([]);      // autocomplete pool from species_index
  let iucnMap = $state(null);
  let ogStats = $state(null);
  let rows = $state(null);          // per-species data bundles
  let genes = $state([]);           // union of panel genes across selection
  let diffsOnly = $state(false);
  let panelOnly = $state(true);      // importance>0 panel genes vs everything searched
  let loading = $state(false);
  let error = $state(null);

  const sciShort = (s) => s.replace(/([A-Z])\w*\s/, '$1. ');
  const IMP = { critical: 3, high: 2, standard: 1 };
  const impRank = (i) => IMP[i] || 0;

  function parseParams(p) {
    const s = (p.s || '').split('|').map(decodeURIComponent).filter(Boolean).slice(0, MAX);
    if (s.join('|') !== selected.join('|')) selected = s;
  }

  onMount(() => {
    (async () => {
      try {
        const [idx, iu, og] = await Promise.all([
          fetch('data/species_index.json').then((r) => r.json()),
          fetch('data/species/iucn_status.json').then((r) => r.ok ? r.json() : null),
          fetch('data/orthofinder/species_og_stats.json').then((r) => r.ok ? r.json() : null),
        ]);
        candidates = idx.map((s) => ({ sci: s.sci, com: s.com, det: s.det || 0 }))
          .sort((a, b) => b.det - a.det);
        iucnMap = iu ? new Map(Object.entries(iu.status || {})) : null;
        ogStats = og || null;
      } catch { /* picker still works with DuckDB-detected names */ }
    })();
    parseParams(getRoute().params || {});
    return routerSubscribe(({ params }) => parseParams(params || {}));
  });

  $effect(() => {
    const sel = [...selected];
    if (!sel.length) { rows = null; genes = []; return; }
    let alive = true;
    loading = true; error = null;
    (async () => {
      try {
        const bundles = await Promise.all(sel.map(loadSpeciesBundle));
        if (!alive) return;
        rows = bundles;
        // union of genes, ordered by importance then symbol
        const byGene = new Map();
        for (const b of bundles) {
          for (const c of b.presence) {
            const g = byGene.get(c.gene) || { gene: c.gene, importance: 0 };
            g.importance = Math.max(g.importance, impRank(c.importance));
            byGene.set(c.gene, g);
          }
        }
        genes = [...byGene.values()].sort(
          (a, b) => b.importance - a.importance || a.gene.localeCompare(b.gene));
      } catch (e) {
        console.error(e);
        if (alive) error = t('compare.load.error') || 'Failed to load comparison data.';
      } finally {
        if (alive) loading = false;
      }
    })();
    return () => { alive = false; };
  });

  async function loadSpeciesBundle(sci) {
    const esc = sci.replace(/'/g, "''");
    await dbStore.loadSpecies();
    const [spRow] = await db.query(
      `SELECT * FROM species WHERE scientific_name = '${esc}' LIMIT 1`);
    let genome = null;
    try {
      await dbStore.loadGenomes();
      [genome] = await db.query(
        `SELECT * FROM genomes WHERE LOWER(organism_name) = '${esc.toLowerCase()}'
         ORDER BY (is_representative) DESC, assembly_level DESC LIMIT 1`);
    } catch { /* genomes optional */ }
    let susc = null;
    try {
      await dbStore.loadSusceptibility();
      [susc] = await db.query(
        `SELECT * FROM susceptibility WHERE scientific_name = '${esc}' LIMIT 1`);
    } catch { /* susceptibility optional */ }
    const presence = await db.getPresenceCallsForSpecies(sci);
    return {
      sci,
      row: spRow || null,
      genome: genome || null,
      susc: susc || null,
      presence,
      byGene: new Map(presence.map((c) => [c.gene, c])),
      iucn: iucnMap?.get(sci) || null,
      og: ogStats?.[sci] || null,
    };
  }

  // --- selection management ---------------------------------------------
  const filteredCandidates = $derived.by(() => {
    const q = normalizeText(search.trim());
    if (q.length < 2) return [];
    return candidates
      .filter((c) => !selected.includes(c.sci))
      .filter((c) => normalizeText(c.sci).includes(q) || normalizeText(c.com || '').includes(q))
      .slice(0, 8);
  });

  function addSpecies(sci) {
    if (selected.length >= MAX || selected.includes(sci)) return;
    trackEvent('Compare', 'add', sci);
    selected = [...selected, sci];
    search = '';
    updateParams({ s: selected.join('|') });
  }
  function removeSpecies(sci) {
    selected = selected.filter((s) => s !== sci);
    updateParams({ s: selected.join('|') || null });
  }

  // --- derived views ------------------------------------------------------
  const shownGenes = $derived((panelOnly ? genes.filter((g) => g.importance >= 2) : genes)
    .filter((g) => {
      if (!diffsOnly) return true;
      const codes = rows.map((r) => r.byGene.get(g.gene)?.status);
      const first = codes.find((c) => c != null);
      return codes.some((c) => (c || '—') !== (first || '—'));
    }));

  const STATUS_STYLE = {
    FULL: 'bg-green-600 text-white',
    PARTIAL: 'bg-amber-500 text-white',
    FRAGMENT: 'bg-amber-500 text-white',
    NOT_FOUND: 'bg-gray-300 text-gray-600 dark:text-gray-400 dark:bg-gray-600 dark:text-gray-300',
  };
  const chip = (code) => STATUS_STYLE[code] || 'bg-gray-200 text-gray-500 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-400';

  // --- CSV export ---------------------------------------------------------
  function exportCsv() {
    trackEvent('Compare', 'export-csv', selected.join(' vs '));
    if (!rows?.length) return;
    const cols = rows.map((r) => r.sci);
    const esc = (v) => {
      const s = v == null ? '' : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const lines = [];
    lines.push(['metric', ...cols].map(esc).join(','));
    const M = [
      ['common name', (r) => r.row?.common_name],
      ['order', (r) => r.row?.order],
      ['family', (r) => r.row?.family],
      ['IUCN status', (r) => r.iucn || ''],
      ['HPAI detections', (r) => r.row?.detection_count ?? 0],
      ['countries', (r) => r.row?.country_count ?? 0],
      ['first detection', (r) => r.row?.first_detection],
      ['last detection', (r) => r.row?.last_detection],
      ['susceptibility score', (r) => r.susc?.susceptibility_score],
      ['susceptibility class', (r) => r.susc?.susceptibility_class],
      ['genome accession', (r) => r.genome?.assembly_accession || r.row?.genome_accession],
      ['assembly level', (r) => r.genome?.assembly_level || r.row?.assembly_level],
      ['scaffold N50', (r) => r.genome?.scaffold_n50 || r.row?.scaffold_n50],
      ['orthogroups', (r) => r.og?.n_ogs],
      ['panel genes in OGs', (r) => r.og?.n_panel_ogs],
    ];
    for (const [label, get] of M) lines.push([label, ...rows.map(get)].map(esc).join(','));
    lines.push('');
    lines.push(['gene', ...cols].map(esc).join(','));
    for (const g of genes) {
      lines.push([g.gene, ...rows.map((r) => r.byGene.get(g.gene)?.status || '')].map(esc).join(','));
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `roost-comparison-${rows.map((r) => r.sci.replace(/ /g, '_')).join('-vs-')}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }
</script>

<svelte:head><title>{t('compare.page.title') || 'Compare species'} — Roost</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent">
    {t('compare.page.title') || 'Compare species'}
  </h1>
  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-6">
    {t('compare.desc') || 'Side-by-side view of 2–'}{MAX} {t('compare.desc2') || 'species: detections, genome quality, susceptibility, IUCN status, OrthoFinder orthogroups and the host-panel gene presence matrix.'}
    {t('compare.desc3') || 'The URL carries your selection, so comparisons are shareable.'}
  </p>

  <!-- picker -->
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-6">
    <div class="flex flex-wrap items-center gap-2 mb-2">
      {#each selected as sci (sci)}
        <span class="inline-flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-full bg-blue-100 dark:bg-blue-900/40 text-sm">
          <button class="font-medium text-blue-800 dark:text-blue-200 hover:underline"
                  onclick={() => navigate('species-full', sci, {})}>
            {#if ogStats?.[sci]?.com || rows?.find((r) => r.sci === sci)?.row?.common_name}
              {ogStats?.[sci]?.com || rows?.find((r) => r.sci === sci)?.row?.common_name}
            {:else}
              <i>{sci}</i>
            {/if}
          </button>
          <button class="w-5 h-5 rounded-full bg-blue-600 text-white text-xs leading-none hover:bg-blue-700"
                  title={t('tip.compare.remove') || 'Remove'} onclick={() => removeSpecies(sci)}>×</button>
        </span>
      {:else}
        <span class="text-sm text-gray-500 dark:text-gray-400">{t('compare.pick.two') || 'Pick at least two species…'}</span>
      {/each}
      <span class="text-[11px] text-gray-500 dark:text-gray-400 ml-auto">{selected.length}/{MAX}</span>
    </div>
    <div class="relative">
      <input
        type="text" value={search} placeholder={t('search.placeholder.species.long') || 'Search species by common or scientific name…'}
        oninput={(e) => (search = e.target.value)}
        class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={selected.length >= MAX}
      />
      {#if filteredCandidates.length}
        <div class="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg max-h-72 overflow-auto">
          {#each filteredCandidates as c (c.sci)}
            <button
              class="w-full text-left px-4 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 text-sm flex justify-between gap-4"
              onclick={() => addSpecies(c.sci)}
            >
              <span><i>{c.sci}</i></span>
              <span class="text-gray-500 dark:text-gray-400">{c.com} {c.det ? `· ${formatNumber(c.det)} det` : ''}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
    {#if selected.length < 2}
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
        {t('compare.tip') || 'Tip: open any species page and use'} <span class="font-semibold">⚖ {t('compare.compare') || 'Compare'}</span> {t('compare.tip2') || 'to start from there.'}
      </p>
    {/if}
  </div>

  {#if error}
    <div class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">{error}</div>
  {/if}
  {#if loading}
    <div class="p-6 text-gray-500 dark:text-gray-400 animate-pulse">{t('compare.loading')}</div>
  {/if}

  {#if rows && rows.length >= 2 && !loading}
    <!-- overview -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 mb-6 overflow-x-auto">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Overview</h2>
        <button
          class="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          onclick={exportCsv}
        >{t('compare.export_csv')}</button>
      </div>
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            <th class="py-2 pr-4 font-medium">Metric</th>
            {#each rows as r (r.sci)}
              <th class="py-2 pr-4 font-semibold text-gray-700 dark:text-gray-200">
                <a class="hover:underline" href="#/species-full/{encodeURIComponent(r.sci)}">
                  <i>{sciShort(r.sci)}</i>
                </a>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
          {#each [
            ['Common name', (r) => r.row?.common_name || '—'],
            ['Taxonomy', (r) => [r.row?.order, r.row?.family].filter(Boolean).join(' · ') || '—'],
            ['IUCN status', (r) => r.iucn],
            ['HPAI detections', (r) => r.row?.detection_count ? formatNumber(r.row.detection_count) : '—'],
            ['Countries', (r) => r.row?.country_count || '—'],
            ['First detection', (r) => r.row?.first_detection || '—'],
            ['Last detection', (r) => r.row?.last_detection || '—'],
            ['Susceptibility', (r) => r.susc?.susceptibility_score != null
              ? `${Number(r.susc.susceptibility_score).toFixed(1)} (${r.susc.susceptibility_class || '?'})` : '—'],
            ['Genome assembly', (r) => r.genome?.assembly_accession || r.row?.genome_accession || '—'],
            ['Assembly level', (r) => r.genome?.assembly_level || r.row?.assembly_level || '—'],
            ['Scaffold N50', (r) => (r.genome?.scaffold_n50 || r.row?.scaffold_n50) ? formatN50(r.genome?.scaffold_n50 || r.row?.scaffold_n50) : '—'],
            ['Orthogroups (OrthoFinder)', (r) => r.og?.n_ogs ? formatNumber(r.og.n_ogs) : '—'],
            ['Panel genes in OGs', (r) => r.og?.n_panel_ogs != null ? `${r.og.n_panel_ogs}` : '—'],
          ] as [label, get] (label)}
            <tr>
              <td class="py-2 pr-4 text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{label}</td>
              {#each rows as r (r.sci)}
                <td class="py-2 pr-4 whitespace-nowrap">
                  {#if label === 'IUCN status' && r.iucn}
                    {@const info = getIUCNInfo(r.iucn)}
                    <span class="px-1.5 py-0.5 text-[11px] font-bold rounded {info.bg} {info.text}"
                          title={info.name}>{r.iucn}</span>
                  {:else}
                    <span class="text-gray-800 dark:text-gray-200">{get(r)}</span>
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- gene panel matrix -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 overflow-x-auto">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {t('compare.panel_presence')}
          <span class="font-normal text-gray-500 dark:text-gray-400">({shownGenes.length} genes)</span>
        </h2>
        <label class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 cursor-pointer">
          <input type="checkbox" bind:checked={diffsOnly} class="accent-blue-600" />
          {t('compare.diffs_only')}
        </label>
        <label class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 cursor-pointer" title="{t('compare.panel.title') || 'The curated host panel (critical + high importance genes) vs every gene searched'} in the presence pipeline">
          <input type="checkbox" bind:checked={panelOnly} class="accent-blue-600" />
          {t('compare.panel_only')}
        </label>
      </div>
      {#if !shownGenes.length}
        <p class="text-sm text-gray-500 dark:text-gray-400 py-4">{t('empty.compare.diffs') || 'No differing genes across this selection.'}</p>
      {:else}
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <th class="py-2 pr-4 font-medium">Gene</th>
              {#each rows as r (r.sci)}
                <th class="py-2 font-semibold text-gray-700 dark:text-gray-200"><i>{sciShort(r.sci)}</i></th>
              {/each}
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            {#each shownGenes as g (g.gene)}
              <tr>
                <td class="py-1.5 pr-4">
                  <a href="#/genes/{g.gene}"
                     class="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline text-xs">{g.gene}</a>
                </td>
                {#each rows as r (r.sci)}
                  {@const c = r.byGene.get(g.gene)}
                  <td class="py-1.5 pr-2">
                    {#if c}
                      <span class="inline-block px-2 py-0.5 text-[10px] font-bold rounded {chip(c.status)}"
                            title="{c.status} · {c.method || ''}{c.level ? ' · ' + c.level : ''}">{c.status}</span>
                    {:else}
                      <span class="text-gray-500 dark:text-gray-400">·</span>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
      <p class="mt-3 text-[11px] text-gray-500 dark:text-gray-400">
        {t('compare.status_legend')}
      </p>
    </div>
  {/if}
</div>
