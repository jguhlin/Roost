<script>
  // Source attribution badge
  let { source = '', count = null, compact = false } = $props();

  // Source display info
  const sourceInfo = {
    'aphis': { name: 'USDA APHIS', color: 'blue' },
    'canada_cwhc': { name: 'Canada CWHC', color: 'red' },
    'uk_defra': { name: 'UK DEFRA', color: 'purple' },
    'ireland_dafm': { name: 'Ireland DAFM', color: 'green' },
    'acap_hpai': { name: 'ACAP', color: 'teal' },
    'empresi': { name: 'FAO EMPRES-i', color: 'orange' },
    'gisaid': { name: 'GISAID', color: 'yellow' },
    'italy_wild': { name: 'Italy IZSVe', color: 'indigo' },
    'iceland_usgs': { name: 'Iceland USGS', color: 'cyan' }
  };

  let info = $derived(sourceInfo[source] || { name: source, color: 'gray' });

  const colorClasses = {
    blue: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    red: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    green: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    purple: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    orange: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    teal: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300',
    indigo: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
    cyan: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
    gray: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  };
</script>

<span class="inline-flex items-center gap-1 rounded-full font-medium {colorClasses[info.color]} {compact ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'}">
  {info.name}
  {#if count !== null}
    <span class="font-normal opacity-75">({count.toLocaleString()})</span>
  {/if}
</span>
