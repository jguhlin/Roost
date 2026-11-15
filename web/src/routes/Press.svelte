<script>
  /**
   * Press page — landing page for journalists, science writers, and
   * conservation officers. Fact sheet, stories in the data, how to credit,
   * contact. Assembled from existing artifacts (by_the_numbers.json).
   */
  import { t } from '../lib/stores/i18n.svelte.js';
  import { formatNumber } from '../lib/utils/format.js';
  import { onMount } from 'svelte';

  let numbers = $state(null);
  let copied = $state(false);
  let emailRevealed = $state(false);

  // Email obfuscation (same pattern as the beta banner)
  const _fragments = ['hpesoj', 'nilhug', 'liamg', 'moc'];
  const emailParts = _fragments.map((f) => [...f].reverse().join(''));
  const _dot = String.fromCharCode(46), _at = String.fromCharCode(64);
  const emailAddress = emailParts[0] + _dot + emailParts[1] + _at + emailParts[2] + _dot + emailParts[3];

  function copyCitation() {
    navigator.clipboard?.writeText(citationText)
      .then(() => { copied = true; setTimeout(() => (copied = false), 2000); })
      .catch(() => {});
  }

  const citationText = 'Roost: Avian Influenza Host Genomics Resource (2026). https://josephguhlin.com/Roost/. Accessed ' + new Date().toISOString().slice(0, 10) + '.';

  onMount(async () => {
    try {
      const r = await fetch('data/by_the_numbers.json');
      if (r.ok) numbers = await r.json();
    } catch { /* numbers stay hidden */ }
  });

  const facts = $derived.by(() => {
    if (!numbers) return [];
    const c = numbers.corpus || {};
    const s = numbers.species || {};
    const lc = numbers.literature_concentration || {};
    const g = numbers.gene_registry || {};
    const gen = numbers.genomics || {};
    return [
      { n: formatNumber(c.detections || 0), label: t('press.fact.records'), tip: t('press.fact.records.tip') },
      { n: formatNumber(s.detected || 0), label: t('press.fact.species'), tip: t('press.fact.species.tip') },
      { n: formatNumber(c.countries || 0), label: t('press.fact.countries'), tip: t('press.fact.countries.tip') },
      { n: formatNumber(c.papers || 0), label: t('press.fact.papers'), tip: t('press.fact.papers.tip') },
      { n: formatNumber(lc.detected_zero_papers || 0), label: t('press.fact.gap'), tip: t('press.fact.gap.tip'), highlight: true },
      { n: `${lc.top10_share_pct || 0}%`, label: t('press.fact.concentration'), tip: t('press.fact.concentration.tip'), highlight: true },
      { n: formatNumber(g.total_genes || 1428), label: t('press.fact.genes'), tip: t('press.fact.genes.tip') },
      { n: formatNumber(11348), label: t('press.fact.searchable'), tip: t('press.fact.searchable.tip') },
    ];
  });
</script>

<svelte:head><title>{t('press.page.title')} — Roost</title></svelte:head>

<div class="max-w-5xl mx-auto px-4 py-8 space-y-8">

  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{t('press.title')}</h1>
    <p class="text-gray-600 dark:text-gray-300 max-w-3xl">{t('press.subtitle')}</p>
  </div>

  <!-- What Roost is / isn't -->
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">{t('press.what.title')}</h2>
    <p class="text-gray-600 dark:text-gray-300 leading-relaxed">{t('press.what.body')}</p>
  </div>

  <!-- Fact sheet -->
  {#if numbers}
    <div class="rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-5">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">{t('press.facts.title')}</h2>
        <span class="text-xs text-slate-500 dark:text-slate-400">{t('insights.as_of')} {numbers.generated?.slice(0, 10)}</span>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {#each facts as f}
          <div class="text-center {f.highlight ? 'rounded-lg bg-amber-50 dark:bg-amber-900/20 p-3' : ''}" title={f.tip}>
            <div class="text-3xl font-bold {f.highlight ? 'text-amber-700 dark:text-amber-300' : 'text-slate-800 dark:text-slate-100'}">{f.n}</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{f.label}</div>
          </div>
        {/each}
      </div>
      <p class="text-[10px] text-slate-500 dark:text-slate-400 mt-3 text-center">
        {t('press.facts.definitions_note')}
      </p>
    </div>
  {/if}

  <!-- Stories in the data -->
  <div>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">{t('press.stories.title')}</h2>
    <div class="grid sm:grid-cols-2 gap-4">
      {#each [
        { icon: '🔍', title: t('press.story.gap.title'), body: t('press.story.gap.body'), link: '#/numbers' },
        { icon: '🐔', title: t('press.story.concentration.title'), body: t('press.story.concentration.body'), link: '#/numbers' },
        { icon: '⚖️', title: t('press.story.contradictions.title'), body: t('press.story.contradictions.body'), link: '#/contradictions' },
        { icon: '🪺', title: t('press.story.kakapo.title'), body: t('press.story.kakapo.body'), link: '#/species-full/Strigops%20habroptila?tab=overview' },
      ] as story}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 flex flex-col">
          <div class="text-2xl mb-2">{story.icon}</div>
          <h3 class="font-semibold text-gray-900 dark:text-white mb-1.5">{story.title}</h3>
          <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed flex-1">{story.body}</p>
          <a href={story.link} class="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-3">{t('press.story.read_more')} →</a>
        </div>
      {/each}
    </div>
  </div>

  <!-- How to credit -->
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">{t('press.credit.title')}</h2>
    <div class="rounded-lg bg-gray-50 dark:bg-gray-700 p-4 border-l-4 border-blue-500 flex items-center justify-between gap-4">
      <code class="text-sm text-gray-800 dark:text-gray-100 break-all">{citationText}</code>
      <button class="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium whitespace-nowrap"
              onclick={copyCitation}>
        {#if copied}{t('insights.facts.copied')}{:else}{t('insights.facts.copy_citation')}{/if}
      </button>
    </div>
    <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">{t('press.credit.license_note')}</p>
  </div>

  <!-- Why numbers differ -->
  <div class="rounded-xl bg-blue-50 dark:bg-blue-900/20 p-5">
    <h2 class="text-lg font-semibold text-blue-900 dark:text-blue-200 mb-2">{t('press.differ.title')}</h2>
    <p class="text-sm text-blue-900/80 dark:text-blue-100/80 leading-relaxed mb-3">{t('press.differ.body')}</p>
    <div class="flex flex-wrap gap-3 text-sm">
      <a href="#/contradictions" class="text-blue-700 dark:text-blue-300 underline">{t('nav.contradictions')}</a>
      <a href="#/methods" class="text-blue-700 dark:text-blue-300 underline">{t('nav.methods')}</a>
    </div>
  </div>

  <!-- Contact -->
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">{t('press.contact.title')}</h2>
    <p class="text-sm text-gray-600 dark:text-gray-300 mb-4">{t('press.contact.body')}</p>
    <div class="flex flex-wrap items-center gap-3">
      {#if emailRevealed}
        <a href={'ma' + 'ilto:' + emailAddress} class="text-sm font-medium text-blue-700 dark:text-blue-300 underline break-all">
          {emailAddress}
        </a>
        <span class="text-xs text-gray-500 dark:text-gray-400">{t('press.contact.timezone')}</span>
      {:else}
        <button class="text-sm px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium"
                onclick={() => (emailRevealed = true)}
                aria-label={t('home.beta.reveal_aria')}>{t('home.beta.reveal')}</button>
        <span class="text-xs text-gray-500 dark:text-gray-400">{t('home.beta.reveal_hint')}</span>
      {/if}
    </div>
  </div>

  <!-- Quick links -->
  <div class="flex flex-wrap gap-4 text-sm border-t border-gray-200 dark:border-gray-700 pt-4">
    <span class="text-gray-500 dark:text-gray-400 font-medium">{t('press.quick_links')}:</span>
    <a href="#/numbers" class="text-blue-600 dark:text-blue-400 hover:underline">{t('nav.numbers')}</a>
    <a href="#/contradictions" class="text-blue-600 dark:text-blue-400 hover:underline">{t('nav.contradictions')}</a>
    <a href="#/methods" class="text-blue-600 dark:text-blue-400 hover:underline">{t('nav.methods')}</a>
    <a href="#/downloads" class="text-blue-600 dark:text-blue-400 hover:underline">{t('nav.downloads')}</a>
    <a href="#/region-risk" class="text-blue-600 dark:text-blue-400 hover:underline">{t('nav.region_risk')}</a>
    <a href="#/credits" class="text-blue-600 dark:text-blue-400 hover:underline">{t('nav.credits')}</a>
  </div>
</div>
