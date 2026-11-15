<script>
  import { t } from '../lib/stores/i18n.svelte.js';
  /**
   * Credits — sources, software, and contributors not credited elsewhere.
   * Route: #/credits
   */
  import { onMount } from 'svelte';

  let phylopic = $state(null);
  let figLibraries = $state([]);
  let dataSourcesRegistry = $state(/** @type {any | null} */ (null));
  let mbSearch = $state('');
  let mbShowAll = $state(false);

  onMount(async () => {
    try {
      const r = await fetch('data/phylopic.json');
      phylopic = await r.json();
    } catch { /* attributions optional */ }
    try {
      const r = await fetch(`figures/libraries.json?t=${Date.now()}`);
      if (r.ok) figLibraries = (await r.json()).libraries || [];
    } catch { /* figure libraries optional */ }
    try {
      const r = await fetch('data/data_sources.json');
      if (r.ok) dataSourcesRegistry = await r.json();
    } catch { /* registry optional */ }
  });

  const mbStudies = $derived.by(() => {
    let list = dataSourcesRegistry?.movebank?.studies ?? [];
    const q = mbSearch.trim().toLowerCase();
    if (q) {
      list = list.filter((s) =>
        (s.study_name + ' ' + s.pi + ' ' + s.citation + ' ' + s.our_species.join(' '))
          .toLowerCase().includes(q));
    }
    return mbShowAll ? list : list.slice(0, 50);
  });
  let phylopicContributors = $derived.by(() => {
    if (!phylopic) return [];
    const byC = new Map();
    for (const [slug, info] of Object.entries(phylopic)) {
      if (info.status !== 'ok') continue;
      // fetch_phylopic.py stores the artist as `attribution` (contributor is
      // null in the mirrored index) — accept both.
      const artist = info.attribution || info.contributor;
      if (!artist) continue;
      if (!byC.has(artist)) {
        byC.set(artist, { name: artist, images: [], url: null });
      }
      const c = byC.get(artist);
      c.images.push(info);
      if (!c.url) c.url = info.url;
    }
    return [...byC.values()].sort((a, b) => b.images.length - a.images.length);
  });

  const dataSources = [
    {
      name: 'WOAH WAHIS',
      desc: 'World Animal Health Information System — global outbreak reports (API, reverse-engineered interface)',
      url: 'https://wahis.woah.org/'
    },
    {
      name: 'USDA APHIS WHISPers',
      desc: 'Wildlife Health Information Sharing Partnership — event-based US wildlife mortality data',
      url: 'https://whispers.usgs.gov/'
    },
    {
      name: 'FAO',
      desc: 'Food and Agriculture Organization — global HPAI situation updates and Sub-Saharan Africa bulletins',
      url: 'https://www.fao.org/animal-health'
    },
    {
      name: 'SA OCIMS',
      desc: 'South Africa Ocean and Coastal Information Management System — coastal seabird HPAI events',
      url: 'https://ocims.dalrrd.gov.za/'
    },
    {
      name: 'ImmunomeDB',
      desc: 'Comparative immunology database (2020 / B10K-v1 snapshot) — used as vintage breadth-only layer, reconfirmed against modern assemblies. The original immunomedb.org is offline; the project lives on here.',
      url: 'https://gitlab.com/rcmueller/immunomedb'
    },
    {
      name: 'New Zealand MPI / Biosecurity NZ',
      desc: 'Aotearoa New Zealand HPAI surveillance and wildlife health reporting',
      url: 'https://www.mpi.govt.nz/'
    },
    {
      name: 'Wildlife Health Australia',
      desc: 'Australian wildlife disease surveillance events',
      url: 'https://wildlifehealthaustralia.com.au/'
    },
    {
      name: 'NCBI',
      desc: 'Genome assemblies, RefSeq annotations, taxonomy, and Gene data',
      url: 'https://www.ncbi.nlm.nih.gov/'
    },
    {
      name: 'UniProt',
      desc: 'GO-annotated immune gene backbone (546 panel genes) and cross-references',
      url: 'https://www.uniprot.org/'
    },
    {
      name: 'Birds of the World / Clements taxonomy',
      desc: 'Aves taxonomy backbone (~16,500 species) and vernacular names',
      url: 'https://birdsoftheworld.org/'
    },
    {
      name: 'IUCN Red List',
      desc: 'Conservation status and population trend data',
      url: 'https://www.iucnredlist.org/'
    },
    {
      name: 'GBIF',
      desc: 'Species occurrence and name resolution links',
      url: 'https://www.gbif.org/'
    },
    {
      name: 'RCSB PDB',
      desc: 'Protein 3D structures shown on gene pages',
      url: 'https://www.rcsb.org/'
    },
    {
      name: 'Avian Immunology (3rd ed., 2022)',
      desc: 'Schat, Kaspers & Kaiser (eds.), Academic Press/Elsevier — cited as reference; chapter content mined internally for extraction only, never republished',
      url: 'https://www.elsevier.com/books/avian-immunology/schat/978-0-12-818708-1'
    },
    {
      name: 'Research literature',
      desc: 'LLM extraction pipeline covering 1,366 registered papers — 1,204 with full markdown text, 142 with verified 7-step extraction — cited individually on every gene, mutation, and species page',
      url: '#/papers'
    }
  ];

  const software = [
    { name: 'pi agent', desc: 'primary AI development tool (powered by GLM 5.3)', url: 'https://github.com/earendil-works/pi-coding-agent' },
    { name: 'Codex', desc: 'contributing AI development tool', url: 'https://openai.com/codex' },
    { name: 'Claude', desc: 'contributing AI development tool', url: 'https://anthropic.com/claude' },
    { name: 'Muse Glimmer', desc: 'LLM literature analysis pipeline (gene mechanisms, mutation effects, spread pathways)', url: null },
    { name: 'DIAMOND', desc: 'sequence alignment (blastp/tblastn replacement)', url: 'https://github.com/bbuchfink/diamond' },
    { name: 'BLAST+', desc: 'NCBI blastn layer-1 evidence', url: 'https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+' },
    { name: 'EMBOSS getorf', desc: 'ORF extraction', url: 'https://emboss.sourceforge.net/' },
    { name: 'MAFFT', desc: 'multiple sequence alignment', url: 'https://mafft.cbrc.jp/alignment/software/' },
    { name: 'FastTree', desc: 'phylogenetic inference', url: 'http://www.microbesonline.org/fasttree/' },
    { name: 'MCL', desc: 'ortholog clustering', url: 'https://micans.org/mcl/' },
    { name: 'OrthoFinder', desc: 'orthogroup inference across the 463-bird set', url: 'https://davidemms.github.io/OrthoFinder/' },
    { name: 'DuckDB', desc: 'in-browser analytics (WASM)', url: 'https://duckdb.org/' },
    { name: 'SvelteKit + Svelte 5', desc: 'web framework', url: 'https://svelte.dev/' },
    { name: 'MapLibre GL + deck.gl', desc: 'mapping and map layers', url: 'https://maplibre.org/' },
    { name: 'Phylocanvas', desc: 'phylogenetic tree viewer', url: 'https://phylocanvas.org/' },
    { name: '3Dmol.js', desc: 'protein structure viewer', url: 'https://3dmol.org/' },
    { name: 'igv.js', desc: 'embedded genome browser', url: 'https://igv.org/' },
    { name: 'Cytoscape', desc: 'pathway and network graphs (with ELK and fcose layouts)', url: 'https://js.cytoscape.org/' },
    { name: 'Roost WASM BLAST', desc: 'in-browser Smith-Waterman protein search kernel (Rust/WASM)', url: null },
    { name: 'Vite', desc: 'build tooling', url: 'https://vitejs.dev/' },
    { name: 'Playwright', desc: 'end-to-end tests', url: 'https://playwright.dev/' },
    { name: 'pixi', desc: 'reproducible toolchain environments', url: 'https://pixi.sh/' }
  ];
</script>

<svelte:head><title>{t('credits_page.credits.amp.sources') || 'Credits & sources'} — Roost</title></svelte:head>

<div class="max-w-4xl mx-auto space-y-10">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{t('credits_page.credits.amp.sources')}</h1>
    <p class="text-gray-600 dark:text-gray-300">
      {t('credits.intro')}
    </p>
  </div>

  <!-- How to cite -->
  <section>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">{t('credits_page.how.to.cite.this')}</h2>
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-5">
      <p class="text-sm text-gray-600 dark:text-gray-300 mb-3">
        {t('credits.cite_intro')}
      </p>
      <!-- Primary citation: the resource paper. TODO(biorxiv): set PAPER_URL
           + full citation string when the preprint posts. -->
      <blockquote class="text-sm font-mono text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-l-4 border-blue-500 mb-3">
        Roost: Avian Influenza Host Genomics Resource. bioRxiv preprint
        ({t('credits.cite.submitted')}). https://josephguhlin.com/Roost/
      </blockquote>
      <blockquote class="text-sm font-mono text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-l-4 border-gray-300 dark:border-gray-600">
        Roost: Avian Influenza Host Genomics Resource (2026).
        Detection, genomic, and susceptibility data for H5N1 host species.
        Retrieved from https://josephguhlin.com/Roost/.
        Accessed {new Date().toISOString().slice(0, 10)}.
      </blockquote>
      <p class="text-xs text-gray-600 dark:text-gray-400 mt-3">
        {t('credits.license_pre')}
        <a href="data/provenance.json" class="text-blue-600 dark:text-blue-400 underline">{t('credits_page.provenancejson')}</a>
        {t('credits.license_post')}
      </p>
    </div>
  </section>

  <!-- Data sources -->
  <section>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">{t('credits_page.data.sources')}</h2>
    <div class="grid md:grid-cols-2 gap-3">
      {#each dataSources as src}
        {#if src.url}
          <a
            href={src.url}
            target={src.url.startsWith('#') ? undefined : '_blank'}
            rel="noopener noreferrer"
            class="block bg-white dark:bg-gray-800 rounded-lg shadow p-4 hover:shadow-md transition-shadow"
          >
            <div class="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">{src.name}
              <svg class="w-3.5 h-3.5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">{t('credits.desc.' + src.name) || src.desc}</div>
          </a>
        {:else}
          <div class="block bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 p-4"
               title={t('routes.credits.no.live.site.historical') || 'No live site — historical snapshot'}>
            <div class="font-semibold text-gray-500 dark:text-gray-400 flex items-center gap-2">{src.name}
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">{t('credits_page.archived')}</span>
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{t('credits.desc.' + src.name) || src.desc}</div>
          </div>
        {/if}
      {/each}
    </div>
    <p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
      {t('credits.machine.list') || 'Machine-readable source list with licenses and record counts:'}
      <a href="data/provenance.json" class="text-blue-600 dark:text-blue-400 underline" target="_blank" rel="noopener">{t('credits_page.provenancejson')}</a>
      {t('credits.regen_note')}
    </p>
  </section>

  <!-- Software -->
  {#if dataSourcesRegistry?.movebank}
  <section class="mt-10">
    <div class="flex flex-wrap items-baseline justify-between gap-2 mb-3">
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
        {t('credits.movebank_studies', { n: dataSourcesRegistry.movebank.total_studies_matching.toLocaleString() })}
      </h2>
      <span class="text-sm text-gray-500 dark:text-gray-400">
        {t('credits.movebank_with_citations', { n: dataSourcesRegistry.movebank.with_formal_citations })} ·
        <a href="https://www.movebank.org" class="underline">movebank.org</a>
      </span>
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4 max-w-3xl">
      {dataSourcesRegistry.movebank.attribution_note}
    </p>
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <label class="sr-only" for="mb-search">{t('credits.search_studies')}</label>
      <input id="mb-search" type="search" class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm w-72"
        placeholder={t('common.search_dots')} bind:value={mbSearch} />
      <button class="text-sm text-blue-600 dark:text-blue-400 underline"
        onclick={() => (mbShowAll = !mbShowAll)}>
        {mbShowAll ? t('credits.show_top_50') : t('credits.show_all_n', { n: (dataSourcesRegistry.movebank.total_studies_matching || 0).toLocaleString() })}
      </button>
    </div>
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700" tabindex="0" role="region" aria-label={t('credits.movebank_table_label')}>
      <table class="w-full text-sm">
        <caption class="sr-only">{t('credits.movebank.caption') || 'Studies informing our movement-coverage layer'}</caption>
        <thead class="bg-gray-100 dark:bg-gray-800 text-left sticky top-0">
          <tr>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('credits.mb.study')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">PI</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('credits.mb.individuals')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('credits.our_species')}</th>
            <th scope="col" class="px-3 py-2.5 font-semibold">{t('credits.mb.citation')}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
          {#each mbStudies as s (s.study_id)}
            <tr class="bg-white dark:bg-gray-900 even:bg-gray-50/60 dark:even:bg-gray-800/30">
              <td class="px-3 py-2.5 text-gray-900 dark:text-gray-100">{s.study_name}</td>
              <td class="px-3 py-2.5 text-gray-600 dark:text-gray-300">{s.pi}</td>
              <td class="px-3 py-2.5 tabular-nums text-gray-500 dark:text-gray-400">{s.n_individuals.toLocaleString()}</td>
              <td class="px-3 py-2.5 text-gray-500 dark:text-gray-400 italic text-xs">{s.our_species.slice(0, 3).join(', ')}{#if s.our_species.length > 3} +{s.our_species.length - 3}{/if}</td>
              <td class="px-3 py-2.5 text-gray-500 dark:text-gray-400 text-xs max-w-md">
                {#if s.citation}<span class="citation-text">{s.citation.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()}</span>{:else if s.acknowledgements}<span class="text-gray-500 dark:text-gray-400">{s.acknowledgements.slice(0, 120)}</span>{:else}<span class="text-gray-400">—</span>{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if !mbShowAll && (dataSourcesRegistry.movebank.total_studies_matching || 0) > 50}
      <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">Showing top 50 of {dataSourcesRegistry.movebank.total_studies_matching.toLocaleString()} studies — search or show all to see more.</p>
    {/if}
  </section>
  {/if}

  {#if dataSourcesRegistry?.corpus_papers}
  <section class="mt-10">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
      Corpus Papers ({dataSourcesRegistry.corpus_papers.total.toLocaleString()})
    </h2>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      {dataSourcesRegistry.corpus_papers.attribution_note}
    </p>
    <details>
      <summary class="text-sm text-blue-600 dark:text-blue-400 underline cursor-pointer">
        View all {dataSourcesRegistry.corpus_papers.total.toLocaleString()} citations
      </summary>
      <ul class="mt-3 space-y-1 text-xs text-gray-600 dark:text-gray-300 max-h-96 overflow-y-auto">
        {#each dataSourcesRegistry.corpus_papers.papers as p (p.id)}
          <li class="border-b border-gray-100 dark:border-gray-800 pb-1">
            {#if p.doi}<a href="https://doi.org/{p.doi}" class="underline">
              {p.authors} ({p.year}) {p.title} <em>{p.journal}</em>
            </a>
            {:else}
              {p.authors} ({p.year}) {p.title} <em>{p.journal}</em>
            {/if}
          </li>
        {/each}
      </ul>
    </details>
  </section>
  {/if}

  <section>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">{t('routes_Credits.software')}</h2>
    <div class="flex flex-wrap gap-2">
      {#each software as s}
        <a
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          class="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
          title={t('credits.desc.' + s.name) || s.desc}
        >
          {s.name}
        </a>
      {/each}
    </div>
  </section>

  <!-- Figure asset libraries -->
  <section>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-1">{t('credits_page.figure.asset.libraries')}</h2>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      {t('credits.figure_lib_intro')}
      <a href="credits/asset-credits.md" class="text-blue-600 dark:text-blue-400 underline" target="_blank" rel="noopener">{t('credits_page.full.credits.rollup')}</a>.
      CC BY licensed assets require attribution (creator + license link + modification note) — we
      credit everything, including CC0/public-domain assets.
    </p>
    <div class="grid sm:grid-cols-2 gap-2 mb-3">
      {#each figLibraries as l (l.key)}
        <div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 text-sm">
          <div class="flex items-start justify-between gap-2">
            <a href={l.url} target="_blank" rel="noopener noreferrer"
               class="font-medium text-gray-900 dark:text-gray-100 hover:underline">{l.name}</a>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-semibold shrink-0">{l.assets_indexed.toLocaleString()} assets</span>
          </div>
          <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">{l.note}</p>
          {#if l.license_url}
            <a href={l.license_url} target="_blank" rel="noopener noreferrer"
               class="text-xs text-blue-600 dark:text-blue-400 underline mt-1 inline-block">{l.license}</a>
          {:else}
            <span class="text-xs text-gray-600 dark:text-gray-400 mt-1 inline-block">license: {l.license}</span>
          {/if}
        </div>
      {/each}
    </div>
    {#if !figLibraries.length}
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('credits_page.registry.unavailable.see.docsassetcreditsmd')}</p>
    {/if}
  </section>

  <!-- PhyloPic -->
  <section>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-1">{t('credits_page.species.silhouettes')}</h2>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
      {t('credits.silhouettes.from') || 'Silhouette images from'}
      <a href="https://www.phylopic.org" target="_blank" rel="noopener noreferrer"
        class="text-blue-600 dark:text-blue-400 underline">{t('routes_Credits.phylopic')}</a>
      (public domain / per-image licenses), downloaded locally so the site never hits their API at runtime.
      {#if phylopicContributors.length}
        {phylopicContributors.reduce((n, c) => n + c.images.length, 0)} images by
        {phylopicContributors.length} contributors:
      {/if}
    </p>
    {#if phylopicContributors.length}
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {#each phylopicContributors as c}
          <a
            href={c.url || 'https://www.phylopic.org'}
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center justify-between gap-2 bg-white dark:bg-gray-800 rounded-lg shadow p-3 hover:shadow-md transition-shadow"
          >
            <span class="text-sm font-medium text-gray-900 dark:text-white truncate">{c.name}</span>
            <span class="text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap">{c.images.length} img</span>
          </a>
        {/each}
      </div>
    {:else if phylopic}
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('credits_page.no.silhouettes.downloaded.yet')}</p>
    {/if}
  </section>

  <!-- Disclaimer -->
  <section class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-5 text-sm text-gray-500 dark:text-gray-400">
    <p>
      Roost aggregates public surveillance and research data for conservation planning and research.
      It is not a primary source for animal health decisions — always verify against the linked
      original sources. Genome-based gene presence calls carry evidence levels (E0–E5) documented
      in the project log; consult individual gene pages for confidence details.
    </p>
  </section>
</div>
