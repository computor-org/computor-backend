import { expect, test, type Page, type Route } from '@playwright/test';

const API = 'http://localhost:8000';
const COURSE = '00000000-0000-0000-0000-000000000001';
const ASSIGNMENT = '00000000-0000-0000-0000-000000000002';
const JOB = '00000000-0000-0000-0000-000000000003';

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page, enabled: boolean) {
  await page.addInitScript(() => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: 'u-me', username: 'me', email: 'me@example.org',
      givenName: 'Ada', familyName: 'Learner', role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  });
  const sent: unknown[] = [];
  await page.route(`${API}/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === '/user') return json(route, { id: 'u-me', username: 'me', email: 'me@example.org' });
    if (path.startsWith('/user/views')) return json(route, ['student']);
    if (path === '/user/scopes') return json(route, { is_admin: false });
    if (path.startsWith('/messages')) return json(route, []);
    if (path === `/courses/${COURSE}`) return json(route, { id: COURSE, title: 'Open course', public: true });
    if (path === `/students/course-contents/${ASSIGNMENT}`) {
      return json(route, { id: ASSIGNMENT, title: 'Loop', status: null, submitted: false,
        result_count: 0, submission_count: 0, description: 'Write a loop' });
    }
    if (path === '/public-luna/availability') return json(route, { enabled });
    if (path === '/public-luna/requests' && request.method() === 'POST') {
      sent.push(request.postDataJSON());
      return json(route, { id: JOB, state: 'queued' }, 202);
    }
    if (path === `/public-luna/requests/${JOB}`) {
      return json(route, { state: 'done', answer: '<script>alert(1)</script> Try a nonempty list.' });
    }
    return json(route, {});
  });
  return sent;
}

test('public Luna form appears only when enabled and renders the answer as text', async ({ page }) => {
  const sent = await setup(page, true);
  await page.goto(`/courses/${COURSE}/student/assignments/${ASSIGNMENT}`);
  await expect(page.getByRole('heading', { name: 'Ask Luna' })).toBeVisible();
  await page.getByLabel('Question').fill('Why is it empty?');
  await page.getByLabel('Your code or result').fill('for x in []: print(x)');
  await page.getByRole('button', { name: 'Ask Luna' }).click();
  await expect(page.getByText('<script>alert(1)</script> Try a nonempty list.')).toBeVisible();
  expect(await page.locator('script:has-text("alert(1)")').count()).toBe(0);
  expect(sent).toEqual([{ course_content_id: ASSIGNMENT,
    question: 'Why is it empty?', submitted_text: 'for x in []: print(x)' }]);
});

test('disabled public Luna leaves the assignment page usable', async ({ page }) => {
  await setup(page, false);
  await page.goto(`/courses/${COURSE}/student/assignments/${ASSIGNMENT}`);
  await expect(page.getByRole('heading', { name: 'Description' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ask Luna' })).toHaveCount(0);
});
