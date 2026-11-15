<script>
  /**
   * SpeciesSearch (D125) — searchable species picker for the model pages.
   * 254 species in a <select> is unusable; filter-as-you-type combobox
   * (scientific OR common name), keyboard navigable, ARIA combobox pattern
   * (ARIA APG): the input owns keyboard focus; options are addressed via
   * aria-activedescendant and are individually keyboard-activable as a
   * fallback for assistive tech that moves focus into the listbox.
   * bind:value carries the scientific name.
   */
  import { t } from '../../stores/i18n.svelte.js';
  import { normalizeText } from '../../stores/search.js';

  let {
    value = $bindable(null),
    species = [],
    commonNames = {},
    placeholder = 'Search species…',
    allowEmpty = true,
    emptyLabel = '— none (model only) —',
    onPick = null,
  } = $props();

  let query = $state('');
  let open = $state(false);
  let active = $state(-1);
  let wrap = $state(null);
  let inputEl = $state(null);

  function labelOf(sp) { return commonNames[sp] || sp; }

  let matches = $derived.by(() => {
    const q = normalizeText(query.trim());
    if (!q) return species.slice(0, 10);
    const starts = [], contains = [];
    for (const sp of species) {
      const sci = normalizeText(sp);
      const com = normalizeText(commonNames[sp] || '');
      const hitStarts = sci.startsWith(q) || sci.includes(' ' + q) || com.startsWith(q);
      const hitContains = sci.includes(q) || com.includes(q);
      if (hitStarts) starts.push(sp);
      else if (hitContains) contains.push(sp);
      if (starts.length > 12) break;
    }
    return [...starts, ...contains].slice(0, 10);
  });

  function choose(sp) {
    value = sp;
    query = '';
    open = false;
    active = -1;
    onPick?.(sp);
    inputEl?.blur();
  }

  function onKey(e) {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) { open = true; return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, matches.length - 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, allowEmpty ? -1 : 0); }
    else if (e.key === 'Enter' && open) {
      e.preventDefault();
      // active === -1 selects the empty option (when offered)
      if (active >= 0) choose(matches[active]);
      else if (allowEmpty) choose(null);
    } else if (e.key === 'Escape') { open = false; active = -1; }
  }

  /** option activation when focus somehow lands on an option element */
  function optionKey(e, sp) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(sp); }
  }

  function onDocClick(e) {
    if (wrap && !wrap.contains(e.target)) { open = false; active = -1; }
  }
  $effect(() => {
    document.addEventListener('click', onDocClick);
    return () => document.removeEventListener('click', onDocClick);
  });
</script>

<div class="relative min-w-[13rem]" bind:this={wrap}>
  <input
    bind:this={inputEl}
    type="text"
    role="combobox"
    aria-expanded={open}
    aria-haspopup="listbox"
    aria-autocomplete="list"
    aria-controls="species-search-list"
    aria-activedescendant={open
      ? (active >= 0 ? `species-opt-${active}` : (allowEmpty ? 'species-opt-empty' : undefined))
      : undefined}
    placeholder={placeholder}
    value={open ? query : (value ? labelOf(value) : '')}
    onfocus={() => { open = true; active = -1; query = ''; }}
    oninput={() => { open = true; active = -1; query = inputEl?.value || ''; }}
    onkeydown={onKey}
    class="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 w-full"
  />
  {#if value && !open}
    <button
      class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xs"
      title={t('common.clear.selection')}
      aria-label={t('common.clear.selection')}
      onclick={() => choose(null)}
    >✕</button>
  {/if}
  {#if open}
    <ul id="species-search-list" role="listbox"
        class="absolute z-30 mt-1 w-full max-h-64 overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-lg">
      {#if allowEmpty}
        <li role="option" id="species-opt-empty" aria-selected={value == null} tabindex="-1"
            class="px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer {active === -1 ? 'bg-blue-50 dark:bg-blue-900/30' : ''}"
            onclick={() => choose(null)} onkeydown={(e) => optionKey(e, null)} onmouseenter={() => active = -1}>{emptyLabel}</li>
      {/if}
      {#each matches as sp, i}
        <li role="option" id="species-opt-{i}" aria-selected={value === sp} tabindex="-1"
            class="px-3 py-1.5 text-sm text-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer {active === i ? 'bg-blue-50 dark:bg-blue-900/30' : ''}"
            onclick={() => choose(sp)} onkeydown={(e) => optionKey(e, sp)} onmouseenter={() => active = i}>
          {labelOf(sp)} <span class="text-gray-500 dark:text-gray-400 text-xs italic">({sp})</span>
        </li>
      {/each}
      {#if !matches.length}
        <li class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">{t('species.search.no.matches')}</li>
      {/if}
    </ul>
  {/if}
</div>
