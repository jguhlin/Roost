/**
 * Shared gene-presence helpers (DATA_MATURATION Phase 2 Step 3).
 *
 * The presence matrix ships ONLY as gene_presence.parquet (queried through
 * DuckDB); gene metadata ships as the small gene_catalogue.json. These
 * helpers let components keep the { species: { gene: call } } shape they
 * were originally written against, without shipping a duplicated matrix.
 *
 * NOTE: deliberately free of any db.js import — pages that only need the
 * catalogue (e.g. memory-heavy Cytoscape) must not pay for duckdb-wasm.
 */

let cataloguePromise = null;

/** Cached fetch of gene_catalogue.json ({generated, total_*, gene_catalogue, key_genes}). */
export function fetchGeneCatalogue() {
  if (!cataloguePromise) {
    cataloguePromise = fetch('data/gene_catalogue.json')
      .then(r => (r.ok ? r.json() : null))
      .catch(() => null);
  }
  return cataloguePromise;
}

/** rows → { species: { gene: {status, level, method, importance} } } */
export function pivotCallsBySpecies(rows) {
  const species = {};
  for (const r of rows || []) {
    (species[r.species] ||= {})[r.gene] = {
      status: r.status, level: r.level, method: r.method, importance: r.importance,
    };
  }
  return species;
}

/** rows → { gene: { species: status } } (the retired catalogue.species shape) */
export function pivotCallsByGene(rows) {
  const genes = {};
  for (const r of rows || []) {
    (genes[r.gene] ||= {})[r.species] = r.status;
  }
  return genes;
}

/** One species' calls rows → { gene: call } panel slice */
export function panelFromCalls(rows) {
  const panel = {};
  for (const r of rows || []) panel[r.gene] = r;
  return panel;
}
