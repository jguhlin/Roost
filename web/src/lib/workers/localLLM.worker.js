/**
 * localLLM.worker.js (D123b/D126) — SmolLM2 runs INSIDE a Web Worker so
 * generation never blocks the UI thread. Streams token deltas back to the
 * store; main thread stays responsive throughout. The active model is
 * switchable at runtime (135M default; 360M/1.7B opt-in) — switching loads
 * the new pipeline and drops the old reference.
 *
 * Protocol (worker ← main):  {type:'load', model?} | {type:'generate', id, messages, opts}
 * Protocol (worker → main):  {type:'status', ...} | {type:'progress', value}
 *                           | {type:'device', device} | {type:'token', id, delta}
 *                           | {type:'done', id, text} | {type:'error', id?, message}
 */
import { pipeline, TextStreamer, env } from '@huggingface/transformers';

// D127: SELF-HOSTED weights — no HF CDN at runtime. Models live under
// /models/HuggingFaceTB/<model>/ (onnx q8 + tokenizer) and the matching
// onnxruntime-web wasm binaries under /models/wasm/. Vendored by
// scripts/papers/vendor_llm_weights (see web/public/models/). Future dist
// builds pick these up automatically via public/.
env.allowLocalModels = true;
env.allowRemoteModels = false;
env.localModelPath = '/models/';
env.backends.onnx.wasm.wasmPaths = '/models/wasm/';

let pipe = null;
let currentModel = null;
let loadSeq = 0; // D128: switching models supersedes in-flight loads —
                // stale results are discarded instead of stacking downloads

function post(msg) {
  self.postMessage(msg);
}

async function load(model) {
  const my = ++loadSeq;
  post({ type: 'status', status: 'loading', model });
  const opts = (device) => ({
    dtype: 'q8',
    device,
    progress_callback: (p) => {
      if (p?.status === 'progress' && p.total) {
        // tag progress with the model so the store can drop stale streams
        post({ type: 'progress', value: Math.min(1, p.loaded / p.total), model });
      }
    },
  });
  // switching models: drop the old pipeline before allocating the new one
  if (pipe && currentModel !== model) pipe = null;
  currentModel = model;
  let result = null, device = null;
  try {
    result = await pipeline('text-generation', model, opts('webgpu'));
    device = 'webgpu';
  } catch {
    result = await pipeline('text-generation', model, opts('wasm'));
    device = 'wasm';
  }
  if (my !== loadSeq) {
    // superseded by a newer switch — discard this pipeline, post nothing
    result = null;
    return;
  }
  pipe = result;
  post({ type: 'device', device });
  post({ type: 'status', status: 'ready', model });
}

async function generate(id, messages, opts) {
  const {
    maxNewTokens = 80,
    temperature = 0.2,
    topK = 50,
    topP = 0.9,
    repetitionPenalty = 1.1,
  } = opts || {};
  const streamer = new TextStreamer(pipe.tokenizer, {
    skip_prompt: true,
    skip_special_tokens: true,
    callback_function: (delta) => {
      if (delta) post({ type: 'token', id, delta });
    },
  });

  const out = await pipe(messages, {
    max_new_tokens: maxNewTokens,
    temperature,
    do_sample: temperature > 0,
    top_k: topK,
    top_p: topP,
    repetition_penalty: repetitionPenalty,
    streamer,
  });

  const text = out?.[0]?.generated_text;
  let final = '';
  if (Array.isArray(text)) {
    const last = text[text.length - 1];
    final = last?.role === 'assistant' ? (last.content || '') : '';
  } else {
    final = String(text || '');
  }
  post({ type: 'done', id, text: final.trim() });
}

self.onmessage = async (e) => {
  const { type, id, messages, opts, model } = e.data || {};
  try {
    if (type === 'load') {
      await load(model || 'HuggingFaceTB/SmolLM2-135M-Instruct');
    } else if (type === 'generate') {
      if (!pipe || (model && model !== currentModel)) {
        await load(model || currentModel || 'HuggingFaceTB/SmolLM2-135M-Instruct');
        if (!pipe) return; // superseded mid-load; the newer load will post ready
      }
      if (loadSeq && !pipe) return;
      await generate(id, messages, opts);
    }
  } catch (err) {
    post({ type: 'error', id, message: String(err?.message || err).slice(0, 200) });
  }
};
