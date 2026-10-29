import { test, expect, type Page, type Route } from '@playwright/test';

// Two things the pages get wrong today (computor-org/issues#533):
// a <select> has no colours of its own, so on a dark page the language picker
// is light text on a transparent hole, and the legal pages declare German as
// the document language even when their text is English.

const API_ORIGIN = 'http://localhost:8000';

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

/** Signed-in as a plain student, enough for the profile form to render. */
async function signIn(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [], language: null,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  });
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/courses' || path === '/courses/public') return json(route, []);
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: {} });
    if (path === '/user') return json(route, {
      id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner',
      user_roles: [], profile: { id: 'p', nickname: 'learner', bio: null, url: null, language_code: null },
    });
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
}

/** WCAG contrast ratio between two `rgb(r, g, b)` strings. */
function contrast(foreground: string, background: string): number {
  const channel = (value: number) => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const luminance = (rgb: string) => {
    const [r, g, b] = rgb.match(/\d+/g)!.map(Number);
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  const [a, b] = [luminance(foreground), luminance(background)];
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

test('the language select is readable in dark mode', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('computor-theme', 'dark'));
  await page.emulateMedia({ colorScheme: 'dark' });
  await signIn(page);
  await page.goto('/profile');

  const select = page.getByLabel('Language');
  await expect(select).toBeVisible();

  const read = await select.evaluate((el) => {
    const s = getComputedStyle(el);
    return { backgroundColor: s.backgroundColor, color: s.color };
  });
  console.log(`select ${read.backgroundColor} on ${read.color}`);

  // A transparent field is the bug: the popup and the field paint whatever is
  // behind them, so the ratio has to be taken against an opaque background.
  expect(read.backgroundColor, 'the select paints its own background').not.toBe('rgba(0, 0, 0, 0)');
  expect(read.backgroundColor, 'dark surface').toBe('rgb(22, 27, 38)');
  expect(read.color, 'dark ink').toBe('rgb(232, 235, 242)');
  expect(contrast(read.color, read.backgroundColor), 'text-to-field contrast').toBeGreaterThan(4.5);
});

test('the English privacy notice declares English', async ({ page }) => {
  await page.goto('/privacy/en');
  await expect(page.getByRole('heading', { level: 1, name: /privacy/i })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('the English terms declare English', async ({ page }) => {
  await page.goto('/terms/en');
  await expect(page.getByRole('heading', { level: 1, name: /terms/i })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('the German privacy notice still declares German', async ({ page }) => {
  await page.goto('/privacy');
  await expect(page.getByRole('heading', { level: 1, name: /datenschutz/i })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'de');
});

// Impressum, accessibility and report hold both languages on one page; the
// reading language decides which section comes first and what the document
// calls itself.
for (const [locale, expected] of [
  ['en-US', { lang: 'en', first: 'English', title: 'Accessibility · Computor' }],
  ['de-AT', { lang: 'de', first: 'Deutsch', title: 'Barrierefreiheit · Computor' }],
] as const) {
  test.describe(`accessibility page in ${locale}`, () => {
    test.use({ locale });

    test('leads with its section and titles itself in one language', async ({ page }) => {
      await page.goto('/accessibility');
      await expect(page.getByRole('heading', { level: 2, name: expected.first })).toBeVisible();
      await expect(page.locator('html')).toHaveAttribute('lang', expected.lang);
      await expect(page).toHaveTitle(expected.title);
      const sections = page.locator('main article section');
      await expect(sections).toHaveCount(2);
      await expect(sections.first()).toHaveAttribute('lang', expected.lang);
      await expect(sections.first()).toContainText(expected.first);
    });
  });
}

for (const [locale, expected] of [
  ['en-US', { title: 'Imprint · Computor', first: 'English' }],
  ['de-AT', { title: 'Impressum · Computor', first: 'Deutsch' }],
] as const) {
  test.describe(`imprint in ${locale}`, () => {
    test.use({ locale });

    test('leads with its section and titles itself in one language', async ({ page }) => {
      await page.goto('/impressum');
      await expect(page).toHaveTitle(expected.title);
      await expect(page.locator('main article section').first()).toContainText(expected.first);
    });
  });
}

test('the report page follows the reading language', async ({ page }) => {
  await page.goto('/report');
  await expect(page).toHaveTitle('Report content · Computor');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.locator('main article section').first()).toContainText('Report illegal content');
});
