import { test, expect } from '@playwright/test';
import { PERSONAS, injectAuth, json, mockApi } from './fixtures';

/**
 * Auth routing: authenticated users are bounced off /login, unauthenticated
 * users are bounced onto it, and /auth/success sanitizes its redirect target.
 */

test.describe('auth routing', () => {
  test('an authenticated user is redirected off /login to the dashboard', async ({ page }) => {
    await injectAuth(page, PERSONAS.admin);
    await mockApi(page, {
      persona: PERSONAS.admin,
      handlers: (route, url) => {
        if (url.pathname === '/courses' && route.request().method() === 'GET') {
          void json(route, []); return true;
        }
        return false;
      },
    });
    await page.goto('/login');

    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('an unauthenticated user hitting a protected page is sent into SSO login', async ({ page }) => {
    // No injectAuth → no session. /user 401s so the session never validates; the
    // protected page bounces to /login, which kicks off the Keycloak SSO redirect.
    await mockApi(page, {
      handlers: (route, url) => {
        if (url.pathname.endsWith('/user')) {
          void json(route, { detail: 'unauthorized' }, 401); return true;
        }
        return false;
      },
    });
    await page.goto('/courses');

    await expect(page).toHaveURL(/\/auth\/keycloak\/login/);
  });

  test('/auth/success sanitizes an unsafe redirect target to the dashboard', async ({ page }) => {
    // A protocol-relative redirect must not escape the app.
    await page.addInitScript(() => sessionStorage.setItem('auth_redirect', '//evil.example.com'));
    await mockApi(page, {
      persona: PERSONAS.admin,
      handlers: (route, url) => {
        if (url.pathname === '/courses' && route.request().method() === 'GET') {
          void json(route, []); return true;
        }
        return false;
      },
    });
    await page.goto('/auth/success');

    await expect(page).toHaveURL(/\/dashboard/);
  });
});
