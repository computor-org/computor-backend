import { test, expect, type Page, type Route } from '@playwright/test';

// Terms 1.6 rollout (playwright.config.ts builds with the computor-at profile and
// NEXT_PUBLIC_TERMS_EFFECTIVE_FROM=2026-12-07, so release day is 2026-11-02).
// Accounts from before release day see a dismissible notice until a week after
// the effective date; later accounts accepted 1.6 at signup and see none.

const API_ORIGIN = 'http://localhost:8000';
const EXISTING = '2026-10-01T09:00:00Z';
const NEW_SIGNUP = '2026-11-05T09:00:00Z';

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

async function signIn(page: Page, createdAt: string, now: string) {
  await page.clock.setFixedTime(new Date(now));
  await page.addInitScript((created) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [],
      language: null, createdAt: created,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, createdAt);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: {} });
    if (path === '/user') return json(route, {
      id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner',
      user_roles: [], profile: null, created_at: createdAt, is_service: false,
    });
    if (path.startsWith('/messages') || path === '/courses') return json(route, []);
    return json(route, {});
  });
}

const notice = (page: Page) => page.getByRole('note').filter({ hasText: 'version 1.6' });

test('an existing account sees the notice once, with links, until it is dismissed', async ({ page }) => {
  await signIn(page, EXISTING, '2026-11-03T10:00:00Z');
  await page.goto('/courses');
  await expect(notice(page)).toContainText('New Terms of Use (version 1.6) apply from 7 December 2026.');
  await expect(notice(page).getByRole('link', { name: 'What changes' })).toHaveAttribute('href', '/terms/en/changes');
  await expect(notice(page).getByRole('link', { name: 'Privacy notice 1.6' })).toHaveAttribute('href', '/privacy/en');
  await notice(page).getByRole('button', { name: 'Dismiss notice' }).click();
  await expect(notice(page)).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('complementary')).toBeVisible();
  await expect(notice(page)).toHaveCount(0);
});

test.describe('German interface', () => {
  test.use({ locale: 'de-AT' });

  test('the notice is German', async ({ page }) => {
    await signIn(page, EXISTING, '2026-12-13T10:00:00Z');
    await page.goto('/courses');
    const de = page.getByRole('note').filter({ hasText: 'Version 1.6' });
    await expect(de).toContainText('Ab 07.12.2026 gelten neue Nutzungsbedingungen (Version 1.6). Du musst nichts tun.');
    await expect(de.getByRole('link', { name: 'Was sich ändert' })).toHaveAttribute('href', '/terms/changes');
    await expect(de.getByRole('link', { name: 'Datenschutzerklärung 1.6' })).toHaveAttribute('href', '/privacy');
  });
});

test('no notice for an account created after release day', async ({ page }) => {
  await signIn(page, NEW_SIGNUP, '2026-11-06T10:00:00Z');
  await page.goto('/courses');
  await expect(page.getByRole('complementary')).toBeVisible();
  await expect(notice(page)).toHaveCount(0);
});

test('no notice a week after the effective date', async ({ page }) => {
  await signIn(page, EXISTING, '2026-12-14T10:00:00Z');
  await page.goto('/courses');
  await expect(page.getByRole('complementary')).toBeVisible();
  await expect(notice(page)).toHaveCount(0);
});

// Terms 1.7 need consent at sign-in, so their pages carry a fixed date, not the notice date.
test('the terms and changes pages show version 1.7', async ({ page }) => {
  await page.goto('/terms/de');
  await expect(page.getByText('Version 1.7, Stand 29.10.2026')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Was sich ändert' })).toHaveAttribute('href', '/terms/changes');
  await page.goto('/terms/en/changes');
  await expect(page.getByRole('heading', { name: 'What changes' })).toBeVisible();
  await expect(page.getByText('Terms of Use version 1.7, dated 29 October 2026')).toBeVisible();
  await expect(page.locator('article').getByRole('listitem')).toHaveCount(5);
});
