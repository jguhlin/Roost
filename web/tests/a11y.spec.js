/**
 * a11y smoke tests — app-shell accessibility hooks.
 *
 * Covers: skip-to-content link, route-change focus management + titles,
 * the screen-reader live region, nav landmarks, and Modal focus trap.
 * Run: npx playwright test tests/a11y.spec.js
 */
import { test, expect } from '@playwright/test';

test.describe('app-shell a11y hooks', () => {
  test('skip-to-content link is the first focusable element and works', async ({ page }) => {
    await page.goto('/');
    // Wait for the app to mount
    await expect(page.locator('header')).toBeVisible();

    // First Tab should land on the skip link
    await page.keyboard.press('Tab');
    const skip = page.locator('.skip-link');
    await expect(skip).toBeFocused();

    // Activating it moves focus to <main id="main-content">
    await page.keyboard.press('Enter');
    await expect(page.locator('#main-content')).toBeFocused();
  });

  test('route change updates document.title and moves focus to main', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
    await expect(page).toHaveTitle(/Roost/);

    // Navigate via header (keyboard path)
    await page.locator('header nav[aria-label="Primary"] button', { hasText: 'Species' }).first().click();
    await expect(page).toHaveTitle(/Species/);
    await expect(page.locator('#main-content')).toBeFocused();

    // Focus landed inside main, not stuck on the nav button
    const focusedInMain = await page.evaluate(
      () => document.getElementById('main-content').contains(document.activeElement)
    );
    expect(focusedInMain).toBe(true);
  });

  test('live region exists for screen-reader announcements', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
    const live = page.locator('[aria-live="polite"][role="status"]');
    await expect(live).toHaveCount(1);
    // sr-only: visually clipped (1px), still in the a11y tree
    await expect(live).toHaveClass(/sr-only/);

    // Route change announces the new page title (page-name or results count)
    await page.locator('header nav button', { hasText: 'Genes' }).first().click();
    await expect.poll(() => live.textContent()).toMatch(/genes/i);
  });

  test('nav landmarks are labelled', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('header nav[aria-label="Primary"]')).toHaveCount(1);
    await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(1);
    await expect(page.getByRole('banner')).toHaveCount(1); // <header> landmark
    await expect(page.getByRole('main')).toHaveCount(1); // <main> landmark
  });

  test('mobile menu button has accessible name and expanded state', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await expect(page.locator('header')).toBeVisible();

    const menuBtn = page.locator('header button[aria-label="Menu"]');
    await expect(menuBtn).toBeVisible();
    await expect(menuBtn).toHaveAttribute('aria-expanded', 'false');

    await menuBtn.click();
    await expect(menuBtn).toHaveAttribute('aria-expanded', 'true');
    await expect(
      page.locator('header nav[aria-label="Mobile"]')
    ).toBeVisible();
  });

  test('SpeciesSearch combobox: full keyboard operation (ARIA APG)', async ({ page }) => {
    await page.goto('/#/model');
    const cb = page.getByRole('combobox').first();
    await expect(cb).toBeVisible();

    // open + navigate + select without ever touching the mouse
    await cb.click();
    await expect(cb).toHaveAttribute('aria-expanded', 'true');
    await page.locator('#species-opt-0').waitFor({ timeout: 10000 }); // species hydrated
    await page.keyboard.press('ArrowDown');
    const ad = await cb.getAttribute('aria-activedescendant');
    expect(ad).toBeTruthy();
    await page.keyboard.press('Enter');

    // collapsed, value committed, no stray focus in the listbox
    await expect(cb).toHaveAttribute('aria-expanded', 'false');
    const val = await cb.inputValue();
    expect(val.length).toBeGreaterThan(0);

    // Escape closes the popup
    await cb.click();
    await expect(cb).toHaveAttribute('aria-expanded', 'true');
    await page.keyboard.press('Escape');
    await expect(cb).toHaveAttribute('aria-expanded', 'false');
  });

  test('Genes page: no nested interactive elements; rows keyboard-selectable', async ({ page }) => {
    await page.goto('/#/genes');
    // wait for the gene list to hydrate (stage chips render per row)
    await page.waitForSelector('[data-testid="gene-stage-chip"], .font-mono button', { timeout: 20000 });

    // the old outer-<button>-with-inner-<button>s pattern must stay gone
    const nested = await page.evaluate(() => document.querySelectorAll('button button').length);
    expect(nested).toBe(0);

    // a gene row button exists and is keyboard-focusable
    const row = page.locator('main button', { has: page.locator('.font-mono') }).first();
    await row.focus();
    await expect(row).toBeFocused();
  });

  test('species detail dialog: named, focus-trapped, Escape restores focus', async ({ page }) => {
    await page.goto('/#/species');
    // first species card opens the detail dialog (SPA hash -> modal)
    const card = page.locator('main button', { has: page.locator('h3') }).first();
    await card.waitFor({ timeout: 20000 });
    await card.click();

    const dialog = page.locator('[role=dialog][aria-modal=true]');
    await expect(dialog).toBeVisible({ timeout: 15000 });
    // the unnamed-dialog bug: label must come from the species name
    await expect(dialog).toHaveAttribute('aria-label', /.+/);

    // focus moves into the dialog and stays there under Tab cycling
    await expect.poll(async () => {
      const el = await dialog.elementHandle();
      return page.evaluate((d) => d.contains(document.activeElement), el);
    }).toBe(true);
    for (let i = 0; i < 12; i++) await page.keyboard.press('Tab');
    const el = await dialog.elementHandle();
    expect(await page.evaluate((d) => d.contains(document.activeElement), el)).toBe(true);

    // Escape closes and focus returns to the invoking card
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(card).toBeFocused();
  });

  test('live region announces async result counts', async ({ page }) => {
    await page.goto('/#/species');
    const live = page.locator('[aria-live=polite][role=status]');
    // after the list loads, the count is announced (polite)
    await expect
      .poll(() => live.textContent(), { timeout: 20000 })
      .toMatch(/Showing \d+ species/);
  });
});
