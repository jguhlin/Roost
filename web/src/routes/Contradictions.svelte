<script>
  /** Literature contradictions — adjudicated claim clusters. Minimal view. */
  import { onMount } from 'svelte';
  import { t, pt, ft } from '../lib/stores/i18n.svelte.js';

  let data = $state(null);
  let error = $state(null);
  let verdict = $state('real');   // real | context-dependent | apparent | all
  let search = $state('');

  onMount(async () => {
    try {
      const r = await fetch('data/papers/contradictions.json');
      if (!r.ok) throw new Error('payload missing');
      data = await r.json();
    } catch {
      error = 'Contradiction data unavailable (run scripts/papers/export_contradictions.py).';
    }
  });

  const shown = $derived.by(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    return data.contradictions.filter((c) =>
      (verdict === 'all' || c.verdict === verdict)
      && (!q || c.topic.toLowerCase().includes(q)
          || c.what.toLowerCase().includes(q)
          || c.cluster.toLowerCase().includes(q)));
  });

  const VERDICT_STYLE = {
    real: 'bg-red-600 text-white',
    'context-dependent': 'bg-amber-500 text-white',
    apparent: 'bg-gray-400 text-white',
    unclassified: 'bg-gray-200 text-gray-600 dark:text-gray-400',
  };
  const REASON_LABEL = {
    temporal: '⏱ ' + t('contradictions.reason.temporal'), methodological: '🧪 ' + t('contradictions.reason.method'),
    'species-context': '🐦 ' + t('contradictions.reason.species'), geographic: '🌍 ' + t('contradictions.reason.geography'),
    'dose-route': '💉 ' + t('contradictions.reason.dose'), 'sample-size': '📐 ' + t('contradictions.reason.n'),
    definitional: '📖 ' + t('contradictions.reason.definition'), 'data-currency': '🔄 ' + t('contradictions.reason.data_age'),
    other: '·',
  };
  // Safe verdict label — falls back to the raw data value when the key
  // is missing (t() returns the key itself, never leak that into the UI)
  function verdictLabel(v) {
    const k = 'contradictions.verdict.' + (v || 'unclassified');
    const s = t(k);
    return s === k ? v : s;
  }
</script>

<svelte:head><title>{t('contradictions.page.title') || 'Literature contradictions'} — Roost</title></svelte:head>

<div class="max-w-5xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{t('contradictions.page.title')}</h1>
  {#if data}
    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-4">
      {t('contradictions.meta', {c: data.meta.n_contradictions, k: data.meta.n_clusters, q: data.meta.n_open_questions, s: data.meta.n_consensus})}
      {t('contradictions.generated', {d: data.meta.generated?.slice(0, 10) || ''})}
    </p>
    <div class="flex flex-wrap gap-2 mb-4 items-center">
      {#each [['real', '⚠ ' + t('contradictions.verdict.real')], ['context-dependent', t('contradictions.verdict.context-dependent')], ['apparent', t('contradictions.verdict.apparent')], ['all', t('contradictions.verdict.all')]] as [v, label]}
        <button
          class="px-2.5 py-1 rounded-full text-xs font-medium {verdict === v ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}"
          onclick={() => (verdict = v)}>{label}</button>
      {/each}
      <input
        type="text" value={search} placeholder={t('contradictions.filter')}
        oninput={(e) => (search = e.target.value)}
        class="ml-auto px-3 py-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm w-48"
      />
    </div>
    <div class="space-y-3">
      {#each shown.slice(0, 300) as c, i (i)}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="font-medium text-gray-900 dark:text-gray-100 text-sm">{ft(c.th) || c.topic}</div>
            <div class="flex gap-1 shrink-0">
              {#if c.reason && c.reason !== 'other'}
                <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
                      title="why: {c.reason}">{REASON_LABEL[c.reason] || c.reason}</span>
              {/if}
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold {VERDICT_STYLE[c.verdict] || VERDICT_STYLE.unclassified}">{verdictLabel(c.verdict)}</span>
            </div>
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{ft(c.wh) || c.what}</p>
          <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
            <a class="text-blue-600 dark:text-blue-400 hover:underline" href="#/papers/{c.a.id}" title={c.a.title}>« {(pt(c.a.id, 'title') || c.a.title).slice(0, 60)}… ({c.a.year})</a>
            <a class="text-blue-600 dark:text-blue-400 hover:underline" href="#/papers/{c.b.id}" title={c.b.title}>» {(pt(c.b.id, 'title') || c.b.title).slice(0, 60)}… ({c.b.year})</a>
          </div>
          {#if c.explanation}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5 italic">{ft(c.ex) || c.explanation}</p>
          {/if}
          {#if c.tags?.length}
            <div class="flex gap-1 mt-1.5 flex-wrap">
              {#each c.tags as tag}
                <span class="px-1.5 py-0.5 rounded text-[9px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">{tag}</span>
              {/each}
            </div>
          {/if}
          <div class="text-[10px] text-gray-500 dark:text-gray-400 mt-1">{c.cluster}</div>
        </div>
      {/each}
    </div>
    {#if shown.length > 300}
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-3">{t('contradictions.showing', {n: 300, total: shown.length})}</p>
    {/if}
  {:else if error}
    <p class="text-red-600 dark:text-red-400 text-sm mt-4">{error}</p>
  {:else}
    <p class="text-gray-500 dark:text-gray-400 text-sm mt-4 animate-pulse">{t('common.loading') || 'Loading…'}</p>
  {/if}
</div>
