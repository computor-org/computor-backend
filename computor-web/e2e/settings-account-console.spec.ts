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

async function setup(page: Page, providers: unknown, extra: Record<string, unknown> = {}) {
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
    if (path in extra) return json(route, extra[path]);
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

// Accounts, workspace tokens and the version are named for the learner, not by
// provider ids, internal addresses, token names or a detached "HEAD".
test('accounts, tokens and the version read without internal names', async ({ page }) => {
  await setup(page, [], {
    '/accounts': [
      { id: 'a1', provider: 'keycloak', type: 'oidc', provider_account_id: '6f1c2d3e-0000-4000-8000-00000000abcd', user_id: 'u-1', builtin: true },
      { id: 'a2', provider: 'http://forgejo:3030', type: 'forgejo', provider_account_id: 'ada@example.org', user_id: 'u-1', builtin: true },
    ],
    '/api-tokens': [{ id: 't1', name: 'workspace-auto-login:vscode', token_prefix: 'ctp_ab', created_at: '2026-10-01T10:00:00Z', expires_at: null, last_used_at: null, revoked_at: null }],
    '/instance-status': { started_at: '2026-10-29T08:00:00Z', uptime_seconds: 3600, commit: null, branch: 'HEAD', build_time: '2026-10-29T07:00:00Z' },
  });
  await page.goto('/settings');
  await expect(page.getByText(/^Computor account/)).toBeVisible();
  await expect(page.getByText(/^Git server \(Forgejo\)/)).toBeVisible();
  await expect(page.getByText('Workspace sign-in', { exact: true })).toBeVisible();
  await expect(page.getByText('Server online since')).toBeVisible();
  for (const raw of ['Oidc', 'keycloak', '6f1c2d3e-0000-4000-8000-00000000abcd', 'forgejo:3030', 'workspace-auto-login:vscode', 'HEAD']) {
    await expect(page.getByText(raw)).toHaveCount(0);
  }
});
