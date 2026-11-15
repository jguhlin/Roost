/**
 * BLAST worker — runs the WASM blastp kernel off the main thread.
 * Receives the wasm bytes + reference DB once, then executes queries.
 */
import init, { init_db, search } from '../wasm/blast/roost_blast.js';

let ready = false;

self.onmessage = async (e) => {
  const { type } = e.data;
  if (type === 'init') {
    const { wasm, entries } = e.data;
    await init(wasm);
    const n = init_db(entries);
    ready = true;
    self.postMessage({ type: 'ready', n });
  } else if (type === 'search') {
    const { query, maxHits } = e.data;
    if (!ready) {
      self.postMessage({ type: 'error', message: 'kernel not initialised' });
      return;
    }
    const t0 = performance.now();
    const hits = search(query, maxHits || 20);
    self.postMessage({
      type: 'done',
      ms: Math.round(performance.now() - t0),
      hits: Array.from(hits, (h) => JSON.parse(h)),
    });
  }
};
