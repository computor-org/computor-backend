import { test, expect, type Page } from '@playwright/test';
import fs from 'node:fs';

const COURSE = 'python-beginner';
const MATH = 'week_1.math_constants';
const URL = `/learn/${COURSE}/content/${MATH}`;

async function blockApi(page: Page, calls: string[]) {
  // Cover both the local test API origin and production's same-origin /api.
  for (const pattern of ['http://localhost:8000/**', '**/api/**']) {
    await page.route(pattern, route => {
      calls.push(route.request().url());
      return route.fulfill({ status: 503, body: '{}' });
    });
  }
}

test('anonymous reading uses only static files even when the API is unavailable', async ({ page }) => {
  const apiRequests: string[] = [];
  const mutations: string[] = [];
  await blockApi(page, apiRequests);
  page.on('request', request => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) mutations.push(request.url());
  });
  await page.goto('/learn');
  await expect(page.getByRole('link', { name: 'Browse course' })).toHaveCount(3);
  await expect(page.getByText('python-beginner.yaml')).toHaveCount(0);
  await page.getByRole('link', { name: 'Browse course' }).first().click();
  await expect(page).toHaveURL(new RegExp(`/learn/${COURSE}$`));
  await expect(page.getByRole('heading', { name: 'Welcome', exact: true })).toBeVisible();
  await page.getByRole('link', { name: /Start with Mathematical Constants/ }).click();
  await expect(page).toHaveURL(new RegExp(URL.replaceAll('.', '\\.') + '$'));
  await expect(page.getByText(/This is the first task/)).toBeVisible();
  await expect(page.locator('.katex').first()).toBeVisible();
  const image = page.getByRole('img', { name: 'Run File in Interactive Window' });
  await expect(image).toHaveAttribute('src', `/learning/media/${COURSE}/${MATH}/run_interactively.png`);
  await expect(image).toBeVisible();
  expect(await image.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  await page.getByRole('button', { name: 'Deutsch', exact: true }).click();
  await expect(page.getByText(/Dies ist die erste Aufgabe/)).toBeVisible();
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.getByText(/This is the first task/)).toBeVisible();
  await page.getByRole('navigation', { name: 'Exercise navigation' }).getByRole('link').last().click();
  await expect(page).toHaveURL(/week_1\.basis1$/);
  await expect(page.locator('article .prose')).not.toBeEmpty();
  expect(apiRequests).toEqual([]);
  expect(mutations).toEqual([]);
});

test('all three courses have native reading content', async ({ page }) => {
  for (const slug of ['python-beginner', 'python-intermediate', 'python-advanced']) {
    await page.goto(`/learn/${slug}`);
    await expect(page.getByRole('heading', { name: 'Welcome', exact: true })).toBeVisible();
    await page.getByRole('link', { name: /Start with / }).click();
    await expect(page.locator('article .prose')).not.toBeEmpty();
  }
});

test('landing shows open registration and static courses with no pilot or invite claim', async ({ page }) => {
  const calls: string[] = [];
  await blockApi(page, calls);
  await page.goto('/');
  await expect(page.getByText('Offen zur Anmeldung / Open for registration')).toBeVisible();
  await expect(page.getByText(/Pilotbetrieb|join with an invite link|Teilnahme mit Einladungslink/)).toHaveCount(0);
  await page.getByRole('link', { name: /Data Science mit Python – Grundlagen/ }).click();
  await expect(page).toHaveURL(/\/learn\/python-beginner$/);
  await expect(page.getByRole('heading', { name: 'Welcome', exact: true })).toBeVisible();
  expect(calls).toEqual([]);
});

test('course outline remains usable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/learn/${COURSE}`);
  await page.getByText('Course outline', { exact: true }).click();
  await expect(page.locator('details[open] nav').getByText('Week 1', { exact: true })).toBeVisible();
  await page.locator('details[open] nav').getByText('Mathematical Constants', { exact: true }).click();
  await expect(page.getByText(/This is the first task/)).toBeVisible();
});

test('Markdown cannot execute HTML, trusted math commands or load foreign images', async ({ page }) => {
  const outline = JSON.parse(fs.readFileSync('public/learning/courses/python-beginner.json', 'utf8'));
  const hostile = `# Safety example
<script>window.__readerAttack = true</script>
<img src="https://evil.invalid/pixel.png" onerror="window.__readerAttack = true" />
![Foreign](https://evil.invalid/pixel.png)
![Inline](data:image/svg+xml;base64,PHN2Zz4=)
![Traversal](mediaFiles/../../secret.png)
[Attack](javascript:alert(1))
$\\href{javascript:alert(1)}{click}$`;
  outline.materials[MATH].markdown_variants = { de: hostile, en: hostile };
  await page.route('**/learning/courses/python-beginner.json', route => route.fulfill({
    contentType: 'application/json', body: JSON.stringify(outline),
  }));
  const foreign: string[] = [];
  page.on('request', request => { if (request.url().includes('evil.invalid')) foreign.push(request.url()); });
  await page.goto(URL);
  await expect(page.getByRole('heading', { name: 'Safety example' })).toBeVisible();
  expect(await page.evaluate(() => Reflect.get(window, '__readerAttack'))).toBeUndefined();
  await expect(page.locator('article a[href^="javascript:"]')).toHaveCount(0);
  await expect(page.locator('article img')).toHaveCount(0);
  expect(foreign).toEqual([]);
});

test('unknown courses and exercise IDs do not leak other content', async ({ page }) => {
  expect((await page.goto('/learn/private-course'))?.status()).toBe(404);
  expect((await page.goto(`/learn/${COURSE}/content/private-exercise`))?.status()).toBe(404);
});

test('static publication is read-only and restricts content sniffing', async ({ request }) => {
  const file = '/learning/catalog.json';
  const response = await request.get(file);
  expect(response.headers()['x-content-type-options']).toBe('nosniff');
  expect(response.headers()['content-security-policy']).toContain("default-src 'none'");
  const original = await response.body();
  for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) {
    const rejected = await request.fetch(file, { method });
    // Next 16.3.6 production can fail rendering its 405 page with
    // NoFallbackError (500). Both responses deny the method; assert the
    // explicit read-only Allow header and unchanged bytes independently.
    expect([405, 500]).toContain(rejected.status());
    expect(rejected.headers()['allow']?.split(/,\s*/).sort()).toEqual(['GET', 'HEAD']);
    expect(await (await request.get(file)).body()).toEqual(original);
  }
});
