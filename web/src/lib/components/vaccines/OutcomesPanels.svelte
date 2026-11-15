<script>
  /**
   * OutcomesPanels — what the corpus says vaccination achieved.
   * Consumes vaccine_outcomes.json (PAPER_EXTRACTED intervention outcomes +
   * verified platform claims + the protection-gap join). Every number on
   * screen comes from the artifact; provenance labels are data-driven.
   */
  import { t } from '../../stores/i18n.svelte.js';
  import { announce } from '../../stores/a11y.svelte.js';

  let { doc } = $props();

  let settingFilter = $state('all'); // all | farm | wild
  const FILTERS = [
    { id: 'all', label: 'vaccines.outcomes.filter.all' },
    { id: 'farm', label: 'vaccines.outcomes.filter.farm' },
    { id: 'wild', label: 'vaccines.outcomes.filter.wild' },
  ];

  const OUTCOME_STYLE = {
    worked: 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300',
    partial: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
    unclear: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  };

  const items = $derived(doc?.vaccination?.items ?? []);
  const filtered = $derived.by(() => {
    if (settingFilter === 'farm') return items.filter((i) => i.setting === 'farm');
    if (settingFilter === 'wild')
      return items.filter((i) => ['wild', 'captive', 'zoo'].includes(i.setting));
    return items;
  });
  $effect(() => {
    if (doc) announce(t('a11y.announce.vaccine.outcomes', { n: filtered.length }));
  });

  const years = $derived(
    Object.entries(doc?.vaccination?.by_year ?? {})
      .map(([y, n]) => ({ y: Number(y), n }))
      .sort((a, b) => a.y - b.y)
  );
  const maxYear = $derived(Math.max(1, ...years.map((x) => x.n)));

  const wildPrograms = $derived(doc?.wild_programs ?? []);
  const efficacy = $derived(doc?.platforms?.efficacy_rows ?? []);
  const gaps = $derived(doc?.protection_gaps?.candidates ?? []);
  const vaccinatedSpecies = $derived(doc?.protection_gaps?.vaccinated_species ?? []);
  const landscape = $derived(
    Object.entries(doc?.response_landscape ?? {})
      .sort((a, b) => b[1] - a[1])
      .filter(([k]) => k !== 'vaccination')
  );
</script>

<div class="space-y-10">
  <!-- headline stats -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
    {#each Object.entries(doc?.vaccination?.outcomes ?? {}) as [outcome, n] (outcome)}
      <div class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 text-center">
        <div class="text-3xl font-bold {outcome === 'worked' ? 'text-green-600 dark:text-green-400' : outcome === 'failed' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}">
          {n}
        </div>
        <div class="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mt-1">
          {t(`vaccines.outcome.${outcome}`)}
        </div>
      </div>
    {/each}
  </div>

  <!-- outcome ledger -->
  <section aria-labelledby="vax-ledger">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h3 id="vax-ledger" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.outcomes.ledger.title')}
      </h3>
      <div class="flex gap-1" role="group" aria-label={t('vaccines.outcomes.filter.label')}>
        {#each FILTERS as f (f.id)}
          <button
            aria-pressed={settingFilter === f.id}
            class="px-3 py-1 text-xs rounded-full border transition-colors
              {settingFilter === f.id
                ? 'bg-blue-600 border-blue-700 text-white'
                : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300'}"
            onclick={() => (settingFilter = f.id)}>{t(f.label)}</button>
        {/each}
      </div>
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {t('vaccines.outcomes.ledger.desc', {
        n: (doc?.vaccination?.papers ?? 0).toLocaleString(),
        g: (items.filter((i) => i.grounded).length).toLocaleString(),
      })}
    </p>
    <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table class="w-full text-sm">
        <caption class="sr-only">{t('vaccines.outcomes.ledger.title')}</caption>
        <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0 z-10">
          <tr>
            <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.col.species')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.col.setting')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.col.outcome')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.col.metric')}</th>
            <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.col.year')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
          {#each filtered.slice(0, 40) as it (it.paper_id)}
            <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
              <td class="px-3 py-2 font-medium text-slate-800 dark:text-slate-100">{it.target_species ?? '—'}</td>
              <td class="px-3 py-2 text-slate-600 dark:text-slate-300">{t(`vaccines.setting.${it.setting || 'other'}`)}</td>
              <td class="px-3 py-2">
                <span class="text-xs px-2 py-0.5 rounded-full {OUTCOME_STYLE[it.outcome] ?? OUTCOME_STYLE.unclear}">
                  {t(`vaccines.outcome.${it.outcome || 'unclear'}`)}
                </span>
              </td>
              <td class="px-3 py-2 text-slate-600 dark:text-slate-300 max-w-md">{it.metric}</td>
              <td class="px-3 py-2 text-slate-500 dark:text-slate-400 tabular-nums">{it.year ?? '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if filtered.length > 40}
      <p class="mt-2 text-xs text-slate-400">{t('common.showing.first', { n: 40, m: filtered.length.toLocaleString() })}</p>
    {/if}
  </section>

  <!-- wild programs -->
  {#if wildPrograms.length}
    <section aria-labelledby="vax-wild">
      <h3 id="vax-wild" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.outcomes.wild.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('vaccines.outcomes.wild.desc')}</p>
      <ul class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {#each wildPrograms as p (p.paper_id)}
          <li class="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <div class="flex items-baseline justify-between gap-2">
              <h4 class="font-semibold text-slate-900 dark:text-slate-50">{p.target_species}</h4>
              <span class="text-xs px-2 py-0.5 rounded-full {OUTCOME_STYLE[p.outcome] ?? OUTCOME_STYLE.unclear}">
                {t(`vaccines.outcome.${p.outcome || 'unclear'}`)}
              </span>
            </div>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">{p.metric}</p>
            <p class="mt-2 text-xs text-slate-400">{t(`vaccines.setting.${p.setting || 'other'}`)} · {p.year ?? ''} · {p.paper_id}</p>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- timeline -->
  {#if years.length}
    <section aria-labelledby="vax-years">
      <h3 id="vax-years" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.outcomes.timeline.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('vaccines.outcomes.timeline.desc')}</p>
      <div class="mt-3 flex items-end gap-1 h-24" role="img" aria-label={t('vaccines.outcomes.timeline.aria')}>
        {#each years as y (y.y)}
          <div class="flex-1 flex flex-col items-center justify-end h-full" title="{y.y}: {y.n}">
            <span class="text-[10px] text-slate-400">{y.n}</span>
            <div
              class="w-full rounded-t bg-blue-500 dark:bg-blue-400 min-h-[2px]"
              style="height: {Math.max((y.n / maxYear) * 70, 2)}%"
            ></div>
            <span class="text-[10px] text-slate-400 mt-1">{String(y.y).slice(2)}</span>
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <!-- protection gaps -->
  {#if gaps.length}
    <section aria-labelledby="vax-gaps">
      <h3 id="vax-gaps" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.outcomes.gaps.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('vaccines.outcomes.gaps.desc', {
          v: vaccinatedSpecies.length,
          c: gaps.length,
        })}
      </p>
      <p class="mt-2 text-xs text-slate-400">{t('vaccines.outcomes.gaps.note')}</p>
      <ul class="mt-3 flex flex-wrap gap-2">
        {#each gaps.slice(0, 28) as g (g.species)}
          <li class="text-xs px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            <span class="italic">{g.species}</span>
            <span class="text-slate-400 ml-1">· {t('vaccines.outcomes.gaps.susceptibility')} {g.susceptibility ?? '—'}{#if g.mortality_pct != null} · {t('vaccines.outcomes.gaps.mortality')} {g.mortality_pct}%{/if}</span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- platform depth -->
  {#if doc?.platforms?.claims}
    <section aria-labelledby="vax-platforms">
      <h3 id="vax-platforms" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.outcomes.platforms.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('vaccines.outcomes.platforms.desc', {
          n: doc.platforms.claims,
          d: doc.platforms.diva_compatible,
        })}
      </p>
      {#if efficacy.length}
        <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
          <table class="w-full text-sm">
            <caption class="sr-only">{t('vaccines.outcomes.platforms.efficacy')}</caption>
            <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0 z-10">
              <tr>
                <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.col.species')}</th>
                <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.platforms.col.platform')}</th>
                <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.platforms.col.clade')}</th>
                <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.platforms.col.mortality')}</th>
                <th scope="col" class="px-3 py-2 font-semibold">{t('vaccines.outcomes.platforms.col.lab')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
              {#each efficacy as r, ri (r.paper_id + ':' + ri)}
                <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
                  <td class="px-3 py-2 text-slate-800 dark:text-slate-100">{r.species ?? '—'}</td>
                  <td class="px-3 py-2 text-slate-600 dark:text-slate-300">{r.platform ?? '—'}</td>
                  <td class="px-3 py-2 text-slate-500 dark:text-slate-400">{r.challenge_clade ?? '—'}</td>
                  <td class="px-3 py-2 text-slate-600 dark:text-slate-300">
                    {#if r.mortality_vaccinated != null || r.mortality_control != null}
                      <span class="text-green-700 dark:text-green-300">{r.mortality_vaccinated ?? '—'}</span>
                      <span class="text-slate-400"> vs </span>
                      <span class="text-red-700 dark:text-red-300">{r.mortality_control ?? '—'}</span>
                    {:else}—{/if}
                  </td>
                  <td class="px-3 py-2 text-slate-500 dark:text-slate-400">{r.field_or_lab ?? '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}

  <!-- response landscape -->
  {#if landscape.length}
    <section aria-labelledby="vax-landscape">
      <h3 id="vax-landscape" class="text-xl font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.outcomes.landscape.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('vaccines.outcomes.landscape.desc')}</p>
      <ul class="mt-3 flex flex-wrap gap-2">
        {#each landscape as [kind, n] (kind)}
          <li class="text-sm px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            {kind} <span class="font-semibold">{n}</span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <p class="text-xs text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-3">
    {t('vaccines.outcomes.provenance')}
  </p>
</div>
