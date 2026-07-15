import { test, expect, type Page, type Route } from '@playwright/test';

const API_ORIGIN = 'http://localhost:8000';

const USER = {
  id: 'u-maintainer',
  username: 'maintainer',
  email: 'maintainer@example.org',
  given_name: 'Mina',
  family_name: 'Maintainer',
  user_roles: [{ role_id: '_workspace_maintainer' }],
};

const fleet = {
  healthy: true,
  version: '2.29.4+7dfaa60',
  workspace_count: 2,
  templates: [
    {
      id: 't-vscode',
      name: 'vscode-workspace',
      display_name: 'VS Code',
      active_version_id: 'version-v2',
      workspace_count: 1,
      current_count: 0,
      outdated_count: 1,
      running_outdated_count: 1,
      scheduled_on_start_count: 0,
      actionable_count: 1,
      rollout_state: 'ready',
    },
    {
      id: 't-bash',
      name: 'bash-workspace',
      display_name: 'Bash Terminal',
      active_version_id: 'version-b2',
      workspace_count: 1,
      current_count: 0,
      outdated_count: 1,
      running_outdated_count: 0,
      scheduled_on_start_count: 1,
      actionable_count: 0,
      rollout_state: 'scheduled_on_start',
    },
  ],
};

const workspaces = {
  count: 2,
  workspaces: [
    {
      id: 'w1', name: 'code', owner_id: 'u1', owner_name: 'alice',
      template_id: 't-vscode', template_name: 'vscode-workspace',
      template_display_name: 'VS Code', template_version_id: 'version-v1',
      template_version_name: 'old-code', latest_build_transition: 'start',
      latest_build_status: 'succeeded', automatic_updates: 'always',
    },
    {
      id: 'w2', name: 'shell', owner_id: 'u2', owner_name: 'bob',
      template_id: 't-bash', template_name: 'bash-workspace',
      template_display_name: 'Bash Terminal', template_version_id: 'version-b1',
      template_version_name: 'old-bash', latest_build_transition: 'stop',
      latest_build_status: 'stopped', automatic_updates: 'always',
    },
  ],
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(
  page: Page,
  options: { role?: '_workspace_user' | '_workspace_maintainer'; tasks?: unknown[] } = {},
) {
  const role = options.role ?? '_workspace_maintainer';
  await page.addInitScript(({ role, user }) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id,
      username: user.username,
      email: user.email,
      givenName: user.given_name,
      familyName: user.family_name,
      role: 'user',
      systemRoles: [role],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, { role, user: USER });

  const pushedBodies: unknown[] = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path === '/coder/health') return json(route, { healthy: true, version: fleet.version });
    if (path === '/coder/workspaces') return json(route, workspaces);
    if (path === '/coder/workspaces/all') return json(route, workspaces);
    if (path === '/coder/admin/fleet') return json(route, fleet);
    if (path === '/coder/admin/tasks') return json(route, { tasks: options.tasks ?? [] });
    if (path === '/coder/admin/templates/push' && request.method() === 'POST') {
      pushedBodies.push(request.postDataJSON());
      return json(route, {
        workflow_id: 'push-new', task_name: 'push_coder_templates', status: 'submitted',
      });
    }
    return json(route, {});
  });
  return pushedBodies;
}

test('ordinary workspace users do not see the raw Coder version', async ({ page }) => {
  await setup(page, { role: '_workspace_user' });
  await page.goto('/workspaces');
  await expect(page.getByText('Coder healthy', { exact: true })).toBeVisible();
  await expect(page.getByText(/2\.29\.4/)).not.toBeVisible();
});

test('fleet supports template selection and readiness-aware actions', async ({ page }) => {
  const pushedBodies = await setup(page);
  await page.goto('/workspaces/admin?tab=fleet');

  await expect(page.getByText('Coder healthy · v2.29.4+7dfaa60')).toBeVisible();
  await expect(page.getByText('Ready to roll out')).toBeVisible();
  await expect(page.getByText('Scheduled', { exact: true })).toBeVisible();

  await page.getByLabel('Select VS Code').evaluate((element: HTMLInputElement) => element.click());
  await page.getByLabel('Select Bash Terminal').evaluate((element: HTMLInputElement) => element.click());
  await page.getByRole('button', { name: 'Build & push selected (2)' }).click();

  await expect.poll(() => pushedBodies.length).toBe(1);
  expect(pushedBodies[0]).toEqual({
    templates: ['vscode-workspace', 'bash-workspace'],
    build_images: true,
    image_tag: null,
  });
});

test('fleet restores phase and per-template progress after reload', async ({ page }) => {
  await setup(page, {
    tasks: [{
      task_id: 'push-running', workflow_id: 'push-running', task_name: 'push_coder_templates',
      status: 'started', created_at: '2026-07-15T10:00:00Z',
      progress: {
        phase: 'building', operation_status: 'running', completed: 0, total: 2,
        image_tag: 'v20260715-100000',
        templates: [
          { key: 'vscode', name: 'vscode-workspace', display_name: 'VS Code', status: 'running', phase: 'building' },
          { key: 'bash', name: 'bash-workspace', display_name: 'Bash Terminal', status: 'pending', phase: 'queued' },
        ],
      },
    }],
  });
  await page.goto('/workspaces/admin?tab=fleet');

  await expect(page.getByText('Build & push · building')).toBeVisible();
  await expect(page.getByText('v20260715-100000')).toBeVisible();
  await expect(
    page.getByRole('row').filter({ hasText: 'vscode-workspace' }).getByText('Building', { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Build & push selected/ })).toBeDisabled();
});
