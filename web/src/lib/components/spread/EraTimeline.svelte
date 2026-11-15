<script>
  /**
   * EraTimeline — Layer A ledger: proportional era band + chapter detail.
   * Widths derive from window durations; chapters render whatever the feed
   * measured (null measured + note ships as "no feed coverage" — never a
   * made-up number). Paper links resolve via papersIndex.
   */
  import { t } from '../../stores/i18n.svelte.js';

  let { eras, papersIndex, findings, introByEra } = $props();

  // default to the open-ended era (latest start) once data lands
  let selected = $state(null);
  $effect(() => {
    if (eras && !selected) {
      const open = [...eras].sort((a, b) => b.window.start.localeCompare(a.window.start));
      selected = open[0]?.id ?? null;
    }
  });
  const era = $derived(eras?.find((e) => e.id === selected) ?? null);

  const START = 1996;
  const END = 2027;
  function span(e) {
    const s = new Date(e.window.start).getTime();
    const endStr = e.window.end ?? '2027-01-01';
    const x = new Date(endStr).getTime();
    return Math.max(x - s, 0.75 * 365.25 * 864e5); // min visual width
  }
  const totalSpan = $derived(
    eras ? eras.reduce((acc, e) => acc + span(e), 0) : 1
  );

  function fmtDate(iso) {
    return iso ?? '';
  }
  const regionLabelCache = {};
  function regionLabel(r) {
    if (!regionLabelCache[r]) {
      regionLabelCache[r] = r
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
    }
    return regionLabelCache[r];
  }

  const PAPER_SAMPLE = 6
  const eraPapersTotal = $derived(era?.papers?.total ?? era?.papers?.length ?? 0);
  const eraDesignations = $derived(
    Object.entries(era?.papers?.designation_papers ?? {}).sort((a, b) => b[1] - a[1])
  );;
  const eraPapers = $derived(era?.papers ?? []);
  const paperSample = $derived(eraPapers.slice(0, PAPER_SAMPLE));
</script>

{#if eras}
  <!-- proportional era band -->
  <div class="flex gap-1 w-full" role="group" aria-label={t('spread.eras.band.label')}>
    {#each eras as e (e.id)}
      <button
        style="flex-grow: {span(e) / totalSpan}"
        aria-pressed={selected === e.id}
        class="px-2 py-3 text-left text-sm leading-tight rounded-md border transition-colors min-w-0
          {selected === e.id
            ? 'bg-blue-600 border-blue-700 text-white'
            : 'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'}"
        onclick={() => (selected = e.id)}>
        <span class="block font-semibold truncate">{e.label}</span>
        <span class="block opacity-80 truncate text-xs">{e.window.start.slice(0, 4)}–{e.window.end ? e.window.end.slice(0, 4) : '…'}</span>
      </button>
    {/each}
  </div>

  {#if era}
    <div class="mt-6 grid gap-6 lg:grid-cols-3">
      <!-- narrative -->
      <div class="lg:col-span-2 space-y-4">
        {#if findings?.detection_lag}
          {@const lag = findings.detection_lag}
          <p class="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 px-4 py-2.5 text-sm text-blue-800 dark:text-blue-200">
            {t('spread.era.lag.caveat', { m: lag.median, q1: lag.p25, q3: lag.p75, n: lag.n })}
          </p>
        {/if}
        <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 class="font-semibold text-slate-900 dark:text-slate-50">{era.label}</h2>
            {#if introByEra?.[era.id]}
              <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300" title={t('spread.era.intro.chip.tip')}>
                {introByEra[era.id]} {t('spread.era.intro.chip')}
              </span>
            {/if}
          </div>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {t('spread.era.window')}: {fmtDate(era.window.start)} → {era.window.end ? fmtDate(era.window.end) : t('spread.era.ongoing')}
            · {era.lineages}
          </p>
          <p class="mt-3 text-slate-700 dark:text-slate-200 text-base leading-relaxed">{era.narrative}</p>
          {#if era.note}
            <p class="mt-2 text-amber-700 dark:text-amber-300 text-sm">{era.note}</p>
          {/if}
        </div>

        <!-- chapters -->
        <h3 class="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {t('spread.era.chapters')}
        </h3>
        <ul class="space-y-3">
          {#each era.chapters as ch (ch.id)}
            <li class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h4 class="font-medium text-slate-900 dark:text-slate-100">{ch.label}</h4>
                <span class="text-sm text-slate-500 dark:text-slate-400">{ch.window.start} → {ch.window.end}</span>
              </div>
              <div class="mt-2 flex flex-wrap gap-1">
                {#each ch.regions as r (r)}
                  <span class="text-sm px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">{regionLabel(r)}</span>
                {/each}
              </div>
              {#if ch.measured}
                <dl class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
                  <div><dt class="text-sm text-slate-500 dark:text-slate-400">{t('spread.era.detections')}</dt>
                    <dd class="font-medium text-slate-800 dark:text-slate-100">{ch.measured.detections?.toLocaleString() ?? '—'}</dd></div>
                  {#each Object.entries(ch.measured.regions ?? {}) as [rg, m] (rg)}
                    <div><dt class="text-sm text-slate-500 dark:text-slate-400">{regionLabel(rg)} {t('spread.era.first')}</dt>
                      <dd class="font-medium text-slate-800 dark:text-slate-100">{m.first}</dd></div>
                  {/each}
                </dl>
                {#if ch.measured.top_hosts?.length}
                  <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
                    {t('spread.era.top.hosts')}: {ch.measured.top_hosts.map((h) => `${h.host} (${h.n})`).join(', ')}
                  </p>
                {/if}
              {:else}
                <p class="mt-2 text-sm text-amber-700 dark:text-amber-300">{t('spread.era.no.feed')}</p>
              {/if}
            </li>
          {/each}
        </ul>
      </div>

      <!-- provenance + papers -->
      <aside class="space-y-4">
        <div class="bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-200">{t('spread.era.provenance')}</h3>
          <ul class="mt-2 space-y-1 text-sm text-slate-600 dark:text-slate-300">
            {#each Object.entries(era.provenance ?? {}) as [k, v] (k)}
              <li><span class="font-medium">{k}:</span> {v}</li>
            {/each}
          </ul>
        </div>
        <div class="bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {t('spread.era.papers')} ({eraPapersTotal.toLocaleString()})
          </h3>
          <ul class="mt-2 space-y-1 text-sm">
            {#each eraDesignations as [clade, n] (clade)}
              <li class="text-slate-600 dark:text-slate-300">
                <span class="font-mono">{clade}</span> · {n.toLocaleString()}
              </li>
            {/each}
            {#if (era?.papers?.total ?? 0) > 0}
              <li>
                <a class="text-blue-700 dark:text-blue-300 underline" href="#/papers">{t('spread.era.papers.all', { n: eraPapersTotal.toLocaleString() })}</a>
              </li>
            {/if}
          </ul>
        </div>
      </aside>
    </div>
  {/if}
{/if}
