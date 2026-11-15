<script>
  /**
   * Gene-tree renderer for orthogroup trees (Newick with leaf keys
   * "Sci_name__ASM_acc"). Lazy-loads Phylocanvas GL from the same pinned
   * CDN bundle as the Phylogeny page; falls back to collapsed Newick text.
   */
  import { onMount } from 'svelte';
import { t } from '../../stores/i18n.svelte.js';

  let { newick, leafMeta = {} } = $props();

  let container;
  let loading = $state(true);
  let error = $state(null);

  const CDN = 'https://unpkg.com/@phylocanvas/phylocanvas.gl@1.64.1/dist/bundle.min.js';

  function shortLabel(name) {
    // underscore-safe for embedding back into Newick (no spaces in unquoted labels)
    const m = name.match(/^([A-Za-z]+_[a-z]+)__\S+_([A-Za-z0-9_.]+)$/);
    if (m) return `${m[1]}__${m[2]}`;
    return name.slice(0, 40);
  }

  function loadPhylocanvas() {
    return new Promise((resolve, reject) => {
      if (window.phylocanvas) return resolve(window.phylocanvas);
      const script = document.createElement('script');
      script.src = CDN;
      script.onload = () => resolve(window.phylocanvas);
      script.onerror = () => reject(new Error('CDN load failed'));
      document.head.appendChild(script);
    });
  }

  let tree = null;

  onMount(async () => {
    try {
      const PhylocanvasGL = await loadPhylocanvas();
      // shorten leaf labels inside the Newick string itself (leaves = tokens after '(' or ',')
      const src = newick.replace(/([(,]\s*)([^,():;]+?)(:)/g, (all, pre, label, post) =>
        pre + shortLabel(label.trim()) + post
      );
      const rect = container.getBoundingClientRect();
      tree = new PhylocanvasGL.default(container, {
        source: src,
        type: 'rc',
        interactive: true,
        padding: 24,
        showLabels: true,
        showLeafLabels: true,
        alignLabels: true,
        nodeSize: 4,
        lineWidth: 1.5,
        fontFamily: 'ui-monospace, monospace',
        fontSize: 8,
        highlightColour: '#2563eb',
        strokeColour: '#9ca3af',
        fillColour: '#d1d5db',
        size: {
          width: Math.max(320, rect.width || 900),
          height: Math.max(300, rect.height || 500),
        },
      });
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
    return () => { try { tree?.destroy?.(); } catch { /* noop */ } };
  });
</script>

<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
  {#if loading}
    <div class="p-4 text-sm text-gray-500 dark:text-gray-400">{t('app.loading.tree') || 'Loading tree…'}</div>
  {/if}
  {#if error}
    <div class="p-3 text-xs text-amber-700 dark:text-amber-400 border-b border-gray-200 dark:border-gray-700">
      Interactive tree unavailable ({error}) — showing source Newick.
    </div>
    <pre class="p-3 text-[10px] leading-tight overflow-x-auto max-h-96 text-gray-500 dark:text-gray-400 whitespace-pre-wrap break-all">{newick.slice(0, 5000)}{newick.length > 5000 ? ' …' : ''}</pre>
  {/if}
  <div bind:this={container} class="w-full" style="min-height:{Math.min(700, Math.max(300, (newick.match(/,/g) || []).length * 9 + 60))}px"></div>
</div>
