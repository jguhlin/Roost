<script>
  import { t, ft } from '../lib/stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { navigate, subscribe as routerSubscribe, getRoute, updateParams } from '../lib/stores/router.js';
  import MutationFullPage from '../lib/components/genes/MutationFullPage.svelte';
  import ScopeTags from '../lib/components/common/ScopeTags.svelte';

  let mutations = $state({});
  let loading = $state(true);
  let error = $state(null);
  let selected = $state(null);
  let searchQuery = $state('');
  let proteinFilter = $state('');
  let kindFilter = $state('');
  let scopeFilter = $state('');
  let sortBy = $state('scope'); // 'scope' = avian first, 'evidence' = paper count
  // D118 avian scope: mutations whose effects are mammalian-only are outside
  // this site's mission — classified and quantified, hidden by default.
  let showMammalOnly = $state(false);

  // Full-page mutation (#/mutations/PB2-E627K) vs browser view
  let fullPageMutation = $state(null);

  const scopePriority = { avian: 0, both: 1, mammalian: 2, viral: 3 };

  // --- URL state (#/mutations?q=E627K&protein=PB2&kind=viral&scope=avian&
  //     sort=evidence&mut=PB2-E627K) — shareable views, same pattern as the
  //     Species/Genes/Phylogeny pages. Absent param = its default.
  let urlSyncReady = $state(false);

  const applyParams = (p = {}) => {
    searchQuery = p.q || '';
    proteinFilter = p.protein || '';
    kindFilter = ['host', 'viral'].includes(p.kind) ? p.kind : '';
    scopeFilter = ['avian', 'both', 'mammalian', 'viral'].includes(p.scope) ? p.scope : '';
    sortBy = p.sort === 'evidence' ? 'evidence' : 'scope';
    showMammalOnly = p.oos === '1';
    selected = p.mut && mutations[p.mut] ? mutations[p.mut] : null;
  };

  const applyRoute = route => {
    if (route.page === 'mutations') {
      if (route.id && mutations[route.id]) {
        fullPageMutation = mutations[route.id];
        selected = mutations[route.id];
      } else if (!route.id) {
        fullPageMutation = null;
        if (urlSyncReady) applyParams(route.params || {});
      }
    }
  };

  // state → URL (echo-guarded: applyParams no-ops when values already match)
  $effect(() => {
    void searchQuery; void proteinFilter; void kindFilter;
    void scopeFilter; void sortBy; void selected; void showMammalOnly;
    if (loading || fullPageMutation || !urlSyncReady) return;
    updateParams({
      q: searchQuery || null,
      protein: proteinFilter || null,
      kind: kindFilter || null,
      scope: scopeFilter || null,
      sort: sortBy !== 'scope' ? sortBy : null,
      oos: showMammalOnly ? '1' : null,
      mut: selected?.canonical || null,
    });
  });

  onMount(async () => {
    try {
      const response = await fetch('data/wiki_mutations.json');
      if (!response.ok) throw new Error(`Failed to load mutations (${response.status})`);
      const data = await response.json();
      mutations = data.mutations || {};
      loading = false;
      // Data may arrive after the route fired — re-check once loaded, then
      // restore shareable state synchronously (before the subscription's
      // late initial fire could clobber it — the Genes-page lesson).
      applyRoute(getRoute());
      applyParams(getRoute()?.params || {});
      urlSyncReady = true;
    } catch (e) {
      error = e.message;
      loading = false;
    }

    return routerSubscribe(applyRoute);
  });

  let allMutations = $derived(Object.values(mutations));
  let mammalOnlyCount = $derived(
    allMutations.filter(m => (m.host_scope || 'unknown') === 'mammalian').length
  );
  const HOST_CLASS_STYLES = {
    aves: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
    mammal: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    both: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
    non_host: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
    unknown: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  };
  const HOST_CLASS_LABELS = {
    aves: () => t('mutation_full.host.aves'),
    mammal: () => t('mutation_full.host.mammal'),
    both: () => t('mutation_full.host.both'),
    non_host: () => t('mutation_full.host.non_host'),
    unknown: () => t('mutation_full.host.unknown'),
  };
  function hostChipClass(cls) {
    return HOST_CLASS_STYLES[cls] || HOST_CLASS_STYLES.unknown;
  }
  function hostChipLabel(cls, species) {
    const label = (HOST_CLASS_LABELS[cls] || HOST_CLASS_LABELS.unknown)();
    return species ? `${label} · ${species}` : label;
  }
  let proteins = $derived(
    [...new Set(allMutations.map(m => m.protein))].sort((a, b) =>
      (countFor(b) - countFor(a)) || a.localeCompare(b)
    )
  );

  function countFor(protein) {
    return allMutations.filter(m => m.protein === protein).length;
  }

  let filtered = $derived(allMutations
    .filter(m => {
      if (proteinFilter && m.protein !== proteinFilter) return false;
      if (kindFilter === 'viral' && m.protein_is_host) return false;
      if (kindFilter === 'host' && !m.protein_is_host) return false;
      if (scopeFilter && (m.host_scope || 'unknown') !== scopeFilter) return false;
      // D118: mammalian-only effect evidence is out of scope for an avian
      // host-genomics resource — hidden unless revealed or explicitly
      // filtered for. 'both' mutations keep avian rows visible.
      if (!showMammalOnly && scopeFilter !== 'mammalian' && (m.host_scope || 'unknown') === 'mammalian') return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          m.canonical.toLowerCase().includes(q) ||
          m.protein.toLowerCase().includes(q) ||
          m.aliases.some(a => a.toLowerCase().includes(q))
        );
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'scope') {
        const p = (scopePriority[a.host_scope] ?? 4) - (scopePriority[b.host_scope] ?? 4);
        if (p !== 0) return p;
      }
      return b.paper_count - a.paper_count;
    })
  );

  let selectedPapers = $derived(selected ? selected.papers : []);
  let latestEffect = $derived(
    selectedPapers.length > 0 && selectedPapers[0].effect
      ? (ft(selectedPapers[0].eh) || selectedPapers[0].effect)
      : null
  );

  const proteinColors = {
    'PB2': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    'PB1': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    'PA': 'bg-amber-100 text-amber-700 dark:text-amber-400 dark:bg-amber-900/30 dark:text-amber-300',
    'HA': 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
    'NA': 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300',
    'NP': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    'M1': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    'M2': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300',
    'NS1': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  };

  function proteinColor(protein) {
    return proteinColors[protein] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
  }
</script>

<svelte:head><title>{t('lib_components_genes_GeneFullPage.mutations') || 'Mutations'} — Roost</title></svelte:head>

{#if fullPageMutation}
  <!-- Full-page mutation view -->
  <MutationFullPage mutation={fullPageMutation} />
{:else}
  <!-- Mutation browser: list + slim card -->
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('lib_components_genes_GeneFullPage.mutations')}</h1>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        {#if loading}
          {t('mutations.loading') || 'Loading mutations...'}
        {:else}
          {allMutations.length} {t('mutations.intro') || 'mutations with documented effects in HPAI research — host adaptations, viral escape variants, and resistance markers, extracted from verified paper analyses.'}
          {t('mutations.intro2') || 'Avian-focused evidence is listed first.'}
        {/if}
      </p>
    </div>

    {#if error}
      <div class="bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 p-4 rounded-lg">
        Error loading mutations: {error}
      </div>
    {:else if loading}
      <div class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    {:else}
      <!-- Filters -->
      <div class="flex flex-wrap gap-3">
        <input
          type="text"
          bind:value={searchQuery}
          placeholder={t('search.placeholder.mutations') || 'Search mutations (e.g. E627K, PB2, H275Y)...'}
          class="flex-1 min-w-[14rem] px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div class="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden self-start">
          {#each [['', t('common.all') || 'All'], ['host', t('mutations.host.variants') || 'Host variants'], ['viral', t('mutation.viral') || 'Viral mutations']] as [val, label], i}
            <button
              onclick={() => kindFilter = val}
              class="px-3 py-2 text-sm font-medium transition-colors {kindFilter === val
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}
              {i > 0 ? 'border-l border-gray-300 dark:border-gray-600' : ''}"
            >
              {label}
            </button>
          {/each}
        </div>
        <select
          bind:value={scopeFilter}
          aria-label={t('tip.mutations.scope')}
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          title={t('tip.mutations.scope') || 'Filter by host scope of the supporting evidence'}
        >
          <option value="">{t('mutations_page.all.host.scopes')}</option>
          <option value="avian">{t('mutations_page.avian.only')}</option>
          <option value="both">{t('mutations_page.avian.mammalian')}</option>
          <option value="mammalian">{t('mutations_page.mammalian.only')}</option>
          <option value="viral">{t('mutations_page.viral.only')}</option>
        </select>
        <select
          bind:value={proteinFilter}
          aria-label={t('mutations_page.all.proteins')}
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
        >
          <option value="">{t('mutations_page.all.proteins')}</option>
          {#each proteins as protein}
            <option value={protein}>{protein} ({countFor(protein)})</option>
          {/each}
        </select>
        <select
          bind:value={sortBy}
          aria-label={t('tip.mutations.sort')}
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          title={t('tip.mutations.sort') || 'Sort order'}
        >
          <option value="scope">{t('mutations_page.sort.avian.first')}</option>
          <option value="evidence">{t('mutations_page.sort.most.evidence')}</option>
        </select>
        {#if mammalOnlyCount > 0}
          <button
            onclick={() => showMammalOnly = !showMammalOnly}
            class="px-3 py-2 text-sm rounded-lg border transition-colors {showMammalOnly
              ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300 border-orange-300 dark:border-orange-700'
              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}"
            title={t('mutations_page.mammalian.out.of.scope')}
          >
            {showMammalOnly
              ? t('mutations_page.hide.mammalian.only')
              : `${t('mutations_page.show.mammalian.only')} (${mammalOnlyCount})`}
          </button>
        {/if}
      </div>

      <div class="grid lg:grid-cols-3 gap-6">
        <!-- Mutation List -->
        <div class="lg:col-span-2 min-w-0">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
              <h2 class="font-semibold text-gray-900 dark:text-white">
                {filtered.length} mutation{filtered.length !== 1 ? 's' : ''}
              </h2>
            </div>
            <div class="divide-y divide-gray-100 dark:divide-gray-700 max-h-[calc(100vh-16rem)] overflow-y-auto">
              {#each filtered as mut (mut.canonical)}
                <button
                  onclick={() => selected = mut}
                  class="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors {selected?.canonical === mut.canonical ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2 min-w-0 flex-wrap">
                      <span class="font-mono font-semibold text-gray-900 dark:text-white">{mut.canonical}</span>
                      <span class="px-2 py-0.5 text-xs rounded-full font-medium {proteinColor(mut.protein)}">
                        {mut.protein}
                      </span>
                      <ScopeTags scope={mut.host_scope} avianPapers={mut.avian_papers} mammalianPapers={mut.mammalian_papers} />
                      {#if mut.protein_is_host}
                        <span class="px-2 py-0.5 text-xs rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">{t('routes_Mutations.host')}</span>
                      {/if}
                    </div>
                    <span class="flex-shrink-0 text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      {mut.paper_count} {mut.paper_count === 1 ? t('mutations.one_paper') : t('mutations.n_papers', {n: mut.paper_count})}
                    </span>
                  </div>
                  {#if mut.papers[0]?.effect}
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate min-w-0">
                      {ft(mut.papers[0].eh) || mut.papers[0].effect}
                    </p>
                  {/if}
                </button>
              {/each}
              {#if filtered.length === 0 && scopeFilter === 'mammalian'}
                <div class="p-6 text-center">
                  <div class="text-2xl mb-2">🔒</div>
                  <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('mutations.censored.title')}</div>
                  <p class="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">{t('mutations.censored.body')}</p>
                </div>
              {:else if filtered.length === 0}
                <div class="p-6 text-center text-gray-500 dark:text-gray-400">
                  {t('mutations.no.match') || 'No mutations match your filters.'}
                </div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Slim Mutation Card -->
        <div class="lg:col-span-1 min-w-0">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
            {#if selected}
              <div class="p-5">
                <div class="flex items-start justify-between gap-2 mb-2">
                  <h2 class="text-xl font-bold font-mono text-gray-900 dark:text-white">{selected.canonical}</h2>
                </div>
                <div class="flex flex-wrap items-center gap-1.5 mb-3">
                  <span class="px-2 py-0.5 text-xs rounded-full font-medium {proteinColor(selected.protein)}">
                    {selected.protein}
                  </span>
                  <ScopeTags scope={selected.host_scope} avianPapers={selected.avian_papers} mammalianPapers={selected.mammalian_papers} />
                  <span class="px-2 py-0.5 text-xs rounded-full {selected.protein_is_host
                    ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'}">
                    {selected.protein_is_host ? 'host variant' : 'viral'}
                  </span>
                </div>

                {#if latestEffect}
                  <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2.5">
                    <p class="text-xs text-blue-700 dark:text-blue-400 line-clamp-4">{latestEffect}</p>
                    {#if selected.papers[0]?.host_class}
                      <span class="inline-block mt-1.5 px-2 py-0.5 text-xs rounded-full font-medium {hostChipClass(selected.papers[0].host_class)}">
                        {t('mutation_full.effect.host')}: {hostChipLabel(selected.papers[0].host_class, selected.papers[0].host_species)}
                      </span>
                    {/if}
                  </div>
                {/if}

                <div class="flex flex-wrap gap-1.5 mt-3 text-xs">
                  <span class="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                    {selected.paper_count} papers
                  </span>
                  {#if selected.host_scope !== 'viral'}
                    <span class="px-2 py-0.5 rounded-full bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">
                      {selected.avian_papers} avian
                    </span>
                    <span class="px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300">
                      {selected.mammalian_papers} mammalian
                    </span>
                  {/if}
                  {#if selected.key_findings?.length > 0}
                    <span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                      {selected.key_findings.length} key numbers
                    </span>
                  {/if}
                </div>

                <div class="flex flex-wrap gap-2 mt-4">
                  <button
                    onclick={() => navigate('mutations', selected.canonical)}
                    class="flex-1 px-3 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-center"
                  >
                    {t('genes.open_full_page')}
                  </button>
                </div>
                <button
                  onclick={() => navigate('genes', selected.protein)}
                  class="w-full mt-2 text-center text-xs px-2 py-1.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50"
                >
                  View {selected.protein} gene page →
                </button>
              </div>
            {:else}
              <div class="p-6 text-center text-gray-500 dark:text-gray-400">
                <svg class="w-12 h-12 mx-auto mb-3 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                <p class="text-sm">{t('mutations_page.select.a.mutation.for')}</p>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}
