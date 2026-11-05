import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * The per-course "submission grading" setting on the course edit page: the
 * stored mode is preselected and the chosen one is sent on Save.
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

const COURSE = {
  id: 'c-1',
  title: 'Python Basics',
  path: 'org.family.python',
  course_family_id: 'f-1',
  organization_id: 'o-1',
  public: true,
  submission_feedback: 'tests',
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, course: Record<string, unknown> = COURSE) {
  const patches: Record<string, unknown>[] = [];
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
    sessionStorage.setItem('auth_provider', 'sso');
  }, {
    id: SELF.id, username: SELF.username, email: SELF.email,
    givenName: SELF.given_name, familyName: SELF.family_name,
    role: 'admin', systemRoles: ['_admin'],
  });

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === `/courses/${COURSE.id}` && request.method() === 'PATCH') {
      const body = request.postDataJSON() as Record<string, unknown>;
      patches.push(body);
      return json(route, { ...course, ...body });
    }
    if (path === `/courses/${COURSE.id}`) return json(route, course);
    if (path === `/courses/${COURSE.id}/git`) return json(route, { detail: 'none' }, 404);
    if (path.startsWith('/git-servers')) return json(route, []);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });

  await page.goto(`/courses/${COURSE.id}/edit`);
  const group = page.getByRole('radiogroup', { name: 'Submission grading' });
  await expect(group).toBeVisible({ timeout: 15_000 });
  return { group, patches, save: page.getByRole('button', { name: 'Save' }).first() };
}

test('the stored mode is selected and a new choice is saved', async ({ page }) => {
  const { group, patches, save } = await setup(page);
  await expect(group.getByRole('radio', { name: /^Tests only/ })).toBeChecked();

  await group.getByRole('radio', { name: /^Tutors/ }).check();
  await save.click();

  await expect.poll(() => patches.length).toBe(1);
  expect(patches[0].submission_feedback).toBe('human');
});

test('a course without the field is shown with tutors grading', async ({ page }) => {
  const legacy: Record<string, unknown> = { ...COURSE };
  delete legacy.submission_feedback;
  const { group } = await setup(page, legacy);
  await expect(group.getByRole('radio', { name: /^Tutors/ })).toBeChecked();
});
