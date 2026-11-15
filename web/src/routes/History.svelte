<script>
  import { trackEvent } from '../lib/analytics.js';
  import { onMount } from 'svelte';
  import { t, pt } from '../lib/stores/i18n.svelte.js';
  import { db, dbStore } from '../lib/stores/db.js';
  import { routes } from '../lib/stores/router.js';

  // ---- state ------------------------------------------------------------
  let loading = $state(true);
  let error = $state(null);

  // global timeline (DuckDB over detections.parquet)
  let timeline = $state([]); // {year, records, speciesNew, speciesCum}
  let kpis = $state(null);

  // first-records registry (species_first_records.json)
  let registry = $state([]);
  let registryFilter = $state('');
  let registeredYear = $state('all');

  // data activity feed (data_activity.json) — data-level events only
  let activityEvents = $state([]);
  const activityByDate = $derived.by(() => {
    const groups = new Map();
    for (const e of activityEvents) {
      if (!groups.has(e.date)) groups.set(e.date, []);
      groups.get(e.date).push(e);
    }
    // newest first; summary events before detail events within a date
    return [...groups.entries()]
      .sort((a, b) => (a[0] < b[0] ? 1 : -1))
      .map(([date, events]) => [
        date,
        events.sort((a, b) => (a.kind === b.kind ? 0 : a.kind === 'genome_added' ? 1 : -1)),
      ])
      .slice(0, 14);
  });

  // per-species lookup
  let speciesIndex = $state([]);
  let speciesQuery = $state('');
  let selectedSpecies = $state(null); // {sci, com, id}
  let speciesDetail = $state(null); // {yearly, first, last, records, countries, sources}
  // analytics: species-history lookups
  $effect(() => { if (speciesDetail?.name || speciesDetail?.sci) trackEvent('History', 'species', speciesDetail.sci || speciesDetail.name); });
  let speciesLoading = $state(false);

  const matched = $derived(
    speciesQuery.trim().length < 2
      ? []
      : speciesIndex
          .filter(
            (s) =>
              s.sci.toLowerCase().includes(speciesQuery.toLowerCase()) ||
              (s.com || '').toLowerCase().includes(speciesQuery.toLowerCase())
          )
          .slice(0, 8)
  );

  const registeredYears = $derived(
    [...new Set(registry.map((r) => r.registered_on?.slice(0, 4)))].sort().reverse()
  );

  const filteredRegistry = $derived(
    registry.filter((r) => {
      if (registeredYear !== 'all' && r.registered_on?.slice(0, 4) !== registeredYear) return false;
      if (!registryFilter.trim()) return true;
      const q = registryFilter.toLowerCase();
      return (
        r.scientific_name.toLowerCase().includes(q) ||
        (r.common_name || '').toLowerCase().includes(q)
      );
    })
  );

  // ---- chart geometry (inline SVG, no deps) ------------------------------
  const W = 940;
  const H = 260;
  const PAD = { l: 52, r: 52, t: 18, b: 30 };
  const chartW = W - PAD.l - PAD.r;
  const chartH = H - PAD.t - PAD.b;

  const maxRecords = $derived(Math.max(1, ...timeline.map((d) => d.records)));
  const maxCum = $derived(Math.max(1, ...timeline.map((d) => d.speciesCum)));
  const barW = $derived(timeline.length ? chartW / timeline.length - 2 : 0);

  const x = $derived((i) => PAD.l + (i + 0.5) * (chartW / Math.max(1, timeline.length)));
  const yR = $derived((v) => PAD.t + chartH - (v / maxRecords) * chartH);
  const yC = $derived((v) => PAD.t + chartH - (v / maxCum) * chartH);
  const cumPath = $derived(
    timeline.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${yC(d.speciesCum)}`).join(' ')
  );
  let hovered = $state(null);

  // ---- data loading ------------------------------------------------------
  onMount(async () => {
    try {
      // registry + species index (plain fetch, cheap)
      const [regRes, idxRes, actRes] = await Promise.all([
        fetch('data/species_first_records.json'),
        fetch('data/species_index.json'),
        fetch('data/data_activity.json'),
      ]);
      if (regRes.ok) {
        const doc = await regRes.json();
        registry = doc.registrations || [];
      }
      if (idxRes.ok) speciesIndex = await idxRes.json();
      if (actRes.ok) {
        const doc = await actRes.json();
        activityEvents = doc.events || [];
      }

      // DuckDB timeline queries
      await dbStore.loadDetections();

      const yearly = await db.query(`
        SELECT year(date_iso) AS year,
               COUNT(*) AS records,
               COUNT(DISTINCT scientific_name) AS species_that_year
        FROM detections
        WHERE date_iso IS NOT NULL AND scientific_name IS NOT NULL
        GROUP BY year ORDER BY year
      `);

      const span = await db.query(`
        SELECT EXTRACT(year FROM MIN(date_iso)) AS first_year,
               EXTRACT(year FROM MAX(date_iso)) AS last_year,
               COUNT(DISTINCT scientific_name) AS species,
               SUM(CASE WHEN date_iso IS NOT NULL THEN 1 ELSE 0 END) AS dated
        FROM detections WHERE scientific_name IS NOT NULL
      `);

      let cum = 0;
      timeline = yearly.map((r) => {
        const rec = {
          year: Number(r.year),
          records: Number(r.records),
          speciesNew: Number(r.species_that_year),
        };
        cum += rec.speciesNew;
        rec.speciesCum = cum;
        return rec;
      });
      // exact cumulative: distinct species with first detection ≤ year
      const firsts = await db.query(`
        SELECT scientific_name, MIN(date_iso) AS first_date
        FROM detections
        WHERE date_iso IS NOT NULL AND scientific_name IS NOT NULL
        GROUP BY scientific_name
      `);
      const seen = new Map();
      for (const f of firsts) {
        const y = Number(String(f.first_date).slice(0, 4));
        seen.set(y, (seen.get(y) || 0) + 1);
      }
      const years = [...seen.keys()].sort((a, b) => a - b);
      let acc = 0;
      const cumByYear = new Map();
      for (const y of years) {
        acc += seen.get(y);
        cumByYear.set(y, acc);
      }
      timeline = timeline.map((d) => ({
        ...d,
        speciesNew: cumByYear.has(d.year) ? seen.get(d.year) : 0,
        speciesCum: cumByYear.get(d.year) ?? null,
      })).filter((d) => d.year >= 2000);

      kpis = {
        first: span[0]?.first_year || '—',
        last: span[0]?.last_year || '—',
        species: Number(span[0]?.species || 0),
        dated: Number(span[0]?.dated || 0),
      };

      // deep link: #/history?species=9031
      const params = new URLSearchParams(location.hash.split('?')[1] || '');
      const sp = params.get('species');
      if (sp) {
        const hit = speciesIndex.find((s) => String(s.id) === sp);
        if (hit) selectSpecies(hit);
      }
    } catch (e) {
      error = e?.message || String(e);
    } finally {
      loading = false;
    }
  });

  async function selectSpecies(s) {
    selectedSpecies = s;
    speciesQuery = s.sci;
    speciesLoading = true;
    speciesDetail = null;
    try {
      await dbStore.loadDetections();
      const id = Number(s.id);
      const [meta, yearly, bySource] = await Promise.all([
        db.query(`
          SELECT MIN(date_iso) AS first, MAX(date_iso) AS last, COUNT(*) AS n,
                 COUNT(DISTINCT country) AS countries
          FROM detections WHERE taxon_id = ${id} AND date_iso IS NOT NULL
        `),
        db.query(`
          SELECT year(date_iso) AS year, COUNT(*) AS n
          FROM detections WHERE taxon_id = ${id} AND date_iso IS NOT NULL
          GROUP BY year ORDER BY year
        `),
        db.query(`
          SELECT source, COUNT(*) AS n FROM detections
          WHERE taxon_id = ${id} GROUP BY source ORDER BY n DESC LIMIT 8
        `),
      ]);
      const countries = await db.query(`
        SELECT country, COUNT(*) AS n FROM detections
        WHERE taxon_id = ${id} AND country IS NOT NULL
        GROUP BY country ORDER BY n DESC LIMIT 12
      `);
      speciesDetail = {
        meta: meta[0] || {},
        yearly: yearly.map((r) => ({ year: Number(r.year), n: Number(r.n) })),
        sources: bySource.map((r) => ({ source: r.source, n: Number(r.n) })),
        countries: countries.map((r) => ({ country: r.country, n: Number(r.n) })),
      };
    } catch (e) {
      error = e?.message || String(e);
    } finally {
      speciesLoading = false;
    }
  }

  const spMax = $derived(
    speciesDetail ? Math.max(1, ...speciesDetail.yearly.map((d) => d.n)) : 1
  );
</script>

<svelte:head><title>{t('routes.history.detection.history.roost') || 'Detection History — Roost'}</title></svelte:head>

<div class="max-w-7xl mx-auto">
  <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
    {t('history.title') || 'Roost History'}
  </h1>
  <p class="text-gray-600 dark:text-gray-400 mb-8 max-w-3xl">
    {t('history.subtitle') ||
      'When each species was first registered in Roost, and how detections accumulated over time — across every source in the database.'}
  </p>

  {#if error}
    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-300 mb-6">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="text-gray-500 dark:text-gray-400 py-16 text-center">
      {t('common.loading') || 'loading…'}
    </div>
  {:else}
    <!-- KPI row -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-2xl font-bold text-gray-900 dark:text-white">{kpis?.species?.toLocaleString() || '—'}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{t('history.kpi_detected_species')}</div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-2xl font-bold text-gray-900 dark:text-white">{kpis?.dated?.toLocaleString() || '—'}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{t('history.dated_records')}</div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-2xl font-bold text-gray-900 dark:text-white">{kpis?.first} – {kpis?.last}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{t('history.kpi_detection_years')}</div>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
        <div class="text-2xl font-bold text-gray-900 dark:text-white">{registry.length?.toLocaleString() || '—'}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{t('history.kpi_registered_species')}</div>
      </div>
    </div>

    <!-- Data activity feed: changes in the data itself -->
    {#if activityByDate.length}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
          {t('history.activity') || 'Data activity'}
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {t('history.activity_hint') ||
            'Changes in the data itself — new detections, species registrations, and genome additions (trigger: first detection or periodic NCBI check).'}
        </p>
        <div class="space-y-4 max-h-96 overflow-y-auto pr-1">
          {#each activityByDate as [date, evts] (date)}
            <div class="border-l-2 border-blue-200 dark:border-blue-800 pl-4">
              <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">{date}</div>
              {#each evts as e (e.kind + (e.accession || '') + (e.count ?? ''))}
                <div class="text-sm text-gray-700 dark:text-gray-300 mb-1">
                  {#if e.kind === 'detections_added'}
                    <span class="mr-1">📈</span>
                    <span class="font-medium">{e.count?.toLocaleString()}</span>
                    {t('history.act_detections') || 'new detections added'}
                    <span class="text-gray-500 dark:text-gray-400">· {t('history.act_total') || 'total'} {e.total_after?.toLocaleString()}</span>
                    {#if e.by_source && Object.keys(e.by_source).length}
                      <span class="text-gray-500 dark:text-gray-400">· {Object.entries(e.by_source).slice(0, 3).map(([s, c]) => `${s} +${c}`).join(', ')}</span>
                    {/if}
                    {#if e.species?.length}
                      <div class="mt-1 ml-6 flex flex-wrap gap-1">
                        {#each e.species as s}
                          {#if s.name && !s.name.startsWith('Unidentified')}
                            <a href="#/species-full/{encodeURIComponent(s.name)}"
                               class="inline-flex items-center rounded-full bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                               title={(s.com || s.name) + ' — ' + (t('history.view.species.page') || 'view species page')}>{s.com || s.name}{s.n > 1 ? ` ×${s.n}` : ''}</a>
                          {:else}
                            <span class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400"
                                  title={t('routes.history.detection.events.where.the') || 'Detection events where the reporting source did not identify the species'}>{s.name}{s.n > 1 ? ` ×${s.n}` : ''}</span>
                          {/if}
                        {/each}
                      </div>
                    {/if}
                  {:else if e.kind === 'species_registered'}
                    <span class="mr-1">🐦</span>
                    <span class="font-medium">{e.count}</span>
                    {t('history.act_species') || 'new species first records'}
                    <span class="text-gray-500 dark:text-gray-400">· {e.aves} {t('history.act_birds') || 'birds'}, {e.mammals} {t('history.act_mammals') || 'mammals'}</span>
                  {:else if e.kind === 'genomes_added'}
                    <span class="mr-1">🧬</span>
                    {#if e.mammal_detection}
                      <span class="font-medium">{e.mammal_detection}</span>
                      {t('history.act_mammal_genomes') || 'mammal genomes added'}
                      <span class="text-gray-500 dark:text-gray-400">— {t('history.act_trigger_detection') || 'trigger: first detection'}</span>
                    {/if}
                    {#if e.mammal_detection && e.avian_periodic}; {/if}
                    {#if e.avian_periodic}
                      <span class="font-medium">{e.avian_periodic}</span>
                      {t('history.act_avian_genomes') || 'avian genomes added'}
                      <span class="text-gray-500 dark:text-gray-400">— {t('history.act_trigger_periodic') || 'trigger: periodic NCBI check'}</span>
                    {/if}
                  {:else if e.kind === 'genome_added'}
                    <span class="mr-1">{e.is_aves ? '🕊️' : '🦊'}</span>
                    <span class="font-medium">{e.scientific_name}</span>
                    <span class="text-gray-500 dark:text-gray-400">— {e.accession} ({e.assembly_level}) · {t('history.act_trigger_' + e.trigger) || 'trigger: ' + e.trigger}</span>
                  {:else if e.kind === 'genome_updated'}
                    <span class="mr-1">♻️</span>
                    <span class="font-medium">{e.scientific_name}</span>
                    <span class="text-gray-500 dark:text-gray-400">— {e.old_accession} → {e.new_accession}</span>
                  {:else if e.kind === 'papers_added'}
                    <span class="mr-1">📚</span>
                    <span class="font-medium">{e.count}</span>
                    {t('history.act_papers') || 'new papers added'}
                    {#if e.highlights?.length}
                      <div class="mt-1 ml-6 text-xs text-gray-500 dark:text-gray-400">
                        {#each e.highlights.slice(0, 2) as h}
                          <div>“{pt(h.id, 'title') || h.title}” ({h.year})</div>
                        {/each}
                        {#if e.count > 2}
                          <div class="text-gray-500 dark:text-gray-400">+{e.count - 2} more</div>
                        {/if}
                        <a href="#/papers?added={e.date}" class="inline-block mt-0.5 text-blue-600 dark:text-blue-400 hover:underline">
                          {t('history.view.all.papers') || 'View all papers added →'}
                        </a>
                      </div>
                    {/if}
                  {:else if e.kind === 'connection_added'}
                    <span class="mr-1">🔗</span>
                    <span class="font-medium">{e.from} → {e.label} → {e.to}</span>
                    {#if e.paper_title}
                      <span class="text-gray-500 dark:text-gray-400">— “{e.paper_title.slice(0, 60)}{e.paper_title.length > 60 ? '…' : ''}” ({e.paper_year})</span>
                    {/if}
                  {:else if e.kind === 'baseline'}
                    <span class="mr-1">🗄️</span>
                    {t('history.act_baseline') || 'Registry begins'}
                    <span class="text-gray-500 dark:text-gray-400">· {e.detections?.toLocaleString()} {t('history.act_baseline_detections') || 'detections'}</span>
                  {/if}
                </div>
              {/each}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Global timeline -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
        {t('history.timeline') || 'Detections & species accumulation over time'}
      </h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
        {t('history.timeline_caption')}
      </p>
      <div class="overflow-x-auto">
        <svg viewBox="0 0 {W} {H}" class="w-full min-w-[700px]" role="group" aria-label={t('history.timeline_aria')}>
          <!-- axes -->
          <line x1={PAD.l} y1={PAD.t + chartH} x2={W - PAD.r} y2={PAD.t + chartH} class="stroke-gray-300 dark:stroke-gray-600" />
          <!-- y gridlines + labels -->
          {#each [0, 0.25, 0.5, 0.75, 1] as f}
            <text x={PAD.l - 8} y={yR(maxRecords * f) + 4} text-anchor="end" class="fill-gray-400 text-[10px]">
              {(maxRecords * f) >= 1000 ? ((maxRecords * f) / 1000).toFixed(0) + 'k' : Math.round(maxRecords * f)}
            </text>
            <text x={W - PAD.r + 8} y={yC(maxCum * f) + 4} text-anchor="start" class="fill-teal-500 text-[10px]">
              {Math.round(maxCum * f)}
            </text>
          {/each}
          <!-- bars -->
          {#each timeline as d, i}
            <rect
              x={x(i) - barW / 2}
              y={yR(d.records)}
              width={barW}
              height={PAD.t + chartH - yR(d.records)}
              class="fill-blue-400 dark:fill-blue-500 hover:fill-blue-600 transition-colors cursor-pointer focus:outline-none focus-visible:fill-blue-700"
              opacity={hovered === null || hovered === i ? 1 : 0.55}
              role="button"
              tabindex="0"
              aria-label={`${d.year} — ${t('stats.detections')}: ${d.records}`}
              onclick={() => (hovered = hovered === i ? null : i)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); hovered = hovered === i ? null : i; } }}
              onmousemove={() => (hovered = i)}
            />
            {#if i % Math.ceil(timeline.length / 12) === 0}
              <text x={x(i)} y={H - 8} text-anchor="middle" class="fill-gray-400 text-[10px]">{d.year}</text>
            {/if}
          {/each}
          <!-- cumulative species line -->
          {#if cumPath}
            <path d={cumPath} fill="none" class="stroke-teal-500" stroke-width="2.5" />
          {/if}
          <!-- tooltip -->
          {#if hovered !== null && timeline[hovered]}
            {@const d = timeline[hovered]}
            <g transform="translate({Math.min(Math.max(x(hovered), PAD.l + 60), W - PAD.r - 60)}, {PAD.t + 26})">
              <rect x="-72" y="-16" width="144" height="46" rx="6" class="fill-gray-900 dark:fill-gray-700" opacity="0.92" />
              <text text-anchor="middle" y="0" class="fill-white text-[11px] font-semibold">{d.year}</text>
              <text text-anchor="middle" y="14" class="fill-gray-200 text-[10px]">{d.records.toLocaleString()} records</text>
              <text text-anchor="middle" y="26" class="fill-teal-300 text-[10px]">
                {d.speciesCum ? d.speciesCum.toLocaleString() + ' species cumulative' : ''}
              </text>
            </g>
          {/if}
        </svg>
      </div>
    </div>

    <!-- First records -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
            {t('history.first_records') || 'First records'}
          </h2>
          <p class="text-xs text-gray-500 dark:text-gray-400">
            {t('history.registered.when') || 'When a species was registered in Roost for the first time.'} <span class="text-gray-500 dark:text-gray-400">{t('routes.history.first.detection') || 'first detection'}</span> {t('history.may.predate') || 'may predate registration (historical data).'}
          </p>
        </div>
        <div class="flex gap-2">
          <select bind:value={registeredYear} aria-label={t('history.opt.all.years')} class="border dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 rounded-md text-sm px-2 py-1.5">
            <option value="all">{t('history.opt.all.years') || 'all years'}</option>
            {#each registeredYears as y}
              <option value={y}>{y}</option>
            {/each}
          </select>
          <input
            type="search"
            bind:value={registryFilter}
            placeholder={t('history.filter_placeholder') || 'Filter species…'}
            class="border dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 rounded-md text-sm px-3 py-1.5 w-48"
          />
        </div>
      </div>

      {#if filteredRegistry.length === 0}
        <div class="text-gray-500 dark:text-gray-400 py-8 text-center text-sm">
          {t('common.no_results') || 'No results'}
        </div>
      {:else}
        <div class="overflow-x-auto max-h-[480px] overflow-y-auto border dark:border-gray-700 rounded-lg">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 dark:bg-gray-700/50 sticky top-0">
              <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase">
                <th class="px-3 py-2">Species</th>
                <th class="px-3 py-2">Registered</th>
                <th class="px-3 py-2">{t('routes.history.first.detection.1') || 'First detection'}</th>
                <th class="px-3 py-2">Records</th>
                <th class="px-3 py-2">Countries</th>
                <th class="px-3 py-2">Via</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredRegistry.slice(0, 200) as r (r.scientific_name)}
                <tr class="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/40">
                  <td class="px-3 py-2">
                    <a href={`#/species/${r.taxon_id}`} class="text-blue-600 dark:text-blue-400 hover:underline font-medium">
                      {r.scientific_name}
                    </a>
                    {#if r.common_name}
                      <span class="text-gray-500 dark:text-gray-400 text-xs ml-1">({r.common_name})</span>
                    {/if}
                  </td>
                  <td class="px-3 py-2 whitespace-nowrap text-gray-600 dark:text-gray-300">{r.registered_on}</td>
                  <td class="px-3 py-2 whitespace-nowrap text-gray-600 dark:text-gray-300">
                    {r.first_detection || '—'}
                    {#if r.first_detection && r.registered_on && r.first_detection < r.registered_on}
                      <span class="text-gray-500 dark:text-gray-400 text-xs">(historical)</span>
                    {/if}
                  </td>
                  <td class="px-3 py-2 text-right tabular-nums text-gray-600 dark:text-gray-300">{r.records.toLocaleString()}</td>
                  <td class="px-3 py-2 text-gray-600 dark:text-gray-300">{r.countries?.length ?? '—'}</td>
                  <td class="px-3 py-2">
                    <span class="inline-block bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded px-1.5 py-0.5 text-xs">{r.top_source || r.registered_via || '—'}</span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if filteredRegistry.length > 200}
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Showing first 200 of {filteredRegistry.length.toLocaleString()} — use the filter.</p>
        {/if}
      {/if}
    </div>

    <!-- Per-species lookup -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
        {t('history.species_lookup') || 'Species timeline'}
      </h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
        {t('history.search.hint') || 'Search a species to see its detection history year by year.'}
      </p>

      <div class="relative mb-6 max-w-xl">
        <input
          type="search"
          bind:value={speciesQuery}
          placeholder={t('history.search_species') || 'Search species…'}
          class="w-full border dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 rounded-lg px-4 py-2.5 text-sm"
        />
        {#if matched.length > 0}
          <div class="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border dark:border-gray-600 rounded-lg shadow-lg overflow-hidden">
            {#each matched as s (s.id)}
              <button
                class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200"
                onclick={() => selectSpecies(s)}
              >
                <span class="italic">{s.sci}</span>
                {#if s.com}<span class="text-gray-500 dark:text-gray-400 ml-1">{s.com}</span>{/if}
              </button>
            {/each}
          </div>
        {/if}
      </div>

      {#if speciesLoading}
        <div class="text-gray-500 dark:text-gray-400 py-8 text-center text-sm">{t('common.loading') || 'loading…'}</div>
      {:else if speciesDetail && selectedSpecies}
        <div class="grid md:grid-cols-3 gap-6">
          <div>
            <h3 class="font-semibold text-gray-900 dark:text-white italic">{selectedSpecies.sci}</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">{selectedSpecies.com}</p>
            <dl class="text-sm space-y-1.5">
              <div class="flex justify-between border-b dark:border-gray-700 pb-1">
                <dt class="text-gray-500 dark:text-gray-400">{t('routes.history.first.detection.1') || 'First detection'}</dt>
                <dd class="font-medium text-gray-900 dark:text-white">{speciesDetail.meta.first || '—'}</dd>
              </div>
              <div class="flex justify-between border-b dark:border-gray-700 pb-1">
                <dt class="text-gray-500 dark:text-gray-400">{t('history.most_recent')}</dt>
                <dd class="font-medium text-gray-900 dark:text-white">{speciesDetail.meta.last || '—'}</dd>
              </div>
              <div class="flex justify-between border-b dark:border-gray-700 pb-1">
                <dt class="text-gray-500 dark:text-gray-400">Dated records</dt>
                <dd class="font-medium text-gray-900 dark:text-white">{Number(speciesDetail.meta.n || 0).toLocaleString()}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-gray-500 dark:text-gray-400">Countries</dt>
                <dd class="font-medium text-gray-900 dark:text-white">{Number(speciesDetail.meta.countries || 0).toLocaleString()}</dd>
              </div>
            </dl>
            <div class="mt-3 flex flex-wrap gap-1">
              {#each speciesDetail.countries as c}
                <span class="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded px-1.5 py-0.5">{c.country} · {c.n}</span>
              {/each}
            </div>
            <div class="mt-2 flex flex-wrap gap-1">
              {#each speciesDetail.sources as s}
                <span class="bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded px-1.5 py-0.5">{s.source}</span>
              {/each}
            </div>
          </div>
          <div class="md:col-span-2">
            <div class="flex items-end gap-[2px] h-48 border-b dark:border-gray-600">
              {#each speciesDetail.yearly as d (d.year)}
                <div
                  class="flex-1 bg-blue-400 dark:bg-blue-500 hover:bg-blue-600 rounded-t transition-colors min-w-[3px] relative group"
                  style="height: {(d.n / spMax) * 100}%"
                  title="{d.year}: {d.n.toLocaleString()} records"
                >
                  <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-gray-900 dark:bg-gray-600 text-white text-[10px] rounded px-1.5 py-0.5 whitespace-nowrap z-10">{d.year} · {d.n.toLocaleString()}</span>
                </div>
              {/each}
            </div>
            <div class="flex justify-between text-[10px] text-gray-500 dark:text-gray-400 mt-1">
              <span>{speciesDetail.yearly[0]?.year}</span>
              <span>{speciesDetail.yearly[speciesDetail.yearly.length - 1]?.year}</span>
            </div>
            <a href={`#/species/${selectedSpecies.id}`} class="inline-block mt-4 text-sm text-blue-600 dark:text-blue-400 hover:underline">
              → {t('species.full_page') || 'Full page'}
            </a>
          </div>
        </div>
      {:else}
        <div class="text-gray-500 dark:text-gray-400 py-8 text-center text-sm border-2 border-dashed dark:border-gray-700 rounded-lg">
          {t('history.lookup_hint') || 'Type a species name to see its history'}
        </div>
      {/if}
    </div>
  {/if}
</div>
