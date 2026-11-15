<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { t } from '../../stores/i18n.svelte.js';

  // Props
  export let colorMode = 'detections'; // 'detections', 'susceptibility', 'genome', 'gene'
  export let searchQuery = '';
  // eslint-disable-next-line svelte/no-unused-export-let
  export let filterGenome = false; // Used in buildStyles() for filtering
  export let filterDetected = false; // Show only species with H5N1 detections
  // Gene overlay (from #/phylogeny?gene=SYM): {tree_name: 'FULL'|'FRAGMENT'|'NOT_FOUND'}
  export let geneStatuses = null;
  // eslint-disable-next-line svelte/no-unused-export-let
  export let filterGeneCalls = false; // keep only species with a call for the overlay gene

  const dispatch = createEventDispatcher();

  let container;
  let tree = null;
  let phyloData = null;
  let loading = true;
  let error = null;
  let PhylocanvasGL = null;
  let speciesCount = { total: 0, shown: 0, withDetections: 0, withGenomes: 0 };

  // Color schemes
  const COLOR_SCHEMES = {
    detections: {
      high: '#dc2626',    // red-600 - many detections
      medium: '#f97316',  // orange-500
      low: '#fbbf24',     // amber-400
      none: '#d1d5db',    // gray-300
    },
    detected: {
      yes: '#dc2626',     // red - has detections
      no: '#d1d5db',      // gray - no detections
    },
    susceptibility: {
      High: '#dc2626',    // red
      Medium: '#f97316',  // orange
      Low: '#22c55e',     // green
      unknown: '#d1d5db', // gray
    },
    genome: {
      available: '#3b82f6', // blue
      unavailable: '#d1d5db', // gray
    }
  };

  // Load Phylocanvas from CDN
  async function loadPhylocanvasFromCDN() {
    return new Promise((resolve, reject) => {
      // Check if already loaded
      if (window.phylocanvas) {
        resolve(window.phylocanvas);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://unpkg.com/@phylocanvas/phylocanvas.gl@1.64.1/dist/bundle.min.js';
      script.onload = () => {
        if (window.phylocanvas) {
          resolve(window.phylocanvas);
        } else {
          reject(new Error(t('phylo.load.error') || 'Phylocanvas failed to load'));
        }
      };
      script.onerror = () => reject(new Error(t('phylo.script.error') || 'Failed to load Phylocanvas script'));
      document.head.appendChild(script);
    });
  }

  // Interpolate between two hex colors
  function interpolateColor(color1, color2, factor) {
    const hex = (c) => parseInt(c, 16);
    const r1 = hex(color1.slice(1, 3)), g1 = hex(color1.slice(3, 5)), b1 = hex(color1.slice(5, 7));
    const r2 = hex(color2.slice(1, 3)), g2 = hex(color2.slice(3, 5)), b2 = hex(color2.slice(5, 7));
    const r = Math.round(r1 + (r2 - r1) * factor);
    const g = Math.round(g1 + (g2 - g1) * factor);
    const b = Math.round(b1 + (b2 - b1) * factor);
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  }

  // Store original newick for filtering
  let originalNewick = null;

  // Counter for internal node IDs
  let internalNodeCounter = 0;

  // Parse Newick string into tree structure with internal node IDs
  function parseNewick(newick, assignInternalIds = false) {
    let i = 0;
    if (assignInternalIds) internalNodeCounter = 0;

    function parseNode() {
      const node = { children: [], name: '', length: 0, isInternal: false };

      if (newick[i] === '(') {
        i++; // skip '('
        node.isInternal = true;
        while (true) {
          const child = parseNode();
          child.parent = node;
          node.children.push(child);
          if (newick[i] === ',') {
            i++; // skip ','
          } else if (newick[i] === ')') {
            i++; // skip ')'
            break;
          }
        }
      }

      // Parse name
      let name = '';
      while (i < newick.length && ![',', ')', ':', ';'].includes(newick[i])) {
        name += newick[i++];
      }
      node.name = name.trim();

      // Assign internal node ID if needed and no name exists
      if (assignInternalIds && node.isInternal && !node.name) {
        node.name = `__internal_${internalNodeCounter++}`;
      }

      // Parse branch length
      if (newick[i] === ':') {
        i++; // skip ':'
        let length = '';
        while (i < newick.length && ![',', ')', ';'].includes(newick[i])) {
          length += newick[i++];
        }
        node.length = parseFloat(length) || 0;
      }

      return node;
    }

    return parseNode();
  }

  // Compute descendant statistics for each node (bottom-up traversal)
  function computeDescendantStats(node, metadata) {
    if (node.children.length === 0) {
      // Leaf node - get stats from metadata
      const meta = metadata[node.name] || {};
      node.stats = {
        totalDescendants: 1,
        withDetections: meta.detection_count > 0 ? 1 : 0,
        withGenomes: meta.has_genome ? 1 : 0,
        totalDetectionCount: meta.detection_count || 0,
        susceptibilitySum: meta.susceptibility === 'High' ? 1 : (meta.susceptibility === 'Medium' ? 0.5 : 0),
      };
    } else {
      // Internal node - aggregate children's stats
      let totalDescendants = 0;
      let withDetections = 0;
      let withGenomes = 0;
      let totalDetectionCount = 0;
      let susceptibilitySum = 0;

      for (const child of node.children) {
        computeDescendantStats(child, metadata);
        totalDescendants += child.stats.totalDescendants;
        withDetections += child.stats.withDetections;
        withGenomes += child.stats.withGenomes;
        totalDetectionCount += child.stats.totalDetectionCount;
        susceptibilitySum += child.stats.susceptibilitySum;
      }

      node.stats = {
        totalDescendants,
        withDetections,
        withGenomes,
        totalDetectionCount,
        susceptibilitySum,
      };
    }

    // Compute proportions
    node.stats.detectionProportion = node.stats.withDetections / node.stats.totalDescendants;
    node.stats.genomeProportion = node.stats.withGenomes / node.stats.totalDescendants;
    node.stats.susceptibilityAvg = node.stats.susceptibilitySum / node.stats.totalDescendants;
  }

  // Get all nodes in tree (for iteration)
  function getAllNodes(node, nodes = []) {
    nodes.push(node);
    for (const child of node.children) {
      getAllNodes(child, nodes);
    }
    return nodes;
  }

  // Filter tree to only include species matching predicate
  function filterTree(node, shouldKeep) {
    if (node.children.length === 0) {
      // Leaf node - keep if predicate matches
      return shouldKeep(node.name) ? { ...node, children: [] } : null;
    }

    // Internal node - recursively filter children
    const filteredChildren = node.children
      .map(child => filterTree(child, shouldKeep))
      .filter(child => child !== null);

    if (filteredChildren.length === 0) {
      return null; // No descendants match
    }

    if (filteredChildren.length === 1) {
      // Collapse single-child nodes (combine branch lengths)
      const child = filteredChildren[0];
      return {
        ...child,
        length: (node.length || 0) + (child.length || 0)
      };
    }

    return { ...node, children: filteredChildren };
  }

  // Convert tree back to Newick string
  function toNewick(node) {
    if (node.children.length === 0) {
      return node.name + (node.length ? ':' + node.length : '');
    }

    const childStr = node.children.map(toNewick).join(',');
    const nameStr = node.name || '';
    const lengthStr = node.length ? ':' + node.length : '';
    return '(' + childStr + ')' + nameStr + lengthStr;
  }

  // Get Newick string for the current tree (with internal IDs)
  function getTreeNewick() {
    if (!currentTreeRoot) {
      prepareTree();
    }
    if (!currentTreeRoot) {
      return originalNewick;
    }
    return toNewick(currentTreeRoot) + ';';
  }

  // Update species count statistics
  function updateSpeciesCount() {
    if (!phyloData?.metadata) {
      speciesCount = { total: 0, shown: 0, withDetections: 0, withGenomes: 0 };
      return;
    }

    const meta = phyloData.metadata;
    const total = Object.keys(meta).length;
    let withDetections = 0;
    let withGenomes = 0;
    let shown = 0;

    for (const m of Object.values(meta)) {
      if (m.detection_count > 0) withDetections++;
      if (m.has_genome) withGenomes++;
      if ((!filterGenome || m.has_genome) && (!filterDetected || m.detection_count > 0)) shown++;
    }

    speciesCount = { total, shown, withDetections, withGenomes };
  }

  // Get max detection count for proportional scaling
  function getMaxDetections() {
    if (!phyloData?.metadata) return 1;
    let max = 1;
    for (const meta of Object.values(phyloData.metadata)) {
      if (meta.detection_count > max) max = meta.detection_count;
    }
    return max;
  }

  // Get color for a species based on current mode
  // Neutral branch color used when the detected-only filter makes red meaningless
  const NEUTRAL_BRANCH = '#94a3b8'; // slate-400

  function getNodeColor(speciesName) {
    if (!phyloData?.metadata) return '#d1d5db';

    const meta = phyloData.metadata[speciesName];
    if (!meta) return '#d1d5db';

    // When showing only detected species, detection-based red carries no
    // information (everything would be red) — use neutral lines instead.
    if (filterDetected && (colorMode === 'detected' || colorMode === 'detections')) {
      return NEUTRAL_BRANCH;
    }

    switch (colorMode) {
      case 'detections': {
        const count = meta.detection_count || 0;
        if (count === 0) return COLOR_SCHEMES.detections.none;
        // Proportional color: use log scale for better distribution
        const maxCount = getMaxDetections();
        const factor = Math.log10(count + 1) / Math.log10(maxCount + 1);
        // Gradient from yellow (low) -> orange (mid) -> red (high)
        if (factor < 0.5) {
          return interpolateColor('#fbbf24', '#f97316', factor * 2);
        } else {
          return interpolateColor('#f97316', '#dc2626', (factor - 0.5) * 2);
        }
      }
      case 'detected': {
        // Simple binary: has any detections or not
        const count = meta.detection_count || 0;
        return count > 0 ? COLOR_SCHEMES.detected.yes : COLOR_SCHEMES.detected.no;
      }
      case 'susceptibility': {
        const level = meta.susceptibility || 'unknown';
        return COLOR_SCHEMES.susceptibility[level] || COLOR_SCHEMES.susceptibility.unknown;
      }
      case 'genome': {
        return meta.has_genome
          ? COLOR_SCHEMES.genome.available
          : COLOR_SCHEMES.genome.unavailable;
      }
      case 'gene': {
        const st = geneStatuses?.[speciesName];
        if (st === 'FULL') return '#16a34a';      // green-600 — present
        if (st === 'FRAGMENT') return '#f59e0b';  // amber-500 — partial
        if (st === 'NOT_FOUND_HI') return '#b91c1c'; // red-700 — absence, high confidence
        if (st === 'NOT_FOUND') return '#fca5a5';   // red-300 — not found, low/medium confidence
        return '#d1d5db';                          // gray-300 — not searched
      }
      default:
        return '#d1d5db';
    }
  }

  // Store the current tree being displayed (with stats)
  let currentTreeRoot = null;

  // Prepare tree for display - parse, optionally filter, compute stats, assign IDs
  function prepareTree() {
    if (!originalNewick || !phyloData?.metadata) return null;

    // Parse with internal node IDs
    internalNodeCounter = 0;
    let treeRoot = parseNewick(originalNewick, true);

    // Filter if needed
    if (filterGenome || filterDetected || (filterGeneCalls && geneStatuses)) {
      treeRoot = filterTree(treeRoot, (name) => {
        const meta = phyloData.metadata[name];
        if (!meta) return false;
        if (filterGeneCalls && geneStatuses && !geneStatuses[name]) return false;
        if (filterGenome && !meta.has_genome) return false;
        if (filterDetected && !(meta.detection_count > 0)) return false;
        return true;
      });

      if (!treeRoot) {
        console.warn('[PhyloTree] Filter removed all species');
        internalNodeCounter = 0;
        treeRoot = parseNewick(originalNewick, true);
      }

      // Re-assign internal IDs after filtering (since tree structure changed)
      internalNodeCounter = 0;
      reassignInternalIds(treeRoot);
    }

    // Compute descendant statistics
    computeDescendantStats(treeRoot, phyloData.metadata);

    currentTreeRoot = treeRoot;
    return treeRoot;
  }

  // Reassign internal IDs to a tree (after filtering)
  function reassignInternalIds(node) {
    if (node.isInternal) {
      node.name = `__internal_${internalNodeCounter++}`;
    }
    for (const child of node.children) {
      reassignInternalIds(child);
    }
  }

  // Get color for an internal node based on descendant statistics
  function getInternalNodeColor(stats) {
    switch (colorMode) {
      case 'detections': {
        // Color based on average detection count per descendant
        if (stats.totalDetectionCount === 0) return COLOR_SCHEMES.detections.none;
        const maxCount = getMaxDetections();
        const avgCount = stats.totalDetectionCount / stats.totalDescendants;
        const factor = Math.log10(avgCount + 1) / Math.log10(maxCount + 1);
        if (factor < 0.5) {
          return interpolateColor('#fbbf24', '#f97316', factor * 2);
        } else {
          return interpolateColor('#f97316', '#dc2626', (factor - 0.5) * 2);
        }
      }
      case 'detected': {
        // Color based on proportion of descendants with detections
        const proportion = stats.detectionProportion;
        if (proportion === 0) return COLOR_SCHEMES.detected.no;
        // Gradient from gray (0%) to red (100%)
        return interpolateColor('#d1d5db', '#dc2626', proportion);
      }
      case 'susceptibility': {
        // Color based on average susceptibility
        const avg = stats.susceptibilityAvg;
        if (avg >= 0.7) return COLOR_SCHEMES.susceptibility.High;
        if (avg >= 0.35) return COLOR_SCHEMES.susceptibility.Medium;
        if (avg > 0) return COLOR_SCHEMES.susceptibility.Low;
        return COLOR_SCHEMES.susceptibility.unknown;
      }
      case 'genome': {
        // Color based on proportion of descendants with genomes
        const proportion = stats.genomeProportion;
        if (proportion === 0) return COLOR_SCHEMES.genome.unavailable;
        // Gradient from gray (0%) to blue (100%)
        return interpolateColor('#d1d5db', '#3b82f6', proportion);
      }
      default:
        return '#d1d5db';
    }
  }

  // Build styles object for leaf nodes only
  // (Internal node styles are applied separately via applyInternalNodeStyles)
  function buildStyles() {
    if (!phyloData?.metadata) return {};

    const styles = {};

    // Build styles for leaf nodes (keyed by species name)
    for (const [name, meta] of Object.entries(phyloData.metadata)) {
      if (filterGenome && !meta.has_genome) continue;
      const color = getNodeColor(name);
      const hasDetections = meta.detection_count > 0;
      styles[name] = {
        fillColour: color,
        strokeColour: color,
      };
    }

    console.log('[PhyloTree] Built leaf styles for', Object.keys(styles).length, 'species');
    return styles;
  }

  // Apply colors to tree nodes
  function applyColors() {
    if (!tree || !phyloData) return;

    try {
      const styles = buildStyles();
      tree.setProps({ styles });
      // Also apply internal node styles
      applyInternalNodeStyles();
    } catch (e) {
      console.warn('Failed to apply colors:', e);
    }
  }

  // Apply styles to internal nodes using Phylocanvas's actual tree structure
  function applyInternalNodeStyles() {
    if (!tree || !phyloData?.metadata) return;

    try {
      // Get the graph structure from Phylocanvas
      const graph = tree.getGraphAfterLayout?.();
      if (!graph || !graph.root) {
        console.warn('[PhyloTree] Could not get graph structure');
        return;
      }

      // Start with existing leaf styles
      const styles = { ...tree.props?.styles } || {};
      const maxDetections = getMaxDetections();
      let internalStyleCount = 0;

      // Compute stats and style for a node recursively (bottom-up)
      function computeAndStyle(node, visited = new Set()) {
        if (!node || visited.has(node.id)) {
          return { total: 0, detected: 0, genomes: 0, detectionSum: 0 };
        }
        visited.add(node.id);

        if (node.isLeaf) {
          // Leaf node - get stats from metadata
          // Note: For leaves, node.id equals species name (e.g., "Anas_platyrhynchos")
          const meta = phyloData.metadata[node.id] || {};
          return {
            total: 1,
            detected: meta.detection_count > 0 ? 1 : 0,
            genomes: meta.has_genome ? 1 : 0,
            detectionSum: meta.detection_count || 0,
          };
        }

        // Internal node - aggregate children's stats
        let stats = { total: 0, detected: 0, genomes: 0, detectionSum: 0 };
        if (node.children) {
          for (const child of node.children) {
            const childStats = computeAndStyle(child, visited);
            stats.total += childStats.total;
            stats.detected += childStats.detected;
            stats.genomes += childStats.genomes;
            stats.detectionSum += childStats.detectionSum;
          }
        }

        // Compute color for internal node based on aggregated stats
        if (stats.total > 0 && node.id) {
          let color = '#d1d5db';

          // Detected-only filter: detection-based red is meaningless (all
          // visible branches have detections) — neutral lines instead.
          if (filterDetected && (colorMode === 'detected' || colorMode === 'detections')) {
            color = NEUTRAL_BRANCH;
          } else switch (colorMode) {
            case 'detected': {
              const proportion = stats.detected / stats.total;
              if (proportion > 0) {
                color = interpolateColor('#d1d5db', '#dc2626', proportion);
              }
              break;
            }
            case 'detections': {
              if (stats.detectionSum > 0) {
                const avgCount = stats.detectionSum / stats.total;
                const factor = Math.log10(avgCount + 1) / Math.log10(maxDetections + 1);
                if (factor < 0.5) {
                  color = interpolateColor('#fbbf24', '#f97316', factor * 2);
                } else {
                  color = interpolateColor('#f97316', '#dc2626', (factor - 0.5) * 2);
                }
              }
              break;
            }
            case 'genome': {
              const proportion = stats.genomes / stats.total;
              if (proportion > 0) {
                color = interpolateColor('#d1d5db', '#3b82f6', proportion);
              }
              break;
            }
            case 'susceptibility': {
              // For susceptibility we'd need to track that too - use detected as proxy for now
              const proportion = stats.detected / stats.total;
              if (proportion >= 0.7) color = '#dc2626';
              else if (proportion >= 0.35) color = '#f97316';
              else if (proportion > 0) color = '#22c55e';
              break;
            }
          }

          // Key the style by Phylocanvas's internal ID (e.g., "__0", "__1")
          styles[node.id] = {
            fillColour: color,
            strokeColour: color,
          };
          internalStyleCount++;
        }

        return stats;
      }

      // Start traversal from root
      computeAndStyle(graph.root);
      console.log('[PhyloTree] Applied internal node styles:', internalStyleCount);

      // Update tree with combined styles
      tree.setProps({ styles });
    } catch (e) {
      console.warn('[PhyloTree] Failed to apply internal node styles:', e);
    }
  }

  // Search and highlight species
  function searchTree(query) {
    if (!tree || !query || !phyloData) return;

    const normalizedQuery = query.toLowerCase();

    // Find matching species
    const matches = [];
    for (const [name, meta] of Object.entries(phyloData.metadata)) {
      const scientificName = name.replace(/_/g, ' ').toLowerCase();
      const commonName = (meta.common_name || '').toLowerCase();

      if (scientificName.includes(normalizedQuery) || commonName.includes(normalizedQuery)) {
        matches.push(name);
      }
    }

    if (matches.length > 0) {
      // Highlight the first match
      try {
        tree.selectNode(matches[0]);
      } catch (e) {
        console.warn('selectNode failed:', e);
      }

      // Notify parent of matches
      dispatch('searchResults', { matches, query });
    } else {
      dispatch('searchResults', { matches: [], query });
    }
  }

  // Initialize the tree
  async function initTree() {
    loading = true;
    error = null;

    try {
      // Fetch phylogeny data
      const response = await fetch('data/phylogeny.json');
      if (!response.ok) throw new Error(`Failed to load phylogeny data: ${response.status}`);

      phyloData = await response.json();
      originalNewick = phyloData.newick;
      updateSpeciesCount();
      console.log('[PhyloTree] Loaded data with', Object.keys(phyloData.metadata).length, 'species');

      // Load Phylocanvas from CDN
      PhylocanvasGL = await loadPhylocanvasFromCDN();
      console.log('[PhyloTree] Phylocanvas loaded from CDN');

      // Get container dimensions
      const rect = container.getBoundingClientRect();

      // Prepare tree structure with internal IDs and stats
      prepareTree();

      // Build styles (includes internal node colors)
      const styles = buildStyles();

      // Get newick with internal node IDs
      const newickSource = getTreeNewick();
      console.log('[PhyloTree] Newick sample (first 500 chars):', newickSource?.substring(0, 500));
      console.log('[PhyloTree] Has __internal_ nodes:', newickSource?.includes('__internal_'));

      tree = new PhylocanvasGL.default(container, {
        source: newickSource,
        type: 'cr', // circular layout
        interactive: true,
        padding: 48,
        showLabels: true,
        showLeafLabels: true,
        alignLabels: false, // better for circular
        nodeSize: 4,
        lineWidth: 1.5,
        fontFamily: 'ui-monospace, monospace',
        fontSize: 8, // base font size, will scale with zoom
        highlightColour: '#2563eb',
        strokeColour: '#9ca3af',
        fillColour: '#d1d5db',
        haloWidth: 3,
        haloColour: 'rgba(37, 99, 235, 0.3)',
        styleNodeEdges: true, // color branches based on node styles
        styles,
        size: {
          width: rect.width || 800,
          height: rect.height || 600,
        },
      });

      // Expose tree to window for debugging/testing
      window.phyloTree = tree;

      // Set up zoom-based font scaling
      const updateFontSize = () => {
        if (!tree) return;
        try {
          // Get both zoom types
          const branchZoom = tree.getBranchZoom?.() || 0;
          const viewZoom = tree.getZoom?.() || 0;

          // Use whichever zoom is larger to determine font size
          // branchZoom: starts at 0, goes up as user zooms
          // viewZoom: starts at 0, can go from -6 to +8

          // For branchZoom: scale aggressively
          // At branchZoom 1 -> 10px, at branchZoom 5 -> 28px, at branchZoom 10 -> 48px
          const branchBasedSize = 8 + branchZoom * 4;

          // For viewZoom: convert deck.gl zoom level to font size
          // viewZoom of 0 is default, each level is 2x magnification
          // viewZoom 0 -> 8px, viewZoom 2 -> 16px, viewZoom 4 -> 32px, viewZoom 6 -> 64px
          const viewBasedSize = 8 * Math.pow(1.4, Math.max(0, viewZoom));

          // Use the larger of the two
          const scaledSize = Math.min(72, Math.max(8, Math.max(branchBasedSize, viewBasedSize)));
          tree.setProps({ fontSize: scaledSize });
        } catch (e) {
          // ignore
        }
      };

      // Poll for zoom changes more frequently
      const zoomInterval = setInterval(updateFontSize, 200);

      // Store interval for cleanup
      tree._zoomInterval = zoomInterval;

      // Wait for render
      await new Promise(resolve => setTimeout(resolve, 300));

      // Apply internal node styles using Phylocanvas's actual node IDs
      try {
        applyInternalNodeStyles();
      } catch (e) {
        console.warn('[PhyloTree] Internal node styling failed:', e);
      }

      loading = false;
      console.log('[PhyloTree] Initialized successfully');
    } catch (e) {
      console.error('[PhyloTree] Initialization failed:', e);
      error = e.message;
      loading = false;
    }
  }

  // Handle resize
  function handleResize() {
    if (!tree || !container) return;

    const rect = container.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      try {
        tree.resize(rect.width, rect.height);
      } catch (e) {
        console.warn('Resize failed:', e);
      }
    }
  }

  // Reload tree with new source (for filtering)
  async function reloadTree() {
    if (!tree || !PhylocanvasGL || !container) {
      return;
    }

    // Re-prepare the tree (handles filtering and stats)
    currentTreeRoot = null; // Force re-preparation
    prepareTree();
    updateSpeciesCount();

    const newickSource = getTreeNewick();
    const styles = buildStyles();

    // Destroy old tree
    if (tree._zoomInterval) {
      clearInterval(tree._zoomInterval);
    }
    try {
      tree.destroy?.();
    } catch (e) {
      // ignore
    }

    // Create new tree
    const rect = container.getBoundingClientRect();
    console.log('[PhyloTree] Creating new tree with dimensions:', rect.width, 'x', rect.height);
    tree = new PhylocanvasGL.default(container, {
      source: newickSource,
      type: 'cr',
      interactive: true,
      padding: 48,
      showLabels: true,
      showLeafLabels: true,
      alignLabels: false,
      nodeSize: 4,
      lineWidth: 1.5,
      fontFamily: 'ui-monospace, monospace',
      fontSize: 8,
      highlightColour: '#2563eb',
      strokeColour: '#9ca3af',
      fillColour: '#d1d5db',
      haloWidth: 3,
      haloColour: 'rgba(37, 99, 235, 0.3)',
      styleNodeEdges: true,
      styles,
      size: {
        width: rect.width || 800,
        height: rect.height || 600,
      },
    });

    // Expose tree to window for debugging/testing
    window.phyloTree = tree;

    // Re-setup zoom font scaling
    const updateFontSize = () => {
      if (!tree) return;
      try {
        const branchZoom = tree.getBranchZoom?.() || 0;
        const viewZoom = tree.getZoom?.() || 0;
        const branchBasedSize = 8 + branchZoom * 4;
        const viewBasedSize = 8 * Math.pow(1.4, Math.max(0, viewZoom));
        const scaledSize = Math.min(72, Math.max(8, Math.max(branchBasedSize, viewBasedSize)));
        tree.setProps({ fontSize: scaledSize });
      } catch (e) {
        // ignore
      }
    };
    tree._zoomInterval = setInterval(updateFontSize, 200);

    // Apply internal node styles after tree is ready
    await new Promise(resolve => setTimeout(resolve, 300));
    try {
      applyInternalNodeStyles();
    } catch (e) {
      console.warn('[PhyloTree] Internal node styling failed on reload:', e);
    }
  }

  // Track previous filter state for reload
  let prevFilterGenome = filterGenome;
  let prevFilterDetected = filterDetected;
  let prevFilterGeneCalls = filterGeneCalls;
  let prevGeneStatusesReady = false;

  // Watch filter changes and reload tree
  $: if (tree && filterGenome !== prevFilterGenome) {
    prevFilterGenome = filterGenome;
    reloadTree();
  }
  $: if (tree && filterDetected !== prevFilterDetected) {
    prevFilterDetected = filterDetected;
    reloadTree();
  }
  $: if (tree && filterGeneCalls !== prevFilterGeneCalls) {
    prevFilterGeneCalls = filterGeneCalls;
    reloadTree();
  }
  // statuses arrive async (lazy 48MB fetch) — load once ready
  $: if (tree && geneStatuses && !prevGeneStatusesReady) {
    prevGeneStatusesReady = true;
    reloadTree();
  }

  // Watch colorMode changes and apply colors
  $: if (tree && colorMode) {
    // Re-prepare to recompute stats for current color mode
    currentTreeRoot = null;
    prepareTree();
    applyColors();
  }

  $: if (tree && searchQuery) {
    searchTree(searchQuery);
  }

  // Export methods for parent
  export function zoomIn() {
    if (!tree) return;
    try {
      const currentZoom = tree.getBranchZoom?.() || 1;
      tree.setBranchZoom?.(currentZoom * 1.2);
    } catch (e) {
      console.warn('zoomIn failed:', e);
    }
  }

  export function zoomOut() {
    if (!tree) return;
    try {
      const currentZoom = tree.getBranchZoom?.() || 1;
      tree.setBranchZoom?.(currentZoom * 0.8);
    } catch (e) {
      console.warn('zoomOut failed:', e);
    }
  }

  export function resetView() {
    try {
      tree?.fitInPanel?.();
    } catch (e) {
      console.warn('resetView failed:', e);
    }
  }

  export function collapseAll() {
    console.log('Collapse all not yet implemented');
  }

  export function expandAll() {
    try {
      tree?.resetCollapsedNodes?.();
    } catch (e) {
      console.warn('expandAll failed:', e);
    }
  }

  export function exportNewick() {
    try {
      return tree?.exportNewick?.() || phyloData?.newick;
    } catch (e) {
      return phyloData?.newick;
    }
  }

  onMount(() => {
    initTree();
    window.addEventListener('resize', handleResize);
  });

  onDestroy(() => {
    window.removeEventListener('resize', handleResize);
    if (tree) {
      // Clear zoom polling interval
      if (tree._zoomInterval) {
        clearInterval(tree._zoomInterval);
      }
      try {
        tree.destroy?.();
      } catch (e) {
        // Ignore cleanup errors
      }
      tree = null;
    }
  });
</script>

<div class="phylo-tree-container relative w-full h-full min-h-[500px]">
  {#if loading}
    <div class="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-800/50 z-10">
      <div class="text-center">
        <svg class="animate-spin h-8 w-8 text-blue-600 dark:text-blue-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="text-gray-600 dark:text-gray-300">{t('phylotree.loading.phylogenetic.tree')}</p>
        {#if phyloData}
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {t('phylogeny.count.species', { n: phyloData.stats?.total_species?.toLocaleString() || Object.keys(phyloData.metadata || {}).length })}
          </p>
        {/if}
      </div>
    </div>
  {/if}

  {#if error}
    <div class="absolute inset-0 flex items-center justify-center bg-red-50 dark:bg-red-900/20 z-10">
      <div class="text-center p-4 max-w-md">
        <svg class="h-10 w-10 text-red-600 dark:text-red-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p class="text-red-700 dark:text-red-300 font-medium">{t('phylotree.failed.to.load.tree')}</p>
        <p class="text-red-600 dark:text-red-400 text-sm mt-1 break-words">{error}</p>
        <button
          onclick={() => initTree()}
          class="mt-3 px-4 py-2 bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-700"
        >
          {t('phylogeny.retry')}
        </button>
      </div>
    </div>
  {/if}

  <div
    bind:this={container}
    class="w-full h-full phylo-canvas-wrapper"
    class:opacity-0={loading || error}
  ></div>

  <!-- Species count overlay -->
  {#if !loading && !error && speciesCount.total > 0}
    <div class="absolute bottom-3 left-3 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md text-xs font-mono z-10">
      <div class="text-gray-900 dark:text-gray-100 font-semibold">
        {t('phylogeny.count.species', { n: speciesCount.shown.toLocaleString() })}
        {#if filterGenome && speciesCount.shown !== speciesCount.total}
          <span class="text-gray-500 dark:text-gray-400 font-normal">/ {speciesCount.total.toLocaleString()}</span>
        {/if}
      </div>
      <div class="text-gray-600 dark:text-gray-400 mt-0.5">
        <span class="text-red-600 dark:text-red-400">{speciesCount.withDetections}</span> {t('phylogeny.overlay.detected')} |
        <span class="text-blue-600 dark:text-blue-400">{speciesCount.withGenomes.toLocaleString()}</span> {t('phylogeny.overlay.genomes')}
      </div>
    </div>
  {/if}
</div>

<style>
  .phylo-canvas-wrapper {
    transition: opacity 0.3s ease;
  }

  .phylo-tree-container :global(canvas) {
    width: 100% !important;
    height: 100% !important;
    display: block;
  }
</style>
