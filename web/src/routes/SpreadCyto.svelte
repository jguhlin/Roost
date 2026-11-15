<script>
  /**
   * SpreadCyto — the migration/spread model as an interactive Cytoscape
   * graph (BETA). Route: #/spread-cyto
   *
   * Buckets = model stages (colored by accent), child nodes = the species/
   * factors each stage names, edges = stage-to-stage transmission pathways
   * with short labels. Species nodes deep-link into the species pages.
   * URL state: ?node=<id> selects + centers an element.
   */
  import { onMount, onDestroy } from 'svelte';
  // Performance: cytoscape + elk dynamically imported on mount
  let cytoscape = null;
  import { t } from '../lib/stores/i18n.svelte.js';
  import { navigate, getRoute, updateParams, subscribe as routerSubscribe } from '../lib/stores/router.js';


  let container = $state(null);
  let cy = $state(null);
  let loading = $state(true);
  let model = $state(null);
  let selected = $state(null);   // {id, label, note, stage, sci}
  let selectedEdge = $state(/** @type {any | null} */ (null)); // Phase 3: evidence panel
  let edgeParams = $state(/** @type {any | null} */ (null));   // Layer D parameters
  let mutationLinks = $state(null); // Phase 4: edge → adaptation markers
  let regions = $state(null);       // Phase 5: region risk data
  let flyways = $state(null);
  let activeRegion = $state(null);  // key into regions.regions
  let regionStats = $state(null);   // {first, total, flywayDetections}
  let showDiverges = $state(false);
  let showAdditions = $state(false);
  let matchCount = $state(0);

  // --- Phase 1: the timeline (SPREAD_MODEL.md) ---
  // Periods: yearly pre-2021 (sparse EMPRES era), monthly 2021+ (panzootic).
  let periods = $state([]);        // [{key, label, start, end, count}]
  let periodIdx = $state(0);       // playhead index
  let playing = $state(false);
  let playTimer = null;
  let speciesStats = $state(null); // sci -> {first, total}
  let events = $state([]);         // curated stamps (cited)
  let selectedEvent = $state(null);
  let timelineReady = $state(false);

  // --- Phase 2: data-join styling (species table × susceptibility) ---
  let speciesJoin = $state(null);   // sci -> {det, countries, genomes, mort, susc}

  const SUSC_COLORS = {
    highly_tolerant: '#16a34a', tolerant: '#84cc16', intermediate: '#d97706',
    susceptible: '#ea580c', highly_susceptible: '#dc2626',
  };

  async function loadSpeciesJoin(scis) {
    if (!scis.length) return new Map();
    try {
      const { db, dbStore } = await import('../lib/stores/db.js');
      await dbStore.loadSpecies();
      await dbStore.loadSusceptibility();
      const list = scis.map(x => `'${x.replace(/'/g, "''")}'`).join(', ');
      const rows = await db.query(`
        SELECT s.scientific_name, s.detection_count, s.country_count,
               s.genome_count, s.mortality_rate, su.susceptibility_class
        FROM species s LEFT JOIN susceptibility su
          ON s.scientific_name = su.scientific_name
        WHERE s.scientific_name IN (${list})`);
      return new Map(rows.map(r => [r.scientific_name, {
        det: Number(r.detection_count) || 0,
        countries: Number(r.country_count) || 0,
        genomes: Number(r.genome_count) || 0,
        mort: r.mortality_rate == null ? null : Number(r.mortality_rate),
        susc: r.susceptibility_class || null,
      }]));
    } catch (e) {
      console.error('[spread-cyto] species join failed:', e);
      return new Map();
    }
  }

  const logSize = (n, min = 44, max = 96) => {
    if (!n) return min;
    const tscale = Math.log10(n) / Math.log10(2200000);   // mallard caps the scale
    return Math.round(min + tscale * (max - min));
  };

  function chipFor(st) {
    if (!st) return '';
    const parts = [fmtK(st.det), plural(st.countries, 'country')];
    if (st.genomes) parts.push(plural(st.genomes, 'genome'));
    if (st.mort != null && st.mort >= 0.5) parts.push(`${Math.round(st.mort * 100)}% mortality`);
    return parts.join(' · ');
  }

  const MAX_PERIODS = 400;

  function buildPeriods(dateCounts) {
    // dateCounts: Map(dateStr -> n). Adaptive buckets.
    const dates = [...dateCounts.keys()].sort();
    if (!dates.length) return [];
    const first = new Date(dates[0]), last = new Date(dates[dates.length - 1]);
    const out = [];
    const push = (start, label) => {
      const end = new Date(start); // exclusive
      let n = 0;
      for (const [d, c] of dateCounts) {
        const dt = new Date(d);
        if (dt >= start && dt < end) n += c;
      }
      out.push({ key: start.toISOString().slice(0, 10), label, start, end, count: n });
    };
    const year = (d) => new Date(d.getFullYear(), 0, 1);
    for (let y = first.getFullYear(); y <= 2020 && y <= last.getFullYear(); y++) {
      push(new Date(Date.UTC(y, 0, 1)), String(y));
    }
    const m = new Date(Date.UTC(Math.max(first.getFullYear(), 2021), 0, 1));
    while (m <= last && out.length < MAX_PERIODS) {
      const label = m.toLocaleString('en', { month: 'short', year: 'numeric', timeZone: 'UTC' });
      const end = new Date(m); end.setUTCMonth(end.getUTCMonth() + 1);
      push(new Date(m), label);
      m.setUTCMonth(m.getUTCMonth() + 1);
    }
    return out;
  }

  const cumulativeAt = (idx) => {
    let n = 0;
    for (let i = 0; i <= idx; i++) n += periods[i].count;
    return n;
  };

  async function loadTimeline() {
    try {
      const { db, dbStore } = await import('../lib/stores/db.js');
      await dbStore.loadDetections();
      const [dates, sp] = await Promise.all([
        db.query(`SELECT date_iso, COUNT(*) AS n FROM detections
                  WHERE date_iso IS NOT NULL GROUP BY date_iso ORDER BY date_iso`),
        db.query(`SELECT scientific_name, MIN(date_iso) AS first, COUNT(*) AS total
                  FROM detections WHERE date_iso IS NOT NULL AND scientific_name IS NOT NULL
                  GROUP BY scientific_name`),
      ]);
      const dateCounts = new Map(dates.map(r => [r.date_iso, Number(r.n)]));
      periods = buildPeriods(dateCounts);
      speciesStats = new Map(sp.map(r => [r.scientific_name, { first: r.first, total: Number(r.total) }]));
    } catch (e) {
      console.error('[spread-cyto] timeline failed:', e);
    }
    try {
      const r = await fetch('data/spread_events.json');
      // curated events live in data/manual/, exported alongside the model
      const ev = r.ok ? await r.json() : { events: [] };
      events = (ev.events || []).map(e => ({ ...e, idx: periodIndexFor(e.date) }));
    } catch { events = []; }
    timelineReady = true;
    applyTimelineStyles();
  }

  function periodIndexFor(dateStr) {
    const dt = new Date(dateStr.length === 4 ? `${dateStr}-01-01` : `${dateStr}-01`);
    for (let i = periods.length - 1; i >= 0; i--) {
      if (periods[i].start <= dt) return i;
    }
    return 0;
  }

  function applyTimelineStyles() {
    if (!cy || !periods.length || !timelineReady) return;
    const periodStart = periods[periodIdx].start;
    cy.batch(() => {
      cy.nodes('[kind = "element"]').forEach(n => {
        const d = n.data();
        let active = true;
        if (d.sci && speciesStats) {
          const st = speciesStats.get(d.sci);
          active = st ? new Date(st.first) <= t : true;
        }
        n.toggleClass('faded', !active);
      });
      cy.nodes('[kind = "bucket"]').forEach(b => {
        const kids = b.children('[kind = "element"][sci]');
        let n = 0;
        kids.forEach(k => {
          const st = speciesStats?.get(k.data('sci'));
          if (st && new Date(st.first) <= t) n += st.total;
        });
        b.data('countLabel', n ? `${fmtK(n)} detections` : '');
      });
    });
  }

  function fmtK(n) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`;
    return String(n);
  }
  const plural = (n, word) => n === 1 ? `1 ${word}` : word === 'country' ? `${n} countries` : `${n} ${word}s`;

  function setPeriod(idx, { fromUser = false } = {}) {
    periodIdx = Math.max(0, Math.min(periods.length - 1, idx));
    applyTimelineStyles();
    if (fromUser) {
      clearTimeout(setPeriod._deb);
      setPeriod._deb = setTimeout(() => {
        updateParams({ t: periods[periodIdx].key.slice(0, 7) });
      }, 400);
    }
  }

  function togglePlay() {
    playing = !playing;
    clearInterval(playTimer);
    if (playing) {
      if (periodIdx >= periods.length - 1) setPeriod(0);
      playTimer = setInterval(() => {
        if (periodIdx >= periods.length - 1) { playing = false; clearInterval(playTimer); return; }
        setPeriod(periodIdx + 1);
      }, 350);
    }
  }

  $effect(() => {
    void periodIdx;
    applyTimelineStyles();
  });

  const elId = (stageId, i) => `${stageId}::${i}`;

  function buildElements(m, sciLookup, sj) {
    const els = [];
    for (const st of m.stages) {
      els.push({
        group: 'nodes',
        data: {
          id: st.id, kind: 'bucket', label: st.short || st.title,
          accent: st.accent, count: (st.elements || []).length,
          note: st.desc,
        },
      });
      (st.elements || []).forEach(([name, note], i) => {
        const id = elId(st.id, i);
        const sci = sciLookup.get((name || '').toLowerCase());
        const stt = sci ? sj?.get(sci) : null;
        const chip = chipFor(stt);
        els.push({
          group: 'nodes',
          data: {
            id, kind: 'element', label: chip ? `${name}\n${chip}` : name,
            note, parent: st.id,
            accent: st.accent, sci: sci || null, hasLink: !!sci,
            // Phase 2: data-join styling
            sizeW: stt ? logSize(stt.det) : 118,
            sizeH: stt ? (chip ? 58 : 44) : 40,
            suscColor: stt?.susc ? SUSC_COLORS[stt.susc] : null,
            susc: stt?.susc || null, mort: stt?.mort ?? null,
            chip,
          },
        });
      });
    }
    (m.connections || []).forEach((c, ci) => {
      const ev = m.evidence?.edges?.[`${c.from}->${c.to}`];
      const count = ev?.count ?? 0;
      const mLinkHint = (window.__spreadMutations?.edges?.[`${c.from}->${c.to}`]) ? '🧬' : '';
      const contested = !!ev?.contested;
      els.push({
        group: 'edges',
        data: {
          id: `E${ci}:${c.from}->${c.to}`, source: c.from, target: c.to,
          label: (c.label || '') + (count ? ` · ${count}` : '') + (mLinkHint ? ` ${mLinkHint}` : ''),
          note: c.note || '',
          // Phase 3: evidence layer
          evCount: count, contested,
          papers: ev?.papers || [], mechanisms: ev?.mechanisms || {},
          grounded: ev?.grounded ?? 0,
          inferred: count === 0,
          width: 1.5 + Math.min(count, 20) * 0.18,
          color: contested ? '#d97706' : count ? '#64748b' : '#cbd5e1',
          lineStyle: contested || count === 0 ? 'dashed' : 'solid',
        },
      });
    });
    return els;
  }

  /** species_index lookup: name (sci or common) → scientific name */
  function buildSciLookup(index) {
    const map = new Map();
    for (const s of index || []) {
      if (s.sci) map.set(s.sci.toLowerCase(), s.sci);
      if (s.com) map.set(s.com.toLowerCase(), s.sci);
    }
    return map;
  }

  onMount(async () => {
    // Dynamically import heavy graph libraries (code-split from main bundle)
    const [cytoscapeMod, elkMod] = await Promise.all([
      import('cytoscape'), import('cytoscape-elk'),
    ]);
    cytoscape = cytoscapeMod.default;
    cytoscape.use(elkMod.default);

    let urlReady = false;
    const applyRoute = (route) => {
      if (route.page !== 'spread-cyto' || !urlReady || !cy) return;
      const want = route.params?.node || null;
      const node = want ? cy.getElementById(want) : null;
      const same = (selected?.id || null) === want;
      if (!same) selectNode(node && node.length ? node : null, false);
      const tParam = route.params?.t;
      if (tParam && timelineReady) {
        const idx = periodIndexFor(tParam);
        if (idx !== periodIdx) setPeriod(idx);
      }
      const reg = route.params?.region || null;
      if (reg !== activeRegion) activeRegion = reg;
    };
    const cleanupRoute = routerSubscribe(applyRoute);

    try {
      const [mRes, idxRes] = await Promise.all([
        fetch('data/h5n1_spread_model.json').then(r => r.json()),
        fetch('data/species_index.json').then(r => r.ok ? r.json() : []).catch(() => []),
      ]);
      model = mRes;
      try {
        const mr = await fetch('data/spread_mutations.json');
        mutationLinks = mr.ok ? await mr.json() : null;
        if (typeof window !== 'undefined') window.__spreadMutations = mutationLinks;
      } catch { mutationLinks = null; }
      try {
        const [rr, fr, or_] = await Promise.all([
          fetch('data/spread_regions.json'), fetch('data/flyways.json'),
          fetch('data/species_index.json'),
        ]);
        regions = rr.ok ? await rr.json() : null;
        flyways = fr.ok ? await fr.json() : null;
        // stash the index for the region at-risk lookup
        if (or_.ok && typeof window !== 'undefined') {
          window.__overlaySpecies = await or_.json();
        }
      } catch { regions = null; flyways = null; }
      const sciLookup = buildSciLookup(idxRes);
      const linkedScis = [...sciLookup.values()]
        .filter(sci => (mRes.stages || []).some(st =>
          (st.elements || []).some(([n]) => sciLookup.get((n || '').toLowerCase()) === sci)));
      speciesJoin = await loadSpeciesJoin(linkedScis);
      matchCount = linkedScis.length;

      cy = cytoscape({
        container,
        elements: buildElements(mRes, sciLookup, speciesJoin),
        layout: {
          name: 'elk',
          elk: {
            algorithm: 'elk.layered',
            'elk.direction': 'RIGHT',
            'elk.spacing.nodeNode': '48',
            'elk.layered.spacing.nodeNodeBetweenLayers': '130',
            'elk.spacing.componentComponent': '140',
            'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
            'elk.padding': '[top=40,left=50,bottom=40,right=50]',
            'elk.edgeRouting': 'ORTHOGONAL',
          },
          fit: true, padding: 60,
        },
        style: [
          { selector: 'node[kind = "bucket"]',
            style: {
              label: 'data(label)', 'font-size': 16, 'font-weight': 700,
              'text-wrap': 'wrap', 'text-max-width': 150,
              shape: 'round-rectangle', 'background-opacity': 0.35,
              'border-width': 1.5, 'border-style': 'dashed',
              'border-color': 'data(accent)', 'background-color': 'data(accent)',
              color: '#334155', padding: 34,
              'text-valign': 'top', 'text-halign': 'left',
              'text-margin-x': 4, 'text-margin-y': 8,
            } },
          { selector: 'node[kind = "element"]',
            style: {
              label: 'data(label)', 'font-size': 13,
              'text-wrap': 'wrap', 'text-max-width': 140,
              shape: 'round-rectangle', width: 'data(sizeW)', height: 'data(sizeH)',
              'background-color': '#ffffff', 'border-width': 1.5,
              'border-color': 'data(accent)', color: '#0f172a',
              'text-valign': 'center', 'text-halign': 'center',
            } },
          { selector: 'node[kind = "element"][?hasLink]',
            style: { 'border-style': 'solid', 'font-weight': 600 } },
          { selector: 'node[kind = "element"][?hasLink][?suscColor]',
            style: { 'border-color': 'data(suscColor)', 'border-width': 3 } },
          { selector: 'node[kind = "element"][?hasLink][!?suscColor]',
            style: { 'border-style': 'solid' } },
          { selector: 'node[kind = "element"][!hasLink]',   // groups/factors: muted
            style: { 'border-style': 'dashed', 'background-color': '#f8fafc' } },
          { selector: 'node.faded',
            style: { opacity: 0.25, 'text-opacity': 0.35 } },
          { selector: 'node.selected',
            style: { 'border-width': 3, 'overlay-color': '#2563eb', 'overlay-opacity': 0.15 } },
          { selector: 'edge',
            style: {
              label: 'data(label)', 'font-size': 11, color: '#64748b',
              width: 'data(width)', 'line-color': 'data(color)',
              'line-style': 'data(lineStyle)',
              'target-arrow-shape': 'triangle', 'arrow-scale': 0.9,
              'curve-style': 'bezier', 'text-rotation': 'autorotate',
              'text-margin-y': -10,
            } },
          { selector: 'edge.evid-selected',
            style: { width: 4, 'overlay-color': '#2563eb', 'overlay-opacity': 0.18 } },
        ],
      });

      // Dev/test introspection (window.__cy convention)
      if (typeof window !== 'undefined') window.__cy = cy;

      cy.on('tap', 'edge', (e) => {
        const d = e.target.data();
        const mLink = mutationLinks?.edges?.[`${d.source}->${d.target}`];
        edgeParams = model?.evidence?.parameters?.[`${d.source}->${d.target}`] ?? null;
        selectedEdge = {
          label: model.stages.find(x => x.id === d.source)?.short || d.source,
          to: model.stages.find(x => x.id === d.target)?.short || d.target,
          note: d.note, count: d.evCount, contested: d.contested,
          inferred: d.inferred, papers: d.papers, mechanisms: d.mechanisms,
          grounded: d.grounded,
          mutations: mLink?.mutations || [],
        };
        selected = null;
        cy.edges().removeClass('evid-selected');
        e.target.addClass('evid-selected');
      });
      cy.on('tap', 'node[kind = "element"]', (e) => selectNode(e.target, true));
      cy.on('tap', 'node[kind = "bucket"]', (e) => {
        selected = { id: e.target.id(), label: e.target.data('label'),
                     note: e.target.data('note'), stage: true, sci: null };
        updateParams({ node: null });
      });
      cy.on('tap', (e) => {
        if (e.target === cy) selectNode(null, true);
      });

      loading = false;
      urlReady = true;
      applyRoute(getRoute());
      loadTimeline().then(() => {
        // ?t= restore (after periods exist)
        const tParam2 = getRoute()?.params?.t;
        if (tParam2) setPeriod(periodIndexFor(tParam2));
      });
    } catch (err) {
      loading = false;
      console.error('[spread-cyto] failed:', err);
    }
    return cleanupRoute;
  });

  onDestroy(() => { cy?.destroy(); });

  function selectNode(node, fromUser) {
    selectedEdge = null;
    cy?.edges()?.removeClass('evid-selected');
    if (!node || !node.length) {
      selected = null;
      if (fromUser) updateParams({ node: null });
      return;
    }
    const d = node.data();
    selected = { id: d.id, label: d.label, note: d.note, sci: d.sci || null, stage: false,
                 chip: d.chip || null, susc: d.susc || null };
    cy.elements().removeClass('selected');
    node.addClass('selected');
    if (fromUser) {
      updateParams({ node: d.id });
      cy.center(node);
    }
  }

  $effect(() => {
    void activeRegion;
    if (!timelineReady) return;
    updateParams({ region: activeRegion || null });
  });

  $effect(() => {
    void activeRegion;
    if (!activeRegion || !regions) { regionStats = null; return; }
    computeRegionStats(activeRegion);
  });

  async function computeRegionStats(key) {
    const r = regions?.regions?.[key];
    if (!r) { regionStats = null; return; }
    try {
      const { db, dbStore } = await import('../lib/stores/db.js');
      await dbStore.loadDetections();
      const iso = r.iso3.map(c => `'${c}'`).join(', ');
      const rows = await db.query(`
        SELECT MIN(date_iso) AS first, COUNT(*) AS total,
               COUNT(DISTINCT scientific_name) AS species
        FROM detections WHERE country IN (${iso}) AND date_iso IS NOT NULL`);
      // flyway exposure
      const fw = flyways?.flyways?.[r.flyway];
      let flywayDetections = 0;
      if (fw) {
        const fwIso = fw.countries.map(c => `'${c}'`).join(', ');
        const fwRows = await db.query(
          `SELECT COUNT(*) AS n FROM detections WHERE country IN (${fwIso})`);
        flywayDetections = Number(fwRows[0]?.n) || 0;
      }
      regionStats = {
        first: rows[0]?.first, total: Number(rows[0]?.total) || 0,
        speciesCount: Number(rows[0]?.species) || 0, flywayDetections,
      };
    } catch { regionStats = null; }
  }

  const _overlaySpecies = $derived.by(() => {
    try {
      // the overlay is fetched by the index build, but for the region panel
      // we read it from the species_index.json that's already loaded
      return null; // populated lazily below
    } catch { return null; }
  });

  function regionAtRisk(key) {
    // At-risk species: index records with conservation / vaccination-priority
    // enrichment whose countries intersect the region's ISO3 codes —
    // country-agnostic (any region's curated species match the same way)
    const r = regions?.regions?.[key];
    if (!r) return [];
    const results = [];
    if (window.__overlaySpecies) {
      for (const sp of window.__overlaySpecies) {
        if (!(sp.vaccination_target || sp.conservation)) continue;
        if (!sp.countries?.length) continue;
        if (r.iso3.some(iso => sp.countries.includes(iso))) results.push(sp);
      }
    }
    return results;
  }

  function openSpecies(sci, tab) {
    navigate('species-full', sci, tab ? { tab } : {});
  }

  const totalElements = $derived(
    model ? model.stages.reduce((n, s) => n + (s.elements || []).length, 0) : 0);
  const maxPeriodCount = $derived(periods.reduce((m, p) => Math.max(m, p.count), 1));

  // embedded mode: Model.svelte renders this in place of the deprecated
  // mermaid spread-overview — hides the page hero/back-link
  let { embedded = false } = $props();

  onDestroy(() => { clearInterval(playTimer); });
</script>

<svelte:head><title>{t('spread.page.title') || 'Spread model'} — Roost</title></svelte:head>

<div class="space-y-4">
  {#if !embedded}
  <!-- Mobile notice -->
  <div class="lg:hidden bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 text-sm text-amber-700 dark:text-amber-300">
    {t('spread.cyto.mobile_notice_a')} <a href="#/species" class="underline">{t('spread.cyto.mobile_species_explorer')}</a> {t('spread.cyto.mobile_or')} <a href="#/map" class="underline">{t('spread.cyto.mobile_map')}</a>.
  </div>
  <div class="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
        {t('spread.page.title2') || 'Spread Model'}
        <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-300 dark:border-amber-700">beta</span>
      </h1>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        {t('spread.cyto.intro') || 'How H5N1 moves through wild birds, poultry, and into mammals —'}
        {model ? `${model.stages.length} ` + (t('spread.stages') || 'stages') + ` · ${totalElements} ` + (t('spread.factors') || 'factors') + ` · ${matchCount} ` + (t('spread.linked') || 'linked to our species data') : (t('common.loading') || 'loading…')}
        {#if model}<span class="text-xs text-gray-500 dark:text-gray-400"> · v{model.version} · {model.updated}</span>{/if}
        <a href="#/spread-layers" class="text-blue-600 dark:text-blue-400 underline">{t('spread.layers.link') || 'Eras & host competence →'}</a>
      </p>
    </div>
    <a href="#/model" class="text-sm px-3 py-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">
      ← {t('spreadcyto.narrative.link')}
    </a>
  </div>
  {/if}

  {#if periods.length}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
      <div class="flex items-center gap-3 mb-2">
        <button
          class="w-9 h-9 rounded-lg bg-blue-600 text-white hover:bg-blue-700 flex items-center justify-center"
          onclick={togglePlay}
          title={playing ? (t('common.pause') || 'Pause') : (t('spread.play.panzootic') || 'Play the panzootic')}
        >{playing ? '⏸' : '▶'}</button>
        <div class="font-mono text-sm text-gray-900 dark:text-white min-w-[110px]">
          {periods[periodIdx].label}
        </div>
        <div class="text-xs text-gray-500 dark:text-gray-400">
          {fmtK(cumulativeAt(periodIdx))} {t('spreadcyto.timeline.cumulative')} · {fmtK(periods[periodIdx].count)} {t('spreadcyto.timeline.period')}
          {#if selectedEvent && selectedEvent.idx === periodIdx}
            <span class="ml-1 font-medium text-amber-700 dark:text-amber-400">★ {selectedEvent.label}</span>
          {/if}
        </div>
      </div>

      <!-- sparkline + slider + event flags -->
      <div class="relative" style="height: 64px;">
        <svg class="absolute inset-0 w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 40">
          {#each periods as pd, i}
            <rect x={(i / periods.length) * 100} y={40 - Math.max(1, (pd.count / maxPeriodCount) * 38)}
                  width={Math.max(0.15, 100 / periods.length - 0.1)} height={Math.max(1, (pd.count / maxPeriodCount) * 38)}
                  fill={i <= periodIdx ? '#3b82f6' : '#d1d5db'} opacity={i <= periodIdx ? 0.75 : 0.4} />
          {/each}
        </svg>
        {#each events as ev, ei}
          {#if ev.idx !== undefined}
            {@const stack = events.filter((o, oi) => oi < ei && o.idx === ev.idx).length}
            <button class="absolute text-sm leading-none select-none z-10"
                    style="left: {(ev.idx / periods.length) * 100}%; top: {-14 + stack * -13}px; transform: translateX(-50%);"
                    title="{ev.label} ({ev.date})"
                    onclick={() => { selectedEvent = ev; setPeriod(ev.idx, { fromUser: true }); }}
            >🚩</button>
          {/if}
        {/each}
        <input type="range" min="0" max={periods.length - 1} bind:value={periodIdx}
          aria-label={t("spread.timeline.scrub")}
               oninput={(e) => setPeriod(+e.target.value, { fromUser: true })}
               class="absolute inset-x-0 bottom-0 w-full accent-blue-600 cursor-pointer" />
      </div>

      {#if selectedEvent}
        <div class="mt-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3 flex items-start justify-between gap-3">
          <div>
            <span class="font-semibold text-amber-700 dark:text-amber-300 text-sm">{selectedEvent.label}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400 ml-1">· {selectedEvent.date} · stage: {selectedEvent.stage}</span>
            <p class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{selectedEvent.detail}</p>
            {#if selectedEvent.papers?.length}
              <div class="flex flex-wrap gap-1.5 mt-1.5">
                {#each selectedEvent.papers as pid}
                  <a href="#/papers/{pid}" class="text-xs px-2 py-0.5 rounded-full bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40">📄 {pid}</a>
                {/each}
              </div>
            {/if}
          </div>
          <button class="text-gray-500 dark:text-gray-400 hover:text-gray-600" onclick={() => selectedEvent = null}>✕</button>
        </div>
      {/if}
    </div>
  {/if}

  <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden" style="height: 68vh;">
    <div bind:this={container} class="w-full h-full"></div>
    {#if loading}
      <div class="absolute inset-0 bg-white/80 dark:bg-gray-800/80 flex items-center justify-center">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    {/if}

    <!-- Selected edge evidence panel (Phase 3) -->
    {#if selectedEdge}
      <div class="absolute bottom-3 left-3 right-3 md:right-auto md:max-w-md bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-semibold text-gray-900 dark:text-white text-sm">
            {selectedEdge.label} → {selectedEdge.to}
            {#if selectedEdge.contested}
              <span class="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-300 dark:border-amber-700">contested</span>
            {:else if selectedEdge.inferred}
              <span class="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600">inferred</span>
            {:else}
              <span class="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">{selectedEdge.count} papers</span>
            {/if}
          </h3>
          <button class="text-gray-500 dark:text-gray-400 hover:text-gray-600" onclick={() => { selectedEdge = null; cy?.edges()?.removeClass('evid-selected'); }}>✕</button>
        </div>
        {#if selectedEdge.note}
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{selectedEdge.note}</p>
        {/if}
        {#if Object.keys(selectedEdge.mechanisms).length}
          <div class="flex flex-wrap gap-1 mt-1.5">
            {#each Object.entries(selectedEdge.mechanisms).sort((a, b) => b[1] - a[1]) as [sec, n] (sec)}
              <span class="text-xs px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300" title={t('spreadcyto.edge.section.tip')}>{sec} <span class="font-semibold">{n}</span></span>
            {/each}
          </div>
        {/if}
        {#if selectedEdge.grounded}
          <p class="text-xs text-emerald-600 dark:text-emerald-400 mt-1">{t('spreadcyto.edge.grounded', { n: selectedEdge.grounded })}</p>
        {/if}
        {#if edgeParams?.summary?.n_params}
          <div class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
            <p class="text-xs font-semibold uppercase tracking-wide text-purple-600 dark:text-purple-400 mb-1">{t('spreadcyto.params.title')}</p>
            <ul class="space-y-0.5">
              {#each edgeParams.params.slice(0, 5) as p, i (p.paper_id + i)}
                <li class="text-xs text-gray-600 dark:text-gray-300">
                  <span class="font-mono font-semibold">{p.parameter}</span> = {p.value}{p.unit ? ` ${p.unit}` : ''}
                  <span class="text-gray-400"> — {(p.context || '').slice(0, 70)}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
        {#if selectedEdge.papers.length}
          <div class="flex flex-wrap gap-1 mt-2 max-h-24 overflow-y-auto">
            {#each selectedEdge.papers as pid}
              <a href="#/papers/{pid}" class="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 hover:bg-blue-100">📄 {pid}</a>
            {/each}
          </div>
        {:else}
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-2 italic">{t('spreadcyto.no.edge') || 'No corpus extraction maps to this edge yet — inferred from the model narrative ('}see weaknesses register W5).</p>
        {/if}

        {#if selectedEdge.mutations?.length}
          <div class="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
            <p class="text-xs font-semibold uppercase tracking-wide text-purple-600 dark:text-purple-400 mb-1.5">{t('routes.spreadcyto.adaptation.mutations.on.this') || 'Adaptation mutations on this pathway'}</p>
            <div class="space-y-1">
              {#each selectedEdge.mutations as m}
                <a href="#/mutations/{m.id}" class="block text-xs px-2 py-1.5 rounded bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/40">
                  <span class="font-mono font-semibold">{m.id}</span>
                  <span class="text-gray-500 dark:text-gray-400 ml-1.5">{m.role}</span>
                </a>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Selected node panel -->
    {#if selected}
      <div class="absolute bottom-3 left-3 right-3 md:right-auto md:max-w-md bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4">
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-semibold text-gray-900 dark:text-white">{selected.label}</h3>
          <button class="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" onclick={() => selectNode(null, true)}>✕</button>
        </div>
        {#if selected.note}
          <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">{selected.note}</p>
        {/if}
        {#if selected.chip}
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">{selected.chip}</p>
        {/if}
        {#if selected.susc}
          <span class="mt-1 inline-block px-2 py-0.5 text-xs rounded-full text-white"
                style="background: {SUSC_COLORS[selected.susc] || '#64748b'}">{selected.susc.replace('_', ' ')}</span>
        {/if}
        {#if selected.sci}
          <div class="flex flex-wrap gap-2 mt-2">
            <button
              class="text-sm px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700"
              onclick={() => openSpecies(selected.sci)}
            >Open {selected.sci} profile →</button>
            <button
              class="text-sm px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700"
              title={t('routes.spreadcyto.gene.presence.panel.does') || 'Gene presence panel — does this species have RIG-I, MDA5, ANP32A…?'}
              onclick={() => openSpecies(selected.sci, 'genes')}
            >{t('spread.cyto.gene_panel')}</button>
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <p class="text-xs text-gray-500 dark:text-gray-400">
    {t('spread.cyto.legend_nodes')} · {t('spread.cyto.node_size')}
    {#each Object.entries(SUSC_COLORS) as [cls, col]}
      <span class="inline-flex items-center gap-1 ml-2"><span class="w-2.5 h-2.5 rounded-sm" style="background:{col}"></span>{cls.replace('_', ' ')}</span>
    {/each}
    · {t('spread.cyto.legend_edges')} · {t('spread.cyto.built_from', {src: model?.source || 'the epi corpus'})}.
  </p>

  <!-- Region risk panel (Phase 5) -->
  {#if regions?.regions}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 class="text-sm font-semibold text-gray-900 dark:text-white">Regional risk assessment</h2>
        <div class="flex gap-1.5">
          {#each Object.entries(regions.regions) as [key, r]}
            <button
              class="px-2.5 py-1.5 text-xs rounded-lg font-medium transition-colors {activeRegion === key
                ? 'bg-rose-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
              onclick={() => activeRegion = activeRegion === key ? null : key}
            >{r.name}</button>
          {/each}
        </div>
      </div>

      {#if activeRegion && regions.regions[activeRegion]}
        {@const r = regions.regions[activeRegion]}
        {@const fw = flyways?.flyways?.[r.flyway]}
        <div class="grid md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-semibold text-gray-900 dark:text-white text-sm mb-1">
              {r.name}
              <span class="ml-2 px-2 py-0.5 text-xs rounded-full font-medium
                {r.status === 'established' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                : r.status === 'arrived' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'}">
                {r.status}
              </span>
            </h4>
            <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">{r.narrative}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">{r.risk_summary}</p>

            {#if regionStats}
              <div class="flex flex-wrap gap-2 mt-3 text-xs">
                <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  First detection: {regionStats.first ? String(regionStats.first).slice(0, 10) : 'none recorded'}
                </span>
                <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  {regionStats.total} detections · {regionStats.speciesCount} species
                </span>
                {#if fw}
                  <span class="px-2 py-0.5 rounded-full bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
                        title={`${fw.name}: ${t('spread.cyto.flyway_countries', {n: fw.countries.length})}`}>
                    {fw.name}: {fmtK(regionStats.flywayDetections)} detections
                  </span>
                {/if}
              </div>
            {:else}
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Computing…</p>
            {/if}
          </div>

          <div>
            <h4 class="font-semibold text-gray-900 dark:text-white text-sm mb-2">{t('routes.spreadcyto.at.risk.species.curated') || 'At-risk species (curated overlay)'}</h4>
            <div class="space-y-1.5 max-h-56 overflow-y-auto">
              {#if regionAtRisk(activeRegion).length}
                {#each regionAtRisk(activeRegion) as sp}
                  <a href="#/species-full/{encodeURIComponent(sp.sci)}" class="block text-xs px-2 py-1.5 rounded bg-gray-50 dark:bg-gray-700/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 border border-gray-200 dark:border-gray-600">
                    <span class="font-semibold text-gray-900 dark:text-white">{sp.com || sp.sci}</span>
                    {#if sp.conservation || sp.iucn}
                      <span class="ml-1 px-1 py-0.5 text-xs rounded {sp.conservation === 'critically_endangered' || sp.iucn === 'CR' ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-700 dark:text-amber-400'}">
                        {sp.conservation || sp.iucn}
                      </span>
                    {/if}
                    {#if sp.vaccination_target}
                      <span class="ml-1 px-1 py-0.5 text-xs rounded bg-emerald-100 text-emerald-700">💉 vaccination target</span>
                    {/if}
                    {#if sp.population}
                      <span class="text-gray-500 dark:text-gray-400 ml-1">pop: {sp.population}</span>
                    {/if}
                  </a>
                {/each}
              {:else}
                <p class="text-xs text-gray-500 dark:text-gray-400">{t('routes.spreadcyto.no.curated.at.risk') || 'No curated at-risk species for this region yet.'}</p>
              {/if}
            </div>
          </div>
        </div>

        {#if r.flyway_note}
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
            <strong>{fw?.name || r.flyway}:</strong> {r.flyway_note}
          </p>
        {/if}
      {:else}
        <p class="text-xs text-gray-500 dark:text-gray-400">{t('routes.spreadcyto.select.region.to.see') || 'Select a region to see its risk profile, at-risk species, and flyway exposure.'}</p>
      {/if}
    </div>
  {/if}

  {#if model?.diverges?.length}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <button class="flex items-center justify-between w-full text-left" onclick={() => showDiverges = !showDiverges}>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{t('spreadcyto.diverges.title', {n: model.diverges.length})}</h3>
        <span class="text-gray-500 dark:text-gray-400">{showDiverges ? '▲' : '▼'}</span>
      </button>
      {#if showDiverges}
        <div class="mt-3 space-y-3">
          {#each model.diverges as d}
            <div class="border-l-2 border-amber-400 pl-3">
              <div class="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide">{d.topic}</div>
              <p class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{d.statement}</p>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if model?.additions?.length}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <button class="flex items-center justify-between w-full text-left" onclick={() => showAdditions = !showAdditions}>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{t('spreadcyto.additions.title', {n: model.additions.length})}</h3>
        <span class="text-gray-500 dark:text-gray-400">{showAdditions ? '▲' : '▼'}</span>
      </button>
      {#if showAdditions}
        <div class="mt-3 space-y-3">
          {#each model.additions as a}
            <div class="border-l-2 border-emerald-400 pl-3">
              <div class="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">{a.stage} · {a.topic}</div>
              <p class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{a.statement}</p>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
