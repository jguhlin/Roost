<script>
  import { t } from '../../../lib/stores/i18n.svelte.js';
  let buildDate = new Date().toISOString().split('T')[0];
</script>

<footer class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">
  <div class="max-w-7xl mx-auto px-4 py-6">
    <div class="flex flex-col md:flex-row items-center justify-between gap-4">
      <!-- Left: Project info — logo lockup (the nest mark is the brand:
           header + favicon; the footer is where it gets room to breathe) -->
      <div class="flex items-center gap-3">
        <a href="#/" class="text-4xl leading-none select-none" title="Roost" aria-label="Roost — home">🪺</a>
        <div class="text-sm">
          <div class="font-semibold text-base text-gray-800 dark:text-gray-200">{t('lib_components_common_Footer.roost')}</div>
          <div class="text-gray-500 dark:text-gray-400">{t('lib_components_common_Footer.avian.influenza.host.genomics') || '— Avian Influenza Host Genomics Resource'}</div>
        </div>
      </div>

      <!-- Center: Data update timestamp -->
      <div class="text-sm text-gray-500 dark:text-gray-400">
        {t('lib_components_common_Footer.data.updated')}: {buildDate}
      </div>

      <!-- Right: Links -->
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <a
          href="https://github.com/jguhlin/roost"
          target="_blank"
          rel="noopener noreferrer"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1"
        >
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
          </svg>
          GitHub
        </a>
        <a
          href="#/downloads"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('lib_components_common_Footer.download.data') || 'Download Data'}
        </a>
        <a
          href="#/history"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.history') || 'History'}
        </a>
        <a
          href="#/resources"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.resources') || 'Resources'}
        </a>
        <a
          href="#/glossary"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.glossary') || 'Glossary'}
        </a>
        <a
          href="#/methods"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.methods') || 'Methods'}
        </a>
        <a
          href="#/numbers"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.numbers') || 'Numbers'}
        </a>
        <a
          href="#/press"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('press.page.title')}
        </a>
        <a
          href="#/spread-layers"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.spread_layers') || 'Eras & hosts'}
        </a>
        <a
          href="#/region-risk"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.region_risk') || 'Regional risk'}
        </a>
        <a
          href="#/credits"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
        >
          {t('nav.credits') || 'Credits'}
        </a>
      </div>
    </div>

    <!-- Attribution -->
    <div class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 text-center">
      {t('lib_components_common_Footer.data.aggregated.from.multiple') || 'Data aggregated from multiple public surveillance databases. See individual sources for licensing.'}
    </div>

    <!-- Environmental sustainability statement -->
    <div class="mt-3 text-xs text-gray-500 dark:text-gray-400 text-center max-w-3xl mx-auto leading-relaxed">
      <span class="font-medium text-gray-600 dark:text-gray-300">{t('footer.sustainability.title')}</span>
      {t('footer.sustainability.body')}
      <a href="https://www.otago.ac.nz/sustainability/doing/sdg/contribution#sdg-7-affordable-and-clean-energy"
         target="_blank" rel="noopener noreferrer"
         class="underline hover:text-gray-700 dark:hover:text-gray-300"
         aria-label={`${t('footer.sustainability.sdg7')} — ${t('a11y.open.external')}`}>{t('footer.sustainability.sdg7')}</a>
      {t('footer.sustainability.and')}
      <a href="https://www.otago.ac.nz/propertyservices/energy-and-building-controls/energy-strategy"
         target="_blank" rel="noopener noreferrer"
         class="underline hover:text-gray-700 dark:hover:text-gray-300"
         aria-label={`${t('footer.sustainability.energy_strategy')} — ${t('a11y.open.external')}`}>{t('footer.sustainability.energy_strategy')}</a>.
    </div>

    <!-- GANZ logo -->
    <div class="mt-4 flex justify-center">
      <img src="img/ganz-logo.png" alt={t('common.footer.genomics.aotearoa.new.zealand') || 'Genomics Aotearoa New Zealand (GANZ)'} class="h-14 w-auto opacity-80 hover:opacity-100 transition-opacity" />
    </div>
  </div>
</footer>
