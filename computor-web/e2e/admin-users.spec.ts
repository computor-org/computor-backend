import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Admin → Users list: server-side search + paging against a mocked backend.
 * Self-contained network mocks.
 */

const API_ORIGIN = 'http://localhost:8000';
const TOTAL_USERS = 60; // more than one 50-row page

const SELF = {
  id: 'u-admin',
  username: 'admin1',
  email: 'admin1@example.org',
  given_name: 'Ada',
  family_name: 'Root',
  user_roles: [{ role_id: '_admin' }],
};

function fakeUser(i: number) {
  return {
    id: `u-${String(i).padStart(3, '0')}`,
    username: `user${i}`,
    email: `user${i}@example.org`,
    given_name: `Given${i}`,
    family_name: `Family${i}`,
    archived_at: null,
    is_service: false,
    created_at: '2026-01-15T10:00:00Z',
  };
}

const ALL_USERS = Array.from({ length: TOTAL_USERS }, (_, i) => fakeUser(i + 1));

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, { admin = true }: { admin?: boolean } = {}) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
    sessionStorage.setItem('auth_provider', 'sso');
  }, {
    id: SELF.id,
    username: SELF.username,
    email: SELF.email,
    givenName: SELF.given_name,
    familyName: SELF.family_name,
    role: admin ? 'admin' : 'student',
    systemRoles: admin ? ['_admin'] : [],
  });

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path === '/users') {
      const search = url.searchParams.get('search')?.toLowerCase() ?? '';
      const skip = Number(url.searchParams.get('skip') ?? 0);
      const limit = Number(url.searchParams.get('limit') ?? 50);
      const filtered = search
        ? ALL_USERS.filter(
            (u) => u.email.includes(search) || `${u.given_name} ${u.family_name}`.toLowerCase().includes(search),
          )
        : ALL_USERS;
      return json(route, filtered.slice(skip, skip + limit));
    }
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: admin });
    if (path.endsWith('/user')) return json(route, admin ? SELF : { ...SELF, user_roles: [] });
    if (path.startsWith('/messages')) return json(route, []);
    // Anything else (maintenance status, etc.) — harmless empty object.
    return json(route, {});
  });
}

test.describe('admin users list', () => {
  test('pages through users with server-side skip/limit', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/users');

    // First page: 50 rows, user1 visible, user51 not.
    await expect(page.getByText('user1@example.org')).toBeVisible();
    await expect(page.getByText('user51@example.org')).not.toBeVisible();
    await expect(page.getByText('Page 1')).toBeVisible();

    const next = page.getByRole('button', { name: 'Next', exact: true });
    const prev = page.getByRole('button', { name: 'Previous', exact: true });
    await expect(prev).toBeDisabled();
    await expect(next).toBeEnabled();

    // Second page: remaining 10 users; Next disabled (short page).
    await next.click();
    await expect(page.getByText('user51@example.org')).toBeVisible();
    await expect(page.getByText('user1@example.org', { exact: true })).not.toBeVisible();
    await expect(page.getByText('Page 2')).toBeVisible();
    await expect(next).toBeDisabled();
    await expect(prev).toBeEnabled();
  });

  test('search box queries the backend and resets to page 1', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/users');
    await expect(page.getByText('user1@example.org')).toBeVisible();

    await page.getByPlaceholder('Search by email or name…').fill('user42');
    // Debounced server-side search: only the matching row remains.
    await expect(page.getByText('user42@example.org')).toBeVisible();
    await expect(page.getByText('user1@example.org', { exact: true })).not.toBeVisible();
    await expect(page.getByText('Page 1')).toBeVisible();
  });

  test('non-managers are shown the forbidden state', async ({ page }) => {
    await setup(page, { admin: false });
    await page.goto('/admin/users');

    await expect(page.getByText('Access denied. Requires admin or _user_manager role.')).toBeVisible();
    await expect(page.getByText('user1@example.org')).not.toBeVisible();
  });
});
