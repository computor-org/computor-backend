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

/**
 * The catalog's whole reason to exist: 'matlab' is on disk but was never built,
 * so nothing that reads Coder can see it. 'legacy' is the mirror case — live in
 * Coder with no directory, so there is no image to rebuild.
 */
const catalog = {
  templates_dir_available: true,
  templates: [
    {
      dir_name: 'vscode', name: 'vscode-workspace', display_name: 'VS Code',
      description: 'VS Code in the browser', icon: '/icon/code.svg',
      image_name: 'computor-workspace-vscode', deployed: true,
      template_id: 't-vscode', active_version_id: 'v2', enabled: true,
      customized: false, workspace_count: 2,
      running_workspace_count: 1,
    },
    {
      dir_name: 'matlab', name: 'matlab-workspace', display_name: 'MATLAB',
      description: 'MATLAB in the browser', icon: null,
      image_name: 'computor-workspace-matlab', deployed: false,
      template_id: null, active_version_id: null, enabled: true,
      customized: false, workspace_count: 0,
      running_workspace_count: 0,
    },
    {
      dir_name: null, name: 'legacy-workspace', display_name: 'Legacy',
      description: null, icon: null, image_name: null, deployed: true,
      template_id: 't-legacy', active_version_id: 'l1', enabled: false,
      customized: false, workspace_count: 0,
      running_workspace_count: 0,
    },
  ],
};

const settings = {
  settings: [
    {
      template_name: 'vscode-workspace', enabled: true, memory_mb: 4096,
      cpu_shares: null, max_running_workspaces: 10, allow_root: false,
      allow_internet: true, template_variables: {},
    },
  ],
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

function setup(page: Page, options: { tasks?: unknown[] } = {}) {
  return setupWith(page, catalog, options);
}

async function setupWith(
  page: Page,
  body: typeof catalog,
  options: { tasks?: unknown[] } = {},
) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id,
      username: user.username,
      email: user.email,
      givenName: user.given_name,
      familyName: user.family_name,
      role: 'user',
      systemRoles: ['_workspace_maintainer'],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  const pushedBodies: unknown[] = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path === '/coder/admin/templates/catalog') return json(route, body);
    if (path === '/coder/admin/templates/settings') return json(route, settings);
    if (path === '/coder/admin/tasks') return json(route, { tasks: options.tasks ?? [] });
    if (path === '/coder/admin/templates/push' && request.method() === 'POST') {
      pushedBodies.push(request.postDataJSON());
      return json(route, {
        workflow_id: 'push-matlab', task_name: 'push_coder_templates', status: 'submitted',
      });
    }
    return json(route, {});
  });
  return pushedBodies;
}

function row(page: Page, name: string) {
  return page.getByRole('row').filter({ hasText: name });
}

test('the catalog lists templates that were never deployed', async ({ page }) => {
  await setup(page);
  await page.goto('/workspaces/admin?tab=templates');

  await expect(row(page, 'vscode-workspace').getByText('Available')).toBeVisible();
  await expect(row(page, 'matlab-workspace').getByText('Not deployed')).toBeVisible();
  await expect(row(page, 'legacy-workspace').getByText('Disabled')).toBeVisible();
});

test('a fresh deployment is told to pick, not left reading empty rows', async ({ page }) => {
  // Nothing is deployed automatically, so this is what a brand-new system sees.
  const pushedBodies = await setupWith(page, {
    templates_dir_available: true,
    templates: catalog.templates
      .filter((t) => t.dir_name)
      .map((t) => ({ ...t, deployed: false, template_id: null, active_version_id: null })),
  });
  await page.goto('/workspaces/admin?tab=templates');

  await expect(page.getByText('No workspace templates are deployed yet')).toBeVisible();

  // Pick one of the two, and only that one is built.
  await page.getByLabel('Select MATLAB').check();
  await page.getByRole('button', { name: 'Deploy selected (1)' }).click();

  await expect.poll(() => pushedBodies.length).toBe(1);
  expect(pushedBodies[0]).toEqual({ templates: ['matlab'], build_images: true });
});

test('deploying an undeployed template builds and pushes just that one', async ({ page }) => {
  const pushedBodies = await setup(page);
  await page.goto('/workspaces/admin?tab=templates');

  await row(page, 'matlab-workspace').getByRole('button', { name: 'Deploy', exact: true }).click();

  await expect.poll(() => pushedBodies.length).toBe(1);
  // The DIRECTORY name, which is what the build activity resolves against.
  expect(pushedBodies[0]).toEqual({ templates: ['matlab'], build_images: true });

  // A template live in Coder with no directory has no image to rebuild.
  await expect(row(page, 'legacy-workspace').getByRole('button', { name: 'Deploy', exact: true }))
    .toHaveCount(0);
});

test('a template cannot be enabled before it is deployed', async ({ page }) => {
  await setup(page);
  await page.goto('/workspaces/admin?tab=templates');

  await expect(
    row(page, 'vscode-workspace').getByRole('switch'),
  ).toHaveAttribute('aria-checked', 'true');
  await expect(row(page, 'legacy-workspace').getByRole('switch'))
    .toHaveAttribute('aria-checked', 'false');
  // Undeployed: no switch at all rather than one stuck in the ON position for
  // something users cannot pick (a template with no settings row is "enabled").
  await expect(row(page, 'matlab-workspace').getByRole('switch')).toHaveCount(0);
});

test('a running build reports its stages as a list with progress bars', async ({ page }) => {
  await setup(page, {
    tasks: [{
      task_id: 'push-matlab', workflow_id: 'push-matlab', task_name: 'push_coder_templates',
      status: 'started', created_at: '2026-07-30T10:00:00Z',
      progress: {
        phase: 'building', operation_status: 'running', completed: 0, total: 2,
        image_tag: 'v20260730-100000',
        templates: [
          { key: 'matlab', name: 'matlab-workspace', display_name: 'MATLAB', status: 'running', phase: 'building' },
          { key: 'vscode', name: 'vscode-workspace', display_name: 'VS Code', status: 'pending', phase: 'queued' },
        ],
      },
    }],
  });
  await page.goto('/workspaces/admin?tab=templates');

  await expect(page.getByText('Build & push · building')).toBeVisible();

  const stages = page.getByRole('listitem');
  await expect(stages.filter({ hasText: 'MATLAB' }).getByText('Building image')).toBeVisible();
  await expect(stages.filter({ hasText: 'VS Code' }).getByText('Queued')).toBeVisible();

  // One bar for the run plus one per template — the stage, not just a spinner.
  await expect(page.getByRole('progressbar')).toHaveCount(3);
  await expect(
    page.getByRole('progressbar', { name: 'MATLAB: Building image' }),
  ).toHaveAttribute('aria-valuenow', '30');
});
