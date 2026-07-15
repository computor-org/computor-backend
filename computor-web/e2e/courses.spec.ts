import { test, expect } from '@playwright/test';
import { PERSONAS, injectAuth, json, mockApi } from './fixtures';

/** /courses — the course list: create gate, per-course role badge, empty state. */

test.describe('course list', () => {
  test('admin sees the courses and the create link', async ({ page }) => {
    await injectAuth(page, PERSONAS.admin);
    await mockApi(page, {
      persona: PERSONAS.admin,
      handlers: (route, url) => {
        if (url.pathname === '/courses' && route.request().method() === 'GET') {
          void json(route, [
            { id: 'c-1', title: 'Algorithms', path: 'algo', language_code: 'en' },
            { id: 'c-2', title: 'Data Structures', path: 'ds' },
          ]);
          return true;
        }
        return false;
      },
    });
    await page.goto('/courses');

    await expect(page.getByRole('heading', { name: 'Courses' })).toBeVisible();
    await expect(page.getByText('Algorithms')).toBeVisible();
    await expect(page.getByText('Data Structures')).toBeVisible();
    await expect(page.getByText('2 courses')).toBeVisible();
    await expect(page.getByRole('link', { name: 'New Course' })).toBeVisible();
  });

  test('a course renders the viewer role badge from scopes', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await mockApi(page, {
      persona: PERSONAS.student,
      handlers: (route, url) => {
        if (url.pathname === '/user/scopes') {
          void json(route, { is_admin: false, course: { 'c-1': ['_lecturer'] } });
          return true;
        }
        if (url.pathname === '/courses' && route.request().method() === 'GET') {
          void json(route, [{ id: 'c-1', title: 'Algorithms', path: 'algo' }]);
          return true;
        }
        return false;
      },
    });
    await page.goto('/courses');

    await expect(page.getByText('Algorithms')).toBeVisible();
    await expect(page.getByText('Lecturer', { exact: true })).toBeVisible();
  });

  test('a student with no courses sees the empty state and no create link', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await mockApi(page, {
      persona: PERSONAS.student,
      handlers: (route, url) => {
        if (url.pathname === '/courses' && route.request().method() === 'GET') {
          void json(route, []);
          return true;
        }
        return false;
      },
    });
    await page.goto('/courses');

    await expect(page.getByText('No courses found')).toBeVisible();
    await expect(page.getByRole('link', { name: 'New Course' })).toHaveCount(0);
  });
});
