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

export const CONSENT_REDIRECT_KEY = 'consent_redirect';

/**
 * Navigate to the consent page, remembering the originally requested route
 * so the consent page can return the user there afterwards. No-op on the
 * consent page itself and during SSR. Shared by both HTTP layers and the
 * AuthenticatedLayout bootstrap check.
 */
export function redirectToConsent(): void {
  if (typeof window === 'undefined' || window.location.pathname.startsWith('/consent')) {
    return;
  }
  sessionStorage.setItem(
    CONSENT_REDIRECT_KEY,
    window.location.pathname + window.location.search
  );
  window.location.href = '/consent';
}

/**
 * True iff the response is the backend consent gate's stable 403 body
 * {"error": "consent_required", ...}. Only JSON responses are parsed
 * (via clone(), so the caller can still read the body).
 */
export async function isConsentRequired(response: Response): Promise<boolean> {
  if (response.status !== 403) return false;
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return false;
  try {
    const body = await response.clone().json();
    return body?.error === 'consent_required';
  } catch {
    return false;
  }
}

/**
 * Global consent interceptor: any consent-gate 403 routes the user to
 * /consent. The 403 response is still returned to the caller.
 */
async function interceptConsentRequired(response: Response): Promise<Response> {
  if (await isConsentRequired(response)) {
    redirectToConsent();
  }
  return response;
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
      return interceptConsentRequired(await fetch(url, fetchOptions));
    }
    // Refresh failed or backend unreachable: return the original 401 —
    // the AuthContext/pages decide whether that means logout.
    return response;
  }

  return interceptConsentRequired(response);
}

/**
 * GET helper over apiFetch — returns the raw Response (token refresh and the
 * consent-gate interceptor are applied by apiFetch).
 */
export function apiGet(url: string, options: RequestInit = {}): Promise<Response> {
  return apiFetch(url, { ...options, method: 'GET' });
}

/**
 * POST helper over apiFetch. A plain-object body is JSON-encoded; pass a string
 * or FormData through untouched. Returns the raw Response.
 */
export function apiPost(url: string, body?: unknown, options: RequestInit = {}): Promise<Response> {
  const isRaw = body === undefined || typeof body === 'string' || body instanceof FormData;
  return apiFetch(url, {
    ...options,
    method: 'POST',
    headers: isRaw
      ? options.headers ?? {}
      : { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    body: isRaw ? (body as BodyInit | undefined) : JSON.stringify(body),
  });
}

