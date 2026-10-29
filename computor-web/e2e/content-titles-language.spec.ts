import { test, expect, type Page, type Route } from '@playwright/test';
import { localized, localizedText } from '../src/utils/localizedText';
import { localizedTitle } from '../src/components/learn/localize';
import type { PublicLearningCourseOutline } from '../src/types/publicLearning';

/**
 * Course, unit and assignment titles in the reading language
 * (computor-org/issues#538, #552, #453). The mock backend answers
 * `?localize=<de|en>` as the real one does: the translation where one exists,
 * else the stored source text.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = '20000000-0000-4000-8000-000000000002';
const COURSE = {
  id: COURSE_ID,
  title: 'Data Science mit Python – Grundlagen',
  title_i18n: { en: 'Data Science with Python – Foundations' },
  description: 'Python-Grundlagen für die Datenanalyse.',
  description_i18n: { en: 'Python basics for data analysis.' },
  path: 'tugraz.dsp.grundlagen',
  course_family_id: 'f-1',
  organization_id: 'o-1',
  language_code: 'de',
};

type I18n = Record<string, string>;
type Row = {
  id: string; path: string; position: number; title: string; title_i18n?: I18n;
  course_content_kind_id: 'unit' | 'assignment';
  deployment?: { example_version: { description: string; description_i18n?: I18n } };
};

const CONTENTS: Row[] = [
  { id: 'u-intro', path: 'intro', position: 1, title: 'Einführung', title_i18n: { en: 'Introduction' }, course_content_kind_id: 'unit' },
  // No translation: the "Woche N" rule still follows the reader.
  { id: 'u-week2', path: 'week2', position: 2, title: 'Woche 2', course_content_kind_id: 'unit' },
  {
    id: 'a-constants', path: 'intro.constants', position: 1, title: 'Mathematische Konstanten',
    title_i18n: { en: 'Mathematical Constants' }, course_content_kind_id: 'assignment',
    deployment: { example_version: { description: 'Print mathematical constants.', description_i18n: { de: 'Gib mathematische Konstanten aus.' } } },
  },
  {
    id: 'a-loops', path: 'week2.loops', position: 1, title: 'Schleifen', title_i18n: { en: 'Loops' },
    course_content_kind_id: 'assignment',
    // meta.yaml text in English only, as for the public examples today.
    deployment: { example_version: { description: 'Write a loop.' } },
  },
];

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

/** Signs in with a mutable profile language and records the `localize` of every student request. */
async function signIn(page: Page, profile: { language: string | null }) {
  const localize: (string | null)[] = [];
  await page.addInitScript((language) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [], language,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, profile.language);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const lang = url.searchParams.get('localize');
    const row = (item: Row) => ({
      ...item,
      title: localizedText(item.title_i18n, lang, item.title),
      course_id: COURSE_ID, visible_effective: true, has_deployment: item.course_content_kind_id === 'assignment',
      submitted: false, result: null,
    });
    if (path.endsWith('/description')) return json(route, { detail: 'Not found' }, 404);
    if (path === '/students/course-contents') {
      localize.push(lang);
      return json(route, CONTENTS.map(row));
    }
    if (path.startsWith('/students/course-contents/')) {
      localize.push(lang);
      const item = CONTENTS.find((c) => c.id === path.split('/')[3]);
      return item ? json(route, row(item)) : json(route, { detail: 'Not found' }, 404);
    }
    if (/^\/profiles\/[^/]+$/.test(path) && route.request().method() === 'PATCH') {
      profile.language = route.request().postDataJSON()?.language_code ?? null;
      return json(route, { id: 'p', language_code: profile.language });
    }
    if (path === '/user') return json(route, {
      id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner', user_roles: [],
      profile: profile.language ? { id: 'p', language_code: profile.language } : null,
      effective_language: profile.language ?? 'de',
    });
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    if (path === '/courses' || path === '/courses/public') return json(route, [COURSE]);
    if (path.startsWith('/user/views')) return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { [COURSE_ID]: ['_student'] } });
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates') || path === '/results' || path === '/submissions/artifacts') return json(route, []);
    return json(route, {});
  });
  return localize;
}

test('a translation replaces the source text only where it has an entry', () => {
  expect(localizedText({ en: 'Loops', de: ' ' }, 'en', 'Schleifen')).toBe('Loops');
  expect(localizedText({ en: 'Loops', de: ' ' }, 'de', 'Schleifen')).toBe('Schleifen');
  expect(localizedText(null, 'en', 'Schleifen')).toBe('Schleifen');
  expect(localized(COURSE, 'en')).toMatchObject({ title: 'Data Science with Python – Foundations', description: 'Python basics for data analysis.' });
  expect(localized(COURSE, 'de')).toBe(COURSE);
});

test.describe('English profile, German browser', () => {
  test.use({ locale: 'de-AT' });

  test('the course tree, the progress pointer and the course name are English', async ({ page }) => {
    const localize = await signIn(page, { language: 'en' });
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);

    await expect(page.getByRole('button', { name: 'Introduction', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: 'Week 2', exact: true })).toBeVisible();
    await expect(page.getByTestId('course-progress')).toContainText('Start with: Introduction › Mathematical Constants');
    await expect(page.getByRole('link', { name: 'Data Science with Python – Foundations' }).first()).toBeVisible();
    for (const german of ['Einführung', 'Woche 2', 'Mathematische Konstanten', COURSE.title]) {
      await expect(page.getByText(german, { exact: true })).toHaveCount(0);
    }
    expect(localize.length).toBeGreaterThan(0);
    expect(localize.every((lang) => lang === 'en')).toBe(true);
  });

  test('my courses and the catalog show the English course title and description', async ({ page }) => {
    await signIn(page, { language: 'en' });
    for (const path of ['/courses', '/courses/catalog']) {
      await page.goto(path);
      await expect(page.getByRole('heading', { name: 'Data Science with Python – Foundations' })).toBeVisible({ timeout: 15_000 });
      await expect(page.getByText('Python basics for data analysis.')).toBeVisible();
      await expect(page.getByText(COURSE.description)).toHaveCount(0);
    }
  });

  test('switching the profile to German brings German titles', async ({ page }) => {
    const profile = { language: 'en' as string | null };
    const localize = await signIn(page, profile);
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);
    await expect(page.getByRole('button', { name: 'Introduction', exact: true })).toBeVisible({ timeout: 15_000 });

    await page.goto('/profile');
    await page.getByLabel('Language', { exact: true }).selectOption('de');
    await page.getByRole('button', { name: 'Save changes' }).click();
    await expect(page.getByText('Gespeichert')).toBeVisible();

    await page.goBack();
    await expect(page.getByRole('button', { name: 'Einführung', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: 'Woche 2', exact: true })).toBeVisible();
    await expect(page.getByText('Introduction', { exact: true })).toHaveCount(0);
    expect(localize.at(-1)).toBe('de');
  });
});

test.describe('German profile, English browser', () => {
  test.use({ locale: 'en-US' });

  test('the assignment page shows the German title and never the English example text', async ({ page }) => {
    const localize = await signIn(page, { language: 'de' });
    await page.goto(`/courses/${COURSE_ID}/student/assignments/a-constants`);
    await expect(page.getByRole('heading', { name: 'Mathematische Konstanten' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Gib mathematische Konstanten aus.')).toBeVisible();
    await expect(page.getByText('Print mathematical constants.')).toHaveCount(0);

    await page.goto(`/courses/${COURSE_ID}/student/assignments/a-loops`);
    await expect(page.getByRole('heading', { name: 'Schleifen' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Keine Beschreibung.')).toBeVisible();
    await expect(page.getByText('Write a loop.')).toHaveCount(0);
    expect(localize).toContain('de');
    expect(localize).not.toContain('en');
  });
});

// --- signed out: the static /learn catalog in the visitor's language --------------

const PUBLIC_COURSE = {
  id: 'python-beginner', position: 1, course_path: 'dsp.beginner', language_code: 'de',
  title: 'Python für Einsteiger', title_i18n: { en: 'Python for beginners' },
  description: 'Erste Schritte mit Python.', description_i18n: { en: 'First steps with Python.' },
  exercise_count: 1, unit_count: 1,
};
const PUBLIC_OUTLINE = {
  ...PUBLIC_COURSE, source_commit: 'a'.repeat(40), welcome_content_id: null, first_exercise_id: 'week_1.loops',
  contents: [
    { id: 'week_1', title: 'Grundlagen', title_i18n: { en: 'Basics' }, path: 'week_1', parent_path: null, depth: 0, position: 1, kind: 'unit', is_submittable: false },
    { id: 'week_1.loops', title: 'Schleifen', title_i18n: { en: 'Loops' }, path: 'week_1.loops', parent_path: 'week_1', depth: 1, position: 1, kind: 'assignment', is_submittable: true },
  ],
  materials: {
    week_1: { id: 'week_1', course_id: 'python-beginner', title: 'Grundlagen', title_i18n: { en: 'Basics' }, path: 'week_1', kind: 'unit', is_submittable: false, markdown_variants: {}, asset_base_url: '/learning/media/python-beginner/week_1/', media_files: [] },
    'week_1.loops': { id: 'week_1.loops', course_id: 'python-beginner', title: 'Schleifen', title_i18n: { en: 'Loops' }, path: 'week_1.loops', kind: 'assignment', is_submittable: true, markdown_variants: {}, asset_base_url: '/learning/media/python-beginner/week_1.loops/', media_files: [] },
  },
};

async function servePublicLearning(page: Page) {
  await page.route('**/learning/catalog.json', (route) => json(route, [PUBLIC_COURSE]));
  await page.route('**/learning/courses/python-beginner.json', (route) => json(route, PUBLIC_OUTLINE));
}

test('the course reader names outline items by their heading, else by their translation', () => {
  const outline = PUBLIC_OUTLINE as unknown as PublicLearningCourseOutline;
  expect(localizedTitle(outline, 'week_1.loops', 'Schleifen', 'en')).toBe('Loops');
  expect(localizedTitle(outline, 'week_1', 'Grundlagen', 'en')).toBe('Basics');
  expect(localizedTitle(outline, 'week_1.loops', 'Schleifen', 'de')).toBe('Schleifen');
  // The heading keeps its TeX for the reader to typeset; the metadata title is plain text.
  const withHeading = structuredClone(outline);
  withHeading.materials['week_1.loops'].markdown_variants = { en: '# Approximation of $\\pi$\n\nText' };
  expect(localizedTitle(withHeading, 'week_1.loops', 'Schleifen', 'en')).toBe('Approximation of $\\pi$');
});

test.describe('signed out, English browser', () => {
  test.use({ locale: 'en-US' });

  test('/learn shows the English course title and description', async ({ page }) => {
    await servePublicLearning(page);
    await page.goto('/learn');
    await expect(page.getByRole('heading', { name: 'Python for beginners' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('First steps with Python.')).toBeVisible();
    await expect(page.getByText('Python für Einsteiger')).toHaveCount(0);
  });
});

test.describe('signed out, German browser', () => {
  test.use({ locale: 'de-AT' });

  test('/learn keeps the German source titles', async ({ page }) => {
    await servePublicLearning(page);
    await page.goto('/learn');
    await expect(page.getByRole('heading', { name: 'Python für Einsteiger' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Python for beginners')).toHaveCount(0);
  });
});
