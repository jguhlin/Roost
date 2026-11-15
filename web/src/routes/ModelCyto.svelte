<script>
  import { trackEvent } from '../lib/analytics.js';
  /**
   * ModelCyto — interactive infection-model prototype (D83).
   * Cytoscape.js replaces Mermaid: pan/zoom, compound stage containers,
   * presence-aware node styling bound to the species selector, tap-to-drawer
   * evidence, curated antagonism edges. Data: same model JSON as Model.svelte.
   */
  import { onDestroy, onMount } from 'svelte';
  import SpeciesSearch from '../lib/components/common/SpeciesSearch.svelte';
  // embedded mode: Model.svelte renders this component in place of the
  // deprecated mermaid infection diagrams — hides the page-hero chrome
  let { embedded = false } = $props();
  // Performance: cytoscape + elk + fcose (~12MB) dynamically imported on mount
  let cytoscape = null;
  import graphAnnotationsData from '../lib/model/geneGraphAnnotations.json';
  import { getRoute } from '../lib/stores/router.js';
  import { fetchGeneCatalogue } from '../lib/utils/presence.js';
  import { t } from '../lib/stores/i18n.svelte.js';


  let cy = null;
  let container = $state(null);
  let model = $state(null);
  let presence = $state(null);
  let catalogueSpecies = $state([]);
  let absence = $state(null);
  let counts = $state(null);
  let selSpecies = $state(null);
  // analytics: which species people project onto the pathway graph
  $effect(() => { if (selSpecies) trackEvent('ModelCyto', 'species', selSpecies); });
  let geneEvidence = $state(null);   // { sym, note } — opens the evidence panel
  let view = $state('all');          // all | recognition | signalling | storm | viral
  let layoutMode = $state('pathway'); // pathway (directed) | organic (force-directed)
  let showLabels = $state(true);
  let showAllLabels = $state(false);
  let fullPanel = $state(false);
  let unassignedGenes = $state([]);
  let showUnassigned = $state(false);
  let stageAssignment = $state(null);
  let graphAnnotations = $state(graphAnnotationsData);
  let phaseHighlight = $state('all');
  let locationHighlight = $state('all');
  let annotationMatchCount = $state(0);
  let geneQuery = $state('');
  let queryMessage = $state('');
  let searchableGenes = $state([]);
  let edgeTooltip = $state(null);
  let hostAssociations = $state({});
  let edgeStrains = $state([]);
  let hostClassFilter = $state('all');   // all | aves | mammal | both
  let strainFilter = $state('all');      // registry strain id or 'all'
  let resizeObserver = null;
  let layoutRevision = 0;
  let pendingCenterGene = null;

  const SPECIES_COMMON = {
    'Gallus gallus': 'Chicken', 'Anas platyrhynchos': 'Mallard duck',
    'Taeniopygia guttata': 'Zebra finch', 'Meleagris gallopavo': 'Turkey',
    'Strigops habroptila': 'Kākāpō', 'Porphyrio hochstetteri': 'Takahē',
    'Nestor notabilis': 'Kea', 'Apteryx mantelli': 'North Island brown kiwi',
    'Apteryx rowi': 'Okarito kiwi', 'Apteryx haastii': 'Great spotted kiwi',
    'Apteryx owenii': 'Little spotted kiwi',
    'Megadyptes antipodes antipodes': 'Yellow-eyed penguin',
    'Cyanoramphus novaezelandiae': 'Red-crowned kākāriki',
    'Gallirallus australis': 'Weka', 'Notiomystis cincta': 'Stitchbird',
  };

  // Evidence-species matching for the selector: exact-species evidence is
  // highlighted, evidence naming only OTHER species dims (never hides), and
  // general/ambiguous mentions (avian, mammalian, poultry…) stay neutral.
  const SPECIES_TOKENS = {
    'Gallus gallus': ['chicken', 'gallus', 'chook'],
    'Anas platyrhynchos': ['duck', 'mallard', 'anas'],
    'Taeniopygia guttata': ['zebra finch', 'finch', 'taeniopygia'],
    'Meleagris gallopavo': ['turkey', 'meleagris'],
    'Strigops habroptila': ['kākāpō', 'kakapo', 'strigops'],
    'Porphyrio hochstetteri': ['takahē', 'takahe', 'porphyrio'],
    'Nestor notabilis': ['kea', 'nestor'],
    'Apteryx mantelli': ['kiwi', 'apteryx'],
    'Apteryx rowi': ['kiwi', 'apteryx'],
    'Apteryx haastii': ['kiwi', 'apteryx'],
    'Apteryx owenii': ['kiwi', 'apteryx'],
    'Megadyptes antipodes antipodes': ['penguin', 'megadyptes'],
    'Cyanoramphus novaezelandiae': ['kākāriki', 'kakariki', 'cyanoramphus'],
    'Gallirallus australis': ['weka', 'gallirallus'],
    'Notiomystis cincta': ['stitchbird', 'notiomystis'],
  };
  const GENERAL_SPECIES_TOKENS = ['avian', 'mammal', 'poultry', 'multiple',
    'various', 'general', 'several', 'wild bird', 'birds'];

  const ALIAS = { 'RIG-I': 'DDX58', 'MDA5': 'IFIH1', 'LGP2': 'DHX58', 'PKR': 'EIF2AK2', 'TNF': 'TNFSF15' };
  const aliasOf = (s) => ALIAS[s] || s;

  // Curated interaction edges — endpoints verified against stage gene lists.
  // Mechanistic wiring now comes from the PUBLISHED relationship file
  // (gene_relationships.json: legacy-curated + review-approved edges);
  // the arrays below remain only as viral node membership.
  const VIRAL_GENES = ['PB2', 'PB1', 'PB1-F2', 'PA', 'PA-X', 'HA', 'NP', 'NA', 'NS1', 'M2'];

  // Published mechanistic relationships (fetched in onMount)
  let relationships = $state(null);
  // Literature-backed mechanism edges from the aggregation layer
  // (pathway_edges.json) — 579 verified actor→interaction→target edges
  // from 465 papers. Distinguished from curated edges by the lit-edge class.
  let pathwayEdges = $state([]);
  const MECH_KIND = {
    activation: 'signal', inhibition: 'inhibit', binding: 'interact',
    cleavage_trafficking: 'interact', viral_dependency: 'interact',
  };
  const relEdges = () => relationships?.edges || [];
  const edgeKindOf = (mechanism) => MECH_KIND[mechanism] || 'interact';

  // Each lens tells one part of the infection story. The overview deliberately
  // collapses genes so the protective and pathological branches are legible.
  const VIEWS = {
    all: null, // every stage
    recognition: ['entry', 'sensing'],
    signalling: ['sensing', 'signaling', 'effectors', 'adaptive'],
    storm: ['signaling', 'cytokine_storm', 'celldeath'],
    viral: ['VIRAL', 'entry', 'dependency', 'hostrange'],
  };
  const VIEW_META = {
    all: { label: 'Pathway overview', eyebrow: 'THE WHOLE STORY',
      summary: 'Infection forks after immune signalling: antiviral effectors support clearance, while dysregulated inflammation drives cell death.' },
    recognition: { label: 'Detect the virus', eyebrow: 'ENTRY + SENSING',
      summary: 'Surface receptors and intracellular RNA sensors detect influenza and feed the MAVS / TLR signalling relay.' },
    signalling: { label: 'Mount a response', eyebrow: 'PROTECTIVE BRANCH',
      summary: 'Interferon signalling activates antiviral effector genes and helps bridge innate detection to adaptive immunity.' },
    storm: { label: 'Trace pathology', eyebrow: 'DYSREGULATED BRANCH',
      summary: 'Excess inflammatory signalling activates cytokines, inflammasomes and cell-death programs associated with tissue damage.' },
    viral: { label: 'See viral strategy', eyebrow: 'VIRUS + HOST RANGE',
      summary: 'Viral proteins bind entry factors, exploit host machinery and suppress immune signalling in species-specific ways.' },
  };

  const VIRAL = new Set(['PB2', 'PB1', 'PB1-F2', 'PA', 'PA-X', 'HA', 'NP', 'NA',
    'M1', 'M2', 'NS1', 'NS2', 'V-POL']);

  const STAGE_META = {
    entry: { short: 'Entry & tropism', summary: 'Attachment and cleavage', fill: '#ecfeff', accent: '#0891b2' },
    sensing: { short: 'Recognition', summary: 'Viral RNA is detected', fill: '#eff6ff', accent: '#2563eb' },
    signaling: { short: 'Immune signalling', summary: 'Interferon relay', fill: '#eef2ff', accent: '#4f46e5' },
    cytokine_storm: { short: 'Cytokine storm', summary: 'Inflammation escalates', fill: '#fff1f2', accent: '#e11d48' },
    effectors: { short: 'Antiviral effectors', summary: 'Replication is restricted', fill: '#ecfdf5', accent: '#059669' },
    dependency: { short: 'Viral dependency', summary: 'Host machinery is hijacked', fill: '#fffbeb', accent: '#d97706' },
    celldeath: { short: 'Cell death & pathology', summary: 'Tissue damage accumulates', fill: '#fff7ed', accent: '#ea580c' },
    adaptive: { short: 'Adaptive immunity', summary: 'Clearance and memory', fill: '#faf5ff', accent: '#9333ea' },
    hostrange: { short: 'Host-range bridge', summary: 'Species barriers matter', fill: '#ecfeff', accent: '#0e7490' },
    VIRAL: { short: 'Viral proteins', summary: 'Host defences are disrupted', fill: '#f5f3ff', accent: '#7c3aed' },
    NEUTRAL: { short: 'Reviewed connection', summary: 'Pathway assignment pending review', fill: '#f1f5f9', accent: '#64748b' },
  };

  // study tiers: primary (well-studied) / secondary (mentioned) / unknown
  function tierOf(sym) {
    const e = counts?.[sym];
    if (!e || !e.papers) return 'unknown';
    if (e.studied >= 2) return 'primary';
    if (e.papers >= 3 || e.studied === 1) return 'secondary';
    return 'unknown';
  }

  // role shape by home stage (first membership wins)
  const STAGE_SHAPE = {
    entry: 'vee', sensing: 'ellipse', signaling: 'round-diamond',
    cytokine_storm: 'triangle', effectors: 'round-rectangle',
    dependency: 'star', celldeath: 'cut-rectangle',
    adaptive: 'round-octagon', hostrange: 'tag', VIRAL: 'hexagon',
  };
  const SHAPE_LEGEND = [
    ['entry', 'Entry', 'shape-vee'],
    ['sensing', 'Recognition', 'shape-circle'],
    ['signaling', 'Signalling', 'shape-diamond'],
    ['cytokine_storm', 'Inflammation', 'shape-triangle'],
    ['effectors', 'Effectors', 'shape-rounded'],
    ['dependency', 'Dependency', 'shape-star'],
    ['celldeath', 'Cell death', 'shape-cut'],
    ['adaptive', 'Adaptive', 'shape-octagon'],
    ['hostrange', 'Host range', 'shape-tag'],
    ['VIRAL', 'Viral', 'shape-hexagon'],
  ];

  function locationsFor(sym) {
    // curated annotations ∪ published reviewed overlay (approved evidence only)
    return [...new Set([
      ...(graphAnnotations?.gene_locations?.[sym] || []),
      ...(relationships?.location_overlay?.[sym] || []),
    ])];
  }

  function locationLabel(id) {
    return graphAnnotations?.locations?.find((location) => location.id === id)?.label || id;
  }

  function hideEdgeTooltip(force = false) {
    if (force || !edgeTooltip?.pinned) edgeTooltip = null;
  }

  function showEdgeTooltip(edge, renderedPosition, pinned = false) {
    if (!cy || !edge) return;
    const position = renderedPosition || edge.renderedMidpoint();
    const horizontalMargin = Math.min(112, Math.max(12, cy.width() / 2));
    edgeTooltip = {
      source: edge.source().data('id2'),
      target: edge.target().data('id2'),
      relation: edge.data('label'),
      mechanism: edge.data('mechanism'),
      provenance: edge.data('provenance'),
      evidenceCount: edge.data('evidenceCount') || 0,
      papers: edge.data('papers') || [],
      species: edge.data('species') || [],
      strains: edge.data('strains') || [],
      pinned,
      x: Math.max(horizontalMargin, Math.min(cy.width() - horizontalMargin, position.x)),
      y: Math.max(48, Math.min(cy.height() - 20, position.y)),
    };
  }

  /** Keep labels useful at reading scale instead of letting them pile up at overview scale. */
  function applySemanticLabels(force = false) {
    if (!cy) return;
    const zoom = cy.zoom();
    const mode = zoom < 0.55 ? 'wide' : zoom < 0.9 ? 'medium' : 'detail';
    const key = `${mode}:${showLabels}:${showAllLabels}`;
    if (!force && cy.scratch('_semanticLabelKey') === key) return;
    cy.scratch('_semanticLabelKey', key);

    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const kind = node.data('kind');
        let visible = mode !== 'wide';
        if (kind === 'gene') {
          visible = showLabels && mode !== 'wide';
          if (mode === 'medium') visible = visible && node.hasClass('tier-primary');
          if (mode === 'detail' && node.hasClass('tier-unknown')) visible = visible && showAllLabels;
        }
        node.toggleClass('label-hidden', !visible);
      });
    });
  }

  /** Highlight a node and its direct wiring without erasing graph context. */
  function focusNeighborhood(node) {
    if (!cy) return;
    cy.elements().removeClass('focused near dimmed');
    const neighborhood = node.closedNeighborhood();
    cy.nodes('[kind = "gene"]').not(neighborhood.nodes()).addClass('dimmed');
    cy.edges().not(neighborhood.edges()).addClass('dimmed');
    neighborhood.addClass('near');
    neighborhood.nodes().parents().addClass('near');
    node.addClass('focused');
  }
  function clearFocus() {
    if (!cy) return;
    cy.elements().removeClass('focused near dimmed');
  }

  function clearSelection() {
    geneEvidence = null;
    geneQuery = '';
    queryMessage = '';
    hideEdgeTooltip(true);
    clearFocus();
  }

  function statusLabel(sym) {
    const status = presenceOf(sym);
    if (status === 'NOT_FOUND' || status === 'E2') return 'not found';
    if (status === 'FRAGMENT' || status === 'E3') return 'fragment';
    if (status) return 'present';
    return 'not assessed';
  }

  function viewForStage(stage) {
    if (stage === 'NEUTRAL') return 'all';
    if (['entry', 'sensing'].includes(stage)) return 'recognition';
    if (['signaling', 'effectors', 'adaptive'].includes(stage)) return 'signalling';
    if (['cytokine_storm', 'celldeath'].includes(stage)) return 'storm';
    return 'viral';
  }

  /** Find, reveal, center and select a gene from the toolbar. */
  function selectAndCenterNode(node) {
    const stage = node.data('stage');
    cy.resize();
    geneEvidence = { sym: node.data('id2'), note: node.data('note'), stage };
    focusNeighborhood(node);
    const neighborhood = node.closedNeighborhood();
    const box = neighborhood.boundingBox();
    const fitted = cy.getFitViewport(neighborhood, 120);
    const zoom = Math.min(1.6, fitted?.zoom || 1.35);
    const pan = {
      x: cy.width() / 2 - zoom * (box.x1 + box.w / 2),
      y: cy.height() / 2 - zoom * (box.y1 + box.h / 2),
    };
    cy.animate({ zoom, pan }, { duration: 450 });
  }

  function centerOnGene(raw = geneQuery) {
    if (!cy) return;
    const wanted = raw.trim().toUpperCase();
    if (!wanted) return;
    const node = cy.nodes('[kind = "gene"]').filter((n) => n.data('id2').toUpperCase() === wanted).first();
    if (!node || node.length === 0) {
      queryMessage = `No graph node found for “${raw.trim()}”`;
      return;
    }

    const stage = node.data('stage');
    geneQuery = node.data('id2');
    queryMessage = '';
    const revealsPanel = node.hasClass('panel-extra') && !fullPanel;
    const changesView = view === 'all' || !VIEWS[view]?.includes(stage);
    if (revealsPanel || changesView) pendingCenterGene = node.data('id2');
    if (revealsPanel) fullPanel = true;
    if (changesView) view = viewForStage(stage);
    if (!revealsPanel && !changesView) setTimeout(() => selectAndCenterNode(node), 60);
  }

  function presenceOf(sym) {
    if (!selSpecies || !presence?.species?.[selSpecies]) {
      loadSpeciesPresence(selSpecies);
      return null;
    }
    const call = presence.species[selSpecies][sym] ||
      presence.species[selSpecies][aliasOf(sym)];
    return call?.status || null;
  }

  /** Lazy per-species presence (DuckDB) — fetched on first lookup of a
   *  selected species; re-applies graph styling when the calls arrive.
   *  db.js (and its duckdb-wasm bundle) is imported dynamically so this
   *  memory-heavy page pays for it only when a comparison is requested. */
  const presencePending = new Set();
  function loadSpeciesPresence(sp) {
    if (!sp || presencePending.has(sp) || presence?.species?.[sp]) return;
    presencePending.add(sp);
    import('../lib/stores/db.js')
      .then(({ db }) => db.getPresenceCallsForSpecies(sp))
      .then((rows) => {
        const panel = {};
        for (const r of rows || []) panel[r.gene] = r;
        presence.species[sp] = panel;
      })
      .catch(() => {})
      .finally(() => {
        presencePending.delete(sp);
        applyPresenceStyling();
      });
  }

  function badgeLabel(sym) {
    const c = counts?.[sym];
    if (!c || !c.papers) return 'gap';
    if (c.studied >= 2) return `${c.papers}pp`;
    if (c.studied === 1) return '1 study';
    return `${c.papers} mentions`;
  }

  /** absence evidence for a gene — ported from Model.svelte */
  function absenceEvidence(sym) {
    if (!absence || !selSpecies) return [];
    const key = Object.keys(absence).find((k) => k === sym || k === aliasOf(sym));
    if (!key) return [];
    const recs = absence[key].avian || [];
    return recs.map((r) => ({ ...r, tag: 'reported in ' + (r.host || 'other species') }));
  }

  function buildElements() {
    const genes = [];
    const edges = [];
    const geneBySymbol = new Map();
    const buckets = new Map();
    const gridIdx = {};
    const stages = model.stages || [];

    // connected/unlinked membership comes EXCLUSIVELY from the published
    // relationship file (legacy-curated + approved)
    const PATHWAY_GENES = new Set([
      ...relEdges().flatMap((e) => [e.from, e.to]),
      ...VIRAL_GENES,
    ]);

    function bucketFor(stage) {
      if (!buckets.has(stage)) buckets.set(stage, { modelCount: 0, panelCount: 0 });
      return buckets.get(stage);
    }

    function addGene(sym, note, stage, { viral = false, panelExtra = false } = {}) {
      if (geneBySymbol.has(sym)) {
        const existing = geneBySymbol.get(sym);
        if (!existing.data.stages.includes(stage)) {
          existing.data.stages.push(stage);
          existing.data.stageIds += `${stage}|`;
        }
        return;
      }

      const tier = tierOf(sym);
      const papers = counts?.[sym]?.papers || 0;
      const connected = PATHWAY_GENES.has(sym);
      const meta = STAGE_META[stage] || { fill: '#f8fafc', accent: '#64748b' };
      const size = panelExtra ? 12 : tier === 'primary' ? 36 + Math.min(18, papers * 0.35)
        : tier === 'secondary' ? 32 : 26;
      const parent = connected ? null : `B:${stage}`;
      if (parent) {
        const bucket = bucketFor(stage);
        if (panelExtra) bucket.panelCount += 1;
        else bucket.modelCount += 1;
        gridIdx[stage] = (gridIdx[stage] || 0) + 1;
      }

      const gene = {
        classes: [viral || VIRAL.has(sym) ? 'viral' : '', `tier-${tier}`,
          connected ? 'pathway-node' : 'unlinked-node', panelExtra ? 'panel-extra' : '']
          .filter(Boolean).join(' '),
        group: 'nodes', data: {
          id: `G:${sym}`, id2: sym, label: sym, note, kind: 'gene', stage,
          stages: [stage], stageIds: `|${stage}|`,
          locations: locationsFor(sym),
          ...(parent ? { parent } : {}),
          badge: badgeLabel(sym), shape: STAGE_SHAPE[stage] || 'round-rectangle',
          size, papers, fill: meta.fill, accent: meta.accent,
          fontsize: panelExtra ? 9 : tier === 'primary' ? 12 : tier === 'secondary' ? 11 : 10,
          gridIdx: parent ? gridIdx[stage] : 0,
        },
      };
      genes.push(gene);
      geneBySymbol.set(sym, gene);
    }

    for (const st of stages) {
      for (const [sym, note] of st.genes || []) addGene(sym, note, st.id);
    }
    for (const sym of VIRAL_GENES) {
      addGene(sym, 'viral protein — studied as mutations/drug targets', 'VIRAL', { viral: true });
    }

    // Optional extended panel. Assigned genes join the relevant unlinked group;
    // stage-less genes are represented by one aggregate evidence-gap group.
    // literature-first panel (D85): genome-annotation genes (no corpus
    // evidence) stay off the model — literature confers placement
    const scopeOf = (sym) =>
      presence?.gene_catalogue?.[sym]?.evidence_scope || 'literature';
    unassignedGenes = [];
    if (stageAssignment && Object.keys(stageAssignment).length) {
      for (const [sym, a] of Object.entries(stageAssignment)) {
        if (geneBySymbol.has(sym)) continue;
        if (scopeOf(sym) === 'annotation') continue;
        if (a.stage) addGene(sym, `panel gene — assigned by ${a.source}`, a.stage, { panelExtra: true });
      }
      unassignedGenes = Object.entries(stageAssignment)
        .filter(([s, a]) => a.source === 'none' && !geneBySymbol.has(s)
          && scopeOf(s) !== 'annotation')
        .map(([s]) => s);
    }

    // Genes connected by REVIEWED evidence but lacking any stage assignment
    // become neutral top-level pathway nodes — never assigned by inference.
    // They (and their edges) are extended-panel: visible with the toggle.
    const neutralGenes = new Set();
    for (const e of relEdges()) {
      if (!e.evidence?.length) continue;
      for (const sym of [e.from, e.to]) {
        if (geneBySymbol.has(sym)) continue;
        neutralGenes.add(sym);
        const tier = tierOf(sym);
        genes.push({
          classes: [`tier-${tier}`, 'pathway-node', 'panel-extra', 'neutral-node'].join(' '),
          group: 'nodes', data: {
            id: `G:${sym}`, id2: sym, label: sym, kind: 'gene', stage: 'NEUTRAL',
            stages: ['NEUTRAL'], stageIds: '|NEUTRAL|', neutral: true,
            note: 'connected by reviewed evidence — pathway assignment pending review',
            locations: locationsFor(sym), badge: badgeLabel(sym), shape: 'ellipse',
            size: 26, papers: counts?.[sym]?.papers || 0,
            fill: '#f1f5f9', accent: '#64748b', fontsize: 10, gridIdx: 0,
          },
        });
        geneBySymbol.set(sym, genes[genes.length - 1]);
      }
    }

    const bucketNodes = [...buckets.entries()].map(([stage, bucket]) => {
      const meta = STAGE_META[stage] || { short: stage, fill: '#f8fafc', accent: '#64748b' };
      return {
        classes: `unlinked-bucket${bucket.modelCount ? '' : ' empty-bucket'}`, group: 'nodes', data: {
          id: `B:${stage}`, id2: stage, kind: 'bucket', fill: meta.fill, accent: meta.accent,
          short: meta.short, modelCount: bucket.modelCount, panelCount: bucket.panelCount,
          label: `Unlinked · ${meta.short}\n${bucket.modelCount} unlinked ${bucket.modelCount === 1 ? 'gene' : 'genes'}`,
        },
      };
    });

    const aggregate = unassignedGenes.length ? [{
      classes: 'unclassified-bucket', group: 'nodes', data: {
        id: 'B:UNCLASSIFIED', id2: 'UNCLASSIFIED', kind: 'unclassified',
        label: `Unclassified evidence gap\n${unassignedGenes.length} panel genes without a pathway\nClick to inspect`,
      },
    }] : [];

    const processNodes = [{
      classes: 'process-node', group: 'nodes', data: {
        id: 'P:H5N1', id2: 'H5N1', kind: 'process', stage: 'VIRAL', stages: ['VIRAL'],
        locations: ['viral'], label: 'H5N1\nviral genome',
      },
    }];

    const hasNode = (s) => geneBySymbol.has(s);
    // Published mechanistic edges (legacy-curated + approved) — the graph no
    // longer keeps inline edge arrays. Edges touching neutral/panel-extra
    // genes are extended-panel only.
    for (const e of relEdges()) {
      const a = e.from, b = e.to;
      if (!hasNode(a) || !hasNode(b)) continue;
      const nodeA = geneBySymbol.get(a);
      const nodeB = geneBySymbol.get(b);
      const extended = Boolean(nodeA?.data.neutral || nodeB?.data.neutral);
      const evidence = e.evidence || [];
      edges.push({
        group: 'edges',
        classes: extended ? 'ext-edge' : '',
        data: {
          id: `E:${a}-${b}-${e.mechanism}`, source: `G:${a}`, target: `G:${b}`,
          kind: edgeKindOf(e.mechanism), label: e.label, mechanism: e.mechanism,
          provenance: e.source, evidenceCount: evidence.length,
          papers: evidence.slice(0, 3).map((ev) =>
            `${ev.year || ''} · ${(ev.journal || ev.paper_id || '').slice(0, 40)}`.trim()),
          species: [...new Set(evidence.map((ev) => ev.species).filter(Boolean))],
          strains: [...new Set(evidence.flatMap((ev) =>
            (ev.strain || '').split(',').map((s) => s.trim())).filter(Boolean))],
        },
      });
    }

    // Literature-backed mechanism edges (aggregation layer) — only add
    // edges between genes already in the graph; dashed styling to
    // distinguish from curated relationships
    const curEdgeIds = new Set(edges.map((e) => e.data.id));
    for (const le of pathwayEdges) {
      const a = le.from, b = le.to;
      if (!hasNode(a) || !hasNode(b)) continue;
      const eid = `LE:${a}-${b}-${le.interaction}`;
      if (curEdgeIds.has(eid)) continue;
      curEdgeIds.add(eid);
      const nodeA = geneBySymbol.get(a);
      const nodeB = geneBySymbol.get(b);
      const extended = Boolean(nodeA?.data.neutral || nodeB?.data.neutral);
      edges.push({
        group: 'edges',
        classes: `lit-edge {extended ? 'ext-edge' : ''}`,
        data: {
          id: eid, source: `G:${a}`, target: `G:${b}`,
          kind: 'interact', label: le.interaction,
          mechanism: le.interaction, provenance: 'literature-extracted',
          evidenceCount: 1, verified: le.verified,
          papers: [le.paper_title?.slice(0, 50) || le.paper_id].filter(Boolean),
          paperIds: [le.paper_id],
          effect: le.effect?.slice(0, 120) || '',
          eh: le.eh || '',
        },
      });
    }

    for (const sym of VIRAL_GENES) {
      if (hasNode(sym)) {
        edges.push({ group: 'edges', data: {
          id: `M:H5N1-${sym}`, source: 'P:H5N1', target: `G:${sym}`,
          kind: 'membership', label: 'encodes',
        } });
      }
    }

    searchableGenes = [...geneBySymbol.keys()].sort((a, b) => a.localeCompare(b));
    edgeStrains = [...new Set(edges.flatMap((e) => e.data.strains || []))].sort();
    return [...bucketNodes, ...aggregate, ...processNodes, ...genes, ...edges];
  }

  const elkLayout = {
    name: 'elk',
    elk: {
      algorithm: 'elk.layered',
      'elk.direction': 'RIGHT',
      'elk.spacing.nodeNode': '65',
      'elk.layered.spacing.nodeNodeBetweenLayers': '150',
      'elk.spacing.componentComponent': '130',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.separateConnectedComponents': 'true',
      'elk.aspectRatio': '1.8',
      'elk.padding': '[top=50,left=60,bottom=50,right=60]',
      'elk.edgeRouting': 'ORTHOGONAL',
    },
    fit: false,
  };

  const organicLayout = {
    name: 'fcose',
    quality: 'default',
    randomize: true,
    animate: false,
    fit: false,
    padding: 60,
    nodeDimensionsIncludeLabels: false,
    packComponents: true,
    tile: true,
    tilingPaddingVertical: 18,
    tilingPaddingHorizontal: 18,
    nodeRepulsion: 7000,
    idealEdgeLength: 92,
    edgeElasticity: 0.38,
    nestingFactor: 0.12,
    gravity: 0.3,
    gravityCompound: 1,
    gravityRange: 3.8,
    gravityRangeCompound: 1.5,
    numIter: 2500,
  };

  function setLayoutMode(mode) {
    if (mode === layoutMode) return;
    pendingCenterGene = geneEvidence?.sym || null;
    layoutMode = mode;
  }

  function updateVisibleBuckets() {
    if (!cy) return;
    cy.nodes('[kind = "bucket"]').forEach((bucket) => {
      const visibleChildren = bucket.children('[kind = "gene"]').filter((child) =>
        !child.hasClass('lens-hidden') && (!child.hasClass('panel-extra') || fullPanel));
      const count = visibleChildren.length;
      bucket.toggleClass('empty-bucket', count === 0);
      bucket.data('label', `Unlinked · ${bucket.data('short')}\n${count} unlinked ${count === 1 ? 'gene' : 'genes'}`);
    });
  }

  function applyAnnotationHighlight() {
    if (!cy || !graphAnnotations) return;
    const phase = graphAnnotations.phases?.find((item) => item.id === phaseHighlight);
    const phaseActive = Boolean(phase);
    const locationActive = locationHighlight !== 'all';
    const active = phaseActive || locationActive;
    let matchCount = 0;

    cy.batch(() => {
      const subjects = cy.nodes('[kind = "gene"], [kind = "process"]');
      subjects.removeClass('annotation-match annotation-muted');
      subjects.forEach((node) => {
        const stages = node.data('stages') || [];
        const locations = node.data('locations') || [];
        const phaseMatches = !phaseActive || stages.some((stage) => phase.stages.includes(stage));
        const locationMatches = !locationActive || (locationHighlight === 'unmapped'
          ? locations.length === 0
          : locations.includes(locationHighlight));
        const matches = phaseMatches && locationMatches;
        node.toggleClass('annotation-match', active && matches);
        node.toggleClass('annotation-muted', active && !matches);
        if (active && matches && node.visible()) matchCount += 1;
      });

      cy.nodes('[kind = "bucket"]').forEach((bucket) => {
        const matches = bucket.children('.annotation-match').filter((child) => child.visible()).length > 0;
        bucket.toggleClass('annotation-match', active && matches);
        bucket.toggleClass('annotation-muted', active && !matches);
      });

      const unclassified = cy.nodes('[kind = "unclassified"]');
      const unclassifiedMatches = !phaseActive && locationHighlight === 'unmapped';
      unclassified.toggleClass('annotation-match', active && unclassifiedMatches);
      unclassified.toggleClass('annotation-muted', active && !unclassifiedMatches);

      cy.edges().forEach((edge) => {
        const matches = edge.source().hasClass('annotation-match') || edge.target().hasClass('annotation-match');
        edge.toggleClass('annotation-match', active && matches);
        edge.toggleClass('annotation-muted', active && !matches);
      });
    });
    annotationMatchCount = active ? matchCount : 0;
  }

  function togglePhaseHighlight(phaseId) {
    phaseHighlight = phaseHighlight === phaseId ? 'all' : phaseId;
  }

  function applyPresenceStyling() {
    if (!cy) return;
    cy.batch(() => {
      cy.nodes('[kind = "gene"]').forEach((n) => {
        n.removeClass('absent fragment present impact-absent');
        const st = presenceOf(n.data('id2'));
        if (st === 'NOT_FOUND' || st === 'E2') {
          n.addClass('absent');
          // high-impact absence: heavily-studied gene missing in this species
          const studied = counts?.[n.data('id2')]?.studied || 0;
          if (studied >= 3) n.addClass('impact-absent');
        }
        else if (st === 'FRAGMENT' || st === 'E3') n.addClass('fragment');
        else if (st) n.addClass('present');
      });
    });
    applySpeciesEvidenceStyling();
  }

  /** Host-class lens (D84): dim genes whose corpus evidence does not
   *  include the selected host class. Viral/unknown stay neutral. */
  function applyHostClassStyling() {
    if (!cy) return;
    const want = hostClassFilter;
    cy.batch(() => {
      cy.nodes('[kind = "gene"]').forEach((n) => {
        n.removeClass('host-dim');
        if (want === 'all') return;
        const cls = hostAssociations[n.data('id2')]?.class;
        if (cls === 'viral' || !cls) return;      // neutral
        const ok = want === 'aves' ? ['aves', 'both'].includes(cls)
          : want === 'mammal' ? ['mammalia', 'both'].includes(cls)
          : cls === 'both';
        if (!ok) n.addClass('host-dim');
      });
    });
  }

  /** Strain lens (D89): highlight edges with evidence mentioning the
   *  selected strain, dim the rest. Curated-only edges stay neutral. */
  function applyStrainStyling() {
    if (!cy) return;
    const want = strainFilter;
    cy.batch(() => {
      cy.edges().forEach((edge) => {
        edge.removeClass('ev-strain-match');
        if (want === 'all' || !edge.data('evidenceCount')) return;
        if ((edge.data('strains') || []).includes(want)) {
          edge.addClass('ev-strain-match');
        }
      });
    });
  }

  /** Evidence-species styling: highlight exact-species evidence, keep
   *  general evidence neutral, dim (not hide) explicitly other-species
   *  evidence. Applies only to edges with reviewed evidence. */
  function applySpeciesEvidenceStyling() {
    if (!cy) return;
    const tokens = selSpecies ? (SPECIES_TOKENS[selSpecies] || []) : [];
    cy.batch(() => {
      cy.edges().forEach((edge) => {
        edge.removeClass('ev-species-match ev-species-mismatch');
        if (!selSpecies || !tokens.length || !edge.data('evidenceCount')) return;
        const speciesList = edge.data('species') || [];
        if (!speciesList.length) return;           // general/no info → neutral
        const match = speciesList.some((sp) => {
          const s = (sp || '').toLowerCase();
          return tokens.some((t) => s.includes(t));
        });
        const generalOnly = speciesList.every((sp) => {
          const s = (sp || '').toLowerCase();
          return GENERAL_SPECIES_TOKENS.some((t) => s.includes(t));
        });
        if (match) edge.addClass('ev-species-match');
        else if (!generalOnly) edge.addClass('ev-species-mismatch');
      });
    });
  }

  function applyViewFilter() {
    if (!cy) return;
    hideEdgeTooltip(true);
    const show = VIEWS[view];
    cy.elements().removeClass('lens-hidden');

    if (show) {
      const genes = cy.nodes('[kind = "gene"]');
      let visibleGenes = genes.filter((n) => n.data('stages')?.some((stage) => show.includes(stage)));
      // Keep one-hop boundary nodes so cross-stage lines end somewhere meaningful.
      visibleGenes = visibleGenes.union(visibleGenes.neighborhood('node[kind = "gene"]'));
      genes.not(visibleGenes).addClass('lens-hidden');
      cy.nodes('[kind = "bucket"]').forEach((n) => {
        if (!show.includes(n.data('id2'))) n.addClass('lens-hidden');
      });
      cy.nodes('[kind = "unclassified"]').addClass('lens-hidden');
      if (!show.includes('VIRAL')) cy.nodes('[kind = "process"]').addClass('lens-hidden');
    }

    cy.edges().forEach((edge) => {
      if (edge.source().hasClass('lens-hidden') || edge.target().hasClass('lens-hidden')) {
        edge.addClass('lens-hidden');
      }
    });
    updateVisibleBuckets();
    applyAnnotationHighlight();

    const revision = ++layoutRevision;
    setTimeout(() => {
      if (!cy || revision !== layoutRevision) return;
      cy.resize();
      const layoutElements = cy.elements().filter((ele) => ele.visible());
      const activeMode = layoutMode;
      const options = activeMode === 'organic' ? organicLayout : elkLayout;
      cy.scratch('_activeLayoutMode', activeMode);
      const layout = layoutElements.layout({ ...options, fit: false, animate: false });
      layout.on('layoutstop', () => {
        if (revision !== layoutRevision) return;
        cy.scratch('_completedLayoutMode', activeMode);
        cy.scratch('_completedLayoutRevision', revision);
        if (pendingCenterGene) {
          const sym = pendingCenterGene;
          pendingCenterGene = null;
          const node = cy.nodes('[kind = "gene"]').filter((n) => n.data('id2') === sym).first();
          if (node?.length) setTimeout(() => selectAndCenterNode(node), 20);
        } else {
          fitGraph();
        }
      });
      layout.run();
    }, 30);
  }

  function resetLayout() {
    if (!cy) return;
    pendingCenterGene = geneEvidence?.sym || null;
    applyViewFilter();
  }

  function fitGraph() {
    if (!cy) return;
    const visible = layoutMode === 'organic'
      ? cy.nodes().filter((ele) => ele.visible())
      : view === 'all'
      ? cy.nodes('.pathway-node').filter((ele) => ele.visible())
      : cy.nodes('[kind = "gene"], [kind = "process"]').filter((ele) => ele.visible());
    if (visible.length) cy.animate({ fit: { eles: visible, padding: 80 } }, { duration: 380 });
  }

  function clampDraggedNode(node) {
    if (!cy || !node) return;
    const margin = 48;
    const position = node.renderedPosition();
    const clamped = {
      x: Math.max(margin, Math.min(Math.max(margin, cy.width() - margin), position.x)),
      y: Math.max(margin, Math.min(Math.max(margin, cy.height() - margin), position.y)),
    };
    if (clamped.x !== position.x || clamped.y !== position.y) node.renderedPosition(clamped);
  }

  function geneConnections(sym) {
    if (!cy || !sym) return [];
    const node = cy.getElementById(`G:${sym}`);
    if (!node || node.length === 0) return [];
    return node.connectedEdges().map((edge) => {
      const outgoing = edge.source().id() === node.id();
      const other = outgoing ? edge.target() : edge.source();
      return {
        sym: other.data('id2'), kind: edge.data('kind'), label: edge.data('label'), outgoing,
        mechanism: edge.data('mechanism'), evidenceCount: edge.data('evidenceCount') || 0,
        provenance: edge.data('provenance'),
      };
    }).sort((a, b) => a.sym.localeCompare(b.sym));
  }

  onMount(async () => {
    // Dynamically import the heavy graph libraries (code-split from main bundle)
    const [cytoscapeMod, elkMod, fcoseMod] = await Promise.all([
      import('cytoscape'), import('cytoscape-elk'), import('cytoscape-fcose'),
    ]);
    cytoscape = cytoscapeMod.default;
    cytoscape.use(elkMod.default);
    cytoscape.use(fcoseMod.default);

    const [m, ab, c, sa, rel, ha, cat, pe] = await Promise.all([
      fetch('data/avian_h5n1_model.json').then((r) => r.json()),
      fetch('data/gene_absence_summary.json').then((r) => r.ok ? r.json() : {}),
      fetch('data/gene_evidence_counts.json').then((r) => r.json()),
      fetch('data/gene_stage_assignment.json').then((r) => r.ok ? r.json() : {}).catch(() => ({})),
      fetch('data/gene_relationships.json').then((r) => r.ok ? r.json() : { edges: [] }).catch(() => ({ edges: [] })),
      fetch('data/gene_host_association.json').then((r) => r.ok ? r.json() : { genes: {} }).catch(() => ({ genes: {} })),
      fetchGeneCatalogue(),
      fetch('data/pathway_edges.json').then((r) => r.ok ? r.json() : { edges: [] }).catch(() => ({ edges: [] })),
    ]);
    model = m; absence = ab; counts = c; stageAssignment = sa;
    relationships = rel; hostAssociations = ha.genes || {};
    pathwayEdges = pe?.edges || [];
    // Presence metadata now; per-species calls load lazily from DuckDB on
    // species selection (Phase 2 Step 3: this page is memory-heavy with
    // Cytoscape — don't instantiate DuckDB-WASM here until a comparison
    // is actually requested)
    presence = {
      gene_catalogue: cat?.gene_catalogue || {},
      species: {},
    };
    catalogueSpecies = cat?.species_list || [];

    cy = cytoscape({
      container,
      elements: buildElements(),
      layout: elkLayout,
      style: [
        { selector: 'node[kind = "bucket"]',
          style: {
            label: 'data(label)', 'font-size': 12, 'font-weight': 600,
            'text-wrap': 'wrap', 'text-max-width': 180, 'line-height': 1.35,
            'text-valign': 'top', 'text-halign': 'left', 'text-margin-x': 2, 'text-margin-y': 10,
            shape: 'round-rectangle', 'background-opacity': 0.72,
            'border-width': 1.5, 'border-style': 'dashed', 'border-color': 'data(accent)',
            padding: 32, color: '#475569', 'background-color': 'data(fill)',
          } },
        { selector: 'node[kind = "unclassified"]',
          style: {
            label: 'data(label)', width: 290, height: 104, shape: 'round-rectangle',
            'background-color': '#fff7ed', 'background-opacity': 0.9,
            'border-color': '#f97316', 'border-width': 1.5, 'border-style': 'dashed',
            color: '#9a3412', 'font-size': 14, 'font-weight': 600,
            'text-wrap': 'wrap', 'text-max-width': 240, 'line-height': 1.45,
            'text-valign': 'center', 'text-halign': 'center',
            'overlay-color': '#f97316', 'overlay-opacity': 0,
          } },
        { selector: 'node[kind = "process"]',
          style: {
            label: 'data(label)', width: 88, height: 58, shape: 'round-rectangle',
            'background-color': '#312e81', 'border-color': '#8b5cf6', 'border-width': 3,
            color: '#ffffff', 'font-size': 12, 'font-weight': 700,
            'text-wrap': 'wrap', 'text-max-width': 76, 'text-valign': 'center', 'text-halign': 'center',
          } },
        { selector: 'node[kind = "gene"]',
          style: {
            label: 'data(label)', 'font-size': 'data(fontsize)', 'font-family': 'monospace',
            'font-weight': 600, 'text-valign': 'bottom', 'text-halign': 'center', 'text-margin-y': 7,
            shape: 'data(shape)', width: 'data(size)', height: 'data(size)',
            'background-color': 'data(fill)', 'border-width': 2.25,
            'border-color': 'data(accent)', color: '#0f172a',
          } },
        { selector: 'node.unlinked-node',
          style: { 'border-width': 1.5 } },
        { selector: 'node.viral',
          style: { 'background-color': '#ede9fe', 'border-color': '#7c3aed', 'border-width': 2.75 } },
        { selector: 'node.absent',
          style: { 'background-color': '#fee2e2', 'border-color': '#dc2626', 'border-width': 3.25 } },
        { selector: 'node.fragment',
          style: { 'border-color': '#f59e0b', 'border-style': 'dashed', 'border-width': 2.5 } },
        { selector: 'node.present',
          style: { 'border-color': '#16a34a' } },
        { selector: 'edge',
          style: {
            label: '', 'curve-style': 'bezier', 'control-point-step-size': 44,
            'target-arrow-color': '#3b82f6',
          } },
        { selector: 'edge[kind = "signal"]',
          style: { width: 2, 'line-color': '#60a5fa', 'target-arrow-shape': 'triangle',
            'target-arrow-color': '#3b82f6', 'arrow-scale': 0.9, opacity: 0.72 } },
        { selector: 'edge[kind = "inhibit"]',
          style: { width: 2.3, 'line-color': '#e11d48', 'target-arrow-shape': 'tee',
            'target-arrow-color': '#e11d48', 'arrow-scale': 1.2, opacity: 0.82 } },
        { selector: 'edge[kind = "interact"]',
          style: { width: 2, 'line-color': '#8b5cf6', 'line-style': 'dashed',
            'target-arrow-shape': 'triangle', 'target-arrow-color': '#8b5cf6',
            color: '#6d28d9', opacity: 0.8 } },
        { selector: 'edge[kind = "membership"]',
          style: { width: 1.25, 'line-color': '#a78bfa', 'line-style': 'dotted',
            'target-arrow-shape': 'none', opacity: 0.48, 'curve-style': 'bezier' } },
        // Literature-extracted mechanism edges — distinct from curated:
        // thinner, teal, dashed, semi-transparent
        { selector: 'edge.lit-edge',
          style: { width: 1.5, 'line-color': '#14b8a6', 'line-style': 'dashed',
            'target-arrow-shape': 'triangle', 'target-arrow-color': '#14b8a6',
            opacity: 0.55, 'curve-style': 'bezier' } },
        { selector: 'edge.lit-edge:hover',
          style: { opacity: 0.95, width: 2.5 } },
        { selector: 'edge.ev-species-match',
          style: { width: 3.4, opacity: 1, 'underlay-color': '#059669',
            'underlay-opacity': 0.22, 'underlay-padding': 3, 'z-index': 22 } },
        { selector: 'edge.ev-species-match[kind = "inhibit"]',
          style: { 'underlay-color': '#e11d48' } },
        { selector: 'edge.ev-species-mismatch',
          style: { width: 1.5, opacity: 0.22 } },
        { selector: 'edge.ev-strain-match',
          style: { width: 3.4, opacity: 1, 'underlay-color': '#b45309',
            'underlay-opacity': 0.2, 'underlay-padding': 3, 'z-index': 21 } },
        { selector: 'node.host-dim',
          style: { opacity: 0.25 } },
        { selector: 'node.annotation-match', style: {
          'underlay-color': '#0f766e', 'underlay-opacity': 0.18, 'underlay-padding': 9,
        } },
        { selector: 'edge.annotation-match', style: { opacity: 0.95 } },
        { selector: 'node.annotation-muted', style: { opacity: 0.18 } },
        { selector: 'edge.annotation-muted', style: { opacity: 0.07 } },
        { selector: 'node.dimmed', style: { opacity: 0.48 } },
        { selector: 'edge.dimmed', style: { opacity: 0.15 } },
        { selector: 'node.annotation-muted.dimmed', style: { opacity: 0.14 } },
        { selector: 'edge.annotation-muted.dimmed', style: { opacity: 0.05 } },
        { selector: 'node.label-hidden', style: { 'text-opacity': 0 } },
        { selector: 'node.focused', style: { 'border-width': 4, 'border-color': '#1d4ed8',
          'overlay-color': '#3b82f6', 'overlay-opacity': 0.12, 'overlay-padding': 12,
          'font-size': 13, 'text-opacity': 1 } },
        { selector: 'node.hovered', style: { 'font-size': 12, 'text-opacity': 1, 'z-index': 30 } },
        { selector: 'node.near', style: { opacity: 1 } },
        { selector: 'edge.near', style: { width: 3, opacity: 1, 'z-index': 20 } },
        { selector: 'node.panel-extra', style: { display: 'none' } },
        { selector: 'node.show-panel-extra', style: { display: 'element', opacity: 0.58 } },
        { selector: 'node.neutral-node.show-panel-extra', style: { opacity: 0.85 } },
        { selector: 'edge.ext-edge', style: { display: 'none' } },
        { selector: 'edge.show-ext-edge', style: { display: 'element' } },
        { selector: 'node.empty-bucket, .lens-hidden', style: { display: 'none' } },
      ],
    });

    cy.on('tap', 'node[kind = "gene"]', (evt) => {
      const n = evt.target;
      hideEdgeTooltip(true);
      geneQuery = n.data('id2');
      queryMessage = '';
      geneEvidence = { sym: n.data('id2'), note: n.data('note'), stage: n.data('stage') };
      focusNeighborhood(n);
    });
    cy.on('mouseover', 'node[kind = "gene"]', (evt) => evt.target.addClass('hovered'));
    cy.on('mouseout', 'node[kind = "gene"]', (evt) => evt.target.removeClass('hovered'));
    cy.on('mouseover', 'edge', (evt) => {
      if (!edgeTooltip?.pinned) showEdgeTooltip(evt.target, evt.renderedPosition);
    });
    cy.on('mouseout', 'edge', () => hideEdgeTooltip());
    cy.on('tap', 'edge', (evt) => showEdgeTooltip(evt.target, evt.renderedPosition, true));
    cy.on('grab', 'node.pathway-node, node[kind = "process"]', () => hideEdgeTooltip(true));
    cy.on('dragfree', 'node.pathway-node, node[kind = "process"]', (evt) => clampDraggedNode(evt.target));
    cy.on('zoom', () => { hideEdgeTooltip(true); applySemanticLabels(); });
    cy.on('pan', () => hideEdgeTooltip(true));
    cy.on('tap', 'node[kind = "unclassified"]', () => {
      hideEdgeTooltip(true);
      showUnassigned = !showUnassigned;
    });
    cy.on('tap', (evt) => { if (evt.target === cy) clearSelection(); });
    cy.nodes('.unlinked-node, [kind = "bucket"], [kind = "unclassified"]').ungrabify();
    applySemanticLabels(true);
    if (typeof window !== 'undefined') window.__cy = cy;

    const handleKeydown = (event) => { if (event.key === 'Escape') clearSelection(); };
    window.addEventListener('keydown', handleKeydown);
    resizeObserver = new ResizeObserver(() => cy?.resize());
    resizeObserver.observe(container);

    setTimeout(() => {
      applyViewFilter();
      // Deep link (#/model-cyto?gene=SYM): centre the gene after the first
      // layout settles. Panel-extra/neutral genes reveal the extended panel
      // first; the re-layout consumes pendingCenterGene on layoutstop.
      const wanted = getRoute()?.params?.gene;
      if (!wanted) return;
      const node = cy.nodes('[kind = "gene"]')
        .filter((n) => n.data('id2').toUpperCase() === wanted.toUpperCase()).first();
      if (!node || node.length === 0) return;
      if (node.hasClass('panel-extra') && !fullPanel) {
        pendingCenterGene = node.data('id2');
        fullPanel = true;
      } else {
        setTimeout(() => selectAndCenterNode(node), 400);
      }
    }, 300);
    cy.scratch('_handleKeydown', handleKeydown);
  });

  $effect(() => { selSpecies; applyPresenceStyling(); });
  $effect(() => { hostClassFilter; applyHostClassStyling(); });
  $effect(() => { strainFilter; applyStrainStyling(); });
  $effect(() => { view; layoutMode; applyViewFilter(); });
  $effect(() => {
    fullPanel;
    if (cy) {
      cy.nodes('.panel-extra').toggleClass('show-panel-extra', fullPanel);
      cy.edges('.ext-edge').toggleClass('show-ext-edge', fullPanel);
      updateVisibleBuckets();
      setTimeout(() => applyViewFilter(), 80);
    }
  });
  $effect(() => {
    showLabels; showAllLabels;
    applySemanticLabels(true);
  });
  $effect(() => {
    phaseHighlight; locationHighlight;
    applyAnnotationHighlight();
  });

  onDestroy(() => {
    resizeObserver?.disconnect();
    const handleKeydown = cy?.scratch('_handleKeydown');
    if (handleKeydown) window.removeEventListener('keydown', handleKeydown);
    if (typeof window !== 'undefined' && window.__cy === cy) delete window.__cy;
    cy?.destroy();
    cy = null;
  });
</script>

<svelte:head><title>{t('routes.modelcyto.follow.the.pathway.gene') || 'H5N1 host response'} — Roost</title></svelte:head>

<div class="max-w-7xl mx-auto space-y-4">
  {#if !embedded}
  <!-- Mobile notice -->
  <div class="lg:hidden bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm text-amber-700 dark:text-amber-300">
    📱 {t('model.cyto.mobile_notice.a')} <a href="#/model" class="underline">{t('model.cyto.mobile_notice.link')}</a>.
  </div>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div class="max-w-3xl">
      <div class="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">{t('routes.modelcyto.avian.host.response') || 'Avian H5N1 host response'}</div>
      <h1 class="mt-1 text-3xl font-bold tracking-tight text-slate-950 dark:text-white">{t('routes.modelcyto.follow.the.pathway.gene') || 'Follow the pathway, gene by gene'}</h1>
      <p class="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
        {t('modelcyto.pathway.desc') || 'Connected genes form the biological pathway. Dashed groups hold candidates that still lack a curated link.'}
      </p>
    </div>
    <a href="#/model" class="text-xs font-medium text-slate-500 hover:text-blue-700 dark:text-slate-400 dark:hover:text-blue-300">{t('routes.modelcyto.view.narrative.model') || 'View narrative model →'}</a>
  </header>
  {/if}

  <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800" aria-label={t('model.cyto.controls_aria')}>
    <div class="flex gap-1 overflow-x-auto border-b border-slate-200 p-2 dark:border-slate-700" role="tablist" aria-label={t('model.cyto.lenses_aria')}>
      {#each Object.entries(VIEW_META) as [key, meta]}
        <button
          class="whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold transition {view === key
            ? 'bg-slate-900 text-white shadow-sm dark:bg-blue-600'
            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-300 dark:hover:bg-slate-700'}"
          role="tab" aria-selected={view === key} onclick={() => { clearSelection(); view = key; }}>
          {t('view.' + key + '.label') || meta.label}
        </button>
      {/each}
    </div>

    <div class="grid gap-3 p-3 lg:grid-cols-[minmax(280px,1fr)_minmax(340px,0.9fr)_auto] lg:items-start">
      <div>
        <form class="flex" onsubmit={(event) => { event.preventDefault(); centerOnGene(); }}>
          <label for="gene-query" class="sr-only">{t('modelcyto.find.gene') || 'Find and center a gene'}</label>
          <div class="relative min-w-0 flex-1">
            <svg class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600 dark:text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
              <circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path>
            </svg>
            <input id="gene-query" list="graph-genes" bind:value={geneQuery}
              class="h-10 w-full rounded-l-xl border border-slate-300 bg-white pl-9 pr-3 font-mono text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:focus:ring-blue-900"
              placeholder={t('routes.modelcyto.find.gene.ddx') || 'Find a gene, e.g. DDX58'} autocomplete="off" />
            <datalist id="graph-genes">
              {#each searchableGenes as sym}<option value={sym}></option>{/each}
            </datalist>
          </div>
          <button type="submit" class="h-10 rounded-r-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700">{t('model.cyto.center')}</button>
        </form>
        {#if queryMessage}<div class="mt-1 text-xs font-medium text-rose-600" role="status">{queryMessage}</div>{/if}
      </div>

      <div>
        <!-- species picker is the SpeciesSearch combobox (named via its
             placeholder; the old <select id="species-context"> is gone) -->
        <SpeciesSearch
          bind:value={selSpecies}
          species={catalogueSpecies}
          commonNames={SPECIES_COMMON}
          placeholder={t('model.cyto.compare_species')}
          emptyLabel={t('model.cyto.compare_species')}
        />
        {#if selSpecies}
          <div class="mt-1 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <span class="text-green-700 dark:text-green-400">● {t('model.cyto.present')}</span><span class="text-amber-700 dark:text-amber-400">◌ {t('model.cyto.fragment')}</span><span class="text-rose-600">● {t('model.cyto.not_found')}</span>
            <span class="text-emerald-600" data-testid="species-evidence-legend">{t('routes.modelcyto.line.species.evidence') || '— line: species evidence'}</span>
          </div>
        {/if}
        <div class="mt-2 grid grid-cols-2 gap-2">
          <div class="min-w-0">
            <label for="host-class" class="mb-0.5 block truncate text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400" title={t('routes.modelcyto.dims.genes.without.matching') || 'Dims genes without matching host evidence'}>{t('model.cyto.host_evidence')}</label>
            <select
              id="host-class"
              class="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-700 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
              bind:value={hostClassFilter}
              data-testid="host-class-select"
            >
              <option value="all">{t('modelcyto.all.hosts') || 'All hosts'}</option>
              <option value="aves">Birds (aves)</option>
              <option value="mammal">{t('common.mammals') || 'Mammals'}</option>
              <option value="both">Birds + mammals</option>
            </select>
          </div>
          {#if edgeStrains.length}
            <div class="min-w-0">
              <label for="strain-filter" class="mb-0.5 block truncate text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400" title={t('tip.cyto.strain') || 'Highlights edges with that strain evidence'}>{t('model.cyto.strain')}</label>
              <select
                id="strain-filter"
                class="h-8 w-full rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-700 outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                bind:value={strainFilter}
                data-testid="strain-select"
              >
                <option value="all">{t('modelcyto.all.strains') || 'All strains'}</option>
                {#each edgeStrains as st}
                  <option value={st}>{st}</option>
                {/each}
              </select>
            </div>
          {/if}
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-1.5 lg:justify-end">
        <div class="layout-switch" role="group" aria-label={t('model.cyto.layout_aria')} title={t('model.cyto.layout_aria')}>
          <button
            class="layout-option {layoutMode === 'pathway' ? 'layout-option-active' : ''}"
            aria-pressed={layoutMode === 'pathway'}
            title={t('routes.modelcyto.arrange.genes.as.an') || 'Arrange genes as an upstream-to-downstream pathway'}
            onclick={() => setLayoutMode('pathway')}
          >{t('model.cyto.layout.pathway')}</button>
          <button
            class="layout-option {layoutMode === 'organic' ? 'layout-option-active' : ''}"
            aria-pressed={layoutMode === 'organic'}
            title={t('routes.modelcyto.arrange.genes.as.force') || 'Arrange genes as a force-directed interaction network'}
            onclick={() => setLayoutMode('organic')}
          >{t('model.cyto.layout.organic')}</button>
        </div>
        <button class="control-button {showLabels ? 'control-button-active' : ''}" aria-pressed={showLabels}
          title={t('tip.cyto.labels') || 'Show or hide curated gene labels'} onclick={() => showLabels = !showLabels}>{t('model.cyto.labels')}</button>
        <button class="control-button {showAllLabels ? 'control-button-active' : ''}" aria-pressed={showAllLabels}
          title={t('routes.modelcyto.also.label.low.evidence') || 'Also label low-evidence nodes'} onclick={() => showAllLabels = !showAllLabels}>{t('model.cyto.low_evidence')}</button>
        <button class="control-button {fullPanel ? 'control-button-active' : ''}" aria-pressed={fullPanel}
          title={t('tip.cyto.extended') || 'Show the extended assigned gene panel'} onclick={() => fullPanel = !fullPanel}>{t('model.cyto.extended_panel')}</button>
        {#if unassignedGenes.length}
          <button class="control-button {showUnassigned ? 'control-button-active' : ''}" aria-pressed={showUnassigned}
            title={t('routes.modelcyto.inspect.genes.without.defensible') || 'Inspect genes without a defensible pathway classification'} onclick={() => showUnassigned = !showUnassigned}>{t('model.cyto.unclassified')} · {unassignedGenes.length}</button>
        {/if}
        <button class="control-button" title={t('tip.cyto.fit') || 'Fit the visible graph in the canvas'} onclick={fitGraph}>{t('model.cyto.fit')}</button>
        <button class="control-button" title={t('tip.cyto.relayout') || 'Recompute the active layout and keep the selected gene in focus'} onclick={resetLayout}>{t('model.cyto.reset_layout')}</button>
      </div>
    </div>
    {#if graphAnnotations?.phases?.length}
      <div class="flex flex-col gap-2 border-t border-slate-200 px-3 py-2.5 dark:border-slate-700 xl:flex-row xl:items-center xl:justify-between">
        <div class="flex min-w-0 items-center gap-2 overflow-x-auto" aria-label="Conceptual infection progression">
          <span class="shrink-0 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Infection</span>
          <button
            class="phase-option {phaseHighlight === 'all' ? 'phase-option-active' : ''}"
            aria-pressed={phaseHighlight === 'all'}
            onclick={() => phaseHighlight = 'all'}
          >{t('common.all') || 'All'}</button>
          {#each graphAnnotations.phases as phase, index}
            {#if index > 0}<span class="text-xs text-slate-300 dark:text-slate-400" aria-hidden="true">→</span>{/if}
            <button
              class="phase-option {phaseHighlight === phase.id ? 'phase-option-active' : ''}"
              aria-pressed={phaseHighlight === phase.id}
              title={t('phase.' + phase.id + '.note') || phase.note}
              onclick={() => togglePhaseHighlight(phase.id)}
            >{t('phase.' + phase.id + '.short') || phase.short}</button>
          {/each}
          <span class="shrink-0 text-[10px] text-slate-600 dark:text-slate-400">{t('modelcyto.early.late') || 'early → late · conceptual, not clock time'}</span>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <label for="cell-location" class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">{t('model.cyto.cell_location')}</label>
          <select
            id="cell-location"
            class="h-8 rounded-lg border border-slate-300 bg-white px-2 text-xs font-semibold text-slate-700 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
            bind:value={locationHighlight}
          >
            <option value="all">{t('modelcyto.all.locations') || 'All locations'}</option>
            {#each graphAnnotations.locations || [] as location}
              <option value={location.id}>{location.label}</option>
            {/each}
          </select>
          {#if phaseHighlight !== 'all' || locationHighlight !== 'all'}
            <span class="rounded-full bg-teal-50 px-2 py-1 text-[10px] font-bold text-teal-700 dark:bg-teal-950 dark:text-teal-300">{annotationMatchCount} matches</span>
          {/if}
        </div>
      </div>
    {/if}
  </section>

  <div class="rounded-2xl border border-blue-100 bg-blue-50/70 px-4 py-3 dark:border-blue-900/60 dark:bg-blue-950/30">
    <div class="text-[10px] font-bold uppercase tracking-[0.16em] text-blue-700 dark:text-blue-300">{t('view.' + view + '.eyebrow') || VIEW_META[view].eyebrow}</div>
    <p class="mt-0.5 text-sm leading-5 text-slate-700 dark:text-slate-200">{t('view.' + view + '.summary') || VIEW_META[view].summary}</p>
  </div>

  <div class="flex flex-wrap gap-x-5 gap-y-2 px-1 text-[11px] font-medium text-slate-500 dark:text-slate-400" aria-label={t('model.cyto.legend_aria')}>
    <span class="inline-flex items-center gap-1.5"><i class="legend-line bg-blue-500 dark:bg-blue-400" aria-hidden="true"></i> {t('model.cyto.edge.activates')}</span>
    <span class="inline-flex items-center gap-1.5"><i class="legend-stop bg-rose-500 dark:bg-rose-400" aria-hidden="true"></i> {t('model.cyto.edge.inhibits')}</span>
    <span class="inline-flex items-center gap-1.5"><i class="legend-dash border-violet-500"></i> {t('model.cyto.edge.interaction')}</span>
    <span>{t('routes.modelcyto.node.colour.shape.response') || 'Node colour + shape = response stage'}</span><span>{t('routes.modelcyto.node.size.literature.weight') || 'Node size = literature weight'}</span><span>{t('routes.modelcyto.dashed.box.not.yet') || 'Dashed box = not yet connected'}</span>
  </div>
  <div class="shape-key" aria-label="Node shape key">
    <span class="shape-key-title">{t('model.cyto.shape_key')}</span>
    {#each SHAPE_LEGEND as [stage, label, shapeClass]}
      <span class="shape-key-item">
        <i class="shape-key-icon {shapeClass}" style="color: {STAGE_META[stage].accent}" aria-hidden="true"></i>
        {label}
      </span>
    {/each}
  </div>

  <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
    <section class="graph-shell relative min-h-[660px] overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-sm dark:border-slate-700 dark:bg-slate-900" aria-label={t('routes.modelcyto.interactive.infection.pathway.graph') || 'Interactive infection pathway graph'}>
      <div bind:this={container} class="h-[72vh] min-h-[660px] w-full"></div>
      {#if edgeTooltip}
        <div
          class="edge-tooltip pointer-events-none absolute z-30 max-w-72 -translate-x-1/2 -translate-y-[calc(100%+0.65rem)] rounded-lg border border-slate-200 bg-white/95 px-3 py-2 text-xs text-slate-600 shadow-lg backdrop-blur dark:border-slate-600 dark:bg-slate-800/95 dark:text-slate-200"
          style="left: {edgeTooltip.x}px; top: {edgeTooltip.y}px;"
          role="status"
          data-testid="edge-tooltip"
        >
          <div class="flex items-baseline gap-1">
            <span class="font-mono font-bold text-slate-900 dark:text-white">{edgeTooltip.source}</span>
            <span class="mx-1 text-blue-600 dark:text-blue-400">→</span>
            <span class="font-mono font-bold text-slate-900 dark:text-white">{edgeTooltip.target}</span>
          </div>
          <div class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span class="font-semibold text-slate-700 dark:text-slate-200">{edgeTooltip.relation}</span>
            {#if edgeTooltip.mechanism}<span class="text-slate-600 dark:text-slate-400">· {edgeTooltip.mechanism}</span>{/if}
            <span class="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-700 dark:text-slate-300" data-testid="edge-provenance">{edgeTooltip.provenance || 'curated'}</span>
            {#if edgeTooltip.evidenceCount}
              <span class="rounded-full bg-blue-50 px-1.5 py-0.5 text-[10px] font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-300" data-testid="edge-evidence-count">{edgeTooltip.evidenceCount} evidence{edgeTooltip.evidenceCount === 1 ? '' : 's'}</span>
            {/if}
          </div>
          {#if edgeTooltip.papers?.length}
            <ul class="mt-1 space-y-0.5 border-t border-slate-100 pt-1 dark:border-slate-700" data-testid="edge-citations">
              {#each edgeTooltip.papers as paper}
                <li class="truncate text-[10px] text-slate-500 dark:text-slate-400">{paper}</li>
              {/each}
            </ul>
          {/if}
          {#if edgeTooltip.species?.length}
            <div class="mt-1 flex flex-wrap gap-1">
              {#each edgeTooltip.species as sp}
                <span class="rounded-full bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700 dark:bg-teal-950 dark:text-teal-300">{sp}</span>
              {/each}
            </div>
          {/if}
          {#if edgeTooltip.strains?.length}
            <div class="mt-1 flex flex-wrap gap-1" data-testid="tooltip-strains">
              {#each edgeTooltip.strains as st}
                <span class="rounded-full bg-amber-50 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">{st}</span>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
      <div class="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-slate-200/80 bg-white/90 px-2.5 py-1.5 text-[10px] font-medium text-slate-500 shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-800/90 dark:text-slate-400">
        Drag the canvas to pan · drag pathway genes to adjust · hover a line for its relationship · Reset recomputes the {layoutMode} layout
      </div>
    </section>

    <aside class="min-h-[280px] rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800" aria-live="polite">
      {#if geneEvidence}
        {@const ev = absenceEvidence(geneEvidence.sym)}
        {@const links = geneConnections(geneEvidence.sym)}
        {@const stageMeta = STAGE_META[geneEvidence.stage] || STAGE_META.sensing}
        {@const locations = locationsFor(geneEvidence.sym)}
        <div class="border-b border-slate-200 p-4 dark:border-slate-700">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-[10px] font-bold uppercase tracking-[0.15em] text-blue-600 dark:text-blue-400">{t('model.stage.' + geneEvidence.stage + '.short') || stageMeta.short}</div>
              <h2 class="mt-1 font-mono text-2xl font-bold text-slate-950 dark:text-white">{geneEvidence.sym}</h2>
            </div>
            <button class="rounded-lg p-1 text-xl leading-none text-slate-600 dark:text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700" aria-label={t('routes.modelcyto.clear.selected.gene') || 'Clear selected gene'} onclick={clearSelection}>×</button>
          </div>
          {#if selSpecies}
            <div class="mt-2 inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
              {SPECIES_COMMON[selSpecies]} · {statusLabel(geneEvidence.sym)}
            </div>
          {/if}
          <div class="mt-2 flex flex-wrap gap-1">
            {#if locations.length}
              {#each locations as location}
                <span class="rounded-full bg-teal-50 px-2 py-1 text-[10px] font-semibold text-teal-700 dark:bg-teal-950 dark:text-teal-300">{locationLabel(location)}</span>
              {/each}
            {:else}
              <span class="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-500 dark:bg-slate-700 dark:text-slate-300">{t('routes.modelcyto.location.not.yet.mapped') || 'Location not yet mapped'}</span>
            {/if}
          </div>
          <p class="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{geneEvidence.note}</p>
          <a href="#/genes/{geneEvidence.sym}" class="mt-3 inline-flex text-xs font-semibold text-blue-700 hover:underline dark:text-blue-300">{t('routes.modelcyto.open.full.gene.record') || 'Open full gene record →'}</a>
        </div>

        <div class="p-4">
          <h3 class="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400">Direct pathway links · {links.length}</h3>
          {#if links.length}
            <div class="mt-2 space-y-1.5">
              {#each links as link}
                <button class="group flex w-full items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-2 text-left hover:border-blue-300 hover:bg-blue-50 dark:border-slate-700 dark:hover:border-blue-700 dark:hover:bg-blue-950/30"
                  onclick={() => centerOnGene(link.sym)}>
                  <span class="w-4 text-center text-sm {link.kind === 'inhibit' ? 'text-rose-500' : link.kind === 'interact' ? 'text-violet-500' : 'text-blue-600 dark:text-blue-400'}">{link.outgoing ? '→' : '←'}</span>
                  <span class="min-w-0 flex-1">
                    <span class="block font-mono text-xs font-bold text-slate-800 group-hover:text-blue-700 dark:text-slate-100">{link.sym}</span>
                    <span class="block truncate text-[10px] text-slate-500 dark:text-slate-400">{link.label}</span>
                  </span>
                  {#if link.evidenceCount}
                    <span class="shrink-0 rounded-full bg-blue-50 px-1.5 py-0.5 text-[9px] font-bold text-blue-700 dark:bg-blue-950 dark:text-blue-300" title={t('routes.modelcyto.link.evidencecount.reviewed.evidence') || '{link.evidenceCount} reviewed evidence record(s) across papers'} data-testid="drawer-evidence-count">{link.evidenceCount}ev</span>
                  {/if}
                </button>
              {/each}
            </div>
          {:else}
            <p class="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">{t('modelcyto.no.edge') || 'This model gene has no curated pathway edge yet, so it remains in an unlinked group.'}</p>
          {/if}

          <h3 class="mt-5 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400">{t('routes.modelcyto.species.evidence') || 'Species evidence'}</h3>
          {#if ev.length}
            <div class="mt-2 space-y-3">
              {#each ev.slice(0, 3) as r}
                <div class="border-l-2 border-rose-300 pl-3 text-xs leading-5 text-slate-600 dark:text-slate-300">
                  <div><span class="font-semibold">{r.manipulation}</span> in <em>{r.host}</em> — {r.phenotype}</div>
                  <a href="#/papers/{r.paper_id}" class="mt-1 inline-flex text-blue-600 dark:text-blue-400 hover:underline">{r.tag} · {r.paper_id}{r.year ? `, ${r.year}` : ''}</a>
                </div>
              {/each}
            </div>
          {:else if selSpecies}
            <p class="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">{t('routes.modelcyto.no.avian.absence.evidence') || 'No avian absence evidence has been mined for this gene.'}</p>
          {:else}
            <p class="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">{t('routes.modelcyto.choose.species.to.layer') || 'Choose a species to layer gene-presence calls onto the pathway.'}</p>
          {/if}
        </div>
      {:else}
        <div class="p-5">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300">⌁</div>
          <h2 class="mt-4 text-base font-bold text-slate-900 dark:text-white">{t('model.cyto.trace_title')}</h2>
          <p class="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{t('modelcyto.select.connected') || 'Select any connected gene to keep its neighbours vivid and expose the meaning of each edge. The rest of the graph stays visible as context.'}</p>
          <ol class="mt-5 space-y-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
            <li class="flex gap-2"><span class="step-number">1</span><span>{t('routes.modelcyto.use.lens.to.isolate') || 'Use a lens to isolate one biological story.'}</span></li>
            <li class="flex gap-2"><span class="step-number">2</span><span>{t('routes.modelcyto.search.by.gene.symbol') || 'Search by gene symbol to center it instantly.'}</span></li>
            <li class="flex gap-2"><span class="step-number">3</span><span>{t('routes.modelcyto.choose.species.to.compare') || 'Choose a species to compare presence calls.'}</span></li>
          </ol>
        </div>
      {/if}
    </aside>
  </div>

  {#if showUnassigned && unassignedGenes.length}
    <section class="rounded-2xl border border-orange-200 bg-orange-50/60 p-4 dark:border-orange-900 dark:bg-orange-950/20">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-bold text-orange-950 dark:text-orange-100">Unclassified evidence gap · {unassignedGenes.length} genes</h2>
          <p class="mt-1 text-xs leading-5 text-orange-800/80 dark:text-orange-200/70">{t('modelcyto.no.function') || 'No function match, literature claim or defensible pathway stage has been assigned yet.'}</p>
        </div>
        <button class="text-xl leading-none text-orange-500" aria-label={t('tip.cyto.close.unclassified') || 'Close unclassified gene list'} onclick={() => showUnassigned = false}>×</button>
      </div>
      <div class="mt-3 flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
        {#each unassignedGenes as sym}
          <a href="#/genes/{sym}" class="rounded-md border border-orange-200 bg-white px-1.5 py-0.5 font-mono text-[10px] text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-orange-900 dark:bg-slate-800 dark:text-slate-300">{sym}</a>
        {/each}
      </div>
    </section>
  {/if}
</div>

<style>
  .control-button {
    height: 2.25rem;
    border-radius: 0.65rem;
    border: 1px solid rgb(203 213 225);
    background: white;
    padding: 0 0.65rem;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
    color: rgb(71 85 105);
    transition: 150ms ease;
  }
  .control-button:hover { border-color: rgb(147 197 253); color: rgb(29 78 216); }
  .control-button-active { border-color: rgb(96 165 250); background: rgb(239 246 255); color: rgb(29 78 216); }
  .layout-switch { display: inline-flex; height: 2.25rem; overflow: hidden; border: 1px solid rgb(203 213 225); border-radius: 0.65rem; background: rgb(248 250 252); }
  .layout-option { padding: 0 0.65rem; border: 0; background: transparent; color: rgb(100 116 139); font-size: 0.75rem; font-weight: 700; white-space: nowrap; transition: 150ms ease; }
  .layout-option + .layout-option { border-left: 1px solid rgb(203 213 225); }
  .layout-option:hover { color: rgb(29 78 216); }
  .layout-option-active { background: rgb(15 23 42); color: white; }
  .layout-option-active:hover { color: white; }
  .phase-option { flex: none; border-radius: 999px; border: 1px solid rgb(203 213 225); background: white; padding: 0.25rem 0.55rem; color: rgb(71 85 105); font-size: 0.68rem; font-weight: 700; line-height: 1rem; white-space: nowrap; transition: 150ms ease; }
  .phase-option:hover { border-color: rgb(94 234 212); color: rgb(15 118 110); }
  .phase-option-active { border-color: rgb(13 148 136); background: rgb(240 253 250); color: rgb(15 118 110); }
  .legend-line, .legend-dash { width: 1.6rem; height: 0; border-top-width: 2px; }
  .legend-dash { border-top-style: dashed; }
  .legend-stop { width: 1.6rem; height: 2px; position: relative; }
  .legend-stop::after { content: ''; position: absolute; right: 0; top: -3px; width: 2px; height: 8px; background: inherit; }
  .step-number { display: inline-flex; width: 1.25rem; height: 1.25rem; flex: none; align-items: center; justify-content: center; border-radius: 999px; background: rgb(239 246 255); color: rgb(29 78 216); font-weight: 700; }
  .shape-key { display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem 0.9rem; border: 1px solid rgb(226 232 240); border-radius: 0.75rem; background: rgb(255 255 255 / 0.72); padding: 0.55rem 0.75rem; color: rgb(100 116 139); font-size: 0.68rem; font-weight: 600; }
  .shape-key-title { color: rgb(51 65 85); font-size: 0.65rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
  .shape-key-item { display: inline-flex; align-items: center; gap: 0.35rem; white-space: nowrap; }
  .shape-key-icon { display: inline-block; width: 0.9rem; height: 0.9rem; flex: none; background: currentColor; }
  .shape-vee { clip-path: polygon(0 0, 50% 28%, 100% 0, 72% 100%, 28% 100%); }
  .shape-circle { border-radius: 999px; }
  .shape-diamond { clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%); }
  .shape-triangle { clip-path: polygon(50% 0, 100% 100%, 0 100%); }
  .shape-rounded { border-radius: 0.25rem; }
  .shape-star { clip-path: polygon(50% 0, 61% 34%, 98% 34%, 68% 55%, 79% 91%, 50% 70%, 21% 91%, 32% 55%, 2% 34%, 39% 34%); }
  .shape-cut { clip-path: polygon(20% 0, 100% 0, 100% 80%, 80% 100%, 0 100%, 0 20%); }
  .shape-octagon { clip-path: polygon(30% 0, 70% 0, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0 70%, 0 30%); }
  .shape-tag { clip-path: polygon(0 0, 72% 0, 100% 50%, 72% 100%, 0 100%); }
  .shape-hexagon { clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
  .graph-shell { background-image: radial-gradient(circle at 1px 1px, rgb(203 213 225 / 0.42) 1px, transparent 0); background-size: 22px 22px; }
  :global(.dark) .control-button { border-color: rgb(71 85 105); background: rgb(15 23 42); color: rgb(203 213 225); }
  :global(.dark) .control-button-active { border-color: rgb(59 130 246); background: rgb(30 58 138 / 0.35); color: rgb(147 197 253); }
  :global(.dark) .layout-switch { border-color: rgb(71 85 105); background: rgb(15 23 42); }
  :global(.dark) .layout-option { color: rgb(203 213 225); }
  :global(.dark) .layout-option + .layout-option { border-left-color: rgb(71 85 105); }
  :global(.dark) .layout-option-active { background: rgb(59 130 246); color: white; }
  :global(.dark) .phase-option { border-color: rgb(71 85 105); background: rgb(15 23 42); color: rgb(203 213 225); }
  :global(.dark) .phase-option-active { border-color: rgb(45 212 191); background: rgb(19 78 74 / 0.4); color: rgb(94 234 212); }
  :global(.dark) .shape-key { border-color: rgb(51 65 85); background: rgb(15 23 42 / 0.72); color: rgb(148 163 184); }
  :global(.dark) .shape-key-title { color: rgb(226 232 240); }
  :global(.dark) .graph-shell { background-image: radial-gradient(circle at 1px 1px, rgb(71 85 105 / 0.35) 1px, transparent 0); }
</style>
