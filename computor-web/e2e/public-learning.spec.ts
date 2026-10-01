import { test, expect } from '@playwright/test';

test('anonymous learners can read all three course routes without a backend or login', async ({ page }) => {
  const mutations: string[] = [];
  page.on('request', request => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) mutations.push(request.url());
  });
  await page.route('**/api/**', route => route.fulfill({ status: 503, body: '{}' }));
  await page.goto('/learn');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Data Science');
  await expect(page.getByRole('heading', { level: 2 })).toHaveCount(3);
  await expect(page.getByRole('link', { name: 'Alle Beispiele lesen / Read all examples' }))
    .toHaveAttribute('href', 'https://github.com/computor-org/data-science-python/tree/main/examples/python');
  await expect(page.getByRole('link', { name: 'GitHub Codespaces', exact: true }))
    .toHaveAttribute('href', /^https:\/\/codespaces.new\/computor-org\/data-science-python/);
  await expect(page.getByRole('link', { name: 'Desktop VS Code', exact: true }))
    .toHaveAttribute('href', /itemName=computor-org.computor$/);
  expect(new URL(page.url()).pathname).toBe('/learn');
  expect(mutations).toEqual([]);
});

test('landing offers public learning and independent runtimes even when catalog is unavailable', async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({ status: 503, body: '{}' }));
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Read courses' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'GitHub Codespaces', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Read courses' }).click();
  await expect(page).toHaveURL(/\/learn$/);
});
