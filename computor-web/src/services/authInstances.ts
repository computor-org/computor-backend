import { SSOAuthService } from './ssoAuthService';

/**
 * Single shared instance of the SSO auth service.
 *
 * AuthContext, the API-client config, and the SSO callback page must all see
 * the same in-memory session state; constructing services ad hoc gave each
 * caller its own copy that only agreed by way of sessionStorage.
 *
 * Keycloak SSO is the only identity provider — local password login was
 * removed (see src/types/auth.ts).
 */
export const ssoAuthService = new SSOAuthService();
