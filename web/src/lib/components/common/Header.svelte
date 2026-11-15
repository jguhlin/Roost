<script>
  import { onMount } from 'svelte';
  import { subscribe as routerSubscribe, navigate, routes } from '../../stores/router.js';
  import SearchBar from './SearchBar.svelte';
  import ChatWidget from './ChatWidget.svelte';

  // Current page from router
  let currentPage = $state('home');

  onMount(() => {
    return routerSubscribe(route => {
      currentPage = route.page;
    });
  });

  const navItems = $derived([
    { id: 'model', label: t('nav.model'), icon: 'link' },
    { id: 'vaccines', label: t('nav.vaccines'), icon: 'dna' },
    { id: 'species', label: t('nav.species'), icon: 'species' },
    { id: 'phylogeny', label: t('nav.phylogeny'), icon: 'tree' },
    { id: 'genes', label: t('nav.genes'), icon: 'dna' },
    { id: 'synteny', label: t('nav.synteny'), icon: 'dna' },
    { id: 'compare', label: t('nav.compare'), icon: 'species' },
    { id: 'blast', label: t('nav.blast'), icon: 'dna' },
    { id: 'clade', label: t('nav.clade'), icon: 'mutation' },
    { id: 'mutations', label: t('nav.mutations'), icon: 'mutation' },
    { id: 'genomes', label: t('nav.genomes'), icon: 'genome' },
    { id: 'map', label: t('nav.map'), icon: 'map' },
    { id: 'papers', label: t('nav.papers'), icon: 'paper' },
  ]);

  import { t, getLocale, setLocale, getSupportedLocales } from '../../stores/i18n.svelte.js';

  // Mobile menu state
  let mobileMenuOpen = $state(false);
</script>

<header class="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-40">
  <!-- Skip-to-content: first focusable element on the page; lives INSIDE the
       banner landmark so all content is landmark-contained (axe region rule) -->
  <a
    href="#main-content"
    class="skip-link"
    onclick={(e) => {
      // preventDefault: '#main-content' is not a router hash — focus manually
      e.preventDefault();
      document.getElementById('main-content')?.focus();
      document.getElementById('main-content')?.scrollIntoView();
    }}>{t('a11y.skip.to.content')}</a>
  <div class="max-w-7xl mx-auto px-4">
    <div class="flex items-center justify-between h-16">
      <!-- Logo -->
      <button onclick={() => routes.home()} class="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
        <span class="text-2xl">🪺</span>
        <span>{t('lib_components_common_Footer.roost')}</span>
      </button>

      <!-- Desktop Navigation -->
      <nav class="hidden lg:flex items-center gap-1" aria-label={t('a11y.primary.nav')}>
        {#each navItems as item}
          <button
            onclick={() => navigate(item.id)}
            class="px-3 py-2 rounded-md text-sm font-medium transition-colors {currentPage === item.id ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
          >
            {item.label}
          </button>
        {/each}
      </nav>

      <!-- Search + Mobile Menu Button -->
      <div class="flex items-center gap-4">
        <div class="hidden sm:block">
          <SearchBar compact={true} placeholder={t('search.placeholder.short') || 'Search...'} />
        </div>

        <!-- Mobile menu button -->
        <button
          onclick={() => mobileMenuOpen = !mobileMenuOpen}
          aria-label={t('a11y.menu')}
          aria-expanded={mobileMenuOpen}
          class="lg:hidden p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            {#if mobileMenuOpen}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            {:else}
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            {/if}
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile Search (always visible on small screens) -->
    <div class="sm:hidden pb-3">
      <SearchBar placeholder={t('search.placeholder.species.dots') || 'Search species...'} />
    </div>
  </div>

  <!-- Mobile Navigation Menu -->
  {#if mobileMenuOpen}
    <div class="lg:hidden border-t border-gray-200 dark:border-gray-700">
      <nav class="px-4 py-2 space-y-1" aria-label={t('a11y.mobile.nav')}>
        {#each navItems as item}
          <button
            onclick={() => { navigate(item.id); mobileMenuOpen = false; }}
            class="w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors {currentPage === item.id ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
          >
            {item.label}
          </button>
        {/each}
      </nav>
    </div>
  {/if}

  <!-- Language switcher (desktop, right of nav) — on-device chat icon
       sits to the LEFT of EN (D123, dev-build flag only) -->
  <div class="hidden md:flex items-center gap-1 ml-4">
    <ChatWidget />
    {#each getSupportedLocales() as loc (loc.code)}
      <button
        class="px-2 py-1 rounded text-xs font-medium {getLocale() === loc.code
          ? 'bg-blue-600 text-white'
          : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
        onclick={() => setLocale(loc.code)}
        title={loc.name}
      >{loc.code.toUpperCase()}</button>
    {/each}
  </div>
</header>
