import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  workers: 1, // Cytoscape pages are memory-heavy; serial keeps the suite deterministic
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1, // heavy DuckDB suite on a box that may run the pipeline concurrently
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5178',
    trace: 'on-first-retry',
    launchOptions: {
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        // Cytoscape + elk + DuckDB-WASM pages are heap-hungry; the default
        // renderer heap cap can abort them ("Target crashed") when the full
        // suite runs serially in one browser.
        '--js-flags=--max-old-space-size=4096',
      ],
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
      // the axe sweep + mobile-width sweep live in their own projects below:
      // heavy page loads would otherwise poison the shared browser heap
      testIgnore: /a11y_axe\.spec\.js|mobile_width\.spec\.js/,
    },
    {
      name: 'a11y-axe',
      use: { browserName: 'chromium' },
      testMatch: /a11y_axe\.spec\.js/,
      // NOTE: no `dependencies` — a failing upstream test would SKIP this
      // project entirely ("did not run"). Array order already runs it last.
    },
    {
      name: 'mobile-width',
      use: { browserName: 'chromium' },
      testMatch: /mobile_width\.spec\.js/,
      // same heap-isolation reasoning as a11y-axe: 32 full page loads
    },
  ],
  webServer: {
    // Dedicated port 5178 so test runs never race the LAN dev server on 5177
    // (the fixture binds localhost-only and used to steal the port).
    command: 'npm run dev -- --port 5178',
    url: 'http://localhost:5178',
    reuseExistingServer: true,
    timeout: 120000,
  },
});
