import { test, expect, type Page, type Route } from '@playwright/test';

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

async function setup(page: Page, initial: number | null = 20) {
  const patches: Record<string, unknown>[] = [];
  let stored = { ...COURSE, position: initial };
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
      stored = { ...stored, ...body };
      return json(route, stored);
    }
    if (path === `/courses/${COURSE.id}`) return json(route, stored);
    if (path === `/courses/${COURSE.id}/git`) return json(route, { detail: 'none' }, 404);
    if (path.startsWith('/git-servers')) return json(route, []);
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, SELF);
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });

  await page.goto(`/courses/${COURSE.id}/edit`);
  const order = page.getByLabel(/^(Course order|Kursreihenfolge)$/);
  await expect(order).toHaveValue(initial === null ? '' : String(initial), { timeout: 15_000 });
  return { order, patches, save: page.getByRole('button', { name: 'Save', exact: true }).first() };
}

for (const locale of ['en-US', 'de-AT']) {
  test.describe(locale, () => {
    test.use({ locale });

    test('course order saves a finite fraction, survives reload, and clears to null', async ({ page }) => {
      const { order, patches, save } = await setup(page);
      await order.fill('-2.5');
      await save.click();
      await expect.poll(() => patches.length).toBe(1);
      expect(patches[0].position).toBe(-2.5);
      await page.reload();
      await expect(order).toHaveValue('-2.5');
      await order.fill('');
      await save.click();
      await expect.poll(() => patches.length).toBe(2);
      expect(patches[1].position).toBeNull();
      await page.reload();
      await expect(order).toHaveValue('');
    });

    test('nonfinite order is refused without a request', async ({ page }) => {
      const { order, patches, save } = await setup(page, null);
      await order.fill('1e999');
      await save.click();
      await expect(page.getByRole('alert').filter({ hasText: locale === 'de-AT' ? 'Gib eine endliche Zahl ein' : 'Enter a finite number' })).toContainText(locale === 'de-AT'
        ? 'Gib eine endliche Zahl ein' : 'Enter a finite number');
      await expect(order).toHaveAttribute('aria-invalid', 'true');
      expect(patches).toHaveLength(0);
    });
  });
}
