<script>
import { t } from '../../stores/i18n.svelte.js';
  /**
   * InfoDot — ⓘ icon with a real hover/focus tooltip.
   * Replaces native `title` attributes (slow to appear, unstyleable,
   * invisible on touch) for short explanatory text.
   *
   * Props:
   *   text   — tooltip content (dot is not rendered without it)
   *   align  — 'center' | 'left' — horizontal alignment of the bubble
   */
  export let text = '';
  export let align = 'left';
</script>

{#if text}
  <span class="relative inline-flex group align-baseline">
    <span
      class="cursor-help text-gray-500 dark:text-gray-400 select-none hover:text-blue-600 dark:hover:text-blue-400"
      tabindex="0"
      role="button"
      aria-label={t('tip.info.more') || 'More information'}
    >ⓘ</span>
    <span
      class="pointer-events-none absolute top-full mt-1.5 z-50 w-64 px-3 py-2 rounded-lg bg-gray-900 text-white dark:bg-gray-600 text-xs font-normal leading-relaxed text-left shadow-lg whitespace-normal break-words
        {align === 'center' ? 'left-1/2 -translate-x-1/2' : align === 'right' ? 'right-0' : 'left-0'}
        opacity-0 invisible group-hover:opacity-100 group-hover:visible group-focus-within:opacity-100 group-focus-within:visible transition-opacity duration-150"
      role="tooltip"
    >{text}</span>
  </span>
{/if}
