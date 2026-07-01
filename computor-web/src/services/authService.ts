import { IAuthProviderWithLogin } from '../interfaces/IAuthProvider';
import { AuthResponse, AuthUser } from '../types/auth';
import { LogoutResponse } from '../generated/types/auth';
import { UserGet } from '../generated/types/users';
import {
  clearStoredSession,
  determineRole,
  loadStoredSession,
  saveStoredSession,
} from './authStorage';

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
  private currentUser: AuthUser | null = null;
  private currentViews: string[] = [];

  constructor() {
    const session = loadStoredSession('basic');
    if (session) {
      this.currentUser = session.user;
      this.currentViews = session.views;
    }
  }

  private saveSession(user: AuthUser, views: string[]): void {
    saveStoredSession('basic', user, views);
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
   * Login with credentials
   * Backend sets HttpOnly cookies on successful login
   */
  async login(credentials: { username: string; password: string }): Promise<AuthResponse> {
    try {
      const loginRequest = {
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
      this.saveSession(user, views);

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
  private async fetchUserInfo(): Promise<UserGet | null> {
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
   */
  private transformUserData(userInfo: UserGet, views: string[]): AuthUser {
    // Extract global role IDs from user_roles (e.g. _admin)
    const globalRoles: string[] = (userInfo.user_roles || []).map((r) => r.role_id);

    return {
      id: userInfo.id,
      username: userInfo.username || '',
      email: userInfo.email || '',
      givenName: userInfo.given_name || undefined,
      familyName: userInfo.family_name || undefined,
      role: determineRole(globalRoles, views),
      systemRoles: globalRoles,
    };
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

      if (!response.ok) {
        const logoutResponse: LogoutResponse | null = await response.json().catch(() => null);
        console.error('Logout request failed:', logoutResponse?.message ?? response.status);
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
      this.saveSession(user, views);

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
   */
  clearSession(): void {
    clearStoredSession();
    this.currentUser = null;
    this.currentViews = [];
  }
}
