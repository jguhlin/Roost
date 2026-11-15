<script>
  /**
   * ChatWidget (D123) — floating on-device chat, triggered from the header
   * (icon left of the language switcher). SmolLM2-135M runs entirely in the
   * browser; glossary terms matched in the conversation are injected as
   * grounding context so answers anchor to shipped site data. Experimental
   * and labelled as such; only rendered when the build flag is on.
   */
  import { localLLMEnabled, llm, ensureLLM, llmChat, LLM_MODELS } from '../../stores/localLLM.svelte.js';
  import { runTools, compactHistory, estimateTokens, MODEL_CONTEXT_TOKENS, COMPACTION_THRESHOLD } from '../../stores/chatTools.js';
import { t } from '../../stores/i18n.svelte.js';

  let open = $state(false);
  let messages = $state([]);   // {role: 'user'|'assistant', content}
  let input = $state('');
  let busy = $state(false);
  let streaming = $state('');  // growing assistant text while tokens arrive
  let ctxPct = $state(0);        // est. context usage after last send (D123c)
  let compactedOnce = $state(false);
  let error = $state(null);
  let glossary = [];
  let listEl = $state(null);

  const SYSTEM = 'You are the Roost companion: a small experimental assistant for an avian-influenza host-genomics website, running fully on-device. Answer in 1-3 short sentences at low temperature — stay strictly anchored to the provided site data. When the retrieved data includes a species, point the user to that species page (linked in the card below your answer; e.g. "open the species page linked below for the full gene panel"). Same for gene and paper links when relevant. Admit uncertainty; never invent specific studies, numbers, or species claims.';

  async function openChat() {
    open = true;
    if (!glossary.length) {
      try {
        const r = await fetch('data/glossary.json');
        const d = await r.json();
        glossary = d.entries || [];
      } catch { /* grounding optional */ }
    }
    if (messages.length === 0) {
      messages = [{ role: 'assistant', content: 'Hi! I\u2019m a small experimental model running entirely in your browser (SmolLM2-135M). Ask about avian-immunology terms \u2014 I\u2019ll ground answers in the site glossary. I\u2019m tiny: keep it simple, and trust the site\u2019s data over me.' }];
    }
    ensureLLM().catch(() => {}); // warm start, errors surface on send
  }

  function groundTerms(text) {
    // superseded by runTools (D123d) — stub kept for clarity
    return '';
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    input = '';
    error = null;
    busy = true;
    streaming = '';
    let toolItems = [];
    let context = '';
    try {
      const tools = await runTools(text);
      toolItems = tools.items;
      context = tools.context;
    } catch { /* tools optional — chat still works ungrounded */ }
    messages = [...messages, { role: 'user', content: text, tools: toolItems }];
    try {
      const sys = context ? `${SYSTEM}\n\n${context}` : SYSTEM;

      // auto-compaction: keep the assembled prompt under the 80% threshold
      const systemTokens = estimateTokens(sys);
      const { messages: kept, compacted } = compactHistory(
        messages,
        { systemTokens, reservedTokens: 400 },
      );
      if (compacted) compactedOnce = true;
      const convo = [
        { role: 'system', content: sys },
        ...kept.slice(-6).map(m => ({ role: m.role, content: m.content })),
      ];
      ctxPct = Math.min(100, Math.round(
        convo.reduce((a, m) => a + estimateTokens(m.content), 0)
        / MODEL_CONTEXT_TOKENS * 100));

      const reply = await llmChat(convo, {
        maxNewTokens: 120,
        // D126: tuned defaults come from the store (temp 0.2, top_k 50,
        // top_p 0.9, repetition_penalty 1.1) — grounded paraphrase, not prose
        onToken: (_delta, acc) => { streaming = acc; },
      });
      streaming = '';
      messages = [...messages, {
        role: 'assistant',
        content: reply || '(no output — this tiny model went quiet; try rephrasing)',
      }];
    } catch (e) {
      error = String(e?.message || e).slice(0, 160);
    } finally {
      busy = false;
      streaming = '';
      requestAnimationFrame(() => listEl?.scrollTo?.({ top: 1e6 }));
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }
</script>

{#if localLLMEnabled}
  <!-- trigger sits inline in the header, left of the language switcher -->
  <button
    onclick={openChat}
    title={t('common.chatwidget.on.device.chat.experimental') || 'On-device chat (experimental, SmolLM2-135M — nothing leaves your browser)'}
    class="mr-1 px-1.5 py-1 rounded text-gray-500 dark:text-gray-400 hover:text-violet-600 dark:hover:text-violet-300 hover:bg-violet-50 dark:hover:bg-violet-900/30 transition-colors"
    aria-label={t('chat.open.label')}
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12a8 8 0 0 1-8 8H5l-2 2V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8Z" />
    </svg>
  </button>

  {#if open}
    <div class="fixed bottom-6 right-6 z-50 w-[22rem] h-[30rem] flex flex-col rounded-2xl border border-violet-200 dark:border-violet-800 bg-white dark:bg-gray-800 shadow-2xl" role="dialog" aria-label="On-device chat">
      <div class="flex items-center justify-between gap-2 px-3 py-2 border-b border-violet-100 dark:border-violet-900 rounded-t-2xl bg-violet-50/70 dark:bg-violet-950/30">
        <div class="min-w-0">
          <div class="text-xs font-semibold text-violet-700 dark:text-violet-300">On-device chat</div>
          <div class="text-[10px] text-violet-500 dark:text-violet-400 truncate flex items-center gap-1.5">
            <span>SmolLM2-135M · experimental{llm.device ? ` · ${llm.device}` : ''}</span>
            {#if llm.status === 'loading'}<span>· {Math.round(llm.progress * 100)}%</span>{/if}
            {#if ctxPct}
              <span class="px-1 rounded {ctxPct >= COMPACTION_THRESHOLD * 100 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}"
                title="estimated context usage — auto-compacts at {Math.round(COMPACTION_THRESHOLD * 100)}%">
                ctx {ctxPct}%{compactedOnce ? ' 🧹' : ''}
              </span>
            {/if}
          </div>
        </div>
        <button onclick={() => open = false} class="text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={t('chat.close.label')}>✕</button>
      </div>

      <div bind:this={listEl} class="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {#each messages as m, i}
          {#if m.role === 'user'}
            <div class="max-w-[85%] ml-auto px-2.5 py-1.5 rounded-xl text-sm bg-blue-600 text-white">
              {m.content}
            </div>
            {#if m.tools?.length}
              <!-- tool result cards: harness-generated, links included -->
              <div class="space-y-1 mr-auto max-w-[92%]">
                {#each m.tools as tool}
                  <div class="px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/60 text-xs">
                    <div class="font-medium text-gray-800 dark:text-gray-200">{tool.icon} {tool.title}</div>
                    <div class="text-gray-600 dark:text-gray-400 mt-0.5">{tool.text}</div>
                    {#if tool.links?.length}
                      <div class="flex flex-wrap gap-2 mt-1">
                        {#each tool.links as l}
                          <a href={l.href} class="text-blue-600 dark:text-blue-400 hover:underline">{l.label} →</a>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          {:else}
            <div class="max-w-[85%] mr-auto px-2.5 py-1.5 rounded-xl text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 {m.compacted ? 'italic text-gray-600 dark:text-gray-400 border border-dashed border-gray-300 dark:border-gray-600' : ''}">
              {m.content}
            </div>
          {/if}
        {/each}
        {#if streaming}
          <div class="mr-auto max-w-[85%] px-2.5 py-1.5 rounded-xl text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">
            {streaming}<span class="inline-block w-1.5 h-3.5 ml-0.5 align-middle bg-violet-400 animate-pulse"></span>
          </div>
        {:else if busy}
          <div class="mr-auto flex items-center gap-2 text-xs text-violet-500 dark:text-violet-300 px-1">
            <span class="inline-block w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full animate-spin"></span>
            {llm.status === 'loading' ? `loading model (${Math.round(llm.progress * 100)}%) — first time only` : 'thinking…'}
          </div>
        {/if}
        {#if error}
          <div class="text-xs text-rose-600 dark:text-rose-300 px-1">model unavailable: {error}</div>
        {/if}
      </div>

      <div class="p-2 border-t border-gray-100 dark:border-gray-700 flex gap-2">
        <input
          bind:value={input}
          onkeydown={onKey}
          placeholder={t('common.chatwidget.ask.about.term') || 'Ask about a term…'}
          class="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-300"
        />
        <button
          onclick={send}
          disabled={busy || !input.trim()}
          class="px-3 py-1.5 text-sm rounded-lg bg-violet-600 text-white disabled:opacity-40 hover:bg-violet-700 transition-colors"
        >➤</button>
      </div>
      <div class="px-3 pb-1.5 flex items-center justify-between gap-2">
        <select
          class="text-[10px] rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400 px-1 py-0.5"
          value={llm.model}
          onchange={(e) => ensureLLM(e.currentTarget.value)}
          title={t('common.chatwidget.switch.model.size.loads') || 'Switch model size — loads in the background, conversation stays'}
          aria-label="Model size"
        >
          {#each LLM_MODELS as m}
            <option value={m.id}>{m.label} · {m.size} · {m.hint}</option>
          {/each}
        </select>
        <span class="text-[10px] text-gray-500 dark:text-gray-400">{t('chat.disclaimer')}</span>
      </div>
    </div>
  {/if}
{/if}
