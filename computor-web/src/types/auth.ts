/**
 * Frontend Authentication Types
 *
 * SECURITY: This system uses HttpOnly cookies for authentication.
 * - Tokens are stored ONLY in HttpOnly cookies (backend-managed)
 * - Frontend never accesses or stores authentication tokens
 * - User data is stored in sessionStorage (non-sensitive data only)
 *
 * These types are used by the frontend authentication services
 * and extend/complement the generated backend types.
 */

// Re-export relevant generated types
export type { LocalLoginRequest, LocalLoginResponse } from '../generated/types/auth';

/**
 * Login credentials for authentication
 */
export interface LoginCredentials {
  username: string;
  password: string;
}

/**
 * Authenticated user information (non-sensitive data)
 * This is safe to store in sessionStorage
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

/**
 * Authentication response
 * Note: No token field - tokens are in HttpOnly cookies
 */
export interface AuthResponse {
  success: boolean;
  user?: AuthUser;
  error?: string;
}
