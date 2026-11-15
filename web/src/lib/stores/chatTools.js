/**
 * chatTools.js (D123c) — deterministic site-data tools for the on-device
 * chat. A 135M model cannot do reliable function-calling, so the HARNESS
 * runs the tools: each user message is matched against shipped site data
 * (genes, mutations, species, papers, glossary) and the hits are injected
 * as authoritative context blocks. The model only ever verbalises what
 * these tools retrieved — that is the entire tool contract.
 *
 * All lookups are local JSON fetches, lazy and cached. Exported:
 *   runTools(text)  → { chips: [{icon, label}], context: string }
 *   compactHistory(messages, budgetTokens) → { messages, compacted, tokens }
 *   estimateTokens(str)
 */

const cache = {};

async function loadJSON(name, url) {
  if (!cache[name]) cache[name] = fetch(url).then(r => r.json());
  return cache[name];
}

const esc = (s) => String(s || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

async function toolGene(text) {
  const [rich, cat] = await Promise.all([
    loadJSON('genes', 'data/genes.json'),
    loadJSON('catalogue', 'data/gene_catalogue.json'),
  ]);
  const richBySym = new Map((rich.genes || rich || []).map(g => [g.symbol.toUpperCase(), g]));
  const keyGenes = cat.key_genes || {};
  const tokens = new Set(text.toUpperCase().match(/\b[A-Z][A-Z0-9-]{1,10}\b/g) || []);
  const items = [];
  for (const t of tokens) {
    const r = richBySym.get(t);
    const k = keyGenes[t];
    if (r || k) {
      const sym = r?.symbol || k.name;
      items.push({
        icon: '🧬',
        title: `${sym} — ${r?.name || k.name || 'gene'}`,
        text: `${r?.function || k.function ? `Function: ${(r?.function || k.function).slice(0, 180)}` : ''}${r?.species_difference ? ` · Species differences: ${String(r.species_difference).slice(0, 120)}` : ''}${k?.importance ? ` · Importance: ${k.importance}` : ''}`.replace(/^ · /, ''),
        links: [{ label: 'gene page', href: `#/genes/${sym}` }],
      });
      if (items.length >= 3) break;
    }
  }
  return items;
}

async function toolSpecies(text) {
  const idx = await loadJSON('species', 'data/species_index.json');
  const lower = text.toLowerCase();
  const items = [];
  for (const s of idx) {
    const com = (s.com || '').toLowerCase();
    const sci = (s.sci || '').toLowerCase();
    if ((com.length > 3 && lower.includes(com)) ||
        (sci.length > 5 && lower.includes(sci))) {
      items.push({
        icon: '🦆',
        title: `${s.sci}${s.com ? ` (${s.com})` : ''}`,
        text: `Order ${s.ord || '?'} · detections: ${s.det ? Number(s.det).toLocaleString() : 'none recorded'} · genome: ${s.genome_acc ? 'assembled' : 'not indexed'}`,
        links: [
          { label: 'species page', href: `#/species/${encodeURIComponent(s.sci)}` },
          { label: 'full gene panel', href: `#/species-full/${encodeURIComponent(s.sci)}` },
        ],
      });
      if (items.length >= 3) break;
    }
  }
  return items;
}

const STOP = new Set(['the', 'and', 'for', 'with', 'what', 'how', 'does', 'are', 'was', 'from', 'about', 'avian', 'influenza', 'virus', 'h5n1', 'bird', 'birds', 'this', 'that', 'have', 'has', 'species', 'positive', 'shown', 'which']);

// ISO3 codes present in the detections store + common name aliases.
// Matched against the user message to resolve a country (D123d).
const COUNTRY_NAMES = {
  AFG: ['afghanistan'], ALA: ['aland islands'], ALB: ['albania'], ARE: ['uae', 'united arab emirates'],
  ARG: ['argentina'], ATA: ['antarctica'], AUS: ['australia'], AUT: ['austria'],
  BGD: ['bangladesh'], BGR: ['bulgaria'], BIH: ['bosnia', 'bosnia and herzegovina'],
  BLR: ['belarus'], BEL: ['belgium'], BOL: ['bolivia'], BRA: ['brazil'],
  CAN: ['canada'], CHE: ['switzerland'], CHL: ['chile'], CHN: ['china'],
  COL: ['colombia'], CRI: ['costa rica'], CUB: ['cuba'], CYP: ['cyprus'],
  CZE: ['czechia', 'czech republic'], DEU: ['germany'], DNK: ['denmark'],
  ECU: ['ecuador'], EGY: ['egypt'], ESP: ['spain'], EST: ['estonia'],
  FIN: ['finland'], FRA: ['france'], GBR: ['uk', 'united kingdom', 'britain', 'england', 'scotland', 'wales'],
  GEO: ['georgia'], GHA: ['ghana'], GRC: ['greece'], HRV: ['croatia'],
  HUN: ['hungary'], IDN: ['indonesia'], IND: ['india'], IRL: ['ireland'],
  IRN: ['iran'], ISL: ['iceland'], ISR: ['israel'], ITA: ['italy'],
  JPN: ['japan'], KAZ: ['kazakhstan'], KOR: ['south korea', 'korea'],
  KGZ: ['kyrgyzstan'], LAO: ['laos'], LKA: ['sri lanka'], LTU: ['lithuania'],
  LUX: ['luxembourg'], LVA: ['latvia'], MAR: ['morocco'], MDA: ['moldova'],
  MKD: ['north macedonia', 'macedonia'], MLT: ['malta'], MNE: ['montenegro'],
  MNG: ['mongolia'], MYS: ['malaysia'], NAM: ['namibia'], NGA: ['nigeria'],
  NLD: ['netherlands', 'holland'], NOR: ['norway'], NPL: ['nepal'],
  NZL: ['new zealand'], PAK: ['pakistan'], PER: ['peru'], PHL: ['philippines'],
  POL: ['poland'], PRT: ['portugal'], ROU: ['romania'], RUS: ['russia'],
  RWA: ['rwanda'], SAU: ['saudi arabia'], SGP: ['singapore'], SRB: ['serbia'],
  SVK: ['slovakia'], SVN: ['slovenia'], SWE: ['sweden'], THA: ['thailand'],
  TUN: ['tunisia'], TUR: ['turkey', 'turkiye'], TWN: ['taiwan'], UKR: ['ukraine'],
  URU: ['uruguay'], USA: ['usa', 'united states', 'us', 'america'],
  UZB: ['uzbekistan'], VNM: ['vietnam'], ZAF: ['south africa'], ZWE: ['zimbabwe'],
};

/** country → species positive there, from the detections parquet via
    duckdb-wasm (the same table the Map page queries). */
async function toolCountry(text) {
  const lower = text.toLowerCase();
  let code = null, name = null;
  for (const [c, aliases] of Object.entries(COUNTRY_NAMES)) {
    if (aliases.some(a => new RegExp(`\\b${esc(a)}\\b`).test(lower))) {
      code = c; name = aliases[0].replace(/^./, ch => ch.toUpperCase());
      break;
    }
  }
  if (!code) return [];
  const { dbStore } = await import('../stores/db.js');
  await dbStore.loadDetections();
  const rows = await dbStore.query(`
    SELECT coalesce(nullif(scientific_name_parsed, ''), species_raw) AS sci,
           count(*) AS n
    FROM detections
    WHERE country = '${code}'
    GROUP BY 1 ORDER BY n DESC LIMIT 6`);
  const total = rows.reduce((a, r) => a + Number(r.n), 0);
  if (!rows.length) return [];
  const top = rows.map(r => `${r.sci} (${Number(r.n).toLocaleString()})`).join(', ');
  return [{
    icon: '🌍',
    title: `${name} (${code})`,
    text: `${rows.length === 6 ? '6+' : rows.length} species recorded positive · ${Number(total).toLocaleString()} detections · top: ${top}`,
    links: [{ label: 'map', href: `#/map` }],
  }];
}

async function toolPapers(text) {
  const data = await loadJSON('papers', 'data/papers.json');
  const words = new Set((text.toLowerCase().match(/[a-z]{4,}/g) || []).filter(w => !STOP.has(w)));
  if (words.size < 2) return [];
  const scored = [];
  for (const p of data.papers) {
    const hay = (p.title || '').toLowerCase();
    let n = 0;
    for (const w of words) if (hay.includes(w)) n++;
    if (n >= 2) scored.push({ n, p });
  }
  scored.sort((a, b) => b.n - a.n);
  return scored.slice(0, 3).map(({ p }) => ({
    icon: '📄',
    title: p.title,
    text: `${p.year || '?'} · ${p.journal || 'no journal indexed'}${p.summary ? ` · ${String(p.summary).slice(0, 140)}` : ''}`,
    links: [{ label: 'paper', href: `#/papers?paper=${encodeURIComponent(p.id)}` }],
  }));
}

async function toolGlossary(text) {
  const g = await loadJSON('glossary', 'data/glossary.json');
  return (g.entries || [])
    .filter(e => e.abbr && new RegExp(`\\b${esc(e.abbr)}\\b`, 'i').test(text))
    .slice(0, 4)
    .map(e => ({
      icon: '📖',
      title: e.abbr,
      text: e.def,
      links: [{ label: 'glossary', href: `#/glossary?q=${encodeURIComponent(e.abbr)}` }],
    }));
}

/**
 * Run every tool over the user message. Returns:
 *   chips   — compact per-tool hit counts for the header row
 *   items   — STRUCTURED results (title/text/links) for the UI to render;
 *             links are harness-generated, never model-generated
 *   context — plain-text authoritative block for the system prompt
 */
export async function runTools(text) {
  const results = await Promise.allSettled([
    toolGlossary(text), toolGene(text),
    toolSpecies(text), toolPapers(text), toolCountry(text),
  ]);
  const names = ['glossary', 'genes', 'species', 'papers', 'country'];
  const chips = [];
  const items = [];
  results.forEach((r, i) => {
    if (r.status === 'fulfilled' && r.value.length) {
      chips.push({ icon: r.value[0].icon, label: names[i], n: r.value.length });
      items.push(...r.value);
    }
  });
  const context = items.length
    ? `Site data retrieved (authoritative — use these, do not contradict;\nthe user also sees these as cards with links):\n${items.map(it => `${it.title}: ${it.text}`).join('\n')}`
    : '';
  return { chips, items, context };
}

// ---------------------------------------------------------------------------
// Context budgeting + auto-compaction (D123c)
// ---------------------------------------------------------------------------

export const MODEL_CONTEXT_TOKENS = 8192;
export const COMPACTION_THRESHOLD = 0.8;

/** crude but stable estimate for English + JSON-ish text (~4 chars/token) */
export function estimateTokens(str) {
  return Math.ceil(String(str || '').length / 4);
}

/**
 * Auto-compaction: when system + history would exceed threshold of the
 * model context, fold older turns into a single digest message (first
 * sentence of each) and keep as many recent turns as fit the budget.
 * A 135M summarizer would hallucinate — the digest is deterministic.
 */
export function compactHistory(messages, { systemTokens = 0, reservedTokens = 0 } = {}) {
  const budget = Math.floor(MODEL_CONTEXT_TOKENS * COMPACTION_THRESHOLD)
    - systemTokens - reservedTokens;
  let total = messages.reduce((a, m) => a + estimateTokens(m.content), 0);
  if (total <= budget || messages.length <= 2) {
    return { messages, compacted: false, tokens: total };
  }

  // fold everything except the last exchange into a digest
  const lastUser = [...messages].reverse().findIndex(m => m.role === 'user');
  const keepFrom = lastUser === -1 ? messages.length - 1
    : messages.length - lastUser - (messages[lastUser]?.role === 'assistant' ? 2 : 1);
  const head = messages.slice(0, Math.max(1, keepFrom));
  const tail = messages.slice(Math.max(1, keepFrom));

  const digest = head.map(m =>
    `${m.role === 'user' ? 'Q' : 'A'}: ${m.content.split(/(?<=[.!?])\s/)[0].slice(0, 90)}`
  ).join(' | ');
  const compactMsg = {
    role: 'assistant',
    content: `[earlier conversation compacted to fit context — ${head.length} turns folded]\n${digest}`,
    compacted: true,
  };

  let out = [compactMsg, ...tail];
  total = out.reduce((a, m) => a + estimateTokens(m.content), 0);
  // still over budget (single giant turns) — trim oldest of the tail
  while (total > budget && out.length > 2) {
    const dropped = out.splice(1, 1)[0];
    total -= estimateTokens(dropped.content);
  }
  return { messages: out, compacted: true, tokens: total };
}
