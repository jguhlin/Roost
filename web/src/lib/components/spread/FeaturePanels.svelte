<script>
  /**
   * FeaturePanels — [DET] measured dynamics from spread_features.json:
   * seasonality curves (era × month), diffusion chronology, persistence
   * pairs, mass events, mammal share, sampling mix. All values MEASURED
   * from the detections feed; every panel states what it is.
   */
  import { t } from '../../stores/i18n.svelte.js';

  let { doc, commonNames } = $props();

  let eraId = $state(/** @type {string | null} */ (null));
  $effect(() => {
    if (doc && !eraId) {
      const ids = Object.keys(doc.seasonality ?? {});
      eraId = ids.includes('panzootic_2344b') ? 'panzootic_2344b' : (ids[ids.length - 1] ?? null);
    }
  });
  const season = $derived(doc?.seasonality?.[/** @type {string} */ (eraId)] ?? null);
  const months = $derived(
    season
      ? Array.from({ length: 12 }, (_, i) => ({
          m: i + 1,
          n: season.by_month?.[String(i + 1)] ?? 0,
        }))
      : []
  );
  const maxMonth = $derived(Math.max(1, ...months.map((x) => x.n)));

  const PERSIST_TOP = 12;
  const persistTop = $derived(
    (doc?.persistence?.pairs ?? []).slice(0, PERSIST_TOP)
  );
  const MASS_TOP = 8;
  const massTop = $derived(
    (doc?.mass_events?.largest_wildlife ?? []).slice(0, MASS_TOP)
  );
  const mammalYears = $derived(doc?.mammal_share?.by_year ?? []);
  const maxMammal = $derived(Math.max(1, ...mammalYears.map((y) => y.mammal_pct ?? 0)));

  const samplingYears = $derived.by(() => {
    const by = doc?.sampling_mix?.by_year ?? {};
    return Object.entries(by)
      .sort((a, b) => Number(b[0]) - Number(a[0]))
      .slice(0, 6);
  });

  function dispSpecies(sci) {
    return commonNames?.get(sci) ?? sci;
  }
</script>

<div class="space-y-8">
  <!-- seasonality -->
  <section aria-labelledby="feat-seasonality">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h2 id="feat-seasonality" class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.feat.seasonality')}</h2>
      <label class="text-sm text-slate-600 dark:text-slate-300">
        {t('spread.feat.era')}
        <select
          class="ml-2 px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm"
          bind:value={eraId}
        >
          {#each Object.keys(doc?.seasonality ?? {}) as id (id)}
            <option value={id}>{id}</option>
          {/each}
        </select>
      </label>
    </div>
    {#if season}
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {t('spread.feat.seasonality.desc', { n: (season.total ?? 0).toLocaleString() })}
      </p>
      <div class="mt-3 flex items-end gap-1.5 h-36" role="img" aria-label={t('spread.feat.seasonality.aria')}>
        {#each months as { m, n } (m)}
          <div class="flex-1 flex flex-col items-center justify-end h-full">
            <div
              class="w-full rounded-t bg-blue-500 dark:bg-blue-400 min-h-[2px]"
              style="height: {Math.max((n / maxMonth) * 100, n > 0 ? 2 : 0)}%"
              title="{t('spread.feat.month')} {m}: {n.toLocaleString()}"
            ></div>
            <span class="text-xs text-slate-400 mt-1">{m}</span>
          </div>
        {/each}
      </div>
    {:else}
      <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">{t('spread.feat.no.data')}</p>
    {/if}
  </section>

  <!-- diffusion -->
  <section aria-labelledby="feat-diffusion">
    <h2 id="feat-diffusion" class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.feat.diffusion')}</h2>
    <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('spread.feat.diffusion.desc')}</p>
    <ul class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {#each Object.entries(doc?.diffusion ?? {}) as [id, f] (id)}
        <li class="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3">
          <h3 class="text-sm font-medium text-slate-800 dark:text-slate-100">{id}</h3>
          <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">
            {t('spread.feat.diffusion.origin', { c: f.origin_country, d: f.first_stamp })}
          </p>
          <p class="mt-1 text-sm">
            {#if f.early_wave_km_per_day != null}
              <strong class="text-slate-900 dark:text-slate-50">{f.early_wave_km_per_day} {t('units.km.per.day')}</strong>
            {:else}
              <span class="text-slate-400">— {t('spread.feat.diffusion.no.slope')}</span>
            {/if}
          </p>
        </li>
      {/each}
    </ul>
  </section>

  <div class="grid gap-8 lg:grid-cols-2">
    <!-- persistence -->
    <section aria-labelledby="feat-persistence">
      <h2 id="feat-persistence" class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.feat.persistence')}</h2>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {t('spread.feat.persistence.desc', { n: (doc?.persistence?.pairs ?? []).length.toLocaleString(), y: doc?.persistence?.min_years ?? 2 })}
      </p>
      <ul class="mt-3 divide-y divide-slate-100 dark:divide-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-700">
        {#each persistTop as p (p.country + p.species)}
          <li class="flex justify-between gap-2 px-3 py-2 text-sm bg-white dark:bg-slate-800">
            <span class="min-w-0">
              <span class="font-medium text-slate-800 dark:text-slate-100">{p.country}</span>
              <span class="ml-2 text-slate-600 dark:text-slate-300 truncate">{dispSpecies(p.species)}</span>
            </span>
            <span class="tabular-nums text-slate-500 dark:text-slate-400 whitespace-nowrap">
              {p.years} {t('units.years')} · {p.first.slice(0, 4)}–{p.last.slice(0, 4)}
            </span>
          </li>
        {/each}
      </ul>
    </section>

    <!-- mass events -->
    <section aria-labelledby="feat-mass">
      <h2 id="feat-mass" class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.feat.mass')}</h2>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {t('spread.feat.mass.desc', {
          p: (doc?.mass_events?.poultry_count ?? 0).toLocaleString(),
          w: (doc?.mass_events?.wildlife_count ?? 0).toLocaleString(),
          n: doc?.mass_events?.threshold ?? 100,
        })}
      </p>
      <ul class="mt-3 space-y-2">
        {#each massTop as e, i (i)}
          <li class="flex justify-between gap-2 text-sm px-3 py-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            <span class="min-w-0">
              <span class="font-medium text-slate-800 dark:text-slate-100">{dispSpecies(e.species ?? '')}</span>
              <span class="ml-2 text-slate-500 dark:text-slate-400">{e.country} · {e.date}</span>
            </span>
            <span class="tabular-nums text-slate-700 dark:text-slate-200 whitespace-nowrap">{e.count.toLocaleString()}</span>
          </li>
        {/each}
      </ul>
    </section>
  </div>

  <div class="grid gap-8 lg:grid-cols-2">
    <!-- mammal share -->
    <section aria-labelledby="feat-mammal">
      <h2 id="feat-mammal" class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.feat.mammal')}</h2>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('spread.feat.mammal.desc')}</p>
      <div class="mt-3 flex items-end gap-1 h-28" role="img" aria-label={t('spread.feat.mammal.aria')}>
        {#each mammalYears as y (y.year)}
          <div class="flex-1 flex flex-col items-center justify-end h-full">
            <span class="text-xs text-slate-400">{y.mammal_pct}%</span>
            <div
              class="w-full rounded-t bg-amber-500 dark:bg-amber-400 min-h-[2px]"
              style="height: {Math.max((y.mammal_pct ?? 0) / maxMammal * 80, 2)}%"
              title={t('spread.features.mammal_share_tip', { year: y.year, pct: y.mammal_pct ?? 0, n: y.mammal_n ?? 0, total: y.total ?? 0 })}
            ></div>
            <span class="text-xs text-slate-400 mt-1">{String(y.year).slice(2)}</span>
          </div>
        {/each}
      </div>
    </section>

    <!-- sampling mix -->
    <section aria-labelledby="feat-sampling">
      <h2 id="feat-sampling" class="font-semibold text-slate-900 dark:text-slate-50">{t('spread.feat.sampling')}</h2>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('spread.feat.sampling.desc')}</p>
      <table class="mt-3 w-full text-sm">
        <caption class="sr-only">{t('spread.feat.sampling')}</caption>
        <thead>
          <tr class="text-left text-xs text-slate-500 dark:text-slate-400">
            <th scope="col" class="py-1 pr-3">{t('spread.feat.year')}</th>
            <th scope="col" class="py-1">{t('spread.feat.top.types')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
          {#each samplingYears as [y, types] (y)}
            <tr>
              <td class="py-1.5 pr-3 font-medium text-slate-700 dark:text-slate-200 tabular-nums">{y}</td>
              <td class="py-1.5 text-slate-600 dark:text-slate-300">
                {#each Object.entries(types).sort((a, b) => b[1] - a[1]).slice(0, 3) as [ty, n] (ty)}
                  <span class="mr-3">{ty}: {n.toLocaleString()}</span>
                {/each}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  </div>

  <p class="text-xs text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-3">
    {t('spread.feat.provenance')}
  </p>
</div>
