/**
 * a11y store — screen-reader announcement channel.
 *
 * App.svelte renders `getLiveMessage()` inside a visually-hidden
 * `role="status" aria-live="polite"` region. Any code (pages, components,
 * workers) can call `announce(msg)` to surface async state changes to
 * assistive tech: "Loading…", "1,245 species found", "BLAST complete".
 *
 * Svelte 5 runes module — must keep the `.svelte.js` extension.
 */

let liveMessage = $state('');

/**
 * Announce a message to screen readers via the app-wide live region.
 * Identical consecutive messages are re-announced by clearing first
 * (aria-live regions deduplicate unchanged text).
 * @param {string} message
 */
export function announce(message) {
  liveMessage = '';
  requestAnimationFrame(() => {
    liveMessage = message;
  });
}

/** Current live-region text (rendered by App.svelte). */
export function getLiveMessage() {
  return liveMessage;
}
