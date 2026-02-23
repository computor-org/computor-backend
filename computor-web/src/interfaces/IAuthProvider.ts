/**
 * Authentication provider interface for dependency injection
 *
 * This interface allows the APIClient to work with any authentication
 * provider (SSO, mock, basic auth, etc.) without tight coupling.
 *
 * SECURITY NOTE: This system uses HttpOnly cookies for token storage.
 * Tokens are NOT accessible to JavaScript, preventing XSS attacks.
 */

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  givenName?: string;
  familyName?: string;
  role: 'admin' | 'lecturer' | 'student';
  permissions: string[];
  courses: string[];
}

export interface AuthResponse {
  success: boolean;
  user?: AuthUser;
  error?: string;
}

/**
 * Core authentication provider interface
 *
 * NOTE: Tokens are stored in HttpOnly cookies by the backend.
 * The frontend never directly accesses or stores tokens.
 */
export interface IAuthProvider {
  /**
   * Check if user is currently authenticated
   * This checks for valid session/user data, NOT tokens
   */
  isAuthenticated(): boolean;

  /**
   * Get the current authenticated user if available
   * Returns null if not authenticated
   */
  getCurrentUser(): AuthUser | null;

  /**
   * Refresh the authentication session
   * Backend will refresh HttpOnly cookies automatically
   */
  refreshSession(): Promise<AuthResponse>;

  /**
   * Logout the current user
   * Clears session data and instructs backend to clear cookies
   */
  logout(): Promise<void>;

  /**
   * Clear local session data (not cookies - those are HttpOnly)
   */
  clearSession(): void;
}

/**
 * Extended authentication provider with login capabilities
 */
export interface IAuthProviderWithLogin extends IAuthProvider {
  /**
   * Login with credentials
   * Backend sets HttpOnly cookies on successful login
   */
  login(credentials: { username: string; password: string }): Promise<AuthResponse>;
}

/**
 * SSO authentication provider interface
 */
export interface ISSOAuthProvider extends IAuthProvider {
  /**
   * Initiate SSO login flow
   * Redirects to SSO provider
   */
  initiateSSO(provider?: string): void;

  /**
   * Handle SSO callback after redirect
   * Backend sets HttpOnly cookies on successful SSO login
   */
  handleSSOCallback(): Promise<AuthResponse>;

  /**
   * Check if current route is an SSO callback
   */
  isSSOCallback(): boolean;

  /**
   * Get available SSO providers
   */
  getProviders(): Promise<Array<{ name: string; display_name: string }>>;
}
