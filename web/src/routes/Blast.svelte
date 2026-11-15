<script>
  import { trackEvent } from '../lib/analytics.js';
  /**
   * Static BLAST (FUTURE_TODO #3) — protein search against the panel
   * reference set, entirely in the browser: a Rust/WASM Smith-Waterman
   * kernel (BLOSUM62, affine gaps 11/1, Karlin-Altschul E-values) in a
   * web worker. No server, no sequence upload.
   */
  import { onMount, onDestroy } from 'svelte';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { getRoute } from '../lib/stores/router.js';
  import wasmUrl from '../wasm/blast/roost_blast_bg.wasm?url';

  let query = $state('');
  let maxHits = $state(20);
  let dbMeta = $state(null);       // {n_entries, species, scoring}
  let status = $state('idle');     // idle | loading | searching | done | error
  let hits = $state([]);
  let ms = $state(null);
  let errMsg = $state(null);
  let expanded = $state(new Set());
  let worker = null;
  let exampleSeq = $state(null);   // chicken MX1 for the example button

  onMount(async () => {
    worker = new Worker(new URL('../workers/blast.worker.js', import.meta.url),
                        { type: 'module' });
    worker.onmessage = (e) => {
      const { type } = e.data;
      if (type === 'ready') {
        status = 'idle';
      } else if (type === 'done') {
        hits = e.data.hits;
        ms = e.data.ms;
        status = 'done';
      } else if (type === 'error') {
        errMsg = e.data.message;
        status = 'error';
      }
    };
    status = 'loading';
    try {
      const [dbRes, wasmRes] = await Promise.all([
        fetch('data/blast/panel_refs.json'),
        fetch(wasmUrl),
      ]);
      if (!dbRes.ok || !wasmRes.ok) throw new Error('payload fetch failed');
      const db = await dbRes.json();
      dbMeta = db.meta;
      exampleSeq = db.entries.find((x) => x.g === 'MX1' && x.s === 'Gallus gallus')?.q
                || db.entries[0]?.q || null;
      const wasm = await wasmRes.arrayBuffer();
      worker.postMessage({ type: 'init', wasm, entries: db.entries }, [wasm]);
      // ?gene=SYMBOL prefills the query with that gene's reference protein
      const geneParam = getRoute().params?.gene;
      if (geneParam && !query) {
        const hit = db.entries.find((x) => x.g === geneParam && x.s === 'Gallus gallus')
                 || db.entries.find((x) => x.g === geneParam);
        if (hit) query = hit.q;
      }
    } catch {
      status = 'error';
      errMsg = t('blast.load.error') || 'Failed to load the BLAST kernel or reference database.';
    }
  });
  onDestroy(() => worker?.terminate());

  const cleaned = $derived(query.replace(/[^A-Za-z]/g, '').toUpperCase());
  const invalid = $derived(cleaned.length > 0 &&
    /[^ARNDCQEGHILKMFPSTWYVBZXU*]/i.test(query.replace(/[^A-Za-z]/g, '')));

  function run() {
    trackEvent('BLAST', 'run', 'all species');
    if (!cleaned || cleaned.length < 5 || invalid) return;
    status = 'searching';
    hits = [];
    expanded = new Set();
    worker.postMessage({ type: 'search', query: cleaned, maxHits });
  }

  function toggle(i) {
    const next = new Set(expanded);
    if (next.has(i)) next.delete(i); else next.add(i);
    expanded = next;
  }

  function fmtE(ev) {
    if (ev === 0) return '0';
    if (ev < 0.001 || ev >= 1000) return ev.toExponential(1);
    return ev.toFixed(3);
  }

  // wrap alignment strings in 60-char blocks
  function blocks(h) {
    const out = [];
    for (let i = 0; i < h.q_aln.length; i += 60) {
      out.push({
        q: h.q_aln.slice(i, i + 60), m: h.midline.slice(i, i + 60),
        t: h.t_aln.slice(i, i + 60), pos: i,
      });
    }
    return out;
  }
</script>

<svelte:head><title>{t('blast.page.title') || 'BLAST against bird genomes'} — Roost</title></svelte:head>

<div class="max-w-5xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent">
    {t('blast.h1')}
  </h1>
  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-6">
    {t('blast.intro', { entries: dbMeta?.n_entries ?? 0, species: dbMeta?.species?.length ?? 0 })}
    <span class="text-gray-400 dark:text-gray-500">({t('blast.intro.tech')})</span> —
    {t('blast.intro.privacy')}
  </p>

  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
    <textarea
      bind:value={query}
      rows="7"
      spellcheck="false"
      placeholder={t('routes.blast.paste.protein.sequence.in') || 'Paste a protein sequence in FASTA or raw amino acids…'}
      class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-mono text-xs placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
    ></textarea>
    <div class="flex flex-wrap items-center gap-3 mt-3">
      <button
        onclick={run}
        disabled={status === 'searching' || status === 'loading' || cleaned.length < 5 || invalid}
        class="px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >{status === 'searching' ? (t('blast.searching') || 'Searching…') : '⚡ ' + (t('blast.search') || 'Search')}</button>
      {#if exampleSeq}
        <button
          onclick={() => (query = exampleSeq)}
          class="px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs hover:bg-gray-200 dark:hover:bg-gray-600"
          title={t('routes.blast.load.the.chicken.mx') || 'Load the chicken MX1 protein as an example query'}
        >{t('routes.blast.load.example.chicken.mx') || 'Load example: chicken MX1'}</button>
      {/if}
      <label class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
        {t('blast.max.hits')}
        <select bind:value={maxHits} class="rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-xs">
          {#each [10, 20, 50] as n}<option value={n}>{n}</option>{/each}
        </select>
      </label>
      <span class="text-xs text-gray-500 dark:text-gray-400 ml-auto">{cleaned.length} aa</span>
    </div>
    {#if invalid}
      <p class="mt-2 text-xs text-red-600 dark:text-red-400">
        {t('blast.invalid_residues')}
      </p>
    {/if}
    {#if status === 'loading'}
      <p class="mt-3 text-sm text-gray-500 dark:text-gray-400 animate-pulse">{t('routes.blast.loading.wasm.kernel.reference') || 'Loading WASM kernel + reference database…'}</p>
    {/if}
    {#if status === 'error'}
      <p class="mt-3 text-sm text-red-600 dark:text-red-400">{errMsg}</p>
    {/if}
  </div>

  {#if status === 'done'}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 mt-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {t(hits.length === 1 ? 'blast.hits.one' : 'blast.hits.count', { n: hits.length })} <span class="font-normal text-gray-500 dark:text-gray-400">· {ms} ms</span>
        </h2>
        {#if hits[0]}
          <p class="text-xs text-gray-500 dark:text-gray-400">
            {t('blast.best.match')}:
            <a class="font-semibold text-blue-600 dark:text-blue-400 hover:underline" href="#/genes/{hits[0].gene}">{hits[0].gene}</a>
            ({hits[0].species.replace(/([A-Z])\w*\s/, '$1. ')}) — {hits[0].identity.toFixed(1)}% {t('blast.identity')}, E = {fmtE(hits[0].evalue)}
          </p>
        {/if}
      </div>
      {#if !hits.length}
        <p class="text-sm text-gray-500 dark:text-gray-400 py-3">{t('empty.blast') || 'No significant similarity found in the reference set.'}</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                <th class="py-2 pr-4 font-medium">{t('blast.col.gene')}</th>
                <th class="py-2 pr-4 font-medium">{t('blast.col.species')}</th>
                <th class="py-2 pr-3 font-medium text-right">{t('blast.col.bits')}</th>
                <th class="py-2 pr-3 font-medium text-right">{t('blast.col.evalue')}</th>
                <th class="py-2 pr-3 font-medium text-right">{t('blast.col.identity')}</th>
                <th class="py-2 pr-3 font-medium text-right">{t('blast.col.coverage')}</th>
                <th class="py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
              {#each hits as h, i (i)}
                {@const cov = Math.round((h.q_end - h.q_start + 1) / Math.max(1, cleaned.length) * 100)}
                <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/20">
                  <td class="py-2 pr-4">
                    <a class="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline" href="#/genes/{h.gene}">{h.gene}</a>
                  </td>
                  <td class="py-2 pr-4 text-xs">
                    <a class="hover:underline text-gray-600 dark:text-gray-300" href="#/species-full/{encodeURIComponent(h.species)}" title={h.species}>
                      {h.species.replace(/([A-Z])\w*\s/, '$1. ')}
                    </a>
                  </td>
                  <td class="py-2 pr-3 text-right tabular-nums {h.bits > 50 ? 'font-semibold text-gray-800 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}">{h.bits.toFixed(1)}</td>
                  <td class="py-2 pr-3 text-right tabular-nums {h.evalue < 0.001 ? 'text-gray-800 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}">{fmtE(h.evalue)}</td>
                  <td class="py-2 pr-3 text-right tabular-nums">{h.identity.toFixed(1)}</td>
                  <td class="py-2 pr-3 text-right tabular-nums text-gray-500 dark:text-gray-400">{cov}%</td>
                  <td class="py-2">
                    <button class="text-xs text-blue-600 dark:text-blue-400 hover:underline" onclick={() => toggle(i)}>
                      {expanded.has(i) ? t('blast.hide') : t('blast.align')}
                    </button>
                  </td>
                </tr>
                {#if expanded.has(i)}
                  <tr>
                    <td colspan="7" class="pb-4">
                      <div class="rounded-lg bg-gray-50 dark:bg-gray-900/60 p-3 overflow-x-auto">
                        {#each blocks(h) as b (b.pos)}
                          <div class="font-mono text-[11px] leading-5 whitespace-pre">
                            <span class="text-gray-500 dark:text-gray-400">Q{h.q_start + (b.pos === 0 ? 0 : h.q_aln.slice(0, b.pos).replace(/-/g, '').length)}</span>
                            {' '.repeat(6)}<span class="text-gray-800 dark:text-gray-200">{b.q}</span>
                            <br>
                            <span class="text-gray-300">{' '.repeat(7)}</span><span class="text-blue-600 dark:text-blue-400">{b.m}</span>
                            <br>
                            <span class="text-gray-500 dark:text-gray-400">T{h.t_start + (b.pos === 0 ? 0 : h.t_aln.slice(0, b.pos).replace(/-/g, '').length)}</span>
                            {' '.repeat(6)}<span class="text-gray-800 dark:text-gray-200">{b.t}</span>
                          </div>
                        {/each}
                        <p class="mt-2 text-[10px] text-gray-500 dark:text-gray-400">
                          {t('blast.alignment.score', { score: h.score, bits: h.bits.toFixed(1), evalue: fmtE(h.evalue) })};
                          {t('blast.alignment.detail', { identity: h.identity.toFixed(0), aln_len: h.aln_len, positive: h.positive.toFixed(0), gaps: h.gaps })}
                          {dbMeta?.scoring}
                        </p>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
</div>
