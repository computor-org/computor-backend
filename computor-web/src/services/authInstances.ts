import { SSOAuthService } from './ssoAuthService';
import { AuthService } from './authService';

/**
 * Single shared instances of the auth services.
 *
 * AuthContext, the API-client config, and the SSO callback page must all see
 * the same in-memory session state; constructing services ad hoc gave each
 * caller its own copy that only agreed by way of sessionStorage.
 */
export const ssoAuthService = new SSOAuthService();
export const authService = new AuthService();
