<script>
  /** Research landscape — synthesis, contradictions, gaps, open questions. */
  import { onMount } from 'svelte';
  import { t, ft } from '../lib/stores/i18n.svelte.js';

  let landscape = $state(null);
  let error = $state(null);
  let tab = $state('synthesis');   // synthesis | gaps | contradictions | questions
  let briefings = $state([]);
  let synthesis = $state(null);
  let contraLinks = $state(null);
  let media = $state({ figures: [], videos: [] });
  let bridges = $state(null);
  let bridgesError = $state(null);

  onMount(async () => {
    // data-vs-literature bridges (deterministic gaps) — first, so any later
    // hang can't starve it
    try {
      const r = await fetch(`data/data_lit_bridges.json?t=${Date.now()}`);
      if (r.ok) bridges = await r.json();
      else bridgesError = `HTTP ${r.status} on data_lit_bridges.json`;
    } catch (e) { bridgesError = String(e); }
    try {
      const r = await fetch(`data/research_landscape.json?t=${Date.now()}`);
      if (!r.ok) throw new Error('payload missing');
      landscape = await r.json();
    } catch {
      error = 'Research landscape data unavailable (run scripts/papers/build_aggregation.py).';
    }
    // auto-discover briefings
    try {
      const r = await fetch('data/research_briefings/index.json');
      if (r.ok) briefings = await r.json();
    } catch { /* no briefings yet */ }
    // cross-briefing synthesis (LLM theme cards)
    try {
      const r = await fetch(`data/research_synthesis.json?t=${Date.now()}`);
      if (r.ok) synthesis = await r.json();
    } catch { /* synthesis optional */ }
    // contradiction <-> briefing links
    try {
      const r = await fetch(`data/contradiction_briefing_links.json?t=${Date.now()}`);
      if (r.ok) contraLinks = await r.json();
    } catch { /* links optional */ }
    // figure/video registry (for media counts on briefing entries)
    try {
      const r = await fetch(`figures/index.json?t=${Date.now()}`);
      if (r.ok) {
        const idx = await r.json();
        media = { figures: idx.figures || [], videos: idx.videos || [] };
      }
    } catch { /* registry optional */ }
  });

  function mediaCount(slug) {
    const f = media.figures.filter((x) => x.page === slug).length;
    const v = media.videos.filter((x) => x.page === slug).length;
    return { f, v };
  }

  const latest = $derived({
    media: [...media.figures, ...media.videos]
      .filter((x) => x.published)
      .sort((a, b) => b.published.localeCompare(a.published))
      .slice(0, 5),
    briefings: [...(briefings || [])]
      .filter((b) => b.generated)
      .sort((a, b) => (b.generated || '').localeCompare(a.generated || ''))
      .slice(0, 3),
  });
</script>

<svelte:head><title>{t('landscape.page.title') || 'Research landscape'} — Roost</title></svelte:head>

<div class="max-w-5xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{t('landscape.page.title')}</h1>
  {#if landscape}
    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-4">
      Where the avian influenza literature is contested, incomplete, and open.
      Generated from {landscape.contradictions?.total || 0} adjudicated contradictions
      across the corpus.
    </p>

    <div class="flex gap-2 mb-4">
      {#each [['synthesis', '🧠 ' + t('landscape.chip.synthesis')], ['gaps', '🔍 ' + t('landscape.chip.gaps')], ['contradictions', '⚠ ' + t('landscape.chip.conflicts')], ['questions', '❓ ' + t('landscape.chip.open')]] as [v, label]}
      <button
          class="px-3 py-1 rounded-full text-xs font-medium {tab === v ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}"
          onclick={() => (tab = v)}>{label}</button>
      {/each}
    </div>

    <!-- Latest: newest briefings + media -->
    {#if latest.media.length || latest.briefings.length}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-6">
        <h2 class="text-sm font-bold text-gray-900 dark:text-white mb-2">🆕 Latest</h2>
        <div class="flex flex-wrap gap-2">
          {#each latest.briefings as b (b.slug)}
            <a href="#/research/{b.slug}" class="text-[11px] px-2 py-1 rounded-lg bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:underline">
              📄 {t('landscape.briefing.label')} · {new Date(b.generated).toLocaleDateString()} · {(ft(b.th) || b.title || '').slice(0, 46)}{(b.title?.length > 46 ? '…' : '')}
            </a>
          {/each}
          {#each latest.media as m (m.file)}
            <a href="#/research/{m.page}" class="text-[11px] px-2 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:underline">
              {m.kind === 'video' ? '🎬 video' : '📊 figure'} · {new Date(m.published).toLocaleDateString()} · {m.caption?.slice(0, 40) || m.file}{m.caption?.length > 40 ? '…' : ''}
            </a>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Research briefings (auto-discovered from research_briefings/*.json) -->
  {#if briefings?.length}
    <div class="mb-6">
      <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-3">{t('landscape.briefings')}</h2>
      <div class="space-y-2">
        {#each briefings as b (b.slug)}
          <a href="#/research/{b.slug}" class="block bg-white dark:bg-gray-800 rounded-lg shadow p-4 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{ft(b.th) || b.title}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{(ft(b.sh) || b.summary || '').slice(0, 120)}…</p>
              </div>
              <div class="flex gap-1 shrink-0 text-[10px]">
                {#if mediaCount(b.slug).f}
                  <span class="px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 font-semibold">📊 {mediaCount(b.slug).f}</span>
                {/if}
                {#if mediaCount(b.slug).v}
                  <span class="px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 font-semibold">🎬 {mediaCount(b.slug).v}</span>
                {/if}
                {#if contraLinks?.by_briefing?.[b.slug]?.length}
                  <span class="px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300 font-semibold">⚠ {contraLinks.by_briefing[b.slug].length}</span>
                {/if}
                {#if b.hypotheses?.length}
                  <span class="px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 font-semibold">{b.hypotheses.length} hypotheses</span>
                {/if}
                {#if b.research_plan?.length}
                  <span class="px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-semibold">{b.research_plan.length} studies</span>
                {/if}
              </div>
            </div>
          </a>
        {/each}
      </div>
    </div>
  {/if}

  {#if tab === 'synthesis'}
      {#if synthesis?.themes?.length}
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {synthesis.meta.n_themes} themes across {synthesis.meta.n_briefings} briefings — grouped by shared cited papers, written by the local model.
        </p>
        <div class="space-y-3">
          {#each synthesis.themes as theme (theme.id)}
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-semibold text-gray-900 dark:text-gray-100 text-sm">🧠 {theme.theme}</p>
                  <div class="flex flex-wrap gap-1 mt-1">
                    {#each theme.briefings as s}
                      <a href="#/research/{s}" class="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 hover:underline">{s.length > 34 ? s.slice(0, 34) + '…' : s}</a>
                    {/each}
                  </div>
                </div>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0
                  {t.confidence === 'high' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                  : t.confidence === 'low' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                  : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'}">{t.confidence}</span>
              </div>
              <div class="grid md:grid-cols-3 gap-3 mt-3 text-xs">
                <div>
                  <p class="font-semibold text-emerald-600 dark:text-emerald-400 mb-1">Consensus</p>
                  <ul class="space-y-1 text-gray-600 dark:text-gray-400">
                    {#each (t.consensus ?? []).slice(0, 3) as c}<li class="leading-snug">✓ {c}</li>{/each}
                  </ul>
                </div>
                <div>
                  <p class="font-semibold text-red-600 dark:text-red-400 mb-1">Conflicts</p>
                  <ul class="space-y-1 text-gray-600 dark:text-gray-400">
                    {#each (t.conflicts ?? []).slice(0, 3) as c}<li class="leading-snug">⚠ {c}</li>{/each}
                  </ul>
                </div>
                <div>
                  <p class="font-semibold text-blue-600 dark:text-blue-400 mb-1">{t('routes.landscape.still.open') || 'Still open'}</p>
                  <ul class="space-y-1 text-gray-600 dark:text-gray-400">
                    {#each (t.open_questions ?? []).slice(0, 3) as q}<li class="leading-snug">? {q}</li>{/each}
                  </ul>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-sm text-gray-500 dark:text-gray-400">{t('routes.landscape.no.synthesis.yet.run') || 'No synthesis yet — run'}<code class="text-xs">scripts/papers/synthesize_briefings.py</code>.</p>
      {/if}
    {:else if tab === 'gaps'}
      {#if bridgesError}
        <div class="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 text-xs rounded-lg p-3 mb-4">bridges: {bridgesError}</div>
      {/if}
      {#if bridges?.species}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-4">
          <h3 class="text-sm font-bold text-gray-900 dark:text-white mb-2">{t('routes.landscape.data.literature.checkable.gaps') || '🔗 Data ↔ literature — checkable gaps'}</h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
            {bridges.species.n_overlap} species appear in both the surveillance data and the literature;
            the joins below are deterministic (script: data_lit_bridges.py).
          </p>
          <div class="grid md:grid-cols-2 gap-3 text-xs">
            <div>
              <p class="font-semibold text-blue-600 dark:text-blue-400 mb-1">{t('routes.landscape.detected.constantly.unstudied.experimentally') || 'Detected constantly, unstudied experimentally'}</p>
              <ul class="space-y-1 text-gray-600 dark:text-gray-400">
                {#each bridges.species.data_no_literature.slice(0, 5) as r}
                  <li>• <span class="italic">{r.scientific_name}</span> — {r.det_records.toLocaleString()} detections, susceptibility {r.susceptibility_score.toFixed(1)}</li>
                {/each}
              </ul>
            </div>
            <div>
              <p class="font-semibold text-amber-700 dark:text-amber-400 mb-1">{t('routes.landscape.key.panel.genes.with') || 'Key panel genes with thin corpus evidence'}</p>
              <ul class="space-y-1 text-gray-600 dark:text-gray-400">
                {#each bridges.genes.key_gene_thin_evidence.slice(0, 5) as r}
                  <li>• <span class="font-mono">{r.gene}</span> — {r.n_papers} paper{r.n_papers === 1 ? '' : 's'}{r.function ? ` · ${r.function.slice(0, 60)}…` : ''}</li>
                {/each}
              </ul>
            </div>
          </div>
        </div>
      {/if}
      <div class="space-y-3">
        {#each landscape.gaps?.synthesized || [] as gap, i (i)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="font-medium text-gray-900 dark:text-gray-100 text-sm">{gap.title}</div>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0
                {gap.evidence === 'coverage' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                : gap.evidence === 'both' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'}">{gap.evidence}</span>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{gap.why}</p>
            {#if gap.study_needed}
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5 italic">→ {gap.study_needed}</p>
            {/if}
          </div>
        {/each}
      </div>
    {:else if tab === 'contradictions'}
      <div class="mb-4 text-xs text-gray-500 dark:text-gray-400">
        {landscape.contradictions?.real || 0} real ·
        {landscape.contradictions?.context_dependent || 0} context-dependent ·
        {landscape.contradictions?.apparent || 0} apparent
        — <a href="#/contradictions" class="text-blue-600 dark:text-blue-400 hover:underline">full detail →</a>
      </div>
      <div class="space-y-2">
        {#each landscape.contradictions?.top_real || [] as c, i (i)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3 text-xs">
            <div class="flex items-start justify-between gap-2">
              <span class="font-medium text-gray-800 dark:text-gray-200">{c.topic}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 shrink-0">{c.reason}</span>
            </div>
            <p class="text-gray-500 dark:text-gray-400 mt-0.5">{c.what}</p>
          </div>
        {/each}
      </div>
    {:else if tab === 'questions'}
      <div class="space-y-2">
        {#each landscape.open_questions || [] as q, i (i)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3 text-xs">
            <p class="text-gray-800 dark:text-gray-200">{q.q}</p>
            <div class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{q.cluster}</div>
          </div>
        {/each}
      </div>
    {/if}
  {:else if error}
    <p class="text-red-600 dark:text-red-400 text-sm mt-4">{error}</p>
  {:else}
    <p class="text-gray-500 dark:text-gray-400 text-sm mt-4 animate-pulse">{t('common.loading') || 'Loading…'}</p>
  {/if}
</div>
