<script>
  import { trackEvent } from '../lib/analytics.js';
import { t } from '../lib/stores/i18n.svelte.js';
  /** Research briefing — agentic deep-dive on a research question. */

  let { slug = '' } = $props();

  let briefing = $state(null);
  // analytics: which research briefings people read
  $effect(() => { if (briefing?.slug || briefing?.title) trackEvent('Research', 'briefing', briefing.slug || briefing.title.slice(0, 60)); });
  let error = $state(null);
  let showTrace = $state(false);
  let media = $state({ figures: [], videos: [] });
  let contraLinks = $state(null);

  // slug-keyed effect (not onMount): hash-route links between briefings
  // change the slug prop without remounting — fetch must re-run
  $effect(() => {
    const s = slug;
    if (!s) return;
    let alive = true;
    error = null;
    briefing = null;
    (async () => {
      try {
        const r = await fetch(`data/research_briefings/${s}.json`);
        if (!r.ok) throw new Error('not found');
        if (alive) briefing = await r.json();
      } catch {
        if (alive) error = (t('research.briefing.not.found') || 'Briefing not found:') + ` "${s}"`;
      }
      try {
        // cache-busted: vite serves public/ with heuristic caching and the SPA
        // re-mounts without revalidating subresources
        const r = await fetch(`figures/index.json?t=${Date.now()}`);
        if (r.ok && alive) {
          const idx = await r.json();
          media = {
            figures: (idx.figures || []).filter((f) => f.page === s),
            videos: (idx.videos || []).filter((v) => v.page === s)
          };
        }
      } catch { /* media registry optional */ }
      try {
        const r = await fetch('data/contradiction_briefing_links.json');
        if (r.ok && alive) contraLinks = await r.json();
      } catch { /* links optional */ }
    })();
    return () => { alive = false; };
  });

  /** Sentence-split a paragraph into bullet items (keeps [paper_id]s). */
  function sentences(text) {
    return (text || '').split(/(?<=[.!?])\s+/).map(t => t.trim()).filter(t => t.length > 3);
  }

  /** Agentic/process sections render last, subdued. */
  const META_SECTION = /^(search(es| history)?|evidence (retrieved|found)|relevance assessment|limitations( of| and)?|agent process)/i;

  const orderedSections = $derived.by(() => {
    const secs = briefing?.sections || [];
    const content = [], meta = [];
    for (const sec of secs) (META_SECTION.test(sec.heading || '') ? meta : content).push(sec);
    return [...content, ...meta];
  });

  /** Known tool names to exclude from paper-id linkification */
  const TOOL_NAMES = new Set(['search_corpus', 'query_field', 'get_model',
    'search_external', 'check_contradictions', 'get_paper_detail',
    'get_gene_evidence', 'query_species_traits', 'check_disagreements']);

  /** Convert [paper_id] in text to an array of text/link segments.
   *  Also strips (corpus), (field), (model) labels from old briefings. */
  function linkify(text) {
    if (!text) return [];
    // strip source labels from old-format briefings
    text = text.replace(/\s*\((?:corpus|field|model|external)\)/g, '');
    const parts = [];
    const re = /\[([a-z0-9][a-z0-9_-]{3,40})\]/g;
    let last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (TOOL_NAMES.has(m[1])) continue;  // tool name, not a paper
      if (m.index > last) parts.push({ t: text.slice(last, m.index) });
      parts.push({ link: m[1] });
      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push({ t: text.slice(last) });
    return parts;
  }

  const FEAS = { high: 'bg-emerald-100 text-emerald-700', medium: 'bg-amber-100 text-amber-700 dark:text-amber-400', low: 'bg-red-100 text-red-700' };
  const TOOL_COLORS = {
    search_corpus: '#3b82f6', get_gene_evidence: '#14b8a6', query_field: '#f59e0b',
    get_model: '#8b5cf6', check_contradictions: '#ef4444', search_external: '#64748b',
    get_paper_detail: '#6366f1', query_species_traits: '#ec4899', check_disagreements: '#f97316',
  };
</script>

<svelte:head><title>{briefing ? briefing.title : (t('research.page.title') || 'Research briefings')} — Roost</title></svelte:head>

<div class="max-w-4xl mx-auto px-4 py-8">
  {#if !slug}
    <!-- bare #/research: no briefing selected — a proper empty state, not
         an eternal spinner (and an h1 so the page is navigable) -->
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mt-8">{t('research.page.title') || 'Research briefings'}</h1>
    <p class="text-sm text-gray-600 dark:text-gray-300 mt-2">
      {t('research.pick.a.briefing') || 'Pick a briefing from the Research links on the Home or Papers pages.'}
    </p>
  {:else if error}
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mt-8">{t('research.page.title') || 'Research briefings'}</h1>
    <p class="text-red-600 dark:text-red-400 text-sm mt-4">{error}</p>
  {:else if !briefing}
    <p class="text-gray-700 dark:text-gray-300 text-sm mt-8 animate-pulse">{t('research.loading') || 'Loading briefing…'}</p>
  {:else}
    <!-- Header: the question under investigation is the top item -->
    <div class="mb-6">
      <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">Research Briefing</p>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white leading-tight">{briefing.title}</h1>
      {#if briefing.question}
        <div class="mt-3 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded-r-lg px-4 py-2.5">
          <p class="text-[10px] uppercase tracking-wide text-blue-600 dark:text-blue-300 font-bold mb-0.5">Investigating</p>
          <p class="text-sm text-blue-900 dark:text-blue-100 leading-snug">{briefing.question}</p>
        </div>
      {/if}
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-2 leading-relaxed">{briefing.summary}</p>
    </div>

    <!-- Sections: content first (bullets); agentic process sections last -->
    <div class="space-y-3 mb-8">
      {#each orderedSections as sec}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 {META_SECTION.test(sec.heading || '') ? 'opacity-75 border border-dashed border-gray-200 dark:border-gray-700' : ''}">
          {#if META_SECTION.test(sec.heading || '')}
            <h2 class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">⚙ Agent process · {sec.heading}</h2>
          {:else}
            <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">{sec.heading}</h2>
          {/if}
          <ul class="space-y-1.5">
            {#each sentences(sec.body) as sent}
              <li class="text-sm text-gray-600 dark:text-gray-400 leading-snug flex gap-2">
                <span class="text-gray-500 dark:text-gray-400 select-none shrink-0">•</span>
                <span>
                  {#each linkify(sent) as part}
                    {#if part.link}
                      <a href="#/papers/{part.link}"
                         class="text-blue-600 dark:text-blue-400 hover:underline text-xs font-mono bg-blue-50 dark:bg-blue-900/20 px-1 rounded"
                         title={t('btn.view.paper') || 'View paper'}>{part.link}</a>
                    {:else}
                      {part.t}
                    {/if}
                  {/each}
                </span>
              </li>
            {/each}
          </ul>
        </div>
      {/each}
    </div>

    <!-- Figures & media (registry: web/public/figures/index.json) -->
    {#if media.figures.length || media.videos.length}
      <h2 class="text-base font-bold text-gray-900 dark:text-white mb-2 mt-6">📊 Figures &amp; media</h2>
      <div class="grid md:grid-cols-2 gap-3 mb-3">
      {#each media.figures as f (f.file)}
        <figure class="bg-white dark:bg-gray-800 rounded-xl shadow p-3 flex flex-col">
          <a href={f.url} target="_blank" rel="noopener" title={t('research.open_full_size')}>
            <img src={f.url} alt={f.caption || f.file} loading="lazy"
                 class="w-full max-h-56 object-contain rounded-lg border border-gray-100 dark:border-gray-700" />
          </a>
          {#if f.caption}<figcaption class="text-[11px] text-gray-500 dark:text-gray-400 mt-1.5 leading-snug line-clamp-2">{f.caption}</figcaption>{/if}
          <div class="flex items-center gap-3 mt-2 flex-wrap">
            {#if f.svg}<a href={f.svg} target="_blank" class="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline">SVG source</a>{/if}
            <a href={f.url} target="_blank" class="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline">PNG</a>
            {#if f.credits?.length}
              <span class="text-[10px] text-gray-500 dark:text-gray-400">
                {#each f.credits as c, i}{#if i}&nbsp;·&nbsp;{/if}
                  {#if c.source_url}<a href={c.source_url} target="_blank" rel="noopener" class="hover:underline text-gray-500 dark:text-gray-400">{c.title}</a>{:else}{c.title}{/if}
                  by {c.author}
                  {#if c.license_url}<a href={c.license_url} target="_blank" rel="noopener" class="text-blue-600 dark:text-blue-400 hover:underline">{c.license}</a>{:else}({c.license}){/if}
                  {#if c.modified}<span class="text-gray-500 dark:text-gray-400" title={t('routes.research.modified.from.the.original') || 'modified from the original (within license terms)'}>(modified)</span>{/if}
                {/each}
              </span>
            {:else if f.attribution}<span class="text-[10px] text-gray-500 dark:text-gray-400">Assets: {f.attribution}</span>{/if}
          </div>
        </figure>
      {/each}
      </div>
      {#each media.videos as v (v.file)}
        <figure class="bg-white dark:bg-gray-800 rounded-xl shadow p-3 mb-3 max-w-3xl mx-auto">
          <video controls preload="metadata" src={v.url} aria-label={v.caption || v.file} class="w-full h-auto rounded-lg">
            <track kind="captions" src={v.caption ? v.url.replace(/\.mp4$/, '.vtt') : undefined} />
          </video>
          {#if v.caption}<figcaption class="text-[11px] text-gray-500 dark:text-gray-400 mt-1.5 leading-snug">{v.caption}</figcaption>{/if}
        </figure>
      {/each}
    {/if}

    <!-- Linked contradictions (shared citations with adjudicated clusters) -->
    {#if contraLinks?.by_briefing?.[slug]?.length}
      <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-3 mt-8">{t('research.contradictions_touching')}</h2>
      <div class="space-y-2 mb-4">
        {#each contraLinks.by_briefing[slug].slice(0, 12) as c (c.cluster)}
          <a href="#/contradictions" class="block bg-white dark:bg-gray-800 rounded-xl shadow p-3 hover:shadow-md transition-shadow">
            <div class="flex items-start justify-between gap-2">
              <p class="text-xs font-medium text-gray-800 dark:text-gray-200">{c.topic}</p>
              <span class="text-[10px] px-1.5 py-0.5 rounded shrink-0 font-semibold
                {c.verdict === 'real' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                : c.verdict === 'apparent' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'}">{c.verdict}</span>
            </div>
          </a>
        {/each}
      </div>
    {/if}

    <!-- Hypotheses -->
    {#if briefing.hypotheses?.length}
      <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-3 mt-8">🔬 Testable Hypotheses</h2>
      {#each briefing.hypotheses as h}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-3 border-l-4 {h.confidence === 'high' ? 'border-emerald-400' : h.confidence === 'medium' ? 'border-amber-400' : 'border-red-400'}">
          <div class="flex items-start justify-between gap-3">
            <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{h.hypothesis}</p>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 {FEAS[h.confidence] || FEAS.medium}">{h.confidence}</span>
          </div>
          {#if h.prediction}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5"><b>Prediction:</b> {h.prediction}</p>
          {/if}
          {#if h.evidence_for?.length}
            <div class="mt-2 text-xs">
              <span class="text-emerald-600 dark:text-emerald-400 font-medium">For:</span>
              <ul class="ml-4 mt-0.5 space-y-0.5">
                {#each h.evidence_for.slice(0, 3) as ev}
                  <li class="text-gray-500 dark:text-gray-400">
                    {#each linkify(ev) as part}
                      {#if part.link}
                        <a href="#/papers/{part.link}" class="text-blue-600 dark:text-blue-400 hover:underline font-mono text-[10px]">{part.link}</a>
                      {:else}{part.t}{/if}
                    {/each}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
          {#if h.evidence_against?.length}
            <div class="mt-1.5 text-xs">
              <span class="text-red-600 dark:text-red-400 font-medium">Against:</span>
              <ul class="ml-4 mt-0.5 space-y-0.5">
                {#each h.evidence_against.slice(0, 3) as ev}
                  <li class="text-gray-500 dark:text-gray-400">
                    {#each linkify(ev) as part}
                      {#if part.link}
                        <a href="#/papers/{part.link}" class="text-blue-600 dark:text-blue-400 hover:underline font-mono text-[10px]">{part.link}</a>
                      {:else}{part.t}{/if}
                    {/each}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
          {#if h.test}
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 italic"><b>Test:</b> {h.test}</p>
          {/if}
        </div>
      {/each}
    {/if}

    <!-- Research Plan -->
    {#if briefing.research_plan?.length}
      <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-3 mt-8">{t('research.plan')}</h2>
      {#each briefing.research_plan as p, pi}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3 mb-2 flex items-start gap-3">
          <span class="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center shrink-0">{pi + 1}</span>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-gray-800 dark:text-gray-200">{p.study}</p>
            <div class="flex flex-wrap gap-x-3 mt-1 text-[10px] text-gray-500 dark:text-gray-400">
              {#if p.method}<span>{p.method}</span>{/if}
              {#if p.model_system}<span>{p.model_system}</span>{/if}
            </div>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 {FEAS[p.feasibility] || FEAS.medium}">{p.feasibility}</span>
        </div>
      {/each}
    {/if}

    <!-- Unresolved & Gaps & Meta-Questions -->
    {#if briefing.unresolved?.length || briefing.data_gaps?.length || briefing.meta_questions?.length}
      <div class="mt-8 space-y-4">
        {#if briefing.meta_questions?.length}
          <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
            <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase mb-3">{t('routes.research.questions.from.this.investigation') || '🔮 Questions from this investigation'}</h3>
            <div class="space-y-2">
              {#each briefing.meta_questions as mq}
                {@const isObj = typeof mq === 'object'}
                {@const q = isObj ? mq.question : mq}
                {@const scope = isObj ? mq.scope : 'own_briefing'}
                <div class="flex items-start gap-2 text-xs">
                  <span class="shrink-0 mt-0.5 {scope === 'this_report' ?
                    'text-blue-600 dark:text-blue-400' : 'text-purple-500'}"
                    title={scope === 'this_report'
                      ? 'Sub-detail of the main question — belongs in this report'
                      : 'Its own research question — worth a separate briefing'}>
                    {scope === 'this_report' ? '↳' : '→'}
                  </span>
                  <div class="min-w-0">
                    <span class="text-gray-700 dark:text-gray-300">{q}</span>
                    {#if isObj && mq.reasoning}
                      <span class="text-gray-500 dark:text-gray-400 text-[10px] ml-1 italic">{mq.reasoning}</span>
                    {/if}
                    {#if scope === 'own_briefing'}
                      <button
                        class="ml-1 text-[10px] text-purple-500 dark:text-purple-400 hover:underline"
                        title={t('routes.research.investigate.this.as.its') || 'Investigate this as its own briefing'}
                        onclick={() => window.location.hash = `#/research`}>
                        [investigate separately]
                      </button>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
        <div class="grid md:grid-cols-2 gap-4">
          {#if briefing.unresolved?.length}
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase mb-2">❓ Unresolved</h3>
              <ul class="space-y-1">
                {#each briefing.unresolved as q}<li class="text-xs text-gray-500 dark:text-gray-400">• {q}</li>{/each}
              </ul>
            </div>
          {/if}
          {#if briefing.data_gaps?.length}
            <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
              <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase mb-2">{t('research.data_gaps')}</h3>
              <ul class="space-y-1">
                {#each briefing.data_gaps as g}<li class="text-xs text-gray-500 dark:text-gray-400">• {g}</li>{/each}
              </ul>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Evidence Trail (bottom, collapsible) -->
    {#if briefing.agent_trace?.tool_calls?.length}
      <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-8">
        <button class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-2"
          onclick={() => (showTrace = !showTrace)}>
          {showTrace ? '▾' : '▸'} Evidence trail — {briefing.agent_trace.tool_calls.length} tool calls
          across {briefing.agent_trace.n_iterations || briefing.agent_trace.tool_calls.length} iterations
        </button>
        {#if showTrace}
          {@const toolCounts = Object.entries(
            briefing.agent_trace.tool_calls.reduce((acc, c) => {
              acc[c.tool] = (acc[c.tool] || 0) + 1; return acc; }, {})
          ).sort((a, b) => b[1] - a[1])}
          <div class="flex flex-wrap gap-1 mb-3">
            {#each toolCounts as [tool, count]}
              <span class="px-2 py-0.5 rounded-full text-[10px] font-medium"
                    style="background: {(TOOL_COLORS[tool] || '#94a3b8')}18; color: {TOOL_COLORS[tool] || '#94a3b8'}">
                {tool} ×{count}
              </span>
            {/each}
          </div>
          <div class="overflow-x-auto max-h-72 overflow-y-auto rounded-lg border border-gray-100 dark:border-gray-700">
            <table class="w-full text-[10px]">
              <thead class="sticky top-0 bg-gray-50 dark:bg-gray-800">
                <tr class="text-left text-gray-500 dark:text-gray-400 uppercase">
                  <th class="px-2 py-1">#</th>
                  <th class="px-2 py-1">Tool</th>
                  <th class="px-2 py-1">Query</th>
                  <th class="px-2 py-1 text-right">Results</th>
                  <th class="px-2 py-1 text-right">Duration</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-50 dark:divide-gray-700/30">
                {#each briefing.agent_trace.tool_calls as call, ci}
                  <tr class="hover:bg-gray-25 dark:hover:bg-gray-700/20">
                    <td class="px-2 py-1 text-gray-300">{ci + 1}</td>
                    <td class="px-2 py-1">
                      <span class="font-mono font-semibold" style="color: {TOOL_COLORS[call.tool] || '#94a3b8'}">{call.tool}</span>
                    </td>
                    <td class="px-2 py-1 text-gray-500 dark:text-gray-400 max-w-xs truncate">{JSON.stringify(call.args || {})}</td>
                    <td class="px-2 py-1 text-right tabular-nums">{call.hits ?? '—'}</td>
                    <td class="px-2 py-1 text-right tabular-nums text-gray-500 dark:text-gray-400">{call.duration_ms ? `${call.duration_ms}ms` : '—'}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>
