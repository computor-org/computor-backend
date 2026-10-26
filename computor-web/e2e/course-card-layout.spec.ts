import { test, expect, type Locator, type Page, type Route } from '@playwright/test';

const API_ORIGIN = 'http://localhost:8000';
const ORGANIZATION = 'Institute of Theoretical and Computational Physics';
const COURSES = [
  { id: 'beginner', title: 'Python for Beginners', enrolled: false },
  { id: 'intermediate', title: 'Python Intermediate', enrolled: true },
  { id: 'advanced', title: 'Python Advanced', enrolled: false },
].map((course) => ({
  ...course,
  organization_title: course.id === 'advanced' ? `${ORGANIZATION} ${'Research'.repeat(10)}` : ORGANIZATION,
  language_code: 'en',
  description: 'Practical programming exercises with examples and feedback.',
}));

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  });
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/courses/public' || path === '/courses') return json(route, COURSES);
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, {
      is_admin: false, course: Object.fromEntries(COURSES.map(({ id }) => [id, ['_student']])),
    });
    if (path === '/user') return json(route, {
      id: 'learner', username: 'learner', email: 'learner@example.org',
      given_name: 'Course', family_name: 'Learner', user_roles: [],
    });
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
}

async function expectUnclippedText(locator: Locator) {
  await expect(locator).toBeVisible();
  expect(await locator.evaluate((element) => ({
    horizontal: element.scrollWidth > element.clientWidth + 1,
    vertical: element.scrollHeight > element.clientHeight + 1,
  }))).toEqual({ horizontal: false, vertical: false });
}

for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`catalog titles and organization badges remain readable at ${viewport.width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await setup(page);
    await page.goto('/courses/catalog');
    if (viewport.width < 768) {
      // Phones start with the collapsed icon rail.
      await expect.poll(async () => (await page.getByRole('complementary').boundingBox())?.width).toBe(64);
    }
    await expect(page.getByRole('heading', { name: COURSES[0].title })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath('catalog.png'), fullPage: true });

    for (const course of COURSES) {
      const heading = page.getByRole('heading', { name: course.title, exact: true });
      await expectUnclippedText(heading);
      const badge = heading.locator('..').getByText(course.enrolled ? 'Enrolled' : course.organization_title, { exact: true });
      await expectUnclippedText(badge);
      const [titleBox, badgeBox, headerBox] = await Promise.all([
        heading.boundingBox(), badge.boundingBox(), heading.locator('..').boundingBox(),
      ]);
      expect(titleBox).not.toBeNull();
      expect(badgeBox).not.toBeNull();
      expect(headerBox).not.toBeNull();
      expect(badgeBox!.x + badgeBox!.width).toBeLessThanOrEqual(headerBox!.x + headerBox!.width + 1);
      // Readable text must not overlap, regardless of how the header is laid out.
      const overlaps = titleBox!.x < badgeBox!.x + badgeBox!.width
        && badgeBox!.x < titleBox!.x + titleBox!.width
        && titleBox!.y < badgeBox!.y + badgeBox!.height
        && badgeBox!.y < titleBox!.y + titleBox!.height;
      expect(overlaps).toBe(false);
    }
    await expect(page.getByRole('button', { name: 'Join course' })).toHaveCount(2);
    // An enrolled learner opens the course overview, as before (issues#521).
    await expect(page.getByRole('link', { name: 'Open course' })).toHaveAttribute('href', '/courses/intermediate');
  });

  test(`member course titles and role badges remain readable at ${viewport.width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize(viewport);
    await setup(page);
    await page.goto('/courses');
    if (viewport.width < 768) {
      // Phones start with the collapsed icon rail.
      await expect.poll(async () => (await page.getByRole('complementary').boundingBox())?.width).toBe(64);
    }
    await expect(page.getByRole('heading', { name: COURSES[0].title })).toBeVisible();
    for (const course of COURSES) {
      const heading = page.getByRole('heading', { name: course.title, exact: true });
      await expectUnclippedText(heading);
      await expectUnclippedText(heading.locator('..').getByText('Student', { exact: true }));
    }
    await page.screenshot({ path: testInfo.outputPath('member-courses.png'), fullPage: true });
  });
}
