import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Creating a template = copying an existing one. The form owns two things the
 * backend would otherwise only reject after the fact: which templates can be
 * copied (those with a directory here) and what the key expands to.
 */

const API_ORIGIN = 'http://localhost:8000';

const USER = {
  id: 'u-maintainer', username: 'maintainer', email: 'maintainer@example.org',
  given_name: 'Mina', family_name: 'Maintainer',
  user_roles: [{ role_id: '_workspace_maintainer' }],
};

const catalog = {
  templates_dir_available: true,
  templates: [
    {
      dir_name: 'vscode', name: 'vscode-workspace', display_name: 'VS Code',
      description: 'VS Code in the browser', icon: '/icon/code.svg',
      image_name: 'computor-workspace-vscode', deployed: true,
      template_id: 't-vscode', active_version_id: 'v2', enabled: true,
      customized: false, workspace_count: 2, running_workspace_count: 1,
    },
    {
      dir_name: 'matlab', name: 'matlab-workspace', display_name: 'MATLAB',
      description: 'MATLAB in the browser', icon: null,
      image_name: 'computor-workspace-matlab', deployed: false,
      template_id: null, active_version_id: null, enabled: true,
      customized: false, workspace_count: 0, running_workspace_count: 0,
    },
    {
      dir_name: null, name: 'legacy-workspace', display_name: 'Legacy',
      description: null, icon: null, image_name: null, deployed: true,
      template_id: 't-legacy', active_version_id: 'l1', enabled: false,
      customized: false, workspace_count: 0, running_workspace_count: 0,
    },
  ],
};

const createdMeta = {
  template_name: 'py-ds-workspace', dir_name: 'py-ds', display_name: 'Python DS',
  description: 'Data science', icon: 'https://example.org/py.svg',
  image_name: 'computor-workspace-py-ds', cloned_from: 'vscode',
  created_at: '2026-08-28T10:00:00+00:00', customized: true,
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: ['_workspace_maintainer'],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  const created: unknown[] = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path === '/coder/admin/templates/catalog') return json(route, catalog);
    if (path === '/coder/admin/templates' && request.method() === 'POST') {
      created.push(request.postDataJSON());
      return json(route, createdMeta, 201);
    }
    // The page the create redirects to.
    if (path === '/coder/admin/templates/py-ds-workspace/metadata') return json(route, createdMeta);
    if (path === '/coder/admin/templates/settings') return json(route, { settings: [] });
    if (path === '/coder/admin/templates/py-ds-workspace/variables') {
      return json(route, { template_name: 'py-ds-workspace', dir_name: 'py-ds', customized: true, variables: [] });
    }
    return json(route, {});
  });
  return created;
}

test('?from= preselects the source and the derived names follow the key', async ({ page }) => {
  await setup(page);
  await page.goto('/workspaces/admin/templates/create?from=matlab');

  await expect(page.getByLabel('Copy from')).toHaveValue('matlab');
  // Live in Coder without a directory: nothing to copy, so not offered.
  await expect(page.getByRole('option', { name: /Legacy/ })).toHaveCount(0);

  await page.getByLabel('Key').fill('py-ds');
  await expect(page.getByLabel('Directory')).toHaveValue('py-ds');
  await expect(page.getByLabel('Coder template name')).toHaveValue('py-ds-workspace');
  await expect(page.getByLabel('Image')).toHaveValue('computor-workspace-py-ds');
});

test('a bad key keeps Create disabled and says what is wrong', async ({ page }) => {
  await setup(page);
  await page.goto('/workspaces/admin/templates/create');
  const create = page.getByRole('button', { name: 'Create template' });

  await expect(page.getByLabel('Copy from')).toHaveValue('vscode');
  await expect(create).toBeDisabled(); // no key yet

  await page.getByLabel('Key').fill('Py_DS');
  await expect(page.getByText('Lowercase letters, digits and inner hyphens only.')).toBeVisible();
  await expect(create).toBeDisabled();

  await page.getByLabel('Key').fill('py-workspace');
  await expect(page.getByText("Leave out '-workspace'")).toBeVisible();
  await expect(create).toBeDisabled();

  await page.getByLabel('Key').fill('py-ds');
  await expect(create).toBeEnabled();
});

test('creating sends source, key and display fields, then opens the new template', async ({ page }) => {
  const created = await setup(page);
  await page.goto('/workspaces/admin/templates/create?from=vscode');

  // Display fields start out as the source's until edited.
  await expect(page.getByLabel('Display name')).toHaveValue('VS Code (copy)');
  await expect(page.getByLabel('Description')).toHaveValue('VS Code in the browser');

  await page.getByLabel('Key').fill('py-ds');
  await page.getByLabel('Display name').fill('Python DS');
  await page.getByLabel('Description').fill('Data science');
  await page.getByLabel('Icon').fill('https://example.org/py.svg');
  await page.getByRole('button', { name: 'Create template' }).click();

  await expect(page).toHaveURL(/\/workspaces\/admin\/templates\/py-ds-workspace\?tab=details$/);
  expect(created).toEqual([{
    source: 'vscode', key: 'py-ds', display_name: 'Python DS',
    description: 'Data science', icon: 'https://example.org/py.svg',
  }]);
  await expect(page.getByText('cloned from vscode').first()).toBeVisible();
});
