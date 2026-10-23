import { test, expect, type Page } from '@playwright/test';

/**
 * German-first public pages (computor-org/issues#453): the server render is
 * German, an explicit Deutsch/English choice holds across the public pages and
 * reloads, and the landing page has an account-creation entry that opens
 * Keycloak's registration form rather than the sign-in form.
 */

const API_ORIGIN = 'http://localhost:8000';

async function blockApi(page: Page, calls: string[]) {
  await page.route(`${API_ORIGIN}/**`, (route) => {
    calls.push(route.request().url());
    // Send the SSO navigation straight back to this site's /learn, so the
    // page's own sessionStorage can be read afterwards.
    if (new URL(route.request().url()).pathname.startsWith('/auth/')) {
      const site = new URL(new URL(route.request().url()).searchParams.get('redirect_uri')!).origin;
      return route.fulfill({ status: 302, headers: { location: `${site}/learn` } });
    }
    return route.fulfill({ status: 503, body: '{}' });
  });
}

test('the server render declares German', async ({ request }) => {
  const html = await (await request.get('/')).text();
  expect(html).toMatch(/<html lang="de"/);
});

test.describe('German browser', () => {
  test.use({ locale: 'de-DE' });

  test('an explicit English choice holds across reloads and public pages', async ({ page }) => {
    await blockApi(page, []);
    await page.goto('/');
    const languages = page.getByRole('group', { name: 'Sprache' });
    await expect(languages.getByRole('button', { name: 'DE' })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('heading', { name: /Programmieren lernen mit/ })).toBeVisible();

    await languages.getByRole('button', { name: 'EN' }).click();
    await expect(page.getByRole('heading', { name: /Learn programming with/ })).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');

    await page.reload();
    await expect(page.getByRole('heading', { name: /Learn programming with/ })).toBeVisible();

    await page.goto('/learn');
    await expect(page.getByRole('heading', { name: 'Courses', exact: true })).toBeVisible();
    await page.getByRole('group', { name: 'Language' }).getByRole('button', { name: 'DE' }).click();
    await expect(page.getByRole('heading', { name: 'Kurse', exact: true })).toBeVisible();
    await expect(page.locator('html')).toHaveAttribute('lang', 'de');
  });

  test('the footer follows the chosen language on the landing page and in /learn', async ({ page }) => {
    await blockApi(page, []);
    await page.goto('/');
    const footer = page.locator('footer');
    await expect(footer.getByText('Mit den Mitteln der Förderaktion netidee')).toBeVisible();

    await page.getByRole('group', { name: 'Sprache' }).getByRole('button', { name: 'EN' }).click();
    await expect(footer.getByText('Financially supported and made possible by the netidee funding programme.')).toBeVisible();
    await expect(footer).not.toContainText('Förderaktion');
    await expect(footer).not.toContainText('Impressum');

    await page.goto('/learn');
    await expect(footer.getByText('Financially supported and made possible by the netidee funding programme.')).toBeVisible();
    await expect(footer).not.toContainText('Förderaktion');
    await expect(footer).not.toContainText('Impressum');
  });

  test('"Konto erstellen" opens the registration form and returns to the catalog', async ({ page }) => {
    const calls: string[] = [];
    await blockApi(page, calls);
    await page.goto('/');
    await page.getByRole('link', { name: 'Konto erstellen' }).click();
    await expect.poll(() => calls.find((url) => url.includes('/auth/keycloak/login'))).toBeTruthy();
    const login = new URL(calls.find((url) => url.includes('/auth/keycloak/login'))!);
    expect(login.searchParams.get('action')).toBe('register');
    await expect(page).toHaveURL(/\/learn$/);
    expect(await page.evaluate(() => sessionStorage.getItem('auth_redirect'))).toBe('/courses/catalog');
  });
});

test('plain sign-in does not ask for the registration form', async ({ page }) => {
  const calls: string[] = [];
  await blockApi(page, calls);
  await page.goto('/login?action=delete');
  await expect.poll(() => calls.find((url) => url.includes('/auth/keycloak/login'))).toBeTruthy();
  const login = new URL(calls.find((url) => url.includes('/auth/keycloak/login'))!);
  expect(login.searchParams.has('action')).toBe(false);
});
