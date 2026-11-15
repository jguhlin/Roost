<script>
  import { trackEvent } from '../lib/analytics.js';
  /**
   * Susceptibility — the v2 two-axis scoring surface.
   * No slug: overview (methodology + sortable table of all species).
   * With slug (#/susceptibility/<scientific name>): the dedicated species
   * page — full documented breakdown of how the score was reached.
   */
  import { onMount } from 'svelte';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { announce } from '../lib/stores/a11y.svelte.js';

  let { slug = '' } = $props();
  // analytics: which species susceptibility pages people open
  $effect(() => { if (slug) trackEvent('Susceptibility', 'view', decodeURIComponent(slug)); });

  let doc = $state(/** @type {any | null} */ (null));
  let error = $state(/** @type {string | null} */ (null));
  let movement = $state(/** @type {any | null} */ (null));
  let query = $state('');
  let sortKey = $state('permissiveness');
  let sortDir = $state(-1);
  let methodOpen = $state(false);

  const CLASS_STYLE = {
    highly_susceptible: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
    susceptible: 'bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300',
    intermediate: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    tolerant: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    highly_tolerant: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    unevaluated: 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
  };
  const OUTCOME_STYLE = {
    severe: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
    moderate: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    mild: 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300',
  };
  const PROV_STYLE = {
    MEASURED: 'text-emerald-600 dark:text-emerald-400',
    PAPER_EXTRACTED: 'text-blue-600 dark:text-blue-400',
    'MODELED (proxy)': 'text-amber-600 dark:text-amber-400',
  };

  onMount(async () => {
    try {
      const r = await fetch('data/species_susceptibility.json');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      doc = await r.json();
      announce(t('a11y.announce.susceptibility.loaded', {
        n: doc.species.length,
      }));
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
    fetch('data/movement_lookup.json')
      .then((r) => r.ok ? r.json() : null)
      .then((d) => (movement = d))
      .catch(() => {});
  });

  const currentMovement = $derived.by(() => {
    if (!movement?.species || !current) return null;
    return movement.species[current.species] ?? null;
  });

  const species = $derived(slug ? null : (doc?.species ?? []));
  const rows = $derived.by(() => {
    let list = species ?? [];
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter((s) =>
        (s.species + ' ' + (s.common ?? '')).toLowerCase().includes(q));
    }
    const dir = sortDir;
    return [...list].sort((a, b) => {
      if (sortKey === 'species') return dir * a.species.localeCompare(b.species);
      const av = a[sortKey] ?? -1;
      const bv = b[sortKey] ?? -1;
      return dir * (av - bv) || a.species.localeCompare(b.species);
    });
  });

  const current = $derived.by(() => {
    if (!slug || !doc) return null;
    const dec = decodeURIComponent(slug).toLowerCase();
    return doc.species.find(
      (s) => s.species.toLowerCase() === dec
        || (s.common ?? '').toLowerCase() === dec) ?? null;
  });

  function setSort(k) {
    if (sortKey === k) sortDir = -sortDir;
    else { sortKey = k; sortDir = -1; }
  }
  const ariaSort = (k) =>
    sortKey === k ? (sortDir === -1 ? 'descending' : 'ascending') : 'none';
</script>

<section class="max-w-6xl mx-auto px-4 py-8">
  {#if error}
    <p role="alert" class="text-red-700 dark:text-red-300">{t('common.load.error')} {error}</p>
  {:else if !doc}
    <p class="text-slate-500 dark:text-slate-400" aria-busy="true">{t('common.loading')}</p>
  {:else if current}
    <!-- ==================== dedicated species page ==================== -->
    <nav class="text-sm mb-4" aria-label={t('a11y.breadcrumb')}>
      <a href="#/susceptibility" class="text-blue-600 dark:text-blue-400 underline">{t('susceptibility.title')}</a>
      <span class="text-slate-400 mx-1">/</span>
      <span class="text-slate-600 dark:text-slate-300 italic">{current.species}</span>
    </nav>

    <header class="mb-6">
      <h1 class="text-3xl font-bold text-slate-900 dark:text-slate-50 italic">{current.species}</h1>
      {#if current.common}
        <p class="text-slate-500 dark:text-slate-400 mt-1">{current.common} · {current.order ?? ''}</p>
      {/if}
      <div class="mt-3 flex flex-wrap gap-2">
        <span class="px-3 py-1 rounded-full text-sm {CLASS_STYLE[current.class] ?? CLASS_STYLE.unevaluated}">
          {t(`susceptibility.class.${current.class}`)}
        </span>
        {#if current.outcome}
          <span class="px-3 py-1 rounded-full text-sm {OUTCOME_STYLE[current.outcome]}">
            {t('susceptibility.outcome.label')}: {t(`susceptibility.outcome.${current.outcome}`)}
          </span>
        {/if}
        {#if current.proxy}
          <span class="px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300">
            {t('susceptibility.proxy.badge')}
          </span>
        {/if}
        {#if current.literature_only}
          <span class="px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300">
            {t('susceptibility.litonly.badge')}
          </span>
        {/if}
      </div>
    </header>

    <!-- the two axes -->
    <div class="grid gap-4 md:grid-cols-2 mb-8">
      <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
        <h2 class="font-semibold text-slate-900 dark:text-slate-50">{t('susceptibility.axis.perm')}</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400">{t('susceptibility.axis.perm.desc')}</p>
        {#if !current.detections}
          <p class="mt-2 text-xs rounded bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 px-2.5 py-1.5 inline-block">
            {t('susceptibility.nodetections')}
          </p>
        {/if}
        <div class="mt-3 flex items-end gap-3">
          {#if (current.confidence ?? 1) < 0.3}
            <span class="text-2xl font-semibold text-slate-400 dark:text-slate-500">{t('susceptibility.insufficient')}</span>
          {:else}
            <span class="text-5xl font-bold text-blue-700 dark:text-blue-300">{current.permissiveness ?? '—'}</span>
          {/if}
          <div class="flex-1 h-3 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden" role="img" aria-label="{t('susceptibility.axis.perm')} {current.permissiveness}/100">
            <div class="h-full bg-blue-500 dark:bg-blue-400" style="width: {current.permissiveness ?? 0}%"></div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
        <h2 class="font-semibold text-slate-900 dark:text-slate-50">{t('susceptibility.axis.sev')}</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400">{t('susceptibility.axis.sev.desc')}</p>
        <div class="mt-3 flex items-end gap-3">
          {#if (current.confidence ?? 1) < 0.3}
            <span class="text-2xl font-semibold text-slate-400 dark:text-slate-500">{t('susceptibility.insufficient')}</span>
          {:else}
            <span class="text-5xl font-bold text-rose-700 dark:text-rose-300">{current.severity || '—'}</span>
          {/if}
          <div class="flex-1 h-3 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden" role="img" aria-label="{t('susceptibility.axis.sev')} {current.severity}/100">
            <div class="h-full bg-rose-500 dark:bg-rose-400" style="width: {current.severity ?? 0}%"></div>
          </div>
        </div>
        <p class="text-xs text-slate-400 mt-2" title={t('susceptibility.confidence.tip')}>{t('susceptibility.confidence')}: {current.confidence}</p>
        {#if current.severity_basis}
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('susceptibility.sev.basis')}: {t(`susceptibility.sev.basis.${current.severity_basis}`)} (n={current.severity_studies})</p>
        {/if}
      </div>
    </div>

    <!-- movement tracking -->
    {#if currentMovement}
      <section class="mb-8" aria-labelledby="sus-movement">
        <h2 id="sus-movement" class="text-xl font-bold text-slate-900 dark:text-slate-50 mb-2">
          {t('susceptibility.movement.title')}
        </h2>
        {#if currentMovement.tracked}
          <div class="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-5">
            <div class="flex flex-wrap items-baseline gap-3">
              <span class="text-4xl font-bold text-emerald-700 dark:text-emerald-300">{currentMovement.n_studies}</span>
              <div>
                <p class="text-sm font-semibold text-emerald-900 dark:text-emerald-100">
                  {t('susceptibility.movement.tracked')}
                </p>
                <p class="text-sm text-emerald-800/80 dark:text-emerald-200/80">
                  {t('susceptibility.movement.individuals', { n: currentMovement.n_individuals.toLocaleString() })}
                  {#if currentMovement.years && currentMovement.years[0]}
                    · {currentMovement.years[0]}–{currentMovement.years[1] ?? '…'}
                  {/if}
                </p>
              </div>
            </div>
            <p class="text-xs text-emerald-700/70 dark:text-emerald-300/70 mt-2">
              {t('susceptibility.movement.tracked.implies')}
              {#if currentMovement.temporal_quality === 'era_aligned'}
                <span class="ml-1 px-1.5 py-0.5 rounded bg-emerald-200/60 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200">{t('susceptibility.movement.temporal.era')}</span>
              {:else if currentMovement.temporal_quality === 'recent'}
                <span class="ml-1 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">{t('susceptibility.movement.temporal.recent')}</span>
              {:else}
                <span class="ml-1 px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">{t('susceptibility.movement.temporal.historical')}</span>
              {/if}
              <a href="https://www.movebank.org/" class="underline ml-1">Movebank</a>
            </p>
          </div>
        {:else if currentMovement.genus_tracked}
          <div class="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-5">
            <p class="text-sm font-semibold text-amber-900 dark:text-amber-100">
              ⚠ {t('susceptibility.movement.genus.title')}
            </p>
            <p class="text-sm text-amber-800/80 dark:text-amber-200/80 mt-1">
              {t('susceptibility.movement.genus.desc', {
                n: currentMovement.genus_studies,
                m: currentMovement.genus_individuals.toLocaleString(),
              })}
            </p>
            <p class="text-xs text-amber-700/70 dark:text-amber-300/70 mt-2">{t('susceptibility.movement.genus.implies')}</p>
          </div>
        {:else}
          <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 p-5">
            <p class="text-sm font-semibold text-slate-700 dark:text-slate-200">
              {t('susceptibility.movement.untracked.title')}
            </p>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('susceptibility.movement.untracked.desc')}</p>
          </div>
        {/if}
      </section>
    {/if}

    <!-- component breakdown — how we got there -->
    <section class="mb-8" aria-labelledby="sus-comp">
      <h2 id="sus-comp" class="text-xl font-bold text-slate-900 dark:text-slate-50 mb-1">
        {t('susceptibility.components.title')}
      </h2>
      <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">{t('susceptibility.components.desc')}</p>
      {#if current.components.length}
        <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
          <table class="w-full text-sm">
            <caption class="sr-only">{t('susceptibility.components.title')}</caption>
            <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0">
              <tr>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.components.col.component')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.components.col.strength')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.components.col.weight')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.components.col.contrib')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.components.col.prov')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
              {#each current.components as c (c.id)}
                <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
                  <td class="px-3 py-2.5">
                    {t(`susceptibility.component.${c.id}`)}
                    {#if c.level}<span class="text-xs text-slate-400 ml-1">({c.level}, {c.donors} {t('susceptibility.proxy.donors')})</span>{/if}
                  </td>
                  <td class="px-3 py-2.5 tabular-nums">{c.value}</td>
                  <td class="px-3 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{c.weight}</td>
                  <td class="px-3 py-2.5 tabular-nums font-medium">{c.contribution}</td>
                  <td class="px-3 py-2.5 {PROV_STYLE[c.provenance] ?? ''}">{c.provenance}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <p class="text-sm text-slate-500 dark:text-slate-400">{t('susceptibility.components.none')}</p>
      {/if}
    </section>

    <div class="grid gap-8 lg:grid-cols-2 mb-8">
      <!-- clade differences -->
      <section aria-labelledby="sus-clades">
        <h2 id="sus-clades" class="text-lg font-bold text-slate-900 dark:text-slate-50 mb-2">
          {t('susceptibility.clades.title')}
        </h2>
        {#if Object.keys(current.clades ?? {}).length}
          <ul class="space-y-1.5">
            {#each Object.entries(current.clades) as [clade, m] (clade)}
              <li class="text-sm text-slate-700 dark:text-slate-200 flex justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-1">
                <span class="font-mono text-xs text-blue-600 dark:text-blue-400">{clade}</span>
                <span>{t('spread.card.mortality')} {m.mortality}% ({t('spread.card.studies', { n: m.studies })})</span>
              </li>
            {/each}
          </ul>
        {:else}
          <p class="text-sm text-slate-500 dark:text-slate-400">{t('susceptibility.clades.none')}</p>
        {/if}
        <!-- RIG-I context -->
        <div class="mt-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 p-3">
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-200">{t('susceptibility.rigi.heading')}</h3>
          <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">
            {current.rigi.present ? t('susceptibility.rigi.present') : t('susceptibility.rigi.absent')}
            <span class="text-slate-400"> · {t('susceptibility.rigi.context')}</span>
          </p>
        </div>
      </section>

      <!-- verdicts -->
      <section aria-labelledby="sus-verdicts">
        <h2 id="sus-verdicts" class="text-lg font-bold text-slate-900 dark:text-slate-50 mb-2">
          {t('susceptibility.verdicts.title')}
        </h2>
        {#if current.verdict_summary}
          <ul class="space-y-1.5 text-sm">
            {#each ['infection_confirmed', 'exposure_only', 'resistance_suspected'] as k (k)}
              {#if current.verdict_summary[k]}
                <li class="flex justify-between border-b border-slate-100 dark:border-slate-800 pb-1">
                  <span class="text-slate-700 dark:text-slate-200">{t(`susceptibility.verdict.${k}`)}</span>
                  <span class="font-semibold tabular-nums">{current.verdict_summary[k]}</span>
                </li>
              {/if}
            {/each}
          </ul>
          <p class="text-xs text-slate-400 mt-2">
            {t('susceptibility.verdicts.grounded', { g: current.verdict_summary.grounded })}
          </p>
        {:else}
          <p class="text-sm text-slate-500 dark:text-slate-400">{t('susceptibility.verdicts.none')}</p>
        {/if}
      </section>
    </div>

    <p class="text-xs text-slate-400">
      <a href="#/spread-layers" class="underline">{t('susceptibility.link.competence')}</a>
    </p>

    {#if current.vax_program}
      <section class="mt-6 rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30 p-4" aria-labelledby="sus-vax">
        <h2 id="sus-vax" class="font-semibold text-green-900 dark:text-green-100">
          {t('susceptibility.vax.title')}
        </h2>
        <p class="text-sm text-green-800/80 dark:text-green-200/80 mt-1">
          {t('susceptibility.vax.desc', { n: current.vax_program.items })}
          {Object.entries(current.vax_program.outcomes).map(([k, v]) => `${k} ×${v}`).join(' · ')}
        </p>
        <p class="text-xs text-green-700/70 dark:text-green-300/70 mt-1">{t('susceptibility.vax.note')}</p>
      </section>
    {/if}
  {:else}
    <!-- ==================== overview ==================== -->
    <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-50">{t('susceptibility.title')}</h1>
    <p class="mt-2 text-slate-600 dark:text-slate-300 max-w-3xl">{t('susceptibility.subtitle')}</p>
    <p class="mt-2 text-sm">
      <a href="#/region-risk" class="text-blue-600 dark:text-blue-400 underline">{t('region.risk.link.species') || 'Where is each species at risk? See the regional view →'}</a>
    </p>

    <!-- methodology -->
    <button
      class="mt-4 text-sm text-blue-700 dark:text-blue-300 underline"
      aria-expanded={methodOpen}
      onclick={() => (methodOpen = !methodOpen)}>
      {t('susceptibility.method.toggle')}
    </button>
    {#if methodOpen}
      <div class="mt-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 p-5 text-sm text-slate-700 dark:text-slate-200 space-y-3">
        <p>{doc.methodology.summary}</p>
        <p><span class="font-semibold">{t('susceptibility.method.formula')}:</span> <code class="bg-white dark:bg-slate-900 rounded px-1.5 py-0.5 text-xs">{doc.methodology.formula}</code></p>
        <div>
          <span class="font-semibold">{t('susceptibility.method.weights')}:</span>
          <ul class="mt-1 grid grid-cols-2 sm:grid-cols-3 gap-1">
            {#each Object.entries(doc.methodology.weights) as [k, w] (k)}
              <li>{t(`susceptibility.component.${k}`)} — {w}</li>
            {/each}
          </ul>
        </div>
        <p><span class="font-semibold">{t('susceptibility.method.bands')}:</span>
          {Object.entries(doc.methodology.class_bands).map(([k, v]) => `${t(`susceptibility.class.${k}`)} ${v}`).join(' · ')}
        </p>
        <ul class="text-xs text-slate-500 dark:text-slate-400 list-disc pl-4">
          {#each doc.methodology.changelog as c, i (i)}<li>{c}</li>{/each}
        </ul>
      </div>
    {/if}

    <!-- table -->
    <div class="mt-5 flex flex-wrap items-center gap-3">
      <label class="sr-only" for="sus-search">{t('susceptibility.search.label')}</label>
      <input
        id="sus-search"
        type="search"
        class="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm w-64"
        placeholder={t('susceptibility.search.placeholder')}
        bind:value={query} />
      <span class="text-sm text-slate-500 dark:text-slate-400" aria-live="polite">
        {t('spread.competence.rows', { n: rows.length.toLocaleString() })}
      </span>
    </div>

    <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table class="w-full text-sm">
        <caption class="sr-only">{t('susceptibility.title')}</caption>
        <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0">
          <tr>
            <th scope="col" aria-sort={ariaSort('species')} class="px-3 py-2.5 font-semibold">
              <button class="underline decoration-dotted" onclick={() => setSort('species')}>{t('spread.competence.col.species')}</button>
            </th>
            <th scope="col" aria-sort={ariaSort('permissiveness')} class="px-3 py-2.5 font-semibold">
              <button class="underline decoration-dotted" onclick={() => setSort('permissiveness')}>{t('susceptibility.axis.perm')}</button>
            </th>
            <th scope="col" aria-sort={ariaSort('severity')} class="px-3 py-2.5 font-semibold">
              <button class="underline decoration-dotted" onclick={() => setSort('severity')}>{t('susceptibility.axis.sev')}</button>
            </th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.col.profile')}</th>
            <th scope="col" aria-sort={ariaSort('confidence')} class="px-3 py-2.5 font-semibold">
              <button class="underline decoration-dotted" onclick={() => setSort('confidence')}>{t('susceptibility.confidence')}</button>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
          {#each rows.slice(0, 50) as s (s.species)}
            <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
              <td class="px-3 py-2.5">
                <a href={`#/susceptibility/${encodeURIComponent(s.species)}`} class="font-medium text-slate-900 dark:text-slate-50 italic underline decoration-slate-300 hover:text-blue-700 dark:hover:text-blue-300">
                  {s.species}
                </a>
                {#if s.common}<span class="ml-2 text-xs text-slate-500 dark:text-slate-400">{s.common}</span>{/if}
              </td>
              <td class="px-3 py-2.5 tabular-nums text-slate-800 dark:text-slate-100">{s.confidence < 0.3 ? t('susceptibility.insufficient') : (s.permissiveness ?? '—')}</td>
              <td class="px-3 py-2.5 tabular-nums text-slate-600 dark:text-slate-300">{s.confidence < 0.3 ? '' : (s.severity || '—')}</td>
              <td class="px-3 py-2.5">
                <span class="text-xs px-2 py-0.5 rounded-full {CLASS_STYLE[s.class] ?? CLASS_STYLE.unevaluated}">{t(`susceptibility.class.${s.class}`)}</span>
                {#if s.outcome}<span class="text-xs px-2 py-0.5 rounded-full ml-1 {OUTCOME_STYLE[s.outcome]}">{t(`susceptibility.outcome.${s.outcome}`)}</span>{/if}
                {#if s.proxy}<span class="text-xs text-amber-800 dark:text-amber-300 ml-1" title={t('susceptibility.proxy.badge.tip')}>{t('susceptibility.proxy.marker')}</span>{/if}
              </td>
              <td class="px-3 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{s.confidence}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if rows.length > 50}
      <p class="mt-2 text-xs text-slate-600 dark:text-slate-400">{t('common.showing.first', { n: 50, m: rows.length.toLocaleString() })}</p>
    {/if}
  {/if}
</section>
