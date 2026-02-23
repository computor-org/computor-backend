/**
 * API Configuration Module
 *
 * Configures the API client with authentication providers.
 * This module should be imported early in the application lifecycle.
 */

import { apiClient } from '../api/client';
import { SSOAuthService } from '../services/ssoAuthService';
import { AuthService } from '../services/authService';

/**
 * Initialize API client with authentication providers
 *
 * Auth providers are checked in order:
 * 1. SSO Authentication (Keycloak)
 * 2. Mock/Basic Authentication (for development)
 */
export function configureAPIClient() {
  // Create provider instances
  const ssoProvider = new SSOAuthService();
  const mockProvider = new AuthService();

  // Configure API client with providers (checked in order)
  apiClient.setAuthProviders([
    ssoProvider,
    mockProvider,
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
