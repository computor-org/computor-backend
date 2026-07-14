import { test, expect, type Route } from '@playwright/test';
import { API_ORIGIN, json } from './fixtures';

/**
 * Public /invite/[token]: the platform's only self-service registration page.
 * No auth injection — this page is reached unauthenticated.
 */

const TOKEN = 'tok-abcdef123456';

const PUBLIC_INVITE = {
  id: 'inv-1',
  email: null,
  roles: ['_user_manager'],
  expires_at: '2099-01-01T00:00:00Z',
  note: 'onboard a manager',
};

async function mockInvite(page: import('@playwright/test').Page, opts: {
  found?: boolean;
  onAccept?: (route: Route) => void;
} = {}) {
  const found = opts.found ?? true;
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === `/invites/${TOKEN}` && route.request().method() === 'GET') {
      return found ? json(route, PUBLIC_INVITE) : json(route, { detail: 'Not found' }, 404);
    }
    if (path === `/invites/${TOKEN}/accept` && route.request().method() === 'POST') {
      if (opts.onAccept) return opts.onAccept(route);
      return json(route, { user_id: 'u-new', email: 'new@example.org' }, 201);
    }
    return json(route, {});
  });
}

test.describe('public invite acceptance', () => {
  test('a valid token renders the account form', async ({ page }) => {
    await mockInvite(page);
    await page.goto(`/invite/${TOKEN}`);

    await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
  });

  test('an unknown token shows Invite Not Found', async ({ page }) => {
    await mockInvite(page, { found: false });
    await page.goto(`/invite/${TOKEN}`);

    await expect(page.getByRole('heading', { name: 'Invite Not Found' })).toBeVisible();
  });

  test('mismatched passwords are rejected client-side', async ({ page }) => {
    await mockInvite(page);
    await page.goto(`/invite/${TOKEN}`);

    await page.locator('input[type="text"]').first().fill('New');
    await page.locator('input[type="text"]').nth(1).fill('User');
    await page.locator('input[type="email"]').fill('new@example.org');
    await page.locator('input[type="password"]').first().fill('password123');
    await page.locator('input[type="password"]').nth(1).fill('different999');
    await page.getByRole('button', { name: 'Create account' }).click();

    await expect(page.getByText('Passwords do not match')).toBeVisible();
  });

  test('a completed acceptance shows the ready state', async ({ page }) => {
    await mockInvite(page);
    await page.goto(`/invite/${TOKEN}`);

    await page.locator('input[type="text"]').first().fill('New');
    await page.locator('input[type="text"]').nth(1).fill('User');
    await page.locator('input[type="email"]').fill('new@example.org');
    await page.locator('input[type="password"]').first().fill('password123');
    await page.locator('input[type="password"]').nth(1).fill('password123');
    await page.getByRole('button', { name: 'Create account' }).click();

    await expect(page.getByRole('heading', { name: 'Account ready' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continue to sign in' })).toBeVisible();
  });
});
