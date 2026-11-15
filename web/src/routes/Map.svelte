<script>
  import { t } from '../lib/stores/i18n.svelte.js';
  import { onMount, onDestroy } from 'svelte';
  // Performance: maplibre-gl (~7MB) dynamically imported on mount
  let maplibregl = null;
  import { db, dbStore } from '../lib/stores/db.js';
  import { navigate, getRoute, updateParams } from '../lib/stores/router.js';
  import { trackEvent } from '../lib/analytics.js';
  import { formatNumber, formatDate } from '../lib/utils/format.js';

  let mapContainer = $state(null);
  let map = $state(null);
  let mapReady = false;          // MapLibre 'load' fired (WebGL-dependent)
  let pendingDetections = null;  // geojson stash until the map is ready
  // Optional CARTO key (web/.env → VITE_CARTO_API_KEY). Unset = keyless
  // public tiles, which still work — the key just lifts rate limits.
  const CARTO_API_KEY = import.meta.env.VITE_CARTO_API_KEY || '';
  // Basemap: OpenStreetMap raster (keyless). CARTO's free basemaps now
  // REQUIRE a valid API key — the one in web/.env is rejected (CARTO serves
  // an "API KEY REQUIRED" error tile with HTTP 200, so status checks are
  // misleading). To restore CARTO's nicer tiles: get a key at
  // https://carto.com/basemaps/apikey, set VITE_CARTO_API_KEY, and swap the
  // tile URL back to https://{sub}.basemaps.cartocdn.com/light_all/...
  const osmTile = (sub) => `https://${sub}.tile.openstreetmap.org/{z}/{x}/{y}.png`;
  let loading = $state(true);
  let stats = $state({ points: 0, countries: 0 });
  let loadError = $state(null);
  let speciesFilter = $state('');
  let suppressCameraSync = false;   // one-shot: skip the moveend after jumpTo
  let cameraSyncTimer = null;

  // --- URL state: ?species=… (detection filter) and the map camera
  // (?lat=&lng=&z=) so a shared link opens the same view. Camera values
  // are rounded (lat/lng 3dp, zoom 1dp) so URL writes converge instead of
  // echoing on every moveend.
  const cameraFromParams = (p = {}) => {
    const lat = Number(p.lat), lng = Number(p.lng), z = Number(p.z);
    return {
      center: (isFinite(lat) && isFinite(lng) && lat >= -85 && lat <= 85 && lng >= -180 && lng <= 180)
        ? [lng, lat] : null,
      zoom: (isFinite(z) && z >= 1 && z <= 18) ? z : null,
    };
  };

  onMount(async () => {
    const p0 = getRoute()?.params || {};
    speciesFilter = p0.species || '';
    const cam0 = cameraFromParams(p0);

    // Dynamically import maplibre-gl (code-split from main bundle)
    maplibregl = await import('maplibre-gl');

    // Initialize map
    map = new maplibregl.Map({
      container: mapContainer,
      style: {
        version: 8,
        sources: {
          'osm-light': {
            type: 'raster',
            tiles: ['a', 'b', 'c'].map(osmTile),
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          }
        },
        layers: [
          {
            id: 'osm-light-layer',
            type: 'raster',
            source: 'osm-light',
            minzoom: 0,
            maxzoom: 19
          }
        ]
      },
      center: cam0.center || [172.8, -41.5],  // default: Aotearoa NZ centre,
      zoom: cam0.zoom || 2                       // world view (not zoomed in)
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    window.addEventListener('hashchange', onHashChange);
    // Dev/test introspection (same convention as window.__cy / window.__db)
    if (typeof window !== 'undefined') window.__map = map;

    // Camera → URL (debounced; one-shot suppression for programmatic jumps)
    map.on('moveend', () => {
      if (suppressCameraSync) { suppressCameraSync = false; return; }
      clearTimeout(cameraSyncTimer);
      cameraSyncTimer = setTimeout(() => {
        if (!map) return;
        const c = map.getCenter(), z = map.getZoom();
        updateParams({
          lat: c.lat.toFixed(3),
          lng: c.lng.toFixed(3),
          z: z.toFixed(1),
        });
      }, 600);
    });

    map.on('load', async () => {
      mapReady = true;
      if (pendingDetections) {
        setDetections(pendingDetections);
        pendingDetections = null;
      }
      registerPointLayers();
      loading = false;
    });

    // Data loads independently of map readiness: the stats line and any
    // WebGL-less fallback must not depend on the map's load event (host
    // chromium lost WebGL once — the counts froze at 0; lesson 2026-11).
    loadLayers().catch(e => console.warn('[map] loadLayers failed:', e));
  });

  onDestroy(() => {
    window.removeEventListener('hashchange', onHashChange);
    if (map) {
      try {
        map.remove();
      } catch {
        // maplibre remove() can throw during teardown races (container already
        // detached / style still loading) — an exception here would escape the
        // route boundary and kill the whole SPA for every later route.
      }
      map = null;
    }
  });

  async function loadLayers() {
    // Phase 4: detection points come from the DuckDB parquet (LEFT JOIN
    // species for common names). The static geojson layers are download
    // artifacts only — nothing fetches them at runtime anymore.
    await dbStore.loadDetections();
    await dbStore.loadSpecies();
    await refresh();
  }

  async function refresh() {
    const points = await queryDetections(speciesFilter);
    setDetections(points);
    // Stats first: never let map-layer registration (WebGL-dependent)
    // abort the data path — the count line must render headless too.
    stats.points = points.features.length;
    stats.countries = new Set(
      points.features.map(f => f.properties.country).filter(Boolean)
    ).size;
    registerPointLayers();
  }

  async function queryDetections(filter) {
    let sql = `
      SELECT d.scientific_name, s.common_name, d.date_detected, d.country,
             d.state, d.strain, d.source, d.latitude, d.longitude
      FROM detections d
      LEFT JOIN species s ON d.scientific_name = s.scientific_name
      WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL`;
    const f = (filter || '').trim();
    if (f) {
      const esc = f.replace(/'/g, "''");
      sql += /^\d+$/.test(f)
        ? ` AND d.taxon_id = ${f}`
        : ` AND d.scientific_name = '${esc}'`;
    }
    const rows = await db.query(sql);
    return {
      type: 'FeatureCollection',
      features: rows.map(r => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [Number(r.longitude), Number(r.latitude)],
        },
        properties: {
          scientific_name: r.scientific_name || '',
          common_name: r.common_name || '',
          date: r.date_detected == null ? '' : String(r.date_detected),
          country: r.country || '',
          state: r.state || '',
          strain: r.strain || '',
          source: r.source || '',
        },
      })),
    };
  }

  function setDetections(fc) {
    if (!map || !mapReady) {
      // map not initialised (or WebGL unavailable): stash for the load
      // event; stats/tables still update below.
      pendingDetections = fc;
      return;
    }
    const src = map.getSource('detections');
    if (src) {
      src.setData(fc);
    } else {
      map.addSource('detections', {
        type: 'geojson',
        data: fc,
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50
      });
    }
    // source now exists — safe to attach the point layers (idempotent)
    registerPointLayers();
  }

  async function clearSpeciesFilter() {
    speciesFilter = '';
    await refresh();
  }

  // SPA deep links (#/map?species=…&lat=&lng=&z=): hash-only navigations
  // don't re-mount the component, so react to route changes explicitly.
  // Guarded by rounded-value comparison so camera echoes converge.
  async function onHashChange() {
    const p = getRoute()?.params || {};
    const f = p.species || '';
    if (f !== speciesFilter) {
      speciesFilter = f;
      if (f) trackEvent('Map', 'filter-species', decodeURIComponent(f));
      if (map) await refresh();
    }
    const cam = cameraFromParams(p);
    if (map && (cam.center || cam.zoom)) {
      const c = map.getCenter(), z = map.getZoom();
      const same = cam.center
        ? Math.abs(c.lng - cam.center[0]) < 5e-4 && Math.abs(c.lat - cam.center[1]) < 5e-4 &&
          (!cam.zoom || Math.abs(z - cam.zoom) < 0.05)
        : cam.zoom !== null && Math.abs(z - cam.zoom) < 0.05;
      if (!same) {
        suppressCameraSync = true;              // consumed by the moveend below
        setTimeout(() => { suppressCameraSync = false; }, 800);  // backup
        map.jumpTo({ center: cam.center || [c.lng, c.lat], zoom: cam.zoom ?? z });
      }
    }
  }

  let layersRegistered = false;
  function registerPointLayers() {
    if (layersRegistered) return;
    if (!map || !mapReady) return;   // deferred to the map 'load' event
    if (!map.getSource('detections')) return; // data not loaded yet —
    // retried from setDetections once the source exists (registering
    // layers against a missing source throws and would strand the flag)
    layersRegistered = true;

    // Cluster circles
    map.addLayer({
      id: 'clusters',
      type: 'circle',
      source: 'detections',
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': [
          'step',
          ['get', 'point_count'],
          '#fca5a5',  // < 10: light red
          10, '#f87171',  // 10-100: red
          100, '#ef4444',  // 100-1000: darker red
          1000, '#dc2626'  // 1000+: darkest red
        ],
        'circle-radius': [
          'step',
          ['get', 'point_count'],
          15,    // < 10
          10, 20,  // 10-100
          100, 25,  // 100-1000
          1000, 35  // 1000+
        ],
        'circle-stroke-width': 2,
        'circle-stroke-color': '#fff'
      }
    });

    // Cluster count labels
    map.addLayer({
      id: 'cluster-count',
      type: 'symbol',
      source: 'detections',
      filter: ['has', 'point_count'],
      layout: {
        'text-field': '{point_count_abbreviated}',
        'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
        'text-size': 12
      },
      paint: {
        'text-color': '#ffffff'
      }
    });

    // Individual points
    map.addLayer({
      id: 'unclustered-point',
      type: 'circle',
      source: 'detections',
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': '#ef4444',
        'circle-radius': 6,
        'circle-stroke-width': 1,
        'circle-stroke-color': '#fff'
      }
    });

    // Click on cluster to zoom
    map.on('click', 'clusters', async (e) => {
      const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
      const clusterId = features[0].properties.cluster_id;
      const zoom = await map.getSource('detections').getClusterExpansionZoom(clusterId);
      map.easeTo({
        center: features[0].geometry.coordinates,
        zoom: zoom
      });
    });

    // Click on point to show popup
    map.on('click', 'unclustered-point', (e) => {
      const props = e.features[0].properties;
      const coords = e.features[0].geometry.coordinates.slice();

      // Ensure coords are correct for popup
      while (Math.abs(e.lngLat.lng - coords[0]) > 180) {
        coords[0] += e.lngLat.lng > coords[0] ? 360 : -360;
      }

      new maplibregl.Popup()
        .setLngLat(coords)
        .setHTML(`
          <div class="p-2">
            <div class="font-medium italic">${props.species || props.scientific_name || 'Unknown species'}</div>
            ${props.common_name ? `<div class="text-sm text-gray-600 dark:text-gray-400">${props.common_name}</div>` : ''}
            <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              ${props.date || props.date_detected || 'Unknown date'}<br/>
              ${props.country || ''}${props.state ? ', ' + props.state : ''}
            </div>
            ${props.strain ? `<div class="text-xs text-blue-600 dark:text-blue-400 mt-1">Strain: ${props.strain}</div>` : ''}
            ${props.source ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Source: ${props.source}</div>` : ''}
          </div>
        `)
        .addTo(map);
    });

    // Change cursor on hover
    map.on('mouseenter', 'clusters', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'clusters', () => {
      map.getCanvas().style.cursor = '';
    });
    map.on('mouseenter', 'unclustered-point', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'unclustered-point', () => {
      map.getCanvas().style.cursor = '';
    });
  }
</script>

<svelte:head>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet" />
</svelte:head>

<div class="space-y-4">
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{t('map.title') || 'Detection Map'}</h1>
      <p class="text-gray-600 dark:text-gray-300 mt-1">
        {t('map.georef.desc', {n: formatNumber(stats.points), c: stats.countries}) || formatNumber(stats.points) + ' georeferenced detections across ' + stats.countries + ' countries'}
      </p>
    </div>

    <!-- Species filter (from #/map?species=… deep links; clearable) -->
    {#if speciesFilter}
      <div class="flex items-center gap-2">
        <span class="px-3 py-1.5 text-sm rounded-md bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
          {speciesFilter}
        </span>
        <button
          onclick={clearSpeciesFilter}
          class="px-3 py-1.5 text-sm rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          {t('map.clear.filter')}
        </button>
      </div>
    {/if}
  </div>

  <!-- Map container -->
  <div class="relative bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden shadow-lg" style="height: 70vh;">
    <div bind:this={mapContainer} class="w-full h-full"></div>

    <!-- basemap attribution/status: OSM raster (CARTO key plumbing kept
         dormant above — see the comment at osmTile for restoration) -->
    <div class="absolute bottom-1 left-1 z-10 text-[10px] px-1.5 py-0.5 rounded bg-white/80 dark:bg-gray-900/80 text-gray-600 dark:text-gray-300"
         title={t('map.basemap.osm.tip')}>
      {t('map.basemap.osm')}
    </div>

    {#if loading}
      <div class="absolute inset-0 bg-white/80 dark:bg-gray-800/80 flex items-center justify-center">
        <div class="text-center">
          <svg class="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin mx-auto mb-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span class="text-gray-600 dark:text-gray-300">{t('map_page.loading.map.data')}</span>
        </div>
      </div>
    {/if}

    <!-- Legend -->
    <div class="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3">
      <h2 class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">{t('map_page.detection.density')}</h2>
      <div class="flex items-center gap-2 text-xs">
        <span class="w-4 h-4 rounded-full bg-red-300"></span>
        <span class="text-gray-600 dark:text-gray-400">&lt;10</span>
        <span class="w-4 h-4 rounded-full bg-red-400"></span>
        <span class="text-gray-600 dark:text-gray-400">10-100</span>
        <span class="w-4 h-4 rounded-full bg-red-500"></span>
        <span class="text-gray-600 dark:text-gray-400">100-1K</span>
        <span class="w-4 h-4 rounded-full bg-red-600"></span>
        <span class="text-gray-600 dark:text-gray-400">&gt;1K</span>
      </div>
    </div>
  </div>

  {#if loadError}
    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-center">
      <p class="text-red-700 dark:text-red-300">{loadError}</p>
    </div>
  {/if}

  <!-- Help text -->
  <div class="text-sm text-gray-500 dark:text-gray-400">
    {t('map.hint') || 'Click on clusters to zoom in. Click on individual points to see detection details.'}
  </div>
</div>
