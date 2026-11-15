/**
 * Phylogeny gene-overlay tests — guards the absence-confidence ladder
 * (scientific-consistency pass 2026-11-10):
 *   - the gene overlay banner splits absent counts into high-confidence
 *   - the legend distinguishes high vs low/medium confidence non-detections
 *   - DDX58 must show high-confidence absences (gamebird loss) while
 *     IFITM3 must show none (its non-detections are all low-confidence —
 *     never presentable as established losses).
 */
import { test, expect } from '@playwright/test';

const BANNER = /GENE OVERLAY/;

async function openOverlay(page, gene) {
  await page.goto(`/#/phylogeny?gene=${gene}&overlaytest=1`, { waitUntil: 'domcontentloaded' });
  // The banner renders with the route (no data needed); the counts + tree
  // colours need the DuckDB gene_presence parquet (heavy on cold load).
  await expect(page.locator('main').getByText(BANNER)).toBeVisible({ timeout: 30000 });
}

async function highConfCount(page) {
  // the counts line renders "N absent (M high-confidence) · K species with
  // calls" — inline text nodes, so use getByText (substring semantics)
  const counts = page.getByText(/\(\d+ high-confidence\)/);
  await expect(counts).toBeVisible({ timeout: 60000 });
  const m = (await counts.innerText()).match(/\((\d+) high-confidence\)/);
  return Number(m[1]);
}

test.describe('phylogeny gene overlay', () => {
  test('legend separates high vs low/medium confidence non-detections', async ({ page }) => {
    await openOverlay(page, 'DDX58');
    const main = page.locator('main');
    await expect(main.getByText('Not found — high confidence')).toBeVisible({ timeout: 60000 });
    await expect(main.getByText(/Not found — low\/medium confidence/)).toBeVisible();
  });

  test('DDX58 banner reports high-confidence absence count', async ({ page }) => {
    await openOverlay(page, 'DDX58');
    // the web twin carries 36 high-confidence DDX58 non-detections after
    // alias merge + rollup (39 in the raw per-assembly parquet)
    expect(await highConfCount(page)).toBeGreaterThanOrEqual(30);
  });

  test('IFITM3 banner reports zero high-confidence absences', async ({ page }) => {
    await openOverlay(page, 'IFITM3');
    expect(await highConfCount(page)).toBe(0);
  });
});
