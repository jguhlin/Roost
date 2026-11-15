<script>
  import { trackEvent } from '../../analytics.js';
  import { t, ft, vt } from '../../../lib/stores/i18n.svelte.js';
  /**
   * Full-page gene view — the "wiki page" for a gene.
   * Props: gene (curated panel record), wiki (LLM-extracted synthesis),
   * pdb (structure info or null).
   */
  import { navigate } from '../../stores/router.js';
  import { ncbi, uniprot } from '../../utils/urls.js';
  import { formatNumber } from '../../utils/format.js';
  import MolecularViewer from './MolecularViewer.svelte';
  import ScopeTags from '../common/ScopeTags.svelte';
  import { phylopicIndex, phylopicPath } from '../../utils/phylopic.js';
  import EvidenceDrawer from './EvidenceDrawer.svelte';
  import GeneProfile from './GeneProfile.svelte';
  let geneProfileHasContent = $state(false);
  // analytics: which genes people open (no-op in dev)
  $effect(() => { if (gene?.symbol) trackEvent('Gene', 'view', gene.symbol); });
  import GenomeBrowser from './GenomeBrowser.svelte';
  import { db } from '../../stores/db.js';

  let { gene, wiki = null, pdb = null, relationships = null,
        hostAssoc = null } = $props();

  let showViewer = $state(false); // open by default when a structure is available
  // $state initializers don't re-run when props change — the Genes page
  // reuses this instance across gene switches, so re-seed on pdb change
  $effect(() => { showViewer = !!pdb; });
  // Research-papers list pagination (full corpus ships in genes.json —
  // no builder-side cap — so long lists page 10 at a time). Reset on
  // gene switch, same re-seed rule as showViewer.
  const PAPERS_PAGE_SIZE = 10;
  let papersPage = $state(0);
  $effect(() => { void gene.symbol; papersPage = 0; });
  let papersPageCount = $derived(Math.max(1, Math.ceil((gene.papers?.length || 0) / PAPERS_PAGE_SIZE)));
  let pagedPapers = $derived((gene.papers || []).slice(
    papersPage * PAPERS_PAGE_SIZE, (papersPage + 1) * PAPERS_PAGE_SIZE));

  let silhouettes = $state(null);
  let inspectSpecies = $state(null); // species name with open evidence drawer
  let presenceSearch = $state('');   // live filter for the presence matrix
  let presenceFilter = $state('all'); // all | FULL | FRAGMENT | NOT_FOUND
  let presenceShow = $state(60);      // render cap — 'show more' pagination
  $effect(() => { phylopicIndex().then(i => silhouettes = i); });

  // Per-gene species→status map, loaded lazily from the DuckDB matrix
  // (replaces the eager catalogue.species copy — Phase 2 Step 3)
  let presenceMap = $state(null);
  // OrthoFinder orthology (lazy, one fetch per app load)
  let ortho = $state(null); // {mapping, ogStats}
  // Literature evidence from the aggregation layer (gene_evidence/{GENE}.json)
  // — automatically picks up new extractions when build_aggregation.py re-runs
  let geneEv = $state(null);
  $effect(() => {
    const sym = gene.symbol;
    geneEv = null;
    if (!sym) return;
    let alive = true;
    (async () => {
      try {
        const r = await fetch(`data/gene_evidence/${encodeURIComponent(sym)}.json`);
        if (r.ok && !alive) return;
        if (r.ok) geneEv = await r.json();
      } catch { /* stays hidden */ }
    })();
    return () => { alive = false; };
  });
  // Genomic context (synteny neighbours, lazy)
  let geneCtx = $state(null); // [{sci, assembly, chrom, self:[s,e], nb:[{sym,start,end}]}]
  let flanks = $state(null); // curated-block detailed windows + gene_index
  $effect(() => {
    const sym = gene.symbol;
    geneCtx = null;
    flanks = null;
    if (!sym) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch('data/synteny/gene_context.json');
        if (!r.ok || cancelled) return;
        const ctx = await r.json();
        if (!cancelled) geneCtx = ctx?.[sym] || null;
      } catch { /* context stays hidden */ }
      try {
        const r = await fetch('data/synteny/flanks.json');
        if (!r.ok || cancelled) return;
        const f = await r.json();
        const bid = f?.gene_index?.[sym];
        if (!cancelled) flanks = bid ? { bid, win: f[bid] || null } : null;
      } catch { /* detail upgrade stays hidden */ }
    })();
    return () => { cancelled = true; };
  });
  $effect(() => {
    const sym = gene.symbol;
    if (!sym) return;
    let cancelled = false;
    (async () => {
      try {
        const [gm, os] = await Promise.all([
          fetch('data/gene_orthogroups.json').then((r) => r.ok ? r.json() : null),
          fetch('data/orthogroups/og_summary.json').then((r) => r.ok ? r.json() : null),
        ]);
        if (cancelled) return;
        const mapping = gm?.genes?.[sym];
        if (mapping) ortho = { mapping, ogStats: os?.[mapping.og] || null };
      } catch { /* orthology stays hidden */ }
    })();
    return () => { cancelled = true; };
  });
  $effect(() => {
    const sym = gene.symbol;
    let alive = true;
    (async () => {
      try {
        const rows = await db.getPresenceCallsForGene(sym);
        if (!alive) return;
        const m = {};
        for (const r of rows || []) m[r.species] = r.status;
        presenceMap = Object.keys(m).length ? m : null;
      } catch { if (alive) presenceMap = null; }
    })();
    return () => { alive = false; };
  });

  // Host vs viral (falls back to category for curated records without wiki data)
  let geneKind = $derived(
    wiki?.kind === 'viral' || ['Viral Protein', 'Viral Segment'].includes(gene.category)
      ? 'viral' : 'host'
  );

  let avianSpecies = $derived((wiki?.species_studied || []).filter(s => s.avian === true));
  let mammalSpecies = $derived((wiki?.species_studied || []).filter(s => s.avian === false));
  let otherSpecies = $derived((wiki?.species_studied || []).filter(s => s.avian == null));

  const REL_GROUPS = [
    ['upstream', 'Upstream'], ['downstream', 'Downstream'],
    ['physical', 'Physical interactions'], ['viral', 'Viral dependency & support'],
  ];
  const MECH_ARROW = { activation: '\u2192', inhibition: '\u22a2', binding: '\u2014',
    cleavage_trafficking: '\u21c4', viral_dependency: '\u21e2' };
  let relTotal = $derived(relationships
    ? relationships.upstream.length + relationships.downstream.length
      + relationships.physical.length + relationships.viral.length : 0);

  const categoryColors = {
    'Host Factor': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    'Pattern Recognition': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    'Antiviral Response': 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300',
    'ISG': 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
    'Signal Transduction': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300',
    'Receptor': 'bg-amber-100 text-amber-700 dark:text-amber-400 dark:bg-amber-900/30 dark:text-amber-300',
    'Viral Protein': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    'Viral Segment': 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
    'Host Gene': 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
  };
</script>

<div class="space-y-6">
  <!-- Back -->
  <button
    onclick={() => navigate('genes')}
    class="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
  >
    {t('genes.back_to_panel')}
  </button>

  <!-- Header -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="text-3xl font-bold font-mono text-blue-600 dark:text-blue-400">{gene.symbol}</h1>
          {#if geneKind !== 'viral'}
            <a href="#/blast?gene={gene.symbol}"
               class="px-2 py-0.5 text-xs rounded-full font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
               title={t('tip.gene.blast') || 'Search this gene\'s protein family in your browser — static WASM blastp, nothing uploaded'}>⚡ BLAST</a>
          {/if}
          <span class="px-2 py-0.5 text-xs rounded-full font-medium {geneKind === 'viral'
            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300'}">
            {geneKind === 'viral' ? 'Viral ' + (gene.category === 'Viral Segment' ? 'segment' : 'protein') : 'Host gene'}
          </span>
          <span class="px-2 py-0.5 text-xs rounded-full font-medium {categoryColors[gene.category] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}" title={gene.category}>
            {gene.category}
          </span>
          {#if gene.tier}
            <span class="px-2 py-0.5 text-xs rounded-full {gene.tier === 1 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : gene.tier === 2 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
              Tier {gene.tier}
            </span>
          {/if}
        </div>
        <p class="text-lg text-gray-700 dark:text-gray-300 mt-1">{gene.name}</p>
        {#if gene.evidence_scope === 'annotation'}
          <span class="px-2 py-0.5 text-xs rounded-full bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-200 dark:border-amber-800" data-testid="annotation-badge">
            {t('genes.annotation_badge')}
          </span>
        {/if}
        {#if hostAssoc}
          <div class="flex flex-wrap items-center gap-1.5 mt-2" data-testid="host-association">
            <span class="px-2 py-0.5 text-xs font-semibold rounded-full {
              hostAssoc.class === 'aves' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
              : hostAssoc.class === 'mammalia' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300'
              : hostAssoc.class === 'both' ? 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300'
              : hostAssoc.class === 'viral' ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
              {hostAssoc.class === 'none' ? 'no host-classified evidence yet'
                : hostAssoc.class === 'both' ? 'evidence: birds + mammals'
                : hostAssoc.class === 'aves' ? 'evidence: birds'
                : hostAssoc.class === 'mammalia' ? 'evidence: mammals'
                : hostAssoc.class === 'viral' ? 'viral protein'
                : 'evidence: ' + hostAssoc.class + ' hosts'}
            </span>
            {#if Object.values(hostAssoc.papers || {}).some(n => n > 0)}
              <span class="text-xs text-gray-500 dark:text-gray-400">·</span>
              <span class="text-xs text-gray-500 dark:text-gray-400">
                {hostAssoc.papers.aves || 0} bird · {hostAssoc.papers.mammalia || 0} mammal evidence records
              </span>
            {/if}
            {#if hostAssoc.species?.length}
              <span class="text-xs text-gray-500 dark:text-gray-400">·</span>
              <span class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md">
                studied in: {hostAssoc.species.slice(0, 8).join(', ')}{hostAssoc.species.length > 8 ? '…' : ''}
              </span>
            {/if}
          </div>
        {/if}
        {#if gene.aliases && gene.aliases.length > 0}
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Aliases: {gene.aliases.join(', ')}
          </p>
        {/if}
      </div>
      <div class="flex flex-wrap gap-2">
        <a
          href={ncbi.geneSearch(gene.symbol, 'Aves')}
          target="_blank" rel="noopener noreferrer"
          class="px-3 py-1.5 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50"
        >{t('genes.ncbi_gene')}</a>
        <a
          href={uniprot.search(gene.symbol + ' Aves')}
          target="_blank" rel="noopener noreferrer"
          class="px-3 py-1.5 text-sm bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded hover:bg-orange-200 dark:hover:bg-orange-900/50"
        >{t('lib_components_genes_GeneFullPage.uniprot')}</a>
        {#if pdb}
          <a
            href="https://www.rcsb.org/structure/{pdb.recommended}"
            target="_blank" rel="noopener noreferrer"
            class="px-3 py-1.5 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-900/50"
          >PDB: {pdb.recommended}</a>
        {/if}
        <a
          href="#/model-cyto?gene={gene.symbol}" data-testid="view-in-pathway"
          class="px-3 py-1.5 text-sm font-semibold bg-teal-600 text-white rounded hover:bg-teal-700"
          title={t('genes.genefullpage.open.the.pathway.graph', { 'gene.symbol': gene.symbol })}
        >{t('gene_full.pathway')}</a>
        {#if presenceMap && Object.keys(presenceMap).length > 0}
          <a
            href="#/phylogeny?gene={gene.symbol}" data-testid="view-in-phylogeny"
            class="px-3 py-1.5 text-sm font-semibold bg-emerald-600 text-white rounded hover:bg-emerald-700"
            title={t('genes.genefullpage.show.gene.symbol.presence', { 'gene.symbol': gene.symbol })}
          >{t('gene_full.phylogeny')}</a>
        {/if}
        {#if ortho?.mapping?.og}
          <a
            href="#/orthogroups/{ortho.mapping.og}" data-testid="view-in-orthogroup"
            class="px-3 py-1.5 text-sm font-semibold bg-sky-700 text-white rounded hover:bg-sky-800"
            title={t('tip.gene.og.confidence') || 'How confidently the gene\'s annotated proteins map to a single orthogroup'}
          >{t('gene_full.orthogroup')} · {ortho.mapping.og}</a>
        {/if}
      </div>
    </div>
  </div>

  <!-- Headline cards (moved to top 2026-11: key finding + impact-if-lost
       + ANP32 cross-link lead the page; description/profile follow) -->
  {#if gene.key_finding || gene.impact_if_absent}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4 mb-6">
      {#if gene.key_finding}
        <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
          <h2 class="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-1">{t('gene_full.key.finding')}</h2>
          <p class="text-sm text-blue-700 dark:text-blue-400">{gene.key_finding}</p>
        </div>
      {/if}
      {#if gene.impact_if_absent}
        <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
          <h2 class="text-sm font-semibold text-amber-800 dark:text-amber-300 mb-1">
            {t('gene.impact.if.lost') || 'Impact if this gene is lost'}
            <span class="ml-1 text-[10px] font-normal px-1.5 py-0.5 rounded bg-amber-200/60 text-amber-700 dark:text-amber-400">{t('gene_full.curated.not.from.paper')}</span>
          </h2>
          <p class="text-sm text-amber-800/90 dark:text-amber-200/90">{gene.impact_if_absent}</p>
        </div>
      {/if}
    </div>
  {/if}
  {#if /^ANP32[ABE]$/.test(gene.symbol || '')}
    <a href="#/anp32"
       class="block mb-6 p-4 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors">
      <span class="text-sm font-semibold text-blue-700 dark:text-blue-300">{t('genes.anp32_comparison_link')}</span>
      <span class="block text-xs text-blue-600/80 dark:text-blue-400/80 mt-0.5">
        {t('anp32.subtitle') || 'The 33-aa insert across 463 birds and every HPAI-confirmed mammal — who can support the avian influenza polymerase, and who can\'t.'}
      </span>
    </a>
  {/if}

  <!-- LLM-enriched gene profile (D92) -->
  <GeneProfile gene={gene.symbol} onhasprofile={(v) => geneProfileHasContent = v} />

  <div class="grid lg:grid-cols-2 gap-6 items-start">
    <!-- Left: curated knowledge -->
    <div class="space-y-6">
      {#if !geneProfileHasContent}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4">
        <div>
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">{t('lib_components_genes_GeneFullPage.description')}</h2>
          <p class="text-sm text-gray-600 dark:text-gray-400">{gene.description}</p>
        </div>
        {#if gene.function}
          <div>
            <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">{t('lib_components_genes_GeneFullPage.function')}</h2>
            <p class="text-sm text-gray-600 dark:text-gray-400">{gene.function}</p>
          </div>
        {/if}
        {#if gene.species_difference}
          <div>
            <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">{t('gene_full.species.differences')}</h2>
            <p class="text-sm text-gray-600 dark:text-gray-400">{gene.species_difference}</p>
          </div>
        {/if}
      </div>
      {/if}
      <!-- 3D Structure -->
      {#if pdb}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">3D Structure</h2>
            <button
              onclick={() => showViewer = !showViewer}
              class="text-xs px-2 py-1 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50"
            >
              {showViewer ? 'Hide' : 'Show'} Viewer
            </button>
          </div>
          {#if pdb.structures && pdb.structures.length > 0}
            <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {pdb.structures.length} structure{pdb.structures.length !== 1 ? 's' : ''} available
            </p>
          {/if}
          {#if pdb.note}
            <p class="text-xs text-amber-700 dark:text-amber-400 mb-2 italic">{pdb.note}</p>
          {/if}
          {#if showViewer}
            <MolecularViewer pdbId={pdb.recommended} geneName={gene.symbol} height="400px" />
            {#if pdb.structures && pdb.structures.length > 1}
              <div class="mt-2 flex flex-wrap gap-1">
                {#each pdb.structures.filter(s => s.pdb_id !== pdb.recommended) as structure}
                  <a
                    href="https://www.rcsb.org/structure/{structure.pdb_id}"
                    target="_blank" rel="noopener noreferrer"
                    class="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                    title={structure.title}
                  >{structure.pdb_id}</a>
                {/each}
              </div>
            {/if}
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <!-- Presence across sequenced genomes (full width, D103) -->
  {#if presenceMap && Object.keys(presenceMap).length > 0}
    {@const presenceEntries = Object.entries(presenceMap).sort((a, b) => a[0].localeCompare(b[0]))}
    {@const nFull = presenceEntries.filter(([, s]) => s === 'FULL').length}
    {@const nFrag = presenceEntries.filter(([, s]) => s === 'FRAGMENT').length}
    {@const nMiss = presenceEntries.filter(([, s]) => s === 'NOT_FOUND').length}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
            {t('genes.presence_across_genomes')}
          </h2>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {nFull} present · {nFrag} fragment · <button class="underline decoration-dotted hover:text-red-600 dark:text-red-400" onclick={() => { presenceFilter = 'NOT_FOUND'; presenceSearch = ''; }}>{nMiss} missing</button> of {presenceEntries.length} species — where is it lost, where is it kept
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <input
            type="search" placeholder={t('search.placeholder.filter.species') || 'Filter species…'} value={presenceSearch}
            oninput={(e) => presenceSearch = e.target.value}
            class="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white w-48"
          />
          <div class="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600 text-xs">
            <button class="px-2.5 py-1.5 {presenceFilter === 'all' ? 'bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'}" onclick={() => presenceFilter = 'all'}>All {presenceEntries.length}</button>
            <button class="px-2.5 py-1.5 {presenceFilter === 'FULL' ? 'bg-green-600 text-white' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'}" onclick={() => presenceFilter = 'FULL'}>✓ {nFull}</button>
            <button class="px-2.5 py-1.5 {presenceFilter === 'FRAGMENT' ? 'bg-amber-500 text-white' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'}" onclick={() => presenceFilter = 'FRAGMENT'}>~ {nFrag}</button>
            <button class="px-2.5 py-1.5 {presenceFilter === 'NOT_FOUND' ? 'bg-red-600 text-white' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'}" onclick={() => presenceFilter = 'NOT_FOUND'}>✗ {nMiss}</button>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
        {#each presenceEntries.filter(([sp, status]) => (presenceFilter === 'all' || status === presenceFilter) && (!presenceSearch || sp.toLowerCase().includes(presenceSearch.toLowerCase()))).slice(0, presenceShow) as [sp, status]}
          {@const sil = phylopicPath(sp, silhouettes)}
          <div class="col-span-1 min-w-0">
            <div class="flex items-stretch min-w-0">
              <a
                href="#/species-full/{encodeURIComponent(sp)}"
                class="flex-1 min-w-0 flex items-center justify-between gap-2 p-2 rounded-l-lg border text-sm {status === 'FULL'
                  ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
                  : status === 'FRAGMENT'
                    ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20'
                    : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'} hover:shadow-md transition-shadow"
              >
                <span class="flex items-center gap-2 min-w-0">
                  {#if sil}
                    <img src={sil} alt="" class="h-4 w-4 object-contain flex-shrink-0 dark:invert opacity-60" />
                  {/if}
                  <span class="italic truncate min-w-0">{sp.replace(/_/g, ' ')}</span>
                </span>
                <span class="flex-shrink-0" title={status === 'FULL' ? (t('presence.full') || 'Present (full-length)') : status === 'FRAGMENT' ? (t('presence.fragment') || 'Fragment found') : (t('presence.notfound') || 'Not found')}>
                  {status === 'FULL' ? '✓' : status === 'FRAGMENT' ? '~' : '✗'}
                </span>
              </a>
              <button
                class="px-2 rounded-r-lg border border-l-0 flex items-center justify-center {status === 'FULL'
                  ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                  : status === 'FRAGMENT'
                    ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                    : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 text-red-700 dark:text-red-300'} {inspectSpecies === sp ? 'opacity-100 font-bold' : 'opacity-70 hover:opacity-100'}"
                style="border-left: none"
                title={t('tip.gene.evidence') || 'Inspect the raw evidence — HSPs, coordinates, threshold math'}
                onclick={() => inspectSpecies = inspectSpecies === sp ? null : sp}
              >
                <svg class="w-3.5 h-3.5 {inspectSpecies === sp ? 'stroke-[2.5]' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
            </div>
            {#if inspectSpecies === sp}
              <EvidenceDrawer gene={gene.symbol} species={sp} />
            {/if}
          </div>
        {/each}
      </div>
      {#if presenceEntries.filter(([sp, status]) => (presenceFilter === 'all' || status === presenceFilter) && (!presenceSearch || sp.toLowerCase().includes(presenceSearch.toLowerCase()))).length > presenceShow}
        <button
          class="mt-3 px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          onclick={() => presenceShow += 100}
        >Show {Math.min(100, presenceEntries.filter(([sp, status]) => (presenceFilter === 'all' || status === presenceFilter) && (!presenceSearch || sp.toLowerCase().includes(presenceSearch.toLowerCase()))).length - presenceShow)} more of {presenceEntries.filter(([sp, status]) => (presenceFilter === 'all' || status === presenceFilter) && (!presenceSearch || sp.toLowerCase().includes(presenceSearch.toLowerCase()))).length}</button>
      {/if}
      <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-2">
        {t('genes.presence_legend_prefix')} <a href="#/phylogeny?gene={gene.symbol}" class="underline hover:text-emerald-600">{t('gene_full.the.phylogeny.view')}</a> {t('genes.presence_legend_suffix')}
      </p>
    </div>
  {/if}

  <!-- Orthology (OrthoFinder, 463 species) -->
  {#if ortho}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{t('gene_full.orthology.across.463.bird')}</h2>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {t('gene.og.method') || 'OrthoFinder orthogroup — a different method than the BLAST panel above (orthology from gene trees, not sequence search)'}
          </p>
        </div>
        <span class="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full font-medium
          {ortho.mapping.confidence === 'high' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
            : ortho.mapping.confidence === 'curated' ? 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300'
            : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'}"
          title={t('tip.gene.og.confidence') || 'How confidently the gene\'s annotated proteins map to a single orthogroup'}>
          {ortho.mapping.confidence} confidence
        </span>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-4 text-sm">
        <a href="#/orthogroups/{ortho.mapping.og}" class="font-mono text-sky-600 dark:text-sky-400 hover:underline">
          {ortho.mapping.og} →
        </a>
        {#if ortho.ogStats}
          <span class="text-gray-500 dark:text-gray-400">
            present in <b class="text-gray-800 dark:text-gray-200">{ortho.ogStats.n_species_present}/463</b> species
          </span>
          <span class="text-gray-500 dark:text-gray-400">{ortho.ogStats.n_proteins.toLocaleString()} proteins</span>
          {#if ortho.ogStats.single_copy}
            <span class="text-emerald-600 dark:text-emerald-400">{t('gene_full.singlecopy')}</span>
          {:else}
            <span class="text-gray-500 dark:text-gray-400">up to {ortho.ogStats.max_copies} copies</span>
          {/if}
          <span class="text-gray-500 dark:text-gray-400">{t('gene_full.tree.alignment')}</span>
        {/if}
        <a href="#/orthogroups/{ortho.mapping.og}" class="ml-auto text-xs px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">
          {t('genes.view_tree_alignment')}
        </a>
      </div>
      {#if ortho.mapping.confidence !== 'high'}
        <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {ortho.mapping.confidence === 'curated'
            ? 'Manually curated mapping (see Methods for the curation notes).'
            : 'Automatic mapping with partial agreement — treat orthogroup membership as approximate.'}
        </p>
      {/if}
    </div>
  {/if}

  <!-- Literature evidence (aggregation layer) -->
  {#if geneEv?.papers?.length || geneEv?.mechanisms?.length}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{t('gene_full.literature.evidence')}</h2>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            What the research corpus says about {gene.symbol} — {geneEv.n_papers} papers,
            {geneEv.n_mechanism_edges} mechanism edges
          </p>
        </div>
        <div class="flex gap-2 text-[10px]">
          {#if geneEv.n_studied}
            <span class="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 font-semibold">{geneEv.n_studied} studied</span>
          {/if}
          {#if geneEv.n_perturbed}
            <span class="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300 font-semibold">{geneEv.n_perturbed} perturbed</span>
          {/if}
          {#if geneEv.n_measured}
            <span class="px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 font-semibold">{geneEv.n_measured} measured</span>
          {/if}
        </div>
      </div>

      {#if geneEv.mechanisms?.length}
        <div class="mb-4">
          <h3 class="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">Mechanistic interactions ({geneEv.mechanisms.length})</h3>
          <div class="space-y-1.5">
            {#each geneEv.mechanisms.slice(0, 5) as m, i (i)}
              <div class="flex items-start gap-2 text-xs">
                <span class="font-mono px-1.5 py-0.5 rounded {m.verified ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-gray-100 text-gray-600'} shrink-0">
                  {m.verified ? '✓' : '?'}
                </span>
                <div class="min-w-0">
                  <span class="font-medium text-gray-800 dark:text-gray-200">{m.interaction}</span>
                  <span class="text-gray-500 dark:text-gray-400"> — {ft(m.eh) || m.effect}</span>
                  <a href="#/papers/{m.paper_id}" class="ml-1 text-blue-600 dark:text-blue-400 hover:underline text-[10px]">[paper]</a>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if geneEv.papers?.length}
        <div>
          <h3 class="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">Papers ({geneEv.papers.length})</h3>
          <div class="space-y-2 max-h-64 overflow-y-auto">
            {#each geneEv.papers.slice(0, 10) as p, i (i)}
              <div class="text-xs border-l-2 pl-3 {p.role === 'studied' ? 'border-blue-400' : p.role === 'perturbed' ? 'border-purple-400' : p.role === 'measured' ? 'border-teal-400' : 'border-gray-200'}">
                <div class="flex items-baseline gap-2">
                  <a href="#/papers/{p.id}" class="font-medium text-gray-800 dark:text-gray-200 hover:underline">{p.title}</a>
                  <span class="text-gray-500 dark:text-gray-400 shrink-0">({p.year})</span>
                  <span class="text-[9px] px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 shrink-0">{p.role}</span>
                </div>
                {#if p.finding && p.finding !== 'null'}
                  <p class="text-gray-500 dark:text-gray-400 mt-0.5 italic">{p.finding}</p>
                {/if}
              </div>
            {/each}
            {#if geneEv.papers.length > 10}
              <p class="text-[10px] text-gray-500 dark:text-gray-400">{t('genes.more_papers', { n: geneEv.papers.length - 10 })}</p>
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {/if}

  {#if geneCtx?.length}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
      <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{t('gene_full.genomic.context')}</h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 mb-3">
        Neighbouring host-panel genes within ±2.5 Mb. Blue = {gene.symbol}; grey = panel neighbours;
        <span class="text-gray-500 dark:text-gray-400">✦ outlined = named flanking genes</span> from the current NCBI annotation of
        {#if flanks} the {flanks.bid.replace(/^b_/, '').replace(/_/g, ' ')} block{/if} (▸/◂ = strand, where available).
      </p>
      <div class="space-y-1">
        {#each geneCtx.slice(0, 5) as c}
          {@const f = flanks?.win?.[c.sci] || null}
          {@const lo = f ? f.lo : Math.min(c.self[0], ...c.nb.map((n) => n.start))}
          {@const hi = f ? f.hi : Math.max(c.self[1], ...c.nb.map((n) => n.end))}
          {@const span = Math.max(hi - lo, 1)}
          <div class="flex items-center gap-3">
            <div class="w-40 shrink-0 text-right text-[11px] text-gray-500 dark:text-gray-400">
              <span class="font-medium text-gray-700 dark:text-gray-300">{c.sci.replace(/([A-Z])\w*\s/, '$1. ')}</span>
              <span> · chr{f ? f.chrom : c.chrom}</span>
              {#if f}<span class="{f.aligned === false ? 'text-amber-700' : 'text-gray-500 dark:text-gray-400'}" title={f.aligned === false ? 'Track located by coordinate overlap only — verify region' : 'Detailed track: named flanking genes from the current NCBI annotation of ' + c.assembly}>{f.aligned === false ? ' ⚠' : ' ✦'}</span>{/if}
            </div>
            <div class="relative flex-1 h-6 rounded bg-gray-50 dark:bg-gray-900/60 border border-gray-100 dark:border-gray-700/50 overflow-hidden">
              {#if f}
                {#each f.genes as g}
                  {@const isSelf = g.s.toUpperCase() === gene.symbol.toUpperCase()}
                  {@const left = ((g.b - lo) / span) * 100}
                  {@const width = Math.max(0.35, ((g.e - g.b) / span) * 100)}
                  <button
                    class="absolute top-0.5 h-5 rounded-sm overflow-hidden whitespace-nowrap
                      {g.core || isSelf ? 'text-white' : 'bg-transparent border border-gray-300 dark:border-gray-600'}"
                    style="left:{left}%; width:{width}%; background:{isSelf ? '#2563eb' : g.core ? '#0d9488' : 'transparent'}"
                    title="{g.s} · chr{f.chrom}:{(g.b / 1e6).toFixed(2)} Mb{g.o ? ` · strand ${g.o}` : ''}{g.tr ? ' · ' + (t('gene.position.translated') || 'position translated (older panel coords)') : ''}{isSelf ? ' — ' + (t('gene.this.gene') || 'this gene') : g.core ? ' (' + (t('gene.block.core') || 'block core') + ')' : ' (' + (t('gene.flanking') || 'annotated flanking gene') + ')'}"
                    onclick={() => navigate('genes', g.s, {})}
                  >{#if width > 7}<span class="text-[9px] leading-5 px-0.5 block truncate">{g.o === '-' ? '◂' : g.o === '+' ? '▸' : ''} {g.s}</span>{/if}</button>
                {/each}
              {:else}
                {#each c.nb as n}
                  <button
                    class="absolute top-0.5 h-5 rounded-sm bg-gray-400 dark:bg-gray-500 opacity-70 hover:opacity-100"
                    style="left:{((n.start - lo) / span) * 100}%; width:{Math.max(0.8, ((n.end - n.start) / span) * 100)}%"
                    title="{n.sym} · chr{c.chrom}:{(n.start / 1e6).toFixed(2)} Mb{n.o ? ` · strand ${n.o}` : ''} — {t('gene.view.gene') || 'view gene'}"
                    onclick={() => navigate('genes', n.sym, {})}
                  ></button>
                {/each}
                <div
                  class="absolute top-0.5 h-5 rounded-sm bg-blue-600 text-white text-[9px] leading-5 px-1 overflow-hidden whitespace-nowrap"
                  style="left:{((c.self[0] - lo) / span) * 100}%; width:{Math.max(2, ((c.self[1] - c.self[0]) / span) * 100)}%"
                  title="{gene.symbol} · chr{c.chrom}:{(c.self[0] / 1e6).toFixed(2)} Mb{c.o ? ` · ${t('genes.strand', { s: c.o })}` : ''}"
                >{c.o === '-' ? '◂' : c.o === '+' ? '▸' : ''} {gene.symbol}</div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
      <a href="#/synteny{flanks ? '/' + flanks.bid : ''}" class="mt-3 inline-block text-xs text-blue-600 dark:text-blue-400 hover:underline">
        {t('genes.explore_synteny')}
      </a>
    </div>
  {/if}

  <!-- Mechanistic connections -->
  {#if relationships && relTotal > 0}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6" data-testid="gene-connections-section">
      <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">{t('gene_full.mechanistic.connections')}</h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">{t('gene_full.curated.pathway.wiring.plus')}</p>
      <div class="grid gap-4 md:grid-cols-2">
        {#each REL_GROUPS as [key, label]}
          {@const items = relationships[key] || []}
          {#if items.length}
            <div class="border border-gray-100 dark:border-gray-700 rounded-lg p-3">
              <h3 class="text-[10px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">{label} · {items.length}</h3>
              <div class="space-y-2.5">
                {#each items as rel}
                  <div class="text-sm" data-testid="gene-connection-item">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="text-slate-600 dark:text-slate-400" title={rel.mechanism}>{MECH_ARROW[rel.mechanism] || '\u2192'}</span>
                      <a href="#/genes/{rel.counterpart}" class="font-mono font-semibold text-blue-600 dark:text-blue-400 hover:underline">{rel.counterpart}</a>
                      <span class="text-xs text-gray-500 dark:text-gray-400">{rel.label}</span>
                      {#if rel.evidence?.length}
                        <span class="px-1.5 py-0.5 text-[10px] rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 font-semibold">{rel.evidence.length}ev</span>
                      {/if}
                    </div>
                    {#if rel.evidence?.length}
                      <div class="mt-1 ml-6 space-y-1">
                        {#each rel.evidence.slice(0, 3) as ev}
                          <div class="text-xs text-gray-500 dark:text-gray-400">
                            <a href="#/papers/{ev.paper_id}" class="hover:underline" title={ev.quote}>
                              {ev.year || ''} {(ev.journal || ev.paper_id || '').slice(0, 42)}
                            </a>
                            {#if ev.species || ev.timepoints || ev.location}
                              <span class="text-gray-500 dark:text-gray-400">
                                {#if ev.species} · {vt(ev.species)}{/if}
                                {#if ev.location} · {vt(ev.location)}{/if}
                                {#if ev.timepoints} · {ev.timepoints}{/if}
                              </span>
                            {/if}
                            {#if ev.strain}
                              <span class="ml-1">
                                {#each ev.strain.split(',').map(s => s.trim()).filter(Boolean) as st}
                                  <a href="#/papers?q={encodeURIComponent(st)}" class="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 hover:underline font-mono" data-testid="strain-chip">{st}</a>
                                {/each}
                              </span>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}

    <!-- Right: literature synthesis -->
    {#if wiki}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-lg font-bold text-gray-900 dark:text-white">{t('gene_full.from.the.literature')}</h2>
          <div class="flex flex-wrap items-center gap-1.5">
            {#if wiki.host_scope}
              <ScopeTags scope={wiki.host_scope} avianPapers={wiki.avian_papers} mammalianPapers={wiki.mammalian_papers} />
            {/if}
            <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              {wiki.paper_count} papers · {wiki.central_count} central
            </span>
          </div>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400">
          {t('gene.evidence.synth') || 'Synthesized from verified LLM extraction of full-text papers. Every claim is cited.'}
        </p>

        <!-- Roles -->
        {#if wiki.roles?.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">{t('gene_full.role.in.infection')}</h3>
            <div class="space-y-2">
              {#each wiki.roles as role}
                <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                  <div class="flex items-start justify-between gap-2 mb-1">
                    <span class="text-xs font-medium {role.importance === 'central'
                      ? 'text-purple-700 dark:text-purple-300'
                      : 'text-gray-500 dark:text-gray-400'}">
                      {role.importance === 'central' ? '★ central' : 'mentioned'} · {role.year ?? ''}
                    </span>
                    <a href="#/papers/{role.paper_id}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline line-clamp-1" title={role.title}>
                      {role.paper_id}
                    </a>
                  </div>
                  <p class="text-sm text-gray-600 dark:text-gray-400">{ft(role.fh) || role.role}</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Key numbers -->
        {#if wiki.key_findings?.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">{t('gene_full.key.numbers')}</h3>
            <div class="space-y-1.5">
              {#each wiki.key_findings as f}
                <div class="flex items-start gap-2 text-xs">
                  <span class="flex-shrink-0 px-1.5 py-0.5 rounded font-mono font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300">
                    {f.value}
                  </span>
                  <span class="text-gray-600 dark:text-gray-400 min-w-0">
                    {ft(f.fh) || f.finding}
                    <a href="#/papers/{f.paper_id}" class="text-blue-600 dark:text-blue-400 hover:underline" title={f.title}>[{f.paper_id}, {f.year ?? ''}]</a>
                  </span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if wiki.methods_findings?.length > 0}
          <details class="group">
            <summary class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide cursor-pointer list-none flex items-center gap-1 hover:text-gray-600 dark:hover:text-gray-300">
              <svg class="w-3 h-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
              {t('species_detail.sequencing.methods')} ({wiki.methods_findings.length})
            </summary>
            <div class="space-y-1.5 mt-1.5">
              {#each wiki.methods_findings as f}
                <div class="flex items-start gap-2 text-xs">
                  <span class="flex-shrink-0 px-1.5 py-0.5 rounded font-mono font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                    {f.value}
                  </span>
                  <span class="text-gray-500 dark:text-gray-400 min-w-0">
                    {ft(f.fh) || f.finding}
                    <a href="#/papers/{f.paper_id}" class="text-blue-600 dark:text-blue-400 hover:underline" title={f.title}>[{f.paper_id}, {f.year ?? ''}]</a>
                  </span>
                </div>
              {/each}
            </div>
          </details>
        {/if}

        <!-- Conclusions -->
        {#if wiki.conclusions?.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2 uppercase tracking-wide">{t('gene_full.study.conclusions')}</h3>
            <div class="space-y-1.5">
              {#each wiki.conclusions as c}
                <blockquote class="text-xs text-gray-600 dark:text-gray-400 border-l-2 border-gray-300 dark:border-gray-600 pl-2">
                  {ft(c.fh) || c.conclusion}
                  <a href="#/papers/{c.paper_id}" class="text-blue-600 dark:text-blue-400 hover:underline ml-1" title={c.title}>[{c.paper_id}, {c.year ?? ''}]</a>
                </blockquote>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Mutations -->
        {#if wiki.mutations?.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">{t('lib_components_genes_GeneFullPage.mutations')}</h3>
            <div class="flex flex-wrap gap-1.5">
              {#each wiki.mutations as m}
                <a
                  href="#/mutations/{m.mutation}"
                  class="text-xs px-2 py-1 rounded font-mono bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-900/50"
                  title="{m.mutation} — {t('genes.n_papers', { n: m.paper_count })}"
                >{m.mutation}</a>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Studied in: avian first, mammals separate -->
        {#if avianSpecies.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-sky-700 dark:text-sky-300 mb-1.5 uppercase tracking-wide">{t('genes.studied_in_birds')}</h3>
            <div class="flex flex-wrap gap-1.5">
              {#each avianSpecies as s}
                <a
                  href="#/species/{encodeURIComponent(s.scientific || s.name)}"
                  class="text-xs px-2 py-1 rounded bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300 hover:underline hover:bg-sky-200 dark:hover:bg-sky-900/50"
                  title="{t('genes.n_papers', { n: s.papers })}{s.scientific ? ' — ' + s.scientific : ''}"
                >
                  {s.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}
        {#if mammalSpecies.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-orange-700 dark:text-orange-300 mb-1.5 uppercase tracking-wide">{t('genes.also_studied_mammals')}</h3>
            <div class="flex flex-wrap gap-1.5">
              {#each mammalSpecies as s}
                <a
                  href="#/species/{encodeURIComponent(s.scientific || s.name)}"
                  class="text-xs px-2 py-1 rounded bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 hover:underline hover:bg-orange-200 dark:hover:bg-orange-900/50"
                  title="{t('genes.n_papers', { n: s.papers })}{s.scientific ? ' — ' + s.scientific : ''}"
                >
                  {s.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}
        {#if otherSpecies.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">{t('gene_full.other.hosts')}</h3>
            <div class="flex flex-wrap gap-1.5">
              {#each otherSpecies as s}
                <a
                  href="#/species/{encodeURIComponent(s.scientific || s.name)}"
                  class="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:underline"
                  title={t('genes.genefullpage.papers.paper.papers.host', { n: s.papers })}
                >
                  {s.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {:else}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="text-center text-gray-500 dark:text-gray-400">
          <p class="font-medium mb-2">{t('gene_full.not.yet.covered.by')}</p>
          <p class="text-sm max-w-md mx-auto">
            {#if gene.panel_only}
              {t('gene.panel.only.desc') || 'This gene is part of the Roost immune-gene panel and its presence has been checked across sequenced bird genomes (left), but no paper in our analysed corpus reports on it yet.'}
            {:else}
              {t('gene.no.literature') || 'No extracted literature for this gene yet.'}
            {/if}
            {#if gene.importance && gene.importance !== 'standard'}
              The <strong>{gene.importance === 'critical' ? '● critical' : '◐ high'}</strong>
              importance label reflects panel curation and established immunology —
              not claims from our corpus. Adding relevant papers will fill this section.
            {/if}
          </p>
        </div>
      </div>
    {/if}

  <!-- Papers (full width) -->
  {#if gene.papers && gene.papers.length > 0}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-1">
        {t('gene_full.research.papers')} ({gene.papers.length})
      </h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
        {t('gene_full.research.mentions.total', { n: formatNumber(gene.total_mentions) })}
      </p>
      <div class="grid md:grid-cols-2 gap-3">
        {#each pagedPapers as paper}
          <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-sm">
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                {#if paper.url}
                  <a href={paper.url} target="_blank" rel="noopener noreferrer"
                    class="font-medium text-blue-600 dark:text-blue-400 hover:underline line-clamp-2">
                    {paper.title || paper.paper_id}
                  </a>
                {:else}
                  <span class="font-medium text-gray-700 dark:text-gray-300 line-clamp-2">
                    {paper.title || paper.paper_id}
                  </span>
                {/if}
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {paper.authors || ''}{paper.year ? ` (${paper.year})` : ''}
                </p>
                {#if paper.journal}
                  <p class="text-xs text-gray-500 dark:text-gray-400 italic">{paper.journal}</p>
                {/if}
              </div>
              {#if paper.mentions != null}
                <span class="flex-shrink-0 px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                  {t('gene_full.research.mentions.count', { n: paper.mentions })}
                </span>
              {/if}
            </div>
            {#if paper.passage}
              <p class="text-xs text-gray-600 dark:text-gray-400 mt-2 italic border-l-2 border-gray-300 dark:border-gray-600 pl-2 line-clamp-3">
                "{paper.passage.slice(0, 200)}{paper.passage.length > 200 ? '...' : ''}"
              </p>
            {/if}
            {#if paper.doi}
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                DOI: <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">{paper.doi}</a>
              </p>
            {/if}
          </div>
        {/each}
      </div>
      {#if papersPageCount > 1}
        <div class="flex items-center justify-center gap-3 mt-4">
          <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-40"
            disabled={papersPage === 0}
            onclick={() => (papersPage = Math.max(0, papersPage - 1))}>{t('gene_full.research.prev')}</button>
          <span class="text-xs text-gray-500 dark:text-gray-400">
            {t('gene_full.research.page.of', { i: papersPage + 1, j: papersPageCount })}
          </span>
          <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-40"
            disabled={papersPage >= papersPageCount - 1}
            onclick={() => (papersPage = Math.min(papersPageCount - 1, papersPage + 1))}>{t('gene_full.research.next')}</button>
        </div>
      {/if}
    </div>
  {/if}
</div>
