import { test, expect } from '@playwright/test';
import { PERSONAS, injectAuth, json, mockApi } from './fixtures';

/** /admin/git-servers — the hierarchy-manager gate, server badges, empty state. */

test.describe('git servers', () => {
  test('an admin sees a managed server with its badges and the register link', async ({ page }) => {
    await injectAuth(page, PERSONAS.admin);
    await mockApi(page, {
      persona: PERSONAS.admin,
      handlers: (route, url) => {
        if (url.pathname === '/git-servers' && route.request().method() === 'GET') {
          void json(route, [{
            id: 'gs-1', type: 'gitlab', base_url: 'https://git.example.org',
            name: 'Forgejo', managed: true, has_token: true,
          }]);
          return true;
        }
        return false;
      },
    });
    await page.goto('/admin/git-servers');

    await expect(page.getByRole('heading', { name: 'Git Servers' })).toBeVisible();
    await expect(page.getByText('Forgejo')).toBeVisible();
    await expect(page.getByText('managed', { exact: true })).toBeVisible();
    await expect(page.getByText('token set', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Register Server' })).toBeVisible();
  });

  test('a non-manager is shown the forbidden state', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await mockApi(page, { persona: PERSONAS.student });
    await page.goto('/admin/git-servers');

    await expect(page.getByText(
      'Admin or organization-manager access is required to manage git servers.',
    )).toBeVisible();
  });

  test('an empty registry shows the empty state', async ({ page }) => {
    await injectAuth(page, PERSONAS.admin);
    await mockApi(page, {
      persona: PERSONAS.admin,
      handlers: (route, url) => {
        if (url.pathname === '/git-servers' && route.request().method() === 'GET') {
          void json(route, []);
          return true;
        }
        return false;
      },
    });
    await page.goto('/admin/git-servers');

    await expect(page.getByText(/No git servers registered yet/)).toBeVisible();
  });
});
