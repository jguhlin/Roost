/**
 * DuckDB-WASM singleton store for client-side SQL queries
 *
 * Loads Parquet files and provides query interface for:
 * - detections.parquet: Detection records
 * - species.parquet: Species profiles
 * - gene_presence.parquet: Gene × species matrix (future)
 * - susceptibility.parquet: Risk scores (future)
 * - genomes.parquet: Assembly catalog (future)
 */

// Performance: duckdb-wasm (~7MB) is dynamically imported on first init.
// Every page that imports this file does NOT pay the download cost up front.
let _duckdb = null;
async function loadDuckDBModule() {
  if (!_duckdb) _duckdb = await import('@duckdb/duckdb-wasm');
  return _duckdb;
}

// Singleton state
let dbInstance = null;
let conn = null;
let initPromise = null;
let loadedTables = new Set();

// Subscribers for loading state
const subscribers = new Set();
let state = {
  initialized: false,
  loading: false,
  error: null,
  tables: []
};

function notify() {
  subscribers.forEach(cb => cb(state));
}

/**
 * Initialize DuckDB-WASM
 */
async function initDuckDB() {
  if (initPromise) return initPromise;

  initPromise = (async () => {
    state = { ...state, loading: true, error: null };
    notify();

    try {
      const duckdb = await loadDuckDBModule();
      // Use CDN bundles for simplicity
      const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();

      // Select bundle based on browser capabilities
      const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

      // Create worker
      const worker_url = URL.createObjectURL(
        new Blob([`importScripts("${bundle.mainWorker}");`], { type: 'text/javascript' })
      );
      const worker = new Worker(worker_url);
      const logger = new duckdb.ConsoleLogger();

      // Instantiate database
      dbInstance = new _duckdb.AsyncDuckDB(logger, worker);
      await dbInstance.instantiate(bundle.mainModule, bundle.pthreadWorker);

      // Create connection
      conn = await dbInstance.connect();

      // Enable extensions
      await conn.query(`INSTALL parquet; LOAD parquet;`);

      state = { ...state, initialized: true, loading: false };
      notify();

      console.log('[DuckDB] Initialized successfully');
    } catch (error) {
      state = { ...state, loading: false, error: error.message };
      notify();
      console.error('[DuckDB] Initialization failed:', error);
      throw error;
    }
  })();

  return initPromise;
}

/**
 * Load a Parquet file as a table
 */
const loadingTables = new Map();  // name → in-flight load promise (dedupes concurrent loads)

async function loadTable(name, url) {
  if (loadedTables.has(name)) return;
  if (loadingTables.has(name)) return loadingTables.get(name);

  const load = (async () => {
    if (!conn) await initDuckDB();
    if (loadedTables.has(name)) return;  // re-check after await

    try {
      // Fetch the file
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.status}`);

      const buffer = await response.arrayBuffer();

      // Register as a file in DuckDB
      await dbInstance.registerFileBuffer(`${name}.parquet`, new Uint8Array(buffer));

      // Create table from file (OR REPLACE guards against partial-interrupt retries)
      await conn.query(`CREATE OR REPLACE TABLE ${name} AS SELECT * FROM read_parquet('${name}.parquet')`);

      loadedTables.add(name);
      state = { ...state, tables: [...loadedTables] };
      notify();

      console.log(`[DuckDB] Loaded table: ${name}`);
    } catch (error) {
      console.error(`[DuckDB] Failed to load table ${name}:`, error);
      throw error;
    }
  })();

  loadingTables.set(name, load);
  try {
    await load;
  } finally {
    loadingTables.delete(name);
  }
}

/**
 * Execute a SQL query and return results as array of objects
 */
async function query(sql, params = []) {
  if (!conn) await initDuckDB();

  try {
    const result = await conn.query(sql);
    return result.toArray().map(row => row.toJSON());
  } catch (error) {
    console.error('[DuckDB] Query failed:', sql, error);
    throw error;
  }
}

/**
 * Execute a query and return first row
 */
async function queryOne(sql, params = []) {
  const results = await query(sql, params);
  return results[0] || null;
}

/**
 * Execute a query and return scalar value
 */
async function queryScalar(sql, params = []) {
  const row = await queryOne(sql, params);
  if (!row) return null;
  const keys = Object.keys(row);
  return keys.length > 0 ? row[keys[0]] : null;
}

// Export store interface
export const dbStore = {
  subscribe(callback) {
    subscribers.add(callback);
    callback(state);
    return () => subscribers.delete(callback);
  },

  get state() {
    return state;
  },

  init: initDuckDB,
  loadTable,
  query,
  queryOne,
  queryScalar,

  // Convenience loaders for standard tables
  async loadDetections() {
    await loadTable('detections', 'data/detections.parquet');
  },

  async loadSpecies() {
    await loadTable('species', 'data/species.parquet');
  },

  async loadGenomes() {
    await loadTable('genomes', 'data/genomes.parquet');
  },

  async loadGenePresence() {
    await loadTable('gene_presence', 'data/gene_presence.parquet');
  },

  async loadSusceptibility() {
    await loadTable('susceptibility', 'data/susceptibility.parquet');
  },

  // Check if a table is loaded
  hasTable(name) {
    return loadedTables.has(name);
  }
};

// Shorthand query helpers
export const db = {
  query,
  queryOne,
  queryScalar,
  init: initDuckDB,

  // Common queries
  async getStats() {
    await dbStore.loadDetections();
    await dbStore.loadSpecies();

    const [detections, species, countries] = await Promise.all([
      queryScalar('SELECT COUNT(*) FROM detections'),
      queryScalar('SELECT COUNT(DISTINCT scientific_name) FROM species'),
      queryScalar('SELECT COUNT(DISTINCT country) FROM detections')
    ]);

    return { detections, species, countries };
  },

  async searchSpecies(query, limit = 20) {
    await dbStore.loadSpecies();

    const pattern = `%${query.toLowerCase()}%`;
    return await db.query(`
      SELECT * FROM species
      WHERE LOWER(scientific_name) LIKE '${pattern}'
         OR LOWER(common_name) LIKE '${pattern}'
      ORDER BY detection_records DESC
      LIMIT ${limit}
    `);
  },

  /**
   * Search species including those without detections
   * Combines results from parquet (detections) and species_index.json
   */
  async searchSpeciesAll(query, limit = 50) {
    // Normalize query for diacritic-insensitive search
    const normalizeText = (text) => {
      if (!text) return '';
      return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    };

    const q = normalizeText(query);
    if (!q || q.length < 2) return [];

    // Search parquet database
    let dbResults = [];
    try {
      await dbStore.loadSpecies();
      const pattern = `%${query.toLowerCase()}%`;
      dbResults = await db.query(`
        SELECT * FROM species
        WHERE LOWER(scientific_name) LIKE '${pattern}'
           OR LOWER(common_name) LIKE '${pattern}'
        ORDER BY detection_records DESC
        LIMIT ${limit}
      `);
    } catch (e) {
      console.error('[db] parquet search failed:', e);
    }

    // Search species_index.json + wiki supplement (mammals, literature-only
    // species) for species not in parquet
    let indexResults = [];
    try {
      const [response, supplementResponse] = await Promise.all([
        fetch('data/species_index.json'),
        fetch('data/species_wiki_supplement.json').catch(() => null)
      ]);
      let index = await response.json();
      if (supplementResponse && supplementResponse.ok) {
        const supplement = await supplementResponse.json();
        if (Array.isArray(supplement) && supplement.length) {
          // Dedupe by scientific name: since the index gained mammals
          // (Phase 3), supplement entries for the same species would
          // otherwise appear twice (duplicate keyed-each crash downstream).
          const have = new Set(index.map(s => (s.sci || '').toLowerCase()));
          for (const s of supplement) {
            if (!have.has((s.sci || '').toLowerCase())) { index.push(s); have.add((s.sci || '').toLowerCase()); }
          }
        }
      }

      // Find matches in index
      const matches = index.filter(sp => {
        const sci = normalizeText(sp.sci);
        const com = normalizeText(sp.com);
        return sci.includes(q) || com.includes(q);
      });

      // Convert to species format, excluding those already in dbResults.
      // String-normalise the ids: parquet taxon_ids arrive as BigInt from
      // DuckDB, index ids are Numbers — Set.has does not coerce, so the
      // same species would otherwise appear twice.
      const dbIds = new Set(dbResults.map(r => String(r.taxon_id)));
      indexResults = matches
        .filter(sp => !dbIds.has(String(sp.id)))
        .map(sp => db._indexToSpecies(sp));
    } catch (e) {
      console.error('[db] index search failed:', e);
    }

    // Combine and sort by detections
    const combined = [...dbResults, ...indexResults];
    // DuckDB returns detection_count as BigInt, index results as Number —
    // normalise before comparing (mixing them throws)
    combined.sort((a, b) => (Number(b.detection_count) || 0) - (Number(a.detection_count) || 0));

    return combined.slice(0, limit);
  },

  async getSpeciesById(taxonId) {
    await dbStore.loadSpecies();
    const num = parseInt(taxonId, 10);
    if (!isNaN(num)) {
      return await queryOne(`SELECT * FROM species WHERE taxon_id = ${num}`);
    }
    // non-numeric id (e.g. scientific name from a wiki link) — no taxon row
    return null;
  },

  async getSpeciesByName(scientificName) {
    await dbStore.loadSpecies();
    return await queryOne(`SELECT * FROM species WHERE scientific_name = '${scientificName}'`);
  },

  async getDetectionsForSpecies(scientificName) {
    await dbStore.loadDetections();
    return await query(`
      SELECT * FROM detections
      WHERE scientific_name = '${scientificName}'
      ORDER BY date_detected DESC
    `);
  },

  async getTopSpecies(limit = 10) {
    await dbStore.loadSpecies();
    return await query(`
      SELECT * FROM species
      ORDER BY detection_records DESC
      LIMIT ${limit}
    `);
  },

  // --- Gene presence (Phase 2 Step 2: matrix lives in parquet) ---

  /** All calls for one species, e.g. the gene-panel tab of a species page. */
  async getPresenceCallsForSpecies(scientificName) {
    await dbStore.loadGenePresence();
    const sci = String(scientificName).replace(/'/g, "''");
    return await query(`
      SELECT gene, status, level, method, importance
      FROM gene_presence
      WHERE species = '${sci}'
      ORDER BY importance DESC, gene
    `);
  },

  /** All calls for one gene — species→status view of the matrix. */
  async getPresenceCallsForGene(gene) {
    await dbStore.loadGenePresence();
    const sym = String(gene).replace(/'/g, "''");
    return await query(`
      SELECT species, status, level, method, importance, conf, searchability
      FROM gene_presence
      WHERE gene = '${sym}'
      ORDER BY status DESC, species
    `);
  },

  /** Calls for a set of genes (e.g. the model sensor matrix + aliases) —
   *  ~genes × species rows instead of the whole 131k-call table. */
  async getPresenceCallsForGenes(geneList) {
    await dbStore.loadGenePresence();
    const syms = [...new Set((geneList || []).map(g => String(g).replace(/'/g, "''")))];
    if (!syms.length) return [];
    return await query(`
      SELECT species, gene, status, level, method, importance, conf, searchability
      FROM gene_presence
      WHERE gene IN (${syms.map(s => `'${s}'`).join(', ')})
    `);
  },

  /** Per-species presence rollup (counts + critical/high absences).
   *  (full/fragment/not_found counts + critical/high absences).
   *  Counts are normalised to Number (DuckDB returns BigInt) and the
   *  absence list to a real Array (string_agg survives JSON conversion). */
  async getSpeciesGeneSummary(scientificName) {
    await dbStore.loadGenePresence();
    const sci = String(scientificName).replace(/'/g, "''");
    const row = await queryOne(`
      SELECT COUNT(*) AS total_genes_searched,
             COUNT(*) FILTER (WHERE status = 'FULL') AS full,
             COUNT(*) FILTER (WHERE status = 'FRAGMENT') AS fragment,
             COUNT(*) FILTER (WHERE status = 'NOT_FOUND') AS not_found,
             COALESCE(string_agg(gene, ',' ORDER BY gene) FILTER (
               WHERE status = 'NOT_FOUND' AND importance = 'critical'
             ), '') AS critical_absences,
             COALESCE(string_agg(gene, ',' ORDER BY importance, gene) FILTER (
               WHERE status = 'NOT_FOUND'
                 AND importance IN ('critical', 'high')
             ), '') AS high_absences
      FROM gene_presence
      WHERE species = '${sci}'
    `);
    if (!row) return null;
    const out = {};
    for (const [k, v] of Object.entries(row)) out[k] = typeof v === 'bigint' ? Number(v) : v;
    out.critical_absences = row.critical_absences ? String(row.critical_absences).split(',') : [];
    out.high_absences = row.high_absences ? String(row.high_absences).split(',') : [];
    return out;
  },

  /** Per-gene rollup for ALL genes (Genes page detail view) — replaces
   *  the retired gene_presence_summary.json with one GROUP BY. */
  async getGenePresenceSummaries() {
    await dbStore.loadGenePresence();
    const rows = await query(`
      SELECT gene,
             COUNT(*) FILTER (WHERE status = 'FULL') AS full,
             COUNT(*) FILTER (WHERE status = 'FRAGMENT') AS fragment,
             COUNT(*) FILTER (WHERE status = 'NOT_FOUND') AS not_found,
             COUNT(*) AS total
      FROM gene_presence
      GROUP BY gene
    `);
    const out = {};
    for (const r of rows) {
      out[r.gene] = {
        full: Number(r.full), fragment: Number(r.fragment),
        not_found: Number(r.not_found), total: Number(r.total),
      };
    }
    return out;
  },

  /** Per-gene rollup for a single gene. */
  async getGenePresenceSummary(gene) {
    await dbStore.loadGenePresence();
    const sym = String(gene).replace(/'/g, "''");
    const row = await queryOne(`
      SELECT COUNT(*) AS total,
             COUNT(*) FILTER (WHERE status = 'FULL') AS full,
             COUNT(*) FILTER (WHERE status = 'FRAGMENT') AS fragment,
             COUNT(*) FILTER (WHERE status = 'NOT_FOUND') AS not_found
      FROM gene_presence
      WHERE gene = '${sym}'
    `);
    if (!row) return null;
    const out = {};
    for (const [k, v] of Object.entries(row)) out[k] = typeof v === 'bigint' ? Number(v) : v;
    return out;
  },

  /**
   * Get species from index (includes species without detections)
   * Used as fallback for species not in parquet
   */
  async getSpeciesFromIndex(idOrName) {
    try {
      const [response, supplementResponse] = await Promise.all([
        fetch('data/species_index.json'),
        fetch('data/species_wiki_supplement.json').catch(() => null)
      ]);
      let index = await response.json();
      if (supplementResponse && supplementResponse.ok) {
        const supplement = await supplementResponse.json();
        if (Array.isArray(supplement) && supplement.length) {
          // Dedupe by scientific name: since the index gained mammals
          // (Phase 3), supplement entries for the same species would
          // otherwise appear twice (duplicate keyed-each crash downstream).
          const have = new Set(index.map(s => (s.sci || '').toLowerCase()));
          for (const s of supplement) {
            if (!have.has((s.sci || '').toLowerCase())) { index.push(s); have.add((s.sci || '').toLowerCase()); }
          }
        }
      }

      // Try to find by taxon_id first
      const numId = parseInt(idOrName, 10);
      if (!isNaN(numId)) {
        const byId = index.find(s => s.id === numId);
        if (byId) return db._indexToSpecies(byId);
      }

      // Try by scientific name
      const byName = index.find(s =>
        s.sci?.toLowerCase() === idOrName?.toLowerCase()
      );
      if (byName) return db._indexToSpecies(byName);

      // Try by common name
      const byCom = index.find(s =>
        s.com?.toLowerCase() === idOrName?.toLowerCase()
      );
      if (byCom) return db._indexToSpecies(byCom);

      return null;
    } catch (error) {
      console.error('[db] Failed to load species from index:', error);
      return null;
    }
  },

  /**
   * Convert species_index record to species profile format
   */
  _indexToSpecies(record) {
    return {
      taxon_id: record.id,
      scientific_name: record.sci,
      common_name: record.com,
      order: record.ord || null,
      family: record.fam || null,
      detection_count: record.det || 0,
      // Conservation data
      iucn: record.iucn || null,
      trend: record.trend || null,
      endemic: record.endemic || null,
      range: record.range || null,
      population: record.population || null,
      notes: record.notes || null,
      vaccination_target: record.vaccination_target || false,
      conservation: record.conservation || null,
      // Genome data (index uses compact keys: genome_acc/genome_level/genome_n50)
      genome_accession: record.genome_acc || record.genome_accession || null,
      assembly_level: record.genome_level || record.assembly_level || null,
      scaffold_n50: record.genome_n50 || record.scaffold_n50 || null,
      contig_n50: record.genome_ctg_n50 || record.contig_n50 || null,
      total_length: record.genome_len || record.total_length || null,
      has_annotation: record.genome_annot ?? record.has_annotation ?? null,
      annotation_status: record.genome_annot_status || record.annotation_status || null,
      is_representative: record.genome_rep ?? record.is_representative ?? null,
      has_genome: record.has_genome || false,
      has_presence: record.has_presence || false,
      // Flags
      has_detections: (record.det || 0) > 0,
      mammal: record.mammal || record.ord === 'Mammalia' || record.class === 'Mammalia' || false,
      _from_index: true   // Flag to indicate source
    };
  }
};

export default db;

// Dev/test introspection (mirrors the window.__cy convention used by the
// e2e suite for Cytoscape): lets Playwright drive DuckDB queries directly.
if (typeof window !== 'undefined') {
  window.__db = db;
}
