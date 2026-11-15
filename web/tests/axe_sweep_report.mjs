/**
 * axe_sweep_report.mjs — standalone aggregation of axe violations across all
 * routes. Usage: node tests/axe_sweep_report.mjs [baseUrl]
 * Prints: ruleId (impact) ×count — routes affected, plus one sample node.
 */
import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const BASE = process.argv[2] || 'http://localhost:5178';
const ROUTES = [
  '/', '/species', '/genes', '/model', '/model?tab=spread', '/model-cyto',
  '/spread-cyto', '/vaccines', '/genomes', '/map', '/papers', '/mutations',
  '/clade', '/synteny', '/compare', '/blast', '/orthogroups', '/anp32',
  '/phylogeny', '/history', '/numbers', '/contradictions', '/landscape',
  '/research', '/resources', '/methods', '/credits', '/downloads', '/glossary',
];

const browser = await chromium.launch();
const ctx = await browser.newContext();
const page = await ctx.newPage();
const agg = {}; // ruleId -> {impact, count, routes:Set, sample}

for (const route of ROUTES) {
  try {
    await page.goto(`${BASE}${route === '/' ? '' : '#' + route}`, { timeout: 45000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(900);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    for (const v of results.violations) {
      agg[v.id] ??= { impact: v.impact, count: 0, routes: new Set(), sample: v.nodes[0]?.html?.slice(0, 160) };
      agg[v.id].count += v.nodes.length;
      agg[v.id].routes.add(route);
    }
    console.error(`scanned ${route} (${results.violations.length} rules)`);
  } catch (e) {
    console.error(`FAILED ${route}: ${String(e).slice(0, 120)}`);
  }
}
await browser.close();

for (const [id, a] of Object.entries(agg).sort((x, y) => y[1].count - x[1].count)) {
  console.log(`\n${id} (${a.impact}) ×${a.count} on ${a.routes.size} routes`);
  console.log(`  routes: ${[...a.routes].join(' ')}`);
  console.log(`  sample: ${a.sample}`);
}
