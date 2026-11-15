<script>
  import { t, ft, pt, tc } from '../lib/stores/i18n.svelte.js';
  import { announce } from '../lib/stores/a11y.svelte.js';
  import { onMount } from 'svelte';
  import { navigate, subscribe as routerSubscribe, getRoute, updateParams } from '../lib/stores/router.js';
  import { vt } from '../lib/stores/i18n.svelte.js';

  // Host-class associations (D84): aves / mammalia / both / other / none
  let hostAssoc = $state({});
  let geneHostSpecies = $state({});
  let selectedHostSpecies = $derived(selectedGene
    ? geneHostSpecies[canonicalOf(selectedGene.symbol)] || geneHostSpecies[selectedGene.symbol]
    : null);
  const HOST_CLASS_META = {
    aves: { label: 'aves', cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300', title: 'Evidence in birds only' },
    mammalia: { label: 'mammalia', cls: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300', title: 'Evidence in mammals only' },
    both: { label: 'aves+mammalia', cls: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300', title: 'Evidence in birds AND mammals' },
    other: { label: 'other hosts', cls: 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300', title: 'Evidence only in other hosts/cell systems' },
    none: { label: 'no host evidence', cls: 'bg-gray-50 text-gray-600 dark:text-gray-400 dark:bg-gray-800 dark:text-gray-500 dark:text-gray-400', title: 'No host-classified corpus evidence yet' },
    viral: { label: 'viral', cls: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300', title: 'Viral protein' },
  };
  function hostClassOf(sym) {
    return hostAssoc[canonicalOf(sym)]?.class || null;
  }
  function hostSpeciesOf(sym) {
    return hostAssoc[canonicalOf(sym)]?.species || [];
  }
  import { ncbi, uniprot } from '../lib/utils/urls.js';
  import { formatNumber } from '../lib/utils/format.js';
  import GeneFullPage from '../lib/components/genes/GeneFullPage.svelte';
  import ScopeTags from '../lib/components/common/ScopeTags.svelte';
  import InfoDot from '../lib/components/common/InfoDot.svelte';

  let genes = $state([]);

  // a11y: announce the gene-panel size to screen readers once loaded
  let lastAnnouncedGenes = $state(-1);
  $effect(() => {
    const n = genes.length;
    if (n > 0 && n !== lastAnnouncedGenes) {
      lastAnnouncedGenes = n;
      announce(t('a11y.announce.genes.results', { n }));
    }
  });
  let pdbStructures = $state({});
  let wikiGenes = $state({});
  let papersWithGenes = $state(null); // true corpus count (uncapped by role display)
  let loading = $state(true);
  let error = $state(null);
  let showGenome = $state(false); // D105: 'genome available' — genes with presence calls (was: annotation-only)
  let connectionInfo = $state({});   // canonical symbol → {connections, evidence}
  let stageAssignment = $state({});
  let relationshipEdges = $state([]); // published edges (curated + approved)

  // ---- canonical identity (D78): every record resolves through one alias
  // index so curated, wiki, presence, alias and relationship records can
  // never fork into duplicate cards. Mirrors data/genes/gene_config.json.
  const EXPLICIT_ALIAS = {
    'RIG-I': 'DDX58', 'RIGI': 'DDX58', 'MDA5': 'IFIH1', 'LGP2': 'DHX58',
    'PKR': 'EIF2AK2', 'TNF': 'TNFSF15', 'IL-18': 'IL18', 'IFITM': 'IFITM3',
    'ANP32': 'ANP32A', 'IFNA': 'IFNA1', 'JAK': 'JAK2', 'GBP': 'GBP1',
    'INOS': 'NOS2', 'IL-1BETA': 'IL1B',
  };
  const aliasIndex = new Map();  // lowercase symbol-or-alias → canonical
  function indexRecord(g) {
    if (!g?.symbol) return;
    const explicit = EXPLICIT_ALIAS[g.symbol.toUpperCase()];
    const canonical = explicit || g.symbol;
    for (const s of [g.symbol, ...(g.aliases || []), canonical]) {
      const key = String(s).toLowerCase();
      if (!aliasIndex.has(key)) aliasIndex.set(key, canonical);
    }
  }
  function canonicalOf(sym) {
    if (!sym) return sym;
    const key = String(sym).toLowerCase();
    return aliasIndex.get(key) || EXPLICIT_ALIAS[String(sym).toUpperCase()] || sym;
  }
  function indexed(canonical) {
    return aliasIndex.get(String(canonical).toLowerCase()) === canonical
      || [...aliasIndex.values()].includes(canonical);
  }
  function connectionsOf(sym) {
    return connectionInfo[canonicalOf(sym)] || { connections: 0, evidence: 0 };
  }
  function relationshipsFor(sym) {
    const canon = canonicalOf(sym);
    const groups = { upstream: [], downstream: [], physical: [], viral: [] };
    for (const e of relationshipEdges) {
      const from = canonicalOf(e.from), to = canonicalOf(e.to);
      if (from !== canon && to !== canon) continue;
      const outgoing = from === canon;
      const rec = { ...e, counterpart: outgoing ? e.to : e.from, outgoing };
      if (e.mechanism === 'viral_dependency') groups.viral.push(rec);
      else if (e.mechanism === 'binding' || e.mechanism === 'cleavage_trafficking') groups.physical.push(rec);
      else if (outgoing) groups.downstream.push(rec);
      else groups.upstream.push(rec);
    }
    for (const g of Object.values(groups)) g.sort((a, b) => a.counterpart.localeCompare(b.counterpart));
    return groups;
  }
  function stageOf(sym) {
    return stageAssignment[canonicalOf(sym)]?.stage || null;
  }
  const STAGE_SHORT = {
    entry: 'Entry', sensing: 'Recognition', signaling: 'Signalling',
    cytokine_storm: 'Inflammation', effectors: 'Effectors',
    dependency: 'Viral dependency', celldeath: 'Cell death',
    adaptive: 'Adaptive', hostrange: 'Host range',
  };

  // Full-page gene (#/genes/ANP32A) vs panel view (#/genes)
  let fullPageGene = $state(null);

  let selectedGene = $state(null);
  let searchQuery = $state('');

  // Wiki (LLM-extracted) data for the selected gene
  let selectedWiki = $derived(selectedGene ? wikiGenes[selectedGene.symbol] : null);
  let slimRels = $derived(selectedGene ? relationshipsFor(selectedGene.symbol) : null);
  let slimTotal = $derived(slimRels ? slimRels.upstream.length + slimRels.downstream.length
    + slimRels.physical.length + slimRels.viral.length : 0);

  // Resolve a URL id to a gene record (symbol or alias match, canonicalised)
  function resolveGene(id) {
    const canonical = canonicalOf(id);
    return genes.find(g =>
      g.symbol === canonical || canonicalOf(g.symbol) === canonical ||
      (g.aliases || []).some(a => canonicalOf(a) === canonical)
    ) || genes.find(g =>
      g.symbol.toLowerCase() === id.toLowerCase() ||
      (g.aliases || []).some(a => a.toLowerCase() === id.toLowerCase())
    ) || null;
  }

  // Shared URL-params → state restore (used on load AND on SPA nav).
  // Absent param = its default: the URL is the whole truth, so navigating
  // from ?q=rig to ?genome=1 must clear the search. Echo-safe: our own
  // sync effect only ever omits params that already hold default values.
  const applyParams = (p = {}) => {
    searchQuery = p.q || '';
    kindFilter = ['all', 'host', 'viral'].includes(p.kind) ? p.kind : 'all';
    showGenome = p.genome === '1' || p.annotation === '1';
    tierFilter = ['1','2','3','lit'].includes(p.tier) ? p.tier : 'all';
    stageFilter = p.stage || 'all';
    hostClassFilter = ['aves','mammalia','both','other','none','viral'].includes(p.host) ? p.host : 'all';
    viewMode = (p.view === 'detail' && showGenome) ? 'detail' : 'list';
    if (['variable', 'missing', 'present', 'fragment', 'name'].includes(p.sort)) detailSort = p.sort;
    if (p.dir === 'asc' || p.dir === 'desc') detailSortDir = p.dir;
    categoryFilter = p.category || 'all';
    page = Math.max(1, parseInt(p.page, 10) || 1);
    selectedGene = p.gene ? (resolveGene(p.gene) || null) : null;
  };

  const applyRoute = route => {
    if (route.page === 'genes') {
      if (route.id) {
        // #/genes/{symbol} — the full gene page
        fullPageGene = resolveGene(route.id);
        if (fullPageGene) selectedGene = fullPageGene;
      } else {
        fullPageGene = null;
        // #/genes?gene={symbol} — list view with that gene selected (sidebar)
        const q = route.params?.gene || null;
        selectedGene = q ? (resolveGene(q) || null) : (loading ? selectedGene : null);
        // SPA navigation with changed filter params applies them too
        if (urlSyncReady) applyParams(route.params || {});
      }
    }
  };

  onMount(async () => {
    try {
      const [genesResponse, pdbResponse, wikiResponse, catalogueResponse,
             relResponse, stageResponse, hostResponse, hostSpeciesResponse] = await Promise.all([
        fetch('data/genes.json'),
        fetch('data/gene_pdb_structures.json'),
        fetch('data/wiki_genes.json'),
        fetch('data/gene_catalogue.json'),
        fetch('data/gene_relationships.json').then((r) => r.ok ? r.json() : { edges: [] }).catch(() => ({ edges: [] })),
        fetch('data/gene_stage_assignment.json').then((r) => r.ok ? r.json() : {}).catch(() => ({})),
        fetch('data/gene_host_association.json').then((r) => r.ok ? r.json() : { genes: {} }).catch(() => ({ genes: {} })),
        fetch('data/gene_host_species.json').then((r) => r.ok ? r.json() : {}).catch(() => ({})),
      ]);
      const genesData = await genesResponse.json();
      genes = genesData.genes || [];

      // canonical index seeded by curated records first (they win conflicts)
      for (const g of genes) indexRecord(g);

      // Reviewed connection aggregates from the PUBLISHED relationship file
      // (approved evidence only — pending/rejected never publish)
      const connAgg = {};
      for (const e of relResponse.edges || []) {
        if (!e.evidence?.length) continue;
        for (const sym of [e.from, e.to]) {
          const key = canonicalOf(sym);
          const c = connAgg[key] ??= { connections: 0, evidence: 0 };
          c.connections += 1;
          c.evidence += e.evidence.length;
        }
      }
      connectionInfo = connAgg;
      relationshipEdges = relResponse.edges || [];
      const hostMap = {};
      for (const [sym, rec] of Object.entries(hostResponse.genes || {})) {
        hostMap[canonicalOf(sym)] = rec;
      }
      hostAssoc = hostMap;
      // per-gene detected host species (from typed claims; registry-derived)
      geneHostSpecies = hostSpeciesResponse || {};
      // stage map keyed canonically — records with a null stage are
      // legacy-symbol duplicates (host_panel_v2 dedup still queued); they
      // must never clobber a real assignment (e.g. RIGI:{null} over
      // DDX58:{sensing})
      const stageMap = {};
      for (const [sym, rec] of Object.entries(stageResponse)) {
        if (rec?.stage == null) continue;
        stageMap[canonicalOf(sym)] = rec;
      }
      stageAssignment = stageMap;

      // Presence catalogue — panel-only genes get auto-generated pages.
      // Per-gene species maps load lazily on the gene page (DuckDB);
      // nothing eager here anymore.
      let presenceCatalogue = null;
      if (catalogueResponse.ok) {
        try {
          const catDoc = await catalogueResponse.json();
          presenceCatalogue = catDoc.gene_catalogue || null;
          catalogueHeader = catDoc;
        } catch { /* ok */ }
      }

      if (pdbResponse.ok) {
        const pdbData = await pdbResponse.json();
        pdbStructures = pdbData.genes || {};
      }

      if (wikiResponse.ok) {
        const wikiData = await wikiResponse.json();
        wikiGenes = wikiData.genes || {};
        papersWithGenes = wikiData.papers_with_genes || null;
      }

      // Merge: curated panel first, then corpus-discovered (wiki-only) genes.
      // Canonical-ID merge: a wiki gene whose symbol canonicalises to an
      // already-known record enriches it instead of forking a duplicate card.
      const known = new Set(genes.map(g => canonicalOf(g.symbol)));
      const wikiOnly = Object.values(wikiGenes)
        .filter(w => !known.has(canonicalOf(w.symbol)))
        .sort((a, b) => b.paper_count - a.paper_count)
        .map(w => ({
          symbol: w.symbol,
          name: w.name && w.name !== w.symbol ? w.name : w.symbol,
          aliases: [],
          category: w.category || 'Host Gene',
          tier: null,
          wiki_only: true,
          description: w.roles?.[0] ? (ft(w.roles[0].fh) || w.roles[0].role) : t('genes.fallback_desc'),
          paper_count: w.paper_count,
          total_mentions: 0,
          papers: (w.roles || []).map(r => ({
            paper_id: r.paper_id, title: pt(r.paper_id, 'title') || r.title, authors: '',
            year: r.year, journal: r.journal, doi: null, url: '',
            mentions: null, passage: ''
          }))
        }));
      genes = [...genes, ...wikiOnly];
      for (const g of wikiOnly) indexRecord(g);

      // Merge presence-panel genes not already covered — these get pages with
      // the 15-species presence matrix + panel metadata (canonical-ID match)
      if (presenceCatalogue) {
        const known2 = new Set(genes.map(g => canonicalOf(g.symbol)));
        const panelOnly = Object.entries(presenceCatalogue)
          .filter(([sym]) => !known2.has(canonicalOf(sym)))
          .map(([sym, info]) => ({
            symbol: sym,
            name: info.name || sym,
            aliases: info.aliases || [],
            category: info.category || 'Immune (GO:0002376)',
            tier: null,
            panel_only: true,
            description: info.notes || info.name || (t('genes.panel.fallback') || 'Immune gene from the Roost host panel — searched across sequenced bird genomes.'),
            paper_count: 0,
            total_mentions: 0,
            papers: [],
            importance: info.importance,
            impact_if_absent: info.impact_if_absent || null,
            description: info.function || info.notes || info.name || (t('genes.panel.fallback') || 'Immune gene from the Roost host panel — searched across sequenced bird genomes.')
          }));
        // critical/high first, then alphabetical
        panelOnly.sort((a, b) => {
          const imp = { critical: 0, high: 1, standard: 2 };
          return (imp[a.importance] ?? 3) - (imp[b.importance] ?? 3) || a.symbol.localeCompare(b.symbol);
        });
        genes = [...genes, ...panelOnly];
        for (const g of panelOnly) indexRecord(g);

        // Enrich genes already listed (curated + wiki) with presence + importance
        for (const g of genes) {
          const cat = presenceCatalogue[g.symbol.toUpperCase()];
          // literature scope unless the catalogue says annotation-only;
          // curated/wiki records are literature by construction
          g.evidence_scope = cat?.evidence_scope === 'annotation'
            ? 'annotation' : 'literature';
          if (cat) {
            if (!g.importance) g.importance = cat.importance;
            if (!g.impact_if_absent) g.impact_if_absent = cat.impact_if_absent || null;
            // richer function from catalogue (UniProt/curated) when the gene
            // has no curated description of its own — prefer the translated
            // content layer (tc) when available, fall back to the en data
            const fnT = tc(`gene.${g.symbol}.function`);
            const fnText = fnT || cat.function;
            if (fnText && (!g.description || g.description.length < 40)) {
              g.description = fnText;
            }
            if (!g.function && fnText) g.function = fnText;
            // catalogue aliases (MHC-B nomenclature etc.) attach to every
            // record — wiki-backed cards otherwise carry none, so searching
            // "MHC" or "tapasin" would miss BF2/TAPBP
            if (cat.aliases?.length) {
              g.aliases = [...new Set([...(g.aliases || []), ...cat.aliases])];
              indexRecord(g);
            }
          }
        }
      }

      loading = false;
      // Data may arrive after the route fired — re-check once loaded
      applyRoute(getRoute());

      // D104/D105: restore shareable filter state from the URL — BEFORE the
      // presence await: ensurePresenceSummary() initialises DuckDB (seconds
      // on a cold load) and deep links used to sit unfiltered behind it.
      // The sync effect is guarded by urlSyncReady, so this can't be raced.
      const p0 = getRoute()?.params || {};
      applyParams(p0);
      // Flip the sync guard BEFORE the presence await: DuckDB init takes
      // seconds, and user interactions during that window used to be
      // clobbered when the router subscription finally attached and fired
      // applyRoute with the still-paramless hash.
      urlSyncReady = true;

      // presence summary powers the genome-available filter + detail view
      await ensurePresenceSummary();
    } catch (e) {
      error = e.message;
      loading = false;
    }

    return routerSubscribe(applyRoute);
  });

  // D104: keep the URL in sync so exact searches are shareable
  $effect(() => {
    if (loading || fullPageGene || !urlSyncReady) return;
    updateParams({
      gene: (!fullPageGene && selectedGene) ? selectedGene.symbol : null,
      q: searchQuery || null,
      kind: kindFilter !== 'all' ? kindFilter : null,
      genome: showGenome ? '1' : null,
      tier: tierFilter !== 'all' ? tierFilter : null,
      stage: stageFilter !== 'all' ? stageFilter : null,
      host: hostClassFilter !== 'all' ? hostClassFilter : null,
      view: viewMode === 'detail' && showGenome ? 'detail' : null,
      sort: viewMode === 'detail' && showGenome && detailSort !== 'variable' ? detailSort : null,
      dir: viewMode === 'detail' && showGenome && detailSort !== 'variable' ? detailSortDir : null,
      category: categoryFilter !== 'all' ? categoryFilter : null,
      page: page > 1 ? String(page) : null,
    });
  });

  // Get PDB info for selected gene
  let selectedPdb = $derived(selectedGene ? pdbStructures[selectedGene.symbol] : null);

  // Group by category
  let categories = $derived([...new Set(genes.map(g => g.category))]);

  // Click-a-chip filters (D110): tier ('1'|'2'|'3'|'lit'), stage (model
  // stage id), host class (aves|mammalia|both|other|none|viral)
  let tierFilter = $state('all');
  let stageFilter = $state('all');
  let hostClassFilter = $state('all');
  function toggleTier(v) { tierFilter = tierFilter === v ? 'all' : v; page = 1; }
  function toggleStage(v) { stageFilter = stageFilter === v ? 'all' : v; page = 1; }
  function toggleHostClass(v) { hostClassFilter = hostClassFilter === v ? 'all' : v; page = 1; }
  function tierOf(g) { return g.tier ? String(g.tier) : (g.wiki_only ? 'lit' : 'none'); }

  let filteredGenes = $derived(genes.filter(g =>
    (!showGenome || presenceOf(g.symbol) !== null) &&
    (showGenome || g.evidence_scope !== 'annotation') &&
    (tierFilter === 'all' || tierOf(g) === tierFilter) &&
    (stageFilter === 'all' || stageOf(g.symbol) === stageFilter) &&
    (hostClassFilter === 'all' || hostClassOf(g.symbol) === hostClassFilter) &&
    (g.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    g.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (g.aliases || []).some(a => a.toLowerCase().includes(searchQuery.toLowerCase())))
  ));

  // Category colors
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
    'Immune Response': 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300',
  };

  // Category explanations (ⓘ tooltips on section headers)
  const categoryInfo = {
    'Host Factor': 'Host proteins the virus co-opts (or must overcome) to replicate — e.g. ANP32A supports the viral polymerase.',
    'Pattern Recognition': 'Host sensors that detect viral RNA and raise the alarm — RIG-I (DDX58), MDA5 (IFIH1), TLRs.',
    'Antiviral Response': 'Host effector proteins that directly inhibit viral replication (includes interferon-stimulated genes).',
    'ISG': 'Interferon-stimulated gene — a host gene switched ON by interferon signaling during infection (OAS, viperin/RSAD2, IFIT5, MX1…).',
    'Signal Transduction': 'Host signaling molecules that relay the antiviral response — IRF3/IRF7, MAVS.',
    'Signaling': 'Signaling relay molecules that carry the antiviral response from sensors to effectors — IRF3/IRF7, MAVS.',
    'Receptor': 'Host surface molecules/glycans the virus binds for entry — sialic acid, ST6Gal1, TMPRSS2.',
    'Immune Response': 'Cytokines and immune regulators induced during infection — IFNs, interleukins, TNF, NF-κB, MHC.',
    'Host Gene': 'Other host genes implicated in the literature that don’t fit the immune categories above.',
    'Immune (GO:0002376)': 'Host immune genes from the Gene Ontology “immune system process” term (GO:0002376) — the Roost presence panel, searched across sequenced bird genomes for gene presence/absence.',
    'Effector': 'Downstream antiviral effector proteins that act directly against the virus once infection has been detected.',
    'Sensor': 'Upstream sensor molecules that detect viral components and initiate the immune response.',
    'Dependency': 'Host factors the virus depends on for replication — loss of these factors can protect the host.',
    'Tolerance': 'Genes involved in disease tolerance — limiting the damage an infection causes rather than resisting the virus itself.',
    'Viral Protein': 'Virus-encoded proteins — the viral polymerase complex (PB2/PB1/PA), surface glycoproteins (HA/NA), and accessory proteins.',
    'Viral Segment': 'Viral genome segments named as a whole (M segment encodes M1+M2; NS segment encodes NS1+NEP).',
  };

  // Host vs viral kind for a gene record
  function geneKind(g) {
    if (g.kind) return g.kind;                                   // wiki-only records carry it
    if (['Viral Protein', 'Viral Segment'].includes(g.category)) return 'viral';
    if (wikiGenes[g.symbol]?.kind) return wikiGenes[g.symbol].kind; // curated, resolved via wiki
    return 'host';
  }

  // Display names for categories that read better expanded
  const categoryDisplay = {
    'ISG': 'Interferon-Stimulated Genes (ISG)',
    'Immune (GO:0002376)': 'Immune Genes (GO:0002376)',
  };

  // Short labels for the filter chips
  const categoryChip = {
    'Immune (GO:0002376)': 'Immune panel',
  };

  // Translated category label — falls back to the raw data value when the
  // key is missing (t() returns the key itself, which would leak into the UI)
  function catLabel(category) {
    let slug = category.toLowerCase();
    if (slug.includes('go:0002376')) slug = 'immune panel';
    slug = slug.replace(/[^a-z0-9]+/g, '-');
    const k = 'genes.category.' + slug;
    const v = t(k);
    return v === k ? (categoryChip[category] || categoryDisplay[category] || category) : v;
  }

  let kindFilter = $state('all');

  // --- Presence-detail view (D104): only with annotation-only enabled ---
  let viewMode = $state('list');   // 'list' | 'detail'
  let detailSort = $state('variable'); // variable | missing | present | fragment | name
  let detailSortDir = $state('desc');  // asc | desc — toggled by clicking the active header
  function sortBy(key) {
    if (detailSort === key) {
      detailSortDir = detailSortDir === 'desc' ? 'asc' : 'desc';
    } else {
      detailSort = key;
      detailSortDir = key === 'name' ? 'asc' : 'desc';
    }
  }
  let presenceSummary = $state(null);  // per-gene presence rollup (DuckDB, lazy)
  let urlSyncReady = $state(false);    // URL restore finished; effect may sync
  async function ensurePresenceSummary() {
    if (presenceSummary) return;
    try {
      // Phase 2 Step 4: derived from the parquet matrix in one GROUP BY
      // (retired the static gene_presence_summary.json). Dynamic import
      // keeps duckdb-wasm out of the page until the genome view is used.
      const { db } = await import('../lib/stores/db.js');
      presenceSummary = await db.getGenePresenceSummaries();
    } catch { presenceSummary = {}; }
  }
  function setView(mode) {
    if (mode === 'detail' && !showGenome) return; // gate: genome-available first (D105)
    viewMode = mode;
    page = 1;
    if (mode === 'detail') ensurePresenceSummary();
  }
  function presenceOf(sym) {
    return presenceSummary?.[sym] || presenceSummary?.[canonicalOf(sym)] || null;
  }

  // D104: gene-page links carry the current list filters so the URL stays
  // shareable and browser-back restores the exact filtered view
  function filterParams() {
    const out = {};
    if (searchQuery) out.q = searchQuery;
    if (kindFilter !== 'all') out.kind = kindFilter;
    if (showGenome) out.genome = '1';
    if (tierFilter !== 'all') out.tier = tierFilter;
    if (stageFilter !== 'all') out.stage = stageFilter;
    if (hostClassFilter !== 'all') out.host = hostClassFilter;
    if (viewMode === 'detail' && showGenome) {
      out.view = 'detail';
      if (detailSort !== 'variable') { out.sort = detailSort; out.dir = detailSortDir; }
    }
    if (categoryFilter !== 'all') out.category = categoryFilter;
    return out;
  }
  let annotationCount = $derived(genes.filter(g => g.evidence_scope === 'annotation').length);
  let genomeCount = $derived(genes.filter(g => presenceOf(g.symbol) !== null).length); // 'all' | 'host' | 'viral'
  let kindFilteredGenes = $derived(
    kindFilter === 'all' ? filteredGenes : filteredGenes.filter(g => geneKind(g) === kindFilter)
  );

  // --- Category filter + pagination (the full list is ~950 rows) ---
  let categoryFilter = $state('all');
  let page = $state(1);
  const PER_PAGE = 25;

  let categoryFilteredGenes = $derived(
    categoryFilter === 'all'
      ? kindFilteredGenes
      : kindFilteredGenes.filter(g => g.category === categoryFilter)
  );

  // Pack whole categories into pages: a category is never split across a
  // page boundary unless it alone exceeds PER_PAGE; small categories share
  // a page ("all Host Factor genes, then the next category where it fits").
  let pages = $derived.by(() => {
    const out = [];
    let cur = [];
    const flush = () => { if (cur.length) { out.push(cur); cur = []; } };
    const sections = [
      ...orderCategories(hostCategories, hostCategoryOrder).map(c => [c, 'host']),
      ...orderCategories(viralCategories, ['Viral Protein', 'Viral Segment']).map(c => [c, 'viral']),
    ];
    for (const [category, kind] of sections) {
      const catGenes = categoryFilteredGenes.filter(g => geneKind(g) === kind && g.category === category);
      if (!catGenes.length) continue;
      if (cur.length && cur.length + catGenes.length > PER_PAGE) flush();
      if (catGenes.length > PER_PAGE) {
        // Oversized category: consecutive full pages; the tail stays open
        // so a following small category can join it.
        for (let i = 0; i < catGenes.length; i += PER_PAGE) {
          const chunk = catGenes.slice(i, i + PER_PAGE);
          if (i + PER_PAGE >= catGenes.length) cur = chunk;
          else out.push(chunk);
        }
      } else {
        cur = cur.concat(catGenes);
      }
    }
    flush();
    return out;
  });

  let totalPages = $derived(Math.max(1, pages.length));
  let pagedGenes = $derived(pages[Math.min(page, totalPages) - 1] || []);
  let pageStart = $derived(page === 1 ? 1 : pages.slice(0, page - 1).reduce((s, p) => s + p.length, 0) + 1);
  let pageEnd = $derived(categoryFilteredGenes.length === 0 ? 0 : pageStart + pagedGenes.length - 1);

  function goTo(n) {
    page = Math.min(Math.max(1, n), totalPages);
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // windowed page buttons: 1 … p-1 p p+1 … last
  let pageWindow = $derived.by(() => {
    const out = [];
    const add = (n) => { if (n >= 1 && n <= totalPages && !out.includes(n)) out.push(n); };
    add(1); add(2);
    for (let n = page - 2; n <= page + 2; n++) add(n);
    add(totalPages - 1); add(totalPages);
    out.sort((a, b) => a - b);
    const disp = [];
    let prev = 0;
    for (const n of out) {
      if (n - prev > 1) disp.push('…');
      disp.push(n);
      prev = n;
    }
    return disp;
  });

  // Search/kind changes clear the category filter
  $effect(() => { void searchQuery; void kindFilter; categoryFilter = 'all'; });
  // Any filter change (search, kind, category chip) returns to page 1
  let filterKey = $derived(`${searchQuery}|${kindFilter}|${categoryFilter}`);
  $effect(() => { void filterKey; page = 1; });

  // Catalogue header counts (Phase: de-numbered copy) + corpus size
  let catalogueHeader = $state(null);
  const nSearched = $derived(catalogueHeader?.total_species || 0);
  const nSearchedAssemblies = $derived(catalogueHeader?.total_assemblies || nSearched);
  let corpusPapers = $state(0);
  $effect(() => {
    if (corpusPapers) return;
    fetch('data/stats.json').then(r => r.ok ? r.json() : null)
      .then(s => { if (s?.papers) corpusPapers = s.papers; })
      .catch(() => {});
  });

  // Distinct research papers linked to the listed genes — per-gene counts
  // double-count papers that mention several genes
  let linkedPapers = $derived(papersWithGenes
    ?? new Set(genes.flatMap(g => (g.papers || []).map(p => p.paper_id).filter(Boolean))).size);

  // Two clearly-separated groups: host genes first, viral proteins/segments after
  let hostCategories = $derived([...new Set(kindFilteredGenes.filter(g => geneKind(g) === 'host').map(g => g.category))]);
  let viralCategories = $derived([...new Set(kindFilteredGenes.filter(g => geneKind(g) === 'viral').map(g => g.category))]);
  const hostCategoryOrder = ['Host Factor', 'Pattern Recognition', 'ISG', 'Antiviral Response', 'Immune Response', 'Signal Transduction', 'Receptor', 'Host Gene'];
  const orderCategories = (cats, order) =>
    [...cats].sort((a, b) => {
      const ia = order.indexOf(a), ib = order.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
</script>

<svelte:head><title>{t('genes_page.gene.panel') || 'Gene panel'} — Roost</title></svelte:head>

{#if fullPageGene}
  <!-- Full-page gene view -->
  {#if loading}
    <div class="flex items-center justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  {:else}
    <GeneFullPage
      gene={fullPageGene}
      wiki={wikiGenes[fullPageGene.symbol] || null}
      pdb={pdbStructures[fullPageGene.symbol] || null}
      relationships={relationshipsFor(fullPageGene.symbol)}
      hostAssoc={hostAssoc[canonicalOf(fullPageGene.symbol)] || null}
    />
  {/if}
{:else}
  <!-- Gene panel: list + slim card -->
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('genes_page.gene.panel')}</h1>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        {#if loading}
          {t('genes.loading') || 'Loading genes...'}
        {:else}
          {genes.filter(g => g.evidence_scope !== 'annotation').length} {t('genes.lit.evidence') || 'genes with literature evidence'} (+{annotationCount} {t('genes.genome.annotation') || 'genome-annotation, toggle to show'}), {t('genes.roles.from') || 'gene roles from'} {formatNumber(linkedPapers)} {t('common.of') || 'of'} {formatNumber(corpusPapers)} {t('genes.corpus.papers') || 'corpus papers'}
        {/if}
      </p>
    </div>

    {#if error}
      <div class="bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 p-4 rounded-lg">
        Error loading genes: {error}
      </div>
    {:else if loading}
      <div class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    {:else}
      <!-- Search -->
      <div class="max-w-md">
        <input
          type="text"
          bind:value={searchQuery}
          placeholder={t('search.placeholder.genes') || 'Search genes by symbol, name, or alias...'}
          class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <!-- Host/Viral toggle -->
      <div class="flex items-center gap-2">
        <div class="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
          {#each [['all', t('common.all') || 'All'], ['host', t('genes.kind.host') || 'Host genes'], ['viral', t('genes.kind.viral') || 'Viral proteins']] as [val, label], i}
            <button
              onclick={() => kindFilter = val}
              class="px-3 py-1.5 text-sm font-medium transition-colors {kindFilter === val
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'}
              {i > 0 ? 'border-l border-gray-300 dark:border-gray-600' : ''}"
            >
              {label}
            </button>
          {/each}
        </div>
        <button
          onclick={() => { showGenome = !showGenome; if (showGenome) ensurePresenceSummary(); else viewMode = 'list'; }}
          data-testid="genome-available-toggle"
          aria-pressed={showGenome}
          title={t('genes.panel.title') || `Genes with genome presence calls — searched by sequence across the ${nSearched} sequenced species. Default shows literature-evidence genes only.`}
          class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors {showGenome
            ? 'bg-amber-600 text-white'
            : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}"
        >
          {showGenome ? '✓' : '+'} {t('genes.genome.available') || 'genome available'} · {formatNumber(genomeCount)}
        </button>

        <!-- Presence-detail view (D104) — gated behind annotation-only -->
        {#if showGenome}
          <button
            onclick={() => setView(viewMode === 'detail' ? 'list' : 'detail')}
            data-testid="presence-detail-toggle"
            aria-pressed={viewMode === 'detail'}
            title={t('genes.detail.title') || `Detailed table: per-gene presence / fragment / absence counts across the ${nSearched} sequenced species, sortable by variability`}
            class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors {viewMode === 'detail'
              ? 'bg-emerald-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}"
          >
            {viewMode === 'detail' ? '✓ ' : ''}{t('genes.presence.detail') || 'Presence detail'}
          </button>
        {/if}
      </div>

      <!-- Active chip filters (D110) with one-click clear -->
      {#if tierFilter !== 'all' || stageFilter !== 'all' || hostClassFilter !== 'all'}
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="text-xs text-gray-500 dark:text-gray-400">{t('genes_page.filters')}</span>
          {#if tierFilter !== 'all'}
            <button class="px-2 py-1 text-xs font-medium rounded-full bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900" onclick={() => tierFilter = 'all'}>{tierFilter === 'lit' ? 'lit only' : 'Tier ' + tierFilter} ✕</button>
          {/if}
          {#if stageFilter !== 'all'}
            <button class="px-2 py-1 text-xs font-medium rounded-full bg-teal-600 text-white" onclick={() => stageFilter = 'all'}>{vt(STAGE_SHORT[stageFilter] || stageFilter)} ✕</button>
          {/if}
          {#if hostClassFilter !== 'all'}
            <button class="px-2 py-1 text-xs font-medium rounded-full bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900" onclick={() => hostClassFilter = 'all'}>{HOST_CLASS_META[hostClassFilter] ? (t('genes.host.' + hostClassFilter + '.label') || HOST_CLASS_META[hostClassFilter].label) : hostClassFilter} ✕</button>
          {/if}
        </div>
      {/if}

      <!-- Category filter chips -->
      <div class="flex flex-wrap items-center gap-1.5">
        <button
          onclick={() => categoryFilter = 'all'}
          class="px-2.5 py-1 text-xs font-medium rounded-full transition-colors {categoryFilter === 'all'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
        >{t('common.all')} {kindFilteredGenes.length}</button>
        {#each orderCategories(hostCategories, hostCategoryOrder).concat(orderCategories(viralCategories, ['Viral Protein', 'Viral Segment'])) as category (category)}
          <button
            onclick={() => categoryFilter = categoryFilter === category ? 'all' : category}
            class="px-2.5 py-1 text-xs font-medium rounded-full transition-colors {categoryFilter === category
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
          >{catLabel(category)} {kindFilteredGenes.filter(g => g.category === category).length}</button>
        {/each}
      </div>

      <div class="grid lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-6 min-w-0">
        <!-- Result count -->
        <p class="text-xs text-gray-500 dark:text-gray-400">
          {t('papers.showing') || 'Showing'} {pageStart}–{pageEnd} {t('common.of')} {categoryFilteredGenes.length} {t('genes.word') || 'genes'}
        </p>

        {#if categoryFilteredGenes.length === 0}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center text-gray-500 dark:text-gray-400">
            {t('common.no_results')}
          </div>
        {/if}

        {#if viewMode === 'detail' && showGenome}
          {@const rows = categoryFilteredGenes
            .map(g => ({ gene: g, p: presenceOf(g.symbol) }))
            .filter(({ p }) => p !== null)  // presence view: genes never searched (no references) can't participate
            .sort((a, b) => {
              const sign = detailSortDir === 'desc' ? -1 : 1;
              if (detailSort === 'name') return sign * a.gene.symbol.localeCompare(b.gene.symbol);
              if (detailSort === 'present') return sign * ((a.p?.full || 0) - (b.p?.full || 0));
              if (detailSort === 'missing') return sign * ((a.p?.not_found || 0) - (b.p?.not_found || 0));
              if (detailSort === 'fragment') return sign * ((a.p?.fragment || 0) - (b.p?.fragment || 0));
              // 'variable': fragment + absent share — the most variable genes first (default)
              const varOf = (x) => (x.p.fragment + x.p.not_found) / Math.max(1, x.p.total);
              return sign * (varOf(a) - varOf(b)) || sign * ((a.p?.fragment || 0) - (b.p?.fragment || 0));
            })}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <table class="w-full text-sm table-fixed">
              <colgroup>
                <col style="width: 13%" />
                <col style="width: 29%" />
                <col style="width: 11%" />
                <col style="width: 11%" />
                <col style="width: 11%" />
                <col style="width: 25%" />
              </colgroup>
              <thead>
                <tr class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-left text-xs text-gray-500 dark:text-gray-400">
                  <th class="px-4 py-2 pr-6 cursor-pointer hover:text-gray-900 dark:hover:text-white whitespace-nowrap" onclick={() => sortBy('name')}>Gene <span class="ml-0.5">{detailSort === 'name' ? (detailSortDir === 'desc' ? '▼' : '▲') : '↕'}</span></th>
                  <th class="px-4 py-2 truncate">{t('genes_page.name')}</th>
                  <th class="px-4 py-2 pl-6 cursor-pointer hover:text-gray-900 dark:hover:text-white text-right whitespace-nowrap" onclick={() => sortBy('present')}>✓ Present <span class="ml-0.5">{detailSort === 'present' ? (detailSortDir === 'desc' ? '▼' : '▲') : '↕'}</span></th>
                  <th class="px-4 py-2 pl-6 cursor-pointer hover:text-gray-900 dark:hover:text-white text-right whitespace-nowrap" onclick={() => sortBy('fragment')}>~ Fragment <span class="ml-0.5">{detailSort === 'fragment' ? (detailSortDir === 'desc' ? '▼' : '▲') : '↕'}</span></th>
                  <th class="px-4 py-2 pl-6 cursor-pointer hover:text-gray-900 dark:hover:text-white text-right whitespace-nowrap" onclick={() => sortBy('missing')}>✗ Missing <span class="ml-0.5">{detailSort === 'missing' ? (detailSortDir === 'desc' ? '▼' : '▲') : '↕'}</span></th>
                  <th class="px-4 py-2 pl-6 cursor-pointer hover:text-gray-900 dark:hover:text-white text-right whitespace-nowrap" onclick={() => sortBy('variable')} title={t('routes.genes.variability.fragment.missing.species') || 'Variability = (fragment + missing) / species searched'}>↕ Variability <span class="ml-0.5">{detailSort === 'variable' ? (detailSortDir === 'desc' ? '▼' : '▲') : ''}</span></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                {#each rows.slice(0, page * PER_PAGE) as { gene, p }}
                  {@const variable = p ? (p.fragment + p.not_found) / Math.max(1, p.total) : null}
                  <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/40 cursor-pointer" onclick={() => { selectedGene = gene; window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
                    <td class="px-4 py-2 truncate" title={gene.symbol}><span class="font-mono font-semibold text-blue-600 dark:text-blue-400">{gene.symbol}</span></td>
                    <td class="px-4 py-2 truncate text-gray-500 dark:text-gray-400" title={gene.name}>{gene.name}</td>
                    <td class="px-4 py-2 text-right font-medium text-green-700 dark:text-green-400">{p ? p.full : '—'}</td>
                    <td class="px-4 py-2 text-right font-medium text-amber-700 dark:text-amber-400">{p ? p.fragment : '—'}</td>
                    <td class="px-4 py-2 text-right font-medium text-red-600 dark:text-red-400">{p ? p.not_found : '—'}</td>
                    <td class="px-4 py-2 text-right">
                      {#if variable !== null}
                        <div class="flex items-center gap-1.5 justify-end">
                          <div class="w-16 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <div class="h-full {variable > 0.5 ? 'bg-red-500' : variable > 0.2 ? 'bg-amber-500' : 'bg-green-500'}" style="width: {Math.round(variable * 100)}%"></div>
                          </div>
                          <span class="text-xs text-gray-500 dark:text-gray-400 w-8 text-right">{Math.round(variable * 100)}%</span>
                        </div>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
            {#if rows.length > page * PER_PAGE}
              <div class="p-3 text-center">
                <button class="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700" onclick={() => page += 1}>
                  Show more ({rows.length - page * PER_PAGE} remaining)
                </button>
              </div>
            {/if}
            <p class="px-4 py-2 text-[11px] text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700">
              {t('genes.variability.def') || 'Variability = (fragment + missing) / species searched'} {t('genes.across.genomes') || 'across'} {formatNumber(nSearchedAssemblies)} {t('genomes.word') || 'genomes'}.
              {categoryFilteredGenes.length - categoryFilteredGenes.filter(g => presenceOf(g.symbol) !== null).length} {t('genes.no.ref.hidden') || 'gene(s) without reference sequences are hidden (never genome-searched).'}
              Click a row for the gene page.
            </p>
          </div>
        {:else}
          <div class="flex items-center gap-2 pt-1">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white">{t('genes_page.host.genes')}</h2>
            <span class="text-xs px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300">
              {kindFilteredGenes.filter(g => geneKind(g) === 'host').length}
            </span>
            <span class="text-xs text-gray-500 dark:text-gray-400">{t('genes_page.the.birds.own.immune')}</span>
          </div>
        {#each orderCategories(hostCategories, hostCategoryOrder) as category}
          {@const categoryGenes = pagedGenes.filter(g => geneKind(g) === 'host' && g.category === category)}
          {#if categoryGenes.length > 0}
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center gap-1">
                <span class="font-semibold text-gray-900 dark:text-white">{catLabel(category)}</span>
                <InfoDot text={t('genes.cat.' + category) || categoryInfo[category] || ''} />
              </div>
              <div class="divide-y divide-gray-100 dark:divide-gray-700">
                {#each categoryGenes as gene}{@const conn = connectionsOf(gene.symbol)}{@const stage = stageOf(gene.symbol)}
                  <div
                    class="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors {selectedGene?.symbol === gene.symbol ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
                  >
                    {#if hostClassOf(gene.symbol)}
                      <div class="flex flex-wrap items-center gap-1.5 mb-0.5">
                        <button class="px-1.5 py-0.5 text-[10px] rounded-full font-semibold {HOST_CLASS_META[hostClassOf(gene.symbol)].cls} {hostClassFilter === hostClassOf(gene.symbol) ? 'ring-2 ring-offset-1 ring-gray-800 dark:ring-gray-200' : 'hover:brightness-95'}" data-testid="host-class-chip" title="{t('genes.host.' + hostClassOf(gene.symbol) + '.title') || HOST_CLASS_META[hostClassOf(gene.symbol)].title} · {t('genes.click.filter') || 'click to filter'} · {t('genes.papers.label') || 'papers'}: {JSON.stringify(hostAssoc[canonicalOf(gene.symbol)]?.papers || {})}" onclick={() => toggleHostClass(hostClassOf(gene.symbol))}>{t('genes.host.' + hostClassOf(gene.symbol) + '.label') || HOST_CLASS_META[hostClassOf(gene.symbol)].label}</button>
                      </div>
                    {/if}
                    <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                      <button
                        onclick={() => selectedGene = gene}
                        class="flex flex-wrap items-center gap-x-3 gap-y-0.5 min-w-0 text-left cursor-pointer rounded focus-visible:ring-2 focus-visible:ring-blue-500"
                      >
                        <span class="font-mono font-semibold text-blue-600 dark:text-blue-400">{gene.symbol}</span>
                        <span class="text-sm text-gray-600 dark:text-gray-300 truncate">{gene.name}</span>
                      </button>
                      <div class="flex items-center gap-2">
                        {#if stage && STAGE_SHORT[stage]}
                          <button class="px-2 py-0.5 text-xs rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300 {stageFilter === stage ? 'ring-2 ring-offset-1 ring-teal-600 font-semibold' : 'hover:bg-teal-100 dark:hover:bg-teal-900'}" data-testid="gene-stage-chip" title={t('tip.genes.stage') || 'Model stage assignment · click to filter'} onclick={() => toggleStage(stage)}>{vt(STAGE_SHORT[stage])}</button>
                        {/if}
                        {#if gene.tier}
                          <button class="px-2 py-0.5 text-xs rounded-full {gene.tier === 1 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : gene.tier === 2 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'} {tierFilter === String(gene.tier) ? 'ring-2 ring-offset-1 ring-gray-800 dark:ring-gray-200 font-semibold' : 'hover:brightness-95'}" title={t('tip.genes.tier') || 'Curated evidence tier · click to filter'} onclick={() => toggleTier(String(gene.tier))}>
                            Tier {gene.tier}
                          </button>
                        {:else if gene.wiki_only}
                          <button class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 {tierFilter === 'lit' ? 'ring-2 ring-offset-1 ring-gray-800 dark:ring-gray-200 font-semibold' : 'hover:brightness-95'}" title={t('tip.genes.discovered') || 'Discovered in the research corpus, not in the curated panel · click to filter'} onclick={() => toggleTier('lit')}>
                            lit
                          </button>
                        {/if}
                      </div>
                    </div>
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">{gene.description}</p>
                    <div class="flex items-center gap-2 mt-1">
                      {#if gene.paper_count > 0}
                        <span class="text-xs text-gray-500 dark:text-gray-400">{t('genes.n_papers', {n: gene.paper_count})}</span>
                      {/if}
                      {#if gene.paper_count > 0 && conn.connections > 0}<span class="text-xs text-gray-500 dark:text-gray-400">·</span>{/if}
                      {#if conn.connections > 0}
                        <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="connection-count-badge" title={t('routes.genes.conn.connections.reviewed.connection', { 'conn.connections': conn.connections, 'conn.evidence': conn.evidence })}>{t('genes.n_connections', {n: conn.connections})}</span>
                      {:else}
                        <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="no-connections-chip" title={t('routes.genes.no.reviewed.mechanistic.connections') || 'No reviewed mechanistic connections yet'}>{t('genes_page.no.reviewed.connections')}</span>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}

        <!-- Viral proteins & segments -->
        {#if pagedGenes.some(g => geneKind(g) === 'viral')}
          <div class="flex items-center gap-2 pt-4">
            <h2 class="text-lg font-bold text-gray-900 dark:text-white">{t('genes_page.viral.proteins.amp.segments')}</h2>
            <span class="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {kindFilteredGenes.filter(g => geneKind(g) === 'viral').length}
            </span>
            <span class="text-xs text-gray-500 dark:text-gray-400">{t('genes_page.virusencoded.studied.as.mutations')}</span>
          </div>
        {/if}
        {#each orderCategories(viralCategories, ['Viral Protein', 'Viral Segment']) as category}
          {@const categoryGenes = pagedGenes.filter(g => geneKind(g) === 'viral' && g.category === category)}
          {#if categoryGenes.length > 0}
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center gap-1">
                <span class="font-semibold text-gray-900 dark:text-white">{catLabel(category)}</span>
                <InfoDot text={t('genes.cat.' + category) || categoryInfo[category] || ''} />
              </div>
              <div class="divide-y divide-gray-100 dark:divide-gray-700">
                {#each categoryGenes as gene}{@const conn = connectionsOf(gene.symbol)}{@const stage = stageOf(gene.symbol)}
                  <div
                    class="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors {selectedGene?.symbol === gene.symbol ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
                  >
                    {#if hostClassOf(gene.symbol)}
                      <div class="flex flex-wrap items-center gap-1.5 mb-0.5">
                        <button class="px-1.5 py-0.5 text-[10px] rounded-full font-semibold {HOST_CLASS_META[hostClassOf(gene.symbol)].cls} {hostClassFilter === hostClassOf(gene.symbol) ? 'ring-2 ring-offset-1 ring-gray-800 dark:ring-gray-200' : 'hover:brightness-95'}" data-testid="host-class-chip" title="{t('genes.host.' + hostClassOf(gene.symbol) + '.title') || HOST_CLASS_META[hostClassOf(gene.symbol)].title} · {t('genes.click.filter') || 'click to filter'} · {t('genes.papers.label') || 'papers'}: {JSON.stringify(hostAssoc[canonicalOf(gene.symbol)]?.papers || {})}" onclick={() => toggleHostClass(hostClassOf(gene.symbol))}>{t('genes.host.' + hostClassOf(gene.symbol) + '.label') || HOST_CLASS_META[hostClassOf(gene.symbol)].label}</button>
                      </div>
                    {/if}
                    <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                      <button
                        onclick={() => selectedGene = gene}
                        class="flex flex-wrap items-center gap-x-3 gap-y-0.5 min-w-0 text-left cursor-pointer rounded focus-visible:ring-2 focus-visible:ring-blue-500"
                      >
                        <span class="font-mono font-semibold text-blue-600 dark:text-blue-400">{gene.symbol}</span>
                        <span class="text-sm text-gray-600 dark:text-gray-300 truncate">{gene.name}</span>
                      </button>
                      <div class="flex items-center gap-2">
                        {#if stage && STAGE_SHORT[stage]}
                          <button class="px-2 py-0.5 text-xs rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950 dark:text-teal-300 {stageFilter === stage ? 'ring-2 ring-offset-1 ring-teal-600 font-semibold' : 'hover:bg-teal-100 dark:hover:bg-teal-900'}" data-testid="gene-stage-chip" title={t('tip.genes.stage') || 'Model stage assignment · click to filter'} onclick={() => toggleStage(stage)}>{vt(STAGE_SHORT[stage])}</button>
                        {/if}
                        {#if gene.tier}
                          <button class="px-2 py-0.5 text-xs rounded-full {gene.tier === 1 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : gene.tier === 2 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'} {tierFilter === String(gene.tier) ? 'ring-2 ring-offset-1 ring-gray-800 dark:ring-gray-200 font-semibold' : 'hover:brightness-95'}" title={t('tip.genes.tier') || 'Curated evidence tier · click to filter'} onclick={() => toggleTier(String(gene.tier))}>
                            Tier {gene.tier}
                          </button>
                        {:else if gene.wiki_only}
                          <button class="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 {tierFilter === 'lit' ? 'ring-2 ring-offset-1 ring-gray-800 dark:ring-gray-200 font-semibold' : 'hover:brightness-95'}" title={t('tip.genes.discovered') || 'Discovered in the research corpus, not in the curated panel · click to filter'} onclick={() => toggleTier('lit')}>
                            lit
                          </button>
                        {/if}
                      </div>
                    </div>
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate">{gene.description}</p>
                    <div class="flex items-center gap-2 mt-1">
                      {#if gene.paper_count > 0}
                        <span class="text-xs text-gray-500 dark:text-gray-400">{t('genes.n_papers', {n: gene.paper_count})}</span>
                      {/if}
                      {#if gene.paper_count > 0 && conn.connections > 0}<span class="text-xs text-gray-500 dark:text-gray-400">·</span>{/if}
                      {#if conn.connections > 0}
                        <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="connection-count-badge" title={t('routes.genes.conn.connections.reviewed.connection', { 'conn.connections': conn.connections, 'conn.evidence': conn.evidence })}>{t('genes.n_connections', {n: conn.connections})}</span>
                      {:else}
                        <span class="text-xs text-gray-500 dark:text-gray-400" data-testid="no-connections-chip" title={t('routes.genes.no.reviewed.mechanistic.connections') || 'No reviewed mechanistic connections yet'}>{t('genes_page.no.reviewed.connections')}</span>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}
        {/if}

        <!-- Pagination (Papers-page style) — list view only; the detail
             table grows via its own 'show more' -->
        {#if totalPages > 1 && viewMode !== 'detail'}
          <div class="flex flex-wrap items-center justify-center gap-1.5">
            <button
              class="px-3 py-1.5 rounded-lg text-sm bg-white dark:bg-gray-800 shadow {page === 1 ? 'text-gray-500 dark:text-gray-400' : 'text-gray-700 dark:text-gray-200 hover:shadow-md'}"
              disabled={page === 1}
              onclick={() => goTo(page - 1)}
            >
              ←
            </button>
            {#each pageWindow as pn}
              {#if pn === '…'}
                <span class="px-2 text-gray-500 dark:text-gray-400">…</span>
              {:else}
                <button
                  class="min-w-[36px] px-2 py-1.5 rounded-lg text-sm {pn === page
                    ? 'bg-blue-600 text-white shadow'
                    : 'bg-white dark:bg-gray-800 shadow text-gray-700 dark:text-gray-200 hover:shadow-md'}"
                  onclick={() => goTo(pn)}
                >
                  {pn}
                </button>
              {/if}
            {/each}
            <button
              class="px-3 py-1.5 rounded-lg text-sm bg-white dark:bg-gray-800 shadow {page === totalPages ? 'text-gray-500 dark:text-gray-400' : 'text-gray-700 dark:text-gray-200 hover:shadow-md'}"
              disabled={page === totalPages}
              onclick={() => goTo(page + 1)}
            >
              →
            </button>
            <span class="text-sm text-gray-500 dark:text-gray-400 ml-2">
              {t('common.page_n_of_m', { p: page, m: totalPages })}
            </span>
          </div>
        {/if}
      </div>

      <!-- Slim Gene Card -->
      <div class="lg:col-span-1 min-w-0">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
            {#if selectedGene}
              <div class="p-5">
                <div class="flex items-start justify-between mb-2">
                  <div class="min-w-0">
                    <h2 class="text-xl font-bold font-mono text-blue-600 dark:text-blue-400">{selectedGene.symbol}</h2>
                    <p class="text-sm text-gray-600 dark:text-gray-300">{selectedGene.name}</p>
                    {#if selectedGene.aliases && selectedGene.aliases.length > 0}
                      <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                        aka {selectedGene.aliases.slice(0, 3).join(', ')}
                      </p>
                    {/if}
                  </div>
                  <div class="flex flex-col items-end gap-1 flex-shrink-0">
                    {#if selectedGene.tier}
                      <span class="px-2 py-0.5 text-xs rounded-full {selectedGene.tier === 1 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : selectedGene.tier === 2 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
                        Tier {selectedGene.tier}
                      </span>
                    {/if}
                    <span class="px-2 py-0.5 text-xs rounded-full {categoryColors[selectedGene.category] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
                      {selectedGene.category}
                    </span>
                  </div>
                </div>

                <p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">{selectedGene.description}</p>

                {#if selectedGene.key_finding}
                  <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2.5 mt-3">
                    <p class="text-xs text-blue-700 dark:text-blue-400 line-clamp-3">{selectedGene.key_finding}</p>
                  </div>
                {/if}

                {#if slimTotal > 0}
                  <div class="mt-3 border-t border-gray-100 dark:border-gray-700 pt-3" data-testid="slim-connections">
                    <h4 class="text-[10px] font-bold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1.5">Mechanistic connections · {slimTotal}</h4>
                    <div class="flex flex-wrap gap-1">
                      {#each [...slimRels.upstream, ...slimRels.downstream, ...slimRels.physical, ...slimRels.viral].slice(0, 8) as rel}
                        <a href="#/genes/{rel.counterpart}" title="{vt(rel.label)}{rel.evidence?.length ? ` · ${rel.evidence.length} ` + (t('genes.reviewed.evidence') || 'reviewed evidence') : ''}" class="px-1.5 py-0.5 text-[11px] rounded-full font-mono {rel.mechanism === 'inhibition' ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300' : rel.mechanism === 'viral_dependency' ? 'bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300' : 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'} hover:underline">
                          {rel.outgoing ? '→' : '←'} {rel.counterpart}
                        </a>
                      {/each}
                      {#if slimTotal > 8}<span class="text-[10px] text-gray-500 dark:text-gray-400 self-center">+{slimTotal - 8} more</span>{/if}
                    </div>
                  </div>
                {/if}

                {#if selectedWiki}
                  <div class="flex flex-wrap gap-1.5 mt-3 text-xs">
                    {#if selectedWiki.host_scope}
                      <ScopeTags scope={selectedWiki.host_scope} avianPapers={selectedWiki.avian_papers} mammalianPapers={selectedWiki.mammalian_papers} />
                    {/if}
                    <span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                      {t('genes.n_papers', {n: selectedWiki.paper_count})}
                    </span>
                    {#if selectedWiki.mutations?.length > 0}
                      <span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                        {selectedWiki.mutations.length} mutations
                      </span>
                    {/if}
                    {#if selectedWiki.key_findings?.length > 0}
                      <span class="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {selectedWiki.key_findings.length} key numbers
                      </span>
                    {/if}
                  </div>
                {/if}

                {#if selectedHostSpecies?.n_species > 0}
                  <div class="mt-3">
                    <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">
                      Detected host species ({selectedHostSpecies.n_species})
                      <span class="font-normal text-gray-500 dark:text-gray-400">{t('routes.genes.hosts.named.in.typed') || '— hosts named in typed claims about this gene'}</span>
                    </div>
                    <div class="flex flex-wrap gap-1">
                      {#each selectedHostSpecies.species.slice(0, 10) as sp}
                        <a href="#/species-full/{encodeURIComponent(sp)}" class="px-1.5 py-0.5 text-[11px] rounded-full bg-teal-50 text-teal-700 dark:bg-teal-950/40 dark:text-teal-300 hover:underline font-mono">
                          {sp}
                        </a>
                      {/each}
                      {#if selectedHostSpecies.n_species > 10}
                        <span class="text-[10px] text-gray-500 dark:text-gray-400 self-center">+{selectedHostSpecies.n_species - 10} more</span>
                      {/if}
                    </div>
                  </div>
                {/if}

                <div class="flex flex-wrap gap-2 mt-4">
                  <button
                    onclick={() => navigate('genes', selectedGene.symbol, filterParams())}
                    class="flex-1 px-3 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-center"
                  >
                    {t('genes.open_full_page')}
                  </button>
                  <a
                    href="#/model-cyto?gene={selectedGene.symbol}"
                    data-testid="slim-view-in-pathway"
                    class="flex-1 px-3 py-2 text-sm font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700 text-center"
                    title={t('tip.genes.pathway') || 'Open the pathway graph centred on this gene'}
                  >
                    {t('genes.view_in_pathway')}
                  </a>
                </div>
                <div class="flex flex-wrap gap-2 mt-2">
                  <a
                    href="#/phylogeny?gene={selectedGene.symbol}"
                    data-testid="slim-view-in-phylogeny"
                    class="flex-1 px-3 py-2 text-sm font-medium bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-center"
                    title={t('tip.genes.phylogeny') || 'Show this gene\'s presence/absence across the bird phylogeny'}
                  >
                    {t('genes.view_in_phylogeny')}
                  </a>
                </div>
                <div class="flex flex-wrap gap-2 mt-2">
                  <a
                    href={ncbi.geneSearch(selectedGene.symbol, 'Aves')}
                    target="_blank" rel="noopener noreferrer"
                    class="flex-1 text-center px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-900/50"
                  >NCBI</a>
                  <a
                    href={uniprot.search(selectedGene.symbol + ' Aves')}
                    target="_blank" rel="noopener noreferrer"
                    class="flex-1 text-center px-2 py-1 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded hover:bg-orange-200 dark:hover:bg-orange-900/50"
                  >{t('lib_components_genes_GeneFullPage.uniprot')}</a>
                  {#if selectedPdb}
                    <a
                      href="https://www.rcsb.org/structure/{selectedPdb.recommended}"
                      target="_blank" rel="noopener noreferrer"
                      class="flex-1 text-center px-2 py-1 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-900/50"
                    >PDB</a>
                  {/if}
                </div>
              </div>
            {:else}
              <div class="p-6 text-center text-gray-500 dark:text-gray-400">
                <svg class="w-12 h-12 mx-auto mb-3 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
                <p class="text-sm">{t('genes_page.select.a.gene.for')}</p>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}
