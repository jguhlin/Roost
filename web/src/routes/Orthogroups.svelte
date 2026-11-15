<script>
  /**
   * Orthogroup detail page: #/orthogroups/OGxxxxxxxx
   *
   * Loads data/orthogroups/{OG}.json (members, copy counts, tree) plus
   * orthofinder/species_map.json. Presence grid ordered by the shipped
   * species tree (leaf order), colour = copy number. MSA lazily fetched
   * (.fa.zst + fzstd) via MsaViewer.
   */
  import { onMount } from 'svelte';
  import { trackEvent } from '../lib/analytics.js';
  import { navigate } from '../lib/stores/router.js';
  import GeneTree from '../lib/components/orthogroups/GeneTree.svelte';
  import MsaViewer from '../lib/components/orthogroups/MsaViewer.svelte';
  import { t } from '../lib/stores/i18n.svelte.js';

  let { og = null } = $props();

  // ---- index view state (#/orthogroups with no id): panel-gene directory ----
  let directory = $state(null);    // [{sym, og, confidence, n_species_hit}]
  let dirSearch = $state('');
  let dirLoading = $state(false);
  $effect(() => {
    const id = og;
    if (id) { directory = null; loadAll(); return; }
    if (directory || dirLoading) return;
    dirLoading = true;
    (async () => {
      try {
        const r = await fetch('data/gene_orthogroups.json');
        if (r.ok) {
          const d = await r.json();
          directory = Object.entries(d.genes || {})
            .map(([sym, m]) => ({ sym, og: m.og, confidence: m.confidence,
                                 tier: m.tier, n_species_hit: m.n_species_hit }))
            .sort((a, b) => a.sym.localeCompare(b.sym));
        }
      } catch { /* directory stays empty */ }
      dirLoading = false;
    })();
  });

  const filteredDirectory = $derived.by(() => {
    if (!directory) return [];
    const q = dirSearch.trim().toLowerCase();
    if (!q) return directory;
    return directory.filter((d) => d.sym.toLowerCase().includes(q) || d.og.toLowerCase().includes(q));
  });


  let data = $state(null);
  let smap = $state(null);          // species_map entries in of_id order
  let order = $state(null);         // phylogenetic order: array of of_id
  let error = $state(null);
  let loading = $state(true);
  let tab = $state('presence');     // presence | tree | msa | members
  let memberSearch = $state('');
  let memberShow = $state(40);

  const byLabel = new Map();

  async function loadAll() {
    loading = true; error = null; data = null;
    if (!og) { loading = false; return; }   // index view: no detail fetch
    trackEvent('Orthogroup', 'view', og);
    try {
      const [dRes, sRes] = await Promise.all([
        fetch(`data/orthogroups/${og}.json`),
        fetch('data/orthofinder/species_map.json'),
      ]);
      if (!dRes.ok) throw new Error(`Orthogroup ${og} not found (HTTP ${dRes.status})`);
      data = await dRes.json();
      smap = await sRes.json();
      byLabel.clear();
      for (const s of smap) byLabel.set(s.label, s);
      // phylogenetic ordering from species tree leaves
      try {
        const tRes = await fetch('data/orthofinder/species_tree.txt');
        const txt = await tRes.text();
        const labels = [];
        const re = /[(,]\s*([A-Za-z_]+__[A-Za-z0-9_.]+)\s*:/g;
        let m;
        while ((m = re.exec(txt))) labels.push(m[1]);
        const ids = labels.map((l) => byLabel.get(l)?.of_id).filter((x) => x !== undefined);
        if (ids.length >= smap.length * 0.95) {
          const seen = new Set(ids);
          for (const s of smap) if (!seen.has(s.of_id)) ids.push(s.of_id);
          order = ids;
        }
      } catch { /* fall back to of_id order */ }
      if (!order) order = smap.map((s) => s.of_id);
      memberSearch = ''; memberShow = 40; tab = 'presence';
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  $effect(() => { if (og) loadAll(); });

  const ofEntry = (ofId) => smap?.find((s) => s.of_id === ofId);
  const countAt = (ofId) => data ? data.counts[ofId] : 0;

  function cellColor(n) {
    if (!n) return 'bg-gray-100 dark:bg-gray-700/40';
    if (n === 1) return 'bg-emerald-500';
    if (n === 2) return 'bg-emerald-300';
    if (n === 3) return 'bg-amber-400';
    if (n === 4) return 'bg-orange-500';
    return 'bg-red-500';
  }

  function cellTitle(ofId) {
    const s = ofEntry(ofId);
    return `${s?.sci} — ${countAt(ofId)} cop${countAt(ofId) === 1 ? 'y' : 'ies'}`;
  }

  const membersFiltered = $derived(
    !data ? [] : data.members.filter((m) => {
      if (!memberSearch) return true;
      const q = memberSearch.toLowerCase();
      const s = ofEntry(m.s);
      return (m.a || '').toLowerCase().includes(q)
        || (m.p || '').toLowerCase().includes(q)
        || (s?.sci || '').toLowerCase().includes(q)
        || (s?.com || '').toLowerCase().includes(q);
    })
  );

  const nCopiesHist = $derived.by(() => {
    const h = [0, 0, 0, 0, 0]; // absent, 1, 2, 3, 4+
    if (!data) return h;
    for (const c of data.counts) h[c === 0 ? 0 : c >= 4 ? 4 : c]++;
    return h;
  });
</script>

<svelte:head><title>{t('og.page.title') || 'Orthogroups'} — Roost</title></svelte:head>

<div class="max-w-7xl mx-auto">
  {#if !og}
    <!-- Index: panel-gene → orthogroup directory -->
    <div class="px-4 py-8">
      <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent">
        Orthogroups
      </h1>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-4 max-w-3xl">
        {t('orthogroups.intro', {n: directory ? directory.length : 799})}
      </p>
      {#if dirLoading}
        <div class="p-6 text-gray-500 dark:text-gray-400 animate-pulse">{t('routes.orthogroups.loading.gene.orthogroup.map') || 'Loading gene–orthogroup map…'}</div>
      {:else if directory}
        <input
          type="text" value={dirSearch} placeholder={t('search.placeholder.orthogroups') || 'Filter by gene symbol or orthogroup id…'}
          oninput={(e) => (dirSearch = e.target.value)}
          class="w-full sm:w-96 px-4 py-2 mb-4 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
        />
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">{t('orthogroups.n_genes', {n: filteredDirectory.length})}</p>
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 max-h-[70vh] overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-white dark:bg-gray-800">
              <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                <th class="py-2 pr-4 font-medium">Gene</th>
                <th class="py-2 pr-4 font-medium">Orthogroup</th>
                <th class="py-2 pr-3 font-medium text-right">{t('orthogroups.col_species_hit')}</th>
                <th class="py-2 font-medium">{t('orthogroups.th.confidence')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
              {#each filteredDirectory as d (d.sym)}
                <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/20">
                  <td class="py-1.5 pr-4">
                    <a class="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline" href="#/genes/{d.sym}">{d.sym}</a>
                  </td>
                  <td class="py-1.5 pr-4">
                    <a class="font-mono hover:underline" href="#/orthogroups/{d.og}">{d.og}</a>
                  </td>
                  <td class="py-1.5 pr-3 text-right tabular-nums text-gray-500 dark:text-gray-400">{d.n_species_hit}</td>
                  <td class="py-1.5 text-xs">
                    <span class="px-1.5 py-0.5 rounded {d.confidence === 'high' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : d.confidence === 'medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">{t('orthogroups.tier.' + d.confidence)}</span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {:else if loading}
    <div class="p-8 text-center text-gray-500 dark:text-gray-400">{t('orthogroups.loading')}</div>
  {:else if error}
    <div class="p-8">
      <div class="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-300">
        {error}
      </div>
      <button class="mt-4 text-sm text-sky-600 dark:text-sky-400 hover:underline"
        onclick={() => navigate('orthogroups', null, {})}>{t('orthogroups.all_link')}</button>
    </div>
  {:else if data}
    <!-- header -->
    <div class="flex flex-wrap items-baseline gap-3 mb-1">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{data.og}</h1>
      {#each data.genes as g}
        <button class="px-2 py-0.5 rounded-full bg-sky-100 dark:bg-sky-900/50 text-sky-700 dark:text-sky-300 text-sm font-medium hover:bg-sky-200 dark:hover:bg-sky-900"
          onclick={() => navigate('genes', encodeURIComponent(g), {})}>{g}</button>
      {/each}
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      {t('orthogroups.stats_line', {a: data.n_species_present, b: data.n_species, p: data.n_proteins.toLocaleString(), c: data.max_copies})}
      {#if data.single_copy}· <span class="text-emerald-600 dark:text-emerald-400">{t('orthogroups.single_copy')}</span>{/if}
      · <span class="text-gray-500 dark:text-gray-400">{t('routes.orthogroups.orthofinder.bird.run.root') || 'OrthoFinder 463-bird run (root-corrected)'}</span>
    </p>

    <!-- tabs -->
    <div class="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-4">
      {#each [['presence', t('og.tab.presence') || 'Presence'], ['tree', data.has_tree ? (t('og.tab.tree') || 'Gene tree') : (t('og.tab.tree.none') || 'Gene tree (none)')], ['msa', data.has_msa ? (t('og.tab.msa') || 'Alignment') : (t('og.tab.msa.none') || 'Alignment (none)')], ['members', (t('og.tab.members') || 'Members') + ` (${data.members.length})`]] as [id, label]}
        <button class="px-3 py-2 text-sm rounded-t-lg -mb-px border-x border-t
          {tab === id ? 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 font-medium' : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'}"
          onclick={() => (tab = id)}>{label}</button>
      {/each}
    </div>

    {#if tab === 'presence'}
      <div class="grid md:grid-cols-3 gap-4">
        <div class="md:col-span-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('orthogroups.copy_across')} <span class="text-gray-500 dark:text-gray-400 font-normal">{t('orthogroups.ordered_by_tree')}</span>
          </div>
          <div class="flex flex-wrap gap-[3px]">
            {#each order as ofId (ofId)}
              <div class="w-[14px] h-[14px] rounded-[3px] {cellColor(countAt(ofId))}"
                title={cellTitle(ofId)}></div>
            {/each}
          </div>
          <div class="flex items-center gap-3 mt-3 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-gray-100 dark:bg-gray-700/40 inline-block"></span>absent</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-emerald-500 inline-block"></span>1</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-emerald-300 inline-block"></span>2</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-amber-400 inline-block"></span>3</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-red-500 inline-block"></span>4+</span>
          </div>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('orthogroups.copy_distribution')}</div>
          <div class="space-y-1.5">
            {#each [['absent', nCopiesHist[0]], ['1 copy', nCopiesHist[1]], ['2 copies', nCopiesHist[2]], ['3 copies', nCopiesHist[3]], ['4+ copies', nCopiesHist[4]]] as [label, n]}
              <div class="flex items-center gap-2 text-xs">
                <span class="w-20 text-gray-500 dark:text-gray-400 text-right">{label}</span>
                <div class="flex-1 h-3 bg-gray-100 dark:bg-gray-700 rounded overflow-hidden">
                  <div class="h-full {label === 'absent' ? 'bg-gray-300 dark:bg-gray-600' : 'bg-emerald-500'}"
                    style="width:{(n / data.n_species * 100).toFixed(1)}%"></div>
                </div>
                <span class="w-8 text-gray-500 dark:text-gray-400">{n}</span>
              </div>
            {/each}
          </div>
        </div>
      </div>
    {:else if tab === 'tree'}
      {#if data.has_tree}
        <GeneTree newick={data.tree} leafMeta={Object.fromEntries(data.members.map((m) => [m.m, m]))} />
      {:else}
        <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-500 dark:text-gray-400">
          {t('og.no.tree') || 'No resolved gene tree was exported for this orthogroup (small or fragmented family).'}
        </div>
      {/if}
    {:else if tab === 'msa'}
      {#if data.has_msa}
        <MsaViewer {og} leafMeta={Object.fromEntries(data.members.map((m) => [m.m, m]))} />
      {:else}
        <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm text-gray-500 dark:text-gray-400">
          {t('og.no.alignment') || 'No alignment exported for this orthogroup.'}
        </div>
      {/if}
    {:else}
      <!-- members -->
      <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
        <div class="p-3 border-b border-gray-200 dark:border-gray-700">
          <input class="w-full max-w-sm px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm"
            placeholder={t('search.placeholder.og.species') || 'Search species, accession, product…'} bind:value={memberSearch}>
          <span class="ml-2 text-xs text-gray-500 dark:text-gray-400">{membersFiltered.length.toLocaleString()} of {data.members.length.toLocaleString()}</span>
        </div>
        <div class="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400 text-xs uppercase">
              <tr>
                <th class="text-left px-3 py-2">Species</th>
                <th class="text-left px-3 py-2">Protein</th>
                <th class="text-left px-3 py-2">Product (NCBI annotation)</th>
              </tr>
            </thead>
            <tbody>
              {#each membersFiltered.slice(0, memberShow) as m (m.a)}
                <tr class="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/40">
                  <td class="px-3 py-1.5 whitespace-nowrap">
                    <span class="italic">{ofEntry(m.s)?.sci}</span>
                    <span class="text-gray-500 dark:text-gray-400 text-xs ml-1">{ofEntry(m.s)?.com}</span>
                  </td>
                  <td class="px-3 py-1.5 font-mono text-xs">
                    <a class="text-sky-600 dark:text-sky-400 hover:underline"
                      href={`https://www.ncbi.nlm.nih.gov/protein/${m.a}`} target="_blank" rel="noopener">{m.a}</a>
                  </td>
                  <td class="px-3 py-1.5 text-gray-600 dark:text-gray-300">{m.p}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if membersFiltered.length > memberShow}
          <button class="w-full py-2 text-sm text-sky-600 dark:text-sky-400 hover:bg-gray-50 dark:hover:bg-gray-700/40 border-t border-gray-200 dark:border-gray-700"
            onclick={() => (memberShow += 100)}>Show 100 more ({membersFiltered.length - memberShow} remaining)</button>
        {/if}
      </div>
    {/if}

    <p class="mt-6 text-xs text-gray-500 dark:text-gray-400">
      {t('orthogroups.orthology_note')}
    </p>
  {/if}
</div>
