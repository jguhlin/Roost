<script>
  import { trackEvent, trackSearch } from '../../analytics.js';
  import { t, tc, sn, ft } from '../../../lib/stores/i18n.svelte.js';
  /**
   * SpeciesFullPage — complete species view (not the modal).
   * Route: #/species-full/{Scientific_name}
   *
   * Sections:
   *   - Header: names, taxonomy, status badges (detected / genome / gene panel)
   *   - Gene Panel: ALL genes with search + filters (status × importance)
   *   - Research: wiki findings (future: same as modal research tab)
   */
  import { onMount } from 'svelte';
  import { dbStore, db } from '../../stores/db.js';
  import { fetchGeneCatalogue, panelFromCalls } from '../../utils/presence.js';
  import { updateParams, getRoute, subscribe as routerSubscribe } from '../../stores/router.js';
  import { formatNumber, formatN50, formatDate, getAssemblyLevelInfo, getIUCNInfo } from '../../utils/format.js';

  /** Clean strain labels: the parquet sometimes carries Python-dict strings
   *  ("{'id': 117, 'keyValue': 'not typed', ...}") — extract the readable part. */
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
  import { iucn as iucnUrl } from '../../utils/urls.js';
  import SourceBadge from '../common/SourceBadge.svelte';
  import { phylopicIndex, phylopicPath } from '../../utils/phylopic.js';
  import EvidenceDrawer from '../genes/EvidenceDrawer.svelte';
  import SpeciesInsights from './SpeciesInsights.svelte';

  let { sciName = '' } = $props();
  // analytics: which species pages people open
  $effect(() => { if (sciName) trackEvent('Species', 'view', decodeURIComponent(sciName)); });

  let loading = $state(true);
  let species = $state(null);          // row from db/species or index entry
  let detections = $state([]);
  let genePresence = $state(null);          // full 48MB catalogue — lazy
  let genomeRelatives = $state(null);        // closest relatives with genomes (for no-genome species)
  let presenceSummaryCompact = null; // retired (Phase 2 Step 4): SQL summary is the single source
  let wikiSpecies = $state(null);
  let silhouette = $state(null);
  let assembly = $state(null);               // NCBI assembly record (genomes.parquet)

  $effect(() => {
    if (species?.scientific_name) {
      phylopicIndex().then(idx => { silhouette = phylopicPath(species.scientific_name, idx); });
    }
  });

  // IUCN Red List badge (Wikidata P141 mirror; see fetch_iucn_status.py)
  let iucnCode = $state(null);
  $effect(() => {
    const name = species?.scientific_name || decodeURIComponent(sciName);
    if (!name) return;
    let alive = true;
    (async () => {
      try {
        const r = await fetch('data/species/iucn_status.json');
        if (!r.ok) return;
        const d = await r.json();
        if (alive) iucnCode = d?.status?.[name] || null;
      } catch { /* badge stays hidden */ }
    })();
    return () => { alive = false; };
  });

  // Gene panel state
  let geneSearch = $state('');
  let statusFilter = $state('all');    // all | FULL | FRAGMENT | NOT_FOUND
  let importanceFilter = $state('all'); // all | critical | high | standard
  let geneView = $state('compact');     // compact (bird's-eye) | detailed (list)
  let inspectGene = $state(null);        // gene symbol with open evidence drawer
  let section = $state('overview');    // overview | genome | genes | research

  async function loadFullPresence() {
    if (genePresence) return;
    try {
      // This species' panel + summary from DuckDB; catalogue metadata from
      // the small JSON — template shape preserved (Phase 2 Step 3)
      const sci = decodeURIComponent(sciName);
      const [cat, calls, summary] = await Promise.all([
        fetchGeneCatalogue(),
        db.getPresenceCallsForSpecies(sci),
        db.getSpeciesGeneSummary(sci),
      ]);
      genePresence = {
        total_species: cat?.total_species || 0,
        gene_catalogue: cat?.gene_catalogue || {},
        species: { [sci]: panelFromCalls(calls) },
        summary: { [sci]: summary },
      };
    } catch { /* ok */ }
  }

  const statusIcon = { FULL: '✓', FRAGMENT: '~', NOT_FOUND: '✗' };
  const statusLabel = { FULL: 'Present', FRAGMENT: 'Fragment', NOT_FOUND: 'Not found' };

  // Method provenance — how do we know this call?
  // E5 = NCBI annotation | E4 = our DIAMOND search (✨ annotation-gap recovery
  // when the genome IS annotated) | E3 = fragment | E2 = no match anywhere
  function methodInfo(level, genomeAnnotated) {
    if (!level) return null;
    if (level.startsWith('E5')) return {
      icon: '🏷️', label: (t('method.annotated') || 'annotated'), code: 'E5',
      cls: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
      tip: 'Listed in this genome\'s NCBI annotation — gold standard evidence'
    };
    if (level.startsWith('E4')) return {
      icon: '✨', label: (t('method.search-found') || 'search-found'), code: 'E4',
      cls: 'bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-800',
      tip: genomeAnnotated
        ? 'Missing from the annotation but recovered by our DIAMOND search — an annotation gap the pipeline found'
        : 'Found by DIAMOND search (genome has no NCBI annotation)'
    };
    if (level.startsWith('E3')) return {
      icon: '≈', label: (t('method.fragment') || 'fragment'), code: 'E3',
      cls: 'bg-amber-50 text-amber-700 dark:text-amber-400 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800',
      tip: 'Partial match only — possibly pseudogene, assembly gap, or divergent gene'
    };
    if (level.startsWith('E2')) return {
      icon: '∅', label: (t('method.nomatch') || 'no match'), code: 'E2',
      cls: 'bg-gray-100 text-gray-600 dark:text-gray-400 border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
      tip: genomeAnnotated
        ? 'Annotated genome + no search match = high-confidence absence'
        : 'No search match on an unannotated genome — weaker absence evidence'
    };
    return null;
  }

  // count of E4s on an annotated genome = annotation gaps recovered
  const recoveredCount = $derived.by(() => {
    if (!genePanel || species?.has_annotation !== true) return 0;
    return Object.values(genePanel).filter(g => g.level?.startsWith('E4')).length;
  });

  // verdict computed from the VISIBLE strip — never contradict the cards above
  const stripVerdict = $derived.by(() => {
    if (!birdseye.length) return null;
    const missingCritical = birdseye.filter(g => g.status === 'NOT_FOUND' && g.importance === 'critical');
    const missingHigh = birdseye.filter(g => g.status === 'NOT_FOUND' && g.importance !== 'critical');
    const frags = birdseye.filter(g => g.status === 'FRAGMENT');
    return { missingCritical, missingHigh, frags };
  });

  // --- URL state: ?tab= plus gene-panel sub-state — ?gq= (gene search),
  //     ?gst= (status), ?gimp= (importance), ?gview= (compact|detailed),
  //     ?gg= (open evidence drawer gene). Absent param = its default;
  //     echo-guarded so URL↔state converges without loops.
  let urlSyncReady = $state(false);

  const applyParams = (p = {}) => {
    const nextTab = ['overview', 'genome', 'genes', 'research'].includes(p.tab) ? p.tab : 'overview';
    if (nextTab !== section) {
      section = nextTab;
      if (nextTab === 'genes') loadFullPresence();
    }
    const nextGq = p.gq || '';
    if (nextGq !== geneSearch) geneSearch = nextGq;
    const nextSt = ['FULL', 'FRAGMENT', 'NOT_FOUND'].includes(p.gst) ? p.gst : 'all';
    if (nextSt !== statusFilter) statusFilter = nextSt;
    const nextImp = ['critical', 'high', 'standard'].includes(p.gimp) ? p.gimp : 'all';
    if (nextImp !== importanceFilter) importanceFilter = nextImp;
    const nextView = p.gview === 'detailed' ? 'detailed' : 'compact';
    if (nextView !== geneView) geneView = nextView;
    const nextGg = p.gg || null;
    if (nextGg !== inspectGene) inspectGene = nextGg;
  };

  const applyRoute = (route) => {
    // SPA navigation: same species with new params applies them; a new
    // species is handled by the sciName effect below.
    if (route.page !== 'species-full' || !urlSyncReady) return;
    if (decodeURIComponent(route.id || '').toLowerCase() !== decodeURIComponent(sciName).toLowerCase()) return;
    applyParams(route.params || {});
  };

  function setSection(tab) {
    trackEvent('Species', 'tab', tab);
    section = tab;   // URL sync via the effect below
  }

  // state → URL
  $effect(() => {
    void section; void geneSearch; void statusFilter;
    void importanceFilter; void geneView; void inspectGene;
    if (!urlSyncReady) return;
    updateParams({
      tab: section !== 'overview' ? section : null,
      gq: geneSearch || null,
      gst: statusFilter !== 'all' ? statusFilter : null,
      gimp: importanceFilter !== 'all' ? importanceFilter : null,
      gview: geneView !== 'compact' ? geneView : null,
      gg: inspectGene || null,
    });
  });
  const statusColor = {
    FULL: 'text-green-700 dark:text-green-400 bg-green-50 border-green-200 dark:text-green-300 dark:bg-green-900/20 dark:border-green-800',
    FRAGMENT: 'text-amber-700 dark:text-amber-400 bg-amber-50 border-amber-200 dark:text-amber-300 dark:bg-amber-900/20 dark:border-amber-800',
    NOT_FOUND: 'text-red-700 bg-red-50 border-red-200 dark:text-red-300 dark:bg-red-900/20 dark:border-red-800'
  };

  let lastLoadedSci = null;
  let loadSeq = 0;
  const loadData = async () => {
    const seq = ++loadSeq;
    const isNewSpecies = lastLoadedSci !== sciName;
    if (isNewSpecies) {
      lastLoadedSci = sciName;
      species = null; detections = []; wikiSpecies = null; assembly = null;
      genePresence = null; genomeRelatives = null; loading = true;
    }
    try {
      // For species without genomes: pull closest relatives from the insights
      // artifact (relatives are pre-computed by phylogeny at build time).
      // The insights manifest maps taxon_id → sci; artifacts are {taxon_id}.json.
      try {
        const sci = decodeURIComponent(sciName);
        const rIdx = await fetch('data/species_index.json').then(r => r.json());
        const self = rIdx.find(s => s.sci?.toLowerCase() === sci.toLowerCase());
        if (self && !self.has_genome) {
          const rIns = await fetch(`data/species_insights/${self.id}.json`);
          if (rIns.ok) {
            const ins = await rIns.json();
            if (ins.relatives?.length) {
              genomeRelatives = ins.relatives
                .map(rel => {
                  const e = rIdx.find(s => s.sci === rel);
                  return { sci: rel, com: e?.com || rel, has_genome: !!e?.has_genome };
                })
                .slice(0, 6);
            }
          }
        }
      } catch { /* insights optional */ }
      // NCBI assembly record for the Genome tab (all species, not just
      // detected ones — kakapo & friends previously lost this entirely)
      try {
        await dbStore.loadGenomes();
        const rows = await db.query(
          `SELECT * FROM genomes WHERE LOWER(organism_name) = '${sciName.toLowerCase().replace(/'/g, "''")}' ORDER BY (is_representative) DESC, assembly_level DESC LIMIT 1`
        );
        if (rows.length) assembly = rows[0];
      } catch { /* ok */ }

      // Try db first (detected species have full profile)
      try {
        await dbStore.loadSpecies();
        const rows = await db.query(
          `SELECT * FROM species WHERE scientific_name = '${sciName.replace(/'/g, "''")}' LIMIT 1`
        );
        if (rows.length) species = rows[0];
      } catch { /* fall through */ }

      // Fall back to the comprehensive species index
      if (!species) {
        try {
          const r = await fetch('data/species_index.json');
          const idx = await r.json();
          const entry = idx.find(s => s.sci?.toLowerCase() === decodeURIComponent(sciName).toLowerCase());
          if (entry) {
            species = {
              scientific_name: entry.sci,
              common_name: entry.com,
              order: entry.ord,
              family: entry.fam,
              taxon_id: entry.id,
              detection_count: entry.det || 0,
              has_genome: entry.has_genome,
              has_presence: entry.has_presence,
              // carry curated overlay/enrichment fields (hihi-class entries:
              // taxonomy tail species the DuckDB table doesn't know)
              iucn: entry.iucn || null,
              conservation: entry.conservation || null,
              population: entry.population || null,
              countries: entry.countries || null,
              maori_name: entry.maori_name || null,
              vaccination_target: entry.vaccination_target || null,
              case: entry.case || null,
            };
          }
        } catch { /* ok */ }
      }

      // Always fetch the index entry for overlay enrichment fields (Māori
      // name, population, vaccination target, DOC cases) — these live in the
      // index even for DuckDB-known species (kāhu, detected species with
      // curated metadata) and the DuckDB table doesn't carry them
      try {
        const rIdx = await fetch('data/species_index.json');
        const idxAll = rIdx.ok ? await rIdx.json() : [];
        const idxEntry = idxAll.find(s => s.sci?.toLowerCase() === decodeURIComponent(sciName).toLowerCase());
        if (idxEntry && species) {
          for (const f of ['maori_name', 'population', 'vaccination_target', 'case', 'conservation', 'countries']) {
            if (idxEntry[f] !== undefined && idxEntry[f] !== null) {
              species[f] = idxEntry[f];
            }
          }
        }
      } catch { /* enrichment fields are optional */ }

      // Load detections if species has any (via store — loads the table first)
      if (species?.taxon_id && (species.detection_count || 0) > 0) {
        try {
          detections = await db.getDetectionsForSpecies(decodeURIComponent(sciName).replace(/'/g, "''"));
        } catch { detections = []; }
      }

      // Load wiki data (wiki_species.json: {generated, total_species, species:{}})
      try {
        const r = await fetch('data/wiki_species.json');
        const wiki = (await r.json()).species || {};
        const key = decodeURIComponent(sciName).toLowerCase();
        const com = (species?.common_name || '').toLowerCase();
        wikiSpecies = Object.values(wiki).find(
          w => (w.scientific_name || '').toLowerCase() === key ||
               (w.canonical || '').toLowerCase() === (com || key)
        ) || null;
      } catch { /* ok */ }
    } finally {
      if (seq === loadSeq) loading = false;
    }
  };

  // SPA species switch (e.g. a related-species link while mounted):
  // re-run the data load for the new name. ($effect must be top-level;
  // the null-guard makes mount ordering irrelevant.)
  $effect(() => {
    void sciName;
    if (lastLoadedSci === null || lastLoadedSci === sciName) return;
    loadData();
  });

  // OrthoFinder badge (463-bird run): per-species OG stats, hidden for
  // species outside the run. Small file (~30 KB) fetched once per mount.
  let ogStatsMap = null;
  let ogStats = $state(null);
  $effect(() => {
    const sci = decodeURIComponent(sciName);
    ogStats = null;
    if (!sci) return;
    void (async () => {
      try {
        ogStatsMap ??= await (await fetch('data/orthofinder/species_og_stats.json')).json();
        ogStats = ogStatsMap[sci] || null;
      } catch { /* badge stays hidden */ }
    })();
  });

  onMount(() => {
    applyParams(getRoute()?.params || {});
    urlSyncReady = true;
    loadData();
    // eagerly load gene presence so the overview summary card shows for
    // every species with calls (no-detection species included — kākāpō fix)
    loadFullPresence();
    return routerSubscribe(applyRoute);
  });

  // Gene panel derived values
  const genePanel = $derived(genePresence?.species?.[decodeURIComponent(sciName)] || null);
  const summary = $derived(genePresence?.summary?.[decodeURIComponent(sciName)] || null);

  // analytics: gene-panel filter searches with result counts (no-op dev)
  let _geneSearchTimer = null;
  $effect(() => {
    void geneSearch;
    if (_geneSearchTimer) clearTimeout(_geneSearchTimer);
    if (geneSearch.trim().length < 2) return;
    const q = geneSearch.trim();
    _geneSearchTimer = setTimeout(() => {
      const n = filteredGenes.length;
      trackSearch('species-genes', q, n);
    }, 600);
  });

  const filteredGenes = $derived.by(() => {
    if (!genePanel) return [];
    const q = geneSearch.toLowerCase();
    return Object.entries(genePanel)
      .filter(([sym, g]) => {
        if (q && !sym.toLowerCase().includes(q)) return false;
        if (statusFilter !== 'all' && g.status !== statusFilter) return false;
        if (importanceFilter !== 'all' && g.importance !== importanceFilter) return false;
        return true;
      })
      .sort((a, b) => {
        // critical first, then high, then alphabetical
        const imp = { critical: 0, high: 1, standard: 2 };
        const d = imp[a[1].importance] - imp[b[1].importance];
        return d !== 0 ? d : a[0].localeCompare(b[0]);
      });
  });

  const totalSpecies = $derived(genePresence?.total_species || 0);

  // Bird's-eye: the headline sensors/factors a worried conservationist checks first
  const BIRDSEYE = ['DDX58', 'IFIH1', 'ANP32A', 'MX1', 'IFITM3', 'TLR7', 'STAT1', 'MAVS'];
  const birdseye = $derived.by(() => {
    if (!genePanel) return [];
    return BIRDSEYE.map(sym => ({
      sym,
      name: genePresence?.gene_catalogue?.[sym]?.name || sym,
      fn: (tc(`gene.${sym}.function`) || genePresence?.gene_catalogue?.[sym]?.function || '').split(/[.—]/)[0],
      ...(genePanel[sym] || {})
    }));
  });
</script>

<div class="max-w-7xl mx-auto">
  {#if loading}
    <div class="animate-pulse py-16">
      <div class="h-10 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-8"></div>
      <div class="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
    </div>
  {:else}
    <!-- Breadcrumb -->
    <nav class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      <a href="#/species" class="hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-400">{t('lib_components_species_SpeciesFullPage.species')}</a>
      <span class="mx-1">/</span>
      <span class="text-gray-900 dark:text-white">{sn(species?.scientific_name, species?.common_name) || decodeURIComponent(sciName)}</span>
    </nav>

    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex items-start gap-5">
          {#if silhouette}
            <img
              src={silhouette}
              alt=""
              class="h-20 w-20 object-contain dark:invert"
              title="Silhouette: PhyloPic"
            />
          {/if}
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
            {species?.common_name || decodeURIComponent(sciName)}
          </h1>
          <p class="italic text-gray-600 dark:text-gray-300 mt-1 flex items-center gap-2">
            {species?.scientific_name || decodeURIComponent(sciName)}
            {#if iucnCode || species?.iucn || species?.conservation}
              {@const CONV = { 'least concern': 'LC', 'near threatened': 'NT', 'conservation dependent': 'LR/cd', 'vulnerable': 'VU', 'endangered': 'EN', 'critically endangered': 'CR', 'extinct in the wild': 'EW', 'extinct': 'EX' }}
              {@const code = iucnCode || species?.iucn || CONV[(species?.conservation || '').replace(/_/g, ' ')] || 'DD'}
              {@const info = getIUCNInfo(code)}
              <a
                href={iucnUrl.search(species?.scientific_name || sciName)}
                target="_blank" rel="noopener noreferrer"
                title={t('species.speciesfullpage.info.name.iucn.red', { 'info.name': info.name })}
                class="px-2 py-0.5 text-xs not-italic font-bold rounded {info.bg} {info.text} hover:opacity-80 transition-opacity"
              >{code}</a>
            {/if}
            <a
              href="#/compare?s={encodeURIComponent(species?.scientific_name || sciName)}"
              class="text-xs not-italic px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/60 transition-colors"
              title={t('species.speciesfullpage.compare.this.species.side') || 'Compare this species side-by-side with others (detections, genome, gene panel)'}
            >⚖ Compare</a>
          </p>
          <!-- Enriched metadata: Māori name, population, vaccination target,
               DOC case notes (from the curated overlay) -->
          <div class="flex flex-wrap gap-1.5 mt-1.5">
            {#if species?.maori_name}
              <span class="text-sm font-medium text-teal-700 dark:text-teal-300" title="te reo Māori name">{species.maori_name}</span>
            {/if}
            {#if species?.population}
              <span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">{species.population}</span>
            {/if}
            {#if species?.vaccination_target}
              <span class="text-xs px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300" title={t('species.vax_target_tip')}>💉 {t('species.vax_target')}</span>
            {/if}
            {#if species?.case && species.case.location}
              <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                {t('species.case_note', { n: species.case.case_number, loc: species.case.location, date: species.case.date, src: species.case.source })}
              </span>
            {/if}
          </div>
          {#if species?.order || species?.family}
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {#if species?.order}{species.order}{/if}{#if species?.order && species?.family} · {/if}{#if species?.family}{species.family}{/if}
            </p>
          {/if}
        </div>
        </div>

        <div class="flex flex-wrap gap-2">
          {#if detections.length > 0}
            <span class="px-3 py-1 rounded-full text-sm bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                  title={t('species.reports_tooltip')}>
              {formatNumber(detections.length)} {t('species.reports_n')}
            </span>
          {:else if (species?.detection_count || 0) > 0}
            <span class="px-3 py-1 rounded-full text-sm bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                  title={t('species.reports_tooltip')}>
              {formatNumber(species.detection_count)} {t('species.birds_n')}
            </span>
          {:else}
            <span class="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {t('species.no.detections') || 'No detections recorded'}
            </span>
          {/if}
          {#if genePanel}
            <span class="px-3 py-1 rounded-full text-sm bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              {t('species.gene_panel_available')}
            </span>
          {/if}
          {#if species?.has_genome}
            <span class="px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              {t('species.genome_available')}
            </span>
          {/if}
          {#if ogStats}
            <span class="px-3 py-1 rounded-full text-sm bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
              title="{t('species.orthofinder.title') || 'OrthoFinder 3.1.5 run over 463 avian proteomes (root-corrected species tree)'}: {ogStats.n_ogs.toLocaleString()} orthogroups include proteins from this species ({ogStats.n_proteins.toLocaleString()} proteins); present in {ogStats.n_panel_ogs} of 720 host-panel orthogroups. See gene pages for per-orthogroup copy numbers.">
              🌳 OrthoFinder: {ogStats.n_ogs.toLocaleString()} orthogroups
            </span>
          {/if}
          {#if wikiSpecies}
            <span class="px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
              📚 {wikiSpecies.paper_count} papers
            </span>
          {/if}
        </div>
      </div>

      {#if summary?.critical_absences?.length > 0}
        <div class="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p class="text-sm text-red-700 dark:text-red-300">
            <strong>{t('species.critical_absences')}</strong>
            {summary.critical_absences.join(', ')}
            {t('species.critical_absences_tail')}
            <span class="text-red-600 dark:text-red-400">{t('species_full.these.genes.are.directly')}</span>
          </p>
        </div>
      {/if}
    </div>

    <!-- Section tabs -->
    <div class="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-6">
      {#each [['overview', 'Overview'], ['genome', 'Genome'], ['genes', 'Gene Panel'], ['research', 'Research']] as [id, label]}
        <button
          class="px-4 py-2 font-medium text-sm border-b-2 transition-colors {section === id
            ? 'border-blue-600 text-blue-600 dark:text-blue-400'
            : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white'}"
          onclick={() => { setSection(id); if (id === 'genes') loadFullPresence(); }}
        >
          {label}
          {#if id === 'genes' && genePanel}
            <span class="ml-1 text-xs text-gray-500 dark:text-gray-400">({Object.keys(genePanel).length})</span>
          {/if}
        </button>
      {/each}
    </div>

    <!-- Overview section -->
    {#if section === 'overview'}
      <!-- Insights panel — the plain-language gene story (design brief 2026-11) -->
      <div>
        <SpeciesInsights taxonId={species?.taxon_id} sci={species?.scientific_name || decodeURIComponent(sciName)} mode="full" />
      </div>
      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
          <h2 class="font-semibold text-gray-900 dark:text-white mb-3">{t('lib_components_species_SpeciesDetail.detections')}</h2>
          {#if detections.length > 0}
            <p class="text-3xl font-bold text-gray-900 dark:text-white mb-1">{formatNumber(detections.length)}</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">{t('species_full.reports')}</p>
            {#if species?.detection_count && species.detection_count > detections.length}
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{t('species_full.covering_birds', { n: formatNumber(species.detection_count) })}</p>
            {/if}
            <p class="text-sm text-gray-500 dark:text-gray-400">{t('species_full.confirmed.hpai.detections')}</p>
            <table class="mt-4 w-full text-sm">
              <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                {#each detections.slice(0, 10) as d}
                  <tr>
                    <td class="py-1.5 pr-3 text-gray-500 dark:text-gray-400">{formatDate(d.date_detected)}</td>
                    <td class="py-1.5 pr-3 text-gray-900 dark:text-white">{d.country || '—'}</td>
                    <td class="py-1.5 text-gray-600 dark:text-gray-300">{cleanStrain(d.strain)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
            {#if detections.length > 10}
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">+ {detections.length - 10} more (see map)</p>
            {/if}
          {:else}
            <p class="text-gray-500 dark:text-gray-400 text-sm">
              {t('species_full.no_detections_note')} <a href="#/map" class="text-blue-600 dark:text-blue-400 hover:underline">{t('species_full.the.map')}</a> {t('species_full.no_detections_note2')}
            </p>
          {/if}
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
          <h2 class="font-semibold text-gray-900 dark:text-white mb-3">{t('species_full.immune.gene.summary')}</h2>
          {#if summary}
            <div class="space-y-3">
              <div class="flex gap-2">
                <div class="flex-1 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-center">
                  <div class="text-2xl font-bold text-green-700 dark:text-green-300">{summary.full}</div>
                  <div class="text-xs text-green-700 dark:text-green-400">{t('lib_components_species_SpeciesFullPage.present')}</div>
                </div>
                <div class="flex-1 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-center">
                  <div class="text-2xl font-bold text-amber-700 dark:text-amber-300">{summary.fragment}</div>
                  <div class="text-xs text-amber-700 dark:text-amber-400">{t('lib_components_species_SpeciesFullPage.fragment')}</div>
                </div>
                <div class="flex-1 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-center">
                  <div class="text-2xl font-bold text-red-700 dark:text-red-300">{summary.not_found}</div>
                  <div class="text-xs text-red-600 dark:text-red-400">{t('lib_components_species_SpeciesFullPage.absent')}</div>
                </div>
              </div>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                {summary.total_genes_searched} immune genes searched against this genome.
                <button class="text-blue-600 dark:text-blue-400 hover:underline" onclick={() => setSection('genes')}>
                  {t('btn.view.all.genes')}
                </button>
              </p>
              {#if summary.high_absences?.length > 0}
                <p class="text-sm text-amber-700 dark:text-amber-300">
                  Notable absences (high-importance): {summary.high_absences.slice(0, 6).join(', ')}{summary.high_absences.length > 6 ? '…' : ''}
                </p>
              {/if}
            </div>
          {:else if !species?.has_genome}
            <p class="text-gray-500 dark:text-gray-400 text-sm">
              {t('species.no_genome_yet')}
            </p>
          {:else if !summary}
            <p class="text-gray-500 dark:text-gray-400 text-sm animate-pulse">{t('common.loading')}</p>
          {/if}
        </div>
      </div>
    {:else if section === 'genome'}
      <div class="space-y-4">
        {#if assembly}
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 space-y-4">
            <div class="flex items-center justify-between">
              <h3 class="font-semibold text-gray-900 dark:text-white">{t('species_full.ncbi.assembly')}</h3>
              <a
                href="https://www.ncbi.nlm.nih.gov/datasets/genome/{assembly.accession}"
                target="_blank" rel="noopener"
                class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >{assembly.accession} ↗</a>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{t('species_full.level')}</div>
                <div class="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1.5">
                  {#if assembly.assembly_level}
                    {@const levelInfo = getAssemblyLevelInfo(assembly.assembly_level)}
                    <span class="px-1.5 py-0.5 rounded {levelInfo.color === 'green' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : levelInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">{assembly.assembly_level}</span>
                  {:else}—{/if}
                </div>
              </div>
              <div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{t('species_full.contig.n50')}</div>
                <div class="text-sm font-medium text-gray-900 dark:text-white">{formatN50(assembly.contig_n50)}</div>
              </div>
              <div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{t('species_full.scaffold.n50')}</div>
                <div class="text-sm font-medium text-gray-900 dark:text-white">{formatN50(assembly.scaffold_n50)}</div>
              </div>
              <div>
                <div class="text-xs text-gray-500 dark:text-gray-400">{t('species_full.total.length')}</div>
                <div class="text-sm font-medium text-gray-900 dark:text-white">{formatNumber(Number(assembly.total_length || 0))} bp</div>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 text-xs">
              {#if assembly.is_representative}
                <span class="px-2 py-1 rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">★ Representative assembly</span>
              {/if}
              {#if assembly.annotation_status}
                <span class="px-2 py-1 rounded-full bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300">Annotated — {assembly.annotation_status}</span>
              {:else}
                <span class="px-2 py-1 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">{t('species_full.no.ncbi.annotation.gene')}</span>
              {/if}
            </div>
          </div>
        {:else}
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 text-sm text-gray-500 dark:text-gray-400">
            {t('species.no.assembly') || 'No NCBI genome assembly for this species.'}
          </div>
        {/if}
        {#if summary}
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <h3 class="font-semibold text-gray-900 dark:text-white mb-2">{t('species_full.presence.search.on.this')}</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {summary.total_genes_searched} panel genes searched · {summary.full} present ·
              {summary.fragment} fragment · {summary.not_found} absent.
              <button class="text-blue-600 dark:text-blue-400 hover:underline" onclick={() => { setSection('genes'); loadFullPresence(); }}>{t('species_full.view.all.genes')}</button>
            </p>
          </div>
        {/if}
      </div>
    {:else if section === 'genes'}
      <!-- Gene panel -->
      {#if genePanel && summary && summary.total_genes_searched > 0}
        <div class="space-y-4">
          <!-- Bird's-eye strip: the eight genes that matter most, at a glance -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="flex items-center justify-between mb-3">
              <h3 class="font-semibold text-gray-900 dark:text-white">{t('species_full.birdseye.view')}</h3>
              <span class="text-xs text-gray-500 dark:text-gray-400">{t('species_full.the.headline.antiviral.genes')}</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {#each birdseye as g}
                <a href="#/genes/{g.sym}" class="p-2.5 rounded-lg border text-center transition-shadow hover:shadow-md {g.status === 'FULL'
                  ? 'border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20'
                  : g.status === 'FRAGMENT'
                    ? 'border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20'
                    : 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-900/20'}">
                  <div class="text-lg leading-none">{g.status === 'FULL' ? '✓' : g.status === 'FRAGMENT' ? '~' : '✗'}</div>
                  <div class="font-mono text-xs font-semibold text-gray-900 dark:text-white mt-1">{g.name || g.sym}</div>
                  {#if g.fn}
                    <div class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">{g.fn}</div>
                  {/if}
                </a>
              {/each}
            </div>
            {#if stripVerdict}
              {@const sv = stripVerdict}
              {#if sv.missingCritical.length > 0}
                <p class="mt-3 text-sm text-red-600 dark:text-red-400">
                  ⚠ Missing critical genes: {sv.missingCritical.map(g => g.sym).join(', ')}
                  {#if sv.missingHigh.length > 0}
                    · also missing high-importance: {sv.missingHigh.map(g => g.sym).join(', ')}
                  {/if}
                </p>
              {:else if sv.missingHigh.length > 0}
                <p class="mt-3 text-sm text-amber-700 dark:text-amber-400">
                  ✓ All critical genes present — but missing high-importance: {sv.missingHigh.map(g => g.sym).join(', ')}
                  {#if sv.frags.length > 0}
                    · fragments: {sv.frags.map(g => g.sym).join(', ')}
                  {/if}
                </p>
              {:else}
                <p class="mt-3 text-sm text-green-700 dark:text-green-400">
                  ✓ All headline antiviral genes present ({summary.full} of {summary.total_genes_searched} searched genes found)
                </p>
              {/if}
            {/if}
            {#if recoveredCount > 0}
              <p class="mt-1.5 text-sm text-violet-600 dark:text-violet-400">
                ✨ {recoveredCount} genes missing from this genome's annotation but recovered by our search — <button class="underline" onclick={() => { geneView = 'detailed'; statusFilter = 'FULL'; }}>{t('species_full.see.how.we.know')}</button>
              </p>
            {/if}
          </div>

          <!-- View toggle + controls -->
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex flex-wrap gap-3 items-center">
            <div class="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
              <button
                class="px-3 py-2 text-sm font-medium {geneView === 'compact' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300'}"
                onclick={() => geneView = 'compact'}
              >{t('lib_components_species_SpeciesFullPage.compact')}</button>
              <button
                class="px-3 py-2 text-sm font-medium {geneView === 'detailed' ? 'bg-blue-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300'}"
                onclick={() => geneView = 'detailed'}
              >{t('species_full.detailed.list')}</button>
            </div>
            <input
              type="text"
              placeholder={t('search.placeholder.genes.example') || 'Search genes (e.g. DDX58, TLR, interferon)…'}
              bind:value={geneSearch}
              class="flex-1 min-w-[180px] px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select bind:value={statusFilter} class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
              <option value="all">{t('species_full.all.statuses')}</option>
              <option value="FULL">✓ Present ({summary.full})</option>
              <option value="FRAGMENT">~ Fragment ({summary.fragment})</option>
              <option value="NOT_FOUND">✗ Absent ({summary.not_found})</option>
            </select>
            <select bind:value={importanceFilter} class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
              <option value="all">{t('species_full.all.importance')}</option>
              <option value="critical">● Critical</option>
              <option value="high">◐ High</option>
              <option value="standard">○ Standard</option>
            </select>
            <span class="text-sm text-gray-500 dark:text-gray-400">{filteredGenes.length} of {Object.keys(genePanel).length}</span>
          </div>

          <!-- Legend -->
          <div class="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap gap-4">
            <span>{t('species.legend_present_full')}</span>
            <span>{t('species.legend_fragment')}</span>
            <span>{t('species.legend_absent')}</span>
            <span>{t('species.legend_critical_tied')}</span>
            <span>{t('species.speciesfullpage.high.strong.literature.evidence') || '◐ high — strong literature evidence'}</span>
          </div>

          {#if geneView === 'compact'}
            <!-- Compact grid -->
            {#if filteredGenes.length === 0}
              <p class="text-center py-8 text-gray-500 dark:text-gray-400">{t('species_full.no.genes.match.your')}</p>
            {:else}
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {#each filteredGenes as [sym, g]}
                  {@const mi = methodInfo(g.level, species?.has_annotation === true)}
                  <a
                    href="#/genes/{sym}"
                    class="block p-2.5 rounded-lg border {statusColor[g.status]} hover:shadow-md transition-shadow"
                    title={(mi ? ((t('method.tip.' + mi.code + (species?.has_annotation === true ? 'a' : '')) || mi.tip) + ' · ') : '') + (genePresence.gene_catalogue?.[sym]?.function || sym)}
                  >
                    <div class="flex items-center justify-between gap-1">
                      <span class="font-mono text-xs font-semibold truncate">{sym}</span>
                      <span class="text-xs">{statusIcon[g.status]}{mi?.icon === '✨' ? '✨' : ''}</span>
                    </div>
                    <div class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                      {genePresence.gene_catalogue?.[sym]?.name || sym}
                    </div>
                    {#if g.importance !== 'standard'}
                      <span class="text-[11px] {g.importance === 'critical' ? 'text-red-600' : 'text-amber-700 dark:text-amber-400'} font-medium">
                        {g.importance === 'critical' ? '● critical' : '◐ high'}
                      </span>
                    {/if}
                  </a>
                {/each}
              </div>
            {/if}
          {:else}
            <!-- Detailed list view -->
            {#if filteredGenes.length === 0}
              <p class="text-center py-8 text-gray-500 dark:text-gray-400">{t('species_full.no.genes.match.your')}</p>
            {:else}
              <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-gray-200 dark:border-gray-700 text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                      <th class="py-2.5 px-3">{t('lib_components_species_SpeciesFullPage.gene')}</th>
                      <th class="py-2.5 px-3">{t('lib_components_genes_GeneFullPage.function')}</th>
                      <th class="py-2.5 px-3 w-20">{t('lib_components_species_SpeciesFullPage.status')}</th>
                      <th class="py-2.5 px-3 w-32">{t('species_full.how.we.know')}</th>
                      <th class="py-2.5 px-3 w-20">{t('lib_components_species_SpeciesFullPage.role')}</th>
                      <th class="py-2.5 px-3 w-10"></th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                    {#each filteredGenes as [sym, g]}
                      {@const cat = genePresence.gene_catalogue?.[sym] || {}}
                      {@const mi = methodInfo(g.level, species?.has_annotation === true)}
                      <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/40">
                        <td class="py-2 px-3 align-top">
                          <a href="#/genes/{sym}" class="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline">{sym}</a>
                          <div class="text-[11px] text-gray-500 dark:text-gray-400">{cat.name || ''}</div>
                        </td>
                        <td class="py-2 px-3 align-top text-gray-600 dark:text-gray-300 max-w-md">
                          {tc(`gene.${sym}.function`) || cat.function || cat.notes || '—'}
                          {#if g.status === 'NOT_FOUND' && cat.impact_if_absent}
                            <div class="text-[11px] text-red-600 dark:text-red-400 mt-1">
                              <strong>{t('species_full.if.lost')}</strong> {cat.impact_if_absent}
                            </div>
                          {/if}
                        </td>
                        <td class="py-2 px-3 align-top">
                          <span class="inline-block px-1.5 py-0.5 rounded text-xs {statusColor[g.status]}">{statusIcon[g.status]} {g.status === 'FULL' ? (t('presence.full') || 'Present') : g.status === 'FRAGMENT' ? (t('presence.fragment') || 'Fragment') : (t('presence.notfound') || 'Not found')}</span>
                        </td>
                        <td class="py-2 px-3 align-top">
                          {#if mi}
                            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[11px] {mi.cls}" title="{t('method.tip.' + mi.code + (species?.has_annotation === true ? 'a' : '')) || mi.tip} ({mi.code})">
                              <span>{mi.icon}</span>{mi.label}
                            </span>
                          {:else}
                            <span class="text-[11px] text-gray-500 dark:text-gray-400">—</span>
                          {/if}
                        </td>
                        <td class="py-2 px-3 align-top">
                          {#if g.importance === 'critical'}<span class="text-[11px] text-red-600 dark:text-red-400 font-medium">● critical</span>
                          {:else if g.importance === 'high'}<span class="text-[11px] text-amber-700 dark:text-amber-400 font-medium">◐ high</span>
                          {:else}<span class="text-[11px] text-gray-500 dark:text-gray-400">○ standard</span>{/if}
                        </td>
                        <td class="py-2 px-3 align-top">
                          <button
                            class="rounded px-1.5 py-1 {inspectGene === sym ? 'bg-blue-600 text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600'}"
                            title={t('species.speciesfullpage.inspect.raw.evidence.hsps') || 'Inspect raw evidence — HSPs, coordinates, genome browser'}
                            onclick={() => inspectGene = inspectGene === sym ? null : sym}
                          >
                            <svg class="w-3.5 h-3.5 {inspectGene === sym ? 'stroke-[2.5]' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                      {#if inspectGene === sym}
                        <tr>
                          <td colspan="6" class="p-2 bg-gray-50/50 dark:bg-gray-900/30">
                            <EvidenceDrawer gene={sym} species={decodeURIComponent(sciName)} call={g} level={g.level} />
                          </td>
                        </tr>
                      {/if}
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          {/if}
        </div>
      {:else}
        <div class="text-center py-12">
          <div class="text-4xl mb-3">🧬</div>
          <p class="text-gray-700 dark:text-gray-300 font-medium">{t('species_full.no.genome.available.gene')}</p>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-lg mx-auto">{t('species_full.no.genome.available.detail')}</p>
          {#if genomeRelatives?.length}
            <div class="mt-6 max-w-xl mx-auto">
              <h4 class="text-sm font-semibold text-gray-600 dark:text-gray-300 mb-2">{t('species_full.closest.relatives.with.genomes')}</h4>
              <div class="flex flex-wrap justify-center gap-2">
                {#each genomeRelatives as r (r.sci)}
                  <a href="#/species-full/{encodeURIComponent(r.sci)}?tab=genes"
                     class="px-3 py-1.5 rounded-full text-sm border transition-colors {r.has_genome
                       ? 'border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/30'
                       : 'border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-800 text-gray-500 dark:text-gray-400'}">
                    {r.com} {#if r.has_genome}<span class="ml-1" title={t('species.genome_available')}>🧬</span>{/if}
                  </a>
                {/each}
              </div>
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-3">{t('species_full.relatives.note')}</p>
            </div>
          {/if}
        </div>
      {/if}
    {:else if section === 'research'}
      {#if wikiSpecies}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
          <h2 class="font-semibold text-gray-900 dark:text-white mb-3">
            Research findings ({wikiSpecies.paper_count} papers)
          </h2>
          <p class="text-xs text-gray-400 dark:text-gray-500 mb-3">{t('species.research_scope_note')}</p>
          <ul class="space-y-2">
            {#each (wikiSpecies.key_findings || []).slice(0, 20) as f}
              <li class="text-sm text-gray-700 dark:text-gray-300 flex gap-2">
                <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">{f.value}</span>
                <span class="min-w-0">
                  {ft(f.fh) || f.finding}
                  <a href="#/papers/{f.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline" title={f.title}>[{f.paper_id}]</a>
                </span>
              </li>
            {/each}
          </ul>
          <a
            href="#/papers?species={encodeURIComponent(species?.scientific_name || sciName)}"
            class="inline-block mt-4 text-blue-600 dark:text-blue-400 hover:underline text-sm"
          >
            {t('species.view_all_papers')}
          </a>
        </div>
      {:else}
        <div class="text-center py-12 text-gray-500 dark:text-gray-400">
          <p>{t('species_full.no.research.findings.linked')}</p>
        </div>
      {/if}
    {/if}
  {/if}
</div>
