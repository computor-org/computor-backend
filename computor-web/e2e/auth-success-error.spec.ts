import { test, expect } from '@playwright/test';

/**
 * Keycloak ends an expired sign-in with a callback that carries no code; the
 * backend then sends the browser back here with error=sign_in_expired
 * (computor-org/issues#477). The page must explain it, not show a blank
 * spinner, and offer a way to sign in again.
 */
test.describe('/auth/success after an interrupted sign-in', () => {
  test('explains an expired sign-in page in English', async ({ page }) => {
    await page.goto('/auth/success?error=sign_in_expired&error_description=x');
    await expect(page.getByText('The sign-in page was open too long and has expired.')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Try again' })).toHaveAttribute('href', '/login');
  });

  test('explains an incomplete sign-in', async ({ page }) => {
    await page.goto('/auth/success?error=sign_in_failed');
    await expect(page.getByText('The sign-in was not completed.')).toBeVisible();
  });

  test.describe('German interface', () => {
    test.use({ locale: 'de-DE' });
    test('shows the expiry in German', async ({ page }) => {
      await page.goto('/auth/success?error=sign_in_expired');
      await expect(page.getByText('Die Anmeldeseite war zu lange geöffnet')).toBeVisible();
      await expect(page.getByRole('link', { name: 'Erneut versuchen' })).toBeVisible();
    });
  });
});
