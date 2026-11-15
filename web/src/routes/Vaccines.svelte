<script>
  import { trackEvent } from '../lib/analytics.js';
  /**
   * Vaccines — the vaccine model page (third model pillar).
   * Route: #/vaccines
   *
   * Infection model = what happens inside the bird (genes).
   * Spread model    = how it moves between birds (ecology).
   * Vaccine model   = how we intervene (platforms → outcomes).
   *
   * v0.1: deterministic keyword-tier evidence (🟡) — the literature LLM
   * is down; verified per-paper claims merge in when it returns
   * (scripts/model/build_vaccine_model.py + mine_vaccines.py).
   */
  import { onMount } from 'svelte';
  import { t, tc, ft } from '../lib/stores/i18n.svelte.js';
  import Mermaid from '../lib/components/common/Mermaid.svelte';
  import VaccineCyto from '../lib/components/common/VaccineCyto.svelte';
  import OutcomesPanels from '../lib/components/vaccines/OutcomesPanels.svelte';
  import CampaignPanels from '../lib/components/vaccines/CampaignPanels.svelte';

  let model = $state(null);
  let loading = $state(true);
  let failed = $state(false);
  let openStage = $state(null);   // expanded stage card id
  // analytics: which vaccine stages people expand
  $effect(() => { if (openStage) trackEvent('Vaccines', 'stage', openStage); });
  let planOpen = $state(false);   // LLM mining plan section
  let readiness = $state(null);   // species vaccine-response capacity
  let outcomes = $state(/** @type {any | null} */ (null));    // corpus outcomes synthesis (v2)
  let campaignDoc = $state(/** @type {any | null} */ (null)); // campaigns layer (historical)
  let readyQuery = $state('');
  let readyAvesOnly = $state(true);

  const PIPELINE = `flowchart LR
    PLAT["1 Platforms<br/>inactivated · LAIV · vectored<br/>mRNA · DNA · nanoparticle"] --> ANT["2 Antigen<br/>HA match · NA · NP · M2e"]
    ANT --> DEL["3 Delivery<br/>in ovo · spray · water · injection"]
    DEL --> ADJ["4 Adjuvant<br/>oil · CpG/TLR21 · cytokine"]
    ADJ --> RESP["5 Response<br/>IgY · IgA · CD8 · breadth"]
    RESP --> PROT["6 Protection<br/>clinical · shedding · transmission"]
    PROT --> DIVA["7 DIVA"]
    PROT --> DEPL["8 Deployment"]
    PROT --> ESC["9 Escape"]
    DIVA -.enables.-> DEPL
    ESC -.constrains.-> ANT
    style PLAT fill:#e0f2fe,stroke:#0ea5e9
    style ANT fill:#ede9fe,stroke:#8b5cf6
    style DEL fill:#ccfbf1,stroke:#14b8a6
    style ADJ fill:#fef3c7,stroke:#f59e0b
    style RESP fill:#fce7f3,stroke:#ec4899
    style PROT fill:#dcfce7,stroke:#22c55e
    style DIVA fill:#f1f5f9,stroke:#64748b
    style DEPL fill:#fee2e2,stroke:#ef4444
    style ESC fill:#ede9fe,stroke:#7c3aed
  `;

  onMount(async () => {
    try {
      const r = await fetch('data/h5n1_vaccine_model.json');
      if (!r.ok) throw new Error(r.statusText);
      model = await r.json();
    } catch {
      failed = true;
    } finally {
      loading = false;
    }
    fetch('data/vaccine_readiness.json').then(r => r.ok ? r.json() : null)
      .then(d => readiness = d).catch(() => {});
    fetch('data/vaccine_outcomes.json').then(r => r.ok ? r.json() : null)
      .then(d => outcomes = d).catch(() => {});
    fetch('data/vaccine_campaigns.json').then(r => r.ok ? r.json() : null)
      .then(d => campaignDoc = d).catch(() => {});
  });

  const totalCandidates = $derived(
    model ? model.stages.reduce((n, s) => n + (s.evidence?.candidate_papers || 0), 0) : 0);

  // --- readiness table ---
  const BAND_STYLE = {
    strong: 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-950/60 dark:text-green-300',
    capable: 'bg-lime-100 text-lime-700 dark:bg-lime-950/60 dark:text-lime-300',
    reduced: 'bg-amber-100 text-amber-700 dark:text-amber-400 dark:bg-amber-950/60 dark:text-amber-300',
    concern: 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300',
    'n/a': 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-800 dark:text-gray-400',
  };
  const readyRows = $derived.by(() => {
    if (!readiness) return [];
    const q = readyQuery.trim().toLowerCase();
    return Object.entries(readiness.species)
      .filter(([sp, v]) => !readyAvesOnly || v.is_aves !== false)
      .filter(([sp]) => !q || sp.toLowerCase().includes(q))
      .slice(0, 60);   // bounded render; full list searchable
  });
  const readyBands = $derived.by(() => {
    if (!readiness) return {};
    const d = {};
    for (const v of Object.values(readiness.species)) {
      if (v.is_aves === false) continue;
      if (v.band === 'n/a') continue;   // mammals + backbone-only — not bands
      d[v.band] = (d[v.band] || 0) + 1;
    }
    return d;
  });
  const MODULE_LABELS = $derived(
    readiness ? Object.fromEntries(readiness.modules.map(m => [m.id, m.label])) : {});

  // compact paper id for inline citation chips
  function paperShort(p) {
    return p.length > 22 ? p.slice(0, 20) + '…' : p;
  }
</script>

<svelte:head><title>{t('vaccines.page.title') || 'Vaccines'} — Roost</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 py-8">
  <!-- Hero -->
  <div class="mb-8">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-1">
          💉 {t('vaccines.model.title') || 'The Vaccine Model'}
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 max-w-3xl">
          {t('vaccines.intro1') || 'How we intervene: from vaccine platform to deployed protection — the third model pillar,'}
          {t('vaccines.intro2') || 'alongside the'} <a href="#/model" class="text-blue-600 dark:text-blue-400 underline">{t('vaccines.infection.model') || 'infection model'}</a>
          {t('vaccines.intro3') || '(what happens inside the bird) and the'}
          <a href="#/model?tab=spread" class="text-blue-600 dark:text-blue-400 underline">{t('spread.page.title2') || 'spread model'}</a>
          {t('vaccines.intro4') || '(how it moves between birds). Genes named in each stage link into the gene panel.'}
        </p>
      </div>
      {#if model}
        <div class="text-xs text-gray-500 dark:text-gray-400 text-right">
          v{model.version} · {model.updated}
        </div>
      {/if}
    </div>

    {#if model}
      <!-- Evidence-tier banner -->
      <div class="mt-4 rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/40 px-4 py-3 text-sm text-amber-800 dark:text-amber-300">
        <strong>{t('routes.vaccines.evidence.tier.keyword.scan') || 'Evidence tier: keyword-scan (🟡).'}</strong>
        {t('vaccines.evidence.banner.body', {n: totalCandidates})}
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="text-center py-16 text-gray-500 dark:text-gray-400">{t('vaccines.loading')}</div>
  {:else if failed}
    <div class="text-center py-16 text-gray-500 dark:text-gray-400">
      {t('vaccines.unavailable')}
      <code class="text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">pixi run python scripts/model/build_vaccine_model.py</code>
    </div>
  {:else if model}
    <!-- Pipeline diagram (D125: Cytoscape — pan/zoom, claim-weighted nodes,
         gene-bridge links; tap a stage to open its card) -->
    <div class="mb-8">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('vaccines.pipeline_title')}</h2>
      <VaccineCyto {model} onStage={(id) => (openStage = id)} />
    </div>

    <!-- Stage cards -->
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3 mb-10">
      {#each model.stages as stage (stage.id)}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden flex flex-col">
          <div class="h-1" style="background: {stage.accent}"></div>
          <div class="p-5 flex-1 flex flex-col">
            <div class="flex items-start justify-between gap-2 mb-2">
              <h3 class="font-semibold text-gray-900 dark:text-white leading-tight">{tc(`vaccine.stage.${stage.id}.title`) || stage.title}</h3>
              <div class="flex shrink-0 gap-1">
                {#if stage.evidence.extracted}
                  <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
                        title={t('vaccines.stage.extracted.tip')}>
                    🟢 {t('vaccines.stage.extracted')}
                  </span>
                {/if}
                <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                      title={t('routes.vaccines.candidate.papers.from.keyword') || 'Candidate papers from keyword scan — LLM verification pending'}>
                  🟡 {stage.evidence.candidate_papers} pp
                </span>
              </div>
            </div>
            {#if stage.evidence.extracted}
              <div class="flex flex-wrap gap-1.5 mb-3">
                {#each Object.entries(stage.evidence.extracted).slice(0, 4) as [k, v] (k)}
                  {#if typeof v === 'number' || typeof v === 'string'}
                    <span class="text-xs px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300">{k.replace(/_/g, ' ')}: {typeof v === 'string' ? v : v}</span>
                  {:else if typeof v === 'object' && !Array.isArray(v)}
                    {#each Object.entries(v).slice(0, 3) as [ik, iv] (ik)}
                      <span class="text-xs px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300">{ik} <strong>{iv}</strong></span>
                    {/each}
                  {/if}
                {/each}
              </div>
            {/if}
            <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-3">{tc(`vaccine.stage.${stage.id}.desc`) || stage.desc}</p>

            {#if stage.genes?.length}
              <div class="mb-3">
                <span class="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold">{t('vaccines.gene_links')}</span>
                <div class="flex flex-wrap gap-1.5 mt-1">
                  {#each stage.genes as gene}
                    <a href="#/genes/{gene}" class="text-xs px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300 hover:ring-1 ring-teal-500"
                       data-testid="vaccine-gene-chip">{gene}</a>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Cited claims: every load-bearing assertion → corpus papers -->
            {#if stage.claims_resolved?.length}
              <div class="mb-3">
                <span class="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold">{t('routes.vaccines.key.claims.cited') || 'Key claims · cited'}</span>
                <ul class="mt-1 space-y-1">
                  {#each stage.claims_resolved as c}
                    <li class="text-xs leading-relaxed">
                      {#if c.backed_by.length}
                        <span class="text-gray-600 dark:text-gray-300">{ft(c.ch) || c.claim}</span>
                        {#each c.backed_by as p}
                          <a href="#/papers?q={encodeURIComponent(p)}" class="text-blue-600 dark:text-blue-400 underline" title={p}>[{paperShort(p)}]</a>
                        {/each}
                      {:else}
                        <span class="text-amber-700 dark:text-amber-400">⚠ {t('vaccines.unsourced_claim')}: {ft(c.ch) || c.claim}</span>
                      {/if}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

            <!-- Top candidate papers -->
            <div class="mb-3">
              <span class="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold">{t('vaccines.top_papers')}</span>
              <ul class="mt-1 space-y-0.5">
                {#each stage.evidence.top_papers.slice(0, 4) as p}
                  <li class="text-xs truncate">
                    <a href="#/papers?q={encodeURIComponent(p.paper)}" class="text-blue-600 dark:text-blue-400 underline" title="{p.paper} — {t('vaccines.keyword_hits', {n: p.hits})}">{p.paper}</a>
                    <span class="text-gray-500 dark:text-gray-400 ml-1">({p.hits})</span>
                  </li>
                {/each}
              </ul>
            </div>

            <div class="mt-auto">
              <button class="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 font-medium"
                      onclick={() => openStage = openStage === stage.id ? null : stage.id}
                      data-testid="vaccine-metrics-toggle">
                {openStage === stage.id ? '▾' : '▸'} What we'll extract ({stage.metrics.length} fields)
              </button>
              {#if openStage === stage.id}
                <ul class="mt-2 text-xs text-gray-500 dark:text-gray-400 list-disc pl-4 space-y-0.5 border-l-2 ml-1 pl-3" style="border-color: {stage.accent}">
                  {#each stage.metrics as m}<li>{m}</li>{/each}
                </ul>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Gene × vaccine bridge -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8">
      <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">{t('routes.vaccines.the.gene.vaccine.bridge') || 'The gene × vaccine bridge'}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {t('vaccines.bridge.intro')}
      </p>
      <div class="grid gap-3 md:grid-cols-2">
        {#each model.gene_bridge as gb (gb.gene)}
          <div class="flex gap-3 items-start border border-gray-100 dark:border-gray-700 rounded-lg p-3">
            <a href="#/genes/{gb.gene}" class="font-mono text-sm font-semibold text-teal-700 dark:text-teal-300 shrink-0 mt-0.5 hover:underline">{gb.gene}</a>
            <span class="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">{gb.why}</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Species vaccine-response capacity -->
    {#if readiness}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8" data-testid="vaccine-readiness">
        <div class="flex flex-wrap items-end justify-between gap-3 mb-1">
          <div>
            <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">{t('vaccines.readiness.title')}</h2>
            <p class="text-sm text-gray-500 dark:text-gray-400 max-w-3xl">
              {t('vaccines.readiness.intro.a')} <em>{t('vaccines.readiness.machinery')}</em> {t('vaccines.readiness.intro.b')}
              {#if readiness.immunomedb}
                <span class="block mt-1">{t('vaccines.readiness.immunomedb', {n: readiness.immunomedb.backbone_only, g: readiness.immunomedb.panel_genes, v: readiness.immunomedb.vintage})}</span>
              {/if}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <label class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
              <input type="checkbox" bind:checked={readyAvesOnly} class="accent-teal-600"> {t('vaccines.birds_only')}
            </label>
            <input bind:value={readyQuery} placeholder={t('search.placeholder.filter.species') || 'Filter species…'}
                   class="text-sm px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                   data-testid="vaccine-readiness-filter">
          </div>
        </div>

        <div class="flex flex-wrap gap-2 my-3 text-xs">
          {#each Object.entries(readyBands) as [b, n]}
            <span class="px-2 py-0.5 rounded-full font-semibold {BAND_STYLE[b] || BAND_STYLE['n/a']}" title="{readiness.bands[b] || ''}">{b}: {n}</span>
          {/each}
          {#each readiness.modules as m}
            <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300" title={m.why}>{m.label}</span>
          {/each}
        </div>

        {#if readiness.species['Strigops habroptila']}
          <div class="rounded-lg border border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-950/40 p-4 mb-4 text-sm" data-testid="kakapo-planner">
            <strong class="text-teal-800 dark:text-teal-300">🦜 Kākāpō planner.</strong>
            <span class="text-teal-900/80 dark:text-teal-200/80">
              readiness {readiness.species['Strigops habroptila'].overall} ({readiness.species['Strigops habroptila'].band}) —
              CpG-adjuvant arm intact (TLR21/MYD88 {readiness.species['Strigops habroptila'].modules.cpg_adjuvant});
              MHC-I/CD8 arm reduced ({readiness.species['Strigops habroptila'].modules.mhc1_cd8}: BF2 fragment,
              {readiness.species['Strigops habroptila'].missing.join(', ') || 'no'} missing).
              Closest deployed wildlife template: king-penguin trial (individual dosing, inactivated HA);
              evidence species with trial data: chicken &amp; mallard. Programme design data: none (gap V1).
            </span>
          </div>
        {/if}

        <div class="overflow-x-auto">
          <table class="w-full text-sm text-gray-900 dark:text-gray-100" data-testid="vaccine-readiness-table">
            <thead>
              <tr class="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <th class="py-2 pr-3">{t('vaccines.th.species')}</th>
                <th class="py-2 pr-3">{t('vaccines.th.overall')}</th>
                <th class="py-2 pr-3">Band</th>
                {#each readiness.modules as m}
                  <th class="py-2 pr-3" title={m.why}>{m.label}</th>
                {/each}
                <th class="py-2 pr-3" title={t('routes.vaccines.immunomedb.gene.immune.backbone') || 'ImmunomeDB 520-gene immune backbone — intact-annotated fraction'}>Backbone</th>
                <th class="py-2">{t('vaccines.th.missing_modules')}</th>
              </tr>
            </thead>
            <tbody>
              {#each readyRows as [sp, v] (sp)}
                <tr class="border-b border-gray-100 dark:border-gray-700/50 {v.anchor ? 'bg-blue-50/60 dark:bg-blue-950/30' : ''}
                  {v.source === 'immunomedb-2020' ? 'opacity-80' : ''}">
                  <td class="py-1.5 pr-3">
                    {#if v.source === 'immunomedb-2020'}
                      <span class="text-gray-700 dark:text-gray-300">{sp}</span>
                      <span class="block text-[10px] text-gray-500 dark:text-gray-400">{v.order} · backbone-only (ImmunomeDB 2020)</span>
                    {:else}
                      <a href="#/species-full/{encodeURIComponent(sp)}" class="hover:underline text-gray-900 dark:text-white">{sp}</a>
                      {#if v.anchor}<span class="block text-[10px] text-blue-600 dark:text-blue-400">{v.anchor}</span>{/if}
                      {#if v.caveat}<span class="block text-[10px] text-gray-500 dark:text-gray-400">{v.caveat}</span>{/if}
                    {/if}
                  </td>
                  <td class="py-1.5 pr-3 font-mono">{v.overall != null ? v.overall.toFixed(2) : '—'}</td>
                  <td class="py-1.5 pr-3"><span class="px-1.5 py-0.5 rounded text-[11px] font-semibold {BAND_STYLE[v.band] || BAND_STYLE['n/a']}">{v.band === 'n/a' && v.source === 'immunomedb-2020' ? 'backbone' : v.band}</span></td>
                  {#each readiness.modules as m}
                    <td class="py-1.5 pr-3 font-mono text-xs">{v.modules ? v.modules[m.id].toFixed(2) : '—'}</td>
                  {/each}
                  <td class="py-1.5 pr-3 font-mono text-xs">{v.backbone_immunomedb != null ? v.backbone_immunomedb.toFixed(2) : '—'}</td>
                  <td class="py-1.5 text-xs text-gray-500 dark:text-gray-400">{v.missing.length ? v.missing.join(', ') : '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-2">Showing {readyRows.length} of {Object.keys(readiness.species).length} species · weighting {readiness.weighting} · generated {readiness.generated}</p>
      </div>
    {/if}

    <!-- Development tracker -->
    {#if model?.tracker?.length}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8" data-testid="vaccine-tracker">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">{t('vaccines.tracker.title')}</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {t('vaccines.subtitle') || 'Candidates, licensed products and deployed programs — seeded from the corpus (paper links) and curated;'}
          <span class="text-amber-700 dark:text-amber-400">⚠ {t('vaccines.web_verify_pending')}</span> {t('vaccines.web_verify_note')}
        </p>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <th class="py-2 pr-3">{t('vaccines.th.program')}</th>
                <th class="py-2 pr-3">{t('vaccines.th.platform')}</th>
                <th class="py-2 pr-3">{t('vaccines.th.antigen')}</th>
                <th class="py-2 pr-3">{t('vaccines.th.species')}</th>
                <th class="py-2 pr-3">{t('vaccines.th.status')}</th>
                <th class="py-2 pr-3">DIVA</th>
                <th class="py-2">{t('vaccines.th.corpus')}</th>
              </tr>
            </thead>
            <tbody>
              {#each model.tracker as trk (trk.name)}
                <tr class="border-b border-gray-100 dark:border-gray-700/50 align-top">
                  <td class="py-2 pr-3">
                    <span class="font-medium text-gray-900 dark:text-white">{trk.name}</span>
                    <span class="block text-[11px] text-gray-500 dark:text-gray-400">{trk.region}</span>
                    {#if trk.note}<span class="block text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 max-w-md">{trk.note}</span>{/if}
                    {#if trk.web_verified === false}<span class="text-[10px] text-amber-700 dark:text-amber-400">⚠ web-verify pending</span>{/if}
                  </td>
                  <td class="py-2 pr-3 text-xs">{trk.platform}</td>
                  <td class="py-2 pr-3 text-xs">{trk.antigen}</td>
                  <td class="py-2 pr-3 text-xs">{trk.species.join(', ')}</td>
                  <td class="py-2 pr-3 text-xs">{trk.status}</td>
                  <td class="py-2 pr-3 text-xs">{trk.diva}</td>
                  <td class="py-2 text-xs">
                    {#each trk.corpus as p}
                      <a href="#/papers?q={encodeURIComponent(p)}" class="text-blue-600 dark:text-blue-400 underline block truncate max-w-[180px]" title={p}>{p}</a>
                    {/each}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}

    <!-- Corpus outcomes synthesis (v2 extraction) -->
    {#if outcomes}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8" data-testid="vaccine-outcomes">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">
          {t('vaccines.outcomes.title') || 'What vaccination achieved — the corpus ledger'}
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('vaccines.outcomes.subtitle')}</p>
        <!-- headline teaser: the ledger's three most decision-relevant numbers -->
        <div class="mb-6 flex flex-wrap gap-3" role="group" aria-label={t('vaccines.outcomes.teaser.label')}>
          {#if outcomes.vaccination?.outcomes?.worked}
            <div class="flex items-baseline gap-2 rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30 px-4 py-2.5">
              <span class="text-2xl font-bold text-green-700 dark:text-green-300">{outcomes.vaccination.outcomes.worked}</span>
              <span class="text-sm text-green-800/80 dark:text-green-200/80">{t('vaccines.outcomes.teaser.worked')}</span>
            </div>
          {/if}
          {#if outcomes.wild_programs?.length}
            <div class="flex items-baseline gap-2 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 px-4 py-2.5">
              <span class="text-2xl font-bold text-amber-700 dark:text-amber-300">{outcomes.wild_programs.length}</span>
              <span class="text-sm text-amber-800/80 dark:text-amber-200/80">{t('vaccines.outcomes.teaser.wild')}</span>
            </div>
          {/if}
          {#if outcomes.protection_gaps?.candidates?.length}
            <div class="flex items-baseline gap-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-4 py-2.5">
              <span class="text-2xl font-bold text-slate-700 dark:text-slate-200">{outcomes.protection_gaps.candidates.length}</span>
              <span class="text-sm text-slate-600 dark:text-slate-300">{t('vaccines.outcomes.teaser.gaps')}</span>
            </div>
          {/if}
        </div>
        <OutcomesPanels doc={outcomes} />
      </div>
    {/if}

    <!-- Campaign history (era-joined) -->
    {#if campaignDoc?.campaigns?.length}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8" data-testid="vaccine-campaigns">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">
          {t('vaccines.campaigns.title')}
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-5">{t('vaccines.campaigns.subtitle')}</p>
        <CampaignPanels doc={campaignDoc} />
      </div>
    {/if}

    <!-- Spread integration -->
    {#if model?.spread_integration}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8" data-testid="vaccine-spread-integration">
        <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">Vaccination × spread</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">{model.spread_integration._doc}</p>
        <div class="grid gap-3 md:grid-cols-2">
          {#each model.spread_integration.links as l (l.spread_stage)}
            <a href="#/model?tab=spread" class="border border-gray-100 dark:border-gray-700 rounded-lg p-3 hover:ring-1 ring-blue-400 block">
              <span class="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">{l.spread_stage}</span>
              <span class="block text-sm text-gray-700 dark:text-gray-300 mt-1">{l.mechanism}</span>
              {#if l.formula}<code class="block text-[11px] text-gray-500 dark:text-gray-400 mt-1.5 bg-gray-50 dark:bg-gray-900 rounded px-2 py-1">{l.formula}</code>{/if}
            </a>
          {/each}
        </div>
        <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-3">{model.spread_integration.evidence_status}</p>
      </div>
    {/if}

    <!-- Mining plan -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6 mb-8">
      <button class="w-full flex items-center justify-between text-left"
              onclick={() => planOpen = !planOpen} data-testid="vaccine-plan-toggle">
        <div>
          <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-1">{t('routes.vaccines.the.mining.queue.questions') || 'The mining queue — questions for the literature LLM'}</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            {model.llm_plan.cross_cutting_questions.length} cross-cutting questions ·
            {model.llm_plan.fields.length} extraction fields per vaccine × species × experiment.
            Runs when the agent is back.
          </p>
        </div>
        <span class="text-gray-500 dark:text-gray-400 ml-4">{planOpen ? '▾' : '▸'}</span>
      </button>
      {#if planOpen}
        <div class="mt-5 grid gap-6 md:grid-cols-2">
          <div>
            <h3 class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold mb-2">{t('vaccines.schema.title')}</h3>
            <div class="flex flex-wrap gap-1.5">
              {#each model.llm_plan.fields as f}
                <code class="text-[11px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">{f}</code>
              {/each}
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-3">{model.llm_plan._doc}</p>
          </div>
          <div>
            <h3 class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 font-semibold mb-2">{t('vaccines.questions.title')}</h3>
            <ol class="list-decimal pl-5 space-y-1.5">
              {#each model.llm_plan.cross_cutting_questions as q, i}
                <li class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed" data-testid="vaccine-llm-question">{q}</li>
              {/each}
            </ol>
          </div>
        </div>
      {/if}
    </div>

    <!-- Gaps -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <h2 class="text-xl font-bold text-gray-900 dark:text-white mb-4">{t('vaccines.gaps.title')}</h2>
      <div class="space-y-2">
        {#each model.gaps as gap (gap.id)}
          <div class="flex gap-3 items-start">
            <span class="font-mono text-xs font-bold shrink-0 mt-0.5 {gap.kind === 'true-gap' ? 'text-red-600 dark:text-red-400' : 'text-amber-700 dark:text-amber-400'}">{gap.id}</span>
            <div>
              <span class="text-sm text-gray-700 dark:text-gray-200">{gap.what}</span>
              <span class="ml-2 text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded font-semibold {gap.kind === 'true-gap'
                ? 'bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300'
                : 'bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300'}">{gap.kind}</span>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
