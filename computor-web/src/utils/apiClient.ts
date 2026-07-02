/**
 * API Client with automatic token refresh
 *
 * Handles:
 * - Automatic token refresh on 401 errors
 * - Request retry after successful refresh
 * - Prevents multiple simultaneous refresh requests
 */

import { refreshOnce, type RefreshOutcome } from './tokenRefresh';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Refresh the access token using the refresh token cookie.
 */
async function refreshAccessToken(): Promise<RefreshOutcome> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send refresh token cookie
    });

    return response.ok ? 'refreshed' : 'failed';
  } catch (error) {
    console.error('[apiClient] Token refresh error:', error);
    return 'unreachable';
  }
}

/**
 * Enhanced fetch with automatic token refresh on 401
 *
 * @param url - The URL to fetch
 * @param options - Fetch options
 * @param retryOn401 - Whether to retry on 401 (default: true)
 * @returns Fetch response
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {},
  retryOn401: boolean = true
): Promise<Response> {
  // Ensure credentials are included for cookie-based auth
  const fetchOptions: RequestInit = {
    ...options,
    credentials: 'include',
  };

  // Make the initial request
  const response = await fetch(url, fetchOptions);

  // If we get a 401 and haven't already retried: refresh once (coalesced
  // app-wide via refreshOnce) and retry the original request.
  if (response.status === 401 && retryOn401) {
    const outcome = await refreshOnce(refreshAccessToken);
    if (outcome === 'refreshed') {
      return fetch(url, fetchOptions);
    }
    // Refresh failed or backend unreachable: return the original 401 —
    // the AuthContext/pages decide whether that means logout.
    return response;
  }

  return response;
}

