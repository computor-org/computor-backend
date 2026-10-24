import { test, expect } from '@playwright/test';

for (const [locale, selected, message] of [
  ['en-US', 'en', 'Completing sign-in…'],
  ['de-DE', 'en', 'Completing sign-in…'],
  ['en-US', 'de', 'Anmeldung wird abgeschlossen …'],
] as const) {
  test(`completion first paint uses ${selected} with ${locale} browser`, async ({ browser }) => {
    // Holding all JavaScript means this is the real server-rendered first
    // screen, before hydration or the asynchronous /user callback can finish.
    const context = await browser.newContext({ locale, javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto(`/auth/success?ui_locale=${selected}`);
    await expect(page.getByText(message, { exact: true })).toBeVisible();
    await context.close();
  });
}

for (const [locale, selected, message] of [
  ['de-DE', 'en', 'Completing sign-in…'],
  ['en-US', 'de', 'Anmeldung wird abgeschlossen …'],
] as const) {
  test(`delayed callback keeps ${selected} after hydration with ${locale} browser`, async ({ browser }) => {
    const context = await browser.newContext({ locale });
    const page = await context.newPage();
    let release!: () => void;
    const paused = new Promise<void>((resolve) => { release = resolve; });
    await page.route('http://localhost:8000/**', async (route) => {
      if (new URL(route.request().url()).pathname === '/user') await paused;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
    await page.goto(`/auth/success?ui_locale=${selected}`);
    await expect(page.getByText(message, { exact: true })).toBeVisible();
    await page.waitForTimeout(300);
    await expect(page.getByText(message, { exact: true })).toBeVisible();
    release();
    await context.close();
  });
}

test('a remembered explicit choice wins over an older callback locale after hydration', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('computor.language', 'en'));
  await page.goto('/auth/success?ui_locale=de&error=sign_in_expired');
  await expect(page.getByText('The sign-in page was open too long and has expired.')).toBeVisible();
});
