<script>
  import { t, i18nRev } from '../lib/stores/i18n.svelte.js';
  /**
   * Methods — how Roost works, as Mermaid flowcharts.
   * Route: #/methods
   */
  import Mermaid from '../lib/components/common/Mermaid.svelte';
  import { onMount } from 'svelte';

  // verso DAG viewer web component (graph-only embeds on this page).
  // Error handler: a failed load leaves a visible notice, not blank boxes.
  let viewerError = $state(false);
  onMount(() => {
    const s = document.createElement('script');
    s.type = 'module';
    s.src = 'viewer/verso-dag-viewer.js';
    s.onerror = () => { viewerError = true; };
    document.head.appendChild(s);
    return () => { s.remove(); };
  });

  let stats = $state(null);
  onMount(async () => {
    try {
      const r = await fetch('data/stats.json');
      if (r.ok) stats = await r.json();
    } catch { /* numbers stay hidden */ }
  });

  // IUCN coverage numbers come from the artifact itself
  // (data/species/iucn_status.json) — never hardcoded prose. Rebuilt by
  // scripts/species/fetch_iucn_status.py; the Numbers page cross-checks
  // the same totals.
  let iucnCounts = $state(null);
  onMount(async () => {
    try {
      const r = await fetch('data/species/iucn_status.json');
      if (r.ok) {
        const d = await r.json();
        const cats = {};
        for (const v of Object.values(d.status || {})) cats[v] = (cats[v] || 0) + 1;
        iucnCounts = {
          matched: d.meta?.n_matched ?? Object.keys(d.status || {}).length,
          total: d.meta?.n_species ?? stats?.species ?? null,
          lc: cats.LC ?? 0, nt: cats.NT ?? 0, vu: cats.VU ?? 0, en: cats.EN ?? 0,
        };
      }
    } catch { /* counts stay hidden */ }
  });

  function formatNumber(n) {
    return n?.toLocaleString?.() ?? n;
  }

  const genePipeline_src = () => `flowchart TD
    panel["Host panel<br/>${t('methods_page.curated.corpus.uniprot.go')}<br/>+ discovery-bucket growth"] --> refs["Reference proteins<br/>${t('methods_page.chicken.duck.orthologs')}<br/>NCBI-verified, sha-tracked"]
    refs --> genome{"Per genome<br/>(sequenced species)"}

    genome --> l0["Layer 0 · NCBI annotation scan"]
    genome --> l1["Layer 1 · blastn<br/>summed HSP coverage"]
    genome --> l2["Layer 2 · DIAMOND + getorf<br/>grouped ORF coverage"]

    l0 --> e5["E5 🏷️ annotated<br/>gold standard"]
    l2 --> e4["E4 ✨ search-found<br/>annotation gap recovered"]
    l2 --> e3["E3 ≈ fragment<br/>partial match"]
    l1 --> e3
    l1 --> e2["E2 ∅ no match"]
    l0 -. "no annotation entry" .-> e2

    e5 & e4 & e3 & e2 --> d20["Classification<br/>e-value &lt; 1e-50 AND coverage ≥ 80% → FULL"]
    d20 --> calls["Presence calls<br/>species × gene · best evidence wins"]

    calls --> align["MAFFT alignments"]
    align --> tree["FastTree phylogenies"]
    calls --> mcl["All-vs-all DIAMOND similarity"]
    mcl --> clusters["MCL clusters<br/>ortholog groups"]

    disc["Discovery bucket<br/>${t('methods_page.nonpanel.genes.from.text')}<br/>≥3 papers = candidate"] -.->|panel growth| panel

    style e5 fill:#dbeafe,stroke:#60a5fa
    style e4 fill:#ede9fe,stroke:#a78bfa
    style e3 fill:#fef3c7,stroke:#fbbf24
    style e2 fill:#f3f4f6,stroke:#9ca3af
    style disc fill:#f0fdf4,stroke:#4ade80`;

  const paperPipeline_src = () => `flowchart TD
    drop["PDF drop folder<br/>pdfs_to_process/"] --> type{"What is it?<br/>typed intake"}

    type -->|correction| corr["attach to parent paper<br/>archived + noted"]
    type -->|news| news["clip shelf (docs/news_md)<br/>never corpus evidence alone"]
    type -->|thesis / book chapter| tagged["full pipeline<br/>venue-weighted + cited"]
    type -->|paper| dup{"duplicate?<br/>filename + content matching"}

    dup -->|yes| dd["logged + deleted<br/>dedup ledger"]
    dup -->|new| fast["FAST PASS ~25s/paper<br/>${t('methods_page.markdown.triage.summary')}<br/>immediately searchable"]

    fast --> digest["FULL DIGEST ~2 min/paper<br/>7-step verified extraction<br/>(muse-glimmer-30b, 56-way parallel)"]
    digest --> meta["METADATA PASS<br/>language · doc type · species focus"]
    meta --> doi["DOI + AUTHOR ENRICHMENT<br/>${t('methods_page.crossref.datacite.pubmed')}<br/>${t('methods_page.year.journal.full.author')}<br/>BibTeX export"]
    doi --> scope{"SCOPE ROUTING<br/>${t('methods_page.avianhumanmammalianepi')}<br/>vaccination | viral | methods"}

    scope --> routes["POLICY DESTINATIONS"]
    routes --> genes["gene evidence<br/>(full / text-scan / via-taxon)"]
    routes --> species["species wiki pages"]
    routes --> model["model badges + synthesis<br/>(cross-taxon pairing)"]
    routes --> rg["full-text rg corpus<br/>every paper, every scope"]

    style dd fill:#f3f4f6,stroke:#9ca3af
    style fast fill:#fef3c7,stroke:#fbbf24
    style digest fill:#dbeafe,stroke:#60a5fa
    style scope fill:#ede9fe,stroke:#a78bfa
    style routes fill:#dcfce7,stroke:#4ade80`;

  const trustTiers_src = () => `flowchart LR
    verified["✓ verified extraction<br/>7-step + LLM verification"] -->|weaker| textscan["~ text-scan tier<br/>regex mentions in full text"]
    textscan -->|weaker| alias["via-alias tier<br/>family symbol attribution"]

    docw["doc-type weights:<br/>${t('methods_page.peerreviewed.10.review.10')}<br/>report 0.8 · thesis 0.7 · preprint 0.6"]

    style verified fill:#dcfce7,stroke:#4ade80
    style textscan fill:#fef3c7,stroke:#fbbf24
    style alias fill:#e0e7ff,stroke:#818cf8
    style docw fill:#f3f4f6,stroke:#9ca3af`;

  const miningCampaign_src = () => `flowchart TD
    md["Paper markdowns<br/>docs/papers_md/"] --> b["PHASE B · SUMMARY REBUILD<br/>2 sentences + main conclusion<br/>numbers required"]

    md --> c1["PHASE C1 · GENE-CLAIM LOOP<br/>'one gene, excluding previous…'<br/>until false · panel-verified"]
    md --> c2["PHASE C2 · CONCLUSIONS LOOP<br/>same exclusion pattern"]
    md --> c3["PHASE C3 · ABSENCE PHENOTYPES<br/>${t('methods_page.kosirnacrispinatural.loss')}<br/>avian vs mammalian"]

    c1 --> verify{"symbol in<br/>panel + aliases?"}
    verify -->|yes| claim["grounded claim<br/>tier + quote"]
    verify -->|no| disc["DISCOVERY BUCKET<br/>≥3 papers = candidate"]

    c1 & c2 & c3 --> gate["GROUNDING GATE<br/>${t('methods_page.quote.source.markdown')}<br/>verbatim check"]
    gate -->|pass| out["cited outputs<br/>papers.json · gene pages · model"]
    gate -->|fail| drop["dropped — never published"]

    md --> d["PHASE D · MODEL VERIFICATION<br/>9 infection + 9 spread stages<br/>agrees/disagrees/changes/adds"]
    d --> tally["stage ledgers<br/>${t('methods_page.diverges.disputes.additions.extensions')}<br/>→ model version review"]

    style b fill:#dbeafe,stroke:#60a5fa
    style c1 fill:#dcfce7,stroke:#4ade80
    style c3 fill:#fef3c7,stroke:#fbbf24
    style d fill:#ede9fe,stroke:#a78bfa
    style gate fill:#fee2e2,stroke:#f87171
    style disc fill:#f3f4f6,stroke:#9ca3af`;

  const surveillance = $derived(`flowchart LR
    subgraph sources ["Surveillance sources"]
      wahis["WOAH WAHIS API"]
      whispers["USDA WHISPers"]
      fao["FAO global + SSA"]
      ocims["SA OCIMS"]
      nz["NZ MPI"]
      aus["Wildlife Health Australia"]
    end
    sources --> ingest["ingest_detections.py<br/>normalise + geocode + dedupe"]
    ingest --> det["Detection store<br/>species × country × date"]
    det --> duck["DuckDB parquet<br/>(in-browser analytics)"]

    tax["Aves taxonomy<br/>every bird species"] --> idx
    det --> profiles["species profiles"]
    genomes["NCBI genome assemblies"] --> idx["Comprehensive species index<br/>all searchable"]
    presence["Gene presence<br/>${stats?.presence_species ?? '…'} species"] --> idx
    phylopic["PhyloPic silhouettes"] --> idx

    style duck fill:#fef9c3,stroke:#facc15
    style idx fill:#dbeafe,stroke:#60a5fa`);
  const evidenceLadder_src = () => `flowchart TD
    e5["E5 · annotated<br/>NCBI annotation lists the gene"] --> e4["E4 · search-found<br/>DIAMOND match despite no annotation"]
    e4 --> e3["E3 · fragment<br/>partial match only"]
    e3 --> e2["E2 · no match<br/>searched, nothing found"]
    e2 --> e1["E1 · weak<br/>searchability issues"]
    e1 --> e0["E0 · unknown"]

    style e5 fill:#dbeafe,stroke:#60a5fa
    style e4 fill:#ede9fe,stroke:#a78bfa
    style e3 fill:#fef3c7,stroke:#fbbf24
    style e2 fill:#f3f4f6,stroke:#9ca3af
    style e1 fill:#fff7ed,stroke:#fdba74
    style e0 fill:#fff,stroke:#d1d5db`;

  // diagram sources re-evaluate when the async i18n dictionaries land (or
  // the locale switches) — otherwise module-load-time t() calls freeze raw
  // keys for anything defined in en_i18n.json (user report 2026-11)
  let genePipeline = $derived.by(() => { void i18nRev(); return genePipeline_src(); });
  let paperPipeline = $derived.by(() => { void i18nRev(); return paperPipeline_src(); });
  let trustTiers = $derived.by(() => { void i18nRev(); return trustTiers_src(); });
  let miningCampaign = $derived.by(() => { void i18nRev(); return miningCampaign_src(); });
  let evidenceLadder = $derived.by(() => { void i18nRev(); return evidenceLadder_src(); });
</script>

<svelte:head><title>{t('lib_components_common_Footer.methods') || 'Methods'} — Roost</title></svelte:head>

<div class="max-w-5xl mx-auto space-y-12">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{t('lib_components_common_Footer.methods')}</h1>
    <p class="text-gray-600 dark:text-gray-300">
      {t('methods.intro')}
      <code class="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{t('methods_page.docsgenepresencelogmd')}</code>.
    </p>
  </div>

  <!-- 1. Gene finding -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">1 · {t('methods.h2.gene_presence')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.gene_presence.desc')}
      </p>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
      <div class="rounded-lg border border-gray-100 dark:border-gray-700 p-1 overflow-x-auto" aria-label={t('methods.scrolling_diagram', { name: t('methods.h2.gene_presence') })}>
        <Mermaid source={genePipeline} id="gene-pipeline" />
      </div>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <h3 class="font-semibold text-gray-900 dark:text-white mb-3 text-sm">{t('methods_page.evidence.ladder.e5.e0')}</h3>
      <Mermaid source={evidenceLadder} id="evidence-ladder" config={{ flowchart: { nodeSpacing: 48 } }} />
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-3">
        {t('methods.badges.legend')}
      </p>
    </div>

    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <h3 class="font-semibold text-gray-900 dark:text-white mb-3 text-sm">{t('methods_page.executed.pipelines.interactive.dags')}</h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {t('methods.workflows.note')}
      </p>
      <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">{t('methods_page.gene.panel.intake.collisionfirst')}</h4>
      {#if viewerError}
        <div class="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 text-sm">{t('methods.viewer_failed')}</div>
      {:else}
      <div class="overflow-x-auto" style="border-radius:0.5rem">
        <verso-dag-viewer
          src="data/dag_gene_panel_intake.json"
          style="display:block;width:100%;height:520px;border:1px solid rgb(229 231 235);border-radius:0.5rem">
        </verso-dag-viewer>
      </div>
      {/if}
      <h4 class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2 mt-6">{t('methods_page.gene.panel.presence.search')}</h4>
      {#if viewerError}
        <div class="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 text-sm">{t('methods.viewer_failed')}</div>
      {:else}
      <div class="overflow-x-auto" style="border-radius:0.5rem">
        <verso-dag-viewer
          src="data/dag_gene_panel_presence.json"
          style="display:block;width:100%;height:520px;border:1px solid rgb(229 231 235);border-radius:0.5rem">
        </verso-dag-viewer>
      </div>
      {/if}
    </div>
  </section>

  <!-- 2. Paper extraction -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">2 · {t('methods.h2.paper_pipeline')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.paper_pipeline.desc1')}
        <strong>{t('routes_Methods.scope')}</strong>
        {t('methods.paper_pipeline.desc2')}
        <em>{t('methods.paper_pipeline.scope_note')}</em>
      </p>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
      <div class="rounded-lg border border-gray-100 dark:border-gray-700 p-1" aria-label={t('methods.scrolling_diagram', { name: t('methods.h2.paper_pipeline') })}>
        <Mermaid source={paperPipeline} id="paper-pipeline" />
      </div>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <h3 class="font-semibold text-gray-900 dark:text-white mb-3 text-sm">{t('methods_page.evidence.trust.tiers')}</h3>
      <Mermaid source={trustTiers} id="trust-tiers" />
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-3">
        {t('methods.citation.tiers')}
      </p>
    </div>
  </section>

  <!-- 3. Surveillance aggregation -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">3 · {t('methods.h2.surveillance')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.surveillance.desc')}
      </p>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <Mermaid source={surveillance} id="surveillance" />
    </div>
  </section>

  <!-- 4 · Literature text-mining campaign -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">4 · {t('methods.h2.text_mining')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.text_mining.desc')}
      </p>
    </div>
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <Mermaid source={miningCampaign} id="mining-campaign" />
    </div>
    <div class="grid sm:grid-cols-2 gap-3 text-xs text-gray-500 dark:text-gray-400">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.summary.rebuild')}</div>
        {t('methods.text_mining.summary_rebuild')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.geneclaim.exclusion.loop')}</div>
        {t('methods.text_mining.exclusion_loop')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.absence.phenotypes')}</div>
        {t('methods.text_mining.lof')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.model.verification')}</div>
        {t('methods.text_mining.model_verification')}
      </div>
    </div>
  </section>

  <!-- Live numbers (from stats.json — always current) -->
  <section class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
    {#if stats}
      {#each [
        [formatNumber(stats.detections), 'detections', stats.sources + ' sources'],
        [formatNumber(stats.species), 'species affected', stats.countries + ' countries'],
        [formatNumber(stats.papers), 'papers analysed', 'grounded text mining'],
        [formatNumber(stats?.presence_calls ?? 0), 'presence calls', (stats?.panel_genes ?? '…') + ' genes × ' + (stats?.presence_species ?? '…') + ' genomes']
      ] as [n, label, sub]}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-center">
          <div class="text-2xl font-bold text-gray-900 dark:text-white">{n}</div>
          <div class="text-sm text-gray-600 dark:text-gray-300">{label}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{sub}</div>
        </div>
      {/each}
    {/if}
  </section>

  <!-- 5 · OrthoFinder orthology -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">5 · {t('methods.h2.orthology')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.orthology.desc')}
      </p>
    </div>
    <div class="grid sm:grid-cols-2 gap-3 text-xs text-gray-500 dark:text-gray-400">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.mapping.method')}</div>
        {t('methods.orthology.mapping')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.two.presence.methods.both')}</div>
        {t('methods.orthology.presence_methods')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.payloads')}</div>
        {t('methods.orthology.payloads')}
        <code>{t('methods_page.ogmatrixparquet')}</code>.
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.caveats')}</div>
        {t('methods.orthology.caveats')}
      </div>
    </div>
  </section>

  <!-- 6 · Synteny -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">6 · {t('methods.h2.synteny')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.synteny.desc1')}
        <code>{t('methods_page.datasets')}</code>
        {t('methods.synteny.desc2')}
      </p>
    </div>
  </section>

  <!-- 7 · IUCN -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">7 · {t('methods.h2.iucn')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods_page.iucn.source')}
        {#if iucnCounts}
          {t('methods_page.iucn.match', { a: iucnCounts.matched, b: iucnCounts.total, c: iucnCounts.lc, d: iucnCounts.nt, e: iucnCounts.vu, f: iucnCounts.en })}
        {/if}
        {t('methods_page.iucn.tiebreak')}
      </p>
    </div>
  </section>

  <!-- 8 · ANP32 -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">8 · {t('methods.h2.anp32')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.anp32.desc1')}
        <code>{t('methods_page.datasets')}</code>
        {t('methods.anp32.desc2')}
      </p>
    </div>
  </section>

  <!-- 9 · BLAST -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">9 · {t('methods.h2.blast')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.blast.desc')}
      </p>
    </div>
  </section>

  <!-- 10 · Autonomous research agent -->
  <section class="space-y-4">
    <div>
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">10 · {t('methods.h2.agent')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
        {t('methods.agent.lead')} <code>#/research/{'{slug}'}</code> and <code>#/landscape</code>
        {t('methods.agent.desc')}
      </p>
    </div>
    <div class="grid sm:grid-cols-2 gap-3 text-xs text-gray-500 dark:text-gray-400">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.selfassessment.and.refinement')}</div>
        {t('methods.agent.selfassessment')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.question.scoring.and.autonomy')}</div>
        {t('methods.agent.scoring')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.every.claim.has.provenance')}</div>
        {t('methods.agent.provenance')}
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-3">
        <div class="font-semibold text-gray-700 dark:text-gray-200 mb-1">{t('methods_page.transparent.evidence.trail')}</div>
        {t('methods.agent.trail')}
      </div>
    </div>
  </section>

  <!-- 11 · Multilingual translation pipeline -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">11 · {t('methods.h2.i18n')}</h2>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5 space-y-3 text-sm text-gray-600 dark:text-gray-300">
      <p>{t('methods.i18n.p1')}</p>
      <p>{t('methods.i18n.p2')}</p>
      <p>{t('methods.i18n.p3')}</p>
      <p>{t('methods.i18n.p4')}</p>
    </div>
  </section>

  <!-- 12 · Species insights -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">12 · {t('methods.h2.insights')}</h2>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5 space-y-3 text-sm text-gray-600 dark:text-gray-300">
      <p>{t('methods.insights.p1')}</p>
      <p>{t('methods.insights.p2')}</p>
      <p>{t('methods.insights.p3')}</p>
      <p>{t('methods.insights.p4')}</p>
    </div>
  </section>

  <!-- Clade view methodology -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('methods_page.cladespecific.gene.patterns')}</h2>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5 space-y-3 text-sm text-gray-600 dark:text-gray-300">
      <p>
        The <a href="#/clade" class="text-blue-600 dark:text-blue-400 underline">{t('methods_page.clade.view')}</a>
        {t('methods.clade.quantifies')}
        <strong>{t('methods_page.genomesearched.species')}</strong>
        {t('methods.clade.full_length')}
      </p>
      <p><strong>{t('methods_page.normalization')}</strong> {t('methods.clade.normalization')}</p>
      <p><strong>{t('methods_page.cladespecific.loss')}</strong> {t('methods.clade.loss_def')}</p>
      <p><strong>{t('methods_page.taxonomy.source')}</strong> {t('methods.clade.taxonomy')}</p>
      <p><strong>{t('methods_page.evidence.ladder')}</strong>
      {t('methods.clade.evidence_ladder')}
      <a href="#/genes" class="text-blue-600 dark:text-blue-400 underline">{t('methods_page.genes.page')}</a>
      {t('methods.clade.evidence_ladder_tail')}</p>
      <p class="text-xs text-gray-500 dark:text-gray-400 italic">
        {t('methods.clade.limitation')}
      </p>
    </div>
  </section>

  <!-- Build tools & attribution -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('methods_page.how.this.resource.was')}</h2>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5 space-y-3">
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">{t('methods_page.development')}</h3>
        <p class="text-sm text-gray-600 dark:text-gray-300">
          {t('methods.ai.built') || 'This site was built with AI coding agents as the primary development tools:'}
        </p>
        <ul class="text-sm text-gray-600 dark:text-gray-300 mt-2 space-y-1 ml-4 list-disc">
          <li><strong>{t('methods_page.pi.agent')}</strong>{t('routes.methods.primary.architecture.data.pipeline') || '(primary) — architecture, data pipeline, and the majority of implementation'}</li>
          <li><strong>{t('methods_page.codex')}</strong> {t('methods.attribution.contrib')}</li>
          <li><strong>{t('methods_page.claude')}</strong> {t('methods.attribution.contrib')}</li>
        </ul>
        <p class="text-sm text-gray-600 dark:text-gray-300 mt-2">
          {t('methods.attribution.powered_by')} <strong>GLM 5.3</strong> {t('methods.attribution.powered_session')}
        </p>
      </div>
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-1">{t('methods_page.literature.analysis')}</h3>
        <p class="text-sm text-gray-600 dark:text-gray-300">
          {t('methods.attribution.corpus')} <strong>{t('methods_page.muse.glimmer')}</strong>,
          {t('methods.attribution.corpus_desc')}
        </p>
      </div>
    </div>
  </section>
</div>
