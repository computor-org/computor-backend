import { test, expect } from '@playwright/test';

/**
 * An unknown URL is a 404 for everyone. Anonymous visitors used to be sent to
 * sign-in for it, as if a page existed behind the login; a real protected
 * route must keep that redirect.
 */

test('an unknown URL shows a 404 to an anonymous visitor instead of sign-in', async ({ page }) => {
  const response = await page.goto('/does-not-exist');
  expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading', { name: '404 - Not Found' })).toBeVisible();
  await expect(page.getByText('This page does not exist.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Go to the home page' })).toHaveAttribute('href', '/');
  // Give a redirect the time it would need, then make sure none happened.
  await page.waitForTimeout(500);
  expect(new URL(page.url()).pathname).toBe('/does-not-exist');
});

test('a protected route still sends an anonymous visitor to sign-in', async ({ page }) => {
  // /login hands straight on to the backend's SSO, which is not running here;
  // the request for /login with the page to return to is what matters.
  await page.route('http://localhost:8000/**', (route) => route.abort());
  const signIn = page.waitForRequest((request) => request.url().includes('/login?next=%2Fdashboard'));
  await page.goto('/dashboard');
  await signIn;
});
