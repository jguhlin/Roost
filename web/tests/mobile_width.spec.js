/**
 * mobile_width.spec.js — standing mobile-width overflow gate (2026-11).
 *
 * Every canonical route must render without horizontal overflow at phone
 * width (390px). Catches the grid/flex `min-width:auto` + nowrap(truncate)
 * class that blew Genes out to 2491px and Mutations to 4901px
 * (user-reported 2026-11-04) — a template edit can regress it silently.
 *
 * What is measured:
 *   - documentElement.scrollWidth — the user-visible scroll. The root has
 *     overflow-x:clip as a guard, so this exceeding the viewport means the
 *     GUARD itself regressed (e.g. someone replaced clip with visible).
 *   - body.scrollWidth — the scrollable overflow region. Stays honest even
 *     under the clip guard: phantom overflow (wide shadow-DOM canvases like
 *     the vendored verso-dag-viewer, unbreakable tokens) shows up here.
 * Both must be ≤ innerWidth + 1 (rounding). Content inside intended scroll
 * containers (mermaid diagrams, wrapped tables, mermaid-wrap) does NOT
 * propagate — those are excluded by the ancestor-overflow walk.
 *
 * On failure the message names the widest unclipped element for triage.
 *
 * Run: npx playwright test tests/mobile_width.spec.js
 */
import { test, expect } from '@playwright/test';

// DuckDB-matrix routes: slow hydration under suite memory pressure — one
// retry absorbs the occasional timeout (same policy as a11y_axe.spec.js)
test.describe.configure({ retries: 1 });

// keep in sync with tests/a11y_axe.spec.js + scripts/i18n/render_pages.mjs
const ROUTES = [
  '/', '/species', '/genes', '/model', '/model?tab=spread', '/model-cyto',
  '/spread-cyto', '/spread-layers', '/susceptibility', '/region-risk', '/vaccines', '/genomes', '/map',
  '/papers', '/mutations', '/clade', '/synteny', '/compare', '/blast',
  '/orthogroups', '/anp32', '/phylogeny', '/history', '/numbers',
  '/contradictions', '/landscape', '/research', '/resources', '/methods',
  '/credits', '/downloads', '/glossary', '/press',
];

// Heavy single-page apps need longer to render their primary content
// (no networkidle: DuckDB/cytoscape pages hold worker connections open)
const SLOW = new Set(['/clade', '/orthogroups', '/anp32', '/phylogeny', '/compare']);

async function settle(page, route) {
  await page.waitForLoadState('load').catch(() => {});
  await page.waitForFunction(
    () => document.body && document.body.innerText.length > 200,
    { timeout: 20000 }
  ).catch(() => {}); // still measure: a failing render is a different test's job
  await page.waitForTimeout(SLOW.has(route) ? 2500 : 1200);
}

for (const route of ROUTES) {
  test(`mobile width: ${route}`, async ({ page }) => {
    // must be INSIDE the body (module-level setTimeout in a loop is a no-op)
    test.setTimeout(SLOW.has(route) ? 120_000 : 60_000);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/${route === '/' ? '' : '#' + route}`, { timeout: 45000 });
    await settle(page, route);

    const m = await page.evaluate(() => {
      // widest element right-edge NOT inside a scroll container — the triage
      // hint. (getBoundingClientRect ignores clipping, so elements under
      // auto/scroll/hidden/clip ancestors are skipped: their geometry never
      // reaches the page's scrollable region.)
      let maxRight = 0, worst = '';
      for (const el of document.querySelectorAll('*')) {
        let p = el.parentElement, contained = false;
        while (p && p !== document.documentElement) {
          const ox = getComputedStyle(p).overflowX;
          if (ox !== 'visible') { contained = true; break; }
          p = p.parentElement;
        }
        if (contained) continue;
        const r = el.getBoundingClientRect();
        if (r.right > maxRight) {
          maxRight = r.right;
          worst = `${el.tagName}.${String(el.className).slice(0, 60)}`;
        }
      }
      return {
        inner: window.innerWidth,
        html: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
        worst: `${worst} @${Math.round(maxRight)}px`,
      };
    });

    const limit = m.inner + 1; // 1px subpixel/rounding slack
    expect(
      m.html,
      `html.scrollWidth ${m.html} > viewport ${m.inner} on ${route} — the overflow-x:clip guard may have regressed. Widest unclipped: ${m.worst}`
    ).toBeLessThanOrEqual(limit);
    expect(
      m.body,
      `body.scrollWidth ${m.body} > viewport ${m.inner} on ${route} — real horizontal overflow (check min-w-0 on grid/flex items holding truncate text, wrap wide elements in overflow-x-auto). Widest unclipped: ${m.worst}`
    ).toBeLessThanOrEqual(limit);
  });
}
