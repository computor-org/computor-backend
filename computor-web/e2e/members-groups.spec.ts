import { test, expect } from '@playwright/test';
import { PERSONAS, injectAuth, json, mockApi } from './fixtures';

/**
 * Course management — members and groups pages: the lecturer gate, the
 * role-assignment ceiling, and delete-only-when-empty for groups.
 */

const COURSE = 'c-1';

/** Scopes granting the persona a course `_lecturer` seat on COURSE. */
function lecturerScopes(route: import('@playwright/test').Route): void {
  void json(route, { is_admin: false, course: { [COURSE]: ['_lecturer'] } });
}

test.describe('course members management', () => {
  test('a lecturer sees members and a ceiling-limited role select', async ({ page }) => {
    await injectAuth(page, PERSONAS.lecturer);
    await mockApi(page, {
      persona: PERSONAS.lecturer,
      handlers: (route, url) => {
        if (url.pathname === '/user/scopes') { lecturerScopes(route); return true; }
        if (url.pathname === '/course-members' && route.request().method() === 'GET') {
          void json(route, [{
            id: 'm-1', user_id: 'u-1', course_id: COURSE, course_group_id: null,
            course_role_id: '_student',
            user: { id: 'u-1', given_name: 'Sam', family_name: 'Student', email: 'sam@example.org' },
          }]);
          return true;
        }
        if (url.pathname === '/course-groups' && route.request().method() === 'GET') {
          void json(route, []);
          return true;
        }
        return false;
      },
    });
    await page.goto(`/courses/${COURSE}/management/members`);

    await expect(page.getByRole('heading', { name: 'Course Members' })).toBeVisible();
    await expect(page.getByText('Sam Student')).toBeVisible();
    // Editable member → a role <select>; the lecturer ceiling excludes senior roles.
    await expect(page.getByRole('combobox').first()).toBeVisible();
    await expect(page.getByRole('option', { name: 'Owner' })).toHaveCount(0);
    await expect(page.getByRole('option', { name: 'Maintainer' })).toHaveCount(0);
  });

  test('a non-lecturer is shown the forbidden state', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await mockApi(page, { persona: PERSONAS.student });
    await page.goto(`/courses/${COURSE}/management/members`);

    await expect(page.getByText(
      'You need lecturer access (or higher) on this course to manage its members.',
    )).toBeVisible();
  });
});

test.describe('course groups management', () => {
  test('groups list allows deleting only empty groups', async ({ page }) => {
    await injectAuth(page, PERSONAS.lecturer);
    await mockApi(page, {
      persona: PERSONAS.lecturer,
      handlers: (route, url) => {
        if (url.pathname === '/user/scopes') { lecturerScopes(route); return true; }
        if (url.pathname === '/course-groups' && route.request().method() === 'GET') {
          void json(route, [
            { id: 'g-1', title: 'Lab A', course_id: COURSE },
            { id: 'g-2', title: 'Lab B', course_id: COURSE },
          ]);
          return true;
        }
        if (url.pathname === '/course-members' && route.request().method() === 'GET') {
          // one member in g-2 → g-2 non-empty, g-1 empty
          void json(route, [{
            id: 'm-1', user_id: 'u-1', course_id: COURSE, course_group_id: 'g-2',
            course_role_id: '_student',
            user: { id: 'u-1', given_name: 'Sam', family_name: 'Student', email: 'sam@example.org' },
          }]);
          return true;
        }
        return false;
      },
    });
    await page.goto(`/courses/${COURSE}/management/groups`);

    await expect(page.getByRole('heading', { name: 'Course Groups' })).toBeVisible();
    await expect(page.getByText('Lab A')).toBeVisible();
    await expect(page.getByText('Lab B')).toBeVisible();
    // g-1 (empty) → an enabled Delete button; g-2 (non-empty) → disabled, titled.
    await expect(page.getByRole('button', { name: 'Delete' })).toBeVisible();
    await expect(
      page.locator('[title="Reassign this group\'s members before deleting it."]'),
    ).toBeVisible();
  });
});
