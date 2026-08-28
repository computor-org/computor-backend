import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * The Details tab edits the template's manifest — display name, description,
 * icon — and the page offers Delete for templates created here. Two rules the
 * UI has to get right: a repo-managed template is asked before its first write
 * detaches it from repo syncing (a clone never is), and only a clone can be
 * deleted (a repo-shipped one would just be seeded again).
 */

const API_ORIGIN = 'http://localhost:8000';

const USER = {
  id: 'u-maintainer', username: 'maintainer', email: 'maintainer@example.org',
  given_name: 'Mina', family_name: 'Maintainer',
  user_roles: [{ role_id: '_workspace_maintainer' }],
};

const managed = {
  template_name: 'vscode-workspace', dir_name: 'vscode', display_name: 'VS Code',
  description: 'VS Code in the browser', icon: '/icon/code.svg',
  image_name: 'computor-workspace-vscode', cloned_from: null, created_at: null,
  customized: false,
};

const clone = {
  template_name: 'py-ds-workspace', dir_name: 'py-ds', display_name: 'Python DS',
  description: null, icon: 'https://example.org/py.svg',
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

  const updates: unknown[] = [];
  const deletes: string[] = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);

    const meta = path.startsWith('/coder/admin/templates/vscode-workspace/') ? managed
      : path.startsWith('/coder/admin/templates/py-ds-workspace/') ? clone : null;
    if (meta && path.endsWith('/metadata')) {
      if (method === 'PUT') {
        const body = request.postDataJSON();
        updates.push(body);
        return json(route, {
          ...meta, ...body, customized: true,
          coder_updated: true, message: 'Saved and applied to Coder.',
        });
      }
      return json(route, meta);
    }
    if (meta && path.endsWith('/files')) {
      return json(route, {
        template_name: meta.template_name, dir_name: meta.dir_name,
        customized: meta.customized, cloned_from: meta.cloned_from,
        files: [{ name: 'main.tf', content: 'x = 1' }],
      });
    }
    if (meta && path.endsWith('/variables')) {
      return json(route, {
        template_name: meta.template_name, dir_name: meta.dir_name,
        customized: meta.customized, variables: [],
      });
    }
    if (path === '/coder/admin/templates/settings') return json(route, { settings: [] });
    if (path === '/coder/admin/templates/py-ds-workspace' && method === 'DELETE') {
      deletes.push(path);
      return json(route, {
        success: true, message: "Template 'py-ds-workspace' deleted.",
        coder_deleted: true, settings_deleted: true,
      });
    }
    if (path === '/coder/admin/templates/catalog') {
      return json(route, { templates_dir_available: true, templates: [] });
    }
    return json(route, {});
  });
  return { updates, deletes };
}

test('saving a managed template asks before customizing it', async ({ page }) => {
  const { updates } = await setup(page);
  await page.goto('/workspaces/admin/templates/vscode-workspace?tab=details');

  await expect(page.getByText('managed', { exact: true })).toBeVisible();
  const save = page.getByRole('button', { name: 'Save details' });
  await expect(save).toBeDisabled(); // nothing changed yet

  await page.getByLabel('Display name').fill('Code');
  await save.click();
  await expect(page.getByText('Customize this template?')).toBeVisible();
  expect(updates).toEqual([]); // not before the answer

  await page.getByRole('button', { name: 'Save & customize' }).click();
  await expect.poll(() => updates.length).toBe(1);
  expect(updates[0]).toEqual({
    display_name: 'Code', description: 'VS Code in the browser', icon: '/icon/code.svg',
  });
});

test('saving a clone needs no warning', async ({ page }) => {
  const { updates } = await setup(page);
  await page.goto('/workspaces/admin/templates/py-ds-workspace?tab=details');

  await expect(page.getByText('cloned from vscode').first()).toBeVisible();
  await expect(page.getByLabel('Image')).toHaveValue('computor-workspace-py-ds');

  await page.getByLabel('Display name').fill('Python DS 2');
  await page.getByRole('button', { name: 'Save details' }).click();
  await expect.poll(() => updates.length).toBe(1);
  await expect(page.getByText('Customize this template?')).toHaveCount(0);
  expect(updates[0]).toEqual({ display_name: 'Python DS 2', description: null, icon: 'https://example.org/py.svg' });
});

test('Delete exists for a clone only and confirms by name', async ({ page }) => {
  const { deletes } = await setup(page);

  await page.goto('/workspaces/admin/templates/vscode-workspace');
  await expect(page.getByRole('heading', { name: 'vscode-workspace' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Delete template' })).toHaveCount(0);

  await page.goto('/workspaces/admin/templates/py-ds-workspace');
  await page.getByRole('button', { name: 'Delete template' }).click();
  const confirm = page.getByRole('button', { name: 'Delete', exact: true });
  await expect(confirm).toBeDisabled();
  await page.getByLabel(/to confirm/).fill('py-ds-workspace');
  await confirm.click();

  await expect(page).toHaveURL(/\/workspaces\/admin\?tab=templates$/);
  expect(deletes).toEqual(['/coder/admin/templates/py-ds-workspace']);
});

test("a clone's Files tab offers no Restore managed", async ({ page }) => {
  await setup(page);
  await page.goto('/workspaces/admin/templates/py-ds-workspace?tab=files');

  await expect(page.getByRole('button', { name: 'main.tf', exact: true })).toBeVisible();
  await expect(page.getByText('cloned from vscode').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Restore managed' })).toHaveCount(0);
});
