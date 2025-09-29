/**
 * Auto-generated client for ExtensionInterface.
 * Endpoint: /extensions
 */

import type { ExtensionMetadata, ExtensionPublishRequest, ExtensionVersionListItem, ExtensionVersionYankRequest } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ExtensionClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/extensions');
  }

  async create(payload: ExtensionPublishRequest): Promise<ExtensionMetadata> {
    return this.client.post<ExtensionMetadata>(this.basePath, payload);
  }

  async get(id: string | number): Promise<ExtensionMetadata> {
    return this.client.get<ExtensionMetadata>(this.buildPath(id));
  }

  async list(params?: Record<string, unknown>): Promise<ExtensionVersionListItem[]> {
    const queryParams = params ? (params as unknown as Record<string, unknown>) : undefined;
    return this.client.get<ExtensionVersionListItem[]>(this.basePath, queryParams ? { params: queryParams } : undefined);
  }

  async update(id: string | number, payload: ExtensionVersionYankRequest): Promise<ExtensionMetadata> {
    return this.client.patch<ExtensionMetadata>(this.buildPath(id), payload);
  }

  async delete(id: string | number): Promise<void> {
    await this.client.delete<void>(this.buildPath(id));
  }
}
