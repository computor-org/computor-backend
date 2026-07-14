import { test, expect } from '@playwright/test';
import { PERSONAS, buildInvite, injectAuth, json, mockApi } from './fixtures';

/** Admin → Users → Invites: the invite-manager list, status badges, and the gate. */

test.describe('admin invites', () => {
  test('user-manager sees the invite list with an Active badge', async ({ page }) => {
    await injectAuth(page, PERSONAS.userManager);
    await mockApi(page, {
      persona: PERSONAS.userManager,
      handlers: (route, url) => {
        if (url.pathname === '/admin/invites' && route.request().method() === 'GET') {
          void json(route, [buildInvite({ note: 'onboard a manager' })]);
          return true;
        }
        return false;
      },
    });
    await page.goto('/admin/users/invites');

    await expect(page.getByRole('heading', { name: 'Invite Links' })).toBeVisible();
    await expect(page.getByText('onboard a manager')).toBeVisible();
    await expect(page.getByText('Active', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Copy Link' })).toBeVisible();
  });

  test('status badges reflect revoked / expired / used invites', async ({ page }) => {
    await injectAuth(page, PERSONAS.userManager);
    await mockApi(page, {
      persona: PERSONAS.userManager,
      handlers: (route, url) => {
        if (url.pathname === '/admin/invites' && route.request().method() === 'GET') {
          void json(route, [
            buildInvite({ id: 'r', token: 't-r', note: 'first', revoked_at: '2026-02-01T00:00:00Z' }),
            buildInvite({ id: 'e', token: 't-e', note: 'second', expires_at: '2000-01-01T00:00:00Z' }),
            buildInvite({ id: 'u', token: 't-u', note: 'third', max_uses: 1, use_count: 1 }),
          ]);
          return true;
        }
        return false;
      },
    });
    await page.goto('/admin/users/invites');

    await expect(page.getByText('Revoked', { exact: true })).toBeVisible();
    await expect(page.getByText('Expired', { exact: true })).toBeVisible();
    await expect(page.getByText('Used', { exact: true })).toBeVisible();
  });

  test('non-managers are shown the forbidden state', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await mockApi(page, { persona: PERSONAS.student });
    await page.goto('/admin/users/invites');

    await expect(page.getByText('Requires admin or _user_manager role.')).toBeVisible();
  });
});
