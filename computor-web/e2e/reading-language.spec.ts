import { test, expect, type Page, type Route } from '@playwright/test';
import JSZip from 'jszip';
import { acceptLanguage } from '../src/utils/requestLanguage';
import { descriptionInLanguage } from '../src/components/student/studentDescription';

/**
 * One reading language per screen (computor-org/issues#552, #453, #557): the
 * server renders in the request's language, assignment texts follow the
 * interface language instead of the course language, a welcome unit shows only
 * its section in that language, and dates follow it too.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = '20000000-0000-4000-8000-000000000002';
const COURSE = {
  id: COURSE_ID, title: 'Data Science mit Python – Grundlagen', path: 'dsp.basics',
  course_family_id: 'f-1', organization_id: 'o-1', language_code: 'de',
};
const WELCOME = [
  'Intro für alle.',
  '<!-- lang: de -->',
  'In drei Wochen lernst du die Grundlagen von Python.',
  '<!-- lang: en -->',
  'In three weeks you learn the basics of Python.',
].join('\n');
const CONTENTS = [
  { id: 'welcome', path: 'welcome', position: 0, title: 'Willkommen', course_content_kind_id: 'unit', description: WELCOME },
  { id: 'constants', path: 'week1.constants', position: 1, title: 'Mathematische Konstanten', course_content_kind_id: 'assignment', has_deployment: true },
];

// --- the server render ------------------------------------------------------------------

test('Accept-Language follows the backend rule', () => {
  expect(acceptLanguage('en-US,en;q=0.9,de;q=0.8')).toBe('en');
  expect(acceptLanguage('fr-FR,de;q=0.5')).toBe('en');
  expect(acceptLanguage('it;q=0.5,de-AT;q=0.9')).toBe('de');
  expect(acceptLanguage('de-CH')).toBe('de');
  expect(acceptLanguage('')).toBe('de');
  expect(acceptLanguage(null)).toBe('de');
});

for (const [header, cookie, lang, text] of [
  ['en-US,en;q=0.9', '', 'en', 'Programming step by step.'],
  ['de-AT,de;q=0.9', '', 'de', 'Programmieren Schritt für Schritt.'],
  // An explicit choice on a signed-out page outranks the browser.
  ['de-AT,de;q=0.9', 'computor_language=en', 'en', 'Programming step by step.'],
] as const) {
  test(`the landing page is served in ${lang} for ${header} ${cookie}`.trim(), async ({ request }) => {
    const response = await request.get('/', { headers: { 'Accept-Language': header, ...(cookie ? { Cookie: cookie } : {}) } });
    const html = await response.text();
    expect(html).toMatch(new RegExp(`<html lang="${lang}"`));
    expect(html).toContain(text);
  });
}

test('a signed-in reader is served in their language on the first paint', async ({ request }) => {
  // The browser is German, the profile English: the cookie the app wrote decides.
  const response = await request.get('/courses', {
    headers: { 'Accept-Language': 'de-AT', Cookie: 'computor_reading_language=en' },
  });
  const html = await response.text();
  expect(html).toMatch(/<html lang="en"/);
  expect(html).toContain('Learning platform for programming');
});

// --- assignment texts in the reading language -----------------------------------------

test('a welcome text keeps its intro and only the section in the reading language', () => {
  expect(descriptionInLanguage(WELCOME, 'en')).toBe('Intro für alle.\n\nIn three weeks you learn the basics of Python.');
  expect(descriptionInLanguage(WELCOME, 'de')).toBe('Intro für alle.\n\nIn drei Wochen lernst du die Grundlagen von Python.');
  expect(descriptionInLanguage('Kein Marker.', 'en')).toBe('Kein Marker.');
});

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function readme(): Promise<Buffer> {
  const zip = new JSZip();
  zip.file('index_de.md', '# Mathematische Konstanten\n\nDies ist die erste Aufgabe.');
  zip.file('index_en.md', '# Mathematical Constants\n\nThis is the first task.');
  return zip.generateAsync({ type: 'nodebuffer' });
}

async function signIn(page: Page, profileLanguage: string | null, { accountUrl }: { accountUrl?: string } = {}) {
  const archive = await readme();
  await page.addInitScript((language) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [], language,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, profileLanguage);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/students/course-contents') return json(route, CONTENTS.map((item) => ({ ...item, course_id: COURSE_ID, visible_effective: true })));
    if (path === '/students/course-contents/constants/description') {
      return route.fulfill({ status: 200, contentType: 'application/zip', body: archive });
    }
    if (path.endsWith('/description')) return json(route, { detail: 'Not found' }, 404);
    if (path.startsWith('/students/course-contents/')) {
      const item = CONTENTS.find((entry) => entry.id === path.split('/')[3]);
      return item ? json(route, { ...item, course_id: COURSE_ID, visible_effective: true }) : json(route, { detail: 'Not found' }, 404);
    }
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    if (path === '/courses') return json(route, [COURSE]);
    if (path === '/auth/providers') return json(route, [{ name: 'keycloak', display_name: 'Keycloak', type: 'oidc', enabled: true, account_url: accountUrl }]);
    if (path.startsWith('/user/views')) return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { [COURSE_ID]: ['_student'] } });
    if (path === '/user') {
      const header = (route.request().headers()['accept-language'] ?? '').toLowerCase();
      return json(route, {
        id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner', user_roles: [],
        created_at: '2026-10-26T09:00:00Z',
        profile: profileLanguage ? { id: 'p', language_code: profileLanguage } : null,
        effective_language: profileLanguage ?? (header.startsWith('de') ? 'de' : 'en'),
      });
    }
    if (path.startsWith('/api-tokens') || path.startsWith('/accounts')) return json(route, []);
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates') || path === '/results' || path === '/submissions/artifacts') return json(route, []);
    return json(route, {});
  });
}

const assignmentUrl = (id: string) => `/courses/${COURSE_ID}/student/assignments/${id}`;

test.describe('English browser, no profile language, German course', () => {
  test.use({ locale: 'en-US' });

  // Read in the course language before: German text under English chrome.
  test('the assignment text is English', async ({ page }) => {
    await signIn(page, null);
    await page.goto(assignmentUrl('constants'));
    await expect(page.getByRole('heading', { name: 'Mathematical Constants' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('This is the first task.')).toBeVisible();
    await expect(page.getByText('Dies ist die erste Aufgabe.')).toHaveCount(0);
  });

  test('the welcome unit shows only its English section', async ({ page }) => {
    await signIn(page, null);
    await page.goto(assignmentUrl('welcome'));
    await expect(page.getByText('In three weeks you learn the basics of Python.')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('In drei Wochen lernst du')).toHaveCount(0);
  });

  test('the course language is named, not coded', async ({ page }) => {
    await signIn(page, null);
    await page.goto('/courses');
    await expect(page.getByText('German', { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('de', { exact: true })).toHaveCount(0);
  });
});

test.describe('German browser, English profile', () => {
  test.use({ locale: 'de-DE' });

  test('the assignment text follows the profile', async ({ page }) => {
    await signIn(page, 'en');
    await page.goto(assignmentUrl('constants'));
    await expect(page.getByRole('heading', { name: 'Mathematical Constants' })).toBeVisible({ timeout: 15_000 });
  });

  // The date used the browser's German format beside English labels.
  test('dates are in the English format', async ({ page }) => {
    await signIn(page, 'en');
    await page.goto('/profile');
    await expect(page.getByText('joined 10/26/2026')).toBeVisible({ timeout: 15_000 });
  });
});

test.describe('the profile help names only what exists (computor-org/issues#557)', () => {
  test.use({ locale: 'de-DE' });

  test('without an account console it points nowhere', async ({ page }) => {
    await signIn(page, null);
    await page.goto('/profile');
    await expect(page.getByText('Die E-Mail-Adresse verwaltet dein Login-Anbieter; hier lässt sie sich nicht ändern.')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Konto und Sicherheit/)).toHaveCount(0);
  });

  test('with an account console it names the Settings section that opens it', async ({ page }) => {
    await signIn(page, null, { accountUrl: 'https://login.example.org/realms/computor/account/' });
    await page.goto('/profile');
    await expect(page.getByText(/unter „Konto und Sicherheit“ öffnest/)).toBeVisible({ timeout: 15_000 });
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Konto und Sicherheit' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('link', { name: 'Kontoverwaltung öffnen' })).toBeVisible();
  });
});
