<script>
  /**
   * SynthesisPanels — the item-level spread corpus ledgers.
   * Everything renders from spread_synthesis.json (PAPER_EXTRACTED,
   * quote-grounded): introduction events, mammal chains, virus ledger,
   * transmission parameters, silent spread, establishment outcomes,
   * non-vaccine response, and documented population impact.
   */
  import { t } from '../../stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { announce } from '../../stores/a11y.svelte.js';

  let { doc } = $props();
  let movement = $state(/** @type {any | null} */ (null));
  let gaps = $state(/** @type {any | null} */ (null));
  onMount(() => {
    fetch('data/movement_lookup.json')
      .then((r) => r.ok ? r.json() : null)
      .then((d) => (movement = d))
      .catch(() => {});
    fetch('data/movement_coverage.json')
      .then((r) => r.ok ? r.json() : null)
      .then((d) => (gaps = d))
      .catch(() => {});
  });

  let routeFilter = $state('all');
  let eraFilter = $state('all');

  const intro = $derived(doc?.introductions ?? {});
  const introItems = $derived(intro.items ?? []);
  const routes = $derived(Object.keys(intro.by_route ?? {}));
  const eras = $derived(Object.keys(intro.by_era ?? {}));

  const filteredIntro = $derived.by(() => {
    let list = introItems;
    if (routeFilter !== 'all') list = list.filter((i) => i.route === routeFilter);
    if (eraFilter !== 'all') list = list.filter((i) => i.era === eraFilter);
    return list;
  });
  $effect(() => {
    if (doc) announce(t('a11y.announce.spread.synthesis', { n: filteredIntro.length }));
  });

  const years = $derived(
    Object.entries(intro.years ?? {}).map(([y, n]) => ({ y: Number(y), n })).sort((a, b) => a.y - b.y)
  );
  const maxYear = $derived(Math.max(1, ...years.map((x) => x.n)));

  const mam = $derived(doc?.mammal_chains ?? {});
  const lens = $derived(doc?.findings?.surveillance_lens);
  const lr = $derived(doc?.findings?.loss_recovery);
  const est = $derived(doc?.findings?.establishment_2344b);
  const r0 = $derived(doc?.findings?.r0_range);
  const virus = $derived(doc?.virus_ledger ?? {});
  const params = $derived(doc?.transmission_params ?? {});
  const silent = $derived(doc?.silent_spread ?? {});
  const estab = $derived(doc?.establishment ?? {});
  const response = $derived(doc?.response ?? {});
  const impact = $derived(doc?.impact_recovery ?? {});

  const OUTCOME_STYLE = {
    worked: 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300',
    established: 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300',
    recurring: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    partial: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    burned_out: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
    unclear: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  };
  const chip = 'text-sm px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400';
</script>

<div class="space-y-14">
  <!-- derived findings -->
  {#if doc?.findings}
    <section aria-labelledby="syn-findings">
      <h3 id="syn-findings" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.findings.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('spread.synthesis.findings.desc')}</p>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {#if doc.findings.detection_lag}
          {@const lag = doc.findings.detection_lag}
          <div class="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 p-5">
            <h4 class="font-semibold text-blue-900 dark:text-blue-100">{t('spread.finding.lag.title')}</h4>
            <p class="text-4xl font-bold text-blue-700 dark:text-blue-300 mt-1">{lag.median} <span class="text-base font-normal">{t('units.months')}</span></p>
            <p class="text-sm text-blue-800/80 dark:text-blue-200/80 mt-1">{t('spread.finding.lag.body', { n: lag.n, q1: lag.p25, q3: lag.p75 })}</p>
            <p class="text-sm text-blue-700/70 dark:text-blue-300/70 mt-2">{t('spread.finding.lag.implies')}</p>
          </div>
        {/if}
        {#if lens}
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h4 class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.finding.lens.title')}</h4>
          <p class="text-3xl font-bold text-slate-700 dark:text-slate-200 mt-1">{lens.mortality_based} : {lens.active}</p>
          <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('spread.finding.lens.body')}</p>
          <p class="text-sm text-slate-400 mt-2">{t('spread.finding.lens.implies', { e: lens.environmental, s: lens.sentinel })}</p>
        </div>
        {/if}
        {#if lr}
        <div class="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4">
          <h4 class="font-semibold text-amber-900 dark:text-amber-100">{t('spread.finding.recovery.title')}</h4>
          <p class="text-4xl font-bold text-amber-700 dark:text-amber-300 mt-1">{lr.loss} : {lr.recovery}</p>
          <p class="text-sm text-amber-800/80 dark:text-amber-200/80 mt-1">{t('spread.finding.recovery.body')}</p>
          <p class="text-sm text-amber-700/70 dark:text-amber-300/70 mt-2">{t('spread.finding.recovery.implies')}</p>
        </div>
        {/if}
        {#if est}
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h4 class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.finding.establishment.title')}</h4>
          <p class="text-3xl font-bold text-slate-700 dark:text-slate-200 mt-1">{est.share_pct}% · {est.established_pct}%</p>
          <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('spread.finding.establishment.body', { n: est.n, s: est.share_pct, e: est.established_pct })}</p>
          <p class="text-sm text-slate-400 mt-2">{t('spread.finding.establishment.implies', { b: est.burned_out })}</p>
        </div>
        {/if}
        {#if r0?.max != null}
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h4 class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.finding.r0.title')}</h4>
          <p class="text-3xl font-bold text-slate-700 dark:text-slate-200 mt-1">{r0.min}–{r0.max}</p>
          <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('spread.finding.r0.body', { n: r0.n })}</p>
          <p class="text-sm text-slate-400 mt-2">{t('spread.finding.r0.implies')}</p>
        </div>
        {/if}
        {#if doc.introductions?.emergence_phase_note?.count}
          <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <h4 class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.finding.emergence.title')}</h4>
            <p class="text-3xl font-bold text-slate-700 dark:text-slate-200 mt-1">{doc.introductions.emergence_phase_note.count}</p>
            <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('spread.finding.emergence.body')}</p>
          </div>
        {/if}
      </div>
    </section>
  {/if}

  <!-- introduction events -->
  <section aria-labelledby="syn-intro">
    <h3 id="syn-intro" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
      {t('spread.synthesis.intro.title')}
    </h3>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {t('spread.synthesis.intro.desc', { n: introItems.length.toLocaleString() })}
    </p>

    <div class="mt-3 flex flex-wrap gap-4 items-center">
      <label class="text-sm text-gray-600 dark:text-gray-300">
        {t('spread.synthesis.filter.route')}
        <select class="ml-2 px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm" bind:value={routeFilter}>
          <option value="all">{t('vaccines.outcomes.filter.all')}</option>
          {#each routes as r (r)}<option value={r}>{r}</option>{/each}
        </select>
      </label>
      <label class="text-sm text-gray-600 dark:text-gray-300">
        {t('spread.synthesis.filter.era')}
        <select class="ml-2 px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm" bind:value={eraFilter}>
          <option value="all">{t('vaccines.outcomes.filter.all')}</option>
          {#each eras as e (e)}<option value={e}>{e}</option>{/each}
        </select>
      </label>
      <span class="text-sm text-slate-500 dark:text-slate-400" aria-live="polite">
        {t('spread.competence.rows', { n: filteredIntro.length.toLocaleString() })}
      </span>
    </div>

    {#if years.length}
      <div class="mt-4 flex items-end gap-0.5 h-20" role="img" aria-label={t('spread.synthesis.intro.aria')}>
        {#each years as y (y.y)}
          <div class="flex-1 flex flex-col items-center justify-end h-full" title="{y.y}: {y.n}">
            <div class="w-full rounded-t bg-blue-500 dark:bg-blue-400 min-h-[2px]" style="height: {Math.max((y.n / maxYear) * 80, 2)}%"></div>
            <span class="text-xs text-slate-400 mt-1">{String(y.y).slice(2)}</span>
          </div>
        {/each}
      </div>
    {/if}
    {#if intro.emergence_phase_note?.count}
      <p class="mt-2 text-sm text-amber-700 dark:text-amber-300">
        {t('spread.synthesis.intro.emergence', { n: intro.emergence_phase_note.count })}
      </p>
    {/if}

    <div class="mt-4 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table class="w-full text-sm">
        <caption class="sr-only">{t('spread.synthesis.intro.title')}</caption>
        <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0 z-10">
          <tr>
            <th scope="col" class="px-3 py-2 font-semibold">{t('spread.synthesis.col.year')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('spread.synthesis.col.lineage')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('spread.synthesis.col.from')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('spread.synthesis.col.to')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('spread.synthesis.col.route')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('spread.synthesis.col.basis')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50 odd:bg-slate-50/60 dark:odd:bg-slate-800/30">
          {#each filteredIntro.slice(0, 30) as it, i (it.paper_id + i)}
            <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
              <td class="px-3 py-2 tabular-nums text-slate-500 dark:text-slate-400">{it.year ?? '—'}</td>
              <td class="px-3 py-2 text-slate-800 dark:text-slate-100">{it.lineage ?? '—'}</td>
              <td class="px-3 py-2 text-slate-600 dark:text-slate-300">{it.source_region ?? '—'}</td>
              <td class="px-3 py-2 text-slate-600 dark:text-slate-300">{it.dest_region ?? '—'}</td>
              <td class="px-3 py-2">
                {#if it.route}<span class={chip} title={t('spread.synthesis.col.route')}>{t(`spread.route.${it.route}`)}</span>{/if}
                {#if it.direction && it.direction !== 'unknown'}<span class={chip}>{t(`spread.direction.${it.direction}`)}</span>{/if}
              </td>
              <td class="px-3 py-2 text-slate-500 dark:text-slate-400">{it.basis ?? '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if filteredIntro.length > 30}
      <p class="mt-2 text-sm text-slate-400">{t('common.showing.first', { n: 30, m: filteredIntro.length.toLocaleString() })}</p>
    {/if}
  </section>

  <!-- mammal chains -->
  <section aria-labelledby="syn-mam">
    <h3 id="syn-mam" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
      {t('spread.synthesis.mam.title')}
    </h3>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {t('spread.synthesis.mam.desc', { n: (mam.items ?? []).length })}
    </p>
    <ul class="mt-2 flex flex-wrap gap-2">
      {#each Object.entries(mam.by_species ?? {}).slice(0, 10) as [sp, n] (sp)}
        <li class="text-sm px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">{sp} <span class="font-semibold">{n}</span></li>
      {/each}
    </ul>
    <ul class="mt-4 grid gap-3 sm:grid-cols-2">
      {#each (mam.items ?? []).filter((x) => x.grounded).slice(0, 6) as it, i (it.paper_id + i)}
        <li class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <div class="flex items-baseline justify-between gap-2">
            <h4 class="font-semibold text-slate-900 dark:text-slate-50">{it.species ?? '?'}</h4>
            {#if it.evidence_kind}<span class={chip}>{it.evidence_kind}</span>{/if}
          </div>
          <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">{(it.scale ?? '').slice(0, 180)}</p>
          <p class="mt-2 text-sm text-slate-400">{it.date ?? ''} · {it.paper_id}</p>
        </li>
      {/each}
    </ul>
  </section>

  <!-- virus ledger -->
  <section aria-labelledby="syn-virus">
    <h3 id="syn-virus" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
      {t('spread.synthesis.virus.title')}
    </h3>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {t('spread.synthesis.virus.desc', {
        r: (virus.reassortments ?? []).length,
        a: (virus.adaptations ?? []).length,
      })}
    </p>
    <div class="mt-3 grid gap-6 lg:grid-cols-2">
      <div>
        <h4 class="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">{t('spread.synthesis.virus.reassort')}</h4>
        <ul class="space-y-1.5">
          {#each (virus.reassortments ?? []).slice(0, 8) as it, i (it.paper_id + i)}
            <li class="text-sm text-slate-700 dark:text-slate-200">
              <span class="font-medium">{(it.genotype_or_name ?? '?').slice(0, 60)}</span>
              <span class="text-slate-400 text-sm ml-2">{it.date_window ?? ''}</span>
            </li>
          {/each}
        </ul>
      </div>
      <div>
        <h4 class="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2">{t('spread.synthesis.virus.adapt')}</h4>
        <ul class="flex flex-wrap gap-1.5">
          {#each (virus.adaptations ?? []).slice(0, 24) as it, i (it.paper_id + i)}
            <li class={chip} title="{it.phenotype ?? ''} — {it.host_context ?? ''}">{it.mutation ?? '?'}</li>
          {/each}
        </ul>
      </div>
    </div>
  </section>

  <!-- params + establishment + silent spread -->
  <div class="grid gap-8 lg:grid-cols-2">
    <section aria-labelledby="syn-params">
      <h3 id="syn-params" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.params.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('spread.synthesis.params.desc', { n: (params.items ?? []).length })}
      </p>
      <ul class="mt-3 space-y-1.5">
        {#each (params.items ?? []).slice(0, 10) as it, i (it.paper_id + i)}
          <li class="text-sm text-slate-700 dark:text-slate-200">
            <span class="font-mono text-sm text-blue-600 dark:text-blue-400">{it.parameter ?? '?'}</span>
            = <span class="font-medium">{it.value}{it.unit ? ' ' + it.unit : ''}</span>
            <span class="text-slate-400 text-sm"> — {(it.context ?? '').slice(0, 90)}</span>
          </li>
        {/each}
      </ul>
    </section>

    <section aria-labelledby="syn-establishment">
      <h3 id="syn-establishment" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.est.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('spread.synthesis.est.desc')}</p>
      <ul class="mt-3 flex flex-wrap gap-2">
        {#each Object.entries(estab.outcomes ?? {}) as [o, n] (o)}
          <li class="text-sm px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800">
            <span class="text-slate-700 dark:text-slate-200">{t('spread.synthesis.est.outcome.' + o, o)}</span> <span class="font-semibold">{n}</span>
          </li>
        {/each}
      </ul>
      <p class="mt-4 text-sm font-semibold text-slate-700 dark:text-slate-200">{t('spread.synthesis.silent.title')}</p>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('spread.synthesis.silent.desc', { n: (silent.items ?? []).length })}
      </p>
      <ul class="mt-2 space-y-1">
        {#each (silent.items ?? []).filter((x) => x.grounded).slice(0, 4) as it, i (it.paper_id + i)}
          <li class="text-sm text-slate-700 dark:text-slate-200">
            <span class={chip}>{it.evidence}</span> {it.region}: {(it.circulation_window ?? '').slice(0, 60)}
          </li>
        {/each}
      </ul>
    </section>
  </div>

  <!-- response + impact -->
  <div class="grid gap-8 lg:grid-cols-2">
    <section aria-labelledby="syn-response">
      <h3 id="syn-response" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.response.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('spread.synthesis.response.desc')}</p>
      <ul class="mt-3 flex flex-wrap gap-2">
        {#each Object.entries(response.outcomes ?? {}) as [o, n] (o)}
          <li class="text-sm px-3 py-1 rounded-lg {OUTCOME_STYLE[o] ?? OUTCOME_STYLE.unclear}">{t(`vaccines.outcome.${o}`)} <span class="font-semibold">{n}</span></li>
        {/each}
      </ul>
      <ul class="mt-3 flex flex-wrap gap-2">
        {#each Object.entries(response.by_intervention ?? {}) as [k, n] (k)}
          <li class="text-sm px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">{k} <span class="font-semibold">{n}</span></li>
        {/each}
      </ul>
    </section>

    <section aria-labelledby="syn-impact">
      <h3 id="syn-impact" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.impact.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('spread.synthesis.impact.desc', { n: (impact.items ?? []).length })}
      </p>
      <ul class="mt-3 space-y-2">
        {#each (impact.items ?? []).slice(0, 5) as it, i (it.paper_id + i)}
          <li class="text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3">
            <span class="font-medium text-slate-900 dark:text-slate-50">{(it.species ?? '?').slice(0, 50)}</span>
            <span class="text-slate-400 text-sm ml-2">{it.location ?? ''} · {it.timeframe ?? ''}</span>
            <p class="text-slate-600 dark:text-slate-300 text-sm mt-1">{(it.loss ?? '').slice(0, 140)}</p>
          </li>
        {/each}
      </ul>
    </section>
  </div>

  <p class="text-sm text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-3">
    {t('spread.synthesis.provenance')}
  </p>

  <!-- movement coverage (Plaza et al. 2026 verified) -->
  {#if movement?.summary}
    <section aria-labelledby="syn-movement" class="mt-8">
      <h3 id="syn-movement" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.movement.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">{t('spread.synthesis.movement.desc')}</p>
      <div class="grid gap-4 md:grid-cols-3">
        <div class="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-5">
          <div class="text-4xl font-bold text-emerald-700 dark:text-emerald-300">{movement.summary.detected_tracked_pct}%</div>
          <p class="text-sm text-emerald-800/80 dark:text-emerald-200/80 mt-1">{t('spread.synthesis.movement.tracked', { n: movement.summary.detected_tracked, m: movement.summary.detected })}</p>
        </div>
        <div class="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-5">
          <div class="text-4xl font-bold text-amber-700 dark:text-amber-300">{movement.summary.detected_genus_pct}%</div>
          <p class="text-sm text-amber-800/80 dark:text-amber-200/80 mt-1">{t('spread.synthesis.movement.genus', { n: movement.summary.detected_genus_covered, m: movement.summary.detected })}</p>
        </div>
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
          <div class="text-4xl font-bold text-slate-700 dark:text-slate-200">{movement.summary.untracked_infected}</div>
          <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('spread.synthesis.movement.gap')}</p>
          <p class="text-xs text-slate-400 mt-2">{t('spread.synthesis.movement.gap.note')}</p>
        </div>
      </div>
      <p class="text-xs text-slate-400 mt-3">
        {t('spread.synthesis.movement.paper')}
        <a href="https://doi.org/10.1111/irv.70330" class="underline">{t('spread.synthesis.movement.paper.authors') || 'Plaza et al. 2026'}</a>
      </p>
    </section>
  {/if}

  <!-- surveillance gaps (the research agenda) -->
  {#if gaps?.surveillance_gaps?.top?.length}
    <section aria-labelledby="syn-gaps" class="mt-8">
      <h3 id="syn-gaps" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('spread.synthesis.gaps.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">{t('spread.synthesis.gaps.desc')}</p>
      <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table class="w-full text-sm">
          <caption class="sr-only">{t('spread.synthesis.gaps.title')}</caption>
          <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0">
            <tr>
              <th scope="col" class="px-3 py-2.5 font-semibold">{t('spread.synthesis.gaps.col.species')}</th>
              <th scope="col" class="px-3 py-2.5 font-semibold text-right">{t('spread.synthesis.gaps.col.priority')}</th>
              <th scope="col" class="px-3 py-2.5 font-semibold text-right">{t('spread.synthesis.gaps.col.perm')}</th>
              <th scope="col" class="px-3 py-2.5 font-semibold text-right">{t('spread.synthesis.gaps.col.det')}</th>
              <th scope="col" class="px-3 py-2.5 font-semibold text-right">{t('spread.synthesis.gaps.col.countries')}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
            {#each gaps.surveillance_gaps.top.slice(0, 15) as g (g.species)}
              <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
                <td class="px-3 py-2.5">
                  <a href={`#/susceptibility/${encodeURIComponent(g.species)}`} class="italic font-medium text-slate-900 dark:text-slate-50 underline decoration-slate-300">{g.species}</a>
                  {#if g.common}<span class="ml-2 text-xs text-slate-500 dark:text-slate-400">{g.common}</span>{/if}
                </td>
                <td class="px-3 py-2.5 tabular-nums">
                  <span class="inline-block px-2 py-0.5 rounded-full {g.priority > 0.2 ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300' : g.priority > 0.1 ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}">{g.priority.toFixed(3)}</span>
                </td>
                <td class="px-3 py-2.5 tabular-nums text-slate-800 dark:text-slate-100">{g.permissiveness}</td>
                <td class="px-3 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{g.detections}</td>
                <td class="px-3 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{g.countries}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="text-xs text-slate-400 mt-2">{t('spread.synthesis.gaps.note')}</p>
    </section>
  {/if}
</div>
