import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * When the API last restarted and what it is running (#350), on both surfaces
 * that show it: System → Status for the operator, and Settings → About this
 * instance for everyone else.
 *
 * The cases worth pinning are the honest ones: a built image reports when it was
 * built, a working tree says it is not a built image rather than showing a blank
 * where a date belongs, and a non-admin is told the uptime without the commit.
 */

const API_ORIGIN = 'http://localhost:8000';

const USER = {
  id: 'u-admin',
  username: 'admin',
  email: 'admin@example.org',
  given_name: 'Ada',
  family_name: 'Admin',
  user_roles: [{ role_id: '_admin' }],
};

const STATUS = {
  started_at: '2026-08-27T04:12:00Z',
  uptime_seconds: 108_000, // 1d 6h
  commit: '9f3c1abfeed0000000000000000000000000000',
  branch: 'release/2026.10',
  build_time: '2026-08-26T21:40:00Z',
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, { isAdmin = true, status = STATUS as unknown } = {}) {
  await page.addInitScript(([user, admin]) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: (user as typeof USER).id,
      username: (user as typeof USER).username,
      email: (user as typeof USER).email,
      givenName: (user as typeof USER).given_name,
      familyName: (user as typeof USER).family_name,
      role: admin ? 'admin' : 'user',
      systemRoles: admin ? ['_admin'] : [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, [USER, isAdmin] as const);

  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: isAdmin });
    if (path.endsWith('/user')) return json(route, { ...USER, user_roles: isAdmin ? USER.user_roles : [] });
    if (path.startsWith('/messages')) return json(route, []);
    // Settings' own calls, so the About section can be exercised on that page.
    if (path.startsWith('/api-tokens')) return json(route, []);
    if (path.startsWith('/accounts')) return json(route, []);
    if (path === '/consent/status') return json(route, { required_version: null });
    if (path === '/instance-status') {
      // The endpoint answers everyone; it withholds the commit from a non-admin.
      // Mirrored here so the mock cannot drift into justifying the page's gate.
      return json(route, isAdmin ? status : { ...(status as object), commit: null });
    }
    return json(route, {});
  });
}

test('reports the restart, the uptime and the running build', async ({ page }) => {
  await setup(page);
  await page.goto('/admin/status');

  await expect(page.getByText('up 1d 6h')).toBeVisible();
  await expect(page.getByText('9f3c1ab', { exact: true })).toBeVisible();
  await expect(page.getByText('release/2026.10')).toBeVisible();
  // Rendered in the viewer's locale, so assert the date rather than the format.
  await expect(page.getByText(/2026/).first()).toBeVisible();
});

test('a working tree says so instead of leaving the build date blank', async ({ page }) => {
  await setup(page, { status: { ...STATUS, build_time: null, commit: 'unknown', branch: 'unknown' } });
  await page.goto('/admin/status');

  await expect(page.getByText('not a built image (development)')).toBeVisible();
  await expect(page.getByText('unknown').first()).toBeVisible();
});

// The operator page stays under /admin with its siblings even though the data
// behind it is no longer admin-only — a non-admin reads the same restart time
// from Settings → About this instance, without the commit.
test('non-admins are turned away', async ({ page }) => {
  await setup(page, { isAdmin: false });
  await page.goto('/admin/status');

  await expect(page.getByText('Access Denied')).toBeVisible();
  await expect(page.getByText('up 1d 6h')).toBeHidden();
});

test('Settings tells a non-admin the uptime without the commit', async ({ page }) => {
  await setup(page, { isAdmin: false });
  await page.goto('/settings');

  await expect(page.getByText('About this instance')).toBeVisible();
  await expect(page.getByText('up 1d 6h')).toBeVisible();
  await expect(page.getByText('release/2026.10')).toBeVisible();
  // Redacted by the API, so the row it would fill is not rendered at all.
  await expect(page.getByText('Server commit')).toBeHidden();
});
