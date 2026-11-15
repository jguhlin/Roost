#!/usr/bin/env node
/* Render every route in a locale and dump visible text for LLM leak-audit.
 * Usage: node scripts/i18n/render_pages.mjs <base_url> <locale> [out_dir]
 * Uses playwright-core + system chromium (channel or executablePath).
 */
import { createRequire } from 'module';
const require = createRequire(new URL('../../web/package.json', import.meta.url));
const { chromium } = require('playwright-core');
import { mkdirSync, writeFileSync } from 'fs';

const [,, baseUrl, locale, outDir] = process.argv;
if (!baseUrl || !locale) {
  console.error('usage: node render_pages.mjs <base_url> <locale> [out_dir]');
  process.exit(1);
}
const OUT = outDir || `/tmp/i18n_pages/${locale}`;
mkdirSync(OUT, { recursive: true });

const ROUTES = [
  '/', '/species', '/genes', '/model', '/model?tab=spread', '/model-cyto',
  '/spread-cyto', '/spread-layers', '/susceptibility', '/region-risk', '/vaccines', '/genomes', '/map', '/papers',
  '/mutations',
  '/clade', '/synteny', '/compare', '/blast', '/orthogroups', '/anp32',
  '/phylogeny', '/history', '/numbers', '/contradictions', '/landscape',
  '/research', '/resources', '/methods', '/credits', '/downloads', '/glossary', '/press',
];

const exe = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';

const browser = await chromium.launch({
  executablePath: exe,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
const ctx = await browser.newContext({ viewport: { width: 1400, height: 2400 } });
const page = await ctx.newPage();
page.on('pageerror', (e) => { /* tolerate runtime errors; we want the rendered text */ });

// load home first, click the locale button (EXACT match — substring 'ES'
// would hit Species/Genes/Genomes nav buttons and navigate away)
await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle', timeout: 45000 });
const locBtn = page.locator(`header button`).filter({ hasText: new RegExp(`^\\s*${locale.toUpperCase()}\\s*$`) }).first();
try {
  await locBtn.click({ timeout: 8000 });
} catch {
  console.error(`locale button ${locale.toUpperCase()} not found`);
}
await page.waitForTimeout(1500);

for (const route of ROUTES) {
  const name = route.replace(/^\//, '').replace(/[/?&=]/g, '_') || 'home';
  try {
    await page.goto(`${baseUrl}/#${route}`, { waitUntil: 'networkidle', timeout: 45000 });
    // wait for real content: some routes (methods/numbers/…) sit chrome-only for
    // seconds while DuckDB-WASM initializes — a fixed delay undercaptures them.
    await page.waitForFunction(() => document.body.innerText.length > 900, { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(600); // let async data + remount settle
    // dismiss obvious modals/drawers if any (best effort)
    const text = await page.evaluate(() => document.body.innerText);
    writeFileSync(`${OUT}/${name}.txt`, text);
    console.log(`✓ ${route} (${text.length} chars)`);
  } catch (e) {
    console.error(`✗ ${route}: ${String(e).slice(0, 80)}`);
  }
}
await browser.close();
console.log(`done → ${OUT}`);
