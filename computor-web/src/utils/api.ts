import { apiFetch, API_BASE_URL } from './apiClient';

/**
 * Thin typed wrapper over apiFetch: one consistent fetching style for pages.
 *
 *   const orgs = await api.get<OrganizationList[]>('/organizations');
 *   await api.patch(`/organizations/${id}`, { title });
 *
 * Resolves the parsed JSON body, throws an Error with the server's message on a
 * non-2xx response (so callers just try/catch), and handles 204 No Content.
 * `path` is relative to API_BASE_URL.
 *
 * PREFER the generated clients in `src/generated/clients/*` for new code — this
 * helper is retained only for the three endpoints without a usable generated
 * method: the two ambiguous dual-route deletes `DELETE /organizations/{id}` and
 * `DELETE /course-families/{id}` (left hand-typed to preserve the exact route
 * the backend matches), and `DELETE /examples/{id}` (the backend emits no
 * single-id example delete). Everything else — including all `/user*` and
 * `/consent/*` calls — now uses generated clients.
 */
async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `Request failed (${res.status})`);
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

const jsonInit = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  get: <T>(path: string) => apiFetch(`${API_BASE_URL}${path}`).then((r) => handle<T>(r)),
  post: <T>(path: string, body?: unknown) => apiFetch(`${API_BASE_URL}${path}`, jsonInit('POST', body)).then((r) => handle<T>(r)),
  put: <T>(path: string, body?: unknown) => apiFetch(`${API_BASE_URL}${path}`, jsonInit('PUT', body)).then((r) => handle<T>(r)),
  patch: <T>(path: string, body?: unknown) => apiFetch(`${API_BASE_URL}${path}`, jsonInit('PATCH', body)).then((r) => handle<T>(r)),
  del: <T = void>(path: string) => apiFetch(`${API_BASE_URL}${path}`, { method: 'DELETE' }).then((r) => handle<T>(r)),
};
