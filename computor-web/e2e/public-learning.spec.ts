import { test, expect, type Page, type Route } from '@playwright/test';

const API_ORIGIN = 'http://localhost:8000';
const COURSE = '00000000-0000-0000-0000-000000000101';
const MATH = '00000000-0000-0000-0000-000000000201';
const BASIS = '00000000-0000-0000-0000-000000000202';

function json(route: Route, body: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

async function mockPublicReader(page: Page) {
  await page.route(`${API_ORIGIN}/**`, async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;

    if (path === '/public/courses') {
      return json(route, [
        { id: COURSE, title: 'Data Science mit Python – Grundlagen', description: 'Python von Anfang an.', language_code: 'de' },
        { id: '00000000-0000-0000-0000-000000000102', title: 'Data Science mit Python – Aufbau', description: 'Weiterführende Übungen.', language_code: 'de' },
        { id: '00000000-0000-0000-0000-000000000103', title: 'Data Science mit Python – Vertiefung', description: 'Vertiefende Übungen.', language_code: 'de' },
      ]);
    }

    if (path === `/public/courses/${COURSE}/outline`) {
      return json(route, {
        id: COURSE,
        title: 'Data Science mit Python – Grundlagen',
        description: 'Python von Anfang an.',
        language_code: 'de',
        contents: [
          { id: 'unit-1', title: 'Week 1', path: 'week_1', parent_path: null, depth: 0, position: 1, kind: 'unit', type_title: 'Week', color: 'green', is_submittable: false },
          { id: MATH, title: 'Mathematical Constants', path: 'week_1.math_constants', parent_path: 'week_1', depth: 1, position: 1, kind: 'assignment', type_title: 'Exercise', color: 'yellow', is_submittable: true },
          { id: BASIS, title: 'Basis 1', path: 'week_1.basis1', parent_path: 'week_1', depth: 1, position: 2, kind: 'assignment', type_title: 'Exercise', color: 'yellow', is_submittable: true },
        ],
        welcome_content_id: null,
        first_exercise_id: MATH,
        exercise_count: 2,
        unit_count: 1,
      });
    }

    if (path === `/public/course-contents/${MATH}`) {
      const english = url.searchParams.get('language') === 'en';
      return json(route, {
        id: MATH,
        course_id: COURSE,
        title: 'Mathematical Constants',
        path: 'week_1.math_constants',
        kind: 'assignment',
        is_submittable: true,
        markdown: english
          ? '# Mathematical Constants\n\nEnglish instructions. Euler: $e^{i\\pi}+1=0$.\n\n![Console](mediaFiles/demo.svg)'
          : '# Mathematische Konstanten\n\nDeutsche Anleitung. Euler: $e^{i\\pi}+1=0$.\n\n![Konsole](mediaFiles/demo.svg)',
        selected_language: english ? 'en' : 'de',
        available_languages: ['de', 'en'],
      });
    }

    if (path === `/public/course-contents/${BASIS}`) {
      return json(route, {
        id: BASIS,
        course_id: COURSE,
        title: 'Basis 1',
        path: 'week_1.basis1',
        kind: 'assignment',
        is_submittable: true,
        markdown: '# Basis 1\n\nNext exercise.',
        selected_language: 'de',
        available_languages: ['de', 'en'],
      });
    }

    if (path.includes('/assets/mediaFiles/demo.svg')) {
      return route.fulfill({
        status: 200,
        contentType: 'image/svg+xml',
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>',
      });
    }

    return route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
  });
}

test('anonymous learner browses a native course and bilingual exercises', async ({ page }) => {
  const mutations: string[] = [];
  page.on('request', request => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) mutations.push(request.url());
  });
  await mockPublicReader(page);

  await page.goto('/learn');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Data Science mit Python');
  await expect(page.getByRole('link', { name: 'Browse course' })).toHaveCount(3);
  await expect(page.getByText('python-beginner.yaml')).toHaveCount(0);

  await page.getByRole('link', { name: 'Browse course' }).first().click();
  await expect(page).toHaveURL(new RegExp(`/learn/${COURSE}$`));
  await expect(page.getByText('Week 1', { exact: true })).toBeVisible();
  await expect(page.getByText('Mathematical Constants', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Welcome' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Start with Mathematical Constants/ })).toBeVisible();

  await page.getByRole('link', { name: /Start with Mathematical Constants/ }).click();
  await expect(page).toHaveURL(new RegExp(`/learn/${COURSE}/content/${MATH}$`));
  await expect(page.getByText('Deutsche Anleitung.')).toBeVisible();
  await expect(page.locator('.katex')).toBeVisible();
  await expect(page.getByRole('img', { name: 'Konsole' })).toHaveAttribute(
    'src',
    new RegExp(`/public/course-contents/${MATH}/assets/mediaFiles/demo.svg$`),
  );

  await page.getByRole('button', { name: 'English' }).click();
  await expect(page.getByText('English instructions.')).toBeVisible();

  await page.getByRole('link', { name: /Basis 1/ }).last().click();
  await expect(page).toHaveURL(new RegExp(`/learn/${COURSE}/content/${BASIS}$`));
  await expect(page.getByText('Next exercise.')).toBeVisible();
  expect(mutations).toEqual([]);
});

test('public course outline remains usable on a narrow screen', async ({ page }) => {
  await mockPublicReader(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/learn/${COURSE}`);

  const outline = page.getByText('Course outline', { exact: true });
  await expect(outline).toBeVisible();
  await outline.click();
  await expect(page.getByText('Week 1', { exact: true })).toBeVisible();
});

test('landing still links to the public reader when the catalog is unavailable', async ({ page }) => {
  await page.route(`${API_ORIGIN}/**`, route => route.fulfill({ status: 503, body: '{}' }));
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Read courses' })).toBeVisible();
  await page.getByRole('link', { name: 'Read courses' }).click();
  await expect(page).toHaveURL(/\/learn$/);
});
