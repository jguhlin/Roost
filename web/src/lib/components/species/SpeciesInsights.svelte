<script>
  /**
   * SpeciesInsights — "What this bird's genes tell us" panel.
   * mode="card": compact summary + chips for the species dialog (above tabs)
   * mode="full": narrative + functional gene groups + susceptibility +
   *              vaccines + caveats for the full-page overview tab.
   * Degrades silently when no artifact exists for the species.
   */
  import { t } from '../../stores/i18n.svelte.js';
  import { fetchGeneCatalogue } from '../../utils/presence.js';

  let { taxonId = null, sci = '', mode = 'card' } = $props();

  let insight = $state(null);
  let catalogue = $state(null);
  let openGroup = $state(null);
  let copied = $state(false);

  function copyCitation() {
    if (insight?.facts?.citation) {
      navigator.clipboard?.writeText(insight.facts.citation)
        .then(() => { copied = true; setTimeout(() => (copied = false), 2000); })
        .catch(() => {});
    }
  }

  $effect(() => {
    const id = taxonId;
    insight = null;
    if (!id) return;
    fetch(`data/species_insights/${id}.json`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => { insight = d; })
      .catch(() => { insight = null; });
    fetchGeneCatalogue().then(c => { catalogue = c?.gene_catalogue || null; });
  });

  const isAnnotated = (g) => g.level?.startsWith('E5') || g.level?.startsWith('E4_annotated');
  const chipClass = (gene) => {
    const color = gene.status === 'FULL'
      ? 'border-green-300 dark:border-green-700 text-green-800 dark:text-green-300 bg-green-50 dark:bg-green-900/20'
      : gene.status === 'FRAGMENT'
      ? 'border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20'
      : 'border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800';
    const style = gene.status === 'FULL' && !isAnnotated(gene)
      ? 'border-dashed'  // putative — sequence-match only, not annotation-backed
      : '';
    return `${color} ${style}`.trim();
  };
  const statusWord = (g) => t(`insights.status.${g.status === 'NOT_FOUND' ? 'absent' : g.status === 'FRAGMENT' ? 'fragment' : g.level?.startsWith('E5') ? 'full_annotated' : 'full_search'}`);

  let groupCounts = $derived((insight?.groups || []).map(g => ({ key: g.key, label: g.label, n: g.genes.length, present: g.genes.filter(x => x.status === 'FULL').length, absent: g.genes.filter(x => x.status === 'NOT_FOUND').length })));
</script>

{#if insight}
  {#if mode === 'card'}
    <!-- compact card for the species dialog -->
    <div class="mb-4 rounded-xl border border-teal-200 dark:border-teal-800 bg-gradient-to-r from-teal-50 to-blue-50 dark:from-teal-900/20 dark:to-blue-900/20 p-4">
      <div class="flex items-start justify-between gap-3">
        <h3 class="text-sm font-semibold text-teal-900 dark:text-teal-200">{t('insights.title')}</h3>
        <a href="#/species-full/{encodeURIComponent(sci)}?tab=overview" class="text-xs text-blue-700 dark:text-blue-300 underline whitespace-nowrap">{t('insights.view_more')} →</a>
      </div>
      {#if insight.summary}
        <p class="text-sm text-gray-700 dark:text-gray-200 leading-relaxed mt-1.5">{insight.summary}</p>
      {:else}
        <p class="text-sm text-gray-600 dark:text-gray-300 mt-1.5">
          {insight.has_genome ? t('insights.genome_panel_ready') : t('insights.estimated_panel')}
        </p>
      {/if}
      <div class="flex flex-wrap gap-1.5 mt-2.5">
        {#if insight.detections > 0}
          <span class="text-[10px] px-2 py-0.5 rounded-full font-medium bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300">
            {t('insights.detected_n', { n: insight.detection_history?.n ?? insight.detections })}
            {#if insight.detection_history?.first}({insight.detection_history.first.slice(0, 4)}–){/if}
          </span>
        {:else}
          <span class="text-[10px] px-2 py-0.5 rounded-full font-medium bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {t('insights.no_detections')}
          </span>
        {/if}
        <span class="text-[10px] px-2 py-0.5 rounded-full font-medium {insight.has_genome ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'}">
          {insight.has_genome ? t('insights.basis.genome') : t('insights.basis.relatives')}
        </span>
        {#if insight.susceptibility?.class}
          <span class="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300">{t('insights.susc_class.' + insight.susceptibility.class)}</span>
        {/if}
        {#if species?.population}
          <span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">{species.population}</span>
        {/if}
        {#each groupCounts as gc}
          <span class="text-[10px] px-2 py-0.5 rounded-full bg-white/70 dark:bg-gray-800/70 text-gray-600 dark:text-gray-300">{gc.label} · {gc.present}/{gc.n}</span>
        {/each}
      </div>
    </div>
  {:else}
    <!-- full panel for the overview tab -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 space-y-5">
      <div class="flex items-start justify-between gap-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{t('insights.title')}</h2>
        <span class="text-[10px] px-2 py-0.5 rounded-full font-medium {insight.has_genome ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'}">
          {insight.has_genome ? t('insights.basis.genome') : t('insights.basis.relatives')}
        </span>
      </div>

      {#if insight.summary}
        <p class="text-base text-gray-800 dark:text-gray-100 leading-relaxed">{insight.summary}</p>
      {/if}
      {#if insight.overview}
        <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{insight.overview}</p>
      {/if}

      <!-- Facts at a glance -->
      {#if insight.facts}
        <div class="rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide">{t('insights.facts_title')}</h3>
            <span class="text-[10px] text-slate-400 dark:text-slate-500">{t('insights.as_of')} {insight.generated}</span>
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-300 mb-3">{t('insights.facts.evidence.' + insight.facts.evidence_level)}</p>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {#if insight.detection_history}
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-800 dark:text-slate-100">{insight.detection_history.n}</div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400">{t('insights.facts.reports')}</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-slate-800 dark:text-slate-100">{insight.detection_history.countries}</div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400">{t('insights.facts.countries')}</div>
              </div>
              <div class="text-center">
                <div class="text-sm font-semibold text-slate-700 dark:text-slate-200 mt-1">{insight.detection_history.first}</div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400">{t('insights.facts.first')}</div>
              </div>
              <div class="text-center">
                <div class="text-sm font-semibold text-slate-700 dark:text-slate-200 mt-1">{insight.detection_history.last}</div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400">{t('insights.facts.last')}</div>
              </div>
              {#if insight.detection_history.n > 1000}
                <div class="text-center col-span-4 text-[10px] text-slate-400 dark:text-slate-500">
                  {t('species.reports_tooltip')}
                </div>
              {/if}
            {:else}
              <div class="text-center">
                <div class="text-lg font-semibold text-slate-500 dark:text-slate-400">{t('insights.no_detections')}</div>
                <div class="text-[10px] text-slate-400 dark:text-slate-500">{t('insights.facts.no_det_note')}</div>
              </div>
              <div class="text-center">
                <div class="text-lg font-semibold {insight.has_genome ? 'text-green-600 dark:text-green-400' : 'text-slate-400'}">{insight.has_genome ? t('insights.facts.genome_yes') : t('insights.facts.genome_no')}</div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400">{t('insights.facts.genome_label')}</div>
              </div>
            {/if}
          </div>

          {#if insight.detections === 0 && insight.facts.detected_relatives?.length}
            <div class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-600">
              <p class="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {t('insights.facts.detected_relatives', { n: insight.facts.n_detected_relatives, order: insight.facts.order || '' })}
                {#each insight.facts.detected_relatives.slice(0, 4) as r}
                  <a href="#/species-full/{encodeURIComponent(r.sci)}" class="text-blue-600 dark:text-blue-400 hover:underline">{r.sci}</a>{r.rank === 'family' ? ' (family)' : ''}{r !== insight.facts.detected_relatives[3] ? ', ' : ''}
                {/each}
                {#if insight.facts.detected_relatives.length > 4}
                  {t('insights.facts.and_n_more', { n: insight.facts.detected_relatives.length - 4 })}
                {/if}
              </p>
            </div>
          {/if}

          <div class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-600 flex items-center justify-between">
            <span class="text-[10px] text-slate-400 dark:text-slate-500">{t('insights.facts.why_differ')}</span>
            <button class="text-xs px-3 py-1 rounded-lg bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-500 font-medium transition-colors"
                    onclick={copyCitation}>
              {#if copied}{t('insights.facts.copied')}{:else}{t('insights.facts.copy_citation')}{/if}
            </button>
          </div>
        </div>
      {/if}

      <!-- Detection history -->
      <div class="rounded-lg {insight.detections > 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-gray-50 dark:bg-gray-700/30'} p-4">
        <h3 class="text-sm font-semibold {insight.detections > 0 ? 'text-red-900 dark:text-red-200' : 'text-gray-700 dark:text-gray-300'} mb-1">
          {insight.detections > 0 ? t('insights.detected_title') : t('insights.no_detections_title')}
        </h3>
        {#if insight.detections > 0 && insight.detection_history}
          <p class="text-sm {insight.detections > 0 ? 'text-red-900/70 dark:text-red-100/70' : 'text-gray-600 dark:text-gray-400'} leading-relaxed">
            {t('insights.detected_text', {
              n: insight.detection_history.n,
              first: insight.detection_history.first,
              last: insight.detection_history.last,
              c: insight.detection_history.countries
            })}
          </p>
        {:else if insight.detections > 0}
          <p class="text-sm text-red-900/70 dark:text-red-100/70">{t('insights.detected_generic', { n: insight.detections })}</p>
        {:else}
          <p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{t('insights.no_detections_text')}</p>
        {/if}
      </div>

      {#each insight.groups || [] as g (g.key)}
        <div class="border border-gray-100 dark:border-gray-700 rounded-lg overflow-hidden">
          <button class="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 dark:bg-gray-900/40 hover:bg-gray-100 dark:hover:bg-gray-900/60 text-left"
                  onclick={() => (openGroup = openGroup === g.key ? null : g.key)}
                  aria-expanded={openGroup === g.key}>
            <span class="text-sm font-semibold text-gray-800 dark:text-gray-200">{t('insights.group.' + g.key)}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">
              {g.genes.filter(x => x.status === 'FULL').length} {t('insights.present')} ·
              {g.genes.filter(x => x.status === 'NOT_FOUND').length} {t('insights.absent')} ·
              {g.genes.filter(x => x.status === 'FRAGMENT').length} {t('insights.fragment_n')}
              <span class="ml-1">{openGroup === g.key ? '▾' : '▸'}</span>
            </span>
          </button>
          {#if openGroup === g.key}
            <div class="p-3 space-y-2">
              <div class="flex flex-wrap gap-1.5">
              {#each g.genes as gene (gene.symbol)}
                {@const meta = catalogue?.[gene.symbol] || {}}
                <a href="#/genes/{gene.symbol}"
                   class="group inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border text-xs font-mono transition-colors {chipClass(gene)}"
                   title="{meta.name || gene.symbol} — {statusWord(gene)}{meta.function ? '\n' + meta.function : ''}{gene.origin !== 'called' ? '\n(' + gene.origin + ')' : ''}">
                  {gene.symbol}
                  {#if gene.importance === 'critical'}<span class="text-red-500" title={t('insights.critical')}>●</span>{/if}
                </a>
              {/each}
              </div>
              <p class="text-[10px] text-gray-400 dark:text-gray-500 flex flex-wrap gap-x-3">
                <span>— {t('insights.legend.solid')}</span>
                <span>-- {t('insights.legend.dashed')}</span>
                <span class="text-red-500">●</span> <span>{t('insights.critical')}</span>
              </p>
            </div>
          {/if}
        </div>
      {/each}

      {#if insight.susceptibility_narrative || insight.susceptibility}
        <div class="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
          <h3 class="text-sm font-semibold text-blue-900 dark:text-blue-200 mb-1">{t('insights.susceptibility_title')}</h3>
          {#if insight.susceptibility_narrative}
            <p class="text-sm text-blue-900/80 dark:text-blue-100/80 leading-relaxed">{insight.susceptibility_narrative}</p>
          {:else if insight.susceptibility}
            <p class="text-sm text-blue-900/70 dark:text-blue-100/70">{t('insights.susc_class.' + insight.susceptibility.class)} · {t('insights.confidence')}: {Math.round((insight.susceptibility.confidence ?? 1) * 100)}%</p>
          {/if}
        </div>
      {/if}

      {#if insight.vaccines}
        <div class="rounded-lg bg-teal-50 dark:bg-teal-900/20 p-4">
          <h3 class="text-sm font-semibold text-teal-900 dark:text-teal-200 mb-1">{t('insights.vaccines_title')}</h3>
          <p class="text-sm text-teal-900/80 dark:text-teal-100/80 leading-relaxed">{insight.vaccines}</p>
        </div>
      {/if}

      {#if insight.caveats?.length}
        <div class="text-xs text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700 pt-3 space-y-1">
          <span class="font-semibold uppercase tracking-wide">{t('insights.caveats_title')}</span>
          {#each insight.caveats as c}
            <p>· {c}</p>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
{/if}
