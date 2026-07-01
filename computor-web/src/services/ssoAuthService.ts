import { AuthResponse, AuthUser } from '../types/auth';
import { ISSOAuthProvider } from '../interfaces/IAuthProvider';
import { UserGet } from '../generated/types/users';
import { apiFetch, API_BASE_URL } from '../utils/apiClient';
import {
  clearStoredSession,
  determineRole,
  loadStoredSession,
  saveStoredSession,
} from './authStorage';

/**
 * SSO Authentication Service
 *
 * SECURITY: Uses HttpOnly cookies for authentication tokens.
 * - Tokens are stored ONLY in HttpOnly cookies (set by backend)
 * - Frontend stores only non-sensitive user data in sessionStorage
 * - XSS attacks cannot access authentication tokens
 * - Tokens are automatically sent with all requests via cookies
 */
export class SSOAuthService implements ISSOAuthProvider {
  private currentUser: AuthUser | null = null;
  private currentViews: string[] = [];

  constructor() {
    const session = loadStoredSession('sso');
    if (session) {
      this.currentUser = session.user;
      this.currentViews = session.views;
    }
  }

  private saveSession(user: AuthUser, views: string[]): void {
    saveStoredSession('sso', user, views);
    this.currentUser = user;
    this.currentViews = views;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.currentUser !== null;
  }

  /**
   * Get current authenticated user
   */
  getCurrentUser(): AuthUser | null {
    return this.currentUser;
  }

  /**
   * Get current user's available views
   */
  getCurrentViews(): string[] {
    return this.currentViews;
  }

  /**
   * Initiate SSO login by redirecting to the provider
   * Backend will set HttpOnly cookies after successful authentication
   */
  initiateSSO(provider: string = 'keycloak'): void {
    // Save current location to return after auth
    sessionStorage.setItem('auth_redirect', window.location.pathname);

    // Build the frontend callback URL
    const frontendCallbackUrl = `${window.location.origin}/auth/success`;

    // Redirect to SSO login with redirect_uri parameter
    const params = new URLSearchParams({
      redirect_uri: frontendCallbackUrl
    });

    window.location.href = `${API_BASE_URL}/auth/${provider}/login?${params.toString()}`;
  }

  /**
   * Handle SSO callback after redirect from provider
   * Backend should have already set HttpOnly cookies
   */
  async handleSSOCallback(): Promise<AuthResponse> {
    try {
      // Fetch user info and views — cookies are sent automatically.
      const [response, views] = await Promise.all([
        fetch(`${API_BASE_URL}/user`, { credentials: 'include' }),
        this.fetchUserViews(),
      ]);

      if (!response.ok) {
        throw new Error('Failed to fetch user info');
      }

      const userInfo: UserGet = await response.json();
      const user = this.mapUserResponse(userInfo, views ?? []);

      // Store ONLY user data (not tokens!)
      this.saveSession(user, views ?? []);

      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);

      return {
        success: true,
        user,
      };
    } catch (error) {
      console.error('SSO callback error:', error);
      return {
        success: false,
        error: 'Failed to complete authentication',
      };
    }
  }

  /**
   * Fetch the user's course views (student/tutor/lecturer/user_manager).
   * Returns null on failure so callers can keep the views they already have.
   */
  private async fetchUserViews(): Promise<string[] | null> {
    try {
      const response = await apiFetch(`${API_BASE_URL}/user/views`);
      if (!response.ok) return null;
      const views = await response.json();
      return Array.isArray(views) ? views : null;
    } catch {
      return null;
    }
  }

  /**
   * Build an AuthUser from a backend `GET /user` payload.
   *
   * GET /user returns the User object directly (not wrapped in { user: ... }).
   * user_roles is an array of { role_id: string, ... } — extract role_id strings.
   */
  private mapUserResponse(userInfo: UserGet, views: string[]): AuthUser {
    const roleIds: string[] = (userInfo.user_roles || []).map((r) => r.role_id);
    return {
      id: userInfo.id,
      username: userInfo.username || userInfo.email || '',
      email: userInfo.email || '',
      givenName: userInfo.given_name || undefined,
      familyName: userInfo.family_name || undefined,
      role: determineRole(roleIds, views),
      systemRoles: roleIds,
    };
  }

  /**
   * Validate the cached session against the backend.
   *
   * The auth tokens live in HttpOnly cookies; the cached user in sessionStorage
   * can outlive them — e.g. Firefox restores sessionStorage after a restart while
   * the cookies have already expired. Without this check the UI keeps showing a
   * logged-in state (the "Sign Out" button) for a session that is actually dead.
   *
   * Returns:
   *  - 'valid'       session is good (cached user refreshed from the backend)
   *  - 'invalid'     backend rejected us (401/403) — session cleared
   *  - 'unreachable' backend could not be reached (e.g. off VPN) — session kept
   */
  async validateSession(): Promise<'valid' | 'invalid' | 'unreachable'> {
    if (!this.currentUser) {
      return 'invalid';
    }

    let response: Response;
    try {
      // apiFetch transparently refreshes the access token on a 401 and retries,
      // so a merely-expired access token (with a still-valid refresh token) is
      // renewed here instead of being treated as a dead session.
      response = await apiFetch(`${API_BASE_URL}/user`);
    } catch {
      // Network error: the backend is unreachable. Keep the cached session —
      // being off VPN must not look like being logged out.
      return 'unreachable';
    }

    if (response.ok) {
      try {
        const userInfo: UserGet = await response.json();
        const views = (await this.fetchUserViews()) ?? this.currentViews;
        this.saveSession(this.mapUserResponse(userInfo, views), views);
      } catch {
        // A body-parse hiccup must not drop an otherwise-valid session.
      }
      return 'valid';
    }

    if (response.status === 401 || response.status === 403) {
      this.clearSession();
      return 'invalid';
    }

    // Server-side error (5xx) etc. — don't punish the user for it; keep session.
    return 'unreachable';
  }

  /**
   * Logout user.
   *
   * Browser-navigates to the backend's SSO logout endpoint, which:
   *   1. Clears the HttpOnly auth cookies
   *   2. Redirects the browser to Keycloak's end_session_endpoint so the
   *      SSO session at the IdP also ends. Without this, the next "Sign in
   *      with Keycloak" silently re-logs the user in.
   *   3. Keycloak then redirects back to post_logout_redirect_uri (the app home).
   */
  async logout(): Promise<void> {
    // Clear local user data first — browser will navigate away after.
    this.clearSession();

    const postLogoutRedirect = `${window.location.origin}/`;
    const params = new URLSearchParams({ post_logout_redirect_uri: postLogoutRedirect });
    window.location.href = `${API_BASE_URL}/auth/keycloak/logout?${params.toString()}`;
  }

  /**
   * Refresh authentication session
   * Backend will refresh HttpOnly cookies automatically
   */
  async refreshSession(): Promise<AuthResponse> {
    // NOTE: error === 'unreachable' is a signal to callers that the backend
    // could not be reached (e.g. off VPN). In that case the session is left
    // intact on purpose — a transient network failure must not log the user out.
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Send refresh token cookie
        body: JSON.stringify({
          provider: 'keycloak',
        }),
      });
    } catch (error) {
      console.warn('Session refresh skipped (backend unreachable):', error);
      return { success: false, error: 'unreachable' };
    }

    if (!response.ok) {
      // The backend explicitly refused the refresh token — the session is dead.
      this.clearSession();
      return { success: false, error: 'Failed to refresh session' };
    }

    // Fetch updated user info
    let userResponse: Response;
    try {
      userResponse = await fetch(`${API_BASE_URL}/user`, {
        credentials: 'include',
      });
    } catch (error) {
      console.warn('User fetch after refresh skipped (backend unreachable):', error);
      return { success: false, error: 'unreachable' };
    }

    if (!userResponse.ok) {
      if (userResponse.status === 401 || userResponse.status === 403) {
        this.clearSession();
        return { success: false, error: 'Failed to refresh session' };
      }
      return { success: false, error: 'unreachable' };
    }

    try {
      const userInfo: UserGet = await userResponse.json();
      const views = (await this.fetchUserViews()) ?? this.currentViews;
      const user = this.mapUserResponse(userInfo, views);
      this.saveSession(user, views);
      return { success: true, user };
    } catch (error) {
      console.warn('User payload parse failed after refresh:', error);
      return { success: false, error: 'unreachable' };
    }
  }

  /**
   * Clear local session data
   * Does NOT clear HttpOnly cookies (only backend can do that)
   */
  clearSession(): void {
    clearStoredSession();
    this.currentUser = null;
    this.currentViews = [];
  }

  /**
   * Check if current route is an SSO callback
   * Only runs on client-side (browser)
   */
  isSSOCallback(): boolean {
    // Check if we're in the browser (not SSR)
    if (typeof window === 'undefined') {
      return false;
    }

    const path = window.location.pathname;
    return path === '/auth/success' || path === '/auth/callback';
  }

  /**
   * Get available SSO providers from backend
   */
  async getProviders(): Promise<Array<{ name: string; display_name: string; type: string; enabled: boolean }>> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/providers`, {
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to fetch providers');
      }

      const providers = await response.json();

      // Map ProviderInfo to simplified format
      return providers.map((p: { name: string; display_name: string; type: string; enabled: boolean }) => ({
        name: p.name,
        display_name: p.display_name,
        type: p.type,
        enabled: p.enabled,
      }));
    } catch (error) {
      console.error('Failed to fetch SSO providers:', error);
      return [];
    }
  }
}
