import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * The "enrol Lena as AI tutor" switch (issues#618): on by default when a
 * course is created, read from and saved through /courses/{id}/tutor-agent on
 * the edit page, and absent on a deployment without a tutor agent.
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
};

const ENROL = 'Enrol Lena as AI tutor in this course';
const AUTO_ROUTE = 'Send student messages without an @mention to Lena';

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

type Calls = { method: string; path: string; body: unknown }[];

async function signIn(page: Page, { agentName, agent }: { agentName: string | null; agent: unknown }) {
  const calls: Calls = [];
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
    const method = request.method();
    if (method !== 'GET') calls.push({ method, path, body: request.postDataJSON() });
    if (path === '/instance-info') return json(route, { tutor_agent_name: agentName });
    if (path.endsWith('/tutor-agent') && method === 'PUT') {
      const body = request.postDataJSON() as { enrolled: boolean };
      return json(route, { available: true, enrolled: body.enrolled, name: 'Lena', course_role_id: body.enrolled ? '_tutor' : null });
    }
    if (path.endsWith('/tutor-agent')) return json(route, agent);
    if (path === '/courses' && method === 'POST') {
      return json(route, { ...COURSE, id: 'c-new', ...(request.postDataJSON() as object) });
    }
    if (path === `/courses/${COURSE.id}` && method === 'PATCH') {
      return json(route, { ...COURSE, ...(request.postDataJSON() as object) });
    }
    if (path === `/courses/${COURSE.id}` || path === '/courses/c-new') return json(route, COURSE);
    if (path.endsWith('/git')) return json(route, { detail: 'none' }, 404);
    if (path === '/course-families') return json(route, [{ id: 'f-1', title: 'Python', organization_id: 'o-1' }]);
    if (path.startsWith('/git-servers')) return json(route, []);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
  return calls;
}

test('a new course enrols Lena unless the box is cleared', async ({ page }) => {
  const calls = await signIn(page, { agentName: 'Lena', agent: {} });
  await page.goto('/courses/create');

  const enrol = page.getByRole('checkbox', { name: new RegExp(ENROL) });
  await expect(enrol).toBeChecked({ timeout: 15_000 });

  // Routing to a tutor who is not in the course reaches nobody.
  await enrol.uncheck();
  await expect(page.getByRole('checkbox', { name: new RegExp(AUTO_ROUTE) })).toBeDisabled();
  await enrol.check();

  await page.getByPlaceholder('algorithms-2026w').fill('python-2027');
  await page.getByRole('button', { name: 'Create', exact: true }).click();

  await expect.poll(() => calls.find((c) => c.method === 'PUT')).toBeTruthy();
  const created = calls.findIndex((c) => c.method === 'POST' && c.path === '/courses');
  const enrolled = calls.findIndex((c) => c.method === 'PUT' && c.path === '/courses/c-new/tutor-agent');
  expect(created).toBeGreaterThanOrEqual(0);
  expect(enrolled).toBeGreaterThan(created);
  expect(calls[enrolled].body).toEqual({ enrolled: true });
});

test('a deployment without a tutor agent offers no switch', async ({ page }) => {
  await signIn(page, { agentName: null, agent: {} });
  await page.goto('/courses/create');

  await expect(page.getByRole('checkbox', { name: new RegExp(AUTO_ROUTE) })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('checkbox', { name: new RegExp(ENROL) })).toHaveCount(0);
});

test('the edit page shows the membership and saves a change', async ({ page }) => {
  const calls = await signIn(page, {
    agentName: 'Lena',
    agent: { available: true, enrolled: false, name: 'Lena', course_role_id: null },
  });
  await page.goto(`/courses/${COURSE.id}/edit`);

  const enrol = page.getByRole('checkbox', { name: new RegExp(ENROL) });
  await expect(enrol).not.toBeChecked({ timeout: 15_000 });
  await enrol.check();
  await page.getByRole('button', { name: 'Save' }).first().click();

  await expect.poll(() => calls.find((c) => c.method === 'PUT')).toEqual({
    method: 'PUT', path: `/courses/${COURSE.id}/tutor-agent`, body: { enrolled: true },
  });
});

test('saving without touching the switch leaves the membership alone', async ({ page }) => {
  const calls = await signIn(page, {
    agentName: 'Lena',
    agent: { available: true, enrolled: true, name: 'Lena', course_role_id: '_tutor' },
  });
  await page.goto(`/courses/${COURSE.id}/edit`);

  await expect(page.getByRole('checkbox', { name: new RegExp(ENROL) })).toBeChecked({ timeout: 15_000 });
  await page.getByRole('button', { name: 'Save' }).first().click();

  await expect.poll(() => calls.some((c) => c.method === 'PATCH')).toBe(true);
  expect(calls.some((c) => c.method === 'PUT')).toBe(false);
});
