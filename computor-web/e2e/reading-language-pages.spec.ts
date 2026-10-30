import { test, expect, type Page, type Route } from '@playwright/test';
import { profileUiLanguage } from '../src/hooks/useUiLanguage';
import { duration } from '../src/utils/instanceStatus';

/**
 * Pages that used to ignore the reading language (profile language, else the
 * browser language, German without one): the public pages while signed in,
 * maintenance texts, tutor and lecturer titles, a legacy profile code and an
 * empty browser language.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = 'demo';
const MEMBER = 'm-ada';

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

const UNIT = { id: 'u1', path: 'week1', position: 1, title: 'Woche 1', title_i18n: { en: 'Week 1' }, course_content_kind_id: 'unit', course_content_type_id: 'weekly', is_submittable: false };
const LOOPS = {
  id: 'loops', path: 'week1.loops', position: 1, title: 'Schleifen', title_i18n: { en: 'Loops' },
  course_content_kind_id: 'assignment', course_content_type_id: 'task', is_submittable: true,
  course_id: COURSE_ID, submission_count: 1, result_count: 1, unreviewed_count: 0,
};
const TYPES = [
  { id: 'weekly', slug: 'weekly', title: 'Woche', title_i18n: { en: 'Week' } },
  { id: 'task', slug: 'task', title: 'Aufgabe', title_i18n: { en: 'Exercise' } },
];

/** Signs in with `profileLanguage`; the mock resolves effective_language as the backend does. */
async function signIn(page: Page, profileLanguage: string | null, extra: (path: string, route: Route) => unknown = () => undefined) {
  await page.addInitScript((language) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'u-1', username: 'lea', email: 'lea@example.org', givenName: 'Lea', familyName: 'Synthetic',
      role: 'user', systemRoles: [], language,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, profileLanguage);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    const handled = extra(path, route);
    if (handled) return handled;
    if (path === '/user/views') return json(route, ['student', 'tutor', 'lecturer']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { [COURSE_ID]: ['_lecturer'] } });
    if (path === '/user') {
      const header = (route.request().headers()['accept-language'] ?? '').toLowerCase();
      const profile = profileLanguage === 'de' || profileLanguage === 'en' ? profileLanguage : null;
      return json(route, {
        id: 'u-1', email: 'lea@example.org', given_name: 'Lea', family_name: 'Synthetic', user_roles: [],
        profile: profileLanguage ? { id: 'p', language_code: profileLanguage } : null,
        effective_language: profile ?? (header ? (header.startsWith('de') ? 'de' : 'en') : 'de'),
      });
    }
    if (path === '/courses' || path === '/courses/public') return json(route, []);
    if (path === `/courses/${COURSE_ID}`) return json(route, { id: COURSE_ID, title: 'Python', path: 'demo' });
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
}

// --- pure helpers ----------------------------------------------------------------------

test('a legacy profile code is not a language choice', () => {
  expect(profileUiLanguage('fr')).toBeNull();
  expect(profileUiLanguage(' DE ')).toBe('de');
  expect(profileUiLanguage('en')).toBe('en');
  expect(profileUiLanguage(null)).toBeNull();
});

test('uptime reads in the interface language', () => {
  expect(duration(30 * 3600, 'de')).toBe('1 T 6 Std.');
  expect(duration(90 * 60, 'de')).toBe('1 Std. 30 Min.');
  expect(duration(30 * 3600, 'en')).toBe('1d 6h');
});

// --- public pages while signed in ------------------------------------------------------

test.describe('German browser, English profile', () => {
  test.use({ locale: 'de-DE' });

  test('/learn is English, names the dashboard as the sidebar does and offers no switch', async ({ page }) => {
    await signIn(page, 'en');
    await page.goto('/learn');
    await expect(page.getByRole('heading', { level: 1, name: 'Data Science with Python' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
    await expect(page.getByRole('group', { name: /Sprache|Language/ })).toHaveCount(0);
  });
});

test.describe('English browser, German profile', () => {
  test.use({ locale: 'en-US' });

  test('/learn is German and calls the dashboard "Übersicht"', async ({ page }) => {
    await signIn(page, 'de');
    await page.goto('/learn');
    await expect(page.getByRole('heading', { level: 1, name: 'Data Science mit Python' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Übersicht', exact: true })).toBeVisible();
  });
});

test.describe('a legacy profile code', () => {
  test.use({ locale: 'de-DE' });

  test('falls through to the browser language, as on the server', async ({ page }) => {
    await signIn(page, 'fr');
    await page.goto('/courses');
    await expect(page.getByRole('complementary').getByRole('link', { name: 'Meine Kurse' })).toBeVisible();
  });

  test('shows as Automatic, and the picker offers only Automatic, Deutsch and English', async ({ page }) => {
    await signIn(page, 'fr');
    await page.goto('/profile');
    const picker = page.getByRole('combobox', { name: 'Sprache' });
    await expect(picker).toHaveValue('');
    await expect(picker.locator('option')).toHaveText(['Automatisch (Browser)', 'Deutsch', 'English']);
  });
});

test('an empty browser language reads German', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'languages', { get: () => [] });
    Object.defineProperty(navigator, 'language', { get: () => '' });
  });
  await page.route(`${API_ORIGIN}/**`, (route) => json(route, {}, 401));
  await page.goto('/learn');
  await expect(page.getByRole('heading', { level: 1, name: 'Data Science mit Python' })).toBeVisible();
  await expect(page.getByText('Offene Lernmaterialien')).toBeVisible();
});

// --- maintenance -----------------------------------------------------------------------

for (const [profile, shown] of [['en', 'Locked from 6 pm.'], ['de', 'Ab 18 Uhr gesperrt.']] as const) {
  test(`the maintenance banner shows the admin text in ${profile}`, async ({ page }) => {
    await signIn(page, profile, (path, route) => path === '/system/maintenance/status' && json(route, {
      active: true, message: 'Ab 18 Uhr gesperrt.',
      message_i18n: { de: 'Ab 18 Uhr gesperrt.', en: 'Locked from 6 pm.' },
      activated_at: null, activated_by: null, activated_by_name: null,
      scheduled_at: null, scheduled_by: null, scheduled_by_name: null,
    }));
    await page.goto('/courses');
    await expect(page.getByText(shown)).toBeVisible();
  });
}

// --- tutor and lecturer titles ---------------------------------------------------------

test.describe('English profile, German course', () => {
  test.use({ locale: 'de-DE' });

  test('the tutor grading list shows the English assignment title', async ({ page }) => {
    await signIn(page, 'en', (path, route) => {
      if (path === `/tutors/course-members/${MEMBER}`) return json(route, { id: MEMBER, course_id: COURSE_ID, user: { given_name: 'Ada', family_name: 'Synthetic' } });
      if (path === `/tutors/course-members/${MEMBER}/course-contents`) return json(route, [UNIT, LOOPS]);
      if (path === `/tutors/course-members/${MEMBER}/course-contents/loops`) return json(route, LOOPS);
    });
    await page.goto(`/courses/${COURSE_ID}/tutor/grading/${MEMBER}?content=loops`);
    await expect(page.getByRole('button', { name: /Loops/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Loops' })).toBeVisible();
    await expect(page.getByText('Schleifen')).toHaveCount(0);
  });

  test('the tutor submission queue names the assignment in English', async ({ page }) => {
    await signIn(page, 'en', (path, route) => {
      if (path === '/course-contents') return json(route, [LOOPS]);
      if (path === '/tutors/submission-groups') return json(route, [{
        id: 'g1', course_id: COURSE_ID, course_content_id: 'loops', display_name: 'Ada Synthetic',
        max_group_size: 1, member_count: 1, submission_count: 1, latest_submission_at: '2026-03-02T09:00:00Z',
        has_ungraded_submissions: true, created_at: '2026-03-02T09:00:00Z', updated_at: '2026-03-02T09:00:00Z',
      }]);
    });
    await page.goto(`/courses/${COURSE_ID}/tutor/submissions`);
    await expect(page.getByRole('cell', { name: 'Loops' })).toBeVisible();
    await expect(page.getByText('Schleifen')).toHaveCount(0);
  });

  test('the lecturer tree shows English item and content-type titles', async ({ page }) => {
    await signIn(page, 'en', (path, route) => {
      if (path === '/lecturers/course-contents') return json(route, [UNIT, LOOPS]);
      if (path === '/course-content-types') return json(route, TYPES);
    });
    await page.goto(`/courses/${COURSE_ID}/lecturer/assignments`);
    await expect(page.getByText('Loops', { exact: true })).toBeVisible();
    await expect(page.getByText('Week 1', { exact: true })).toBeVisible();
    await expect(page.getByText('Exercise', { exact: true })).toBeVisible();
    await expect(page.getByText('Schleifen')).toHaveCount(0);
    await expect(page.getByText('Aufgabe', { exact: true })).toHaveCount(0);
  });
});

// The German terms and privacy texts are authoritative. An English reader gets
// the English translation, opened by a note that the German text applies and a
// link to it; a German reader gets the German text.
for (const [path, german, english] of [
  ['/terms', 'Nutzungsbedingungen computor.at', 'Terms of Use computor.at'],
  ['/privacy', 'Datenschutzerklärung computor.at', 'Privacy Notice computor.at'],
] as const) {
  test.describe(`${path} for an English browser`, () => {
    test.use({ locale: 'en-US' });

    test('shows the English translation and links the authoritative German text', async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(english);
      await expect(page.getByText('Version 1.7, dated 29 October 2026', { exact: false }).first()).toBeVisible();
      const notice = page.getByRole('note');
      await expect(notice).toContainText('Only the German text is authoritative.');
      await notice.getByRole('link', { name: 'Read the German text' }).click();
      await expect(page).toHaveURL(new RegExp(`${path}/de$`));
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(german);
      await expect(page.getByRole('note')).toHaveCount(0);
    });
  });

  test.describe(`${path} for a German browser`, () => {
    test.use({ locale: 'de-DE' });

    test('shows the German text without the notice', async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(german);
      await expect(page.getByText('Version 1.7, Stand 29.10.2026')).toBeVisible();
      await expect(page.getByRole('note')).toHaveCount(0);
    });
  });
}

// Bilingual legal pages keep both bodies, but name themselves and date their
// version in the reading language.
for (const [path, german, english, germanVersion, englishVersion] of [
  ['/impressum', 'Impressum computor.at', 'Imprint computor.at', 'Version 1.1, gültig ab 25.10.2026', 'Version 1.1, valid from 25 October 2026'],
  ['/accessibility', 'Barrierefreiheitserklärung computor.at', 'Accessibility statement computor.at', 'Version 1.2, Stand 29.10.2026', 'Version 1.2, dated 29 October 2026'],
  ['/report', 'Inhalte melden', 'Report content', 'Version 1.2, Stand 29.10.2026', 'Version 1.2, dated 29 October 2026'],
] as const) {
  for (const [locale, heading, version] of [['en-US', english, englishVersion], ['de-DE', german, germanVersion]] as const) {
    test.describe(`${path} for ${locale}`, () => {
      test.use({ locale });

      test(`is headed "${heading}" with "${version}"`, async ({ page }) => {
        await page.goto(path);
        await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading);
        await expect(page.getByText(version, { exact: true })).toBeVisible();
      });
    });
  }
}
