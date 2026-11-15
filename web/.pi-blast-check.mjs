import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9348');
const page = await browser.contexts()[0].newPage();
await page.bringToFront();
await page.setViewportSize({ width: 1600, height: 1000 });
page.setDefaultTimeout(40000);
const errs = [];
page.on('pageerror', (e) => errs.push(String(e).slice(0, 200)));
await page.goto('http://127.0.0.1:8795/#/blast', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(5000);
// load example + search
await page.locator('button', { hasText: 'Load example: chicken MX1' }).click();
await page.waitForTimeout(300);
const seqLen = await page.locator('span.text-xs.text-gray-400.ml-auto').textContent();
await page.locator('button', { hasText: '⚡ Search' }).click();
await page.waitForTimeout(12000);
const res = await page.evaluate(() => {
  const txt = document.body.innerText;
  const rows = [...document.querySelectorAll('table tbody tr')].filter(tr => !tr.textContent.includes('Q'));
  const firstRow = rows[0]?.textContent.replace(/\s+/g, ' ').trim();
  return {
    ready: !txt.includes('Loading WASM'),
    nHits: txt.match(/^(\d+) hits?/m)?.[1],
    bestMatch: txt.match(/Best match:[^\n]*/)?.[0]?.slice(0, 90),
    firstRow,
    navBLAST: [...document.querySelectorAll('nav button')].some(b => b.textContent.trim() === 'BLAST'),
  };
});
console.log('blast page:', JSON.stringify(res, null, 1));
// expand an alignment
await page.locator('table tbody button', { hasText: 'align' }).first().click();
await page.waitForTimeout(600);
const aln = await page.evaluate(() => {
  const block = document.querySelector('.rounded-lg.bg-gray-50.font-mono, .rounded-lg.bg-gray-50');
  return { hasAlignment: !!block, head: block?.innerText.slice(0, 120).replace(/\n/g, ' | ') };
});
console.log('alignment:', JSON.stringify(aln));
console.log('pageerrors:', errs.length ? errs.slice(0, 3) : 'none');
await browser.close();
console.log('DONE');
