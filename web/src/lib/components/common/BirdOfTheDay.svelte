<script>
  /**
   * BirdOfTheDay — homepage engagement card (2026-11).
   *
   * Deterministic pick from web/public/data/bird_of_the_day.json:
   *   candidates[floor(UTCms / 86400000) % candidates.length]
   * Same bird for every browser on the same day; cycles through all
   * sequenced+searched bird species and loops. The artifact regenerates on
   * every web export, so new genomes join the cycle (list-length changes
   * shift the day-to-day mapping — accepted).
   *
   * Birds only (builder filters via aves_taxonomy.tsv); every candidate
   * carries complete 18-gene core-panel calls (P/F/A).
   */
  import { onMount } from 'svelte';
  import { t, getLocale } from '../../stores/i18n.svelte.js';
  import { phylopicIndex, phylopicPath } from '../../utils/phylopic.js';

  /** @typedef {{s: string, n: string, c: string}} Gene */
  /** @typedef {{i: string, sci: string, nm: Record<string, string>, st: string, w?: {e: string, u: string} | null}} Candidate */
  /** @typedef {{generated?: string, genes: Gene[], candidates: Candidate[]}} BirdDoc */

  /** @type {BirdDoc | null} */
  let doc = $state(null);
  /** @type {Candidate | null} */
  let pick = $state(null);
  let failed = $state(false);
  /** @type {Record<string, {slug: string}> | null} */
  let silhouettes = $state(null);
  let dayLabel = $state('');

  const STATUS = /** @type {Record<string, {tile: string, dot: string, key: string}>} */ ({
    P: { tile: 'bg-emerald-500/90 text-white hover:bg-emerald-600', dot: 'bg-emerald-500', key: 'home.bird.present' },
    F: { tile: 'bg-amber-400/90 text-amber-950 hover:bg-amber-500', dot: 'bg-amber-400', key: 'home.bird.fragment' },
    A: { tile: 'bg-rose-500/90 text-white hover:bg-rose-600', dot: 'bg-rose-500', key: 'home.bird.absent' },
    '?': { tile: 'bg-gray-200 text-gray-400 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-500', dot: 'bg-gray-300', key: 'home.bird.nocall' },
  });

  /** @type {Array<{cat: string, genes: Array<Gene & {code: string}>}>} */
  const groups = $derived.by(() => {
    if (!doc || !pick) return [];
    /** @type {Map<string, Array<Gene & {code: string}>>} */
    const seen = new Map();
    const st = pick.st;
    doc.genes.forEach((g, i) => {
      const cat = g.c || 'Other';
      if (!seen.has(cat)) seen.set(cat, []);
      seen.get(cat)?.push({ ...g, code: st[i] ?? '?' });
    });
    return [...seen.entries()].map(([cat, genes]) => ({ cat, genes }));
  });

  /** @type {{[k: string]: number} | null} */
  const counts = $derived.by(() => {
    if (!pick) return null;
    const st = [...pick.st];
    return {
      P: st.filter((c) => c === 'P').length,
      F: st.filter((c) => c === 'F').length,
      A: st.filter((c) => c === 'A').length,
    };
  });

  const silhouette = $derived.by(() => {
    const p = pick;
    return p ? phylopicPath(p.sci, silhouettes) : null;
  });
  const speciesHref = $derived.by(() => {
    const p = pick;
    return p ? '#/species-full/' + encodeURIComponent(p.sci) : '';
  });

  // locale-first vernaculars: viewer's-locale name + English (deduped) —
  // an English page shows only English; a ja page shows アトリ · brambling
  const names = $derived.by(() => {
    const p = pick;
    if (!p) return [];
    const nm = p.nm || {};
    const loc = getLocale();
    /** @type {string[]} */
    const out = [];
    if (nm[loc]) out.push(nm[loc]);
    if (nm.en && nm.en !== out[0]) out.push(nm.en);
    return out.slice(0, 2);
  });

  /** LLM species summary from species_insights (lazy, per-day pick) */
  let summary = $state('');
  $effect(() => {
    const p = pick;
    summary = '';
    if (!p) return;
    (async () => {
      try {
        const r = await fetch(`data/species_insights/${p.i}.json`);
        if (!r.ok) return;
        const d = await r.json();
        summary = (d?.summary || '').trim();
      } catch { /* card works without the summary */ }
    })();
  });

  onMount(async () => {
    phylopicIndex().then((i) => (silhouettes = i));
    try {
      const r = await fetch('data/bird_of_the_day.json');
      if (!r.ok) throw new Error(String(r.status));
      const d = await r.json();
      doc = d;
      const dayIndex = Math.floor(Date.now() / 86400000);
      pick = d.candidates[dayIndex % d.candidates.length];
      dayLabel = new Date().toLocaleDateString(getLocale() || 'en', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
      });
    } catch {
      failed = true;
    }
  });
</script>

<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6" data-testid="bird-of-the-day">
  {#if pick && doc}
    <div class="flex items-center justify-between gap-3 mb-4 flex-wrap">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">
        🐦 {t('home.bird.title')}
      </h2>
      <div class="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
        <span>{dayLabel}</span>
        {#if pick?.w?.u}
          <a href={pick.w.u} target="_blank" rel="noopener noreferrer"
             class="text-blue-600 dark:text-blue-400 hover:underline">
            {t('home.bird.wikipedia')} ↗
          </a>
        {/if}
      </div>
    </div>

    <div class="flex items-center gap-4 mb-4 flex-wrap">
      {#if silhouette}
        <img src={silhouette} alt="" class="h-16 w-16 object-contain flex-shrink-0 dark:invert" />
      {/if}
      <div class="min-w-0">
        <a href={speciesHref} class="text-2xl font-bold italic text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 hover:underline">
          {pick.sci}
        </a>
        {#if names.length}
          <div class="text-sm text-gray-500 dark:text-gray-400">{names.join(' · ')}</div>
        {/if}
      </div>
    </div>

    {#if summary}
      <p class="text-sm text-gray-600 dark:text-gray-300 mb-4 leading-relaxed">{summary}</p>
    {:else if pick.w?.e}
      <p class="text-sm text-gray-600 dark:text-gray-300 mb-4 leading-relaxed">{pick.w.e}</p>
    {/if}

    <div class="mb-4">
      <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
        {t('home.bird.core.panel', { n: doc.genes.length })}
      </h3>
      <div class="flex flex-wrap gap-x-6 gap-y-3">
        {#each groups as { cat, genes } (cat)}
          <div>
            <div class="text-xs text-gray-400 dark:text-gray-500 mb-1">{t('home.bird.cat.' + cat.toLowerCase())}</div>
            <div class="flex flex-wrap gap-1.5">
              {#each genes as g (g.s)}
                {@const s = STATUS[g.code] ?? STATUS['?']}
                <a
                  href="#/gene/{g.s}"
                  aria-label="{g.s}: {t(s.key)}"
                  title="{g.n} — {t(s.key)}"
                  class="px-2 py-1 rounded-md text-xs font-mono font-semibold transition-colors {s.tile}"
                >{g.s}</a>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="flex items-center justify-between gap-3 flex-wrap border-t border-gray-100 dark:border-gray-700 pt-3">
      <div class="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-300 flex-wrap">
        {#if counts}
          {#each ['P', 'F', 'A'] as code (code)}
            <span class="flex items-center gap-1.5">
              <span class="w-2.5 h-2.5 rounded-full {STATUS[code].dot}" aria-hidden="true"></span>
              {counts[code]} {t(STATUS[code].key)}
            </span>
          {/each}
        {/if}
      </div>
      <div class="flex items-center gap-4 text-sm">
        <a href={speciesHref + '?tab=genes'} class="text-blue-600 dark:text-blue-400 hover:underline font-medium">
          {t('home.bird.view.species')} →
        </a>
      </div>
    </div>
  {:else if failed}
    <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">🐦 {t('home.bird.title')}</h2>
    <p class="text-sm text-gray-500 dark:text-gray-400">{t('common.load.error')}</p>
  {/if}
</div>
