import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Admin → Services: the service-account admin surface.
 * Self-contained network mocks, modelled on admin-users.spec.ts.
 *
 * The assertions that matter beyond "it renders":
 *  - the scope-semantics warning is present wherever a token is minted
 *    (scopes are additive, so a token is never weaker than its account);
 *  - the reveal panel shows the token value exactly once;
 *  - `_service_manager` reaches the page, a plain user does not.
 */

const API_ORIGIN = 'http://localhost:8000';

const SERVICE = {
  id: 'svc-1',
  slug: 'acme.exec.py',
  name: 'Acme Python Runner',
  description: 'Third-party python runner',
  service_type_id: 'st-1',
  service_type_path: 'testing.temporal',
  user_id: 'u-svc-1',
  config: { language: 'python', temporal: { task_queue: 'testing' } },
  enabled: true,
  last_seen_at: null,
  created_at: '2026-07-01T10:00:00Z',
};

const AGENT = {
  ...SERVICE,
  id: 'svc-2',
  slug: 'demo.tutor.agent',
  name: 'Demo Tutor Agent',
  description: null,
  service_type_path: 'agent',
  user_id: 'u-svc-2',
  config: {},
};

const SERVICE_TYPES = [
  { id: 'st-1', path: 'testing.temporal', name: 'Temporal Testing Worker', category: 'testing', enabled: true, version: 0 },
  { id: 'st-2', path: 'agent', name: 'AI Agent', category: 'agent', enabled: true, version: 0 },
];

const EXISTING_TOKEN = {
  id: 'tok-1',
  name: 'Worker Token',
  description: null,
  user_id: 'u-svc-1',
  token_prefix: 'ctp_abcdefgh',
  scopes: ['result:create', 'result:update'],
  expires_at: null,
  last_used_at: null,
  usage_count: 0,
  revoked_at: null,
  created_at: '2026-07-01T10:00:00Z',
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

type Role = '_admin' | '_service_manager' | 'none';

async function setup(page: Page, role: Role = '_admin') {
  const systemRoles = role === 'none' ? [] : [role];
  await page.addInitScript((roles) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'u-caller',
      username: 'caller',
      email: 'caller@example.org',
      givenName: 'Cal',
      familyName: 'Ler',
      role: roles.includes('_admin') ? 'admin' : 'user',
      systemRoles: roles,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
    sessionStorage.setItem('auth_views', '[]');
  }, systemRoles);

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();

    if (path === '/service-accounts') return json(route, [SERVICE, AGENT]);
    if (path === '/service-accounts/svc-1') return json(route, SERVICE);
    if (path === '/service-accounts/svc-2') return json(route, AGENT);
    if (path === '/service-types') return json(route, SERVICE_TYPES);

    if (path === '/api-tokens' && method === 'POST') {
      return json(route, {
        id: 'tok-new',
        token: 'ctp_thisIsTheOnlyTimeYouSeeIt00',
        name: 'new token',
        description: null,
        user_id: 'u-svc-1',
        token_prefix: 'ctp_thisIsTh',
        scopes: ['result:create', 'result:update', 'example:download'],
        expires_at: null,
        created_at: '2026-07-27T10:00:00Z',
      }, 201);
    }
    if (path === '/api-tokens') return json(route, [EXISTING_TOKEN]);
    if (path === '/course-members') return json(route, []);
    if (path === '/courses') return json(route, []);

    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: role === '_admin' });
    // `/user` must echo the caller's roles: AuthContext refreshes the session
    // from it, so returning `{}` here silently wipes systemRoles and every
    // role-gated assertion below fails for the wrong reason.
    if (path.endsWith('/user')) {
      return json(route, {
        id: 'u-caller',
        email: 'caller@example.org',
        given_name: 'Cal',
        family_name: 'Ler',
        user_roles: systemRoles.map((role_id) => ({ role_id })),
      });
    }
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
}

test.describe('admin services', () => {
  test('lists services with slug, type and language', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/services');

    await expect(page.getByRole('heading', { name: 'Service Accounts' })).toBeVisible();
    await expect(page.getByText('acme.exec.py')).toBeVisible();
    await expect(page.getByText('testing.temporal').first()).toBeVisible();
    await expect(page.getByText('python').first()).toBeVisible();
    // "never" is the tell that a worker has not checked in.
    await expect(page.getByText('never').first()).toBeVisible();
  });

  test('detail page explains the slug binding and shows config', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/services/svc-1');

    await expect(page.getByText(/properties\.executionBackend\.slug/)).toBeVisible();
    await expect(page.getByText(/"language": "python"/)).toBeVisible();
    await expect(page.getByText('testing', { exact: true }).first()).toBeVisible();
  });

  test('token section warns that scopes only add permissions', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/services/svc-1');

    await expect(page.getByText(/Scopes only add permissions/)).toBeVisible();
    await expect(page.getByText(/full permissions of its account/)).toBeVisible();
  });

  test('minting a token reveals the value exactly once', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/services/svc-1');

    await page.getByPlaceholder(/token/i).first().fill('ui token');
    await page.getByRole('button', { name: 'Create token' }).click();

    await expect(page.getByText(/copy it now/)).toBeVisible();
    await expect(page.getByText('ctp_thisIsTheOnlyTimeYouSeeIt00')).toBeVisible();
    // The backend-applied defaults are surfaced, so an empty scope box is not
    // mistaken for "no permissions".
    await expect(page.getByText(/Granted 3 default scope/)).toBeVisible();

    await page.getByRole('button', { name: 'Dismiss' }).click();
    await expect(page.getByText('ctp_thisIsTheOnlyTimeYouSeeIt00')).not.toBeVisible();
  });

  test('agent services get the course-enrolment section, testing services do not', async ({ page }) => {
    await setup(page);

    await page.goto('/admin/services/svc-2');
    await expect(page.getByText('Course memberships')).toBeVisible();

    await page.goto('/admin/services/svc-1');
    await expect(page.getByText('Course memberships')).not.toBeVisible();
  });

  test('create form only asks for a language on testing types', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/services/create');

    const languageHint = page.getByText('Selects the test runner.');
    const queueLabel = page.getByText('Temporal task queue');

    await expect(page.getByText(/meta\.yaml/)).toBeVisible();
    await expect(languageHint).toHaveCount(0);

    await page.getByRole('combobox').first().selectOption('testing.temporal');
    await expect(languageHint).toBeVisible();
    await expect(queueLabel).toBeVisible();

    // An agent service runs no tests, so neither field applies.
    await page.getByRole('combobox').first().selectOption('agent');
    await expect(languageHint).toHaveCount(0);
    await expect(queueLabel).toHaveCount(0);
  });

  test('_service_manager reaches the page; a plain user does not', async ({ page }) => {
    await setup(page, '_service_manager');
    await page.goto('/admin/services');
    await expect(page.getByRole('heading', { name: 'Service Accounts' })).toBeVisible();
  });

  test('plain user is forbidden', async ({ page }) => {
    await setup(page, 'none');
    await page.goto('/admin/services');
    await expect(page.getByText(/service-manager access is required/)).toBeVisible();
  });
});
