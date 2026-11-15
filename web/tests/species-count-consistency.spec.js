// Guard: species-count consistency across pages. Home hero = birds + "+n mammals"
// from stats.json; Numbers detected = birds + mammals; Methods IUCN coverage
// matches the iucn_status.json artifact (no stale hardcoded 682/719).
import { test, expect } from '@playwright/test';

test('IUCN coverage numbers on Methods match the artifact', async ({ page }) => {
  const [iucn, res] = await Promise.all([
    page.request.get('/data/species/iucn_status.json').then(r => r.json()),
    page.goto('/#/methods'),
  ]);
  const cats = {};
  for (const v of Object.values(iucn.status)) cats[v] = (cats[v] || 0) + 1;
  const body = await page.locator('body').innerText();
  await expect(page.getByText(/Conservation status \(IUCN\)/)).toBeVisible({ timeout: 20000 });
  const want = `${iucn.meta.n_matched} of ${iucn.meta.n_species} catalogue species are assessed`;
  expect(body).toContain(want);
  expect(body).toContain(`(${cats.LC} LC · ${cats.NT} NT · ${cats.VU} VU · ${cats.EN} EN)`);
  // the stale hardcode must be gone
  expect(body).not.toContain('682 of 719');
});

test('Downloads iucn description is data-driven', async ({ page }) => {
  const [stats, ,] = await Promise.all([
    page.request.get('/data/stats.json').then(r => r.json()),
    page.goto('/#/downloads'),
  ]);
  await expect(page.getByText('iucn_status.json').first()).toBeVisible({ timeout: 20000 });
  const body = await page.locator('body').innerText();
  expect(body).toContain(`${stats.iucn_species} of ${stats.species} catalogue species assessed`);
  expect(body).not.toContain('682 of 719');
});
