<script>
  import { t } from '../../../lib/stores/i18n.svelte.js';
  import { onMount, onDestroy } from 'svelte';

  let { pdbId = null, geneName = '', height = '400px',
       src = null, format = 'pdb', highlight = null,
       highlightColor = '0xFF4D4D' } = $props();
  // src: fetch structure text from an arbitrary URL (e.g. AlphaFold CIF);
  // highlight: { start, end, label } residue range emphasized with spheres

  let viewerContainer;
  let viewer = null;
  let mol3dLib = null;
  let loading = $state(true);
  let error = $state(null);
  let viewerReady = $state(false);

  // Load 3Dmol.js from CDN
  function load3Dmol() {
    return new Promise((resolve, reject) => {
      // Library attaches to window.$3Dmol
      if (window['$3Dmol']) {
        resolve(window['$3Dmol']);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://3dmol.org/build/3Dmol-min.js';
      script.onload = () => resolve(window['$3Dmol']);
      script.onerror = () => reject(new Error('Failed to load 3Dmol.js'));
      document.head.appendChild(script);
    });
  }

  async function initViewer() {
    if ((!pdbId && !src) || !viewerContainer) return;

    loading = true;
    error = null;

    try {
      mol3dLib = await load3Dmol();

      // Clear previous viewer
      if (viewer) {
        viewerContainer.innerHTML = '';
      }

      // Create viewer
      viewer = mol3dLib.createViewer(viewerContainer, {
        backgroundColor: 'white',
        antialias: true,
      });

      // Fetch structure: explicit src URL (e.g. AlphaFold mmCIF) or RCSB PDB
      let structureData, modelFormat = format;
      if (src) {
        const response = await fetch(src);
        if (!response.ok) throw new Error(`Failed to fetch structure`);
        structureData = await response.text();
        modelFormat = format;
      } else {
        const response = await fetch(`https://files.rcsb.org/download/${pdbId}.pdb`);
        if (!response.ok) {
          throw new Error(`Failed to fetch PDB ${pdbId}`);
        }
        structureData = await response.text();
        modelFormat = 'pdb';
      }

      // Add model and set style
      viewer.addModel(structureData, modelFormat);

      // Default cartoon style with chain coloring
      viewer.setStyle({}, { cartoon: { color: 'spectrum' } });

      // Highlight a residue range (e.g. the avian 33-aa insert) with spheres
      // on top of the cartoon, and zoom to it
      let zoomSel = undefined;
      if (highlight && highlight.start && highlight.end) {
        const sel = { resi: `${highlight.start}-${highlight.end}` };
        viewer.setStyle(sel, { sphere: { radius: 1.6, color: highlightColor } });
        zoomSel = sel;
      }

      // Zoom to fit (or to the highlight)
      viewer.zoomTo(zoomSel);
      viewer.render();

      viewerReady = true;
      loading = false;
    } catch (e) {
      error = e.message;
      loading = false;
    }
  }

  // Style presets
  function setCartoon() {
    if (!viewer) return;
    viewer.setStyle({}, { cartoon: { color: 'spectrum' } });
    viewer.render();
  }

  function setStick() {
    if (!viewer) return;
    viewer.setStyle({}, { stick: { colorscheme: 'Jmol' } });
    viewer.render();
  }

  function setSurface() {
    if (!viewer || !mol3dLib) return;
    viewer.setStyle({}, { cartoon: { color: 'spectrum' } });
    viewer.addSurface(mol3dLib.SurfaceType.VDW, { opacity: 0.7, color: 'white' });
    viewer.render();
  }

  function setBallAndStick() {
    if (!viewer) return;
    viewer.setStyle({}, {
      stick: { radius: 0.15, colorscheme: 'Jmol' },
      sphere: { radius: 0.3, colorscheme: 'Jmol' }
    });
    viewer.render();
  }

  function spin() {
    if (!viewer) return;
    viewer.spin('y', 1);
  }

  function stopSpin() {
    if (!viewer) return;
    viewer.spin(false);
  }

  function resetView() {
    if (!viewer) return;
    viewer.zoomTo();
    viewer.render();
  }

  onMount(() => {
    if (pdbId || src) {
      initViewer();
    }
  });

  onDestroy(() => {
    if (viewer) {
      viewer = null;
    }
  });

  // Watch for pdbId changes
  $effect(() => {
    if (pdbId && viewerContainer) {
      initViewer();
    }
  });
</script>

<div class="molecular-viewer">
  <div class="viewer-header">
    <div class="viewer-title">
      {#if pdbId}
        <span class="pdb-id">PDB: {pdbId}</span>
      {:else}
        <span class="pdb-id">{src?.includes('alphafold') ? 'AlphaFold' : 'Structure'}</span>
      {/if}
      {#if geneName}
        <span class="gene-name">({geneName})</span>
      {/if}
    </div>
    {#if pdbId}
      <a
        href="https://www.rcsb.org/structure/{pdbId}"
        target="_blank"
        rel="noopener noreferrer"
        class="rcsb-link"
      >
        {t('genes.view_on_rcsb')}
      </a>
    {:else if src?.includes('alphafold')}
      <a href="https://alphafold.ebi.ac.uk" target="_blank" rel="noopener noreferrer" class="rcsb-link">{t('molviewer.alphafold.db')}</a>
    {/if}
  </div>

  <div
    bind:this={viewerContainer}
    class="viewer-canvas"
    style="height: {height};"
  >
    {#if loading}
      <div class="loading-overlay">
        <div class="spinner"></div>
        <span>{t('molviewer.loading.structure')}</span>
      </div>
    {/if}
    {#if error}
      <div class="error-overlay">
        <span>Error: {error}</span>
      </div>
    {/if}
  </div>

  {#if viewerReady}
    <div class="viewer-controls">
      <div class="control-group">
        <span class="control-label">{t('lib_components_genes_MolecularViewer.style')}</span>
        <button onclick={setCartoon} class="control-btn">{t('lib_components_genes_MolecularViewer.cartoon')}</button>
        <button onclick={setStick} class="control-btn">{t('lib_components_genes_MolecularViewer.stick')}</button>
        <button onclick={setBallAndStick} class="control-btn">Ball & Stick</button>
        <button onclick={setSurface} class="control-btn">{t('lib_components_genes_MolecularViewer.surface')}</button>
      </div>
      <div class="control-group">
        <button onclick={spin} class="control-btn">{t('lib_components_genes_MolecularViewer.spin')}</button>
        <button onclick={stopSpin} class="control-btn">{t('lib_components_genes_MolecularViewer.stop')}</button>
        <button onclick={resetView} class="control-btn">{t('lib_components_genes_MolecularViewer.reset')}</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .molecular-viewer {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e5e7eb;
  }

  :global(.dark) .molecular-viewer {
    background: #1f2937;
    border-color: #374151;
  }

  .viewer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }

  :global(.dark) .viewer-header {
    background: #111827;
    border-color: #374151;
  }

  .viewer-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .pdb-id {
    font-family: monospace;
    font-weight: 600;
    color: #2563eb;
  }

  :global(.dark) .pdb-id {
    color: #60a5fa;
  }

  .gene-name {
    font-size: 0.875rem;
    color: #6b7280;
  }

  :global(.dark) .gene-name {
    color: #9ca3af;
  }

  .rcsb-link {
    font-size: 0.75rem;
    color: #2563eb;
    text-decoration: none;
  }

  .rcsb-link:hover {
    text-decoration: underline;
  }

  :global(.dark) .rcsb-link {
    color: #60a5fa;
  }

  .viewer-canvas {
    position: relative;
    width: 100%;
    min-height: 300px;
  }

  .loading-overlay,
  .error-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    background: rgba(255, 255, 255, 0.9);
    color: #374151;
  }

  :global(.dark) .loading-overlay,
  :global(.dark) .error-overlay {
    background: rgba(31, 41, 55, 0.9);
    color: #d1d5db;
  }

  .error-overlay {
    color: #dc2626;
  }

  :global(.dark) .error-overlay {
    color: #f87171;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid #e5e7eb;
    border-top-color: #2563eb;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .viewer-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 8px 12px;
    background: #f9fafb;
    border-top: 1px solid #e5e7eb;
  }

  :global(.dark) .viewer-controls {
    background: #111827;
    border-color: #374151;
  }

  .control-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .control-label {
    font-size: 0.75rem;
    color: #6b7280;
    margin-right: 4px;
  }

  :global(.dark) .control-label {
    color: #9ca3af;
  }

  .control-btn {
    padding: 4px 8px;
    font-size: 0.75rem;
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    color: #374151;
    cursor: pointer;
    transition: all 0.15s;
  }

  .control-btn:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
  }

  :global(.dark) .control-btn {
    background: #374151;
    border-color: #4b5563;
    color: #d1d5db;
  }

  :global(.dark) .control-btn:hover {
    background: #4b5563;
    border-color: #6b7280;
  }
</style>
