/**
 * On-device LLM (D123, D123b, D126) — optional, lazy, grounded-only, NON-BLOCKING.
 *
 * SmolLM2 (135M default; 360M/1.7B switchable at runtime) runs inside a Web
 * Worker (WebGPU with WASM fallback): the UI thread never executes
 * inference. Feature-flagged via VITE_LOCAL_LLM (dev on, prod off).
 *
 * Generation defaults tuned for a small grounded paraphraser (D126):
 * temperature 0.2, top_k 50, top_p 0.9, repetition_penalty 1.1 — lower
 * temperature keeps it anchored to retrieved site data.
 */
const isBrowser = typeof window !== 'undefined';

export const localLLMEnabled =
  isBrowser && import.meta.env.VITE_LOCAL_LLM === '1';

export const LLM_MODELS = [
  { id: 'HuggingFaceTB/SmolLM2-135M-Instruct', label: '135M', size: '~150 MB', hint: 'fast default' },
  { id: 'HuggingFaceTB/SmolLM2-360M-Instruct', label: '360M', size: '~380 MB', hint: 'sharper answers' },
  { id: 'HuggingFaceTB/SmolLM2-1.7B-Instruct', label: '1.7B', size: '~1.8 GB', hint: 'best, slow on CPU' },
];

export const llm = $state({
  status: 'idle', // idle | loading | ready | error
  progress: 0,    // 0..1 model download progress
  device: null,   // 'webgpu' | 'wasm'
  error: null,
  model: LLM_MODELS[0].id,
});

let worker = null;
let loadResolve = null;
let genCounter = 0;
const pending = new Map(); // id -> {resolve, reject, onToken, acc}

function ensureWorker() {
  if (worker) return worker;
  // D128: the worker ships PRE-BUILT (public/models/worker/llm-worker.js,
  // rebuilt via: npx esbuild src/lib/workers/localLLM.worker.js --bundle
  //   --format=esm --platform=browser --outfile=public/models/worker/llm-worker.js --minify).
  // Routing through Vite's worker pipeline crashed the dev server (the ORT
  // runtime's dynamic imports wedge its module loader); a raw static worker
  // behaves identically in dev and prod and keeps all LLM bytes on /models/.
  worker = new Worker('/models/worker/llm-worker.js', { type: 'module' });
  worker.onmessage = (e) => {
    const m = e.data || {};
    switch (m.type) {
      case 'status':
        if (m.model && m.model !== llm.model && m.status !== 'ready') break; // stale load (D128)
        if (m.model) llm.model = m.model;
        llm.status = m.status;
        if (m.status === 'ready') {
          llm.progress = 1;
          loadResolve?.();
          loadResolve = null;
        }
        break;
      case 'progress':
        if (m.model && m.model !== llm.model) break; // stale load's progress
        llm.progress = m.value;
        break;
      case 'device':
        llm.device = m.device;
        break;
      case 'token': {
        const p = pending.get(m.id);
        if (p) { p.acc += m.delta; p.onToken?.(m.delta, p.acc); }
        break;
      }
      case 'done': {
        const p = pending.get(m.id);
        pending.delete(m.id);
        p?.resolve((p.acc || m.text || '').trim());
        break;
      }
      case 'error': {
        const p = pending.get(m.id);
        if (p) { pending.delete(m.id); p.reject(new Error(m.message)); }
        else {
          llm.status = 'error';
          llm.error = m.message;
          loadResolve?.(new Error(m.message));
          loadResolve = null;
        }
        break;
      }
    }
  };
  return worker;
}

/** Load a model (default the 135M). Switching supersedes any in-flight
    load — the worker discards stale pipelines (D128), so only the newest
    model actually lands. */
export function ensureLLM(modelId) {
  const model = modelId || llm.model;
  if (llm.status === 'ready' && model === llm.model) return Promise.resolve();
  const w = ensureWorker();
  llm.status = 'loading';
  llm.progress = 0;
  llm.model = model;
  w.postMessage({ type: 'load', model });
  return new Promise((resolve, reject) => { loadResolve = resolve; });
}

/**
 * Chat-style generation with streaming. Resolves with the full assistant
 * text; onToken(delta, accumulated) fires per streamed chunk. Generation
 * params (temperature/top_k/top_p/repetition_penalty) pass straight
 * through to the worker.
 */
export async function llmChat(messages, {
  maxNewTokens = 80, temperature = 0.2, topK = 50, topP = 0.9,
  repetitionPenalty = 1.1, onToken,
} = {}) {
  await ensureLLM();
  const id = ++genCounter;
  const w = ensureWorker();
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject, onToken, acc: '' });
    w.postMessage({ type: 'generate', id, messages,
                    opts: { maxNewTokens, temperature, topK, topP, repetitionPenalty } });
  });
}
