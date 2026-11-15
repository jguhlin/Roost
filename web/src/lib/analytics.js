/**
 * Matomo analytics loader — production-only.
 *
 * Gating (all three must hold or this module is a no-op):
 *   1. Hostname is josephguhlin.com or *.josephguhlin.com
 *      (dev on localhost / LAN IPs never tracks)
 *   2. VITE_MATOMO_URL is set (your Matomo instance, e.g. https://matomo.josephguhlin.com/)
 *   3. VITE_MATOMO_SITE_ID is set (the numeric site id in Matomo)
 *
 * Cookieless by default (setCookiesDisabled) — aggregate pageview analytics
 * without consent-banner obligations. Hash-SPA aware: every route change
 * pushes a virtual pageview with its real URL fragment.
 */

const MATOMO_URL = import.meta.env.VITE_MATOMO_URL || '';
const MATOMO_SITE_ID = import.meta.env.VITE_MATOMO_SITE_ID || '';

function isProdHost() {
  if (typeof location === 'undefined') return false;
  return /(^|\.)josephguhlin\.com$/.test(location.hostname);
}

export function initMatomo() {
  if (!MATOMO_URL || !MATOMO_SITE_ID || !isProdHost()) return false;

  /** @type {any} */
  const w = window;
  w._paq = w._paq || [];
  w._paq.push(['setTrackerUrl', `${MATOMO_URL.replace(/\/$/, '')}/matomo.php`]);
  w._paq.push(['setSiteId', String(MATOMO_SITE_ID)]);
  w._paq.push(['disableCookies']);          // cookieless aggregate analytics
  w._paq.push(['enableLinkTracking']);
  w._paq.push(['enableHeartBeatTimer', 15]); // accurate visit duration (SPA)
  w._paq.push(['trackPageView']);

  const script = document.createElement('script');
  script.async = true;
  script.src = `${MATOMO_URL.replace(/\/$/, '')}/matomo.js`;
  document.head.appendChild(script);

  // Hash-SPA: each ROUTE change is a virtual pageview. Deferred a tick so
  // the new document.title has rendered; param-only changes (map camera,
  // filters, tabs) are not fresh pageviews.
  let lastTrackedRoute = location.hash.split('?')[0];
  const trackRoute = () => {
    setTimeout(() => {
      const route = location.hash.split('?')[0];
      if (route === lastTrackedRoute) return;
      lastTrackedRoute = route;
      w._paq.push(['setCustomUrl', location.href]);
      w._paq.push(['trackPageView', document.title]);
    }, 100);
  };
  window.addEventListener('hashchange', trackRoute);
  return true;
}

/** @type {any} */
const w = () => /** @type {any} */ (typeof window !== 'undefined' ? window : {});

/** Custom event — no-op unless Matomo is active (production).
 *  trackEvent('Gene', 'view', 'ANP32A')
 *  @param {string} category @param {string} action @param {string} [name] @param {number} [value] */
export function trackEvent(category, action, name, value) {
  const _paq = w()._paq;
  if (_paq) {
    _paq.push(['trackEvent', category, action, name, value]);
  }
}

/** Site-search with category + result count — no-op in dev.
 *  trackSearch('species-genes', 'RIG', 3)
 *  @param {string} category @param {string} keyword @param {number} [resultsCount] */
export function trackSearch(category, keyword, resultsCount) {
  const _paq = w()._paq;
  if (_paq) {
    _paq.push(['trackSiteSearch', keyword, category, resultsCount]);
  }
}
