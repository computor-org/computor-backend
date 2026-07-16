import { test, expect, type Page, type Route } from '@playwright/test';

const API_ORIGIN = 'http://localhost:8000';
const WORKSPACE_URL = 'http://localhost:8080/coder/u-me/code/';

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
}: {
  status: string;
  lifecycle?: string | null;
  ready?: boolean;
  withUrl?: boolean;
}) {
  return {
    workspace: {
      id: 'w1', name: 'code', owner_id: 'u-me', owner_name: 'u-me',
      template_id: 't-vscode', template_name: 'vscode-workspace',
      latest_build_status: status === 'running' ? 'succeeded' : status,
    },
    status,
    access_url: withUrl && status === 'running' ? WORKSPACE_URL : null,
    code_server_url: withUrl && status === 'running' ? WORKSPACE_URL : null,
    agent_lifecycle: lifecycle ?? null,
    ready: ready ?? false,
    health: true,
    resources: {},
  };
}

/**
 * Serve workspace-details responses. Pass an array to script one per poll (the
 * last repeating), or a supplier for tests that need to control exactly when the
 * status changes — the page re-fetches on mount as well as on the poll timer, so
 * a fixed array cannot pin down a specific poll. Returns the start-build
 * requests the page issued.
 */
async function setup(page: Page, source: unknown[] | (() => unknown)) {
  const next = typeof source === 'function' ? source : undefined;
  const sequence = typeof source === 'function' ? [] : source;
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: ['_workspace_user'],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  const starts: string[] = [];
  let poll = 0;

  // The workspace itself is not part of this app; stub it so the redirect lands
  // somewhere assertable instead of a connection error.
  await page.route(`${WORKSPACE_URL}**`, (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: '<h1>editor</h1>' }),
  );

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);

    if (path === '/coder/workspaces/u-me/code/start' && request.method() === 'POST') {
      starts.push(path);
      return json(route, { success: true, message: 'starting' });
    }
    if (path === '/coder/workspaces/u-me/code') {
      if (next) return json(route, next());
      const body = sequence[Math.min(poll, sequence.length - 1)];
      poll += 1;
      return json(route, body);
    }
    return json(route, {});
  });

  return { starts };
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

  // It must hold on the spinner while not ready...
  await expect(page.getByText('Almost there — waiting for the editor…')).toBeVisible();
  expect(page.url()).not.toContain('8080');

  // ...and then open the workspace once the agent reports ready.
  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });
  await expect(page.getByRole('heading', { name: 'editor' })).toBeVisible();
});

test('does not redirect while the workspace is merely running', async ({ page }) => {
  // ready never arrives: the page must keep waiting, not open a 502.
  await setup(page, [details({ status: 'running', lifecycle: 'starting', ready: false })]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');
  await expect(page.getByText('Almost there — waiting for the editor…')).toBeVisible();

  await page.waitForTimeout(5_000);
  expect(page.url()).toContain('/workspaces/launch');
});

test('opens anyway when the agent gave up on its startup script', async ({ page }) => {
  await setup(page, [details({ status: 'running', lifecycle: 'start_timeout', ready: false })]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');

  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });
});

test('starts a stopped workspace exactly once, then opens it', async ({ page }) => {
  const { starts } = await setup(page, [
    details({ status: 'stopped' }),
    details({ status: 'stopped' }),
    details({ status: 'starting' }),
    details({ status: 'running', lifecycle: 'ready', ready: true }),
  ]);

  await page.goto('/workspaces/launch?owner=u-me&name=code');
  await page.waitForURL(WORKSPACE_URL, { timeout: 20_000 });

  // The guard: repeated polls of a stopped workspace must not fire a build each tick.
  expect(starts).toHaveLength(1);
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
    }),
  );
  await page.route(`${API_ORIGIN}/coder/workspaces/provision`, (route) =>
    json(route, {
      user: { id: 'u-me', username: 'u-me', email: USER.email },
      // A self-provisioner's requested name is discarded and re-derived server
      // side, so the launch tab must follow this, not any client-side guess.
      workspace: { id: 'w1', name: 'vscode', owner_id: 'u-me', template_id: 't-vscode' },
      created_user: false,
      created_workspace: true,
    }),
  );

  await page.goto('/workspaces/create');

  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Create' }).click();
  const launchTab = await popup;

  await launchTab.waitForURL(/\/workspaces\/launch\?/);
  expect(launchTab.url()).toContain('owner=u-me');
  expect(launchTab.url()).toContain('name=vscode');

  // The tab the user was on goes back to the list rather than following along.
  await page.waitForURL(/\/workspaces$/);
});
