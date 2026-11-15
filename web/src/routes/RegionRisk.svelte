<script>
  import { trackEvent } from '../lib/analytics.js';
  /**
   * RegionRisk — the conservation operational view: species X in region Y.
   * Everything renders from region_risk.json (deterministic joins over
   * measured detections, susceptibility v2, measured seasonality, corpus
   * introduction routes, and vaccination campaigns).
   */
  import { onMount } from 'svelte';
  import { t } from '../lib/stores/i18n.svelte.js';
  import { announce } from '../lib/stores/a11y.svelte.js';

  let doc = $state(/** @type {any | null} */ (null));
  let error = $state(/** @type {string | null} */ (null));
  let selected = $state('');
  // analytics: country drill-downs
  $effect(() => { if (selected) trackEvent('RegionRisk', 'country', selected); });
  let susQuery = $state('');
  let movement = $state(/** @type {any | null} */ (null));

  const countries = $derived(Object.entries(doc?.countries ?? {}).sort((a, b) =>
    (a[1].name ?? a[0]).localeCompare(b[1].name ?? b[0])));
  const regions = $derived(Object.entries(doc?.regions ?? {}).sort(
    (a, b) => a[1].first_detection.localeCompare(b[1].first_detection)));
  const country = $derived(selected ? doc?.countries?.[selected] ?? null : null);

  onMount(async () => {
    try {
      const r = await fetch('data/region_risk.json');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      doc = await r.json();
      announce(t('a11y.announce.region.risk.loaded', { n: Object.keys(doc.countries).length }));
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
    fetch('data/movement_lookup.json')
      .then((r) => r.ok ? r.json() : null)
      .then((d) => (movement = d))
      .catch(() => {});
  });

  const moveBadge = $derived.by(() => {
    return (species) => {
      if (!movement?.species) return null;
      return movement.species[species] ?? null;
    };
  });

  const CLASS_STYLE = {
    highly_susceptible: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
    susceptible: 'bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300',
    intermediate: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    tolerant: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    highly_tolerant: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    unevaluated: 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
  };

  const months = $derived.by(() => {
    const s = country?.seasonality ?? {};
    return Array.from({ length: 12 }, (_, i) => ({ m: i + 1, n: s[String(i + 1)] ?? 0 }));
  });
  const maxMonth = $derived(Math.max(1, ...months.map((x) => x.n)));

  const detected = $derived.by(() => {
    let list = country?.detected ?? [];
    const q = susQuery.trim().toLowerCase();
    if (q) list = list.filter((s) => (s.species + ' ' + (s.common ?? '')).toLowerCase().includes(q));
    return list;
  });

  function regionLabel(r) {
    const key = `region.${r}`;
    const val = t(key);
    return val === key ? r : val;
  }
</script>

<section class="max-w-6xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-50">{t('region.risk.title')}</h1>
  <p class="mt-2 text-slate-600 dark:text-slate-300 max-w-3xl">{t('region.risk.subtitle')}</p>

  {#if error}
    <p role="alert" class="mt-6 text-red-700 dark:text-red-300">{t('common.load.error')} {error}</p>
  {:else if !doc}
    <p class="mt-6 text-slate-500 dark:text-slate-400" aria-busy="true">{t('common.loading')}</p>
  {:else}
    <div class="mt-5 flex flex-wrap items-center gap-3">
      <label class="text-sm text-slate-600 dark:text-slate-300" for="region-select">
        {t('region.risk.select')}
      </label>
      <select
        id="region-select"
        class="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm max-w-[calc(100vw-6rem)] sm:max-w-xs min-w-0"
        bind:value={selected}>
        <option value="">{t('region.risk.world')}</option>
        {#each countries as [code, c] (code)}
          <option value={code}>{c.name ?? code} ({code})</option>
        {/each}
      </select>
      {#if country}
        <span class="text-sm text-slate-500 dark:text-slate-400">{regionLabel(country.region)}</span>
      {/if}
    </div>

    {#if country}
      <!-- presence -->
      <div class="mt-6 grid gap-4 md:grid-cols-4">
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <div class="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('region.risk.first')}</div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">{country.first_detection}</div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{country.first_era ?? ''}</div>
        </div>
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <div class="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('region.risk.records')}</div>
          <div class="text-2xl font-bold text-slate-900 dark:text-slate-50 mt-1">{country.total_records.toLocaleString()}</div>
          <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{country.species_count} {t('region.risk.species')}</div>
        </div>
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 md:col-span-2">
          <div class="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('region.risk.season.window')}</div>
          {#if months.some((m) => m.n > 0)}
            <div class="mt-2 flex items-end gap-1 h-12" role="img" aria-label={t('spread.feat.seasonality.aria')}>
              {#each months as m (m.m)}
                <div class="flex-1 rounded-t bg-blue-500 dark:bg-blue-400 min-h-[2px]" style="height: {Math.max((m.n / maxMonth) * 100, m.n > 0 ? 4 : 0)}%" title="{t('spread.feat.month')} {m.m}: {m.n.toLocaleString()}"></div>
              {/each}
            </div>
          {:else}
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">{t('spread.feat.no.data')}</p>
          {/if}
        </div>
      </div>

      <!-- arrival risk (the prediction layer) -->
      {#if country.arrival_risk}
        {@const ar = country.arrival_risk}
        {#if ar.band === 'arrived'}
          <div class="mt-4 rounded-xl border-2 border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950/30 p-5">
            <div class="flex flex-wrap items-baseline justify-between gap-3">
              <div>
                <h2 class="text-lg font-bold text-red-700 dark:text-red-300">
                  {t('region.risk.arrived.title')}
                </h2>
                <p class="text-sm text-red-700/70 dark:text-red-300/70 mt-1">
                  {t('region.risk.arrived.text', {
                    date: country.first_detection,
                    n: country.species_count,
                    r: country.total_records
                  })}
                </p>
              </div>
              <span class="text-4xl">🟢</span>
            </div>
          </div>
        {:else}
        <div class="mt-4 rounded-xl border-2 {ar.band === 'high' ? 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950/30' : ar.band === 'moderate' ? 'border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30' : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800'} p-5">
          <div class="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold {ar.band === 'high' ? 'text-red-700 dark:text-red-300' : ar.band === 'moderate' ? 'text-amber-700 dark:text-amber-300' : 'text-slate-700 dark:text-slate-200'}">
                {t('region.risk.arrival.title')} — {t(`region.risk.arrival.band.${ar.band}`)}
              </h2>
              <p class="text-sm text-slate-600 dark:text-slate-300 mt-1">{t('region.risk.arrival.desc')}</p>
            </div>
            <div class="text-5xl font-bold {ar.band === 'high' ? 'text-red-600 dark:text-red-400' : ar.band === 'moderate' ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500 dark:text-slate-400'}">
              {ar.score}
            </div>
          </div>
          <div class="mt-4 grid gap-2 sm:grid-cols-5">
            {#each [['source_proximity', 'region.risk.arrival.prox'], ['bridge_pressure', 'region.risk.arrival.bridge'], ['movement_intelligence', 'region.risk.arrival.intel'], ['seasonal_signal', 'region.risk.arrival.season'], ['era_activity', 'region.risk.arrival.era']] as [key, label] (key)}
              <div class="text-center">
                <div class="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                  <div class="h-full {ar.band === 'high' ? 'bg-red-400' : 'bg-amber-400'}" style="width: {ar[key] * 100}%"></div>
                </div>
                <div class="text-[10px] text-slate-500 dark:text-slate-400 mt-1">{t(label)}</div>
              </div>
            {/each}
          </div>
          {#if ar.bridge_species_count > 0}
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-3">
              {t('region.risk.arrival.bridges', { n: ar.bridge_species_count, m: ar.bridge_species_tracked })}
            </p>
          {/if}
        </div>
        {/if}
      {/if}

      <!-- routes + campaigns -->
      <div class="mt-4 grid gap-4 md:grid-cols-2">
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200">{t('region.risk.routes')}</h2>
          <ul class="mt-2 flex flex-wrap gap-2">
            {#each Object.entries(country.intro_routes ?? {}) as [route, n] (route)}
              <li class="text-sm px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">{route} <span class="font-semibold">{n}</span></li>
            {:else}
              <li class="text-sm text-slate-500 dark:text-slate-400">{t('spread.feat.no.data')}</li>
            {/each}
          </ul>
        </div>
        <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200">{t('region.risk.programs')}</h2>
          <ul class="mt-2 space-y-1 text-sm">
            {#each country.campaigns ?? [] as c, i (i)}
              <li class="text-slate-700 dark:text-slate-200">{c.region} · {c.period} · <span class="text-slate-500 dark:text-slate-400">{t(`vaccines.campaign.sector.${c.sector}`)}</span></li>
            {:else}
              <li class="text-slate-500 dark:text-slate-400">{t('region.risk.programs.none')}</li>
            {/each}
          </ul>
        </div>
      </div>

      <!-- watchlist -->
      <section class="mt-8" aria-labelledby="watch-head">
        <h2 id="watch-head" class="text-xl font-bold text-slate-900 dark:text-slate-50 mb-1">
          {t('region.risk.watchlist.title')}
        </h2>
        <p class="text-sm text-slate-500 dark:text-slate-400">{country.watchlist.note}</p>
        <div class="mt-3 grid gap-6 lg:grid-cols-2">
          <div>
            <h3 class="text-sm font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wide">{t('region.risk.watchlist.relatives')}</h3>
            <ul class="mt-2 space-y-1.5">
              {#each country.watchlist.relatives_arrived as s (s.species)}
                <li class="flex items-baseline justify-between gap-2 text-sm border-b border-slate-100 dark:border-slate-800 pb-1">
                  <span class="flex items-baseline gap-1.5">
                    <a class="italic text-slate-800 dark:text-slate-100 underline decoration-slate-300" href={`#/susceptibility/${encodeURIComponent(s.species)}`}>{s.species}</a>
                    {#if moveBadge(s.species)?.tracked}
                      <span class="text-[10px] text-emerald-600 dark:text-emerald-400" title={t('region.risk.movement.tracked.tip')}>📍</span>
                    {:else if moveBadge(s.species)?.genus_tracked}
                      <span class="text-[10px] text-amber-600 dark:text-amber-400" title={t('region.risk.movement.genus.tip')}>📍~</span>
                    {:else}
                      <span class="text-[10px] text-slate-400" title={t('region.risk.movement.untracked.tip')}>📍?</span>
                    {/if}
                  </span>
                  <span class="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">perm {s.permissiveness} · sev {s.severity ?? '—'}</span>
                </li>
              {:else}
                <li class="text-sm text-slate-500 dark:text-slate-400">{t('region.risk.watchlist.empty')}</li>
              {/each}
            </ul>
          </div>
          <div>
            <h3 class="text-sm font-semibold text-rose-700 dark:text-rose-300 uppercase tracking-wide">{t('region.risk.watchlist.global')}</h3>
            <ul class="mt-2 space-y-1.5">
              {#each country.watchlist.global as s (s.species)}
                <li class="flex items-baseline justify-between gap-2 text-sm border-b border-slate-100 dark:border-slate-800 pb-1">
                  <span class="flex items-baseline gap-1.5">
                    <span>
                      <a class="italic text-slate-800 dark:text-slate-100 underline decoration-slate-300" href={`#/susceptibility/${encodeURIComponent(s.species)}`}>{s.species}</a>
                      {#if s.vax_program}<span class="ml-1 text-xs text-green-700 dark:text-green-300" title={t('region.risk.vax.flag')}>💉</span>{/if}
                    </span>
                    {#if moveBadge(s.species)?.tracked}
                      <span class="text-[10px] text-emerald-600 dark:text-emerald-400" title={t('region.risk.movement.tracked.tip')}>📍</span>
                    {:else if moveBadge(s.species)?.genus_tracked}
                      <span class="text-[10px] text-amber-600 dark:text-amber-400" title={t('region.risk.movement.genus.tip')}>📍~</span>
                    {:else}
                      <span class="text-[10px] text-slate-400" title={t('region.risk.movement.untracked.tip')}>📍?</span>
                    {/if}
                  </span>
                  <span class="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">perm {s.permissiveness}</span>
                </li>
              {:else}
                <li class="text-sm text-slate-500 dark:text-slate-400">{t('region.risk.watchlist.empty')}</li>
              {/each}
            </ul>
          </div>
        </div>
      </section>

      <!-- detected species -->
      <section class="mt-8" aria-labelledby="det-head">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="det-head" class="text-xl font-bold text-slate-900 dark:text-slate-50">
            {t('region.risk.detected.title')}
          </h2>
          <label class="sr-only" for="det-search">{t('spread.competence.search.label')}</label>
          <input id="det-search" type="search" class="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm w-56"
            placeholder={t('susceptibility.search.placeholder')} bind:value={susQuery} />
        </div>
        <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
          <table class="w-full text-sm">
            <caption class="sr-only">{t('region.risk.detected.title')}</caption>
            <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0">
              <tr>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('spread.competence.col.species')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('region.risk.first')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('region.risk.last')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.axis.perm')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.axis.sev')}</th>
                <th scope="col" class="px-3 py-2.5 font-semibold">{t('susceptibility.col.profile')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
              {#each detected.slice(0, 40) as s (s.species)}
                <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
                  <td class="px-3 py-2.5">
                    <a class="italic font-medium text-slate-900 dark:text-slate-50 underline decoration-slate-300" href={`#/susceptibility/${encodeURIComponent(s.species)}`}>{s.species}</a>
                    {#if s.common}<span class="ml-2 text-xs text-slate-500 dark:text-slate-400">{s.common}</span>{/if}
                  </td>
                  <td class="px-3 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{s.first}</td>
                  <td class="px-3 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{s.last}</td>
                  <td class="px-3 py-2.5 tabular-nums text-slate-800 dark:text-slate-100">{s.permissiveness ?? '—'}</td>
                  <td class="px-3 py-2.5 tabular-nums text-slate-600 dark:text-slate-300">{s.severity || '—'}</td>
                  <td class="px-3 py-2.5">
                    <span class="text-xs px-2 py-0.5 rounded-full {CLASS_STYLE[s.class] ?? CLASS_STYLE.unevaluated}">{t(`susceptibility.class.${s.class}`)}</span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if detected.length > 40}
          <p class="mt-2 text-xs text-slate-600 dark:text-slate-400">{t('common.showing.first', { n: 40, m: detected.length.toLocaleString() })}</p>
        {/if}
      </section>
    {:else}
      <!-- world view: region rollups -->
      <ul class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {#each regions as [bucket, r] (bucket)}
          <li class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <h2 class="font-semibold text-slate-900 dark:text-slate-50">{regionLabel(bucket)}</h2>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {t('region.risk.first')}: {r.first_detection} · {r.countries} {t('region.risk.countries')}
            </p>
            <p class="text-sm text-slate-500 dark:text-slate-400">{r.total_records.toLocaleString()} {t('region.risk.records').toLowerCase()}</p>
          </li>
        {/each}
      </ul>
      <p class="mt-4 text-sm text-slate-500 dark:text-slate-400">{t('region.risk.world.hint')}</p>
    {/if}
  {/if}
</section>
