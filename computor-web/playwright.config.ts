import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config for the web frontend. Tests drive a real `next dev` server and mock
 * the backend at the network layer (see e2e/fixtures.ts), so they need no
 * running API or database. The backend's own pytest + analytics system test
 * cover the server side.
 */
const PORT = Number(process.env.E2E_PORT ?? 3100);
const API = process.env.E2E_API_URL ?? 'http://localhost:8000';

// The `live` project drives a REAL Keycloak login against the running
// integration stack; it is opt-in so the hermetic default run never touches it.
// Enable with E2E_LIVE=1 and point the app at the integration API, e.g.:
//   E2E_LIVE=1 E2E_API_URL=http://localhost:18000 npx playwright test --project=live
const LIVE = !!process.env.E2E_LIVE;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : [['list']],
  timeout: 30_000,
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'on-first-retry',
    headless: true,
  },
  projects: [
    // Hermetic, mocked-backend specs — the default run. Never picks up e2e/live/.
    { name: 'chromium', use: { ...devices['Desktop Chrome'] }, testIgnore: '**/live/**' },
    // Live full-stack slice — only present when E2E_LIVE is set.
    ...(LIVE
      ? [{
          name: 'live',
          use: { ...devices['Desktop Chrome'] },
          testMatch: '**/live/**/*.spec.ts',
        }]
      : []),
  ],
  webServer: {
    command: `npx next dev -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    env: { NEXT_PUBLIC_API_URL: API },
  },
});
