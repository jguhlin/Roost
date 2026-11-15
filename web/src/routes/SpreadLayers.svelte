<script>
  /**
   * SpreadLayers — Phase 7/8 rendering of the layered spread model.
   * Three views over the deterministic + extracted twins:
   *   Eras      — Layer A timeline ledger (spread_eras.json)
   *   Hosts     — Layer C competence matrix + risk cards (host_competence.json)
   *   Dynamics  — [DET] measured features (spread_features.json)
   * Everything renders from data; nothing about specific eras/species/numbers
   * is hardcoded here.
   */
  import { onMount } from 'svelte';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { announce } from '../lib/stores/a11y.svelte.js';
  import EraTimeline from '../lib/components/spread/EraTimeline.svelte';
  import CompetenceTable from '../lib/components/spread/CompetenceTable.svelte';
  import FeaturePanels from '../lib/components/spread/FeaturePanels.svelte';
  import SynthesisPanels from '../lib/components/spread/SynthesisPanels.svelte';

  let eras = $state(/** @type {any[] | null} */ (null));
  let competence = $state(/** @type {any | null} */ (null));
  let features = $state(/** @type {any | null} */ (null));
  let synthesis = $state(/** @type {any | null} */ (null));
  let vaxDoc = $state(/** @type {any | null} */ (null));
  let papersIndex = $state(/** @type {Map<string, string> | null} */ (null));
  let commonNames = $state(/** @type {Map<string, string> | null} */ (null));
  let error = $state(/** @type {string | null} */ (null));
  let tab = $state('eras');         // eras | hosts | dynamics | synthesis

  const TABS = [
    { id: 'eras', label: 'spread.layers.tab.eras' },
    { id: 'hosts', label: 'spread.layers.tab.hosts' },
    { id: 'dynamics', label: 'spread.layers.tab.dynamics' },
    { id: 'synthesis', label: 'spread.layers.tab.synthesis' },
  ];

  onMount(async () => {
    try {
      const [e, h, f, s, p, sp, vo] = await Promise.all([
        fetch('data/spread_eras.json').then((r) => r.json()),
        fetch('data/host_competence.json').then((r) => r.json()),
        fetch('data/spread_features.json').then((r) => r.json()),
        fetch('data/spread_synthesis.json').then((r) => r.json()),
        fetch('data/papers.json').then((r) => r.json()),
        fetch('data/species_index.json').then((r) => r.json()),
        fetch('data/vaccine_outcomes.json').then((r) => r.ok ? r.json() : null).catch(() => null),
      ]);
      eras = e.eras;
      competence = h;
      features = f;
      synthesis = s;
      vaxDoc = vo;
      papersIndex = new Map((p.papers || []).map((x) => [x.id, x.title]));
      commonNames = new Map((sp || []).map((x) => [x.sci, x.com]));
      announce(
        t('a11y.announce.spread.layers.loaded', {
          n: eras?.length ?? 0,
          m: competence?.species?.length ?? 0,
        })
      );
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    }
  });

  function switchTab(id) {
    tab = id;
    announce(t(`spread.layers.tab.${id}`));
  }
</script>

<section class="max-w-6xl mx-auto px-4 py-8" aria-labelledby="spread-layers-title">
  <h1 id="spread-layers-title" class="text-2xl font-bold text-slate-900 dark:text-slate-50">
    {t('spread.layers.title')}
  </h1>
  <p class="mt-2 text-slate-600 dark:text-slate-300 max-w-3xl">
    {t('spread.layers.subtitle')}
    <a href="#/region-risk" class="ml-1 text-blue-600 dark:text-blue-400 underline">{t('region.risk.link') || 'Regional risk view →'}</a>
  </p>

  {#if synthesis?.findings}
    <!-- headline findings teaser — the synthesis tab's callouts, one click away -->
    <div class="mt-5 flex flex-wrap gap-3" role="group" aria-label={t('spread.findings.teaser.label')}>
      {#if synthesis.findings.detection_lag}
        <button
          class="group flex items-baseline gap-2 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 px-4 py-2.5 hover:ring-2 ring-blue-300 dark:ring-blue-700"
          onclick={() => { tab = 'synthesis'; document.getElementById('spread-panel-synthesis')?.scrollIntoView({ behavior: 'smooth' }); }}>
          <span class="text-2xl font-bold text-blue-700 dark:text-blue-300">{synthesis.findings.detection_lag.median}</span>
          <span class="text-sm text-blue-800/80 dark:text-blue-200/80">{t('spread.findings.teaser.lag')}</span>
        </button>
      {/if}
      {#if synthesis.findings.loss_recovery}
        <button
          class="group flex items-baseline gap-2 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 px-4 py-2.5 hover:ring-2 ring-amber-300 dark:ring-amber-700"
          onclick={() => { tab = 'synthesis'; document.getElementById('spread-panel-synthesis')?.scrollIntoView({ behavior: 'smooth' }); }}>
          <span class="text-2xl font-bold text-amber-700 dark:text-amber-300">{synthesis.findings.loss_recovery.loss}:{synthesis.findings.loss_recovery.recovery}</span>
          <span class="text-sm text-amber-800/80 dark:text-amber-200/80">{t('spread.findings.teaser.recovery')}</span>
        </button>
      {/if}
      {#if synthesis.findings.establishment_2344b}
        <button
          class="group flex items-baseline gap-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 hover:ring-2 ring-slate-300 dark:ring-slate-600"
          onclick={() => { tab = 'synthesis'; document.getElementById('spread-panel-synthesis')?.scrollIntoView({ behavior: 'smooth' }); }}>
          <span class="text-2xl font-bold text-slate-700 dark:text-slate-200">{synthesis.findings.establishment_2344b.share_pct}%</span>
          <span class="text-sm text-slate-600 dark:text-slate-300">{t('spread.findings.teaser.establishment')}</span>
        </button>
      {/if}
    </div>
  {/if}

  {#if error}
    <p role="alert" class="mt-6 text-red-700 dark:text-red-300">{t('common.load.error')} {error}</p>
  {:else if !eras}
    <p class="mt-6 text-slate-500 dark:text-slate-400" aria-busy="true">{t('common.loading')}</p>
  {:else}
    <!-- tabs -->
    <div class="mt-6 flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-700" role="tablist" aria-label={t('spread.layers.tablist.label')}>
      {#each TABS as tb (tb.id)}
        <button
          role="tab"
          id={`spread-tab-${tb.id}`}
          aria-selected={tab === tb.id}
          aria-controls={`spread-panel-${tb.id}`}
          tabindex={tab === tb.id ? 0 : -1}
          class="px-4 py-2 text-sm font-medium rounded-t-lg -mb-px border border-b-0 transition-colors
            {tab === tb.id
              ? 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-blue-700 dark:text-blue-300'
              : 'bg-slate-100 dark:bg-slate-900 border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'}"
          onclick={() => switchTab(tb.id)}>{t(tb.label)}</button>
      {/each}
    </div>

    {#if tab === 'eras'}
      <div role="tabpanel" id="spread-panel-eras" aria-labelledby="spread-tab-eras" tabindex="-1" class="pt-6">
        <EraTimeline {eras} {papersIndex} findings={synthesis?.findings} introByEra={synthesis?.introductions?.by_era} />
      </div>
    {:else if tab === 'hosts'}
      <div role="tabpanel" id="spread-panel-hosts" aria-labelledby="spread-tab-hosts" tabindex="-1" class="pt-6">
        <CompetenceTable doc={competence} {commonNames} {papersIndex} {synthesis} {vaxDoc} />
      </div>
    {:else if tab === 'dynamics'}
      <div role="tabpanel" id="spread-panel-dynamics" aria-labelledby="spread-tab-dynamics" tabindex="-1" class="pt-6">
        <FeaturePanels doc={features} {commonNames} />
      </div>
    {:else if tab === 'synthesis'}
      <div role="tabpanel" id="spread-panel-synthesis" aria-labelledby="spread-tab-synthesis" tabindex="-1" class="pt-6">
        <SynthesisPanels doc={synthesis} />
      </div>
    {/if}
  {/if}
</section>
