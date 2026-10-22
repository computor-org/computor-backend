import { test, expect, type Page, type Route } from '@playwright/test';

// The signed-in interface speaks one language: the profile language when the
// user chose one, else the browser language (German for de-*, English otherwise).

const API_ORIGIN = 'http://localhost:8000';
const COURSES = [{
  id: 'python', title: 'Python für Einsteiger', organization_title: 'TU Graz',
  language_code: 'de', description: 'Kurs aus dem Kurs-Repository.',
}];

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

async function signIn(page: Page, profileLanguage: string | null) {
  await page.addInitScript((language) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [], language,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, profileLanguage);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/courses/public' || path === '/courses') return json(route, COURSES);
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { python: ['_student'] } });
    if (path === '/user') return json(route, {
      id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner',
      user_roles: [], profile: profileLanguage ? { id: 'p', language_code: profileLanguage } : null,
    });
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
}

const sidebar = (page: Page) => page.getByRole('complementary');

test.describe('German browser', () => {
  test.use({ locale: 'de-AT' });

  test('my courses and the navigation are German', async ({ page }) => {
    await signIn(page, null);
    await page.goto('/courses');
    await expect(page.getByRole('heading', { name: COURSES[0].title })).toBeVisible();
    await expect(sidebar(page).getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
    await expect(sidebar(page).getByRole('link', { name: 'Katalog' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Benutzermenü' })).toBeVisible();
    await expect(page.getByText('My courses', { exact: true })).toHaveCount(0);
    await expect(page.locator('html')).toHaveAttribute('lang', 'de');
  });

  test('the catalog is German', async ({ page }) => {
    await signIn(page, null);
    await page.goto('/courses/catalog');
    await expect(page.getByRole('heading', { name: COURSES[0].title })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Join course' })).toHaveCount(0);
    await expect(page.getByText('Catalog', { exact: true })).toHaveCount(0);
  });

  test('an English profile language wins over the German browser', async ({ page }) => {
    await signIn(page, 'en');
    await page.goto('/courses');
    await expect(sidebar(page).getByRole('link', { name: 'My courses' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'User menu' })).toBeVisible();
  });
});

test('a German profile language wins over an English browser', async ({ page }) => {
  await signIn(page, 'de');
  await page.goto('/courses');
  await expect(sidebar(page).getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
  await page.getByRole('button', { name: 'Benutzermenü' }).click();
  await expect(page.getByRole('button', { name: 'Abmelden' })).toBeVisible();
});
