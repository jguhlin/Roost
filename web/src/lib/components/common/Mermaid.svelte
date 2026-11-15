<script>
  /**
   * Mermaid diagram renderer — re-renders when `source` changes.
   * Lazy-loads mermaid, theme-aware, handles prop updates.
   */
  import { onMount } from 'svelte';

  // module-level: mermaid.render is not safe for concurrent calls — serialize
  let renderChain = Promise.resolve();
  let instanceCounter = 0;

  let { source = '', id = '', config = null } = $props();
  let el = $state(null);
  let error = $state(null);
  let scrollable = $state(false);   // wrapper overflows horizontally
  let canLeft = $state(false);
  let canRight = $state(false);
  let mermaid = null;
  let baseConfig = null;   // initialized once; per-diagram config layered per render
  const instanceId = ++instanceCounter;
  let renderCount = $state(0);

  // Full base config as a factory (dark-aware) + a two-level deep merge
  // for per-diagram overrides.
  function makeBaseConfig(dark) {
    return {
      startOnLoad: false,
      theme: 'base',
      // native SVG labels: mermaid's HTML-in-foreignObject labels have
      // documented rendering failures (esp. Firefox)
      htmlLabels: false,
      fontFamily: 'Arial, sans-serif',
      flowchart: {
        htmlLabels: false,
        useMaxWidth: false,
        useMaxHeight: false,
        nodeSpacing: 20,
        rankSpacing: 25,
        diagramPadding: 8,
        padding: 8,
        curve: 'linear'
      },
      sequence: { useMaxWidth: false },
      themeVariables: dark ? {
        background: '#111827',
        primaryColor: '#1f2937',
        primaryTextColor: '#f9fafb',
        primaryBorderColor: '#4b5563',
        lineColor: '#6b7280',
        secondaryColor: '#374151',
        tertiaryColor: '#1f2937',
        fontSize: '16px'
      } : {
        background: '#ffffff',
        primaryColor: '#eff6ff',
        primaryTextColor: '#111827',
        primaryBorderColor: '#93c5fd',
        lineColor: '#6b7280',
        secondaryColor: '#f0fdf4',
        tertiaryColor: '#fefce8',
        fontSize: '16px'
      }
    };
  }

  function deepMerge(target, extra) {
    for (const [k, v] of Object.entries(extra)) {
      if (v && typeof v === 'object' && !Array.isArray(v) && target[k] && typeof target[k] === 'object') {
        deepMerge(target[k], v);
      } else {
        target[k] = v;
      }
    }
    return target;
  }

  async function ensureMermaid() {
    if (!mermaid) {
      mermaid = (await import('mermaid')).default;
      const dark = document.documentElement.classList.contains('dark');
      baseConfig = makeBaseConfig(dark);
      mermaid.initialize(baseConfig);
    }
    // per-diagram overrides (e.g. taller ladder spacing): deep-merge over
    // the full base config and re-initialize (renderChain serializes
    // renders, so per-diagram config is race-free)
    if (config && baseConfig) {
      mermaid.initialize(deepMerge(JSON.parse(JSON.stringify(baseConfig)), config));
    } else if (baseConfig) {
      mermaid.initialize(baseConfig);
    }
    return mermaid;
  }

  async function render() {
    error = null;
    if (!source) return;
    // queue this render after any in-flight one (mermaid concurrency bug workaround)
    renderChain = renderChain.then(async () => {
      try {
        const m = await ensureMermaid();
        const renderId = `${id || 'mmd'}-${instanceId}-${renderCount}`;
        const { svg } = await m.render(renderId, source);
        if (el) {
          el.innerHTML = svg;
          renderCount++;
          await sizeMermaid(el);
          updateScrollState();
        }
      } catch (e) {
        error = e.message?.slice(0, 200) || 'diagram failed';
      }
    });
  }

  /** Size from the ACTUAL drawing bounds (getBBox), not mermaid's reported
   *  viewBox — with native SVG labels the drawing can extend past the
   *  reported box, clipping text (user report 2026-11: ladder cut mid-text).
   *  Fonts settle first so text metrics are final. */
  async function sizeMermaid(container) {
    await document.fonts.ready;
    await new Promise(requestAnimationFrame);
    const svgEl = container.querySelector('svg');
    if (!svgEl) return;
    const bounds = svgEl.getBBox();
    if (![bounds.x, bounds.y, bounds.width, bounds.height].every(Number.isFinite)
        || bounds.width <= 0 || bounds.height <= 0) {
      throw new Error('Invalid Mermaid drawing bounds');
    }
    const padding = 20;
    const x = Math.floor(bounds.x) - padding;
    const y = Math.floor(bounds.y) - padding;
    const width = Math.ceil(bounds.x + bounds.width) + padding - x;
    const height = Math.ceil(bounds.y + bounds.height) + padding - y;
    svgEl.setAttribute('viewBox', `${x} ${y} ${width} ${height}`);
    svgEl.setAttribute('width', String(width));
    svgEl.setAttribute('height', String(height));
    svgEl.style.width = `${width}px`;
    svgEl.style.height = `${height}px`;
    svgEl.style.maxWidth = 'none';
    svgEl.style.display = 'block';
  }

  function updateScrollState() {
    if (!el) return;
    scrollable = el.scrollWidth > el.clientWidth + 4;
    canLeft = el.scrollLeft > 4;
    canRight = el.scrollLeft < el.scrollWidth - el.clientWidth - 4;
  }

  function scrollByPage(dir) {
    el?.scrollBy({ left: dir * Math.max(200, el.clientWidth * 0.8), behavior: 'smooth' });
  }

  // Re-render whenever source changes
  $effect(() => {
    source; // reactive dependency
    if (source) render();
  });

  onMount(() => {
    if (source) render();
  });
</script>

{#if error}
  <pre class="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-lg overflow-x-auto">{error}\n\n{source}</pre>
{:else}
  <div class="relative group">
    <div class="mermaid-wrap overflow-x-auto" bind:this={el} role="region" tabindex="0" aria-label={id ? `diagram: ${id} — scrollable` : 'diagram — scrollable'}
      onscroll={() => updateScrollState()}
    ></div>
    {#if scrollable}
      <button class="mermaid-nav absolute left-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full bg-white/95 dark:bg-gray-800/95 border border-gray-300 dark:border-gray-600 shadow flex items-center justify-center text-gray-700 dark:text-gray-200 hover:bg-white dark:hover:bg-gray-700 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
              aria-label="scroll diagram left" onclick={() => scrollByPage(-1)}
              style="display:{canLeft ? 'flex' : 'none'}">◀</button>
      <button class="mermaid-nav absolute right-1 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full bg-white/95 dark:bg-gray-800/95 border border-gray-300 dark:border-gray-600 shadow flex items-center justify-center text-gray-700 dark:text-gray-200 hover:bg-white dark:hover:bg-gray-700 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
              aria-label="scroll diagram right" onclick={() => scrollByPage(1)}
              style="display:{canRight ? 'flex' : 'none'}">▶</button>
    {/if}
  </div>
{/if}

<style>
  .mermaid-wrap {
    display: block;
    width: 100%;
    min-width: 0;
    height: auto;
    max-height: none;
    overflow: auto;   /* the ONE scroll container per diagram */
  }

  .mermaid-wrap :global(svg) {
    display: block;
    min-width: 0;
    max-width: none;
    max-height: none;
    flex-shrink: 0;
  }
</style>
