import { test, expect } from '@playwright/test';
import { PERSONAS, buildUsers, injectAuth, json, mockApi } from './fixtures';

/** Admin → Users list: server-side search + paging against a mocked backend. */

const ALL_USERS = buildUsers(60); // more than one 50-row page

async function setup(page: import('@playwright/test').Page, admin = true) {
  const persona = admin ? PERSONAS.admin : PERSONAS.student;
  await injectAuth(page, persona);
  await mockApi(page, {
    persona,
    isAdmin: admin,
    handlers: (route, url) => {
      if (url.pathname !== '/users') return false;
      const search = url.searchParams.get('search')?.toLowerCase() ?? '';
      const skip = Number(url.searchParams.get('skip') ?? 0);
      const limit = Number(url.searchParams.get('limit') ?? 50);
      const filtered = search
        ? ALL_USERS.filter(
            (u) => u.email.includes(search) ||
              `${u.given_name} ${u.family_name}`.toLowerCase().includes(search),
          )
        : ALL_USERS;
      void json(route, filtered.slice(skip, skip + limit));
      return true;
    },
  });
}

test.describe('admin users list', () => {
  test('pages through users with server-side skip/limit', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/users');

    await expect(page.getByText('user1@example.org')).toBeVisible();
    await expect(page.getByText('user51@example.org')).not.toBeVisible();
    await expect(page.getByText('Page 1')).toBeVisible();

    const next = page.getByRole('button', { name: 'Next', exact: true });
    const prev = page.getByRole('button', { name: 'Previous', exact: true });
    await expect(prev).toBeDisabled();
    await expect(next).toBeEnabled();

    await next.click();
    await expect(page.getByText('user51@example.org')).toBeVisible();
    await expect(page.getByText('user1@example.org', { exact: true })).not.toBeVisible();
    await expect(page.getByText('Page 2')).toBeVisible();
    await expect(next).toBeDisabled();
    await expect(prev).toBeEnabled();
  });

  test('search box queries the backend and resets to page 1', async ({ page }) => {
    await setup(page);
    await page.goto('/admin/users');
    await expect(page.getByText('user1@example.org')).toBeVisible();

    await page.getByPlaceholder('Search by email or name…').fill('user42');
    await expect(page.getByText('user42@example.org')).toBeVisible();
    await expect(page.getByText('user1@example.org', { exact: true })).not.toBeVisible();
    await expect(page.getByText('Page 1')).toBeVisible();
  });

  test('non-managers are shown the forbidden state', async ({ page }) => {
    await setup(page, false);
    await page.goto('/admin/users');

    await expect(page.getByText('Access denied. Requires admin or _user_manager role.')).toBeVisible();
    await expect(page.getByText('user1@example.org')).not.toBeVisible();
  });
});
