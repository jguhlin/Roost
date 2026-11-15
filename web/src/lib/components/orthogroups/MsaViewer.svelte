<script module>
  /**
   * Minimal canvas MSA viewer for orthogroup alignments.
   *
   * Fetches data/orthogroups/{og}.fa.zst, decompresses in-browser with fzstd,
   * renders a CLUSTAL-coloured alignment on canvas with horizontal
   * virtualisation (only visible columns are drawn), drag-to-scroll and
   * hover tooltips. No external viewer dependency.
   */
</script>

<script>
  import { onMount } from 'svelte';
  import { decompress } from 'fzstd';
  import { t } from '../../../lib/stores/i18n.svelte.js';

  let { og, leafMeta = {} } = $props();

  let canvas = $state(null);
  let wrap;
  let loading = $state(false);
  let error = $state(null);
  let seqs = $state(null);      // [{name, seq}]
  let colWidth = $state(14);    // px per column
  let scrollX = $state(0);
  let hover = $state(null);     // {seqIdx, col, x, y}
  let consensus = $state(null); // per-column dominant residue
  let rulerCanvas = $state(null);

  const ROW_H = 16;
  const LABEL_W = 210;

  // CLUSTAL-inspired palette (dark-mode friendly)
  const COLORS = {
    A: '#e05c5c', V: '#e05c5c', L: '#e05c5c', I: '#e05c5c', M: '#e05c5c', F: '#e05c5c', W: '#e05c5c', // hydrophobic
    K: '#6aa84f', R: '#6aa84f', H: '#6aa84f',                                                          // basic
    D: '#5c9de0', E: '#5c9de0',                                                                        // acidic
    S: '#c98ad9', T: '#c98ad9', N: '#c98ad9', Q: '#c98ad9', C: '#c98ad9', Y: '#c98ad9',               // polar
    G: '#d9a441', P: '#d9a441',
    X: '#8b8b8b', '*': '#8b8b8b', U: '#d9a441', 'B': '#8b8b8b', 'Z': '#8b8b8b',
  };

  async function load() {
    loading = true; error = null;
    try {
      const r = await fetch(`data/orthogroups/${og}.fa.zst`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const buf = new Uint8Array(await r.arrayBuffer());
      const text = new TextDecoder().decode(decompress(buf));
      const out = [];
      let cur = null;
      for (const line of text.split('\n')) {
        if (line.startsWith('>')) {
          cur = { name: line.slice(1).trim(), seq: '' };
          out.push(cur);
        } else if (cur) cur.seq += line.trim();
      }
      seqs = out;
      computeConsensus();
      draw();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function computeConsensus() {
    if (!seqs?.length) return;
    const n = seqs[0].seq.length;
    const cons = new Array(n);
    for (let c = 0; c < n; c++) {
      const counts = {};
      for (const s of seqs) {
        const ch = s.seq[c];
        if (ch && ch !== '-') counts[ch] = (counts[ch] || 0) + 1;
      }
      let best = '-', bn = 0;
      for (const [k, v] of Object.entries(counts)) if (v > bn) { best = k; bn = v; }
      cons[c] = { res: best, frac: seqs.length ? bn / seqs.length : 0 };
    }
    consensus = cons;
  }

  function shortLabel(name) {
    // "Acridotheres_tristis__GCA_027559615_1_KAM7023517.1" -> "A. tristis KAM7023517"
    const m = name.match(/^([A-Za-z]+)_([a-z]+)__\S+_([A-Za-z0-9_.]+)$/);
    if (m) return `${m[1][0]}. ${m[2]} ${m[3]}`;
    return name.slice(0, 28);
  }

  function draw() {
    if (!canvas || !seqs) return;
    const dpr = window.devicePixelRatio || 1;
    const W = wrap.clientWidth;
    const H = seqs.length * ROW_H + 4;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.height = `${H}px`;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    const font = '11px ui-monospace, SFMono-Regular, Menlo, monospace';
    ctx.font = font;

    for (let i = 0; i < seqs.length; i++) {
      const y = i * ROW_H;
      // label
      ctx.fillStyle = 'rgba(148, 163, 184, 0.9)';
      ctx.textBaseline = 'middle';
      const label = shortLabel(seqs[i].name);
      ctx.fillText(label, 4, y + ROW_H / 2, LABEL_W - 8);
      // residues in visible window
      const startCol = Math.max(0, Math.floor((scrollX) / colWidth));
      const endCol = Math.min(seqs[i].seq.length, Math.ceil((scrollX + W - LABEL_W) / colWidth));
      for (let c = startCol; c < endCol; c++) {
        const ch = seqs[i].seq[c];
        const x = LABEL_W + c * colWidth - scrollX;
        if (x < LABEL_W - colWidth || x > W) continue;
        if (ch === '-') {
          ctx.fillStyle = 'rgba(100, 116, 139, 0.25)';
          ctx.fillRect(x, y + 3, Math.max(1, colWidth - 1), ROW_H - 6);
        } else if (colWidth >= 9) {
          ctx.fillStyle = COLORS[ch.toUpperCase()] || '#a8a29e';
          ctx.fillText(ch, x + colWidth / 2 - 3, y + ROW_H / 2);
        } else {
          ctx.fillStyle = COLORS[ch.toUpperCase()] || '#a8a29e';
          ctx.fillRect(x, y + 2, Math.max(1, colWidth - 0.5), ROW_H - 4);
        }
      }
    }
    drawRuler();
  }

  function drawRuler() {
    if (!rulerCanvas || !seqs) return;
    const dpr = window.devicePixelRatio || 1;
    const W = wrap.clientWidth;
    const H = 20;
    rulerCanvas.width = W * dpr; rulerCanvas.height = H * dpr;
    const ctx = rulerCanvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.font = '10px ui-monospace, monospace';
    ctx.fillStyle = 'rgba(148,163,184,0.8)';
    ctx.textBaseline = 'top';
    const nCols = seqs[0]?.seq.length || 0;
    const step = colWidth >= 18 ? 10 : colWidth >= 9 ? 50 : 200;
    const startCol = Math.max(0, Math.floor(scrollX / colWidth));
    const endCol = Math.min(nCols, Math.ceil((scrollX + W - LABEL_W) / colWidth) + 1);
    for (let c = 0; c < nCols; c += step) {
      if (c < startCol - step || c > endCol) continue;
      const x = LABEL_W + c * colWidth - scrollX;
      if (x < LABEL_W || x > W - 20) continue;
      ctx.fillText(String(c + 1), x, 2);
      ctx.fillStyle = 'rgba(148,163,184,0.35)';
      ctx.fillRect(x, 14, 1, 6);
      ctx.fillStyle = 'rgba(148,163,184,0.8)';
    }
  }

  function seqIndexAt(my) {
    return Math.max(0, Math.min(seqs.length - 1, Math.floor(my / ROW_H)));
  }

  function handleMove(e) {
    if (!seqs) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const i = seqIndexAt(my);
    const col = Math.floor((mx - LABEL_W + scrollX) / colWidth);
    const seq = seqs[i]?.seq || '';
    hover = (mx > LABEL_W && col >= 0 && col < seq.length)
      ? { i, col, x: e.clientX, y: e.clientY, res: seq[col], name: seqs[i].name }
      : null;
  }

  let dragging = false, lastX = 0;
  function handleDown(e) { dragging = true; lastX = e.clientX; }
  function handleUp() { dragging = false; }
  function handleDrag(e) {
    if (!dragging) return;
    const dx = e.clientX - lastX;
    lastX = e.clientX;
    scrollX = Math.max(0, scrollX - dx);
    draw();
  }
  function handleWheel(e) {
    if (e.ctrlKey) { // zoom
      e.preventDefault();
      const old = colWidth;
      colWidth = Math.max(3, Math.min(24, colWidth + (e.deltaY < 0 ? 2 : -2)));
      scrollX = Math.max(0, scrollX * colWidth / old);
      draw();
    }
  }

  $effect(() => { if (seqs && canvas) draw(); });

  onMount(() => {
    load();
  });

  // observe the outer card (always mounted) so the observer never gets a null
  // element while the alignment body is still hidden behind the loading state
  $effect(() => {
    if (!wrap || !seqs) return;
    const ro = new ResizeObserver(() => draw());
    ro.observe(wrap);
    return () => ro.disconnect();
  });
</script>

<div bind:this={wrap} class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
  <div class="flex items-center gap-2 px-3 py-1.5 border-b border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
    <span>{seqs?.length ?? 0} sequences · {seqs?.[0]?.seq.length ?? 0} columns</span>
    <span class="ml-auto flex items-center gap-1">
      <button class="px-2 py-0.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
        onclick={() => { colWidth = Math.max(3, colWidth - 2); draw(); }}>−</button>
      <span>zoom</span>
      <button class="px-2 py-0.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
        onclick={() => { colWidth = Math.min(24, colWidth + 2); draw(); }}>+</button>
      <span>· drag to scroll{hover ? ` · ${hover.col + 1}: ${hover.res}` : ''}</span>
    </span>
  </div>

  {#if error}
    <div class="p-4 text-sm text-red-600 dark:text-red-400">Failed to load alignment: {error}</div>
  {:else if !seqs}
    <div class="p-4 text-sm text-gray-500 dark:text-gray-400">{loading ? (t('msa.loading') || 'Loading alignment…') : ''}</div>
  {:else}
    <div class="overflow-hidden">
      <canvas bind:this={rulerCanvas} class="w-full block" style="height:20px"></canvas>
      <canvas bind:this={canvas} class="w-full block cursor-grab active:cursor-grabbing"
        style="touch-action: pan-y"
        onmousemove={handleMove}
        onmouseleave={() => { hover = null; handleUp(); }}
        onmousedown={handleDown}
        onmouseup={handleUp}
        onwheel={handleWheel}></canvas>
    </div>
    {#if hover}
      <div class="fixed z-50 px-2 py-1 rounded bg-gray-900 text-gray-100 text-xs pointer-events-none shadow-lg"
        style="left:{hover.x + 12}px; top:{hover.y + 12}px;">
        <div class="font-mono">{hover.name.split('__').pop()}</div>
        <div>pos {hover.col + 1} · {hover.res}</div>
        <div class="text-gray-500 dark:text-gray-400">{leafMeta[hover.name]?.p || ''}</div>
      </div>
    {/if}
  {/if}
</div>
