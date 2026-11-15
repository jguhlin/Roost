<script>
  import { onMount } from 'svelte';
import { t } from '../lib/stores/i18n.svelte.js';

  let data = $state(null);
  let error = $state(null);

  onMount(async () => {
    try {
      const r = await fetch('data/by_the_numbers.json');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      data = await r.json();
    } catch (e) {
      error = e.message;
    }
  });

  const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString('en-US'));
  const pct = (n) => `${Number(n).toFixed(1)}%`;

  let failed = $derived(data ? data.checks.filter((c) => c.status !== 'pass') : []);
  let dist = $derived(data ? data.landscape.distribution : {});
  let maxDist = $derived(Math.max(1, ...Object.values(dist)));
</script>

<svelte:head><title>{t('numbers.page.title') || 'By the numbers'} — Roost</title></svelte:head>

<div class="max-w-4xl mx-auto space-y-10">
  <header class="space-y-2">
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('numbers.title')}</h1>
    <p class="text-gray-600 dark:text-gray-400">
      {t('numbers.intro.a')}
      (<code class="[overflow-wrap:anywhere]">scripts/papers/build_by_the_numbers.py</code>). {t('numbers.intro.b')}
      {#if data}<span class="text-sm text-gray-500 dark:text-gray-400">{t('numbers.generated', {date: data.generated?.slice(0, 10)})}</span>{/if}
    </p>
  </header>

  {#if error}
    <div class="bg-red-100 border border-red-300 text-red-800 rounded p-4">
      {t('numbers.could_not_load')} <code>data/by_the_numbers.json</code>: {error}
    </div>
  {/if}

  {#if data}
    <!-- ============ deterministic checks ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.checks.title')}</h2>
      {#if failed.length === 0}
        <div class="bg-green-100 border border-green-300 text-green-800 rounded-lg p-4 font-medium">
          ✓ {t('numbers.checks.all_pass', {n: data.checks.length})}
        </div>
      {:else}
        <div class="bg-red-100 border border-red-400 text-red-800 rounded-lg p-4 font-medium">
          ⚠ {t('numbers.checks.n_failed', {f: failed.length, n: data.checks.length})}
          Triage: compare the sources listed on each failing row, rebuild the stale side,
          then rerun <code>build_by_the_numbers.py</code>.
        </div>
      {/if}
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table class="w-full text-sm text-gray-900 dark:text-gray-100">
          <thead class="bg-gray-50 dark:bg-gray-800 text-left">
            <tr>
              <th class="px-3 py-2">{t('numbers.checks.check')}</th>
              <th class="px-3 py-2">Left</th>
              <th class="px-3 py-2">{t('numbers.checks.right')}</th>
              <th class="px-3 py-2">{t('numbers.checks.sources')}</th>
              <th class="px-3 py-2">{t('numbers.checks.status')}</th>
            </tr>
          </thead>
          <tbody>
            {#each data.checks as c}
              <tr class="border-t border-gray-100 dark:border-gray-800 {c.status !== 'pass' ? 'bg-red-50 dark:bg-red-900/20' : ''}">
                <td class="px-3 py-2 font-medium dark:text-gray-200">{c.name}</td>
                <td class="px-3 py-2 dark:text-gray-300">{fmt(c.left)}</td>
                <td class="px-3 py-2 dark:text-gray-300">{fmt(c.right)}</td>
                <td class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">{c.left_source} vs {c.right_source}</td>
                <td class="px-3 py-2 font-mono {c.status === 'pass' ? 'text-green-700 dark:text-green-400' : 'text-red-600 font-bold'}">{c.status === 'pass' ? '✓ pass' : '✗ FAIL'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <!-- ============ spread model v2 ============ -->
    {#if data.spread_model && !data.spread_model.error}
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.spread.title')}</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="text-3xl font-bold text-gray-900 dark:text-white">{fmt(data.spread_model.extracted_items)}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">extracted items ({data.spread_model.grounded_pct}% quote-grounded)</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="text-3xl font-bold text-gray-900 dark:text-white">{fmt(data.spread_model.edge_paper_links)}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">edge paper-links across {data.spread_model.edges} edges · {data.spread_model.eras} eras</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="text-3xl font-bold text-gray-900 dark:text-white">{fmt(data.spread_model.faithful)}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">verified faithful ({fmt(data.spread_model.unsupported)} unsupported)</div>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="text-3xl font-bold text-gray-900 dark:text-white">{fmt(data.spread_model.susceptibility_species)}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">species scored · {fmt(data.spread_model.region_countries)} countries at risk</div>
        </div>
      </div>
    </section>
    {/if}

    <!-- ============ corpus ============ -->
    <section class="grid grid-cols-2 md:grid-cols-4 gap-4">
      {#each [
        ['Papers in corpus', data.corpus.papers],
        ['Data sources', data.corpus.sources],
        ['Detection records', data.corpus.detections],
        ['Countries', data.corpus.countries]
      ] as [label, value]}
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="text-2xl font-bold dark:text-white">{fmt(value)}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">{label}</div>
        </div>
      {/each}
    </section>

    <!-- ============ species ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.species_hosts.title')}</h2>
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"><table class="w-full text-sm text-gray-900 dark:text-gray-100 border rounded-lg dark:border-gray-700">
        <tbody>
          {#each [
            ['Detected species', fmt(data.species.detected)],
            ['— birds', fmt(data.species.birds)],
            ['— mammal spillover hosts', fmt(data.species.mammals)],
            ['Searchable (incl. overlay-only)', fmt(data.species.searchable)],
            ['With IUCN status', fmt(data.species.iucn_statused)]
          ] as [label, value]}
            <tr class="border-b last:border-0 dark:border-gray-800">
              <td class="px-3 py-1.5 text-gray-600 dark:text-gray-400">{t('numbers.' + label.toLowerCase().replace(/[^a-z0-9]+/g, '.')) || label}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{value}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      </div>
    </section>

    <!-- ============ gene registry ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.registry.title')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('numbers.registry.intro.a')} <em>{t('numbers.registry.studied')}</em> {t('numbers.registry.intro.b')}
      </p>
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"><table class="w-full text-sm text-gray-900 dark:text-gray-100 border rounded-lg dark:border-gray-700">
        <tbody>
          {#each Object.entries({
            'Host genes tracked (total)': data.gene_registry.host_total,
            '— studied (≥1 study-subject paper)': data.gene_registry.buckets.studied,
            '— claims/discovery-linked only': data.gene_registry.buckets.claims_discovery_linked_only,
            '— panel-only (no literature yet)': data.gene_registry.buckets.panel_only_no_literature,
            '— text-only mentions': data.gene_registry.buckets.text_only_mentions
          }) as [label, value]}
            <tr class="border-b last:border-0 dark:border-gray-800">
              <td class="px-3 py-1.5 text-gray-600 dark:text-gray-400">{t('numbers.' + label.toLowerCase().replace(/[^a-z0-9]+/g, '.')) || label}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(value)}</td>
            </tr>
          {/each}
          <tr class="border-t dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
            <td class="px-3 py-1.5 text-gray-500 dark:text-gray-400">Non-host kinds: {Object.entries(data.gene_registry.non_host_kinds).map(([k, v]) => `${k} ${v}`).join(' · ')}</td>
            <td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(Object.values(data.gene_registry.non_host_kinds).reduce((a, b) => a + b, 0))}</td>
          </tr>
        </tbody>
      </table>
      </div>
    </section>

    <!-- ============ landscape ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.landscape.title')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('numbers.landscape.intro', {n: fmt(data.landscape.studied), pct: data.landscape.single_study_pct})}
      </p>
      <div class="space-y-1 font-mono text-sm dark:text-gray-300">
        {#each Object.entries(dist) as [k, v]}
          <div class="flex items-center gap-2">
            <span class="w-16 text-right text-gray-500 dark:text-gray-400">{k === '1' ? t('numbers.one_paper') : t('numbers.n_papers', {n: k})}</span>
            <div class="flex-1 h-5 bg-gray-100 dark:bg-gray-800 rounded">
              <div class="h-5 bg-blue-500 rounded" style="width: {100 * v / maxDist}%"></div>
            </div>
            <span class="w-28 text-right">{fmt(v)} ({pct(100 * v / data.landscape.studied)})</span>
          </div>
        {/each}
      </div>
      <p class="text-sm mt-3 text-gray-600 dark:text-gray-400">
        Most-studied:
        {#each data.landscape.top12 as g, i}{g.symbol} ({g.papers}){i < data.landscape.top12.length - 1 ? ' · ' : ''}{/each}
      </p>
      <p class="text-sm text-gray-600 dark:text-gray-400">
        Cross-host replication: {fmt(data.landscape.species_linked)} genes name a host species ·
        {fmt(data.landscape.multi_host_ge2)} in ≥2 species · {fmt(data.landscape.multi_host_ge3)} in ≥3.
        Widest: {#each data.landscape.cross_host_top.slice(0, 8) as g, i}{g.symbol} ({g.species} spp){i < 7 ? ' · ' : ''}{/each}
      </p>
    </section>

    <!-- ============ evidence classes ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.classes.title')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('numbers.classes.intro.a')}
        ({t('numbers.classes.intro.b')} <code>gene_registry.meta.json</code>; {t('numbers.classes.intro.c')}
      </p>
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"><table class="w-full text-sm text-gray-900 dark:text-gray-100 border rounded-lg dark:border-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-800 text-left">
          <tr><th class="px-3 py-2">{t('numbers.th.class')}</th><th class="px-3 py-2 text-right">{t('numbers.th.genes')}</th></tr>
        </thead>
        <tbody>
          {#each Object.entries(data.evidence.classes).sort((a, b) => b[1] - a[1]) as [cls, n]}
            <tr class="border-t dark:border-gray-800">
              <td class="px-3 py-1.5 dark:text-gray-300">{cls.replace(/_/g, ' ')}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(n)}</td>
            </tr>
          {/each}
          <tr class="border-t dark:border-gray-800"><td class="px-3 py-1.5 dark:text-gray-300">{t('numbers.classes.mechanistic')}</td><td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(data.evidence.mechanistic_genes)}</td></tr>
          <tr class="border-t dark:border-gray-800"><td class="px-3 py-1.5 dark:text-gray-300">{t('numbers.classes.central')}</td><td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(data.evidence.curated_central)}</td></tr>
          <tr class="border-t dark:border-gray-800"><td class="px-3 py-1.5 dark:text-gray-300">{t('numbers.classes.supporting')}</td><td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(data.evidence.curated_supporting)}</td></tr>
        </tbody>
      </table>
      </div>

      <h3 class="font-semibold mt-4 dark:text-white">{t('routes.numbers.breadth.depth.mentioned.supported') || 'Breadth × depth — "mentioned ≠ supported"'}</h3>
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"><table class="w-full text-sm text-gray-900 dark:text-gray-100 border rounded-lg dark:border-gray-700">
        <thead class="bg-gray-50 dark:bg-gray-800 text-left">
          <tr>
            <th class="px-3 py-2">{t('numbers.th.papers')}</th><th class="px-3 py-2 text-right">{t('numbers.th.genes')}</th>
            <th class="px-3 py-2 text-right">{t('numbers.th.mechanistic')}</th>
            <th class="px-3 py-2 text-right">{t('numbers.th.perturbation')}</th>
            <th class="px-3 py-2 text-right">≥2 classes</th>
          </tr>
        </thead>
        <tbody>
          {#each data.evidence.breadth_depth as row}
            <tr class="border-t dark:border-gray-800">
              <td class="px-3 py-1.5 font-medium dark:text-gray-200">{row.bucket}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-300">{fmt(row.genes)}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-300">{row.mechanistic_pct}%</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-300">{row.perturbation_pct}%</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-300">{row.multi_class_pct}%</td>
            </tr>
          {/each}
        </tbody>
      </table>
      </div>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('numbers.consensus_note')}
      </p>
    </section>

    <!-- ============ genomics ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.comparative.title')}</h2>
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"><table class="w-full text-sm text-gray-900 dark:text-gray-100 border rounded-lg dark:border-gray-700">
        <tbody>
          {#each [
            ['Genome assemblies catalogued', data.genomics.assemblies_catalogued],
            ['Chromosome-level', data.genomics.chromosome_level],
            ['Genomes searched (presence progress)', data.genomics.genomes_searched_progress],
            ['Presence calls', data.genomics.presence_calls],
            ['Panel genes searched', data.genomics.panel_genes_searched],
            ['Species with presence calls', data.genomics.presence_species],
            ['Ortholog groups', data.genomics.orthogroups]
          ] as [label, value]}
            <tr class="border-b last:border-0 dark:border-gray-800">
              <td class="px-3 py-1.5 text-gray-600 dark:text-gray-400">{t('numbers.' + label.toLowerCase().replace(/[^a-z0-9]+/g, '.')) || label}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{fmt(value)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400">
        {t('numbers.presence_note')}
      </p>
    </section>

    <!-- ============ authors ============ -->
    {#if data.authors?.total}
      <section class="space-y-3">
        <h2 class="text-xl font-semibold dark:text-white">{t('numbers.authors.title')}</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          {fmt(data.authors.total)} distinct author names across
          {fmt(data.authors.papers_with_author_lists)} papers with extracted author lists
          ({data.authors.corpus_coverage_pct}% of the corpus) ·
          {fmt(data.authors.multi_paper)} authors ({pct(100 * data.authors.multi_paper / data.authors.total)}) appear in ≥2 papers ·
          {t('numbers.coauthor_edges', {n: fmt(data.authors.co_author_edges)})}
        </p>
        <div class="space-y-1 font-mono text-sm dark:text-gray-300">
          {#each Object.entries(data.authors.papers_per_author) as [k, v]}
            <div class="flex items-center gap-2">
              <span class="w-20 text-right text-gray-500 dark:text-gray-400">{k === '1' ? t('numbers.one_paper') : t('numbers.n_papers', {n: k === '5' ? '5+' : k})}</span>
              <div class="flex-1 h-5 bg-gray-100 dark:bg-gray-800 rounded">
                <div class="h-5 bg-teal-500 rounded" style="width: {100 * v / Math.max(...Object.values(data.authors.papers_per_author))}%"></div>
              </div>
              <span class="w-24 text-right">{fmt(v)}</span>
            </div>
          {/each}
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Most prolific:
          {#each data.authors.top as a, i}{a.name} ({a.papers}){i < data.authors.top.length - 1 ? ' · ' : ''}{/each}
        </p>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Top collaborations:
          {#each data.authors.top_collaborations as c, i}{c.pair} ({c.papers}){i < data.authors.top_collaborations.length - 1 ? ' · ' : ''}{/each}
        </p>
      </section>
    {/if}

    <!-- ============ orthogroups ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.orthologs.title')}</h2>
      <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"><table class="w-full text-sm text-gray-900 dark:text-gray-100 border rounded-lg dark:border-gray-700">
        <tbody>
          {#each [
            ['Orthogroups (total)', data.genomics.orthogroups_detail.total_ogs],
            ['Species in the OG analysis', data.genomics.orthogroups_detail.species_in_analysis],
            ['Membership matrix rows (OG × species × copies)', data.genomics.orthogroups_detail.matrix_rows],
            ['Host-panel genes mapped to OGs', data.genomics.orthogroups_detail.panel_genes_mapped],
            ['Distinct OGs containing panel genes', data.genomics.orthogroups_detail.panel_ogs],
            ['Single-species OGs', data.genomics.orthogroups_detail.single_species_ogs],
            ['Universal OGs (in all species)', data.genomics.orthogroups_detail.universal_ogs],
            ['Median species per OG', data.genomics.orthogroups_detail.median_species_per_og],
            ['Panel-gene OGs: median species coverage', data.genomics.orthogroups_detail.panel_median_species_per_og + ' of 463'],
            ['Panel-gene OGs: universal', data.genomics.orthogroups_detail.panel_universal_ogs],
            ['Panel-gene OGs: total copies', data.genomics.orthogroups_detail.panel_total_copies],
            ['OG species: HPAI hosts / non-hosts', `${data.genomics.orthogroups_detail.og_host_species} / ${data.genomics.orthogroups_detail.og_nonhost_species}`],
            ['Mean panel-gene copies per species: hosts vs non-hosts', `${data.genomics.orthogroups_detail.panel_mean_copies_host_species} vs ${data.genomics.orthogroups_detail.panel_mean_copies_nonhost_species}`],
            ['Largest OG (total gene copies)', `${data.genomics.orthogroups_detail.largest_og} (${fmt(data.genomics.orthogroups_detail.largest_og_copies)})`]
          ] as [label, value]}
            <tr class="border-b last:border-0 dark:border-gray-800">
              <td class="px-3 py-1.5 text-gray-600 dark:text-gray-400">{t('numbers.' + label.toLowerCase().replace(/[^a-z0-9]+/g, '.')) || label}</td>
              <td class="px-3 py-1.5 text-right font-mono dark:text-gray-200">{typeof value === 'number' ? fmt(value) : value}</td>
            </tr>
          {/each}
        </tbody>
      </table>
      </div>
    </section>

    <!-- ============ literature concentration ============ -->
    <section class="space-y-3">
      <h2 class="text-xl font-semibold dark:text-white">{t('numbers.literature.title')}</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {t('numbers.literature.intro', {s: fmt(data.literature_concentration.species_mentioned), l: fmt(data.literature_concentration.total_links), top: data.literature_concentration.top10_share_pct, p80: fmt(data.literature_concentration.pct80_species), p80s: data.literature_concentration.pct80_share_of_mentioned_pct, med: data.literature_concentration.median_papers_per_species})}
      </p>
      <p class="text-sm">
        {#each data.literature_concentration.top10 as row, i}{row.species} ({row.papers}){i < 9 ? ' · ' : ''}{/each}
      </p>
      <p class="text-sm text-red-600 dark:text-red-400 font-medium">
        {fmt(data.literature_concentration.detected_zero_papers)} of
        {fmt(data.literature_concentration.detected_hosts)} detected HPAI hosts
        ({Math.round(100 * data.literature_concentration.detected_zero_papers / data.literature_concentration.detected_hosts)}%)
        have never been studied — the observed hosts of the panzootic are nearly unstudied.
      </p>
      <p class="text-sm text-gray-600 dark:text-gray-400">
        Avian research effort by order:
        {#each Object.entries(data.literature_concentration.avian_links_by_order) as [o, n], i}{o} ({n}){i < 4 ? ' · ' : ''}{/each}
      </p>
    </section>

    <!-- ============ gene concentration ============ -->
    {#if data.gene_concentration}
      <section class="space-y-3">
        <h2 class="text-xl font-semibold dark:text-white">{t('routes.numbers.gene.concentration.broad.but') || 'Gene concentration — broad but shallow'}</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          {t('numbers.gene_concentration.intro', {g: fmt(data.gene_concentration.studied_genes), l: fmt(data.gene_concentration.total_links), top: data.gene_concentration.top10_share_pct, p80: fmt(data.gene_concentration.pct80_genes), p80s: data.gene_concentration.pct80_share_pct, core: fmt(data.gene_concentration.genes_20plus)})}
        </p>
        <p class="text-sm">
          {#each data.gene_concentration.top10 as row, i}{row.symbol} ({row.papers}){i < 9 ? ' · ' : ''}{/each}
        </p>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          {t('numbers.concentration_note')}
        </p>
      </section>
    {/if}

    <footer class="text-xs text-gray-500 dark:text-gray-400 border-t pt-4 dark:border-gray-800">
      {t('numbers.sources_prefix')} stats.json · species_breakdown.json · gene_registry.jsonl (+meta) ·
      gene_evidence_counts.json · wiki_genes.json · gene_presence_v2.jsonl/.parquet ·
      chrom_progress.json · papers_index.parquet. {t('numbers.rebuild')}:
      <code>pixi run python scripts/papers/build_by_the_numbers.py</code>
    </footer>
  {/if}
</div>
