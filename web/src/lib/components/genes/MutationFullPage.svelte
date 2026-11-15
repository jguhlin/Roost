<script>
  import { trackEvent } from '../../analytics.js';
  import { t, ft } from '../../../lib/stores/i18n.svelte.js';
  /**
   * Full-page mutation view — the "wiki page" for a mutation.
   * Props: mutation (wiki_mutations record).
   */
  import { navigate } from '../../stores/router.js';
  import ScopeTags from '../common/ScopeTags.svelte';

  let { mutation } = $props();
  // analytics: which mutations people open
  $effect(() => { if (mutation?.canonical) trackEvent('Mutation', 'view', mutation.canonical); });

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

  let avianSpecies = $derived((mutation.species_studied || []).filter(s => s.avian === true));
  let mammalSpecies = $derived((mutation.species_studied || []).filter(s => s.avian === false));
  let otherSpecies = $derived((mutation.species_studied || []).filter(s => s.avian == null));

  // D118 avian scope: effect-level host classes (mutation_host_claims ledger).
  // Mammalian-effect papers are out of scope — classified, quantified, and
  // hidden behind an explicit toggle.
  let showMammalEffects = $state(false);
  let effectHosts = $derived(mutation.effect_hosts || null);
  let mammalEffectPapers = $derived(
    (mutation.papers || []).filter(p => p.host_class === 'mammal').length
  );
  let visiblePapers = $derived(
    showMammalEffects
      ? mutation.papers
      : (mutation.papers || []).filter(p => p.host_class !== 'mammal')
  );
  const HOST_CLASS_STYLES = {
    aves: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
    mammal: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    both: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
    non_host: 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300',
    unknown: 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300',
  };
  const HOST_CLASS_LABELS = {
    aves: () => t('mutation_full.host.aves'),
    mammal: () => t('mutation_full.host.mammal'),
    both: () => t('mutation_full.host.both'),
    non_host: () => t('mutation_full.host.non_host'),
    unknown: () => t('mutation_full.host.unknown'),
  };
</script>

<div class="space-y-6">
  <!-- Back -->
  <button
    onclick={() => navigate('mutations')}
    class="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
  >
    ← Mutations
  </button>

  <!-- Header -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="text-3xl font-bold font-mono text-gray-900 dark:text-white">{mutation.canonical}</h1>
          <span class="px-2 py-0.5 text-xs rounded-full font-medium {proteinColors[mutation.protein] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
            {mutation.protein}
          </span>
          <span class="px-2 py-0.5 text-xs rounded-full font-medium {mutation.protein_is_host
            ? 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300'
            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'}">
            {mutation.protein_is_host ? (t('mutation.host.variant') || 'Host gene variant') : (t('mutation.viral') || 'Viral mutation')}
          </span>
          <ScopeTags scope={mutation.host_scope} avianPapers={mutation.avian_papers} mammalianPapers={mutation.mammalian_papers} />
        </div>
        {#if mutation.aliases.length > 0}
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Also written as: {mutation.aliases.join(', ')}
          </p>
        {/if}
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Documented in <span class="font-semibold text-gray-700 dark:text-gray-300">{mutation.paper_count}</span> papers
          ({mutation.avian_papers} avian · {mutation.mammalian_papers} mammalian)
          {#if mutation.host_scope_source === 'effect_claims'}
            <span class="text-xs" title={t('mutation_full.effect.scope.note')}>· {t('mutation_full.effect.host')}: {t('mutation_full.effect.level')}</span>
          {/if}
        </p>
      </div>
      <button
        onclick={() => navigate('genes', mutation.protein)}
        class="px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50"
      >
        {mutation.protein} gene page →
      </button>
    </div>

    {#if mutation.papers[0]?.effect}
      <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 mt-4">
        <h2 class="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-1">{t('lib_components_genes_MutationFullPage.effect')}</h2>
        <p class="text-sm text-blue-700 dark:text-blue-400">{ft(mutation.papers[0].eh) || mutation.papers[0].effect}</p>
        <p class="text-xs text-blue-600/70 dark:text-blue-400/70 mt-1">
          From {mutation.papers[0].paper_id} ({mutation.papers[0].year ?? ''})
        </p>
      </div>
    {/if}
  </div>

  <div class="grid lg:grid-cols-2 gap-6 items-start">
    <!-- Left: key numbers + papers -->
    <div class="space-y-6">
      {#if mutation.key_findings?.length > 0}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide">{t('mutation_full.key.numbers')}</h2>
          <div class="space-y-2">
            {#each mutation.key_findings as f}
              <div class="flex items-start gap-2 text-sm">
                <span class="flex-shrink-0 px-1.5 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                  {f.value}
                </span>
                <span class="text-gray-600 dark:text-gray-400 min-w-0">
                  {f.finding}
                  <a href="#/papers/{f.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline" title={f.title}>[{f.paper_id}, {f.year ?? ''}]</a>
                </span>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center justify-between gap-2 mb-3">
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
            Papers ({mutation.paper_count})
          </h2>
          {#if mammalEffectPapers > 0}
            <button
              onclick={() => showMammalEffects = !showMammalEffects}
              class="text-xs px-2 py-1 rounded-lg border transition-colors {showMammalEffects
                ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300 border-orange-300 dark:border-orange-700'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}"
              title={t('mutations_page.mammalian.out.of.scope')}
            >
              {showMammalEffects
                ? t('mutation_full.hide.mammalian.effects')
                : `${t('mutation_full.show.mammalian.effects')} (${mammalEffectPapers})`}
            </button>
          {/if}
        </div>
        {#if effectHosts}
          <div class="flex flex-wrap gap-1.5 mb-3 text-xs">
            {#each Object.entries(effectHosts).filter(([, n]) => n > 0) as [cls, n]}
              <span class="px-2 py-0.5 rounded-full font-medium {HOST_CLASS_STYLES[cls] || HOST_CLASS_STYLES.unknown}">
                {(HOST_CLASS_LABELS[cls] || HOST_CLASS_LABELS.unknown)()}: {n}
              </span>
            {/each}
          </div>
        {/if}
        <div class="space-y-3 max-h-[32rem] overflow-y-auto pr-1">
          {#each visiblePapers as paper}
            <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-sm">
              <div class="flex items-start justify-between gap-2">
                <a href="#/papers/{paper.paper_id}" class="font-medium text-blue-600 dark:text-blue-400 hover:underline line-clamp-2">
                  {paper.title || paper.paper_id}
                </a>
                <span class="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400">{paper.year ?? ''}</span>
              </div>
              {#if paper.journal}
                <p class="text-xs text-gray-500 dark:text-gray-400 italic mt-0.5">{paper.journal}</p>
              {/if}
              {#if paper.host_class}
                <span
                  class="inline-block mt-1.5 px-2 py-0.5 text-xs rounded-full font-medium {HOST_CLASS_STYLES[paper.host_class] || HOST_CLASS_STYLES.unknown}"
                  title={t('mutation_full.effect.host')}
                >
                  {(HOST_CLASS_LABELS[paper.host_class] || HOST_CLASS_LABELS.unknown)()}{paper.host_species ? ' · ' + paper.host_species : ''}
                </span>
              {/if}
              {#if paper.effect}
                <p class="text-xs text-gray-600 dark:text-gray-400 mt-2 border-l-2 border-gray-300 dark:border-gray-600 pl-2">
                  {ft(paper.eh) || paper.effect}
                </p>
              {/if}
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">{paper.paper_id}</p>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Right: host context -->
    <div class="space-y-6">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide">{t('mutation_full.host.context')}</h2>

        {#if avianSpecies.length > 0}
          <div class="mb-4">
            <p class="text-xs font-semibold text-sky-700 dark:text-sky-300 mb-1.5">🪶 Avian hosts</p>
            <div class="flex flex-wrap gap-1.5">
              {#each avianSpecies as s}
                <a
                  href="#/species/{encodeURIComponent(s.scientific || s.name)}"
                  class="text-xs px-2 py-1 rounded bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300 hover:underline hover:bg-sky-200 dark:hover:bg-sky-900/50"
                  title={`${s.papers} ${s.papers !== 1 ? (t('common.papers.plural') || 'papers') : (t('common.paper.singular') || 'paper')}${s.scientific ? ' — ' + s.scientific : ''}`}
                >
                  {s.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}

        {#if mammalSpecies.length > 0}
          <div class="mb-4">
            <p class="text-xs font-semibold text-orange-700 dark:text-orange-300 mb-1.5">🐁 Mammalian hosts</p>
            <div class="flex flex-wrap gap-1.5">
              {#each mammalSpecies as s}
                <a
                  href="#/species/{encodeURIComponent(s.scientific || s.name)}"
                  class="text-xs px-2 py-1 rounded bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 hover:underline hover:bg-orange-200 dark:hover:bg-orange-900/50"
                  title={`${s.papers} ${s.papers !== 1 ? (t('common.papers.plural') || 'papers') : (t('common.paper.singular') || 'paper')}${s.scientific ? ' — ' + s.scientific : ''}`}
                >
                  {s.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}

        {#if otherSpecies.length > 0}
          <div>
            <p class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">{t('mutation_full.other.unclassified')}</p>
            <div class="flex flex-wrap gap-1.5">
              {#each otherSpecies as s}
                <a
                  href="#/species/{encodeURIComponent(s.scientific || s.name)}"
                  class="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:underline"
                  title={t('genes.mutationfullpage.papers.paper.papers.host', { n: s.papers })}
                >
                  {s.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}

        {#if mutation.species_studied?.length === 0}
          <p class="text-sm text-gray-500 dark:text-gray-400">
            {t('mutation.no.host') || 'No host species recorded for this mutation — evidence is viral-only or in vitro.'}
          </p>
        {/if}
      </div>
    </div>
  </div>
</div>
