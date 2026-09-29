import { test, expect, type Page, type Route } from '@playwright/test';
import { safeInternalPath } from '../src/utils/safeRedirect';

/**
 * Post-login redirect targets must stay on this origin (PR #244 review).
 *
 * `/login?next=` and the `auth_redirect` value consumed by /auth/success are
 * attacker-influenced. Browsers strip tab/CR/LF and read "\" as "/", so
 * "/\t/evil.example" used to pass a prefix check and navigate off-site. Both
 * flows are driven in a real browser; any request to evil.example is recorded
 * and aborted, and the test fails if one happens.
 */

const API_ORIGIN = 'http://localhost:8000';
const ORIGIN = 'http://localhost:3100';

const USER = {
  id: 'u-1',
  username: 'student',
  email: 'student@example.org',
  given_name: 'Stu',
  family_name: 'Dent',
  user_roles: [],
};

const HOSTILE = [
  '/\t/evil.example',
  '/\n/evil.example',
  '/\r/evil.example',
  '/%09/evil.example',
  '/%0A/evil.example',
  '/%2509/evil.example',
  '/\\evil.example',
  '/%5Cevil.example',
  '//evil.example',
  '/.//evil.example',
  'https://evil.example/',
  'javascript:alert(1)',
];

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function mockBackend(page: Page, offsite: string[]) {
  // Match on the host: the /login?next=… URL itself mentions evil.example.
  await page.route((url) => url.hostname.endsWith('evil.example'), (route) => {
    offsite.push(route.request().url());
    return route.abort();
  });
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path === '/consent/status') return json(route, { required_version: null });
    return json(route, []);
  });
}

async function signedIn(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id,
      username: user.username,
      email: user.email,
      givenName: user.given_name,
      familyName: user.family_name,
      role: 'user',
      systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);
}

test('safeInternalPath rejects every off-site form and canonicalises the rest', () => {
  for (const raw of HOSTILE) {
    expect(safeInternalPath(raw, ORIGIN), JSON.stringify(raw)).toBeNull();
    // As delivered through a query string, i.e. after one round of decoding.
    let once: string;
    try { once = decodeURIComponent(raw); } catch { continue; }
    expect(safeInternalPath(once, ORIGIN), JSON.stringify(once)).toBeNull();
  }
  expect(safeInternalPath('/courses/catalog', ORIGIN)).toBe('/courses/catalog');
  expect(safeInternalPath('/courses/../courses/catalog?x=1#h', ORIGIN)).toBe('/courses/catalog?x=1#h');
  expect(safeInternalPath(null, ORIGIN)).toBeNull();
});

test.describe('signed-in /login?next=', () => {
  for (const next of ['/%09/evil.example', '/%0A/evil.example', '/%5Cevil.example']) {
    test(`stays on site for next=${next}`, async ({ page }) => {
      const offsite: string[] = [];
      await mockBackend(page, offsite);
      await signedIn(page);
      await page.goto(`/login?next=${next}`);
      await expect(page).toHaveURL(`${ORIGIN}/dashboard`);
      expect(offsite).toEqual([]);
    });
  }

  test('follows a genuine same-origin next', async ({ page }) => {
    const offsite: string[] = [];
    await mockBackend(page, offsite);
    await signedIn(page);
    await page.goto('/login?next=%2Fcourses%2Fcatalog');
    await expect(page).toHaveURL(`${ORIGIN}/courses/catalog`);
    expect(offsite).toEqual([]);
  });
});

test.describe('/auth/success with a stored auth_redirect', () => {
  async function callbackWith(page: Page, stored: string, offsite: string[]) {
    await mockBackend(page, offsite);
    // Only seed the value for the callback page itself, not for where it goes.
    await page.addInitScript((value) => {
      if (window.location.pathname === '/auth/success') {
        sessionStorage.setItem('auth_redirect', value);
      }
    }, stored);
    await page.goto('/auth/success');
  }

  for (const stored of ['/\t/evil.example', '/\n/evil.example', '/\\evil.example']) {
    test(`stays on site for ${JSON.stringify(stored)}`, async ({ page }) => {
      const offsite: string[] = [];
      await callbackWith(page, stored, offsite);
      await expect(page).toHaveURL(`${ORIGIN}/dashboard`);
      expect(offsite).toEqual([]);
    });
  }

  test('follows a genuine stored path', async ({ page }) => {
    const offsite: string[] = [];
    await callbackWith(page, '/courses/catalog', offsite);
    await expect(page).toHaveURL(`${ORIGIN}/courses/catalog`);
    expect(offsite).toEqual([]);
  });
});
