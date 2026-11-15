<script>
  import { trackEvent } from '../../analytics.js';
  import { t, ft } from '../../../lib/stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { db } from '../../stores/db.js';
  import { navigate } from '../../stores/router.js';
  import { ncbi, gbif, wikimedia, doi } from '../../utils/urls.js';
  import { formatNumber, formatDate, formatN50, getAssemblyLevelInfo, getSusceptibilityInfo, formatTaxonomy, getIUCNInfo, getTrendInfo } from '../../utils/format.js';
  import { iucn as iucnUrl, birdlife } from '../../utils/urls.js';
  import Modal from '../common/Modal.svelte';
  import { phylopicIndex, phylopicPath } from '../../utils/phylopic.js';
  import SourceBadge from '../common/SourceBadge.svelte';
  import Sparkline from '../common/Sparkline.svelte';
  import { fetchGeneCatalogue, panelFromCalls } from '../../utils/presence.js';
  import SpeciesInsights from './SpeciesInsights.svelte';

  /** Clean strain labels: the parquet sometimes carries Python-dict strings */
  function cleanStrain(s) {
    if (!s) return '';
    if (s.startsWith("{'")) {
      const m = s.match(/'keyValue':\s*'([^']+)'/);
      return m ? m[1] : '';
    }
    if (s.startsWith("[")) {
      try { const a = JSON.parse(s.replace(/'/g, '"')); return Array.isArray(a) ? a.join(', ') : s; }
      catch { return s; }
    }
    return s;
  }

  // Props
  let { speciesId = null, onclose } = $props();

  // State
  let species = $state(null);
  let detections = $state([]);
  let loading = $state(true);
  let error = $state(null);
  const _hashTab = typeof window !== 'undefined'
    ? new URLSearchParams(window.location.hash.split('?')[1] || '').get('tab') : null;
  let activeTab = $state(
    ['overview', 'detections', 'genome', 'genes', 'research'].includes(_hashTab || '') ? _hashTab || 'overview' : 'overview');
  let silhouette = $state(null);

  $effect(() => {
    if (species?.scientific_name) {
      phylopicIndex().then(idx => { silhouette = phylopicPath(species.scientific_name, idx); });
      trackEvent('Species', 'dialog', species.scientific_name);
    }
  });

  // OrthoFinder 463-bird run: per-species orthogroup stats (null = not in run)
  let ogStatsMap = null;
  let ogStats = $state(null);
  $effect(() => {
    const sci = species?.scientific_name;
    ogStats = null;
    if (!sci) return;
    void (async () => {
      try {
        ogStatsMap ??= await (await fetch('data/orthofinder/species_og_stats.json')).json();
        ogStats = ogStatsMap[sci] || null;
      } catch { /* stays hidden */ }
    })();
  });

  // Load species data
  $effect(() => {
    if (speciesId) {
      loadSpecies(speciesId);
    }
  });

  async function loadSpecies(id) {
    loading = true;
    error = null;

    // Route ids arrive URL-encoded from wiki links (#/species/Gallus%20gallus)
    try {
      id = decodeURIComponent(id);
    } catch {
      // malformed encoding — use as-is
    }

    try {
      // Try to load from DuckDB first (species with detections)
      species = await db.getSpeciesById(id);

      if (!species) {
        // Try by name if ID didn't work
        species = await db.getSpeciesByName(id);
      }

      if (!species) {
        // Fallback to species_index.json (includes species without detections)
        species = await db.getSpeciesFromIndex(id);
      }

      if (species) {
        // IUCN badge (Wikidata P141 mirror; the db/index rows carry no status)
        try {
          const r = await fetch('data/species/iucn_status.json');
          if (r.ok) {
            const d = await r.json();
            species.iucn = d?.status?.[species.scientific_name] || null;
          }
        } catch { /* badge stays hidden */ }
        // Load detections for this species (may be empty)
        if (species.has_detections !== false) {
          try {
            detections = await db.getDetectionsForSpecies(species.scientific_name);
          } catch (e) {
            // No detections table loaded yet, or no detections for this species
            detections = [];
          }
        } else {
          detections = [];
        }
      } else {
        error = (t('species.not.found') || 'Species not found:') + ` ${id}`;
      }
    } catch (e) {
      console.error('Failed to load species:', e);
      error = e.message;
    } finally {
      loading = false;
    }
  }

  // Compute detection timeline (monthly counts)
  function getTimelineData() {
    if (!detections || detections.length === 0) return [];

    // Group by month
    const counts = {};
    detections.forEach(d => {
      if (d.date_detected) {
        const month = d.date_detected.substring(0, 7); // YYYY-MM
        counts[month] = (counts[month] || 0) + 1;
      }
    });

    // Sort and return as array
    return Object.entries(counts)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([month, count]) => count);
  }

  // Get unique countries
  function getCountries() {
    if (!detections) return [];
    const countries = new Set(detections.map(d => d.country).filter(Boolean));
    return Array.from(countries).sort();
  }

  // Get sources
  function getSources() {
    if (!detections) return {};
    const sources = {};
    detections.forEach(d => {
      if (d.source) {
        sources[d.source] = (sources[d.source] || 0) + 1;
      }
    });
    return sources;
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'detections', label: 'Detections' },
    { id: 'genome', label: 'Genome' },
    { id: 'genes', label: 'Gene Panel' },
    { id: 'research', label: 'Research' }
  ];

  // --- Wiki research data (LLM-extracted from papers) ---
  let wikiSpecies = $state(null);
  let wikiLoaded = $state(false);
  let showAllEvidence = $state(false);

  // --- Gene presence data (from blast pipeline) ---
  let genePresence = $state(null);

  const statusColors = {
    confirmed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    susceptible: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    resistant: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    sampled: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    unknown: 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300'
  };

  async function loadWikiResearch() {
    if (wikiLoaded) return;
    wikiLoaded = true;
    try {
      const response = await fetch('data/wiki_species.json');
      if (!response.ok) return;
      const data = await response.json();
      const all = data.species || {};
      const sci = (species?.scientific_name || '').toLowerCase();
      const com = (species?.common_name || '').toLowerCase();
      // Match by scientific name, then common name, then genus prefix
      wikiSpecies = Object.values(all).find(s =>
        (s.scientific_name || '').toLowerCase() === sci && sci
      ) || Object.values(all).find(s =>
        s.canonical.toLowerCase() === com && com
      ) || Object.values(all).find(s =>
        sci && (s.scientific_name || '').toLowerCase().startsWith(sci.split(' ')[0] + ' ')
      ) || null;
    } catch {
      wikiSpecies = null;
    }
  }

  // Gene panel for THIS species only: catalogue (small JSON, cached) +
  // DuckDB calls + SQL summary — same shape the template was written for
  // ({key_genes, species[sci], summary[sci]}), no 13 MB fetch (Phase 2 Step 3)
  async function loadGenePresence() {
    try {
      const sci = species.scientific_name;
      const [cat, calls, summary] = await Promise.all([
        fetchGeneCatalogue(),
        db.getPresenceCallsForSpecies(sci),
        db.getSpeciesGeneSummary(sci),
      ]);
      genePresence = {
        key_genes: cat?.key_genes || {},
        species: { [sci]: panelFromCalls(calls) },
        summary: { [sci]: summary },
      };
    } catch { genePresence = null; }
  }

  $effect(() => {
    if (activeTab === 'research' && species) {
      loadWikiResearch();
    }
    if (activeTab === 'genes' && species && !genePresence) {
      loadGenePresence();
    }
  });
</script>

<Modal open={!!speciesId} {onclose} size="xl" ariaLabel={species?.common_name || species?.scientific_name || speciesId || 'Species detail'}>
  {#if loading}
    <div class="flex items-center justify-center py-12">
      <svg class="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span class="ml-3 text-gray-500 dark:text-gray-400">{t('species_detail.loading.species.data')}</span>
    </div>
  {:else if error}
    <div class="text-center py-12">
      <div class="text-red-600 dark:text-red-400 mb-2">{t('species_detail.failed.to.load.species')}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400">{error}</div>
    </div>
  {:else if species}
    <!-- Header -->
    <div class="border-b border-gray-200 dark:border-gray-700 pb-4 mb-4">
      <div class="flex items-start justify-between">
        <div class="flex items-start gap-4">
          {#if silhouette}
            <img
              src={silhouette}
              alt=""
              class="h-16 w-16 object-contain dark:invert mt-1"
              title="Silhouette: PhyloPic"
            />
          {/if}
        <div>
          <div class="flex items-center gap-3">
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white italic">
              {species.scientific_name}
            </h2>
            {#if species.iucn}
              {@const iucnInfo = getIUCNInfo(species.iucn)}
              <a
                href={iucnUrl.search(species.scientific_name)}
                target="_blank"
                rel="noopener noreferrer"
                title={(t('iucn.' + (species.iucn || 'DD')) || iucnInfo.name) + ' — ' + (t('iucn.click.for') || 'Click for IUCN Red List')}
                class="px-2 py-0.5 text-xs font-bold rounded {iucnInfo.bg} {iucnInfo.text} hover:opacity-80"
              >
                {species.iucn}
              </a>
              {#if species.trend}
                {@const trendInfo = getTrendInfo(species.trend)}
                <span class="text-sm {trendInfo.color}" title="{t('iucn.pop.trend') || 'Population trend'}: {t('trend.' + (species.population_trend || 'unknown')) || trendInfo.label}">
                  {trendInfo.icon}
                </span>
              {/if}
            {/if}
          </div>
          {#if species.common_name}
            <p class="text-lg text-gray-600 dark:text-gray-300">{species.common_name}</p>
          {/if}
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {formatTaxonomy(species.order, species.family, species.genus)}
            {#if species.endemic}
              <span class="ml-2 px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs rounded">
                Endemic to {species.endemic}
              </span>
            {/if}
          </p>
        </div>
        </div>

        <!-- External links + full page -->
        <div class="flex flex-col gap-2 items-end">
          <a
            href="#/species-full/{encodeURIComponent(species.scientific_name)}"
            class="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 inline-flex items-center gap-1.5"
            title={t('tip.species.full') || 'Open full species page — complete gene panel, research, links'}
          >
            {t('species.full_page')}
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
          <div class="flex gap-2">
            {#if species.taxon_id}
              <a
                href={ncbi.taxonomy(species.taxon_id)}
                target="_blank"
                rel="noopener noreferrer"
                class="px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md hover:bg-blue-200 dark:hover:bg-blue-900/50"
              >
                NCBI Taxonomy
              </a>
            {/if}
            <a
              href={gbif.search(species.scientific_name)}
              target="_blank"
              rel="noopener noreferrer"
              class="px-3 py-1.5 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-md hover:bg-green-200 dark:hover:bg-green-900/50"
            >
              GBIF
            </a>
            <a
              href={wikimedia.wikipedia(species.scientific_name)}
              target="_blank"
              rel="noopener noreferrer"
              class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Wikipedia
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- No cases notice for species without detections -->
    {#if (species.detection_count || 0) === 0 && detections.length === 0}
      <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-6">
        <div class="flex items-center gap-3">
          <svg class="w-6 h-6 text-green-700 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <div class="font-medium text-green-800 dark:text-green-200">{t('species_detail.no.recorded.hpai.cases')}</div>
            <div class="text-sm text-green-700 dark:text-green-400">
              {#if species.vaccination_target}
                {t('species.detail.vaccination.program') || 'This species is part of an emergency vaccination program due to HPAI risk.'}
              {:else}
                {t('species.detail.no.hpai.detections') || 'No H5 detections have been recorded for this species in our database.'}
              {/if}
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- At a Glance stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
        <div class="text-2xl font-bold text-red-600 dark:text-red-400">
          {#if detections.length > 0}
            {formatNumber(detections.length)}
          {:else if (species.detection_count || 0) > 0}
            {formatNumber(species.detection_count)}
          {:else}
            <span class="text-gray-500 dark:text-gray-400">0</span>
          {/if}
        </div>
        <div class="text-sm text-red-600/70 dark:text-red-400/70">
          {detections.length > 0 ? t('species.reports_n') : t('lib_components_species_SpeciesDetail.detections')}
        </div>
        {#if detections.length > 0 && species.detection_count > detections.length}
          <div class="text-[10px] text-red-500/60 dark:text-red-400/60 mt-0.5">{t('species_full.covering_birds', { n: formatNumber(species.detection_count) })}</div>
        {/if}
      </div>
      <div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
        <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
          {getCountries().length || '—'}
        </div>
        <div class="text-sm text-purple-600/70 dark:text-purple-400/70">{t('lib_components_species_SpeciesDetail.countries')}</div>
      </div>
      <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
        <div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
          {species.genome_accession ? 'Yes' : 'No'}
        </div>
        <div class="text-sm text-blue-600/70 dark:text-blue-400/70">{t('lib_components_species_SpeciesDetail.genome')}</div>
      </div>
      <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4" title={t('susc.legacy.tip')}>
        <div class="text-2xl font-bold text-amber-700 dark:text-amber-400">
          {species.susceptibility_class || '—'}
        </div>
        <div class="text-sm text-amber-700/70 dark:text-amber-400/70">{t('lib_components_species_SpeciesDetail.susceptibility')} · {t('susc.legacy.short')}</div>
        <a href={`#/susceptibility/${encodeURIComponent(species.scientific_name)}`}
           class="text-xs text-amber-700 dark:text-amber-300 underline mt-1 inline-block">
          {t('susceptibility.link.page') || 'Two-axis view →'}
        </a>
      </div>
    </div>

    <!-- Detection Timeline -->
    {#if detections.length > 0}
      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('species_detail.detection.timeline')}</h3>
        <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <Sparkline data={getTimelineData()} width={500} height={60} color="#ef4444" />
          <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-2">
            <span>First: {formatDate(detections[detections.length - 1]?.date_detected)}</span>
            <span>Last: {formatDate(detections[0]?.date_detected)}</span>
          </div>
        </div>
      </div>
    {/if}

    <!-- Insights card (above the tabs) — plain-language gene panel summary -->
    {#if species}
      <SpeciesInsights taxonId={species.taxon_id} sci={species.scientific_name || ''} mode="card" />
    {/if}

    <!-- Tabs -->
    <div class="border-b border-gray-200 dark:border-gray-700 mb-4">
      <nav class="flex gap-4">
        {#each tabs as tab}
          <button
            onclick={() => {
              activeTab = tab.id;
              if (species?.taxon_id) navigate('species', String(species.taxon_id), { tab: tab.id });
            }}
            class="px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors {activeTab === tab.id ? 'border-blue-500 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
          >
            {t('tab.' + tab.id) || tab.label}
          </button>
        {/each}
      </nav>
    </div>

    <!-- Tab content -->
    {#if activeTab === 'overview'}
      <div class="space-y-6">
        <!-- Conservation Status -->
        {#if species.iucn || species.population || species.range || species.notes}
          <div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              Conservation
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              {#if species.iucn}
                {@const iucnInfo = getIUCNInfo(species.iucn)}
                <div>
                  <span class="text-gray-500 dark:text-gray-400">{t('species_detail.iucn.status')}</span>
                  <span class="ml-2 px-2 py-0.5 text-xs font-bold rounded {iucnInfo.bg} {iucnInfo.text}">
                    {t('iucn.' + (species.iucn || 'DD')) || iucnInfo.name}
                  </span>
                </div>
              {/if}
              {#if species.trend}
                {@const trendInfo = getTrendInfo(species.trend)}
                <div>
                  <span class="text-gray-500 dark:text-gray-400">{t('species_detail.population.trend')}</span>
                  <span class="ml-2 {trendInfo.color} font-medium">{trendInfo.icon} {t('trend.' + (species.population_trend || 'unknown')) || trendInfo.label}</span>
                </div>
              {/if}
              {#if species.population}
                <div>
                  <span class="text-gray-500 dark:text-gray-400">{t('lib_components_species_SpeciesDetail.population')}</span>
                  <span class="ml-2 text-gray-900 dark:text-white">{species.population}</span>
                </div>
              {/if}
              {#if species.range}
                <div class="md:col-span-2">
                  <span class="text-gray-500 dark:text-gray-400">{t('lib_components_species_SpeciesDetail.range')}</span>
                  <span class="ml-2 text-gray-900 dark:text-white">{species.range}</span>
                </div>
              {/if}
              {#if species.notes}
                <div class="md:col-span-2">
                  <span class="text-gray-500 dark:text-gray-400">{t('lib_components_species_SpeciesDetail.notes')}</span>
                  <span class="ml-2 text-gray-700 dark:text-gray-300">{species.notes}</span>
                </div>
              {/if}
            </div>
            <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <a
                href={iucnUrl.search(species.scientific_name)}
                target="_blank"
                rel="noopener noreferrer"
                class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                {t('species.view_iucn_red_list')}
              </a>
            </div>
          </div>
        {/if}

        <!-- Countries -->
        {#if getCountries().length > 0}
          <div>
            <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('species_detail.countries.with.detections')}</h4>
            <div class="flex flex-wrap gap-2">
              {#each getCountries() as country}
                <span class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-sm">
                  {country}
                </span>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Data Sources -->
        <div>
          <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('species_detail.data.sources')}</h4>
          <div class="flex flex-wrap gap-2">
            {#each Object.entries(getSources()) as [source, count]}
              <SourceBadge {source} {count} />
            {/each}
          </div>
        </div>
      </div>

    {:else if activeTab === 'detections'}
      {#if detections.length === 0}
        <div class="text-center py-10 px-4">
          <svg class="w-12 h-12 mx-auto text-gray-500 dark:text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="font-medium text-gray-700 dark:text-gray-300">{t('species_detail.no.hpai.detections.recorded')}</p>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-sm mx-auto">
            {t('species.no_detections_lead')} <a href="#/map" class="text-blue-600 dark:text-blue-400 hover:underline">{t('species_detail.global.map')}</a>
            {t('species.no_detections_tail')}
          </p>
        </div>
      {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200 dark:border-gray-700">
              <th class="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesDetail.date')}</th>
              <th class="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesDetail.country')}</th>
              <th class="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesDetail.strain')}</th>
              <th class="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">{t('lib_components_species_SpeciesDetail.source')}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-800">
            {#each detections.slice(0, 50) as detection}
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td class="py-2 px-3 text-gray-900 dark:text-white">{formatDate(detection.date_detected)}</td>
                <td class="py-2 px-3 text-gray-600 dark:text-gray-300">{detection.country || '—'}</td>
                <td class="py-2 px-3 text-gray-600 dark:text-gray-300">{cleanStrain(detection.strain) || '—'}</td>
                <td class="py-2 px-3"><SourceBadge source={detection.source} compact /></td>
              </tr>
            {/each}
          </tbody>
        </table>
        {#if detections.length > 50}
          <p class="text-sm text-gray-500 dark:text-gray-400 text-center py-3">
            Showing 50 of {detections.length} detections
          </p>
        {/if}
      </div>
      {/if}

    {:else if activeTab === 'genome'}
      {#if species.genome_accession}
        <div class="space-y-4">
          {#if ogStats}
            <div class="flex items-start gap-2 p-3 rounded-lg bg-sky-50 dark:bg-sky-900/20 border border-sky-200 dark:border-sky-800">
              <span>🌳</span>
              <div class="text-sm text-sky-800 dark:text-sky-200">
                {t('species.part_of_the')} <strong>{t('species_detail.orthofinder.463bird.orthology.run')}</strong>
                {t('species.orthofinder_og_stats', { ogs: ogStats.n_ogs.toLocaleString(), prots: ogStats.n_proteins.toLocaleString(), panel: ogStats.n_panel_ogs })}
                <span class="text-sky-600/70 dark:text-sky-300/70">{t('species_detail.pergene.copy.numbers.are')}</span>
              </div>
            </div>
          {/if}
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">{t('species_detail.assembly.accession')}</div>
              <div class="font-medium text-gray-900 dark:text-white">
                <a
                  href={ncbi.assembly(species.genome_accession)}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {species.genome_accession}
                </a>
              </div>
            </div>
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">{t('species_detail.assembly.level')}</div>
              <div class="font-medium">
                {#if species.assembly_level}
                  {@const levelInfo = getAssemblyLevelInfo(species.assembly_level)}
                  <span class="px-2 py-0.5 rounded text-sm {levelInfo.color === 'green' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : levelInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}">
                    {t('assembly.' + (species.genome_level || 'Unknown')) || levelInfo.label}
                  </span>
                {:else}
                  <span class="text-gray-500 dark:text-gray-400">—</span>
                {/if}
              </div>
            </div>
            {#if species.total_length}
              <div>
                <div class="text-sm text-gray-500 dark:text-gray-400">{t('species_detail.total.length')}</div>
                <div class="font-medium text-gray-900 dark:text-white">{formatN50(species.total_length)}</div>
              </div>
            {/if}
            {#if species.scaffold_n50}
              <div>
                <div class="text-sm text-gray-500 dark:text-gray-400">{t('species_detail.scaffold.n50')}</div>
                <div class="font-medium text-gray-900 dark:text-white">{formatN50(species.scaffold_n50)}</div>
              </div>
            {/if}
            {#if species.contig_n50}
              <div>
                <div class="text-sm text-gray-500 dark:text-gray-400">{t('species_detail.contig.n50')}</div>
                <div class="font-medium text-gray-900 dark:text-white">{formatN50(species.contig_n50)}</div>
              </div>
            {/if}
            <div>
              <div class="text-sm text-gray-500 dark:text-gray-400">{t('lib_components_species_SpeciesDetail.annotation')}</div>
              <div class="font-medium">
                {#if species.has_annotation === true}
                  <span class="px-2 py-0.5 rounded text-sm bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
                    ✓ Annotated{species.annotation_status ? ` (${species.annotation_status.toLowerCase()})` : ''}
                  </span>
                {:else if species.has_annotation === false}
                  <span class="px-2 py-0.5 rounded text-sm bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">{t('species_detail.not.annotated')}</span>
                {:else}
                  <span class="text-gray-500 dark:text-gray-400">—</span>
                {/if}
              </div>
            </div>
            {#if species.is_representative !== null && species.is_representative !== undefined}
              <div>
                <div class="text-sm text-gray-500 dark:text-gray-400">{t('species_detail.ncbi.status')}</div>
                <div class="font-medium text-gray-900 dark:text-white">
                  {species.is_representative ? '★ Representative assembly' : 'Alternative assembly'}
                </div>
              </div>
            {/if}
          </div>

          <div class="pt-4 border-t border-gray-200 dark:border-gray-700">
            <a
              href={ncbi.assembly(species.genome_accession)}
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              {t('species.view_ncbi_datasets')}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      {:else}
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-3 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <p>{t('species_detail.no.genome.assembly.available')}</p>
          <a
            href={ncbi.geneSearch(species.scientific_name)}
            target="_blank"
            rel="noopener noreferrer"
            class="text-blue-600 dark:text-blue-400 hover:underline text-sm mt-2 inline-block"
          >
            {t('species.search.ncbi') || 'Search NCBI for related sequences →'}
          </a>
        </div>
      {/if}

    {:else if activeTab === 'genes'}
      {@const genePanel = genePresence?.species?.[species.scientific_name]}
      {#if genePanel}
        {@const s = genePresence?.summary?.[species.scientific_name]}
        <div class="space-y-4">
          <!-- Summary + view-all shortcut (top, per usability review 2026-11) -->
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('genes.n_genes_searched', {n: Object.keys(genePanel).length})}
            </span>
            {#if s}
              <span class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
                {s.full} {t('model.cyto.present')}
              </span>
              <span class="px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                {s.fragment} {t('model.cyto.fragment')}
              </span>
              <span class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {s.not_found} {t('species.chip.absent')}
              </span>
              {#if s.critical_absences?.length > 0}
                <span class="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  ⚠ {t('species.critical_absence')}: {s.critical_absences.join(', ')}
                </span>
              {/if}
            {/if}
            <a
              href="#/species-full/{encodeURIComponent(species.scientific_name)}?tab=genes"
              class="ml-auto text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap"
            >
              {t('species.view_all_genes_n', { n: Object.keys(genePanel).length })}
            </a>
          </div>

          <!-- Key genes (critical + high importance) -->
          <div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {t('species.key.genes.legend') || 'Key genes — colour = status in this species, badge = role in H5N1 biology'}
            </p>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {#each Object.entries(genePresence?.key_genes || {}) as [sym, info]}
                {#if genePanel[sym]}
                  {@const g = genePanel[sym]}
                  <a href="#/genes/{sym}" class="block p-2 rounded-lg border {g.status === 'FULL'
                    ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
                    : g.status === 'FRAGMENT'
                      ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20'
                      : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'} hover:shadow-md transition-shadow"
                    title={t('species.speciesdetail.view.sym.gene.page', { sym })}>
                    <div class="flex items-center justify-between gap-1">
                      <span class="font-mono text-xs font-semibold text-gray-900 dark:text-white">{sym}</span>
                      <span class="text-xs" title={g.status === 'FULL' ? (t('presence.full') || 'Present (full-length)') : g.status === 'FRAGMENT' ? (t('presence.fragment') || 'Fragment found') : (t('presence.notfound') || 'Not found')}>
                        {g.status === 'FULL' ? '✓' : g.status === 'FRAGMENT' ? '~' : '✗'}
                      </span>
                    </div>
                    <p class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">{info.name}</p>
                    {#if g.importance === 'critical'}
                      <span class="text-[11px] text-red-600 dark:text-red-400 font-medium">● critical</span>
                    {:else if g.importance === 'high'}
                      <span class="text-[11px] text-amber-700 dark:text-amber-400 font-medium">◐ high</span>
                    {/if}
                  </a>
                {/if}
              {/each}
            </div>
          </div>

          <!-- Legend + link to full page -->
          <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <div class="flex flex-wrap gap-3 text-[11px] text-gray-500 dark:text-gray-400">
              <span>{t('species.legend_presence')}</span>
              <span>{t('species.legend_critical')}</span>
              <span>{t('species.legend_high')}</span>
            </div>
            <a
              href="#/species-full/{encodeURIComponent(species.scientific_name)}?tab=genes"
              class="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap"
            >
              {t('species.view_all_genes_n', { n: Object.keys(genePanel).length })}
            </a>
          </div>
        </div>
      {:else}
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <p class="text-sm">{t('species_detail.no.genome.available.for')}</p>
          <p class="text-xs mt-1 text-gray-500 dark:text-gray-400">{t('species_detail.gene.presence.requires.a')}</p>
        </div>
      {/if}

    {:else if activeTab === 'research'}
      {#if !wikiLoaded}
        <div class="text-center py-8">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{t('species_detail.loading.research.evidence')}</p>
        </div>
      {:else if wikiSpecies}
        <div class="space-y-4">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-semibold text-gray-700 dark:text-gray-300">
              {wikiSpecies.paper_count} papers · {wikiSpecies.evidence_count} findings
            </span>
            {#if wikiSpecies.avian === true}
              <span class="px-2 py-0.5 text-xs rounded-full bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">🪶 avian host</span>
            {:else if wikiSpecies.avian === false}
              <span class="px-2 py-0.5 text-xs rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300">🐁 mammalian host</span>
            {/if}
            {#each Object.entries(wikiSpecies.status_counts) as [status, count]}
              <span class="px-2 py-0.5 text-xs rounded-full {statusColors[status] || statusColors.unknown}">
                {count} {status}
              </span>
            {/each}
            {#each Object.entries(wikiSpecies.study_types || {}).slice(0, 3) as [stype, count]}
              <span class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {stype.replace(/,/g, ' + ')} ×{count}
              </span>
            {/each}
            {#if wikiSpecies.scientific_name && wikiSpecies.scientific_name !== species.scientific_name}
              <span class="text-xs text-gray-500 dark:text-gray-400 italic">({wikiSpecies.scientific_name})</span>
            {/if}
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400">
            {t('species.evidence.synth') || 'Evidence synthesized from verified LLM extraction of full-text research papers.'}
          </p>

          {#if wikiSpecies.conclusions?.length > 0}
            <div>
              <h4 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">{t('species_detail.study.conclusions')}</h4>
              <div class="space-y-2">
                {#each wikiSpecies.conclusions.slice(0, 3) as c}
                  <blockquote class="text-sm text-gray-600 dark:text-gray-400 border-l-2 border-blue-300 dark:border-blue-700 pl-3">
                    {c.conclusion}
                    <a href="#/papers/{c.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-1" title={c.title}>[{c.paper_id}, {c.year ?? ''}]</a>
                  </blockquote>
                {/each}
              </div>
            </div>
          {/if}

          {#if wikiSpecies.key_findings?.length > 0}
            <div>
              <h4 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">{t('species_detail.key.numbers')}</h4>
              <div class="space-y-1.5">
                {#each wikiSpecies.key_findings.slice(0, 5) as f}
                  <div class="flex items-start gap-2 text-sm">
                    <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                      {f.value}
                    </span>
                    <span class="text-gray-600 dark:text-gray-400 min-w-0">
                      {ft(f.fh) || f.finding}
                      <a href="#/papers/{f.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline" title={f.title}>[{f.paper_id}]</a>
                    </span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          {#if wikiSpecies.methods_findings?.length > 0}
            <details class="group">
              <summary class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5 uppercase tracking-wide cursor-pointer list-none flex items-center gap-1 hover:text-gray-600 dark:hover:text-gray-300">
                <svg class="w-3 h-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                {t('species_detail.sequencing.methods')} ({wikiSpecies.methods_findings.length})
              </summary>
              <div class="space-y-1.5 mt-1.5">
                {#each wikiSpecies.methods_findings as f}
                  <div class="flex items-start gap-2 text-sm">
                    <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-mono font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      {f.value}
                    </span>
                    <span class="text-gray-500 dark:text-gray-400 min-w-0">
                      {ft(f.fh) || f.finding}
                      <a href="#/papers/{f.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline" title={f.title}>[{f.paper_id}]</a>
                    </span>
                  </div>
                {/each}
              </div>
            </details>
          {/if}

          <div>
            <h4 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">{t('species_detail.evidence.by.paper')}</h4>
            <div class="space-y-3">
              {#each (showAllEvidence ? wikiSpecies.evidence : wikiSpecies.evidence.slice(0, 5)) as ev}
                <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                  <div class="flex items-start justify-between gap-2 mb-1">
                    <span class="px-2 py-0.5 text-xs rounded-full {statusColors[ev.infection_status] || statusColors.unknown}">
                      {ev.infection_status}
                    </span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">{ev.year ?? ''}</span>
                  </div>
                  <p class="text-sm text-gray-600 dark:text-gray-400">{ev.finding}</p>
                  <a
                    href="#/papers/{ev.paper_id}"
                    class="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1 inline-block"
                    title={ev.title}
                  >
                    {ev.title || ev.paper_id} →
                  </a>
                </div>
              {/each}
            </div>
            {#if wikiSpecies.evidence.length > 5}
              <button
                onclick={() => showAllEvidence = !showAllEvidence}
                class="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-2"
              >
                {showAllEvidence ? (t('common.show.less') || 'Show less') : (t('common.show.all.rows') || 'Show all') + ` ${wikiSpecies.evidence.length} ` + (t('evidence.rows') || 'evidence rows')}
              </button>
            {/if}
          </div>

          {#if wikiSpecies.notable_claims?.length > 0}
            <div>
              <h4 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">{t('species_detail.notable.claims')}</h4>
              {#each wikiSpecies.notable_claims.slice(0, 2) as claim}
                <div class="text-sm text-gray-600 dark:text-gray-400 flex items-start gap-2">
                  <span class="text-amber-700 dark:text-amber-400 flex-shrink-0">★</span>
                  <span>
                    {claim.claim}
                    <a href="#/papers/{claim.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline ml-1" title={claim.title}>[{claim.paper_id}]</a>
                  </span>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {:else}
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <svg class="w-12 h-12 mx-auto mb-3 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <p>{t('species_detail.no.extracted.research.findings')}</p>
          <p class="text-sm mt-1">{t('species.check_the')} <a href="#/papers" class="text-blue-600 dark:text-blue-400 hover:underline">{t('lib_components_species_SpeciesDetail.papers')}</a>{t('species.speciesdetail.page.for.related.literature') || 'page for related literature.'}</p>
        </div>
      {/if}
    {/if}
  {/if}
</Modal>
