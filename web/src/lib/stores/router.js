/**
 * Hash-based router store for SPA navigation
 *
 * URL structure: #/page?param1=value1&param2=value2
 * Examples:
 *   #/                       → Home
 *   #/species                → Species list
 *   #/species/9031           → Species detail (taxon_id 9031)
 *   #/species?q=mallard      → Species search
 *   #/genomes?detected=true  → Filtered genomes
 *   #/map?species=9031       → Map filtered to species
 */

// Route state - reactive in Svelte 5 via $state in components
let currentRoute = {
  page: 'home',
  id: null,
  params: {}
};

// Subscribers for route changes
const subscribers = new Set();

/**
 * Parse hash into route object
 */
function safeDecode(s) {
  // '+' is not a space per URL spec in fragments, but some tools/users
  // paste query-style encoding — normalise before decoding so species
  // names with spaces (Gallus+gallus) resolve like %20 does
  try { return decodeURIComponent(s.replace(/\+/g, ' ')); } catch { return s; }
}

function parseHash(hash) {
  // Remove leading # and /
  const cleanHash = hash.replace(/^#\/?/, '');

  // Split path and query string
  const [pathPart, queryPart] = cleanHash.split('?');
  const segments = pathPart.split('/').filter(Boolean);

  // Parse query params
  const params = {};
  if (queryPart) {
    const searchParams = new URLSearchParams(queryPart);
    for (const [key, value] of searchParams) {
      params[key] = value;
    }
  }

  // Determine page and optional ID (decode: ids may be %2F-encoded symbols)
  const page = segments[0] || 'home';
  const id = segments[1] ? safeDecode(segments[1]) : null;

  return { page, id, params };
}

/**
 * Build hash from route object
 */
function buildHash(page, id = null, params = {}) {
  let hash = `#/${page}`;
  // Encode the id: gene symbols can contain forward slashes (PGR2/3) which
  // would otherwise split the route path
  if (id) hash += `/${encodeURIComponent(id)}`;

  const queryParts = Object.entries(params)
    .filter(([_, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`);

  if (queryParts.length > 0) {
    hash += '?' + queryParts.join('&');
  }

  return hash;
}

/**
 * Navigate to a new route
 */
export function navigate(page, id = null, params = {}) {
  const hash = buildHash(page, id, params);
  window.location.hash = hash;
}

/**
 * Update query params without changing page
 */
export function updateParams(newParams) {
  const merged = { ...currentRoute.params, ...newParams };
  // Remove null/undefined values
  Object.keys(merged).forEach(k => {
    if (merged[k] === null || merged[k] === undefined) delete merged[k];
  });
  navigate(currentRoute.page, currentRoute.id, merged);
}

/**
 * Go back in history
 */
export function goBack() {
  window.history.back();
}

/**
 * Subscribe to route changes
 */
export function subscribe(callback) {
  subscribers.add(callback);
  // Immediately call with current route
  callback(currentRoute);

  return () => {
    subscribers.delete(callback);
  };
}

/**
 * Get current route (snapshot)
 */
export function getRoute() {
  return { ...currentRoute };
}

/**
 * Initialize router - call once at app start
 */
export function initRouter() {
  // Handle initial hash
  const handleHashChange = () => {
    currentRoute = parseHash(window.location.hash);
    subscribers.forEach(cb => cb(currentRoute));
  };

  // Listen for hash changes
  window.addEventListener('hashchange', handleHashChange);

  // Set initial route
  if (!window.location.hash) {
    window.location.hash = '#/';
  }
  handleHashChange();

  // Return cleanup function
  return () => {
    window.removeEventListener('hashchange', handleHashChange);
  };
}

// Route helper functions for common patterns
export const routes = {
  home: () => navigate('home'),
  species: (id = null, params = {}) => navigate('species', id, params),
  speciesSearch: (query) => navigate('species', null, { q: query }),
  phylogeny: (focus = null) => navigate('phylogeny', null, focus ? { focus } : {}),
  genes: (symbol = null) => navigate('genes', symbol),
  mutations: (canonical = null) => navigate('mutations', canonical),
  genomes: (params = {}) => navigate('genomes', null, params),
  map: (params = {}) => navigate('map', null, params),
  history: (species = null) => navigate('history', null, species ? { species } : {}),
  papers: (params = {}) => navigate('papers', null, params),
  numbers: () => navigate('numbers'),
  press: () => navigate('press'),
  downloads: () => navigate('downloads'),
  resources: () => navigate('resources')
};
