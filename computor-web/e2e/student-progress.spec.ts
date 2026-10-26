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
const COURSE_ID = '10000000-0000-4000-8000-000000000001';
const EDITOR = 'http://localhost:8080/coder/learner/vscode/';
const OWN_WORKSPACE = { id: 'personal', name: 'vscode', owner_name: 'learner', owner_id: 'learner', template_name: 'vscode-workspace', latest_build_status: 'succeeded' };
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
  description?: string;
  course_id?: string;
  visible_effective?: boolean;
  has_deployment?: boolean;
  result_count?: number;
  submission_count?: number;
  status?: string;
  submission_group?: { id: string; grading?: number };
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

async function signIn(page: Page, { contents = CONTENTS, roles = ['_student'], systemRoles = [], workspace = false, workspaceState = 'running' }: { contents?: Row[]; roles?: string[]; systemRoles?: string[]; workspace?: boolean; workspaceState?: 'running' | 'stopped' | 'missing' } = {}) {
  const requested: string[] = [];
  await page.addInitScript((systemRoles) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles, language: null,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, systemRoles);
  let state = workspaceState;
  await page.context().route(`${EDITOR}**`, (route) => route.fulfill({ status: 200, contentType: 'text/html', body: '<h1>Personal editor</h1>' }));
  await page.context().route(`${API_ORIGIN}/**`, (route) => {
    const path = new URL(route.request().url()).pathname;
    requested.push(path);
    if (path === '/students/course-contents') return json(route, contents.map((item) => ({ ...item, course_id: item.course_id ?? COURSE_ID, visible_effective: item.visible_effective ?? true, has_deployment: item.has_deployment ?? item.course_content_kind_id === 'assignment' })));
    if (path.startsWith('/students/course-contents/')) {
      const item = contents.find((item) => item.id === path.split('/')[3]);
      return item ? json(route, { ...item, course_id: COURSE_ID, has_deployment: item.has_deployment ?? item.course_content_kind_id === 'assignment', visible_effective: item.visible_effective ?? true }) : json(route, { detail: 'Not found' }, 404);
    }
    if (path === `/courses/${COURSE_ID}/workspace-settings`) return json(route, {
      course_id: COURSE_ID,
      templates: workspace ? [{ template_name: 'vscode-workspace', display_name: 'VS Code', enabled: true, exists_in_coder: true }] : [],
    });
    if (path === '/coder/templates') return json(route, {
      templates: workspace ? [{ id: 't-vscode', name: 'vscode-workspace', display_name: 'VS Code' }] : [], preparing: [],
    });
    if (path === '/coder/workspaces') return json(route, { workspaces: workspace && state !== 'missing' ? [OWN_WORKSPACE] : [] });
    if (path === '/coder/workspaces/provision') {
      state = 'running';
      return json(route, { workspace: OWN_WORKSPACE, user: { username: 'learner' }, created_workspace: true });
    }
    if (path === '/coder/workspaces/learner/vscode/launch-context') return json(route, { ...route.request().postDataJSON(), request_id: 'targeted', expires_at: '2099-01-01T00:00:00Z' });
    if (path === '/coder/workspaces/learner/vscode/start') {
      state = 'running';
      return json(route, { success: true });
    }
    if (path === '/coder/workspaces/learner/vscode') return json(route, {
      workspace: OWN_WORKSPACE, status: state, access_url: state === 'running' ? EDITOR : null,
      code_server_url: state === 'running' ? EDITOR : null, ready: state === 'running', agent_lifecycle: 'ready', resources: {},
    });
    if (path === `/user/courses/${COURSE_ID}/self-enrollment`) return json(route, { detail: 'Not found' }, 404);
    if (path === `/user/courses/${COURSE_ID}/repository`) return json(route, { detail: 'Not found' }, 404);
    if (path === `/user/courses/${COURSE_ID}/git`) return json(route, { configured: false });
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    if (path === '/courses') return json(route, [COURSE]);
    if (path === '/organizations/o-1') return json(route, { id: 'o-1', title: 'TU Graz' });
    if (path === '/course-families/f-1') return json(route, { id: 'f-1', title: 'Data Science mit Python' });
    if (path.startsWith('/user/views')) return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false, course: { [COURSE_ID]: roles } });
    if (path === '/user') {
      return json(route, { id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner', user_roles: systemRoles.map((role_id) => ({ role_id })) });
    }
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates') || path === '/results' || path === '/submissions/artifacts') return json(route, []);
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
    // The title opens the task page, as on main, rather than VS Code.
    await expect(card.getByRole('link', { name: 'Beta-Absorption', exact: true })).toHaveAttribute(
      'href', new RegExp(`^/courses/${COURSE_ID}/student/assignments/[^/?]+$`),
    );
    await expect(card.getByRole('link', { name: 'Aufgabe lesen' })).toHaveCount(0);
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

  test('the assignment list counts each unit and names the next assignment once', async ({ page }) => {
    await signIn(page);
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);

    await expect(page.getByTestId('course-progress')).toContainText('Weiter mit: Woche 3 › Beta-Absorption', { timeout: 15_000 });
    await expect(page.getByText('2/2 eingereicht')).toHaveCount(2);
    await expect(page.getByText('2 Elemente', { exact: true })).toBeVisible();
    // Only the "Weiter mit" line points at it; the row has no second marker.
    await expect(page.getByText('Weiter hier', { exact: true })).toHaveCount(0);
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
    await expect(card.getByRole('link', { name: 'Beta-Absorption', exact: true })).toBeVisible();
    await expect(card.getByRole('link', { name: 'Read task', exact: true })).toHaveCount(0);
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
        await expect(card.getByRole('link', { name: 'Listen', exact: true })).toBeVisible();
        expect(await mountedCard?.evaluate((node) => node === document.querySelector('[data-testid="course-progress"]'))).toBe(true);
        expect(new URL(page.url()).pathname).toBe(path);
        // The existing workspace templates refresh on visibility only where
        // the workspace component now lives. Other resources must stay untouched.
        expect(requested.slice(requestsBefore)).toEqual(
          returnEvent === 'visibilitychange'
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
      await expect(page.getByRole('button', { name: /VS Code/ })).toHaveCount(1);
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

const FIRST = '20000000-0000-4000-8000-000000000001';
const SECOND = '20000000-0000-4000-8000-000000000002';
const WELCOME = '20000000-0000-4000-8000-000000000003';
const EXACT_CONTENTS: Row[] = [
  { ...unit('introduction', 0, 'Course introduction'), id: WELCOME, description: 'Authored introduction', has_deployment: false },
  unit('topic_a', 1, 'Topic A'), { ...unit('topic_b', 2, 'Topic B'), description: 'Container description' },
  { ...assignment('topic_a.first', 1, 'First exercise', false, 0), id: FIRST, description: 'Exercise instructions' },
  { ...assignment('topic_b.second', 1, 'Second exercise', false), id: SECOND, description: 'Second instructions' },
];

function recordTargets(page: Page) {
  const targets: { course_id: string; course_content_id: string; ui_language: string }[] = [];
  page.context().on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/launch-context')) {
      targets.push(request.postDataJSON());
    }
  });
  return targets;
}

for (const language of ['de', 'en'] as const) {
  test.describe(`Exact exercise entry (${language})`, () => {
    test.use({ locale: language === 'de' ? 'de-DE' : 'en-US' });
    test('one primary action, titles that open the task page, and one VS Code button there', async ({ page }) => {
      const requested = await signIn(page, { contents: EXACT_CONTENTS, workspace: true });
      const targets = recordTargets(page);
      await page.goto(`/courses/${COURSE_ID}/student/assignments`);
      const openLabel = language === 'de' ? 'In VS Code öffnen' : 'Open in VS Code';
      const primary = page.getByRole('button', { name: openLabel, exact: true });
      await expect(primary).toHaveCount(1);
      await expect(page.getByRole('link', { name: /Read task|Aufgabe lesen/ })).toHaveCount(0);
      await expect(page.getByRole('button', { name: /^(Expand all|Collapse all|Alle ausklappen|Alle einklappen)$/ })).toHaveCount(0);
      await expect(page.getByRole('button', { name: 'Topic B', exact: true })).toHaveAttribute('aria-expanded', 'false');
      await expect(page.getByRole('link', { name: 'Second exercise', exact: true })).toHaveCount(0);
      // A learner row is title · status · score · results: no usage badge.
      await expect(page.getByText(/\d+[TA] \/ /)).toHaveCount(0);
      await expect(page.getByRole('link', { name: language === 'de' ? 'Ergebnisse' : 'Results', exact: true })).toHaveAttribute('href', `/courses/${COURSE_ID}/student/assignments/${FIRST}`);
      await expect(page.locator(`[title="${language === 'de' ? 'Letztes Testergebnis' : 'Latest test result'}"]`)).toContainText('0%');
      await page.getByRole('button', { name: 'Topic B', exact: true }).click();
      for (const [name, id] of [['First exercise', FIRST], ['Second exercise', SECOND], ['Course introduction', WELCOME]] as const) {
        // .last(): the row, below the "Weiter mit" line that may name the same task.
        await expect(page.getByRole('link', { name, exact: true }).last()).toHaveAttribute('href', `/courses/${COURSE_ID}/student/assignments/${id}`);
      }
      const settingsBefore = requested.filter((path) => path.endsWith('/workspace-settings')).length;
      let popupReady = page.waitForEvent('popup');
      await primary.click();
      let editor = await popupReady;
      await expect(editor).toHaveURL(EDITOR);
      expect(targets.at(-1)).toEqual({ course_id: COURSE_ID, course_content_id: FIRST, ui_language: language });
      await editor.close();
      expect(requested.filter((path) => path.endsWith('/workspace-settings'))).toHaveLength(settingsBefore);

      // A title shows the task; VS Code opens only from the page's one button.
      await page.getByRole('link', { name: 'Second exercise', exact: true }).click();
      await expect(page).toHaveURL(`/courses/${COURSE_ID}/student/assignments/${SECOND}`);
      await expect(page.getByText('Second instructions', { exact: true })).toBeVisible();
      expect(targets).toHaveLength(1);
      popupReady = page.waitForEvent('popup');
      await page.getByRole('button', { name: openLabel, exact: true }).click();
      editor = await popupReady;
      await expect(editor).toHaveURL(EDITOR);
      expect(targets.at(-1)).toEqual({ course_id: COURSE_ID, course_content_id: SECOND, ui_language: language });
      await editor.close();
      expect(requested).not.toContain('/coder/workspaces/provision');
    });
  });
}

test('the assignment page shows the task and never opens VS Code by itself', async ({ page }) => {
  const requested = await signIn(page, { contents: EXACT_CONTENTS, workspace: true, workspaceState: 'missing' });
  const targets = recordTargets(page);
  await page.goto(`/courses/${COURSE_ID}/student/assignments/${FIRST}`);
  await expect(page.getByRole('heading', { name: 'Description', exact: true })).toBeVisible();
  await expect(page.getByText('Exercise instructions', { exact: true })).toBeVisible();
  await expect(page.getByText('0.0%', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Open in VS Code', exact: true })).toHaveCount(1);
  await page.waitForLoadState('networkidle');
  expect(requested).not.toContain('/coder/workspaces/provision');
  expect(targets).toEqual([]);
  expect(page.url()).toMatch(new RegExp(`/student/assignments/${FIRST}$`));
});

test('German failure on the assignment page is bounded and never exposes raw API text', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await page.addInitScript(() => localStorage.setItem('computor.language', 'de'));
  await signIn(page, { contents: EXACT_CONTENTS, workspace: true });
  await page.context().route(`${API_ORIGIN}/coder/workspaces`, (route) => json(route, { detail: '/private/tester.py: secret internal failure' }, 500));
  await page.goto(`/courses/${COURSE_ID}/student/assignments/${FIRST}`);
  await page.getByRole('button', { name: 'In VS Code öffnen', exact: true }).click();
  await expect(page.getByText('Deine Auswahl konnte in deiner Arbeitsumgebung nicht geöffnet werden. Versuch es noch einmal.', { exact: true })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('/private/tester.py');
  expect(page.context().pages()).toHaveLength(1);
});

test('an explicit public content path resolves its exact UUID instead of the next exercise', async ({ page }) => {
  await signIn(page, { contents: EXACT_CONTENTS, workspace: true, workspaceState: 'stopped' });
  const targets = recordTargets(page);
  await page.goto(`/courses/${COURSE_ID}/student/assignments?contentPath=topic_b.second`);
  await expect(page).toHaveURL(EDITOR);
  expect(targets).toEqual([{ course_id: COURSE_ID, course_content_id: SECOND, ui_language: 'en' }]);
  expect(page.context().pages()).toHaveLength(1);
});

for (const invalid of ['empty', 'unknown', 'hidden', 'other-course', 'unreleased', 'duplicate'] as const) {
  test(`an explicit ${invalid} content path never falls back or provisions`, async ({ page }) => {
    const contents = EXACT_CONTENTS.map((item) => item.id !== SECOND ? item : {
      ...item, visible_effective: invalid !== 'hidden',
      course_id: invalid === 'other-course' ? 'another-course' : COURSE_ID,
      has_deployment: invalid !== 'unreleased',
    });
    const requested = await signIn(page, { contents, workspace: true, workspaceState: 'missing' });
    const query = invalid === 'empty' ? '' : invalid === 'unknown' ? 'absent.path' : 'topic_b.second';
    await page.goto(`/courses/${COURSE_ID}/student/assignments?contentPath=${query}${invalid === 'duplicate' ? '&contentPath=topic_a.first' : ''}`);
    await expect(page.getByRole('main').getByText('This content is not available in this course.', { exact: true })).toBeVisible();
    expect(requested).not.toContain('/coder/workspaces/provision');
    expect(requested.some((path) => path.endsWith('/launch-context'))).toBe(false);
    await expect(page.getByRole('button', { name: /VS Code/ })).toHaveCount(0);
  });
}

test('a missing legacy exercise cannot provision a workspace', async ({ page }) => {
  const requested = await signIn(page, { contents: EXACT_CONTENTS, workspace: true, workspaceState: 'missing' });
  await page.goto(`/courses/${COURSE_ID}/student/assignments/20000000-0000-4000-8000-000000000099`);
  await expect(page.getByRole('main').getByText('Not found', { exact: true })).toBeVisible();
  expect(requested).not.toContain('/coder/workspaces/provision');
});

for (const staff of [
  { name: 'tutor', roles: ['_student', '_tutor'], systemRoles: [] },
  { name: 'administrator', roles: ['_student'], systemRoles: ['_admin'] },
  { name: 'organization manager', roles: ['_student'], systemRoles: ['_organization_manager'] },
]) {
  test(`${staff.name} keeps the existing assignment description and results`, async ({ page }) => {
    const requested = await signIn(page, { ...staff, contents: EXACT_CONTENTS, workspace: true });
    await page.goto(`/courses/${COURSE_ID}/student/assignments/${FIRST}`);
    await expect(page.getByRole('heading', { name: 'Description', exact: true })).toBeVisible();
    await expect(page.getByText('Exercise instructions', { exact: true })).toBeVisible();
    await expect(page.getByText('0.0%', { exact: true })).toBeVisible();
    expect(requested.some((path) => path.endsWith('/launch-context'))).toBe(false);
  });
}


test('an authored unit-only course still mounts one launcher and opens its introduction', async ({ page }) => {
  await signIn(page, { contents: [EXACT_CONTENTS[0]], workspace: true });
  const targets = recordTargets(page);
  await page.goto(`/courses/${COURSE_ID}/student/assignments`);
  await expect(page.getByRole('button', { name: 'Open in VS Code', exact: true })).toHaveCount(1);
  await page.getByRole('link', { name: 'Course introduction', exact: true }).click();
  await expect(page.getByText('Authored introduction', { exact: true })).toBeVisible();
  const popupReady = page.waitForEvent('popup');
  await page.getByRole('button', { name: 'Open in VS Code', exact: true }).click();
  const editor = await popupReady;
  await expect(editor).toHaveURL(EDITOR);
  expect(targets).toEqual([{ course_id: COURSE_ID, course_content_id: WELCOME, ui_language: 'en' }]);
});
for (const language of ['de', 'en'] as const) {
  test(`an untouched course opens its introduction while an explicit exercise stays exact (${language})`, async ({ page }) => {
    await page.addInitScript((language) => localStorage.setItem('computor.language', language), language);
    await signIn(page, { contents: EXACT_CONTENTS.map((item) => ({ ...item, result: null })), workspace: true });
    const targets = recordTargets(page);
    await page.goto(`/courses/${COURSE_ID}/student/assignments`);
    const openLabel = language === 'de' ? 'In VS Code öffnen' : 'Open in VS Code';
    for (const [open, expected] of [
      [async () => {}, { course_id: COURSE_ID, ui_language: language }],
      [async () => {
        await page.getByRole('link', { name: 'First exercise', exact: true }).first().click();
        await expect(page).toHaveURL(`/courses/${COURSE_ID}/student/assignments/${FIRST}`);
      }, { course_id: COURSE_ID, course_content_id: FIRST, ui_language: language }],
    ] as const) {
      await open();
      const popupReady = page.waitForEvent('popup');
      await page.getByRole('button', { name: openLabel, exact: true }).click();
      const editor = await popupReady;
      await expect(editor).toHaveURL(EDITOR);
      expect(targets.at(-1)).toEqual(expected);
      await editor.close();
    }
  });
}
