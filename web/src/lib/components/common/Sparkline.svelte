<script>
  // Simple SVG sparkline component
  let { data = [], width = 100, height = 30, color = '#3b82f6', fill = true } = $props();

  // Normalize data to handle BigInt from DuckDB
  function normalizeData(arr) {
    if (!arr || arr.length === 0) return [];
    return arr.map(v => typeof v === 'bigint' ? Number(v) : Number(v) || 0);
  }

  // Calculate path
  function getPath() {
    const normalized = normalizeData(data);
    if (normalized.length < 2) return '';

    const max = Math.max(...normalized);
    const min = Math.min(...normalized);
    const range = max - min || 1;

    const xStep = width / (normalized.length - 1);

    const points = normalized.map((value, i) => {
      const x = i * xStep;
      const y = height - ((value - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    });

    return `M ${points.join(' L ')}`;
  }

  function getFillPath() {
    const normalized = normalizeData(data);
    if (normalized.length < 2) return '';

    const max = Math.max(...normalized);
    const min = Math.min(...normalized);
    const range = max - min || 1;

    const xStep = width / (normalized.length - 1);

    const points = normalized.map((value, i) => {
      const x = i * xStep;
      const y = height - ((value - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    });

    // Close the path for fill
    return `M 0,${height} L ${points.join(' L ')} L ${width},${height} Z`;
  }
</script>

<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" {height} class="inline-block w-full">
  {#if fill}
    <path d={getFillPath()} fill={color} fill-opacity="0.2" />
  {/if}
  <path d={getPath()} fill="none" stroke={color} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>
