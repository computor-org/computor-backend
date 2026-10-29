import { test, expect, type Page, type Route } from '@playwright/test';

// Admin pages speak one language, like the learner pages: German for a German
// browser, English when the profile language says so. Guards the staff pages
// against falling back to English bodies inside a German interface.

const API_ORIGIN = 'http://localhost:8000';

const USERS = [{
  id: 'u-001', username: 'user1', email: 'user1@example.org', given_name: 'Given', family_name: 'Family',
  archived_at: null, is_service: false, created_at: '2026-01-15T10:00:00Z',
}];

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

async function signInAsAdmin(page: Page, profileLanguage: string | null) {
  await page.addInitScript((language) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'u-admin', username: 'admin1', email: 'admin1@example.org',
      givenName: 'Ada', familyName: 'Root', role: 'admin', systemRoles: ['_admin'], language,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, profileLanguage);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/users') return json(route, USERS);
    if (path === '/git-servers') return json(route, []);
    if (path === '/courses/c-1') return json(route, {
      id: 'c-1', title: 'Algorithmen', path: 'algorithms', course_family_id: 'f-1', organization_id: 'o-1', language_code: 'de',
    });
    if (path === '/course-families') return json(route, [{ id: 'f-1', title: 'Algorithmen', organization_id: 'o-1' }]);
    if (path === '/system/maintenance/status') return json(route, { active: true, message: null, scheduled_at: null });
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, {
      id: 'u-admin', email: 'admin1@example.org', given_name: 'Ada', family_name: 'Root',
      user_roles: [{ role_id: '_admin' }],
      profile: profileLanguage ? { id: 'p', language_code: profileLanguage } : null,
    });
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
}

test.describe('German browser', () => {
  test.use({ locale: 'de-AT' });

  test('admin users and git servers are German', async ({ page }) => {
    await signInAsAdmin(page, null);
    await page.goto('/admin/users');
    await expect(page.getByRole('heading', { name: 'Benutzer', exact: true })).toBeVisible();
    await expect(page.getByPlaceholder('Nach E-Mail oder Name suchen…')).toBeVisible();
    await expect(page.getByText('user1@example.org')).toBeVisible();
    await expect(page.getByText('Users', { exact: true })).toHaveCount(0);

    await page.goto('/admin/git-servers');
    await expect(page.getByRole('button', { name: 'Server registrieren' })
      .or(page.getByRole('link', { name: 'Server registrieren' }))).toBeVisible();
    await expect(page.getByText('Register Server')).toHaveCount(0);
  });

  test('an English profile language wins over the browser', async ({ page }) => {
    await signInAsAdmin(page, 'en');
    await page.goto('/admin/users');
    await expect(page.getByRole('heading', { name: 'Users', exact: true })).toBeVisible();
    await expect(page.getByPlaceholder('Search by email or name…')).toBeVisible();
    await expect(page.getByText('Benutzer', { exact: true })).toHaveCount(0);
  });

  // Course settings, course creation and the maintenance banner were English
  // in a German interface (computor-org/issues#552).
  test('course settings are German', async ({ page }) => {
    await signInAsAdmin(page, null);
    await page.goto('/courses/c-1/edit');
    await expect(page.getByRole('heading', { name: 'Kurs bearbeiten' })).toBeVisible();
    await expect(page.getByLabel('Plätze für die Selbstanmeldung')).toBeVisible();
    await expect(page.getByText('Kurs für die Selbstanmeldung im Katalog anbieten')).toBeVisible();
    await expect(page.getByText('Wartungsmodus aktiv')).toBeVisible();
    await expect(page.getByText(/Self-registration|Edit course|Default max|Maintenance Mode/)).toHaveCount(0);
  });

  test('creating a course is German', async ({ page }) => {
    await signInAsAdmin(page, null);
    await page.goto('/courses/create');
    await expect(page.getByRole('heading', { name: 'Neuer Kurs' })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /^Kursfamilie/ })).toBeVisible();
    await expect(page.getByText('Nachrichten von Studierenden ohne @-Erwähnung an Lena senden')).toBeVisible();
    await expect(page.getByText(/Course family|Import from file|Send student messages/)).toHaveCount(0);
  });
});
