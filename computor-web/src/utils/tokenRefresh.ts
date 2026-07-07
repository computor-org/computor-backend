/**
 * Single-flight, single-strategy token refresh.
 *
 * Every HTTP layer refreshes on 401 through `refreshSession()`, so at most one
 * `/auth/refresh` is in flight at any time (concurrent callers await the same
 * promise) AND all layers share one refresh implementation.
 *
 * The strategy is pluggable: by default it hits the backend refresh endpoint
 * directly; `apiConfig` overrides it with a provider-aware refresh so the
 * cached SSO user data is refreshed in step with the HttpOnly cookies.
 */
export type RefreshOutcome = 'refreshed' | 'failed' | 'unreachable';

// Read independently of apiClient.ts to avoid an import cycle.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Refresh the HttpOnly cookies via the backend endpoint. 'unreachable' on a
 * network error (caller must NOT log out); 'failed' when the backend refuses.
 */
export async function directRefresh(): Promise<RefreshOutcome> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    return response.ok ? 'refreshed' : 'failed';
  } catch {
    return 'unreachable';
  }
}

let strategy: () => Promise<RefreshOutcome> = directRefresh;

/**
 * Override the refresh strategy (called by apiConfig with a provider-aware
 * implementation). Resets to `directRefresh` if given nothing.
 */
export function setRefreshStrategy(fn?: () => Promise<RefreshOutcome>): void {
  strategy = fn ?? directRefresh;
}

let inflight: Promise<RefreshOutcome> | null = null;

/**
 * Refresh the session, coalescing concurrent callers onto one refresh.
 */
export function refreshSession(): Promise<RefreshOutcome> {
  if (!inflight) {
    inflight = strategy().finally(() => {
      inflight = null;
    });
  }
  return inflight;
}
