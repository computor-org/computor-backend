/**
 * API Client with automatic token refresh
 *
 * Handles:
 * - Automatic token refresh on 401 errors
 * - Request retry after successful refresh
 * - Prevents multiple simultaneous refresh requests
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Refresh the access token using the refresh token
 * Returns true if refresh was successful
 */
async function refreshAccessToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send refresh token cookie
    });

    return response.ok;
  } catch (error) {
    console.error('[apiClient] Token refresh error:', error);
    return false;
  }
}

/**
 * Get or create a refresh promise to prevent multiple simultaneous refreshes
 */
function getRefreshPromise(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      isRefreshing = false;
      refreshPromise = null;
    });
  }
  return refreshPromise;
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

  // If we get a 401 and haven't already retried
  if (response.status === 401 && retryOn401) {
    // If another request is already refreshing, wait for it
    if (isRefreshing) {
      const refreshSuccess = await getRefreshPromise();
      if (refreshSuccess) {
        // Retry the original request
        return fetch(url, fetchOptions);
      }
      // Refresh failed, just return the 401 response
      // Let the calling component handle it
      return response;
    }

    // Start refreshing
    isRefreshing = true;
    const refreshSuccess = await getRefreshPromise();

    if (refreshSuccess) {
      // Retry the original request with new token
      return fetch(url, fetchOptions);
    }
    // Refresh failed, just return the 401 response
    // The AuthContext/pages will handle logout/redirect
    return response;
  }

  return response;
}

