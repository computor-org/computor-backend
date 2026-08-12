import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * The `[id]/edit` pages seed their form state from the loaded entity during
 * render (React's "adjust state when data changes" pattern) rather than from an
 * effect. That is easy to get subtly wrong in two directions, so both are
 * pinned here: the inputs must pick up server values, and a later re-render
 * must NOT re-seed and discard what the user has typed.
 *
 * Backend is mocked at the network layer; no API or database needed.
 */

const API_ORIGIN = 'http://localhost:8000';

const SELF = {
  id: 'u-admin',
  username: 'admin1',
  email: 'admin1@example.org',
  given_name: 'Ada',
  family_name: 'Root',
  user_roles: [{ role_id: '_admin' }],
};

const TARGET = {
  id: 'u-001',
  username: 'jdoe',
  email: 'jane.doe@example.org',
  given_name: 'Jane',
  family_name: 'Doe',
  archived_at: null,
  is_service: false,
};

const ORG = {
  id: 'org-1',
  title: 'Faculty of Informatics',
  description: 'The org description',
  organization_type: 'organization',
  path: 'informatics',
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
    sessionStorage.setItem('auth_provider', 'sso');
  }, {
    id: SELF.id, username: SELF.username, email: SELF.email,
    givenName: SELF.given_name, familyName: SELF.family_name,
    role: 'admin', systemRoles: ['_admin'],
  });

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === `/users/${TARGET.id}`) return json(route, TARGET);
    if (path === `/organizations/${ORG.id}`) return json(route, ORG);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
}

test('user edit form seeds its inputs from the loaded user', async ({ page }) => {
  await setup(page);
  await page.goto(`/admin/users/${TARGET.id}/edit`);

  await expect(page.getByLabel('Email')).toHaveValue('jane.doe@example.org', { timeout: 10_000 });
  await expect(page.getByLabel('Given name')).toHaveValue('Jane');
  await expect(page.getByLabel('Family name')).toHaveValue('Doe');
});

test('user edit form stays editable after seeding', async ({ page }) => {
  await setup(page);
  await page.goto(`/admin/users/${TARGET.id}/edit`);

  const given = page.getByLabel('Given name');
  await expect(given).toHaveValue('Jane', { timeout: 10_000 });
  await given.fill('Janet');
  // A later re-render must not re-seed and clobber the edit back to 'Jane'.
  await expect(given).toHaveValue('Janet');
  await page.getByLabel('Email').fill('janet@example.org');
  await expect(given).toHaveValue('Janet');
});

test('organization edit form seeds title and description', async ({ page }) => {
  await setup(page);
  await page.goto(`/organizations/${ORG.id}/edit`);

  await expect(page.getByLabel('Title')).toHaveValue('Faculty of Informatics', { timeout: 10_000 });
  await expect(page.getByLabel('Description')).toHaveValue('The org description');
});
