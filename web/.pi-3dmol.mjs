import { chromium } from 'playwright';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9346');
const page = await browser.contexts()[0].newPage();
await page.bringToFront();
await page.setViewportSize({ width: 1600, height: 1000 });
page.setDefaultTimeout(40000);
const errs = [];
page.on('pageerror', (e) => errs.push(String(e).slice(0, 200)));
const logs = [];
page.on('console', (m) => { if (m.type() === 'error') logs.push(m.text().slice(0, 150)); });

// gene page with a structure (ANP32A)
await page.goto('http://127.0.0.1:8793/#/genes/ANP32A', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(12000); // CDN 3Dmol + RCSB pdb fetch + render
const res = await page.evaluate(() => {
  const card = [...document.querySelectorAll('h2')].find(h => h.textContent.includes('3D Structure'));
  if (!card) return { found: false };
  const container = card.closest('div.bg-white, div[class*="rounded"]');
  const canvas = container?.querySelector('canvas');
  const btns = [...(container?.querySelectorAll('button') || [])].map(b => b.textContent.trim());
  const bodyHasLoading = container?.textContent.includes('Loading');
  const lib3d = typeof window['$3Dmol'] !== 'undefined';
  return {
    found: true, hasCanvas: !!canvas, canvasW: canvas?.width, canvasH: canvas?.height,
    lib3dLoaded: lib3d, buttons: btns.slice(0, 8), loading: bodyHasLoading,
    pdbLink: [...(container?.querySelectorAll('a') || [])].map(a => a.href).filter(h => h.includes('rcsb')).slice(0, 2),
  };
});
console.log('3D card:', JSON.stringify(res, null, 1));
// canvas painted? (WebGL toDataURL)
const painted = await page.evaluate(() => {
  const c = document.querySelector('h2') && [...document.querySelectorAll('canvas')].find(x => x.width > 100 && x.height > 100);
  if (!c) return { found: false };
  try { const u = c.toDataURL('image/png'); return { found: true, kb: Math.round(u.length / 1024), painted: u.length > 12000 }; }
  catch (e) { return { found: true, err: String(e).slice(0, 80) }; }
});
console.log('canvas paint:', JSON.stringify(painted));

// compare link on species list
await page.goto('http://127.0.0.1:8793/#/species', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(6000);
const link = await page.evaluate(() => {
  const a = [...document.querySelectorAll('a')].find(x => x.textContent.includes('Compare species'));
  return { found: !!a, href: a?.getAttribute('href') };
});
console.log('species list compare link:', JSON.stringify(link));
console.log('pageerrors:', errs.length ? errs.slice(0, 3) : 'none');
console.log('console errors:', logs.length ? logs.slice(0, 3) : 'none');
await browser.close();
console.log('DONE');
