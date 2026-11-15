<script>
  /**
   * GeneProfile — rich LLM-enriched gene profile (D92 Phase 4).
   * Renders overview, function, species differences, tiered key findings
   * (⭐ core / 📊 mentioned), strain interactions, and cross-study patterns.
   * All findings cite papers by ID with links to the papers page.
   */
  import { onMount } from 'svelte';
  import { t, gpt } from '../../../lib/stores/i18n.svelte.js';

  let { gene, onhasprofile } = $props();

  let profile = $state(null);
  let loading = $state(true);
  let showMentioned = $state(false);
  let expandedPapers = $state(new Set());

  // Expose to parent so it can hide the old curated sections


  onMount(async () => {
    try {
      // gene profiles are internal data; served via the public data dir
      const r = await fetch(`data/gene_profiles/${gene}.json`);
      if (r.ok) {
        profile = await r.json();
      }
    } catch { /* no profile yet */ }
    loading = false;
    if (onhasprofile) onhasprofile(!!profile);
  });

  // Split findings into tiers
  let coreFindings = $derived(
    (profile?.key_findings || []).filter(f => f.tier === 'core'));
  let mentionedFindings = $derived(
    (profile?.key_findings || []).filter(f => f.tier !== 'core'));

  let directionColor = (dir) => {
    if (!dir) return 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300';
    if (dir.includes('protective') || dir.includes('antiviral') || dir.includes('upregul'))
      return 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300';
    if (dir.includes('proviral') || dir.includes('required') || dir.includes('downregul'))
      return 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300';
    return 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300';
  };
</script>

{#if loading}
  <div class="animate-pulse bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
    <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
  </div>
{:else if profile}
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-5" data-testid="gene-profile">

    <!-- Overview -->
    {#if profile.overview}
      <div>
        <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-blue-600 dark:text-blue-400 mb-2">
          {t('gene_profile.overview')}
        </h3>
        <p class="text-sm leading-6 text-gray-700 dark:text-gray-300">
          {gpt(profile.overview, profile._h?.overview)}
        </p>
      </div>
    {/if}

    <!-- Function -->
    {#if profile.function}
      <div>
        <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400 mb-2">
          {t('gene_profile.function')}
        </h3>
        <p class="text-sm leading-6 text-gray-600 dark:text-gray-400">
          {gpt(profile.function, profile._h?.function)}
        </p>
      </div>
    {/if}

    <!-- Species Differences -->
    {#if profile.species_differences}
      <div class="border-l-4 border-emerald-400 pl-4" data-testid="species-differences">
        <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-emerald-600 dark:text-emerald-400 mb-2">
          {t('genes.species_differences')}
        </h3>
        <p class="text-sm leading-6 text-gray-700 dark:text-gray-300">
          {gpt(profile.species_differences, profile._h?.species_differences)}
        </p>
      </div>
    {/if}

    <!-- Key Findings: Core (⭐) -->
    {#if coreFindings.length}
      <div>
        <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400 mb-3">
          {t('genes.key_findings_core')} <span class="text-amber-700 dark:text-amber-400">⭐</span> {t('genes.paren_count', { n: coreFindings.length })}
        </h3>
        <div class="space-y-3">
          {#each coreFindings as finding, i}
            <div class="flex items-start gap-3 p-3 rounded-lg bg-amber-50/50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/30">
              <span class="text-amber-700 dark:text-amber-400 text-lg leading-none mt-0.5">⭐</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{gpt(finding.text, finding._h)}</p>
                <div class="mt-1.5 flex items-center gap-2 flex-wrap">
                  {#if finding.direction}
                    <span class="px-1.5 py-0.5 text-[10px] font-semibold rounded-full {directionColor(finding.direction)}">
                      {finding.direction}
                    </span>
                  {/if}
                  {#if finding.paper_id}
                    <a href="#/papers/{finding.paper_id}"
                      class="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline">
                      {finding.paper_id}
                    </a>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Key Findings: Mentioned/Screen (📊) -->
    {#if mentionedFindings.length}
      <div>
        <button
          class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
          onclick={() => showMentioned = !showMentioned}
        >
          <span>{t('genes.screen_mentions')} <span class="text-violet-500">📊</span> {t('genes.paren_count', { n: mentionedFindings.length })}</span>
          <svg class="w-3 h-3 transition-transform {showMentioned ? 'rotate-180' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m6 9 6 6 6-6"/>
          </svg>
        </button>
        {#if showMentioned}
          <div class="mt-3 space-y-2">
            <p class="text-xs text-gray-500 dark:text-gray-400 italic mb-2">
              {t('gene.profile.screens') || 'Gene appears in broader screens/tables — cross-study patterns may reveal signals that no single paper focused on.'}
            </p>
            {#each mentionedFindings as finding}
              <div class="flex items-start gap-3 p-2.5 rounded-lg bg-violet-50/30 dark:bg-violet-900/10 border border-violet-100 dark:border-violet-900/20">
                <span class="text-violet-400 text-sm leading-none mt-1">📊</span>
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">{finding.text}</p>
                  <div class="mt-1 flex items-center gap-2">
                    {#if finding.direction}
                      <span class="px-1.5 py-0.5 text-[9px] font-semibold rounded-full {directionColor(finding.direction)}">
                        {finding.direction}
                      </span>
                    {/if}
                    {#if finding.paper_id}
                      <a href="#/papers/{finding.paper_id}"
                        class="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline">
                        {finding.paper_id}
                      </a>
                    {/if}
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <!-- Cross-Study Patterns -->
    {#if profile.cross_study_patterns}
      <div class="p-3 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-100 dark:border-cyan-900/30" data-testid="cross-study-patterns">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-cyan-500">🔗</span>
          <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-cyan-700 dark:text-cyan-400">
            {t('genes.cross_study_pattern')}
          </h3>
        </div>
        <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          {gpt(profile.cross_study_patterns, profile._h?.cross_study_patterns)}
        </p>
      </div>
    {/if}

    <!-- Strain Interactions -->
    {#if profile.strain_interactions?.length}
      <div>
        <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-amber-700 dark:text-amber-400 mb-3">
          Strain-Specific Effects
        </h3>
        <div class="space-y-2">
          {#each profile.strain_interactions as si}
            <div class="p-2.5 rounded-lg bg-amber-50/50 dark:bg-amber-900/10 border border-amber-100 dark:border-amber-900/30">
              <p class="text-xs text-gray-700 dark:text-gray-300">{si.text || si.description || si}</p>
              {#if si.paper_id}
                <a href="#/papers/{si.paper_id}"
                  class="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline mt-1 inline-block">
                  {si.paper_id}
                </a>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Clinical Relevance -->
    {#if profile.clinical_relevance}
      <div class="border-l-4 border-blue-400 pl-4">
        <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-blue-600 dark:text-blue-400 mb-2">
          Clinical Relevance
        </h3>
        <p class="text-sm leading-6 text-gray-700 dark:text-gray-300">
          {gpt(profile.clinical_relevance, profile._h?.clinical_relevance)}
        </p>
      </div>
    {/if}

  </div>
{/if}
