<script>
  import { onMount } from 'svelte';
  import { db, dbStore } from '../lib/stores/db.js';
  import { navigate } from '../lib/stores/router.js';
  import { formatNumber, formatCompact, formatDateLong } from '../lib/utils/format.js';
  import SearchBar from '../lib/components/common/SearchBar.svelte';
  import { t, tc, sn } from '../lib/stores/i18n.svelte.js';
  import Sparkline from '../lib/components/common/Sparkline.svelte';
  import BirdOfTheDay from '../lib/components/common/BirdOfTheDay.svelte';
  import { phylopicIndex, phylopicPath } from '../lib/utils/phylopic.js';
  import SpeciesCard from '../lib/components/species/SpeciesCard.svelte';

  // State
  let stats = $state({ detections: 0, species: 0, countries: 0, sources: 0, generated: null, georeferenced: 0 });
  let topSpecies = $state([]);
  let silhouettes = $state(null);
  $effect(() => { phylopicIndex().then(i => silhouettes = i); });
  let recentDetections = $state([]);
  let loading = $state(true);
  let trendData = $state([]);

  // --- Beta banner: email assembled at click-time (never contiguous in
  // HTML or the bundle — reversed fragments defeat email-regex harvesters)
  // ---
  let emailRevealed = $state(false);
  let betaDismissed = $state('0');
  try { betaDismissed = localStorage.getItem('roost-beta-dismissed') || '0'; } catch {}
  const _fragments = ['hpesoj', 'nilhug', 'liamg', 'moc']; // reversed parts
  const emailParts = _fragments.map((f) => [...f].reverse().join(''));
  const _dot = String.fromCharCode(46), _at = String.fromCharCode(64);
  const emailAddress = emailParts[0] + _dot + emailParts[1] + _at + emailParts[2] + _dot + emailParts[3];

  // Injected at build/dev time by vite.config.js (last git commit timestamp)
  const pageUpdated = typeof __PAGE_UPDATED__ !== 'undefined' ? __PAGE_UPDATED__ : '';

  onMount(async () => {
    try {
      // Load stats from static JSON first (fast)
      const statsRes = await fetch('data/stats.json');
      const statsJson = await statsRes.json();
      // deep-assign into the existing $state proxy so Svelte 5 reactivity
      // fires even on cold loads (fresh fetch arriving after first paint)
      Object.assign(stats, statsJson);

      // Load DuckDB for detailed data
      await dbStore.loadSpecies();
      await dbStore.loadDetections();

      // Get top species
      topSpecies = await db.getTopSpecies(5);

      // Get monthly trend data
      const trends = await db.query(`
        SELECT
          substr(date_detected, 1, 7) as month,
          COUNT(*) as count
        FROM detections
        WHERE date_detected IS NOT NULL AND length(date_detected) >= 7
        GROUP BY month
        ORDER BY month
      `);
      trendData = trends.map(t => t.count);

      // Get recent detections
      recentDetections = await db.query(`
        SELECT * FROM detections
        WHERE date_detected IS NOT NULL
        ORDER BY date_detected DESC
        LIMIT 10
      `);

    } catch (e) {
      console.error('Failed to load home data:', e);
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head><title>{t('home.page.title') || 'Roost — avian influenza host genomics'} — Roost</title></svelte:head>

<div class="space-y-8">
  <!-- Hero section -->
  <div class="text-center pt-8 pb-2">
    <h1 class="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
      {t('home.title')}
    </h1>
    <p class="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto mb-8">
      {t('home.subtitle')}
    </p>

    <!-- Central search -->
    <div class="max-w-xl mx-auto">
      <SearchBar placeholder={t('home.search.placeholder') || 'Search species by scientific or common name...'} />
    </div>
  </div>

  <!-- Public-beta welcome banner (2026-11) — email is assembled at
       click-time from split parts: never present in the served HTML or as a
       contiguous string in the JS bundle (scraper-resistant). -->
  {#if betaDismissed !== '1'}
  <div class="bg-gradient-to-r from-blue-50 to-teal-50 dark:from-blue-900/30 dark:to-teal-900/30 border border-blue-200 dark:border-blue-800 rounded-xl p-5 mb-6 relative" role="note">
    <button class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm px-2"
            onclick={() => { betaDismissed = '1'; try { localStorage.setItem('roost-beta-dismissed', '1'); } catch {} }}
            aria-label={t('home.beta.dismiss')}>{t('home.beta.dismiss_symbol')}</button>
    <p class="text-sm text-gray-700 dark:text-gray-200 leading-relaxed pr-8">
      <strong>{t('home.beta.welcome')}</strong> {t('home.beta.body1')}
      <em>“{t('home.beta.question')}”</em> {t('home.beta.body2')}
      {t('home.beta.body3')}
    </p>
    <div class="mt-3 flex flex-wrap items-center gap-3">
      {#if emailRevealed}
        <a href={'ma' + 'ilto:' + emailAddress} class="text-sm font-medium text-blue-700 dark:text-blue-300 underline break-all">
          {emailAddress}
        </a>
        <button class="text-xs px-2 py-1 rounded-lg bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800"
                onclick={() => navigator.clipboard?.writeText(emailAddress)}>{t('home.beta.copy')}</button>
      {:else}
        <button class="text-sm px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium"
                onclick={() => (emailRevealed = true)}
                aria-label={t('home.beta.reveal_aria')}>{t('home.beta.reveal')}</button>
        <span class="text-xs text-gray-500 dark:text-gray-400">{t('home.beta.reveal_hint')}</span>
      {/if}
    </div>
  </div>
  {/if}

  <!-- Stats Grid -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
      <div class="text-3xl font-bold text-red-600 dark:text-red-400">{formatNumber(stats.detections)}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400">{t('stats.detections')}</div>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
      <div class="text-3xl font-bold text-green-700 dark:text-green-400">
        {formatNumber(stats.species_birds ?? stats.species)}
        {#if stats.species_mammals}<span class="text-lg text-gray-500 dark:text-gray-400 font-medium"> {t('home.stats.mammals', { n: formatNumber(stats.species_mammals) })}</span>{/if}
      </div>
      <div class="text-sm text-gray-500 dark:text-gray-400">{t('stats.species')}</div>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
      <div class="text-3xl font-bold text-purple-600 dark:text-purple-400">{formatNumber(stats.countries)}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400">{t('lib_components_species_SpeciesDetail.countries')}</div>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center">
      <div class="text-3xl font-bold text-orange-600">{formatNumber(stats.sources ?? '—')}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400">{t('stats.sources')}</div>
    </div>
  </div>

  <!-- Trend + Top Species -->
  <div class="grid md:grid-cols-2 gap-6">
    <!-- Detection Trend -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('home.detection.trend')}</h2>
      {#if trendData.length > 0}
        <div class="h-24">
          <Sparkline data={trendData} width={400} height={80} color="#ef4444" />
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{t('home.monthly.detection.counts.over')}</p>
      {:else if loading}
        <div class="h-24 flex items-center justify-center">
          <span class="text-gray-500 dark:text-gray-400">{t('home.loading')}</span>
        </div>
      {:else}
        <div class="h-24 flex items-center justify-center">
          <span class="text-gray-500 dark:text-gray-400">{t('home.no.trend.data.available')}</span>
        </div>
      {/if}
    </div>

    <!-- Most Affected Species -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{t('home.most.affected.species')}</h2>
        <button
          onclick={() => navigate('species')}
          class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          {t('home.view_all')}
        </button>
      </div>
      {#if topSpecies.length > 0}
        <div class="space-y-2">
          {#each topSpecies as species, i}
            <div class="flex items-center gap-3">
              <span class="w-6 h-6 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full text-xs font-medium text-gray-600 dark:text-gray-300">
                {i + 1}
              </span>
              {#if phylopicPath(species.scientific_name, silhouettes)}
                <img src={phylopicPath(species.scientific_name, silhouettes)} alt="" class="h-6 w-6 object-contain flex-shrink-0 dark:invert" />
              {/if}
              <button
                onclick={() => navigate('species', species.taxon_id || species.scientific_name)}
                class="flex-1 text-left hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-400"
              >
                <span class="text-sm font-medium text-gray-900 dark:text-white italic">
                  {species.scientific_name}
                </span>
                {#if species.common_name}
                  <span class="text-sm text-gray-500 dark:text-gray-400 ml-1">
                    ({sn(species.scientific_name, species.common_name)})
                  </span>
                {/if}
              </button>
              <span class="text-sm font-medium text-red-600 dark:text-red-400" title={t('species.card.detections.tip')}>
                {formatNumber(species.detection_records ?? species.detection_count)}
              </span>
            </div>
          {/each}
        </div>
      {:else if loading}
        <div class="space-y-2">
          {#each [1,2,3,4,5] as _}
            <div class="h-8 bg-gray-100 dark:bg-gray-700 rounded animate-pulse"></div>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <!-- Bird of the Day (deterministic per-day genome + core panel) -->
  <BirdOfTheDay />

  <!-- Research tools strip -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
    <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
      {t('home.comparative.tools') || 'Comparative genomics tools'}
    </h2>
    <div class="flex flex-wrap gap-2">
      {#each [
        ['orthogroups', `🧬 ${t('nav.orthogroups') || 'Orthogroups'}`, t('home.tip.orthogroups') || 'Gene trees, alignments, copy numbers across 463 birds'],
        ['synteny', `🔗 ${t('nav.synteny') || 'Synteny'}`, t('home.tip.synteny') || 'Conserved immune-gene neighborhoods, with flanking genes'],
        ['compare', `⚖ ${t('nav.compare') || 'Compare species'}`, t('home.tip.compare') || 'Side-by-side gene panels, genomes, detections'],
        ['blast', `⚡ ${t('nav.blast') || 'BLAST'}`, t('home.tip.blast') || 'In-browser protein search — nothing uploaded'],
        ['anp32', `🔬 ${t('nav.anp32') || 'ANP32 barrier'}`, t('home.tip.anp32') || 'The 33-aa insert behind the species barrier'],
        ['phylogeny', `🌳 ${t('nav.phylogeny') || 'Phylogeny'}`, t('home.tip.phylogeny') || 'Species tree with trait overlays'],
      ] as [route, label, tip] (route)}
        <button
          onclick={() => navigate(route)}
          title={tip}
          class="px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/40 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
        >{label}</button>
      {/each}
    </div>
  </div>

  <!-- Quick Actions -->
  <div class="grid md:grid-cols-3 gap-6">
    <button
      onclick={() => navigate('model')}
      class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-left hover:shadow-lg transition-shadow group"
    >
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
          <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 13h4l2-7 4 14 2-7h6" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
          {t('home.card.disease')}
        </h3>
      </div>
      <p class="text-gray-600 dark:text-gray-300">
        {t('home.card.disease.desc')}
      </p>
    </button>

    <button
      onclick={() => navigate('map')}
      class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-left hover:shadow-lg transition-shadow group"
    >
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
          <svg class="w-5 h-5 text-green-700 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-green-700 dark:group-hover:text-green-400">
          {t('home.card.map')}
        </h3>
      </div>
      <p class="text-gray-600 dark:text-gray-300">
        {t('home.map.desc', { n: formatNumber(stats.georeferenced ?? '—'), c: stats.countries })}
      </p>
    </button>

    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
          <svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
          {t('home.data.freshness') || 'Data Freshness'}
        </h3>
      </div>
      <dl class="space-y-2 text-sm">
        <div class="flex items-baseline justify-between gap-4">
          <dt class="text-gray-500 dark:text-gray-400">{t('home.page.updated')}</dt>
          <dd class="font-medium text-gray-900 dark:text-white">{formatDateLong(pageUpdated)}</dd>
        </div>
        <div class="flex items-baseline justify-between gap-4">
          <dt class="text-gray-500 dark:text-gray-400">{t('home.occurrence.sources.checked')}</dt>
          <dd class="font-medium text-gray-900 dark:text-white">{stats.generated ? formatDateLong(stats.generated) : '—'}</dd>
        </div>
      </dl>
    </div>
  </div>
</div>
