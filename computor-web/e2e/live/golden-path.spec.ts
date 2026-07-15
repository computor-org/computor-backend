import { test, expect } from '@playwright/test';

/**
 * Live golden-path smoke: a REAL Keycloak browser login against the running
 * integration stack (api :18000, keycloak :18180, forgejo :13030), then a thin
 * authenticated navigation slice. This is NOT hermetic — it needs the stack up.
 *
 * Excluded from the default run; runs only under the opt-in `live` project:
 *   E2E_LIVE=1 E2E_API_URL=http://localhost:18000 npx playwright test --project=live
 *
 * Skips unless API_ADMIN_EMAIL / API_ADMIN_PASSWORD are set (they live in
 * integration-tests/.env.integration), so it never breaks anyone's default run.
 */

const EMAIL = process.env.API_ADMIN_EMAIL;
const PASSWORD = process.env.API_ADMIN_PASSWORD;

test.describe('live golden path', () => {
  test('admin logs in via Keycloak and reaches the dashboard', async ({ page }) => {
    test.skip(!EMAIL || !PASSWORD,
      'set API_ADMIN_EMAIL and API_ADMIN_PASSWORD (integration-tests/.env.integration) to run the live slice');

    // /login auto-initiates the Keycloak SSO redirect (login/page.tsx →
    // loginWithSSO('keycloak') → backend → the Keycloak login form).
    await page.goto('/login');

    // The Keycloak login form — same hops as integration-tests/fixtures/keycloak_auth.py.
    await page.waitForSelector('#kc-form-login', { timeout: 30_000 });
    await page.fill('#username', EMAIL!);
    await page.fill('#password', PASSWORD!);
    await page.click('#kc-login');

    // Backend /auth/keycloak/callback → /auth/success → /dashboard.
    await page.waitForURL('**/dashboard', { timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /Welcome back/ })).toBeVisible();

    // Thin authenticated slice: the course list renders for the logged-in admin.
    await page.goto('/courses');
    await expect(page.getByRole('heading', { name: 'Courses' })).toBeVisible();
  });
});
