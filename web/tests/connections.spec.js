import { test, expect } from '@playwright/test';

/**
 * Connection-mining frontend acceptance (D78 item 30).
 *
 * Real review state is all-pending by design, so approved-data paths are
 * exercised through route interception: the published relationship file is
 * fulfilled with a synthetic approved edge. The real file on disk is never
 * touched.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REAL_REL = JSON.parse(
  readFileSync(path.join(__dirname, '../public/data/gene_relationships.json'), 'utf8'));

const SYNTH_EDGE = {
  from: 'STAT1', to: 'MX1', mechanism: 'activation', label: 'activates',
  source: 'curated+reviewed',
  evidence: [
    {
      paper_id: 'anp32_independent2024', year: 2024, journal: 'bioRxiv',
      quote: 'STAT1 activates MX1 transcription after IFN stimulation',
      species: 'chicken (Gallus gallus)', stage: 'middle',
      location: 'nucleus', timepoints: '12 hpi', evidence_type: 'experimental',
    },
    {
      paper_id: 'duck_mda52014', year: 2014, journal: 'J Virol',
      quote: 'STAT1-dependent MX1 induction restricts H5N1 replication',
      species: 'duck', stage: 'middle', location: '', timepoints: '24 hpi',
      evidence_type: 'experimental',
    },
  ],
};

const SYNTH_NEW_GENE_EDGE = {
  // endpoint outside the focused model AND without a stage assignment →
  // neutral top-level node behind the extended-panel toggle
  from: 'OASL', to: 'ABCB10', mechanism: 'binding', label: 'binds',
  source: 'reviewed',
  evidence: [
    {
      paper_id: 'anp32_independent2024', year: 2024, journal: 'bioRxiv',
      quote: 'ABCB10 transport complexes associate with OASL during infection',
      species: 'human', stage: 'unclear', location: 'cytosol',
      timepoints: '', evidence_type: 'experimental',
    },
  ],
};

// the real file already carries STAT1→MX1 activation (curated); replace it so
// edge ids stay unique (the real export aggregates by from/to/mechanism)
// core-to-core edge with human-only evidence: dims under the duck/chicken
// selector but never hides (dim-not-hide acceptance)
const SYNTH_HUMAN_CORE_EDGE = {
  from: 'MAVS', to: 'IRF3', mechanism: 'activation', label: 'activates',
  source: 'reviewed',
  evidence: [
    {
      paper_id: 'anp32_independent2024', year: 2024, journal: 'bioRxiv',
      quote: 'MAVS-dependent IRF3 activation proceeds in reconstituted cells',
      species: 'human', stage: 'middle', location: '', timepoints: '',
      evidence_type: 'experimental',
    },
  ],
};

function edgesWithSyntheticRealReplaced(...synth) {
  const keys = new Set(synth.map((e) => `${e.from}|${e.to}|${e.mechanism}`));
  return [...REAL_REL.edges.filter((e) =>
    !keys.has(`${e.from}|${e.to}|${e.mechanism}`)), ...synth];
}

function relWith(edges, extra = {}) {
  return {
    version: 1, generated: 'test',
    counts: { edges: edges.length },
    stage_proposals: {}, location_overlay: {},
    edges, ...extra,
  };
}

async function serveRel(page, payload = REAL_REL) {
  await page.route('**/data/gene_relationships.json', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });
}

test('canonical alias routing: #/genes/RIG-I lands on the DDX58 record', async ({ page }) => {
  await serveRel(page);
  await page.goto('/#/genes/RIG-I');
  await page.waitForSelector('h1');
  await expect(page.locator('h1')).toHaveText(/^DDX58$/);
  await expect(page.getByTestId('view-in-pathway')).toHaveCount(1);
});

test('list cards show stage chip and the subtle no-reviewed-connections state', async ({ page }) => {
  // zero approved evidence in the intercepted file → the subtle state must
  // appear everywhere regardless of what the real review has approved
  await serveRel(page, relWith([]));
  await page.goto('/#/genes');
  await page.waitForSelector('[data-testid="no-connections-chip"]', { timeout: 20000 });
  // DDX58 has a stage assignment (sensing) — its row shows the stage chip.
  // (a11y restructure 2026-10-08: chips are siblings of the gene-name
  // button inside the card, no longer nested inside it)
  const ddx = page.locator('button', { hasText: 'DDX58' }).first();
  await expect(ddx.locator('xpath=../*/*[@data-testid="gene-stage-chip"]')).toHaveCount(1);
  // with zero approvals every host card shows the subtle state
  const chips = await page.locator('[data-testid="no-connections-chip"]').count();
  expect(chips).toBeGreaterThan(20);
});

test('gene page connection section cites supporting papers (approved data only)', async ({ page }) => {
  await serveRel(page, relWith(edgesWithSyntheticRealReplaced(SYNTH_EDGE)));
  await page.goto('/#/genes/MX1');
  await page.waitForSelector('[data-testid="gene-connections-section"]', { timeout: 20000 });
  const section = page.locator('[data-testid="gene-connections-section"]');
  // counterpart link + mechanism label + citation with species/timepoint context
  await expect(section.locator('a[href="#/genes/STAT1"]').first()).toBeVisible();
  await expect(section).toContainText('activates');
  await expect(section.locator('a[href="#/papers/anp32_independent2024"]').first()).toBeVisible();
  await expect(section).toContainText('12 hpi');
});

test('approved evidence drives the connection badge on list cards', async ({ page }) => {
  test.slow(); // DuckDB init under full-suite heap pressure
  // isolated payload: only the synthetic edge → deterministic badge numbers
  await serveRel(page, relWith([SYNTH_EDGE]));
  await page.goto('/#/genes');
  await page.locator('input[placeholder="Search genes by symbol, name, or alias..."]').fill('STAT1');
  await page.waitForTimeout(400);
  // scope to the STAT1 row so pagination/hidden sections cannot interfere
  // a11y restructure 2026-10-08: the badge lives in the card footer,
  // a sibling of the gene-name button (no longer nested inside it)
  const badge = page.locator('button', { hasText: 'STAT1' })
    .locator('xpath=../..//*[@data-testid="connection-count-badge"]');
  await expect(badge).toBeVisible({ timeout: 20000 });
  await expect(badge).toContainText(/connection/);
  await expect(badge).toHaveAttribute('title', /2 evidence records/);
});

test('pathway deep link centers the gene and the tooltip shows reviewed provenance', async ({ page }) => {
  test.slow(); // deep-link + relayout under full-suite load exceeds the default budget
  await serveRel(page, relWith(edgesWithSyntheticRealReplaced(SYNTH_EDGE)));
  await page.goto('/#/model-cyto?gene=STAT1');
  await page.waitForFunction(() => window.__cy?.nodes('[kind = "gene"]').length > 0);
  await page.waitForFunction(
    () => window.__cy?.nodes('.focused').first()?.data('id2') === 'STAT1',
    null, { timeout: 20000 },
  );
  await page.waitForTimeout(700); // let the centering animation settle (pan/zoom hides tooltips)
  const tooltip = page.getByTestId('edge-tooltip');
  // pan/zoom events during settling can dismiss the hover — re-emit until it sticks
  for (let attempt = 0; attempt < 4; attempt++) {
    await page.evaluate(() =>
      window.__cy.getElementById('E:STAT1-MX1-activation').emit('mouseover'));
    try {
      await expect(tooltip).toContainText('STAT1', { timeout: 1500 });
      break;
    } catch (e) {
      if (attempt === 3) throw e;
    }
  }
  await expect(tooltip).toContainText('MX1');
  await expect(page.getByTestId('edge-provenance')).toContainText('curated+reviewed');
  await expect(page.getByTestId('edge-evidence-count')).toContainText('2');
  const citations = page.getByTestId('edge-citations');
  await expect(citations).toContainText('bioRxiv');
});

test('species selector highlights exact-species evidence and dims other-species evidence', async ({ page }) => {
  await serveRel(page, relWith(edgesWithSyntheticRealReplaced(SYNTH_EDGE, SYNTH_NEW_GENE_EDGE, SYNTH_HUMAN_CORE_EDGE)));
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.nodes('[kind = "gene"]').length > 0);
  // species picker is the SpeciesSearch combobox now (old #species-context
  // select was replaced). NOTE: scope by name — this page has FIVE combobox
  // roles (gene input with list=, three selects, this one)
  const combo = page.getByRole('combobox', { name: 'Compare a species…' });
  await combo.click();
  await combo.fill('gallus');
  await page.locator('#species-search-list li[role="option"]', { hasText: 'Gallus gallus' }).first().click();
  await page.waitForTimeout(300);
  const styled = await page.evaluate(() => ({
    match: window.__cy.edges('.ev-species-match').map((e) => e.data('label')),
    mismatch: window.__cy.edges('.ev-species-mismatch').map((e) => e.data('label')),
  }));
  // chicken-evidence edge highlighted; human-only evidence dimmed, not hidden
  expect(styled.match).toContain('activates');
  expect(styled.mismatch).toContain('binds');
  const dimmed = await page.evaluate(() =>
    window.__cy.getElementById('E:MAVS-IRF3-activation').visible());
  expect(dimmed).toBe(true);
  await expect(page.getByTestId('species-evidence-legend')).toBeVisible();
});

test('reviewed edges create neutral top-level nodes behind the extended panel toggle', async ({ page }) => {
  await serveRel(page, relWith(edgesWithSyntheticRealReplaced(SYNTH_NEW_GENE_EDGE)));
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.nodes('[kind = "gene"]').length > 0);
  // hidden until the toggle
  let visible = await page.evaluate(() =>
    window.__cy.getElementById('G:ABCB10').visible());
  expect(visible).toBe(false);
  await page.getByRole('button', { name: 'Extended panel' }).click();
  await page.waitForTimeout(500);
  visible = await page.evaluate(() =>
    window.__cy.getElementById('G:ABCB10').visible());
  expect(visible).toBe(true);
  const stage = await page.evaluate(() =>
    window.__cy.getElementById('G:ABCB10').data('stage'));
  expect(stage).toBe('NEUTRAL');
});

test('unlinked counts derive from the published relationship data', async ({ page }) => {
  // intercept with an EMPTY relationship file: every model gene becomes unlinked
  await serveRel(page, relWith([]));
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.nodes('[kind = "gene"]').length > 0);
  await page.waitForTimeout(600);
  const stats = await page.evaluate(() => ({
    pathway: window.__cy.nodes('.pathway-node').filter((n) => n.data('kind') === 'gene').length,
    unlinked: window.__cy.nodes('.unlinked-node').length,
  }));
  // no published edges → only viral genes stay connected via membership edges
  expect(stats.unlinked).toBeGreaterThan(30);
});
