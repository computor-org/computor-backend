import { IAuthProvider } from '../interfaces/IAuthProvider';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  params?: Record<string, unknown>;
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
      if (response.status === 401) {
        // Try to refresh session with any available provider
        let refreshed = false;

        for (const provider of this.authProviders) {
          if (provider.isAuthenticated()) {
            const refreshResult = await provider.refreshSession();
            if (refreshResult.success) {
              refreshed = true;
              break;
            }
          }
        }

        // If refresh failed, clear sessions and trigger auth error callback
        if (!refreshed) {
          this.authProviders.forEach(p => p.clearSession());
          this.onAuthError();
        }
      }

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

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'DELETE' });
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

    const response = await fetch(url, {
      ...restOptions,
      method: methodUpper,
      headers: {
        ...headers,
        ...(customHeaders ?? {}),
      },
      body: ['GET', 'HEAD'].includes(methodUpper) ? undefined : body,
      // CRITICAL: Include credentials (cookies) in all requests
      credentials: 'include',
    });

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
