/**
 * API Configuration Module
 *
 * Configures the API client with authentication providers.
 * This module should be imported early in the application lifecycle.
 */

import { apiClient } from '../api/client';
import { ssoAuthService, authService } from '../services/authInstances';

/**
 * Initialize API client with authentication providers
 *
 * Auth providers are checked in order:
 * 1. SSO Authentication (Keycloak)
 * 2. Basic Authentication (fallback, e.g. for development)
 */
export function configureAPIClient() {
  // Configure API client with the shared provider instances (checked in order)
  apiClient.setAuthProviders([
    ssoAuthService,
    authService,
  ]);
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
