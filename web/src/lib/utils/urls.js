/**
 * URL builders for external resources
 *
 * Generates links to:
 * - NCBI (GenBank, Gene, Assembly, Taxonomy)
 * - DOI resolvers
 * - UniProt
 * - BLAST
 * - Other external databases
 */

// NCBI URLs
export const ncbi = {
  /**
   * Link to NCBI Taxonomy
   */
  taxonomy(taxonId) {
    return `https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${taxonId}`;
  },

  /**
   * Link to NCBI Assembly
   */
  assembly(accession) {
    return `https://www.ncbi.nlm.nih.gov/datasets/genome/${accession}/`;
  },

  /**
   * Link to NCBI Gene
   */
  gene(geneId) {
    return `https://www.ncbi.nlm.nih.gov/gene/${geneId}`;
  },

  /**
   * Link to NCBI Gene search by symbol
   */
  geneSearch(symbol, organism = 'Aves') {
    return `https://www.ncbi.nlm.nih.gov/gene/?term=${encodeURIComponent(symbol)}[sym]+AND+${encodeURIComponent(organism)}[orgn]`;
  },

  /**
   * Link to NCBI Nucleotide (GenBank)
   */
  nucleotide(accession) {
    return `https://www.ncbi.nlm.nih.gov/nuccore/${accession}`;
  },

  /**
   * Link to NCBI Protein
   */
  protein(accession) {
    return `https://www.ncbi.nlm.nih.gov/protein/${accession}`;
  },

  /**
   * Link to NCBI PubMed
   */
  pubmed(pmid) {
    return `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;
  },

  /**
   * BLAST nucleotide search
   */
  blastn(sequence, database = 'nt') {
    const params = new URLSearchParams({
      PROGRAM: 'blastn',
      DATABASE: database,
      QUERY: sequence,
      CMD: 'request'
    });
    return `https://blast.ncbi.nlm.nih.gov/Blast.cgi?${params}`;
  },

  /**
   * BLAST protein search
   */
  blastp(sequence, database = 'nr') {
    const params = new URLSearchParams({
      PROGRAM: 'blastp',
      DATABASE: database,
      QUERY: sequence,
      CMD: 'request'
    });
    return `https://blast.ncbi.nlm.nih.gov/Blast.cgi?${params}`;
  }
};

// DOI resolution
export function doi(identifier) {
  // Remove doi: prefix if present
  const clean = identifier.replace(/^doi:\s*/i, '');
  return `https://doi.org/${clean}`;
}

// UniProt URLs
export const uniprot = {
  entry(accession) {
    return `https://www.uniprot.org/uniprotkb/${accession}`;
  },

  search(query) {
    return `https://www.uniprot.org/uniprotkb?query=${encodeURIComponent(query)}`;
  }
};

// Ensembl URLs
export const ensembl = {
  gene(id) {
    return `https://www.ensembl.org/id/${id}`;
  },

  species(name) {
    // Convert "Anas platyrhynchos" to "Anas_platyrhynchos"
    const formatted = name.replace(/\s+/g, '_');
    return `https://www.ensembl.org/${formatted}/Info/Index`;
  }
};

// GBIF (occurrence data)
export const gbif = {
  species(key) {
    return `https://www.gbif.org/species/${key}`;
  },

  search(name) {
    return `https://www.gbif.org/species/search?q=${encodeURIComponent(name)}`;
  },

  occurrences(speciesKey) {
    return `https://www.gbif.org/occurrence/search?taxon_key=${speciesKey}`;
  }
};

// eBird
export const ebird = {
  species(speciesCode) {
    return `https://ebird.org/species/${speciesCode}`;
  },

  explore(region = 'world') {
    return `https://ebird.org/explore?region=${region}`;
  }
};

// IUCN Red List
export const iucn = {
  species(id) {
    return `https://www.iucnredlist.org/species/${id}`;
  },

  search(name) {
    return `https://www.iucnredlist.org/search?query=${encodeURIComponent(name)}`;
  }
};

// Wikipedia/Wikimedia
export const wikimedia = {
  wikipedia(title) {
    return `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replace(/\s+/g, '_'))}`;
  },

  commons(filename) {
    return `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(filename)}`;
  },

  // Thumbnail URL from Commons filename
  thumbnail(filename, width = 300) {
    const hash = filename.replace(/\s+/g, '_');
    const md5 = hash; // Would need actual MD5 for production
    return `https://upload.wikimedia.org/wikipedia/commons/thumb/${md5.charAt(0)}/${md5.substring(0, 2)}/${hash}/${width}px-${hash}`;
  }
};

// BirdLife International
export const birdlife = {
  species(sisId) {
    return `https://datazone.birdlife.org/species/factsheet/${sisId}`;
  },

  search(name) {
    return `http://datazone.birdlife.org/species/results?thrlev1=&thrlev2=&kw=${encodeURIComponent(name)}`;
  }
};

// Surveillance/outbreak sources
export const surveillance = {
  wahis(outbreakId) {
    return `https://wahis.woah.org/#/report-info?reportId=${outbreakId}`;
  },

  gisaid() {
    return 'https://gisaid.org/';
  },

  nextstrain(pathogen = 'avian-flu') {
    return `https://nextstrain.org/${pathogen}`;
  }
};

// Internal app routes (hash-based)
export const app = {
  species(taxonIdOrName) {
    return `#/species/${encodeURIComponent(taxonIdOrName)}`;
  },

  speciesSearch(query) {
    return `#/species?q=${encodeURIComponent(query)}`;
  },

  gene(symbol) {
    return `#/genes/${encodeURIComponent(symbol)}`;
  },

  map(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return qs ? `#/map?${qs}` : '#/map';
  }
};
