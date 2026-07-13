import { AuthUser } from '@/src/types/auth';

/**
 * Shared sessionStorage-backed auth session store.
 *
 * Both auth services (SSO and basic) persist the same session shape; the
 * provider tag records which service owns the session so a basic-auth login
 * is never misread as an SSO session (whose Keycloak refresh call would fail
 * and log the user out). Tokens live in HttpOnly cookies — never here.
 */
export type AuthProviderKind = 'sso' | 'basic';

const USER_KEY = 'auth_user';
const VIEWS_KEY = 'auth_views';
const PROVIDER_KEY = 'auth_provider';

export interface StoredSession {
  user: AuthUser;
  views: string[];
}

export function loadStoredSession(kind: AuthProviderKind): StoredSession | null {
  if (typeof window === 'undefined') return null;

  try {
    const storedUser = sessionStorage.getItem(USER_KEY);
    if (!storedUser) return null;

    // Sessions written before the provider tag existed default to SSO —
    // Keycloak is the only login the UI offers.
    const provider =
      (sessionStorage.getItem(PROVIDER_KEY) as AuthProviderKind | null) ?? 'sso';
    if (provider !== kind) return null;

    const storedViews = JSON.parse(sessionStorage.getItem(VIEWS_KEY) ?? '[]');
    return {
      user: JSON.parse(storedUser),
      views: Array.isArray(storedViews) ? storedViews : [],
    };
  } catch (error) {
    console.error('Failed to load auth session from storage:', error);
    return null;
  }
}

export function saveStoredSession(
  kind: AuthProviderKind,
  user: AuthUser,
  views: string[],
): void {
  if (typeof window === 'undefined') return;

  try {
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    sessionStorage.setItem(VIEWS_KEY, JSON.stringify(views));
    sessionStorage.setItem(PROVIDER_KEY, kind);
  } catch (error) {
    console.error('Failed to save auth session to storage:', error);
  }
}

/** Clears the whole session atomically — user, views, and provider tag. */
export function clearStoredSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(USER_KEY);
  sessionStorage.removeItem(VIEWS_KEY);
  sessionStorage.removeItem(PROVIDER_KEY);
}

/**
 * Frontend display role from global roles + course views.
 * Priority: admin (global) > lecturer/tutor (course view) > student.
 *
 * `role` drives display-level choices only; real gating goes through
 * usePermissions (backend scopes/views). Both auth services must map
 * identically — this is the single implementation.
 */
export function determineRole(
  globalRoles: string[],
  views: string[],
): 'admin' | 'lecturer' | 'student' {
  if (globalRoles.includes('_admin')) return 'admin';
  if (views.includes('lecturer')) return 'lecturer';
  if (views.includes('tutor')) return 'lecturer'; // tutors share the lecturer-facing UI
  return 'student';
}
