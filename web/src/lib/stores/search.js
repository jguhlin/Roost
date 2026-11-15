/**
 * Global search state and functionality
 *
 * Manages:
 * - Search query text
 * - Autocomplete results
 * - Search history
 * - Type indicators (species, gene, location)
 */

// Search state
let searchState = {
  query: '',
  results: [],
  loading: false,
  open: false,
  history: []
};

// Subscribers
const subscribers = new Set();

// localized species names from the i18n store
import { speciesSearchNames } from './i18n.svelte.js';
const await_import = () => ({ speciesSearchNames });

// Species index cache
let speciesIndex = null;
// Wiki entity index (genes, mutations) for cross-entity search
let wikiIndex = null;

function notify() {
  subscribers.forEach(cb => cb(searchState));
}

/**
 * Load species index for autocomplete (includes wiki supplement:
 * mammals and literature-only species referenced by gene/mutation pages)
 */
let supplementMerged = false;
async function loadSpeciesIndex() {
  if (speciesIndex) return speciesIndex;

  try {
    const [indexResponse, supplementResponse] = await Promise.all([
      fetch('data/species_index.json'),
      fetch('data/species_wiki_supplement.json').catch(() => null)
    ]);
    let index = await indexResponse.json();
    if (supplementResponse && supplementResponse.ok && !supplementMerged) {
      const supplement = await supplementResponse.json();
      if (Array.isArray(supplement) && supplement.length) {
        // dedupe by scientific name — the supplement must never double a
        // species already in (or concurrently merged into) the index
        const have = new Set(index.map(s => String(s.sci || '').toLowerCase()));
        const extras = supplement.filter(s => {
          const key = String(s.sci || '').toLowerCase();
          if (!key || have.has(key)) return false;
          have.add(key);
          return true;
        });
        index = [...index, ...extras];
      }
      supplementMerged = true;
    }
    speciesIndex = index;
    return speciesIndex;
  } catch (error) {
    console.error('[Search] Failed to load species index:', error);
    return [];
  }
}

/**
 * Load wiki entity index (genes + mutations)
 */
async function loadWikiIndex() {
  if (wikiIndex) return wikiIndex;

  try {
    const response = await fetch('data/wiki_index.json');
    wikiIndex = await response.json();
    return wikiIndex;
  } catch (error) {
    console.error('[Search] Failed to load wiki index:', error);
    return { genes: [], mutations: [] };
  }
}

/**
 * Normalize text by removing diacritics/accents for search matching
 * e.g., "kākāpō" -> "kakapo", "takahē" -> "takahe"
 */
export function normalizeText(text) {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

/**
 * Search species index with fuzzy matching
 */
function searchIndex(query, limit = 10) {
  if (!speciesIndex || !query) return [];

  const q = normalizeText(query.trim());
  if (q.length < 2) return [];

  // localized names + aliases from species_names.json (via i18n store)
  const { speciesSearchNames } = await_import();

  // Score each species
  const scored = speciesIndex.map(species => {
    const sci = normalizeText(species.sci || '');
    const com = normalizeText(species.com || '');
    const altNames = (speciesSearchNames(species.sci) || []).map(normalizeText);

    let score = 0;

    // Exact match boost (any language or alias)
    if (sci === q || com === q) score += 100;
    if (altNames.some(n => n === q)) score += 100;

    // Starts with match
    if (sci.startsWith(q)) score += 50;
    if (com.startsWith(q)) score += 40;
    if (altNames.some(n => n.startsWith(q))) score += 35;

    // Contains match
    if (sci.includes(q)) score += 20;
    if (com.includes(q)) score += 15;
    if (altNames.some(n => n.includes(q))) score += 12;

    // Word start match
    const sciWords = sci.split(' ');
    const comWords = com.split(' ');
    if (sciWords.some(w => w.startsWith(q))) score += 30;
    if (comWords.some(w => w.startsWith(q))) score += 25;
    if (altNames.some(n => n.split(' ').some(w => w.startsWith(q)))) score += 20;

    if (score === 0) return { species, score: 0 }; // no textual match at all

    // Detection count tiebreaker — only among actual matches (otherwise
    // high-detection species like chicken "match" every query)
    score += Math.log10((species.det || 0) + 1) * 0.1;

    return { species, score };
  });

  // Filter and sort
  return scored
    .filter(s => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(s => ({
      id: s.species.id,
      type: 'species',
      scientific_name: s.species.sci,
      common_name: s.species.com,
      order: s.species.ord,
      family: s.species.fam,
      detections: s.species.det,
      iucn: s.species.iucn,
      endemic: s.species.endemic,
      vaccination_target: s.species.vaccination_target,
      score: s.score
    }));
}

/**
 * Search wiki entities (genes, mutations)
 */
const SCOPE_TEXT = {
  avian: 'avian',
  both: 'avian + mammalian',
  mammalian: 'mammalian',
  viral: 'viral only',
};

function scopeText(scope) {
  return scope ? ' · ' + (SCOPE_TEXT[scope] || scope) : '';
}

function searchWiki(query, geneLimit = 3, mutationLimit = 2) {
  if (!wikiIndex || !query) return [];
  const q = normalizeText(query.trim());
  if (q.length < 2) return [];

  const geneResults = (wikiIndex.genes || []).map(g => {
    const sym = normalizeText(g.symbol);
    let score = 0;
    if (sym === q) score += 100;
    if (sym.startsWith(q)) score += 60;
    if (sym.includes(q)) score += 30;
    score += Math.min(g.paper_count, 100) * 0.05;
    return {
      type: 'gene',
      id: g.symbol,
      symbol: g.symbol,
      label: g.symbol,
      sublabel: g.category,
      paper_count: g.paper_count,
      score
    };
  }).filter(g => g.score > 25).sort((a, b) => b.score - a.score).slice(0, geneLimit);

  const mutResults = (wikiIndex.mutations || []).map(m => {
    const canon = normalizeText(m.canonical);
    const protein = normalizeText(m.protein);
    let score = 0;
    if (canon === q) score += 100;
    if (canon.startsWith(q)) score += 60;
    if (canon.includes(q)) score += 30;
    // bare mutation match e.g. "e627k" matches PB2-E627K
    if (canon.includes('-' + q)) score += 45;
    if (protein === q) score += 20;
    score += Math.min(m.paper_count, 100) * 0.05;
    return {
      type: 'mutation',
      id: m.canonical,
      canonical: m.canonical,
      label: m.canonical,
      sublabel: `${m.protein} · ${m.paper_count} papers${scopeText(m.host_scope)}`,
      score
    };
  }).filter(m => m.score > 25).sort((a, b) => b.score - a.score).slice(0, mutationLimit);

  return [...geneResults, ...mutResults];
}
let searchTimeout = null;

async function performSearch(query) {
  if (searchTimeout) clearTimeout(searchTimeout);

  if (!query || query.length < 2) {
    searchState = { ...searchState, results: [], loading: false };
    notify();
    return [];
  }

  searchState = { ...searchState, query, loading: true };
  notify();

  // Returns a Promise resolving with the results (analytics consumes it);
  // the debounce stays internal.
  return new Promise((resolve) => {
    searchTimeout = setTimeout(async () => {
      await Promise.all([loadSpeciesIndex(), loadWikiIndex()]);
      const speciesResults = searchIndex(query);
      const wikiResults = searchWiki(query);
      // Species first, then genes/mutations (each already scored/sorted)
      const results = [...speciesResults, ...wikiResults];

      searchState = { ...searchState, results, loading: false };
      notify();
      resolve(results);
    }, 150);
  });
}

/**
 * Add to search history
 */
function addToHistory(item) {
  // Remove duplicates
  const filtered = searchState.history.filter(h => h.id !== item.id);

  // Add to front, limit to 10
  const history = [item, ...filtered].slice(0, 10);

  searchState = { ...searchState, history };
  notify();

  // Persist to localStorage
  try {
    localStorage.setItem('roost_search_history', JSON.stringify(history));
  } catch (e) {
    // Ignore localStorage errors
  }
}

/**
 * Load search history from localStorage
 */
function loadHistory() {
  try {
    const saved = localStorage.getItem('roost_search_history');
    if (saved) {
      searchState = { ...searchState, history: JSON.parse(saved) };
      notify();
    }
  } catch (e) {
    // Ignore localStorage errors
  }
}

/**
 * Clear search history
 */
function clearHistory() {
  searchState = { ...searchState, history: [] };
  notify();
  try {
    localStorage.removeItem('roost_search_history');
  } catch (e) {
    // Ignore
  }
}

// Export search store
export const searchStore = {
  subscribe(callback) {
    subscribers.add(callback);
    callback(searchState);
    return () => subscribers.delete(callback);
  },

  get state() {
    return searchState;
  },

  setQuery(query) {
    searchState = { ...searchState, query };
    notify();
    const r = performSearch(query);
    if (r && typeof r.then === 'function') {
      // Matomo site-search tracking (no-op unless production + configured):
      // what visitors look for, with result counts — the resource-site signal.
      r.then((results) => {
        if (query.trim().length >= 2 && window._paq && results) {
          window._paq.push(['trackSiteSearch', query.trim(), 'global', results.length]);
        }
      }).catch(() => {});
    }
    return r;
  },

  setOpen(open) {
    searchState = { ...searchState, open };
    notify();
  },

  clear() {
    searchState = { ...searchState, query: '', results: [], open: false };
    notify();
  },

  selectResult(result) {
    addToHistory(result);
    this.clear();
  },

  loadHistory,
  clearHistory,

  // Preload index
  async preload() {
    loadHistory();
    await Promise.all([loadSpeciesIndex(), loadWikiIndex()]);
  }
};

export default searchStore;
