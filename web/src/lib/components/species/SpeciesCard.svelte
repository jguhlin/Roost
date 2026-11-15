<script>
  import { navigate } from '../../stores/router.js';
  import { formatNumber, getAssemblyLevelInfo, getSusceptibilityInfo, getIUCNInfo } from '../../utils/format.js';
  import { phylopicIndex, phylopicPath } from '../../utils/phylopic.js';
  import { sn } from '../../stores/i18n.svelte.js';
import { t } from '../../stores/i18n.svelte.js';

  // Props
  let { species, compact = false } = $props();

  let silhouette = $state(null);
  $effect(() => {
    const sci = species.scientific_name;
    silhouette = null; // clear immediately on species change (recycled components)
    phylopicIndex().then(idx => {
      if (species.scientific_name === sci) silhouette = phylopicPath(sci, idx);
    });
  });

  function handleClick() {
    // Wiki-only/presence species have no taxon_id — the detection modal
    // cannot resolve them. Route to the full page, which serves the gene
    // panel + wiki content for any scientific name.
    if (!species.taxon_id && species.scientific_name) {
      navigate('species-full', species.scientific_name);
      return;
    }
    navigate('species', species.taxon_id || species.scientific_name);
  }
</script>

<button
  onclick={handleClick}
  class="w-full min-w-0 text-left bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow p-4 {compact ? 'p-3' : 'p-4'}"
>
  <div class="flex items-start justify-between gap-2">
    {#if silhouette}
      <img
        src={silhouette}
        alt=""
        loading="lazy"
        class="flex-shrink-0 h-10 w-10 object-contain dark:invert"
        title="Silhouette: PhyloPic"
      />
    {/if}
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <h3 class="font-medium text-gray-900 dark:text-white truncate italic {compact ? 'text-sm' : ''}">
          {species.scientific_name}
        </h3>
        {#if species.iucn}
          {@const iucnInfo = getIUCNInfo(species.iucn)}
          <span class="flex-shrink-0 px-1.5 py-0.5 text-xs font-bold rounded {iucnInfo.bg} {iucnInfo.text}" title={t('iucn.' + (species.iucn || 'DD')) || iucnInfo.name}>
            {species.iucn}
          </span>
        {/if}
      </div>
      {#if species.common_name}
        <p class="text-gray-500 dark:text-gray-400 truncate {compact ? 'text-xs' : 'text-sm'}">
          {sn(species.scientific_name, species.common_name)}
          {#if sn(species.scientific_name) !== species.common_name && species.common_name}
            <span class="text-gray-500 dark:text-gray-400 text-xs">· {species.common_name}</span>
          {/if}
        </p>
      {/if}
    </div>

    <!-- Detection badge or "No cases" indicator -->
    {#if species.detection_count > 0}
      <span class="flex-shrink-0 ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
            title={t('species.card.detections.tip')} aria-label={t('species.card.detections.tip')}>
        {formatNumber(species.detection_count)}
      </span>
    {:else if species.vaccination_target}
      <span class="flex-shrink-0 ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300" title={t('species.card.vaccination.target') || 'Vaccination target species'}>
        Vacc
      </span>
    {:else}
      <span class="flex-shrink-0 ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
        0 cases
      </span>
    {/if}
  </div>

  {#if !compact}
    <!-- Additional info row -->
    <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
      {#if species.order}
        <span>{species.order}</span>
      {/if}

      {#if species.assembly_level}
        {@const levelInfo = getAssemblyLevelInfo(species.assembly_level)}
        <span class="px-1.5 py-0.5 rounded {levelInfo.color === 'green' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : levelInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}">
          {t('assembly.' + (species.genome_level || 'Unknown')) || levelInfo.label}
        </span>
      {:else}
        <span class="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
          {t('species.no.genome') || 'No genome'}
        </span>
      {/if}

      {#if species.susceptibility_class}
        {@const suscInfo = getSusceptibilityInfo(species.susceptibility_class)}
        <span class="px-1.5 py-0.5 rounded {suscInfo.color === 'red' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : suscInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' : suscInfo.color === 'green' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}"
              title={t('susc.legacy.tip')} aria-label={t('susc.legacy.tip')}>
          {t('susc.' + (species.susceptibility_class || 'Unknown')) || suscInfo.label} {t('susc.risk') || 'risk'}
          <span class="opacity-70">({t('susc.legacy.short')})</span>
        </span>
      {/if}
    </div>
  {/if}
</button>
