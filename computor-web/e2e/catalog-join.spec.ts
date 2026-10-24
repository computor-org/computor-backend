import { test, expect, type Page, type Route } from '@playwright/test';

// issues#521: "Anmelden und beitreten" on a public course page has to end in
// that course, not in the generic catalog.

const API_ORIGIN = 'http://localhost:8000';
const COURSES = [
  { id: 'c-intermediate', title: 'Data Science mit Python – Aufbau', path: 'python.intermediate', enrolled: false },
  { id: 'c-beginner', title: 'Data Science mit Python – Grundlagen', path: 'python.beginner', enrolled: false },
  { id: 'c-advanced', title: 'Data Science mit Python – Vertiefung', path: 'python.advanced', enrolled: true },
].map((course) => ({ ...course, language_code: 'de', description: 'Synthetic test course.' }));

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, { signedIn = true } = {}) {
  const enrolled: string[] = [];
  if (signedIn) {
    await page.addInitScript(() => {
      sessionStorage.setItem('auth_user', JSON.stringify({
        id: 'learner', username: 'learner', email: 'learner@example.org',
        givenName: 'Course', familyName: 'Learner', role: 'user', systemRoles: [],
      }));
      sessionStorage.setItem('auth_provider', 'sso');
    });
  }
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const enroll = path.match(/^\/user\/courses\/([^/]+)\/enroll$/);
    if (enroll && request.method() === 'POST') {
      enrolled.push(enroll[1]);
      return json(route, {});
    }
    if (path === '/courses/public') return json(route, COURSES);
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: {} });
    if (path === '/user') return json(route, {
      id: 'learner', username: 'learner', email: 'learner@example.org',
      given_name: 'Course', family_name: 'Learner', user_roles: [],
    });
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
  return enrolled;
}

test('signed out, both sign-in links on a public course return to that course', async ({ page }) => {
  await setup(page, { signedIn: false });
  await page.goto('/learn/python-beginner');
  const next = `/login?next=${encodeURIComponent('/courses/catalog?join=python.beginner')}`;
  await expect(page.getByRole('link', { name: 'Sign in to join' })).toHaveAttribute('href', next);
  await expect(page.getByRole('banner').getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', next);
});

test('signed in, the reader opens the join confirmation for the chosen course', async ({ page }) => {
  const enrolled = await setup(page);
  await page.goto('/learn/python-beginner');
  await page.getByRole('link', { name: 'Open the course catalog' }).click();
  await expect(page).toHaveURL(/\/courses\/catalog\?join=python\.beginner$/);
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Join this course?')).toBeVisible();
  await expect(dialog.getByText(/Data Science mit Python – Grundlagen/)).toBeVisible();
  await expect(page.locator('[aria-current="true"]')).toContainText('Data Science mit Python – Grundlagen');
  await dialog.getByRole('button', { name: 'Join course' }).click();
  await expect(page).toHaveURL(/\/courses\/c-beginner$/);
  expect(enrolled).toEqual(['c-beginner']);
});

test('a cancelled confirmation leaves the chosen course marked in the catalog', async ({ page }) => {
  const enrolled = await setup(page);
  await page.goto('/courses/catalog?join=python.beginner');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('[aria-current="true"]')).toContainText('Data Science mit Python – Grundlagen');
  expect(enrolled).toEqual([]);
});

test('a course the learner already belongs to opens directly', async ({ page }) => {
  const enrolled = await setup(page);
  await page.goto('/courses/catalog?join=python.advanced');
  await expect(page).toHaveURL(/\/courses\/c-advanced$/);
  expect(enrolled).toEqual([]);
});

test('an unknown course leaves the plain catalog', async ({ page }) => {
  await setup(page);
  await page.goto('/courses/catalog?join=python.unknown');
  await expect(page.getByRole('heading', { name: 'Data Science mit Python – Grundlagen' })).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('[aria-current="true"]')).toHaveCount(0);
});

test.describe('German catalog', () => {
  test.use({ locale: 'de-DE' });
  // "Angemeldet" also means "signed in", which every learner here is.
  test('a joined course is marked "Beigetreten"', async ({ page }) => {
    await setup(page);
    await page.goto('/courses/catalog');
    await expect(page.getByText('Beigetreten', { exact: true })).toHaveCount(1);
    await expect(page.getByText('Angemeldet', { exact: true })).toHaveCount(0);
  });
});

test('on a phone the sidebar starts as an icon rail and leaves the page its width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await setup(page);
  await page.goto('/courses/catalog');
  await expect(page.getByRole('button', { name: 'Expand sidebar' })).toBeVisible();
  const box = await page.getByRole('heading', { name: 'Data Science mit Python – Grundlagen' }).boundingBox();
  expect(box!.width).toBeGreaterThan(200);
});

test('on a desktop the sidebar starts expanded', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setup(page);
  await page.goto('/courses/catalog');
  await expect(page.getByRole('button', { name: 'Collapse sidebar' })).toBeVisible();
});
