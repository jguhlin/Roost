/**
 * a11y_axe.spec.js — standing axe-core gate (Phase 3).
 *
 * Sweeps all 30 canonical routes (same list as scripts/i18n/render_pages.mjs)
 * with @axe-core/playwright. Any violation fails the suite — keep this green
 * by FIXING the issue, not by adding an exclusion. Exclusions must cite a
 * justification comment (third-party widget, data-driven false positive).
 *
 * Run: npx playwright test tests/a11y_axe.spec.js
 */
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { appendFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const REPORT = 'test-results/axe-violations.jsonl';

// DuckDB-matrix routes: slow hydration under suite memory pressure — one
// retry absorbs the occasional timeout (config: heap-hungry pages, workers=1)
test.describe.configure({ retries: 1 });
const SLOW = new Set(['/clade', '/orthogroups', '/anp32', '/phylogeny', '/compare']);

// keep in sync with scripts/i18n/render_pages.mjs ROUTES
const ROUTES = [
  '/', '/species', '/genes', '/model', '/model?tab=spread', '/model-cyto',
  '/spread-cyto', '/spread-layers', '/susceptibility', '/region-risk', '/vaccines', '/genomes', '/map',
  '/papers', '/mutations', '/clade', '/synteny', '/compare', '/blast',
  '/orthogroups', '/anp32', '/phylogeny', '/history', '/numbers',
  '/contradictions', '/landscape', '/research', '/resources', '/methods',
  '/credits', '/downloads', '/glossary', '/press',
];

// Heavy single-page apps: give data-driven pages a moment to render their
// primary content before scanning (axe only checks what is in the DOM).
// NOTE: no networkidle — DuckDB/cytoscape pages hold worker/wasm
// connections open and it may never settle.
async function settle(page) {
  await page.waitForLoadState('load').catch(() => {});
  await page.waitForTimeout(1200);
}

// Per-route axe scoping — each MUST have a justification.
const EXCLUDE = {
  // vendored third-party DAG-viewer bundle (public/viewer/verso-dag-viewer.js):
  // node-label templates are baked into the minified bundle; contrast fixes
  // belong upstream, not in our vendored copy
  '/methods': ['verso-dag-viewer'],
};

// Routes where the scan is INCLUDE-scoped: axe must not walk the huge data
// DOM even to exclude it (clade's matrix alone is ~28k nodes; a full walk
// blew past 4 minutes). Scanning the interactive shell covers the controls,
// landmarks and headings; matrix cells are uniformly generated data.
const INCLUDE = {
  '/clade': ['header', '#clade-controls', 'footer'],
};

// include-scoped routes must WAIT for their page-specific selector — scanning
// a still-loading page would pass vacuously (spinner, no controls)
const WAIT_FOR = {
  '/clade': '#clade-controls',
};

function report(route, scheme, violations) {
  const summary = violations.map(
    (v) => `[${scheme}] ${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(' ')).slice(0, 3).join(' | ')}`
  );
  console.log(`\n=== ${route} violations ===\n${summary.join('\n')}`);
  // machine-readable report for triage (workers=1, append is safe)
  mkdirSync(dirname(REPORT), { recursive: true });
  appendFileSync(REPORT, JSON.stringify({
    route, scheme,
    violations: violations.map((v) => ({
      id: v.id, impact: v.impact, tags: v.tags,
      nodes: v.nodes.map((n) => ({ target: n.target.join(' '), html: (n.html || '').slice(0, 200) })),
    })),
  }) + '\n');
}

for (const route of ROUTES) {
  test(`axe: #${route} (light+dark)`, async ({ page }) => {
    // SLOW routes: a single full axe pass over these DuckDB-table pages
    // measures ~50s (color-contrast forces style resolution per node);
    // light + dark passes + settle need well over the default budget.
    // Page itself hydrates in <10s at a stable DOM size — the cost is
    // axe's walk. (Must be set INSIDE the body — module-level
    // setTimeout in a loop silently doesn't apply.)
    test.setTimeout(SLOW.has(route) ? 240_000 : 60_000);
    await page.goto(`/${route === '/' ? '' : '#' + route}`, { timeout: 45000 });
    await settle(page);
    if (WAIT_FOR[route]) {
      await page.locator(WAIT_FOR[route]).first().waitFor({ timeout: 25000 });
    }

    // document what was scanned (empty pages would otherwise silently pass)
    expect(
      await page.locator('main, #main-content').first().isVisible().catch(() => false),
      'main content rendered'
    ).toBe(true);

    const failures = [];
    // light pass, then dark — dark: variants follow the .dark class synced
    // from prefers-color-scheme (main.js), so emulating re-themes without reload
    for (const scheme of ['light', 'dark']) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.waitForTimeout(150); // repaint
      const builder = new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']);
      if (scheme === 'dark') {
        // axe-core (≤4.14) mis-resolves Tailwind v4's stylesheet oklch
        // backgrounds (reports #efefef) producing false contrast positives;
        // structural rules remain fully checked in dark. Dark contrast pairs
        // are maintained by hand (light/dark class pairs) — see AGENTS.md.
        builder.options({ rules: { 'color-contrast': { enabled: false } } });
      }
      if (INCLUDE[route]) builder.include(INCLUDE[route]);
      else builder.exclude(EXCLUDE[route] ?? []);
      const results = await builder.analyze();

      if (results.violations.length) {
        report(route, scheme, results.violations);
        failures.push(...results.violations.map((v) => `[${scheme}] ${v.id}`));
      }
    }
    expect(failures, `${route}: ${failures.join(', ')}`).toEqual([]);
  });
}
