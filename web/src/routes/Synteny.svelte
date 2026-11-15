<script>
  import { trackEvent } from '../lib/analytics.js';
  /**
   * Synteny explorer — conserved micro-synteny blocks among host-panel genes.
   *
   * Loads data/synteny/blocks.json (recurring co-located core gene-sets from
   * annotation coordinates; see scripts/genes/export_synteny.py). Left: block
   * list (searchable); right: per-species tracks, genes positioned by real
   * coordinates within each track's window. Species ordered phylogenetically
   * via the OrthoFinder species tree where available.
   */
  import { onMount } from 'svelte';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { navigate } from '../lib/stores/router.js';

  let { block = null } = $props();

  let blocks = $state(null);
  let meta = $state(null);
  let flanks = $state(null);       // {block_id: {sci: {chrom, seq, lo, hi, genes:[{s,n,b,e,o,core}]}}}
  let error = $state(null);
  let search = $state('');
  let selected = $state(null);     // block object
  // analytics: which synteny blocks people open
  $effect(() => { if (selected?.id || selected?.label) trackEvent('Synteny', 'view', selected.label || selected.id); });
  let smapBySci = new Map();       // sci -> species_map entry
  let treeOrder = null;            // sci names in leaf order (463 subset)

  const PALETTE = [
    '#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2',
    '#db2777', '#65a30d', '#ea580c', '#4f46e5', '#0d9488', '#b45309',
  ];
  const colorOf = (sym) => {
    const i = selected ? selected.genes.indexOf(sym) : -1;
    if (i >= 0) return PALETTE[i % PALETTE.length];
    let h = 0;
    for (const c of sym) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  };

  async function load() {
    try {
      const [bRes, sRes, tRes, fRes] = await Promise.all([
        fetch('data/synteny/blocks.json'),
        fetch('data/orthofinder/species_map.json'),
        fetch('data/orthofinder/species_tree.txt'),
        fetch('data/synteny/flanks.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
      ]);
      meta = await bRes.json();
      blocks = meta.blocks;
      flanks = await fRes;
      const smap = await sRes.json();
      for (const s of smap) smapBySci.set(s.sci, s);
      try {
        const txt = await tRes.text();
        const labels = [];
        const re = /[(,]\s*([A-Za-z_]+__[A-Za-z0-9_.]+)\s*:/g;
        let m;
        while ((m = re.exec(txt))) labels.push(m[1]);
        const sciOf = new Map(smap.map((s) => [s.label, s.sci]));
        treeOrder = labels.map((l) => sciOf.get(l)).filter(Boolean);
      } catch { treeOrder = null; }
      if (block) selected = blocks.find((b) => b.id === block) || blocks[0];
      else selected = blocks[0];
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);
  $effect(() => { if (blocks && block !== undefined) selected = blocks.find((b) => b.id === block) || selected; });

  const filtered = $derived.by(() => {
    if (!blocks) return [];
    const q = search.trim().toLowerCase();
    if (!q) return blocks;
    return blocks.filter(
      (b) => b.label.toLowerCase().includes(q) || b.genes.some((g) => g.toLowerCase().includes(q))
    );
  });

  const sortedSpecies = $derived.by(() => {
    if (!selected) return [];
    const scis = Object.keys(selected.tracks);
    if (!treeOrder) return scis.sort();
    const rank = new Map(treeOrder.map((s, i) => [s, i]));
    return scis.sort((a, b) => {
      const ra = rank.has(a) ? rank.get(a) : 1e6 + a.localeCompare(b);
      const rb = rank.has(b) ? rank.get(b) : 1e6 + b.localeCompare(b);
      return ra - rb || a.localeCompare(b);
    });
  });

  function trackRows(sci) {
    // geometry for one species track, normalised to its own window
    const trk = selected.tracks[sci];
    const f = flanks?.[selected.id]?.[sci] || null;
    const coreSet = new Set(selected.genes);
    let lo, hi;
    let rows;
    if (f) {
      // detailed track: fully server-merged genes from the current NCBI
      // annotation of this assembly (incl. strand and drift-translated panel
      // genes flagged 'tr') — coordinates are annotation-consistent
      lo = f.lo; hi = f.hi;
      rows = f.genes.map((g) => ({
        sym: g.s, start: g.b, end: g.e, o: g.o, tr: g.tr,
        isCore: g.core ?? coreSet.has(g.s.toUpperCase()),
        isPanel: !!(g.core || coreSet.has(g.s.toUpperCase())),
      }));
    } else {
      lo = Math.min(...trk.members.map((m) => m.start));
      hi = Math.max(...trk.members.map((m) => m.end));
      rows = trk.members.map((m) => ({
        ...m, isCore: coreSet.has(m.sym), isPanel: true, o: m.o || null,
      }));
    }
    const span = Math.max(hi - lo, 1);
    return rows
      .map((m) => ({
        ...m,
        left: ((m.start - lo) / span) * 100,
        width: Math.max(0.35, ((m.end - m.start) / span) * 100),
        kb: Math.round((m.end - m.start) / 100) / 10,
      }))
      .sort((a, b) => a.start - b.start);
  }

  const fmtMb = (n) => (n / 1e6).toFixed(n < 1e7 ? 1 : 0);
  const sciShort = (sci) => sci.replace(/([A-Z])\w*\s/, '$1. ');

  // hover a gene block → highlight the same gene across all species tracks
  let hoverSym = $state(null);
  const symKey = (s) => (s || '').toUpperCase();
  // click a species row → expand to a tall lane with every gene labelled
  let expandedRows = $state(new Set());
  const toggleRow = (sci) => {
    const next = new Set(expandedRows);
    if (next.has(sci)) next.delete(sci);
    else next.add(sci);
    expandedRows = next;
  };
</script>

<svelte:head><title>{t('synteny.page.title') || 'Synteny'} — Roost</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 py-8">
  {#if error}
    <div class="p-6 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">
      {t('synteny.load.error') || 'Failed to load synteny blocks'}: {error}
    </div>
  {:else if !blocks}
    <div class="p-6 text-gray-500 dark:text-gray-400">{t('synteny.loading') || 'Loading synteny blocks…'}</div>
  {:else}
    <div class="mb-6">
      <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent">
        {t('synteny.page.title') || 'Synteny explorer'}
      </h1>
      <p class="text-sm text-gray-600 dark:text-gray-300 mt-1 max-w-3xl">
        {t('synteny.intro_pre')}<span class="font-mono">≤{meta.gap_mb} Mb apart</span>{t('synteny.intro_mid', {n: meta.n_species_total})} <em>{t('synteny.core')}</em> {t('synteny.intro_post')}
      </p>
    </div>

    <div class="grid lg:grid-cols-[280px_1fr] gap-6 items-start">
      <!-- block list -->
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 lg:sticky lg:top-4 max-h-[80vh] overflow-y-auto">
        <input
          type="search"
          placeholder={t('search.placeholder.genes.blocks') || 'Search genes or blocks…'}
          bind:value={search}
          class="w-full mb-2 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
        />
        <div class="space-y-1">
          {#each filtered as b (b.id)}
            <button
              class="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors
                {selected?.id === b.id
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700/50 text-gray-700 dark:text-gray-300'}"
              onclick={() => { selected = b; navigate('synteny', b.id, {}); }}
            >
              <div class="truncate">{b.label}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{t('synteny.n_species', {n: b.n_species})}</div>
            </button>
          {/each}
          {#if !filtered.length}
            <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No blocks match “{search}”.</div>
          {/if}
        </div>
      </div>

      <!-- block detail -->
      {#if selected}
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <div class="flex flex-wrap items-center gap-2 mb-1">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white mr-2">{t('synteny.core_genes')}</h2>
            {#each selected.genes as g}
              <button
                class="px-2 py-0.5 rounded-full text-xs font-semibold text-white"
                style="background:{colorOf(g)}"
                title={t('btn.view.gene') || 'View gene page'}
                onclick={() => navigate('genes', g, {})}>{g}</button
              >
            {/each}
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
            {t('synteny.legend_pre', {found: selected.n_species, total: meta.n_species_total})}
            <span class="text-gray-500 dark:text-gray-400">{t('synteny.legend_outlined')}</span> {t('synteny.legend_tail')}
          </p>
          <p class="text-[11px] text-gray-500 dark:text-gray-400 mb-3 flex flex-wrap gap-x-4 gap-y-1">
            <span><span class="font-semibold text-gray-500 dark:text-gray-400">Hover</span>{t('routes.synteny.block.to.highlight.that') || 'a block to highlight that gene in every species'}</span>
            <span><span class="font-semibold text-gray-500 dark:text-gray-400">{t('synteny.click_caret')}</span>{t('routes.synteny.next.to.species.to') || 'next to a species to reveal all labels'}</span>
          </p>

          <div class="space-y-1">
            {#each sortedSpecies as sci (sci)}
              {@const trk = selected.tracks[sci]}
              {@const rows = trackRows(sci)}
              {@const open = expandedRows.has(sci)}
              <div
                class="flex items-center gap-3 px-1 -mx-1 rounded-lg transition-colors
                  {open
                    ? 'bg-blue-50/60 dark:bg-blue-900/15'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/20'}"
              >
                <button
                  class="w-44 shrink-0 text-right"
                  title={(open ? (t('common.collapse') || 'Collapse') : (t('common.expand') || 'Expand')) + ' — ' + (t('synteny.show.every.gene.label') || 'show every gene label in this track')}
                  onclick={() => toggleRow(sci)}
                >
                  <div class="text-xs font-medium text-gray-700 dark:text-gray-300 truncate" title={sci}>
                    {sciShort(sci)}{smapBySci.get(sci)?.com ? ` · ${smapBySci.get(sci).com}` : ''}
                    <span class="text-gray-500 dark:text-gray-400 group-hover:text-blue-600">{open ? ' ▴' : ' ▾'}</span>
                  </div>
                  <div class="text-[10px] text-gray-500 dark:text-gray-400">
                    chr{trk.chrom} · {fmtMb(Math.min(...trk.members.map((m) => m.start)))} Mb
                    <span class="opacity-60" title={trk.assembly}>{trk.assembly}</span>
                  </div>
                </button>
                <!-- presentation: hover-tooltip container — the mouseleave reset
                     is decorative; track contents stay accessible to AT -->
                <div
                  role="presentation"
                  class="relative flex-1 rounded bg-gray-50 dark:bg-gray-900/60 border border-gray-100 dark:border-gray-700/50 overflow-hidden
                    {open ? 'h-24' : 'h-7'} transition-[height] duration-200"
                  onmouseleave={() => (hoverSym = null)}
                >
                  {#each rows as r, i}
                    <button
                      class="absolute {open ? 'top-2 h-8' : 'top-1 h-5'} rounded-sm transition-all duration-150
                        {r.isPanel
                          ? `text-white ${r.isCore ? 'shadow-md' : 'opacity-60 dark:opacity-70'}`
                          : 'bg-transparent border border-gray-300 dark:border-gray-500 text-gray-500 dark:text-gray-400'}
                        {hoverSym && symKey(r.sym) === hoverSym ? 'ring-2 ring-gray-900 dark:ring-white z-20' : ''}"
                      style="left:{r.left}%; width:{Math.max(open ? 0.5 : 0.35, r.width)}%;
                        background:{r.isPanel ? (r.isCore ? colorOf(r.sym) : '#6b7280') : 'transparent'}"
                      title="{r.sym} · chr{trk.chrom}:{fmtMb(r.start)}–{fmtMb(r.end)} Mb · {r.kb} kb{r.o ? ` · ${t('synteny.title_strand', {o: r.o})}` : ''}{r.tr ? ` · ${t('synteny.title_translated')}` : ''}{r.isCore ? ` ${t('synteny.title_core')}` : r.isPanel ? ` ${t('synteny.title_panel')}` : ` ${t('synteny.title_flank')}`}"
                      onmouseenter={() => (hoverSym = symKey(r.sym))}
                      onclick={() => navigate('genes', r.sym, {})}
                    >
                      {#if !open && r.width > 7}<span class="text-[9px] leading-5 px-0.5 block truncate">{r.o === '-' ? '◂' : r.o === '+' ? '▸' : ''} {r.sym}</span>{/if}
                    </button>
                    {#if open && (r.width > 1.3 || r.isCore)}
                      <span
                        class="absolute pointer-events-none -translate-x-1/2 whitespace-nowrap text-[9px] leading-4 px-1 rounded
                          {i % 2 ? 'top-[48px]' : 'top-[68px]'}
                          {r.isCore
                            ? 'text-white font-semibold'
                            : 'bg-white/90 dark:bg-gray-800/90 text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-600'}"
                        style="left:{Math.min(96.5, Math.max(3.5, r.left + r.width / 2))}%;{r.isCore ? ` background:${colorOf(r.sym)}` : ''}"
                      >{r.o === '-' ? '◂' : r.o === '+' ? '▸' : ''}{r.sym}</span>
                    {/if}
                  {/each}
                </div>
                {#if flanks?.[selected.id]?.[sci]}
                  <span
                    class="text-[9px] shrink-0 {flanks[selected.id][sci].aligned === false ? 'text-amber-700' : 'text-gray-500 dark:text-gray-400'}"
                    title={flanks[selected.id][sci].aligned === false
                      ? "Track located by coordinate overlap only (anchor symbol not found in the current annotation of " + trk.assembly + ") — verify region"
                      : "Track includes named flanking genes from the current NCBI annotation of " + trk.assembly + " (strand shown)"}
                  >{flanks[selected.id][sci].aligned === false ? '⚠' : '✦'}</span>
                {/if}
              </div>
            {/each}
          </div>

          <p class="mt-4 text-[11px] text-gray-500 dark:text-gray-400">
            Method: {t('synteny.method_note', {n: meta.min_species, gap: meta.gap_mb, span: meta.max_span_mb ?? 2, date: meta.generated})}
          </p>
        </div>
      {/if}
    </div>
  {/if}
</div>
