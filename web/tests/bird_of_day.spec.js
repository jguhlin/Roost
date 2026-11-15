/**
 * bird_of_day.spec.js — Bird of the Day card (2026-11).
 *
 * The homepage card must show the deterministic pick for today:
 *   candidates[floor(UTCms / 86400000) % candidates.length]
 * computed independently here from the shipped artifact. Also guards the
 * 18 core-panel tiles, the status counts, and the species deep-link.
 */
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

const doc = JSON.parse(readFileSync('public/data/bird_of_the_day.json', 'utf8'));
const pick = doc.candidates[Math.floor(Date.now() / 86400000) % doc.candidates.length];

test('Bird of the Day shows the deterministic pick with its core panel', async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto('/', { timeout: 45000 });
  const card = page.locator('[data-testid="bird-of-the-day"]');
  await card.waitFor({ timeout: 30000 });

  // same species everywhere today (sci name, case-insensitive)
  await expect(card).toContainText(pick.sci, { ignoreCase: true });

  // all 18 core-panel genes as tiles
  const tiles = card.locator('a[aria-label]');
  expect(await tiles.count()).toBe(doc.genes.length);
  for (const g of doc.genes) {
    await expect(card.locator(`a[aria-label^="${g.s}:"]`)).toHaveCount(1);
  }

  // status counts match the artifact's status string
  const counts = {
    P: [...pick.st].filter((c) => c === 'P').length,
    F: [...pick.st].filter((c) => c === 'F').length,
    A: [...pick.st].filter((c) => c === 'A').length,
  };
  await expect(card).toContainText(`${counts.P} present`);
  await expect(card).toContainText(`${counts.F} fragment`);
  await expect(card).toContainText(`${counts.A} absent`);

  // deep links go to the dedicated full page (modal route fails for
  // genome-only species): name → overview, CTA → genes tab
  const full = `#/species-full/${encodeURIComponent(pick.sci)}`;
  await expect(card.locator(`a[href="${full}"]`)).toHaveCount(1);
  await expect(card.locator(`a[href="${full}?tab=genes"]`)).toHaveCount(1);
});
