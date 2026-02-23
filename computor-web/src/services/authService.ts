import { IAuthProviderWithLogin, AuthResponse, AuthUser } from '../interfaces/IAuthProvider';
import { LocalLoginRequest, LocalLoginResponse, LogoutResponse } from '../generated/types/auth';
import { UserGet } from '../generated/types/users';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Authentication Service using FastAPI Backend
 *
 * SECURITY: Uses HttpOnly cookies for authentication tokens.
 * - Tokens are stored ONLY in HttpOnly cookies (set by backend)
 * - Frontend stores only non-sensitive user data in sessionStorage
 * - XSS attacks cannot access authentication tokens
 * - Tokens are automatically sent with all requests via cookies
 */
export class AuthService implements IAuthProviderWithLogin {
  private readonly USER_KEY = 'auth_user';
  private readonly VIEWS_KEY = 'auth_views';
  private currentUser: AuthUser | null = null;
  private currentViews: string[] = [];

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
      const storedViews = sessionStorage.getItem(this.VIEWS_KEY);

      if (storedUser) {
        this.currentUser = JSON.parse(storedUser);
      }

      if (storedViews) {
        this.currentViews = JSON.parse(storedViews);
      }
    } catch (error) {
      console.error('Failed to load user from storage:', error);
      this.currentUser = null;
      this.currentViews = [];
    }
  }

  /**
   * Save user data to sessionStorage (NOT tokens!)
   * Only runs on client-side (browser)
   */
  private saveUserToStorage(user: AuthUser, views: string[]): void {
    // Check if we're in the browser (not SSR)
    if (typeof window === 'undefined') {
      this.currentUser = user;
      this.currentViews = views;
      return;
    }

    try {
      sessionStorage.setItem(this.USER_KEY, JSON.stringify(user));
      sessionStorage.setItem(this.VIEWS_KEY, JSON.stringify(views));
      this.currentUser = user;
      this.currentViews = views;
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
   * Get current user's available views
   */
  getCurrentViews(): string[] {
    return this.currentViews;
  }

  /**
   * Login with credentials
   * Backend sets HttpOnly cookies on successful login
   */
  async login(credentials: { username: string; password: string }): Promise<AuthResponse> {
    try {
      const loginRequest: LocalLoginRequest = {
        username: credentials.username,
        password: credentials.password,
      };

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Receive and send cookies
        body: JSON.stringify(loginRequest),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Login failed';

        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorJson.message || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }

        return {
          success: false,
          error: errorMessage,
        };
      }

      const loginResponse: LocalLoginResponse = await response.json();

      // Fetch user info and views
      const [userInfo, views] = await Promise.all([
        this.fetchUserInfo(),
        this.fetchUserViews(),
      ]);

      if (!userInfo) {
        return {
          success: false,
          error: 'Failed to fetch user information',
        };
      }

      // Transform user data with views to determine correct role
      const user = this.transformUserData(userInfo, views);

      // Store user data and views (cookies are already set by backend)
      this.saveUserToStorage(user, views);

      return {
        success: true,
        user,
      };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  /**
   * Fetch raw user information from GET /user
   * Returns UserGet data without transformation
   */
  private async fetchUserInfo(): Promise<any | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/user`, {
        credentials: 'include',
      });

      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to fetch user info:', error);
      return null;
    }
  }

  /**
   * Fetch user's available views from /user/views
   */
  private async fetchUserViews(): Promise<string[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/user/views`, {
        credentials: 'include',
      });

      if (!response.ok) {
        return [];
      }

      const views: string[] = await response.json();
      return views;
    } catch (error) {
      console.error('Failed to fetch user views:', error);
      return [];
    }
  }

  /**
   * Transform backend UserGet to frontend AuthUser
   * Note: Role will be determined after views are fetched
   */
  private transformUserData(userInfo: any, views?: string[]): AuthUser {
    const role = this.determineRoleFromViews(views || []);

    return {
      id: userInfo.id || userInfo.user?.id,
      username: userInfo.username || userInfo.user?.username || '',
      email: userInfo.email || userInfo.user?.email || '',
      givenName: userInfo.given_name || userInfo.user?.given_name,
      familyName: userInfo.family_name || userInfo.user?.family_name,
      role,
      permissions: this.mapViewsToPermissions(views || []),
      courses: [], // TODO: Fetch from user's course enrollments
    };
  }

  /**
   * Determine user role from available views
   *
   * IMPORTANT: Views are course-specific roles (which perspectives user can access)
   * - If user is student in any course → ['student']
   * - If user is tutor in any course → ['student', 'tutor']
   * - If user is lecturer/maintainer/owner → ['student', 'tutor', 'lecturer']
   *
   * This determines the highest course role they have for UI display purposes.
   * Global roles like 'admin' will be added later from backend.
   */
  private determineRoleFromViews(views: string[]): 'admin' | 'lecturer' | 'student' {
    // TODO: When global admin role is added to backend, check for it here
    // For now, use highest course role available

    if (views.includes('lecturer')) return 'lecturer';
    if (views.includes('tutor')) return 'lecturer'; // Show as lecturer in UI
    return 'student'; // Default to student
  }

  /**
   * Map views to permissions
   */
  private mapViewsToPermissions(views: string[]): string[] {
    const permissions: string[] = [];

    if (views.includes('lecturer')) {
      permissions.push(
        'view_students',
        'view_course_students',
        'create_assignments',
        'view_grades',
        'manage_course'
      );
    }

    if (views.includes('tutor')) {
      permissions.push(
        'view_students',
        'view_course_students',
        'view_grades'
      );
    }

    if (views.includes('student')) {
      permissions.push(
        'view_assignments',
        'submit_assignments'
      );
    }

    return permissions;
  }

  /**
   * Logout user
   * Instructs backend to clear HttpOnly cookies
   */
  async logout(): Promise<void> {
    try {
      // Notify backend to clear cookies
      const response = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Send cookies for logout
      });

      if (response.ok) {
        const logoutResponse: LogoutResponse = await response.json();
        console.log('Logout response:', logoutResponse.message);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local session data
      this.clearSession();
    }
  }

  /**
   * Refresh authentication session
   * Calls /auth/refresh to get a new access token using the refresh token
   */
  async refreshSession(): Promise<AuthResponse> {
    try {
      // Call the refresh endpoint to get a new access token
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // Send refresh token cookie
      });

      if (!refreshResponse.ok) {
        this.clearSession();
        return {
          success: false,
          error: 'Session expired',
        };
      }

      // After successful refresh, fetch updated user info and views
      const [userInfo, views] = await Promise.all([
        this.fetchUserInfo(),
        this.fetchUserViews(),
      ]);

      if (!userInfo) {
        this.clearSession();
        return {
          success: false,
          error: 'Failed to fetch user information',
        };
      }

      // Transform user data with views to determine correct role
      const user = this.transformUserData(userInfo, views);
      this.saveUserToStorage(user, views);

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
      sessionStorage.removeItem(this.VIEWS_KEY);
    }
    this.currentUser = null;
    this.currentViews = [];
  }
}
