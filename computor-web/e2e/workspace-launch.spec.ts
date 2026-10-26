import { test, expect, type Page, type Route } from '@playwright/test';

const API_ORIGIN = 'http://localhost:8000';
const WORKSPACE_URL = 'http://localhost:8080/coder/u-me/code/';
const COURSE_WORKSPACE_URL = 'http://localhost:8080/coder/u-me/vscode/';
const COURSE_A = '11111111-1111-4111-8111-111111111111';
const ASSIGNMENT_A = 'aaaaaaaa-1111-4111-8111-111111111111';
const COURSE_B = '22222222-2222-4222-8222-222222222222';
const COURSE_WORKSPACE = {
  id: 'w1', name: 'vscode', owner_id: 'u-me', owner_name: 'u-me',
  template_id: 't-vscode', template_name: 'vscode-workspace',
  latest_build_status: 'succeeded', latest_build_id: 'build-existing',
};

const USER = {
  id: 'u-me',
  username: 'me',
  email: 'me@example.org',
  given_name: 'Wanda',
  family_name: 'Workspace',
  user_roles: [{ role_id: '_workspace_user' }],
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

/** A GET /coder/workspaces/{owner}/{name} response. */
function details({
  status,
  lifecycle,
  ready,
  withUrl = true,
  name = 'code',
}: {
  status: string;
  lifecycle?: string | null;
  ready?: boolean;
  withUrl?: boolean;
  name?: string;
}) {
  const url = name === 'vscode' ? COURSE_WORKSPACE_URL : WORKSPACE_URL;
  return {
    workspace: {
      id: 'w1', name, owner_id: 'u-me', owner_name: 'u-me',
      template_id: 't-vscode', template_name: 'vscode-workspace',
      latest_build_status: status === 'running' ? 'succeeded' : status,
      latest_build_id: 'build-existing',
    },
    status,
    access_url: withUrl && status === 'running' ? url : null,
    code_server_url: withUrl && status === 'running' ? url : null,
    agent_lifecycle: lifecycle ?? null,
    ready: ready ?? false,
    health: true,
    resources: {},
  };
}

/**
 * The dashboard reserves its named launch tab blank inside the click and
 * only then sends it to the launch page, so the course appears in the tab's
 * URL after the popup event, not with it.
 */
async function launchedFor(tab: Page, courseId: string) {
  await tab.waitForURL(
    (url) => url.pathname === '/workspaces/launch' && url.searchParams.get('courseId') === courseId,
    { waitUntil: 'commit' },
  );
}

/**
 * Serve workspace-details responses. Pass an array to script one per poll (the
 * last repeating), or a supplier for tests that need to control exactly when the
 * status changes — the page re-fetches on mount as well as on the poll timer, so
 * a fixed array cannot pin down a specific poll. Returns the start-build
 * requests the page issued.
 */
async function setup(
  page: Page,
  source: ReturnType<typeof details>[] | (() => ReturnType<typeof details>),
  options: {
    handoff?: (route: Route) => Promise<unknown>;
    courseWorkspaces?: boolean;
    workspaces?: Partial<typeof COURSE_WORKSPACE>[];
    workspaceListStatus?: number | (() => number);
    allowProvision?: boolean;
    /** System roles of the signed-in user; a self-enrolled learner has none. */
    systemRoles?: string[];
    userId?: string;
    profileLanguage?: string | null;
    courseRoles?: string[];
    /** False: no cached session, as after the login expired in an idle tab. */
    signedIn?: boolean;
  } = {},
) {
  const next = typeof source === 'function' ? source : undefined;
  const sequence = typeof source === 'function' ? [] : source;
  const systemRoles = options.systemRoles ?? ['_workspace_user'];
  const user = { ...USER, id: options.userId ?? USER.id, profile: { language_code: options.profileLanguage ?? null }, user_roles: systemRoles.map((role_id) => ({ role_id })) };
  if (options.signedIn !== false) await page.addInitScript(({ user, systemRoles }) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles, language: user.profile.language_code,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, { user, systemRoles });

  const starts: string[] = [];
  const stops: string[] = [];
  const contexts: { course_id: string }[] = [];
  const launchRequests: { course_id: string; ui_language?: string; course_content_id?: string }[] = [];
  const actions: string[] = [];
  const provisions: { template: string }[] = [];
  const observedWorkspaces: { id: string; name: string; build: string }[] = [];
  const workspaceName = options.courseWorkspaces ? 'vscode' : 'code';
  const workspaceUrl = options.courseWorkspaces ? COURSE_WORKSPACE_URL : WORKSPACE_URL;
  const workspacePath = `/coder/workspaces/u-me/${workspaceName}`;
  let poll = 0;

  // The workspace itself is not part of this app; stub it so the redirect lands
  // somewhere assertable instead of a connection error.
  await page.context().route(`${workspaceUrl}**`, (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: '<h1>editor</h1>' }),
  );

  await page.context().route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path === '/user/views' || path.startsWith('/user/views/')) return json(route, []);
    if (path.endsWith('/user/scopes')) {
      return json(route, { is_admin: false, course: { [COURSE_A]: options.courseRoles ?? ['_student'], [COURSE_B]: options.courseRoles ?? ['_student'] } });
    }
    if (path.endsWith('/user')) return json(route, user);
    if (path.startsWith('/messages')) return json(route, []);

    if (options.courseWorkspaces) {
      if (path === '/coder/templates') {
        return json(route, {
          templates: [{ id: 't-vscode', name: 'vscode-workspace', display_name: 'VS Code' }],
          count: 1, preparing: [],
        });
      }
      if (path === '/coder/workspaces') {
        const status = typeof options.workspaceListStatus === 'function'
          ? options.workspaceListStatus()
          : options.workspaceListStatus ?? 200;
        if (status !== 200) return json(route, { detail: 'Workspace lookup unavailable.' }, status);
        const workspaces = options.workspaces ?? [COURSE_WORKSPACE];
        return json(route, {
          workspaces, count: workspaces.length,
        });
      }
      if (path === '/courses') {
        return json(route, [
          { id: COURSE_A, title: 'Course A' },
          { id: COURSE_B, title: 'Course B' },
        ]);
      }
      if (/^\/courses\/[^/]+\/workspace-settings$/.test(path)) {
        return json(route, {
          course_id: path.split('/')[2],
          templates: [{
            template_name: 'vscode-workspace', display_name: 'VS Code', enabled: true, exists_in_coder: true,
          }],
          lecturer_provision_enabled: false, can_manage: false,
        });
      }
      if (/^\/courses\/[^/]+$/.test(path)) {
        return json(route, { id: path.split('/')[2], title: 'Course with a workspace' });
      }
      if (path === '/coder/workspaces/provision' && request.method() === 'POST') {
        provisions.push(request.postDataJSON() as { template: string });
        actions.push('provision');
        if (!options.allowProvision) {
          return json(route, { detail: 'Existing workspaces must not be provisioned again.' }, 500);
        }
        return json(route, {
          user: { id: 'u-me', username: 'u-me', email: USER.email },
          workspace: COURSE_WORKSPACE,
          created_user: false, created_workspace: true,
        });
      }
    }

    if (path === `${workspacePath}/launch-context` && request.method() === 'POST') {
      const body = request.postDataJSON() as { course_id: string };
      contexts.push({ course_id: body.course_id });
      launchRequests.push(body);
      if (options.handoff) return options.handoff(route);
      actions.push('context');
      return json(route, { ...body, request_id: `request-${contexts.length}`, expires_at: '2099-01-01T00:00:00Z' });
    }

    if (path === `${workspacePath}/start` && request.method() === 'POST') {
      starts.push(path);
      actions.push('start');
      return json(route, { success: true, message: 'starting' });
    }
    if (path === `${workspacePath}/stop` && request.method() === 'POST') {
      stops.push(path);
      return json(route, { success: true, message: 'stopping' });
    }
    if (path === workspacePath) {
      const body = next ? next() : sequence[Math.min(poll, sequence.length - 1)];
      poll += 1;
      observedWorkspaces.push({
        id: body.workspace.id, name: body.workspace.name, build: body.workspace.latest_build_id,
      });
      return json(route, body);
    }
    return json(route, {});
  });

  return { starts, stops, contexts, launchRequests, actions, provisions, observedWorkspaces };
}

test('waits while the agent is still starting, then opens when it reports ready', async ({ page }) => {
  await setup(page, [
    details({ status: 'starting' }),
    // The 502 trap: running with a URL, but the service inside is still booting.
    details({ status: 'running', lifecycle: 'starting', ready: false }),
    details({ status: 'running', lifecycle: 'starting', ready: false }),
    details({ status: 'running', lifecycle: 'ready', ready: true }),
  ]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');

  // It must hold on the progress view while not ready...
  await expect(page.getByText('Preparing the editor…')).toBeVisible();
  expect(page.url()).not.toContain('8080');

  // A transient launch tab, not an app page: no sidebar/topbar chrome.
  await expect(page.getByRole('navigation')).toHaveCount(0);

  // ...and then open the workspace once the agent reports ready.
  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });
  await expect(page.getByRole('heading', { name: 'editor' })).toBeVisible();
});

test('does not redirect while the workspace is merely running', async ({ page }) => {
  // ready never arrives: the page must keep waiting, not open a 502.
  await setup(page, [details({ status: 'running', lifecycle: 'starting', ready: false })]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');
  // The stage in words, not just "busy": the build is up, and what is left is
  // the agent. No bar — a start has no measurable progress to draw.
  await expect(page.getByText('Preparing the editor…')).toBeVisible();
  await expect(page.getByRole('progressbar')).toHaveCount(0);

  await page.waitForTimeout(5_000);
  expect(page.url()).toContain('/workspaces/launch');
});

test('opens anyway when the agent gave up on its startup script', async ({ page }) => {
  await setup(page, [details({ status: 'running', lifecycle: 'start_timeout', ready: false })]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');

  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });
});

test('starts a stopped workspace exactly once, then opens it', async ({ page }) => {
  const { starts, contexts } = await setup(page, [
    details({ status: 'stopped' }),
    details({ status: 'stopped' }),
    details({ status: 'starting' }),
    details({ status: 'running', lifecycle: 'ready', ready: true }),
  ]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');
  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });

  // The guard: repeated polls of a stopped workspace must not fire a build each tick.
  expect(starts).toHaveLength(1);
  expect(contexts).toHaveLength(0); // Generic launches keep the current course.
});

test('a failed workspace is retried, and its stale status is not mistaken for the retry', async ({
  page,
}) => {
  // Coder keeps reporting the OLD failed build for a while after we ask it to
  // start. Hold it there deliberately: the page must sit tight, not declare
  // failure at the build it just asked for.
  let body = details({ status: 'failed' });
  const { starts } = await setup(page, () => body);

  await page.goto('/workspaces/launch?owner=u-me&name=code');

  await expect.poll(() => starts.length, { timeout: 10_000 }).toBe(1);

  // Several more polls of the stale `failed` — none may surface an error.
  await page.waitForTimeout(6_000);
  await expect(page.getByText('Could not open the workspace')).not.toBeVisible();
  expect(starts).toHaveLength(1); // and no second build

  body = details({ status: 'starting' });
  await page.waitForTimeout(2_500);
  body = details({ status: 'running', lifecycle: 'ready', ready: true });

  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });
});

test('reports failure once our own start build is the one that failed', async ({ page }) => {
  let body = details({ status: 'failed' });
  const { starts } = await setup(page, () => body);

  await page.goto('/workspaces/launch?owner=u-me&name=code');
  await expect.poll(() => starts.length, { timeout: 10_000 }).toBe(1);

  // Our build gets going, so the workspace has left the old failure behind...
  body = details({ status: 'starting' });
  await page.waitForTimeout(2_500);
  // ...and then dies: this failure is ours to report.
  body = details({ status: 'failed' });

  await expect(page.getByText('The workspace failed to start.')).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole('link', { name: 'Desktop VS Code', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'GitHub Codespaces', exact: true }))
    .toHaveAttribute('href', /^https:\/\/codespaces.new\/computor-org\/data-science-python/);
  expect(page.url()).toContain('/workspaces/launch');
});

test('a link with no workspace explains itself instead of spinning', async ({ page }) => {
  await setup(page, [details({ status: 'running', lifecycle: 'ready', ready: true })]);

  await page.goto('/workspaces/launch');

  await expect(page.getByText('Could not open the workspace')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Back to workspaces' })).toBeVisible();
});

test('creating a workspace opens a launch tab for the name the server chose', async ({ page }) => {
  await setup(page, [details({ status: 'starting' })]);

  await page.route(`${API_ORIGIN}/coder/templates`, (route) =>
    json(route, {
      templates: [{ id: 't-vscode', name: 'vscode-workspace', display_name: 'VS Code' }],
      count: 1,
      preparing: [],
    }),
  );
  await page.route(`${API_ORIGIN}/coder/workspaces/provision`, async (route) => {
    // Hold the response so the test can see the tab parked on the creating state.
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    return json(route, {
      user: { id: 'u-me', username: 'u-me', email: USER.email },
      // A self-provisioner's requested name is discarded and re-derived server
      // side, so the launch tab must follow this, not any client-side guess.
      workspace: { id: 'w1', name: 'vscode', owner_id: 'u-me', template_id: 't-vscode' },
      created_user: false,
      created_workspace: true,
    });
  });

  // Creation is the workspaces page itself: one click on the type's card.
  await page.goto('/workspaces');

  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: /VS Code/ }).click();
  const launchTab = await popup;

  // While provisioning round-trips, the tab is already the launch spinner —
  // never a blank about:blank page.
  await expect(launchTab.getByText('Creating your workspace…')).toBeVisible();

  await launchTab.waitForURL(/owner=u-me/);
  expect(launchTab.url()).toContain('name=vscode');

  // The tab the user clicked from stays where it was.
  expect(page.url()).toMatch(/\/workspaces$/);
});

test('a tab parked on the creating state spins instead of erroring', async ({ page }) => {
  await setup(page, [details({ status: 'starting' })]);

  await page.goto('/workspaces/launch?creating=1');

  await expect(page.getByText('Creating your workspace…')).toBeVisible();
  await expect(page.getByText('Could not open the workspace')).not.toBeVisible();
});

test('a ready workspace waits for its course handoff despite repeated polls', async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const { contexts } = await setup(page, [details({ status: 'running', ready: true })], {
    handoff: async (route) => {
      await gate;
      return json(route, { course_id: COURSE_A, request_id: 'request-1', expires_at: '2099-01-01T00:00:00Z' });
    },
  });

  await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
  await expect.poll(() => contexts.length).toBe(1);
  await page.waitForTimeout(4_500); // More polls must share the pending handoff.
  expect(page.url()).toContain('/workspaces/launch');
  expect(contexts).toEqual([{ course_id: COURSE_A }]);

  release();
  await page.waitForURL(WORKSPACE_URL);
});

test('the ready grace period cannot redirect past a pending course handoff', async ({ page }) => {
  await page.clock.install();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const { contexts } = await setup(page, [details({ status: 'running', lifecycle: 'starting' })], {
    handoff: async (route) => {
      await gate;
      return json(route, { course_id: COURSE_A, request_id: 'request-1', expires_at: '2099-01-01T00:00:00Z' });
    },
  });
  await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
  await expect(page.getByText('Preparing the editor…')).toBeVisible();
  await page.clock.fastForward(46_000);
  await expect.poll(() => contexts.length).toBe(1);
  expect(page.url()).toContain('/workspaces/launch');

  release();
  await page.waitForURL(WORKSPACE_URL);
  expect(contexts).toHaveLength(1);
});

test('a stopped course workspace receives its context before its single start request', async ({ page }) => {
  let body = details({ status: 'stopped' });
  const { contexts, starts, actions } = await setup(page, () => body);
  await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
  await expect.poll(() => starts.length).toBe(1);
  expect(actions).toEqual(['context', 'start']);

  body = details({ status: 'running', ready: true });
  await page.waitForURL(WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(starts).toHaveLength(1);
});

test('a rejected course handoff offers retry without opening the wrong course', async ({ page }) => {
  const { contexts, starts } = await setup(page, [details({ status: 'stopped' })], {
    handoff: (route) => json(route, { detail: 'You are not a member of this course.' }, 403),
  });
  await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
  await expect(page.getByRole('heading', { name: 'Could not open the workspace' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  expect(page.url()).toContain('/workspaces/launch');
  expect(contexts).toHaveLength(1);
  expect(starts).toHaveLength(0);
});

test('primary launches reuse the running workspace across courses without rebuilding it', async ({ page }) => {
  const { contexts, starts, provisions, observedWorkspaces } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], {
    courseWorkspaces: true,
  });

  await page.goto(`/courses/${COURSE_A}`);
  const firstPopup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  const first = await firstPopup;
  await first.waitForURL(COURSE_WORKSPACE_URL);

  // Reusing the primary button for another course must only replace the
  // course context, preserving the editor's workspace and current build.
  await page.goto(`/courses/${COURSE_B}`);
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  // This fixture's editor is cross-origin, so its unverified document stays
  // untouched and the ordinary lifecycle fallback uses the portal tab.
  await page.waitForURL(COURSE_WORKSPACE_URL);
  expect(first.isClosed()).toBe(false);
  expect(page.context().pages()).toHaveLength(2);

  expect(contexts).toEqual([{ course_id: COURSE_A }, { course_id: COURSE_B }]);
  expect(starts).toHaveLength(0);
  expect(provisions).toHaveLength(0);
  expect(observedWorkspaces.length).toBeGreaterThanOrEqual(2);
  expect(observedWorkspaces).toEqual(observedWorkspaces.map(() => ({
    id: 'w1', name: 'vscode', build: 'build-existing',
  })));
  await first.close();
});

test('a primary course launch starts its stopped workspace once after the course handoff', async ({ page }) => {
  let body = details({ status: 'stopped', name: 'vscode' });
  const { contexts, starts, actions, provisions } = await setup(page, () => body, {
    courseWorkspaces: true,
    workspaces: [{ ...COURSE_WORKSPACE, latest_build_status: 'stopped' }],
  });
  await page.goto(`/courses/${COURSE_A}`);
  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Start and open' }).click();
  const launchTab = await popup;
  await expect.poll(() => starts.length).toBe(1);
  expect(actions).toEqual(['context', 'start']);

  body = details({ status: 'running', ready: true, name: 'vscode' });
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(starts).toHaveLength(1);
  expect(provisions).toHaveLength(0);
  await launchTab.close();
});

test('a primary course launch provisions an absent workspace once and retains the selected course', async ({ page }) => {
  const { contexts, starts, provisions, actions } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true, workspaces: [], allowProvision: true });
  await page.goto(`/courses/${COURSE_B}`);
  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: /VS Code.*Set up workspace/s }).click();
  const launchTab = await popup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);

  expect(provisions).toEqual([{ template: 'vscode-workspace' }]);
  expect(contexts).toEqual([{ course_id: COURSE_B }]);
  expect(actions).toEqual(['provision', 'context']);
  expect(starts).toHaveLength(0);
  await launchTab.close();
});

test('a primary course launch does not substitute a scratch workspace or another template', async ({ page }) => {
  const { contexts, provisions, observedWorkspaces } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], {
    courseWorkspaces: true,
    workspaces: [
      { ...COURSE_WORKSPACE, id: 'w-scratch', name: 'lecturer-scratch' },
      { ...COURSE_WORKSPACE, id: 'w-other-template', template_name: 'python-workspace' },
    ],
    allowProvision: true,
  });
  await page.goto(`/courses/${COURSE_A}`);
  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: /VS Code.*Set up workspace/s }).click();
  const launchTab = await popup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);

  expect(provisions).toEqual([{ template: 'vscode-workspace' }]);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(observedWorkspaces.every((workspace) => workspace.id === 'w1')).toBe(true);
  await launchTab.close();
});

test('staff Overview offers one state-aware control for the personal workspace', async ({ page }) => {
  // Read on every listing request, so the polled section follows each change.
  const workspaces: Partial<typeof COURSE_WORKSPACE>[] = [];
  await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], {
    courseWorkspaces: true,
    courseRoles: ['_lecturer'],
    workspaces,
  });
  const card = page.locator('div', { has: page.getByRole('heading', { name: 'Workspaces', exact: true }) }).last();
  await page.goto(`/courses/${COURSE_A}`);

  // None yet: only the tile that sets the workspace up, and no paragraph of hints.
  await expect(card.getByRole('button', { name: /VS Code.*Set up workspace/s })).toBeVisible();
  await expect(card.getByText(/Edit, test and submit/)).toHaveCount(0);
  await expect(card.getByRole('button', { name: 'Open in VS Code' })).toHaveCount(0);

  // Stopped: one row, no tile, and no second list for the same workspace.
  workspaces.push({ ...COURSE_WORKSPACE, latest_build_status: 'stopped' });
  await expect(card.getByRole('button', { name: 'Start and open' })).toBeVisible();
  await expect(card.getByText(/Edit, test and submit|Your files are kept/)).toHaveCount(0);
  await expect(card.getByRole('button', { name: /Set up workspace|Launch workspace/ })).toHaveCount(0);
  await expect(card.getByRole('button', { name: 'Stop', exact: true })).toHaveCount(0);
  await expect(card.getByText('Other workspaces')).toHaveCount(0);

  // Running: open plus Stop as the secondary action, and how to finish.
  workspaces[0] = COURSE_WORKSPACE;
  await expect(card.getByRole('button', { name: 'Open in VS Code' })).toBeVisible();
  await expect(card.getByRole('button', { name: 'Stop', exact: true })).toBeVisible();
  await expect(card.getByRole('button', { name: 'Stop', exact: true })).toHaveAttribute('title', 'Shuts down VS Code. Your files are kept.');
  await expect(card.getByRole('button', { name: 'Start and open' })).toHaveCount(0);

  // Stopping: said so, and the launch page would start it again once stopped.
  workspaces[0] = { ...COURSE_WORKSPACE, latest_build_status: 'stopping', latest_build_transition: 'stop' };
  await expect(card.getByText('Stopping', { exact: true })).toBeVisible();
  await expect(card.getByRole('button', { name: 'Start and open' })).toBeVisible();
  await expect(card.getByRole('button', { name: 'Open in VS Code' })).toHaveCount(0);
});

test('Stop on staff Overview stops the personal workspace without opening it', async ({ page }) => {
  const { stops, contexts, starts, provisions } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true, courseRoles: ['_lecturer'] });
  await page.goto(`/courses/${COURSE_A}`);
  await page.getByRole('button', { name: 'Stop', exact: true }).click();
  await expect.poll(() => stops).toEqual(['/coder/workspaces/u-me/vscode/stop']);
  expect(contexts).toHaveLength(0);
  expect(starts).toHaveLength(0);
  expect(provisions).toHaveLength(0);
});

test('a lecturer-provisioned workspace stays listed apart from the personal one', async ({ page }) => {
  await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], {
    courseWorkspaces: true,
    workspaces: [COURSE_WORKSPACE, { ...COURSE_WORKSPACE, id: 'w-scratch', name: 'lecturer-scratch' }],
  });
  await page.goto(`/courses/${COURSE_A}`);
  await expect(page.getByRole('button', { name: 'Open in VS Code' })).toHaveCount(1);
  await expect(page.getByText('Other workspaces')).toBeVisible();
  await expect(page.getByText('lecturer-scratch')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open', exact: true })).toHaveCount(1);
});

test('a failed workspace lookup shows an error without provisioning and allows a safe retry', async ({ page }) => {
  let status = 200;
  const { contexts, starts, provisions } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true, workspaceListStatus: () => status });
  await page.goto(`/courses/${COURSE_A}`);
  // The background poll saw the existing workspace; a failing fresh lookup
  // must not silently use that stale snapshot or fall back to provisioning.
  await expect(page.getByRole('button', { name: 'Open in VS Code' })).toBeVisible();
  status = 503;
  const firstPopup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  const failedTab = await firstPopup;
  await expect(page.getByText('Workspace lookup unavailable.', { exact: true })).toBeVisible();
  await expect.poll(() => failedTab.isClosed()).toBe(true);
  expect(provisions).toHaveLength(0);
  expect(starts).toHaveLength(0);
  expect(contexts).toHaveLength(0);

  status = 200;
  const retryPopup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  const launchTab = await retryPopup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(provisions).toHaveLength(0);
  expect(starts).toHaveLength(0);
  await launchTab.close();
});

test('an existing workspace with no owner fails safely and can be retried without provisioning', async ({ page }) => {
  const workspaces: Partial<typeof COURSE_WORKSPACE>[] = [
    { ...COURSE_WORKSPACE, owner_name: undefined },
  ];
  const { contexts, starts, provisions } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true, workspaces });
  await page.goto(`/courses/${COURSE_A}`);
  const firstPopup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  const failedTab = await firstPopup;
  await expect(page.getByText('The existing workspace owner is unavailable. Please retry.', {
    exact: true,
  })).toBeVisible();
  await expect.poll(() => failedTab.isClosed()).toBe(true);
  expect(provisions).toHaveLength(0);
  expect(starts).toHaveLength(0);
  expect(contexts).toHaveLength(0);

  workspaces[0] = COURSE_WORKSPACE;
  const retryPopup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  const launchTab = await retryPopup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(provisions).toHaveLength(0);
  expect(starts).toHaveLength(0);
  await launchTab.close();
});

test('the compact course-card launcher reuses the running workspace without provisioning', async ({ page }) => {
  const { contexts, starts, provisions } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true });
  await page.goto('/courses');
  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Launch VS Code workspace' }).first().click();
  const launchTab = await popup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(page.url()).toMatch(/\/courses$/);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(provisions).toHaveLength(0);
  expect(starts).toHaveLength(0);
  await launchTab.close();
});

test('a popup-blocked primary course launch retains the course in its same-tab fallback', async ({ page }) => {
  const { contexts, provisions, starts } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], {
    courseWorkspaces: true,
  });
  await page.addInitScript(() => { window.open = () => null; });
  await page.goto(`/courses/${COURSE_B}`);
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  await page.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_B }]);
  expect(provisions).toHaveLength(0);
  expect(starts).toHaveLength(0);
});

test('a popup-blocked Start and open retains the selected course', async ({ page }) => {
  let body = details({ status: 'stopped', name: 'vscode' });
  const { contexts, starts, provisions } = await setup(page, () => body, {
    courseWorkspaces: true,
    workspaces: [{ ...COURSE_WORKSPACE, latest_build_status: 'stopped' }],
  });
  await page.addInitScript(() => { window.open = () => null; });
  await page.goto(`/courses/${COURSE_B}`);
  await page.getByRole('button', { name: 'Start and open' }).click();
  await expect.poll(() => starts.length).toBe(1);
  body = details({ status: 'running', ready: true, name: 'vscode' });
  await page.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_B }]);
  expect(provisions).toHaveLength(0);
});

test('the dashboard offers a stopped workspace with a labelled start action', async ({ page }) => {
  let body = details({ status: 'stopped', name: 'vscode' });
  const { contexts, starts, provisions } = await setup(page, () => body, {
    courseWorkspaces: true,
    workspaces: [{
      ...COURSE_WORKSPACE, latest_build_status: 'succeeded', latest_build_transition: 'stop',
      template_display_name: 'VS Code', template_version_created_at: '2026-10-20T12:05:00Z',
    }],
  });
  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByText('VS Code', { exact: true })).toBeVisible();
  await expect(section.getByText('Stopped')).toBeVisible();
  // The version date is in the status chip's tooltip, not a line of its own.
  await expect(section.getByTitle(/· Version of \d{1,2} Oct 2026, \d{2}:\d{2}$/)).toBeVisible();
  await expect(section.getByText(/Version of/)).toHaveCount(0);

  await section.getByRole('combobox', { name: 'Choose a course' }).selectOption(COURSE_A);
  const popup = page.waitForEvent('popup');
  await section.getByRole('button', { name: 'Start and open' }).click();
  const launchTab = await popup;
  await launchedFor(launchTab, COURSE_A);
  await expect.poll(() => starts.length).toBe(1);
  body = details({ status: 'running', ready: true, name: 'vscode' });
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  expect(provisions).toHaveLength(0);
  await launchTab.close();
});

test('the dashboard reopens a running workspace in the course it was last opened for', async ({ page }) => {
  const { contexts, starts } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true });

  await page.goto(`/courses/${COURSE_B}`);
  const coursePopup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code' }).click();
  const courseTab = await coursePopup;
  await courseTab.waitForURL(COURSE_WORKSPACE_URL);
  await courseTab.close();

  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByText('Last opened in Course B')).toBeVisible();
  const popup = page.waitForEvent('popup');
  await section.getByRole('button', { name: 'Open', exact: true }).click();
  const launchTab = await popup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_B }, { course_id: COURSE_B }]);
  expect(starts).toHaveLength(0);
  await launchTab.close();
});

test('the dashboard reopens the course the server remembers, also in a fresh browser', async ({ page }) => {
  const { contexts } = await setup(page, [
    details({ status: 'running', ready: true, name: 'vscode' }),
  ], { courseWorkspaces: true, workspaces: [{ ...COURSE_WORKSPACE, last_course_id: COURSE_B }] });

  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByText('Last opened in Course B')).toBeVisible();
  const popup = page.waitForEvent('popup');
  await section.getByRole('button', { name: 'Open', exact: true }).click();
  const launchTab = await popup;
  await launchedFor(launchTab, COURSE_B);
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_B }]);
  await launchTab.close();
});

test('the dashboard ignores a remembered course the learner is no longer in', async ({ page }) => {
  await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], {
    courseWorkspaces: true,
    workspaces: [{ ...COURSE_WORKSPACE, last_course_id: '33333333-3333-4333-8333-333333333333' }],
  });
  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByRole('button', { name: 'Open', exact: true })).toBeVisible();
  await expect(section.getByText(/Last opened in/)).toHaveCount(0);
});

test('a stopping workspace says so and offers to start it again', async ({ page }) => {
  await setup(page, [details({ status: 'stopped', name: 'vscode' })], {
    courseWorkspaces: true,
    workspaces: [{ ...COURSE_WORKSPACE, latest_build_status: 'stopping', latest_build_transition: 'stop' }],
  });
  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByText('Stopping', { exact: true })).toBeVisible();
  await expect(section.getByRole('button', { name: 'Start and open' })).toBeVisible();
  await expect(section.getByRole('button', { name: 'Open', exact: true })).toHaveCount(0);
});

test.describe('in German', () => {
  test.use({ locale: 'de-AT' });

  test('a stopping workspace reads "Wird gestoppt" and offers to start it again', async ({ page }) => {
    await setup(page, [details({ status: 'stopped', name: 'vscode' })], {
      courseWorkspaces: true,
      workspaces: [{ ...COURSE_WORKSPACE, latest_build_status: 'stopping', latest_build_transition: 'stop' }],
    });
    await page.goto('/dashboard');
    const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Deine Arbeitsumgebungen' }) });
    await expect(section.getByText('Wird gestoppt', { exact: true })).toBeVisible();
    await expect(section.getByRole('button', { name: 'Starten und öffnen' })).toBeVisible();
  });

  test('the course page says what Stop does in its tooltip, not in a paragraph', async ({ page }) => {
    await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], { courseWorkspaces: true });
    await page.goto(`/courses/${COURSE_A}`);
    await expect(page.getByRole('button', { name: 'Stoppen', exact: true }))
      .toHaveAttribute('title', 'Beendet VS Code. Deine Dateien bleiben erhalten.');
    await expect(page.getByText(/Wenn du fertig bist|Deine Dateien bleiben erhalten/)).toHaveCount(0);
  });

  test('a new learner is welcomed without "zurück" and pointed to the catalog', async ({ page }) => {
    await setup(page, [details({ status: 'stopped', name: 'vscode' })], { systemRoles: [] });
    await page.route(`${API_ORIGIN}/courses`, (route) => json(route, []));
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: 'Willkommen, Wanda' })).toBeVisible();
    await expect(page.getByText(/zurück/)).toHaveCount(0);
    await expect(page.getByText('Im Katalog findest du Kurse, denen du beitreten kannst.')).toBeVisible();
    await expect(page.getByText(/keinen Zugriff/)).toHaveCount(0);
  });
});

test('a learner without a workspace role finds their workspace in the sidebar', async ({ page }) => {
  await setup(page, [details({ status: 'stopped', name: 'vscode' })], {
    courseWorkspaces: true,
    systemRoles: [],
    workspaces: [{ ...COURSE_WORKSPACE, latest_build_status: 'stopped' }],
  });
  await page.goto('/dashboard');
  await expect(page.getByRole('complementary').getByRole('link', { name: 'Workspaces' })).toBeVisible();
});

test('a learner without a workspace role or workspace gets no workspace entry', async ({ page }) => {
  await setup(page, [details({ status: 'stopped', name: 'vscode' })], {
    courseWorkspaces: true,
    systemRoles: [],
    workspaces: [],
  });
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: 'Your courses' })).toBeVisible();
  await expect(page.getByRole('complementary').getByRole('link', { name: 'Courses', exact: true })).toBeVisible();
  await expect(page.getByRole('complementary').getByRole('link', { name: 'Workspaces' })).toHaveCount(0);
});


test('the dashboard infers the only course supporting a workspace without launch history', async ({ page }) => {
  const { contexts } = await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], { courseWorkspaces: true });
  await page.route(`${API_ORIGIN}/courses/${COURSE_B}/workspace-settings`, (route) => json(route, { templates: [] }));
  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByText('Course: Course A', { exact: true })).toBeVisible();
  const popup = page.waitForEvent('popup');
  await section.getByRole('button', { name: 'Open', exact: true }).click();
  const launchTab = await popup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_A }]);
  await launchTab.close();
});

test('the dashboard asks which course to open when there is no course history', async ({ page }) => {
  const { contexts } = await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], { courseWorkspaces: true });
  await page.goto('/dashboard');
  const section = page.locator('section').filter({ has: page.getByRole('heading', { name: 'Your workspaces' }) });
  await expect(section.getByRole('button', { name: 'Open', exact: true })).toBeDisabled();
  await section.getByRole('combobox', { name: 'Choose a course' }).selectOption(COURSE_B);
  const popup = page.waitForEvent('popup');
  await section.getByRole('button', { name: 'Open', exact: true }).click();
  const launchTab = await popup;
  await launchTab.waitForURL(COURSE_WORKSPACE_URL);
  expect(contexts).toEqual([{ course_id: COURSE_B }]);
  await launchTab.close();
});


test.describe('launch interface language', () => {
  test.use({ locale: 'de-DE' });
  for (const profileLanguage of [null, 'en']) {
    test(`hands off resolved interface language for profile ${profileLanguage ?? 'Automatic'}`, async ({ page }) => {
      const { launchRequests } = await setup(page, [details({ status: 'running', ready: true })], { profileLanguage });
      await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
      await page.waitForURL(WORKSPACE_URL);
      expect(launchRequests).toEqual([{ course_id: COURSE_A, ui_language: profileLanguage ?? 'de' }]);
    });
  }
  test('an explicit browser interface choice wins over browser locale for Automatic', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('computor.language', 'en'));
    const { launchRequests } = await setup(page, [details({ status: 'running', ready: true })]);
    await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
    await page.waitForURL(WORKSPACE_URL);
    expect(launchRequests).toEqual([{ course_id: COURSE_A, ui_language: 'en' }]);
  });
});


test.describe('launch interface language in an English browser', () => {
  test.use({ locale: 'en-US' });
  for (const profileLanguage of [null, 'de']) {
    test(`hands off resolved interface language for profile ${profileLanguage ?? 'Automatic'}`, async ({ page }) => {
      const { launchRequests } = await setup(page, [details({ status: 'running', ready: true })], { profileLanguage });
      await page.goto(`/workspaces/launch?owner=u-me&name=code&courseId=${COURSE_A}`);
      await page.waitForURL(WORKSPACE_URL);
      expect(launchRequests).toEqual([{ course_id: COURSE_A, ui_language: profileLanguage ?? 'en' }]);
    });
  }
});


for (const locale of ['de-DE', 'en-US']) {
  test.describe(`returning greeting ${locale}`, () => {
    test.use({ locale });
    for (const returningState of ['course', 'workspace']) {
      test(`welcomes back a learner with an existing ${returningState}`, async ({ page }) => {
        await setup(page, [details({ status: 'stopped', name: 'vscode' })], {
          courseWorkspaces: true, workspaces: returningState === 'course' ? [] : [COURSE_WORKSPACE],
        });
        if (returningState === 'workspace') await page.route(`${API_ORIGIN}/courses`, (route) => json(route, []));
        await page.goto('/dashboard');
        await expect(page.getByRole('heading', { name: locale === 'de-DE' ? 'Willkommen zurück, Wanda' : 'Welcome back, Wanda', exact: true })).toBeVisible();
      });
    }
  });
}

test('a never-enrolled learner without a workspace gets a first welcome in English', async ({ page }) => {
  await setup(page, [details({ status: 'stopped', name: 'vscode' })], { courseWorkspaces: true, workspaces: [] });
  await page.route(`${API_ORIGIN}/courses`, (route) => json(route, []));
  await page.goto('/dashboard');
  await expect(page.getByText('The catalog lists the courses you can join.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Welcome, Wanda', exact: true })).toBeVisible();
});

for (const [locale, event, stopped, running, start, open, courseLaunch] of [
  ['en-US', 'focus', 'Stopped', 'Running', 'Start and open', 'Open', 'Launch VS Code workspace'],
  ['de-DE', 'visibilitychange', 'Gestoppt', 'Läuft', 'Starten und öffnen', 'Öffnen', 'Arbeitsumgebung VS Code starten'],
] as const) {
  test.describe(`dashboard workspace return refresh ${locale}`, () => {
    test.use({ locale });
    test(`refreshes external workspace changes on ${event}`, async ({ page }, testInfo) => {
      await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], { courseWorkspaces: true });
      let isRunning = false;
      let workspaceReads = 0;
      const heavyReads: string[] = [];
      page.on('request', (request) => {
        const path = new URL(request.url()).pathname;
        if (path === '/courses' || path === '/students/course-contents' || path === '/messages' || path.endsWith('/workspace-settings')) heavyReads.push(path);
      });
      await page.route(`${API_ORIGIN}/coder/workspaces`, (route) => {
        workspaceReads++;
        return json(route, {
          workspaces: [{ ...COURSE_WORKSPACE, last_course_id: COURSE_A, latest_build_status: 'succeeded', latest_build_transition: isRunning ? 'start' : 'stop' }], count: 1,
        });
      });
      await page.goto('/dashboard');
      await expect(page.getByText(stopped, { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: start, exact: true })).toBeVisible();
      // Each course card loads its course's workspace settings once when it
      // mounts, which can land after the workspace row. Count those reads as
      // part of the first load before checking that a return re-reads none.
      await expect(page.getByRole('button', { name: courseLaunch, exact: true })).toHaveCount(2);
      const initialHeavyReads = [...heavyReads];
      expect(initialHeavyReads).toContain('/courses');
      // The editor/launch tab updates the server while this dashboard stays mounted.
      isRunning = true;
      await page.evaluate((event) => {
        (event === 'focus' ? window : document).dispatchEvent(new Event(event));
      }, event);
      await expect(page.getByText(running, { exact: true })).toBeVisible({ timeout: 2000 });
      await expect(page.getByRole('button', { name: open, exact: true })).toBeEnabled();
      await expect(page.getByRole('button', { name: start, exact: true })).toHaveCount(0);
      await expect.poll(() => workspaceReads).toBeGreaterThanOrEqual(3);
      expect(heavyReads).toEqual(initialHeavyReads);
      await page.screenshot({ path: testInfo.outputPath(`dashboard-running-${locale}.png`) });
    });
  });
}

test.describe('German mobile workspace action', () => {
  test.use({ locale: 'de-DE', viewport: { width: 390, height: 844 } });

  test('the setup action is fully readable and opens its selected course', async ({ page }, testInfo) => {
    const { contexts, provisions } = await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], {
      courseWorkspaces: true, workspaces: [], allowProvision: true,
    });
    await page.goto(`/courses/${COURSE_A}`);
    const button = page.getByRole('button', { name: /VS Code.*Arbeitsumgebung einrichten/s });
    await expect(button).toBeVisible();
    const collapseSidebar = page.getByRole('button', { name: 'Seitenleiste einklappen', exact: true });
    if (await collapseSidebar.isVisible()) await collapseSidebar.click();
    await expect(page.getByRole('complementary')).toHaveCSS('width', '64px');
    const action = button.getByText('Arbeitsumgebung einrichten', { exact: true });
    await expect(action).toBeVisible();
    const screenshot = testInfo.outputPath('workspace-setup-390.png');
    await button.screenshot({ path: screenshot });
    await testInfo.attach('workspace setup at 390 pixels', { path: screenshot, contentType: 'image/png' });
    // toBeVisible also passes for ellipsized text. Every rendered text line
    // must fit inside the label, so the whole action can actually be read.
    expect(await action.evaluate((element) => {
      const bounds = element.getBoundingClientRect();
      const range = document.createRange();
      range.selectNodeContents(element);
      return Array.from(range.getClientRects()).every((line) =>
        line.left >= bounds.left - 1 && line.right <= bounds.right + 1 &&
        line.top >= bounds.top - 1 && line.bottom <= bounds.bottom + 1);
    })).toBe(true);
    const popup = page.waitForEvent('popup');
    await button.click();
    const launchTab = await popup;
    await launchTab.waitForURL(COURSE_WORKSPACE_URL);
    expect(provisions).toEqual([{ template: 'vscode-workspace' }]);
    expect(contexts).toEqual([{ course_id: COURSE_A }]);
    await launchTab.close();
  });
});


for (const locale of ['de-DE', 'en-US']) {
  test.describe(`course continuation permissions ${locale}`, () => {
    test.use({ locale, viewport: { width: locale === 'de-DE' ? 390 : 1440, height: 900 } });
    for (const persona of [
      { name: 'learner', courseRoles: ['_student'], systemRoles: [], screenshot: true },
      { name: 'tutor', courseRoles: ['_student', '_tutor'], systemRoles: [], screenshot: false },
      { name: 'teacher', courseRoles: ['_lecturer'], systemRoles: [], screenshot: false },
      { name: 'admin enrolled as learner', courseRoles: ['_student'], systemRoles: ['_admin'], screenshot: false },
      { name: 'organization manager enrolled as learner', courseRoles: ['_student'], systemRoles: ['_organization_manager'], screenshot: false },
      { name: 'member without course permissions', courseRoles: [], systemRoles: [], screenshot: false },
    ]) {
      test(`existing course links keep the right destination for ${persona.name}`, async ({ page }, testInfo) => {
        await setup(page, [details({ status: 'stopped' })], { courseWorkspaces: true, ...persona });
        // Every role lands on the course overview, as on main.
        const destination = `/courses/${COURSE_A}`;
        const label = locale === 'de-DE' ? 'Kurs ansehen' : 'View Course';
        for (const surface of ['/dashboard', '/courses']) {
          await page.goto(surface);
          const title = page.getByRole('link', { name: /^Course A(?:\s|$)/ });
          await expect(title).toBeVisible();
          if (locale === 'de-DE') {
            const collapse = page.getByRole('button', { name: 'Seitenleiste einklappen', exact: true });
            if (await collapse.isVisible()) await collapse.click();
            await expect(page.getByRole('complementary')).toHaveCSS('width', '64px');
          }
          await expect(title).toHaveAttribute('href', destination);
          const card = title.locator('..');
          await expect(card.getByRole('link', { name: label, exact: true })).toHaveAttribute('href', destination);
          if (persona.screenshot) {
            await card.getByRole('link', { name: label, exact: true }).scrollIntoViewIfNeeded();
            await page.screenshot({ path: testInfo.outputPath(`continue-${locale}-${surface.slice(1)}.png`) });
          }
          if (!persona.courseRoles.length) {
            await expect(card.getByRole('button')).toHaveCount(0);
          }
        }
      });
    }
    test('a signed-out visitor still reaches login instead of learner continuation', async ({ page, baseURL }) => {
      await setup(page, [details({ status: 'stopped' })], { signedIn: false });
      const handoffs: string[] = [];
      const navigations: string[] = [];
      page.on('framenavigated', (frame) => {
        if (frame === page.mainFrame()) navigations.push(frame.url());
      });
      await page.route(`${API_ORIGIN}/auth/keycloak/login**`, (route) => {
        handoffs.push(route.request().url());
        return route.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Sign-in handoff</h1>' });
      });
      await page.goto('/dashboard');
      await expect(page.getByRole('heading', { name: 'Sign-in handoff', exact: true })).toBeVisible();
      expect(handoffs).toHaveLength(1);
      const appOrigin = new URL(baseURL!).origin;
      const entry = navigations.map((url) => new URL(url)).find((url) => url.origin === appOrigin && url.pathname === '/login');
      expect(entry?.searchParams.get('next')).toBe('/dashboard');
      const login = new URL(handoffs[0]);
      expect(login.searchParams.get('ui_locales')).toBe(locale === 'de-DE' ? 'de' : 'en');
      const callback = new URL(login.searchParams.get('redirect_uri')!);
      expect(callback.origin).toBe(new URL(baseURL!).origin);
      expect(callback.pathname).toBe('/auth/success');
      await expect(page.getByRole('link', { name: locale === 'de-DE' ? 'Kurs ansehen' : 'View Course', exact: true })).toHaveCount(0);
    });
  });
}


test('catalog cards keep plain titles and joining while enrolled learners open the course overview', async ({ page }) => {
  await setup(page, [details({ status: 'stopped' })]);
  await page.route(`${API_ORIGIN}/courses/public**`, (route) => json(route, [
    { id: COURSE_A, title: 'Course A', enrolled: false },
    { id: COURSE_B, title: 'Course B', enrolled: true },
  ]));
  await page.goto('/courses/catalog');
  await expect(page.getByRole('heading', { name: 'Course A', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Course B', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: /^Course [AB](?:\s|$)/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Join course', exact: true })).toHaveCount(1);
  await expect(page.getByRole('link', { name: 'Open course', exact: true })).toHaveAttribute('href', `/courses/${COURSE_B}`);
});


for (const initial of ['running', 'stopped'] as const) {
  test(`exact assignment launch retains its target in a ${initial} personal workspace`, async ({ page }) => {
    let workspace = details({ status: initial, ready: initial === 'running', name: 'vscode' });
    const { launchRequests, starts, provisions } = await setup(page, () => workspace, { courseWorkspaces: true });
    await page.goto(`/workspaces/launch?owner=u-me&name=vscode&courseId=${COURSE_A}&courseContentId=${ASSIGNMENT_A}`);
    await expect.poll(() => launchRequests.length).toBe(1);
    expect(launchRequests[0]).toEqual({ course_id: COURSE_A, ui_language: 'en', course_content_id: ASSIGNMENT_A });
    if (initial === 'stopped') {
      await expect.poll(() => starts.length).toBe(1);
      workspace = details({ status: 'running', ready: true, name: 'vscode' });
    }
    await page.waitForURL(COURSE_WORKSPACE_URL);
    expect(starts).toHaveLength(initial === 'stopped' ? 1 : 0);
    expect(provisions).toHaveLength(0);
  });
}

test('opening the same assignment again sends a new launch request without rebuilding', async ({ page }) => {
  const { launchRequests, starts, provisions } = await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], { courseWorkspaces: true });
  for (let click = 0; click < 2; click++) {
    await page.goto(`/workspaces/launch?owner=u-me&name=vscode&courseId=${COURSE_A}&courseContentId=${ASSIGNMENT_A}`);
    await page.waitForURL(COURSE_WORKSPACE_URL);
  }
  expect(launchRequests.map((request) => request.course_content_id)).toEqual([ASSIGNMENT_A, ASSIGNMENT_A]);
  expect(starts).toHaveLength(0);
  expect(provisions).toHaveLength(0);
});

for (const failure of ['unavailable', 'wrong-target', 'missing-course'] as const) {
  test(`an exact assignment launch fails safely for ${failure}`, async ({ page }) => {
    const { starts, provisions } = await setup(page, [details({ status: 'running', ready: true, name: 'vscode' })], {
      courseWorkspaces: true,
      handoff: (route) => failure === 'unavailable'
        ? json(route, { detail: 'Assignment is not available.' }, 404)
        : json(route, { course_id: COURSE_A, course_content_id: null, request_id: 'request-1', expires_at: '2099-01-01T00:00:00Z' }),
    });
    const course = failure === 'missing-course' ? '' : `&courseId=${COURSE_A}`;
    await page.goto(`/workspaces/launch?owner=u-me&name=vscode${course}&courseContentId=${ASSIGNMENT_A}`);
    await expect(page.getByRole('heading', { name: 'Could not open the workspace' })).toBeVisible();
    if (failure === 'unavailable') {
      await expect(page.getByText('Your selection could not be opened in your workspace. Please retry.', { exact: true })).toBeVisible();
      await expect(page.getByText('Assignment is not available.', { exact: true })).toHaveCount(0);
    }
    expect(page.url()).toContain('/workspaces/launch');
    expect(starts).toHaveLength(0);
    expect(provisions).toHaveLength(0);
  });
}


for (const language of ['de', 'en'] as const) {
  test(`named workspace reuse preserves the dirty editor and renews the exact target in ${language}`, async ({ page, baseURL }) => {
    const nativeUrl = new URL('/coder/u-me/vscode/', baseURL).href;
    const state = { ...details({ status: 'running', ready: true, name: 'vscode' }), access_url: nativeUrl, code_server_url: nativeUrl };
    let rejectSelection = false;
    const { launchRequests, starts, provisions } = await setup(page, [state], {
      courseWorkspaces: true, profileLanguage: language,
      handoff: (route) => rejectSelection
        ? json(route, { detail: 'PRIVATE_INTERNAL_ERROR_PATH' }, 503)
        : json(route, { ...route.request().postDataJSON(), request_id: 'fresh-request', expires_at: '2099-01-01T00:00:00Z' }),
    });
    let loads = 0;
    await page.context().route(`${nativeUrl}**`, (route) => {
      loads++;
      return route.fulfill({ contentType: 'text/html', body: '<h1>Pinned Welcome</h1><textarea aria-label="Dirty Python">unsaved code</textarea>' });
    });
    await page.route(`${API_ORIGIN}/students/course-contents**`, (route) => json(route, [
      { id: ASSIGNMENT_A, course_id: COURSE_A, course_content_kind_id: 'assignment', title: 'Exercise A', path: 'a', status: 'correction_necessary' },
      { id: 'bbbbbbbb-1111-4111-8111-111111111111', course_id: COURSE_B, course_content_kind_id: 'assignment', title: 'Exercise B', path: 'b', status: 'correction_necessary' },
    ]));
    await page.goto('/dashboard');
    const popup = page.waitForEvent('popup');
    await page.getByRole('link', { name: /Exercise A/ }).click();
    const editor = await popup;
    await editor.waitForURL(nativeUrl);
    await editor.getByRole('textbox', { name: 'Dirty Python' }).fill('unsaved change before another exercise');
    const originalDocument = await editor.evaluate(() => performance.timeOrigin);
    const originalName = await editor.evaluate(() => window.name);
    await page.getByRole('link', { name: /Exercise B/ }).click();
    await expect.poll(() => launchRequests.length).toBe(2);
    expect(launchRequests.map((request) => request.course_content_id)).toEqual([ASSIGNMENT_A, 'bbbbbbbb-1111-4111-8111-111111111111']);
    expect(await editor.evaluate(() => performance.timeOrigin)).toBe(originalDocument);
    expect(await editor.evaluate(() => window.name)).toBe(originalName);
    await expect(editor.getByRole('heading', { name: 'Pinned Welcome' })).toBeVisible();
    await expect(editor.getByRole('textbox', { name: 'Dirty Python' })).toHaveValue('unsaved change before another exercise');
    expect(page.context().pages()).toHaveLength(2);
    expect(loads).toBe(1);
    expect(starts).toHaveLength(0);
    expect(provisions).toHaveLength(0);
    rejectSelection = true;
    await page.getByRole('link', { name: /Exercise A/ }).click();
    await expect(page.getByText(language === 'de'
      ? 'Deine Auswahl konnte in deiner Arbeitsumgebung nicht geöffnet werden. Versuch es noch einmal.'
      : 'Your selection could not be opened in your workspace. Please retry.', { exact: true })).toBeVisible();
    await expect(page.getByText(/PRIVATE_INTERNAL_ERROR_PATH/)).toHaveCount(0);
    await page.getByRole('button', { name: language === 'de' ? 'Arbeitsumgebung VS Code starten' : 'Launch VS Code workspace', exact: true }).first().click();
    await expect.poll(() => launchRequests.length).toBe(4);
    expect(launchRequests[3].course_content_id).toBeUndefined();
    await expect(page.getByText(/PRIVATE_INTERNAL_ERROR_PATH/)).toHaveCount(0);
    expect(editor.isClosed()).toBe(false);
    expect(await editor.evaluate(() => performance.timeOrigin)).toBe(originalDocument);
    await expect(editor.getByRole('textbox', { name: 'Dirty Python' })).toHaveValue('unsaved change before another exercise');
    expect(loads).toBe(1);
    expect(page.context().pages()).toHaveLength(2);
  });
}


async function namedDashboard(page: Page, baseURL: string | undefined, options: Parameters<typeof setup>[2] = {}, path = '/coder/u-me/vscode/') {
  const url = new URL(path, baseURL).href;
  let state = { ...details({ status: 'running', ready: true, name: 'vscode' }), access_url: url, code_server_url: url };
  const harness = await setup(page, () => state, { courseWorkspaces: true, ...options });
  let loads = 0;
  await page.context().route(`${url}**`, (route) => {
    loads++;
    return route.fulfill({ contentType: 'text/html', body: '<h1>Pinned Welcome</h1><textarea aria-label="Dirty Python">unsaved code</textarea>' });
  });
  await page.route(`${API_ORIGIN}/students/course-contents**`, (route) => json(route, [
    { id: ASSIGNMENT_A, course_id: COURSE_A, course_content_kind_id: 'assignment', title: 'Exercise A', path: 'a', status: 'correction_necessary' },
    { id: 'bbbbbbbb-1111-4111-8111-111111111111', course_id: COURSE_B, course_content_kind_id: 'assignment', title: 'Exercise B', path: 'b', status: 'correction_necessary' },
  ]));
  await page.goto('/dashboard');
  return { ...harness, url, loads: () => loads, stop: () => { state = { ...state, status: 'stopped', ready: false }; },
    async open() {
      const popup = page.waitForEvent('popup');
      await page.getByRole('link', { name: /Exercise A/ }).click();
      const editor = await popup;
      await editor.waitForURL(url);
      await editor.getByRole('textbox', { name: 'Dirty Python' }).fill('preserve this unsaved buffer');
      return editor;
    },
  };
}

test('named workspace context writes serialize so a delayed older target cannot win', async ({ page, baseURL }) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  const committed: string[] = [];
  let requests = 0;
  const fixture = await namedDashboard(page, baseURL, { handoff: async (route) => {
    requests++;
    if (requests === 2) await held;
    const body = route.request().postDataJSON();
    committed.push(body.course_content_id);
    return json(route, { ...body, request_id: `r${requests}`, expires_at: '2099-01-01T00:00:00Z' });
  } });
  const editor = await fixture.open();
  await editor.evaluate(() => {
    const focus = window.focus.bind(window);
    window.focus = () => { document.body.dataset.focuses = String(Number(document.body.dataset.focuses ?? 0) + 1); focus(); };
  });
  await page.getByRole('link', { name: /Exercise B/ }).click();
  await expect.poll(() => requests).toBe(2);
  const detailsResponse = page.waitForResponse((response) => response.url().endsWith('/coder/workspaces/u-me/vscode'));
  await page.getByRole('link', { name: /Exercise A/ }).click();
  await detailsResponse;
  expect(requests).toBe(2);
  release();
  await expect.poll(() => committed.length).toBe(3);
  expect(committed).toEqual([ASSIGNMENT_A, 'bbbbbbbb-1111-4111-8111-111111111111', ASSIGNMENT_A]);
  await expect(editor.locator('body')).toHaveAttribute('data-focuses', '1');
  await expect(editor.getByRole('textbox', { name: 'Dirty Python' })).toHaveValue('preserve this unsaved buffer');
  expect(fixture.loads()).toBe(1);
  expect(page.context().pages()).toHaveLength(2);
});

test('concurrent first named launches share one provision before the workspace name is known', async ({ page, baseURL }) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  const fixture = await namedDashboard(page, baseURL, { workspaces: [], allowProvision: true });
  let provisions = 0;
  await page.route(`${API_ORIGIN}/coder/workspaces/provision`, async (route) => {
    provisions++;
    await held;
    return json(route, { user: { username: 'u-me' }, workspace: COURSE_WORKSPACE });
  });
  const popup = page.waitForEvent('popup');
  await page.getByRole('link', { name: /Exercise A/ }).click();
  const editor = await popup;
  await expect.poll(() => provisions).toBe(1);
  await page.getByRole('link', { name: /Exercise B/ }).click();
  release();
  await editor.waitForURL(fixture.url);
  expect(provisions).toBe(1);
  expect(fixture.launchRequests.map((request) => request.course_content_id)).toEqual(['bbbbbbbb-1111-4111-8111-111111111111']);
  expect(page.context().pages()).toHaveLength(2);
  await page.route(`${API_ORIGIN}/coder/workspaces`, (route) => json(route, { workspaces: [COURSE_WORKSPACE], count: 1 }));
  await page.getByRole('link', { name: /Exercise A/ }).click();
  await expect.poll(() => fixture.launchRequests.length).toBe(2);
  expect(fixture.loads()).toBe(1);
  expect(page.context().pages()).toHaveLength(2);
});

test('a verified named stopped workspace uses its existing lifecycle tab', async ({ page, baseURL }) => {
  const fixture = await namedDashboard(page, baseURL);
  const editor = await fixture.open();
  fixture.stop();
  await page.getByRole('link', { name: /Exercise B/ }).click();
  await expect.poll(() => fixture.starts.length).toBe(1);
  expect(page.url()).toContain('/dashboard');
  expect(page.context().pages()).toHaveLength(2);
  expect(editor.url()).toContain('/workspaces/launch');
  expect(fixture.provisions).toHaveLength(0);
});

for (const retained of ['custom-base', 'unverified'] as const) {
  test(`named workspace handles a ${retained} document without unsafe replacement`, async ({ page, baseURL }) => {
    const fixture = await namedDashboard(page, baseURL, {}, '/custom/authorized-editor/u-me/vscode/');
    const editor = await fixture.open();
    const original = await editor.evaluate(() => performance.timeOrigin);
    if (retained === 'unverified') {
      const elsewhere = new URL('/unrelated-document', baseURL).href;
      await page.context().route(elsewhere, (route) => route.fulfill({ contentType: 'text/html', body: '<textarea aria-label="Dirty Python">preserve this unsaved buffer</textarea>' }));
      await editor.goto(elsewhere);
    }
    const retainedDocument = await editor.evaluate(() => performance.timeOrigin);
    await page.getByRole('link', { name: /Exercise B/ }).click();
    await expect.poll(() => fixture.launchRequests.length).toBe(2);
    if (retained === 'custom-base') expect(await editor.evaluate(() => performance.timeOrigin)).toBe(original);
    else await page.waitForURL(fixture.url);
    expect(await editor.evaluate(() => performance.timeOrigin)).toBe(retainedDocument);
    await expect(editor.getByRole('textbox', { name: 'Dirty Python' })).toHaveValue('preserve this unsaved buffer');
    expect(editor.isClosed()).toBe(false);
    expect(page.context().pages()).toHaveLength(2);
  });
}


for (const isolation of ['user', 'template', 'workspace'] as const) {
  test(`named editor contexts isolate a different ${isolation}`, async ({ page, baseURL }) => {
    const fixture = await namedDashboard(page, baseURL);
    const original = await fixture.open();
    const document = await original.evaluate(() => performance.timeOrigin);
    const name = await original.evaluate(() => window.name);
    const otherUser = isolation === 'user' ? 'u-other' : 'u-me';
    const template = isolation === 'template' ? 'python-workspace' : 'vscode-workspace';
    const workspaceName = isolation === 'workspace' ? 'extra-lab' : isolation === 'template' ? 'python' : 'vscode';
    const otherUrl = new URL(`/coder/${otherUser}/${workspaceName}/`, baseURL).href;
    const workspace = { ...COURSE_WORKSPACE, id: 'w-other', owner_id: otherUser, owner_name: otherUser,
      name: workspaceName, template_name: template, template_display_name: isolation === 'template' ? 'Python' : 'VS Code' };
    const portal = await page.context().newPage();
    await setup(portal, [details({ status: 'running', ready: true })], { courseWorkspaces: true, userId: otherUser, workspaces: [workspace] });
    await portal.route(`${API_ORIGIN}/courses/*/workspace-settings`, (route) => json(route, {
      templates: [{ template_name: template, display_name: workspace.template_display_name, enabled: true, exists_in_coder: true }],
    }));
    await portal.context().route(otherUrl, (route) => route.fulfill({ contentType: 'text/html', body: '<h1>Other owned editor</h1>' }));
    await portal.context().route(`${API_ORIGIN}/coder/workspaces/${otherUser}/${workspaceName}**`, (route) => {
      if (route.request().method() === 'POST') return json(route, { ...route.request().postDataJSON(), request_id: 'other', expires_at: '2099-01-01T00:00:00Z' });
      return json(route, { ...details({ status: 'running', ready: true }), workspace, access_url: otherUrl, code_server_url: otherUrl });
    });
    await portal.goto('/dashboard');
    const popup = portal.waitForEvent('popup');
    if (isolation === 'workspace') {
      await portal.getByRole('combobox', { name: 'Choose a course' }).selectOption(COURSE_A);
      await portal.getByRole('button', { name: 'Open', exact: true }).click();
    } else {
      await portal.getByRole('button', { name: `Launch ${workspace.template_display_name} workspace`, exact: true }).first().click();
    }
    const other = await popup;
    await other.waitForURL(otherUrl);
    expect(await other.evaluate(() => window.name)).not.toBe(name);
    expect(await other.evaluate(() => window.name)).not.toBe('');
    expect(await original.evaluate(() => performance.timeOrigin)).toBe(document);
    await expect(original.getByRole('textbox', { name: 'Dirty Python' })).toHaveValue('preserve this unsaved buffer');
    expect(original.isClosed()).toBe(false);
    expect(page.context().pages()).toHaveLength(4);
  });
}


test('a blocked named editor popup keeps the exact target in the ordinary same-tab fallback', async ({ page, baseURL }) => {
  const fixture = await namedDashboard(page, baseURL);
  await page.evaluate(() => { window.open = () => null; });
  await page.getByRole('link', { name: /Exercise A/ }).click();
  await page.waitForURL(fixture.url);
  expect(fixture.launchRequests.map((request) => request.course_content_id)).toEqual([ASSIGNMENT_A]);
  expect(fixture.starts).toHaveLength(0);
  expect(fixture.provisions).toHaveLength(0);
  expect(page.context().pages()).toHaveLength(1);
});


test('an unmounted named launch cannot provision after its delayed workspace lookup returns', async ({ page, baseURL }) => {
  const fixture = await namedDashboard(page, baseURL, { workspaces: [], allowProvision: true });
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let lookups = 0;
  await page.route(`${API_ORIGIN}/coder/workspaces`, async (route) => {
    lookups++;
    await held;
    return json(route, { workspaces: [], count: 0 });
  });
  const popup = page.waitForEvent('popup');
  await page.getByRole('link', { name: /Exercise A/ }).click();
  const waiter = await popup;
  await expect.poll(() => lookups).toBeGreaterThan(0);
  await page.getByRole('link', { name: 'View Course', exact: true }).first().click();
  await page.waitForURL(`**/courses/${COURSE_A}`);
  release();
  // Let the held response and any request it causes settle after the real
  // client-side route change, which retains the original async JavaScript.
  await page.waitForLoadState('networkidle');
  expect(fixture.provisions).toHaveLength(0);
  expect(fixture.launchRequests).toHaveLength(0);
  await expect(waiter.getByText('Creating your workspace…')).toBeVisible();
  await waiter.close();
});
