<script>
  import { onMount } from 'svelte';
  import { initRouter, subscribe as routerSubscribe, getRoute } from './lib/stores/router.js';
  import { dbStore } from './lib/stores/db.js';
  import searchStore from './lib/stores/search.js';

  // Components
  import Header from './lib/components/common/Header.svelte';
  import Footer from './lib/components/common/Footer.svelte';
  import SpeciesDetail from './lib/components/species/SpeciesDetail.svelte';
  import SpeciesFullPage from './lib/components/species/SpeciesFullPage.svelte';

  // Pages
  import Home from './routes/Home.svelte';
  import Species from './routes/Species.svelte';
  import Phylogeny from './routes/Phylogeny.svelte';
  import Genes from './routes/Genes.svelte';
  import Orthogroups from './routes/Orthogroups.svelte';
  import Synteny from './routes/Synteny.svelte';
  import Compare from './routes/Compare.svelte';
  import Anp32 from './routes/Anp32.svelte';
  import Blast from './routes/Blast.svelte';
  import Contradictions from './routes/Contradictions.svelte';
  import Landscape from './routes/Landscape.svelte';
  import Numbers from './routes/Numbers.svelte';
  import Press from './routes/Press.svelte';
  import Research from './routes/Research.svelte';
  import Mutations from './routes/Mutations.svelte';
  import Genomes from './routes/Genomes.svelte';
  import Map from './routes/Map.svelte';
  import Papers from './routes/Papers.svelte';
  import Downloads from './routes/Downloads.svelte';
  import Resources from './routes/Resources.svelte';
  import Credits from './routes/Credits.svelte';
  import Methods from './routes/Methods.svelte';
  import Model from './routes/Model.svelte';
  import ModelCyto from './routes/ModelCyto.svelte';
  import SpreadCyto from './routes/SpreadCyto.svelte';
  import SpreadLayers from './routes/SpreadLayers.svelte';
  import Susceptibility from './routes/Susceptibility.svelte';
  import RegionRisk from './routes/RegionRisk.svelte';
  import Vaccines from './routes/Vaccines.svelte';
  import Clade from './routes/Clade.svelte';
  import Glossary from './routes/Glossary.svelte';
  import History from './routes/History.svelte';
import { t, getLocale, i18nRev } from './lib/stores/i18n.svelte.js';
import { announce, getLiveMessage } from './lib/stores/a11y.svelte.js';

  // Router state
  let currentPage = $state('home');
  let currentId = $state(null);
  let currentParams = $state({});

  // <main> element reference for focus management
  let mainEl;
  let lastPage = null;

  // Route → i18n title key (fallback: capitalized route id)
  const TITLE_KEYS = {
    home: 'nav.home',
    species: 'nav.species',
    'species-full': 'nav.species',
    phylogeny: 'nav.phylogeny',
    genes: 'nav.genes',
    orthogroups: 'nav.orthogroups',
    synteny: 'nav.synteny',
    compare: 'nav.compare',
    anp32: 'nav.anp32',
    blast: 'nav.blast',
    contradictions: 'nav.contradictions',
    landscape: 'nav.landscape',
    numbers: 'nav.numbers',
    research: 'nav.research',
    mutations: 'nav.mutations',
    genomes: 'nav.genomes',
    map: 'nav.map',
    history: 'nav.history',
    papers: 'nav.papers',
    downloads: 'nav.downloads',
    resources: 'nav.resources',
    credits: 'nav.credits',
    methods: 'nav.methods',
    model: 'nav.model',
    'model-cyto': 'nav.model',
    'spread-cyto': 'nav.model',
    'spread-layers': 'nav.spread_layers',
    'susceptibility': 'nav.susceptibility',
    'region-risk': 'nav.region_risk',
    clade: 'nav.clade',
    vaccines: 'nav.vaccines',
    glossary: 'nav.glossary'
  };

  function pageTitle(page) {
    if (page === 'home') return `Roost — ${t('home.title')}`;
    const key = TITLE_KEYS[page];
    const label = key ? t(key) : page.replace(/[-/]/g, ' ');
    const pretty = label ? label.charAt(0).toUpperCase() + label.slice(1) : 'Roost';
    return `${pretty} — Roost`;
  }

  // a11y: keep document.title in sync (route + locale), move focus to
  // <main> and announce page changes — SPA route swaps don't do this
  // natively, leaving screen-reader users at a stale focus point.
  $effect(() => {
    const page = currentPage;
    // re-run on locale / translation load so the title re-translates
    void getLocale();
    void i18nRev();

    document.title = pageTitle(page);

    const isFirst = lastPage === null;
    const changed = lastPage !== page;
    lastPage = page;

    if (changed && !isFirst) {
      announce(pageTitle(page));
      // wait for the {#key} remount to render the new page
      requestAnimationFrame(() => mainEl?.focus());
    }
  });

  // Species detail modal state
  let showSpeciesDetail = $state(false);
  let speciesDetailId = $state(null);

  onMount(() => {
    // Initialize router
    const cleanupRouter = initRouter();

    // Subscribe to route changes
    const unsubscribeRouter = routerSubscribe(route => {
      currentPage = route.page;
      currentId = route.id;
      currentParams = route.params;

      // Handle species detail as modal when ID is provided
      // (species-full/{sci_name} renders the full page instead)
      if (route.page === 'species' && route.id) {
        showSpeciesDetail = true;
        speciesDetailId = route.id;
      } else {
        showSpeciesDetail = false;
        speciesDetailId = null;
      }
    });

    // Preload search index
    searchStore.preload();

    // DuckDB is NOT eagerly initialised — each page that needs it
    // lazy-loads on first query. Saves ~8MB WASM on JSON-only pages.

    return () => {
      cleanupRouter();
      unsubscribeRouter();
    };
  });

  function closeSpeciesDetail() {
    showSpeciesDetail = false;
    speciesDetailId = null;
    // Navigate back to species list without ID
    window.location.hash = '#/species';
  }
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
  <!-- Screen-reader live region for async state announcements -->
  <div class="sr-only" role="status" aria-live="polite">{getLiveMessage()}</div>

  <Header />

  <main
    id="main-content"
    tabindex="-1"
    bind:this={mainEl}
    class="flex-1 max-w-7xl mx-auto px-4 py-8 w-full focus:outline-none"
  >
    <!-- Re-key the route tree on locale / translation-load so legacy children re-render -->
    <svelte:boundary onerror={(e) => console.error('[route boundary]', e)}>
    {#key getLocale() + ':' + i18nRev()}
    {#if currentPage === 'home'}
      <Home />
    {:else if currentPage === 'species'}
      <Species />
    {:else if currentPage === 'species-full'}
      <SpeciesFullPage sciName={decodeURIComponent(currentId || '')} />
    {:else if currentPage === 'phylogeny'}
      <Phylogeny />
    {:else if currentPage === 'genes'}
      <Genes />
    {:else if currentPage === 'orthogroups'}
      <Orthogroups og={currentId} />
    {:else if currentPage === 'synteny'}
      <Synteny block={currentId} />
    {:else if currentPage === 'compare'}
      <Compare />
    {:else if currentPage === 'anp32'}
      <Anp32 />
    {:else if currentPage === 'blast'}
      <Blast />
    {:else if currentPage === 'contradictions'}
      <Contradictions />
    {:else if currentPage === 'landscape'}
      <Landscape />
    {:else if currentPage === 'numbers'}
      <Numbers />
    {:else if currentPage === 'press'}
      <Press />
    {:else if currentPage === 'research'}
      <Research slug={decodeURIComponent(currentId || '')} />
    {:else if currentPage === 'mutations'}
      <Mutations />
    {:else if currentPage === 'genomes'}
      <Genomes />
    {:else if currentPage === 'map'}
      <Map />
    {:else if currentPage === 'history'}
      <History />
    {:else if currentPage === 'papers'}
      <Papers />
    {:else if currentPage === 'downloads'}
      <Downloads />
    {:else if currentPage === 'resources'}
      <Resources />
    {:else if currentPage === 'credits'}
      <Credits />
    {:else if currentPage === 'methods'}
      <Methods />
    {:else if currentPage === 'model'}
      <Model />
    {:else if currentPage === 'clade'}
      <Clade />
    {:else if currentPage === 'spread-cyto'}
      <SpreadCyto />
    {:else if currentPage === 'spread-layers'}
      <SpreadLayers />
    {:else if currentPage === 'susceptibility'}
      <Susceptibility slug={decodeURIComponent(currentId || '')} />
    {:else if currentPage === 'region-risk'}
      <RegionRisk />
    {:else if currentPage === 'model-cyto'}
      <ModelCyto />
    {:else if currentPage === 'vaccines'}
      <Vaccines />
    {:else if currentPage === 'glossary'}
      <Glossary />
    {:else}
      <!-- 404 -->
      <div class="text-center py-16">
        <h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">{t('app.notfound') || 'Page Not Found'}</h1>
        <p class="text-gray-600 dark:text-gray-300 mb-8">
          {t('app.404.desc') || 'The page you\'re looking for doesn\'t exist.'}
        </p>
        <a href="#/" class="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          {t('app.go.home')}
        </a>
      </div>
    {/if}
    {/key}
    </svelte:boundary>
  </main>

  <Footer />

  <!-- Species Detail Modal -->
  {#if showSpeciesDetail}
    <SpeciesDetail
      speciesId={speciesDetailId}
      onclose={closeSpeciesDetail}
    />
  {/if}
</div>
