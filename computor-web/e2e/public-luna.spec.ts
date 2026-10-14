import { expect, test, type Page, type Route } from '@playwright/test';

const API = 'http://localhost:8000';
const COURSE = '00000000-0000-0000-0000-000000000001';
const ASSIGNMENT = '00000000-0000-0000-0000-000000000002';
const JOB = '00000000-0000-0000-0000-000000000003';
// Luna writes Markdown (issues#457); the HTML, image and script link are model
// output that must not become markup, a request or a clickable link.
const ANSWER = [
  '**Hint:** `range(3)` is *not* empty. <script>alert(1)</script>',
  '',
  '```python',
  'for x in range(3):',
  '    print(x)',
  '```',
  '',
  '![tracker](https://tracker.invalid/pixel.png) [docs](https://docs.python.org/3/) [bad](javascript:alert(2))',
  '',
  '$$\n\\begin{aligned}\nx_1 &= 2 \\\\\nx_2 &= 3\n\\end{aligned}\n$$',
].join('\n');

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
      return json(route, { state: 'done', answer: ANSWER });
    }
    return json(route, {});
  });
  return sent;
}

test('public Luna form appears only when enabled and renders the answer as Markdown', async ({ page }) => {
  const sent = await setup(page, true);
  const fetched: string[] = [];
  page.on('request', (request) => { fetched.push(request.url()); });
  await page.goto(`/courses/${COURSE}/student/assignments/${ASSIGNMENT}`);
  await expect(page.getByRole('heading', { name: 'Ask Luna' })).toBeVisible();
  await page.getByLabel('Question').fill('Why is it empty?');
  await page.getByLabel('Your code or result').fill('for x in []: print(x)');
  await page.getByRole('button', { name: 'Ask Luna' }).click();

  const answer = page.getByTestId('luna-answer');
  await expect(answer.locator('strong')).toHaveText('Hint:');
  await expect(answer.locator('em')).toHaveText('not');
  await expect(answer.locator('p code')).toHaveText('range(3)');
  await expect(answer.locator('pre code')).toHaveText('for x in range(3):\n    print(x)');
  const text = await answer.innerText();
  expect(text).not.toContain('**');
  expect(text).not.toContain('```');
  expect(text).not.toContain('`range');
  await expect(answer.locator('.katex-display .mtable')).toBeVisible();
  await expect(answer.locator('.katex-error')).toHaveCount(0);

  // Model output: no markup, no fetched image, no script link.
  expect(text).not.toContain('<script>');
  expect(await page.locator('script:has-text("alert(1)")').count()).toBe(0);
  await expect(answer.locator('img')).toHaveCount(0);
  await expect(answer).toContainText('tracker');
  expect(fetched.some((url) => url.includes('tracker.invalid'))).toBe(false);
  await expect(answer.getByRole('link', { name: 'docs' })).toHaveAttribute('href', 'https://docs.python.org/3/');
  await expect(answer.getByRole('link', { name: 'bad' })).toHaveCount(0);
  await expect(answer).toContainText('bad');

  expect(sent).toEqual([{ course_content_id: ASSIGNMENT,
    question: 'Why is it empty?', submitted_text: 'for x in []: print(x)' }]);
});

test('disabled public Luna leaves the assignment page usable', async ({ page }) => {
  await setup(page, false);
  await page.goto(`/courses/${COURSE}/student/assignments/${ASSIGNMENT}`);
  await expect(page.getByRole('heading', { name: 'Description' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ask Luna' })).toHaveCount(0);
});
