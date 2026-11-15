// Permanent guard: the gene-page "Research Papers" section ships the FULL
// corpus list (no builder-side cap) and paginates client-side. Number-
// agnostic — parses the rendered count so corpus rebuilds don't break it.
// @chromium only, runs against the shared playwright.config.js fixture (:5178).
import { test, expect } from '@playwright/test';

test('gene page research papers: full count + working pagination', async ({ page }) => {
  await page.goto('/#/genes/ANP32A');
  const header = page.getByRole('heading', { name: /Research Papers \(\d+\)/ });
  await expect(header).toBeVisible({ timeout: 20000 });

  // total-mentions line renders alongside the header
  await expect(page.getByText(/total mentions across all papers/)).toBeVisible();

  const n = Number((await header.textContent()).match(/\((\d+)\)/)[1]);

  if (n > 10) {
    // ceil(n/10) pages; controls navigate and page 1 disables prev
    const pages = Math.ceil(n / 10);
    await expect(page.getByText(new RegExp(`Page 1 of ${pages}`))).toBeVisible();
    await expect(page.getByRole('button', { name: '← previous' })).toBeDisabled();
    await page.getByRole('button', { name: 'next →' }).click();
    await expect(page.getByText(new RegExp(`Page 2 of ${pages}`))).toBeVisible();
    await page.getByRole('button', { name: '← previous' }).click();
    await expect(page.getByText(new RegExp(`Page 1 of ${pages}`))).toBeVisible();
  } else {
    // short lists render no pagination controls at all
    await expect(page.getByText(/Page \d+ of \d+/)).toHaveCount(0);
  }
});
