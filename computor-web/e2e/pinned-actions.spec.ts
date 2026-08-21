import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * A surface with one commit action keeps it reachable without scrolling.
 *
 * Each of these had its Save at the bottom of a page-length scroll, so it left
 * the screen exactly when the form grew long enough to need it. Measured
 * against HEAD before the fix: Save settings 1152px, Publish version 1875px and
 * Save configuration 1144px, all in an 800px viewport.
 */

const API = 'http://localhost:8000';
const USER = {
  id: 'u-a', username: 'a', email: 'a@e.org', given_name: 'A', family_name: 'A',
  user_roles: [{ role_id: '_admin' }, { role_id: '_workspace_maintainer' }],
};
const json = (r: Route, b: unknown) =>
  r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(b) });

const many = (n: number, f: (i: number) => unknown) => Array.from({ length: n }, (_, i) => f(i));

const ROUTES: Record<string, unknown> = {
  // Enough rows that each form is longer than the viewport — the case that broke.
  '/coder/admin/templates/settings': {
    settings: many(8, (i) => ({
      template_name: `t${i}-workspace`, enabled: true, memory_mb: 4096, cpu_shares: null,
      max_running_workspaces: 10, allow_root: false, allow_internet: true,
      template_variables: { A: '1', B: '2', C: '3' },
    })),
  },
  '/coder/admin/templates/catalog': {
    templates_dir_available: true,
    templates: [{ dir_name: 'vscode', name: 'vscode-workspace', display_name: 'VS Code',
      description: null, icon: null, image_name: 'i', deployed: true, template_id: 't',
      active_version_id: 'v', enabled: true, customized: false, workspace_count: 0,
      running_workspace_count: 0 }],
  },
  '/consent/policy-versions': many(14, (i) => ({
    id: `v${i}`, version: `1.${i}`, title: `Notice 1.${i}`,
    effective_at: new Date().toISOString(), is_current: i === 13,
    created_at: new Date().toISOString(),
  })),
  '/courses/c1/workspace-settings': {
    course_id: 'c1', allow_root: false, allow_internet: true,
    home_mode: 'persistent', lecturer_may_provision: true,
    templates: [{ template_name: 'vscode-workspace' }],
    available: many(8, (i) => ({ name: `t${i}-workspace`, display_name: `T${i}`,
      description: `template ${i}`, icon: null })),
  },
};

async function seed(page: Page) {
  await page.addInitScript((u) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: u.id, username: u.username, email: u.email, givenName: u.given_name,
      familyName: u.family_name, role: 'admin',
      systemRoles: ['_admin', '_workspace_maintainer'],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);
  await page.route(`${API}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: true });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path in ROUTES) return json(route, ROUTES[path]);
    return json(route, {});
  });
  await page.setViewportSize({ width: 1280, height: 800 });
}

/** True when the button is fully within the viewport at the initial scroll position. */
async function isOnScreen(page: Page, label: string) {
  return page.evaluate((text) => {
    const btn = [...document.querySelectorAll('button')]
      .find((b) => (b.textContent ?? '').trim().startsWith(text));
    if (!btn) return null;
    const r = btn.getBoundingClientRect();
    return r.bottom <= window.innerHeight && r.top >= 0;
  }, label);
}

const CASES: [name: string, url: string, label: string][] = [
  ['template settings', '/workspaces/admin/templates/vscode-workspace', 'Save settings'],
  ['privacy notices', '/admin/consent', 'Publish version'],
  ['course workspace configuration', '/workspaces/admin/courses/c1', 'Save configuration'],
];

for (const [name, url, label] of CASES) {
  test(`${name}: "${label}" is reachable without scrolling`, async ({ page }) => {
    await seed(page);
    await page.goto(url);
    await expect
      .poll(() => isOnScreen(page, label), { timeout: 8000, message: `${label} never rendered` })
      .toBe(true);
  });
}
