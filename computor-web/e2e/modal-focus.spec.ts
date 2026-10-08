import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Modal focus handling (issues#437): typing in a dialog field that is not the
 * first one must keep focus and caret there. The invite dialog passes an
 * inline onClose, so every keystroke re-renders the Modal with a new handler.
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

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
    sessionStorage.setItem('auth_provider', 'sso');
  }, {
    id: SELF.id,
    username: SELF.username,
    email: SELF.email,
    givenName: SELF.given_name,
    familyName: SELF.family_name,
    role: 'admin',
    systemRoles: ['_admin'],
  });

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/admin/invites') return json(route, []);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    if (path.startsWith('/roles')) return json(route, []);
    return json(route, {});
  });
}

test('typing in a later dialog field keeps focus there', async ({ page }) => {
  await setup(page);
  await page.goto('/admin/users/invites');
  await page.getByRole('button', { name: /New Invite/i }).click();

  const dialog = page.getByRole('dialog', { name: 'New invite link' });
  const email = dialog.getByPlaceholder('student@example.com');
  const note = dialog.getByPlaceholder('e.g. WS2024 students');

  // Opening still moves focus into the dialog (its first field).
  await expect(email).toBeFocused();

  await email.fill('student@example.com');
  await note.click();
  await page.keyboard.type('WS2026 cohort');

  await expect(note).toBeFocused();
  await expect(note).toHaveValue('WS2026 cohort');
  await expect(email).toHaveValue('student@example.com');

  // Escape still closes through the latest onClose.
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
});
