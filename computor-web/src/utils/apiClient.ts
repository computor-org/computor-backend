/**
 * API Client with automatic token refresh
 *
 * Handles:
 * - Automatic token refresh on 401 errors
 * - Request retry after successful refresh
 * - Prevents multiple simultaneous refresh requests
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Refresh the access token using the refresh token
 * Returns true if refresh was successful
 */
async function refreshAccessToken(): Promise<boolean> {
  try {
    console.log('[apiClient] Calling /auth/refresh endpoint...');
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send refresh token cookie
    });

    if (response.ok) {
      console.log('[apiClient] Token refresh successful');
      return true;
    } else {
      console.log(`[apiClient] Token refresh failed with status: ${response.status}`);
      return false;
    }
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
    console.log('Received 401, attempting token refresh...');

    // If another request is already refreshing, wait for it
    if (isRefreshing) {
      const refreshSuccess = await getRefreshPromise();
      if (refreshSuccess) {
        // Retry the original request
        return fetch(url, fetchOptions);
      } else {
        // Refresh failed, just return the 401 response
        // Let the calling component handle it
        console.log('Token refresh failed');
        return response;
      }
    }

    // Start refreshing
    isRefreshing = true;
    const refreshSuccess = await getRefreshPromise();

    if (refreshSuccess) {
      console.log('Token refresh successful, retrying original request');
      // Retry the original request with new token
      return fetch(url, fetchOptions);
    } else {
      console.log('Token refresh failed');
      // Refresh failed, just return the 401 response
      // The AuthContext/pages will handle logout/redirect
      return response;
    }
  }

  return response;
}

/**
 * Convenience method for GET requests
 */
export async function apiGet(url: string): Promise<Response> {
  return apiFetch(url, { method: 'GET' });
}

/**
 * Convenience method for POST requests
 */
export async function apiPost(url: string, body?: any): Promise<Response> {
  return apiFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * Convenience method for PUT requests
 */
export async function apiPut(url: string, body?: any): Promise<Response> {
  return apiFetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * Convenience method for DELETE requests
 */
export async function apiDelete(url: string): Promise<Response> {
  return apiFetch(url, { method: 'DELETE' });
}
