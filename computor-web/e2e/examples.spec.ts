import { test, expect } from '@playwright/test';
import { PERSONAS, type Persona, injectAuth, json, mockApi } from './fixtures';

/** /examples — view gate (three tiers) and the manage/upload gate. */

const exampleManager: Persona = {
  ...PERSONAS.student, id: 'u-exma', username: 'exma', email: 'exma@example.org',
  givenName: 'Eve', familyName: 'Examples', role: 'user', systemRoles: ['_example_manager'],
};
const orgManager: Persona = {
  ...PERSONAS.student, id: 'u-orga', username: 'orga', email: 'orga@example.org',
  givenName: 'Otto', familyName: 'Org', role: 'user', systemRoles: ['_organization_manager'],
};

const exampleRows = [{
  id: 'e-1', directory: 'hello', identifier: 'itpcp.hello', title: 'Hello World',
  tags: ['py'], example_repository_id: 'r-1',
}];

function exampleHandlers(route: import('@playwright/test').Route, url: URL): boolean {
  if (url.pathname === '/examples' && route.request().method() === 'GET') {
    void json(route, exampleRows); return true;
  }
  if (url.pathname === '/example-repositories' && route.request().method() === 'GET') {
    void json(route, [{ id: 'r-1', name: 'Default Examples' }]); return true;
  }
  return false;
}

test.describe('examples', () => {
  test('an example manager sees the list and the upload link', async ({ page }) => {
    await injectAuth(page, exampleManager);
    await mockApi(page, { persona: exampleManager, handlers: exampleHandlers });
    await page.goto('/examples');

    await expect(page.getByRole('heading', { name: 'Examples' })).toBeVisible();
    await expect(page.getByText('Hello World')).toBeVisible();
    await expect(page.getByText('itpcp.hello')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Upload examples' })).toBeVisible();
  });

  test('an org-manager can view but not upload', async ({ page }) => {
    await injectAuth(page, orgManager);
    await mockApi(page, { persona: orgManager, handlers: exampleHandlers });
    await page.goto('/examples');

    await expect(page.getByText('Hello World')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Upload examples' })).toHaveCount(0);
  });

  test('a student is shown the forbidden state', async ({ page }) => {
    await injectAuth(page, PERSONAS.student);
    await mockApi(page, { persona: PERSONAS.student });
    await page.goto('/examples');

    await expect(page.getByText('You do not have access to examples.')).toBeVisible();
  });
});
