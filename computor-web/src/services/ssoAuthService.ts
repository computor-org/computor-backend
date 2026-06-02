import { LoginCredentials, AuthResponse, AuthUser } from '../types/auth';
import { ISSOAuthProvider } from '../interfaces/IAuthProvider';
import { apiFetch } from '../utils/apiClient';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  private readonly USER_KEY = 'auth_user';
  private currentUser: AuthUser | null = null;

  constructor() {
    // Load user from sessionStorage on initialization
    this.loadUserFromStorage();
  }

  /**
   * Load user data from sessionStorage
   * Only runs on client-side (browser)
   */
  private loadUserFromStorage(): void {
    // Check if we're in the browser (not SSR)
    if (typeof window === 'undefined') {
      return;
    }

    try {
      const storedUser = sessionStorage.getItem(this.USER_KEY);
      if (storedUser) {
        this.currentUser = JSON.parse(storedUser);
      }
    } catch (error) {
      console.error('Failed to load user from storage:', error);
      this.currentUser = null;
    }
  }

  /**
   * Save user data to sessionStorage (NOT tokens!)
   * Only runs on client-side (browser)
   */
  private saveUserToStorage(user: AuthUser): void {
    // Check if we're in the browser (not SSR)
    if (typeof window === 'undefined') {
      this.currentUser = user;
      return;
    }

    try {
      sessionStorage.setItem(this.USER_KEY, JSON.stringify(user));
      this.currentUser = user;
    } catch (error) {
      console.error('Failed to save user to storage:', error);
    }
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
      // Fetch user info - cookies are sent automatically
      // No need to pass tokens manually!
      const response = await fetch(`${API_BASE_URL}/user`, {
        credentials: 'include', // Send cookies
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user info');
      }

      const userInfo = await response.json();
      const user = this.mapUserResponse(userInfo);

      // Store ONLY user data (not tokens!)
      this.saveUserToStorage(user);

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
   * Build an AuthUser from a backend `GET /user` payload.
   *
   * GET /user returns the User object directly (not wrapped in { user: ... }).
   * user_roles is an array of { role_id: string, ... } — extract role_id strings.
   */
  private mapUserResponse(userInfo: any): AuthUser {
    const roleIds: string[] = (userInfo.user_roles || []).map((r: any) => r.role_id);
    return {
      id: userInfo.id,
      username: userInfo.username || userInfo.email,
      email: userInfo.email,
      givenName: userInfo.given_name,
      familyName: userInfo.family_name,
      role: this.mapRolesToFrontend(roleIds),
      systemRoles: roleIds,
      permissions: this.mapPermissions(roleIds),
      courses: [],
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
        const userInfo = await response.json();
        this.saveUserToStorage(this.mapUserResponse(userInfo));
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
   * Direct login (for testing or basic auth fallback)
   * Backend sets HttpOnly cookies on successful login
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Receive cookies
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const error = await response.text();
        return {
          success: false,
          error: error || 'Login failed',
        };
      }

      const data = await response.json();

      // Store user data (cookies are already set by backend)
      const user: AuthUser = data.user;
      this.saveUserToStorage(user);

      return {
        success: true,
        user,
      };
    } catch (error) {
      return {
        success: false,
        error: 'Network error',
      };
    }
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
      const userInfo = await userResponse.json();
      const user = this.mapUserResponse(userInfo);
      this.saveUserToStorage(user);
      return { success: true, user };
    } catch (error) {
      console.warn('User payload parse failed after refresh:', error);
      return { success: false, error: 'unreachable' };
    }
  }

  /**
   * Clear local session data
   * Does NOT clear HttpOnly cookies (only backend can do that)
   * Only runs on client-side (browser)
   */
  clearSession(): void {
    // Check if we're in the browser (not SSR)
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem(this.USER_KEY);
    }
    this.currentUser = null;
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
      return providers.map((p: any) => ({
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

  /**
   * Map backend roles to frontend role
   */
  private mapRolesToFrontend(roles: string[]): 'admin' | 'lecturer' | 'student' {
    if (roles.includes('_admin')) return 'admin';
    if (roles.includes('_lecturer')) return 'lecturer';
    return 'student';
  }

  /**
   * Map roles to permissions
   */
  private mapPermissions(roles: string[]): string[] {
    const permissions: string[] = [];

    if (roles.includes('_admin')) {
      permissions.push(
        'view_students',
        'view_course_students',
        'create_assignments',
        'view_grades',
        'manage_course',
        'admin_access',
        'manage_users',
        'system_settings',
        'view_audit'
      );
    }

    if (roles.includes('_lecturer')) {
      permissions.push(
        'view_students',
        'view_course_students',
        'create_assignments',
        'view_grades',
        'manage_course'
      );
    }

    if (roles.includes('_student')) {
      permissions.push(
        'view_assignments',
        'submit_assignments'
      );
    }

    return permissions;
  }
}
