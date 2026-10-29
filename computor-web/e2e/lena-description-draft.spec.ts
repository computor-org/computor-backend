import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * "Draft with Lena" on the unit edit page (computor-org/issues#559).
 *
 * A draft only reaches the description field when the lecturer picks it, and
 * only reaches the server when they press Save. Backend mocked at the network
 * layer.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = 'course-1';
const JOB_ID = '6f1c1a52-6a0e-4b8f-9c3e-2f0d7a1b5c44';

const SELF = {
  id: 'u-admin',
  username: 'admin1',
  email: 'admin1@example.org',
  given_name: 'Ada',
  family_name: 'Root',
  user_roles: [{ role_id: '_admin' }],
};

const UNIT = {
  id: 'unit-1',
  course_id: COURSE_ID,
  title: 'Week 1',
  description: 'Old text',
  path: 'week1',
  position: 1,
  course_content_type_id: 'type-week',
  course_content_kind_id: 'unit',
  is_submittable: false,
  visible: null,
};

const ASSIGNMENT = { ...UNIT, id: 'task-1', title: 'Loops', path: 'week1.loops', is_submittable: true };

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, { enabled = true } = {}) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
    sessionStorage.setItem('auth_provider', 'sso');
  }, {
    id: SELF.id, username: SELF.username, email: SELF.email,
    givenName: SELF.given_name, familyName: SELF.family_name,
    role: 'admin', systemRoles: ['_admin'],
  });

  const calls = { requests: [] as unknown[], patches: [] as unknown[] };
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    if (path === '/course-contents/description-drafts/availability') return json(route, { enabled });
    if (path === `/course-contents/${UNIT.id}/description-draft` && method === 'POST') {
      calls.requests.push(request.postDataJSON());
      return json(route, { id: JOB_ID, state: 'queued' }, 202);
    }
    if (path === `/course-contents/description-drafts/${JOB_ID}`) {
      return json(route, {
        id: JOB_ID,
        state: 'done',
        drafts: [
          { language: 'de', description: 'Woche 1: **Schleifen**' },
          { language: 'en', description: 'Week 1 covers **loops**.' },
        ],
      });
    }
    if (path === `/course-contents/${UNIT.id}`) {
      if (method === 'PATCH') {
        calls.patches.push(request.postDataJSON());
        return json(route, UNIT);
      }
      return json(route, UNIT);
    }
    if (path === `/course-contents/${ASSIGNMENT.id}`) return json(route, ASSIGNMENT);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
  return calls;
}

test('a Lena draft fills the description only when picked, and is stored only on Save', async ({ page }) => {
  const calls = await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/assignments/${UNIT.id}/edit`);

  const description = page.getByLabel('Description');
  await expect(description).toHaveValue('Old text', { timeout: 10_000 });

  await page.getByLabel('Extra instruction for Lena (optional)').fill('Keep it short');
  await page.getByRole('button', { name: 'Draft with Lena' }).click();

  const drafts = page.getByTestId('lena-description-draft');
  await expect(drafts.getByText('English')).toBeVisible({ timeout: 10_000 });
  await expect(drafts.getByText('German')).toBeVisible();
  expect(calls.requests).toEqual([{ instruction: 'Keep it short' }]);
  // Showing the drafts changes nothing yet.
  await expect(description).toHaveValue('Old text');

  await drafts.getByRole('button', { name: 'Replace the description with this draft' }).nth(1).click();
  await expect(description).toHaveValue('Week 1 covers **loops**.');
  await expect(page.getByText('Preview')).toBeVisible();
  expect(calls.patches).toEqual([]);

  await page.getByRole('button', { name: 'Save' }).click();
  await expect.poll(() => calls.patches.length).toBe(1);
  expect(calls.patches[0]).toMatchObject({ description: 'Week 1 covers **loops**.' });
});

test('no Lena draft for an assignment', async ({ page }) => {
  await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/assignments/${ASSIGNMENT.id}/edit`);
  await expect(page.getByLabel('Title')).toHaveValue('Loops', { timeout: 10_000 });
  await expect(page.getByRole('button', { name: 'Draft with Lena' })).toHaveCount(0);
});

test('no Lena draft when no Lena worker is running', async ({ page }) => {
  await setup(page, { enabled: false });
  await page.goto(`/courses/${COURSE_ID}/lecturer/assignments/${UNIT.id}/edit`);
  await expect(page.getByLabel('Title')).toHaveValue('Week 1', { timeout: 10_000 });
  await expect(page.getByRole('button', { name: 'Draft with Lena' })).toHaveCount(0);
});
