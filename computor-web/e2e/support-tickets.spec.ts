import { test, expect, type Page, type Route } from '@playwright/test';

/**
 * Support tickets: list, detail, composer and attachment download. The backend
 * is mocked at the network layer with synthetic data; the backend's own pytest
 * covers the endpoints. Set SCREENSHOT_DIR to also save a screenshot of the
 * list and the detail view.
 */

const API_ORIGIN = 'http://localhost:8000';
const T1 = '00000000-0000-0000-0000-0000000000t1';
const T2 = '00000000-0000-0000-0000-0000000000t2';
const MAILBOX = 'contact@example.org';

const USER = {
  id: 'u-sup',
  username: 'sup',
  email: 'sup@example.org',
  given_name: 'Sam',
  family_name: 'Support',
  user_roles: [],
};

const CAPS = {
  can_view: true,
  can_reply: true,
  can_manage: true,
  can_write_internal: true,
  is_admin: false,
  team_addresses: [MAILBOX, 'help@example.org'],
};

const ticketRow = (id: string, number: number, subject: string, restricted: boolean) => ({
  id,
  number,
  subject,
  channel: 'mail',
  status: 'open',
  priority: 'normal',
  restricted,
  mailbox_address: MAILBOX,
  reporter_email: 'reporter@example.org',
  reporter_name: 'Rita Reporter',
  reporter_user_id: null,
  assignee: null,
  message_count: 3,
  last_message_at: '2026-03-02T10:00:00Z',
  created_at: '2026-03-02T09:00:00Z',
  updated_at: '2026-03-02T10:00:00Z',
});

const message = (over: Record<string, unknown>) => ({
  id: 'm',
  visibility: 'public',
  direction: 'in',
  author: null,
  from_address: 'reporter@example.org',
  from_name: 'Rita Reporter',
  to: [MAILBOX],
  cc: [],
  subject: 'Help',
  text: 'plain',
  html: null,
  attachments: [],
  delivery_state: null,
  delivery_error: null,
  created_at: '2026-03-02T09:00:00Z',
  ...over,
});

function detail(status = 'open', assignee: unknown = null) {
  return {
    ...ticketRow(T1, 7, 'Cannot log in', true),
    status,
    assignee,
    messages: [
      message({
        id: 'm1',
        text: 'Literal <b>not markup</b> here',
        html: '<p>Formatted <b>body</b></p>',
        attachments: [
          { id: 'a1', filename: 'report.txt', content_type: 'text/html', size: 2048, stored: true },
          { id: 'a2', filename: 'huge.zip', content_type: 'application/zip', size: 90_000_000, stored: false },
        ],
      }),
      message({
        id: 'm2',
        visibility: 'internal',
        direction: 'note',
        author: { id: 'u-sup', given_name: 'Sam', family_name: 'Support' },
        from_address: null,
        to: [],
        text: 'Checked the logs',
        created_at: '2026-03-02T09:30:00Z',
      }),
      message({
        id: 'm3',
        direction: 'out',
        author: { id: 'u-sup', given_name: 'Sam', family_name: 'Support' },
        from_address: MAILBOX,
        to: ['reporter@example.org'],
        text: 'We are looking into it',
        delivery_state: 'failed',
        delivery_error: 'SMTP connection refused',
        created_at: '2026-03-02T10:00:00Z',
      }),
    ],
    events: [
      { id: 'e1', kind: 'created', actor: null, data: {}, created_at: '2026-03-02T09:00:00Z' },
    ],
  };
}

function json(route: Route, body: unknown, status = 200, headers: Record<string, string> = {}) {
  return route.fulfill({ status, contentType: 'application/json', headers, body: JSON.stringify(body) });
}

type Call = { method: string; path: string; search: string; body: Record<string, unknown> | null };

async function setup(page: Page, caps = CAPS) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  const calls: Call[] = [];
  let current = detail();
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    let body: Record<string, unknown> | null = null;
    try {
      body = req.postDataJSON();
    } catch {
      body = null;
    }
    calls.push({ method: req.method(), path, search: url.search, body });

    if (path.startsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);

    if (path === '/support/capabilities') return json(route, caps);
    if (path === '/support/agents') {
      return json(route, [{ id: 'u-sup', given_name: 'Sam', family_name: 'Support', email: 'sup@example.org', roles: ['_support'] }]);
    }
    if (path === '/support/tickets') {
      return json(route, [ticketRow(T1, 7, 'Cannot log in', true), ticketRow(T2, 8, 'Question about grades', false)], 200, {
        'X-Total-Count': '2',
        'Access-Control-Expose-Headers': 'X-Total-Count',
      });
    }
    if (path === `/support/tickets/${T1}` && req.method() === 'GET') return json(route, current);
    if (path === `/support/tickets/${T1}/claim`) {
      current = detail('in_progress', { id: 'u-sup', given_name: 'Sam', family_name: 'Support' });
      return json(route, current);
    }
    if (path === `/support/tickets/${T1}` && req.method() === 'PATCH') {
      current = { ...current, status: String(body?.status ?? current.status) };
      return json(route, current);
    }
    if (path === `/support/tickets/${T1}/messages`) return json(route, current);
    if (path === `/support/tickets/${T1}/messages/m3/retry`) return json(route, current);
    if (path === `/support/tickets/${T1}/attachments/a1`) {
      return route.fulfill({
        status: 200,
        contentType: 'application/octet-stream',
        headers: { 'Content-Disposition': 'attachment; filename="report.txt"' },
        body: 'synthetic attachment',
      });
    }
    return json(route, {});
  });
  return calls;
}

async function shot(page: Page, name: string) {
  const dir = process.env.SCREENSHOT_DIR;
  if (!dir) return;
  await page.setViewportSize({ width: 1440, height: 1800 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${dir}/${name}.png` });
}

const ticketCalls = (calls: Call[]) => calls.filter((c) => c.path === '/support/tickets');
const lastTicketQuery = (calls: Call[]) => new URLSearchParams(ticketCalls(calls).at(-1)?.search ?? '');

test('support user sees the sidebar entry and a filterable ticket list', async ({ page }) => {
  const calls = await setup(page);
  await page.goto('/support');

  await expect(page.getByRole('link', { name: 'Support', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Cannot log in' })).toBeVisible();
  await expect(page.getByText('restricted', { exact: true })).toHaveCount(1);
  expect(lastTicketQuery(calls).get('scope')).toBe('unassigned');
  await shot(page, 'support-list');

  await page.getByRole('button', { name: 'Mine' }).click();
  await expect.poll(() => lastTicketQuery(calls).get('scope')).toBe('mine');
  await page.getByRole('button', { name: 'All', exact: true }).click();
  await expect.poll(() => lastTicketQuery(calls).get('scope')).toBe('all');

  await page.getByLabel('Status filter').selectOption('waiting');
  await expect.poll(() => lastTicketQuery(calls).get('status')).toBe('waiting');
  await page.getByLabel('Search tickets').fill('login');
  await page.getByRole('button', { name: 'Search' }).click();
  await expect.poll(() => lastTicketQuery(calls).get('search')).toBe('login');
});

test('ticket detail shows text literally and formatted mail only in a sandboxed iframe', async ({ page }) => {
  await setup(page);
  await page.goto(`/support/${T1}`);

  await expect(page.getByText('Literal <b>not markup</b> here')).toBeVisible();
  await expect(page.locator('iframe')).toHaveCount(0);

  await page.getByRole('button', { name: 'Show formatted' }).click();
  const frame = page.locator('iframe');
  await expect(frame).toHaveCount(1);
  expect(await frame.getAttribute('sandbox')).toBe('');
  expect(await frame.getAttribute('referrerpolicy')).toBe('no-referrer');
  const srcdoc = (await frame.getAttribute('srcdoc')) ?? '';
  expect(srcdoc).toContain('http-equiv="Content-Security-Policy"');
  expect(srcdoc).toContain("default-src 'none'");

  await expect(page.getByText('Internal note - not visible to the reporter').first()).toBeVisible();
  await expect(page.getByText('Checked the logs')).toBeVisible();
  await expect(page.getByText('SMTP connection refused')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  await expect(page.getByText('too large, in the mailbox archive')).toBeVisible();
  await shot(page, 'support-detail');
});

test('ticket actions send the expected requests', async ({ page }) => {
  const calls = await setup(page);
  await page.goto(`/support/${T1}`);
  await expect(page.getByRole('button', { name: 'Claim' })).toBeVisible();
  const post = (suffix: string) => calls.filter((c) => c.method === 'POST' && c.path === `/support/tickets/${T1}${suffix}`);

  await page.getByRole('button', { name: 'Retry' }).click();
  await expect.poll(() => post('/messages/m3/retry').length).toBe(1);

  await page.getByRole('button', { name: 'Claim' }).click();
  await expect.poll(() => post('/claim').length).toBe(1);
  await expect(page.getByRole('button', { name: 'Claim' })).toHaveCount(0);

  await page.getByLabel('Status').selectOption('waiting');
  await expect
    .poll(() => calls.find((c) => c.method === 'PATCH')?.body)
    .toEqual({ status: 'waiting' });

  // Internal note: sent without a confirm step.
  await page.getByRole('button', { name: 'Internal note' }).click();
  await page.getByLabel('Internal note', { exact: true }).fill('Remember to call back');
  await page.getByRole('button', { name: 'Add note' }).click();
  await expect.poll(() => post('/messages').length).toBe(1);
  expect(post('/messages')[0].body).toMatchObject({ internal: true, content: 'Remember to call back' });

  // Reply: needs the confirm step and goes out from the ticket's team address.
  await page.getByRole('button', { name: 'Reply by mail' }).click();
  await expect(page.getByRole('textbox', { name: 'To' })).toHaveValue('reporter@example.org');
  await page.getByLabel('Reply text').fill('Please try again');
  await page.getByRole('button', { name: 'Send reply' }).click();
  expect(post('/messages')).toHaveLength(1);
  await page.getByRole('dialog').getByRole('button', { name: 'Send' }).click();
  await expect.poll(() => post('/messages').length).toBe(2);
  expect(post('/messages')[1].body).toMatchObject({
    internal: false,
    from_address: MAILBOX,
    content: 'Please try again',
  });
});

test('attachments download without navigating', async ({ page, context }) => {
  await setup(page);
  await page.goto(`/support/${T1}`);
  const pagesBefore = context.pages().length;

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'report.txt' }).click(),
  ]);
  expect(download.suggestedFilename()).toBe('report.txt');
  expect(context.pages()).toHaveLength(pagesBefore);
  expect(page.url()).toContain(`/support/${T1}`);
});

test('a user without support access sees neither the entry nor tickets', async ({ page }) => {
  const calls = await setup(page, { ...CAPS, can_view: false, can_reply: false, can_manage: false, can_write_internal: false });
  await page.goto('/support');

  await expect(page.getByText('You do not have access to support tickets.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Support', exact: true })).toHaveCount(0);
  expect(ticketCalls(calls)).toHaveLength(0);
});
