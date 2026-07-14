/**
 * Shared e2e fixtures: auth injection + backend network mocking.
 *
 * These tests drive a real `next dev` server and mock the backend at the network
 * layer, so they need no running API or database. Auth is injected into
 * sessionStorage the way the SSO flow leaves it (`auth_user` / `auth_provider`),
 * matching `src/services/authStorage.ts`. Permission gates read the persona's
 * `systemRoles` / `role` (see `src/hooks/usePermissions.ts`), so switching
 * persona is all it takes to exercise a different access level.
 */
import { type Page, type Route } from '@playwright/test';

export const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export type Persona = {
  id: string;
  username: string;
  email: string;
  givenName: string;
  familyName: string;
  role: string;
  systemRoles: string[];
};

export const PERSONAS = {
  admin: mk('u-admin', 'admin1', 'admin', 'Ada', 'Root', 'admin', ['_admin']),
  userManager: mk('u-uma', 'uma', 'uma', 'Ursula', 'Manager', 'user', ['_user_manager']),
  lecturer: mk('u-lena', 'lena', 'lena', 'Lena', 'Lecturer', 'lecturer', []),
  tutor: mk('u-tobi', 'tobi', 'tobi', 'Tobias', 'Tutor', 'tutor', []),
  student: mk('u-stud', 'stud', 'student', 'Cora', 'Correct', 'student', []),
} satisfies Record<string, Persona>;

function mk(
  id: string, username: string, local: string, givenName: string, familyName: string,
  role: string, systemRoles: string[],
): Persona {
  return { id, username, email: `${local}@example.org`, givenName, familyName, role, systemRoles };
}

/** Leave the page authenticated as `persona` (call before `page.goto`). */
export async function injectAuth(page: Page, persona: Persona): Promise<void> {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
    sessionStorage.setItem('auth_provider', 'sso');
  }, persona);
}

export function json(route: Route, body: unknown, status = 200): Promise<void> {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

/** A custom route handler: return true if it handled the request. */
export type RouteHandler = (route: Route, url: URL) => boolean | Promise<boolean>;

export type MockOptions = {
  persona?: Persona;
  isAdmin?: boolean;
  /** Checked before the defaults; return true to take over the request. */
  handlers?: RouteHandler;
};

/**
 * Mock every call to the backend origin. Custom `handlers` run first; the
 * always-called endpoints (`/user`, `/user/scopes`, `/user/views`, `/messages`)
 * fall through to sane defaults so specs only declare what they test.
 */
export async function mockApi(page: Page, opts: MockOptions = {}): Promise<void> {
  const persona = opts.persona ?? PERSONAS.admin;
  const isAdmin = opts.isAdmin ?? persona.systemRoles.includes('_admin');
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (opts.handlers && (await opts.handlers(route, url))) return;
    if (path.endsWith('/user/views')) return json(route, []);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: isAdmin });
    if (path.endsWith('/user')) {
      return json(route, {
        id: persona.id, username: persona.username, email: persona.email,
        given_name: persona.givenName, family_name: persona.familyName,
        // Role gates re-derive systemRoles from user_roles on refresh, so echo them.
        user_roles: persona.systemRoles.map((role_id) => ({ role_id })),
      });
    }
    if (path.startsWith('/messages')) return json(route, []);
    return json(route, {});
  });
}

// ---- typed data builders -------------------------------------------------

export function buildUsers(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `u-${String(i + 1).padStart(3, '0')}`,
    username: `user${i + 1}`,
    email: `user${i + 1}@example.org`,
    given_name: `Given${i + 1}`,
    family_name: `Family${i + 1}`,
    archived_at: null,
    is_service: false,
    created_at: '2026-01-15T10:00:00Z',
  }));
}

export function buildInvite(over: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'inv-1',
    token: 'tok-abcdef123456',
    email: null,
    max_uses: 1,
    use_count: 0,
    expires_at: '2099-01-01T00:00:00Z',
    revoked_at: null,
    roles: ['_user_manager'],
    note: 'onboard a manager',
    created_at: '2026-01-15T10:00:00Z',
    ...over,
  };
}
