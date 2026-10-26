import { test, expect, type Page, type Route } from '@playwright/test';
import { flagReason, flagRuleDescription, flagTitle } from '../src/utils/flagText';
import { roleTitle } from '../src/utils/systemRoles';

// Phone-width layout (390 px): no page may scroll sideways, in particular not
// a header with actions or a public page, and the grading flags and built-in
// role names read German in a German interface.

const API_ORIGIN = 'http://localhost:8000';
const PHONE = { width: 390, height: 844 };

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

async function signInAsAdmin(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'u-admin', username: 'admin1', email: 'admin1@example.org',
      givenName: 'Ada', familyName: 'Root', role: 'admin', systemRoles: ['_admin'],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  });
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/user/views')) return json(route, ['lecturer']);
    if (path.startsWith('/messages') || path === '/users' || path.startsWith('/courses')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, {
      id: 'u-admin', email: 'admin1@example.org', given_name: 'Ada', family_name: 'Root',
      user_roles: [{ role_id: '_admin' }], profile: null,
    });
    return json(route, {});
  });
}

async function overflow(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

test.describe('phone width', () => {
  test.use({ viewport: PHONE, locale: 'de-AT' });

  test('a page header with actions stacks instead of overflowing', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/courses');
    const title = page.getByRole('heading', { level: 1, name: 'Kurse' });
    const catalog = page.getByRole('link', { name: 'Katalog durchsuchen' }).first();
    await expect(catalog).toBeVisible();
    // The title keeps a readable line instead of being squeezed to one word,
    // and the action buttons stay inside the phone's width.
    await expect.poll(async () => (await title.boundingBox())?.width ?? 0).toBeGreaterThan(150);
    await expect.poll(async () => {
      const b = await catalog.boundingBox();
      return b ? b.x + b.width : Infinity;
    }).toBeLessThanOrEqual(PHONE.width);
    expect(await overflow(page)).toBeLessThanOrEqual(0);
  });

  test('the accessibility statement does not scroll sideways', async ({ page }) => {
    test.skip(process.env.NEXT_PUBLIC_LEGAL_PROFILE !== 'computor-at', 'legal pages exist only with NEXT_PUBLIC_LEGAL_PROFILE=computor-at');
    // A large title stands in for the real font, where the long German title
    // word ("Barrierefreiheitserklärung") is wider than the phone's text column.
    await page.addInitScript(() => {
      document.addEventListener('DOMContentLoaded', () => {
        const style = document.createElement('style');
        style.textContent = 'h1 { font-size: 3.5rem !important; }';
        document.head.appendChild(style);
      });
    });
    await page.goto('/accessibility');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(await overflow(page)).toBeLessThanOrEqual(0);
  });
});

test('flags and built-in roles have German texts, with the backend text as fallback', () => {
  expect(flagTitle('low_progress', 'Low progress', 'de')).toBe('Geringer Fortschritt');
  expect(flagTitle('inactive', 'Inactive', 'de')).toBe('Inaktiv');
  expect(flagTitle('low_progress', 'Low progress', 'en')).toBe('Low progress');
  expect(flagTitle('brand_new', 'Brand new', 'de')).toBe('Brand new');
  expect(flagReason({ code: 'low_progress', reason: 'Submitted 0 of 4 assignments (0%).' }, 'de'))
    .toBe('0 von 4 Aufgaben abgegeben (0 %).');
  expect(flagReason({ code: 'inactive', reason: 'Last test run or submission 12 days ago.' }, 'de'))
    .toBe('Letzter Testlauf oder letzte Abgabe vor 12 Tagen.');
  expect(flagReason({ code: 'inactive', reason: 'Something reworded.' }, 'de')).toBe('Something reworded.');
  expect(flagRuleDescription({ code: 'inactive', description: 'No test run and no submission in the last 14 days.' }, 'de'))
    .toBe('Kein Testlauf und keine Abgabe in den letzten 14 Tagen.');
  expect(roleTitle('_user_manager', 'User Manager', 'de')).toBe('Benutzerverwaltung');
  expect(roleTitle('_workspace_user', 'Workspace User', 'en')).toBe('Workspace User');
  expect(roleTitle('custom_role', 'Custom', 'de')).toBe('Custom');
});
