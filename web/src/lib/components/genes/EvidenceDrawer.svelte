<script>
  import { t } from '../../../lib/stores/i18n.svelte.js';
  /**
   * EvidenceDrawer — "judge it yourself" HSP viewer for a gene × species call.
   * Fetches /data/evidence/{gene}.json and renders the DIAMOND HSP cluster:
   * query track (reference protein) + subject track (genome ORFs), blocks
   * sized by coordinates, colored by identity. Shows the threshold math.
   */
  let { gene = '', species = '', call = null, level = '' } = $props();

  import { trackEvent } from '../../../lib/analytics.js';
  // analytics: evidence-drawer opens (the "judge it yourself" feature)
  $effect(() => { if (gene && species) trackEvent('Feature', 'evidence-drawer', gene, null); });

  import GenomeBrowser from './GenomeBrowser.svelte';

  let data = $state(null);
  let loading = $state(false);
  let showSeqs = $state(false);
  let showBrowser = $state(false);
  let showOthers = $state(false);
  let hasGenomic = $derived(data?.hsps?.some(h => h.gstart !== undefined) && data?.assembly);

  function formatFasta(seq, width = 60) {
    if (!seq) return '';
    const lines = [];
    for (let i = 0; i < seq.length; i += width) lines.push(seq.slice(i, i + width));
    return lines.join('\n');
  }

  let querySeq = $derived(cache[gene]?.query?.seq || '');
  let queryIdFull = $derived(cache[gene]?.query?.id || '');

  const cache = {};

  $effect(() => {
    const g = gene, sp = species;
    if (!g || !sp) return;
    loading = true;
    data = null;
    (async () => {
      if (!cache[g]) {
        try {
          const r = await fetch(`data/evidence/${encodeURIComponent(g)}.json`);
          cache[g] = r.ok ? await r.json() : null;
        } catch { cache[g] = null; }
      }
      data = cache[g]?.species?.[sp] || null;
      loading = false;
    })();
  });

  // SVG layout constants
  const W = 720, QY = 46, SY = 126, TRACK_H = 18;

  function heat(p) {
    // identity → hue: red(0) → green(85)
    const h = Math.max(0, Math.min(85, (p - 25) * (85 / 75)));
    return `hsl(${h}, 72%, 45%)`;
  }

  function fmtE(e) {
    if (e === 0) return '0';
    if (e < 1e-200) return e.toExponential(0);
    return e.toExponential(1);
  }

  let qlen = $derived(data?.qlen || data?.hsps?.[0] ? (data?.qlen || 1000) : 1000);
  let slen = $derived(data?.hsps?.length ? Math.max(...data.hsps.map(h => h.slen + (h.sstart || 0)), 100) : 100);

  function xq(pos) { return 40 + (pos / qlen) * (W - 60); }
  function xs(pos) { return 40 + (pos / slen) * (W - 60); }

  let connections = $derived.by(() => {
    if (!data?.hsps) return [];
    // group HSPs by ORF for the subject track layout
    const orfs = new Map();
    for (const h of data.hsps) {
      if (!orfs.has(h.orf)) orfs.set(h.orf, []);
      orfs.get(h.orf).push(h);
    }
    return orfs;
  });
</script>

<div class="border-l-2 border-blue-300 dark:border-blue-700 pl-4 py-2 my-1 text-sm">
  {#if loading}
    <p class="text-gray-500 dark:text-gray-400 py-2 text-xs">{t('evidence.loading.evidence')}</p>
  {:else if !data}
    <div class="py-2 space-y-1">
      <p class="text-gray-500 dark:text-gray-400 text-xs">{t('evidence.no.hsp.evidence.stored')}</p>
      {#if call}
        <p class="text-xs text-gray-600 dark:text-gray-400">
          {t('evidence.reference_only_note')}
          <span class="px-1.5 py-0.5 rounded font-mono text-[11px] font-semibold {call.status === 'FULL' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : call.status === 'FRAGMENT' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}">{call.status}</span>
          <span class="px-1.5 py-0.5 rounded text-[11px] bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 font-semibold">{level || call.level}</span>
          {#if call.method}<span class="text-gray-500 dark:text-gray-400">· {call.method}</span>{/if}
        </p>
      {/if}
    </div>
  {:else if data.no_hit}
    <div class="py-2">
      <p class="text-gray-500 dark:text-gray-400">∅ {data.note || 'No hit above threshold.'}</p>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        {t('genes.no_hit_scope')}
      </p>
    </div>
  {:else}
    <!-- Stats row -->
    <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs mb-2">
      <span class="font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700">{data.level?.split('_')[0] || data.status}</span>
      <span>contig <code class="text-[11px]">{data.contig}</code></span>
      <span>protein coverage <strong>{data.total_qcov}%</strong>{#if data.multi_exon} (stitched){/if}</span>
      {#if data.exon_count}
        <span class="text-blue-600 dark:text-blue-400">{t('genes.mrna_evidence')} <strong>{t('genes.n_exons', { n: data.exon_count })}</strong>, best e={fmtE(data.exon_best_e)}</span>
      {/if}
      <span>{data.hsps.length} {data.hsps.length > 1 ? (t('evidence.protein.hsps') || 'protein HSPs') : (t('evidence.protein.hsp') || 'protein HSP')}</span>
    </div>

    <!-- NCBI annotation overlap -->
    {#if data.annotation_hits?.length}
      <div class="mb-2 p-2 rounded bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 text-[11px] text-amber-800 dark:text-amber-300">
        <span class="font-semibold">{t('evidence.ncbi.annotation.at.this')}</span>
        {#each data.annotation_hits.slice(0, 2) as hit, i}
          <div class="mt-0.5">
            {#if i > 0}<span class="opacity-60">{t('genes.also_overlaps')} </span>{/if}
            <code class="font-mono">{hit.gene}</code>
            {#if hit.biotype}<span class="opacity-60"> · {hit.biotype}</span>{/if}
            {#each hit.transcripts.slice(0, 1) as tx}
              {#if tx.acc}<span class="opacity-60"> · {tx.acc}</span>{/if}
              {#if tx.product} “{tx.product}”{/if}
              {#if tx.cds_products?.length && tx.cds_products[0] !== tx.product}
                <span>— CDS product: <strong>{tx.cds_products[0]}</strong></span>
              {/if}
            {/each}
            <span class="opacity-60"> · {hit.overlap_bp.toLocaleString()} bp overlap</span>
          </div>
        {/each}
        {#if (data.level || '').includes('unannotated')}
          <p class="mt-1 opacity-80">
            {t('gene.overlap.note') || 'Recorded as “found outside the annotation”, but the match overlaps the annotated gene above — the hit is likely that gene (possibly under a different name; judge by the CDS product).'}
          </p>
        {/if}
      </div>
    {/if}

    {#if data.exon_count && data.total_qcov < 70}
      <div class="mb-2 p-2 rounded bg-blue-50 dark:bg-blue-900/20 text-[11px] text-blue-700 dark:text-blue-300">
        <strong>{t('evidence.read.the.coverage.numbers')}</strong> protein-ORF coverage understates multi-exon genes —
        6-frame ORFs cannot splice, so each exon becomes a separate small ORF. The nucleotide (mRNA) layer above
        shows {data.exon_count} aligned exons{#if data.exon_best_e < 1e-50} at very high significance (e &lt; 1e-50){/if}.
        Judge presence primarily by the exon evidence in the genome browser.
      </div>
    {/if}

    <!-- HSP map -->
    <svg viewBox="0 0 {W} 170" class="w-full max-w-3xl select-none" role="img" aria-label={t('genes.hsp_map_label')}>
      <!-- query track -->
      <text x="40" y="{QY - 8}" class="fill-gray-500 dark:fill-gray-400" font-size="11">{t('evidence.svg.query') || 'query · reference protein'} ({qlen} aa)</text>
      <rect x="40" y="{QY}" width="{W - 60}" height="{TRACK_H}" rx="3" class="fill-gray-200 dark:fill-gray-700" />
      {#each data.hsps as h}
        <rect x="{xq(h.qstart)}" y="{QY}" width="{Math.max(2, xq(h.qend) - xq(h.qstart))}"
              height="{TRACK_H}" fill={heat(h.pident)} opacity="0.9" rx="1">
          <title>HSP {h.orf}: query {h.qstart}-{h.qend} · {h.pident}% id · e={fmtE(h.evalue)}</title>
        </rect>
      {/each}

      <!-- connections + subject blocks -->
      <text x="40" y="{SY - 8}" class="fill-gray-500 dark:fill-gray-400" font-size="11">{t('evidence.svg.subject') || 'subject · genome ORFs on'} {data.contig}</text>
      <rect x="40" y="{SY}" width="{W - 60}" height="{TRACK_H}" rx="3" class="fill-gray-100 dark:fill-gray-800" />
      {#each data.hsps as h}
        <line x1="{xq(h.qstart)}" y1="{QY + TRACK_H}" x2="{xs(h.sstart)}" y2="{SY}" stroke={heat(h.pident)} stroke-width="1" opacity="0.45" />
        <rect x="{xs(h.sstart)}" y="{SY}" width="{Math.max(2, xs(h.send) - xs(h.sstart))}"
              height="{TRACK_H}" fill={heat(h.pident)} opacity="0.75" rx="1">
          <title>{h.orf}: ORF {h.sstart}-{h.send} of {h.slen} · {h.pident}% id · e={fmtE(h.evalue)}</title>
        </rect>
      {/each}

      <!-- scale hints -->
      <text x="40" y="{QY + TRACK_H + 14}" font-size="9" class="fill-gray-400">1</text>
      <text x="{W - 20}" y="{QY + TRACK_H + 14}" font-size="9" text-anchor="end" class="fill-gray-400">{qlen}</text>
      <text x="40" y="{SY + TRACK_H + 14}" font-size="9" class="fill-gray-400">0</text>
      <text x="{W - 20}" y="{SY + TRACK_H + 14}" font-size="9" text-anchor="end" class="fill-gray-400">{slen}</text>

      <!-- identity legend -->
      <text x="40" y="165" font-size="9" class="fill-gray-400">{t('lib_components_genes_EvidenceDrawer.identity')}</text>
      {#each [30, 50, 70, 90] as p, i}
        <rect x="{78 + i * 58}" y="158" width="12" height="8" fill={heat(p)} rx="1" />
        <text x="{93 + i * 58}" y="166" font-size="9" class="fill-gray-400">{p}%</text>
      {/each}
    </svg>

    <!-- HSP table -->
    <div class="overflow-x-auto mt-1">
      <table class="w-full text-[11px] text-gray-600 dark:text-gray-300">
        <thead>
          <tr class="text-left text-gray-500 dark:text-gray-400">
            <th class="py-1 pr-2">ORF</th>
            <th class="py-1 pr-2">query aa</th>
            <th class="py-1 pr-2">ORF aa</th>
            <th class="py-1 pr-2">%id</th>
            <th class="py-1 pr-2">{t('evidence.evalue')}</th>
            <th class="py-1">{t('evidence.qcov')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
          {#each data.hsps as h}
            <tr>
              <td class="py-1 pr-2 font-mono">{h.orf}</td>
              <td class="py-1 pr-2">{h.qstart}–{h.qend}</td>
              <td class="py-1 pr-2">{h.sstart}–{h.send}/{h.slen}</td>
              <td class="py-1 pr-2" style="color: {heat(h.pident)}">{h.pident.toFixed(1)}</td>
              <td class="py-1 pr-2">{fmtE(h.evalue)}</td>
              <td class="py-1">{h.qcov.toFixed(1)}%</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Verdict box -->
    <div class="mt-2 p-2 rounded bg-gray-50 dark:bg-gray-800/60 text-[11px] text-gray-500 dark:text-gray-400">
      <strong>{t('evidence.thresholds.applied')}</strong> blastn e≤1e-20, id≥80%, cov≥60% → FULL (20–60% → FRAGMENT) ·
      tblastn e≤1e-10, id≥40%, cov≥50% → FULL · D20 override: e&lt;1e-50 AND cov≥80% → FULL regardless of identity.
      Multi-exon genes: verdict uses summed non-overlapping HSP coverage (this cluster: <strong>{data.total_qcov}%</strong>;
      largest single HSP: <strong>{Math.max(...data.hsps.map(h => h.qcov)).toFixed(0)}%</strong>),
      best e <strong>{fmtE(Math.min(...data.hsps.map(h => h.evalue)))}</strong>.
      {#if data.multi_exon}HSPs stitched across ORFs on one contig — the per-HSP figure understates gene coverage for split genes.{/if}
    </div>

    <!-- Other-contig hits (all HSPs, not just the verdict cluster) -->
    {#if data.other_hits?.length}
      <div class="mt-2">
        <button
          class="text-xs text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
          onclick={() => showOthers = !showOthers}
        >
          {showOthers ? '▾' : '▸'} {data.other_hits.length} {data.other_hits.length > 1 ? (t('evidence.more.hits') || 'more hits') : (t('evidence.more.hit') || 'more hit')} {t('evidence.other.contigs') || 'on other contigs'}
          (not used for the verdict — possible paralogs, domain matches, or unrelated)
        </button>
        {#if showOthers}
          <div class="overflow-x-auto mt-1">
            <table class="w-full text-[11px] text-gray-500 dark:text-gray-400">
              <thead>
                <tr class="text-left text-gray-500 dark:text-gray-400">
                  <th class="py-1 pr-2">{t('lib_components_genes_EvidenceDrawer.contig_2')}</th>
                  <th class="py-1 pr-2">ORF</th>
                  <th class="py-1 pr-2">query aa</th>
                  <th class="py-1 pr-2">ORF aa</th>
                  <th class="py-1 pr-2">%id</th>
                  <th class="py-1 pr-2">{t('evidence.evalue')}</th>
                  <th class="py-1">{t('evidence.qcov')}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                {#each data.other_hits as h}
                  <tr title={h.orf}>
                    <td class="py-1 pr-2 font-mono text-[10px] max-w-[120px] truncate">{h.contig}</td>
                    <td class="py-1 pr-2 font-mono">{h.orf.split('_').pop()}</td>
                    <td class="py-1 pr-2">{h.qstart}–{h.qend}</td>
                    <td class="py-1 pr-2">{h.sstart}–{h.send}/{h.slen}</td>
                    <td class="py-1 pr-2" style="color: {heat(h.pident)}">{h.pident.toFixed(1)}</td>
                    <td class="py-1 pr-2">{fmtE(h.evalue)}</td>
                    <td class="py-1">{h.qcov.toFixed(1)}%</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Genome browser -->
    {#if hasGenomic}
      <button
        class="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
        onclick={() => showBrowser = !showBrowser}
      >
        {showBrowser ? '▾' : '▸'} 🧬 Genome context — open the actual locus in an igv.js browser
      </button>
      {#if showBrowser}
        <GenomeBrowser
          assembly={data.assembly}
          contig={data.contig}
          hsps={data.hsps}
          exon_hsps={data.exon_hsps || []}
          species={species}
        />
      {/if}
    {/if}

    <!-- Sequences -->
    <div class="mt-2">
      <button
        class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
        onclick={() => showSeqs = !showSeqs}
      >
        {showSeqs ? '▾' : '▸'} Sequences (query reference · translated ORF hits)
      </button>
      {#if showSeqs}
        <div class="mt-2 space-y-2">
          <div>
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase">query · reference protein ({data.qlen} aa)</span>
              <button
                class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                onclick={() => navigator.clipboard?.writeText(`>${queryIdFull || gene}_query\n${querySeq}`)}
              >{t('lib_components_genes_EvidenceDrawer.copy')}</button>
            </div>
            <pre class="mt-1 p-2 rounded bg-gray-900 text-green-300 text-[10px] leading-relaxed overflow-x-auto max-h-40 overflow-y-auto">{formatFasta(querySeq)}</pre>
          </div>
          {#each data.hsps as h}
            {#if h.sseq}
              <div>
                <div class="flex items-center justify-between">
                  <span class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase truncate">{h.orf} · translated ORF ({h.slen} aa, {h.pident.toFixed(0)}% id)</span>
                  <button
                    class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                    onclick={() => navigator.clipboard?.writeText(`>${h.orf}\n${h.sseq}`)}
                  >{t('evidence.copy')}</button>
                </div>
                <pre class="mt-1 p-2 rounded bg-gray-900 text-amber-200 text-[10px] leading-relaxed overflow-x-auto max-h-40 overflow-y-auto">{formatFasta(h.sseq)}</pre>
              </div>
            {/if}
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
