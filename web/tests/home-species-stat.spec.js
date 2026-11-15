// Guard: home hero species stat = birds + "+n mammals" annotation, from stats.json.
// Regression for the tc()-vs-t() bug where the mammal note silently rendered nothing.
import { test, expect } from '@playwright/test';

test('home species stat shows birds count plus mammals annotation', async ({ page }) => {
  await page.goto('/');
  const r = await page.evaluate(() => fetch('data/stats.json').then(x => x.json()));
  const stat = page.locator('div.text-3xl.text-green-700, div.text-3xl.dark\\:text-green-400').first();
  await expect(stat).toBeVisible({ timeout: 20000 });
  const text = (await stat.textContent()).trim();
  // e.g. "656 +62 mammals" — birds number, then the plus-annotation
  expect(text).toMatch(new RegExp(`^${r.species_birds}\\s*\\+${r.species_mammals}\\s*\\S+`));
});
