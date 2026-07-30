import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * What a user is told about the workspace types they can have.
 *
 * Nothing is deployed to Coder automatically, so between an admin picking a
 * type and a user being able to use it there is a build Coder knows nothing
 * about — and a course can go on offering a type that was never deployed at
 * all. Both used to be invisible: the type was simply missing from the choice,
 * or (on a course page) was a normal-looking button whose click came back
 * "Template 'bash-workspace' is not yet available".
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = 'c-1';

const USER = {
  id: 'u-me',
  username: 'me',
  email: 'me@example.org',
  given_name: 'Wanda',
  family_name: 'Workspace',
  user_roles: [{ role_id: '_workspace_user' }],
};

const VSCODE = { id: 't-vscode', name: 'vscode-workspace', display_name: 'VS Code' };

/** One entry of GET /coder/templates' `preparing`. */
function building(name: string, display: string, phase = 'building', status = 'running') {
  return {
    name,
    display_name: display,
    description: null,
    icon: null,
    status,
    phase,
    deployed: false,
    task_name: 'push_coder_templates',
  };
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(
  page: Page,
  options: {
    templates?: unknown[];
    preparing?: unknown[];
    workspaces?: unknown[];
    systemRoles?: string[];
    courseTemplates?: unknown[];
  } = {},
) {
  const systemRoles = options.systemRoles ?? ['_workspace_user'];
  const user = { ...USER, user_roles: systemRoles.map((role_id) => ({ role_id })) };

  await page.addInitScript(([who, roles]) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: (who as typeof USER).id,
      username: (who as typeof USER).username,
      email: (who as typeof USER).email,
      givenName: (who as typeof USER).given_name,
      familyName: (who as typeof USER).family_name,
      role: 'user',
      systemRoles: roles as string[],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, [user, systemRoles] as const);

  const provisioned: unknown[] = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;

    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) {
      // A student of the course: what gates the course page's workspace card.
      return json(route, { is_admin: false, course: { [COURSE_ID]: ['_student'] } });
    }
    if (path.endsWith('/user')) return json(route, user);
    if (path.startsWith('/messages')) return json(route, []);

    if (path === '/coder/health') return json(route, { healthy: true, version: '2.29.4' });
    if (path === '/coder/templates') {
      return json(route, {
        templates: options.templates ?? [],
        count: (options.templates ?? []).length,
        preparing: options.preparing ?? [],
      });
    }
    if (path === '/coder/workspaces') {
      return json(route, {
        workspaces: options.workspaces ?? [],
        count: (options.workspaces ?? []).length,
      });
    }
    if (path === `/courses/${COURSE_ID}/workspace-settings`) {
      return json(route, {
        course_id: COURSE_ID,
        templates: options.courseTemplates ?? [],
        lecturer_provision_enabled: false,
        can_manage: false,
      });
    }
    if (path === '/coder/workspaces/provision' && request.method() === 'POST') {
      provisioned.push(request.postDataJSON());
      return json(route, {
        user: { id: 'u-me', username: 'u-me', email: USER.email },
        workspace: { id: 'w1', name: 'vscode', owner_id: 'u-me', template_id: 't-vscode' },
        created_user: false,
        created_workspace: true,
      });
    }
    return json(route, {});
  });

  return provisioned;
}

function card(page: Page, name: string) {
  return page.getByRole('button').filter({ hasText: name });
}

test('a type that is still being built is shown, with the stage it has reached', async ({ page }) => {
  await setup(page, { templates: [VSCODE], preparing: [building('matlab-workspace', 'MATLAB')] });

  await page.goto('/workspaces');

  // The one Coder has is a normal choice...
  await expect(card(page, 'VS Code')).toBeEnabled();
  // ...and the one being built is present rather than silently missing, says
  // what it is doing, and cannot be clicked into a 503.
  const matlab = card(page, 'MATLAB');
  await expect(matlab).toBeVisible();
  await expect(matlab).toBeDisabled();
  await expect(matlab).toContainText('Building image');
  await expect(matlab).toHaveAttribute('title', /being prepared/i);
});

test('a deployment that failed says so instead of the type disappearing', async ({ page }) => {
  await setup(page, {
    templates: [VSCODE],
    preparing: [building('matlab-workspace', 'MATLAB', 'building', 'failed')],
  });

  await page.goto('/workspaces');

  const matlab = card(page, 'MATLAB');
  await expect(matlab).toBeDisabled();
  await expect(matlab).toContainText('Image build failed');
});

test('a fresh deployment tells a maintainer where to deploy a type', async ({ page }) => {
  await setup(page, { systemRoles: ['_workspace_maintainer'] });

  await page.goto('/workspaces');

  await expect(page.getByText('No workspace types are available to you yet.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Administration → Templates' })).toBeVisible();
});

test('a card for a type you already have opens it instead of creating another', async ({ page }) => {
  const provisioned = await setup(page, {
    templates: [VSCODE],
    workspaces: [{
      id: 'w1', name: 'vscode', owner_id: 'u-me', owner_name: 'u-me',
      template_id: 't-vscode', template_name: 'vscode-workspace',
      latest_build_transition: 'start', latest_build_status: 'succeeded',
    }],
  });

  await page.goto('/workspaces');

  const vscode = card(page, 'VS Code').first();
  await expect(vscode).toContainText('Open workspace');

  const popup = page.waitForEvent('popup');
  await vscode.click();
  const tab = await popup;

  // Straight to the launch page for the workspace that exists — no second
  // provisioning round-trip for a user who can only ever have one of these.
  await expect(tab).toHaveURL(/\/workspaces\/launch\?owner=u-me&name=vscode/);
  expect(provisioned).toHaveLength(0);
});

test('a maintainer can still name a workspace, without leaving the page', async ({ page }) => {
  const provisioned = await setup(page, {
    templates: [VSCODE],
    systemRoles: ['_workspace_maintainer'],
  });

  await page.goto('/workspaces');
  await page.getByRole('button', { name: 'New workspace…' }).click();

  await page.getByRole('textbox').fill('exam-2026');
  const popup = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Create', exact: true }).click();
  await popup;

  expect(provisioned).toEqual([
    { template: 'vscode-workspace', workspace_name: 'exam-2026' },
  ]);
});

// --- course pages ------------------------------------------------------------

test('a course does not offer a type the server does not have', async ({ page }) => {
  const provisioned = await setup(page, {
    templates: [VSCODE],
    courseTemplates: [
      {
        template_name: 'vscode-workspace', enabled: true, display_name: 'VS Code',
        exists_in_coder: true, template_allow_root: false, template_allow_internet: true,
        effective_allow_root: false, effective_allow_internet: true,
      },
      {
        // The course still asks for it; nobody ever deployed it.
        template_name: 'bash-workspace', enabled: true, display_name: 'Terminal',
        exists_in_coder: false, template_allow_root: false, template_allow_internet: true,
        effective_allow_root: false, effective_allow_internet: true,
      },
    ],
  });

  await page.goto(`/courses/${COURSE_ID}`);

  const bash = card(page, 'Terminal');
  await expect(bash).toBeVisible();
  await expect(bash).toBeDisabled();
  await expect(bash).toHaveAttribute('title', /not been set up/i);

  // The old behaviour: a click that travelled to the server to be refused.
  await bash.click({ force: true });
  await page.waitForTimeout(500);
  expect(provisioned).toHaveLength(0);
});

test('a course shows the build a student is waiting on', async ({ page }) => {
  await setup(page, {
    templates: [VSCODE],
    preparing: [building('matlab-workspace', 'MATLAB', 'pushing')],
    courseTemplates: [
      {
        template_name: 'matlab-workspace', enabled: true, display_name: 'MATLAB',
        exists_in_coder: false, template_allow_root: false, template_allow_internet: true,
        effective_allow_root: false, effective_allow_internet: true,
      },
    ],
  });

  await page.goto(`/courses/${COURSE_ID}`);

  const matlab = card(page, 'MATLAB');
  await expect(matlab).toBeDisabled();
  // The words the administration page uses for the same run.
  await expect(matlab).toContainText('Pushing template');
});
