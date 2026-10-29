import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Settings links the login provider's account console, where users add or
 * replace an authenticator app (issues#485). The link used to come from a
 * NEXT_PUBLIC_KEYCLOAK_URL no deployment's build carried, so computor.at never
 * showed it; the API now names it in /auth/providers.
 */

const API_ORIGIN = 'http://localhost:8000';
const CONSOLE = 'https://computor.at/auth/realms/computor/account/';

const USER = {
  id: 'u-1',
  username: 'ada',
  email: 'ada@example.org',
  given_name: 'Ada',
  family_name: 'Lovelace',
  user_roles: [],
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, providers: unknown) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id,
      username: user.username,
      email: user.email,
      givenName: user.given_name,
      familyName: user.family_name,
      role: 'user',
      systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path.startsWith('/api-tokens')) return json(route, []);
    if (path.startsWith('/accounts')) return json(route, []);
    if (path === '/consent/status') return json(route, { required_version: null });
    if (path === '/auth/providers') return json(route, providers);
    return json(route, {});
  });
}

test('links the account console the API names', async ({ page }) => {
  await setup(page, [{
    name: 'keycloak', display_name: 'Keycloak', type: 'oidc', enabled: true,
    login_url: '/auth/keycloak/login', account_url: CONSOLE,
  }]);
  await page.goto('/settings');

  const link = page.getByRole('link', { name: 'Open account console' });
  await expect(link).toHaveAttribute('href', CONSOLE);
  await expect(page.getByText('API tokens', { exact: true })).toBeVisible();
});

test('an API that names no console shows no section, and nothing else breaks', async ({ page }) => {
  // An older API without the field, then one whose value is not a web address.
  for (const accountUrl of [undefined, 'javascript:alert(1)']) {
    await setup(page, [{ name: 'keycloak', display_name: 'Keycloak', type: 'oidc', enabled: true, account_url: accountUrl }]);
    await page.goto('/settings');
    await expect(page.getByText('API tokens', { exact: true })).toBeVisible();
    await expect(page.getByText('Account & Security')).toHaveCount(0);
    await page.unrouteAll();
  }
});
