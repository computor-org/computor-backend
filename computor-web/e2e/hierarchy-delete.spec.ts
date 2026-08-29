import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Deleting and archiving in the org → family → course hierarchy.
 *
 * The rules under test are the client's half of the backend's: only a scope
 * owner (or admin) is offered Delete; a delete previews first (dry run) and
 * shows what goes and what stays; the server's `blocked_reason` disables the
 * confirm before anything is typed; and the confirm button only arms once the
 * entity's exact path has been typed. Everything backend-side is mocked at
 * the network layer.
 */

const API_ORIGIN = 'http://localhost:8000';
const ORG_ID = '00000000-0000-0000-0000-00000000a001';
const FAMILY_ID = '00000000-0000-0000-0000-00000000f001';
const COURSE_ID = '00000000-0000-0000-0000-0000000000c1';

const ORG = { id: ORG_ID, path: 'itpcp', title: 'ITPCP', organization_type: 'university' };
const FAMILY = { id: FAMILY_ID, path: 'matlab', title: 'MATLAB', organization_id: ORG_ID };
const COURSE = {
  id: COURSE_ID,
  path: 'ws2026',
  title: 'MATLAB WS 2026',
  organization_id: ORG_ID,
  course_family_id: FAMILY_ID,
  archived_at: null as string | null,
};

const USER = {
  id: 'u-owner',
  username: 'owner',
  email: 'owner@example.org',
  given_name: 'Olga',
  family_name: 'Owner',
  user_roles: [],
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

type Scopes = {
  is_admin?: boolean;
  organization?: Record<string, string[]>;
  course_family?: Record<string, string[]>;
  course?: Record<string, string[]>;
};

type Options = {
  scopes?: Scopes;
  course?: typeof COURSE;
  /** The dry-run answer for DELETE /courses/{id}. */
  coursePreview?: Record<string, unknown>;
};

const OWNER_EVERYWHERE: Scopes = {
  is_admin: false,
  organization: { [ORG_ID]: ['_owner'] },
  course_family: { [FAMILY_ID]: ['_owner'] },
  course: { [COURSE_ID]: ['_owner'] },
};

const DEFAULT_PREVIEW = {
  dry_run: true,
  entity_type: 'course',
  entity_id: COURSE_ID,
  deleted_counts: { course_members: 12, submission_groups: 40, submission_artifacts: 3, results: 9, student_submissions: 0 },
  git_repositories: ['forgejo:itpcp-ws2026/template', 'forgejo:itpcp-ws2026/reference'],
  student_repositories_kept: 11,
  blocked_reason: null as string | null,
};

async function setup(page: Page, options: Options = {}) {
  const { scopes = OWNER_EVERYWHERE, course = COURSE, coursePreview = DEFAULT_PREVIEW } = options;

  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  /** Every DELETE the page issued: "<path><query>". */
  const deletes: string[] = [];
  /** Every PATCH the page issued. */
  const patches: string[] = [];

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    // /user/views and the course-scoped /user/views/{id} the sidebar uses —
    // the latter must be an array or Sidebar throws.
    if (path.startsWith('/user/views')) return json(route, ['lecturer']);
    if (path.endsWith('/user/scopes')) return json(route, scopes);
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);

    if (method === 'DELETE') {
      deletes.push(`${path}${url.search}`);
      const dryRun = url.searchParams.get('dry_run') === 'true';
      if (path === `/courses/${COURSE_ID}`) {
        return json(route, { ...coursePreview, dry_run: dryRun });
      }
      if (path === `/organizations/${ORG_ID}`) {
        return json(route, {
          dry_run: dryRun, entity_type: 'organization', entity_id: ORG_ID,
          deleted_counts: { messages: 2 }, git_repositories: [], student_repositories_kept: 0,
          blocked_reason: null,
        });
      }
      return json(route, { message: 'unexpected delete' }, 500);
    }
    if (method === 'PATCH') {
      patches.push(path);
      return route.fulfill({ status: 204, body: '' });
    }

    if (path === `/courses/${COURSE_ID}`) return json(route, course);
    if (path === `/organizations/${ORG_ID}`) return json(route, ORG);
    if (path === `/course-families/${FAMILY_ID}`) return json(route, FAMILY);
    if (path === '/course-families') return json(route, [FAMILY]);
    if (path === '/courses') return json(route, [course]);
    // The course page probes git + workspaces; none of it matters here.
    if (path === `/user/courses/${COURSE_ID}/git`) return json(route, { configured: false });
    if (path === `/user/courses/${COURSE_ID}/repository`) return json(route, { message: 'none' }, 404);
    return json(route, {});
  });

  return { deletes, patches };
}

test('an owner deletes a course: preview, typed path, then the real call', async ({ page }) => {
  const { deletes } = await setup(page);
  await page.goto(`/courses/${COURSE_ID}`);
  await expect(page.getByRole('heading', { name: 'MATLAB WS 2026' })).toBeVisible();

  await page.getByRole('button', { name: 'Delete', exact: true }).click();

  // The dry run drives the preview: counts, the repos that go, the ones kept.
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('Course members')).toBeVisible();
  await expect(dialog.getByText('forgejo:itpcp-ws2026/template')).toBeVisible();
  await expect(dialog.getByText('forgejo:itpcp-ws2026/reference')).toBeVisible();
  await expect(dialog.getByText('Student repositories are kept (11).')).toBeVisible();
  expect(deletes).toEqual([`/courses/${COURSE_ID}?dry_run=true`]);

  const confirm = dialog.getByRole('button', { name: 'Delete', exact: true });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel(/to confirm/).fill('ws2026-wrong');
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel(/to confirm/).fill('ws2026');
  await expect(confirm).toBeEnabled();
  await confirm.click();

  await expect(page).toHaveURL(/\/courses$/);
  expect(deletes).toEqual([
    `/courses/${COURSE_ID}?dry_run=true`,
    `/courses/${COURSE_ID}?dry_run=false`,
  ]);
});

test('a blocked delete is explained up front and cannot be confirmed', async ({ page }) => {
  const reason = 'This course has 3 submissions from students and can only be deleted by an administrator.';
  const { deletes } = await setup(page, {
    coursePreview: {
      ...DEFAULT_PREVIEW,
      deleted_counts: { ...DEFAULT_PREVIEW.deleted_counts, student_submissions: 3 },
      blocked_reason: reason,
    },
  });
  await page.goto(`/courses/${COURSE_ID}`);
  await page.getByRole('button', { name: 'Delete', exact: true }).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText(reason)).toBeVisible();
  await expect(dialog.getByText('Submissions from students', { exact: true })).toBeVisible();

  const confirm = dialog.getByRole('button', { name: 'Delete', exact: true });
  await expect(confirm).toBeDisabled();
  // Typing the exact path changes nothing while the server says no.
  await expect(dialog.getByLabel(/to confirm/)).toBeDisabled();
  await expect(confirm).toBeDisabled();
  expect(deletes).toEqual([`/courses/${COURSE_ID}?dry_run=true`]);
});

test('only an owner is offered Delete on an organization', async ({ page }) => {
  await setup(page, {
    scopes: { is_admin: false, organization: { [ORG_ID]: ['_manager'] } },
  });
  await page.goto(`/organizations/${ORG_ID}`);
  await expect(page.getByRole('heading', { name: 'ITPCP' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Delete', exact: true })).toHaveCount(0);

  await setup(page, { scopes: OWNER_EVERYWHERE });
  await page.goto(`/organizations/${ORG_ID}`);
  await expect(page.getByRole('heading', { name: 'ITPCP' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Delete', exact: true })).toBeVisible();
});

test('an organization delete confirms by path and refreshes the caller', async ({ page }) => {
  const { deletes } = await setup(page);
  await page.goto(`/organizations/${ORG_ID}`);
  await page.getByRole('button', { name: 'Delete', exact: true }).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Messages')).toBeVisible();
  const confirm = dialog.getByRole('button', { name: 'Delete', exact: true });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel(/to confirm/).fill('itpcp');
  await confirm.click();

  await expect(page).toHaveURL(/\/organizations$/);
  expect(deletes).toEqual([
    `/organizations/${ORG_ID}?dry_run=true`,
    `/organizations/${ORG_ID}?dry_run=false`,
  ]);
});

test('an archived course is badged and an owner can unarchive it', async ({ page }) => {
  const { patches } = await setup(page, {
    course: { ...COURSE, archived_at: '2026-08-29T10:00:00+00:00' },
  });
  await page.goto(`/courses/${COURSE_ID}`);

  await expect(page.getByText('Archived', { exact: true })).toBeVisible();
  await expect(page.getByText(/students no longer see this course/)).toBeVisible();
  await page.getByRole('button', { name: 'Unarchive' }).click();

  await expect.poll(() => patches).toEqual([`/courses/${COURSE_ID}/unarchive`]);
});

test('a live course offers Archive to its owner and records the call', async ({ page }) => {
  const { patches } = await setup(page);
  await page.goto(`/courses/${COURSE_ID}`);
  await page.getByRole('button', { name: 'Archive', exact: true }).click();

  await expect.poll(() => patches).toEqual([`/courses/${COURSE_ID}/archive`]);
});

test('a maintainer sees neither Archive nor Delete', async ({ page }) => {
  await setup(page, { scopes: { is_admin: false, course: { [COURSE_ID]: ['_maintainer'] } } });
  await page.goto(`/courses/${COURSE_ID}`);
  await expect(page.getByRole('heading', { name: 'MATLAB WS 2026' })).toBeVisible();

  await expect(page.getByRole('button', { name: 'Delete', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Archive', exact: true })).toHaveCount(0);
});

test('the course list folds archived courses away behind a toggle', async ({ page }) => {
  await setup(page, { course: { ...COURSE, archived_at: '2026-08-29T10:00:00+00:00' } });
  await page.goto('/courses');

  await expect(page.getByRole('switch', { name: 'Show archived courses' })).toBeVisible();
  await expect(page.getByText('MATLAB WS 2026')).toHaveCount(0);

  await page.getByRole('switch', { name: 'Show archived courses' }).click();
  await expect(page.getByText('MATLAB WS 2026')).toBeVisible();
  await expect(page.getByText('Archived', { exact: true })).toBeVisible();
});
