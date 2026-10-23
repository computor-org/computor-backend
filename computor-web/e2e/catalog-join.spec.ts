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

async function setup(page: Page, { signedIn = true, courseRoles = { 'c-advanced': ['_student'] } as Record<string, string[]>, isAdmin = false, systemRoles = [] as string[] } = {}) {
  const enrolled: string[] = [];
  if (signedIn) {
    await page.addInitScript((roles) => {
      sessionStorage.setItem('auth_user', JSON.stringify({
        id: 'learner', username: 'learner', email: 'learner@example.org',
        givenName: 'Course', familyName: 'Learner', role: 'user', systemRoles: roles,
      }));
      sessionStorage.setItem('auth_provider', 'sso');
    }, systemRoles);
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
    if (path === '/user/scopes') return json(route, { is_admin: isAdmin, course: courseRoles });
    if (path === '/user') return json(route, {
      id: 'learner', username: 'learner', email: 'learner@example.org',
      given_name: 'Course', family_name: 'Learner', user_roles: systemRoles.map(role_id => ({ role_id })),
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


test('a cancelled confirmation leaves the chosen course marked in the catalog', async ({ page }) => {
  const enrolled = await setup(page);
  await page.goto('/courses/catalog?join=python.beginner');
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.locator('[aria-current="true"]')).toContainText('Data Science mit Python – Grundlagen');
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

for (const [locale, joinLabel, continueLabel, openLabel] of [
  ['en-US', 'Join course', 'Continue', 'Open course'],
  ['de-DE', 'Kurs beitreten', 'Weiterlernen', 'Kurs öffnen'],
] as const) {
  test.describe(`catalog learner continuation (${locale})`, () => {
    test.use({ locale });
    test('confirmed enrollment opens assignments before refreshed student scopes arrive', async ({ page }) => {
      const enrolled = await setup(page);
      await page.goto('/learn/python-beginner');
      await page.getByRole('link', { name: locale === 'de-DE' ? 'Zum Kurskatalog' : 'Open the course catalog' }).click();
      await expect(page).toHaveURL(/\/courses\/catalog\?join=python\.beginner$/);
      const dialog = page.getByRole('dialog');
      await expect(dialog.getByText(locale === 'de-DE' ? 'Diesem Kurs beitreten?' : 'Join this course?')).toBeVisible();
      await expect(dialog.getByText(/Data Science mit Python – Grundlagen/)).toBeVisible();
      await expect(page.locator('[aria-current="true"]')).toContainText('Data Science mit Python – Grundlagen');
      await dialog.getByRole('button', { name: joinLabel }).click();
      await expect(page).toHaveURL(/\/courses\/c-beginner\/student\/assignments$/);
      expect(enrolled).toEqual(['c-beginner']);
    });
    test('an enrolled learner join link opens assignments', async ({ page }) => {
      const enrolled = await setup(page);
      await page.goto('/courses/catalog?join=python.advanced');
      await expect(page).toHaveURL(/\/courses\/c-advanced\/student\/assignments$/);
      expect(enrolled).toEqual([]);
    });
    test('learner footer continues to assignments and catalog titles stay plain', async ({ page }) => {
      await setup(page);
      await page.goto('/courses/catalog');
      await expect(page.getByRole('link', { name: continueLabel, exact: true })).toHaveAttribute('href', '/courses/c-advanced/student/assignments');
      await expect(page.getByRole('link', { name: COURSES[2].title, exact: true })).toHaveCount(0);
    });
    for (const staff of ['tutor', 'lecturer', 'admin', 'organization manager']) {
      test(`${staff} keeps overview for all three entries`, async ({ page }) => {
        await setup(page, {
          courseRoles: Object.fromEntries(COURSES.map(course => [course.id, ['_student', ...(staff === 'tutor' ? ['_tutor'] : staff === 'lecturer' ? ['_lecturer'] : [])]])),
          isAdmin: staff === 'admin',
          systemRoles: staff === 'organization manager' ? ['_organization_manager'] : [],
        });
        await page.goto('/courses/catalog?join=python.beginner');
        await page.getByRole('dialog').getByRole('button', { name: joinLabel }).click();
        await expect(page).toHaveURL(/\/courses\/c-beginner$/);
        await page.goto('/courses/catalog');
        await expect(page.getByRole('link', { name: openLabel, exact: true })).toHaveAttribute('href', '/courses/c-advanced');
        await page.goto('/courses/catalog?join=python.advanced');
        await expect(page).toHaveURL(/\/courses\/c-advanced$/);
      });
    }
    test('enrolled without actual student permission keeps overview', async ({ page }) => {
      await setup(page, { courseRoles: {} });
      await page.goto('/courses/catalog');
      await expect(page.getByRole('link', { name: openLabel, exact: true })).toHaveAttribute('href', '/courses/c-advanced');
      await page.goto('/courses/catalog?join=python.advanced');
      await expect(page).toHaveURL(/\/courses\/c-advanced$/);
    });
  });
}
