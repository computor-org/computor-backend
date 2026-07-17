import { test, expect, type Page, type Route } from '@playwright/test';

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = '00000000-0000-0000-0000-0000000000c1';

const COURSE = { id: COURSE_ID, title: 'Programming 101', path: 'prog.2026' };

const USER = {
  id: 'u-lect',
  username: 'lect',
  email: 'lect@example.org',
  given_name: 'Lea',
  family_name: 'Lecturer',
  user_roles: [],
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

/** A minimal but real zip — the page saves whatever bytes the API returns. */
const ZIP_BYTES = Buffer.from('504b0506000000000000000000000000000000000000', 'hex');

type Options = {
  /** Course roles reported by /user/scopes; [] makes the user a non-lecturer. */
  courseRoles?: string[];
  /** Fail the download with this status + body instead of serving the zip. */
  failWith?: { status: number; body: unknown };
  /** Serve no readable Content-Disposition (header absent, or not CORS-exposed). */
  withoutDisposition?: boolean;
};

async function setup(page: Page, options: Options = {}) {
  const { courseRoles = ['_lecturer'], failWith, withoutDisposition } = options;

  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  /** Every template request the page issued, in order. */
  const downloads: string[] = [];

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    // Covers both /user/views and the course-scoped /user/views/{id} the
    // sidebar uses — the latter must be an array or Sidebar throws.
    if (path.startsWith('/user/views')) return json(route, ['lecturer']);
    if (path.endsWith('/user/scopes')) {
      return json(route, { is_admin: false, course: { [COURSE_ID]: courseRoles } });
    }
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);

    if (path === `/courses/${COURSE_ID}/template`) {
      downloads.push(url.search);
      if (failWith) {
        return route.fulfill({
          status: failWith.status,
          contentType: 'application/json',
          body: JSON.stringify(failWith.body),
        });
      }
      const hierarchical = url.searchParams.get('hierarchical') === 'true';
      return route.fulfill({
        status: 200,
        contentType: 'application/zip',
        headers: withoutDisposition
          ? {}
          : {
              'content-disposition': `attachment; filename="template${hierarchical ? '-hierarchical' : ''}.zip"`,
              // The API is a different origin, so the filename is only readable
              // because the backend exposes the header (server.py CORS config).
              'access-control-expose-headers': 'Content-Disposition',
            },
        body: ZIP_BYTES,
      });
    }
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    return json(route, {});
  });

  return { downloads };
}

test('downloads the flat template as it is in git', async ({ page }) => {
  const { downloads } = await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/templates`);

  const save = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download ZIP' }).first().click();

  expect((await save).suggestedFilename()).toBe('template.zip');
  expect(downloads).toEqual(['?hierarchical=false']);
});

test('downloads the hierarchical template under its own filename', async ({ page }) => {
  const { downloads } = await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/templates`);

  const save = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download ZIP' }).nth(1).click();

  expect((await save).suggestedFilename()).toBe('template-hierarchical.zip');
  expect(downloads).toEqual(['?hierarchical=true']);
});

test('falls back to a course-derived filename when the header is unreadable', async ({ page }) => {
  await setup(page, { withoutDisposition: true });
  await page.goto(`/courses/${COURSE_ID}/lecturer/templates`);

  const save = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download ZIP' }).first().click();

  expect((await save).suggestedFilename()).toBe('prog.2026-template.zip');
});

test('surfaces the rate limit instead of saving an error body as a zip', async ({ page }) => {
  await setup(page, {
    failWith: { status: 429, body: { message: 'Too many template downloads. Please wait before trying again.' } },
  });
  await page.goto(`/courses/${COURSE_ID}/lecturer/templates`);

  await page.getByRole('button', { name: 'Download ZIP' }).first().click();

  await expect(page.getByText('Too many template downloads. Please wait before trying again.')).toBeVisible();
});

test('surfaces a course with no template bound', async ({ page }) => {
  await setup(page, {
    failWith: { status: 400, body: { message: 'This course has no downloadable template' } },
  });
  await page.goto(`/courses/${COURSE_ID}/lecturer/templates`);

  await page.getByRole('button', { name: 'Download ZIP' }).first().click();

  await expect(page.getByText('This course has no downloadable template')).toBeVisible();
});

test('a student on the course cannot reach the page', async ({ page }) => {
  await setup(page, { courseRoles: ['_student'] });
  await page.goto(`/courses/${COURSE_ID}/lecturer/templates`);

  await expect(page.getByText(/lecturer access \(or higher\)/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Download ZIP' })).toHaveCount(0);
});
