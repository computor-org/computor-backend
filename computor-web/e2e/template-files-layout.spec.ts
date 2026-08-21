import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * The raw file editor has to fit the page, not grow past it.
 *
 * It used to render the textarea at a fixed `rows={26}`, so the card grew to the
 * file's length and pushed "Save <file>" below the fold — you had to scroll the
 * whole page to reach the button for the file already on screen. These tests pin
 * the arrangement: the editor scrolls, the page does not, Save stays reachable.
 */

const API_ORIGIN = 'http://localhost:8000';
const USER = {
  id: 'u-m', username: 'm', email: 'm@e.org', given_name: 'M', family_name: 'M',
  user_roles: [{ role_id: '_workspace_maintainer' }],
};

const longFile = {
  customized: false,
  files: [
    { name: 'Dockerfile', content: Array.from({ length: 60 }, (_, i) => `RUN echo "layer ${i}"`).join('\n') },
    { name: 'main.tf', content: 'resource "docker_container" "x" {}' },
  ],
};
const shortFile = { customized: false, files: [{ name: 'main.tf', content: 'x = 1' }] };

const json = (r: Route, b: unknown) =>
  r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(b) });

async function seed(page: Page, body: typeof longFile) {
  await page.addInitScript((u) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: u.id, username: u.username, email: u.email, givenName: u.given_name,
      familyName: u.family_name, role: 'user', systemRoles: ['_workspace_maintainer'],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path === '/coder/admin/templates/vscode-workspace/files') return json(route, body);
    return json(route, {});
  });
}

/** Geometry that decides whether the panel fits: what scrolls, and where Save is. */
function measure(page: Page) {
  return page.evaluate(() => {
    const save = [...document.querySelectorAll('button')]
      .find((b) => /^Save /.test(b.textContent ?? ''))!;
    const editor = document.querySelector('textarea')!;
    return {
      saveInView: save.getBoundingClientRect().bottom <= window.innerHeight,
      editorHeight: Math.round(editor.getBoundingClientRect().height),
      editorScrolls: editor.scrollHeight > editor.clientHeight + 1,
    };
  });
}

async function open(page: Page, body: typeof longFile, height: number) {
  await seed(page, body);
  await page.setViewportSize({ width: 1280, height });
  await page.goto('/workspaces/admin/templates/vscode-workspace?tab=files');
  await expect(page.locator('textarea')).toBeVisible();
}

test('a long file scrolls inside the editor, leaving Save on screen', async ({ page }) => {
  await open(page, longFile, 800);
  const m = await measure(page);
  expect(m.editorScrolls).toBe(true);
  expect(m.saveInView).toBe(true);
});

test('a short file still fills the card', async ({ page }) => {
  await open(page, shortFile, 800);
  const m = await measure(page);
  expect(m.editorScrolls).toBe(false);
  expect(m.saveInView).toBe(true);
  expect(m.editorHeight).toBeGreaterThan(200);
});

test('a very short window floors the editor instead of crushing it', async ({ page }) => {
  await open(page, longFile, 420);
  const m = await measure(page);
  // min-h-48. Below this the page scrolls, which beats an unusable editor.
  expect(m.editorHeight).toBeGreaterThanOrEqual(190);
});

test('switching files keeps the arrangement', async ({ page }) => {
  await open(page, longFile, 800);
  await page.getByRole('button', { name: 'main.tf', exact: true }).click();
  const m = await measure(page);
  expect(m.saveInView).toBe(true);
  await expect(page.getByRole('button', { name: 'Save main.tf' })).toBeVisible();
});
