<script>
  /**
   * CampaignPanels — the historical arm of the vaccine model: real
   * deployments from the corpus, joined to the spread-era timeline.
   * Everything renders from vaccine_campaigns.json (PAPER_EXTRACTED).
   */
  import { t } from '../../stores/i18n.svelte.js';
  import { announce } from '../../stores/a11y.svelte.js';

  let { doc } = $props();

  let sectorFilter = $state('all');
  const SECTORS = ['all', 'poultry_routine', 'emergency_ring', 'wildlife',
                   'zoo_captive', 'other'];

  const campaigns = $derived(doc?.campaigns ?? []);
  const filtered = $derived(
    sectorFilter === 'all' ? campaigns
      : campaigns.filter((c) => c.sector === sectorFilter)
  );
  $effect(() => {
    if (doc) announce(t('a11y.announce.campaigns.loaded', { n: filtered.length }));
  });

  const eras = $derived(
    Object.entries(doc?.by_era ?? {})
      .map(([id, e]) => ({ id, ...e,
        start: Number(e.window.start.slice(0, 4)),
        end: e.window.end ? Number(e.window.end.slice(0, 4)) : null }))
      .sort((a, b) => a.start - b.start)
  );
  const maxCamp = $derived(Math.max(1, ...eras.map((e) => e.campaigns)));

  const SECTOR_STYLE = {
    poultry_routine: 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300',
    emergency_ring: 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300',
    wildlife: 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300',
    zoo_captive: 'bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300',
    other: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  };
</script>

<div class="space-y-8">
  <!-- era timeline -->
  {#if eras.length}
    <section aria-labelledby="camp-eras">
      <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.campaigns.era.title')}
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('vaccines.campaigns.era.desc')}</p>
      <div class="mt-3 flex gap-1 items-end" role="img" aria-label={t('vaccines.campaigns.era.title')}>
        {#each eras as e (e.id)}
          <div class="flex-1 flex flex-col items-center justify-end h-28" title="{e.label}: {e.campaigns}">
            <span class="text-xs text-slate-500 dark:text-slate-400">{e.campaigns}</span>
            <div class="w-full rounded-t bg-blue-500 dark:bg-blue-400 min-h-[3px]" style="height: {Math.max((e.campaigns / maxCamp) * 70, 3)}%"></div>
            <span class="text-[11px] text-slate-500 dark:text-slate-400 mt-1 text-center leading-tight">{String(e.start).slice(2)}–{e.end ? String(e.end).slice(2) : '…'}</span>
          </div>
        {/each}
      </div>
      <ul class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {#each eras as e (e.id)}
          <li class="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3">
            <div class="text-sm font-medium text-slate-800 dark:text-slate-100">{e.label}</div>
            <div class="mt-1 flex flex-wrap gap-1">
              {#each Object.entries(e.sectors) as [s, n] (s)}
                <span class="text-xs px-1.5 py-0.5 rounded-full {SECTOR_STYLE[s] ?? SECTOR_STYLE.other}">{t(`vaccines.campaign.sector.${s}`)} {n}</span>
              {/each}
            </div>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- region span -->
  {#if Object.keys(doc?.by_region ?? {}).length}
    <section aria-labelledby="camp-regions">
      <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.campaigns.regions.title')}
      </h3>
      <ul class="mt-2 flex flex-wrap gap-2">
        {#each Object.entries(doc.by_region) as [r, v] (r)}
          <li class="text-sm px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
            <span class="font-medium">{t(`region.${r}`) !== `region.${r}` ? t(`region.${r}`) : r}</span>
            <span class="text-slate-500 dark:text-slate-400 ml-2">{v.campaigns} · {v.first}–{v.last}</span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- campaign ledger -->
  <section aria-labelledby="camp-ledger">
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h3 id="camp-ledger" class="text-lg font-bold text-gray-900 dark:text-white mb-1">
        {t('vaccines.campaigns.ledger.title')}
      </h3>
      <div class="flex flex-wrap gap-1" role="group" aria-label={t('vaccines.campaigns.filter.label')}>
        {#each SECTORS as s (s)}
          <button
            aria-pressed={sectorFilter === s}
            class="px-2.5 py-1 text-xs rounded-full border transition-colors
              {sectorFilter === s
                ? 'bg-blue-600 border-blue-700 text-white'
                : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300'}"
            onclick={() => (sectorFilter = s)}>
            {s === 'all' ? t('vaccines.outcomes.filter.all') : t(`vaccines.campaign.sector.${s}`)}
          </button>
        {/each}
      </div>
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400">
      {t('vaccines.campaigns.ledger.desc', { n: campaigns.length.toLocaleString() })}
      {#if doc?.diva}
        · {t('vaccines.campaigns.diva', { n: doc.diva.true })}
      {/if}
    </p>
    <div class="mt-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
      <table class="w-full text-sm">
        <caption class="sr-only">{t('vaccines.campaigns.ledger.title')}</caption>
        <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0">
          <tr>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('vaccines.campaigns.col.period')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('vaccines.campaigns.col.region')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('vaccines.campaigns.col.sector')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('vaccines.campaigns.col.type')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('vaccines.campaigns.col.effect')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50">
          {#each filtered.slice(0, 40) as c, i (c.paper_id + i)}
            <tr class="bg-white dark:bg-slate-900 even:bg-slate-50/60 dark:even:bg-slate-800/30">
              <td class="px-3 py-2.5 tabular-nums text-slate-600 dark:text-slate-300 whitespace-nowrap">{c.period ?? '—'}</td>
              <td class="px-3 py-2.5 text-slate-800 dark:text-slate-100">{c.region ?? '—'}</td>
              <td class="px-3 py-2.5">
                <span class="text-xs px-2 py-0.5 rounded-full {SECTOR_STYLE[c.sector] ?? SECTOR_STYLE.other}">{t(`vaccines.campaign.sector.${c.sector}`)}</span>
              </td>
              <td class="px-3 py-2.5 text-slate-500 dark:text-slate-400">{c.vaccine_type}</td>
              <td class="px-3 py-2.5 text-slate-600 dark:text-slate-300 max-w-md">{c.effect}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if filtered.length > 40}
      <p class="mt-2 text-xs text-slate-600 dark:text-slate-400">{t('common.showing.first', { n: 40, m: filtered.length.toLocaleString() })}</p>
    {/if}
  </section>

  <p class="text-xs text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-3">
    {t('vaccines.campaigns.provenance')}
  </p>
</div>
