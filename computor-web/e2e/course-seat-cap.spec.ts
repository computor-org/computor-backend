import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * The self-registration seat cap on the course edit page. A blank field means
 * unlimited, so an invalid entry must never be sent as `null`: that would
 * silently open a capped course to every account. Invalid input shows an
 * error and saves nothing; only an explicitly emptied field clears the cap.
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
  title: 'Capped Course',
  path: 'org.family.capped',
  course_family_id: 'f-1',
  organization_id: 'o-1',
  public: true,
  max_self_registrations: 30,
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
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
      return json(route, { ...COURSE, ...body });
    }
    if (path === `/courses/${COURSE.id}`) return json(route, COURSE);
    if (path === `/courses/${COURSE.id}/git`) return json(route, { detail: 'none' }, 404);
    if (path.startsWith('/git-servers')) return json(route, []);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });

  await page.goto(`/courses/${COURSE.id}/edit`);
  const seats = page.getByLabel('Self-registration seats');
  await expect(seats).toHaveValue('30', { timeout: 15_000 });
  return { seats, patches, save: page.getByRole('button', { name: 'Save' }).first() };
}

for (const invalid of ['-1', '1.5', 'ten']) {
  test(`an invalid seat cap "${invalid}" is refused and nothing is saved`, async ({ page }) => {
    const { seats, patches, save } = await setup(page);

    await seats.fill(invalid);
    await save.click();

    await expect(page.getByText('Enter a whole number of 0 or more')).toBeVisible();
    await page.waitForTimeout(300);
    expect(patches).toHaveLength(0);
    await expect(seats).toHaveValue(invalid);
  });
}

test('an explicitly emptied seat cap is saved as unlimited', async ({ page }) => {
  const { seats, patches, save } = await setup(page);

  await seats.fill('');
  await save.click();

  await expect.poll(() => patches.length).toBe(1);
  expect(patches[0].max_self_registrations).toBeNull();
});

test('a valid seat cap is saved as a number', async ({ page }) => {
  const { seats, patches, save } = await setup(page);

  await seats.fill('12');
  await save.click();

  await expect.poll(() => patches.length).toBe(1);
  expect(patches[0].max_self_registrations).toBe(12);
});
