<script>
  import { onMount } from 'svelte';
  import { t } from '../../stores/i18n.svelte.js';

  // Props
  let { open = false, onclose, title = '', ariaLabel = '', size = 'lg', children } = $props();

  // a11y: unique id so aria-labelledby can point at the dialog title
  const titleId = `modal-title-${Math.random().toString(36).slice(2)}`;
  let dialogEl = $state(null);
  let previouslyFocused = null;

  // Escape key to close (focus is trapped inside the dialog, but keep the
  // window listener as a belt-and-braces path)
  onMount(() => {
    const handleKeydown = (e) => {
      if (e.key === 'Escape' && open && onclose) {
        onclose();
      }
    };
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });

  // a11y focus management: move focus into the dialog when it opens,
  // restore it to the invoking element when it closes.
  $effect(() => {
    if (open) {
      previouslyFocused = document.activeElement;
      const raf = requestAnimationFrame(() => dialogEl?.focus());
      return () => {
        cancelAnimationFrame(raf);
        if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
          previouslyFocused.focus();
        }
        previouslyFocused = null;
      };
    }
  });

  // a11y: trap Tab navigation inside the dialog while it is open
  function handleTabTrap(e) {
    if (e.key !== 'Tab' || !dialogEl) return;
    const focusables = dialogEl.querySelectorAll(
      'a[href], button:not([disabled]), textarea, input:not([type="hidden"]), select, [tabindex]:not([tabindex="-1"])'
    );
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  // Prevent scroll when modal is open
  $effect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  });

  // Size classes
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-6xl'
  };
</script>

{#if open}
  <!-- Backdrop: mousedown (not click) so dragging a text selection that
       ends outside the dialog doesn't dismiss it; keyboard users have
       Escape and the labelled close button. -->
  <div
    class="fixed inset-0 bg-black/50 z-50 flex items-start justify-center p-4 overflow-y-auto"
    role="presentation"
    onmousedown={(e) => { if (e.target === e.currentTarget && onclose) onclose(); }}
  >
    <!-- Modal content -->
    <div
      bind:this={dialogEl}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
      aria-label={title ? undefined : (ariaLabel || undefined)}
      tabindex="-1"
      onkeydown={handleTabTrap}
      class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full {sizeClasses[size] || sizeClasses.lg} my-8 max-h-[90vh] overflow-y-auto focus:outline-none"
    >
      <!-- Header -->
      {#if title || onclose}
        <div class="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between z-10">
          {#if title}
            <h2 id={titleId} class="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
          {:else}
            <div></div>
          {/if}
          {#if onclose}
            <button
              onclick={onclose}
              aria-label={t('a11y.close')}
              class="p-1 rounded-md text-gray-600 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          {/if}
        </div>
      {/if}

      <!-- Body -->
      <div class="px-6 py-4">
        {@render children?.()}
      </div>
    </div>
  </div>
{/if}
