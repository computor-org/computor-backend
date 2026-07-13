/**
 * API Configuration Module
 *
 * Wires the SSO auth service's refresh into the shared token-refresh strategy
 * so every HTTP layer, on a 401, refreshes the cached SSO user data in step
 * with the HttpOnly cookies. Imported early in the app lifecycle.
 */

import { ssoAuthService } from '@/src/services/authInstances';
import { setRefreshStrategy, directRefresh, type RefreshOutcome } from '@/src/utils/tokenRefresh';

/**
 * Install the provider-aware refresh strategy shared by all HTTP layers.
 * Falls back to the direct backend refresh when no SSO session is present.
 */
export function configureAPIClient() {
  setRefreshStrategy(async (): Promise<RefreshOutcome> => {
    if (ssoAuthService.isAuthenticated()) {
      try {
        const result = await ssoAuthService.refreshSession();
        if (result.success) return 'refreshed';
        if (result.error === 'unreachable') return 'unreachable';
        return 'failed';
      } catch {
        // Fall through to the direct refresh below.
      }
    }
    return directRefresh();
  });
}

// Auto-configure if in browser environment
if (typeof window !== 'undefined') {
  configureAPIClient();
}
