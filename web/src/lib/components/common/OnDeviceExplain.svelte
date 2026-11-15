<script>
  /**
   * OnDeviceExplain (D123) — experimental in-browser paraphrase of a
   * glossary term, grounded on the shipped definition. SmolLM2-135M runs
   * locally (WebGPU/WASM); nothing leaves the browser. Output is labelled
   * experimental; the definition beside it stays authoritative.
   */
  import { localLLMEnabled, llm, ensureLLM, llmChat } from '../../stores/localLLM.svelte.js';
import { t } from '../../stores/i18n.svelte.js';

  let { abbr = '', definition = '' } = $props();

  let open = $state(false);
  let busy = $state(false);
  let answer = $state(null);
  let error = $state(null);

  async function explain() {
    open = true;
    error = null;
    answer = null;
    busy = true;
    try {
      await ensureLLM();
      const reply = await llmChat([
        { role: 'system', content: 'You rewrite technical glossary definitions as one short plain-language sentence for a curious non-specialist. Use ONLY the provided definition — never add facts.' },
        { role: 'user', content: `Term: ${abbr}\nDefinition: ${definition}\nPlain-language sentence:` },
      ], { maxNewTokens: 60, temperature: 0.2 });
      answer = reply || '(model returned nothing — the definition above is the reference)';
    } catch (e) {
      error = String(e?.message || e).slice(0, 160);
    } finally {
      busy = false;
    }
  }
</script>

{#if localLLMEnabled}
  <button
    onclick={explain}
    title="{t('ondevice.paraphrase.title') || 'Experimental: paraphrase this definition with a small LLM running entirely in your browser (SmolLM2-135M). First use downloads ~150 MB, cached afterwards.'}"
    class="shrink-0 text-[10px] px-1.5 py-0.5 rounded border border-violet-200 dark:border-violet-800 text-violet-600 dark:text-violet-300 hover:bg-violet-50 dark:hover:bg-violet-900/30 transition-colors"
  >🧪 explain</button>

  {#if open}
    <div class="w-full mt-1.5 rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50/60 dark:bg-violet-950/20 px-3 py-2">
      {#if busy}
        <div class="text-xs text-violet-600 dark:text-violet-300 flex items-center gap-2">
          <span class="inline-block w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full animate-spin"></span>
          {llm.status === 'loading'
            ? `loading SmolLM2-135M on-device (${Math.round(llm.progress * 100)}%)${llm.device ? ' · ' + llm.device : ''}… first time only`
            : 'thinking…'}
        </div>
      {:else if error}
        <div class="text-xs text-rose-600 dark:text-rose-300">on-device model unavailable: {error}</div>
        <div class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{t('common.ondeviceexplain.the.definition.above.remains') || 'the definition above remains the reference'}</div>
      {:else if answer}
        <p class="text-sm text-gray-700 dark:text-gray-200">{answer}</p>
        <p class="text-[10px] text-violet-500/80 dark:text-violet-300/70 mt-1">
          experimental · generated on-device (SmolLM2-135M{llm.device ? ', ' + llm.device : ''}) · may be imprecise — the definition is authoritative
        </p>
      {/if}
    </div>
  {/if}
{/if}
