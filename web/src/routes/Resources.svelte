<script>
  import { t } from '../lib/stores/i18n.svelte.js';

  // External resource links organized by category
  const resources = [
    {
      category: 'Occurrence & Distribution Data',
      items: [
        {
          name: 'GBIF',
          url: 'https://www.gbif.org/',
          description: 'Global Biodiversity Information Facility - worldwide species occurrence records',
          coverage: 'Global',
          access: 'Open'
        },
        {
          name: 'eBird',
          url: 'https://ebird.org/',
          description: 'Real-time bird observations from citizen scientists worldwide',
          coverage: 'Global (strongest in Americas)',
          access: 'Open'
        },
        {
          name: 'BirdLife International',
          url: 'https://www.birdlife.org/',
          description: 'Conservation partnership with species range maps',
          coverage: 'Global',
          access: 'Open'
        }
      ]
    },
    {
      category: 'Tracking & Movement Data',
      items: [
        {
          name: 'Movebank',
          url: 'https://www.movebank.org/',
          description: 'Animal tracking data repository with GPS telemetry',
          coverage: 'Global',
          access: 'Registration required'
        },
        {
          name: 'USGS Bird Banding Laboratory',
          url: 'https://www.usgs.gov/labs/bird-banding-laboratory',
          description: 'US bird banding and recovery data',
          coverage: 'North America',
          access: 'Request required'
        }
      ]
    },
    {
      category: 'Viral Sequences & Surveillance',
      items: [
        {
          name: 'GISAID',
          url: 'https://gisaid.org/',
          description: 'Global initiative on sharing avian flu data - viral sequences',
          coverage: 'Global',
          access: 'Registration required'
        },
        {
          name: 'Nextstrain',
          url: 'https://nextstrain.org/avian-flu',
          description: 'Real-time tracking of avian influenza evolution',
          coverage: 'Global',
          access: 'Open'
        },
        {
          name: 'FAO EMPRES-i',
          url: 'https://empres-i.fao.org/',
          description: 'Global Animal Disease Information System',
          coverage: 'Global',
          access: 'Open'
        },
        {
          name: 'WOAH WAHIS',
          url: 'https://wahis.woah.org/',
          description: 'World Organisation for Animal Health Information System',
          coverage: 'Global',
          access: 'Open'
        }
      ]
    },
    {
      category: 'Genomics & Sequences',
      items: [
        {
          name: 'NCBI Datasets',
          url: 'https://www.ncbi.nlm.nih.gov/datasets/',
          description: 'Download genome assemblies and annotations',
          coverage: 'Global',
          access: 'Open'
        },
        {
          name: 'Ensembl',
          url: 'https://www.ensembl.org/',
          description: 'Genome browser and annotation database',
          coverage: 'Selected species',
          access: 'Open'
        },
        {
          name: 'UniProt',
          url: 'https://www.uniprot.org/',
          description: 'Protein sequence and functional information',
          coverage: 'Global',
          access: 'Open'
        },
        {
          name: 'NCBI Gene',
          url: 'https://www.ncbi.nlm.nih.gov/gene/',
          description: 'Gene records and annotations',
          coverage: 'Global',
          access: 'Open'
        }
      ]
    },
    {
      category: 'Phylogeny & Taxonomy',
      items: [
        {
          name: 'BirdTree.org',
          url: 'https://birdtree.org/',
          description: 'Global avian phylogeny with 10,000+ species',
          coverage: 'Global (all birds)',
          access: 'Open'
        },
        {
          name: 'TimeTree',
          url: 'https://timetree.org/',
          description: 'Divergence time estimation between species',
          coverage: 'Global (all life)',
          access: 'Open'
        },
        {
          name: 'NCBI Taxonomy',
          url: 'https://www.ncbi.nlm.nih.gov/taxonomy',
          description: 'Taxonomic classification database',
          coverage: 'Global',
          access: 'Open'
        },
        {
          name: 'IOC World Bird List',
          url: 'https://www.worldbirdnames.org/',
          description: 'Authoritative bird species names and taxonomy',
          coverage: 'Global (all birds)',
          access: 'Open'
        }
      ]
    },
    {
      category: 'Conservation Status',
      items: [
        {
          name: 'IUCN Red List',
          url: 'https://www.iucnredlist.org/',
          description: 'Global conservation status assessments',
          coverage: 'Global',
          access: 'Open (API requires registration)'
        },
        {
          name: 'ACAP',
          url: 'https://www.acap.aq/',
          description: 'Agreement on Conservation of Albatrosses and Petrels',
          coverage: 'Southern Hemisphere seabirds',
          access: 'Open'
        }
      ]
    }
  ];

  function getAccessBadgeClass(access) {
    switch (access) {
      case 'Open': return 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300';
      case 'Registration required': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300';
      case 'Request required': return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300';
      default: return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
    }
  }
</script>

<svelte:head><title>{t('resources_page.external.resources') || 'External resources'} — Roost</title></svelte:head>

<div class="space-y-8">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('resources_page.external.resources')}</h1>
    <p class="text-gray-600 dark:text-gray-300 mt-2">
      {t('resources.page.intro')}
    </p>
  </div>

  {#each resources as category}
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{category.category}</h2>
      </div>
      <div class="divide-y divide-gray-100 dark:divide-gray-700">
        {#each category.items as resource}
          <div class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-3">
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-lg font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {resource.name}
                  </a>
                  <span class="px-2 py-0.5 text-xs rounded-full {getAccessBadgeClass(resource.access)}">
                    {resource.access}
                  </span>
                </div>
                <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">{t('resources.desc.' + resource.name) || resource.description}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Coverage: {resource.coverage}</p>
              </div>
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${resource.name} — ${t('a11y.open.external')}`}
                class="ml-4 p-2 text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/each}

  <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 border border-blue-100 dark:border-blue-800">
    <h3 class="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">{t('resources_page.suggest.a.resource')}</h3>
    <p class="text-blue-800 dark:text-blue-200 text-sm">
      {t('resources.suggest') || 'Know of a relevant database or tool that should be listed here?'}
      <a href="https://github.com/jguhlin/roost/issues" target="_blank" rel="noopener noreferrer" class="underline">
        {t('resources.suggest.link')}
      </a>
      {t('resources.suggest.tail')}
    </p>
  </div>
</div>
