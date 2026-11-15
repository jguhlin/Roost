<script>
  /**
   * GenomeBrowser — igv.js embedded genome context for an evidence call.
   * Props: assembly (NCBI accession), contig, hsps (with genomic spans),
   * species name. Lazy-loads igv (~2 MB) and the genome FASTA via range
   * requests — only the viewed region is fetched.
   */
  import { onMount, onDestroy } from 'svelte';
import { t } from '../../stores/i18n.svelte.js';

  let { assembly = '', contig = '', hsps = [], exon_hsps = [], species = '' } = $props();

  let container;
  let browser = null;
  let error = $state(null);
  let loading = $state(true);
  let hasGff = $state(false);
  let distant = $state(0); // weak hits outside the framed locus

  onMount(async () => {
    try {
      // annotation overlay (if staged for this genome)
      try {
        const r = await fetch(`data/genomes/${assembly}/annotation.gff.bgz.tbi`, { method: 'HEAD' });
        hasGff = r.ok;
      } catch { hasGff = false; }

  const igv = (await import('igv')).default ?? await import('igv');

      const feats = hsps
        .filter(h => h.gstart !== undefined)
        .map(h => ({
          chr: h.contig || contig,
          start: h.gstart - 1,          // igv is 0-based
          end: h.gend,
          name: `${h.orf} · ${h.pident.toFixed(0)}%`,
          color: `hsl(${Math.max(0, Math.min(85, (h.pident - 25) * (85 / 75)))}, 72%, 45%)`,
          pident: h.pident,
          evalue: h.evalue
        }));

      const gs0 = Math.min(...feats.map(f => f.start));
      const ge0 = Math.max(...feats.map(f => f.end));

      // Frame the view on the cluster of strongest hits. A single weak
      // spurious HSP megabases away (repetitive/low-complexity regions)
      // would otherwise stretch the initial view to ~15 Mb and make the
      // real exons invisible — looking like a scattered non-match.
      const ev = f => (f.evalue ?? Infinity);
      const spans = [
        ...exon_hsps.filter(h => h.gstart !== undefined),
        ...hsps.filter(h => h.gstart !== undefined),
      ];
      const CLUSTER_WINDOW = 100_000;
      let locus = contig;
      if (spans.length) {
        const best = spans.reduce((a, b) => (ev(a) <= ev(b) ? a : b));
        const bestMid = (best.gstart + best.gend) / 2;
        const bestChr = best.contig || contig;
        const cluster = spans.filter(f =>
          (f.contig || contig) === bestChr &&
          Math.abs((f.gstart + f.gend) / 2 - bestMid) <= CLUSTER_WINDOW
        );
        distant = spans.length - cluster.length;
        const gs = Math.min(...cluster.map(f => f.gstart)) - 1;
        const ge = Math.max(...cluster.map(f => f.gend));
        const pad = Math.min(50_000, Math.max(3_000, (ge - gs) * 0.3));
        locus = `${bestChr}:${Math.max(1, gs - pad)}-${ge + pad}`;
      } else {
        const pad = Math.min(50_000, Math.max(3_000, (ge0 - gs0) * 0.3));
        locus = feats.length ? `${contig}:${Math.max(1, gs0 - pad)}-${ge0 + pad}` : contig;
      }

      const exFeats = exon_hsps.map(h => ({
        chr: h.contig || contig,
        start: h.gstart - 1,
        end: h.gend,
        name: `exon ${h.pident.toFixed(0)}%`,
        color: `hsl(${Math.max(0, Math.min(85, (h.pident - 25) * (85 / 75)))}, 72%, 55%)`,
        pident: h.pident
      }));

      const tracks = [
        {
          name: 'mRNA exon HSPs (nucleotide evidence)',
          type: 'annotation',
          format: 'bed',
          features: exFeats,
          displayMode: 'SQUISHED',
          height: 40,
          color: 'hsl(200, 60%, 50%)',
          clickable: true
        },
        {
          name: 'HSP alignments (protein identity)',
          type: 'annotation',
          format: 'bed',
          features: feats,
          displayMode: 'EXPANDED',
          height: 60,
          clickable: true
        }
      ];
      if (hasGff) {
        tracks.unshift({
          name: 'NCBI annotation (genes)',
          type: 'annotation',
          format: 'gff3',
          url: `data/genomes/${assembly}/annotation.gff.bgz`,
          indexURL: `data/genomes/${assembly}/annotation.gff.bgz.tbi`,
          displayMode: 'SQUISHED',
          height: 40
        });
      }

      // Reference sequence: prefer .2bit (4:1 compression, native random
      // access in igv), fall back to the plain FASTA. The content-type check
      // guards against hosts that answer missing files with a 200 SPA
      // fallback page (vite dev, Netlify rewrites…).
      const base = `data/genomes/${assembly}`;
      const headOk = async (url) => {
        try {
          const r = await fetch(url, { method: 'HEAD' });
          return r.ok && !(r.headers.get('content-type') || '').includes('text/html');
        } catch { return false; }
      };
      let reference;
      if (await headOk(`${base}/genome.2bit`)) {
        reference = { name: species, twoBitURL: `${base}/genome.2bit` };
      } else {
        reference = {
          name: species,
          fastaURL: `${base}/genome.fna`,
          indexURL: `${base}/genome.fna.fai`
        };
      }

      browser = await igv.createBrowser(container, {
        genomeName: species,
        showNavigation: true,
        showRuler: true,
        reference,
        locus,
        tracks
      });
    } catch (e) {
      error = e?.message?.slice(0, 200) || String(e);
    } finally {
      loading = false;
    }
  });

  onDestroy(() => {
    if (browser?.destroy) browser.destroy();
  });
</script>

<div class="mt-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
  {#if loading}
    <div class="p-4 text-xs text-gray-500 dark:text-gray-400">{t('genes.genomebrowser.loading.igv.genome.browser') || 'loading igv genome browser… (first load fetches the region only)'}</div>
  {/if}
  {#if error}
    <div class="p-3 text-xs text-red-600 dark:text-red-400">
      Genome browser failed: {error}
      <span class="text-gray-500 dark:text-gray-400">(genome {assembly} is not staged on this deployment — locally: run scripts/genes/genomes_to_2bit.sh; remotely: upload its genome.2bit)</span>
    </div>
  {/if}
  <div bind:this={container} class="igv-container"></div>
  {#if distant > 0}
    <div class="px-3 py-1.5 text-[11px] text-gray-500 dark:text-gray-400 border-t border-gray-100 dark:border-gray-700">
      {t('genome.view.framed') || 'View framed on the strongest matching locus'} — {distant} {distant !== 1 ? (t('genome.weaker.hits') || 'weaker hits') : (t('genome.weaker.hit') || 'weaker hit')} {t('genome.not.in.view') || 'more than 100 kb away not in view (scroll or search the contig to inspect).'}
    </div>
  {/if}
</div>

<style>
  /* igv.js requires an explicitly sized container or it renders nothing */
  .igv-container {
    width: 100%;
    height: 500px;
  }

  .igv-container :global(.igv-root-div) {
    background: transparent;
  }
</style>
