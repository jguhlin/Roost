<script>
  /**
   * VaccineCyto (D125) — Cytoscape rendering of the vaccine pipeline:
   * 9 stage nodes chained platforms→…→escape, gene-bridge nodes attached
   * to their stages, node size scaled by verified-claim count, tier badge
   * colour (verified 🟢 / keyword 🟡). Tap a stage to open its card.
   * Data: h5n1_vaccine_model.json (same writer as the cards view).
   */
  import { onMount, onDestroy } from 'svelte';
  import { t } from '../../stores/i18n.svelte.js';

  let { model = null, onStage = null } = $props();

  let cy = null;
  let container = $state(null);
  let showLabels = $state(true);
  let showBridges = $state(true);

  const STAGE_ORDER = ['platforms', 'antigen', 'delivery', 'adjuvant',
                       'response', 'protection', 'diva', 'deployment', 'escape'];

  $effect(() => {
    if (model && container && !cy) {
      try { build(); }
      catch (e) { console.warn('[VaccineCyto] init failed (container likely detached) — will retry', e); cy = null; }
    }
  });

  onDestroy(() => { try { cy?.destroy(); } catch {} cy = null; });

  function build() {
    import('cytoscape').then(async (mod) => {
      const cytoscape = mod.default;
      try {
        const elk = (await import('cytoscape-elk')).default;
        cytoscape.use(elk);
      } catch { /* plain grid fallback */ }
      const stages = model.stages || [];
      const byId = Object.fromEntries(stages.map(s => [s.id, s]));

      const nodes = stages.map((s, i) => ({
        data: {
          id: s.id,
          kind: 'stage',
          label: `${i + 1} · ${s.short}`,
          claims: s.evidence?.claims || 0,
          papers: s.evidence?.candidate_papers || 0,
          tier: s.evidence?.tier || 'keyword',
          accent: s.accent || '#64748b',
        },
      }));
      const bridges = (model.gene_bridge || []).map((b, i) => ({
        data: {
          id: `bridge_${b.gene || b.symbol || i}`,
          kind: 'bridge',
          label: b.gene || b.symbol || '',
          stage: b.stage,
        },
      }));

      const chain = STAGE_ORDER.filter(id => byId[id]);
      const edges = [];
      for (let i = 0; i < chain.length - 1; i++) {
        edges.push({ data: { id: `e_${chain[i]}_${chain[i + 1]}`, source: chain[i], target: chain[i + 1], kind: 'chain' } });
      }
      // diva enables deployment; escape constrains antigen (curated, dashed)
      edges.push({ data: { id: 'e_diva_depl', source: 'diva', target: 'deployment', kind: 'curated', label: 'enables' } });
      edges.push({ data: { id: 'e_esc_ant', source: 'escape', target: 'antigen', kind: 'curated', label: 'constrains' } });
      for (const b of (model.gene_bridge || [])) {
        const bid = `bridge_${b.gene || b.symbol}`;
        if (b.stage && byId[b.stage]) {
          edges.push({ data: { id: `e_${bid}`, source: bid, target: b.stage, kind: 'bridge' } });
        }
      }

      cy = cytoscape({
        container,
        elements: [...nodes, ...bridges, ...edges],
        style: [
          { selector: 'node[kind = "stage"]', style: {
            'background-color': '#ffffff',
            'border-color': 'data(accent)', 'border-width': 3,
            'width': 'mapData(claims, 0, 120, 70, 150)',
            'height': 'mapData(claims, 0, 120, 70, 150)',
            'label': showLabels ? 'data(label)' : '',
            'color': '#1e293b', 'font-size': 11, 'font-weight': 600,
            'text-valign': 'center', 'text-halign': 'center',
            'text-wrap': 'wrap', 'text-max-width': 90,
          } },
          { selector: 'node[kind = "stage"][tier = "verified"]', style: { 'border-style': 'solid' } },
          { selector: 'node[kind = "stage"][tier = "keyword"]', style: { 'border-style': 'dashed' } },
          { selector: 'node[kind = "bridge"]', style: {
            'background-color': '#eef2ff', 'border-color': '#818cf8', 'border-width': 1,
            'width': 26, 'height': 26, 'shape': 'round-rectangle',
            'label': showLabels && showBridges ? 'data(label)' : '',
            'color': '#4338ca', 'font-size': 8,
            'text-valign': 'center', 'text-halign': 'center',
          } },
          { selector: 'edge[kind = "chain"]', style: {
            'width': 3, 'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8', 'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
          } },
          { selector: 'edge[kind = "curated"]', style: {
            'width': 2, 'line-color': '#a78bfa', 'line-style': 'dashed',
            'target-arrow-color': '#a78bfa', 'target-arrow-shape': 'triangle',
            'label': 'data(label)', 'color': '#7c3aed', 'font-size': 9,
            'curve-style': 'bezier',
          } },
          { selector: 'edge[kind = "bridge"]', style: {
            'width': 1, 'line-color': '#c7d2fe', 'line-style': 'dotted',
            'curve-style': 'bezier',
          } },
          { selector: 'node:selected', style: { 'border-width': 5 } },
        ],
        layout: { name: 'grid', rows: 3 }, // replaced below by elk when available
      });

      try {
        cy.layout({
          name: 'elk',
          elk: { algorithm: 'elk.layered', 'elk.direction': 'RIGHT',
                 'elk.spacing.nodeNode': 40, 'elk.layerSpacing': 90 },
        }).run();
      } catch { /* grid stays */ }

      cy.on('tap', 'node[kind = "stage"]', (evt) => {
        onStage?.(evt.target.id());
      });
      cy.on('tap', 'node[kind = "bridge"]', (evt) => {
        const label = evt.target.data('label');
        if (label) window.location.hash = `#/genes/${label}`;
      });
    });
  }

  function fit() { cy?.fit(undefined, 40); }

  $effect(() => {
    void showLabels; void showBridges;
    if (cy) {
      cy.nodes('[kind = "stage"]').style('label', showLabels ? 'data(label)' : '');
      cy.nodes('[kind = "bridge"]').style('label', (showLabels && showBridges) ? 'data(label)' : '');
      cy.edges('[kind = "bridge"]').style('display', showBridges ? 'element' : 'none');
    }
  });
</script>

<div class="rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
  <div class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-700">
    <div class="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
      {t('vaccines.cyto.legend')}
    </div>
    <div class="flex gap-1.5">
      <button class="px-2 py-1 text-xs rounded-lg border {showLabels ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600'}"
        onclick={() => showLabels = !showLabels}>{t('vaccines.cyto.labels')}</button>
      <button class="px-2 py-1 text-xs rounded-lg border {showBridges ? 'bg-blue-600 text-white border-blue-600' : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600'}"
        onclick={() => showBridges = !showBridges}>{t('vaccines.cyto.gene.bridges')}</button>
      <button class="px-2 py-1 text-xs rounded-lg border bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600"
        onclick={fit}>{t('vaccines.cyto.fit')}</button>
    </div>
  </div>
  <div bind:this={container} class="h-[64vh] min-h-[480px] w-full bg-slate-50 dark:bg-slate-900"></div>
</div>
