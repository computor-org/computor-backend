import { test, expect, type Page, type Route } from '@playwright/test';

// The signed-in interface speaks one language: the profile language when the
// user chose one, else the browser language (German for de-*, English otherwise).

const API_ORIGIN = 'http://localhost:8000';
const COURSES = [{
  id: 'python', title: 'Python für Einsteiger', organization_title: 'TU Graz',
  language_code: 'de', description: 'Kurs aus dem Kurs-Repository.',
}];

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
}

/** Mutable profile language, so a save on /profile changes what GET /user answers. */
type ProfileLanguage = { value: string | null };

async function signIn(page: Page, profileLanguage: string | null | ProfileLanguage) {
  const language = profileLanguage === null || typeof profileLanguage === 'string'
    ? { value: profileLanguage }
    : profileLanguage;
  await page.addInitScript((language) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [], language,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, language.value);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/courses/public' || path === '/courses') return json(route, COURSES);
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { python: ['_student'] } });
    if (/^\/profiles\/[^/]+$/.test(path) && route.request().method() === 'PATCH') {
      language.value = route.request().postDataJSON()?.language_code ?? null;
      return json(route, { id: 'p', language_code: language.value });
    }
    if (path === '/user') return json(route, {
      id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner',
      user_roles: [], profile: language.value ? { id: 'p', language_code: language.value } : null,
      // As the backend resolves it: the profile language, else Accept-Language.
      effective_language: language.value
        ?? ((route.request().headers()['accept-language'] ?? '').toLowerCase().startsWith('de') ? 'de' : 'en'),
    });
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
}

const sidebar = (page: Page) => page.getByRole('complementary');

test.describe('German browser', () => {
  test.use({ locale: 'de-AT' });

  test('my courses and the navigation are German', async ({ page }) => {
    await signIn(page, null);
    await page.goto('/courses');
    await expect(page.getByRole('heading', { name: COURSES[0].title })).toBeVisible();
    await expect(sidebar(page).getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
    await expect(sidebar(page).getByRole('link', { name: 'Katalog' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Benutzermenü' })).toBeVisible();
    await expect(page.getByText('My courses', { exact: true })).toHaveCount(0);
    await expect(page.locator('html')).toHaveAttribute('lang', 'de');
  });

  test('the catalog is German', async ({ page }) => {
    await signIn(page, null);
    await page.goto('/courses/catalog');
    await expect(page.getByRole('heading', { name: COURSES[0].title })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Join course' })).toHaveCount(0);
    await expect(page.getByText('Catalog', { exact: true })).toHaveCount(0);
  });

  test('an English profile language wins over the German browser', async ({ page }) => {
    await signIn(page, 'en');
    await page.goto('/courses');
    await expect(sidebar(page).getByRole('link', { name: 'My courses' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'User menu' })).toBeVisible();
  });
});

test('a German profile language wins over an English browser', async ({ page }) => {
  await signIn(page, 'de');
  await page.goto('/courses');
  await expect(sidebar(page).getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
  await page.getByRole('button', { name: 'Benutzermenü' }).click();
  await expect(page.getByRole('button', { name: 'Abmelden' })).toBeVisible();
});

for (const [locale, profileLanguage, message, retry] of [
  ['de-DE', 'en', 'Die Anmeldeseite war zu lange geöffnet', 'Erneut versuchen'],
  ['en-US', 'de', 'The sign-in page was open too long and has expired.', 'Try again'],
] as const) {
  test.describe(`the profile language stays inside the signed-in app (${locale}/${profileLanguage})`, () => {
    test.use({ locale });
    // Asserted the other way round before: the profile language was copied into
    // the signed-out preference, so a new tab kept it and sent it to Keycloak.
    // That copy is what made "Automatic" stick to one language (computor-org/issues#534).
    test('leaves the signed-out preference to the browser and sends no explicit choice', async ({ page, context }) => {
      await signIn(page, profileLanguage);
      await page.goto('/courses');
      expect(await page.evaluate(() => localStorage.getItem('computor.language'))).toBeNull();
      const freshTab = await context.newPage();
      await freshTab.goto('/auth/success?error=sign_in_expired');
      await expect(freshTab.getByText(message)).toBeVisible();
      const request = freshTab.waitForRequest((request) => request.url().includes('/auth/keycloak/login?'));
      await freshTab.getByRole('link', { name: retry }).click();
      const login = new URL((await request).url());
      const browserLanguage = locale.startsWith('de') ? 'de' : 'en';
      expect(login.searchParams.get('ui_locales')).toBe(browserLanguage);
      expect(login.searchParams.has('explicit_language')).toBe(false);
      expect(new URL(login.searchParams.get('redirect_uri')!).searchParams.get('ui_locale')).toBe(browserLanguage);
      await freshTab.close();
    });
  });
}

test.describe('Automatic follows the browser', () => {
  test.use({ locale: 'de-DE' });

  test('switching the profile from English to Automatic makes the app German again', async ({ page }) => {
    const profileLanguage = { value: 'en' };
    await signIn(page, profileLanguage);
    await page.goto('/courses');
    await expect(sidebar(page).getByRole('link', { name: 'My courses' })).toBeVisible();

    await page.goto('/profile');
    await page.getByLabel('Language', { exact: true }).selectOption('');
    await page.getByRole('button', { name: 'Save changes' }).click();
    await expect(page.getByText('Gespeichert')).toBeVisible();

    await page.goto('/courses');
    await expect(sidebar(page).getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
    await expect(sidebar(page).getByRole('link', { name: 'My courses' })).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.getItem('computor.language'))).toBeNull();
  });

  test('a choice stored on a signed-out page does not pin the signed-in app', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('computor.language', 'en'));
    await signIn(page, null);
    await page.goto('/courses');
    await expect(sidebar(page).getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
    await expect(sidebar(page).getByRole('link', { name: 'My courses' })).toHaveCount(0);
  });

  test('a choice stored on a signed-out page is sent as the explicit one', async ({ page }) => {
    // The same key the public DE/EN switch writes, in a German browser: the
    // stored choice must win and be marked explicit.
    await page.addInitScript(() => localStorage.setItem('computor.language', 'en'));
    await page.goto('/auth/success?error=sign_in_expired');
    const request = page.waitForRequest((request) => request.url().includes('/auth/keycloak/login?'));
    await page.getByRole('link', { name: 'Try again' }).click();
    const login = new URL((await request).url());
    expect(login.searchParams.get('ui_locales')).toBe('en');
    expect(login.searchParams.get('explicit_language')).toBe('1');
  });
});
