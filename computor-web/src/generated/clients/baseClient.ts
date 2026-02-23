/**
 * Auto-generated helper utilities for API endpoint clients.
 */

import { APIClient, apiClient } from 'api/client';

export class BaseEndpointClient {
  protected readonly client: APIClient;
  protected readonly basePath: string;

  constructor(client: APIClient = apiClient, basePath: string) {
    this.client = client;
    if (!basePath) {
      this.basePath = '/';
      return;
    }

    const normalized = basePath.startsWith('/') ? basePath : `/${basePath}`;
    this.basePath = normalized !== '/' && normalized.endsWith('/') ? normalized.slice(0, -1) : normalized;
  }

  protected buildPath(...segments: (string | number)[]): string {
    if (!segments.length) {
      return this.basePath;
    }

    const encoded = segments.map((segment) => encodeURIComponent(String(segment)));
    const joined = encoded.join('/');
    if (this.basePath === '/') {
      return `/${joined}`;
    }

    return `${this.basePath}/${joined}`;
  }
}
