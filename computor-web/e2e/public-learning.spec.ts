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
  await expect(page.getByRole('link', { name: 'Open course' })).toHaveCount(3);
  await expect(page.getByText('python-beginner.yaml')).toHaveCount(0);
  await page.getByRole('link', { name: 'Open course' }).first().click();
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

test('the course welcome item renders as Markdown in the reader language and is not a week', async ({ page }) => {
  await page.goto(`/learn/${COURSE}`);
  await expect(page.getByText('3 weeks · ', { exact: false })).toBeVisible();
  const welcome = page.locator('article section').first();
  await expect(welcome.getByRole('heading', { name: 'Welcome', exact: true })).toBeVisible();
  await expect(welcome.getByText(/How to reach your first submission/)).toBeVisible();
  await expect(welcome.getByRole('link', { name: 'public course page' })).toHaveAttribute('href', /\/learn\/python-beginner$/);
  await expect(welcome.getByText(/lang:|\[public course page\]/)).toHaveCount(0);
  await welcome.getByRole('button', { name: 'Deutsch', exact: true }).click();
  await expect(welcome.getByText(/So kommst du zur ersten Abgabe/)).toBeVisible();
  await expect(welcome.getByRole('link', { name: /Mathematische Konstanten/ })).toBeVisible();
  await welcome.getByRole('button', { name: 'English', exact: true }).click();
  await expect(welcome.getByRole('link', { name: /Start with Mathematical Constants/ })).toBeVisible();
});

test('all three courses have native reading content', async ({ page }) => {
  for (const slug of ['python-beginner', 'python-intermediate', 'python-advanced']) {
    await page.goto(`/learn/${slug}`);
    await expect(page.getByRole('heading', { name: 'Welcome', exact: true })).toBeVisible();
    await page.getByRole('link', { name: /Start with / }).click();
    await expect(page.locator('article .prose')).not.toBeEmpty();
  }
});

for (const exercise of [MATH, 'week_1.basis1']) {
  test(`equations and inline code render from the real ${exercise} descriptions`, async ({ page }, testInfo) => {
    await page.goto(`/learn/${COURSE}/content/${exercise}`);
    for (const language of ['English', 'Deutsch']) {
      await page.getByRole('button', { name: language, exact: true }).click();
      const article = page.locator('article');
      await expect(article.locator('.katex-display .mtable').first()).toBeVisible();
      await expect(article.locator('.katex-error')).toHaveCount(0);
      const equations = article.locator('.katex-display annotation').first();
      await expect(equations).toContainText('\\begin{aligned}');
      await expect(equations).toContainText(exercise === MATH ? 'p\\_half' : 'sum\\_ab');
      const code = article.locator('code').first();
      await expect(code).toBeVisible();
      for (const pseudo of ['::before', '::after']) {
        expect(await code.evaluate((element, pseudo) => getComputedStyle(element, pseudo).content, pseudo)).not.toContain('`');
      }
      await page.screenshot({ path: testInfo.outputPath(`${language}.png`), fullPage: true });
    }
  });
}

test('math parsing leaves literal dollars and LaTeX inside code unchanged', async ({ page }) => {
  const outline = JSON.parse(fs.readFileSync('public/learning/courses/python-beginner.json', 'utf8'));
  const markdown = '# Literal code\n\n`$x_1$`\n\n```python\nprice = "$5"\n# \\begin{aligned} $x_1$\n```\n\n$y_1 = 2$';
  outline.materials[MATH].markdown_variants = { de: markdown, en: markdown };
  await page.route('**/learning/courses/python-beginner.json', route => route.fulfill({
    contentType: 'application/json', body: JSON.stringify(outline),
  }));
  await page.goto(URL);
  await expect(page.locator('article p code')).toHaveText('$x_1$');
  await expect(page.locator('article pre code')).toHaveText('price = "$5"\n# \\begin{aligned} $x_1$');
  await expect(page.locator('article .katex')).toHaveCount(1);
});

test('landing shows static courses, one sign-in link and no pilot or invite claim', async ({ page }) => {
  const calls: string[] = [];
  await blockApi(page, calls);
  await page.goto('/');
  await expect(page.getByRole('link', { name: /^(Anmelden|Sign in)$/ })).toHaveCount(1);
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

test('reference definitions survive title removal and math titles render throughout the reader', async ({ page }) => {
  await page.goto('/learn/python-advanced/content/week_2.pi_int');
  await expect(page.locator('article h2').first()).toContainText('Approximation of');
  await expect(page.locator('article h2 .katex')).toHaveCount(1);
  await expect(page.locator('article .markdown h1')).toHaveCount(0);
  await expect(page.locator('article a[href*="operators/lambda"]')).toHaveCount(1);
  await expect(page.getByRole('navigation', { name: 'Course outline' }).locator('.katex').first()).toBeVisible();
  await expect(page.locator('article')).not.toContainText('$\\pi$');
  await page.getByRole('button', { name: 'Deutsch', exact: true }).click();
  await expect(page.locator('article h2').first()).toContainText('Approximation von');
  await page.goto('/learn/python-advanced/content/week_3.pi_series');
  await expect(page.getByRole('navigation', { name: 'Aufgabennavigation' }).locator('.katex').first()).toBeVisible();
  await expect(page.locator('article .markdown h1')).toHaveCount(0);
});

test('long inline equations stay inside the mobile reader without clipping their scrollable content', async ({ page }) => {
  const outline = JSON.parse(fs.readFileSync('public/learning/courses/python-beginner.json', 'utf8'));
  const terms = Array.from({ length: 30 }, (_, i) => `a_{${i}}`).join(' + ');
  const markdown = `# Narrow reader\n\nA long formula $\\frac{${terms}}{100}$ ends here.`;
  outline.materials[MATH].markdown_variants = { de: markdown, en: markdown };
  await page.route('**/learning/courses/python-beginner.json', route => route.fulfill({
    contentType: 'application/json', body: JSON.stringify(outline),
  }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(URL);
  const math = page.locator('article p .katex');
  await expect(math).toBeVisible();
  const bounds = await math.evaluate(element => ({
    width: element.getBoundingClientRect().width,
    parentWidth: element.parentElement!.getBoundingClientRect().width,
    scrollWidth: element.scrollWidth,
    height: element.clientHeight,
    scrollHeight: element.scrollHeight,
    overflow: getComputedStyle(element).overflowX,
  }));
  expect(bounds.width).toBeLessThanOrEqual(bounds.parentWidth);
  expect(bounds.scrollWidth).toBeGreaterThan(bounds.width);
  expect(bounds.overflow).toBe('auto');
  expect(bounds.scrollHeight).toBeLessThanOrEqual(bounds.height);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
