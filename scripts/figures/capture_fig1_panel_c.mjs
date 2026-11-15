#!/usr/bin/env node
/* Figure 1 · Panel C capture — deterministic, geometry-anchored screenshots.
 *
 * Captures from the running dev server (default http://localhost:5177):
 *   explorer_main  · #/anp32    — paralogue cards + insert-sequence strip
 *   explorer_table · #/anp32    — per-species insert table (top rows)
 *   papers_inset   · #/genes/ANP32A — literature-evidence card (papers list)
 *
 * Everything is placed/anchored from DOM getBoundingClientRect() geometry so
 * make_fig1.py can map callout anchors into SVG coordinates without any
 * pixel inspection. Output: figures/src/assets/fig1c/{*.png, geometry.json}
 *
 * Usage: node scripts/figures/capture_fig1_panel_c.mjs [base_url]
 */
import { mkdirSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
// playwright-core is installed under web/ — resolve it from there regardless
// of where this script is invoked from.
const { chromium } = createRequire(join(ROOT, 'web', 'package.json'))('playwright-core');
const OUT = join(ROOT, 'figures', 'src', 'assets', 'fig1c');
const BASE = process.argv[2] || 'http://localhost:5177';
const DPR = 2;
const VIEWPORT = { width: 1550, height: 4200 };  // tall → every clip inside the viewport;
                                                // width → 3100 px wide captures

mkdirSync(OUT, { recursive: true });

const exe = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';
const browser = await chromium.launch({
  executablePath: exe,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--force-color-profile=srgb'],
});

const ctx = await browser.newContext({
  viewport: VIEWPORT,
  deviceScaleFactor: DPR,
  // fresh context → light theme (site has no prefers-color-scheme handling)
});
const page = await ctx.newPage();

// 3D-structure viewers fetch large remote models we neither show nor need —
// block their hosts so the page settles fast and cleanly.
await ctx.route(/alphafold\.ebi\.ac\.uk|rcsb\.org/, r => r.abort());
page.on('pageerror', () => {});   // tolerate unrelated runtime noise

const pad = 10;
const geometry = { base: BASE, dpr: DPR, viewport: VIEWPORT, captures: {} };

function record(name, { clip, anchors, url, note }) {
  geometry.captures[name] = {
    clip: { x: clip.x, y: clip.y, w: clip.width, h: clip.height },
    anchors, url, note,
  };
}

async function settle(ms = 1600) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(ms);
}

/* ---------------------------------------------------------------- #/anp32 */
await page.goto(`${BASE}/?figcap=${Date.now()}#/anp32`, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForSelector('text=Per-species insert', { timeout: 30000 });
await settle();

// Hide the 3D structures card: heavy, remote-dependent, outside every crop —
// hiding also pulls the sections we DO capture closer together.
await page.evaluate(() => {
  const h2s = [...document.querySelectorAll('h2')];
  const st = h2s.find(h => /structures/i.test(h.textContent || ''));
  (st?.closest('.bg-white') || st?.parentElement)?.style.setProperty('display', 'none');
});
await page.waitForTimeout(250);

const anpBoxes = await page.evaluate(() => {
  const box = el => { const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height }; };
  const byText = (sel, re) =>
    [...document.querySelectorAll(sel)].find(e => re.test(e.textContent || ''));
  const cards = [...document.querySelectorAll('.bg-white.rounded-xl')];
  const paralogGrid = cards[0]?.parentElement;            // grid of A/B/E cards
  const stripCard = byText('h2', /insert sequence/i)?.closest('.bg-white');
  const tableCard = byText('h2', /per-species insert/i)?.closest('.bg-white');
  const mechLine = [...document.querySelectorAll('div')]
    .find(d => /polymerase co-factor/i.test(d.textContent || '') &&
               d.textContent.length < 90);
  const stripH2 = byText('h2', /insert sequence/i);
  return {
    paralogGrid: paralogGrid ? box(paralogGrid) : null,
    stripCard: stripCard ? box(stripCard) : null,
    mechLine: mechLine ? box(mechLine) : null,
    stripH2: stripH2 ? box(stripH2) : null,
    tableCard: tableCard ? box(tableCard) : null,
  };
});
if (!anpBoxes.paralogGrid || !anpBoxes.stripCard || !anpBoxes.tableCard)
  throw new Error('anp32 geometry incomplete: ' + JSON.stringify(anpBoxes));

// main: paralogue cards + sequence strip
const mainClip = {
  x: anpBoxes.paralogGrid.x - pad,
  y: anpBoxes.paralogGrid.y - pad,
  width: anpBoxes.paralogGrid.w + 2 * pad,
  height: (anpBoxes.stripCard.y + anpBoxes.stripCard.h + pad) - (anpBoxes.paralogGrid.y - pad),
};
await page.screenshot({ path: join(OUT, 'explorer_main.png'), clip: mainClip });
record('explorer_main', {
  clip: mainClip,
  url: `${BASE}/#/anp32`,
  note: 'paralogue cards + insert-sequence strip (structures card hidden)',
  anchors: {
    mechanism: anpBoxes.mechLine ? {
      x: anpBoxes.mechLine.x + anpBoxes.mechLine.w / 2 - mainClip.x,
      y: anpBoxes.mechLine.y + anpBoxes.mechLine.h / 2 - mainClip.y,
    } : null,
    comparative: anpBoxes.stripH2 ? {
      x: anpBoxes.stripH2.x + Math.min(anpBoxes.stripH2.w / 2, 220) - mainClip.x,
      y: anpBoxes.stripH2.y + anpBoxes.stripH2.h / 2 - mainClip.y,
    } : null,
  },
});

// table: per-species insert grid, header + first rows
const tableClip = {
  x: anpBoxes.tableCard.x - pad,
  y: anpBoxes.tableCard.y - pad,
  width: anpBoxes.tableCard.w + 2 * pad,
  height: 300,
};
await page.screenshot({ path: join(OUT, 'explorer_table.png'), clip: tableClip });
record('explorer_table', {
  clip: tableClip,
  url: `${BASE}/#/anp32`,
  note: 'per-species insert table (top 300 px)',
  anchors: {},
});

/* ------------------------------------------------------- #/genes/ANP32A */
await page.goto(`${BASE}/?figcap=${Date.now()}#/genes/ANP32A`, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForSelector('h2:text-matches("literature evidence", "i")', { timeout: 30000 });
await settle();

const evBoxes = await page.evaluate(() => {
  const box = el => { const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height }; };
  const h2 = [...document.querySelectorAll('h2')]
    .find(e => /literature evidence/i.test(e.textContent || ''));
  const card = h2?.closest('.bg-white');
  const subtitle = [...card.querySelectorAll('p')]
    .find(e => /what the research corpus says/i.test(e.textContent || ''));
  return { card: card ? box(card) : null,
           subtitle: subtitle ? box(subtitle) : null };
});
if (!evBoxes.card || !evBoxes.subtitle) throw new Error('gene evidence card not found');

// tight band: card header + subtitle ("N papers, M mechanism edges") + first
// mechanism rows — enough to read as the record's evidence view in print.
const evClip = {
  x: evBoxes.card.x - pad,
  y: evBoxes.card.y - pad,
  width: evBoxes.card.w + 2 * pad,
  height: 215,
};
await page.screenshot({ path: join(OUT, 'papers_inset.png'), clip: evClip });
record('papers_inset', {
  clip: evClip,
  url: `${BASE}/#/genes/ANP32A`,
  note: 'literature-evidence card (header + mechanisms + first papers)',
  anchors: {
    evidence: {
      x: evBoxes.subtitle.x + evBoxes.subtitle.w / 2 - evClip.x,
      y: evBoxes.subtitle.y + evBoxes.subtitle.h / 2 - evClip.y,
    },
  },
});

await browser.close();

writeFileSync(join(OUT, 'geometry.json'), JSON.stringify(geometry, null, 2));
for (const [name, c] of Object.entries(geometry.captures)) {
  console.log(`✓ ${name}  ${Math.round(c.clip.w)}×${Math.round(c.clip.h)} css px `
    + `(→ ${Math.round(c.clip.w * DPR)}×${Math.round(c.clip.h * DPR)} px)`);
}
console.log(`geometry → figures/src/assets/fig1c/geometry.json`);
