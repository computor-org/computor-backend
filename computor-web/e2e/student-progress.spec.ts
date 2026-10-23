import { test, expect, type Page, type Route } from '@playwright/test';
import { assignmentsInCourseOrder, courseProgress, progressPercent } from '../src/utils/studentProgress';

/**
 * A learner's own progress and the "Weiter mit" pointer (issues#408, #525):
 * a bar over submitted assignments, per-unit counts in the assignment list, and
 * a link to the first assignment in course order that is still open.
 *
 * Backend is mocked at the network layer; no API or database needed.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = 'c-dsp';
const COURSE = {
  id: COURSE_ID,
  title: 'Data Science mit Python – Grundlagen',
  description: 'Python-Grundlagen für die Datenanalyse.',
  path: 'tugraz.dsp.grundlagen',
  course_family_id: 'f-1',
  organization_id: 'o-1',
  language_code: 'de',
};

type Row = {
  id: string;
  path: string;
  position: number;
  title: string | null;
  course_content_kind_id: 'unit' | 'assignment';
  submitted?: boolean;
  result?: { id: string; result: number } | null;
};

const unit = (path: string, position: number, title: string): Row => ({
  id: `u-${path}`, path, position, title, course_content_kind_id: 'unit',
});
const assignment = (path: string, position: number, title: string, submitted: boolean, result?: number): Row => ({
  id: `a-${path}`, path, position, title, course_content_kind_id: 'assignment', submitted,
  result: result == null ? null : { id: `r-${path}`, result },
});

// Paths deliberately disagree with positions: the course order is by position.
const CONTENTS: Row[] = [
  unit('week3', 3, 'Woche 3'),
  unit('week1', 1, 'Woche 1'),
  unit('week2', 2, 'Woche 2'),
  assignment('week1.constants', 1, 'Mathematische Konstanten', true, 1),
  assignment('week1.lists', 2, 'Listen', true, 1),
  assignment('week2.loops', 1, 'Schleifen', true, 0.8),
  assignment('week2.functions', 2, 'Funktionen', true, 1),
  assignment('week3.review', 2, 'Python Grundlagen Review', false),
  assignment('week3.beta', 1, 'Beta-Absorption', false, 0),
];

// --- the rules, without a browser ---------------------------------------------------

test('assignments follow the course tree: unit position, then assignment position', () => {
  expect(assignmentsInCourseOrder(CONTENTS).map((a) => a.title)).toEqual([
    'Mathematische Konstanten', 'Listen', 'Schleifen', 'Funktionen', 'Beta-Absorption', 'Python Grundlagen Review',
  ]);
});

test('progress counts submitted assignments, per course and per unit, and ignores units', () => {
  const p = courseProgress(CONTENTS);
  expect([p.submitted, p.total]).toEqual([4, 6]);
  expect(p.units.get('week1')).toEqual({ submitted: 2, total: 2 });
  expect(p.units.get('week3')).toEqual({ submitted: 0, total: 2 });
  expect(p.next?.item.title).toBe('Beta-Absorption');
  expect(p.next?.trail).toEqual(['Woche 3']);
  expect(p.started).toBe(true);
});

test('a hidden unit still sorts and names its assignments by path', () => {
  const p = courseProgress([
    assignment('basics.intro', 1, 'Einführung', false),
    assignment('advanced.plots', 1, 'Plots', false),
  ]);
  expect(p.next?.item.title).toBe('Plots'); // siblings with equal position fall back to path
  expect(p.next?.trail).toEqual(['Advanced']);
  expect(p.started).toBe(false);
});

test('nothing left to do means no pointer, and the bar reaches 100 only then', () => {
  const done = courseProgress(CONTENTS.map((c) => ({ ...c, submitted: true })));
  expect(done.next).toBeNull();
  expect(progressPercent(done)).toBe(100);
  expect(progressPercent({ submitted: 199, total: 200 })).toBe(99);
  expect(progressPercent({ submitted: 0, total: 0 })).toBe(0);
});

// --- the screens ----------------------------------------------------------------------

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function signIn(page: Page, { contents = CONTENTS, roles = ['_student'], systemRoles = [], workspace = false }: { contents?: Row[]; roles?: string[]; systemRoles?: string[]; workspace?: boolean } = {}) {
  const requested: string[] = [];
  await page.addInitScript((systemRoles) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles, language: null,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, systemRoles);
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    requested.push(path);
    if (path === '/students/course-contents') return json(route, contents);
    if (path === `/courses/${COURSE_ID}/workspace-settings`) return json(route, {
      course_id: COURSE_ID,
      templates: workspace ? [{ template_name: 'vscode-workspace', display_name: 'VS Code', enabled: true, exists_in_coder: true }] : [],
    });
    if (path === '/coder/templates') return json(route, {
      templates: workspace ? [{ id: 't-vscode', name: 'vscode-workspace', display_name: 'VS Code' }] : [], preparing: [],
    });
    if (path === '/coder/workspaces') return json(route, { workspaces: [] });
    if (path === `/user/courses/${COURSE_ID}/self-enrollment`) return json(route, { detail: 'Not found' }, 404);
    if (path === `/user/courses/${COURSE_ID}/repository`) return json(route, { detail: 'Not found' }, 404);
    if (path === `/user/courses/${COURSE_ID}/git`) return json(route, { configured: false });
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    if (path === '/courses') return json(route, [COURSE]);
    if (path === '/organizations/o-1') return json(route, { id: 'o-1', title: 'TU Graz' });
    if (path === '/course-families/f-1') return json(route, { id: 'f-1', title: 'Data Science mit Python' });
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { [COURSE_ID]: roles } });
    if (path === '/user') {
      return json(route, { id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner', user_roles: systemRoles.map((role_id) => ({ role_id })) });
    }
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
  return requested;
}

test.describe('German learner', () => {
  test.use({ locale: 'de-AT' });

  test('the course page shows the bar and links to where the learner left off', async ({ page }) => {
    await signIn(page);
    await page.goto(`/courses/${COURSE_ID}`);

    const card = page.getByTestId('course-progress');
    await expect(page.getByRole('heading', { name: 'Dein Fortschritt' })).toBeVisible({ timeout: 15_000 });
    await expect(card.getByText('4 von 6 Aufgaben eingereicht')).toBeVisible();
    await expect(card.getByRole('progressbar', { name: 'Eingereichte Aufgaben' })).toHaveAttribute('aria-valuenow', '67');
    await expect(card).toContainText('Weiter mit: Woche 3 › Beta-Absorption (zuletzt getestet: 0%)');
    await expect(card.getByRole('link', { name: 'Aufgabe lesen' })).toHaveAttribute(
      'href', `/courses/${COURSE_ID}/student/assignments/a-week3.beta`,
    );
    await expect(card.getByRole('link', { name: 'Alle Aufgaben' })).toHaveAttribute(
      'href', `/courses/${COURSE_ID}/student/assignments`,
    );
  });

  test('a new learner is told where to begin', async ({ page }) => {
    await signIn(page, { contents: CONTENTS.map((c) => ({ ...c, submitted: false, result: null })) });
    await page.goto(`/courses/${COURSE_ID}`);
    await expect(page.getByTestId('course-progress')).toContainText(
      'Beginne mit: Woche 1 › Mathematische Konstanten', { timeout: 15_000 },
    );
    await expect(page.getByText('0 von 6 Aufgaben eingereicht')).toBeVisible();
  });

  test('a learner who has submitted everything gets a done state instead of a pointer', async ({ page }) => {
    await signIn(page, { contents: CONTENTS.map((c) => ({ ...c, submitted: true })) });
    await page.goto(`/courses/${COURSE_ID}`);
    const card = page.getByTestId('course-progress');
    await expect(card.getByText('Du hast alle Aufgaben eingereicht.', { exact: false })).toBeVisible({ timeout: 15_000 });
    await expect(card.getByRole('link', { name: 'Aufgabe lesen' })).toHaveCount(0);
  });

  test('the assignment list counts each unit and marks the next assignment', async ({ page }) => {
    await signIn(page);
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);

    await expect(page.getByTestId('course-progress')).toContainText('Weiter mit: Woche 3 › Beta-Absorption', { timeout: 15_000 });
    await expect(page.getByText('2/2 eingereicht')).toHaveCount(2);
    await expect(page.getByText('0/2 eingereicht')).toBeVisible();
    const marked = page.getByText('Weiter hier', { exact: true });
    await expect(marked).toHaveCount(1);
    await expect(page.locator('div', { has: marked }).filter({ hasText: 'Beta-Absorption' }).last()).toBeVisible();
  });
});

test.describe('German learner on a phone', () => {
  test.use({ locale: 'de-AT', viewport: { width: 390, height: 844 } });

  test('the assignment titles stay readable and the badges move below them', async ({ page }) => {
    await signIn(page);
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);
    const row = page.locator('.truncate', { hasText: 'Python Grundlagen Review' });
    await expect(row).toBeAttached({ timeout: 15_000 });
    const collapse = page.getByRole('button', { name: 'Seitenleiste einklappen' });
    if (await collapse.isVisible()) await collapse.click();
    await expect(page.getByRole('button', { name: 'Seitenleiste ausklappen' })).toBeVisible();
    await expect.poll(async () => (await page.getByRole('complementary').boundingBox())?.width).toBe(64);
    // The sidebar slides shut, so the width is polled rather than read once.
    await expect.poll(async () => (await row.boundingBox())?.width ?? 0).toBeGreaterThan(120);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBe(0);
  });
});

test.describe('English learner', () => {
  test('the card speaks English', async ({ page }) => {
    await signIn(page);
    await page.goto(`/courses/${COURSE_ID}`);
    const card = page.getByTestId('course-progress');
    await expect(page.getByRole('heading', { name: 'Your progress' })).toBeVisible({ timeout: 15_000 });
    await expect(card.getByText('4 of 6 assignments submitted')).toBeVisible();
    await expect(card).toContainText('Continue with: Woche 3 › Beta-Absorption (last tested: 0%)');
    await expect(card.getByRole('link', { name: 'Read task', exact: true })).toHaveAttribute(
      'href', `/courses/${COURSE_ID}/student/assignments/a-week3.beta`,
    );
  });
});

test('a tutor sees no learner progress and the page does not ask for it', async ({ page }) => {
  const requested = await signIn(page, { roles: ['_tutor'] });
  await page.goto(`/courses/${COURSE_ID}`);
  await expect(page.getByRole('heading', { name: COURSE.title })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('course-progress')).toHaveCount(0);
  expect(requested).not.toContain('/students/course-contents');
});

for (const language of ['de', 'en'] as const) {
  test.describe(`Returning to mounted progress (${language})`, () => {
    test.use({ locale: language === 'de' ? 'de-DE' : 'en-US' });

    for (const [destination, returnEvent] of [
      ['overview', 'focus'], ['overview', 'visibilitychange'],
      ['assignments', 'focus'], ['assignments', 'visibilitychange'],
    ] as const) {
      test(`${destination}: ${returnEvent} refreshes counts and the next assignment without navigation`, async ({ page }) => {
        const initial = CONTENTS.map((c) => ({ ...c, submitted: false, result: null }));
        const requested = await signIn(page, { contents: initial });
        const path = `/courses/${COURSE_ID}${destination === 'assignments' ? '/student/assignments' : ''}`;
        await page.goto(path);
        const card = page.getByTestId('course-progress');
        const count = language === 'de' ? '0 von 6 Aufgaben eingereicht' : '0 of 6 assignments submitted';
        await expect(card).toContainText(count);
        await page.waitForLoadState('networkidle');
        const mountedCard = await card.elementHandle();
        const requestsBefore = requested.length;

        // The workspace submitted the first assignment while this page stayed open.
        const updated = initial.map((c) => c.id === 'a-week1.constants' ? { ...c, submitted: true } : c);
        let refreshRequests = 0;
        let finishRefresh!: () => void;
        const responseReady = new Promise<void>((resolve) => { finishRefresh = resolve; });
        await page.route(`${API_ORIGIN}/students/course-contents?**`, async (route) => {
          refreshRequests += 1;
          await responseReady;
          await json(route, updated);
        });
        await page.evaluate((event) => {
          const target = event === 'focus' ? window : document;
          target.dispatchEvent(new Event(event));
          target.dispatchEvent(new Event(event));
        }, returnEvent);
        await expect.poll(() => refreshRequests).toBe(1);
        finishRefresh();

        await expect(card).toContainText(language === 'de' ? '1 von 6 Aufgaben eingereicht' : '1 of 6 assignments submitted');
        await expect(card.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '17');
        await expect(card).toContainText(language === 'de' ? 'Weiter mit: Woche 1 › Listen' : 'Continue with: Woche 1 › Listen');
        await expect(card.getByRole('link', { name: language === 'de' ? 'Aufgabe lesen' : 'Read task', exact: true })).toHaveAttribute(
          'href', `/courses/${COURSE_ID}/student/assignments/a-week1.lists`,
        );
        expect(await mountedCard?.evaluate((node) => node === document.querySelector('[data-testid="course-progress"]'))).toBe(true);
        expect(new URL(page.url()).pathname).toBe(path);
        // The existing workspace templates refresh on visibility only where
        // the workspace component now lives. Other resources must stay untouched.
        expect(requested.slice(requestsBefore)).toEqual(
          destination === 'assignments' && returnEvent === 'visibilitychange'
            ? ['/coder/templates', '/coder/templates'] : [],
        );
        expect(refreshRequests).toBe(1); // Duplicate return events share the pending refresh.
      });
    }
  });
}

for (const language of ['de', 'en'] as const) {
  test.describe(`Learner workspace location (${language})`, () => {
    test.use({ locale: language === 'de' ? 'de-DE' : 'en-US', viewport: { width: 390, height: 844 } });
    test('the workspace entry moves to assignments even with empty or failed content', async ({ page }) => {
      await signIn(page, { workspace: true, contents: [] });
      const heading = language === 'de' ? 'Arbeitsumgebungen' : 'Workspaces';
      await page.goto(`/courses/${COURSE_ID}`);
      await expect(page.getByRole('heading', { name: COURSE.title })).toBeVisible();
      await expect(page.getByRole('heading', { name: heading, exact: true })).toHaveCount(0);
      if (language === 'en') {
        await page.route(`${API_ORIGIN}/students/course-contents?**`, (route) => json(route, { detail: 'Unavailable' }, 503));
      }
      await page.goto(`/courses/${COURSE_ID}/student/assignments`);
      await expect(page.getByRole('heading', { name: heading, exact: true })).toHaveCount(1);
      const collapse = page.getByRole('button', { name: language === 'de' ? 'Seitenleiste einklappen' : 'Collapse sidebar' });
      if (await collapse.isVisible()) await collapse.click();
      await expect(page.getByRole('button', { name: language === 'de' ? 'Seitenleiste ausklappen' : 'Expand sidebar' })).toBeVisible();
      await expect.poll(async () => (await page.getByRole('complementary').boundingBox())?.width).toBe(64);
      await expect(page.getByRole('button', { name: /VS Code/ })).toBeVisible();
      const empty = page.getByRole('heading', { name: language === 'de' ? 'Noch keine Aufgaben' : 'No assignments yet' });
      await empty.scrollIntoViewIfNeeded();
      await expect(empty).toBeVisible();
    });
  });
}

for (const access of [
  { name: 'tutor', roles: ['_student', '_tutor'], systemRoles: [] },
  { name: 'administrator', roles: ['_student'], systemRoles: ['_admin'] },
  { name: 'organization manager', roles: ['_student'], systemRoles: ['_organization_manager'] },
]) {
  test(`${access.name} keeps the workspace entry on the overview`, async ({ page }) => {
    await signIn(page, { ...access, workspace: true });
    await page.goto(`/courses/${COURSE_ID}`);
    await expect(page.getByRole('heading', { name: 'Workspaces', exact: true })).toHaveCount(1);
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);
    await expect(page.getByRole('heading', { name: 'Assignments', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Workspaces', exact: true })).toHaveCount(0);
  });
}

test('a course without templates offers no workspace entry on assignments', async ({ page }) => {
  await signIn(page);
  await page.goto(`/courses/${COURSE_ID}/student/assignments`);
  await expect(page.getByRole('heading', { name: 'Assignments', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Workspaces', exact: true })).toHaveCount(0);
});


test('a non-member gets no course workspace entry', async ({ page }) => {
  const requested = await signIn(page, { workspace: true, roles: [] });
  for (const path of [`/courses/${COURSE_ID}`, `/courses/${COURSE_ID}/student/assignments`]) {
    await page.goto(path);
    await expect(page.getByRole('heading', { name: path.endsWith('/assignments') ? 'Assignments' : COURSE.title, exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Workspaces', exact: true })).toHaveCount(0);
  }
  expect(requested).not.toContain(`/courses/${COURSE_ID}/workspace-settings`);
});
