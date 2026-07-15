import { test, expect } from '@playwright/test';
import { PERSONAS, type Persona, injectAuth, json, mockApi } from './fixtures';

/**
 * /dashboard — the Quick Actions are gated by `usePermissions` flags, so each
 * persona sees a different set of shortcuts. Presence checks are scoped to the
 * dashboard `<main>` (the same links also appear in the role-gated sidebar).
 */

async function dashboardMock(
  page: import('@playwright/test').Page, persona: Persona, views?: string[],
): Promise<void> {
  await mockApi(page, {
    persona,
    handlers: (route, url) => {
      if (views && url.pathname === '/user/views') { void json(route, views); return true; }
      if (url.pathname === '/courses' && route.request().method() === 'GET') {
        void json(route, []); return true;
      }
      return false;
    },
  });
}

test.describe('dashboard quick actions', () => {
  test('an admin sees the management and system shortcuts', async ({ page }) => {
    await injectAuth(page, PERSONAS.admin);
    await dashboardMock(page, PERSONAS.admin);
    await page.goto('/dashboard');
    const main = page.getByRole('main');

    await expect(page.getByRole('heading', { name: /Welcome back, Ada/ })).toBeVisible();
    await expect(main.getByRole('link', { name: 'System' })).toBeVisible();
    await expect(main.getByRole('link', { name: 'User Management' })).toBeVisible();
    await expect(main.getByRole('link', { name: 'Organizations' })).toBeVisible();
    await expect(main.getByRole('link', { name: 'Course Families' })).toBeVisible();
  });

  test('a student sees only the basic shortcuts', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await dashboardMock(page, PERSONAS.student);
    await page.goto('/dashboard');
    const main = page.getByRole('main');

    await expect(main.getByRole('link', { name: 'Browse Courses' })).toBeVisible();
    await expect(main.getByRole('link', { name: 'Browse Examples' })).toBeVisible();
    await expect(main.getByRole('link', { name: 'Settings' })).toBeVisible();
    // System / User Management / Organizations appear nowhere (neither main nor sidebar).
    await expect(page.getByRole('link', { name: 'System' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'User Management' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Organizations' })).toHaveCount(0);
  });

  test('a lecturer view unlocks the management shortcuts but not system', async ({ page }) => {
    await injectAuth(page, PERSONAS.lecturer);
    await dashboardMock(page, PERSONAS.lecturer, ['lecturer']);
    await page.goto('/dashboard');
    const main = page.getByRole('main');

    await expect(main.getByRole('link', { name: 'Organizations' })).toBeVisible();
    await expect(main.getByRole('link', { name: 'Course Families' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'System' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'User Management' })).toHaveCount(0);
  });
});
