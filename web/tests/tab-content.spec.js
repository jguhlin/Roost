/**
 * Tab & panel content tests — guards the pattern route-level axe can't
 * cover: content that renders only on interaction (tabs, modals, filters).
 * Born from the eraDesignations incident (route passed while the panel
 * was blank behind the error boundary) and the s/sp destructuring bug
 * (all tabs broken, route-level scan green).
 */
import { test, expect } from '@playwright/test';

test.describe('interactive panel content', () => {
  test('spread-layers: all four tabs render their content', async ({ page }) => {
    await page.goto('/#/spread-layers?tabtest=1', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(8000);
    // findings teaser above tabs (synthesis data)
    const main = page.locator('main');
    await expect(main.getByText(/months median detection lag/i)).toBeVisible();
    for (const name of ['Eras', 'Host competence', 'Measured dynamics', 'Corpus synthesis']) {
      await page.getByRole('tab', { name: new RegExp(name, 'i') }).click();
      await page.waitForTimeout(1200);
      await expect(main.locator('[role="tabpanel"]:visible')).toContainText(/\w/);
    }
    // the synthesis tab must show findings + a ledger, not an empty panel
    await page.getByRole('tab', { name: /Corpus synthesis/i }).click();
    await page.waitForTimeout(1200);
    await expect(main.getByText(/What the corpus reveals/i)).toBeVisible();
  });

  test('competence risk card opens with vaccination + impact sections', async ({ page }) => {
    await page.goto('/#/spread-layers?cardtest=1', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(8000);
    await page.getByRole('tab', { name: /Host competence/i }).click();
    await page.waitForTimeout(1500);
    await page.locator('#competence-search').fill('Gallus');
    await page.waitForTimeout(800);
    await page.locator('tbody tr').first().click();
    await page.waitForTimeout(1500);
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(/how the score was reached|vaccination evidence/i);
  });

  test('vaccines page renders outcomes + campaign layers', async ({ page }) => {
    await page.goto('/#/vaccines?vtest=1', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(8000);
    const main = page.locator('main');
    await expect(main.getByText(/outcomes reported working/i)).toBeVisible();
    await expect(main.getByText(/Campaign history/i)).toBeVisible();
  });

  test('susceptibility: overview table + dedicated species page', async ({ page }) => {
    await page.goto('/#/susceptibility?sustest=1', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(6000);
    await expect(page.locator('tbody tr').first()).toBeVisible();
    await page.locator('tbody tr a').first().click();
    await page.waitForTimeout(2500);
    await expect(page.locator('main')).toContainText(/permissiveness/i);
    await expect(page.locator('main')).toContainText(/how the score was reached/i);
  });
});
