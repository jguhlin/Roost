<script>
  /**
   * ANP32 species-barrier comparison (FUTURE_TODO #9).
   *
   * The avian ANP32A 33-aa insert (partial exon-5 duplication between the
   * LRR and LCAR domains; Long et al. 2016, Nature) is what lets avian
   * ANP32A support the avian influenza polymerase — mammals lack it.
   * This view measures the insert across all 463 annotated birds (from
   * OrthoFinder OG MSAs) and every HPAI-confirmed mammal with a genome
   * (NCBI datasets protein FASTAs), against UniProt human references.
   */
  import { onMount } from 'svelte';
  import { navigate } from '../lib/stores/router.js';
  import MolecularViewer from '../lib/components/genes/MolecularViewer.svelte';
  import { formatNumber, getIUCNInfo } from '../lib/utils/format.js';
import { t } from '../lib/stores/i18n.svelte.js';

  let data = $state(null);
  let error = $state(null);
  let search = $state('');
  let groupFilter = $state('');        // '' | Aves | Mammalia
  let iucnMap = $state(null);

  const HUMAN_AF = 'https://alphafold.ebi.ac.uk/files/AF-P39687-F1-model_v6.cif';
  const HUMAN_JUNCTION = { start: 141, end: 157 };
  // zebra finch ANP32A (282 aa, insert included) — UniProt reference
  // proteome, same AlphaFold method as the human model
  const FINCH_AF = 'https://alphafold.ebi.ac.uk/files/AF-A0A674GQF9-F1-model_v6.cif';
  const FINCH_INSERT = { start: 139, end: 171 };   // from comparison.json payload

  onMount(async () => {
    try {
      const r = await fetch('data/anp32/comparison.json');
      if (!r.ok) throw new Error('payload missing');
      data = await r.json();
    } catch {
      error = 'ANP32 comparison data unavailable (regenerate with scripts/genes/export_anp32_comparison.py).';
    }
    try {
      const r = await fetch('data/species/iucn_status.json');
      if (r.ok) iucnMap = new Map(Object.entries((await r.json()).status || {}));
    } catch { /* badges optional */ }
  });

  const PAR_COLOR = { A: 'text-blue-600 dark:text-blue-400 dark:text-blue-400', B: 'text-teal-700 dark:text-teal-400', E: 'text-purple-600 dark:text-purple-400 dark:text-purple-400' };

  function chipClass(len) {
    if (len >= 25) return 'bg-red-600 text-white';          // full avian insert
    if (len >= 8) return 'bg-amber-700 text-white';         // partial / variant
    return 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'; // none
  }

  const rows = $derived.by(() => {
    if (!data?.species) return [];
    const q = search.trim().toLowerCase();
    let list = Object.entries(data.species)
      .map(([sci, v]) => ({ sci, ...v }));
    if (groupFilter) list = list.filter((r) => r.group === groupFilter);
    if (q.length >= 2) list = list.filter((r) =>
      r.sci.toLowerCase().includes(q) || (r.com || '').toLowerCase().includes(q));
    // threatened species with the full insert first among birds? keep it
    // simple: birds by insert length desc, then mammals
    list.sort((a, b) => (a.group === b.group
      ? (b.A?.insert_len || 0) - (a.A?.insert_len || 0)
      : a.group === 'Aves' ? -1 : 1));
    return list;
  });

  const TOTALS = $derived.by(() => {
    if (!data?.stats) return null;
    const s = data.stats.A;
    const avesWith = Object.entries(s.aves_hist)
      .filter(([len]) => Number(len) >= 25)
      .reduce((acc, [, n]) => acc + n, 0);
    const mamWith = Object.entries(s.mammal_hist)
      .filter(([len]) => Number(len) >= 25)
      .reduce((acc, [, n]) => acc + n, 0);
    return { avesWith, avesN: s.aves_n, mamWith, mamN: s.mammal_n };
  });

  // insert sequence strip: named species + human reference
  const STRIP = $derived.by(() => {
    if (!data?.species) return [];
    const wanted = ['Gallus gallus', 'Anas platyrhynchos', 'Meleagris gallopavo',
                    'Taeniopygia guttata', 'Haliaeetus albicilla', 'Oxyura jamaicensis'];
    const rows = wanted
      .filter((s) => data.species[s]?.A)
      .map((s) => ({ label: s, ins: data.species[s].A, group: 'Aves' }));
    rows.push({ label: 'Homo sapiens (reference)', ins: { insert_len: 0, insert_seq: '' }, group: 'Mammalia' });
    return rows;
  });

  const CHICKEN = $derived(data?.species?.['Gallus gallus']?.A || null);
  const sciShort = (s) => s.replace(/([A-Z])\w*\s/, '$1. ');
</script>

<svelte:head><title>{t('anp32.page.title') || 'ANP32 & the 33-aa insert'} — Roost</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-teal-500 bg-clip-text text-transparent">
    {t('anp32.title')}
  </h1>
  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 mb-6 max-w-3xl">
    {t('anp32.intro.a')} <strong>{t('anp32.insert_term')}</strong> {t('anp32.intro.b')}
    {TOTALS ? t('anp32.totals', {aw: formatNumber(TOTALS.avesWith), an: TOTALS.avesN, mw: TOTALS.mamWith, mn: TOTALS.mamN}) : '…'}.
  </p>

  {#if error}
    <div class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">{error}</div>
  {:else if !data}
    <div class="p-6 text-gray-500 dark:text-gray-400 animate-pulse">{t('anp32.loading')}</div>
  {:else}
    <!-- per-paralog summary -->
    <div class="grid gap-4 md:grid-cols-3 mb-6">
      {#each ['A', 'B', 'E'] as par (par)}
        {@const s = data.stats[par]}
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
          <h2 class="text-sm font-bold {PAR_COLOR[par]} mb-1">ANP32{par}</h2>
          <div class="text-[11px] text-gray-500 dark:text-gray-400 mb-2">
            {#if par === 'A'}{t('anp32.par.A')}
            {:else if par === 'B'}{t('anp32.par.B')}
            {:else}{t('anp32.par.E')}{/if}
          </div>
          <div class="flex items-end gap-1 h-20">
            {#each Object.entries({ ...(s.aves_hist || {}), ...(s.mammal_hist || {}) }) as [len, n] (len)}
              <div class="flex-1 flex flex-col items-center gap-0.5"
                   title={t('anp32.insert_tooltip', {len: len, n: n})}>
                <div class="w-full rounded-t {chipClass(Number(len))}"
                     style="height:{Math.min(64, 8 + Math.sqrt(n) * 9)}px"></div>
                <span class="text-[8px] text-gray-500 dark:text-gray-400">{len}</span>
              </div>
            {/each}
          </div>
          <p class="text-[10px] text-gray-500 dark:text-gray-400 mt-1">
            birds {t('anp32.count_n', {n: s.aves_n})} · mammals {t('anp32.count_n', {n: s.mammal_n})} · {t('anp32.bar_height')}
          </p>
        </div>
      {/each}
    </div>

    <!-- structures -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 mb-6">
      <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
        {t('anp32.structures') || 'Structures: the insert sits in the LCAR hinge'}
      </h2>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
        {t('anp32.same_method')}: <strong>{t('anp32.human')}</strong> {t('anp32.human_anp32')}
        <strong>{t('anp32.zebra_finch')}</strong> {t('anp32.finch_anp32')}
        <a class="text-blue-600 dark:text-blue-400 underline" target="_blank" rel="noopener"
           href="https://www.rcsb.org/structure/6XZR">6XZR on RCSB</a>.
        {#if CHICKEN?.insert_len}
          {t('anp32.chicken_residues', {a: CHICKEN.insert_start, b: CHICKEN.insert_start + CHICKEN.insert_len - 1})}
          (<span class="font-mono">{CHICKEN.insert_seq.slice(0, 18)}…</span>)
        {/if}
      </p>
      <div class="grid gap-4 lg:grid-cols-2">
        <MolecularViewer
          src={HUMAN_AF} format="cif" geneName={t('anp32.viewer.human')}
          height="360px" highlight={HUMAN_JUNCTION} highlightColor='0x2563eb' />
        <MolecularViewer
          src={FINCH_AF} format="cif" geneName={t('anp32.viewer.finch')}
          height="360px" highlight={FINCH_INSERT} highlightColor='0xdc2626' />
      </div>
    </div>

    <!-- insert sequence strip -->
    {#if STRIP.length}
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5 mb-6 overflow-x-auto">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          {t('anp32.insert_sequence')}
        </h2>
        <div class="space-y-1 font-mono text-[11px]">
          {#each STRIP as r (r.label)}
            <div class="flex items-center gap-3">
              <span class="w-48 shrink-0 text-right text-gray-500 dark:text-gray-400 truncate" title={r.label}>
                {sciShort(r.label)}
              </span>
              {#if r.ins.insert_len}
                <span class="tracking-wider whitespace-nowrap">
                  {#each r.ins.insert_seq.slice(0, 40) as aa, i (i)}
                    <span class="{aa === 'D' || aa === 'E' ? 'text-red-600' : 'text-gray-600 dark:text-gray-300'}">{aa}</span>
                  {/each}{#if r.ins.insert_len > 40}<span class="text-gray-500 dark:text-gray-400"> +{r.ins.insert_len - 40}</span>{/if}
                </span>
              {:else}
                <span class="text-gray-500 dark:text-gray-400">{t('anp32.none')}</span>
              {/if}
            </div>
          {/each}
        </div>
        <p class="mt-2 text-[10px] text-gray-500 dark:text-gray-400">
          {t('anp32.strip_legend.a')} (<i>Oxyura jamaicensis</i>) {t('anp32.strip_legend.b')}
        </p>
      </div>
    {/if}

    <!-- species table -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-5">
      <div class="flex flex-wrap items-center gap-3 mb-3">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{t('anp32.per_species')}</h2>
        <input
          type="text" value={search} placeholder={t('search.placeholder.species') || 'Search species…'}
          oninput={(e) => (search = e.target.value)}
          class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm w-56"
        />
        <div class="flex gap-1.5">
          {#each [['', t('anp32.group.all')], ['Aves', t('anp32.group.birds')], ['Mammalia', t('anp32.group.mammals')]] as [val, label]}
            <button
              class="px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors {groupFilter === val
                ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
              onclick={() => (groupFilter = val)}>{label}</button>
          {/each}
        </div>
        <span class="text-[11px] text-gray-500 dark:text-gray-400 ml-auto">{t('anp32.n_species', {n: rows.length})}</span>
      </div>
      <div class="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 bg-white dark:bg-gray-800">
            <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              <th class="py-2 pr-4 font-medium">{t('anp32.th.species')}</th>
              <th class="py-2 pr-3 font-medium">IUCN</th>
              <th class="py-2 pr-3 font-medium">{t('anp32.th.insert')}</th>
              <th class="py-2 pr-3 font-medium">len</th>
              <th class="py-2 pr-3 font-medium">ANP32B</th>
              <th class="py-2 pr-3 font-medium">ANP32E</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
            {#each rows.slice(0, 400) as r (r.sci)}
              <tr>
                <td class="py-1.5 pr-4 whitespace-nowrap">
                  <a class="hover:underline text-gray-800 dark:text-gray-200"
                     href="#/species-full/{encodeURIComponent(r.sci)}"><i>{sciShort(r.sci)}</i></a>
                  {#if r.com && r.com !== r.sci}<span class="text-[10px] text-gray-500 dark:text-gray-400 ml-1">{r.com}</span>{/if}
                  {#if r.group === 'Mammalia'}<span class="text-[9px] px-1 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 ml-1">{t('anp32.mammal')}</span>{/if}
                </td>
                <td class="py-1.5 pr-3">
                  {#if iucnMap?.get(r.sci)}
                    {@const info = getIUCNInfo(iucnMap.get(r.sci))}
                    <span class="px-1.5 py-0.5 text-[10px] font-bold rounded {info.bg} {info.text}"
                          title={info.name}>{iucnMap.get(r.sci)}</span>
                  {/if}
                </td>
                {#each ['A', 'B', 'E'] as par (par)}
                  {@const p = r[par]}
                  <td class="py-1.5 pr-3 whitespace-nowrap">
                    {#if par === 'A' && p}
                      <span class="px-2 py-0.5 text-[10px] font-bold rounded {chipClass(p.insert_len)}"
                            title="{p.insert_len} aa{p.insert_seq ? ` · ${p.insert_seq}` : ''}{p.frag ? t('anp32.fragment_paren') : ''}">
                        {p.insert_len || '—'}{#if p.frag}ᶠ{/if}
                      </span>
                    {:else if p}
                      <span class="text-xs text-gray-500 dark:text-gray-400"
                            title={t('anp32.aa_insert', {n: p.insert_len})}>{p.insert_len || '—'}</span>
                    {:else}
                      <span class="text-gray-500 dark:text-gray-400 text-xs">·</span>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if rows.length > 400}
        <p class="text-[11px] text-gray-500 dark:text-gray-400 mt-2">{t('anp32.showing_first', {n: 400, total: rows.length})}</p>
      {/if}
      <p class="mt-3 text-[11px] text-gray-500 dark:text-gray-400">
        {t('anp32.method_note')} <span class="font-semibold">ᶠ</span> =
        {t('anp32.annotation_fragment')} {t('anp32.mammals_note')}
        {t('anp32.generated', {date: data.meta?.generated?.slice(0, 10)})}.
      </p>
    </div>
  {/if}
</div>
