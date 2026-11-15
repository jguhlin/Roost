<script>
import { t } from '../../stores/i18n.svelte.js';
  export let colorMode = 'detections';

  const legends = {
    detected: {
      title: 'Detection Status',
      items: [
        { color: '#dc2626', label: 'H5N1 detected' },
        { color: '#d1d5db', label: 'No detections' },
      ],
    },
    detections: {
      title: 'Detection Count',
      gradient: true,
      gradientColors: ['#fbbf24', '#f97316', '#dc2626'],
      gradientLabels: ['Low', 'Medium', 'High'],
      items: [
        { color: '#d1d5db', label: 'No detections' },
      ],
    },
    susceptibility: {
      title: 'Susceptibility Level',
      items: [
        { color: '#dc2626', label: 'High' },
        { color: '#f97316', label: 'Medium' },
        { color: '#22c55e', label: 'Low' },
        { color: '#d1d5db', label: 'Unknown' },
      ],
    },
    genome: {
      title: 'Genome Availability',
      items: [
        { color: '#3b82f6', label: 'Genome available' },
        { color: '#d1d5db', label: 'No genome' },
      ],
    },
  };

  $: currentLegend = legends[colorMode] || legends.detections;
</script>

<div class="phylo-legend bg-white dark:bg-gray-800 rounded-lg shadow p-4">
  <h2 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
    {t('phylo.legend.title.' + colorMode) || currentLegend.title}
  </h2>

  {#if currentLegend.gradient}
    <!-- Gradient bar for proportional coloring -->
    <div class="mb-3">
      <div
        class="h-3 rounded-full"
        style="background: linear-gradient(to right, {currentLegend.gradientColors.join(', ')})"
      ></div>
      <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
        {#each currentLegend.gradientLabels as label, li}
          <span>{t('phylo.grad.' + li) || label}</span>
        {/each}
      </div>
    </div>
  {/if}

  <div class="space-y-2">
    {#each currentLegend.items as item}
      <div class="flex items-center gap-2">
        <span
          class="w-4 h-4 rounded-full flex-shrink-0"
          style="background-color: {item.color}"
        ></span>
        <span class="text-sm text-gray-600 dark:text-gray-400">
          {t('phylo.item.' + colorMode + '.' + item.label) || item.label}
        </span>
      </div>
    {/each}
  </div>

  <!-- Additional info -->
  <div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
    <p class="text-xs text-gray-500 dark:text-gray-400">
      {t('phylo.legend.zoom') || 'Scroll to zoom, drag to pan'}
    </p>
    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
      {t('phylo.legend.collapse') || 'Double-click to collapse/expand clades'}
    </p>
  </div>
</div>
