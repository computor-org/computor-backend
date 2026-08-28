import { test, expect, type Page, type Route } from '@playwright/test';
import { buildRoster } from '../src/components/course-members/roster';
import type { CourseGroupList, CourseMemberList } from '../src/generated/types/courses';

/**
 * Course groups list the people in them (#385).
 *
 * The page used to show a count per group and nothing else. The count is still
 * there, but a group now opens — collapsed by default, as the issue asks — and
 * members with no group at all get a bucket of their own, which is the question
 * a count could never answer.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = '00000000-0000-0000-0000-0000000000c1';
const GROUPS_URL = `/courses/${COURSE_ID}/lecturer/groups`;

const COURSE = { id: COURSE_ID, title: 'Programming 101', path: 'prog.2026' };

const USER = {
  id: 'u-lect',
  username: 'lect',
  email: 'lect@example.org',
  given_name: 'Lea',
  family_name: 'Lecturer',
  user_roles: [],
};

// "Lab 10" after "Lab 2" is the whole point of the numeric collation, so the
// fixture is deliberately out of order and deliberately double-digit.
const GROUPS: CourseGroupList[] = [
  { id: 'g-10', title: 'Lab 10', course_id: COURSE_ID },
  { id: 'g-2', title: 'Lab 2', course_id: COURSE_ID },
  { id: 'g-empty', title: 'Lab 3', course_id: COURSE_ID },
];

const member = (
  id: string,
  given: string,
  family: string,
  groupId: string | null,
  role = '_student',
): CourseMemberList => ({
  id,
  user_id: `u-${id}`,
  course_id: COURSE_ID,
  course_group_id: groupId,
  course_role_id: role,
  user: {
    id: `u-${id}`,
    given_name: given,
    family_name: family,
    email: `${given.toLowerCase()}@example.org`,
  } as CourseMemberList['user'],
});

const MEMBERS: CourseMemberList[] = [
  member('m1', 'Grace', 'Hopper', 'g-2'),
  member('m2', 'Ada', 'Lovelace', 'g-2'),
  member('m3', 'Alan', 'Turing', 'g-10'),
  member('m4', 'Nina', 'Newcomer', null, '_lecturer'),
  member('m5', 'Tim', 'Tinker', null, '_tutor'),
];

// --------------------------------------------------------------------------
// buildRoster — the bucketing and ordering, without a browser
// --------------------------------------------------------------------------

test('buckets members under their group and orders both levels', () => {
  const roster = buildRoster(GROUPS, MEMBERS);

  expect(roster.map((r) => r.title)).toEqual(['Lab 2', 'Lab 3', 'Lab 10', 'Not in a group']);
  // Sorted by name, not by the primary-key order the API returns.
  expect(roster[0].members.map((m) => m.id)).toEqual(['m2', 'm1']);
  expect(roster[1].members).toEqual([]);
  expect(roster[2].members.map((m) => m.id)).toEqual(['m3']);
  expect(roster[3].members.map((m) => m.id)).toEqual(['m4', 'm5']);
});

test('the unassigned bucket appears only when someone is in it', () => {
  const roster = buildRoster(GROUPS, MEMBERS.filter((m) => m.course_group_id));
  expect(roster.map((r) => r.title)).toEqual(['Lab 2', 'Lab 3', 'Lab 10']);
  expect(roster.every((r) => r.group !== null)).toBe(true);
});

test('a group with no members still gets a row', () => {
  expect(buildRoster(GROUPS, [])).toHaveLength(3);
});

// --------------------------------------------------------------------------
// The page
// --------------------------------------------------------------------------

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const path = new URL(route.request().url()).pathname;

    if (path.startsWith('/user/views')) return json(route, ['lecturer']);
    if (path.endsWith('/user/scopes')) {
      return json(route, { is_admin: false, course: { [COURSE_ID]: ['_lecturer'] } });
    }
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);

    if (path === '/course-groups') return json(route, GROUPS);
    if (path === '/course-members') return json(route, MEMBERS);
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    return json(route, {});
  });
}

test('groups start collapsed, with their size on the row', async ({ page }) => {
  await setup(page);
  await page.goto(GROUPS_URL);

  // Rows in numeric order, each carrying its size. "Not in a group" holds the
  // same count as Lab 2, so the assertion is the whole sequence, not one badge.
  await expect(page.getByText(/^\d+ members?$/)).toHaveText([
    '2 members',
    '0 members',
    '1 member',
    '2 members',
  ]);

  // Nobody is listed until a group is opened.
  await expect(page.getByText('Ada Lovelace')).toBeHidden();
  await expect(page.getByText('Alan Turing')).toBeHidden();
});

test('opening a group reveals its members and only its members', async ({ page }) => {
  await setup(page);
  await page.goto(GROUPS_URL);

  await page.getByRole('button', { name: 'Expand Lab 2' }).click();

  await expect(page.getByText('Ada Lovelace')).toBeVisible();
  await expect(page.getByText('Grace Hopper')).toBeVisible();
  await expect(page.getByText('ada@example.org')).toBeVisible();
  // Lab 10's member stays put.
  await expect(page.getByText('Alan Turing')).toBeHidden();

  // An empty group has nothing to open.
  await expect(page.getByRole('button', { name: 'Expand Lab 3' })).toHaveCount(0);
});

test('members with no group are listed under a bucket of their own', async ({ page }) => {
  await setup(page);
  await page.goto(GROUPS_URL);

  await page.getByRole('button', { name: 'Expand Not in a group' }).click();

  await expect(page.getByText('Nina Newcomer')).toBeVisible();
  await expect(page.getByText('Tim Tinker')).toBeVisible();
  await expect(page.getByText('Tutor', { exact: true })).toBeVisible();
  // It is a view, not a group: nothing here can be edited or deleted.
  await expect(page.getByRole('link', { name: 'Edit' })).toHaveCount(GROUPS.length);
});

test('expand all and collapse all move every group at once', async ({ page }) => {
  await setup(page);
  await page.goto(GROUPS_URL);

  await page.getByRole('button', { name: 'Expand all' }).click();
  await expect(page.getByText('Ada Lovelace')).toBeVisible();
  await expect(page.getByText('Alan Turing')).toBeVisible();
  await expect(page.getByText('Nina Newcomer')).toBeVisible();

  await page.getByRole('button', { name: 'Collapse all' }).click();
  await expect(page.getByText('Ada Lovelace')).toBeHidden();
  await expect(page.getByText('Alan Turing')).toBeHidden();
  await expect(page.getByText('Nina Newcomer')).toBeHidden();
});
