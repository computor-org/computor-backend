import { IAuthProvider } from '../interfaces/IAuthProvider';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  params?: Record<string, unknown>;
  data?: any;
}

/**
 * Configuration for APIClient
 */
interface APIClientConfig {
  baseURL?: string;
  authProviders?: IAuthProvider[];
  onAuthError?: () => void;
}

/**
 * HTTP Client for API requests with HttpOnly cookie-based authentication
 *
 * SECURITY:
 * - Uses HttpOnly cookies for authentication (set by backend)
 * - Tokens are NOT accessible to JavaScript (XSS protection)
 * - All requests include credentials: 'include' for cookie transmission
 * - CSRF protection via SameSite cookie attribute (backend responsibility)
 */
class APIClient {
  private baseURL: string;
  private authProviders: IAuthProvider[];
  private onAuthError: () => void;

  constructor(config: APIClientConfig = {}) {
    this.baseURL = config.baseURL || API_BASE_URL;
    this.authProviders = config.authProviders || [];
    this.onAuthError = config.onAuthError || (() => {
      if (typeof window !== 'undefined') {
        window.location.href = '/';
      }
    });
  }

  /**
   * Set authentication providers
   * Used for session management (user data), not tokens
   */
  setAuthProviders(providers: IAuthProvider[]): void {
    this.authProviders = providers;
  }

  /**
   * Get base headers for requests
   * NOTE: No Authorization header - cookies are sent automatically
   */
  private getHeaders(): HeadersInit {
    return {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Handle HTTP response and potential auth errors
   */
  private async handleResponse<T>(response: Response, method?: string): Promise<T> {
    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `HTTP error! status: ${response.status}`);
    }

    if (response.status === 204 || (method && method.toUpperCase() === 'HEAD')) {
      return {} as T;
    }

    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        return JSON.parse(text) as T;
      } catch (error) {
        console.warn('Failed to parse JSON response', error);
      }
    }

    return text as unknown as T;
  }

  /**
   * Attempt to refresh the access token after a 401.
   * Returns 'refreshed' on success, 'unreachable' if the backend could not be
   * reached (network error — the caller must NOT log out), or 'failed' if the
   * backend refused the refresh (the session is genuinely dead).
   */
  private async tryRefresh(): Promise<'refreshed' | 'failed' | 'unreachable'> {
    // Prefer a wired auth provider so cached user data is refreshed in step.
    for (const provider of this.authProviders) {
      if (provider.isAuthenticated()) {
        try {
          const result = await provider.refreshSession();
          if (result.success) return 'refreshed';
          if (result.error === 'unreachable') return 'unreachable';
          return 'failed';
        } catch {
          // Fall through to the direct refresh below.
        }
      }
    }

    // Fallback: hit the refresh endpoint directly (providers may be unset/stale).
    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      return response.ok ? 'refreshed' : 'failed';
    } catch {
      return 'unreachable';
    }
  }

  /**
   * Clear cached session data and notify the app of an auth failure.
   * Clears sessionStorage directly (key shared with SSOAuthService) so the UI
   * cannot keep showing a logged-in state even when no providers were wired in.
   */
  private handleAuthFailure(): void {
    this.authProviders.forEach((p) => {
      try { p.clearSession(); } catch { /* ignore */ }
    });
    if (typeof window !== 'undefined') {
      try { sessionStorage.removeItem('auth_user'); } catch { /* ignore */ }
    }
    this.onAuthError();
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'POST', data });
  }

  async put<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'PUT', data });
  }

  async patch<T>(endpoint: string, data?: any, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'PATCH', data });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T>;
  async delete<T>(endpoint: string, data: any, options?: RequestOptions): Promise<T>;
  async delete<T>(endpoint: string, dataOrOptions?: any, options?: RequestOptions): Promise<T> {
    // 3-arg form (endpoint, data, options): DELETE with a request body.
    // 1/2-arg form (endpoint, options): options carries params, no body.
    if (options !== undefined) {
      return this.request<T>(endpoint, { ...options, method: 'DELETE', data: dataOrOptions });
    }
    return this.request<T>(endpoint, { ...((dataOrOptions as RequestOptions) ?? {}), method: 'DELETE' });
  }

  async request<T>(
    endpoint: string,
    options: RequestOptions & { method: string; data?: any }
  ): Promise<T> {
    const {
      method,
      data,
      skipAuth,
      params,
      headers: customHeaders,
      body: rawBody,
      ...restOptions
    } = options;

    const headers = skipAuth ? {} : this.getHeaders();
    const url = this.buildUrl(endpoint, params);

    let body: BodyInit | undefined = rawBody as BodyInit | undefined;
    if (data !== undefined) {
      body = data instanceof FormData ? data : JSON.stringify(data);
    }

    const methodUpper = method.toUpperCase();

    const fetchInit: RequestInit = {
      ...restOptions,
      method: methodUpper,
      headers: {
        ...headers,
        ...(customHeaders ?? {}),
      },
      body: ['GET', 'HEAD'].includes(methodUpper) ? undefined : body,
      // CRITICAL: Include credentials (cookies) in all requests
      credentials: 'include',
    };

    let response = await fetch(url, fetchInit);

    // On 401, refresh the access token once and retry the original request.
    // A thrown network error never reaches here — it propagates to the caller,
    // so an offline / VPN-down state surfaces as an inline error in the page
    // rather than a logout or a redirect.
    if (response.status === 401 && !skipAuth) {
      const outcome = await this.tryRefresh();
      if (outcome === 'refreshed') {
        response = await fetch(url, fetchInit);
      } else if (outcome === 'failed') {
        // Genuine auth failure: clear the cached session and notify the app.
        this.handleAuthFailure();
      }
      // outcome === 'unreachable': fall through and let the 401 be thrown below;
      // the session stays intact so a network blip never forces a logout.
    }

    return this.handleResponse<T>(response, methodUpper);
  }

  private buildUrl(endpoint: string, params?: Record<string, unknown>): string {
    if (!params || Object.keys(params).length === 0) {
      return `${this.baseURL}${endpoint}`;
    }

    const searchParams = new URLSearchParams();

    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) {
        continue;
      }

      if (Array.isArray(value)) {
        value
          .filter((item) => item !== undefined && item !== null)
          .forEach((item) => searchParams.append(key, String(item)));
      } else if (value instanceof Date) {
        searchParams.append(key, value.toISOString());
      } else if (typeof value === 'object') {
        searchParams.append(key, JSON.stringify(value));
      } else {
        searchParams.append(key, String(value));
      }
    }

    const query = searchParams.toString();
    if (!query) {
      return `${this.baseURL}${endpoint}`;
    }

    return `${this.baseURL}${endpoint}?${query}`;
  }
}

// Export a singleton instance (configured separately)
export const apiClient = new APIClient();

// Export the class for custom instances
export { APIClient };

// Export types
export type { APIClientConfig, RequestOptions };
