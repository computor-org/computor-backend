/**
 * API Configuration Module
 *
 * Configures the API client with authentication providers.
 * This module should be imported early in the application lifecycle.
 */

import { apiClient } from '../api/client';
import { ssoAuthService } from '../services/authInstances';

/**
 * Initialize API client with the SSO authentication provider.
 *
 * Keycloak SSO is the only identity provider; the client refreshes its
 * HttpOnly cookies through this provider on a 401.
 */
export function configureAPIClient() {
  apiClient.setAuthProviders([ssoAuthService]);
}

/**
 * Get the configured API client singleton
 * Should only be called after configureAPIClient()
 */
export function getAPIClient() {
  return apiClient;
}

// Auto-configure if in browser environment
if (typeof window !== 'undefined') {
  configureAPIClient();
}
