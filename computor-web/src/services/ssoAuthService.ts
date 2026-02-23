import { LoginCredentials, AuthResponse, AuthUser } from '../types/auth';
import { ISSOAuthProvider } from '../interfaces/IAuthProvider';

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

      // Transform backend user data to frontend format
      const user: AuthUser = {
        id: userInfo.user.id,
        username: userInfo.user.username || userInfo.user.email,
        email: userInfo.user.email,
        givenName: userInfo.user.given_name,
        familyName: userInfo.user.family_name,
        role: this.mapRolesToFrontend(userInfo.roles),
        permissions: this.mapPermissions(userInfo.roles),
        courses: [], // TODO: Fetch from user's course enrollments
      };

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
   * Logout user
   * Instructs backend to clear HttpOnly cookies
   */
  async logout(): Promise<void> {
    try {
      // Notify backend to clear cookies
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include', // Send cookies for logout
      });
    } catch (error) {
      console.error('Logout error:', error);
    }

    // Clear local user data
    this.clearSession();
  }

  /**
   * Refresh authentication session
   * Backend will refresh HttpOnly cookies automatically
   */
  async refreshSession(): Promise<AuthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Send refresh token cookie
        body: JSON.stringify({
          provider: 'keycloak',
        }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      // Fetch updated user info
      const userResponse = await fetch(`${API_BASE_URL}/user`, {
        credentials: 'include',
      });

      if (!userResponse.ok) {
        throw new Error('Failed to fetch user info');
      }

      const userInfo = await userResponse.json();
      const user: AuthUser = {
        id: userInfo.user.id,
        username: userInfo.user.username || userInfo.user.email,
        email: userInfo.user.email,
        givenName: userInfo.user.given_name,
        familyName: userInfo.user.family_name,
        role: this.mapRolesToFrontend(userInfo.roles),
        permissions: this.mapPermissions(userInfo.roles),
        courses: [],
      };

      this.saveUserToStorage(user);

      return {
        success: true,
        user,
      };
    } catch (error) {
      console.error('Session refresh error:', error);
      this.clearSession();
      return {
        success: false,
        error: 'Failed to refresh session',
      };
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
