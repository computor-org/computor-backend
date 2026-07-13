import { API_BASE_URL, apiFetch } from '@/src/utils/apiClient';

interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  params?: Record<string, unknown>;
  data?: unknown;
}

/**
 * A non-2xx API response, surfaced as a throwable Error.
 *
 * The backend returns structured error bodies (`{ message, error_code? }`,
 * see computor-backend error_registry.yaml + generate.sh). This parses that
 * shape so `error.message` is the human-readable backend message — safe to
 * drop straight into `notify(err.message, 'error')` — while `errorCode` lets
 * callers branch on a stable code (looked up in
 * `@/src/generated/types/error-codes`). Extends Error, so existing
 * `catch (e) { e instanceof Error ? e.message : … }` sites keep working and
 * now show the real message instead of raw JSON.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly errorCode?: string;
  readonly details?: unknown;

  constructor(message: string, opts: { status: number; errorCode?: string; details?: unknown }) {
    super(message);
    this.name = 'ApiError';
    this.status = opts.status;
    this.errorCode = opts.errorCode;
    this.details = opts.details;
  }
}

/**
 * Build an ApiError from a non-2xx Response, extracting the backend's
 * `{ message, error_code, details }` (falling back to `detail`, then the raw
 * body text, then a status line). Never throws — always resolves to an ApiError.
 */
async function buildApiError(response: Response): Promise<ApiError> {
  const status = response.status;
  const raw = await response.text().catch(() => '');
  let message = raw;
  let errorCode: string | undefined;
  let details: unknown;

  if (raw) {
    try {
      const body = JSON.parse(raw) as Record<string, unknown>;
      if (body && typeof body === 'object') {
        const m = body.message ?? body.detail;
        if (typeof m === 'string') message = m;
        if (typeof body.error_code === 'string') errorCode = body.error_code;
        details = body.details;
      }
    } catch {
      // Body isn't JSON — keep the raw text as the message.
    }
  }

  if (!message) message = `HTTP error! status: ${status}`;
  return new ApiError(message, { status, errorCode, details });
}

/**
 * Configuration for APIClient
 */
interface APIClientConfig {
  baseURL?: string;
}

/**
 * Typed HTTP client for API requests with HttpOnly cookie-based authentication.
 *
 * The network round-trip — credentials, 401→refresh→retry, and the consent-gate
 * 403 interception — is delegated to `apiFetch` (the single low-level transport).
 * This class adds param serialization, body encoding, and typed response parsing
 * on top; it backs the generated clients under src/generated/clients.
 *
 * SECURITY:
 * - Uses HttpOnly cookies for authentication (set by backend)
 * - Tokens are NOT accessible to JavaScript (XSS protection)
 * - CSRF protection via SameSite cookie attribute (backend responsibility)
 */
class APIClient {
  private baseURL: string;

  constructor(config: APIClientConfig = {}) {
    this.baseURL = config.baseURL || API_BASE_URL;
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
   * Parse a response into the typed payload, throwing on a non-2xx status.
   * The consent-gate interception and 401 refresh already happened inside
   * `apiFetch`, so this only decodes the body.
   */
  private async handleResponse<T>(response: Response, method?: string): Promise<T> {
    if (!response.ok) {
      throw await buildApiError(response);
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

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'POST', data });
  }

  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'PUT', data });
  }

  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...(options ?? {}), method: 'PATCH', data });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T>;
  async delete<T>(endpoint: string, data: unknown, options?: RequestOptions): Promise<T>;
  async delete<T>(endpoint: string, dataOrOptions?: unknown, options?: RequestOptions): Promise<T> {
    // 3-arg form (endpoint, data, options): DELETE with a request body.
    // 1/2-arg form (endpoint, options): options carries params, no body.
    if (options !== undefined) {
      return this.request<T>(endpoint, { ...options, method: 'DELETE', data: dataOrOptions });
    }
    return this.request<T>(endpoint, { ...((dataOrOptions as RequestOptions) ?? {}), method: 'DELETE' });
  }

  async request<T>(
    endpoint: string,
    options: RequestOptions & { method: string; data?: unknown }
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
    };

    // Delegate the network round-trip to the single low-level transport:
    // credentials, the coalesced 401→refresh→retry, and the consent-gate
    // interception all live in apiFetch. A thrown network error propagates to
    // the caller (offline / VPN-down surfaces as an inline error, not a logout).
    const response = await apiFetch(url, fetchInit, !skipAuth);

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
