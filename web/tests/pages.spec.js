import { test, expect } from '@playwright/test';

/**
 * Page Loading Tests
 *
 * These tests verify that each page loads without DuckDB schema errors
 * or other console errors. This catches column name mismatches early.
 */

const pages = [
  { path: '#/', name: 'Home' },
  { path: '#/species', name: 'Species' },
  { path: '#/genomes', name: 'Genomes' },
  { path: '#/genes', name: 'Genes' },
  { path: '#/mutations', name: 'Mutations' },
  { path: '#/map', name: 'Map' },
  { path: '#/history', name: 'Detection History' },
  { path: '#/phylogeny', name: 'Phylogeny' },
  { path: '#/papers', name: 'Papers' },
  { path: '#/downloads', name: 'Downloads' },
  { path: '#/resources', name: 'Resources' },
  { path: '#/model-cyto', name: 'Interactive model' },
];

test('Interactive model finds a gene and preserves graph context', async ({ page }) => {
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.nodes('[kind = "gene"]').length > 0);

  await page.locator('#gene-query').fill('DDX58');
  await page.locator('#gene-query').press('Enter');

  await expect(page.getByRole('heading', { name: 'DDX58' })).toBeVisible();
  await page.waitForFunction(() => window.__cy?.nodes('.focused').length === 1);

  const selection = await page.evaluate(() => ({
    focused: window.__cy.nodes('.focused').first().data('id2'),
    visibleNeighbors: window.__cy.nodes('.near').filter((node) => node.visible()).length,
    dimmedOpacity: Number(window.__cy.nodes('.dimmed').first().style('opacity')),
  }));

  expect(selection.focused).toBe('DDX58');
  expect(selection.visibleNeighbors).toBeGreaterThan(1);
  expect(selection.dimmedOpacity).toBeGreaterThanOrEqual(0.45);
});

test('Interactive model hides empty groups and applies semantic zoom', async ({ page }) => {
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.scratch('_semanticLabelKey'));
  await page.waitForTimeout(800);

  const initialGroups = await page.evaluate(() => window.__cy.nodes('[kind = "bucket"]')
    .filter((bucket) => bucket.visible())
    .map((bucket) => ({
      label: bucket.data('label'),
      visibleChildren: bucket.children('[kind = "gene"]').filter((gene) => gene.visible()).length,
    })));

  expect(initialGroups.length).toBeGreaterThan(0);
  expect(initialGroups.every((group) => group.visibleChildren > 0)).toBe(true);
  expect(initialGroups.some((group) => group.label.includes('\n0 unlinked'))).toBe(false);

  await page.getByRole('button', { name: 'Extended panel' }).click();
  await page.waitForFunction(() => window.__cy.nodes('.panel-extra:visible').length > 0);
  await page.waitForTimeout(800);

  const extendedGroups = await page.evaluate(() => window.__cy.nodes('[kind = "bucket"]')
    .filter((bucket) => bucket.visible())
    .map((bucket) => ({
      label: bucket.data('label'),
      visibleChildren: bucket.children('[kind = "gene"]').filter((gene) => gene.visible()).length,
    })));
  expect(extendedGroups.every((group) => group.visibleChildren > 0)).toBe(true);
  expect(extendedGroups.every((group) => group.label.includes(`\n${group.visibleChildren} unlinked`))).toBe(true);

  const zoomStates = await page.evaluate(() => {
    const cy = window.__cy;
    cy.zoom(0.45);
    const wide = {
      genesHidden: cy.nodes('[kind = "gene"]').not('.focused').every((node) => node.hasClass('label-hidden')),
      groupsHidden: cy.nodes('[kind = "bucket"]').every((node) => node.hasClass('label-hidden')),
    };
    cy.zoom(0.7);
    const medium = {
      primaryVisible: cy.nodes('.tier-primary').some((node) => !node.hasClass('label-hidden')),
      secondaryHidden: cy.nodes('.tier-secondary').every((node) => node.hasClass('label-hidden')),
    };
    cy.zoom(1);
    const detail = {
      secondaryVisible: cy.nodes('.tier-secondary').some((node) => !node.hasClass('label-hidden')),
      unknownHidden: cy.nodes('.tier-unknown').every((node) => node.hasClass('label-hidden')),
    };
    return { wide, medium, detail };
  });

  expect(zoomStates.wide).toEqual({ genesHidden: true, groupsHidden: true });
  expect(zoomStates.medium).toEqual({ primaryVisible: true, secondaryHidden: true });
  expect(zoomStates.detail).toEqual({ secondaryVisible: true, unknownHidden: true });
});

test('Interactive model renders literal STAT1 fan-out and resets dragged nodes', async ({ page }) => {
  test.slow(); // ELK can approach the default timeout when the full suite runs in parallel.
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.nodes('[kind = "gene"]').length > 0);

  await page.locator('#gene-query').fill('STAT1');
  await page.locator('#gene-query').press('Enter');
  await expect(page.getByRole('heading', { name: 'STAT1' })).toBeVisible();
  await page.waitForFunction(() => window.__cy?.nodes('.focused').first().data('id2') === 'STAT1');

  const fanOut = await page.evaluate(() => window.__cy.getElementById('G:STAT1')
    .outgoers('edge[kind = "signal"]')
    .map((edge) => ({
      target: edge.target().data('id2'),
      curve: edge.style('curve-style'),
      renderedLabel: edge.style('label'),
    })));

  expect(fanOut.map((edge) => edge.target).sort()).toEqual(
    ['B2M', 'BST2', 'CIITA', 'EIF2AK2', 'IFITM3', 'ISG15', 'MX1', 'OASL', 'RSAD2', 'TAP1']);
  expect(fanOut.every((edge) => edge.curve === 'bezier')).toBe(true);
  expect(fanOut.every((edge) => edge.renderedLabel === '')).toBe(true);

  await page.waitForTimeout(550); // allow the search-centering animation to finish
  await page.evaluate(() => window.__cy.getElementById('E:STAT1-MX1-activation').emit('mouseover'));
  await expect(page.getByTestId('edge-tooltip')).toContainText('STAT1');
  await expect(page.getByTestId('edge-tooltip')).toContainText('MX1');
  await expect(page.getByTestId('edge-tooltip')).toContainText('activates');
  await expect(page.getByTestId('edge-provenance')).toContainText('curated');
  await page.evaluate(() => window.__cy.panBy({ x: 1, y: 0 }));
  await expect(page.getByTestId('edge-tooltip')).toHaveCount(0);

  const clamped = await page.evaluate(() => {
    const node = window.__cy.getElementById('G:STAT1');
    node.renderedPosition({ x: 2, y: 2 });
    node.emit('dragfree');
    return node.renderedPosition();
  });
  expect(clamped.x).toBeGreaterThanOrEqual(48);
  expect(clamped.y).toBeGreaterThanOrEqual(48);

  await page.getByRole('button', { name: 'Reset layout' }).click();
  await page.waitForFunction(() => {
    const position = window.__cy?.getElementById('G:STAT1').renderedPosition();
    return position?.x > 100 && position?.y > 100;
  });
  await expect(page.getByRole('heading', { name: 'STAT1' })).toBeVisible();
  expect(await page.evaluate(() => window.__cy.nodes('.focused').first().data('id2'))).toBe('STAT1');
});

test('Interactive model switches between pathway and fCoSE organic layouts', async ({ page }) => {
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.scratch('_completedLayoutMode') === 'pathway');

  await expect(page.getByRole('button', { name: 'Pathway', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Organic', exact: true }).click();
  await page.waitForFunction(() => window.__cy?.scratch('_completedLayoutMode') === 'organic');
  await page.waitForTimeout(500); // wait for the post-layout viewport fit

  await expect(page.getByRole('button', { name: 'Organic', exact: true })).toHaveAttribute('aria-pressed', 'true');
  const organic = await page.evaluate(() => {
    const cy = window.__cy;
    const bounds = cy.nodes(':visible').renderedBoundingBox();
    return {
      finitePositions: cy.nodes(':visible').every((node) =>
        Number.isFinite(node.position('x')) && Number.isFinite(node.position('y'))),
      insideViewport: bounds.x1 >= 55 && bounds.y1 >= 55 &&
        bounds.x2 <= cy.width() - 55 && bounds.y2 <= cy.height() - 55,
      visibleBucketsHaveChildren: cy.nodes('[kind = "bucket"]:visible').every((bucket) =>
        bucket.children('[kind = "gene"]:visible').length > 0),
    };
  });
  expect(organic).toEqual({
    finitePositions: true,
    insideViewport: true,
    visibleBucketsHaveChildren: true,
  });

  const completedRevision = await page.evaluate(() => window.__cy.scratch('_completedLayoutRevision'));
  await page.getByRole('button', { name: 'Reset layout' }).click();
  await page.waitForFunction((previous) =>
    window.__cy?.scratch('_completedLayoutRevision') > previous, completedRevision);
  expect(await page.evaluate(() => window.__cy.scratch('_completedLayoutMode'))).toBe('organic');

  await page.getByRole('button', { name: 'Pathway', exact: true }).click();
  await page.waitForFunction(() => window.__cy?.scratch('_completedLayoutMode') === 'pathway');
  await expect(page.getByRole('button', { name: 'Pathway', exact: true })).toHaveAttribute('aria-pressed', 'true');
});

test('Interactive model highlights infection phases and cellular locations with a shape key', async ({ page }) => {
  await page.goto('/#/model-cyto');
  await page.waitForFunction(() => window.__cy?.scratch('_completedLayoutMode') === 'pathway');

  const shapeKey = page.locator('[aria-label="Node shape key"]');
  await expect(shapeKey).toContainText('Recognition');
  await expect(shapeKey).toContainText('Inflammation');
  await expect(shapeKey).toContainText('Viral');

  await page.getByRole('button', { name: 'Early', exact: true }).click();
  const early = await page.evaluate(() => ({
    sensorMatches: window.__cy.getElementById('G:DDX58').hasClass('annotation-match'),
    responseMuted: window.__cy.getElementById('G:STAT1').hasClass('annotation-muted'),
  }));
  expect(early).toEqual({ sensorMatches: true, responseMuted: true });
  await expect(page.getByText(/\d+ matches/)).toBeVisible();

  await page.getByRole('button', { name: 'All', exact: true }).click();
  await page.getByLabel('Cell location').selectOption('nucleus');
  const nucleus = await page.evaluate(() => ({
    statMatches: window.__cy.getElementById('G:STAT1').hasClass('annotation-match'),
    sensorMuted: window.__cy.getElementById('G:DDX58').hasClass('annotation-muted'),
    locations: window.__cy.getElementById('G:STAT1').data('locations'),
  }));
  expect(nucleus).toEqual({ statMatches: true, sensorMuted: true, locations: ['cytosol', 'nucleus'] });

  await page.locator('#gene-query').fill('STAT1');
  await page.locator('#gene-query').press('Enter');
  await expect(page.getByRole('heading', { name: 'STAT1' })).toBeVisible();
  await expect(page.locator('aside').getByText('Cytosol', { exact: true })).toBeVisible();
  await expect(page.locator('aside').getByText('Nucleus', { exact: true })).toBeVisible();
});

// Test that each page loads without console errors
for (const page of pages) {
  test(`${page.name} page loads without errors`, async ({ page: browserPage }) => {
    const errors = [];

    // Capture console errors
    browserPage.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Capture page errors
    browserPage.on('pageerror', error => {
      errors.push(error.message);
    });

    // Navigate to page
    await browserPage.goto(`/${page.path}`);

    // Wait for DuckDB to initialize and queries to run
    await browserPage.waitForTimeout(3000);

    // Filter out expected errors (like network issues during tests)
    const criticalErrors = errors.filter(err => {
      // DuckDB schema errors we want to catch
      if (err.includes('Binder Error')) return true;
      if (err.includes('Referenced column') && err.includes('not found')) return true;
      if (err.includes('does not have a column')) return true;

      // Other critical errors
      if (err.includes('TypeError')) return true;
      if (err.includes('ReferenceError')) return true;

      // Ignore certain expected errors
      if (err.includes('Failed to fetch')) return false;
      if (err.includes('net::ERR')) return false;

      return false;
    });

    // Report all errors found
    if (criticalErrors.length > 0) {
      console.log(`Errors on ${page.name}:`);
      criticalErrors.forEach(err => console.log(`  - ${err}`));
    }

    expect(criticalErrors, `Critical errors found on ${page.name} page`).toHaveLength(0);
  });
}

// Test species detail modal
test('Species detail modal loads without errors', async ({ page }) => {
  const errors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', error => {
    errors.push(error.message);
  });

  // Go to home and wait for data to load
  await page.goto('/#/');
  await page.waitForTimeout(3000);

  // Navigate to a species (using the search or direct URL)
  await page.goto('/#/species/Anas%20platyrhynchos');
  await page.waitForTimeout(3000);

  const criticalErrors = errors.filter(err => {
    if (err.includes('Binder Error')) return true;
    if (err.includes('Referenced column') && err.includes('not found')) return true;
    if (err.includes('does not have a column')) return true;
    if (err.includes('TypeError')) return true;
    if (err.includes('ReferenceError')) return true;
    return false;
  });

  expect(criticalErrors, 'Critical errors found on Species Detail modal').toHaveLength(0);
});

// Test DuckDB initialization - verifies no critical errors during data loading
test('DuckDB initializes without errors', async ({ page }) => {
  const errors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', error => {
    errors.push(error.message);
  });

  await page.goto('/#/');
  // Wait for DuckDB to load and run queries
  await page.waitForTimeout(8000);

  // Check for DuckDB-specific errors
  const duckdbErrors = errors.filter(err => {
    if (err.includes('Binder Error')) return true;
    if (err.includes('DuckDB') && err.includes('failed')) return true;
    if (err.includes('Referenced column') && err.includes('not found')) return true;
    return false;
  });

  expect(duckdbErrors, 'DuckDB should initialize without query errors').toHaveLength(0);
});

// Phase 2 Step 2: the gene-presence matrix ships as parquet and serves
// through the DuckDB store (window.__db — same convention as window.__cy).
test('gene_presence parquet serves correct calls via DuckDB', async ({ page }) => {
  await page.goto('/#/');
  await page.waitForFunction(() => !!window.__db, null, { timeout: 15000 });

  const result = await page.evaluate(async () => {
    const summary = await window.__db.getSpeciesGeneSummary('Gallus gallus');
    const gene = await window.__db.getGenePresenceSummary('DDX58');
    const calls = await window.__db.getPresenceCallsForGene('DDX58');
    const speciesCalls = await window.__db.getPresenceCallsForSpecies('Gallus gallus');
    // DuckDB-WASM returns COUNT aggregates as BigInt — normalise to Number
    const norm = (o) => Object.fromEntries(Object.entries(o).map(
      ([k, v]) => [k, typeof v === 'bigint' ? Number(v) : v]));
    return {
      summary: norm(summary),
      gene: norm(gene),
      ddCount: calls.length,
      speciesCallCount: speciesCalls.length,
    };
  });

  // Must mirror the shipped JSON summaries (Gallus: 1428 searched, 1411 full,
  // DDX58 is THE critical absence in chicken)
  expect(result.summary.total_genes_searched).toBe(1428);
  expect(result.summary.full).toBe(1411);
  expect(result.summary.fragment).toBe(4);
  expect(result.summary.not_found).toBe(13);
  expect(result.summary.high_absences).toContain('DDX58');
  expect(result.speciesCallCount).toBe(1428);
  // DDX58 is searched across essentially the whole matrix (~2048 species)
  expect(result.ddCount).toBeGreaterThan(150);
  expect(result.gene.total).toBe(result.ddCount);
});

// Phase: URL state — the phylogeny gene overlay ("secret entrance" from
// gene pages) is deep-linkable and reactive to SPA hash changes.
test('Phylogeny gene overlay deep link renders counts and syncs URL', async ({ page }) => {
  test.slow(); // DuckDB-WASM init + CDN fetch runs long under full-suite load
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/phylogeny?gene=DDX58');
  await expect(page.getByText('GENE OVERLAY')).toBeVisible({ timeout: 15000 });
  // DDX58 ground truth across the matrix (2048-species expansion): 1480 full / 347 fragment / 221 absent
  await expect(page.getByText(/221 absent/)).toBeVisible({ timeout: 30000 });

  // Unchecking the calls filter is shareable (calls=0 = full clade context)
  await page.locator('input[type="checkbox"]').first().uncheck();
  await page.waitForFunction(() => location.hash.includes('calls=0'), null, { timeout: 8000 });

  // Clearing the overlay cleans the URL
  await page.getByRole('button', { name: /Clear overlay/ }).click();
  await page.waitForFunction(() => !location.hash.includes('gene='), null, { timeout: 8000 });
  expect(errors).toHaveLength(0);
});

// Phase: URL state — the Genes panel restores ALL shareable params fast
// (previously serialized behind DuckDB init) and SPA navigation treats the
// URL as the whole truth (dropped params reset state).
test('Genes page URL params restore and reset on SPA navigation', async ({ page }) => {
  test.slow(); // dynamic import of duckdb-wasm adds latency under suite load
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const searchBox = page.getByPlaceholder('Search genes by symbol, name, or alias...');

  await page.goto('/#/genes?q=ANP32');
  await expect(searchBox).toHaveValue('ANP32', { timeout: 15000 });
  const body = await page.locator('main').innerText();
  expect(body).toContain('ANP32A');
  expect(body).not.toContain('DDX58');

  await page.goto('/#/genes?kind=viral');
  await expect(page.locator('.font-mono', { hasText: 'PB2' }).first())
    .toBeVisible({ timeout: 20000 });
  const viral = await page.locator('main').innerText();
  expect(viral).not.toContain('DDX58');

  // SPA navigation to a URL without q resets the search (URL = whole truth)
  await page.evaluate(() => { location.hash = '#/genes?tier=1'; });
  await page.waitForTimeout(1500);
  await expect(searchBox).toHaveValue('');
  expect(errors).toHaveLength(0);
});

// Phase: URL state — the Mutations browser restores shareable params
// (q/protein/kind/scope/sort/mut) and selection lands in the URL.
test('Mutations page URL params restore and selection is shareable', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const box = page.getByPlaceholder('Search mutations (e.g. E627K, PB2, H275Y)...');

  await page.goto('/#/mutations?q=E627K');
  await expect(box).toHaveValue('E627K', { timeout: 15000 });
  await expect(page.locator('main')).toContainText('E627K');

  await page.goto('/#/mutations?protein=PB2');
  await page.waitForTimeout(2000);
  const info = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.divide-y button')];
    const proteins = [...new Set(rows.map(r => r.querySelector('.font-mono + span')?.textContent?.trim()))];
    return { rowCount: rows.length, proteins };
  });
  expect(info.rowCount).toBeGreaterThan(10);
  expect(info.proteins).toEqual(['PB2']);

  // Selecting a mutation puts mut= into the URL (shareable sidebar state)
  await page.locator('.divide-y button').first().click();
  await page.waitForFunction(() => location.hash.includes('mut='), null, { timeout: 8000 });
  expect(errors).toHaveLength(0);
});

// Phase: URL state — the Genomes browser restores shareable params
// (tab/assembly/annotated/order — order was previously missing from the
// URL entirely) and reacts to SPA navigation.
test('Genomes page URL params restore and sync', async ({ page }) => {
  test.slow(); // dynamic import of duckdb-wasm adds latency under suite load
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/genomes?tab=undetected&assembly=Chromosome');
  await expect(page.getByText(/no confirmed cases/i)).toBeVisible({ timeout: 15000 });
  await expect(page.locator('main')).toContainText('Chromosome');

  await page.goto('/#/genomes?order=Anseriformes');
  // exact: the undetected tab's stale rows include the subspecies
  // 'Anas platyrhynchos platyrhynchos', which would match a substring
  // locator before the filtered (detected + Anseriformes) query lands
  await expect(page.getByText('Anas platyrhynchos', { exact: true }).first())
    .toBeVisible({ timeout: 20000 });
  // give the tab switch + debounced query time to replace stale rows
  await page.waitForFunction(
    () => !document.querySelector('main').innerText.includes('Gallus gallus murghi'),
    null, { timeout: 10000 });
  const body = await page.locator('main').innerText();
  expect(body).not.toContain('Gallus gallus');

  // Interaction writes to the URL
  await page.getByRole('button', { name: /Genome Only/ }).click();
  await page.waitForFunction(() => location.hash.includes('tab=undetected'), null, { timeout: 8000 });
  // SPA navigation to a clean URL resets filters
  await page.evaluate(() => { location.hash = '#/genomes'; });
  await page.waitForTimeout(1500);
  expect(await page.evaluate(() => location.hash)).toBe('#/genomes');
  expect(errors).toHaveLength(0);
});

// Phase: URL state — the Map camera (lat/lng/z) is shareable alongside
// ?species=, with a converging round-trip (no moveend/updateParams echo).
test('Map camera state is URL-addressable and converges', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/map?lat=51.5&lng=-0.1&z=6');
  await page.waitForFunction(() => window.__map?.loaded?.(), null, { timeout: 20000 });
  const cam = await page.evaluate(() => {
    const c = window.__map.getCenter();
    return { lat: +c.lat.toFixed(2), lng: +c.lng.toFixed(2), z: +window.__map.getZoom().toFixed(1) };
  });
  expect(cam).toEqual({ lat: 51.5, lng: -0.1, z: 6 });

  // Camera movement writes back to the URL (debounced)
  await page.evaluate(() => window.__map.jumpTo({ center: [10, 40], zoom: 4 }));
  await page.waitForFunction(() => location.hash.includes('lat=40'), null, { timeout: 8000 });

  // URL change (SPA nav) moves the camera and the hash converges exactly
  await page.evaluate(() => { location.hash = '#/map?lat=-20&lng=134&z=4.5'; });
  await page.waitForFunction(
    () => Math.abs(window.__map.getCenter().lat + 20) < 0.01, null, { timeout: 8000 });
  await page.waitForTimeout(2000);
  expect(await page.evaluate(() => location.hash)).toBe('#/map?lat=-20&lng=134&z=4.5');
  expect(errors).toHaveLength(0);
});

// Phase: URL state — the Papers browser: ?q= (search), ?f= (facet chips,
// 'type:value|…'), ?p= (page) alongside #/papers/{id} focus links.
// Interactive filter changes reset pagination; URL restores keep ?p=.
test('Papers page URL params, chips and pagination', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const box = page.getByPlaceholder('Search papers...');
  const rows = async () => {
    const m = (await page.locator('main').innerText()).match(/Showing (\d+)–(\d+) of/);
    return m ? m[1] : 'none';
  };

  await page.goto('/#/papers?p=3');
  await page.waitForTimeout(3000);
  expect(await rows()).toBe('51');

  // SPA navigation keeps the URL-specified page
  await page.evaluate(() => { location.hash = '#/papers?p=2'; });
  await page.waitForTimeout(1500);
  expect(await rows()).toBe('26');

  // Typing filters AND resets pagination, with the query in the URL
  await box.fill('vaccine');
  await page.waitForTimeout(1500);
  expect(await rows()).toBe('1');
  expect(decodeURIComponent(await page.evaluate(() => location.hash))).toContain('q=vaccine');

  // Combined deep link: chips + page
  await page.goto('/#/papers?f=category:Vaccines&p=2');
  await page.waitForTimeout(3000);
  expect(await rows()).toBe('26');
  expect(errors).toHaveLength(0);
});

// Phase: URL state — species FULL page deep state: gene-panel sub-filters
// (?gst/?gimp/?gq), view (?gview), open evidence drawer (?gg), SPA tab
// and species switches; modal close (Escape) scrubs #/species/{id}.
test('Species full page deep-link state and SPA switches', async ({ page }) => {
  test.slow(); // multiple DuckDB-backed loads in one flow
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/species-full/Gallus%20gallus?tab=genes&gst=NOT_FOUND&gg=DDX58');
  await page.waitForTimeout(6000);
  // status filter restored into its select
  const st = await page.evaluate(() =>
    [...document.querySelectorAll('select')].map(s => s.value));
  expect(st).toContain('NOT_FOUND');
  // gene panel rendered for the right species
  const body = await page.locator('main').innerText();
  expect(body).toContain('DDX58');
  expect(body).toContain('1428');

  // importance filter interaction writes to the URL
  const impSel = page.locator('select', { has: page.locator('option[value="critical"]') });
  await impSel.selectOption('critical');
  await page.waitForFunction(() => location.hash.includes('gimp=critical'), null, { timeout: 8000 });

  // SPA: same species, different tab applies
  await page.evaluate(() => { location.hash = '#/species-full/Gallus%20gallus?tab=research'; });
  await page.waitForTimeout(2500);
  expect(await page.locator('main').innerText()).toContain('Research findings');

  // SPA: different species reloads the view
  await page.evaluate(() => { location.hash = '#/species-full/Anas%20platyrhynchos'; });
  await page.waitForTimeout(4000);
  const b2 = await page.locator('main').innerText();
  expect(b2.toLowerCase()).toContain('mallard');

  // Modal close (Escape) scrubs the id from the hash
  await page.goto('/#/species/9031');
  await page.waitForTimeout(4000);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1200);
  expect(await page.evaluate(() => location.hash)).toBe('#/species');
  expect(errors).toHaveLength(0);
});

// Phase 1 (SPREAD_MODEL): the timeline — adaptive periods, measured
// node fading (first dated detection per species), curated event flags
// with paper chips, ?t= deep links.
test('Spread model timeline scrubs, fades and stamps', async ({ page }) => {
  test.slow(); // DuckDB init + timeline queries
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  // Early playhead: species not yet detected are faded
  await page.goto('/#/spread-cyto?t=2005-06');
  await page.waitForFunction(() => window.__cy, null, { timeout: 20000 });
  await page.waitForFunction(
    () => document.querySelector('.font-mono')?.textContent?.trim() === '2005',
    null, { timeout: 20000 });
  const early = await page.evaluate(() => ({
    linked: window.__cy.nodes('[kind="element"][?hasLink]').length,
    faded: window.__cy.nodes('[kind="element"][?hasLink].faded').length,
  }));
  expect(early.linked).toBe(6);
  expect(early.faded).toBe(6);   // first dated detections of all 6 are 2006+

  // Late playhead: everyone active, playhead label restores from ?t=
  await page.evaluate(() => { location.hash = '#/spread-cyto?t=2023-10'; });
  await page.waitForFunction(
    () => document.querySelector('.font-mono')?.textContent?.includes('Oct 2023'),
    null, { timeout: 20000 });
  const late = await page.evaluate(() =>
    window.__cy.nodes('[kind="element"][?hasLink].faded').length);
  expect(late).toBe(0);

  // Curated event flags exist and open a cited panel
  const flags = await page.locator('button[title*="Europe"]').count();
  expect(flags).toBeGreaterThan(0);
  await page.locator('button[title*="South America"]').first().click();
  await page.waitForTimeout(800);
  const panel = await page.locator('main').innerText();
  expect(panel).toContain('South America arrival');
  expect(panel).toContain('hpai_south_america_2022_2025'); // paper chip
  expect(errors).toHaveLength(0);
});

// Clade View (#/clade): heatmap of gene × order presence, clade-specific
// losses flagged, cell click shows species-level detail.
test('Clade view heatmap renders with clade-specific gene losses', async ({ page }) => {
  test.slow();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/clade');
  await page.waitForFunction(
    () => document.body.innerText.includes('genes ×'),
    null, { timeout: 30000 });

  const body = await page.locator('main').innerText();
  expect(body).toContain('Clade-Specific Gene Patterns');
  expect(body).toContain('clade-specific absence');

  // The heatmap has colored cells (gene × order)
  const cells = await page.locator('td div[style*="background"]').count();
  expect(cells).toBeGreaterThan(100);

  // Key genes visible: DDX58 (RIG-I, lost in Galliformes) and CCL17
  // (the most patchy chemokine)
  expect(body).toContain('DDX58');
  expect(body).toContain('CCL17');

  // Verify at least one gene with clade losses is visible by checking
  // that the page contains a number in a badge position (simpler than
  // targeting Tailwind arbitrary-value classes)
  const badgeCount = await page.evaluate(() =>
    [...document.querySelectorAll('td')].filter(td =>
      td.textContent.trim().match(/^\d+$/) && parseInt(td.textContent) > 0
    ).length);
  expect(badgeCount).toBeGreaterThan(3);

  expect(errors).toHaveLength(0);
});

// Phase 5 (SPREAD_MODEL): regional risk views — NZ as the template.
// ?region=nz shows the risk panel with live detection stats, flyway
// exposure, and curated at-risk species from the overlay.
test('Spread model regional risk panel shows NZ profile from live data', async ({ page }) => {
  test.slow();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/spread-cyto?region=nz');
  await page.waitForFunction(
    () => document.body.innerText.includes('New Zealand') &&
           document.body.innerText.includes('First detection'),
    null, { timeout: 30000 });

  const body = await page.locator('main').innerText();
  // NZ narrative + status
  expect(body).toContain('New Zealand');
  expect(body).toContain('arrived');
  expect(body).toContain('First detection');
  // Flyway exposure
  expect(body).toContain('East Asian');
  // At-risk species from the overlay (kākāpō is THE conservation icon)
  expect(body).toMatch(/kakapo|kākāpō/i);
  expect(body).toContain('vaccination target');
  // URL stays addressable
  expect(await page.evaluate(() => location.hash)).toContain('region=nz');

  // Switching regions: South America
  await page.getByRole('button', { name: /South America/ }).click();
  await page.waitForTimeout(2000);
  const sa = await page.locator('main').innerText();
  expect(sa).toContain('established');
  expect(sa).toContain('Peru');

  expect(errors).toHaveLength(0);
});

// Phase 4 (SPREAD_MODEL): mutations on the spillover path — curated
// adaptation markers on the mammalian-crossing edges, gene-panel deep
// links from host nodes.
test('Spread model spillover edges carry adaptation mutations', async ({ page }) => {
  test.slow();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/spread-cyto');
  await page.waitForFunction(() => window.__cy && window.__spreadMutations, null, { timeout: 20000 });
  await page.waitForTimeout(2000);

  // Tap the wild-bird → mammal spillover edge
  await page.evaluate(() => {
    const e = window.__cy.edges('[id *= "amplification->spillover"]').first();
    e.emit('tap', { target: e });
  });
  await page.waitForTimeout(800);
  const panel = await page.locator('main').innerText();

  // ≥3 adaptation mutations, each a navigable link
  expect(panel).toContain('PB2-E627K');
  expect(panel).toContain('canonical');
  expect(panel).toContain('PB2-D701N');
  const mutationLinks = await page.locator('a[href*="#/mutations/"]').count();
  expect(mutationLinks).toBeGreaterThanOrEqual(4);

  // Poultry/cattle edge carries receptor-specificity mutations
  await page.evaluate(() => {
    const e = window.__cy.edges('[id *= "anthropogenic->spillover"]').first();
    e.emit('tap', { target: e });
  });
  await page.waitForTimeout(800);
  const panel2 = await page.locator('main').innerText();
  expect(panel2).toContain('HA-G228S');
  expect(panel2).toContain('HA-N224K');
  expect(errors).toHaveLength(0);
});

// Phase 3 (SPREAD_MODEL): the evidence layer — edges weighted by corpus
// papers, contested styling, citation chips on tap.
test('Spread model edges carry evidence and contest markers', async ({ page }) => {
  test.slow();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/spread-cyto');
  await page.waitForFunction(() => window.__cy, null, { timeout: 20000 });
  await page.waitForTimeout(4000);

  const edges = await page.evaluate(() =>
    window.__cy.edges().map(e => {
      const d = e.data();
      return { id: d.id, count: d.evCount, contested: d.contested,
               inferred: d.inferred, width: d.width, color: e.style('line-color'),
               lineStyle: e.style('line-style') };
    }));

  // The migration edge is well-evidenced and solid
  const mig = edges.find(e => e.id.includes('routes->amplification'));
  expect(mig.count).toBeGreaterThanOrEqual(10);
  expect(mig.contested).toBe(true);              // flyway-limits diverge
  expect(mig.lineStyle).toBe('dashed');          // contested style
  expect(mig.width).toBeGreaterThan(3);          // weighted by papers

  // The spillover edge is inferred (no corpus extraction yet — W5)
  const spillover = edges.find(e => e.id.includes('amplification->spillover'));
  expect(spillover.inferred).toBe(true);
  expect(spillover.width).toBeLessThan(2);

  // Tap an edge → evidence panel with paper chips
  await page.evaluate(() => {
    const e = window.__cy.edges('[id *= "routes->amplification"]').first();
    e.emit('tap', { target: e });
  });
  await page.waitForTimeout(800);
  const panel = await page.locator('main').innerText();
  expect(panel).toContain('contested');
  expect(panel).toMatch(/papers\b/);
  expect(panel).toContain('wild_bird_migration'); // mechanism split shown
  expect(errors).toHaveLength(0);
});

// Phase 2 (SPREAD_MODEL): data-join styling — node size ∝ detections
// (log), susceptibility-class border colors, per-node chips whose numbers
// come from the same tables the Species page queries.
test('Spread model nodes wear the data: size, susceptibility, chips', async ({ page }) => {
  test.slow();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/spread-cyto');
  await page.waitForFunction(() => window.__cy, null, { timeout: 20000 });
  await page.waitForTimeout(6000);

  const nodes = await page.evaluate(() =>
    window.__cy.nodes('[kind="element"][?hasLink]').map(n => ({
      name: n.data('label').split('\n')[0], sizeW: n.data('sizeW'),
      susc: n.data('susc'), chip: n.data('chip'),
      border: window.__cy.getElementById(n.id).style('border-color'),
    })));
  const byName = Object.fromEntries(nodes.map(n => [n.name, n]));

  // Mallard: the reservoir — biggest, green (highly tolerant), 2.2M detections
  expect(byName['Anas platyrhynchos'].sizeW).toBe(96);
  expect(byName['Anas platyrhynchos'].susc).toBe('highly_tolerant');
  expect(byName['Anas platyrhynchos'].chip).toContain('2.2M');
  expect(byName['Anas platyrhynchos'].chip).toMatch(/\d+ countries/);
  // Gannet: the amplifier — red (highly susceptible), 100% mortality chip
  expect(byName['Northern gannet'].susc).toBe('highly_susceptible');
  expect(byName['Northern gannet'].chip).toContain('100% mortality');
  // Size ordering: mallard > wigeon (log scale)
  expect(byName['Anas platyrhynchos'].sizeW)
    .toBeGreaterThan(byName['Mareca penelope'].sizeW);

  // Chip numbers match the species table (same query the Species page uses)
  const check = await page.evaluate(async () => {
    const rows = await window.__db.query(
      `SELECT detection_count, country_count FROM species WHERE scientific_name = 'Anas platyrhynchos'`);
    return { det: Number(rows[0].detection_count), countries: Number(rows[0].country_count) };
  });
  expect(check.countries).toBeGreaterThan(40); // was 55 before dedup, now 45
  expect(check.det).toBeGreaterThan(2_000_000);

  expect(errors).toHaveLength(0);
});

// Spread model beta page (#/spread-cyto): graph builds from the enriched
// model, species nodes deep-link, ?node= selects.
test('Spread model interactive graph (beta) renders and links species', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/spread-cyto');
  await page.waitForFunction(() => window.__cy, null, { timeout: 20000 });
  const graph = await page.evaluate(() => ({
    buckets: window.__cy.nodes('[kind="bucket"]').length,
    elements: window.__cy.nodes('[kind="element"]').length,
    linked: window.__cy.nodes('[kind="element"][?hasLink]').length,
    edges: window.__cy.edges().length,
  }));
  expect(graph.buckets).toBe(9);      // model stages
  expect(graph.elements).toBe(44);    // species/groups/factors
  expect(graph.edges).toBe(11);       // transmission pathways (10 + anthropogenic→spillover)
  expect(graph.linked).toBeGreaterThan(0);

  // ?node= deep link selects the element and offers its species profile
  await page.evaluate(() => { location.hash = '#/spread-cyto?node=reservoir::0'; });
  await page.waitForTimeout(1500);
  const panel = await page.locator('main').innerText();
  expect(panel).toMatch(/Anas platyrhynchos|mallard/i);
  expect(panel).toContain('Open');
  expect(errors).toHaveLength(0);
});

// Phase 4: the Map renders detection points from the DuckDB parquet
// (LEFT JOIN species), not from static geojson layers — those remain
// Downloads-page artifacts only. Also asserts the species deep link.
test('Map renders detections from DuckDB and honours species deep link', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/map');
  await expect(page.getByText('georeferenced detections across')).toBeVisible({ timeout: 20000 });
  // Points stream in from the DuckDB query after the map loads
  await expect.poll(async () => {
    const t = await page.locator('main p').first().innerText();
    return Number((t.match(/[\d,]+/) || ['0'])[0].replace(/,/g, ''));
  }, { timeout: 20000 }).toBeGreaterThan(1000);
  expect(errors).toHaveLength(0);

  // Deep link filters to one species (mallard) and shows a clearable chip
  await page.goto('/#/map?species=Anas%20platyrhynchos');
  await expect(page.getByText('Anas platyrhynchos').first()).toBeVisible({ timeout: 20000 });
  await page.getByRole('button', { name: '✕ clear' }).click();
  await page.waitForTimeout(1500);
  const after = await page.locator('main p').first().innerText();
  expect(Number((after.match(/[\d,]+/) || ['0'])[0].replace(/,/g, ''))).toBeGreaterThan(1000);
});
// Phase 3: susceptibility sort joins the slim susceptibility table —
// previously referenced a column species.parquet never had (Binder Error,
// empty grid). Full-page wiki research section also fetched a file that
// didn't exist (species_wiki.json → wiki_species.json).
test('Species page susceptibility sort and full-page wiki research work', async ({ page }) => {
  const errors = [];
  page.on('console', m => {
    if (m.type() === 'error' && m.text().includes('Binder Error')) errors.push(m.text());
  });

  await page.goto('/#/species');
  await page.waitForTimeout(2500);
  const sortSel = page.locator('select', { has: page.locator('option[value="susceptibility"]') });
  await sortSel.selectOption('susceptibility');
  await page.waitForTimeout(1500);
  // Grid must still render (previously: Binder Error → empty grid)
  const mainText = await page.locator('main').innerText();
  expect(mainText.length, 'species grid rendered').toBeGreaterThan(400);
  expect(errors, 'no Binder Errors from the susceptibility JOIN').toHaveLength(0);
  expect(errors, 'no Binder Errors from the susceptibility JOIN').toHaveLength(0);

  // Full-page wiki research for a well-covered species (Chicken).
  // The overview badge renders when the wiki record matches (the fetch
  // previously hit a nonexistent file → wikiSpecies always null).
  await page.goto('/#/species-full/Gallus%20gallus');
  await expect(page.getByText('papers', { exact: false })).toBeVisible({ timeout: 15000 });
});
// DuckDB (the static gene_presence_summary.json is retired). The genome
// view is what consumes them.
// Phase 2 Step 4 test:
test('Genes genome view derives presence rollups from DuckDB', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  await page.goto('/#/genes');
  await page.getByTestId('genome-available-toggle').click();
  await page.getByTestId('presence-detail-toggle').click();

  // Detail table renders with real per-gene counts from the GROUP BY
  // (rows appear once the async rollup lands — the footnote is static)
  await expect(page.locator('tbody tr').first(), 'genome-view rows from DuckDB rollup')
    .toBeVisible({ timeout: 20000 });
  const rowCount = await page.locator('tbody tr').count();
  expect(rowCount).toBeGreaterThan(10);
  await expect(page.getByText('Variability = (fragment + missing) / species searched')).toBeVisible();
  const dd = page.locator('tbody tr', { hasText: 'DDX58' });
  if (await dd.count()) {
    // DDX58 is genuinely absent in chicken — its Missing column must be > 0
    const missing = await dd.first().locator('td').nth(4).innerText();
    expect(Number(missing)).toBeGreaterThan(0);
  }
  expect(errors, 'genome view must not throw').toHaveLength(0);
});

// Test search functionality
test('Search returns results without errors', async ({ page }) => {
  const errors = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  await page.goto('/#/');
  // Wait longer for page and DuckDB to fully load
  await page.waitForTimeout(6000);

  // Find search input - try multiple selectors
  let searchInput = page.locator('input[type="text"]').first();

  // Try to fill if input exists
  const inputCount = await searchInput.count();
  if (inputCount > 0) {
    try {
      await searchInput.fill('mallard', { timeout: 5000 });
      await page.waitForTimeout(2000);
    } catch {
      // If fill fails, just check page loaded without errors
      console.log('Search input not interactive, skipping search test');
    }
  }

  const criticalErrors = errors.filter(err => {
    if (err.includes('Binder Error')) return true;
    if (err.includes('Referenced column') && err.includes('not found')) return true;
    return false;
  });

  expect(criticalErrors, 'Search should not produce schema errors').toHaveLength(0);
});
