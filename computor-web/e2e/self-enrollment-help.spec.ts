import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Self-enrolment on the course page (issues#458): a learner who joined through
 * the catalog sees who answers what (Lena, the support team, the guides) and
 * can leave the course again. A learner enrolled by staff sees neither, and an
 * account deletion is a preset support request.
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
  public: true,
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

type Enrollment = { self_registered: boolean; can_leave: boolean } | null;

async function signIn(page: Page, enrollment: Enrollment) {
  const calls: { method: string; path: string; body: string }[] = [];
  let left = false;
  await page.addInitScript(() => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'learner', username: 'learner', email: 'learner@example.org',
      givenName: 'Course', familyName: 'Learner', role: 'student', systemRoles: [], language: null,
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  });
  await page.route(`${API_ORIGIN}/**`, (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    calls.push({ method: request.method(), path, body: request.postDataBuffer()?.toString('utf8') ?? '' });
    if (path === `/user/courses/${COURSE_ID}/leave` && request.method() === 'POST') {
      left = true;
      return route.fulfill({ status: 204 });
    }
    if (path === `/user/courses/${COURSE_ID}/self-enrollment`) {
      return enrollment && !left ? json(route, { course_id: COURSE_ID, ...enrollment }) : json(route, { detail: 'Not found' }, 404);
    }
    if (path === `/user/courses/${COURSE_ID}/repository`) return json(route, { detail: 'Not found' }, 404);
    if (path === `/user/courses/${COURSE_ID}/git`) return json(route, { configured: false });
    if (path === `/courses/${COURSE_ID}`) return json(route, COURSE);
    if (path === '/courses') return json(route, left ? [] : [COURSE]);
    if (path === '/organizations/o-1') return json(route, { id: 'o-1', title: 'TU Graz' });
    if (path === '/course-families/f-1') return json(route, { id: 'f-1', title: 'Data Science mit Python' });
    if (path === '/user/views') return json(route, ['student']);
    if (path === '/user/scopes') {
      return json(route, { is_admin: false, course: left ? {} : { [COURSE_ID]: ['_student'] } });
    }
    if (path === '/user') {
      return json(route, { id: 'learner', email: 'learner@example.org', given_name: 'Course', family_name: 'Learner', user_roles: [] });
    }
    if (path === '/instance-info') return json(route, { issue_reporting: { enabled: true, mode: 'tickets' } });
    if (path === '/issue-reports') {
      return json(route, { report_id: 't-1', issue_number: 3, ticket_id: 't-1', ticket_number: 3, screenshot_attached: false, log_attached: false }, 201);
    }
    if (path.startsWith('/messages') || path.endsWith('/workspace-templates')) return json(route, []);
    return json(route, {});
  });
  return calls;
}

test.describe('German learner', () => {
  test.use({ locale: 'de-AT' });

  test('a self-enrolled learner sees help and contact and can leave the course', async ({ page }) => {
    const calls = await signIn(page, { self_registered: true, can_leave: true });
    await page.goto(`/courses/${COURSE_ID}`);

    const help = page.getByRole('heading', { name: 'Hilfe & Kontakt' });
    await expect(help).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Fragen zum Kurs?', { exact: false })).toBeVisible();
    await expect(page.getByText('@lena', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Problem melden' }).last()).toHaveAttribute(
      'href', `/problem?from=${encodeURIComponent(`/courses/${COURSE_ID}`)}`,
    );
    // Guides, export and account deletion wait behind "Mehr Hilfe".
    await expect(page.getByRole('link', { name: 'Konto löschen' })).toHaveCount(0);
    await page.getByText('Mehr Hilfe', { exact: true }).click();
    await expect(page.getByRole('link', { name: 'Mit VS Code auf dem eigenen Rechner arbeiten' })).toHaveAttribute(
      'href', /computor-vscode\/blob\/main\/docs\/user-guide\.md#getting-started$/,
    );
    await expect(page.getByRole('link', { name: 'Eigene Dateien herunterladen' })).toHaveAttribute(
      'href', /#keeping-a-copy-of-your-work$/,
    );
    await expect(page.getByRole('link', { name: 'Konto löschen' })).toHaveAttribute(
      'href', /^\/problem\?topic=delete-account/,
    );

    await page.getByRole('button', { name: 'Kurs verlassen' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByText(`Du wirst aus ${COURSE.title} ausgetragen. Deine Abgaben bleiben gespeichert.`, { exact: true })).toBeVisible();
    await dialog.getByRole('button', { name: 'Kurs verlassen' }).click();

    await expect(page).toHaveURL(/\/courses$/);
    await expect(page.getByText(`Du hast ${COURSE.title} verlassen.`)).toBeVisible();
    expect(calls.filter((c) => c.method === 'POST' && c.path === `/user/courses/${COURSE_ID}/leave`)).toHaveLength(1);
  });

  test('cancelling the dialog leaves the enrolment alone', async ({ page }) => {
    const calls = await signIn(page, { self_registered: true, can_leave: true });
    await page.goto(`/courses/${COURSE_ID}`);
    await page.getByRole('button', { name: 'Kurs verlassen' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Abbrechen' }).click();

    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(calls.filter((c) => c.path.endsWith('/leave'))).toHaveLength(0);
  });

  test('a learner enrolled by staff sees neither the help block nor the leave button', async ({ page }) => {
    await signIn(page, { self_registered: false, can_leave: false });
    await page.goto(`/courses/${COURSE_ID}`);
    await expect(page.getByRole('heading', { name: 'Über den Kurs' }).or(page.getByRole('heading', { name: COURSE.title }))).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('heading', { name: 'Hilfe & Kontakt' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Kurs verlassen' })).toHaveCount(0);
  });

  test('a self-enrolled tutor gets the help but cannot leave here', async ({ page }) => {
    await signIn(page, { self_registered: true, can_leave: false });
    await page.goto(`/courses/${COURSE_ID}`);
    await expect(page.getByRole('heading', { name: 'Hilfe & Kontakt' })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: 'Kurs verlassen' })).toHaveCount(0);
  });

  test('"Konto löschen" opens the report form with that topic preset', async ({ page }) => {
    const calls = await signIn(page, { self_registered: true, can_leave: true });
    await page.goto(`/problem?topic=delete-account&from=${encodeURIComponent(`/courses/${COURSE_ID}`)}`);

    await expect(page.getByLabel('Anliegen')).toHaveValue('delete-account', { timeout: 15_000 });
    await expect(page.getByLabel('Titel (optional)')).toHaveValue('Konto löschen');
    await expect(page.getByLabel('Deine Anfrage')).toHaveValue('Bitte löscht mein Computor-Konto.');
    await page.getByRole('button', { name: 'Meldung senden' }).click();

    await expect(page.getByText('Ticket #3')).toBeVisible();
    const report = calls.find((c) => c.path === '/issue-reports');
    expect(report?.body).toContain('Konto löschen');
    expect(report?.body).toContain('"topic":"delete_account"');
  });
});

test('the English course page offers the same help', async ({ page }) => {
  await signIn(page, { self_registered: true, can_leave: true });
  await page.goto(`/courses/${COURSE_ID}`);
  await expect(page.getByRole('heading', { name: 'Help & contact' })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Questions? Write', { exact: false })).toBeVisible();
  await expect(page.getByText('More help', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Leave course' })).toBeVisible();
});
